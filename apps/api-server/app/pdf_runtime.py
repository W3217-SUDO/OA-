"""串行化同一进程内的 PDFium 原生调用。"""

from functools import wraps
from threading import Lock
from collections.abc import Callable
from typing import ParamSpec, TypeVar


PDFIUM_LOCK = Lock()
_Parameters = ParamSpec("_Parameters")
_Result = TypeVar("_Result")


def serialized_pdfium(function: Callable[_Parameters, _Result]) -> Callable[_Parameters, _Result]:
    """保护一次完整的文档打开、页面操作和关闭过程。"""
    @wraps(function)
    def guarded(*args: _Parameters.args, **kwargs: _Parameters.kwargs) -> _Result:
        with PDFIUM_LOCK:
            return function(*args, **kwargs)

    return guarded
