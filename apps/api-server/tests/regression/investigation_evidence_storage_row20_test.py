import unittest
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import (
    ClueCollectionInput,
    _warehouse_evidence_location_statement,
    register_clue_collection,
)
from app.models import BusinessRecord, User, Warehouse, WarehouseEvidenceLocation, WarehouseStorageLocation


class InvestigationEvidenceStorageRow20Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_collection_evidence_is_bound_to_selected_warehouse_leaf(self):
        async with self.sessions() as db:
            db.add(User(username="collector", display_name="取证员", department="调查部", password_hash="x", role="user"))
            warehouse = Warehouse(warehouse_no="ROW20-WH", name="上海一仓", is_active=True)
            db.add(warehouse)
            await db.flush()
            location = WarehouseStorageLocation(
                warehouse_id=warehouse.id, storage_location_no="ROW20-LOC", name="1-1", is_active=True
            )
            db.add(location)
            clue = BusinessRecord(
                module="clue", serial_no="M26085930", title="第20行线索", customer="客户",
                status="待取证", owner="collector", department="调查部", data={},
            )
            db.add(clue)
            await db.commit()

            result = await register_clue_collection(
                clue.id,
                ClueCollectionInput(
                    notary_institution="取证机构", collected_at=date.today(),
                    warehouse_id=warehouse.id, storage_location_id=location.id,
                ),
                {"username": "collector", "role": "user"},
                db,
            )
            evidence_id = result["data"]["collection_evidence_record_id"]
            binding = await db.scalar(select(WarehouseEvidenceLocation).where(
                WarehouseEvidenceLocation.record_id == evidence_id
            ))
            warehouse_rows = (await db.execute(
                _warehouse_evidence_location_statement([]).where(
                    WarehouseEvidenceLocation.warehouse_id == warehouse.id,
                    WarehouseEvidenceLocation.storage_location_id == location.id,
                )
            )).all()

        self.assertIsNotNone(binding)
        self.assertEqual(binding.warehouse_id, warehouse.id)
        self.assertEqual(binding.storage_location_id, location.id)
        self.assertEqual([row[0].id for row in warehouse_rows], [evidence_id])


if __name__ == "__main__":
    unittest.main()
