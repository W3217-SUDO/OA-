"""按具体开庭日程生成提醒，发送交给持久发件箱。"""

import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.notification_delivery import insert_delivery
from app.models import BusinessRecord, HearingSchedule, Notification, NotificationDelivery, User, WorkflowEvent


def hearing_snapshot(hearing: HearingSchedule) -> dict[str, str]:
    return {
        "hearing_date": hearing.hearing_date.isoformat(),
        "hearing_time": hearing.hearing_time,
        "court": hearing.court,
        "courtroom": hearing.courtroom or "",
    }


def _legacy_matches(record: BusinessRecord, snapshot: dict, content: str) -> bool | None:
    """无法确认旧记录对应哪次日程时保持待核实，避免自动重复发送。"""
    data = record.data or {}
    if all(key in data for key in snapshot):
        return all(data[key] == value for key, value in snapshot.items())
    if record.description == content:
        return True
    if re.fullmatch(r"开庭提醒：案件 .+ 将于 \d{4}-\d{2}-\d{2} .* 开庭。", record.description or ""):
        return False
    return None


async def _apply_hearing_sms_reminders(db: AsyncSession) -> bool:
    """开庭前 3 日和 1 日各生成一次；改期或改时形成新的日程版本。"""
    today = date.today()
    changed = False
    schedules = (await db.scalars(select(HearingSchedule).where(
        HearingSchedule.status == "已排期",
        HearingSchedule.hearing_date.in_([today + timedelta(days=1), today + timedelta(days=3)]),
    ))).all()
    for hearing in schedules:
        days = (hearing.hearing_date - today).days
        case_record = await db.get(BusinessRecord, hearing.case_record_id)
        if not case_record:
            continue
        names = list(dict.fromkeys(value for value in [
            hearing.hearing_lawyer, *((case_record.data or {}).get("handling_lawyers") or []),
            (case_record.data or {}).get("assistant", ""),
        ] if value))
        users = (await db.scalars(select(User).where(
            User.is_active.is_(True), or_(User.username.in_(names), User.display_name.in_(names)),
        ))).all() if names else []
        phones = list(dict.fromkeys(
            str((user.profile or {}).get("phone") or "").strip() for user in users
            if str((user.profile or {}).get("phone") or "").strip()
        ))
        content = f"开庭提醒：案件 {case_record.serial_no} 将于 {hearing.hearing_date} {hearing.hearing_time} 在 {hearing.court}{(' ' + hearing.courtroom) if hearing.courtroom else ''} 开庭。"
        snapshot = hearing_snapshot(hearing)
        revision = hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:24]
        business_key = f"hearing:{hearing.id}:{revision}:{days}"
        notice_prefix = f"hearing-sms-{hearing.id}-{revision}-{days}-"
        payload = {
            "phones": phones, "content": content, "case_no": case_record.serial_no,
            "hearing_id": hearing.id, **snapshot, "notification_prefix": notice_prefix,
        }
        ready = bool(phones and settings.sms_webhook_url)
        sms_status = "待发送" if ready else "待补充手机号" if not phones else "待配置短信通道"
        delivery = await db.scalar(select(NotificationDelivery).where(
            NotificationDelivery.channel == "sms", NotificationDelivery.business_key == business_key,
        ))
        if delivery:
            if delivery.state == "blocked" and ready:
                delivery.state = "pending"
                delivery.available_at = datetime.now(timezone.utc)
                delivery.payload = payload
                delivery.destination = ",".join(phones)
                sms = await db.get(BusinessRecord, delivery.source_record_id) if delivery.source_record_id else None
                if sms:
                    previous_status = sms.status
                    sms.status = "待发送"
                    sms.data = {**(sms.data or {}), **snapshot, "phones": phones, "recipient_users": [user.username for user in users]}
                    db.add(WorkflowEvent(record_id=sms.id, action="短信发送条件已就绪", from_status=previous_status, to_status="待发送", operator="system"))
                changed = True
            continue
        legacy_records = (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "sms",
            BusinessRecord.data["hearing_id"].as_integer() == hearing.id,
            BusinessRecord.data["remind_days"].as_integer() == days,
        ).order_by(BusinessRecord.id.desc()))).all()
        legacy_sms = None
        uncertain_sms = None
        for candidate in legacy_records:
            matched = _legacy_matches(candidate, snapshot, content)
            if matched is True:
                legacy_sms = candidate
                break
            if matched is None and uncertain_sms is None:
                uncertain_sms = candidate
        if legacy_sms or uncertain_sms:
            existing = legacy_sms or uncertain_sms
            legacy_state = (
                "sent" if legacy_sms and existing.status == "已发送" else
                "blocked" if legacy_sms and existing.status in {"待补充手机号", "待配置短信通道"} else "unknown"
            )
            delivery_id = await insert_delivery(db, {
                "channel": "sms", "business_key": business_key,
                "source_record_id": existing.id, "destination": ",".join(phones),
                "payload": payload, "state": legacy_state,
                "available_at": datetime.now(timezone.utc),
                "error": "旧发送记录的日程或结果不明，禁止自动重发" if legacy_state == "unknown" else "",
            })
            changed |= delivery_id is not None
            continue
        delivery_id = await insert_delivery(db, {
            "channel": "sms", "business_key": business_key,
            "destination": ",".join(phones), "payload": payload,
            "state": "pending" if ready else "blocked", "available_at": datetime.now(timezone.utc),
        })
        if delivery_id is None:
            continue
        sms = BusinessRecord(
            module="sms", serial_no=f"DX{datetime.now():%Y%m%d%H%M%S%f}",
            title=f"开庭短信提醒—{case_record.serial_no}", customer=case_record.customer,
            status=sms_status, owner="system", department=case_record.department, description=content,
            data={
                "hearing_id": hearing.id, "case_id": case_record.id, "case_no": case_record.serial_no,
                "remind_days": days, **snapshot, "phones": phones,
                "recipient_users": [user.username for user in users], "provider_response": "",
            },
        )
        db.add(sms)
        await db.flush()
        delivery = await db.get(NotificationDelivery, delivery_id)
        delivery.source_record_id = sms.id
        db.add(WorkflowEvent(record_id=sms.id, action="生成开庭短信提醒", to_status=sms_status, operator="system", comment=f"开庭前 {days} 天；收件手机号 {len(phones)} 个"))
        for user in users:
            db.add(Notification(
                source_key=f"{notice_prefix}{user.username}", source_type="case", source_id=case_record.id,
                sender="system", recipient=user.username, notification_type="系统通知",
                title=f"开庭短信：{sms_status}", content=content, level="warning",
                dingtalk_status="skipped" if ready else "pending",
            ))
        changed = True
    if changed:
        await db.commit()
    return changed
