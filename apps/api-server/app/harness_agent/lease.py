"""使用操作系统文件锁保护原生会话，进程退出后锁自动释放。"""

from contextlib import contextmanager
import errno
import os
from pathlib import Path
import stat

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
