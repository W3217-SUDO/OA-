"""Audit or repair migrated staff identities and case-person relations.

Dry-run is the default. Applying requires ``--apply --backup-confirmed`` and
creates only uniquely identified login accounts with random unknown passwords.
Administrators must reset those passwords before the first login.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import secrets
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.models import BusinessRecord, User
from app.security import hash_password


SPLIT_PATTERN = re.compile(r"[、,，;；\n]+")
USERNAME_PATTERN = re.compile(r"[a-z0-9._-]{2,64}")
DISABLED_STATUSES = {"停用"}


@dataclass(frozen=True)
class PersonIdentity:
    username: str
    display_name: str
    department: str
    is_active: bool
    employee_id: int | None = None
    user_id: int | None = None


CASE_PERSON_FIELDS = (
    ("handling_lawyer_usernames", "handling_lawyers", "CaseLawyer", "CaseLawyerName", True, True),
    ("assistant_username", "assistant", "CaseAssistant", "CaseAssistantName", False, True),
    ("investigator_username", "investigator", "Investigator", "InvestigatorName", False, False),
    ("business_owner_username", "business_owner", "BusinessOwner", "BusinessOwner", False, False),
    ("source_person_username", "source_person", "CaseOriginPeople", "CaseOriginPeople", False, False),
    ("hearing_lawyer_username", "hearing_lawyer", "CourtLawyer", "CourtLawyerName", False, False),
)


def values(value: Any) -> list[str]:
    raw = value if isinstance(value, list) else SPLIT_PATTERN.split(str(value or ""))
    return [str(item or "").strip() for item in raw if str(item or "").strip()]


def employee_username(employee: BusinessRecord) -> str:
    return str((employee.data or {}).get("username") or employee.owner or "").strip().lower()


def is_employee_account(employee: BusinessRecord) -> bool:
    return str((employee.data or {}).get("account_type") or "员工账号").strip() == "员工账号"


def is_migrated_employee(employee: BusinessRecord) -> bool:
    return isinstance((employee.data or {}).get("legacy_hr_identity"), dict)


def is_migrated_case(record: BusinessRecord) -> bool:
    data = record.data or {}
    return bool(
        data.get("migration_source")
        or data.get("legacy_case_id")
        or isinstance(data.get("legacy_record"), dict)
        or isinstance(data.get("legacy_participants"), list)
    )


def build_identity_plan(users: list[User], employees: list[BusinessRecord]) -> dict[str, Any]:
    users_by_username = {user.username.strip().lower(): user for user in users}
    grouped: dict[str, list[BusinessRecord]] = defaultdict(list)
    for employee in employees:
        username = employee_username(employee)
        if is_employee_account(employee) and username:
            grouped[username].append(employee)

    creates: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    identities: dict[str, PersonIdentity] = {
        username: PersonIdentity(
            username=username,
            display_name=str(user.display_name or "").strip(),
            department=str(user.department or "").strip(),
            is_active=bool(user.is_active),
            user_id=user.id,
        )
        for username, user in users_by_username.items()
    }
    for username, rows in grouped.items():
        if len(rows) != 1:
            issues.append({"kind": "duplicate_employee_username", "username": username, "employee_ids": [row.id for row in rows]})
            continue
        employee = rows[0]
        display_name = str(employee.title or "").strip()
        if not USERNAME_PATTERN.fullmatch(username) or username in {"admin", "system"} or not display_name:
            issues.append({"kind": "invalid_employee_identity", "username": username, "employee_id": employee.id, "display_name": display_name})
            continue
        existing = users_by_username.get(username)
        if existing:
            identities[username] = PersonIdentity(
                username=username,
                display_name=str(existing.display_name or display_name).strip(),
                department=str(existing.department or employee.department or "").strip(),
                is_active=bool(existing.is_active),
                employee_id=employee.id,
                user_id=existing.id,
            )
            continue
        if not is_migrated_employee(employee):
            issues.append({"kind": "missing_non_migrated_login", "username": username, "employee_id": employee.id})
            continue
        active = bool((employee.data or {}).get("is_active", True)) and employee.status not in DISABLED_STATUSES
        identity = PersonIdentity(
            username=username,
            display_name=display_name,
            department=str(employee.department or "").strip(),
            is_active=active,
            employee_id=employee.id,
        )
        identities[username] = identity
        creates.append({"identity": identity, "employee": employee})

    display_groups: dict[str, list[PersonIdentity]] = defaultdict(list)
    for identity in identities.values():
        if identity.display_name:
            display_groups[identity.display_name.casefold()].append(identity)
    return {"identities": identities, "display_groups": display_groups, "creates": creates, "issues": issues}


def build_historical_name_map(
    employees: list[BusinessRecord],
    cases: list[BusinessRecord],
) -> dict[str, str]:
    candidates: dict[str, set[str]] = defaultdict(set)

    def remember(account_value: Any, display_value: Any) -> None:
        account = str(account_value or "").strip().lower()
        display = str(display_value or "").strip()
        if account and display and re.search(r"[\u3400-\u9fff]", display):
            candidates[account].add(display)

    for employee in employees:
        remember(employee_username(employee), employee.title)
    for record in cases:
        data = record.data or {}
        legacy = data.get("legacy_record") if isinstance(data.get("legacy_record"), dict) else {}
        for username_key, display_key, legacy_username_key, legacy_display_key, *_ in CASE_PERSON_FIELDS:
            accounts = values(data.get(username_key)) or values(legacy.get(legacy_username_key))
            displays = values(data.get(display_key)) or values(legacy.get(legacy_display_key))
            for index in range(min(len(accounts), len(displays))):
                remember(accounts[index], displays[index])
        participants = data.get("legacy_participants")
        if isinstance(participants, list):
            for participant in participants:
                if not isinstance(participant, dict):
                    continue
                remember(
                    participant.get("staff_name") or participant.get("username") or participant.get("account"),
                    participant.get("display_name")
                    or participant.get("staff_ch_name")
                    or participant.get("legacy_staff_ch_name"),
                )
    result = {account: next(iter(names)) for account, names in candidates.items() if len(names) == 1}
    result.setdefault("system", "系统")
    return result


def resolve_identity(
    account_value: str,
    display_value: str,
    identities: dict[str, PersonIdentity],
    display_groups: dict[str, list[PersonIdentity]],
) -> tuple[str, PersonIdentity | None]:
    account = str(account_value or "").strip()
    display = str(display_value or "").strip()
    if account and account.lower() in identities:
        return "matched", identities[account.lower()]
    for candidate in (display, account):
        if candidate and candidate.lower() in identities:
            return "matched", identities[candidate.lower()]
        matches = display_groups.get(candidate.casefold(), []) if candidate else []
        if len(matches) == 1:
            return "matched", matches[0]
        if len(matches) > 1:
            return "ambiguous", None
    return ("missing" if account or display else "empty"), None


def plan_case_repair(
    record: BusinessRecord,
    identities: dict[str, PersonIdentity],
    display_groups: dict[str, list[PersonIdentity]],
    historical_names: dict[str, str] | None = None,
) -> dict[str, Any]:
    data = dict(record.data or {})
    historical_names = historical_names or {}
    legacy = data.get("legacy_record") if isinstance(data.get("legacy_record"), dict) else {}
    updates: dict[str, Any] = {}
    issues: list[dict[str, str]] = []
    team_usernames = values(data.get("case_team_usernames"))

    for username_key, display_key, legacy_username_key, legacy_display_key, multiple, team_role in CASE_PERSON_FIELDS:
        accounts = values(data.get(username_key)) or values(legacy.get(legacy_username_key))
        displays = values(data.get(display_key)) or values(legacy.get(legacy_display_key))
        size = max(len(accounts), len(displays))
        if not size:
            continue
        resolved: list[PersonIdentity] = []
        display_only_names: list[str] = []
        failed = False
        for index in range(size):
            account = accounts[index] if index < len(accounts) else ""
            display = displays[index] if index < len(displays) else ""
            status, identity = resolve_identity(account, display, identities, display_groups)
            if status == "matched" and identity:
                resolved.append(identity)
                display_only_names.append(identity.display_name)
            else:
                failed = True
                historical_name = historical_names.get(account.lower()) if account else ""
                if not historical_name and account:
                    base_account = re.sub(r"\d+$", "", account.lower())
                    historical_name = historical_names.get(base_account, "") if base_account != account.lower() else ""
                display_only_names.append(
                    historical_name
                    or (display if re.search(r"[\u3400-\u9fff]", display) else "")
                )
                issues.append({
                    "field": display_key,
                    "account": account,
                    "display": display,
                    "status": "historical_display_only" if display_only_names[-1] and status == "missing" else status,
                })
        if failed:
            if display_only_names and all(display_only_names):
                historical_value: Any = list(dict.fromkeys(display_only_names)) if multiple else display_only_names[0]
                if data.get(display_key) != historical_value:
                    updates[display_key] = historical_value
            continue
        if not resolved:
            continue
        usernames = list(dict.fromkeys(identity.username for identity in resolved))
        names = list(dict.fromkeys(identity.display_name for identity in resolved))
        expected_usernames: Any = usernames if multiple else usernames[0]
        expected_names: Any = names if multiple else names[0]
        if data.get(username_key) != expected_usernames:
            updates[username_key] = expected_usernames
        if data.get(display_key) != expected_names:
            updates[display_key] = expected_names
        if team_role:
            team_usernames.extend(usernames)

    legacy_participants = data.get("legacy_participants")
    if isinstance(legacy_participants, list) and legacy_participants:
        participant_names: list[str] = []
        for participant in legacy_participants:
            if not isinstance(participant, dict):
                continue
            account = str(
                participant.get("staff_name")
                or participant.get("username")
                or participant.get("account")
                or ""
            ).strip()
            display = str(
                participant.get("display_name")
                or participant.get("staff_ch_name")
                or participant.get("legacy_staff_ch_name")
                or ""
            ).strip()
            status, identity = resolve_identity(account, display, identities, display_groups)
            if status == "matched" and identity:
                participant_names.append(identity.display_name)
                team_usernames.append(identity.username)
            elif account.lower() in historical_names:
                participant_names.append(historical_names[account.lower()])
                issues.append({"field": "legacy_participants", "account": account, "display": historical_names[account.lower()], "status": "historical_display_only"})
            elif re.sub(r"\d+$", "", account.lower()) in historical_names:
                participant_names.append(historical_names[re.sub(r"\d+$", "", account.lower())])
                issues.append({"field": "legacy_participants", "account": account, "display": participant_names[-1], "status": "historical_display_only"})
            elif display and re.search(r"[\u3400-\u9fff]", display):
                participant_names.append(display)
            else:
                issues.append({"field": "legacy_participants", "account": account, "display": display, "status": status})
        normalized_names = list(dict.fromkeys(name for name in participant_names if name))
        if normalized_names and data.get("legacy_participant_display_names") != normalized_names:
            updates["legacy_participant_display_names"] = normalized_names

    owner_status, owner_identity = resolve_identity(str(record.owner or ""), "", identities, display_groups)
    owner_update = owner_identity.username if owner_status == "matched" and owner_identity and record.owner != owner_identity.username else ""
    normalized_team = list(dict.fromkeys(value.lower() for value in team_usernames if value))
    if normalized_team != values(data.get("case_team_usernames")):
        updates["case_team_usernames"] = normalized_team
    return {"updates": updates, "owner": owner_update, "issues": issues}


async def audit_or_apply(*, apply: bool, backup_confirmed: bool, limit: int) -> dict[str, Any]:
    if apply and not backup_confirmed:
        raise RuntimeError("--apply requires --backup-confirmed")
    async with SessionLocal() as db:
        users = list((await db.scalars(select(User).order_by(User.id))).all())
        employees = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "hr").order_by(BusinessRecord.id))).all())
        all_cases = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "case").order_by(BusinessRecord.id))).all())
        cases = [case for case in all_cases if is_migrated_case(case)]
        identity_plan = build_identity_plan(users, employees)
        identities = identity_plan["identities"]
        display_groups = identity_plan["display_groups"]
        historical_names = build_historical_name_map(employees, cases)
        case_plans: list[tuple[BusinessRecord, dict[str, Any]]] = []
        issue_counts: Counter[str] = Counter()
        issue_field_counts: Counter[str] = Counter()
        unresolved_accounts: Counter[str] = Counter()
        unresolved_by_field: Counter[str] = Counter()
        samples: list[dict[str, Any]] = []
        for case in cases:
            plan = plan_case_repair(case, identities, display_groups, historical_names)
            for issue in plan["issues"]:
                issue_counts[issue["status"]] += 1
                issue_field_counts[f'{issue["field"]}:{issue["status"]}'] += 1
                unresolved = str(issue.get("account") or issue.get("display") or "").strip()
                if unresolved:
                    unresolved_accounts[unresolved] += 1
                    unresolved_by_field[f'{issue["field"]}:{unresolved}'] += 1
            if plan["updates"] or plan["owner"]:
                case_plans.append((case, plan))
            if (plan["updates"] or plan["owner"] or plan["issues"]) and len(samples) < limit:
                samples.append({"case_no": case.serial_no, **plan})

        created_users = 0
        if apply:
            for item in identity_plan["creates"]:
                identity: PersonIdentity = item["identity"]
                employee: BusinessRecord = item["employee"]
                profile = {**(employee.data or {}), "employee_no": employee.serial_no, "account_type": "员工账号"}
                user = User(
                    username=identity.username,
                    display_name=identity.display_name,
                    department=identity.department,
                    password_hash=hash_password(secrets.token_urlsafe(48)),
                    role="user",
                    role_ids=["user"],
                    profile=profile,
                    is_active=identity.is_active,
                    must_change_password=True,
                )
                db.add(user)
                await db.flush()
                employee.data = {**(employee.data or {}), "system_user_id": user.id, "is_active": user.is_active, "role": user.role}
                created_users += 1
            for case, plan in case_plans:
                if plan["updates"]:
                    case.data = {**(case.data or {}), **plan["updates"]}
                if plan["owner"]:
                    case.owner = plan["owner"]
            await db.commit()
        else:
            await db.rollback()

    return {
        "mode": "apply" if apply else "audit",
        "users_before": len(users),
        "employees_scanned": len(employees),
        "cases_scanned": len(cases),
        "missing_login_users": len(identity_plan["creates"]),
        "created_users": created_users,
        "identity_issues": identity_plan["issues"],
        "historical_name_aliases": historical_names,
        "cases_with_repairs": len(case_plans),
        "case_issue_counts": dict(issue_counts),
        "case_issue_field_counts": dict(issue_field_counts),
        "unresolved_accounts": dict(unresolved_accounts.most_common()),
        "unresolved_by_field": dict(unresolved_by_field.most_common()),
        "samples": samples,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-confirmed", action="store_true")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    result = asyncio.run(audit_or_apply(apply=args.apply, backup_confirmed=args.backup_confirmed, limit=max(args.limit, 0)))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
