"""BUG20261029003：待取证线索取证时证物存放处选填，没选也能登记已取证。"""

import unittest
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api_schemas.investigation import ClueCollectionInput
from app.database import Base
from app.models import BusinessRecord, User, Warehouse, WarehouseEvidenceLocation, WarehouseStorageLocation

IDENTITY = {"username": "r1029-003", "role": "admin", "display_name": "R003", "department": "调查部"}


class ClueCollectionStorageOptionalTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name="R003", department="调查部", role="admin",
                        password_hash="x", is_active=True))
            self.clues = []
            for index in range(2):
                clue = BusinessRecord(module="clue", serial_no=f"XS-R003-{index}", title=f"线索{index}", status="待取证",
                                      owner=IDENTITY["username"], department="调查部", data={})
                db.add(clue)
                self.clues.append(clue)
            warehouse = Warehouse(warehouse_no="CK-R003", name="一号仓", is_active=True)
            db.add(warehouse)
            await db.flush()
            location = WarehouseStorageLocation(warehouse_id=warehouse.id, storage_location_no="KW-R003", name="A01", is_active=True)
            db.add(location)
            await db.flush()
            self.warehouse_id, self.location_id = warehouse.id, location.id
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_collect_without_storage_location(self):
        from app.core.investigation import _register_clue_collection

        async with self.sessions() as db:
            body = ClueCollectionInput(collected_at=date.today(), notary_institution="上海公证处")
            clue = await _register_clue_collection(self.clues[0].id, body, IDENTITY, db)
            await db.commit()
            self.assertEqual(clue.status, "已取证")
            self.assertEqual(clue.data["storage_location"], "")
            self.assertNotIn("storage_location_id", clue.data)
            self.assertIsNone(await db.scalar(select(WarehouseEvidenceLocation.id)))

    async def test_collect_with_storage_location_still_binds(self):
        from app.core.investigation import _register_clue_collection

        async with self.sessions() as db:
            body = ClueCollectionInput(collected_at=date.today(), notary_institution="上海公证处",
                                       warehouse_id=self.warehouse_id, storage_location_id=self.location_id)
            clue = await _register_clue_collection(self.clues[1].id, body, IDENTITY, db)
            await db.commit()
            self.assertEqual(clue.data["storage_location_id"], self.location_id)
            self.assertIsNotNone(await db.scalar(select(WarehouseEvidenceLocation.id)))


if __name__ == "__main__":
    unittest.main()
