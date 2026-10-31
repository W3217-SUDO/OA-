"""系统问题反馈与截图附件。"""
import re
from datetime import date, datetime, time, timedelta
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.constants import UPLOAD_ROOT
from app.core.feedback_serial_migration import FEEDBACK_SERIAL_PREFIX
from app.core.dependencies import current_identity, get_db, settings
from app.models import BusinessRecord, FileAttachment, Notification, User, WorkflowEvent

router = APIRouter()

FEEDBACK_TZ = ZoneInfo("Asia/Shanghai")
# 状态（用户要求，2026-10-24；2026-10-28 加“待确认”）：处理人先写打算怎么改，交提交人确认（待确认）；
# 确认后回到待处理开始改，改完发给提交人验证，验证通过即已解决，没解决就重新打开。
# 2026-10-28 加“已撤回”（陶威）：提交人在动手修改之前可以撤回（“没有动手改之前可以撤回，改了就不能撤回”），
# 撤回后不再处理，页面只读，暂不支持重新打开。
FEEDBACK_STATUSES = ("待处理", "待确认", "待验证", "已解决", "已撤回")
WITHDRAW_ACTION = "撤回"
WITHDRAWN_STATUS = "已撤回"
# 待确认随时可撤；待处理只在还没动手时可撤；待验证、已解决都已改过，不能撤。
WITHDRAWABLE_STATUSES = frozenset({"待处理", "待确认"})
# 出现过这些就算已经动手改了：提交人确认修改，或处理人直接报了处理完成（含旧流程的“已处理”）。
WORK_STARTED_ACTIONS = frozenset({"确认修改", "处理完成，请验证"})
WORK_STARTED_STATUSES = frozenset({"待验证", "已处理"})
# 旧状态读出时按新流程归类，不改库里的历史数据：处理中/待补充仍算待处理，已处理等提交人验证。
LEGACY_STATUS = {"处理中": "待处理", "待补充": "待处理", "已处理": "待验证"}
HANDLER_ACTIONS = {
    # 处理说明里写打算怎么改，交给提交人确认。待验证时提交人又提了新要求，也要先把方案发给他确认（陶威 10-31 定）。
    "请确认修改方案": ({"待处理", "待验证"}, "待确认"),
    "处理完成，请验证": ({"待处理"}, "待验证"),
}
REPORTER_ACTIONS = {
    # 修改前要提交人点“确认修改”（用户要求，2026-10-27）：确认后回到待处理开始改；
    # 有意见直接回复继续沟通，状态留在待确认。
    "确认修改": ({"待确认"}, "待处理"),
    "验证通过": ({"待验证"}, "已解决"),
    "未解决，重新打开": ({"待验证", "已解决"}, "待处理"),
}
# 被指派的处理人也能替提交人确认（如非诉问题由指定的人确认）。
ASSIGNEE_CONFIRM_ACTIONS = {"确认修改"}
COMMENT_REQUIRED_ACTIONS = {"未解决，重新打开", "请确认修改方案"}


def _status(value: str | None) -> str:
    return LEGACY_STATUS.get(value or "", value or "")


def _stored_statuses(status: str) -> set[str]:
    """筛选某个新状态时，连同归到它名下的旧状态一起查。"""
    return {status, *(old for old, new in LEGACY_STATUS.items() if new == status)}


# 自动化处理（问题巡检会话）写入的回复和状态操作用这个身份，页面显示为“问题处理助手”，
# 和管理者本人在网页上的回复区分开（用户要求，2026-10-27）。不是登录账号，权限按管理员。
FEEDBACK_BOT_USERNAME = "feedback-bot"
FEEDBACK_BOT_DISPLAY_NAME = "问题处理助手"
FEEDBACK_BOT_IDENTITY = {"username": FEEDBACK_BOT_USERNAME, "display_name": FEEDBACK_BOT_DISPLAY_NAME,
                         "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"]}

