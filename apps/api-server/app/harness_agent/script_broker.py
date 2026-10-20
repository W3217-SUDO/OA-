"""root 所有的技能隔离服务；只接收包字节和脚本参数，不接收宿主路径或容器配置。"""

import asyncio
import base64
import binascii
import errno
import hashlib
import json
import os
import logging
from pathlib import Path
import re
import socket
import signal
import stat
import struct
import time

from fastapi import HTTPException

from .script_container import execute, relative_path, verify_runtime
from .script_network import identifiers

MAX_REQUEST = 48 * 1024 * 1024


def unpack(payload):
    if set(payload) != {"method", "path", "args", "files", "manifest"}:
        raise HTTPException(422, "技能运行参数包含未允许字段")
    files, manifest = payload["files"], payload["manifest"]
    if not isinstance(files, dict) or not isinstance(manifest, dict) or set(files) != set(manifest) or not 0 < len(files) <= 512:
        raise HTTPException(422, "技能资源清单无效")
    result, total = {}, 0
    for name, value in files.items():
        path = relative_path(name)
        if str(path) != name or not isinstance(value, str) or len(value) > 12 * 1024 * 1024:
            raise HTTPException(422, "技能资源路径或内容无效")
        try:
            data = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError):
            raise HTTPException(422, "技能资源必须使用有效 Base64") from None
        total += len(data)
        if len(data) > 8 * 1024 * 1024 or total > 32 * 1024 * 1024:
            raise HTTPException(413, "技能资源超过执行上限")
        if hashlib.sha256(data).hexdigest() != manifest[name]:
            raise HTTPException(409, "技能资源与摘要不符，已阻止执行")
        result[name] = data
    return result


class Broker:
    def __init__(self, image, network, api_uid):
        if not re.fullmatch(r"(?:[A-Za-z0-9./_:-]+@)?sha256:[a-f0-9]{64}", image):
            raise ValueError("技能运行镜像必须固定 SHA256 摘要")
        identifiers(network)
        self.image, self.network, self.api_uid = image, network, api_uid
        self.active = 0
        self.checked = 0

    async def status(self):
        if time.monotonic() - self.checked >= 10:
            await asyncio.to_thread(verify_runtime, self.image, self.network)
            self.checked = time.monotonic()
        return {"ready": True}

    async def handle(self, reader, writer):
        try:
            result = await self.invoke(reader, writer)
            if result is not None:
                data = json.dumps(result, ensure_ascii=False).encode()
                writer.write(struct.pack("!I", len(data)) + data)
                await writer.drain()
        except (ConnectionError, OSError):
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except (ConnectionError, OSError):
                pass

    async def invoke(self, reader, writer):
        task, monitor = None, None
        occupied = False
        try:
            peer = writer.get_extra_info("socket").getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
            _, uid, _ = struct.unpack("3i", peer)
            if uid != self.api_uid:
                raise HTTPException(403, "技能运行服务调用身份无权访问")
            if self.active >= 2:
                raise HTTPException(429, "技能隔离运行服务忙，请稍后重试")
            self.active += 1
            occupied = True
            async with asyncio.timeout(15):
                size = struct.unpack("!I", await reader.readexactly(4))[0]
                if not 0 < size <= MAX_REQUEST:
                    raise HTTPException(413, "技能执行请求超过上限")
                payload = json.loads(await reader.readexactly(size))
            if not isinstance(payload, dict):
                raise HTTPException(422, "技能执行请求必须为对象")
            if payload == {"method": "status"}:
                result = await self.status()
            elif payload.get("method") == "run":
                files = unpack(payload)
                task = asyncio.create_task(execute(files, payload["path"], payload["args"], self.image, self.network))
                monitor = asyncio.create_task(reader.read(1))
                done, _ = await asyncio.wait({task, monitor}, return_when=asyncio.FIRST_COMPLETED)
                if monitor in done:
                    task.cancel()
                    results = await asyncio.gather(task, return_exceptions=True)
                    if isinstance(results[0], HTTPException):
                        logging.error("技能执行断连后的清理失败：%s", results[0].detail)
                    return None
                result = await task
            else:
                raise HTTPException(422, "技能运行服务不支持此操作")
        except HTTPException as exc:
            result = {"error": str(exc.detail), "status": exc.status_code}
        except (ValueError, OSError, asyncio.IncompleteReadError, TimeoutError):
            result = {"error": "技能运行请求或连接无效", "status": 422}
        finally:
            if monitor is not None:
                monitor.cancel()
                await asyncio.gather(monitor, return_exceptions=True)
            if task is not None and not task.done():
                task.cancel()
                results = await asyncio.gather(task, return_exceptions=True)
                if isinstance(results[0], HTTPException):
                    logging.error("技能运行服务停止后的清理失败：%s", results[0].detail)
            if occupied:
                self.active -= 1
        return result


async def serve(path, image, network, api_uid, api_gid):
    location = Path(path)
    if not location.is_absolute() or location.is_symlink() or len(path.encode()) > 100:
        raise ValueError("技能运行 socket 路径无效")
    location.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    if location.parent.is_symlink() or location.parent.stat().st_uid != 0 or location.parent.stat().st_mode & 0o022:
        raise ValueError("技能运行 socket 父目录必须由 root 所有且不可由其他用户写入")
    os.chown(location.parent, 0, api_gid)
    location.parent.chmod(0o750)
    if location.exists():
        previous = location.lstat()
        if previous.st_uid != 0 or not stat.S_ISSOCK(previous.st_mode):
            raise ValueError("技能运行 socket 已存在且归属不符，未覆盖")
        with socket.socket(socket.AF_UNIX) as probe:
            code = probe.connect_ex(path)
        if code != errno.ECONNREFUSED or location.lstat().st_ino != previous.st_ino:
            raise ValueError("技能运行 socket 正在使用或已变化，未覆盖")
        location.unlink()
    broker = Broker(image, network, api_uid)
    handlers = set()

    def connected(reader, writer):
        task = asyncio.create_task(broker.handle(reader, writer))
        handlers.add(task)
        task.add_done_callback(handlers.discard)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for value in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(value, stop.set)
    server = await asyncio.start_unix_server(connected, path)
    os.chown(location, 0, api_gid)
    location.chmod(0o660)
    try:
        async with server:
            await stop.wait()
    finally:
        server.close()
        await server.wait_closed()
        pending = list(handlers)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        location.unlink(missing_ok=True)


def main():
    import pwd
    import sys
    if sys.platform != "linux" or os.geteuid() != 0:
        raise SystemExit("隔离运行服务必须由独立的 Linux root 系统服务启动")
    account = pwd.getpwnam(os.environ["OA_SKILL_RUNNER_API_USER"])
    if account.pw_uid == 0:
        raise SystemExit("OA API 必须使用独立的非 root 用户")
    asyncio.run(serve(os.environ["OA_SKILL_RUNNER_SOCKET"], os.environ["OA_SKILL_RUNNER_IMAGE"],
                      os.environ["OA_SKILL_RUNNER_NETWORK"], account.pw_uid, account.pw_gid))


if __name__ == "__main__":
    main()
