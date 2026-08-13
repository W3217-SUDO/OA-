"""Backfill current OA records into the legacy compatibility tables.

Dry-run is the default.  ``--apply`` commits all projections atomically; any
failure rolls the complete run back.  The existing synchronization functions
make reruns idempotent by resolving records through their legacy soft keys.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import func, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.main import _sync_legacy_projection
from app.models import (
    BusinessRecord,
    LegacyCase,
    LegacyContract,
    LegacyCustomer,
    LegacyInvestigation,
    LegacyInvestigationClue,
    LegacyInvestigationTask,
)


TARGET_MODULES = {"customer", "contract", "case", "investigation", "task", "clue"}
PROJECTION_CLASSES = (
    LegacyCustomer,
    LegacyContract,
    LegacyCase,
    LegacyInvestigation,
    LegacyInvestigationTask,
    LegacyInvestigationClue,
)


async def projection_counts(db) -> dict[str, int]:
    return {
        model.__table__.name: int(await db.scalar(select(func.count()).select_from(model)) or 0)
        for model in PROJECTION_CLASSES
    }


def record_identity(record: BusinessRecord) -> dict[str, str]:
    actor = str((record.data or {}).get("created_by") or record.owner or "system")
    return {
        "username": actor,
        "display_name": actor,
        "role": "admin",
        "department": record.department or "",
    }


async def run_backfill(apply: bool) -> dict:
    async with SessionLocal() as db:
        before = await projection_counts(db)
        records = list(
            (
                await db.scalars(
                    select(BusinessRecord)
                    .where(BusinessRecord.module.in_(TARGET_MODULES))
                    .order_by(BusinessRecord.id)
                )
            ).all()
        )
        try:
            for record in records:
                await _sync_legacy_projection(record, record_identity(record), db)
            await db.flush()
            projected = await projection_counts(db)
            if apply:
                await db.commit()
            else:
                await db.rollback()
        except Exception:
            await db.rollback()
            raise

    async with SessionLocal() as db:
        persisted = await projection_counts(db)
    return {
        "mode": "apply" if apply else "dry-run",
        "processed_records": len(records),
        "before": before,
        "projected": projected,
        "persisted": persisted,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Commit the atomic backfill")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run_backfill(args.apply)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
