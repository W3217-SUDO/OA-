import unittest
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import _next_investigation_clue_serial
from app.models import BusinessRecord


class InvestigationClueSerialRow4Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_new_system_numbers_start_above_the_legacy_sequence(self):
        """旧系统仍在发 M/P 共用流水；新系统每月从 8001 起编，不再接着旧号走（陶威 10-31 定）。"""
        async with self.sessions() as db:
            db.add_all([
                BusinessRecord(
                    module="clue", serial_no="M26085953", title="M clue",
                    customer="customer", status="草稿", owner="admin",
                    department="上海分所", data={},
                ),
                BusinessRecord(
                    module="clue", serial_no="P26085954", title="P clue",
                    customer="customer", status="草稿", owner="admin",
                    department="上海分所", data={},
                ),
            ])
            await db.commit()

            serial_no = await _next_investigation_clue_serial(
                db, datetime(2026, 8, 16, 12, 0, 0)
            )

        self.assertEqual(serial_no, "M26088001")
        self.assertEqual(len(serial_no), 9)
        async with self.sessions() as db:
            db.add(BusinessRecord(module="clue", serial_no="P26088001", title="P clue", customer="customer",
                                  status="草稿", owner="admin", department="上海分所", data={}))
            await db.commit()
            self.assertEqual(await _next_investigation_clue_serial(db, datetime(2026, 8, 16, 12, 0, 0)), "M26088002")


if __name__ == "__main__":
    unittest.main()
