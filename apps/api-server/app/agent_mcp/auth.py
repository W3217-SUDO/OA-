"""仅在当前 HTTP 请求中保留原始 OA 登录凭据。"""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import re

from fastapi import HTTPException, Request
from starlette.datastructures import Headers
from starlette.responses import JSONResponse

from app.config import settings
from app.database import SessionLocal
from app.security import current_identity
from app.agent_mcp.config import origin_allowed


@dataclass
class AuthContext:
    application: object = field(repr=False)
    bearer: str = field(repr=False)
    scope: dict = field(repr=False)
    active: bool = True


_auth_context: ContextVar[AuthContext | None] = ContextVar("oa_mcp_auth_context", default=None)
_case_origin: ContextVar[int | None] = ContextVar("oa_mcp_case_origin", default=None)


def get_auth_context() -> AuthContext:
    context = _auth_context.get()
    if context is None or not context.active or not context.bearer:
        raise HTTPException(401, "MCP 调用需要当前有效的 OA 登录请求")
    return context


async def authenticated_identity(db=None) -> dict:
    context = get_auth_context()
    # 认证入口不携带页面能力；实际业务权限由原路由自己的依赖重新计算。
    scope = {**context.scope, "path": settings.api_prefix + "/agent-tools/catalog", "query_string": b""}
    scope["headers"] = [(b"authorization", f"Bearer {context.bearer}".encode("latin-1"))]
    request = Request(scope)
    if db is not None:
        return await current_identity(request, token=context.bearer, db=db)
    async with SessionLocal() as session:
        return await current_identity(request, token=context.bearer, db=session)


@contextmanager
def tool_origin(case_id: int):
    context = get_auth_context()
    match = re.fullmatch(
        re.escape(settings.api_prefix) + r"/case-spaces/(\d+)/agent/messages",
        context.scope["path"],
    )
    if type(case_id) is not int or case_id <= 0 or match is None or int(match[1]) != case_id:
        raise HTTPException(403, "案件来源必须来自当前已授权的案件智能体入口")
    token = _case_origin.set(case_id)
    try:
        yield
    finally:
        _case_origin.reset(token)


def trusted_case_origin() -> int | None:
    get_auth_context()
    return _case_origin.get()


def require_human_decision(request_id: str) -> None:
    context = get_auth_context()
    path = context.scope["path"]
    base = re.escape(settings.api_prefix)
    allowed = (
        path == settings.api_prefix + f"/agent-tools/requests/{request_id}/decision"
        or re.fullmatch(base + r"/case-spaces/\d+/agent/actions/[^/]+/decision", path)
        or re.fullmatch(base + r"/case-spaces/\d+/agent/actions/[^/]+/restore", path)
        or re.fullmatch(base + r"/personal-agent/actions/[^/]+/decision", path)
    )
    if context.scope.get("method") != "POST" or not allowed:
        raise HTTPException(403, "业务执行只能由人工确认入口发起")
    headers = Headers(scope=context.scope)
    if (
        headers.get("x-oa-agent-confirmation") != "frontend"
        or not origin_allowed(headers.get("origin", ""))
    ):
        raise HTTPException(403, "请在 OA 前端确认按钮发起决定，来源或人工确认标识无效")


class RequestAuthContextMiddleware:
    def __init__(self, app, *, application):
        self.app = app
        self.application = application

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        authorization = Headers(scope=scope).get("authorization", "")
        scheme, separator, value = authorization.partition(" ")
        bearer = value.strip() if separator and scheme.lower() == "bearer" else ""
        context = AuthContext(self.application, bearer, dict(scope))
        token = _auth_context.set(context)
        origin_token = _case_origin.set(None)
        try:
            if scope["path"].rstrip("/") == settings.api_prefix + "/mcp":
                try:
                    await authenticated_identity()
                except HTTPException as exc:
                    await JSONResponse(
                        {"detail": exc.detail}, status_code=exc.status_code,
                        headers={"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else {},
                    )(scope, receive, send)
                    return
            await self.app(scope, receive, send)
        finally:
            context.active = False
            context.bearer = ""
            context.scope.clear()
            _case_origin.reset(origin_token)
            _auth_context.reset(token)
