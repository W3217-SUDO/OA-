#!/usr/bin/env python3
"""Synchronize inactive and departed legacy HR statuses from an audited manifest."""

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


class SyncBlocked(RuntimeError):
    """Raised before writes when the source or target identity is ambiguous."""


class ResultLike(Protocol):
    def fetchall(self) -> list[Any]: ...


class ConnectionLike(Protocol):
    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> ResultLike: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


@dataclass(frozen=True)
class TargetChange:
    record_id: int
    user_id: int
    username: str
    active: bool
    status: str
    record_data: dict[str, Any]
    user_profile: dict[str, Any]


def clean(value: Any) -> str:
    return str(value or "").strip()


def normalized(value: Any) -> str:
    return clean(value).casefold()


def as_object(value: Any, label: str) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    parsed = json.loads(value or "{}")
    if not isinstance(parsed, dict):
        raise SyncBlocked(f"{label} must be a JSON object")
    return parsed


def legacy_bool(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    token = normalized(value)
    if token in {"t", "true", "1", "yes", "y"}:
        return True
    if token in {"f", "false", "0", "no", "n"}:
        return False
    raise SyncBlocked(f"invalid {field} value: {value!r}")


def row_value(row: Any, key: str) -> Any:
    if isinstance(row, dict):
        return row[key]
    return row[key]


def placeholder(dialect: str) -> str:
    return "%s" if dialect == "postgresql" else "?"


def normalize_postgresql_url(database_url: str) -> str:
    for driver in ("+asyncpg", "+psycopg", "+psycopg2"):
        database_url = database_url.replace(f"postgresql{driver}://", "postgresql://", 1)
    return database_url


def load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("staff"), list):
        raise SyncBlocked("manifest must contain a staff array")
    if not clean(payload.get("source_database")) or not clean(payload.get("exported_at")):
        raise SyncBlocked("manifest source_database and exported_at are required")
    return payload


def status_for(source: dict[str, Any]) -> tuple[bool, str]:
    is_active = legacy_bool(source.get("is_actived"), "is_actived")
    job_active = legacy_bool(source.get("job_status"), "job_status")
    resigned_at = clean(source.get("resignation_date"))
    if is_active and job_active and not resigned_at:
        raise SyncBlocked(f"manifest includes active employee {clean(source.get('username'))!r}")
    return False, "离职" if not job_active or resigned_at else "停用"


