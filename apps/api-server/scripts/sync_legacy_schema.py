"""Synchronize and audit the PostgreSQL legacy compatibility schema."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import engine
from app.legacy_schema import (
    align_legacy_column_types,
    align_legacy_constraints,
    align_legacy_indexes,
    audit_legacy_schema,
    create_full_legacy_schema,
    ensure_legacy_indexes,
    load_legacy_schema_manifest,
)


async def run(apply: bool) -> None:
    manifest = load_legacy_schema_manifest()
    async with engine.connect() as connection:
        transaction = await connection.begin()
        await connection.run_sync(create_full_legacy_schema)
        await connection.run_sync(align_legacy_column_types)
        await connection.run_sync(align_legacy_constraints)
        await connection.run_sync(ensure_legacy_indexes)
        await connection.run_sync(align_legacy_indexes)
        report = await connection.run_sync(audit_legacy_schema)
        if report["errors"]:
            await transaction.rollback()
            raise RuntimeError(json.dumps(report, ensure_ascii=False, default=str))
        if apply:
            await transaction.commit()
        else:
            await transaction.rollback()
        print(json.dumps({
            "applied": apply,
            "expected_tables": manifest["table_count"],
            "expected_columns": sum(len(table["columns"]) for table in manifest["tables"]),
            "audit": report,
        }, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Commit the synchronized schema")
    args = parser.parse_args()
    asyncio.run(run(args.apply))
