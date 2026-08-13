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
PREFIX = "CODEX-812-ROW16-"
IDENTITY = {"username": PREFIX + "user", "role": "auditor", "display_name": "行16授权用户", "department": PREFIX + "部门A"}


class ContractCustomerManagerDepartmentRow16Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        tables = [User.__table__, RolePermission.__table__, BusinessRecord.__table__, ContractApprovalStep.__table__]
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))
        async with self.sessions() as db:
            db.add_all([
                User(username=IDENTITY["username"], display_name=IDENTITY["display_name"], department=IDENTITY["department"], role="auditor", password_hash="x", is_active=True),
                User(username=PREFIX + "manager-a", display_name="管理人甲", department=IDENTITY["department"], role="user", password_hash="x", is_active=True),
                User(username=PREFIX + "manager-b", display_name="管理人乙", department=PREFIX + "部门B", role="user", password_hash="x", is_active=True),
            ])
            db.add_all([
                BusinessRecord(module="customer", serial_no=PREFIX + "CUS-A", title=PREFIX + "客户A", customer=PREFIX + "客户A", status="正常", owner=PREFIX + "manager-a", department=IDENTITY["department"], data={"customer_managers": [PREFIX + "manager-a"]}),
                BusinessRecord(module="customer", serial_no=PREFIX + "CUS-B", title=PREFIX + "客户B", customer=PREFIX + "客户B", status="正常", owner=PREFIX + "manager-b", department=PREFIX + "部门B", data={"customer_managers": [PREFIX + "manager-b"]}),
                BusinessRecord(module="contract", serial_no=PREFIX + "CON-A", title=PREFIX + "合同A", customer=PREFIX + "客户A", status="草稿", owner=IDENTITY["username"], department=PREFIX + "部门B", data={"customer_no": PREFIX + "CUS-A"}),
                BusinessRecord(module="contract", serial_no=PREFIX + "CON-B", title=PREFIX + "合同B", customer=PREFIX + "客户B", status="草稿", owner=IDENTITY["username"], department=IDENTITY["department"], data={"customer_no": PREFIX + "CUS-B"}),
            ])
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row16.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_department_contracts_follow_customer_manager_department(self):
        response = await self.client.get(f"{API}/records", params={"module": "contract", "scope": "department", "page": 1, "page_size": 100})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual({item["serial_no"] for item in response.json()["items"]}, {PREFIX + "CON-A"})


if __name__ == "__main__":
    unittest.main()
