"""Audit and repair migrated HR files that share one login identity.

Dry-run is the default. Applying requires ``--apply --backup-confirmed``.
The repair preserves one canonical employee file and its login, moves employee
children to it, and deletes only redundant migrated files.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, update

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.models import BusinessRecord, FileAttachment, HrSubrecord, User, WorkflowEvent


def identity_tokens(record: BusinessRecord) -> set[str]:
    data = record.data or {}
    legacy = data.get("legacy_hr_identity") if isinstance(data.get("legacy_hr_identity"), dict) else {}
    tokens: set[str] = set()
    username = str(data.get("username") or record.owner or "").strip().lower()
    if username:
        tokens.add(f"username:{username}")
    system_user_id = data.get("system_user_id")
    if str(system_user_id or "").strip():
        tokens.add(f"system_user_id:{system_user_id}")
    legacy_staff_id = data.get("legacy_staff_id") or legacy.get("legacy_staff_id")
    if str(legacy_staff_id or "").strip():
        tokens.add(f"legacy_staff_id:{legacy_staff_id}")
    return tokens


def duplicate_groups(records: list[BusinessRecord]) -> list[list[BusinessRecord]]:
    remaining = {record.id: record for record in records}
    groups: list[list[BusinessRecord]] = []
    while remaining:
        _, seed = remaining.popitem()
        group = [seed]
        tokens = identity_tokens(seed)
        changed = True
        while changed:
            changed = False
            for record_id, record in list(remaining.items()):
                record_tokens = identity_tokens(record)
                if tokens and tokens.intersection(record_tokens):
                    group.append(record)
                    tokens.update(record_tokens)
                    del remaining[record_id]
                    changed = True
        if len(group) > 1:
            groups.append(sorted(group, key=lambda item: item.id))
    return groups


async def canonical_record(group: list[BusinessRecord], db) -> BusinessRecord:
    ranked: list[tuple[tuple[int, int, int], BusinessRecord]] = []
    for record in group:
        child_count = 0
        for model, condition in (
            (HrSubrecord, HrSubrecord.employee_id == record.id),
            (FileAttachment, FileAttachment.record_id == record.id),
            (WorkflowEvent, WorkflowEvent.record_id == record.id),
        ):
            child_count += int((await db.scalar(select(func.count()).select_from(model).where(condition))) or 0)
        legacy = (record.data or {}).get("legacy_hr_identity")
        legacy_weight = sum(1 for value in legacy.values() if value is not None and value != "") if isinstance(legacy, dict) else 0
        ranked.append(((child_count, legacy_weight, -int(record.id)), record))
    return max(ranked, key=lambda item: item[0])[1]


def merged_employee_data(canonical: BusinessRecord, duplicates: list[BusinessRecord], user: User | None) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    merged_legacy: dict[str, Any] = {}
    for record in reversed(duplicates):
        data = dict(record.data or {})
        legacy = data.pop("legacy_hr_identity", None)
        for key, value in data.items():
            if value is not None and value != "" and value != [] and value != {}:
                merged.setdefault(key, value)
        if isinstance(legacy, dict):
            for key, value in legacy.items():
                if value is not None and value != "":
                    merged_legacy.setdefault(key, value)
    canonical_data = dict(canonical.data or {})
    canonical_legacy = canonical_data.pop("legacy_hr_identity", None)
    merged.update(canonical_data)
    if isinstance(canonical_legacy, dict):
        merged_legacy.update(canonical_legacy)
    if merged_legacy:
        merged["legacy_hr_identity"] = merged_legacy
        merged["legacy_staff_id"] = merged_legacy.get("legacy_staff_id") or merged.get("legacy_staff_id")
    if user:
        merged.update({
            "username": user.username,
            "system_user_id": user.id,
            "role": user.role,
            "is_active": user.is_active,
        })
    return merged


async def repair_session(
    db,
    *,
    apply: bool,
    canonical_ids: set[int] | None = None,
    expected_tokens: set[str] | None = None,
) -> dict[str, Any]:
    records = list((await db.scalars(
        select(BusinessRecord).where(BusinessRecord.module == "hr").order_by(BusinessRecord.id)
    )).all())
    all_groups = duplicate_groups(records)
    selected_groups: list[tuple[BusinessRecord, list[BusinessRecord]]] = []
    for group in all_groups:
        canonical = await canonical_record(group, db)
        if canonical_ids and canonical.id not in canonical_ids:
            continue
        tokens = set().union(*(identity_tokens(record) for record in group))
        if expected_tokens and not expected_tokens.issubset(tokens):
            continue
        selected_groups.append((canonical, group))
    if apply and canonical_ids and len(selected_groups) != len(canonical_ids):
        selected_ids = {canonical.id for canonical, _ in selected_groups}
        missing = sorted(canonical_ids - selected_ids)
        raise RuntimeError(f"Target duplicate identity group not found or identity tokens changed: {missing}")
    plans: list[dict[str, Any]] = []
    repaired = 0
    deleted = 0
    for canonical, group in selected_groups:
        duplicates = [record for record in group if record.id != canonical.id]
        canonical_data = canonical.data or {}
        user_id = canonical_data.get("system_user_id")
        username = str(canonical_data.get("username") or canonical.owner or "").strip().lower()
        user = await db.get(User, int(user_id)) if str(user_id or "").isdigit() else None
        if not user and username:
            user = await db.scalar(select(User).where(User.username == username))
        legacy = canonical_data.get("legacy_hr_identity") if isinstance(canonical_data.get("legacy_hr_identity"), dict) else {}
        desired_employee_no = str(legacy.get("legacy_staff_no") or canonical_data.get("legacy_staff_no") or "").strip()
        plan = {
            "identity_tokens": sorted(set().union(*(identity_tokens(record) for record in group))),
            "canonical_id": canonical.id,
            "canonical_employee_no": canonical.serial_no,
            "duplicate_ids": [record.id for record in duplicates],
            "duplicate_employee_nos": [record.serial_no for record in duplicates],
            "desired_employee_no": desired_employee_no,
            "user_id": user.id if user else None,
            "username": user.username if user else username,
        }
        plans.append(plan)
        if not apply:
            continue

        canonical.data = merged_employee_data(canonical, duplicates, user)
        if user:
            canonical.title = user.display_name or canonical.title
            canonical.owner = user.username
            canonical.department = user.department or canonical.department
            canonical.status = "在职" if user.is_active else "停用"
        for duplicate in duplicates:
            await db.execute(update(HrSubrecord).where(HrSubrecord.employee_id == duplicate.id).values(employee_id=canonical.id))
            await db.execute(update(FileAttachment).where(FileAttachment.record_id == duplicate.id).values(record_id=canonical.id))
            await db.execute(update(WorkflowEvent).where(WorkflowEvent.record_id == duplicate.id).values(record_id=canonical.id))
            await db.delete(duplicate)
        await db.flush()
        if desired_employee_no and desired_employee_no != canonical.serial_no:
            conflict = await db.scalar(select(BusinessRecord.id).where(
                BusinessRecord.serial_no == desired_employee_no,
                BusinessRecord.id != canonical.id,
            ))
            if not conflict:
                canonical.serial_no = desired_employee_no
        db.add(WorkflowEvent(
            record_id=canonical.id,
            action="合并重复员工档案",
            from_status=canonical.status,
            to_status=canonical.status,
            operator="system",
            comment=f"保留员工档案#{canonical.id}；删除重复档案：{','.join(str(record.id) for record in duplicates)}",
        ))
        repaired += 1
        deleted += len(duplicates)

    if apply:
        await db.commit()
    else:
        await db.rollback()
    return {
        "mode": "apply" if apply else "audit",
        "employees_scanned": len(records),
        "duplicate_groups": len(all_groups),
        "selected_groups": len(selected_groups),
        "groups_repaired": repaired,
        "duplicates_deleted": deleted,
        "plans": plans,
    }


async def run(
    *,
    apply: bool,
    backup_confirmed: bool,
    canonical_ids: set[int] | None = None,
    expected_tokens: set[str] | None = None,
) -> dict[str, Any]:
    if apply and not backup_confirmed:
        raise RuntimeError("--apply requires --backup-confirmed")
    async with SessionLocal() as db:
        return await repair_session(
            db,
            apply=apply,
            canonical_ids=canonical_ids,
            expected_tokens=expected_tokens,
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-confirmed", action="store_true")
    parser.add_argument("--canonical-id", action="append", type=int, default=[])
    parser.add_argument("--expected-token", action="append", default=[])
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(
        apply=args.apply,
        backup_confirmed=args.backup_confirmed,
        canonical_ids=set(args.canonical_id) or None,
        expected_tokens={str(token).strip().lower() for token in args.expected_token if str(token).strip()} or None,
    )), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
