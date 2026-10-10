"""ONLYOFFICE 保存回调：不可变对象、版本审计和失败状态持久化。"""

import copy
import json
import os
import secrets

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_schemas.case_office import OfficeCallbackInput
from app.core.case_office_sessions import (
    authorized_office_attachment,
    finish_office_session,
    locked_office_session,
    office_session_status,
    require_office_lease,
    set_office_session,
    source_document,
)
from app.core.constants import UPLOAD_ROOT
from app.core.documents import _word_editor_now
from app.core.office_editor import DOCX_CONTENT_TYPE, check_editor_download_url, download_document, validate_document
from app.core.oss_attachments import office_revision_key, oss_attachment_location, put_office_revision
from app.data_models.records import WorkflowEvent


async def store_office_revision(item, session: dict, version: str, content: bytes) -> str:
    location = oss_attachment_location(item)
    if location is not None:
        bucket, _original_key = location
        key = office_revision_key(item.id, session["id"], version)
        path = f"oss://{bucket}/{key}"
        await put_office_revision(bucket, key, content, DOCX_CONTENT_TYPE)
        persisted = await source_document(path, item.original_name)
        if not secrets.compare_digest(validate_document(persisted), version):
            raise HTTPException(status_code=502, detail="OSS 新版本回读校验失败，附件指针未修改")
        return path
    target = UPLOAD_ROOT / f"office-{item.id}-{session['id']}-{version}.docx"
    created = False
    try:
        with target.open("xb") as output:
            created = True
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
    except FileExistsError:
        if not secrets.compare_digest(validate_document(target.read_bytes()), version):
            raise HTTPException(status_code=409, detail="本地 Office 不可变版本冲突")
    except OSError as exc:
        if created:
            target.unlink()
        raise HTTPException(status_code=500, detail="本地 Office 新版本写入失败，原附件未修改") from exc
    return str(target)


def pending_revision_path(item, session: dict, version: str) -> str:
    location = oss_attachment_location(item)
    if location is not None:
        return f"oss://{location[0]}/{office_revision_key(item.id, session['id'], version)}"
    return str(UPLOAD_ROOT / f"office-{item.id}-{session['id']}-{version}.docx")


def confirm_saved_callback(item, session: dict, body: OfficeCallbackInput, version: str) -> None:
    request = session.get("close_request")
    if body.status == 6 and request:
        request.update({"phase": "saved", "version": version})
    if request and session["status"] != "closed":
        session["status"] = "closing"
    if body.status == 2 or (session.get("document_closed") and office_session_status(session)["close_ready"]):
        finish_office_session(item, session)
    elif not request and session["status"] != "closed":
        session["status"] = "saved"