FEEDBACK_ATTACHMENT_CATEGORIES = ("问题反馈截图", "问题反馈附件")
# 回复里带的截图和附件，remark 记回复事件 ID。
FEEDBACK_REPLY_CATEGORIES = ("问题反馈补充截图", "问题反馈补充附件")
REPLY_CATEGORY = {"问题反馈截图": "问题反馈补充截图", "问题反馈附件": "问题反馈补充附件"}


class FeedbackSubmit(BaseModel):
    description: str = ""
    page: str = Field(default="", max_length=500)
    route: str = Field(default="", max_length=300)
    controls: list[str] = Field(default_factory=list, max_length=60)


class FeedbackReply(BaseModel):
    content: str = ""
    file_count: int = Field(default=0, ge=0, le=10)


class FeedbackTransition(BaseModel):
    action: str
    comment: str = Field(default="", max_length=2000)


class FeedbackAssignment(BaseModel):
    username: str = Field(min_length=1, max_length=64)


def _created_between(date_from: date | None, date_to: date | None) -> list:
    """按提交日期筛选，日期按北京时间整天算（含结束当天）。"""
    conditions = []
    if date_from:
        conditions.append(BusinessRecord.created_at >= datetime.combine(date_from, time.min, FEEDBACK_TZ))
    if date_to:
        conditions.append(BusinessRecord.created_at < datetime.combine(date_to + timedelta(days=1), time.min, FEEDBACK_TZ))
    return conditions


def _is_admin(identity: dict) -> bool:
    return "admin" in identity.get("_actual_role_ids", [])


def _assignee(record: BusinessRecord) -> str:
    return str((record.data or {}).get("assignee") or "")


def _can_view(record: BusinessRecord, identity: dict) -> bool:
    return _is_admin(identity) or identity["username"] in {record.owner, _assignee(record)}


def _can_handle(record: BusinessRecord, identity: dict) -> bool:
    return _is_admin(identity) or _assignee(record) == identity["username"]


def _operator_role(record: BusinessRecord, operator: str) -> str:
    """处理记录里说话的是谁：提交人（聊天框右侧）、问题处理助手、被指派的处理人、其他（管理者）。"""
    if operator == record.owner:
        return "reporter"
    if operator == FEEDBACK_BOT_USERNAME:
        return "bot"
    if operator == _assignee(record):
        return "assignee"
    return "admin"


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


def _reporter_actions(record: BusinessRecord, identity: dict) -> set[str]:
    if record.owner == identity["username"]:
        return set(REPORTER_ACTIONS)
    if _assignee(record) == identity["username"]:
        return set(ASSIGNEE_CONFIRM_ACTIONS)
    # 提交人或确认人在回复里写了“确认”但没点按钮时，问题处理助手代记“确认修改”（备注写明依据），
    # 不再借用管理者身份，页面上分得清是谁（用户要求，2026-10-29）。
    if identity["username"] == FEEDBACK_BOT_USERNAME:
        return set(ASSIGNEE_CONFIRM_ACTIONS)
    return set()


def _work_started(events) -> bool:
    return any(event.action in WORK_STARTED_ACTIONS or event.to_status in WORK_STARTED_STATUSES for event in events)


def _withdrawable(record: BusinessRecord, events) -> bool:
    status = _status(record.status)
    return status == "待确认" or (status == "待处理" and not _work_started(events))


def _can_withdraw(record: BusinessRecord, identity: dict, events) -> bool:
    """只有提交人本人能撤回自己的问题（管理员也不能替别人撤回），且还没动手修改。"""
    return record.owner == identity["username"] and _withdrawable(record, events)


def _require_open(record: BusinessRecord) -> None:
    """已撤回的问题只读：不能再回复、上传、指派或改状态。"""
    if _status(record.status) == WITHDRAWN_STATUS:
        raise HTTPException(409, "提交人已撤回这个问题，不再处理")


