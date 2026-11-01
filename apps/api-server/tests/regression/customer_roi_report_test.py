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
            # 收入按开给客户的发票算（思法汇成 11-01）；上面的“回款”流水不再计入收入。
            self._invoice("INV-A", customer_a, 300, "2026-09-01T10:00:00", "华东部"),
            self._invoice("INV-B", customer_b, 50, "2026-09-02T10:00:00", "华南部"),
        ])
        await db.commit()
        return customer_a, customer_b

    @staticmethod
    def _invoice(serial_no, customer, amount, invoice_date, department, title=None, status="已开票", case_id=None):
        return BusinessRecord(module="invoice", serial_no=serial_no, title="发票", customer=customer.title, status=status,
                              owner="invoice-owner", department=department,
                              data={"amount": amount, "customer_record_id": customer.id, "customer_no": customer.serial_no,
                                    "invoice_title": title or customer.title, "invoice_date": invoice_date,
                                    "case_ids": [case_id] if case_id else []})

    async def test_groups_by_customer_id_uses_posted_cash_and_returns_null_roi_for_zero_cost(self):
        async with self.sessions() as db:
            customer_a, customer_b = await self._seed(db)
            result = await _customer_roi_analytics(ADMIN, db, date_from=date(2026, 9, 1), date_to=date(2026, 9, 2))

        self.assertEqual(result["date_basis"], "开票日期、到账日期、付款日期")
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

    async def test_income_is_customer_invoices_plus_court_refunds_only(self):
        # 思法汇成 11-01：收入 = 开给客户的发票（不含作废、不含公司之间的发票）+ 法院退费；到账单其余部分（含赔偿款）不算。
        async with self.sessions() as db:
            customer_a, _customer_b = await self._seed(db)
            case_a = BusinessRecord(module="case", serial_no="CODEX-ROI-CASE-A", title="案件A", customer="同名客户", status="办理中", owner="case-owner", department="华东部", data={"customer_id": customer_a.id, "customer_no": customer_a.serial_no})
            db.add(case_a)
            await db.flush()
            db.add_all([
                self._invoice("INV-A2", customer_a, 1000, "2026-09-02T09:00:00", "华东部", case_id=case_a.id),
                self._invoice("INV-VOID", customer_a, 5000, "2026-09-02T09:00:00", "华东部", status="已作废"),
                self._invoice("INV-INT", customer_a, 6246, "2026-09-02T09:00:00", "华东部", title="上海恒达知识产权代理有限公司"),
                self._invoice("INV-LATE", customer_a, 7000, "2026-10-09T09:00:00", "华东部"),
                IncomingPayment(source_kind="hz_crm_20260930", receipt_no="R-PAY", received_date=date(2026, 9, 1), amount=36650, payer_name="姚志富",
                                status="已分配", claimed_customer="同名客户", allocated_amount=36650, operator="admin",
                                allocations=[{"amount": 34700, "case_id": case_a.id, "case_no": case_a.serial_no},
                                             {"amount": 1950, "case_id": case_a.id, "case_no": case_a.serial_no}]),
                IncomingPayment(source_kind="hz_crm_20260930", receipt_no="R-COURT", received_date=date(2026, 9, 2), amount=1650, payer_name="某中级人民法院",
                                status="已分配", claimed_customer="同名客户", allocated_amount=1650, operator="admin",
                                allocations=[{"amount": 1650, "case_id": case_a.id, "case_no": case_a.serial_no, "is_refund": True}]),
            ])
            await db.commit()
            result = await _customer_roi_analytics(ADMIN, db, date_from=date(2026, 9, 1), date_to=date(2026, 9, 2))
        by_customer = {row["customer_id"]: row for row in result["rows"]}
        # 发票 300 + 1000，法院退费 1650；赔偿款到账、作废、公司间发票、日期外发票都不算。
        self.assertEqual(by_customer[customer_a.id]["income"], 2950)
        self.assertEqual(by_customer[customer_a.id]["cost"], 150)
        self.assertIn("case-owner", by_customer[customer_a.id]["employee"])

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
