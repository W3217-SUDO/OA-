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
IDENTITY = {"username": "row17-admin", "role": "admin", "display_name": "Row17 Admin", "department": "Admin"}
SUBTYPES = ["\u4ea7\u54c1\u8d2d\u4e70\u8d39", "\u7ffb\u8bd1\u8d39", "\u6295\u8d44\u63d0\u6210", "\u8c03\u6863\u8d39", "\u624b\u7eed\u8d39", "\u4efb\u52a1\u8c03\u671f\u6263\u6b3e", "\u670d\u52a1\u8d39(\u8c03\u67e5)", "\u670d\u52a1\u8d39(\u5f00\u5ead)", "\u670d\u52a1\u8d39(\u6848\u6e90)", "\u670d\u52a1\u8d39(\u6587\u4e66)", "\u670d\u52a1\u8d39(\u54c1\u7ba1)"]

class CaseInternalFeeRow17Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection: await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name=IDENTITY["display_name"], department=IDENTITY["department"], role="admin", password_hash="x", is_active=True))
            case = BusinessRecord(module="case", serial_no="CODEX-828-R17-CASE", title="Row17 Case", customer="Row17 Customer", status="\u6587\u4e66\u51c6\u5907", owner=IDENTITY["username"], department=IDENTITY["department"], data={"case_type": "\u6c11\u4e8b\u4e89\u8bae", "case_creation_step": "completed"})
            db.add(case); await db.commit(); await db.refresh(case); self.case_id = case.id
        async def override_db():
            async with self.sessions() as db: yield db
        self.previous = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row17.test")

    async def asyncTearDown(self):
        await self.client.aclose(); app.dependency_overrides.clear(); app.dependency_overrides.update(self.previous); await self.engine.dispose()

    async def test_all_internal_fee_types_save_without_contract(self):
        for index, subtype in enumerate(SUBTYPES):
            response = await self.client.post(f"{API}/finance/fees", json={
                "title": f"Row17 {subtype}", "customer": "Row17 Customer", "amount": 170 + index,
                "fee_type": "\u5185\u90e8\u8d39\u7528", "expense_scope": "\u5185\u90e8", "expense_subtype": subtype,
                "case_no": "CODEX-828-R17-CASE", "case_record_id": self.case_id, "handler": IDENTITY["username"],
                "payee": IDENTITY["username"], "base_amount": 1000 + index, "reference_commission": 100 + index,
            })
            self.assertEqual(response.status_code, 201, response.text)
            data = response.json()["data"]
            self.assertEqual(data["expense_subtype"], subtype)
            self.assertIsNone(data["contract_id"])
            self.assertEqual(data["payee"], IDENTITY["username"])
            self.assertEqual(data["base_amount"], 1000 + index)
            self.assertEqual(data["reference_commission"], 100 + index)

if __name__ == "__main__": unittest.main()
