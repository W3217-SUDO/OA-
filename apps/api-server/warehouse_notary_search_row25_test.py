"""Regression coverage for 8.28 row 25 warehouse notary-number search."""

import os
import tempfile
import unittest
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


_TEMP_DIR = tempfile.TemporaryDirectory()
_DB_PATH = Path(_TEMP_DIR.name) / "warehouse-row25.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB_PATH.as_posix()}"

from app.database import Base
from app.main import list_warehouse_evidence
from app.models import BusinessRecord, Warehouse, WarehouseEvidenceLocation, WarehouseStorageLocation


class WarehouseNotarySearchRow25Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(os.environ["DATABASE_URL"])
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await self.engine.dispose()

    async def _fixtures(self):
        async with self.sessions() as db:
            warehouse = Warehouse(warehouse_no="R25-WH", name="Row25 Warehouse", is_active=True)
            db.add(warehouse)
            await db.flush()
            location = WarehouseStorageLocation(
                warehouse_id=warehouse.id,
                storage_location_no="R25-L01",
                name="Row25 Location",
                is_active=True,
            )
            db.add(location)
            await db.flush()
            records = [
                BusinessRecord(module="warehouse", serial_no="R25-NOTARY", title="A", status="in", owner="admin", data={"notary_no": "R25-3333"}),
                BusinessRecord(module="warehouse", serial_no="R25-NOTARY-NOS", title="B", status="in", owner="admin", data={"notary_nos": "R25-3333-SECOND,R25-OTHER"}),
                BusinessRecord(module="warehouse", serial_no="R25-CERTIFICATE", title="C", status="in", owner="admin", data={"certificate_no": "R25-CERT-3333"}),
                BusinessRecord(module="warehouse", serial_no="R25-DECOY", title="D", status="in", owner="admin", data={"notary_no": "R25-9999"}),
            ]
            db.add_all(records)
            await db.flush()
            db.add_all([
                WarehouseEvidenceLocation(
                    record_id=record.id,
                    warehouse_id=warehouse.id,
                    storage_location_id=location.id,
                    assigned_by="admin",
                )
                for record in records
            ])
            await db.commit()
            return warehouse.id, location.id

    async def test_notary_search_accepts_migrated_aliases_and_returns_location(self):
        warehouse_id, location_id = await self._fixtures()
        async with self.sessions() as db:
            result = await list_warehouse_evidence(
                page=1,
                page_size=15,
                warehouse_id=None,
                storage_location_id=None,
                keyword="",
                rights_holder="",
                evidence_status="",
                case_no="",
                shop_name="",
                investigator="",
                notary_no="3333",
                evidence_date_from="",
                evidence_date_to="",
                identity={"username": "admin", "role": "admin", "role_ids": ["admin"]},
                db=db,
            )
        self.assertEqual(result["total"], 3)
        self.assertEqual(
            {item["serial_no"] for item in result["items"]},
            {"R25-NOTARY", "R25-NOTARY-NOS", "R25-CERTIFICATE"},
        )
        for item in result["items"]:
            self.assertEqual(item["data"]["warehouse_id"], warehouse_id)
            self.assertEqual(item["data"]["storage_location_id"], location_id)
            self.assertEqual(item["data"]["location"], "Row25 Location")
            self.assertIn("3333", item["data"]["notary_no"])


if __name__ == "__main__":
    unittest.main()
