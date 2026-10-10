"""关闭前登记唯一保存请求，等待实际回写后才允许前端销毁编辑器。"""

from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.case_office_sessions import (
    authorized_office_attachment,
    finish_office_session,
    locked_office_session,
    office_session_status,
    require_office_lease,
    set_office_session,
)
from app.core.office_editor import office_command


async def persist_close_failure(case_id: int, attachment_id: int, session_id: str, request_id: str,
                                exc: Exception, db: AsyncSession, *, allow_saved: bool) -> dict | None:
    await db.rollback()
    record, _item, session = await locked_office_session(case_id, attachment_id, session_id, db)
    request = session.get("close_request", {})
    if request.get("id") != request_id:
        return None
    if session["status"] == "closed":
        return office_session_status(session) if allow_saved else None
    if allow_saved and request["phase"] == "saved" and not session.get("error"):
        # 匹配的签名回调已实际落库，不能用丢失的命令响应撤销真实保存结果。
        return office_session_status(session)
    if request["phase"] == "rejected":
        return None
    if request["phase"] != "saved":
        request["phase"] = "uncertain"
    session.update({"status": "failed", "error": str(exc.detail) if isinstance(exc, HTTPException)
                    else "Office 关闭保存事务失败，编辑锁保留"})
    set_office_session(record, attachment_id, session)
    await db.commit()
    return None


async def close_office_session(case_id: int, attachment_id: int, session_id: str, username: str, db: AsyncSession) -> dict:
    await authorized_office_attachment(case_id, attachment_id, username, db)
    record, item, session = await locked_office_session(case_id, attachment_id, session_id, db)
    if session["user"] != username:
        raise HTTPException(status_code=403, detail="不能关闭其他用户的 Office 编辑会话")
    if session["status"] == "closed":
        return office_session_status(session)
    require_office_lease(item, session)
    request = session.get("close_request")
    if request and request["phase"] != "rejected":
        return office_session_status(session)
    if session.get("document_closed"):
        raise HTTPException(status_code=409, detail="编辑器已先行断开，无法发起可靠的关闭保存，请保留当前会话核查")
    request_id = f"close:{session_id}:{uuid4().hex}"
    session.update({"status": "closing", "error": "", "close_request": {"id": request_id, "phase": "requested"}})
    set_office_session(record, attachment_id, session)
    # 先提交 nonce 并释放 SQL 锁，回调可能在命令 HTTP 响应之前到达。
    await db.commit()
    command_completed = False
    try:
        code = await office_command({"c": "forcesave", "key": session_id, "userdata": request_id})
        command_completed = True
        record, item, session = await locked_office_session(case_id, attachment_id, session_id, db)
        await authorized_office_attachment(case_id, attachment_id, username, db)
        request = session["close_request"]
        if request["id"] != request_id:
            raise HTTPException(status_code=409, detail="Office 关闭保存请求已变化")
        if session["status"] == "closed" or request["phase"] == "saved":
            return office_session_status(session)
        require_office_lease(item, session)
        request["command_error"] = code
        if code == 0:
            request["phase"] = "queued"
        elif code == 4:
            # 仅在按钮外部 force-save 和服务端自动组装均禁用的协调协议内使用此信号。
            request["phase"] = "no_changes"
            if session.get("document_closed") and not session.get("error"):
                finish_office_session(item, session)
        else:
            request["phase"] = "rejected" if code in {1, 2, 5, 6, 7} else "uncertain"
            session.update({"status": "failed", "error": f"ONLYOFFICE 关闭保存命令失败（错误码 {code}），编辑锁保留"})
        set_office_session(record, attachment_id, session)
        await db.commit()
        if code not in {0, 4}:
            raise HTTPException(status_code=502, detail=session["error"])
        return office_session_status(session)
    except Exception as exc:
        confirmed = await persist_close_failure(case_id, attachment_id, session_id, request_id, exc, db,
                                                allow_saved=not command_completed)
        if confirmed is not None:
            return confirmed
        raise
