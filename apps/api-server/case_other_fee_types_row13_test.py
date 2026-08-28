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
IDENTITY = {"username": "row13-admin", "role": "admin", "display_name": "\u7b2c13\u884c\u7ba1\u7406\u5458", "department": "\u7ba1\u7406\u90e8"}
OTHER_SUBTYPES = ["\u6848\u6e90\u4ecb\u7ecd\u8d39", "\u6743\u5229\u4eba\u8d54\u507f\u6b3e", "\u6295\u8d44\u4eba\u5206\u6210", "\u5176\u4ed6\u8d39\u7528"]


class CaseOtherFeeTypesRow13Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name=IDENTITY["display_name"], department=IDENTITY["department"], role="admin", password_hash="x", is_active=True))
            case = BusinessRecord(module="case", serial_no="CODEX-828-R13-CASE", title="\u7b2c13\u884c\u5176\u4ed6\u8d39\u7528\u6848\u4ef6", customer="\u7b2c13\u884c\u5ba2\u6237", status="\u6587\u4e66\u51c6\u5907", owner=IDENTITY["username"], department=IDENTITY["department"], data={"case_type": "\u6c11\u4e8b\u4e89\u8bae", "case_creation_step": "completed"})
            contract = BusinessRecord(module="contract", serial_no="CODEX-828-R13-CONTRACT", title="\u7b2c13\u884c\u5f8b\u6240\u5408\u540c", customer="\u7b2c13\u884c\u5ba2\u6237", status="\u5ba1\u6279\u901a\u8fc7", owner=IDENTITY["username"], department=IDENTITY["department"], data={"contract_body": "\u5f8b\u6240"})
            db.add_all([case, contract]); await db.commit(); await db.refresh(case); await db.refresh(contract)
            self.case_id, self.contract_id = case.id, contract.id

        async def override_db():
            async with self.sessions() as db:
                yield db
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row13.test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose(); app.dependency_overrides.clear(); app.dependency_overrides.update(self.previous_overrides); await self.engine.dispose()

    async def test_all_legacy_other_types_save_and_echo(self) -> None:
        for index, subtype in enumerate(OTHER_SUBTYPES):
            response = await self.client.post(f"{API}/finance/fees", json={
                "title": f"\u7b2c13\u884c{subtype}", "customer": "\u7b2c13\u884c\u5ba2\u6237", "amount": 400 + index,
                "fee_type": "\u5176\u4ed6\u8d39\u7528", "expense_scope": "\u5f8b\u6240", "expense_subtype": subtype,
                "case_no": "CODEX-828-R13-CASE", "case_record_id": self.case_id,
                "contract_record_id": self.contract_id, "handler": IDENTITY["username"],
            })
            self.assertEqual(response.status_code, 201, response.text)
            self.assertEqual(response.json()["data"]["expense_subtype"], subtype)
            self.assertEqual(response.json()["data"]["fee_type"], "\u5176\u4ed6\u8d39\u7528")


if __name__ == "__main__":
    unittest.main()
