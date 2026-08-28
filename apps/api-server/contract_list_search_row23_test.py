import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, ContractApprovalStep, RolePermission, User
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {
    "username": "row23-admin",
    "role": "admin",
    "display_name": "第23行管理员",
    "department": "第23行部门",
}


class ContractListSearchRow23Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        tables = [User.__table__, RolePermission.__table__, BusinessRecord.__table__, ContractApprovalStep.__table__]
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda sync_connection: Base.metadata.create_all(sync_connection, tables=tables))
        async with self.sessions() as db:
            db.add(User(
                username=IDENTITY["username"], display_name=IDENTITY["display_name"],
                department=IDENTITY["department"], role="admin", password_hash="x", is_active=True,
            ))
            db.add_all([
                BusinessRecord(
                    module="contract", serial_no="SHHT2610061", title="目标商标服务合同",
                    customer="第23行目标客户", status="审批通过", owner=IDENTITY["username"],
                    department=IDENTITY["department"],
                    data={"type": "争议解决合同", "case_no": "SHMS2600424", "signed_at": "2026-08-23"},
                ),
                BusinessRecord(
                    module="contract", serial_no="SHHT2610062", title="其他服务合同",
                    customer="第23行其他客户", status="审批通过", owner=IDENTITY["username"],
                    department=IDENTITY["department"],
                    data={"type": "法律顾问合同", "case_no": "OTHER-CASE", "signed_at": "2026-08-24"},
                ),
            ])
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row23.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def assert_single_contract(self, **params):
        response = await self.client.get(
            f"{API}/records",
            params={"module": "contract", "scope": "mine", "page": 1, "page_size": 15, **params},
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual([item["serial_no"] for item in payload["items"]], ["SHHT2610061"])

    async def test_contract_number_filter_is_applied_before_pagination(self):
        await self.assert_single_contract(serial_no="2610061")

    async def test_contract_title_and_generic_keyword_find_the_target(self):
        await self.assert_single_contract(title="目标商标")
        await self.assert_single_contract(keyword="第23行目标客户")

    async def test_contract_extended_fields_are_not_silently_ignored(self):
        await self.assert_single_contract(type="争议解决合同", case_no="2600424", signed_at_start="2026-08-23", signed_at_end="2026-08-23")


if __name__ == "__main__":
    unittest.main()
