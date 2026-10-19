"""多进程 API 的跨进程协调：后台任务选主与文件状态互斥。

uvicorn 以多个工作进程运行时，进程内的 asyncio.Lock 和全局字典只约束本进程。
本模块提供两类跨进程原语：

- ``run_background_leader``：用 PostgreSQL 会话级 advisory lock 选出唯一主进程，
  只有主进程运行会对外发消息或写业务数据的后台循环。主进程退出或连接断开时
  锁随会话释放，其他进程在下一轮竞争中接管。
- ``file_lock`` / ``file_lock_sync``：使用操作系统原生文件锁，保护多个进程
  共享的磁盘状态文件的读-改-写。

单进程运行或非 PostgreSQL 数据库（测试环境）时，行为与原先直接启动后台循环相同。
"""

from __future__ import annotations

import asyncio
import errno
import hashlib
import logging
import os
import tempfile
import time
from collections.abc import Awaitable, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager, suppress
from pathlib import Path
from typing import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

if os.name == 'nt':
    import msvcrt
else:
    import fcntl

logger = logging.getLogger(__name__)


def advisory_lock_id(name: str) -> int:
    """把稳定名称映射为 PostgreSQL bigint advisory lock 编号。"""
    return int.from_bytes(hashlib.sha256(f"sunhold-oa:{name}".encode()).digest()[:8], byteorder="big", signed=True)


BACKGROUND_LEADER_LOCK_ID = advisory_lock_id("background-leader")
LEADER_RETRY_SECONDS = 15.0
LEADER_HEARTBEAT_SECONDS = 10.0


async def _cancel_all(tasks: list[asyncio.Task]) -> None:
    for task in tasks:
        task.cancel()
    for task in tasks:
        with suppress(asyncio.CancelledError):
            await task


async def run_background_leader(
    engine: AsyncEngine,
    start_loops: Callable[[], list[asyncio.Task]],
    *,
    retry_seconds: float = LEADER_RETRY_SECONDS,
    heartbeat_seconds: float = LEADER_HEARTBEAT_SECONDS,
) -> None:
    """竞争主进程身份；取得后运行 ``start_loops`` 创建的任务，失去连接时停止。

    该协程本身应作为一个长期任务运行，取消它会停止已启动的后台循环并释放锁。
    """
    if engine.dialect.name != "postgresql":
        tasks = start_loops()
        try:
            await asyncio.gather(*tasks)
        finally:
            await _cancel_all(tasks)
        return

    pid = os.getpid()
    while True:
        connection = None
        tasks: list[asyncio.Task] = []
        wait_seconds = retry_seconds
        try:
            connection = await engine.connect()
            acquired = bool(await connection.scalar(
                text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": BACKGROUND_LEADER_LOCK_ID},
            ))
            # 会话级锁跨事务保留；结束隐式事务，避免主进程连接长期处于事务中。
            await connection.commit()
            if acquired:
                logger.info("后台任务主进程已就位 pid=%s", pid)
                tasks = start_loops()
                while True:
                    await asyncio.sleep(heartbeat_seconds)
                    # 连接失效即视为失去主进程身份，立即停止本进程的后台循环。
                    await connection.execute(text("SELECT 1"))
                    await connection.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("后台任务主进程连接异常，停止本进程后台循环并重新竞争 pid=%s", pid)
            wait_seconds = min(retry_seconds, 5.0)
        finally:
            # 先停止循环并结束会话，再等待下一轮竞争，避免失去锁后循环继续运行。
            if tasks:
                await _cancel_all(tasks)
                logger.info("后台任务主进程已退出 pid=%s", pid)
            if connection is not None:
                # 作废底层连接而不是归还连接池，确保会话结束、advisory lock 一定释放。
                with suppress(Exception):
                    await connection.invalidate()
                with suppress(Exception):
                    await connection.close()
        await asyncio.sleep(wait_seconds)


@asynccontextmanager
async def session_advisory_lock(engine: AsyncEngine, name: str) -> AsyncIterator[None]:
    """在一段异步初始化期间持有跨进程互斥；非 PostgreSQL 直接执行。"""
    if engine.dialect.name != "postgresql":
        yield
        return
    async with engine.connect() as connection:
        await connection.execute(text("SELECT pg_advisory_lock(:lock_id)"), {"lock_id": advisory_lock_id(name)})
        await connection.commit()
        try:
            yield
        finally:
            await connection.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": advisory_lock_id(name)})
            await connection.commit()


def coordination_path(name: str) -> Path:
    """跨进程锁和登记文件的位置。

    放在临时目录下，不在业务目录中产生文件。systemd ``PrivateTmp`` 对同一服务的
    全部工作进程共享同一临时目录，服务重启时清空，残留的锁和登记随之消失。
    """
    digest = hashlib.sha256(name.encode()).hexdigest()[:32]
    return Path(tempfile.gettempdir()) / "sunhold-oa-coordination" / digest


def _open_lock_file(path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    return os.open(path, os.O_RDWR | os.O_CREAT, 0o600)


def _lock_descriptor(descriptor: int, *, blocking: bool) -> None:
    if os.name != 'nt':
        fcntl.flock(descriptor, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        return
    while True:
        try:
            os.lseek(descriptor, 0, os.SEEK_SET)
            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
            return
        except OSError as error:
            if error.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                raise
            if not blocking:
                raise BlockingIOError(error.errno, str(error)) from error
            time.sleep(0.01)


def _unlock_descriptor(descriptor: int) -> None:
    if os.name == 'nt':
        os.lseek(descriptor, 0, os.SEEK_SET)
        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(descriptor, fcntl.LOCK_UN)


def windows_process_alive(pid: int) -> bool:
    """Windows 只查询进程状态；不能用会终止进程的 os.kill(pid, 0)。"""
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x00100000, False, pid)
    if not handle:
        error = ctypes.get_last_error()
        if error == 87:
            return False
        if error == 5:
            return True
        raise ctypes.WinError(error)
    try:
        status = kernel.WaitForSingleObject(handle, 0)
        if status == 258:
            return True
        if status == 0:
            return False
        raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.CloseHandle(handle)


@asynccontextmanager
async def file_lock(path: Path, *, poll_seconds: float = 0.01) -> AsyncIterator[None]:
    """跨进程独占文件锁；等待期间让出事件循环，不阻塞本进程其他请求。

    flock 以打开的文件描述为单位，同一进程对同一路径嵌套获取会互相阻塞，
    调用方必须先用进程内锁串行化，且不得在持有时再次获取同一路径。
    """
    descriptor = _open_lock_file(path)
    try:
        while True:
            try:
                _lock_descriptor(descriptor, blocking=False)
                break
            except BlockingIOError:
                await asyncio.sleep(poll_seconds)
        try:
            yield
        finally:
            _unlock_descriptor(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def file_lock_sync(path: Path) -> Iterator[None]:
    """同步代码使用的跨进程文件锁；仅用于持锁时间极短的纯文件读写。"""
    descriptor = _open_lock_file(path)
    try:
        _lock_descriptor(descriptor, blocking=True)
        try:
            yield
        finally:
            _unlock_descriptor(descriptor)
    finally:
        os.close(descriptor)


async def run_with_file_slot(path: Path, operation: Callable[[], Awaitable], *, poll_seconds: float = 0.2):
    """跨进程同一时刻只允许一个持有者执行 ``operation``。"""
    async with file_lock(path, poll_seconds=poll_seconds):
        return await operation()
