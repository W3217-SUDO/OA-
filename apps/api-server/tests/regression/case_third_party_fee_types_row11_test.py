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
IDENTITY = {"username": "row11-admin", "role": "admin", "display_name": "第11行管理员", "department": "管理部"}
THIRD_PARTY_SUBTYPES = ["检索费", "公告费", "担保费", "鉴定费", "公证服务费"]


class CaseThirdPartyFeeTypesRow11Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name=IDENTITY["display_name"], department=IDENTITY["department"], role="admin", password_hash="x", is_active=True))
            case = BusinessRecord(module="case", serial_no="CODEX-828-R11-CASE", title="第11行第三方费用案件", customer="第11行客户", status="文书准备", owner=IDENTITY["username"], department=IDENTITY["department"], data={"case_type": "民事争议", "case_creation_step": "completed"})
            contract = BusinessRecord(module="contract", serial_no="CODEX-828-R11-CONTRACT", title="第11行律所合同", customer="第11行客户", status="审批通过", owner=IDENTITY["username"], department=IDENTITY["department"], data={"contract_body": "律所"})
            db.add_all([case, contract]); await db.commit(); await db.refresh(case); await db.refresh(contract)
            self.case_id, self.contract_id = case.id, contract.id

        async def override_db():
            async with self.sessions() as db:
                yield db

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row11.test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear(); app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_all_legacy_third_party_types_save_and_echo(self) -> None:
        for index, subtype in enumerate(THIRD_PARTY_SUBTYPES):
            response = await self.client.post(f"{API}/finance/fees", json={
                "title": f"第11行{subtype}", "customer": "第11行客户", "amount": 200 + index,
                "fee_type": "其他费用", "expense_scope": "律所", "expense_subtype": subtype,
                "case_no": "CODEX-828-R11-CASE", "case_record_id": self.case_id,
                "contract_record_id": self.contract_id, "handler": IDENTITY["username"],
            })
            self.assertEqual(response.status_code, 201, response.text)
            self.assertEqual(response.json()["data"]["expense_subtype"], subtype)
            self.assertEqual(response.json()["data"]["fee_type"], "其他费用")


if __name__ == "__main__":
    unittest.main()
