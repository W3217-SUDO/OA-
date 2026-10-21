"""使用操作系统文件锁保护原生会话，进程退出后锁自动释放。"""

from contextlib import contextmanager
import asyncio
import errno
import os
from pathlib import Path
import stat
import time

from fastapi import HTTPException


@contextmanager
def session_lease(path: Path):
    if path.is_symlink():
        raise HTTPException(409, "会话锁路径无效")
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        opened, linked = os.fstat(descriptor), path.lstat()
        if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                or (opened.st_dev, opened.st_ino) != (linked.st_dev, linked.st_ino)):
            raise HTTPException(409, "会话锁路径已变化")
        handle = os.fdopen(descriptor, "r+b")
    except BaseException:
        os.close(descriptor)
        raise
    locked = False
    try:
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except OSError as exc:
            if exc.errno in {errno.EACCES, errno.EAGAIN}:
                raise HTTPException(409, "当前工作区会话正在执行，请等待本轮结束") from exc
            raise
        yield
    finally:
        try:
            if locked:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


async def wait_for_session_lease(path: Path, *, timeout: float = 10):
    """限时等待旧进程释放常驻句柄，不重试无效路径或其他文件错误。"""
    deadline = time.monotonic() + timeout
    while True:
        lease = session_lease(path)
        try:
            lease.__enter__()
        except HTTPException as exc:
            cause = exc.__cause__
            if not isinstance(cause, OSError) or cause.errno not in {errno.EACCES, errno.EAGAIN}:
                raise
            if time.monotonic() >= deadline:
                raise HTTPException(409, "工作区常驻会话尚未完成交接，请稍后重试") from exc
            await asyncio.sleep(0.05)
        else:
            return lease
