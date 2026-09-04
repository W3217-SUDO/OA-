#!/usr/bin/env python3
"""Safely project legacy IPR_User identities into new-system employees.

The SQL Server source is opened read-only.  Password columns are deliberately
never selected.  This is dry-run by default; --apply requires an automatic,
checksummed SQLite backup and writes a row-level ledger for every source user.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import shutil
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from pwdlib import PasswordHash


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET_DB = ROOT / "apps" / "api-server" / "legal_platform.db"
DEFAULT_OUTPUT_DIR = ROOT / "docs" / "generated" / "full-parity-inventory" / "migrations"
ACTOR = "legacy_ipr_user_identity_migration"
SOURCE = "PRD_CRM_GD_20200211 dbo.IPR_User (Trusted_Connection, read-only)"
LEGACY_CODE_EVIDENCE = [
    {
        "path": "GD.CRM.WEB.VIP/Areas/IPR/Views/IprBase/UserList.cshtml",
        "purpose": "IPR selector persists UserName and renders the Chinese staff name.",
    },
    {
        "path": "GD.CRM.WEB.VIP/Controllers/CheckUserLogin.cs",
        "purpose": "IPR session identity is sourced by legacy account identity; old passwords are incompatible and excluded.",
    },
    {
        "path": "GD.CRM.WEB.VIP/Areas/IPR/Views/Case/PartialView/CaseFeeInform.cshtml",
        "purpose": "IPR task and fee assignment renders EmployeeName while retaining UserName as the value.",
    },
]


class MigrationError(RuntimeError):
    pass


def clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        for encoding in ("utf-8", "gb18030"):
            try:
                return value.decode(encoding).strip()
            except UnicodeDecodeError:
                pass
        raise MigrationError("legacy SQL Server returned undecodable text")
    return str(value).strip()


def key(value: Any) -> str:
    return "".join(clean(value).casefold().split())


def as_json(value: Any) -> dict[str, Any]:
    if value in (None, ""):
        return {}
    if isinstance(value, dict):
        return dict(value)
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise MigrationError("target JSON profile must be an object") from exc
    if not isinstance(parsed, dict):
        raise MigrationError("target JSON profile must be an object")
    return parsed


def iso(value: Any) -> str:
    return value.isoformat() if isinstance(value, datetime) else clean(value)


def is_codex_account(username: str, display_name: str = "") -> bool:
    return username.casefold().startswith(("codex-", "codex_")) or display_name.casefold().startswith("codex-")


@dataclass(frozen=True)
class LegacyIprUser:
    id: int
    username: str
    display_name: str
    department_id: int | None
    department_code: str
    department_name: str
    is_active: bool
    is_admin: bool
    is_department_manager: bool
    access_level: str
    email: str
    mobile: str
    office_phone: str
    company: str
    created_at: str
    updated_at: str
    roles: tuple[tuple[int, str], ...]


def read_legacy_sql_server(server: str, database: str, driver: str) -> list[LegacyIprUser]:
    """Read only documented identity fields. Password, Password1/2/3 are absent."""
    try:
        import pyodbc
    except ImportError as exc:  # pragma: no cover - machine dependency
        raise MigrationError("pyodbc is required to read the legacy SQL Server") from exc
    connection_string = (
        f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};"
        "Trusted_Connection=yes;ApplicationIntent=ReadOnly;TrustServerCertificate=yes;"
    )
    query = """
        SELECT u.UserId,u.UserName,u.EmployeeName,u.DepartmentId,u.Status,u.IsAdmin,u.IsDepartmentManager,
               u.AccessLevel,u.Email,u.MobilePhone,u.OfficePhone,u.Company,u.CreateTime,u.ChangeTime,
               d.DepartmentCode,d.DepartmentName,ur.RoleId,r.RoleName
        FROM dbo.IPR_User u
        LEFT JOIN dbo.HR_Department d ON d.DepartmentId=u.DepartmentId
        LEFT JOIN dbo.IPR_UserRole ur ON ur.UserId=u.UserId
        LEFT JOIN dbo.IPR_Role r ON r.RoleId=ur.RoleId
        ORDER BY u.UserId,ur.UserRoleId
    """
    # The query intentionally never selects legacy password columns.
    by_id: dict[int, dict[str, Any]] = {}
    with pyodbc.connect(connection_string, autocommit=True) as connection:
        cursor = connection.cursor()
        tables = {clean(row[0]) for row in cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")}
        missing = sorted({"IPR_User", "IPR_UserRole", "IPR_Role", "HR_Department"} - tables)
        if missing:
            raise MigrationError(f"legacy source tables missing: {', '.join(missing)}")
        for row in cursor.execute(query):
            user_id = int(row.UserId)
            item = by_id.setdefault(user_id, {
                "id": user_id, "username": clean(row.UserName), "display_name": clean(row.EmployeeName),
                "department_id": int(row.DepartmentId) if row.DepartmentId is not None else None,
                "department_code": clean(row.DepartmentCode), "department_name": clean(row.DepartmentName),
                "is_active": clean(row.Status) == "1", "is_admin": clean(row.IsAdmin).upper() == "T",
                "is_department_manager": clean(row.IsDepartmentManager).upper() == "T", "access_level": clean(row.AccessLevel),
                "email": clean(row.Email), "mobile": clean(row.MobilePhone), "office_phone": clean(row.OfficePhone),
                "company": clean(row.Company), "created_at": iso(row.CreateTime), "updated_at": iso(row.ChangeTime), "roles": [],
            })
            if row.RoleId is not None:
                item["roles"].append((int(row.RoleId), clean(row.RoleName)))
    return [LegacyIprUser(**{**item, "roles": tuple(item["roles"])}) for item in by_id.values()]


def _target_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}


def _require_target_schema(connection: sqlite3.Connection) -> None:
    required = {
        "users": {"id", "username", "display_name", "department", "password_hash", "role", "role_ids", "profile", "is_active", "must_change_password"},
        "departments": {"id", "code", "name", "is_active"},
        "job_roles": {"id", "code", "name", "is_active"},
        "business_records": {"id", "module", "serial_no", "title", "status", "owner", "department", "data"},
        "workflow_events": {"record_id", "action", "operator", "comment"},
    }
    tables = {str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table, columns in required.items():
        if table not in tables:
            raise MigrationError(f"target table missing: {table}")
        missing = columns - _target_columns(connection, table)
        if missing:
            raise MigrationError(f"target {table} columns missing: {', '.join(sorted(missing))}")


def _target_departments(connection: sqlite3.Connection) -> dict[str, sqlite3.Row]:
    return {key(row["code"]): row for row in connection.execute("SELECT id,code,name,is_active FROM departments")}


def _target_job_roles(connection: sqlite3.Connection) -> dict[str, list[sqlite3.Row]]:
    result: dict[str, list[sqlite3.Row]] = {}
    for row in connection.execute("SELECT id,code,name,is_active FROM job_roles WHERE is_active=1"):
        result.setdefault(key(row["name"]), []).append(row)
    return result


def _hr_records(connection: sqlite3.Connection) -> dict[str, list[sqlite3.Row]]:
    result: dict[str, list[sqlite3.Row]] = {}
    for row in connection.execute("SELECT id,serial_no,title,owner,department,status,data FROM business_records WHERE module='hr'"):
        data = as_json(row["data"])
        username = clean(data.get("username")) or clean(row["owner"])
        if username:
            result.setdefault(key(username), []).append(row)
    return result


def _legacy_profile(user: LegacyIprUser, target_job_role: sqlite3.Row | None) -> dict[str, Any]:
    roles = [{"legacy_role_id": role_id, "legacy_role_name": role_name} for role_id, role_name in user.roles]
    profile: dict[str, Any] = {
        "legacy_ipr_identity": {
            "source": SOURCE, "migrated_by": ACTOR, "legacy_ipr_user_id": user.id,
            "legacy_username": user.username, "legacy_employee_name": user.display_name,
            "legacy_department_id": user.department_id, "legacy_department_code": user.department_code,
            "legacy_department_name": user.department_name, "legacy_status": 1 if user.is_active else 0,
            "legacy_is_admin": user.is_admin, "legacy_is_department_manager": user.is_department_manager,
            "legacy_access_level": user.access_level, "legacy_roles": roles,
            "password_policy": "legacy_password_not_selected_or_migrated; administrator_reset_required",
            "source_created_at": user.created_at, "source_updated_at": user.updated_at,
        },
        "email": user.email, "mobile": user.mobile, "office_phone": user.office_phone,
        "company": user.company, "account_type": "员工账号", "legacy_department_name": user.department_name,
        "password_reset_required_reason": "旧 IPR 密码未读取、未复制；仅管理员重置后可登录",
    }
    if target_job_role:
        profile.update({"staff_role": str(target_job_role["name"]), "permission_role": str(target_job_role["name"]), "permission_role_code": str(target_job_role["code"])})
    return profile


def _compatible_user(existing: sqlite3.Row, source: LegacyIprUser, target_department: str) -> list[str]:
    profile = as_json(existing["profile"])
    existing_ipr = profile.get("legacy_ipr_identity")
    conflicts: list[str] = []
    if isinstance(existing_ipr, dict) and existing_ipr.get("legacy_ipr_user_id") not in (None, source.id):
        conflicts.append("different_legacy_ipr_user_id")
    # UserName is the legacy IPR relation key.  Once it is unique, the IPR
    # name/contact/department snapshot supplements the employee identity and
    # must not be rejected merely because a previous importer stored aliases.
    # A different *IPR* primary key remains a hard conflict.
    return conflicts


def _compatible_hr_record(existing: sqlite3.Row, source: LegacyIprUser, target_department: str) -> list[str]:
    data = as_json(existing["data"])
    existing_ipr = data.get("legacy_ipr_identity")
    conflicts: list[str] = []
    if isinstance(existing_ipr, dict) and existing_ipr.get("legacy_ipr_user_id") not in (None, source.id):
        conflicts.append("different_legacy_ipr_user_id")
    username = clean(data.get("username")) or clean(existing["owner"])
    if username and key(username) != key(source.username):
        conflicts.append("linked_username_mismatch")
    return conflicts


def _is_current_user(existing: sqlite3.Row, source: LegacyIprUser, department: str, target_job_role: sqlite3.Row | None) -> bool:
    profile = as_json(existing["profile"])
    identity = profile.get("legacy_ipr_identity")
    if not isinstance(identity, dict):
        return False
    if any((identity.get("legacy_ipr_user_id") != source.id, clean(identity.get("source_updated_at")) != source.updated_at,
            clean(existing["display_name"]) != source.display_name)):
        return False
    if any(clean(profile.get(field)) != expected for field, expected in (("email", source.email), ("mobile", source.mobile), ("office_phone", source.office_phone))):
        return False
    if target_job_role:
        return clean(profile.get("permission_role_code")) == clean(target_job_role["code"])
    # No unique IPR-to-new-job-role match must not erase or repeatedly rewrite
    # an independently migrated HR job role.
    return True


def _is_current_hr_record(existing: sqlite3.Row, source: LegacyIprUser, department: str) -> bool:
    data = as_json(existing["data"])
    identity = data.get("legacy_ipr_identity")
    return isinstance(identity, dict) and identity.get("legacy_ipr_user_id") == source.id and clean(identity.get("source_updated_at")) == source.updated_at and clean(existing["title"]) == source.display_name and clean(existing["owner"]) == source.username and clean(data.get("username")) == source.username


def build_plan(connection: sqlite3.Connection, source_rows: Iterable[LegacyIprUser]) -> dict[str, Any]:
    _require_target_schema(connection)
    all_rows = list(source_rows)
    included = [row for row in all_rows if not is_codex_account(row.username, row.display_name)]
    excluded = [row.username for row in all_rows if is_codex_account(row.username, row.display_name)]
    users_by_name = {key(row["username"]): row for row in connection.execute("SELECT * FROM users")}
    hr_by_name = _hr_records(connection)
    departments = _target_departments(connection)
    roles = _target_job_roles(connection)
    seen = Counter(key(row.username) for row in included)
    plan: dict[str, Any] = {"source": SOURCE, "mode": "dry-run", "legacy_source_code_evidence": LEGACY_CODE_EVIDENCE,
        "source_counts": {"ipr_users": len(all_rows), "ipr_users_excluding_codex": len(included), "codex_excluded": len(excluded)},
        "staff_actions": [], "conflicts": [], "unmapped_roles": [], "skipped_test_accounts": excluded, "summary": {}}
    for source in included:
        if not source.username or not source.display_name:
            plan["conflicts"].append({"legacy_ipr_user_id": source.id, "username": source.username, "reason": "missing_username_or_employee_name"})
            continue
        if seen[key(source.username)] != 1:
            plan["conflicts"].append({"legacy_ipr_user_id": source.id, "username": source.username, "reason": "duplicate_source_username"})
            continue
        if not source.department_id or not source.department_code or not source.department_name:
            plan["conflicts"].append({"legacy_ipr_user_id": source.id, "username": source.username, "reason": "missing_verifiable_department"})
            continue
        target_department = departments.get(key(source.department_code))
        # DepartmentCode is the common stable identifier.  The old IPR
        # abbreviation and the newer employee-management display name may
        # differ, so retain the IPR name as evidence but reuse the code's
        # canonical new-system name.
        effective_department = str(target_department["name"]) if target_department else source.department_name
        exact_candidates = []
        for _, legacy_role_name in source.roles:
            candidates = roles.get(key(legacy_role_name), []) if legacy_role_name else []
            if len(candidates) == 1:
                exact_candidates.append(candidates[0])
            elif legacy_role_name:
                plan["unmapped_roles"].append({"legacy_ipr_user_id": source.id, "username": source.username, "legacy_role_name": legacy_role_name, "reason": "missing_exact_target_job_role" if not candidates else "ambiguous_exact_target_job_role"})
        target_role = exact_candidates[0] if len(exact_candidates) == 1 else None
        if len({int(item["id"]) for item in exact_candidates}) > 1:
            plan["unmapped_roles"].append({"legacy_ipr_user_id": source.id, "username": source.username, "reason": "multiple_exact_target_job_roles"})
            target_role = None
        existing_user = users_by_name.get(key(source.username))
        existing_hr = hr_by_name.get(key(source.username), [])
        user_conflicts = _compatible_user(existing_user, source, effective_department) if existing_user else []
        hr_conflicts = ["multiple_hr_records_for_username"] if len(existing_hr) > 1 else (_compatible_hr_record(existing_hr[0], source, effective_department) if existing_hr else [])
        if user_conflicts or hr_conflicts:
            plan["conflicts"].append({"legacy_ipr_user_id": source.id, "username": source.username, "reason": "target_identity_conflict", "user_conflicts": user_conflicts, "hr_record_conflicts": hr_conflicts})
            continue
        user_action = "create_random_reset_account" if not existing_user else ("unchanged" if _is_current_user(existing_user, source, effective_department, target_role) else "merge")
        hr_action = "create" if not existing_hr else ("unchanged" if _is_current_hr_record(existing_hr[0], source, effective_department) else "merge")
        plan["staff_actions"].append({"legacy_ipr_user_id": source.id, "username": source.username, "display_name": source.display_name, "is_active": source.is_active,
            "legacy_department": {"id": source.department_id, "code": source.department_code, "name": source.department_name},
            "target_department": {"code": source.department_code, "name": effective_department},
            "department_action": "reuse_code" if target_department else "create_from_verified_ipr_department",
            "legacy_roles": [{"id": role_id, "name": role_name} for role_id, role_name in source.roles],
            "target_job_role": {"id": int(target_role["id"]), "code": str(target_role["code"]), "name": str(target_role["name"])} if target_role else None,
            "system_role": "user", "user_action": user_action, "hr_record_action": hr_action,
            "hr_serial_no": str(existing_hr[0]["serial_no"]) if existing_hr else f"LEGACY-IPR-{source.id}"})
    plan["summary"] = {"eligible_count": len(plan["staff_actions"]), "create_account_count": sum(x["user_action"].startswith("create") for x in plan["staff_actions"]), "merge_account_count": sum(x["user_action"] == "merge" for x in plan["staff_actions"]), "unchanged_account_count": sum(x["user_action"] == "unchanged" for x in plan["staff_actions"]), "create_hr_record_count": sum(x["hr_record_action"] == "create" for x in plan["staff_actions"]), "merge_hr_record_count": sum(x["hr_record_action"] == "merge" for x in plan["staff_actions"]), "unchanged_hr_record_count": sum(x["hr_record_action"] == "unchanged" for x in plan["staff_actions"]), "active_count": sum(x["is_active"] for x in plan["staff_actions"]), "inactive_count": sum(not x["is_active"] for x in plan["staff_actions"]), "conflict_count": len(plan["conflicts"]), "unmapped_role_count": len(plan["unmapped_roles"])}
    return plan


def backup_database(path: Path, output_dir: Path) -> Path:
    if not path.exists():
        raise MigrationError(f"target database does not exist: {path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    backup = output_dir / f"legal_platform.before-legacy-ipr-user-identity-{datetime.now():%Y%m%d-%H%M%S}.db"
    shutil.copy2(path, backup)
    if hashlib.sha256(path.read_bytes()).hexdigest() != hashlib.sha256(backup.read_bytes()).hexdigest():
        raise MigrationError("SQLite backup checksum mismatch")
    return backup


def apply_plan(connection: sqlite3.Connection, source_rows: Iterable[LegacyIprUser], plan: dict[str, Any]) -> dict[str, Any]:
    sources = {row.id: row for row in source_rows if not is_codex_account(row.username, row.display_name)}
    actions = {int(item["legacy_ipr_user_id"]): item for item in plan["staff_actions"]}
    now = datetime.now(timezone.utc).isoformat()
    mutation = {"departments_created": 0, "users_created": 0, "users_merged": 0, "hr_records_created": 0, "hr_records_merged": 0, "workflow_events_created": 0}
    with connection:
        departments = _target_departments(connection)
        for item in actions.values():
            source = sources[int(item["legacy_ipr_user_id"])]
            if item["department_action"] == "create_from_verified_ipr_department":
                connection.execute("INSERT INTO departments(code,name,parent_department_id,manager,overdue_deduction,sort_order,is_active,created_by,updated_by) VALUES(?,?,?,?,?,?,?,?,?)", (source.department_code, source.department_name, None, "", 0, source.department_id or 0, 1, ACTOR, ACTOR))
                mutation["departments_created"] += 1
        departments = _target_departments(connection)
        users = {key(row["username"]): row for row in connection.execute("SELECT * FROM users")}
        hr_by_name = _hr_records(connection)
        roles = _target_job_roles(connection)
        for source_id, item in actions.items():
            source = sources[source_id]
            candidates = [roles[key(name)] for _, name in source.roles if name and len(roles.get(key(name), [])) == 1]
            resolved = [group[0] for group in candidates]
            target_role = resolved[0] if len({int(row["id"]) for row in resolved}) == 1 and len(resolved) == 1 else None
            metadata = _legacy_profile(source, target_role)
            metadata["legacy_ipr_identity"]["migrated_at"] = now
            existing_user = users.get(key(source.username))
            if existing_user and item["user_action"] == "merge":
                profile = {**as_json(existing_user["profile"]), **metadata}
                connection.execute("UPDATE users SET display_name=?,profile=? WHERE id=?", (source.display_name, json.dumps(profile, ensure_ascii=False, sort_keys=True), int(existing_user["id"])))
                mutation["users_merged"] += 1
            elif not existing_user:
                password_hash = PasswordHash.recommended().hash(secrets.token_urlsafe(48))
                department = str(departments[key(source.department_code)]["name"])
                connection.execute("INSERT INTO users(username,display_name,department,password_hash,role,role_ids,profile,is_active,must_change_password,failed_login_attempts) VALUES(?,?,?,?,?,?,?,?,?,?)", (source.username, source.display_name, department, password_hash, "user", json.dumps(["user"]), json.dumps(metadata, ensure_ascii=False, sort_keys=True), int(source.is_active), 1, 0))
                mutation["users_created"] += 1
            existing_records = hr_by_name.get(key(source.username), [])
            record_data = {**metadata, "username": source.username, "role": "user", "is_active": source.is_active}
            status = "在职" if source.is_active else "停用"
            if existing_records and item["hr_record_action"] == "merge":
                record = existing_records[0]
                existing_data = as_json(record["data"])
                merged = {**existing_data, **metadata, "username": source.username, "role": "user"}
                connection.execute("UPDATE business_records SET title=?,owner=?,data=? WHERE id=?", (source.display_name, source.username, json.dumps(merged, ensure_ascii=False, sort_keys=True), int(record["id"])))
                record_id = int(record["id"]); mutation["hr_records_merged"] += 1
            elif not existing_records:
                department = str(departments[key(source.department_code)]["name"])
                cursor = connection.execute("INSERT INTO business_records(module,serial_no,title,customer,status,owner,department,description,data) VALUES(?,?,?,?,?,?,?,?,?)", ("hr", item["hr_serial_no"], source.display_name, source.company or "", status, source.username, department, "旧 IPR_User 历史身份迁移", json.dumps(record_data, ensure_ascii=False, sort_keys=True)))
                record_id = int(cursor.lastrowid); mutation["hr_records_created"] += 1
            else:
                continue
            if item["hr_record_action"] != "unchanged":
                connection.execute("INSERT INTO workflow_events(record_id,action,from_status,to_status,operator,comment) VALUES(?,?,?,?,?,?)", (record_id, "迁移旧 IPR 人员身份", "", status, ACTOR, f"来源 IPR_User.UserId={source.id}; 旧密码未读取或复制，管理员重置后方可登录"))
                mutation["workflow_events_created"] += 1
    result = dict(plan); result.update({"mode": "apply", "applied_at": now, "mutation": mutation})
    return result


def write_report(report: Mapping[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = report.get("summary", {})
    output_path.with_suffix(".md").write_text("# Legacy IPR_User Identity Migration\n\n" + "\n".join(f"- {name}: `{value}`" for name, value in summary.items()) + "\n- Legacy password columns were never selected or copied.\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-db", type=Path, default=DEFAULT_TARGET_DB)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--server", default="."); parser.add_argument("--database", default="PRD_CRM_GD_20200211")
    parser.add_argument("--driver", default="ODBC Driver 17 for SQL Server")
    parser.add_argument("--apply", action="store_true"); parser.add_argument("--backup-confirmed", action="store_true")
    args = parser.parse_args(argv)
    if args.apply and not args.backup_confirmed:
        parser.error("--apply requires --backup-confirmed; a checksummed backup is created automatically")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv); source_rows = read_legacy_sql_server(args.server, args.database, args.driver)
    connection = sqlite3.connect(args.target_db); connection.row_factory = sqlite3.Row
    try:
        plan = build_plan(connection, source_rows); stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        if args.apply:
            backup = backup_database(args.target_db, args.output_dir)
            report = apply_plan(connection, source_rows, plan)
            report["backup"] = {"path": str(backup), "sha256": hashlib.sha256(backup.read_bytes()).hexdigest()}
            output = args.output_dir / f"legacy-ipr-user-identity-apply-{stamp}.json"
        else:
            report = plan; output = args.output_dir / f"legacy-ipr-user-identity-dry-run-{stamp}.json"
        write_report(report, output); print(output); print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())

