"""律师代理费（退费）提成只走内部费用请款，不能生成付款管理的外部请款单。"""
import unittest
from datetime import date

import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, SystemParameter, User, WorkflowEvent
from app.security import current_identity

API = settings.api_prefix
PREFIX = "CODEX-1022-AGRF-"
IDENTITY = {"username": PREFIX + "admin", "role": "admin", "display_name": "退费提成测试", "department": "Admin"}


class AgencyRefundCommissionRoutingTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name=IDENTITY["display_name"], department="Admin",
                        role="admin", password_hash="x", is_active=True))
            payment_type = SystemParameter(category="payment_type", code=PREFIX + "PAY", name="测试付款单位", is_active=True,
                                           extra={"nature": "对公", "payee": "测试收款单位", "account_bank": "测试银行", "account": "TEST"})
            contract = BusinessRecord(module="contract", serial_no=PREFIX + "HT", title="合同", customer=PREFIX + "客户",
                                      status="审批中", owner=IDENTITY["username"], department="Admin", data={"contract_body": "律所"})
            db.add_all([payment_type, contract]); await db.flush()
            case = BusinessRecord(module="case", serial_no=PREFIX + "CASE", title="案件", customer=PREFIX + "客户",
                                  status="一审阶段", owner=IDENTITY["username"], department="Admin",
                                  data={"contract_id": contract.id, "contract_no": contract.serial_no,
                                        "case_type": "民事案件", "case_creation_step": "completed"})
            db.add(case); await db.flush()
            common = {"case_id": case.id, "case_no": case.serial_no, "contract_id": contract.id,
                      "contract_no": contract.serial_no, "expense_scope": "律所", "handler": IDENTITY["username"]}
            fees = {}
            for key, extra in {
                "official": {"fee_type": "官方费用", "expense_subtype": "一审诉讼费", "amount": 100.0},
                "agency": {"fee_type": "代理费", "expense_subtype": "律师代理费", "amount": 1000.0},
                "refund": {"fee_type": "代理费", "expense_subtype": "律师代理费(退费)", "amount": 50.0, "refund_fee": True},
            }.items():
                fee = BusinessRecord(module="finance", serial_no=PREFIX + key, title=extra["expense_subtype"],
                                     customer=PREFIX + "客户", status="草稿", owner=IDENTITY["username"],
                                     department="Admin", data={**common, **extra})
                db.add(fee); await db.flush(); fees[key] = fee.id
            commissions = []
            for index, value in enumerate([5.0, 2.5]):
                item = BusinessRecord(
                    module="finance", serial_no=f"{PREFIX}commission-{index}", title="退费提成", customer=PREFIX + "客户",
                    status="待审批", owner=IDENTITY["username"], department="Admin",
                    data={"amount": value, "fee_type": "内部费用", "expense_scope": "内部", "commission_type": "开庭提成",
                          "case_id": case.id, "case_no": case.serial_no, "source_fee_id": fees["refund"],
                          "handler": IDENTITY["username"], "payee": IDENTITY["username"],
                          "commission_created_by": IDENTITY["username"], "commission_created_at": "2026-10-22T10:26:01",
                          "payment_application_no": PREFIX + "CREATED", "payment_requested_amount": 0,
                          "internal_payment_submitted": False, "applicant": IDENTITY["username"],
                          "commission_lifecycle": "case_agency_refund", "is_refund": True})
                db.add(item); await db.flush(); commissions.append(item.id)
            await db.commit()
        self.payment_type_id, self.contract_id, self.fees, self.commissions = payment_type.id, contract.id, fees, commissions
        self.case_id = case.id

        async def override_db():
            async with self.sessions() as db:
                yield db
        self.previous = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://agency-refund.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous)
        async with self.sessions() as db:
            await db.execute(delete(WorkflowEvent))
            await db.execute(delete(BusinessRecord).execution_options(include_deleted=True))
            await db.execute(delete(SystemParameter))
            await db.execute(delete(User))
            await db.commit()
        await self.engine.dispose()

    def contract_payment_body(self, fee_id, amount):
        return {"payment_type_id": self.payment_type_id, "application_date": str(date.today()),
                "lines": [{"case_fee_id": fee_id, "amount": amount}]}

    async def contract_payment_count(self):
        async with self.sessions() as db:
            return await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == "contract_payment"))

    async def test_refund_agency_fee_is_not_a_contract_payment_candidate(self):
        response = await self.client.get(f"{API}/contracts/{self.contract_id}/payment-candidates")
        self.assertEqual(response.status_code, 200, response.text)
        fee_ids = {item.get("case_fee_id") for item in response.json()["items"]}
        self.assertNotIn(self.fees["refund"], fee_ids)
        self.assertTrue({self.fees["official"], self.fees["agency"]} <= fee_ids)

    async def test_contract_payment_rejects_refund_agency_fee_without_writes(self):
        rejected = await self.client.post(f"{API}/contracts/{self.contract_id}/payment-applications",
                                          json=self.contract_payment_body(self.fees["refund"], 50))
        self.assertEqual(rejected.status_code, 409, rejected.text)
        self.assertIn("律师代理费（退费）", rejected.json()["detail"])
        self.assertEqual(await self.contract_payment_count(), 0)
        accepted = await self.client.post(f"{API}/contracts/{self.contract_id}/payment-applications",
                                          json=self.contract_payment_body(self.fees["official"], 100))
        self.assertEqual(accepted.status_code, 201, accepted.text)
        self.assertEqual(await self.contract_payment_count(), 1)

    async def test_single_fee_payment_request_rejects_refund_agency_fee(self):
        response = await self.client.post(f"{API}/finance/fees/{self.fees['refund']}/submit", json={
            "amount": 50, "payment_type_id": self.payment_type_id, "comment": "CODEX 退费代理费不能外部请款"})
        self.assertEqual(response.status_code, 409, response.text)
        self.assertIn("律师代理费（退费）", response.json()["detail"])
        async with self.sessions() as db:
            fee = await db.get(BusinessRecord, self.fees["refund"])
            self.assertEqual(fee.status, "草稿")
            self.assertFalse((fee.data or {}).get("payment_applied_at"))

    async def test_refund_commission_application_lands_only_in_internal_queues(self):
        applied = await self.client.post(f"{API}/finance/internal-applications/payment-requests", json={
            "lines": [{"fee_id": fee_id, "amount": amount, "payment_payee": IDENTITY["username"], "payment_account": "CODEX-ACCOUNT"}
                      for fee_id, amount in zip(self.commissions, [5.0, 2.5])],
            "comment": "CODEX 退费提成申请付款"})
        self.assertEqual(applied.status_code, 200, applied.text)
        application_no = applied.json()["application_no"]

        # 案件未归档：退费提成在“内部提成-待归档”，归档后才进入“内部提成(退费)-待审核”。
        archive_page = await self.client.get(f"{API}/finance/internal-fees", params={"scope": "archive"})
        self.assertEqual(archive_page.status_code, 200, archive_page.text)
        self.assertIn(application_no, [item["serial_no"] for item in archive_page.json()["items"]])
        early = await self.client.get(f"{API}/finance/internal-review-requests", params={"kind": "refund"})
        self.assertNotIn(application_no, [item["serial_no"] for item in early.json()["items"]])
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, self.case_id)
            case.status = "已归档"
            await db.commit()

        refund_queue = await self.client.get(f"{API}/finance/internal-review-requests", params={"kind": "refund"})
        self.assertEqual(refund_queue.status_code, 200, refund_queue.text)
        self.assertIn(application_no, [item["serial_no"] for item in refund_queue.json()["items"]])
        normal_queue = await self.client.get(f"{API}/finance/internal-review-requests", params={"kind": "commission"})
        self.assertNotIn(application_no, [item["serial_no"] for item in normal_queue.json()["items"]])

        internal_mine = await self.client.get(f"{API}/finance/internal-fees", params={"scope": "applications"})
        self.assertEqual(internal_mine.status_code, 200, internal_mine.text)
        self.assertIn(application_no, [item["serial_no"] for item in internal_mine.json()["items"]])

        for scope in ("mine", "audit"):
            external = await self.client.get(f"{API}/finance/payment-applications/query", params={"scope": scope})
            self.assertEqual(external.status_code, 200, external.text)
            self.assertFalse(set(self.commissions) & {item.get("id") for item in external.json()["items"]})
        self.assertEqual(await self.contract_payment_count(), 0)


if __name__ == "__main__":
    unittest.main()
