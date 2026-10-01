"""附件物理文件删除与数据库提交之间的可恢复暂存协议。"""

from __future__ import annotations

import logging
import errno
import os
import re
import stat
import time
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.core.constants import UPLOAD_ROOT
from app.models import FileAttachment


logger = logging.getLogger(__name__)
_PENDING_NAME = re.compile(r"^\.pending-delete-(?P<id>[1-9][0-9]*)-(?P<token>[0-9a-f]{32})-(?P<name>.+)$")
_LOCK_NAME = re.compile(r"^\.pending-delete-lock-(?P<id>[1-9][0-9]*)-(?P<token>[0-9a-f]{32})-(?P<name>.+)$")


@dataclass
class StagedAttachmentDelete:
    original: Path
    staged: Path
    lock_path: Path
    lock_file: BinaryIO


def _inside_upload_root(path: Path, upload_root: Path | None = None) -> bool:
    return (upload_root or UPLOAD_ROOT).resolve() in path.resolve().parents


def _lock_file(path: Path) -> BinaryIO | None:
    if path.is_symlink():
        raise OSError(f"附件删除锁不能是符号链接：{path.name}")
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        link_info = path.lstat()
        file_info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(link_info.st_mode)
            or (link_info.st_dev, link_info.st_ino) != (file_info.st_dev, file_info.st_ino)
            or link_info.st_nlink != 1
        ):
            raise OSError(f"附件删除锁路径已变化或不是独立普通文件：{path.name}")
        handle = os.fdopen(descriptor, "r+b")
    except Exception:
        os.close(descriptor)
        raise
    locked = False
    try:
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in {errno.EACCES, errno.EAGAIN}:
                handle.close()
                return None
            raise
        locked = True
        if handle.seek(0, os.SEEK_END) == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
    except Exception:
        if locked:
            try:
                _unlock_file(handle)
            except OSError:
                logger.exception("附件删除锁初始化失败后无法释放文件锁：%s", path.name)
        else:
            handle.close()
        raise
    return handle


def _unlock_file(handle: BinaryIO) -> None:
    try:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


def _release(stage: StagedAttachmentDelete) -> None:
    _unlock_file(stage.lock_file)
    if not stage.staged.exists() and not stage.staged.is_symlink():
        stage.lock_path.unlink(missing_ok=True)


def stage_attachment_delete(attachment_id: int, path: Path, upload_root: Path | None = None) -> StagedAttachmentDelete | None:
    if path.is_symlink() or (path.exists() and not _inside_upload_root(path, upload_root)):
        raise OSError(f"附件路径不是上传目录内的普通文件：{path.name}")
    if not path.is_file():
        return None
    token = uuid4().hex
    staged = path.with_name(f".pending-delete-{attachment_id}-{token}-{path.name}")
    lock_path = path.with_name(f".pending-delete-lock-{attachment_id}-{token}-{path.name}")
    lock_file = _lock_file(lock_path)
    if lock_file is None:
        raise OSError(f"无法锁定附件删除暂存文件：{path.name}")
    operation = StagedAttachmentDelete(path, staged, lock_path, lock_file)
    try:
        path.replace(staged)
    except Exception:
        _release(operation)
        raise
    return operation


def restore_attachment_delete(stage: StagedAttachmentDelete) -> None:
    try:
        if stage.original.exists() or stage.original.is_symlink():
            raise FileExistsError(f"附件原文件已存在，不能覆盖：{stage.original.name}")
        if stage.staged.is_symlink() or not stage.staged.is_file():
            raise OSError(f"附件暂存文件已变化，不能恢复：{stage.staged.name}")
        stage.staged.replace(stage.original)
    finally:
        _release(stage)


def finish_attachment_delete(stage: StagedAttachmentDelete) -> None:
    try:
        if stage.staged.is_symlink() or not stage.staged.is_file():
            raise OSError(f"附件暂存文件已变化，不能清理：{stage.staged.name}")
        stage.staged.unlink()
    finally:
        _release(stage)


def defer_attachment_delete(stage: StagedAttachmentDelete) -> None:
    """数据库暂时无法判断文件引用时，释放锁并留待周期协调。"""
    _release(stage)


async def attachment_path_referenced(
    db: AsyncSession, path: Path, exclude_attachment_ids: tuple[int, ...] = (),
) -> bool:
    statement = select(FileAttachment.id).where(FileAttachment.path == str(path))
    if exclude_attachment_ids:
        statement = statement.where(FileAttachment.id.notin_(exclude_attachment_ids))
    return await db.scalar(statement.limit(1)) is not None


def _pending_files() -> list[Path]:
    if not UPLOAD_ROOT.is_dir():
        return []
    return sorted(UPLOAD_ROOT.rglob(".pending-delete-*"))


def _remove_orphan_lock(lock_path: Path) -> bool:
    match = _LOCK_NAME.fullmatch(lock_path.name)
    if match is None:
        raise ValueError(f"附件删除锁名称无效：{lock_path.name}")
    staged = lock_path.with_name(f".pending-delete-{match.group('id')}-{match.group('token')}-{match.group('name')}")
    if staged.exists() or staged.is_symlink():
        return False
    lock_file = _lock_file(lock_path)
    if lock_file is None:
        return False
    try:
        if staged.exists() or staged.is_symlink():
            return False
    finally:
        _unlock_file(lock_file)
    lock_path.unlink(missing_ok=True)
    return True


async def reconcile_pending_attachment_deletes(db: AsyncSession) -> None:
    """跨进程锁保证不碰正在提交的删除，定时重试崩溃和清理失败项。"""
    cutoff = time.time() - settings.attachment_delete_reconcile_min_age_seconds
    for staged in await run_in_threadpool(_pending_files):
        if staged.is_symlink() or not staged.is_file():
            continue
        orphan_lock = _LOCK_NAME.fullmatch(staged.name)
        match = orphan_lock or _PENDING_NAME.fullmatch(staged.name)
        if not match or not _inside_upload_root(staged):
            continue
        if staged.stat().st_mtime > cutoff:
            continue
        if orphan_lock is not None:
            try:
                if await run_in_threadpool(_remove_orphan_lock, staged):
                    logger.warning("已清理附件删除暂存的孤立锁：%s", staged.name)
            except Exception:
                logger.exception("附件暂存锁协调失败：%s", staged.name)
                raise
            continue
        lock_path = staged.with_name(f".pending-delete-lock-{match.group('id')}-{match.group('token')}-{match.group('name')}")
        lock_file = await run_in_threadpool(_lock_file, lock_path)
        if lock_file is None:
            continue
        original = staged.with_name(match.group("name"))
        operation = StagedAttachmentDelete(original, staged, lock_path, lock_file)
        try:
            if not staged.exists():
                await run_in_threadpool(_release, operation)
                continue
            if await attachment_path_referenced(db, original):
                await run_in_threadpool(restore_attachment_delete, operation)
                logger.warning("已恢复数据库仍引用的附件文件：%s", original.name)
            else:
                await run_in_threadpool(finish_attachment_delete, operation)
                logger.warning("已清理数据库不再引用的暂存附件：%s", staged.name)
        except Exception:
            if not lock_file.closed:
                await run_in_threadpool(_release, operation)
            logger.exception("附件暂存文件协调失败：%s", staged.name)
            raise
