"""在日志记录创建时收敛个人MCP的SDK日志，覆盖动态子logger。"""
from contextlib import contextmanager
from contextvars import ContextVar
import logging

_ACTIVE = ContextVar('personal_mcp_safe_logging', default=False)


def _record_factory(*args, _factory=logging.getLogRecordFactory(), **kwargs):
    record = _factory(*args, **kwargs)
    if _ACTIVE.get() and record.name.startswith(('mcp.', 'httpx2', 'httpcore2')):
        error_type = record.exc_info[0].__name__ if record.exc_info and record.exc_info[0] else 'none'
        record.msg = 'personal_mcp_sdk event level=%s error_type=%s'
        record.args = (record.levelname, error_type)
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
    return record


logging.setLogRecordFactory(_record_factory)


@contextmanager
def safe_sdk_logs():
    token = _ACTIVE.set(True)
    try:
        yield
    finally:
        _ACTIVE.reset(token)
