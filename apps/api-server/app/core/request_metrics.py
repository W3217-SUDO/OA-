"""全接口低开销慢请求观测，不记录请求参数、身份、SQL 文本或业务数据。"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import logging
from time import perf_counter

from sqlalchemy import event


logger = logging.getLogger(__name__)


class _WopiAccessLogFilter(logging.Filter):
    """仅移除 WOPI access 日志的查询串，保留其余请求监控字段。"""

    def __init__(self, api_prefix):
        super().__init__()
        self.path_prefix = api_prefix.rstrip("/") + "/office/wopi/"

    def filter(self, record):
        args = record.args
        # Uvicorn 的 access 记录依次包含客户端、方法、地址、协议和状态码。
        if isinstance(args, tuple) and len(args) == 5 and isinstance(args[2], str):
            path = args[2].partition("?")[0]
            if path.startswith(self.path_prefix):
                record.args = (*args[:2], path, *args[3:])
        return True


def _install_wopi_access_filter(api_prefix):
    access_logger = logging.getLogger("uvicorn.access")
    path_prefix = api_prefix.rstrip("/") + "/office/wopi/"
    if not any(isinstance(item, _WopiAccessLogFilter) and item.path_prefix == path_prefix
               for item in access_logger.filters):
        access_logger.addFilter(_WopiAccessLogFilter(api_prefix))


@dataclass
class RequestMetrics:
    started: float = field(default_factory=perf_counter)
    queries: int = 0
    sql_execute_seconds: float = 0
    headers_seconds: float | None = None
    phases: dict[str, float] = field(default_factory=dict)
    closed: bool = False


_current: ContextVar[RequestMetrics | None] = ContextVar("oa_request_metrics", default=None)


@contextmanager
def measure_phase(name):
    metrics = _current.get()
    started = perf_counter()
    try:
        yield
    finally:
        if metrics is not None and not metrics.closed:
            metrics.phases[name] = metrics.phases.get(name, 0) + perf_counter() - started


def add_phase(name, seconds, metrics=None):
    """记录一段已经算好的耗时（如在线程里测得的），与 measure_phase 合并输出。"""
    metrics = metrics or _current.get()
    if metrics is not None and not metrics.closed:
        metrics.phases[name] = metrics.phases.get(name, 0) + seconds


def current_metrics():
    return _current.get()


def install_query_metrics(engine):
    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def before_execute(conn, cursor, statement, parameters, context, executemany):
        metrics = _current.get()
        if metrics is not None and not metrics.closed:
            metrics.queries += 1
            context._oa_request_timing = (metrics, perf_counter())

    def finish(context):
        timing = getattr(context, "_oa_request_timing", None)
        if timing is not None:
            metrics, started = timing
            if not metrics.closed:
                metrics.sql_execute_seconds += perf_counter() - started
            del context._oa_request_timing

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def after_execute(conn, cursor, statement, parameters, context, executemany):
        finish(context)

    @event.listens_for(engine.sync_engine, "handle_error")
    def on_error(exception_context):
        finish(exception_context.execution_context)


class RequestMetricsMiddleware:
    def __init__(self, app, *, api_prefix, threshold_seconds):
        _install_wopi_access_filter(api_prefix)
        self.app = app
        self.api_prefix = api_prefix
        self.threshold_seconds = threshold_seconds

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope.get("path", "").startswith(self.api_prefix + "/"):
            await self.app(scope, receive, send)
            return
        metrics = RequestMetrics()
        token = _current.set(metrics)
        status = 500
        elapsed = None

        async def measured_send(message):
            nonlocal status, elapsed
            if message["type"] == "http.response.start":
                status = message["status"]
                metrics.headers_seconds = perf_counter() - metrics.started
            await send(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                elapsed = perf_counter() - metrics.started
                metrics.closed = True

        try:
            await self.app(scope, receive, measured_send)
        finally:
            elapsed = elapsed if elapsed is not None else perf_counter() - metrics.started
            metrics.closed = True
            _current.reset(token)
            if elapsed >= self.threshold_seconds:
                route = scope.get("route")
                # 仅输出路由模板，未知入口也不输出可能含客户编号的原始路径。
                path = getattr(route, "path", "<unmatched>")
                logger.warning(
                    "slow_api method=%s route=%s status=%s total_ms=%.1f headers_ms=%s queries=%s sql_execute_ms=%.1f phases_ms=%s",
                    scope.get("method"), path, status, elapsed * 1000,
                    round(metrics.headers_seconds * 1000, 1) if metrics.headers_seconds is not None else None,
                    metrics.queries, metrics.sql_execute_seconds * 1000,
                    {name: round(seconds * 1000, 1) for name, seconds in metrics.phases.items()},
                )
