"""9.30 第15行：案件检索、详情与利冲状态使用一致的只读角色范围。"""

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


class CaseReadScope0930Test(unittest.IsolatedAsyncioTestCase):
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
            db.add(RolePermission(
                role="user", display_name="普通用户", data_scope="本人及共享数据",
                menu_keys=["case-mine"], field_keys=[],
            ))
            db.add_all([
                JobRole(code="FINANCE-SUPERVISOR", name="财务主管", permissions=["财务审批"], is_active=True),
                JobRole(code="LEGACY-ROLE-4", name="行政流程", permissions=[], is_active=True),
                JobRole(code="CASE-READER", name="公司案件查看", permissions=["case-company"], is_active=True),
                User(username="oa0930-owner", display_name="案件负责人", role="user", department="法务部", password_hash="x", is_active=True),
                User(username="oa0930-ordinary", display_name="普通人员", role="user", department="法务部", password_hash="x", is_active=True),
                User(username="oa0930-finance", display_name="财务人员", role="user", department="财务部", password_hash="x", profile={"permission_role_code": "FINANCE-SUPERVISOR"}, is_active=True),
                User(username="oa0930-process", display_name="流程人员", role="user", department="行政流程部", password_hash="x", profile={"permission_role_code": "LEGACY-ROLE-4"}, is_active=True),
                User(username="oa0930-company", display_name="公司案件人员", role="user", department="法务部", password_hash="x", profile={"permission_role_code": "CASE-READER"}, is_active=True),
                User(username="oa0930-admin", display_name="管理员", role="admin", role_ids=["admin"], department="管理部", password_hash="x", is_active=True),
                BusinessRecord(module="case", serial_no="CODEX-0930-CASE-READ", title="权限可读案件", customer="测试客户", status="文书准备", owner="oa0930-owner", department="法务部", data={"case_type": "法律顾问", "plaintiff": "全所核查词"}),
            ])
            await db.commit()
            case = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == "CODEX-0930-CASE-READ"))
            self.case_id = case.id
        self.identity = {"username": "oa0930-ordinary", "role": "user", "role_ids": ["user"], "department": "法务部"}
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://oa0930.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    def become(self, username, *, admin=False):
        role = "admin" if admin else "user"
        self.identity = {"username": username, "role": role, "role_ids": [role], "department": "法务部"}

    async def assert_can_read_case(self):
        search = await self.client.post(f"{settings.api_prefix}/cases/search", json={"scope": "global", "keyword": "全所核查词", "page": 1, "page_size": 10})
        self.assertEqual(search.status_code, 200, search.text)
        self.assertIn("CODEX-0930-CASE-READ", {row["serial_no"] for row in search.json()["items"]})
        for path in (
            f"/records/{self.case_id}",
            f"/records/{self.case_id}/history",
            f"/conflict-reviews/record/{self.case_id}",
            f"/cases/{self.case_id}/tasks?scope=case",
            f"/cases/{self.case_id}/tasks?scope=customer",
            f"/cases/{self.case_id}/logs",
            f"/cases/{self.case_id}/relations",
            f"/cases/{self.case_id}/document-folders",
            f"/cases/{self.case_id}/documents",
            f"/cases/{self.case_id}/action-capabilities",
        ):
            response = await self.client.get(f"{settings.api_prefix}{path}")
            self.assertEqual(response.status_code, 200, f"{path}: {response.text}")

    async def test_configured_company_finance_process_and_admin_can_read(self):
        for username, admin in (
            ("oa0930-company", False), ("oa0930-finance", False),
            ("oa0930-process", False), ("oa0930-admin", True),
        ):
            with self.subTest(username=username):
                self.become(username, admin=admin)
                await self.assert_can_read_case()

    async def test_ordinary_user_cannot_read_unrelated_case(self):
        self.become("oa0930-ordinary")
        search = await self.client.post(f"{settings.api_prefix}/cases/search", json={"scope": "global", "keyword": "全所核查词", "page": 1, "page_size": 10})
        self.assertEqual(search.status_code, 200, search.text)
        self.assertEqual(search.json()["items"], [])
        for path in (
            f"/records/{self.case_id}",
            f"/conflict-reviews/record/{self.case_id}",
            f"/cases/{self.case_id}/tasks",
            f"/cases/{self.case_id}/logs",
            f"/cases/{self.case_id}/relations",
            f"/cases/{self.case_id}/document-folders",
            f"/cases/{self.case_id}/documents",
            f"/cases/{self.case_id}/action-capabilities",
        ):
            response = await self.client.get(f"{settings.api_prefix}{path}")
            self.assertEqual(response.status_code, 404, f"{path}: {response.text}")

    async def test_case_read_scope_does_not_grant_conflict_approval(self):
        for username in ("oa0930-finance", "oa0930-process", "oa0930-company"):
            with self.subTest(username=username):
                self.become(username)
                capabilities = await self.client.get(f"{settings.api_prefix}/cases/{self.case_id}/action-capabilities")
                self.assertEqual(capabilities.status_code, 200, capabilities.text)
                self.assertFalse(capabilities.json()["can_write"])
                update = await self.client.patch(f"{settings.api_prefix}/records/{self.case_id}", json={"title": "不应修改"})
                self.assertIn(update.status_code, (403, 404), update.text)
                response = await self.client.post(f"{settings.api_prefix}/conflict-reviews/123456/decision", json={
                    "rule_id": "R-A01", "decision": "reject", "reason": "测试拒绝",
                    "fingerprint": "a" * 64, "revision": 1,
                })
                self.assertEqual(response.status_code, 403, response.text)


if __name__ == "__main__":
    unittest.main()
