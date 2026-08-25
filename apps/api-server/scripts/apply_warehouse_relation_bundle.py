"""Merge an audited warehouse master/relation bundle into the active database.

The bundle never supplies database primary keys. Existing warehouse business
records are matched by their immutable ``WMS-LEGACY-*`` serial numbers, while
warehouse and location masters are matched by legacy business keys. The
command defaults to a rollback-only dry run and requires ``--apply`` to commit.
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app.database import SessionLocal
from app.models import (
    BusinessRecord,
    Warehouse,
    WarehouseEvidenceLocation,
    WarehouseLegacyEvidenceMapping,
    WarehouseStorageLocation,
)


def _datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def load_bundle(path: Path) -> dict[str, Any]:
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as source:
        bundle = json.load(source)
    validate_bundle(bundle)
    return bundle


def validate_bundle(bundle: dict[str, Any]) -> None:
    expected = bundle.get("expected") or {}
    collections = {
        "warehouses": bundle.get("warehouses") or [],
        "storage_locations": bundle.get("storage_locations") or [],
        "mappings": bundle.get("mappings") or [],
    }
    for name, rows in collections.items():
        if not isinstance(rows, list):
            raise ValueError(f"{name} must be a list")
        if name in expected and len(rows) != int(expected[name]):
            raise ValueError(f"{name} expected {expected[name]}, got {len(rows)}")

    warehouse_keys = [int(row["legacy_warehouse_id"]) for row in collections["warehouses"]]
    location_keys = [int(row["legacy_storage_location_id"]) for row in collections["storage_locations"]]
    evidence_keys = [int(row["legacy_evidence_id"]) for row in collections["mappings"]]
    serials = [str(row["record_serial_no"]) for row in collections["mappings"]]
    for label, values in (
        ("warehouse legacy ids", warehouse_keys),
        ("storage location legacy ids", location_keys),
        ("evidence legacy ids", evidence_keys),
        ("record serial numbers", serials),
    ):
        if len(values) != len(set(values)):
            raise ValueError(f"duplicate {label}")


def _assign(row: Any, values: dict[str, Any]) -> bool:
    changed = False
    for key, value in values.items():
        if getattr(row, key) != value:
            setattr(row, key, value)
            changed = True
    return changed


async def apply_bundle(db: AsyncSession, bundle: dict[str, Any], apply: bool) -> dict[str, Any]:
    validate_bundle(bundle)
    report = {
        "warehouse_inserted": 0,
        "warehouse_updated": 0,
        "location_inserted": 0,
        "location_updated": 0,
        "record_matched": 0,
        "record_updated": 0,
        "binding_inserted": 0,
        "binding_updated": 0,
        "mapping_inserted": 0,
        "mapping_updated": 0,
        "database_written": bool(apply),
    }

    existing_warehouses = list((await db.scalars(select(Warehouse))).all())
    warehouse_by_legacy = {row.legacy_warehouse_id: row for row in existing_warehouses if row.legacy_warehouse_id is not None}
    warehouse_by_no = {row.warehouse_no: row for row in existing_warehouses}
    for source in bundle["warehouses"]:
        legacy_id = int(source["legacy_warehouse_id"])
        warehouse_no = str(source["warehouse_no"])
        row = warehouse_by_legacy.get(legacy_id) or warehouse_by_no.get(warehouse_no)
        values = {
            "legacy_warehouse_id": legacy_id,
            "warehouse_no": warehouse_no,
            "name": str(source["name"]),
            "address": str(source.get("address") or ""),
            "is_active": bool(source.get("is_active", True)),
            "sort_order": int(source.get("sort_order") or 0),
            "created_by": str(source.get("created_by") or "legacy-import"),
            "updated_by": str(source.get("updated_by") or "legacy-import"),
            "legacy_created_at": _datetime(source.get("legacy_created_at")),
            "legacy_updated_at": _datetime(source.get("legacy_updated_at")),
        }
        if row is None:
            row = Warehouse(**values)
            db.add(row)
            report["warehouse_inserted"] += 1
        elif _assign(row, values):
            report["warehouse_updated"] += 1
        warehouse_by_legacy[legacy_id] = row
        warehouse_by_no[warehouse_no] = row
    await db.flush()

    existing_locations = list((await db.scalars(select(WarehouseStorageLocation))).all())
    location_by_legacy = {
        row.legacy_storage_location_id: row
        for row in existing_locations
        if row.legacy_storage_location_id is not None
    }
    for source in bundle["storage_locations"]:
        legacy_id = int(source["legacy_storage_location_id"])
        warehouse = warehouse_by_legacy.get(int(source["legacy_warehouse_id"]))
        if warehouse is None:
            raise RuntimeError(f"warehouse missing for location {legacy_id}")
        row = location_by_legacy.get(legacy_id)
        values = {
            "legacy_storage_location_id": legacy_id,
            "warehouse_id": warehouse.id,
            "storage_location_no": str(source["storage_location_no"]),
            "name": str(source["name"]),
            "address": str(source.get("address") or ""),
            "is_active": bool(source.get("is_active", True)),
            "sort_order": int(source.get("sort_order") or 0),
            "created_by": str(source.get("created_by") or "legacy-import"),
            "updated_by": str(source.get("updated_by") or "legacy-import"),
            "legacy_created_at": _datetime(source.get("legacy_created_at")),
            "legacy_updated_at": _datetime(source.get("legacy_updated_at")),
        }
        if row is None:
            row = WarehouseStorageLocation(**values)
            db.add(row)
            report["location_inserted"] += 1
        elif _assign(row, values):
            report["location_updated"] += 1
        location_by_legacy[legacy_id] = row
    await db.flush()

    warehouse_records = list((await db.scalars(
        select(BusinessRecord).where(BusinessRecord.module == "warehouse")
    )).all())
    record_by_serial = {row.serial_no: row for row in warehouse_records}
    existing_bindings = list((await db.scalars(select(WarehouseEvidenceLocation))).all())
    binding_by_record = {row.record_id: row for row in existing_bindings}
    existing_mappings = list((await db.scalars(select(WarehouseLegacyEvidenceMapping))).all())
    mapping_by_legacy = {row.legacy_evidence_id: row for row in existing_mappings}

    missing_records: list[str] = []
    for source in bundle["mappings"]:
        legacy_id = int(source["legacy_evidence_id"])
        serial_no = str(source["record_serial_no"])
        record = record_by_serial.get(serial_no)
        if record is None:
            missing_records.append(serial_no)
            continue
        report["record_matched"] += 1

        location_legacy_id = source.get("legacy_storage_location_id")
        location = location_by_legacy.get(int(location_legacy_id)) if location_legacy_id is not None else None
        warehouse = warehouse_by_legacy.get(int(source["legacy_warehouse_id"])) if source.get("legacy_warehouse_id") is not None else None
        if source["mapping_status"] == "mapped" and (warehouse is None or location is None):
            raise RuntimeError(f"mapped evidence {legacy_id} has no master location")

        if warehouse is not None and location is not None:
            next_data = {
                **(record.data or {}),
                "warehouse_id": warehouse.id,
                "warehouse_no": warehouse.warehouse_no,
                "warehouse": warehouse.name,
                "storage_location_id": location.id,
                "storage_location_no": location.storage_location_no,
                "location": location.name,
            }
            if next_data != (record.data or {}):
                record.data = next_data
                report["record_updated"] += 1
            binding = binding_by_record.get(record.id)
            binding_values = {
                "warehouse_id": warehouse.id,
                "storage_location_id": location.id,
                "assigned_by": "legacy-import",
            }
            if binding is None:
                binding = WarehouseEvidenceLocation(record_id=record.id, **binding_values)
                db.add(binding)
                binding_by_record[record.id] = binding
                report["binding_inserted"] += 1
            elif _assign(binding, binding_values):
                report["binding_updated"] += 1

        mapping = mapping_by_legacy.get(legacy_id)
        mapping_values = {
            "legacy_evidence_id": legacy_id,
            "legacy_evidence_guid": str(source.get("legacy_evidence_guid") or ""),
            "record_id": record.id,
            "warehouse_id": warehouse.id if warehouse else None,
            "storage_location_id": location.id if location else None,
            "mapping_status": str(source["mapping_status"]),
            "reason": str(source.get("reason") or ""),
            "source_snapshot": source.get("source_snapshot") or {},
        }
        if mapping is None:
            mapping = WarehouseLegacyEvidenceMapping(**mapping_values)
            db.add(mapping)
            mapping_by_legacy[legacy_id] = mapping
            report["mapping_inserted"] += 1
        elif _assign(mapping, mapping_values):
            report["mapping_updated"] += 1

    if missing_records:
        preview = ", ".join(missing_records[:10])
        raise RuntimeError(f"missing {len(missing_records)} warehouse records: {preview}")

    await db.flush()
    expected = bundle["expected"]
    if report["record_matched"] != int(expected["mappings"]):
        raise RuntimeError("warehouse record count does not match bundle")
    if apply:
        await db.commit()
    else:
        await db.rollback()
    return report


async def async_main(args: argparse.Namespace) -> None:
    bundle = load_bundle(args.bundle)
    async with SessionLocal() as db:
        report = await apply_bundle(db, bundle, args.apply)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