def collect_changes(
    connection: ConnectionLike, manifest: dict[str, Any], dialect: str
) -> tuple[list[TargetChange], dict[str, int]]:
    marker = placeholder(dialect)
    source_database = clean(manifest["source_database"])
    exported_at = clean(manifest["exported_at"])
    stats = {
        "source": 0,
        "matched": 0,
        "unmatched": 0,
        "identity_conflict": 0,
        "already_current": 0,
        "changed": 0,
        "updated": 0,
    }
    changes: list[TargetChange] = []
    seen_users: set[str] = set()
    seen_guids: set[str] = set()

    for source_value in manifest["staff"]:
        source = as_object(source_value, "manifest staff row")
        stats["source"] += 1
        username = normalized(source.get("username"))
        guid = normalized(source.get("staff_guid"))
        if not username or not guid:
            raise SyncBlocked("every manifest row requires username and staff_guid")
        if username in seen_users or guid in seen_guids:
            raise SyncBlocked(f"duplicate source identity: {username}")
        seen_users.add(username)
        seen_guids.add(guid)
        active, status = status_for(source)

        records = connection.execute(
            "SELECT id,serial_no,owner,status,data FROM business_records WHERE module='hr' AND lower(owner)=" + marker,
            (username,),
        ).fetchall()
        if not records:
            stats["unmatched"] += 1
            continue
        if len(records) != 1:
            raise SyncBlocked(f"target has {len(records)} HR records for {username}")
        record = records[0]
        record_data = as_object(row_value(record, "data"), f"HR record {row_value(record, 'id')} data")
        identities = [
            value
            for value in (record_data.get("legacy_hr_identity"), record_data.get("legacy_hr"))
            if isinstance(value, dict)
        ]
        target_guids = {
            normalized(value.get("legacy_staff_guid"))
            for value in identities
            if normalized(value.get("legacy_staff_guid"))
        }
        source_staff_no = clean(source.get("staff_no"))
        target_staff_no = clean(
            record_data.get("employee_no")
            or record_data.get("legacy_staff_no")
            or row_value(record, "serial_no")
        )
        if target_guids and guid not in target_guids:
            stats["identity_conflict"] += 1
            print(
                f"IDENTITY-CONFLICT user={username}: source_guid={guid} "
                f"target_guids={','.join(sorted(target_guids))}"
            )
            continue
        if not target_guids and (not source_staff_no or target_staff_no != source_staff_no):
            stats["identity_conflict"] += 1
            print(
                f"IDENTITY-CONFLICT user={username}: no target GUID and employee numbers "
                f"differ ({target_staff_no!r} != {source_staff_no!r})"
            )
            continue
        identity = next(
            (dict(value) for value in identities if normalized(value.get("legacy_staff_guid")) == guid),
            {},
        )

        users = connection.execute(
            "SELECT id,is_active,profile FROM users WHERE lower(username)=" + marker,
            (username,),
        ).fetchall()
        if len(users) != 1:
            raise SyncBlocked(f"target has {len(users)} users for {username}")
        user = users[0]
        user_profile = as_object(row_value(user, "profile"), f"user {row_value(user, 'id')} profile")
        resigned_at = clean(source.get("resignation_date"))
        source_active = legacy_bool(source.get("is_actived"), "is_actived")
        source_job = legacy_bool(source.get("job_status"), "job_status")
        audit = {
            **identity,
            "legacy_staff_id": source.get("staff_id"),
            "legacy_staff_guid": clean(source.get("staff_guid")),
            "legacy_staff_no": source_staff_no,
            "legacy_is_actived": source_active,
            "legacy_job_status": source_job,
            "legacy_resignation_date": resigned_at,
            "status_source": source_database,
            "status_source_changed_at": clean(source.get("changed_at")),
            "status_synced_from_export": exported_at,
        }
        record_data.update(
            {
                "is_active": active,
                "left_at": resigned_at,
                "legacy_is_actived": "T" if source_active else "F",
                "legacy_job_status": "T" if source_job else "F",
                "legacy_hr_identity": audit,
            }
        )
        user_profile.update(
            {
                "left_at": resigned_at,
                "legacy_is_actived": "T" if source_active else "F",
                "legacy_job_status": "T" if source_job else "F",
                "legacy_hr_identity": audit,
            }
        )
        stats["matched"] += 1
        changed = (
            bool(row_value(user, "is_active")) != active
            or clean(row_value(record, "status")) != status
            or as_object(row_value(record, "data"), "record data") != record_data
            or as_object(row_value(user, "profile"), "user profile") != user_profile
        )
        if not changed:
            stats["already_current"] += 1
            continue
        stats["changed"] += 1
        changes.append(
            TargetChange(
                record_id=int(row_value(record, "id")),
                user_id=int(row_value(user, "id")),
                username=username,
                active=active,
                status=status,
                record_data=record_data,
                user_profile=user_profile,
            )
        )
    return changes, stats


def synchronize(
    connection: ConnectionLike, manifest: dict[str, Any], dry_run: bool, dialect: str
) -> dict[str, int]:
    try:
        changes, stats = collect_changes(connection, manifest, dialect)
        marker = placeholder(dialect)
        for change in changes:
            print(
                f"{'DRY-RUN' if dry_run else 'SYNC'} user={change.username} "
                f"status={change.status} is_active={change.active}"
            )
            if dry_run:
                continue
            record_data: Any = json.dumps(change.record_data, ensure_ascii=False, sort_keys=True)
            user_profile: Any = json.dumps(change.user_profile, ensure_ascii=False, sort_keys=True)
            if dialect == "postgresql":
                from psycopg.types.json import Jsonb

                record_data = Jsonb(change.record_data)
                user_profile = Jsonb(change.user_profile)
            connection.execute(
                f"UPDATE business_records SET status={marker},data={marker} WHERE id={marker}",
                (change.status, record_data, change.record_id),
            )
            connection.execute(
                f"UPDATE users SET is_active={marker},profile={marker} WHERE id={marker}",
                (change.active, user_profile, change.user_id),
            )
            stats["updated"] += 1
        if dry_run:
            connection.rollback()
        else:
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
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = load_manifest(args.manifest)
    connection, dialect = open_connection(args.database_url, args.db)
    try:
        stats = synchronize(connection, manifest, dry_run=not args.apply, dialect=dialect)
    finally:
        connection.close()  # type: ignore[attr-defined]
    print(json.dumps(stats, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
