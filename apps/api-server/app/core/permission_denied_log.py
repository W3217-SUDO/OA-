"""每次 403 都记一行日志（账号、所在页面、接口、原因），用来盯“能看见却说没权限”是否还有遗漏。"""
import logging
from urllib.parse import unquote

import jwt
from fastapi import Request
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings

logger = logging.getLogger("oa.permission_denied")


def _username(request: Request) -> str:
    header = request.headers.get("authorization") or ""
    if not header.lower().startswith("bearer "):
        return ""
    try:
        return str(jwt.decode(header[7:], settings.secret_key, algorithms=["HS256"]).get("sub") or "")
    except jwt.PyJWTError:
        return ""


async def permission_denied_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 403:
        logger.warning(
            "permission-denied user=%s page=%s method=%s path=%s detail=%s",
            _username(request), unquote(request.headers.get("x-oa-page") or "")[:120],
            request.method, request.url.path, str(exc.detail)[:200],
        )
    return await http_exception_handler(request, exc)
