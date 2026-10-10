"""案件 Office 会话、原始版本和既有附件编辑锁。"""

import copy
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import jwt
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.constants import AI_SPACE_CATEGORY, WORD_EDITOR_LOCK_SECONDS
from app.core.documents import _acquire_case_word_editor_lock, _word_editor_now
from app.core.office_editor import (
    MAX_DOCUMENT_BYTES,
    document_ticket,
    download_document,
    office_settings,
    office_token,
    validate_document,
)
from app.core.oss_attachments import office_revision_key, oss_attachment_location, oss_attachment_signed_url
from app.core.permissions import _ensure_record_module, _require_case_action, _require_case_detail_write_access
from app.core.storage import _attachment_storage_path
from app.data_models.documents import FileAttachment
from app.data_models.identity import User
from app.data_models.records import BusinessRecord
from app.security import user_role_ids


async def office_identity(username: str, db: AsyncSession) -> dict:
    user = await db.scalar(select(User).where(User.username == username).execution_options(populate_existing=True))
    if not user or not user.is_active or user.must_change_password:
        raise HTTPException(status_code=403, detail="Office 编辑账号已失效或必须先修改密码")
    roles = user_role_ids(user)
    return {"username": user.username, "role": roles[0], "role_ids": roles,
            "display_name": user.display_name, "department": user.department}


async def authorized_office_attachment(case_id: int, attachment_id: int, username: str, db: AsyncSession):
    identity = await office_identity(username, db)
    record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_detail_write_access(record, identity, db)
    await _require_case_action(identity, db, "case.document.manage")
    item = await db.get(FileAttachment, attachment_id, populate_existing=True)
    if not item or item.record_id != record.id or item.category == AI_SPACE_CATEGORY:
        raise HTTPException(status_code=404, detail="案件正式 Word 附件不存在")
    if Path(item.original_name).suffix.lower() != ".docx":
        raise HTTPException(status_code=422, detail="本次在线编辑仅支持 DOCX 文件")
    return record, item, identity


def get_office_session(record: BusinessRecord, attachment_id: int, session_id: str) -> dict:
    session = (record.data or {}).get("office_editor_sessions", {}).get(str(attachment_id))
    if not isinstance(session, dict) or session.get("id") != session_id:
        raise HTTPException(status_code=404, detail="Office 编辑会话不存在或已被新会话替代")
    return copy.deepcopy(session)


def set_office_session(record: BusinessRecord, attachment_id: int, session: dict) -> None:
    data = copy.deepcopy(record.data or {})
    sessions = data.setdefault("office_editor_sessions", {})
    sessions[str(attachment_id)] = copy.deepcopy(session)
    record.data = data


def office_lock_expiry(item: FileAttachment) -> datetime | None:
    expiry = item.word_editor_lock_expires_at
    if expiry is not None and expiry.tzinfo is not None:
        return expiry.astimezone(timezone.utc).replace(tzinfo=None)
    return expiry


def office_session_status(session: dict) -> dict:
    status = session["status"]
    if status != "closed" and datetime.fromisoformat(session["expires_at"]) <= _word_editor_now():
        status = "expired"
    return {
        "session_id": session["id"], "status": status, "expires_at": session["expires_at"] + "Z",
        "saved_version": session.get("saved_version", ""), "saved_at": session.get("saved_at", ""),
        "save_sequence": session.get("save_sequence", 0),
        "close_ready": status == "closed" or (status == "closing" and not session.get("error")
                         and session.get("close_request", {}).get("phase") in {"no_changes", "saved"}),
        "error": session.get("error", "") or ("编辑会话已过期，请重新打开文件" if status == "expired" else ""),
    }


def finish_office_session(item: FileAttachment, session: dict) -> None:
    session["status"] = "closed"
    item.word_editor_lock_token = ""
    item.word_editor_lock_expires_at = None
    item.word_editor_locked_by = ""


def require_office_lease(item: FileAttachment, session: dict) -> None:
    if session["status"] in {"closed", "expired"} or office_session_status(session)["status"] == "expired":
        raise HTTPException(status_code=409, detail="Office 编辑会话已关闭或过期")
    expiry = office_lock_expiry(item)
    if (not item.word_editor_lock_token or expiry is None
            or expiry <= _word_editor_now()
            or item.word_editor_locked_by != session["user"]
            or not secrets.compare_digest(hashlib.sha256(item.word_editor_lock_token.encode()).hexdigest(), session["lease_hash"])):
        raise HTTPException(status_code=409, detail="Office 编辑锁已失效，请重新打开文件")
    if item.path != session["current_path"]:
        raise HTTPException(status_code=409, detail="附件版本已变化，不能继续当前 Office 会话")


async def source_document(path: str, original_name: str) -> bytes:
    source = SimpleNamespace(path=path, original_name=original_name, stored_name=Path(path).name)
    signed_url = oss_attachment_signed_url(source)
    if signed_url is not None:
        return await download_document(signed_url)
    local = _attachment_storage_path(source)
    if local is None:
        raise HTTPException(status_code=404, detail="Word 原始版本不存在")
    if local.stat().st_size > MAX_DOCUMENT_BYTES:
        raise HTTPException(status_code=413, detail="Word 文件超过 20MB")
    return local.read_bytes()


