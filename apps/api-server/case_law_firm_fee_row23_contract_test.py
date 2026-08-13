import unittest
from pathlib import Path

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {"username": "row23-admin", "role": "admin", "display_name": "Row23 Admin", "department": "Row23 Department"}


class CaseLawFirmFeeRow23ContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name=IDENTITY["display_name"], department=IDENTITY["department"], role="admin", password_hash="x", is_active=True))
            contract = BusinessRecord(module="contract", serial_no="ROW23-CONTRACT", title="Row23 Contract", customer="Row23 Customer", status="已通过", owner=IDENTITY["username"], department=IDENTITY["department"], data={})
            case = BusinessRecord(module="case", serial_no="ROW23-CASE", title="Row23 Case", customer="Row23 Customer", status="一审阶段", owner=IDENTITY["username"], department=IDENTITY["department"], data={"case_creation_step": "completed", "contract_record_id": 1, "contract_no": "ROW23-CONTRACT"})
            db.add_all([contract, case])
            await db.flush()
            case.data = {**case.data, "contract_record_id": contract.id}
            self.contract_id, self.case_id = contract.id, case.id
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row23.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_law_firm_extended_fee_keeps_contract_and_deadline(self):
        response = await self.client.post(f"{API}/finance/fees", json={
            "title": "Row23 litigation fee", "customer": "Row23 Customer", "amount": 1280.5,
            "fee_type": "官方费用", "expense_scope": "律所", "expense_subtype": "诉讼费",
            "case_no": "ROW23-CASE", "case_record_id": self.case_id, "contract_record_id": self.contract_id,
            "handler": IDENTITY["username"], "deadline": "2026-09-01", "description": "Row23 note",
        })
        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()["data"]
        self.assertEqual(data["expense_subtype"], "诉讼费")
        self.assertEqual(data["fee_type"], "官方费用")
        self.assertEqual(data["contract_id"], self.contract_id)
        self.assertEqual(data["contract_no"], "ROW23-CONTRACT")
        self.assertEqual(data["deadline"], "2026-09-01")

    async def test_create_rejects_contract_from_another_case_customer(self):
        async with self.sessions() as db:
            other = BusinessRecord(module="case", serial_no="ROW23-OTHER-CASE", title="Other Case", customer="Other Customer", status="一审阶段", owner=IDENTITY["username"], department=IDENTITY["department"], data={})
            db.add(other)
            await db.commit()
            await db.refresh(other)
            other_case_id = other.id
        response = await self.client.post(f"{API}/finance/fees", json={
            "title": "Row23 invalid link", "customer": "Other Customer", "amount": 100,
            "fee_type": "官方费用", "expense_scope": "律所", "expense_subtype": "官费",
            "case_no": "ROW23-OTHER-CASE", "case_record_id": other_case_id, "contract_record_id": self.contract_id,
            "handler": IDENTITY["username"],
        })
        self.assertEqual(response.status_code, 409, response.text)


if __name__ == "__main__":
    unittest.main()
