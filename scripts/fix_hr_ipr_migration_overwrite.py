#!/usr/bin/env python3
"""Restore HR-owned department and employment status after an IPR merge."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "apps" / "api-server" / "legal_platform.db"


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


def repair(connection: sqlite3.Connection, dry_run: bool) -> dict[str, int]:
    connection.row_factory = sqlite3.Row
    departments = {
        normalized(row["code"]): str(row["name"])
        for row in connection.execute("SELECT code,name FROM departments")
    }
    stats = {"eligible": 0, "department_corrected": 0, "status_corrected": 0, "missing_department": 0, "missing_user": 0}
    rows = connection.execute(
        "SELECT id,owner,department,status,data FROM business_records WHERE module='hr'"
    ).fetchall()
    for row in rows:
        data = as_object(row["data"])
        hr_identity = data.get("legacy_hr_identity")
        if not isinstance(hr_identity, dict) or not isinstance(data.get("legacy_ipr_identity"), dict):
            continue
        stats["eligible"] += 1
        username = str(row["owner"] or data.get("username") or "").strip()
        department_code = normalized(hr_identity.get("legacy_department_code"))
        correct_department = departments.get(department_code)
        if not correct_department:
            stats["missing_department"] += 1
            print(f"SKIP record={row['id']} owner={username}: department code {department_code!r} not found")
            continue
        correct_active = legacy_bool(hr_identity.get("legacy_is_actived"))
        correct_status = "在职" if correct_active else "停用"
        user = connection.execute(
            "SELECT id,department,is_active FROM users WHERE username=?", (username,)
        ).fetchone()
        if user is None:
            stats["missing_user"] += 1

        department_changed = str(row["department"] or "") != correct_department or (
            user is not None and str(user["department"] or "") != correct_department
        )
        status_changed = str(row["status"] or "") != correct_status or data.get("is_active") is not correct_active or (
            user is not None and bool(user["is_active"]) != correct_active
        )
        if department_changed:
            stats["department_corrected"] += 1
        if status_changed:
            stats["status_corrected"] += 1
        if not department_changed and not status_changed:
            continue

        print(
            f"{'DRY-RUN' if dry_run else 'FIX'} record={row['id']} owner={username}: "
            f"department {row['department']!r}->{correct_department!r}; "
            f"status {row['status']!r}->{correct_status!r}"
        )
        if dry_run:
            continue
        data["is_active"] = correct_active
        connection.execute(
            "UPDATE business_records SET department=?,status=?,data=? WHERE id=?",
            (correct_department, correct_status, json.dumps(data, ensure_ascii=False, sort_keys=True), int(row["id"])),
        )
        if user is not None:
            connection.execute(
                "UPDATE users SET department=?,is_active=? WHERE id=?",
                (correct_department, int(correct_active), int(user["id"])),
            )
    if dry_run:
        connection.rollback()
    else:
        connection.commit()
    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with sqlite3.connect(args.db) as connection:
        stats = repair(connection, args.dry_run)
    print(json.dumps(stats, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
