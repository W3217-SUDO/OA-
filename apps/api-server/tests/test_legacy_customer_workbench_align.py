"""陶威 2026-10-31“要对齐”：「我的客户」和工作台按旧系统算法计算（旧系统 SQL 见共享笔记 legacy-customer-list-sql.md）。"""
import unittest
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.customer_fee_balance import customer_fee_balances, legacy_customer_event_counts, managed_customers_official_unreceived
from app.database import Base
from app.models import BusinessRecord, IncomingPayment, LegacyCustomerHistoryEvent, User


class LegacyCustomerWorkbenchAlignTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.sessions() as db:
            db.add(User(username="codexmgr", display_name="管理人", password_hash="isolated-only", department="CODEX", role="staff"))
            db.add(BusinessRecord(id=1, module="customer", serial_no="KH1", title="客户一", status="T", owner="codexsrc",
                                  data={"customer_managers": ["codexsrc"], "coordinators": ["codexmgr"]}))
            db.add(BusinessRecord(id=2, module="contract", serial_no="HT1", title="合同", status="已归档", owner="codexsrc",
                                  data={"customer_record_id": 1, "customer_no": "KH1"}))
            fees = [
                (11, "官方费用", "11010020", 1000),  # 付 1000，到账 300 → 未到 700
                (12, "官方费用", "11020065", 500),   # 付 0，到账 200 → -200 抵扣
                (13, "官方费用", "11010050", 400),   # 已登记已付但没有请款单 → 不算
                (14, "代理费", "11020010", 900),     # 代理费 900，到账 100 → 待收 800
                (15, "代理费", "11020050", 600),     # 不在旧系统代理费待收的四类里
            ]
            for fee_id, fee_type, code, amount in fees:
                db.add(BusinessRecord(id=fee_id, module="finance", serial_no=f"FY{fee_id}", title=fee_type, status="已通知",
                                      data={"contract_no": "HT1", "fee_type": fee_type, "case_fee_type_id": code,
                                            "amount": amount, "paid_amount": amount}))
            db.add(BusinessRecord(id=21, module="contract_payment", serial_no="P1", title="请款", status="已付款",
                                  data={"lines": [{"fee_record_id": 11, "case_fee_id": 11, "amount": 600},
                                                  {"fee_record_id": 11, "case_fee_id": 11, "amount": 400}]}))
            db.add(BusinessRecord(id=22, module="contract_payment", serial_no="P2", title="作废请款", status="已作废",
                                  data={"lines": [{"fee_record_id": 13, "amount": 400}]}))
            db.add(IncomingPayment(receipt_no="R1", received_date=datetime(2026, 1, 1).date(), amount=600, payer_name="客户一", operator="codexfin",
                                   status="已分配", allocations=[
                                       {"fee_record_id": 11, "amount": 300},
                                       {"settlement_items": [{"finance_record_id": 12, "amount": 200},
                                                             {"finance_record_id": 14, "amount": 100}]},
                                   ]))
            db.add(LegacyCustomerHistoryEvent(source_system="legacy_crm", source_table="CRM_Customer_Event", source_primary_key="1",
                                              legacy_customer_guid="G1", customer_record_id=1, content="客户重新分配给codexsrc.",
                                              operated_at=datetime(2025, 12, 1, tzinfo=timezone.utc)))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_unreceived_official_fee_uses_paid_requests_minus_receipts(self):
        async with self.sessions() as db:
            customer = await db.get(BusinessRecord, 1)
            balances = await customer_fee_balances(db, [customer])
            self.assertEqual(balances[1], {"official_fee_unreceived": 500.0, "agency_fee_due": 800.0})
            # 工作台“未到官费金额”= 本人是负责人或协作人的客户合计。
            self.assertEqual(await managed_customers_official_unreceived(db, "codexmgr"), 500.0)
            self.assertEqual(await managed_customers_official_unreceived(db, "nobody"), 0)

    async def test_contact_count_counts_legacy_customer_events(self):
        async with self.sessions() as db:
            self.assertEqual(await legacy_customer_event_counts(db, [1]), {1: 1})

    async def test_latest_case_manager_is_first_coordinator(self):
        from app.core.cases import _dashboard_latest_case_row
        async with self.sessions() as db:
            customer = await db.get(BusinessRecord, 1)
            case = BusinessRecord(id=31, module="case", serial_no="AJ1", title="案件", status="文书准备", owner="codexsrc",
                                  data={"customer_manager": "codexsrc"})
            row = _dashboard_latest_case_row(case, customer, {"codexmgr": await db.get(User, 1)})
            self.assertEqual(row["manager"], "管理人")


if __name__ == "__main__":
    unittest.main()
