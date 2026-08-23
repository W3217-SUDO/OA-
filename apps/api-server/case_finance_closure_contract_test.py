"""Isolated runtime contracts for case fee payment closure."""

import unittest
from datetime import date

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {"username": "finance-admin", "role": "admin", "display_name": "财务管理员", "department": "上海分所"}


class CaseFinanceClosureContract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async def override_get_db():
            async with self.session_factory() as session:
                yield session

        async def override_identity():
            return IDENTITY

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[current_identity] = override_identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://case-finance.test")

        async with self.session_factory() as session:
            session.add(User(
                username=IDENTITY["username"], display_name=IDENTITY["display_name"],
                department=IDENTITY["department"], role="admin", password_hash="test", is_active=True,
            ))
            case = BusinessRecord(
                module="case", serial_no="CASE-FINANCE-001", title="费用闭环案件",
                customer="费用闭环客户", status="一审阶段", owner=IDENTITY["username"],
                department=IDENTITY["department"], data={"case_creation_step": "completed"},
            )
            session.add(case)
            await session.flush()
            ordinary = BusinessRecord(
                module="finance", serial_no="FEE-ORDINARY-001", title="律所第三方费用",
                customer=case.customer, status="草稿", owner=IDENTITY["username"],
                department=case.department,
                data={"amount": 320.0, "fee_type": "其他费用", "expense_scope": "律所", "expense_subtype": "第三方费用", "handler": IDENTITY["username"], "case_id": case.id, "case_no": case.serial_no, "payee": "第三方机构"},
            )
            payment_ready = BusinessRecord(
                module="finance", serial_no="FEE-PAYMENT-001", title="可申请付款费用",
                customer=case.customer, status="草稿", owner=IDENTITY["username"],
                department=case.department,
                data={"amount": 320.0, "fee_type": "其他费用", "expense_scope": "律所", "expense_subtype": "第三方费用", "handler": IDENTITY["username"], "case_id": case.id, "case_no": case.serial_no, "payee": "第三方机构"},
            )
            internal = BusinessRecord(
                module="finance", serial_no="FEE-INTERNAL-001", title="内部提成",
                customer=case.customer, status="已审批", owner=IDENTITY["username"],
                department=case.department,
                data={"amount": 600.0, "fee_type": "内部费用", "expense_scope": "内部", "expense_subtype": "内部费用", "handler": IDENTITY["username"], "case_id": case.id, "case_no": case.serial_no, "payee": "范文玲"},
            )
            official = BusinessRecord(
                module="finance", serial_no="FEE-OFFICIAL-001", title="案件受理费",
                customer=case.customer, status="已付款", owner=IDENTITY["username"],
                department=case.department,
                data={"amount": 500.0, "fee_type": "官方费用", "expense_scope": "律所", "expense_subtype": "法院费用", "handler": IDENTITY["username"], "case_id": case.id, "case_no": case.serial_no, "payee": "上海市人民法院", "court": "上海市人民法院", "document_no": "PAY-OFFICIAL-001"},
            )
            session.add_all([ordinary, payment_ready, internal, official])
            await session.flush()
            self.ordinary_id = ordinary.id
            self.payment_ready_id = payment_ready.id
            self.internal_id = internal.id
            self.official_id = official.id
            await session.commit()

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_law_firm_fee_submits_through_ordinary_payment_flow(self):
        response = await self.client.post(f"{API}/finance/fees/{self.ordinary_id}/submit", json={"comment": "案件详情申请付款"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "待审批")

    async def test_payment_request_from_draft_persists_amount_and_payment_account(self):
        response = await self.client.post(
            f"{API}/finance/fees/{self.payment_ready_id}/submit",
            json={"amount": 120, "payment_account": "ROW28-TEST-ACCOUNT", "payment_payee": "第三方机构", "comment": "第28行付款申请"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "待审批")
        self.assertEqual(response.json()["data"]["payment_requested_amount"], 120.0)
        self.assertEqual(response.json()["data"]["payment_account"], "ROW28-TEST-ACCOUNT")

        async with self.session_factory() as session:
            fee = await session.get(BusinessRecord, self.payment_ready_id)
            self.assertEqual(fee.data["payment_requested_amount"], 120.0)
            self.assertEqual(fee.data["payment_account"], "ROW28-TEST-ACCOUNT")

    async def test_internal_package_is_pending_until_writeoff_and_syncs_amounts(self):
        preview = await self.client.post(f"{API}/finance/payment-packages/preview", json={"fee_ids": [self.internal_id]})
        self.assertEqual(preview.status_code, 200, preview.text)
        package_no = preview.json()["package_no"]
        created = await self.client.post(
            f"{API}/finance/payment-packages",
            json={"fee_ids": [self.internal_id], "package_no": package_no, "comment": "内部费用申请付款"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        package_id = created.json()["id"]

        async with self.session_factory() as session:
            fee = await session.get(BusinessRecord, self.internal_id)
            self.assertEqual(fee.status, "待核销")
            self.assertEqual(fee.data["payment_status"], "待核销")
            self.assertEqual(fee.data["payment_requested_amount"], 600.0)
            self.assertEqual(fee.data["paid_amount"], 0)

        paid = await self.client.post(
            f"{API}/finance/payment-packages/{package_id}/writeoff",
            json={"amount": 600.0, "paid_date": str(date(2026, 8, 12)), "payment_method": "银行卡", "invoice_no": "PAY-20260812", "remark": "核销"},
        )
        self.assertEqual(paid.status_code, 200, paid.text)
        async with self.session_factory() as session:
            fee = await session.scalar(select(BusinessRecord).where(BusinessRecord.id == self.internal_id))
            self.assertEqual(fee.status, "已付款")
            self.assertEqual(fee.data["payment_status"], "已付款")
            self.assertEqual(fee.data["paid_amount"], 600.0)
            self.assertEqual(fee.data["payment_date"], "2026-08-12")

    async def test_refund_keeps_fee_context_and_rejects_amount_above_original_fee(self):
        payload = {
            "fee_record_id": self.official_id,
            "customer": "费用闭环客户",
            "case_no": "CASE-FINANCE-001",
            "court": "上海市人民法院",
            "original_payment_no": "PAY-OFFICIAL-001",
            "amount": 501,
            "applicant": "财务管理员",
            "refund_account_name": "费用闭环客户",
            "refund_bank": "测试银行",
            "refund_account": "6222000000000000",
            "reason": "诉讼费退费",
        }
        excessive = await self.client.post(f"{API}/finance/refunds", json=payload)
        self.assertEqual(excessive.status_code, 422, excessive.text)
        self.assertIn("退款金额不能超过原费用金额", excessive.text)

        payload["amount"] = 300
        created = await self.client.post(f"{API}/finance/refunds", json=payload)
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["data"]["fee_record_id"], self.official_id)
        self.assertEqual(created.json()["data"]["amount"], 300.0)


if __name__ == "__main__":
    unittest.main()
