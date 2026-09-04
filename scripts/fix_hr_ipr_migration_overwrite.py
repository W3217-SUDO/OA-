#!/usr/bin/env python3
"""Restore HR-owned department and employment status after an IPR merge."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "apps" / "api-server" / "legal_platform.db"


class RepairBlocked(RuntimeError):
    """Raised before writes when source-to-target identity is ambiguous."""


class CursorLike(Protocol):
    def fetchall(self) -> list[Any]: ...


class ConnectionLike(Protocol):
    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> CursorLike: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


@dataclass(frozen=True)
class Change:
    record_id: int
    user_id: int
    username: str
    department: str
    active: bool
    status: str
    data: dict[str, Any]
    department_changed: bool
    status_changed: bool


def as_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    parsed = json.loads(value or "{}")
    if not isinstance(parsed, dict):
        raise ValueError("HR record data must be a JSON object")
    return parsed


def normalized(value: Any) -> str:
    return str(value or "").strip().casefold()


def legacy_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = normalized(value)
    if text in {"t", "true", "1", "yes", "y"}:
        return True
    if text in {"f", "false", "0", "no", "n"}:
        return False
    raise ValueError(f"invalid legacy_is_actived value: {value!r}")


def row_value(row: Any, key: str) -> Any:
    if isinstance(row, dict):
        return row[key]
    try:
        return row[key]
    except (IndexError, TypeError):
        keys = {"id": 0, "owner": 1, "department": 2, "status": 3, "data": 4}
        return row[keys[key]]


def placeholder(dialect: str) -> str:
    return "%s" if dialect == "postgresql" else "?"


def normalize_postgresql_url(database_url: str) -> str:
    for driver in ("+asyncpg", "+psycopg", "+psycopg2"):
        database_url = database_url.replace(f"postgresql{driver}://", "postgresql://", 1)
    return database_url


def collect_changes(connection: ConnectionLike, dialect: str) -> tuple[list[Change], dict[str, int]]:
    departments = {
        normalized(row_value(row, "code")): str(row_value(row, "name"))
        for row in connection.execute("SELECT code,name FROM departments").fetchall()
    }
    stats = {
        "eligible": 0,
        "department_corrected": 0,
        "status_corrected": 0,
        "missing_department": 0,
        "missing_username": 0,
        "missing_user": 0,
        "duplicate_user": 0,
        "blocked": 0,
        "updated": 0,
    }
    changes: list[Change] = []
    errors: list[str] = []
    marker = placeholder(dialect)
    rows = connection.execute(
        "SELECT id,owner,department,status,data FROM business_records WHERE module='hr'"
    ).fetchall()
    for row in rows:
        data = as_object(row_value(row, "data"))
        hr_identity = data.get("legacy_hr_identity")
        if not isinstance(hr_identity, dict) or not isinstance(data.get("legacy_ipr_identity"), dict):
            continue
        stats["eligible"] += 1
        record_id = int(row_value(row, "id"))
        username = str(row_value(row, "owner") or data.get("username") or "").strip()
        if not username:
            stats["missing_username"] += 1
            errors.append(f"record={record_id}: username is empty")
            continue
        department_code = normalized(hr_identity.get("legacy_department_code"))
        correct_department = departments.get(department_code)
        if not correct_department:
            stats["missing_department"] += 1
            errors.append(f"record={record_id} owner={username}: department code {department_code!r} not found")
            continue
        users = connection.execute(
            f"SELECT id,department,is_active FROM users WHERE username={marker}", (username,)
        ).fetchall()
        if not users:
            stats["missing_user"] += 1
            errors.append(f"record={record_id} owner={username}: user not found")
            continue
        if len(users) != 1:
            stats["duplicate_user"] += 1
            errors.append(f"record={record_id} owner={username}: matched {len(users)} users")
            continue

        user = users[0]
        correct_active = legacy_bool(hr_identity.get("legacy_is_actived"))
        correct_status = "在职" if correct_active else "停用"
        department_changed = str(row_value(row, "department") or "") != correct_department or str(
            row_value(user, "department") or ""
        ) != correct_department
        status_changed = (
            str(row_value(row, "status") or "") != correct_status
            or data.get("is_active") is not correct_active
            or bool(row_value(user, "is_active")) != correct_active
        )
        stats["department_corrected"] += int(department_changed)
        stats["status_corrected"] += int(status_changed)
        if department_changed or status_changed:
            data["is_active"] = correct_active
            changes.append(
                Change(
                    record_id=record_id,
                    user_id=int(row_value(user, "id")),
                    username=username,
                    department=correct_department,
                    active=correct_active,
                    status=correct_status,
                    data=data,
                    department_changed=department_changed,
                    status_changed=status_changed,
                )
            )

    if errors:
        stats["blocked"] = len(errors)
        raise RepairBlocked("repair blocked before writes:\n" + "\n".join(errors))
    return changes, stats


def repair(connection: ConnectionLike, dry_run: bool, dialect: str = "sqlite") -> dict[str, int]:
    if dialect not in {"sqlite", "postgresql"}:
        raise ValueError(f"unsupported database dialect: {dialect}")
    try:
        changes, stats = collect_changes(connection, dialect)
        for change in changes:
            print(
                f"{'DRY-RUN' if dry_run else 'FIX'} record={change.record_id} owner={change.username}: "
                f"department->{change.department!r}; status->{change.status!r}"
            )
        if dry_run:
            connection.rollback()
            return stats

        marker = placeholder(dialect)
        for change in changes:
            data_value: Any = json.dumps(change.data, ensure_ascii=False, sort_keys=True)
            if dialect == "postgresql":
                from psycopg.types.json import Jsonb

                data_value = Jsonb(change.data)
            connection.execute(
                f"UPDATE business_records SET department={marker},status={marker},data={marker} WHERE id={marker}",
                (change.department, change.status, data_value, change.record_id),
            )
            connection.execute(
                f"UPDATE users SET department={marker},is_active={marker} WHERE id={marker}",
                (change.department, change.active, change.user_id),
            )
            stats["updated"] += 1
        connection.commit()
        return stats
    except Exception:
        connection.rollback()
        raise


def open_connection(database_url: str | None, db_path: Path) -> tuple[ConnectionLike, str]:
    if database_url:
        database_url = normalize_postgresql_url(database_url)
        if not database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("--database-url must use postgresql:// or postgres://")
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(database_url, row_factory=dict_row), "postgresql"
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection, "sqlite"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite database path")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL URL; defaults to DATABASE_URL",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Report changes without writing (default)")
    mode.add_argument("--apply", action="store_true", help="Apply all changes in one transaction")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    connection, dialect = open_connection(args.database_url, args.db)
    try:
        stats = repair(connection, dry_run=not args.apply, dialect=dialect)
    finally:
        connection.close()  # type: ignore[attr-defined]
    print(json.dumps(stats, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
