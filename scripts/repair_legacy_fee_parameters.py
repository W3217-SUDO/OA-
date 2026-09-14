#!/usr/bin/env python3
"""Scoped, backup-gated repair of legacy fee parameters; never replaces a database.

Use the raw BAS_Case_FeeType JSON export. Run --backup first, stream stdout to an
off-server file, and verify the stderr SHA256. Apply requires that exact file,
digest and release. --restore restores only changed parameters from that backup.
DATABASE_URL / app settings supply the destination; credentials are never output.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import DateTime, MetaData, Table, inspect, or_, select, delete
from app.database import engine
from app.models import SystemParameter, BusinessRecord
from migrate_legacy_system_parameters import ACTOR, normalize


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def digest(value):
    return hashlib.sha256(encode(value).encode("utf-8")).hexdigest()


def native(table, row):
    result = dict(row)
    for col in table.columns:
        if isinstance(col.type, DateTime) and isinstance(result.get(col.name), str):
            result[col.name] = datetime.fromisoformat(result[col.name])
    return result


def find_target(row, existing):
    legacy_id = row["extra"].get("legacy_id")
    matches = [item for item in existing if item["category"] == "fee_type" and (
        item["code"] == row["code"] or
        (legacy_id is not None and str((item["extra"] or {}).get("legacy_id")) == str(legacy_id))
    )]
    if len(matches) > 1:
        raise RuntimeError("Duplicate legacy mapping; repair aborted")
    return matches[0] if matches else None


def values_for(row, current):
    result = dict(row)
    if current:
        result["code"] = current["code"]
        result["extra"] = {**(current["extra"] or {}), **row["extra"]}
        # Root records have no legacy audit dates; don't invent old metadata.
        for key in ("created_by", "updated_by", "created_at", "updated_at"):
            result.setdefault(key, current[key])
    else:
        result.setdefault("created_by", ACTOR)
        result.setdefault("updated_by", ACTOR)
        result.setdefault("created_at", datetime.now(timezone.utc))
        result.setdefault("updated_at", result["created_at"])
    return result


def differs(table, current, desired):
    if current is None:
        return True
    # SQLite stores UTC datetimes without timezone information.
    for key, value in desired.items():
        actual = current[key]
        if isinstance(value, datetime) and isinstance(actual, datetime):
            actual = actual.replace(tzinfo=actual.tzinfo or timezone.utc).astimezone(timezone.utc)
            value = value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc)
        if actual != value:
            return True
    return False


async def run(args):
    source = json.loads(args.source.read_text(encoding="utf-8-sig"))
    if not source or any(int(r["CaseTypeId"]) <= 0 for r in source):
        raise RuntimeError("Expected non-empty legacy CaseTypeId > 0 export")
    desired = normalize({"fee_type": source, "cause": [], "payment_type": []})
    table = SystemParameter.__table__
    async with engine.begin() as conn:
        existing = [dict(r) for r in (await conn.execute(select(table).order_by(table.c.id))).mappings()]
        targets = [(row, find_target(row, existing)) for row in desired]
        affected = [current for _, current in targets if current]
        ids = [r["id"] for r in affected]
        if args.backup:
            tables = {table.name: existing}
            def relationship_tables(sync):
                inspector = inspect(sync)
                result = []
                metadata = MetaData()
                for name in inspector.get_table_names():
                    columns = {col for fk in inspector.get_foreign_keys(name)
                               if fk["referred_table"] == table.name for col in fk["constrained_columns"]}
                    if columns:
                        result.append((Table(name, metadata, autoload_with=sync), columns))
                return result
            for related, columns in await conn.run_sync(relationship_tables):
                rows = (await conn.execute(select(related).where(or_(*(related.c[c].in_(ids) for c in columns))))).mappings()
                tables[related.name] = [dict(r) for r in rows]
            records = BusinessRecord.__table__
            rows = (await conn.execute(select(records).where(
                records.c.module == "finance",
                or_(records.c.data["fee_type_id"].as_integer().in_(ids),
                    records.c.data["fee_type_code"].as_string().in_([r["code"] for r in affected]),
                    records.c.data["expense_subtype"].as_string().in_([r["name"] for r in affected])),
            ))).mappings()
            tables[records.name] = [dict(r) for r in rows]
            snapshot = {"release": args.release, "source_sha256": digest(source),
                        "captured_at": str(datetime.now(timezone.utc)), "affected_ids": ids,
                        "planned_codes": [r["code"] for r, current in targets if current is None],
                        "tables": tables}
            output = encode(snapshot)
            print(output)
            print("SHA256=" + hashlib.sha256(output.encode("utf-8")).hexdigest(), file=sys.stderr)
            return
        changes = [(row, current, values_for(row, current)) for row, current in targets
                   if differs(table, current, values_for(row, current))]
        if not args.apply and not args.restore:
            print(encode({"source": len(source), "groups": len(desired)-len(source),
                          "updates": sum(current is not None for _, current, _ in changes),
                          "inserts": sum(current is None for _, current, _ in changes)}))
            return
        raw = args.backup_file.read_text(encoding="utf-8-sig").strip()
        if hashlib.sha256(raw.encode("utf-8")).hexdigest() != args.sha256:
            raise RuntimeError("Backup checksum mismatch")
        backup = json.loads(raw)
        if backup["release"] != args.release or backup["source_sha256"] != digest(source):
            raise RuntimeError("Backup belongs to another release/source")
        before = [native(table, r) for r in backup["tables"][table.name]]
        if not before:
            raise RuntimeError("Empty system_parameters backup")
        if args.restore:
            for row, current in targets:
                old = find_target(row, before)
                if current is None:
                    raise RuntimeError("Repair target disappeared; restore aborted")
                expected = values_for(row, old)
                # Original inserted roots have new audit timestamps; ignore them.
                if old is None:
                    for key in ("created_at", "updated_at"):
                        expected[key] = current[key]
                if differs(table, current, expected):
                    raise RuntimeError("Parameter changed since repair; restore aborted")
            for row, current in reversed(targets):
                old = find_target(row, before)
                if old:
                    await conn.execute(table.update().where(table.c.id == old["id"]).values(**old))
                elif row["code"] in backup["planned_codes"]:
                    await conn.execute(delete(table).where(table.c.id == current["id"]))
            print(encode({"restored": len(targets), "release": args.release}))
            return
        for row, current in targets:
            old = find_target(row, before)
            if (current is None) != (old is None) or (current and digest(current) != digest(old)):
                raise RuntimeError("Parameters changed since backup; take a fresh scoped backup")
        for row, current, values in changes:
            if current:
                await conn.execute(table.update().where(table.c.id == current["id"]).values(**values))
            else:
                await conn.execute(table.insert().values(**values))
        actual = [dict(r) for r in (await conn.execute(select(table).order_by(table.c.id))).mappings()]
        for row in desired:
            current = find_target(row, actual)
            if current is None or differs(table, current, values_for(row, current)):
                raise RuntimeError("Post-write integrity/idempotency check failed")
        print(encode({"release": args.release, "source": len(source), "changed": len(changes),
                      "inserted": sum(c is None for _, c, _ in changes), "idempotent": True,
                      "parameter_count_before": len(existing), "parameter_count_after": len(actual)}))
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--release", required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--backup", action="store_true")
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--restore", action="store_true")
    parser.add_argument("--backup-file", type=Path)
    parser.add_argument("--sha256")
    args = parser.parse_args()
    if (args.apply or args.restore) and (not args.backup_file or not args.sha256):
        parser.error("Apply/restore requires verified off-server backup and SHA256")
    asyncio.run(run(args))
