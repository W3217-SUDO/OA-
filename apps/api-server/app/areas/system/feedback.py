"""系统问题反馈与截图附件。"""
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.constants import UPLOAD_ROOT
from app.core.dependencies import current_identity, get_db, settings
from app.models import BusinessRecord, FileAttachment, Notification, User, WorkflowEvent

router = APIRouter()

FEEDBACK_STATUSES = {"待处理", "处理中", "待补充", "待验证", "已处理", "已解决"}
HANDLER_ACTIONS = {
    "开始处理": ({"待处理"}, "处理中"),
    "请求补充": ({"待处理", "处理中", "待验证"}, "待补充"),
    "提交修复": ({"处理中"}, "待验证"),
    "标记已处理": ({"待处理", "处理中"}, "已处理"),
}
REPORTER_ACTIONS = {
    "确认解决": ({"待验证", "已处理"}, "已解决"),
    "重新打开": ({"待验证", "已处理", "已解决"}, "待处理"),
}


class FeedbackTransition(BaseModel):
    action: str
    comment: str = Field(default="", max_length=2000)


class FeedbackAssignment(BaseModel):
    username: str = Field(min_length=1, max_length=64)


def _is_admin(identity: dict) -> bool:
    return "admin" in identity.get("_actual_role_ids", [])


def _assignee(record: BusinessRecord) -> str:
    return str((record.data or {}).get("assignee") or "")


def _can_view(record: BusinessRecord, identity: dict) -> bool:
    return _is_admin(identity) or identity["username"] in {record.owner, _assignee(record)}


def _can_handle(record: BusinessRecord, identity: dict) -> bool:
    return _is_admin(identity) or _assignee(record) == identity["username"]


async def _get_feedback(db: AsyncSession, feedback_id: int, identity: dict, *, lock: bool = False) -> BusinessRecord:
    statement = select(BusinessRecord).where(
        BusinessRecord.id == feedback_id, BusinessRecord.module == "bug_feedback",
    )
    if lock:
        statement = statement.with_for_update()
    record = await db.scalar(statement)
    if not record or not _can_view(record, identity):
        raise HTTPException(404, "反馈不存在或无权查看")
    return record


def _available_actions(record: BusinessRecord, identity: dict) -> list[str]:
    actions = []
    if _can_handle(record, identity):
        actions.extend(action for action, (states, _) in HANDLER_ACTIONS.items() if record.status in states)
    if record.owner == identity["username"]:
        actions.extend(action for action, (states, _) in REPORTER_ACTIONS.items() if record.status in states)
    return actions


async def _notify_participants(
    db: AsyncSession, record: BusinessRecord, actor: str, action: str, event_id: int,
) -> None:
    recipients = {record.owner, _assignee(record)} - {"", actor}
    if not _assignee(record):
        admins = (await db.scalars(select(User).where(User.is_active.is_(True)))).all()
        recipients.update(user.username for user in admins if user.role == "admin" or "admin" in (user.role_ids or []))
        recipients.discard(actor)
    for recipient in recipients:
        db.add(Notification(
            source_key=f"feedback-{record.id}-{event_id}-{recipient}", source_type="feedback",
            source_id=record.id, sender=actor, recipient=recipient,
            notification_type="系统通知", title=f"问题反馈 {record.serial_no}：{action}",
            content=f"{record.title}｜当前状态：{record.status}", level="info",
        ))


def _serialize_feedback(record: BusinessRecord, owner_name: str = "", assignee_name: str = "", has_screenshot: bool = False) -> dict:
    return {
        "id": record.id, "serial_no": record.serial_no, "description": record.description,
        "status": record.status, "owner": record.owner, "owner_display_name": owner_name,
        "assignee": _assignee(record), "assignee_display_name": assignee_name,
        "page": (record.data or {}).get("page", ""), "has_screenshot": has_screenshot,
        "created_at": record.created_at, "updated_at": record.updated_at,
    }


