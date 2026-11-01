import unittest
from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
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
        contract_a = BusinessRecord(module="contract", serial_no="CODEX-ROI-CONTRACT-A", title="合同A", customer="同名客户", status="审批通过", owner="income-owner", department="华东部", data={"contract_type": "框架合作合同", "customer_id": customer_a.id, "customer_no": customer_a.serial_no})
        contract_b = BusinessRecord(module="contract", serial_no="CODEX-ROI-CONTRACT-B", title="合同B", customer="同名客户", status="审批通过", owner="other-owner", department="华南部", data={"contract_type": "框架合作合同", "customer_id": customer_b.id, "customer_no": customer_b.serial_no})
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
            # 收入按代理费到账算（思法汇成 11-01）；上面的“回款”流水不再计入收入。
            self._receipt("R-A", 300, "2026-09-01", "同名客户", [{"amount": 300, "contract_no": contract_a.serial_no, "fee_type": "代理费"}]),
            self._receipt("R-B", 50, "2026-09-02", "同名客户", [{"amount": 50, "contract_no": contract_b.serial_no, "fee_type": "代理费"}]),
        ])
        await db.commit()
        return customer_a, customer_b

    @staticmethod
    def _receipt(receipt_no, amount, received, payer, allocations, claimed="同名客户"):
        return IncomingPayment(source_kind="hz_crm_20260930", receipt_no=receipt_no, received_date=date.fromisoformat(received), amount=amount,
                               payer_name=payer, status="已分配", claimed_customer=claimed, allocated_amount=amount, operator="admin",
                               allocations=allocations)

    async def test_groups_by_customer_id_uses_posted_cash_and_returns_null_roi_for_zero_cost(self):
        async with self.sessions() as db:
            customer_a, customer_b = await self._seed(db)
            result = await _customer_roi_analytics(ADMIN, db, date_from=date(2026, 9, 1), date_to=date(2026, 9, 2))

        self.assertEqual(result["date_basis"], "到账日期、付款日期")
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

    async def test_income_is_agency_fee_received_without_internal_duplicates(self):
        # 思法汇成 11-01 13:18：收入按代理费到账算；公司之间转款不重复算，赔偿款转到平台后的平台代理费算一次。
        async with self.sessions() as db:
            customer_a, _customer_b = await self._seed(db)
            contract_a = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == "CODEX-ROI-CONTRACT-A"))
            case_x = BusinessRecord(module="case", serial_no="CODEX-ROI-CASE-X", title="直接付代理费", customer="同名客户", status="办理中", owner="case-owner", department="华东部", data={"customer_id": customer_a.id, "contract_record_id": contract_a.id})
            case_y = BusinessRecord(module="case", serial_no="CODEX-ROI-CASE-Y", title="被告赔偿款", customer="同名客户", status="已归档", owner="case-owner", department="华东部", data={"customer_id": customer_a.id, "contract_record_id": contract_a.id})
            db.add_all([case_x, case_y])
            await db.flush()
            platform_fee = BusinessRecord(module="finance", serial_no="F-PLAT", title="平台代理费", customer="同名客户", status="已通知", owner="x", department="华东部", data={})
            lawyer_fee = BusinessRecord(module="finance", serial_no="F-LAW", title="律师代理费", customer="同名客户", status="已通知", owner="x", department="华东部", data={})
            platform_fee_x = BusinessRecord(module="finance", serial_no="F-PLAT-X", title="平台代理费", customer="同名客户", status="已通知", owner="x", department="华东部", data={})
            db.add_all([platform_fee, lawyer_fee, platform_fee_x])
            await db.flush()
            x, y = {"case_id": case_x.id, "case_no": case_x.serial_no}, {"case_id": case_y.id, "case_no": case_y.serial_no}
            db.add_all([
                # 案件 X：客户直接付代理费 1000；律所再转给恒达 400（同一笔钱，不算）。
                self._receipt("R-X1", 1000, "2026-09-01", "同名客户", [{"amount": 1000, "fee_type": "代理费", **x}]),
                self._receipt("R-X2", 400, "2026-09-02", "上海恒达知识产权代理有限公司", [{"amount": 400, "fee_type": "代理费", "fee_id": platform_fee_x.id, **x}]),
                # 案件 Y（味好美实例）：替被告付款 36,650（官费 1,950 + 赔偿款 34,700）→ 国定转平台：平台代理费 30,290 + 权利人分成 4,410
                # → 恒达转律所：律师代理费 6,246（平台代理费的一部分）。只算平台代理费 30,290。
                self._receipt("R-Y1", 36650, "2026-09-01", "姚志富", [{"amount": 1950, "fee_type": "官方费用", **y}, {"amount": 34700, "fee_type": "其他费用", **y}]),
                self._receipt("R-Y2", 34700, "2026-09-02", "上海国定律师事务所 ", [{"amount": 30290, "fee_type": "代理费", "fee_id": platform_fee.id, **y}, {"amount": 4410, "fee_type": "其他费用", **y}]),
                self._receipt("R-Y3", 6246, "2026-09-02", "上海恒达知识产权代理有限公司", [{"amount": 6246, "fee_type": "代理费", "fee_id": lawyer_fee.id, **y}]),
                # 法院退费算收入；公司之间转款里标的退费不算。
                self._receipt("R-Y4", 1650, "2026-09-02", "江苏省泰州市中级人民法院", [{"amount": 1650, "fee_type": "官方费用", "is_refund": True, **y}]),
                self._receipt("R-Y5", 882, "2026-09-02", "上海恒达知识产权代理有限公司", [{"amount": 882, "fee_type": "官方费用", "is_refund": True, **y}]),
            ])
            await db.commit()
            result = await _customer_roi_analytics(ADMIN, db, date_from=date(2026, 9, 1), date_to=date(2026, 9, 2))
        by_customer = {row["customer_id"]: row for row in result["rows"]}
        # 种子代理费 300 + X 1000 + Y 平台代理费 30290 + 法院退费 1650
        self.assertEqual(by_customer[customer_a.id]["income"], 33240)
        self.assertEqual(by_customer[customer_a.id]["cost"], 150)

    async def test_cost_excludes_internal_company_and_customer_payees(self):
        # 思法汇成 11-01 13:42：成本去掉付给沪知/恒达/国定的公司之间付款，以及付给客户本身的权利人分成、赔偿款转付。
        async with self.sessions() as db:
            customer_a, _customer_b = await self._seed(db)
            contract_a = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == "CODEX-ROI-CONTRACT-A"))
            link = {"contract_id": contract_a.id, "contract_no": contract_a.serial_no}
            to_hengda = BusinessRecord(module="contract_payment", serial_no="CP-HD", title="付恒达", customer="同名客户", status="已付款", owner="x", department="华东部", data={**link, "payee": "上海恒达知识产权代理有限公司"})
            to_customer = BusinessRecord(module="contract_payment", serial_no="CP-KH", title="权利人分成", customer="同名客户", status="已付款", owner="x", department="华东部", data={**link, "payee": "同名客户（代收代付）"})
            to_court = BusinessRecord(module="contract_payment", serial_no="CP-FY", title="诉讼费", customer="同名客户", status="已付款", owner="x", department="华东部", data={**link, "payee": "某某人民法院"})
            db.add_all([to_hengda, to_customer, to_court])
            await db.flush()
            db.add_all([
                FinanceTransaction(finance_record_id=to_hengda.id, transaction_type="合同付款", amount=500, transaction_date=date(2026, 9, 2), operator="admin"),
                FinanceTransaction(finance_record_id=to_customer.id, transaction_type="合同付款", amount=700, transaction_date=date(2026, 9, 2), operator="admin"),
                FinanceTransaction(finance_record_id=to_court.id, transaction_type="合同付款", amount=90, transaction_date=date(2026, 9, 2), operator="admin"),
            ])
            await db.commit()
            result = await _customer_roi_analytics(ADMIN, db, date_from=date(2026, 9, 1), date_to=date(2026, 9, 2))
        by_customer = {row["customer_id"]: row for row in result["rows"]}
        self.assertEqual(by_customer[customer_a.id]["cost"], 240)  # 原 150 + 付法院 90；付恒达、付客户本身不算

    async def test_overdue_deduction_is_not_cost(self):
        # 思法汇成 11-01 14:59：“任务逾期扣款”是扣员工的绩效，不是成本。
        async with self.sessions() as db:
            customer_a, _customer_b = await self._seed(db)
            contract_a = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == "CODEX-ROI-CONTRACT-A"))
            deduction = BusinessRecord(module="finance", serial_no="LIF-OVERDUE", title="任务逾期扣款", customer="同名客户", status="已记录", owner="x", department="华东部",
                                       data={"contract_id": contract_a.id, "contract_no": contract_a.serial_no, "fee_type": "内部费用",
                                             "internal_fee_type": "任务逾期扣款", "fee_type_name": "任务逾期扣款", "amount": -5})
            db.add(deduction)
            await db.flush()
            db.add(FinanceTransaction(finance_record_id=deduction.id, transaction_type="付款", amount=-5, transaction_date=date(2026, 9, 2), operator="admin"))
            await db.commit()
            result = await _customer_roi_analytics(ADMIN, db, date_from=date(2026, 9, 1), date_to=date(2026, 9, 2))
        by_customer = {row["customer_id"]: row for row in result["rows"]}
        self.assertEqual(by_customer[customer_a.id]["cost"], 150)

    async def test_only_customers_with_framework_contract_count(self):
        # 思法汇成 11-01 15:42 定（方案 A）：签过框架合作合同的客户全部收支都算（含其他类型合同下的），没签过的客户不列出。
        async with self.sessions() as db:
            customer_a, _customer_b = await self._seed(db)
            customer_c = BusinessRecord(module="customer", serial_no="CODEX-ROI-CUSTOMER-C", title="单项客户", customer="单项客户", status="正常", owner="owner-c", department="华东部", data={})
            db.add(customer_c)
            await db.flush()
            single_a = BusinessRecord(module="contract", serial_no="CODEX-ROI-CONTRACT-S", title="A的争议解决合同", customer="同名客户", status="审批通过", owner="income-owner", department="华东部",
                                      data={"contract_type": "争议解决合同", "customer_id": customer_a.id, "customer_no": customer_a.serial_no})
            single_c = BusinessRecord(module="contract", serial_no="CODEX-ROI-CONTRACT-C", title="C的合同", customer="单项客户", status="审批通过", owner="income-owner", department="华东部",
                                      data={"contract_type": "争议解决合同", "customer_id": customer_c.id, "customer_no": customer_c.serial_no})
            db.add_all([single_a, single_c])
            await db.flush()
            case_s = BusinessRecord(module="case", serial_no="CODEX-ROI-CASE-S", title="A的案件", customer="同名客户", status="办理中", owner="case-owner", department="华东部",
                                    data={"customer_id": customer_a.id, "contract_record_id": single_a.id})
            fee_s = BusinessRecord(module="finance", serial_no="CODEX-ROI-FEE-S", title="A的费用", customer="同名客户", status="已付款", owner="cost-owner", department="华东部",
                                   data={"contract_id": single_a.id, "contract_no": single_a.serial_no})
            fee_c = BusinessRecord(module="finance", serial_no="CODEX-ROI-FEE-C", title="C的费用", customer="单项客户", status="已付款", owner="cost-owner", department="华东部",
                                   data={"contract_id": single_c.id, "contract_no": single_c.serial_no})
            db.add_all([case_s, fee_s, fee_c])
            await db.flush()
            db.add_all([
                self._receipt("R-S1", 800, "2026-09-01", "同名客户", [{"amount": 800, "fee_type": "代理费", "case_id": case_s.id, "case_no": case_s.serial_no}]),
                self._receipt("R-C1", 500, "2026-09-01", "单项客户", [{"amount": 500, "fee_type": "代理费", "contract_no": single_c.serial_no}]),
                FinanceTransaction(finance_record_id=fee_s.id, transaction_type="付款", amount=70, transaction_date=date(2026, 9, 2), operator="admin"),
                FinanceTransaction(finance_record_id=fee_c.id, transaction_type="付款", amount=90, transaction_date=date(2026, 9, 2), operator="admin"),
            ])
            await db.commit()
            result = await _customer_roi_analytics(ADMIN, db, date_from=date(2026, 9, 1), date_to=date(2026, 9, 2))
        by_customer = {row["customer_id"]: row for row in result["rows"]}
        self.assertEqual(by_customer[customer_a.id]["income"], 1100)
        self.assertEqual(by_customer[customer_a.id]["cost"], 220)
        self.assertNotIn(customer_c.id, by_customer)

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