async def handle_office_callback(case_id: int, attachment_id: int, session_id: str, body: OfficeCallbackInput, db: AsyncSession) -> dict:
    record, item, session = await locked_office_session(case_id, attachment_id, session_id, db)
    if not secrets.compare_digest(body.key, session["key"]):
        raise HTTPException(status_code=401, detail="Office 回调文档 key 与会话不一致")
    try:
        await authorized_office_attachment(case_id, attachment_id, session["user"], db)
        if office_session_status(session)["status"] == "expired":
            raise HTTPException(status_code=409, detail="Office 保存会话已过期，原附件未修改")
        if body.status in {3, 7}:
            raise HTTPException(status_code=502, detail="ONLYOFFICE 报告文档保存失败，原附件未修改")
        if body.status in {1, 4}:
            if session["status"] == "closed":
                if body.status == 4:
                    return {"error": 0}
                raise HTTPException(status_code=409, detail="Office 会话已关闭")
            require_office_lease(item, session)
            if body.status == 4:
                # 无变更关闭通知可能先于在途 force-save，不能提前清锁或拒绝后到的内容。
                save_failed = session["status"] == "failed" or bool(session.get("error"))
                unchanged_close = not session.get("close_request") and not save_failed
                session["document_closed"] = True
                session["status"] = "failed" if save_failed else "closing"
                if unchanged_close or office_session_status(session)["close_ready"]:
                    finish_office_session(item, session)
            set_office_session(record, attachment_id, session)
            await db.commit()
            return {"error": 0}
        if not body.url or body.filetype != "docx":
            raise HTTPException(status_code=422, detail="Office 保存回调缺少有效 DOCX 输出，原附件未修改")
        check_editor_download_url(body.url)
        if body.users and session["user"] not in body.users:
            raise HTTPException(status_code=403, detail="Office 保存操作人与编辑会话不一致")
        request = session.get("close_request")
        if body.status == 6 and request and (body.forcesavetype != 0 or body.userdata != request["id"]):
            raise HTTPException(status_code=409, detail="Office 关闭保存回调未匹配登记请求，编辑锁保留")
        if session["status"] != "closed":
            require_office_lease(item, session)
        content = await download_document(body.url)
        version = validate_document(content)
        # force-save 与最终保存的相同内容只确认既有版本，不产生第二个对象或审计事件。
        if session.get("saved_version") == version and item.path == session["current_path"]:
            persisted = await source_document(item.path, item.original_name)
            if not secrets.compare_digest(validate_document(persisted), version):
                raise HTTPException(status_code=409, detail="已保存版本实际内容与会话不一致")
            session["error"] = ""
            confirm_saved_callback(item, session, body, version)
            set_office_session(record, attachment_id, session)
            await db.commit()
            return {"error": 0}
        if session["status"] == "closed":
            raise HTTPException(status_code=409, detail="已关闭的 Office 会话不能写入不同版本")
        current = await source_document(item.path, item.original_name)
        if not secrets.compare_digest(validate_document(current), session["current_version"]):
            raise HTTPException(status_code=409, detail="附件当前内容已变化，不能覆盖新的业务版本")
        old_path, old_version = item.path, session["current_version"]
        session["pending_version"] = version
        session["pending_path"] = pending_revision_path(item, session, version)
        new_path = await store_office_revision(item, session, version, content)
        item.path = new_path
        item.stored_name = f"office-{attachment_id}-{session_id}-{version}.docx"
        item.size = len(content)
        item.content_type = DOCX_CONTENT_TYPE
        session.update({"current_path": new_path, "current_version": version,
                        "saved_version": version, "saved_at": _word_editor_now().isoformat() + "Z",
                        "save_sequence": session["save_sequence"] + 1, "status": "saved", "error": ""})
        confirm_saved_callback(item, session, body, version)
        set_office_session(record, attachment_id, session)
        data = copy.deepcopy(record.data)
        versions = data.setdefault("office_document_versions", {})
        previous = versions.get(str(attachment_id), {})
        versions[str(attachment_id)] = {"original_storage": previous.get("original_storage", session["source_path"]),
                                        "current_storage": new_path, "version": version}
        record.data = data
        db.add(WorkflowEvent(record_id=record.id, action="在线编辑案件 Office 文件", from_status=record.status,
                             to_status=record.status, operator=session["user"], comment=json.dumps({
                                 "attachment_id": item.id, "name": item.original_name, "session_id": session_id,
                                 "original_storage": versions[str(attachment_id)]["original_storage"],
                                 "previous_storage": old_path, "storage": new_path,
                                 "previous_version": old_version, "version": version,
                             }, ensure_ascii=False)))
        await db.commit()
        return {"error": 0}
    except Exception as exc:
        # 必须先回滚失败写入，再用独立事务保存错误；不能让前端失去真实失败状态。
        pending = {key: session[key] for key in ("pending_version", "pending_path") if key in session}
        await db.rollback()
        failed_record, _item, failed = await locked_office_session(case_id, attachment_id, session_id, db)
        failed.update(pending)
        failed["status"] = "failed"
        failed["error"] = str(exc.detail) if isinstance(exc, HTTPException) else "Office 保存事务失败，附件指针未更新"
        set_office_session(failed_record, attachment_id, failed)
        await db.commit()
        raise
