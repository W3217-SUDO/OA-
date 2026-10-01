"""持久通知发件箱：先提交业务记录，再领取并调用外部通道。"""

import logging
import secrets
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import and_, select, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import SessionLocal
from app.dingtalk import DingTalkError, DingTalkRejectedError, dingtalk_client
from app.models import (
    BusinessRecord, HearingSchedule, Notification, NotificationDelivery, User, WorkflowEvent,
)


logger = logging.getLogger(__name__)
CLAIM_TIMEOUT = timedelta(minutes=2)
RETRY_DELAY = timedelta(minutes=1)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def insert_delivery(db: AsyncSession, values: dict) -> int | None:
    """唯一业务键争用时只允许一个调度实例创建发送记录。"""
    dialect = (await db.connection()).dialect.name
    if dialect == "postgresql":
        statement = postgres_insert(NotificationDelivery).values(**values)
    elif dialect == "sqlite":
        statement = sqlite_insert(NotificationDelivery).values(**values)
    else:
        raise RuntimeError(f"通知发件箱不支持数据库方言 {dialect}")
    result = await db.execute(statement.on_conflict_do_nothing().returning(NotificationDelivery.id))
    return result.scalar_one_or_none()


async def enqueue_dingtalk_notifications(db: AsyncSession) -> int:
    """只从已提交的站内通知生成钉钉发件箱项。"""
    if not settings.dingtalk_notifications_enabled or not dingtalk_client.configured:
        return 0
    inserted = 0
    last_id = 0
    while True:
        rows = (await db.execute(
            select(Notification, User)
            .join(User, User.username == Notification.recipient)
            .outerjoin(NotificationDelivery, and_(
                NotificationDelivery.channel == "dingtalk",
                NotificationDelivery.notification_id == Notification.id,
            ))
            .where(
                Notification.id > last_id,
                Notification.is_read.is_(False),
                Notification.recipient_deleted.is_(False),
                Notification.dingtalk_status.in_(("pending", "failed")),
                Notification.dingtalk_attempts < 5,
                User.is_active.is_(True),
                NotificationDelivery.id.is_(None),
            ).order_by(Notification.id).limit(200)
        )).all()
        if not rows:
            break
        for notice, user in rows:
            ding_user_id = str((user.profile or {}).get("dingtalk_user_id") or "").strip()
            if not ding_user_id:
                continue
            delivery_id = await insert_delivery(db, {
                "channel": "dingtalk",
                "business_key": notice.source_key,
                "notification_id": notice.id,
                "destination": ding_user_id,
                "payload": {"title": notice.title, "content": notice.content},
                "state": "pending",
                "attempts": int(notice.dingtalk_attempts or 0),
                "available_at": _now(),
            })
            inserted += delivery_id is not None
        last_id = rows[-1][0].id
    if inserted:
        await db.commit()
    return inserted


async def claim_delivery(channel: str) -> tuple[int, str] | None:
    """数据库原子领取；领取提交发生在任何外部请求之前。"""
    token = secrets.token_hex(24)
    now = _now()
    async with SessionLocal() as db:
        candidate = (
            select(NotificationDelivery.id)
            .where(
                NotificationDelivery.channel == channel,
                NotificationDelivery.state == "pending",
                NotificationDelivery.available_at <= now,
            ).order_by(NotificationDelivery.id).limit(1)
            .with_for_update(skip_locked=True)
            .scalar_subquery()
        )
        claimed = await db.scalar(
            update(NotificationDelivery)
            .where(NotificationDelivery.id == candidate, NotificationDelivery.state == "pending")
            .values(
                state="claimed", claim_token=token, claimed_at=now,
                attempts=NotificationDelivery.attempts + 1,
            ).returning(NotificationDelivery.id)
        )
        await db.commit()
        return (claimed, token) if claimed is not None else None


async def _set_delivery_result(
    delivery_id: int, token: str, state: str, *, reference: str = "", error: str = "",
) -> bool:
    async with SessionLocal() as db:
        delivery = await db.scalar(select(NotificationDelivery).where(
            NotificationDelivery.id == delivery_id,
            NotificationDelivery.state == "claimed",
            NotificationDelivery.claim_token == token,
        ))
        if delivery is None:
            return False
        if state == "pending" and delivery.attempts >= 5:
            state = "rejected"
            error = f"发送前准备连续失败 {delivery.attempts} 次：{error}"
        delivery.state = state
        delivery.error = error[:500]
        delivery.provider_reference = reference[:500]
        delivery.claim_token = ""
        delivery.completed_at = _now() if state in {"sent", "rejected", "unknown", "cancelled"} else None
        if state == "pending":
            delivery.available_at = _now() + RETRY_DELAY
        if delivery.channel == "dingtalk" and delivery.notification_id:
            notice = await db.get(Notification, delivery.notification_id)
            if notice:
                notice.dingtalk_status = {
                    "sent": "sent", "rejected": "failed", "unknown": "unknown",
                    "cancelled": "skipped", "pending": "pending",
                }[state]
                notice.dingtalk_attempts = delivery.attempts
                notice.dingtalk_sent_at = _now() if state == "sent" else None
                notice.dingtalk_error = delivery.error
        if delivery.channel == "sms" and delivery.source_record_id:
            record = await db.get(BusinessRecord, delivery.source_record_id)
            if record:
                status = {"sent": "已发送", "rejected": "发送失败", "unknown": "结果待核实", "cancelled": "发送取消"}[state]
                record.status = status
                record.data = {**(record.data or {}), "provider_response": reference[:500] if state == "sent" else error[:500]}
                db.add(WorkflowEvent(
                    record_id=record.id, action="更新开庭短信发送结果", from_status="待发送",
                    to_status=status, operator="system", comment=error[:500] or reference[:500],
                ))
                key = delivery.business_key.split(":")
                prefix = delivery.payload.get("notification_prefix")
                if prefix is None:
                    prefix = f"hearing-sms-{key[1]}-{key[2]}-"
                notices = (await db.scalars(select(Notification).where(Notification.source_key.startswith(prefix)))).all()
                for notice in notices:
                    notice.title = f"开庭短信：{status}"
                    notice.level = "info" if state == "sent" else "warning"
                    if notice.dingtalk_status == "skipped":
                        notice.dingtalk_status = "pending"
        await db.commit()
        return True