def _action_definition(record: BusinessRecord, identity: dict, action: str) -> tuple[set[str], str] | None:
    if action == WITHDRAW_ACTION:
        return (set(WITHDRAWABLE_STATUSES), WITHDRAWN_STATUS) if record.owner == identity["username"] else None
    if _can_handle(record, identity) and action in HANDLER_ACTIONS:
        return HANDLER_ACTIONS[action]
    if action in _reporter_actions(record, identity):
        return REPORTER_ACTIONS[action]
    return None


def _available_actions(record: BusinessRecord, identity: dict) -> list[str]:
    return [action for action in (*HANDLER_ACTIONS, *REPORTER_ACTIONS)
            if (definition := _action_definition(record, identity, action)) and _status(record.status) in definition[0]]


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
            content=f"{record.title}｜当前状态：{_status(record.status)}", level="info",
        ))


async def _next_feedback_serial(db: AsyncSession, *, now: datetime | None = None) -> str:
    """问题编号：BUG + 提交当天日期（北京时间）+ 当天三位流水，如 BUG20261026001（用户要求，2026-10-26）。
    已删除的问题也占着号，删除后新问题不会重用同一个编号。"""
    get_bind = getattr(db, "get_bind", None)
    if get_bind is not None and get_bind().dialect.name == "postgresql":
        # 事务级锁持有到提交，多个工作进程同时提交反馈也不会拿到同一个流水号。
        from app.core.process_coordination import advisory_lock_id
        await db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": advisory_lock_id("feedback-serial")})
    prefix = f"{FEEDBACK_SERIAL_PREFIX}{(now or datetime.now(FEEDBACK_TZ)).astimezone(FEEDBACK_TZ):%Y%m%d}"
    existing = (await db.scalars(select(BusinessRecord.serial_no).where(
        BusinessRecord.module == "bug_feedback", BusinessRecord.serial_no.like(f"{prefix}%"),
    ).execution_options(include_deleted=True))).all()
    sequence = max((int(match.group(1)) for value in existing
                    if (match := re.fullmatch(rf"{prefix}(\d{{3,4}})", value))), default=0) + 1
    return f"{prefix}{sequence:03d}"


def _serialize_feedback(record: BusinessRecord, owner_name: str = "", assignee_name: str = "", has_screenshot: bool = False) -> dict:
    return {
        "id": record.id, "serial_no": record.serial_no, "description": record.description,
        "status": _status(record.status), "owner": record.owner, "owner_display_name": owner_name,
        "assignee": _assignee(record), "assignee_display_name": assignee_name,
        "page": (record.data or {}).get("page", ""), "route": (record.data or {}).get("route", ""),
        "controls": (record.data or {}).get("controls", []),
        "legacy_serial_no": (record.data or {}).get("legacy_serial_no", ""),
        "has_screenshot": has_screenshot,
        "created_at": record.created_at, "updated_at": record.updated_at,
    }


async def _read_screenshot(screenshot: UploadFile | None) -> tuple[bytes, str]:
    if not screenshot:
        return b"", ""
    content = await screenshot.read(10 * 1024 * 1024 + 1)
    suffix = _image_suffix(content)
    if not suffix:
        raise HTTPException(422, "截图仅支持 PNG、JPG 或 WebP 图片")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "截图不能超过 10MB")
    return content, suffix


FEEDBACK_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
FEEDBACK_FILE_SUFFIXES = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt", ".log", ".zip", ".mp4", ".mov"}
FEEDBACK_MAX_FILES = 10


IMAGE_SIGNATURES = {
    ".png": lambda content: content.startswith(b"\x89PNG\r\n\x1a\n"),
    ".jpg": lambda content: content.startswith(b"\xff\xd8\xff"),
    ".jpeg": lambda content: content.startswith(b"\xff\xd8\xff"),
    ".webp": lambda content: content.startswith(b"RIFF") and content[8:12] == b"WEBP",
}


def _image_suffix(content: bytes) -> str:
    """按文件头认图片类型。截图工具常把 PNG/WebP 存成 .jpg，扩展名不可靠，按真实类型保存。"""
    for suffix in (".png", ".jpg", ".webp"):
        if IMAGE_SIGNATURES[suffix](content):
            return suffix
    return ""


