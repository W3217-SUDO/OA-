"""共享附件租约上的持久化会话与写入栅栏，不依赖进程内状态。"""

import copy
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm.attributes import set_committed_value

from app.config import settings
from app.core.documents import _word_editor_utc
from app.core.libreoffice_config import office_validation_case_allowed
from app.core.libreoffice_security import authorized_case
from app.models import BusinessRecord, FileAttachment


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass
class OfficeContext:
    record: BusinessRecord
    item: FileAttachment
    session: dict
    identity: dict


async def attachment_context(case_id: int, attachment_id: int, identity: dict, db, *, lock: bool = False):
    if lock:
        await db.scalar(select(BusinessRecord).where(BusinessRecord.id == case_id).with_for_update()
                        .execution_options(populate_existing=True))
    else:
        # 同一条语句读取案件 JSON 与附件租约，并刷新提交后仍留在 ORM 中的旧对象。
        snapshot = (await db.execute(select(BusinessRecord, FileAttachment).join(
            FileAttachment, FileAttachment.record_id == BusinessRecord.id,
        ).where(BusinessRecord.id == case_id, FileAttachment.id == attachment_id)
            .execution_options(populate_existing=True))).first()
    record, identity = await authorized_case(case_id, identity, db)
    if not office_validation_case_allowed(record):
        raise HTTPException(status_code=403, detail="该案件不在 LibreOffice 在线编辑验证范围内")
    if lock:
        query = select(FileAttachment).where(FileAttachment.id == attachment_id, FileAttachment.record_id == case_id)
        item = await db.scalar(query.with_for_update().execution_options(populate_existing=True))
    else:
        item = snapshot[1] if snapshot is not None else None
    if not item:
        raise HTTPException(status_code=404, detail="案件附件不存在")
    return record, item, identity


async def session_context(case_id: int, attachment_id: int, session_id: str, identity: dict, db,
                          *, terminal: bool = False, lock: bool = False) -> OfficeContext:
    record, item, identity = await attachment_context(case_id, attachment_id, identity, db, lock=lock)
    session = copy.deepcopy((record.data or {}).get("libreoffice_sessions", {}).get(session_id))
    if not session or session["user"] != identity["username"] or session["attachment_id"] != attachment_id:
        raise HTTPException(status_code=404, detail="LibreOffice 编辑会话不存在")
    context = OfficeContext(record, item, session, identity)
    if not terminal:
        require_lease(context)
    return context


def require_lease(context: OfficeContext) -> None:
    item, session = context.item, context.session
    expires = _word_editor_utc(item.word_editor_lock_expires_at)
    if session["status"] == "closed" or datetime.fromisoformat(session["expires_at"]) <= now_utc():
        raise HTTPException(status_code=409, detail="LibreOffice 编辑会话已关闭或过期")
    if (not expires or expires <= now_utc() or item.word_editor_locked_by != session["user"]
            or not secrets.compare_digest(item.word_editor_lock_token or "", session["lease_token"])):
        raise HTTPException(status_code=409, detail="LibreOffice 编辑租约已失效")
    if item.path != session["path"]:
        raise HTTPException(status_code=409, detail="附件版本已变化，拒绝旧会话写入")


def store_session(context: OfficeContext) -> None:
    data = dict(context.record.data or {})
    sessions = dict(data.get("libreoffice_sessions", {}))
    sessions[context.session["id"]] = context.session
    context.record.data = {**data, "libreoffice_sessions": sessions}


async def persist_context(context: OfficeContext, db, *, release: bool = False) -> None:
    """租约 CAS 同时序列化 SQLite 写入；WOPI 客户端锁值不会随栅栏轮换。"""
    session, item = context.session, context.item
    previous_token = session["lease_token"]
    next_token = "" if release else secrets.token_urlsafe(48)
    expires = None if release else min(now_utc() + timedelta(seconds=settings.office_editor_lease_seconds),
                                      datetime.fromisoformat(session["expires_at"]))
    result = await db.execute(update(FileAttachment).where(
        FileAttachment.id == item.id, FileAttachment.record_id == context.record.id,
        FileAttachment.word_editor_lock_token == previous_token,
        FileAttachment.word_editor_lock_expires_at > now_utc(),
    ).values(word_editor_lock_token=next_token, word_editor_lock_expires_at=expires,
             word_editor_locked_by="" if release else session["user"])
        .execution_options(synchronize_session=False))
    if result.rowcount != 1:
        await db.rollback()
        raise HTTPException(status_code=409, detail="编辑租约已变化，本次操作未提交")
    session["lease_token"] = next_token
    store_session(context)
    await db.commit()
    set_committed_value(item, "word_editor_lock_token", next_token)
    set_committed_value(item, "word_editor_lock_expires_at", expires)
    set_committed_value(item, "word_editor_locked_by", "" if release else session["user"])


def count_request(context: OfficeContext) -> None:
    bucket = int(now_utc().timestamp()) // 60
    counter = context.session.get("request_counter", {"bucket": bucket, "count": 0})
    count = counter["count"] if counter["bucket"] == bucket else 0
    if count >= settings.office_wopi_requests_per_minute:
        raise HTTPException(status_code=429, detail="WOPI 请求超过会话频率限制", headers={"Retry-After": "60"})
    context.session["request_counter"] = {"bucket": bucket, "count": count + 1}


def status_payload(context: OfficeContext) -> dict:
    session = context.session
    status = session["status"]
    if status != "closed":
        expires = _word_editor_utc(context.item.word_editor_lock_expires_at)
        if (datetime.fromisoformat(session["expires_at"]) <= now_utc() or not expires or expires <= now_utc()
                or context.item.word_editor_lock_token != session["lease_token"]):
            status = "expired"
    return {"session_id": session["id"], "status": status, "save_status": session["save_status"],
            "version": session["version"], "last_saved_at": session.get("last_saved_at"),
            "error": session.get("error"), "expires_at": session["expires_at"],
            "lease_expires_at": iso_utc(_word_editor_utc(context.item.word_editor_lock_expires_at))
            if context.item.word_editor_lock_expires_at else None}