async def mark_expired_claims_unknown() -> int:
    """崩溃后的领取不重发，要求人工核对通道结果。"""
    cutoff = _now() - CLAIM_TIMEOUT
    async with SessionLocal() as db:
        rows = (await db.execute(select(NotificationDelivery.id, NotificationDelivery.claim_token).where(
            NotificationDelivery.state == "claimed",
            NotificationDelivery.claimed_at <= cutoff,
        ))).all()
    changed = 0
    for delivery_id, token in rows:
        changed += await _set_delivery_result(delivery_id, token, "unknown", error="发送进程中断，通道结果待人工核实")
    return changed


async def _send_dingtalk(delivery: NotificationDelivery) -> str:
    return await dingtalk_client.send_work_notification(
        delivery.destination, str(delivery.payload["title"]), str(delivery.payload["content"]),
    )


async def _send_sms(delivery: NotificationDelivery) -> str:
    headers = {"Authorization": f"Bearer {settings.sms_webhook_token}"} if settings.sms_webhook_token else {}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(settings.sms_webhook_url, json=delivery.payload, headers=headers)
        response.raise_for_status()
        return response.text[:500]


async def dispatch_one(channel: str, sender=None) -> bool:
    """发送器可由隔离测试替换，生产默认使用当前通道。"""
    if channel == "dingtalk":
        if not settings.dingtalk_notifications_enabled or not dingtalk_client.configured:
            return False
        send = sender or _send_dingtalk
    elif channel == "sms":
        if not settings.sms_webhook_url:
            return False
        send = sender or _send_sms
    else:
        raise ValueError(f"未知通知通道：{channel}")
    claim = await claim_delivery(channel)
    if claim is None:
        return False
    delivery_id, token = claim
    cancelled_reason = ""
    async with SessionLocal() as db:
        delivery = await db.get(NotificationDelivery, delivery_id)
        if delivery is None:
            raise RuntimeError("已领取的通知发送记录不存在")
        if channel == "dingtalk":
            notice = await db.get(Notification, delivery.notification_id)
            user = await db.scalar(select(User).where(User.username == notice.recipient)) if notice else None
            if (
                not notice or notice.is_read or notice.recipient_deleted
                or not user or not user.is_active
                or str((user.profile or {}).get("dingtalk_user_id") or "").strip() != delivery.destination
            ):
                cancelled_reason = "通知或收件人已变更"
        else:
            record = await db.get(BusinessRecord, delivery.source_record_id) if delivery.source_record_id else None
            hearing_id = delivery.payload.get("hearing_id")
            hearing = await db.get(HearingSchedule, hearing_id) if hearing_id else None
            remind_days = int(delivery.business_key.rsplit(":", 1)[-1])
            if not record or not hearing:
                cancelled_reason = "开庭短信业务记录已删除"
            elif hearing.status != "已排期" or (hearing.hearing_date - datetime.now().date()).days != remind_days:
                cancelled_reason = "开庭日程已变更"
            else:
                from app.core.hearing_reminders import hearing_snapshot

                snapshot = hearing_snapshot(hearing)
                if all(key in delivery.payload for key in snapshot):
                    if any(delivery.payload[key] != value for key, value in snapshot.items()):
                        cancelled_reason = "开庭日程已变更"
                else:
                    cancelled_reason = "旧提醒缺少日程快照，需核实后重新生成"
        payload = delivery
    if cancelled_reason:
        await _set_delivery_result(delivery_id, token, "cancelled", error=cancelled_reason)
        return True
    try:
        reference = await send(payload)
    except DingTalkRejectedError as exc:
        await _set_delivery_result(delivery_id, token, "rejected", error=str(exc))
    except DingTalkError as exc:
        await _set_delivery_result(delivery_id, token, "pending", error=str(exc))
    except httpx.HTTPStatusError as exc:
        state = "rejected" if 400 <= exc.response.status_code < 500 else "unknown"
        await _set_delivery_result(delivery_id, token, state, error=str(exc))
    except Exception as exc:
        await _set_delivery_result(delivery_id, token, "unknown", error=str(exc))
        logger.exception("通知发送 %s 结果不确定", delivery_id)
    else:
        await _set_delivery_result(delivery_id, token, "sent", reference=str(reference))
    return True
