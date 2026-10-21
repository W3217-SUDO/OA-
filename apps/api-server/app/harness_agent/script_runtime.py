"""API 仅向受控 Unix socket 提交授权技能包，不持有 Docker 或防火墙权限。"""

from __future__ import annotations

import asyncio
import base64
from functools import lru_cache
import json
from pathlib import PurePosixPath
import re
import socket
import struct
import sys
import time

from fastapi import HTTPException

from app.config import settings

_SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".sh"}
MAX_REQUEST = 48 * 1024 * 1024
MAX_RESPONSE = 512 * 1024


def _socket_path():
    value = settings.deepseek_harness_skill_socket.strip()
    if sys.platform != "linux":
        raise HTTPException(503, "技能脚本需要 Linux 隔离运行服务")
    if not value.startswith("/") or len(value.encode()) > 100 or "\0" in value:
        raise HTTPException(503, "技能隔离运行服务尚未配置")
    return value


def _result(data):
    try:
        result = json.loads(data)
        if not isinstance(result, dict):
            raise ValueError
    except ValueError:
        raise HTTPException(502, "技能运行服务返回无效协议") from None
    if result.get("error"):
        status = result.get("status")
        raise HTTPException(status if type(status) is int and 400 <= status <= 599 else 502, str(result["error"]))
    return result


def _server_identity(handle):
    _, uid, _ = struct.unpack("3i", handle.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")))
    if uid != 0:
        raise HTTPException(503, "技能运行服务身份无效")


@lru_cache(maxsize=4)
def _probe(path, interval):
    def receive(handle, size):
        content = bytearray()
        while len(content) < size:
            chunk = handle.recv(size - len(content))
            if not chunk:
                raise OSError("技能运行服务连接已关闭")
            content.extend(chunk)
        return bytes(content)

    try:
        with socket.socket(socket.AF_UNIX) as handle:
            handle.settimeout(2)
            handle.connect(path)
            _server_identity(handle)
            data = b'{"method":"status"}'
            handle.sendall(struct.pack("!I", len(data)) + data)
            size = struct.unpack("!I", receive(handle, 4))[0]
            if not 0 < size <= MAX_RESPONSE:
                raise ValueError
            result = _result(receive(handle, size))
            if result.get("ready") is not True:
                raise ValueError
        return []
    except (OSError, ValueError, HTTPException):
        return ["verified-skill-runner-service"]


def runtime_status(bundle: dict | None, instruction: str) -> dict:
    files = (bundle or {}).get("files", {})
    scripts = [name for name in files if PurePosixPath(name).suffix in _SUFFIXES]
    external = bool(re.search(r"```(?:bash|sh|shell)|\b(?:npx|uvx|pip3?|npm)\s", instruction, re.I))
    if not scripts and not external:
        return {"mode": "instruction", "ready": True, "missing_dependencies": [],
                "resource_count": len(files), "message": "由 DSH 加载技能指令和已安装资源"}
    missing = []
    try:
        path = _socket_path()
    except HTTPException:
        missing.append("linux-skill-runner-service")
    else:
        missing.extend(_probe(path, int(time.monotonic() // 10)))
    if not scripts:
        missing.append("packaged-script")
    return {"mode": "script", "ready": not missing, "missing_dependencies": missing,
            "resource_count": len(files), "message": "缺少隔离运行依赖：" + "、".join(missing) if missing else
            "基础执行环境就绪；技能自身依赖按执行结果检查，仅准公网 HTTP/HTTPS，隔离宿主和 OA 凭据"}


async def run_script(skill, path, arguments):
    # 同一工具会话在每次调用前由 WorkspaceTools 重新读取启用状态和账号授权。
    from .script_container import relative_path
    from .bundles import read_resource

    script = relative_path(path)
    if script.suffix not in _SUFFIXES:
        raise HTTPException(422, "仅支持已安装技能包中的 Node、Python 或 Bash 脚本")
    if not isinstance(arguments, list) or len(arguments) > 32 or any(
        not isinstance(item, str) or len(item) > 2000 or "\0" in item for item in arguments
    ):
        raise HTTPException(422, "技能脚本参数必须为有限的字符串数组")
    if not skill.bundle or str(script) not in skill.bundle.get("files", {}):
        raise HTTPException(404, "此技能未安装完整脚本，请先安装完整技能包")
    endpoint = _socket_path()
    files = {name: base64.b64encode(read_resource(skill.bundle, name)).decode("ascii") for name in skill.bundle["files"]}
    payload = json.dumps({"method": "run", "path": str(script), "args": arguments,
                          "files": files, "manifest": skill.bundle["files"]}, ensure_ascii=False).encode()
    return {"skill": skill.id, **await _submit(endpoint, payload)}


_CODE_FILES = {"python": "main.py", "node": "main.js", "bash": "main.sh"}


async def run_code(language, code, arguments):
    """沙箱运行模型写的代码：把代码当作一个临时单文件技能包交给同一个隔离运行服务，不增加任何宿主权限。"""
    import hashlib
    if language not in _CODE_FILES:
        raise HTTPException(422, "沙箱只支持 python、node、bash")
    if not isinstance(code, str) or not code.strip() or len(code) > 200_000 or "\0" in code:
        raise HTTPException(422, "代码不能为空，且不能超过 200000 字符")
    if not isinstance(arguments, list) or len(arguments) > 32 or any(
        not isinstance(item, str) or len(item) > 2000 or "\0" in item for item in arguments
    ):
        raise HTTPException(422, "参数必须为有限的字符串数组")
    name = _CODE_FILES[language]
    data = code.encode("utf-8")
    payload = json.dumps({"method": "run", "path": name, "args": arguments,
                          "files": {name: base64.b64encode(data).decode("ascii")},
                          "manifest": {name: hashlib.sha256(data).hexdigest()}}, ensure_ascii=False).encode()
    return {"sandbox": language, **await _submit(_socket_path(), payload)}


async def _submit(endpoint, payload):
    if len(payload) > MAX_REQUEST:
        raise HTTPException(413, "技能运行请求超过上限")
    writer = None
    try:
        async with asyncio.timeout(75):
            reader, writer = await asyncio.open_unix_connection(endpoint)
            _server_identity(writer.get_extra_info("socket"))
            writer.write(struct.pack("!I", len(payload)) + payload)
            await writer.drain()
            size = struct.unpack("!I", await reader.readexactly(4))[0]
            if not 0 < size <= MAX_RESPONSE:
                raise HTTPException(502, "技能运行服务响应超过上限")
            return _result(await reader.readexactly(size))
    except TimeoutError as exc:
        raise HTTPException(504, "技能隔离运行服务响应超时，未取得完成结果") from exc
    except (OSError, asyncio.IncompleteReadError) as exc:
        raise HTTPException(503, "技能隔离运行服务不可用：" + type(exc).__name__) from None
    finally:
        # 关闭连接会触发 broker 取消本请求并精确清理其容器。
        if writer is not None:
            writer.close()
            await writer.wait_closed()
