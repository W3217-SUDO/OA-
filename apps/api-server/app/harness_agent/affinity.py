"""将同一已认证对话交给原有 API 进程，复用该进程中的常驻运行时。"""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import json
import os
import re
import secrets
import socket
from uuid import uuid4

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import httpx
import uvicorn

from app.config import settings
from .bridge import _Server


_OWNER = uuid4().hex
_START = asyncio.Lock()
_PEER = None
_HEADER = "x-oa-resident-peer"
_SCOPE = "oa.resident.peer"
_HTTP_TURN = ContextVar("oa_resident_http_turn", default=None)


@contextmanager
def request_turn(application):
    token = _HTTP_TURN.set(application)
    try:
        yield
    finally:
        _HTTP_TURN.reset(token)


def _directory():
    from .runtime import storage_root

    root = storage_root() / "resident-routing"
    for path in (root, root / "workers", root / "routes"):
        if path.is_symlink():
            raise HTTPException(503, "智能体会话路由目录无效")
        path.mkdir(exist_ok=True, mode=0o700)
    return root


def _route(root, username, conversation):
    key = hashlib.sha256(json.dumps([username.casefold(), conversation]).encode()).hexdigest()
    return root / "routes" / (key + ".json")


def _write(path, value):
    if path.is_symlink():
        raise HTTPException(503, "智能体会话路由记录无效")
    temporary = path.with_name(uuid4().hex + ".pending")
    try:
        with temporary.open("x", encoding="utf-8") as file:
            temporary.chmod(0o600)
            json.dump(value, file)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class _PeerApplication:
    def __init__(self, app, secret):
        self.app, self.secret = app, secret

    async def __call__(self, scope, receive, send):
        headers = dict(scope.get("headers", []))
        path = scope.get("path", "")
        prefix = settings.api_prefix + "/personal-agent/"
        allowed = path == prefix + "messages" or re.fullmatch(re.escape(prefix) + r"conversations/[^/]+/stop", path)
        if (scope["type"] != "http" or scope.get("method") != "POST" or not allowed
                or not secrets.compare_digest(headers.get(_HEADER.encode(), b""), self.secret.encode())):
            await send({"type": "http.response.start", "status": 403, "headers": []})
            await send({"type": "http.response.body", "body": b""})
            return
        # 私有通道也必须经过原来的登录、账号和工作区校验，不能代替用户身份。
        scope = dict(scope, **{_SCOPE: True})
        scope["headers"] = [(key, value) for key, value in scope["headers"] if key != _HEADER.encode()]
        await self.app(scope, receive, send)


async def claim(username, conversation):
    """仅在业务层完成当前对话权限检查后登记归属。"""
    global _PEER
    application = _HTTP_TURN.get()
    if application is None:
        return
    root = _directory()
    async with _START:
        if _PEER is None:
            listener = socket.socket()
            listener.bind(("127.0.0.1", 0))
            listener.listen(128)
            secret = secrets.token_urlsafe(32)
            server = _Server(uvicorn.Config(_PeerApplication(application, secret), log_config=None,
                                           access_log=False, lifespan="off"))
            task = asyncio.create_task(server.serve(sockets=[listener]))
            try:
                async with asyncio.timeout(5):
                    while not server.started:
                        if task.done():
                            await task
                            raise HTTPException(503, "智能体会话路由未能启动")
                        await asyncio.sleep(0.01)
                record = root / "workers" / (_OWNER + ".json")
                _write(record, {"pid": os.getpid(), "port": listener.getsockname()[1], "token": secret})
                _PEER = (server, task, record)
            except BaseException:
                server.should_exit = True
                await asyncio.gather(task, return_exceptions=True)
                listener.close()
                raise
        _write(_route(root, username, conversation), {"owner": _OWNER})


def _destination(username, conversation):
    root = _directory()
    route = _route(root, username, conversation)
    if not route.exists():
        return None
    try:
        if route.is_symlink():
            raise ValueError
        owner = json.loads(route.read_bytes())["owner"]
        if not isinstance(owner, str) or not re.fullmatch(r"[a-f0-9]{32}", owner):
            raise ValueError
        record = root / "workers" / (owner + ".json")
        if owner == _OWNER or not record.exists():
            return None
        if record.is_symlink():
            raise ValueError
        value = json.loads(record.read_bytes())
        if (type(value.get("pid")) is not int or value["pid"] <= 0
                or type(value.get("port")) is not int or not 1 <= value["port"] <= 65535
                or not isinstance(value.get("token"), str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", value["token"])):
            raise ValueError
        # 异常退出后的记录只在所属进程已不存在时失效；不向其他进程重放失败请求。
        if os.name == "posix":
            try:
                os.kill(value["pid"], 0)
            except ProcessLookupError:
                return None
        return value
    except (ValueError, KeyError, TypeError, OSError) as exc:
        raise HTTPException(503, "智能体会话路由记录不可用，未重新执行请求") from exc


async def forward(request, username, conversation):
    if request.scope.get(_SCOPE) or not conversation:
        return None
    target = _destination(username, conversation)
    if target is None:
        return None
    headers = {name: request.headers[name] for name in ("authorization", "content-type", "accept", "origin", "host")
               if name in request.headers}
    headers[_HEADER] = target["token"]
    client = httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(200, connect=3))
    try:
        response = await client.send(client.build_request("POST",
            f"http://127.0.0.1:{target['port']}{request.url.path}",
            headers=headers, content=await request.body()), stream=True)
    except BaseException as exc:
        await client.aclose()
        if isinstance(exc, httpx.HTTPError):
            raise HTTPException(503, "原智能体进程暂不可达，未重新执行请求") from exc
        raise

    async def stream():
        try:
            async for chunk in response.aiter_raw():
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    return StreamingResponse(stream(), status_code=response.status_code,
        headers={key: value for key, value in response.headers.items()
                 if key.lower() not in {"connection", "transfer-encoding", "content-length"}})


async def close():
    global _PEER
    if _PEER is not None:
        server, task, record = _PEER
        server.should_exit = True
        try:
            await asyncio.wait_for(task, 10)
        finally:
            record.unlink(missing_ok=True)
            _PEER = None