async def _read_screenshot(screenshot: UploadFile | None) -> tuple[bytes, str]:
    if not screenshot:
        return b"", ""
    suffix = Path(screenshot.filename or "").suffix.lower()
    content = await screenshot.read(10 * 1024 * 1024 + 1)
    signatures = {
        ".png": content.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": content.startswith(b"\xff\xd8\xff"),
        ".jpeg": content.startswith(b"\xff\xd8\xff"),
        ".webp": content.startswith(b"RIFF") and content[8:12] == b"WEBP",
    }
    if not signatures.get(suffix):
        raise HTTPException(422, "截图仅支持 PNG、JPG 或 WebP 图片")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "截图不能超过 10MB")
    return content, suffix


def _save_screenshot(
    db: AsyncSession, record_id: int, screenshot: UploadFile, content: bytes, suffix: str,
    username: str, category: str, event_id: int | None = None,
) -> Path:
    stored_name = f"{uuid4().hex}{suffix}"
    stored_path = UPLOAD_ROOT / stored_name
    stored_path.write_bytes(content)
    db.add(FileAttachment(
        record_id=record_id, category=category,
        original_name=Path(screenshot.filename or stored_name).name,
        stored_name=stored_name, content_type=screenshot.content_type or "application/octet-stream",
        size=len(content), path=str(stored_path), uploader=username,
        remark=str(event_id) if event_id else "",
    ))
    return stored_path


