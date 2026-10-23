"""附件以 OSS 为准：新附件先写本机，由后台主进程上传到 OSS“附件/分类/年-月/”并把附件路径切到 OSS。

本机原文件保留作缓存（_attachment_storage_path 会优先读缓存）。正在在线编辑（持有编辑租约）的附件暂不切换；
已登记在线编辑版本的附件，同一事务里把版本记录里的路径一起改成 OSS 路径，避免重新打开时校验失败。
"""

import asyncio
import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select, update
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.core.constants import logger
from app.core.court_intake_storage import _segment
from app.models import BusinessRecord, FileAttachment

BATCH = 50
_failed: dict[int, str] = {}  # 本进程内上传失败或本机文件缺失的附件，不反复重试


def enabled() -> bool:
    return bool(settings.ai_oss_bucket.strip() and settings.ai_oss_credentials_file.strip() and settings.attachment_oss_prefix.strip())


def object_key(item: FileAttachment) -> str:
    month = (item.created_at or datetime.now(timezone.utc)).strftime("%Y-%m")
    return "/".join([settings.attachment_oss_prefix.strip().strip("/"), _segment(item.category or "未分类"), month,
                     f"{item.id}_{_segment(item.original_name or item.stored_name)}"])


async def sync_one(item: FileAttachment, db) -> str | None:
    """上传并切换一个附件；成功返回新路径，跳过返回 None。"""
    from app.core.oss_attachments import oss_put_object
    from app.core.storage import _attachment_storage_path
    old_path = item.path
    local = _attachment_storage_path(item)
    if local is None:
        _failed[item.id] = "本机文件不存在"
        return None
    content = await run_in_threadpool(local.read_bytes)
    bucket = settings.ai_oss_bucket.strip()
    key = object_key(item)
    created = await oss_put_object(bucket, key, content, item.content_type or "application/octet-stream",
                                   credentials_file=settings.ai_oss_credentials_file, endpoint=settings.ai_oss_endpoint,
                                   metadata={"attachment-id": item.id, "record-id": item.record_id or "", "category": item.category,
                                             "original-name": item.original_name, "uploader": item.uploader,
                                             "sha256": hashlib.sha256(content).hexdigest(), "synced-at": datetime.now().isoformat(timespec="seconds")},
                                   tags={"source": "oa-attachment"})
    if not created:
        _failed[item.id] = f"OSS 已有同名对象 {key}"
        return None
    new_path = f"oss://{bucket}/{key}"
    result = await db.execute(update(FileAttachment).where(FileAttachment.id == item.id, FileAttachment.path == old_path)
                              .values(path=new_path).execution_options(synchronize_session=False))
    if result.rowcount != 1:
        await db.rollback()
        return None
    if item.record_id:
        record = await db.get(BusinessRecord, item.record_id, with_for_update=True)
        documents = dict((record.data or {}).get("libreoffice_documents") or {}) if record else {}
        entry = documents.get(str(item.id))
        if entry and entry.get("path") == old_path:
            documents[str(item.id)] = {**entry, "path": new_path}
            record.data = {**(record.data or {}), "libreoffice_documents": documents}
    await db.commit()
    return new_path


async def sync_once(db, *, limit: int = BATCH) -> int:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=settings.attachment_oss_sync_delay_seconds)
    items = (await db.scalars(select(FileAttachment).where(
        ~FileAttachment.path.like("oss://%"), FileAttachment.created_at <= cutoff,
        FileAttachment.id.notin_(list(_failed) or [0]),
        or_(FileAttachment.word_editor_lock_token == "", FileAttachment.word_editor_lock_expires_at.is_(None),
            FileAttachment.word_editor_lock_expires_at <= now),
    ).order_by(FileAttachment.id).limit(limit))).all()
    moved = 0
    for item in items:
        try:
            if await sync_one(item, db):
                moved += 1
        except Exception as exc:
            await db.rollback()
            _failed[item.id] = str(exc)[:200]
            logger.warning("附件同步 OSS 失败 attachment_id=%s：%s", item.id, exc)
    return moved


async def attachment_oss_sync_loop() -> None:
    from app.database import SessionLocal
    while True:
        if enabled():
            try:
                async with SessionLocal() as db:
                    moved = await sync_once(db)
                if moved:
                    logger.info("附件已同步到 OSS：%s 个", moved)
                    continue
            except Exception:
                logger.exception("附件 OSS 同步循环失败")
        await asyncio.sleep(30)
