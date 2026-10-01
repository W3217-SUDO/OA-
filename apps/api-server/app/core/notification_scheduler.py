"""独立于 GET 请求的提醒生成和短信发送调度。"""

import asyncio
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.database import SessionLocal
from app.models import NotificationSyncSchedule, User
from app.security import user_role_ids


logger = logging.getLogger(__name__)
SYNC_INTERVAL = timedelta(minutes=1)
SYNC_LEASE = timedelta(minutes=3)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def seed_notification_schedules() -> int:
    """首次启动和新增账号都能获得一条可领取的生成任务。"""
    async with SessionLocal() as db:
        usernames = (await db.scalars(select(User.username).where(User.is_active.is_(True)))).all()
        if not usernames:
            return 0
        dialect = (await db.connection()).dialect.name
        values = [{"username": username, "next_run_at": _now()} for username in usernames]
        if dialect == "postgresql":
            statement = postgres_insert(NotificationSyncSchedule).values(values)
        elif dialect == "sqlite":
            statement = sqlite_insert(NotificationSyncSchedule).values(values)
        else:
            raise RuntimeError(f"通知调度不支持数据库方言 {dialect}")
        inserted = (await db.execute(statement.on_conflict_do_nothing().returning(
            NotificationSyncSchedule.username,
        ))).scalars().all()
        await db.commit()
        return len(inserted)


async def claim_notification_sync() -> tuple[str, str] | None:
    now = _now()
    token = secrets.token_hex(24)
    async with SessionLocal() as db:
        candidate = (
            select(NotificationSyncSchedule.username)
            .where(
                NotificationSyncSchedule.next_run_at <= now,
                or_(NotificationSyncSchedule.lease_until.is_(None), NotificationSyncSchedule.lease_until <= now),
            ).order_by(NotificationSyncSchedule.next_run_at, NotificationSyncSchedule.username)
            .limit(1).with_for_update(skip_locked=True).scalar_subquery()
        )
        username = await db.scalar(
            update(NotificationSyncSchedule)
            .where(
                NotificationSyncSchedule.username == candidate,
                NotificationSyncSchedule.next_run_at <= now,
                or_(NotificationSyncSchedule.lease_until.is_(None), NotificationSyncSchedule.lease_until <= now),
            )
            .values(lease_until=now + SYNC_LEASE, claim_token=token)
            .returning(NotificationSyncSchedule.username)
        )
        await db.commit()
        return (username, token) if username else None


async def _finish_sync(username: str, token: str, error: str = "") -> None:
    async with SessionLocal() as db:
        await db.execute(
            update(NotificationSyncSchedule)
            .where(NotificationSyncSchedule.username == username, NotificationSyncSchedule.claim_token == token)
            .values(
                next_run_at=_now() + SYNC_INTERVAL,
                lease_until=None,
                claim_token="",
                last_completed_at=None if error else _now(),
                last_error=error[:500],
            )
        )
        await db.commit()


async def sync_one_recipient() -> bool:
    claim = await claim_notification_sync()
    if claim is None:
        return False
    username, token = claim
    try:
        async with SessionLocal() as db:
            user = await db.scalar(select(User).where(User.username == username, User.is_active.is_(True)))
            if user:
                from app.core.permissions import _user_permission_payload
                from app.core.tasks import _sync_notifications

                role_ids = user_role_ids(user)
                profile = user.profile or {}
                permission = await _user_permission_payload(user, db)
                identity = {
                    "username": user.username,
                    "role": role_ids[0],
                    "role_ids": role_ids,
                    "display_name": user.display_name,
                    "department": user.department,
                    "permission_role": profile.get("permission_role") or "",
                    "staff_role": profile.get("staff_role") or "",
                    "position": profile.get("position") or "",
                    "menu_keys": permission.get("menu_keys") or [],
                    "action_keys": permission.get("action_keys") or [],
                    "data_scope": permission.get("data_scope"),
                    "_actual_role": role_ids[0],
                    "_actual_role_ids": role_ids,
                    "_page_menu_capability": False,
                }
                await _sync_notifications(identity, db)
    except Exception as exc:
        await _finish_sync(username, token, str(exc))
        raise
    await _finish_sync(username, token)
    return True


async def run_notification_generation_once(max_recipients: int = 50) -> int:
    from app.core.tasks import _apply_hearing_sms_reminders

    async with SessionLocal() as db:
        await _apply_hearing_sms_reminders(db)
    await seed_notification_schedules()
    processed = 0
    for _ in range(max_recipients):
        if not await sync_one_recipient():
            break
        processed += 1
    return processed


async def notification_scheduler_loop() -> None:
    from app.core.notification_delivery import dispatch_one, mark_expired_claims_unknown

    while True:
        try:
            await run_notification_generation_once()
        except Exception:
            logger.exception("后台通知生成失败")
        try:
            await mark_expired_claims_unknown()
            for _ in range(50):
                if not await dispatch_one("sms"):
                    break
        except Exception:
            logger.exception("后台短信发送失败")
        await asyncio.sleep(30)
