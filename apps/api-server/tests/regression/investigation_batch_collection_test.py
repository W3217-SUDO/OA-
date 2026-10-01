import unittest
from datetime import date

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import ClueBatchCollectionInput, register_clue_collection_batch
from app.models import BusinessRecord, User, Warehouse, WarehouseStorageLocation


class InvestigationBatchCollectionTest(unittest.IsolatedAsyncioTestCase):
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

    async def _fixtures(self, second_status="待取证"):
        db = self.sessions()
        db.add(User(username="collector", display_name="取证员", department="调查部", password_hash="x", role="user"))
        warehouse = Warehouse(warehouse_no="BATCH-WH", name="批量仓", is_active=True)
        db.add(warehouse)
        await db.flush()
        location = WarehouseStorageLocation(warehouse_id=warehouse.id, storage_location_no="BATCH-LOC", name="一号位", is_active=True)
        db.add(location)
        clues = [
            BusinessRecord(module="clue", serial_no=f"CODEX-BATCH-{index}", title=f"批量线索{index}", customer="测试客户", status=status, owner="collector", department="调查部", data={})
            for index, status in enumerate(("待取证", second_status), 1)
        ]
        db.add_all(clues)
        await db.commit()
        return db, warehouse, location, clues

    async def test_batch_collection_updates_every_selected_clue(self):
        db, warehouse, location, clues = await self._fixtures()
        async with db:
            result = await register_clue_collection_batch(
                ClueBatchCollectionInput(clue_ids=[clue.id for clue in clues], collected_at=date.today(), notary_institution="批量取证机构", warehouse_id=warehouse.id, storage_location_id=location.id),
                {"username": "collector", "role": "user"}, db,
            )
            self.assertEqual(result["collected"], 2)
            self.assertEqual([clue.status for clue in clues], ["已取证", "已取证"])
            self.assertTrue(all((clue.data or {}).get("collection_evidence_record_id") for clue in clues))

    async def test_invalid_clue_rolls_back_entire_batch(self):
        db, warehouse, location, clues = await self._fixtures(second_status="草稿")
        async with db:
            with self.assertRaises(HTTPException) as raised:
                await register_clue_collection_batch(
                    ClueBatchCollectionInput(clue_ids=[clue.id for clue in clues], collected_at=date.today(), notary_institution="批量取证机构", warehouse_id=warehouse.id, storage_location_id=location.id),
                    {"username": "collector", "role": "user"}, db,
                )
            self.assertEqual(raised.exception.status_code, 409)
            await db.refresh(clues[0])
            self.assertEqual(clues[0].status, "待取证")


if __name__ == "__main__":
    unittest.main()
