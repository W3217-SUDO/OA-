"""OA 用户入口：创建、查看与协调关闭 CODE 编辑会话。"""

import copy
import secrets
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import or_, update

from app.config import settings
from app.core.constants import AI_SPACE_CATEGORY
from app.core.libreoffice_config import discovery, editor_configuration, editor_url, office_attachment_editable, origin
from app.core.libreoffice_files import read_document, validate_docx
from app.core.libreoffice_security import session_token
from app.core.libreoffice_state import (
    OfficeContext,
    attachment_context,
    iso_utc,
    now_utc,
    persist_context,
    session_context,
    status_payload,
    store_session,
)
from app.core.permissions import _ensure_case_word_editor_not_locked
from app.models import FileAttachment


async def create_session(case_id: int, attachment_id: int, identity: dict, db) -> dict:
    config = editor_configuration()
    record, item, identity = await attachment_context(case_id, attachment_id, identity, db)
    if item.category == AI_SPACE_CATEGORY or item.is_locked or not office_attachment_editable(item, record):
        raise HTTPException(status_code=409, detail="该附件当前不具备 LibreOffice DOCX 编辑能力")
    _ensure_case_word_editor_not_locked(item)
    snapshot = {name: getattr(item, name) for name in ("path", "stored_name", "original_name", "size", "content_type")}
    await db.rollback()
    # discovery 和附件传输在数据库事务之外进行，避免网络等待持有记录锁。
    info = await discovery()
    content = await read_document(SimpleNamespace(**snapshot))
    version = validate_docx(content)
    record, item, identity = await attachment_context(case_id, attachment_id, identity, db, lock=True)
    if item.path != snapshot["path"] or item.stored_name != snapshot["stored_name"] or item.is_locked:
        raise HTTPException(status_code=409, detail="读取期间附件发生变化，请重新打开")
    now = now_utc().replace(microsecond=0)
    session_id, lease_token = uuid4().hex, secrets.token_urlsafe(48)
    expires = now + timedelta(seconds=settings.office_editor_token_seconds)
    result = await db.execute(update(FileAttachment).where(
        FileAttachment.id == attachment_id, FileAttachment.record_id == case_id,
        FileAttachment.path == snapshot["path"],
        or_(FileAttachment.word_editor_lock_token == "", FileAttachment.word_editor_lock_expires_at.is_(None),
            FileAttachment.word_editor_lock_expires_at <= now),
    ).values(word_editor_lock_token=lease_token, word_editor_locked_by=identity["username"],
             word_editor_lock_expires_at=min(expires, now + timedelta(seconds=settings.office_editor_lease_seconds)))
        .execution_options(synchronize_session=False))
    if result.rowcount != 1:
        await db.rollback()
        raise HTTPException(status_code=409, detail="附件已由其他编辑会话占用")
    documents = copy.deepcopy((record.data or {}).get("libreoffice_documents", {}))
    document = documents.get(str(attachment_id))
    if document and (document["path"] != item.path or document["version"] != version):
        raise HTTPException(status_code=409, detail="附件与已登记的版本记录不一致，不能静默重建版本")
    modified = document["modified_at"] if document else iso_utc(now)
    if not document:
        documents[str(attachment_id)] = {"path": item.path, "version": version, "modified_at": modified,
            "original_storage": {**snapshot, "version": version}, "versions": []}
        record.data = {**(record.data or {}), "libreoffice_documents": documents}
    session = {"id": session_id, "case_id": case_id, "attachment_id": attachment_id,
               "user": identity["username"], "token_id": uuid4().hex, "lease_token": lease_token,
               "expires_at": expires.isoformat(), "status": "opening", "save_status": "idle",
               "path": item.path, "version": version, "size": len(content), "modified_at": modified,
               "wopi_lock": "", "engine_started": False, "close_requested": False,
               "pending": None, "error": None, "original_storage": {**snapshot, "version": version}}
    store_session(OfficeContext(record, item, session, identity))
    await db.commit()
    return {"session_id": session_id, "editor_url": editor_url(info, session_id),
            "access_token": session_token(session), "access_token_ttl": int(expires.timestamp() * 1000),
            "expires_at": expires.isoformat(), "filename": snapshot["original_name"],
            "editor_origin": origin(config["browser"]), "postmessage_origin": config["frontend"]}


async def get_session(case_id: int, attachment_id: int, session_id: str, identity: dict, db) -> dict:
    context = await session_context(case_id, attachment_id, session_id, identity, db, terminal=True)
    return status_payload(context)


async def close_session(case_id: int, attachment_id: int, session_id: str, identity: dict, db) -> dict:
    context = await session_context(case_id, attachment_id, session_id, identity, db, terminal=True, lock=True)
    status = status_payload(context)
    if status["status"] in {"closed", "expired"}:
        return status
    if context.session["save_status"] == "error":
        raise HTTPException(status_code=409, detail={"message": "保存失败，必须保留编辑器并重试保存", **status})
    context.session["close_requested"] = True
    # 无实际 WOPI 锁且无在途保存时撤销租约；已持锁的会话仍等待真实 UNLOCK。
    can_cancel_unlocked = not context.session["wopi_lock"] and not context.session["pending"]
    context.session["status"] = "closed" if can_cancel_unlocked else "closing"
    await persist_context(context, db, release=can_cancel_unlocked)
    await db.refresh(context.item)
    return status_payload(context)
