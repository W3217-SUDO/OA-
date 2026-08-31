import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, SystemParameter, User
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {"username": "row14-admin", "role": "admin", "display_name": "第14行管理员", "department": "管理部"}


class CasePaymentUnitRow14Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name=IDENTITY["display_name"], department=IDENTITY["department"], role="admin", password_hash="x", is_active=True))
            case = BusinessRecord(module="case", serial_no="CODEX-831-R14-CASE", title="第14行付款单位案件", customer="第14行客户", status="文书准备", owner=IDENTITY["username"], department=IDENTITY["department"], data={"case_type": "民事争议", "case_creation_step": "completed"})
            db.add(case); await db.flush()
            firm_fee = BusinessRecord(module="finance", serial_no="CODEX-831-R14-FIRM", title="第14行律所费用", customer=case.customer, status="草稿", owner=IDENTITY["username"], department=IDENTITY["department"], data={"amount": 1400, "fee_type": "其他费用", "expense_scope": "律所", "expense_subtype": "第三方费用", "handler": IDENTITY["username"], "case_id": case.id, "case_no": case.serial_no})
            platform_fee = BusinessRecord(module="finance", serial_no="CODEX-831-R14-PLATFORM", title="第14行平台费用", customer=case.customer, status="草稿", owner=IDENTITY["username"], department=IDENTITY["department"], data={"amount": 1410, "fee_type": "官方费用", "expense_scope": "平台", "expense_subtype": "公证费", "handler": IDENTITY["username"], "case_id": case.id, "case_no": case.serial_no})
            known = SystemParameter(category="payment_type", code="CODEX-R14-KNOWN", name="对公", extra={"nature": "对公", "payee": "第14行已知收款单位", "account_bank": "第14行测试银行", "account": "R14-KNOWN-ACCOUNT"}, sort_order=1, is_active=True, created_by=IDENTITY["username"], updated_by=IDENTITY["username"])
            db.add_all([firm_fee, platform_fee, known]); await db.commit()
            await db.refresh(firm_fee); await db.refresh(platform_fee); await db.refresh(known)
            self.firm_fee_id, self.platform_fee_id, self.known_id = firm_fee.id, platform_fee.id, known.id

        async def override_db():
            async with self.sessions() as db:
                yield db
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row14.test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose(); app.dependency_overrides.clear(); app.dependency_overrides.update(self.previous_overrides); await self.engine.dispose()

    async def test_keyword_matches_existing_payment_unit(self) -> None:
        response = await self.client.get(f"{API}/finance/fees/{self.firm_fee_id}/payment-types", params={"keyword": "已知收款"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual([item["id"] for item in response.json()["items"]], [self.known_id])
        self.assertEqual(response.json()["items"][0]["account_bank"], "第14行测试银行")

    async def test_missing_payment_unit_can_be_created_and_is_visible_in_system_parameters(self) -> None:
        response = await self.client.post(f"{API}/finance/fees/{self.platform_fee_id}/payment-types", json={"nature": "对公", "payee": "第14行新增收款单位", "account_bank": "第14行新增银行", "account": "R14-NEW-ACCOUNT"})
        self.assertEqual(response.status_code, 201, response.text)
        created = response.json()
        self.assertEqual(created["payee"], "第14行新增收款单位")
        parameters = await self.client.get(f"{API}/system/parameters", params={"category": "payment_type", "keyword": ""})
        self.assertEqual(parameters.status_code, 200, parameters.text)
        stored = next(item for item in parameters.json()["items"] if item["id"] == created["id"])
        self.assertEqual(stored["extra"]["account_bank"], "第14行新增银行")

    async def test_law_firm_payment_requires_master_id_and_persists_authoritative_snapshot(self) -> None:
        missing = await self.client.post(f"{API}/finance/fees/{self.firm_fee_id}/submit", json={"amount": 100, "payment_payee": "伪造单位", "payment_account": "FAKE"})
        self.assertEqual(missing.status_code, 422, missing.text)
        self.assertIn("系统付款单位", missing.json()["detail"])
        accepted = await self.client.post(f"{API}/finance/fees/{self.firm_fee_id}/submit", json={"amount": 100, "payment_type_id": self.known_id, "payment_payee": "伪造单位", "payment_account": "FAKE", "payment_remark": "第14行律所费用"})
        self.assertEqual(accepted.status_code, 200, accepted.text)
        data = accepted.json()["data"]
        self.assertEqual(data["payment_type_id"], self.known_id)
        self.assertEqual(data["payment_payee"], "第14行已知收款单位")
        self.assertEqual(data["payment_account"], "R14-KNOWN-ACCOUNT")
        self.assertEqual(data["payment_account_bank"], "第14行测试银行")

    async def test_platform_payment_uses_newly_created_master_record(self) -> None:
        created = await self.client.post(f"{API}/finance/fees/{self.platform_fee_id}/payment-types", json={"nature": "个人", "payee": "第14行平台收款单位", "account_bank": "第14行平台银行", "account": "R14-PLATFORM-ACCOUNT"})
        self.assertEqual(created.status_code, 201, created.text)
        submitted = await self.client.post(f"{API}/finance/fees/{self.platform_fee_id}/submit", json={"amount": 210, "payment_type_id": created.json()["id"], "payment_remark": "第14行平台费用"})
        self.assertEqual(submitted.status_code, 200, submitted.text)
        self.assertEqual(submitted.json()["data"]["payment_payee"], "第14行平台收款单位")


if __name__ == "__main__":
    unittest.main()
