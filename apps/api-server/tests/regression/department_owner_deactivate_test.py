"""BUG20261031002 第①步：部门负责人/挂靠人只能选在职账号，删除部门改为停用。"""
import unittest

import httpx
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import (
    BusinessRecord, Department, JobRole, RolePermission, SecurityPolicy, SystemMenu, User, WorkflowEvent,
)
from app.security import hash_password
from tests.personnel_role_fixture import bind_system_role_pages

API = settings.api_prefix


class DepartmentOwnerDeactivateTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=[
                User.__table__, SecurityPolicy.__table__, RolePermission.__table__, SystemMenu.__table__,
                JobRole.__table__, Department.__table__, BusinessRecord.__table__, WorkflowEvent.__table__,
            ]))
        async with self.sessions() as db:
            db.add(SecurityPolicy(id=1, min_password_length=8, max_failed_attempts=5, lock_minutes=30, token_minutes=720, updated_by="test"))
            for username, role, active, department in (
                ("admin", "admin", True, "诉讼一部"), ("zhang", "user", True, "诉讼一部"),
                ("li", "user", True, "空部门"), ("gone", "user", False, "诉讼一部"),
            ):
                db.add(User(username=username, display_name=username.title(), department=department, role=role,
                            password_hash=hash_password("AdminPass2026!"), is_active=active, must_change_password=False))
            db.add(Department(id=1, code="SS1", name="诉讼一部"))
            db.add(Department(id=2, code="EMPTY", name="空部门"))
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://dept-owner.test")
        await bind_system_role_pages(self.sessions)
        login = await self.client.post(f"{API}/auth/login", data={"username": "admin", "password": "AdminPass2026!"},
                                        headers={"Content-Type": "application/x-www-form-urlencoded"})
        self.assertEqual(login.status_code, status.HTTP_200_OK, login.text)
        self.headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_child_department_owner_and_manager(self):
        created = await self.client.post(f"{API}/hr/departments", headers=self.headers, json={
            "code": "SS1A", "name": "诉讼一部A组", "parent_department_id": 1, "manager": "ZHANG", "owner_username": "zhang",
        })
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.text)
        body = created.json()
        self.assertEqual((body["manager"], body["owner_username"], body["owner_display_name"]), ("zhang", "zhang", "Zhang"))

        bad = await self.client.patch(f"{API}/hr/departments/{body['id']}", headers=self.headers, json={"owner_username": "gone"})
        self.assertEqual(bad.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, bad.text)

        top = await self.client.post(f"{API}/hr/departments", headers=self.headers, json={
            "code": "TOP", "name": "顶级部门", "manager": "zhang", "owner_username": "zhang",
        })
        self.assertEqual(top.json()["owner_username"], "", "没有上级部门就没有挂靠人")

        detached = await self.client.patch(f"{API}/hr/departments/{body['id']}", headers=self.headers, json={"parent_department_id": None})
        self.assertEqual(detached.json()["owner_username"], "")

    async def test_delete_only_deactivates(self):
        blocked = await self.client.delete(f"{API}/hr/departments/1", headers=self.headers)
        self.assertEqual(blocked.status_code, status.HTTP_409_CONFLICT, blocked.text)
        async with self.sessions() as db:
            await db.execute(User.__table__.update().where(User.username == "li").values(department="诉讼一部"))
            await db.commit()
        removed = await self.client.delete(f"{API}/hr/departments/2", headers=self.headers)
        self.assertEqual(removed.status_code, status.HTTP_204_NO_CONTENT, removed.text)
        async with self.sessions() as db:
            kept = await db.scalar(select(Department).where(Department.id == 2))
        self.assertIsNotNone(kept)
        self.assertFalse(kept.is_active)


if __name__ == "__main__":
    unittest.main()
