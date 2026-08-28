import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {"username": "row6-admin", "role": "admin", "display_name": "第6行管理员", "department": "管理部"}


class CaseFeeContractScopeRow6Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(
                username=IDENTITY["username"], display_name=IDENTITY["display_name"],
                department=IDENTITY["department"], role="admin", password_hash="x", is_active=True,
            ))
            case = BusinessRecord(
                module="case", serial_no="CODEX-828-R6-CASE", title="第6行费用合同限制案件",
                customer="测试客户8.3", status="文书准备", owner=IDENTITY["username"],
                department=IDENTITY["department"], data={"case_type": "民事争议", "case_creation_step": "completed"},
            )
            law_contract = BusinessRecord(
                module="contract", serial_no="CODEX-828-R6-LAW", title="测试客户8.3律所合同",
                customer="测试客户8.3", status="审批通过", owner=IDENTITY["username"],
                department=IDENTITY["department"], data={"contract_body": "律所"},
            )
            other_platform = BusinessRecord(
                module="contract", serial_no="CODEX-828-R6-OTHER", title="其他客户平台合同",
                customer="其他客户", status="审批通过", owner=IDENTITY["username"],
                department=IDENTITY["department"], data={"contract_body": "平台"},
            )
            db.add_all([case, law_contract, other_platform])
            await db.commit()
            await db.refresh(case); await db.refresh(law_contract)
            self.case_id = case.id
            self.law_contract_id = law_contract.id

        async def override_db():
            async with self.sessions() as db:
                yield db

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row6.test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    def payload(self, scope: str, contract_id: int | None = None) -> dict:
        subtype = "诉讼费" if scope != "内部" else "内部费用"
        fee_type = "官方费用" if scope != "内部" else "内部费用"
        return {
            "title": f"第6行{scope}费用", "customer": "测试客户8.3", "amount": 100,
            "fee_type": fee_type, "expense_scope": scope, "expense_subtype": subtype,
            "case_no": "CODEX-828-R6-CASE", "case_record_id": self.case_id,
            "contract_record_id": contract_id, "handler": IDENTITY["username"],
        }

    async def test_law_firm_fee_uses_matching_customer_contract(self) -> None:
        response = await self.client.post(f"{API}/finance/fees", json=self.payload("律所"))
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["data"]["contract_id"], self.law_contract_id)

    async def test_platform_fee_is_blocked_without_customer_platform_contract(self) -> None:
        response = await self.client.post(f"{API}/finance/fees", json=self.payload("平台"))
        self.assertEqual(response.status_code, 409, response.text)
        self.assertIn("没有平台合同", response.json()["detail"])

        wrong = await self.client.post(
            f"{API}/finance/fees", json=self.payload("平台", self.law_contract_id),
        )
        self.assertEqual(wrong.status_code, 409, wrong.text)
        self.assertIn("合同主体为平台", wrong.json()["detail"])

    async def test_platform_fee_succeeds_after_matching_contract_exists(self) -> None:
        async with self.sessions() as db:
            contract = BusinessRecord(
                module="contract", serial_no="CODEX-828-R6-PLATFORM", title="测试客户8.3平台合同",
                customer="测试客户8.3", status="审批通过", owner=IDENTITY["username"],
                department=IDENTITY["department"], data={"contract_body": "平台"},
            )
            db.add(contract); await db.commit(); await db.refresh(contract)
            contract_id = contract.id
        response = await self.client.post(f"{API}/finance/fees", json=self.payload("平台"))
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["data"]["contract_id"], contract_id)

    async def test_batch_creation_is_atomic_when_one_case_lacks_matching_contract(self) -> None:
        response = await self.client.post(f"{API}/cases/batch-fees", json={
            "case_ids": [self.case_id], "amount": 100, "expense_scope": "平台",
            "expense_subtype": "官费", "handler": IDENTITY["username"], "description": "row6",
        })
        self.assertEqual(response.status_code, 409, response.text)
        self.assertIn("没有平台合同", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
