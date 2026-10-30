"""律所/平台按老系统 GroupId 分开（陶威 2026-10-30）：费用、发票看自己的 GroupId，请款单看合同的，0 两边都不显示。"""
import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.finance_centers import filter_rows_by_center, finance_centers_for_ids, record_center_values
from app.database import Base
from app.models import BusinessRecord


def record(module, serial, data):
    return BusinessRecord(module=module, serial_no=serial, title=serial, customer="客户", status="待审批",
                          owner="admin", department="上海", data=data)


class FinanceCenterGroupIdTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_centers_follow_legacy_group(self):
        async with self.sessions() as db:
            platform_contract = record("contract", "HT-P", {"group_id": 20})
            firm_contract = record("contract", "HT-F", {"group_id": 10})
            db.add_all([platform_contract, firm_contract])
            await db.flush()
            rows = {
                "platform_fee": record("finance", "FEE-P", {"group_id": 20, "expense_scope": "律所"}),
                "firm_fee": record("finance", "FEE-F", {"group_id": 10, "expense_scope": "律所"}),
                "zero_fee": record("finance", "FEE-0", {"group_id": 0, "expense_scope": "律所"}),
                "new_platform_fee": record("finance", "FEE-NEW", {"expense_scope": "平台"}),
                "platform_invoice": record("invoice", "INV-P", {"group_id": 20}),
                "platform_payment": record("contract_payment", "P-P", {"contract_record_id": platform_contract.id}),
                "firm_payment": record("contract_payment", "P-F", {"contract_record_id": firm_contract.id}),
                "orphan_payment": record("contract_payment", "P-X", {"contract_record_id": 999999}),
            }
            db.add_all(rows.values())
            await db.commit()
            centers = await finance_centers_for_ids(db, [row.id for row in rows.values()])
            self.assertEqual({name: centers[row.id] for name, row in rows.items()}, {
                "platform_fee": "platform", "firm_fee": "firm", "zero_fee": None, "new_platform_fee": "platform",
                "platform_invoice": "platform", "platform_payment": "platform", "firm_payment": "firm",
                "orphan_payment": "firm",
            })
            items = [{"id": row.id} for row in rows.values()]
            platform = await filter_rows_by_center(items, {"_finance_scope": "platform"}, db)
            self.assertEqual(len(platform), 4)
            self.assertEqual(len(await filter_rows_by_center(items, {}, db)), len(items))
            self.assertEqual(record_center_values(rows["platform_fee"]), {"platform"})
            self.assertEqual(record_center_values(rows["zero_fee"]), set())


if __name__ == "__main__":
    unittest.main()
