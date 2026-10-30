"""BUG20261030003（范明明 2026-10-30）：请款单审批类型只留勾选的官方费用和其他费用；待缴官费同一口径。"""
import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.contract_payment_lifecycle import attach_line_expense_subtypes, payment_audit_type_visible
from app.core.dashboard_list_counts import payment_audit_official_total
from app.database import Base
from app.models import BusinessRecord, User

IDENTITY = {"username": "admin", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"]}
APPLIED = {"payment_applied_at": "2026-10-29"}


def record(module, serial, status, data):
    return BusinessRecord(module=module, serial_no=serial, title=serial, customer="客户", status=status,
                          owner="admin", department="上海", data=data)


class PaymentAuditTypesTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def asyncTearDown(self):
        await self.engine.dispose()

    def test_visible_types(self):
        self.assertTrue(payment_audit_type_visible("finance", {"fee_type": "官方费用", "expense_subtype": "一审诉讼费"}))
        self.assertTrue(payment_audit_type_visible("finance", {"fee_type": "其他费用", "expense_subtype": "差旅费"}))
        self.assertFalse(payment_audit_type_visible("finance", {"fee_type": "官方费用", "expense_subtype": "核定成本"}))
        self.assertFalse(payment_audit_type_visible("finance", {"fee_type": "官方费用", "fee_type_name": "官费"}))
        self.assertFalse(payment_audit_type_visible("finance", {"fee_type": "代理费"}))
        self.assertFalse(payment_audit_type_visible("contract_payment", {"lines": [{"fee_type": "官方费用", "expense_subtype": "核定成本"}]}))
        self.assertTrue(payment_audit_type_visible("contract_payment", {"lines": [{"fee_type": "官方费用", "expense_subtype": "保全费"}]}))

    async def test_count_uses_checked_official_subtypes(self):
        async with self.sessions() as db:
            db.add(User(username="admin", display_name="管理者", department="上海", password_hash="test", role="admin", is_active=True))
            cost = record("finance", "CASEFEE-COST", "已登记", {"fee_type": "官方费用", "expense_subtype": "核定成本"})
            bail = record("finance", "CASEFEE-BAIL", "已登记", {"fee_type": "官方费用", "expense_subtype": "保全费"})
            db.add_all([cost, bail])
            await db.flush()
            db.add_all([
                record("finance", "FY-SUIT", "待审批", {"fee_type": "官方费用", "expense_subtype": "一审诉讼费", **APPLIED}),
                record("finance", "FY-GUANFEI", "待审批", {"fee_type": "官方费用", "expense_subtype": "官费", **APPLIED}),
                record("finance", "FY-OTHER", "待审批", {"fee_type": "其他费用", "expense_subtype": "差旅费", **APPLIED}),
                record("contract_payment", "P-COST", "待审批", {"lines": [{"fee_type": "官方费用", "case_fee_id": cost.id}]}),
                record("contract_payment", "P-BAIL", "待审批", {"lines": [{"fee_type": "官方费用", "case_fee_id": bail.id}]}),
            ])
            await db.commit()
            self.assertEqual(await payment_audit_official_total(IDENTITY, db), 2)
            items = [{"module": "contract_payment", "data": {"lines": [{"fee_type": "官方费用", "case_fee_id": cost.id}]}}]
            await attach_line_expense_subtypes(items, db)
            self.assertEqual(items[0]["data"]["lines"][0]["expense_subtype"], "核定成本")


if __name__ == "__main__":
    unittest.main()
