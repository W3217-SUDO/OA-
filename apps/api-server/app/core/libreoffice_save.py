"""WOPI PutFile：先登记不可变写入，再原子提交附件指针及审计。"""

import copy
from uuid import uuid4

from fastapi import HTTPException, Request

from app.core.libreoffice_files import DOCX_CONTENT_TYPE, read_put_body, revision_path, validate_docx, write_revision
from app.core.libreoffice_state import iso_utc, now_utc, persist_context, session_context
from app.models import WorkflowEvent


def save_response(session: dict) -> dict:
    return {"LastModifiedTime": session["modified_at"]}


def require_wopi_lock(context, value: str) -> None:
    current = context.session["wopi_lock"]
    if not value or not current or current != value:
        raise HTTPException(status_code=409, detail="WOPI 文件锁不匹配", headers={"X-WOPI-Lock": current})


async def record_failure(case_id: int, attachment_id: int, session_id: str, identity: dict, db, message: str) -> None:
    await db.rollback()
    context = await session_context(case_id, attachment_id, session_id, identity, db, lock=True)
    context.session["save_status"] = "error"
    context.session["error"] = message
    await persist_context(context, db)


async def put_file(context, request: Request, db) -> tuple[dict, str]:
    case_id, attachment_id, session_id = context.record.id, context.item.id, context.session["id"]
    identity = context.identity
    lock = request.headers.get("x-wopi-lock", "")
    require_wopi_lock(context, lock)
    # 先提交本次计数，再在接收正文后重读；网络传输期间不持有 SQL 锁。
    await persist_context(context, db)
    try:
        content = await read_put_body(request)
        version = validate_docx(content)
        context = await session_context(case_id, attachment_id, session_id, identity, db, lock=True)
        require_wopi_lock(context, lock)
        if version == context.session["version"]:
            context.session["save_status"] = "saved"
            context.session["error"] = None
            await persist_context(context, db)
            return save_response(context.session), version
        timestamp = request.headers.get("x-cool-wopi-timestamp", request.headers.get("x-lool-wopi-timestamp"))
        if timestamp and timestamp != context.session["modified_at"]:
            raise HTTPException(status_code=409, detail={"COOLStatusCode": 1010, "message": "文件版本已变化"},
                                headers={"X-WOPI-Lock": context.session["wopi_lock"]})
        pending = context.session["pending"]
        if pending and pending["version"] != version:
            raise HTTPException(status_code=409, detail="另一次保存尚未确认，拒绝覆盖其在途版本")
        if not pending:
            pending = {"id": uuid4().hex, "version": version, "base_version": context.session["version"],
                       "base_path": context.session["path"], "path": revision_path(context.item, context.session, version)}
        context.session.update(pending=pending, save_status="saving", error=None)
        await persist_context(context, db)
        # 对象 I/O 不持有 SQL 锁；pending 已持久化，DB 提交失败后仍可重试同一个对象键。
        await write_revision(pending["path"], content)
        context = await session_context(case_id, attachment_id, session_id, identity, db, lock=True)
        require_wopi_lock(context, lock)
        active = context.session["pending"]
        if not active and context.session["version"] == version and context.item.path == pending["path"]:
            return save_response(context.session), version
        if (not active or active["id"] != pending["id"] or context.session["version"] != pending["base_version"]
                or context.item.path != pending["base_path"]):
            raise HTTPException(status_code=409, detail="提交前附件或保存请求已变化，原指针未覆盖")
        modified = iso_utc(now_utc())
        documents = copy.deepcopy((context.record.data or {})["libreoffice_documents"])
        document = documents[str(attachment_id)]
        revision = {"version": version, "path": pending["path"], "size": len(content),
                    "previous_version": pending["base_version"], "previous_path": pending["base_path"],
                    "saved_at": modified, "operator": identity["username"], "session_id": session_id}
        document["versions"].append(revision)
        document.update(version=version, path=pending["path"], modified_at=modified)
        context.record.data = {**(context.record.data or {}), "libreoffice_documents": documents}
        context.item.path = pending["path"]
        context.item.stored_name = f"libreoffice-{attachment_id}-{session_id}-{version}.docx"
        context.item.size = len(content)
        context.item.content_type = DOCX_CONTENT_TYPE
        context.session.update(path=pending["path"], version=version, size=len(content), modified_at=modified,
                               last_saved_at=modified, pending=None, save_status="saved", error=None)
        db.add(WorkflowEvent(record_id=case_id, action="LibreOffice 保存案件 Word 文件",
                             from_status=context.record.status, to_status=context.record.status,
                             operator=identity["username"], comment=f"附件 {attachment_id}；版本 {version}"))
        await persist_context(context, db)
        return save_response(context.session), version
    except HTTPException as exc:
        # 独立提交错误状态，不能让请求事务回滚后 GET 丢失保存失败事实。
        message = str(exc.detail) if isinstance(exc.detail, str) else "保存请求与当前附件版本冲突"
        await record_failure(case_id, attachment_id, session_id, identity, db, message)
        raise
    except Exception as exc:
        await record_failure(case_id, attachment_id, session_id, identity, db, "保存未完成，原附件指针未提交，请重试")
        raise HTTPException(status_code=500, detail="Office 保存失败，不能视为保存成功") from exc
