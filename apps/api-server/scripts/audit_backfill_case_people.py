"""Audit or idempotently backfill historical case-person account references.

The default mode is read-only. ``--apply`` updates only ``business_records.data``
for uniquely resolved active users; ambiguous or missing people are reported and
never guessed. This script deliberately does not import ``app.main`` or alter
the legacy projection tables, so production API integration remains a separate
reviewable change.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.models import BusinessRecord, LegacyCase, User


PERSON_FIELDS = (
    ("handling_lawyer_usernames", "handling_lawyers", "CaseLawyer", "CaseLawyerName", True),
    ("assistant_username", "assistant", "CaseAssistant", "CaseAssistantName", False),
    ("investigator_username", "investigator", "Investigator", "InvestigatorName", False),
    ("business_owner_username", "business_owner", "BusinessOwner", "BusinessOwner", False),
)
SPLIT_PATTERN = re.compile(r"[、,，;；\n]+")


def values(value: Any) -> list[str]:
    raw = value if isinstance(value, list) else SPLIT_PATTERN.split(str(value or ""))
    return [str(item or "").strip() for item in raw if str(item or "").strip()]


def display_candidate(value: str) -> str:
    return re.sub(r"（[^（）]*）$", "", value).strip()


def resolve_person(value: str, users: list[dict[str, str]]) -> tuple[str, dict[str, str] | None]:
    normalized = str(value or "").strip()
    if not normalized:
        return "empty", None
    by_username = [user for user in users if user["username"] == normalized]
    if len(by_username) == 1:
        return "matched", by_username[0]
    candidate = display_candidate(normalized)
    by_name = [user for user in users if user["display_name"] == candidate]
    if len(by_name) == 1:
        return "matched", by_name[0]
    return ("ambiguous" if len(by_name) > 1 else "missing"), None


def plan_case_person_backfill(record: dict[str, Any], legacy: dict[str, Any], users: list[dict[str, str]]) -> dict[str, Any]:
    data = dict(record.get("data") or {})
    updates: dict[str, Any] = {}
    issues: list[dict[str, str]] = []
    matched = 0
    for username_key, display_key, legacy_username_key, legacy_display_key, multiple in PERSON_FIELDS:
        input_values = values(data.get(username_key)) or values(data.get(display_key))
        if not input_values:
            input_values = values(legacy.get(legacy_username_key)) or values(legacy.get(legacy_display_key))
        resolved: list[dict[str, str]] = []
        field_has_unresolved_value = False
        for raw_value in input_values:
            status, user = resolve_person(raw_value, users)
            if status == "matched" and user:
                resolved.append(user)
                matched += 1
            elif status != "empty":
                field_has_unresolved_value = True
                issues.append({"field": display_key, "value": raw_value, "status": status})
        # Do not partially overwrite a multi-person legacy field. A missing or
        # ambiguous member must remain visible until a human resolves it.
        if not resolved or field_has_unresolved_value:
            continue
        usernames = list(dict.fromkeys(item["username"] for item in resolved))
        displays = list(dict.fromkeys(item["display_name"] for item in resolved))
        if multiple:
            if data.get(username_key) != usernames:
                updates[username_key] = usernames
            if data.get(display_key) != displays:
                updates[display_key] = displays
        else:
            if data.get(username_key) != usernames[0]:
                updates[username_key] = usernames[0]
            if data.get(display_key) != displays[0]:
                updates[display_key] = displays[0]
    return {"updates": updates, "issues": issues, "matched": matched}


def legacy_person_data(item: LegacyCase) -> dict[str, Any]:
    fields = {field for _, _, username_field, display_field, _ in PERSON_FIELDS for field in (username_field, display_field)}
    return {field: getattr(item, field, None) for field in fields}


async def audit_or_backfill(*, apply: bool, case_nos: list[str], limit: int) -> dict[str, Any]:
    async with SessionLocal() as db:
        users = [
            {"username": item.username, "display_name": item.display_name}
            for item in (await db.scalars(select(User).where(User.is_active.is_(True)))).all()
        ]
        statement = select(BusinessRecord).where(BusinessRecord.module == "case").order_by(BusinessRecord.id)
        if case_nos:
            statement = statement.where(BusinessRecord.serial_no.in_(case_nos))
        records = list((await db.scalars(statement)).all()
        )
        legacy_rows = list(
            (await db.scalars(select(LegacyCase).where(LegacyCase.CaseNo.in_([item.serial_no for item in records])))).all()
        ) if records else []
        legacy_by_no = {str(item.CaseNo or ""): legacy_person_data(item) for item in legacy_rows}
        summary: Counter[str] = Counter()
        samples: list[dict[str, Any]] = []
        changed = 0
        for record in records:
            plan = plan_case_person_backfill({"data": record.data}, legacy_by_no.get(record.serial_no, {}), users)
            summary["matched"] += plan["matched"]
            summary["ambiguous"] += sum(item["status"] == "ambiguous" for item in plan["issues"])
            summary["missing"] += sum(item["status"] == "missing" for item in plan["issues"])
            if plan["updates"]:
                changed += 1
                if apply:
                    record.data = {**(record.data or {}), **plan["updates"]}
            if (plan["updates"] or plan["issues"]) and len(samples) < limit:
                samples.append({"case_no": record.serial_no, **plan})
        if apply:
            await db.commit()
        else:
            await db.rollback()
    return {
        "mode": "apply" if apply else "audit",
        "cases_scanned": len(records),
        "cases_with_unique_updates": changed,
        "summary": dict(summary),
        "samples": samples,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Commit only uniquely resolved account/display mappings")
    parser.add_argument("--case-no", action="append", default=[], help="Limit to a case number; repeatable")
    parser.add_argument("--limit", type=int, default=100, help="Maximum changed/issue samples in JSON output")
    args = parser.parse_args()
    result = asyncio.run(audit_or_backfill(apply=args.apply, case_nos=args.case_no, limit=max(args.limit, 0)))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