def _check_feedback_bytes(name: str, content: bytes) -> tuple[str, str]:
    """按文件名后缀和内容校验，返回 (后缀, 分类)：图片 ≤10MB 且文件头对得上，其他附件按白名单 ≤20MB。"""
    suffix = Path(name or "").suffix.lower()
    if suffix in FEEDBACK_IMAGE_SUFFIXES:
        suffix = _image_suffix(content)
        if not suffix:
            raise HTTPException(422, "截图仅支持 PNG、JPG 或 WebP 图片")
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(413, "截图不能超过 10MB")
        return suffix, "问题反馈截图"
    if suffix not in FEEDBACK_FILE_SUFFIXES:
        raise HTTPException(422, f"不支持的附件类型：{name}")
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(413, f"附件不能超过 20MB：{name}")
    return suffix, "问题反馈附件"


async def _read_feedback_file(upload: UploadFile) -> tuple[bytes, str, str]:
    """返回 (内容, 后缀, 分类)；图片按截图校验，其余按附件白名单和 20MB 上限。"""
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix in FEEDBACK_IMAGE_SUFFIXES:
        content, suffix = await _read_screenshot(upload)
        return content, suffix, "问题反馈截图"
    if suffix not in FEEDBACK_FILE_SUFFIXES:
        raise HTTPException(422, f"不支持的附件类型：{upload.filename}")
    content = await upload.read(20 * 1024 * 1024 + 1)
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(413, f"附件不能超过 20MB：{upload.filename}")
    return content, suffix, "问题反馈附件"


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


async def _new_feedback(db: AsyncSession, identity: dict, description: str, page: str, route: str,
                        control_names: list[str]) -> tuple[BusinessRecord, WorkflowEvent]:
    data = {"page": page.strip()}
    if route.strip():
        data["route"] = route.strip()
    if control_names:
        data["controls"] = control_names
    record = BusinessRecord(
        module="bug_feedback", serial_no=await _next_feedback_serial(db),
        title=description[:100], customer="", status="待处理", owner=identity["username"],
        description=description, data=data,
    )
    db.add(record)
    await db.flush()
    event = WorkflowEvent(
        record_id=record.id, action="提交反馈", from_status="", to_status="待处理",
        operator=identity["username"], comment="",
    )
    db.add(event)
    await db.flush()
    return record, event


