"""将当前已认证 OA 请求的能力注册为临时、只监听回环地址的 MCP。"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, contextmanager
from contextvars import copy_context
import json
import secrets
import socket

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
import uvicorn


class _Server(uvicorn.Server):
    @contextmanager
    def capture_signals(self):
        # 内嵌能力通道不能接管主 API 进程的退出信号。
        yield


class _SwitchTools:
    """常驻会话的工具代理：每轮把调用转给当前请求的工具集，两轮之间没有可用的请求上下文。"""

    def __init__(self, holder):
        self.holder = holder

    async def execute(self, name, arguments):
        tools = self.holder.get("tools")
        if tools is None:
            raise HTTPException(409, "当前没有正在处理的请求，不能调用工作区能力")
        return await tools.execute(name, arguments)


@asynccontextmanager
async def workspace_mcp(tools, schemas, context_provider=None):
    """context_provider：常驻会话每轮提供当前请求的上下文（身份、事务等）；不传则固定使用创建时的上下文。"""
    secret = secrets.token_urlsafe(32)
    fixed_context = copy_context()
    current_context = context_provider or (lambda: fixed_context)
    serial = asyncio.Lock()
    application = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
    functions = {item["function"]["name"]: item["function"] for item in schemas}
    script_calls = {}

    @application.post("/mcp")
    async def invoke(request: Request):
        if not secrets.compare_digest(request.headers.get("authorization", ""), "Bearer " + secret):
            raise HTTPException(403, "工作区能力认证失败")
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 1024 * 1024:
                raise HTTPException(413, "能力请求超过上限")
        try:
            payload = json.loads(body)
        except ValueError as exc:
            raise HTTPException(422, "能力请求必须为 JSON") from exc
        if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0":
            raise HTTPException(422, "MCP 请求格式错误")
        method, params = payload.get("method"), payload.get("params", {})
        if "id" not in payload:
            if method == "notifications/cancelled" and isinstance(params, dict):
                identifier = params.get("requestId")
                if type(identifier) in {str, int} and identifier in script_calls:
                    script_calls[identifier].cancel()
                return Response(status_code=202)
            if method in {"notifications/initialized", "notifications/cancelled"}:
                return Response(status_code=202)
            raise HTTPException(422, "未知 MCP 通知")

        async def execute():
            if method == "initialize":
                return {"protocolVersion": "2025-03-26", "capabilities": {"tools": {}},
                        "serverInfo": {"name": "huzhi-workspace", "version": "1"}}
            if method == "ping":
                return {}
            if method == "tools/list":
                return {"tools": [{"name": item["name"], "description": item["description"],
                                   "inputSchema": item["parameters"]} for item in functions.values()]}
            if (method != "tools/call" or not isinstance(params, dict)
                    or not isinstance(params.get("name"), str) or params["name"] not in functions):
                raise HTTPException(422, "能力未在当前工作区注册")
            async with serial:
                result = await tools.execute(params["name"], params.get("arguments", {}))
            return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, default=str)}],
                    "isError": bool(isinstance(result, dict) and result.get("isError"))}

        script = method == "tools/call" and isinstance(params, dict) and params.get("name") == "harness_run_skill_script"
        task, monitor = None, None
        try:
            # 继承原请求的身份、案件范围和事务，不接受模型提供的用户名或令牌。
            if script:
                identifier = payload["id"]
                if type(identifier) not in {str, int} or identifier in script_calls:
                    raise HTTPException(422, "技能脚本请求编号无效或重复")
                task = current_context().run(asyncio.create_task, execute())
                script_calls[identifier] = task

                async def disconnected():
                    while not await request.is_disconnected():
                        await asyncio.sleep(0.1)

                monitor = asyncio.create_task(disconnected())
                done, _ = await asyncio.wait({task, monitor}, return_when=asyncio.FIRST_COMPLETED)
                if monitor in done:
                    task.cancel()
                result = await task
            else:
                result = await current_context().run(asyncio.create_task, execute())
            return JSONResponse({"jsonrpc": "2.0", "id": payload["id"], "result": result})
        except asyncio.CancelledError:
            if not script:
                raise
            return JSONResponse({"jsonrpc": "2.0", "id": payload["id"],
                                 "error": {"code": -32800, "message": "技能脚本调用已取消"}})
        except HTTPException as exc:
            return JSONResponse({"jsonrpc": "2.0", "id": payload["id"],
                                 "error": {"code": -32000, "message": str(exc.detail)}})
        finally:
            if task is not None:
                if script_calls.get(payload["id"]) is task:
                    script_calls.pop(payload["id"])
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            if monitor is not None:
                monitor.cancel()
                await asyncio.gather(monitor, return_exceptions=True)

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(16)
    server = _Server(uvicorn.Config(application, log_config=None, access_log=False,
                                   lifespan="off", timeout_keep_alive=1))
    task = asyncio.create_task(server.serve(sockets=[listener]))
    try:
        async with asyncio.timeout(10):
            while not server.started:
                if task.done():
                    await task
                    raise RuntimeError("工作区 MCP 启动失败")
                await asyncio.sleep(0.01)
        yield f"http://127.0.0.1:{listener.getsockname()[1]}/mcp", secret
    finally:
        pending = list(script_calls.values())
        for running in pending:
            running.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        server.should_exit = True
        try:
            await asyncio.wait_for(task, 5)
        except TimeoutError:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        listener.close()
