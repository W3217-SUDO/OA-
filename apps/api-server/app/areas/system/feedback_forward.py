"""问题处理中心：非免审单的内容自动转发给审核人（范文玲）。

用户要求（2026-11-06）：转发由后端做，不经过本机机器人或任何会话。
做法是发件队列：提交、回复时在同一事务里把“要转发什么”记进 record.data，后台循环再发钉钉工作通知。
所以发送失败、进程重启都不会挡提交，也不会丢；没发出去的留在 review_forward_pending 里，带失败原因，自动重试，
重试次数用完后清掉 attempts 就能补发。
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import select, update

from app.database import SessionLocal
from app.dingtalk import dingtalk_client
from app.models import BusinessRecord, FileAttachment, User, WorkflowEvent

logger = logging.getLogger(__name__)

FEEDBACK_REVIEWER_USERNAME = "fwl"
FEEDBACK_REVIEWER_DINGTALK_ID = "156133631033066318"
FEEDBACK_LINK = "https://huzhilawfirm.com/?page=feedback&id={id}"

PENDING_KEY = "review_forward_pending"
SENT_KEY = "review_forward_sent"
# 分步提交时文件在文字之后几秒才传完：等一小会儿再发，附件名能和正文放在同一条里。
FORWARD_DELAY = timedelta(seconds=15)
LOOP_INTERVAL_SECONDS = 10
# 发送中进程中断时，过这么久重新发。钉钉对同一人一天内内容相同的通知会去重，重发不会打扰。
CLAIM_TIMEOUT = timedelta(minutes=2)
MAX_ATTEMPTS = 30
# send_work_notification 连同标题、结尾应用地址一起截到 2000 字，这里每条正文留足余量。
PART_LIMIT = 1700

ATTACHMENT_CATEGORIES = ("问题反馈截图", "问题反馈附件")
TZ = ZoneInfo("Asia/Shanghai")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _pending(record: BusinessRecord) -> list[dict]:
    return list((record.data or {}).get(PENDING_KEY) or [])


def queue_forward(record: BusinessRecord, kind: str, *, event_id: int | None = None,
                  attachment_id: int | None = None, now: datetime | None = None) -> None:
    """在业务事务里记下要转发的内容，随业务一起提交。kind：submit 新单、event 回复或状态说明、file 补充文件。"""
    item = {
        "key": uuid4().hex, "kind": kind, "event_id": event_id, "attachment_id": attachment_id,
        "not_before": ((now or _now()) + FORWARD_DELAY).isoformat(), "attempts": 0,
    }
    record.data = {**(record.data or {}), PENDING_KEY: [*_pending(record), item]}


def queue_file_forward(record: BusinessRecord, attachment_id: int, event_id: int | None) -> None:
    """文件所属的正文还没开始发，就并进那一条（发的时候会列出附件名）；否则单独发一条。"""
    for item in _pending(record):
        if item.get("claimed_at"):
            continue
        if (event_id is None and item["kind"] == "submit") or (event_id is not None and item.get("event_id") == event_id):
            return
    queue_forward(record, "file", attachment_id=attachment_id)


def split_parts(text: str, limit: int = PART_LIMIT) -> list[str]:
    """按长度分条，尽量断在换行处；拼起来和原文一字不差，只在断点丢掉那个换行。"""
    parts: list[str] = []
    rest = text
    while len(rest) > limit:
        cut = rest.rfind("\n", limit // 2, limit + 1)
        if cut > 0:
            parts.append(rest[:cut])
            rest = rest[cut + 1:]
        else:
            parts.append(rest[:limit])
            rest = rest[limit:]
    if rest or not parts:
        parts.append(rest)
    return parts


def _time_text(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(TZ).strftime("%Y-%m-%d %H:%M:%S")


async def _display(db, username: str) -> str:
    name = await db.scalar(select(User.display_name).where(User.username == username))
    return f"{name}（{username}）" if name else username


async def _attachment_names(db, *conditions) -> list[str]:
    return list((await db.scalars(select(FileAttachment.original_name).where(*conditions).order_by(FileAttachment.id))).all())


def _names_line(names: list[str]) -> str:
    return f"附件和截图（{len(names)} 个）：{'、'.join(names)}" if names else "附件和截图：无"


async def _render(db, record: BusinessRecord, item: dict) -> tuple[str, str] | None:
    """返回 (标题, 正文)。对应的回复或文件已经不在时返回 None，这一项不用再发。"""
    data = record.data or {}
    link = f"直达链接：{FEEDBACK_LINK.format(id=record.id)}"
    if item["kind"] == "submit":
        names = await _attachment_names(
            db, FileAttachment.record_id == record.id, FileAttachment.category.in_(ATTACHMENT_CATEGORIES),
        )
        lines = [f"提交人：{await _display(db, record.owner)}", f"提交时间：{_time_text(record.created_at)}",
                 f"页面：{data.get('page') or '未填写'}"]
        if data.get("controls"):
            lines.append(f"涉及按钮：{'、'.join(data['controls'])}")
        lines += [f"问题描述：\n{record.description}", _names_line(names), link]
        return f"问题反馈待审核 {record.serial_no}", "\n".join(lines)
    if item["kind"] == "event":
        event = await db.scalar(select(WorkflowEvent).where(
            WorkflowEvent.id == item["event_id"], WorkflowEvent.record_id == record.id,
        ))
        if event is None:
            return None
        names = await _attachment_names(
            db, FileAttachment.record_id == record.id, FileAttachment.remark == str(event.id),
        )
        label = "回复" if event.action == "回复" else event.action
        lines = [f"提交人：{await _display(db, record.owner)}", f"操作人：{await _display(db, event.operator)}",
                 f"时间：{_time_text(event.created_at)}", f"动作：{label}（状态：{event.to_status}）",
                 f"内容：\n{event.comment or '（没有文字）'}"]
        if names:
            lines.append(_names_line(names))
        lines.append(link)
        return f"问题反馈{label} {record.serial_no}", "\n".join(lines)
    attachment = await db.scalar(select(FileAttachment).where(
        FileAttachment.id == item["attachment_id"], FileAttachment.record_id == record.id,
    ))
    if attachment is None:
        return None
    lines = [f"提交人：{await _display(db, record.owner)}", f"时间：{_time_text(attachment.created_at)}",
             f"补充文件：{attachment.original_name}", link]
    return f"问题反馈补充文件 {record.serial_no}", "\n".join(lines)


def _due_item(pending: list[dict], now: datetime) -> dict | None:
    """按顺序发：前一条还在等重试时，后面的也先等，免得范文玲先看到回复后看到正文。次数用完的跳过。"""
    for item in pending:
        if item.get("attempts", 0) >= MAX_ATTEMPTS:
            continue
        claimed = item.get("claimed_at")
        if claimed and datetime.fromisoformat(claimed) + CLAIM_TIMEOUT > now:
            return None
        if datetime.fromisoformat(item["not_before"]) > now:
            return None
        return item
    return None


async def _save(db, record: BusinessRecord, data: dict) -> None:
    # updated_at 写回原值：转发不算这条反馈有更新，列表顺序不动。
    await db.execute(update(BusinessRecord).where(BusinessRecord.id == record.id).values(
        data=data, updated_at=BusinessRecord.updated_at,
    ).execution_options(synchronize_session=False))


async def _lock_record(db, record_id: int) -> BusinessRecord | None:
    return await db.scalar(select(BusinessRecord).where(BusinessRecord.id == record_id).with_for_update()
                           .execution_options(populate_existing=True))


async def _settle(sessions, record_id: int, key: str, error: str | None, now: datetime) -> None:
    async with sessions() as db:
        record = await _lock_record(db, record_id)
        if record is None:
            return
        data = dict(record.data or {})
        pending = []
        for item in _pending(record):
            if item["key"] != key:
                pending.append(item)
            elif error is not None:
                attempts = item.get("attempts", 0) + 1
                pending.append({**item, "attempts": attempts, "error": error[:300], "claimed_at": None,
                                "not_before": (now + timedelta(minutes=min(attempts, 60))).isoformat()})
        if error is None:
            data[SENT_KEY] = int(data.get(SENT_KEY) or 0) + 1
        if pending:
            data[PENDING_KEY] = pending
        else:
            data.pop(PENDING_KEY, None)
        await _save(db, record, data)
        await db.commit()


async def _flush_record(sessions, record_id: int, send, now: datetime) -> None:
    while True:
        async with sessions() as db:
            record = await _lock_record(db, record_id)
            if record is None:
                return
            pending = _pending(record)
            item = _due_item(pending, now)
            if item is None:
                return
            key = item["key"]
            rendered = await _render(db, record, item)
            for candidate in pending:
                if candidate["key"] == key:
                    candidate["claimed_at"] = now.isoformat()
            await _save(db, record, {**(record.data or {}), PENDING_KEY: pending})
            await db.commit()
        error = None
        if rendered is not None:
            title, content = rendered
            parts = split_parts(content)
            try:
                for index, part in enumerate(parts, 1):
                    await send(FEEDBACK_REVIEWER_DINGTALK_ID,
                               f"{title}（{index}/{len(parts)}）" if len(parts) > 1 else title, part)
            except Exception as exc:
                error = str(exc) or type(exc).__name__
                logger.error("问题反馈转发审核人失败：record=%s item=%s error=%s", record_id, key, error)
        await _settle(sessions, record_id, key, error, now)
        if error is not None:
            return


async def flush_review_forwards(*, sessions=SessionLocal, send=None, now: datetime | None = None) -> None:
    now = now or _now()
    send = send or dingtalk_client.send_work_notification
    async with sessions() as db:
        record_ids = (await db.scalars(select(BusinessRecord.id).where(
            BusinessRecord.module == "bug_feedback", BusinessRecord.data[PENDING_KEY].as_string().is_not(None),
            BusinessRecord.deleted_at.is_(None),
        ).order_by(BusinessRecord.id))).all()
    for record_id in record_ids:
        await _flush_record(sessions, record_id, send, now)


async def feedback_review_forward_loop() -> None:
    while True:
        try:
            if dingtalk_client.configured:
                await flush_review_forwards()
        except Exception:
            logger.exception("问题反馈转发循环失败")
        await asyncio.sleep(LOOP_INTERVAL_SECONDS)
