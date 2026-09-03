"""Export and idempotently migrate complete HR data from the 8091 system.

The exported payload contains legacy plaintext passwords and is therefore a
short-lived release artifact. Never commit it. The import stores only a modern
password hash and emits counts without secret values.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base, SessionLocal, engine
from app.models import BusinessRecord, Department, HrSubrecord, User
from app.security import hash_password


SOURCE = "8091-local-PRD_CRM_GD_20200211-complete-hr"
TRUE_VALUES = {"1", "T", "TRUE", "Y", "YES"}


def clean(value: Any, limit: int | None = None) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text[:limit] if limit else text


def legacy_bool(value: Any) -> bool:
    return clean(value).upper() in TRUE_VALUES


def iso_date(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, (date, datetime)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    text = clean(value)
    return text[:10] if re.fullmatch(r"\d{4}-\d{2}-\d{2}.*", text) else text


def number(value: Any) -> float:
    return float(value or 0)


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def export_payload(connection_string: str, output: Path) -> dict[str, int]:
    try:
        import pyodbc
    except ImportError as exc:  # pragma: no cover - only used on export workstation
        raise RuntimeError("Export requires pyodbc on the workstation") from exc

    queries = {
        "departments": """
            SELECT DepartmentId, ParentDepartmentId, DepartmentCode, DepartmentName,
                   CompanyId, IsNull(ChangeTime, CreateTime) AS UpdatedAt
            FROM HR_Department ORDER BY DepartmentId
        """,
        "staff": """
            SELECT StaffId, StaffGuid, StaffNo, StaffName, StaffChName, DepartmentId,
                   Company, JobTitle, JobLevel, Email, MobilePhone, OfficePhone,
                   EntryDate, ResignationDate, IsActived, JobStatus, IsAdmin, IsManager,
                   Password, OrgPassword, CreateTime, ChangeTime
            FROM HR_Staff ORDER BY StaffId
        """,
        "performances": """
            SELECT SettingId, StaffName, Salary, AyRate, PgRate, KtRate, TcRate, WsRate,
                   AyFixed, PgFixed, KtFixed, TcFixed, WsFixed, AnnualFrom, AnnualEnd,
                   IsActived, CreateUser, CreateTime, ChangeUser, ChangeTime
            FROM HR_Staff_Performance ORDER BY SettingId
        """,
    }
    payload: dict[str, Any] = {"source": SOURCE}
    with pyodbc.connect(connection_string) as connection:
        for key, query in queries.items():
            cursor = connection.cursor()
            rows = cursor.execute(query).fetchall()
            columns = [column[0] for column in cursor.description]
            payload[key] = [
                {column: _json_value(value) for column, value in zip(columns, row)}
                for row in rows
            ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return {key: len(payload[key]) for key in queries}


def _employee_status(row: dict[str, Any]) -> str:
    if not legacy_bool(row.get("JobStatus")):
        return "离职"
    return "在职" if legacy_bool(row.get("IsActived")) else "停用"


def _password_hash(row: dict[str, Any], current: str = "") -> str:
    original = str(row.get("OrgPassword") or "")
    if original:
        return hash_password(original)
    digest = clean(row.get("Password")).lower()
    if re.fullmatch(r"[0-9a-f]{32}", digest):
        return f"legacy-md5${digest}"
    if current:
        return current
    raise ValueError(f"Legacy staff {clean(row.get('StaffName')) or row.get('StaffId')} has no usable password")


async def migrate_payload(db, payload: dict[str, Any]) -> dict[str, dict[str, int]]:
    if payload.get("source") not in {None, "", SOURCE}:
        raise ValueError("Unexpected legacy HR payload source")
    departments = list(payload.get("departments") or [])
    staff_rows = list(payload.get("staff") or [])
    performance_rows = list(payload.get("performances") or [])
    if not departments or not staff_rows:
        raise ValueError("Legacy HR payload must include departments and staff")

    result = {
        "departments": {"created": 0, "updated": 0},
        "users": {"created": 0, "updated": 0},
        "employees": {"created": 0, "updated": 0},
        "performances": {"created": 0, "updated": 0},
    }

    existing_departments = list((await db.scalars(select(Department))).all())
    departments_by_name = {clean(item.name): item for item in existing_departments}
    departments_by_code = {clean(item.code): item for item in existing_departments}
    legacy_department_names: dict[str, str] = {}
    for index, row in enumerate(departments, start=1):
        legacy_id = clean(row.get("DepartmentId"))
        name = clean(row.get("DepartmentName"), 128)
        if not legacy_id or not name:
            raise ValueError("Legacy department is missing DepartmentId or DepartmentName")
        code = clean(row.get("DepartmentCode"), 64) or f"LEGACY-HR-{legacy_id}"
        item = departments_by_name.get(name) or departments_by_code.get(code)
        if item is None:
            item = Department(
                code=code, name=name, sort_order=index, is_active=True,
                created_by="legacy-hr-migration", updated_by="legacy-hr-migration",
            )
            db.add(item)
            result["departments"]["created"] += 1
            departments_by_name[name] = item
            departments_by_code[code] = item
        else:
            item.name = name
            item.is_active = True
            item.updated_by = "legacy-hr-migration"
            result["departments"]["updated"] += 1
        legacy_department_names[legacy_id] = name
    await db.flush()

    users = list((await db.scalars(select(User))).all())
    users_by_username = {clean(item.username).lower(): item for item in users}
    employees = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "hr"))).all())
    employees_by_username = {
        clean((item.data or {}).get("username") or item.owner).lower(): item
        for item in employees if clean((item.data or {}).get("username") or item.owner)
    }
    employees_by_no = {clean(item.serial_no): item for item in employees}
    employee_no_counts = Counter(clean(row.get("StaffNo"), 64) for row in staff_rows)

    employee_by_username: dict[str, BusinessRecord] = {}
    for row in staff_rows:
        username = clean(row.get("StaffName"), 64).lower()
        employee_no = clean(row.get("StaffNo"), 64)
        serial_no = employee_no
        existing_for_username = employees_by_username.get(username)
        if employee_no_counts[employee_no] > 1:
            # The legacy database contains duplicate StaffNo values. Preserve
            # the business-facing original in data and make only the technical
            # record key unique and traceable.
            serial_no = existing_for_username.serial_no if existing_for_username else f"{employee_no}-LEGACY-{clean(row.get('StaffId'))}"
        display_name = clean(row.get("StaffChName"), 64)
        department_id = clean(row.get("DepartmentId"))
        department_name = legacy_department_names.get(department_id)
        if not username or not employee_no or not display_name or not department_name:
            raise ValueError(f"Legacy staff relation is incomplete: {username or employee_no or row.get('StaffId')}")
        active = legacy_bool(row.get("IsActived"))
        status = _employee_status(row)
        user = users_by_username.get(username)
        profile_update = {
            "migration_source": SOURCE,
            "legacy_staff_id": row.get("StaffId"),
            "legacy_staff_guid": clean(row.get("StaffGuid")),
            "legacy_department_id": row.get("DepartmentId"),
            "employee_no": employee_no,
            "company": clean(row.get("Company"), 255) or "上海申浩律师事务所",
            "position": clean(row.get("JobTitle"), 128),
            "job_level": clean(row.get("JobLevel"), 64),
            "email": clean(row.get("Email"), 255),
            "mobile": clean(row.get("MobilePhone"), 64),
            "office_phone": clean(row.get("OfficePhone"), 64),
            "joined_at": iso_date(row.get("EntryDate")),
            "left_at": iso_date(row.get("ResignationDate")),
            "account_type": "员工账号",
        }
        if user is None:
            user = User(
                username=username, display_name=display_name, department=department_name,
                password_hash=_password_hash(row), role="user", role_ids=["user"],
                profile=profile_update, is_active=active, must_change_password=False,
            )
            db.add(user)
            users_by_username[username] = user
            result["users"]["created"] += 1
        else:
            user.display_name = display_name
            user.department = department_name
            user.profile = {**(user.profile or {}), **profile_update}
            user.password_hash = _password_hash(row, user.password_hash)
            user.is_active = active
            user.must_change_password = False
            user.failed_login_attempts = 0
            user.locked_until = None
            result["users"]["updated"] += 1

        employee = existing_for_username or employees_by_no.get(serial_no)
        if employee and clean((employee.data or {}).get("username") or employee.owner).lower() not in {"", username}:
            raise ValueError(f"Employee number {employee_no} belongs to another username")
        employee_data = {
            **((employee.data or {}) if employee else {}),
            **profile_update,
            "username": username,
            "role": user.role,
            "is_active": active,
            "legacy_is_actived": clean(row.get("IsActived")),
            "legacy_job_status": clean(row.get("JobStatus")),
        }
        if employee is None:
            employee = BusinessRecord(
                module="hr", serial_no=serial_no, title=display_name,
                customer=profile_update["company"], status=status, owner=username,
                department=department_name, description="8091旧系统完整员工迁移",
                data=employee_data,
            )
            db.add(employee)
            employees_by_username[username] = employee
            employees_by_no[serial_no] = employee
            result["employees"]["created"] += 1
        else:
            employee.title = display_name
            employee.customer = profile_update["company"]
            employee.status = status
            employee.owner = username
            employee.department = department_name
            employee.data = employee_data
            result["employees"]["updated"] += 1
        employee_by_username[username] = employee
    await db.flush()

    existing_performances = list((await db.scalars(select(HrSubrecord).where(HrSubrecord.kind == "commission"))).all())
    performances_by_legacy_id = {
        clean((item.data or {}).get("legacy_setting_id")): item
        for item in existing_performances if clean((item.data or {}).get("legacy_setting_id"))
    }
    seen_setting_ids: set[str] = set()
    for row in performance_rows:
        setting_id = clean(row.get("SettingId"))
        username = clean(row.get("StaffName"), 64).lower()
        employee = employee_by_username.get(username)
        if not setting_id or setting_id in seen_setting_ids:
            raise ValueError(f"Invalid or duplicate legacy performance SettingId: {setting_id or '<empty>'}")
        if employee is None:
            raise ValueError(f"Legacy performance {setting_id} has no employee: {username}")
        seen_setting_ids.add(setting_id)
        data = {
            "migration_source": SOURCE,
            "legacy_setting_id": row.get("SettingId"),
            "legacy_is_actived": clean(row.get("IsActived")),
            "start_date": iso_date(row.get("AnnualFrom")),
            "end_date": iso_date(row.get("AnnualEnd")),
            "base_salary": number(row.get("Salary")),
            "hearing_rate": number(row.get("KtRate")),
            "hearing_fixed": number(row.get("KtFixed")),
            "document_rate": number(row.get("WsRate")),
            "document_fixed": number(row.get("WsFixed")),
            "source_rate": number(row.get("AyRate")),
            "source_fixed": number(row.get("AyFixed")),
            "investigation_rate": number(row.get("TcRate")),
            "investigation_fixed": number(row.get("TcFixed")),
            "quality_rate": number(row.get("PgRate")),
            "quality_fixed": number(row.get("PgFixed")),
        }
        item = performances_by_legacy_id.get(setting_id)
        if item is None:
            item = HrSubrecord(
                employee_id=employee.id, kind="commission", data=data,
                created_by="legacy-hr-migration", updated_by="legacy-hr-migration",
            )
            db.add(item)
            performances_by_legacy_id[setting_id] = item
            result["performances"]["created"] += 1
        else:
            item.employee_id = employee.id
            item.data = {**(item.data or {}), **data}
            item.updated_by = "legacy-hr-migration"
            result["performances"]["updated"] += 1
    await db.flush()
    return result


async def import_payload(path: Path, dry_run: bool) -> dict[str, dict[str, int]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        try:
            result = await migrate_payload(db, payload)
            if dry_run:
                await db.rollback()
            else:
                await db.commit()
            return result
        except Exception:
            await db.rollback()
            raise


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("--connection", required=True)
    export_parser.add_argument("--output", type=Path, required=True)
    import_parser = subparsers.add_parser("import")
    import_parser.add_argument("--payload", type=Path, required=True)
    import_parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.command == "export":
        print(json.dumps(export_payload(args.connection, args.output), ensure_ascii=False))
    else:
        print(json.dumps(asyncio.run(import_payload(args.payload, args.dry_run)), ensure_ascii=False))


if __name__ == "__main__":
    main()