@router.post(f"{settings.api_prefix}/feedback")
async def create_feedback(
    description: str = Form(...), page: str = Form(""), route: str = Form(""), controls: str = Form(""),
    screenshot: UploadFile | None = File(None), files: list[UploadFile] = File(default=[]),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    description = description.strip()
    # 描述不限字数，只要求不为空（用户要求，2026-10-24）。
    if not description:
        raise HTTPException(422, "请填写问题描述")
    if len(page) > 500 or len(route) > 300:
        raise HTTPException(422, "页面地址过长")
    if len(controls) > 1000:
        raise HTTPException(422, "选择的按钮过多")
    control_names = list(dict.fromkeys(name.strip() for name in controls.split("、") if name.strip()))
    uploads = ([screenshot] if screenshot else []) + [item for item in files if item.filename]
    if len(uploads) > FEEDBACK_MAX_FILES:
        raise HTTPException(422, f"截图和附件合计最多 {FEEDBACK_MAX_FILES} 个")
    contents = [(upload, *await _read_feedback_file(upload)) for upload in uploads]
    stored_paths: list[Path] = []
    try:
        record, event = await _new_feedback(db, identity, description, page, route, control_names)
        for upload, content, suffix, category in contents:
            stored_paths.append(_save_screenshot(
                db, record.id, upload, content, suffix, identity["username"], category,
            ))
        await _notify_participants(db, record, identity["username"], "新反馈", event.id)
        await db.commit()
        return {"id": record.id, "serial_no": record.serial_no}
    except Exception:
        await db.rollback()
        for stored_path in stored_paths:
            stored_path.unlink(missing_ok=True)
        raise


@router.get(f"{settings.api_prefix}/feedback/status-counts")
async def feedback_status_counts(
    mine: bool = Query(False), date_from: date | None = Query(None), date_to: date | None = Query(None),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """问题处理中心的状态页签计数；范围与列表一致（管理员看全部，其他人看自己提交或指派给自己的）。"""
    conditions = [BusinessRecord.module == "bug_feedback", BusinessRecord.deleted_at.is_(None)]
    # mine：“我的反馈”只看自己提交或指派给自己的（管理员也一样）；全部反馈在问题处理中心看。
    if mine or not _is_admin(identity):
        conditions.append(or_(
            BusinessRecord.owner == identity["username"],
            BusinessRecord.data["assignee"].as_string() == identity["username"],
        ))
    conditions.extend(_created_between(date_from, date_to))
    rows = (await db.execute(select(BusinessRecord.status, func.count()).where(*conditions)
                             .group_by(BusinessRecord.status))).all()
    counts = {status: 0 for status in FEEDBACK_STATUSES}
    for stored, count in rows:
        if _status(stored) in counts:
            counts[_status(stored)] += count
    return {"total": sum(counts.values()), "counts": counts}


@router.get(f"{settings.api_prefix}/feedback")
async def list_feedback(
    keyword: str = Query("", max_length=200), page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100), status: str = Query(""), mine: bool = Query(False),
    date_from: date | None = Query(None), date_to: date | None = Query(None),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    if status and status not in FEEDBACK_STATUSES:
        raise HTTPException(422, "反馈状态无效")
    conditions = [BusinessRecord.module == "bug_feedback", BusinessRecord.deleted_at.is_(None)]  # 核心 Table 联接不带自动过滤，显式排除已删除
    # mine：“我的反馈”只看自己提交或指派给自己的（管理员也一样）；全部反馈在问题处理中心看。
    if mine or not _is_admin(identity):
        conditions.append(or_(
            BusinessRecord.owner == identity["username"],
            BusinessRecord.data["assignee"].as_string() == identity["username"],
        ))
    if status:
        conditions.append(BusinessRecord.status.in_(_stored_statuses(status)))
    conditions.extend(_created_between(date_from, date_to))
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
            BusinessRecord.data["legacy_serial_no"].as_string().icontains(keyword, autoescape=True),
            BusinessRecord.description.icontains(keyword, autoescape=True),
            BusinessRecord.owner.icontains(keyword, autoescape=True),
            owner_user.display_name.icontains(keyword, autoescape=True),
            BusinessRecord.data["page"].as_string().icontains(keyword, autoescape=True),
        ))
    total = await db.scalar(select(func.count()).select_from(joins).where(*conditions))
    has_screenshot = select(FileAttachment.id).where(
        FileAttachment.record_id == BusinessRecord.id,
        FileAttachment.category.in_(FEEDBACK_ATTACHMENT_CATEGORIES),
    ).exists()
    records = (await db.execute(select(BusinessRecord, owner_user.display_name, assignee_user.display_name, has_screenshot)
    .select_from(joins).where(*conditions).order_by(
        BusinessRecord.updated_at.desc(), BusinessRecord.id.desc(),
    ).offset((page - 1) * page_size).limit(page_size))).all()
    return {"total": total, "page": page, "page_size": page_size, "can_delete": _is_admin(identity), "items": [
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
        FileAttachment.record_id == record.id, FileAttachment.category.in_(FEEDBACK_REPLY_CATEGORIES),
    ))).all()
    screenshot_event_ids = {attachment.remark for attachment in screenshots}
    files = (await db.scalars(select(FileAttachment).where(
        FileAttachment.record_id == record.id, FileAttachment.category.in_(FEEDBACK_ATTACHMENT_CATEGORIES),
    ).order_by(FileAttachment.id))).all()
    missing_names = {event.operator for event in events} - names.keys()
    if missing_names:
        authors = (await db.scalars(select(User).where(User.username.in_(missing_names)))).all()
        names.update({user.username: user.display_name for user in authors})
    names[FEEDBACK_BOT_USERNAME] = FEEDBACK_BOT_DISPLAY_NAME
    return {
        **_serialize_feedback(record, names.get(record.owner, ""), names.get(_assignee(record), ""), has_screenshot),
        "can_assign": _is_admin(identity), "can_delete": _is_admin(identity),
        "available_actions": _available_actions(record, identity),
        "can_withdraw": _can_withdraw(record, identity, events),
        "attachments": [{
            "id": item.id, "name": item.original_name, "size": item.size,
            "content_type": item.content_type, "is_image": item.category == "问题反馈截图",
        } for item in files],
        "events": [{
            "id": event.id, "action": event.action, "from_status": _status(event.from_status),
            "to_status": _status(event.to_status), "operator": event.operator,
            "operator_display_name": names.get(event.operator, ""),
            "operator_role": _operator_role(record, event.operator), "comment": event.comment,
            "created_at": event.created_at, "has_screenshot": str(event.id) in screenshot_event_ids,
            "attachments": [{
                "id": item.id, "name": item.original_name, "size": item.size,
                "content_type": item.content_type, "is_image": item.category == "问题反馈补充截图",
            } for item in screenshots if item.remark == str(event.id)],
        } for event in events],
    }