@router.post(f"{settings.api_prefix}/feedback")
async def create_feedback(
    description: str = Form(...), page: str = Form(""), screenshot: UploadFile | None = File(None),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    description = description.strip()
    if not 5 <= len(description) <= 2000:
        raise HTTPException(422, "问题描述需填写 5 到 2000 字")
    if len(page) > 500:
        raise HTTPException(422, "页面地址过长")
    content, suffix = await _read_screenshot(screenshot)
    stored_path = None
    try:
        record = BusinessRecord(
            module="bug_feedback", serial_no=f"BUG{uuid4().hex[:20].upper()}",
            title=description[:100], customer="", status="待处理", owner=identity["username"],
            description=description, data={"page": page.strip()},
        )
        db.add(record)
        await db.flush()
        event = WorkflowEvent(
            record_id=record.id, action="提交反馈", from_status="", to_status="待处理",
            operator=identity["username"], comment="",
        )
        db.add(event)
        await db.flush()
        if screenshot:
            stored_path = _save_screenshot(
                db, record.id, screenshot, content, suffix, identity["username"], "问题反馈截图",
            )
        await _notify_participants(db, record, identity["username"], "新反馈", event.id)
        await db.commit()
        return {"id": record.id, "serial_no": record.serial_no}
    except Exception:
        await db.rollback()
        if stored_path:
            stored_path.unlink(missing_ok=True)
        raise


@router.get(f"{settings.api_prefix}/feedback")
async def list_feedback(
    keyword: str = Query("", max_length=200), page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100), status: str = Query(""),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    if status and status not in FEEDBACK_STATUSES:
        raise HTTPException(422, "反馈状态无效")
    conditions = [BusinessRecord.module == "bug_feedback"]
    if not _is_admin(identity):
        conditions.append(or_(
            BusinessRecord.owner == identity["username"],
            BusinessRecord.data["assignee"].as_string() == identity["username"],
        ))
    if status:
        conditions.append(BusinessRecord.status == status)
    owner_user = aliased(User)
    assignee_user = aliased(User)
    joins = (
        BusinessRecord.__table__
        .outerjoin(owner_user, owner_user.username == BusinessRecord.owner)
        .outerjoin(assignee_user, assignee_user.username == BusinessRecord.data["assignee"].as_string())
    )
    keyword = keyword.strip()
    if keyword:
        conditions.append(or_(
            BusinessRecord.serial_no.icontains(keyword, autoescape=True),
            BusinessRecord.description.icontains(keyword, autoescape=True),
            BusinessRecord.owner.icontains(keyword, autoescape=True),
            owner_user.display_name.icontains(keyword, autoescape=True),
            BusinessRecord.data["page"].as_string().icontains(keyword, autoescape=True),
        ))
    total = await db.scalar(select(func.count()).select_from(joins).where(*conditions))
    has_screenshot = select(FileAttachment.id).where(
        FileAttachment.record_id == BusinessRecord.id,
        FileAttachment.category == "问题反馈截图",
    ).exists()
    records = (await db.execute(select(BusinessRecord, owner_user.display_name, assignee_user.display_name, has_screenshot)
    .select_from(joins).where(*conditions).order_by(
        BusinessRecord.updated_at.desc(), BusinessRecord.id.desc(),
    ).offset((page - 1) * page_size).limit(page_size))).all()
    return {"total": total, "page": page, "page_size": page_size, "items": [
        _serialize_feedback(item, owner_name or "", assignee_name or "", bool(screenshot_exists))
        for item, owner_name, assignee_name, screenshot_exists in records
    ]}


@router.get(f"{settings.api_prefix}/feedback/{{feedback_id}}")
async def get_feedback(feedback_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    record = await _get_feedback(db, feedback_id, identity)
    users = (await db.scalars(select(User).where(User.username.in_({
        record.owner, _assignee(record), identity["username"],
    })))).all()
    names = {user.username: user.display_name for user in users}
    has_screenshot = bool(await db.scalar(select(FileAttachment.id).where(
        FileAttachment.record_id == record.id, FileAttachment.category == "问题反馈截图",
    ).limit(1)))
    events = (await db.scalars(select(WorkflowEvent).where(
        WorkflowEvent.record_id == record.id,
    ).order_by(WorkflowEvent.created_at, WorkflowEvent.id))).all()
    screenshots = (await db.scalars(select(FileAttachment).where(
        FileAttachment.record_id == record.id, FileAttachment.category == "问题反馈补充截图",
    ))).all()
    screenshot_event_ids = {attachment.remark for attachment in screenshots}
    missing_names = {event.operator for event in events} - names.keys()
    if missing_names:
        authors = (await db.scalars(select(User).where(User.username.in_(missing_names)))).all()
        names.update({user.username: user.display_name for user in authors})
    return {
        **_serialize_feedback(record, names.get(record.owner, ""), names.get(_assignee(record), ""), has_screenshot),
        "can_assign": _is_admin(identity), "available_actions": _available_actions(record, identity),
        "events": [{
            "id": event.id, "action": event.action, "from_status": event.from_status,
            "to_status": event.to_status, "operator": event.operator,
            "operator_display_name": names.get(event.operator, ""), "comment": event.comment,
            "created_at": event.created_at, "has_screenshot": str(event.id) in screenshot_event_ids,
        } for event in events],
    }


@router.post(f"{settings.api_prefix}/feedback/{{feedback_id}}/messages")
async def add_feedback_message(
    feedback_id: int, content: str = Form(...), screenshot: UploadFile | None = File(None),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    content = content.strip()
    if not 1 <= len(content) <= 2000:
        raise HTTPException(422, "回复内容需填写 1 到 2000 字")
    image_content, suffix = await _read_screenshot(screenshot)
    record = await _get_feedback(db, feedback_id, identity, lock=True)
    stored_path = None
    try:
        prior_status = record.status
        if record.owner == identity["username"] and prior_status == "待补充":
            record.status = "待处理"
        record.updated_at = func.now()
        event = WorkflowEvent(
            record_id=record.id, action="补充信息" if prior_status == "待补充" and record.owner == identity["username"] else "回复",
            from_status=prior_status, to_status=record.status, operator=identity["username"], comment=content,
        )
        db.add(event)
        await db.flush()
        if screenshot:
            stored_path = _save_screenshot(
                db, record.id, screenshot, image_content, suffix, identity["username"],
                "问题反馈补充截图", event.id,
            )
        await _notify_participants(db, record, identity["username"], event.action, event.id)
        await db.commit()
        return {"status": record.status}
    except Exception:
        await db.rollback()
        if stored_path:
            stored_path.unlink(missing_ok=True)
        raise


@router.post(f"{settings.api_prefix}/feedback/{{feedback_id}}/transitions")
async def transition_feedback(
    feedback_id: int, body: FeedbackTransition,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    record = await _get_feedback(db, feedback_id, identity, lock=True)
    action = body.action.strip()
    definition = HANDLER_ACTIONS.get(action) if _can_handle(record, identity) else None
    if definition is None and record.owner == identity["username"]:
        definition = REPORTER_ACTIONS.get(action)
    if definition is None:
        raise HTTPException(403, "无权执行此操作")
    allowed_statuses, next_status = definition
    if record.status not in allowed_statuses:
        raise HTTPException(409, "反馈状态已变化，请刷新后重试")
    comment = body.comment.strip()
    if action in {"请求补充", "提交修复", "重新打开"} and len(comment) < 5:
        raise HTTPException(422, "请填写至少 5 字的处理说明")
    previous_status = record.status
    record.status = next_status
    record.updated_at = func.now()
    event = WorkflowEvent(
        record_id=record.id, action=action, from_status=previous_status, to_status=next_status,
        operator=identity["username"], comment=comment,
    )
    db.add(event)
    await db.flush()
    await _notify_participants(db, record, identity["username"], action, event.id)
    await db.commit()
    return {"status": record.status}


@router.put(f"{settings.api_prefix}/feedback/{{feedback_id}}/assignee")
async def assign_feedback(
    feedback_id: int, body: FeedbackAssignment,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    if not _is_admin(identity):
        raise HTTPException(403, "仅管理员可以指派处理人")
    record = await _get_feedback(db, feedback_id, identity, lock=True)
    username = body.username.strip()
    user = await db.scalar(select(User).where(User.username == username, User.is_active.is_(True)))
    if not user:
        raise HTTPException(422, "处理人不存在或已停用")
    old_assignee = _assignee(record)
    if old_assignee == username:
        raise HTTPException(409, "该人员已是处理人")
    record.data = {**(record.data or {}), "assignee": username}
    record.updated_at = func.now()
    event = WorkflowEvent(
        record_id=record.id, action="指派处理人", from_status=record.status, to_status=record.status,
        operator=identity["username"], comment=f"{old_assignee or '未指派'} → {user.display_name}（{username}）",
    )
    db.add(event)
    await db.flush()
    await _notify_participants(db, record, identity["username"], "指派处理人", event.id)
    await db.commit()
    return {"assignee": username}


@router.get(f"{settings.api_prefix}/feedback/{{feedback_id}}/screenshot")
async def feedback_screenshot(feedback_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    await _get_feedback(db, feedback_id, identity)
    attachment = await db.scalar(select(FileAttachment).where(
        FileAttachment.record_id == feedback_id, FileAttachment.category == "问题反馈截图"))
    if not attachment or not Path(attachment.path).is_file():
        raise HTTPException(404, "截图不存在")
    return FileResponse(attachment.path, media_type=attachment.content_type, filename=attachment.original_name)


@router.get(f"{settings.api_prefix}/feedback/{{feedback_id}}/events/{{event_id}}/screenshot")
async def feedback_event_screenshot(
    feedback_id: int, event_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    await _get_feedback(db, feedback_id, identity)
    attachment = await db.scalar(select(FileAttachment).where(
        FileAttachment.record_id == feedback_id, FileAttachment.category == "问题反馈补充截图",
        FileAttachment.remark == str(event_id),
    ))
    if not attachment or not Path(attachment.path).is_file():
        raise HTTPException(404, "补充截图不存在")
    return FileResponse(attachment.path, media_type=attachment.content_type, filename=attachment.original_name)
