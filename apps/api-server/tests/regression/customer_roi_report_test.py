import unittest
from datetime import date

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import _customer_roi_analytics
from app.models import BusinessRecord, FinanceTransaction, IncomingPayment, User


ADMIN = {"username": "admin", "role": "admin"}


class CustomerRoiReportTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _seed(self, db: AsyncSession):
        customer_a = BusinessRecord(module="customer", serial_no="CODEX-ROI-CUSTOMER-A", title="同名客户", customer="同名客户", status="正常", owner="owner-a", department="华东部", data={})
        customer_b = BusinessRecord(module="customer", serial_no="CODEX-ROI-CUSTOMER-B", title="同名客户", customer="同名客户", status="正常", owner="owner-b", department="华南部", data={})
        db.add_all([customer_a, customer_b])
        await db.flush()
        contract_a = BusinessRecord(module="contract", serial_no="CODEX-ROI-CONTRACT-A", title="合同A", customer="同名客户", status="审批通过", owner="income-owner", department="华东部", data={"customer_id": customer_a.id, "customer_no": customer_a.serial_no})
        contract_b = BusinessRecord(module="contract", serial_no="CODEX-ROI-CONTRACT-B", title="合同B", customer="同名客户", status="审批通过", owner="other-owner", department="华南部", data={"customer_id": customer_b.id, "customer_no": customer_b.serial_no})
        db.add_all([contract_a, contract_b])
        await db.flush()
        fee_a = BusinessRecord(module="finance", serial_no="CODEX-ROI-FEE-A", title="费用A", customer="同名客户", status="已付款", owner="cost-owner", department="华东部", data={"contract_id": contract_a.id, "contract_no": contract_a.serial_no})
        fee_b = BusinessRecord(module="finance", serial_no="CODEX-ROI-FEE-B", title="费用B", customer="同名客户", status="已付款", owner="other-owner", department="华南部", data={"contract_id": contract_b.id, "contract_no": contract_b.serial_no})
        # This is the real record shape written by
        # pay_contract_payment_application: its settled outflow must count once.
        contract_payment_a = BusinessRecord(module="contract_payment", serial_no="CODEX-ROI-CONTRACT-PAYMENT-A", title="合同付款A", customer="同名客户", status="已付款", owner="income-owner", department="华东部", data={"contract_id": contract_a.id, "contract_no": contract_a.serial_no, "amount": 50})
        # This finance row has only a copied name.  It must never be merged into
        # either same-named customer.
        ambiguous_fee = BusinessRecord(module="finance", serial_no="CODEX-ROI-FEE-AMB", title="费用歧义", customer="同名客户", status="已付款", owner="cost-owner", department="华东部", data={})
        db.add_all([fee_a, fee_b, contract_payment_a, ambiguous_fee])
        await db.flush()
        db.add_all([
            FinanceTransaction(finance_record_id=contract_a.id, transaction_type="回款", amount=300, transaction_date=date(2026, 9, 1), operator="admin"),
            FinanceTransaction(finance_record_id=fee_a.id, transaction_type="付款", amount=100, transaction_date=date(2026, 9, 2), operator="admin"),
            FinanceTransaction(finance_record_id=contract_payment_a.id, transaction_type="合同付款", amount=50, transaction_date=date(2026, 9, 2), operator="admin"),
            FinanceTransaction(finance_record_id=contract_b.id, transaction_type="回款", amount=50, transaction_date=date(2026, 9, 2), operator="admin"),
            FinanceTransaction(finance_record_id=fee_b.id, transaction_type="付款", amount=20, transaction_date=date(2026, 8, 31), operator="admin"),
            FinanceTransaction(finance_record_id=ambiguous_fee.id, transaction_type="付款", amount=999, transaction_date=date(2026, 9, 2), operator="admin"),
            FinanceTransaction(finance_record_id=fee_a.id, transaction_type="开票", amount=777, transaction_date=date(2026, 9, 2), operator="admin"),
        ])
        await db.commit()
        return customer_a, customer_b

    async def test_groups_by_customer_id_uses_posted_cash_and_returns_null_roi_for_zero_cost(self):
        async with self.sessions() as db:
            customer_a, customer_b = await self._seed(db)
            result = await _customer_roi_analytics(ADMIN, db, date_from=date(2026, 9, 1), date_to=date(2026, 9, 2))

        self.assertEqual(result["date_basis"], "收付款流水日期、到账日期")
        self.assertEqual(len(result["rows"]), 2)
        by_customer = {row["customer_id"]: row for row in result["rows"]}
        self.assertEqual(by_customer[customer_a.id]["income"], 300)
        self.assertEqual(by_customer[customer_a.id]["cost"], 150)
        self.assertEqual(by_customer[customer_a.id]["profit"], 150)
        self.assertEqual(by_customer[customer_a.id]["roi"], 100)
        self.assertEqual(by_customer[customer_b.id]["income"], 50)
        self.assertEqual(by_customer[customer_b.id]["cost"], 0)
        self.assertIsNone(by_customer[customer_b.id]["roi"])
        self.assertEqual(result["totals"], {"income": 350, "cost": 150, "profit": 200, "roi": round(200 / 150 * 100, 2)})

    async def test_department_and_employee_filters_only_use_visible_settled_sources(self):
        async with self.sessions() as db:
            await self._seed(db)
            by_department = await _customer_roi_analytics(ADMIN, db, department="华东部")
            by_employee = await _customer_roi_analytics(ADMIN, db, employee="cost-owner")

        self.assertEqual(by_department["totals"]["income"], 300)
        self.assertEqual(by_department["totals"]["cost"], 150)
        self.assertEqual(by_employee["totals"]["income"], 0)
        self.assertEqual(by_employee["totals"]["cost"], 100)
        self.assertEqual(by_employee["filter_options"]["departments"], ["华东部", "华南部"])

    async def test_department_scope_and_amount_permission_do_not_leak_rows(self):
        async with self.sessions() as db:
            await self._seed(db)
            db.add_all([
                User(username="manager-east", display_name="东区负责人", password_hash="unused", role="manager", department="华东部", is_active=True, profile={}),
                User(username="ordinary", display_name="普通用户", password_hash="unused", role="user", department="华东部", is_active=True, profile={}),
            ])
            await db.commit()
            scoped = await _customer_roi_analytics({"username": "manager-east", "role": "manager"}, db)
            with self.assertRaises(HTTPException) as error:
                await _customer_roi_analytics({"username": "ordinary", "role": "user"}, db)

        self.assertEqual(scoped["totals"], {"income": 300, "cost": 150, "profit": 150, "roi": 100})
        self.assertEqual(error.exception.status_code, 403)

    async def test_bank_receipts_count_as_income_by_allocation_then_claimed_customer(self):
        # BUG 500784：收入原来只取“回款”流水，迁来的到账单（按分配的案件/合同）全漏了。
        async with self.sessions() as db:
            customer_a, _customer_b = await self._seed(db)
            customer_c = BusinessRecord(module="customer", serial_no="CODEX-ROI-CUSTOMER-C", title="独立客户", customer="独立客户", status="正常", owner="owner-c", department="华北部", data={})
            db.add(customer_c)
            await db.flush()
            case_a = BusinessRecord(module="case", serial_no="CODEX-ROI-CASE-A", title="案件A", customer="同名客户", status="办理中", owner="case-owner", department="华东部", data={"customer_id": customer_a.id, "customer_no": customer_a.serial_no})
            db.add(case_a)
            await db.flush()
            db.add_all([
                IncomingPayment(source_kind="hz_crm_20260930", receipt_no="R-1", received_date=date(2026, 9, 1), amount=1000, payer_name="同名客户",
                                status="已分配", claimed_customer="同名客户", allocated_amount=1000, operator="admin",
                                allocations=[{"amount": 800, "case_id": case_a.id, "case_no": case_a.serial_no},
                                             {"amount": 200, "case_no": "CODEX-ROI-CASE-A", "is_refund": True}]),
                IncomingPayment(source_kind="hz_crm_20260930", receipt_no="R-2", received_date=date(2026, 9, 2), amount=500, payer_name="独立客户",
                                status="待分配", claimed_customer="独立客户", allocated_amount=0, operator="admin", allocations=[]),
                IncomingPayment(source_kind="hz_crm_20260930", receipt_no="R-3", received_date=date(2026, 9, 2), amount=70, payer_name="同名客户",
                                status="待分配", claimed_customer="同名客户", allocated_amount=0, operator="admin", allocations=[]),
                IncomingPayment(source_kind="bank_import", receipt_no="R-4", received_date=date(2026, 10, 9), amount=90, payer_name="独立客户",
                                status="待分配", claimed_customer="独立客户", allocated_amount=0, operator="admin", allocations=[]),
            ])
            await db.commit()
            result = await _customer_roi_analytics(ADMIN, db, date_from=date(2026, 9, 1), date_to=date(2026, 9, 2))
            by_department = await _customer_roi_analytics(ADMIN, db, date_from=date(2026, 9, 1), date_to=date(2026, 9, 2), department="华北部")

        by_customer = {row["customer_id"]: row for row in result["rows"]}
        # 300 回款流水 + 到账单分配 800 - 退款 200；同名客户的未分配到账（R-3）认领名不唯一，不计入。
        self.assertEqual(by_customer[customer_a.id]["income"], 900)
        self.assertEqual(by_customer[customer_c.id]["income"], 500)  # 未分配，归认领客户；R-4 在日期范围外
        self.assertIn("case-owner", by_customer[customer_a.id]["employee"])
        self.assertEqual(by_department["totals"]["income"], 500)

    async def test_employee_column_shows_person_names(self):
        # BUG 500787：员工列显示姓名，不显示登录账号；筛选项仍是账号。
        from app.core.person_names import refresh_person_names
        async with self.sessions() as db:
            await self._seed(db)
            db.add_all([User(username="owner-a", display_name="陈律师", password_hash="x", role="staff"),
                        User(username="cost-owner", display_name="罗会计", password_hash="x", role="staff")])
            await db.commit()
            await refresh_person_names(db, force=True)
            result = await _customer_roi_analytics(ADMIN, db)
        employees = "、".join(row["employee"] for row in result["rows"])
        self.assertNotIn("owner-a", employees)
        self.assertNotIn("cost-owner", employees)
        self.assertIn("罗会计", employees)
        self.assertIn("cost-owner", result["filter_options"]["employees"])

    async def test_prewarm_replay_recomputes_same_report(self):
        from app.areas.rpt.router import _replay_customer_roi
        from app.core import query_prewarm
        self.assertIn("reports", query_prewarm._replayers)
        async with self.sessions() as db:
            await self._seed(db)
            await _replay_customer_roi("customer_roi", ADMIN, {"date_from": "2026-09-01", "date_to": None, "department": "", "employee": ""}, db)
            with self.assertRaises(ValueError):
                await _replay_customer_roi("other", ADMIN, {}, db)


if __name__ == "__main__":
    unittest.main()
