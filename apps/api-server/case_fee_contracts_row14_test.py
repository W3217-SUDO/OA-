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
IDENTITY = {"username": "row14-user", "role": "user", "display_name": "\u7b2c14\u884c\u7528\u6237", "department": "\u4e00\u90e8"}
CUSTOMER = "\u6d4b\u8bd5\u5ba2\u62378.3"


class CaseFeeContractsRow14Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name=IDENTITY["display_name"], department=IDENTITY["department"], role="user", password_hash="x", is_active=True))
            case = BusinessRecord(module="case", serial_no="CODEX-828-R14-CASE", title="\u7b2c14\u884c\u6848\u4ef6", customer=CUSTOMER, status="\u6587\u4e66\u51c6\u5907", owner=IDENTITY["username"], department=IDENTITY["department"], data={"case_type": "\u6c11\u4e8b\u4e89\u8bae", "case_creation_step": "completed"})
            db.add(case); await db.flush()
            contracts = []
            for index in range(8):
                contracts.append(BusinessRecord(module="contract", serial_no=f"CODEX-828-R14-LAW-{index + 1}", title=f"law-{index + 1}", customer=CUSTOMER, status="\u5df2\u5f52\u6863" if index >= 3 else "\u5ba1\u6279\u901a\u8fc7", owner=f"other-{index}", department="\u5176\u4ed6\u90e8", data={"contract_body": "\u5f8b\u6240"}))
            for index in range(3):
                contracts.append(BusinessRecord(module="contract", serial_no=f"CODEX-828-R14-PLATFORM-{index + 1}", title=f"platform-{index + 1}", customer=CUSTOMER, status="\u5ba1\u6279\u901a\u8fc7", owner=f"platform-{index}", department="\u5176\u4ed6\u90e8", data={"contract_body": "\u5e73\u53f0"}))
            db.add_all(contracts); await db.commit(); await db.refresh(case)
            for contract in contracts: await db.refresh(contract)
            self.case_id = case.id
            self.hidden_contract_id = contracts[7].id

        async def override_db():
            async with self.sessions() as db:
                yield db
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row14.test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose(); app.dependency_overrides.clear(); app.dependency_overrides.update(self.previous_overrides); await self.engine.dispose()

    async def test_visible_case_returns_all_customer_contracts_by_scope(self) -> None:
        law = await self.client.get(f"{API}/cases/{self.case_id}/fee-contracts", params={"expense_scope": "\u5f8b\u6240"})
        platform = await self.client.get(f"{API}/cases/{self.case_id}/fee-contracts", params={"expense_scope": "\u5e73\u53f0"})
        self.assertEqual(law.status_code, 200, law.text); self.assertEqual(law.json()["total"], 8)
        self.assertEqual(platform.status_code, 200, platform.text); self.assertEqual(platform.json()["total"], 3)

    async def test_fee_can_use_customer_contract_outside_generic_record_scope(self) -> None:
        response = await self.client.post(f"{API}/finance/fees", json={
            "title": "\u7b2c14\u884c\u8d39\u7528", "customer": CUSTOMER, "amount": 514,
            "fee_type": "\u5176\u4ed6\u8d39\u7528", "expense_scope": "\u5f8b\u6240", "expense_subtype": "\u5176\u4ed6\u8d39\u7528",
            "case_no": "CODEX-828-R14-CASE", "case_record_id": self.case_id,
            "contract_record_id": self.hidden_contract_id, "handler": IDENTITY["username"],
        })
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["data"]["contract_id"], self.hidden_contract_id)


if __name__ == "__main__":
    unittest.main()
