from __future__ import annotations

import unittest

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.models import BusinessRecord, Warehouse, WarehouseEvidenceLocation, WarehouseLegacyEvidenceMapping, WarehouseStorageLocation
from scripts.apply_warehouse_relation_bundle import apply_bundle


class WarehouseRelationBundleTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(BusinessRecord(
                module="warehouse",
                serial_no="WMS-LEGACY-100",
                title="Legacy evidence",
                customer="",
                status="在库",
                owner="legacy",
                department="历史仓库",
                data={"legacy_evidence_id": 100},
            ))
            await db.commit()
        self.bundle = {
            "expected": {"warehouses": 1, "storage_locations": 1, "mappings": 1, "mapped": 1},
            "warehouses": [{
                "legacy_warehouse_id": 10,
                "warehouse_no": "WH-10",
                "name": "上海一仓",
                "address": "上海",
                "is_active": True,
                "sort_order": 1,
            }],
            "storage_locations": [{
                "legacy_storage_location_id": 20,
                "legacy_warehouse_id": 10,
                "storage_location_no": "LOC-20",
                "name": "1-1",
                "address": "",
                "is_active": True,
                "sort_order": 1,
            }],
            "mappings": [{
                "legacy_evidence_id": 100,
                "legacy_evidence_guid": "guid-100",
                "record_serial_no": "WMS-LEGACY-100",
                "legacy_warehouse_id": 10,
                "legacy_storage_location_id": 20,
                "mapping_status": "mapped",
                "reason": "",
                "source_snapshot": {"EvidenceId": 100},
            }],
        }

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def counts(self):
        async with self.sessions() as db:
            return {
                "warehouses": await db.scalar(select(func.count()).select_from(Warehouse)),
                "locations": await db.scalar(select(func.count()).select_from(WarehouseStorageLocation)),
                "bindings": await db.scalar(select(func.count()).select_from(WarehouseEvidenceLocation)),
                "mappings": await db.scalar(select(func.count()).select_from(WarehouseLegacyEvidenceMapping)),
            }

    async def test_dry_run_rolls_back_and_apply_is_repeatable(self):
        async with self.sessions() as db:
            dry = await apply_bundle(db, self.bundle, apply=False)
        self.assertFalse(dry["database_written"])
        self.assertEqual(await self.counts(), {"warehouses": 0, "locations": 0, "bindings": 0, "mappings": 0})

        async with self.sessions() as db:
            first = await apply_bundle(db, self.bundle, apply=True)
        self.assertEqual(first["record_matched"], 1)
        self.assertEqual(first["binding_inserted"], 1)
        self.assertEqual(first["mapping_inserted"], 1)
        self.assertEqual(await self.counts(), {"warehouses": 1, "locations": 1, "bindings": 1, "mappings": 1})

        async with self.sessions() as db:
            second = await apply_bundle(db, self.bundle, apply=True)
        self.assertEqual(second["warehouse_inserted"], 0)
        self.assertEqual(second["location_inserted"], 0)
        self.assertEqual(second["binding_inserted"], 0)
        self.assertEqual(second["mapping_inserted"], 0)
        self.assertEqual(await self.counts(), {"warehouses": 1, "locations": 1, "bindings": 1, "mappings": 1})


if __name__ == "__main__":
    unittest.main()
