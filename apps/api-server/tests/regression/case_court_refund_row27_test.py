"""Regression coverage for court refunds bound to the source case and official fee."""

import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, SystemParameter, User
from app.security import current_identity


class CaseCourtRefundRow27Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username="row27-admin", display_name="第27行管理员", department="上海分所", role="admin", password_hash="test", is_active=True))
            db.add(SystemParameter(category="fee_type", code="AGENCY-REFUND", name="律师代理费(退费)", is_active=True))
            case = BusinessRecord(module="case", serial_no="CODEX-812-ROW27-CASE", title="第27行原案", customer="CODEX-812-ROW27-CUSTOMER", status="立案", owner="row27-admin", department="上海分所", data={"case_type": "民事案件", "court": "CODEX-812-ROW27-COURT"})
            db.add(case)
            await db.flush()
            fee = BusinessRecord(module="finance", serial_no="CODEX-812-ROW27-FEE", title="第27行官费", customer=case.customer, status="已付款", owner="row27-admin", department="上海分所", data={"amount": 100, "fee_type": "官方费用", "expense_scope": "律所", "expense_subtype": "官费", "case_id": case.id, "case_no": case.serial_no, "court": "CODEX-812-ROW27-COURT", "document_no": "CODEX-812-ROW27-PAYMENT"})
            db.add(fee)
            await db.commit()
            self.case_id = case.id
            self.fee_id = fee.id
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: {"username": "row27-admin", "role": "admin", "display_name": "第27行管理员", "department": "上海分所"}
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row27.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def _add_agency_fee(self, cashed_amount: float) -> None:
        async with self.sessions() as db:
            db.add(BusinessRecord(module="finance", serial_no="CODEX-812-ROW27-AGENCY", title="律师代理费", customer="CODEX-812-ROW27-CUSTOMER", status="已到账", owner="row27-admin", department="上海分所", data={"amount": 1000, "fee_type": "代理费", "expense_scope": "律所", "expense_subtype": "律师代理费", "case_id": self.case_id, "case_no": "CODEX-812-ROW27-CASE", "cashed_amount": cashed_amount}))
            await db.commit()

    def _payload(self):
        return {
            "fee_record_id": self.fee_id,
            "customer": "CODEX-812-ROW27-CUSTOMER",
            "case_no": "CODEX-812-ROW27-CASE",
            "court": "CODEX-812-ROW27-COURT",
            "original_payment_no": "CODEX-812-ROW27-PAYMENT",
            "amount": 60,
            "applicant": "第27行管理员",
            "refund_account_name": "第27行账户",
            "refund_bank": "第27行银行",
            "refund_account": "CODEX-812-ROW27-ACCOUNT",
        }

    async def test_refund_is_bound_and_amount_is_projected_back_to_source_fee(self):
        # 本案律师代理费已部分到账：沿用 10.23 第3行口径，诉讼费“退费”列显示本次退费。
        await self._add_agency_fee(300)
        payload = self._payload()
        created = await self.client.post(f"{settings.api_prefix}/finance/refunds", json=payload)
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["data"]["case_id"], self.case_id)
        self.assertEqual(created.json()["data"]["case_record_id"], self.case_id)
        self.assertEqual(created.json()["data"]["fee_record_id"], self.fee_id)
        relations = await self.client.get(f"{settings.api_prefix}/cases/{self.case_id}/relations")
        self.assertEqual(relations.status_code, 200, relations.text)
        fee = next(item for item in relations.json()["fees"] if item["id"] == self.fee_id)
        self.assertEqual(fee["data"]["refund_amount"], 60)
        over_limit = await self.client.post(f"{settings.api_prefix}/finance/refunds", json={**payload, "amount": 41})
        self.assertEqual(over_limit.status_code, 422, over_limit.text)

    async def test_agency_fee_without_receipt_only_adds_agency_refund_fee(self):
        """10.26 第8行：律师代理费没有到账时，只新增律师代理费（退费），诉讼费退费列不显示。"""
        await self._add_agency_fee(0)
        created = await self.client.post(f"{settings.api_prefix}/finance/refunds", json=self._payload())
        self.assertEqual(created.status_code, 201, created.text)
        relations = await self.client.get(f"{settings.api_prefix}/cases/{self.case_id}/relations")
        self.assertEqual(relations.status_code, 200, relations.text)
        fees = relations.json()["fees"]
        source = next(item for item in fees if item["id"] == self.fee_id)
        self.assertEqual(source["data"]["refund_amount"], 0)
        refund_fee = next(item for item in fees if item["data"].get("refund_fee"))
        self.assertEqual(float(refund_fee["data"]["amount"]), 60)


if __name__ == "__main__":
    unittest.main()