@router.post(f"{settings.api_prefix}/feedback/{{feedback_id}}/messages")
async def add_feedback_message(
    feedback_id: int, content: str = Form(""), screenshot: UploadFile | None = File(None),
    files: list[UploadFile] = File(default=[]),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    content = content.strip()
    uploads = ([screenshot] if screenshot else []) + [item for item in files if item.filename]
    if not content and not uploads:
        raise HTTPException(422, "请填写回复内容或添加截图、附件")
    if len(uploads) > FEEDBACK_MAX_FILES:
        raise HTTPException(422, f"截图和附件合计最多 {FEEDBACK_MAX_FILES} 个")
    contents = [(upload, *await _read_feedback_file(upload)) for upload in uploads]
    record = await _get_feedback(db, feedback_id, identity, lock=True)
    _require_open(record)
    stored_paths: list[Path] = []
    try:
        current = _status(record.status)
        record.updated_at = func.now()
        event = WorkflowEvent(
            record_id=record.id, action="回复",
            from_status=current, to_status=current, operator=identity["username"], comment=content,
        )
        db.add(event)
        await db.flush()
        for upload, data, suffix, category in contents:
            stored_paths.append(_save_screenshot(
                db, record.id, upload, data, suffix, identity["username"], REPLY_CATEGORY[category], event.id,
            ))
        await _notify_participants(db, record, identity["username"], event.action, event.id)
        await db.commit()
        return {"status": _status(record.status)}
    except Exception:
        await db.rollback()
        for stored_path in stored_paths:
            stored_path.unlink(missing_ok=True)
        raise


@router.post(f"{settings.api_prefix}/feedback/{{feedback_id}}/transitions")
async def transition_feedback(
    feedback_id: int, body: FeedbackTransition,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    record = await _get_feedback(db, feedback_id, identity, lock=True)
    action = body.action.strip()
    definition = _action_definition(record, identity, action)
    if definition is None:
        raise HTTPException(403, "无权执行此操作")
    allowed_statuses, next_status = definition
    previous_status = _status(record.status)
    _require_open(record)
    if action == WITHDRAW_ACTION and not _withdrawable(record, (await db.scalars(select(WorkflowEvent).where(
            WorkflowEvent.record_id == record.id))).all()):
        raise HTTPException(409, "已开始修改，不能撤回")
    if previous_status not in allowed_statuses:
        raise HTTPException(409, "反馈状态已变化，请刷新后重试")
    comment = body.comment.strip()
    if action in COMMENT_REQUIRED_ACTIONS and not comment:
        raise HTTPException(422, "请写明打算怎么改" if action == "请确认修改方案" else "请写明哪里还没解决")
    if action == "确认修改" and identity["username"] == FEEDBACK_BOT_USERNAME and not comment:
        raise HTTPException(422, "请写明谁在哪条回复里确认的")
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
    _require_open(record)
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
        record_id=record.id, action="指派处理人", from_status=_status(record.status), to_status=_status(record.status),
        operator=identity["username"], comment=f"{old_assignee or '未指派'} → {user.display_name}（{username}）",
    )
    db.add(event)
    await db.flush()
    await _notify_participants(db, record, identity["username"], "指派处理人", event.id)
    await db.commit()
    return {"assignee": username}


@router.delete(f"{settings.api_prefix}/feedback/{{feedback_id}}")
async def delete_feedback(feedback_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """管理员删除问题（用户要求，2026-10-26）。逻辑删除：处理记录、截图和附件记录一并标记，文件保留，
    可在“系统管理 → 回收站”恢复。"""
    if not _is_admin(identity):
        raise HTTPException(403, "仅管理员可以删除问题")
    record = await _get_feedback(db, feedback_id, identity, lock=True)
    serial_no = record.serial_no
    await db.delete(record)
    await db.commit()
    return {"id": feedback_id, "serial_no": serial_no}


@router.get(f"{settings.api_prefix}/feedback/{{feedback_id}}/screenshot")
async def feedback_screenshot(feedback_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    await _get_feedback(db, feedback_id, identity)
    attachment = await db.scalar(select(FileAttachment).where(
        FileAttachment.record_id == feedback_id, FileAttachment.category == "问题反馈截图",
    ).order_by(FileAttachment.id).limit(1))
    from app.core.storage import ensure_attachment_local
    path = (await ensure_attachment_local(attachment) or Path(str(attachment.path))) if attachment else None
    if not path or not path.is_file():
        raise HTTPException(404, "截图不存在")
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.original_name)


@router.get(f"{settings.api_prefix}/feedback/{{feedback_id}}/events/{{event_id}}/screenshot")
async def feedback_event_screenshot(
    feedback_id: int, event_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    await _get_feedback(db, feedback_id, identity)
    attachment = await db.scalar(select(FileAttachment).where(
        FileAttachment.record_id == feedback_id, FileAttachment.category == "问题反馈补充截图",
        FileAttachment.remark == str(event_id),
    ))
    from app.core.storage import ensure_attachment_local
    path = (await ensure_attachment_local(attachment) or Path(str(attachment.path))) if attachment else None
    if not path or not path.is_file():
        raise HTTPException(404, "补充截图不存在")
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.original_name)


@router.get(f"{settings.api_prefix}/feedback/{{feedback_id}}/attachments/{{attachment_id}}")
async def feedback_attachment(
    feedback_id: int, attachment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    await _get_feedback(db, feedback_id, identity)
    attachment = await db.scalar(select(FileAttachment).where(
        FileAttachment.id == attachment_id, FileAttachment.record_id == feedback_id,
        FileAttachment.category.in_((*FEEDBACK_ATTACHMENT_CATEGORIES, *FEEDBACK_REPLY_CATEGORIES)),
    ))
    from app.core.storage import ensure_attachment_local
    path = (await ensure_attachment_local(attachment) or Path(str(attachment.path))) if attachment else None
    if not path or not path.is_file():
        raise HTTPException(404, "附件不存在")
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.original_name)


# ---- 分步提交：文字走 JSON，截图和附件每个文件单独上传原始内容 ----
# 钉钉 Mac 客户端内置浏览器（DTWKWebView）提交带文件的表单时，服务端收到的表单里没有文字字段
# （2026-10-25 生产日志：POST /feedback 422 “description：Field required”）。先用 JSON 建好反馈，
# 文件再逐个上传，某个文件失败也不影响反馈本身。原来的表单接口保留给旧页面和其他调用方。

@router.post(f"{settings.api_prefix}/feedback/submit")
async def submit_feedback(body: FeedbackSubmit, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    description = body.description.strip()
    if not description:
        raise HTTPException(422, "请填写问题描述")
    control_names = list(dict.fromkeys(name.strip() for name in body.controls if name.strip()))
    record, event = await _new_feedback(db, identity, description, body.page, body.route, control_names)
    await _notify_participants(db, record, identity["username"], "新反馈", event.id)
    await db.commit()
    return {"id": record.id, "serial_no": record.serial_no}


@router.post(f"{settings.api_prefix}/feedback/{{feedback_id}}/replies")
async def reply_feedback(
    feedback_id: int, body: FeedbackReply,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    content = body.content.strip()
    if not content and not body.file_count:
        raise HTTPException(422, "请填写回复内容或添加截图、附件")
    record = await _get_feedback(db, feedback_id, identity, lock=True)
    _require_open(record)
    current = _status(record.status)
    record.updated_at = func.now()
    event = WorkflowEvent(
        record_id=record.id, action="回复", from_status=current, to_status=current,
        operator=identity["username"], comment=content,
    )
    db.add(event)
    await db.flush()
    await _notify_participants(db, record, identity["username"], event.action, event.id)
    await db.commit()
    return {"status": current, "event_id": event.id}


@router.post(f"{settings.api_prefix}/feedback/{{feedback_id}}/files")
async def upload_feedback_file(
    feedback_id: int, request: Request, name: str = Query(..., min_length=1, max_length=255),
    event_id: int | None = Query(None), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """上传一个文件（请求体就是文件内容）。不带 event_id 是反馈本身的截图/附件，只能提交人在提交后 30 分钟内上传；
    带 event_id 是某条回复的文件，只能该回复的发送人上传。"""
    record = await _get_feedback(db, feedback_id, identity, lock=True)
    _require_open(record)
    if event_id is None:
        if record.owner != identity["username"]:
            raise HTTPException(403, "只有提交人可以给反馈添加截图和附件")
        if record.created_at and (datetime.now(record.created_at.tzinfo) - record.created_at) > timedelta(minutes=30):
            raise HTTPException(409, "反馈已提交超过 30 分钟，请在回复里补充截图和附件")
        categories = FEEDBACK_ATTACHMENT_CATEGORIES
    else:
        event = await db.scalar(select(WorkflowEvent).where(WorkflowEvent.id == event_id, WorkflowEvent.record_id == record.id))
        if event is None or event.operator != identity["username"]:
            raise HTTPException(403, "只能给自己的回复添加截图和附件")
        categories = FEEDBACK_REPLY_CATEGORIES
    existing = await db.scalar(select(func.count()).select_from(FileAttachment).where(
        FileAttachment.record_id == record.id, FileAttachment.category.in_(categories),
        FileAttachment.remark == (str(event_id) if event_id else ""),
    ))
    if (existing or 0) >= FEEDBACK_MAX_FILES:
        raise HTTPException(422, f"截图和附件合计最多 {FEEDBACK_MAX_FILES} 个")
    declared = int(request.headers.get("content-length") or 0)
    if declared > 20 * 1024 * 1024 + 1024:
        raise HTTPException(413, "附件不能超过 20MB")
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > 20 * 1024 * 1024:
            raise HTTPException(413, "附件不能超过 20MB")
    if not content:
        raise HTTPException(422, f"文件内容为空：{name}")
    suffix, category = _check_feedback_bytes(name, bytes(content))
    if event_id is not None:
        category = REPLY_CATEGORY[category]
    stored_name = f"{uuid4().hex}{suffix}"
    stored_path = UPLOAD_ROOT / stored_name
    stored_path.write_bytes(bytes(content))
    try:
        db.add(FileAttachment(
            record_id=record.id, category=category, original_name=Path(name).name,
            stored_name=stored_name, content_type=request.headers.get("content-type") or "application/octet-stream",
            size=len(content), path=str(stored_path), uploader=identity["username"],
            remark=str(event_id) if event_id else "",
        ))
        await db.commit()
    except Exception:
        await db.rollback()
        stored_path.unlink(missing_ok=True)
        raise
    return {"name": Path(name).name, "size": len(content)}
