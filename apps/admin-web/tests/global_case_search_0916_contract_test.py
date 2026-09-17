"""9.16 顶栏全类型案件搜索接口与权限验证。"""

import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, JobRole, RolePermission, User
from app.security import current_identity


API = settings.api_prefix


class GlobalCaseSearch0916ContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                RolePermission(role="user", display_name="普通用户", data_scope="本人及共享数据", menu_keys=["case"], field_keys=[]),
                JobRole(code="FINANCE-SUPERVISOR", name="财务审核", permissions=["财务审批"], is_active=True),
                User(username="global-normal", display_name="普通人员", department="法务部", role="user", password_hash="test", is_active=True),
                User(username="global-finance", display_name="财务审核", department="财务部", role="user", password_hash="test", profile={"permission_role_code": "FINANCE-SUPERVISOR"}, is_active=True),
                User(username="global-admin", display_name="系统管理员", department="管理部", role="admin", role_ids=["admin"], password_hash="test", is_active=True),
                User(username="global-owner", display_name="其他人员", department="法务部", role="user", password_hash="test", is_active=True),
                BusinessRecord(module="case", serial_no="CASE-GLOBAL-MINE", title="我的案件", customer="客户甲", status="文书准备", owner="global-normal", department="法务部", data={"case_type": "民事案件", "plaintiff": "李四"}),
                BusinessRecord(module="case", serial_no="CASE-GLOBAL-CRIMINAL", title="刑事案件", customer="客户乙", status="文书准备", owner="global-owner", department="法务部", data={"case_type": "刑事案件", "first_procuratorate_name": "李四检察院"}),
                BusinessRecord(module="case", serial_no="CASE-GLOBAL-ADMIN", title="行政案件", customer="客户丙", status="文书准备", owner="global-owner", department="法务部", data={"case_type": "行政案件及国家赔偿", "administrative_agency": "李四机关"}),
                BusinessRecord(module="case", serial_no="CASE-GLOBAL-COUNSEL", title="法律顾问案件", customer="客户丁", status="文书准备", owner="global-owner", department="法务部", data={"case_type": "法律顾问", "counsel_contact": "李四"}),
            ])
            await db.commit()
            self.other_case_id = await db.scalar(select(BusinessRecord.id).where(
                BusinessRecord.serial_no == "CASE-GLOBAL-CRIMINAL",
            ))
        self.identity = {"username": "global-normal", "role": "user", "role_ids": ["user"], "department": "法务部"}
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://global-search.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def search(self, username: str, role: str = "user"):
        self.identity = {"username": username, "role": role, "role_ids": [role], "department": "法务部"}
        response = await self.client.post(f"{API}/cases/search", json={"scope": "global", "keyword": "李四", "page": 1, "page_size": 50})
        self.assertEqual(response.status_code, 200, response.text)
        return {item["serial_no"] for item in response.json()["items"]}

    async def test_global_search_keeps_normal_users_in_their_personal_case_scope(self):
        self.assertEqual(await self.search("global-normal"), {"CASE-GLOBAL-MINE"})

    async def test_finance_approval_role_searches_all_case_types(self):
        self.assertEqual(await self.search("global-finance"), {
            "CASE-GLOBAL-MINE",
            "CASE-GLOBAL-CRIMINAL",
            "CASE-GLOBAL-ADMIN",
            "CASE-GLOBAL-COUNSEL",
        })

    async def test_administrator_searches_all_case_types(self):
        self.assertEqual(await self.search("global-admin", "admin"), {
            "CASE-GLOBAL-MINE",
            "CASE-GLOBAL-CRIMINAL",
            "CASE-GLOBAL-ADMIN",
            "CASE-GLOBAL-COUNSEL",
        })

    async def test_finance_search_does_not_expand_other_case_detail_access(self):
        await self.search("global-finance")
        response = await self.client.get(f"{API}/records/{self.other_case_id}")
        self.assertEqual(response.status_code, 404, response.text)


if __name__ == "__main__":
    unittest.main()
