"""全接口低开销慢请求观测，不记录请求参数、身份、SQL 文本或业务数据。"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import logging
from time import perf_counter

from sqlalchemy import event


logger = logging.getLogger(__name__)


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
