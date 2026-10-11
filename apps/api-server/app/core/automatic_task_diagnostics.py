"""按巡检结果变化记录自动任务告警，避免重复扫描淹没运行日志。"""

from contextlib import asynccontextmanager
from contextvars import ContextVar

from app.core.constants import logger


_current_warnings: ContextVar[set[str] | None] = ContextVar("automatic_task_warnings", default=None)
_previous_warnings: set[str] = set()


def warn_automatic_task(message: str, *args: object) -> None:
    """巡检内按内容去重；用户主动操作仍即时记录真实失败。"""
    warnings = _current_warnings.get()
    if warnings is None:
        logger.warning(message, *args)
        return
    warnings.add(message % args)


@asynccontextmanager
async def automatic_task_diagnostics_scope():
    """仅保留最近成功巡检的问题集合；异常轮次不覆盖已有状态。"""
    global _previous_warnings
    if _current_warnings.get() is not None:
        raise RuntimeError("自动任务诊断不能重复进入")
    warnings: set[str] = set()
    token = _current_warnings.set(warnings)
    try:
        yield
        new_warnings = warnings - _previous_warnings
        cleared_warnings = _previous_warnings - warnings
        for message in sorted(new_warnings):
            logger.warning("%s", message)
        if new_warnings or cleared_warnings:
            logger.info(
                "automatic task diagnostics changed: pending=%s new=%s cleared=%s",
                len(warnings), len(new_warnings), len(cleared_warnings),
            )
        _previous_warnings = warnings
    finally:
        _current_warnings.reset(token)
