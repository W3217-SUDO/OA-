"""财务旁表（慢查询 A3）：来源行增删改后旁表跟着变，到账来源查询读旁表的结果和按 JSON 现算一致。"""
import unittest

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import LegacyArPaymentField, LegacyFinanceRecord


def payment(legacy_id: str, payment_id: int, **extra) -> LegacyFinanceRecord:
    return LegacyFinanceRecord(source_table="FAM_AR_Payment", legacy_id=legacy_id, record_kind="ar_payment", is_active=True,
                               legacy_customer_no="", source_payload={"PaymentId": payment_id, "GroupId": 10, "PaymentModeName": "转账",
                                                                       "SettlementStatus": 2, **extra})


class SideTableTriggerTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def side_rows(self):
        async with self.sessions() as db:
            return {row.record_id: (row.legacy_id, bool(row.is_active), row.payment_id, row.group_id, row.payment_method,
                                    row.settlement_status, row.source_database)
                    for row in (await db.scalars(select(LegacyArPaymentField))).all()}

    async def test_side_table_follows_inserts_updates_and_deletes(self):
        async with self.sessions() as db:
            first, second = payment("1", 101), payment("2", 102, _source_database="hd")
            other = LegacyFinanceRecord(source_table="FAM_AR_Fee", legacy_id="9", record_kind="fee", is_active=True,
                                        legacy_customer_no="", source_payload={"PaymentId": 999})
            db.add_all([first, second, other])
            await db.commit()
            ids = (first.id, second.id, other.id)
        self.assertEqual(await self.side_rows(), {
            ids[0]: ("1", True, "101", "10", "转账", "2", None),
            ids[1]: ("2", True, "102", "10", "转账", "2", "hd"),
        })
        async with self.sessions() as db:
            row = await db.get(LegacyFinanceRecord, ids[0])
            row.source_payload = {**row.source_payload, "PaymentModeName": "现金"}
            row.is_active = False
            (await db.get(LegacyFinanceRecord, ids[2])).source_table = "FAM_AR_Payment"
            await db.delete(await db.get(LegacyFinanceRecord, ids[1]))
            await db.commit()
        rows = await self.side_rows()
        self.assertEqual(rows[ids[0]], ("1", False, "101", "10", "现金", "2", None))
        self.assertNotIn(ids[1], rows)
        self.assertEqual(rows[ids[2]][2], "999")
        # 改成别的来源表就从旁表移除
        async with self.engine.begin() as connection:
            await connection.execute(text("UPDATE legacy_finance_records SET source_table = 'FAM_OTHER' WHERE id = :id"), {"id": ids[0]})
        self.assertNotIn(ids[0], await self.side_rows())

    async def test_partial_create_without_side_table_does_not_install_triggers(self):
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        try:
            async with engine.begin() as connection:
                await connection.run_sync(lambda sync: Base.metadata.create_all(sync, tables=[LegacyFinanceRecord.__table__]))
            async with async_sessionmaker(engine, class_=AsyncSession)() as db:
                db.add(payment("1", 101))
                await db.commit()  # 没建旁表时不能因为触发器报错
        finally:
            await engine.dispose()


if __name__ == "__main__":
    unittest.main()
