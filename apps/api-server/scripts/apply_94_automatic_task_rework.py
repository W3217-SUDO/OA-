"""Apply the scoped 9.4 automatic-task identity and missed-event repair."""

from __future__ import annotations

import argparse
import asyncio
import json
import secrets

from sqlalchemy import or_, select

from app.core.tasks import _ensure_document_preparation_task, _ensure_phase_automatic_tasks
from app.database import SessionLocal
from app.models import BusinessRecord, User, WorkflowEvent
from app.security import hash_password


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--apply", action="store_true")
    result.add_argument("--owner-username", required=True)
    result.add_argument("--owner-display-name", required=True)
    result.add_argument("--owner-department", required=True)
    result.add_argument("--dingtalk-user-id", required=True)
    result.add_argument("--document-event-id", type=int, action="append", default=[])
    result.add_argument("--archive-event-id", type=int, action="append", default=[])
    return result


async def verified_event(db, event_id: int, *, target_status: str) -> tuple[WorkflowEvent, BusinessRecord]:
    event = await db.get(WorkflowEvent, event_id)
    if not event or event.action not in {"修改普通案件基本信息", "修改案件阶段"}:
        raise RuntimeError(f"event {event_id} is not a verified case transition")
    if event.to_status != target_status or event.from_status == event.to_status:
        raise RuntimeError(f"event {event_id} does not enter {target_status}")
    case = await db.get(BusinessRecord, event.record_id)
    if not case or case.module != "case":
        raise RuntimeError(f"event {event_id} is not linked to a case")
    return event, case


async def resolve_or_create_owner(db, args) -> tuple[User | None, str]:
    matches = list((await db.scalars(select(User).where(or_(
        User.username == args.owner_username,
        User.display_name == args.owner_display_name,
    )))).all())
    if len(matches) > 1:
        raise RuntimeError("configured owner username/display name are not unique")
    if matches:
        owner = matches[0]
        if owner.username != args.owner_username or owner.display_name != args.owner_display_name:
            raise RuntimeError("configured owner conflicts with an existing OA user")
        existing_ding_id = str((owner.profile or {}).get("dingtalk_user_id") or "").strip()
        if existing_ding_id and existing_ding_id != args.dingtalk_user_id:
            raise RuntimeError("configured owner is bound to another DingTalk identity")
        return owner, "reuse"

    duplicate_binding = list((await db.scalars(select(User))).all())
    if any(str((user.profile or {}).get("dingtalk_user_id") or "").strip() == args.dingtalk_user_id for user in duplicate_binding):
        raise RuntimeError("DingTalk identity is already bound to another OA user")
    if not args.apply:
        return None, "create"
    owner = User(
        username=args.owner_username,
        display_name=args.owner_display_name,
        department=args.owner_department,
        password_hash=hash_password(secrets.token_urlsafe(32)),
        role="user",
        role_ids=["user"],
        profile={"dingtalk_user_id": args.dingtalk_user_id},
        is_active=True,
        must_change_password=True,
    )
    db.add(owner)
    await db.flush()
    return owner, "create"


async def run(args) -> dict:
    async with SessionLocal() as db:
        owner, owner_action = await resolve_or_create_owner(db, args)
        document_events = [await verified_event(db, event_id, target_status="文书准备") for event_id in args.document_event_id]
        archive_events = [await verified_event(db, event_id, target_status="一审和解结案") for event_id in args.archive_event_id]
        plan = {
            "mode": "apply" if args.apply else "dry-run",
            "owner_action": owner_action,
            "owner_username": args.owner_username,
            "document_events": [{"event_id": event.id, "case_id": case.id, "case_no": case.serial_no} for event, case in document_events],
            "archive_events": [{"event_id": event.id, "case_id": case.id, "case_no": case.serial_no} for event, case in archive_events],
        }
        if not args.apply:
            await db.rollback()
            return plan
        created_task_ids: list[int] = []
        for event, case in document_events:
            task = await _ensure_document_preparation_task(
                case,
                db,
                system_operator="9.4-scoped-repair",
                transition_date=event.created_at.date(),
            )
            if task:
                created_task_ids.append(task.id)
        for event, case in archive_events:
            tasks = await _ensure_phase_automatic_tasks(
                case,
                db,
                previous_status=event.from_status,
                today=event.created_at.date(),
            )
            created_task_ids.extend(task.id for task in tasks)
        await db.commit()
        plan["task_ids"] = sorted(set(created_task_ids))
        return plan


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run(parser().parse_args())), ensure_ascii=False, indent=2))