async def create_office_session(case_id: int, attachment_id: int, username: str, db: AsyncSession) -> dict:
    public, _internal, api_base = office_settings()
    record, item, identity = await authorized_office_attachment(case_id, attachment_id, username, db)
    session_id = uuid4().hex
    if oss_attachment_location(item) is not None:
        office_revision_key(item.id, session_id, "0" * 64)
    item = await _acquire_case_word_editor_lock(item, identity, db)
    acquired_token = item.word_editor_lock_token
    try:
        content = await source_document(item.path, item.original_name)
        version = validate_document(content)
        session = {
            "id": session_id, "user": username, "status": "editing", "key": session_id,
            "expires_at": office_lock_expiry(item).isoformat(),
            "source_path": item.path, "source_version": version,
            "current_path": item.path, "current_version": version,
            "lease_hash": hashlib.sha256(acquired_token.encode()).hexdigest(),
            "saved_version": "", "saved_at": "", "save_sequence": 0, "error": "",
        }
        await db.execute(update(BusinessRecord).where(BusinessRecord.id == case_id).values(updated_at=BusinessRecord.updated_at))
        record = await db.scalar(select(BusinessRecord).where(BusinessRecord.id == case_id).with_for_update().execution_options(populate_existing=True))
        record, item, _identity = await authorized_office_attachment(case_id, attachment_id, username, db)
        require_office_lease(item, session)
        set_office_session(record, attachment_id, session)
        await db.commit()
    except Exception:
        await db.rollback()
        await db.execute(update(FileAttachment).where(FileAttachment.id == attachment_id, FileAttachment.word_editor_lock_token == acquired_token).values(
            word_editor_lock_token="", word_editor_lock_expires_at=None, word_editor_locked_by=""))
        await db.commit()
        raise
    file_name = f"attachment-{attachment_id}.docx"
    config = {
        "documentType": "word", "type": "desktop",
        "document": {"fileType": "docx", "title": item.original_name, "key": session["key"],
                     "url": f"{api_base}/public/office-editor/document/{document_ticket(case_id, attachment_id, session)}/{file_name}",
                     "permissions": {"edit": True}},
        "editorConfig": {"mode": "edit", "lang": "zh-CN",
                         "user": {"id": username, "name": identity["display_name"]},
                         "callbackUrl": f"{api_base}/office-editor/callback/{case_id}/{attachment_id}/{session_id}",
                         "customization": {"forcesave": False}},
    }
    config["token"] = office_token({**config, "exp": datetime.fromisoformat(session["expires_at"]).replace(tzinfo=timezone.utc)})
    return {"attachment_id": attachment_id, "name": item.original_name, "document_server_url": public,
            "config": config, **office_session_status(session)}


async def locked_office_session(case_id: int, attachment_id: int, session_id: str, db: AsyncSession):
    # 条件更新同时获取 SQLite 写锁，随后回读案件 JSON，避免并发回调覆盖会话状态。
    item = await db.scalar(select(FileAttachment).where(FileAttachment.id == attachment_id).with_for_update().execution_options(populate_existing=True))
    if not item or item.record_id != case_id:
        raise HTTPException(status_code=404, detail="Office 附件不存在")
    await db.execute(update(FileAttachment).where(FileAttachment.id == item.id).values(word_editor_lock_token=item.word_editor_lock_token))
    record = await db.scalar(select(BusinessRecord).where(BusinessRecord.id == case_id).with_for_update().execution_options(populate_existing=True))
    if not record:
        raise HTTPException(status_code=404, detail="Office 案件不存在")
    return record, item, get_office_session(record, attachment_id, session_id)


async def change_office_session(case_id: int, attachment_id: int, session_id: str, username: str, db: AsyncSession, *, operation: str) -> dict:
    await authorized_office_attachment(case_id, attachment_id, username, db)
    record, item, session = await locked_office_session(case_id, attachment_id, session_id, db)
    if session["user"] != username:
        raise HTTPException(status_code=403, detail="不能操作其他用户的 Office 编辑会话")
    if operation == "read" and session["status"] != "closed":
        try:
            require_office_lease(item, session)
        except HTTPException as exc:
            session.update({"status": "expired", "error": str(exc.detail)})
            set_office_session(record, attachment_id, session)
            await db.commit()
    if operation != "read":
        require_office_lease(item, session)
        if operation == "renew":
            item.word_editor_lock_expires_at = _word_editor_now() + timedelta(seconds=WORD_EDITOR_LOCK_SECONDS)
            session["expires_at"] = item.word_editor_lock_expires_at.isoformat()
        set_office_session(record, attachment_id, session)
        await db.commit()
    return office_session_status(session)


async def open_office_document(token: str, file_name: str, db: AsyncSession) -> bytes:
    try:
        claims = jwt.decode(token, settings.secret_key, algorithms=["HS256"], options={"require": ["exp"]})
        if claims["purpose"] != "onlyoffice-document":
            raise ValueError("invalid purpose")
        case_id, attachment_id = int(claims["case_id"]), int(claims["attachment_id"])
        username, session_id, version = claims["user"], claims["session_id"], claims["version"]
    except (jwt.PyJWTError, KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Office 文档地址无效或已过期") from exc
    record, item, _identity = await authorized_office_attachment(case_id, attachment_id, username, db)
    session = get_office_session(record, attachment_id, session_id)
    require_office_lease(item, session)
    if session["user"] != username or session["source_version"] != version or file_name != f"attachment-{attachment_id}.docx":
        raise HTTPException(status_code=401, detail="Office 文档地址与会话或版本不一致")
    content = await source_document(session["source_path"], item.original_name)
    if not secrets.compare_digest(validate_document(content), version):
        raise HTTPException(status_code=409, detail="Word 原始版本内容已变化")
    return content
