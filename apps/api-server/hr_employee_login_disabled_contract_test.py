import unittest

import httpx
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, Department, JobRole, RolePermission, SecurityPolicy, SystemMenu, User, WorkflowEvent
from app.security import hash_password


API = settings.api_prefix


class HrEmployeeLoginDisabledContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=[
                User.__table__,
                SecurityPolicy.__table__,
                RolePermission.__table__,
                SystemMenu.__table__,
                Department.__table__,
                JobRole.__table__,
                BusinessRecord.__table__,
                WorkflowEvent.__table__,
            ]))

        async with self.sessions() as db:
            db.add(SecurityPolicy(id=1, min_password_length=8, max_failed_attempts=5, lock_minutes=30, token_minutes=720, updated_by="test"))
            db.add(Department(code="SH", name="上海分所", is_active=True))
            db.add(JobRole(code="LAWYER", name="律师助理", is_active=True))
            db.add(User(
                username="admin",
                display_name="管理员",
                department="上海分所",
                role="admin",
                password_hash=hash_password("..123456"),
                is_active=True,
                must_change_password=False,
            ))
            db.add(User(
                username="codexactive",
                display_name="CODEX启停测试",
                department="上海分所",
                role="user",
                password_hash=hash_password("Codex123456"),
                profile={"employee_no": "CODEX-ACTIVE-001", "position": "律师助理"},
                is_active=True,
                must_change_password=False,
            ))
            await db.flush()
            db.add(BusinessRecord(
                module="hr",
                serial_no="CODEX-ACTIVE-001",
                title="CODEX启停测试",
                customer="上海申浩律师事务所",
                status="在职",
                owner="codexactive",
                department="上海分所",
                data={
                    "username": "codexactive",
                    "account_type": "员工账号",
                    "role": "user",
                    "position": "律师助理",
                    "is_active": True,
                    "joined_at": "2026-08-04",
                },
            ))
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://hr-login-disabled.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def _login(self, username: str, password: str) -> httpx.Response:
        return await self.client.post(
            f"{API}/auth/login",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    async def test_employee_login_switch_disables_list_display_login_and_existing_token(self):
        admin_login = await self._login("admin", "..123456")
        self.assertEqual(admin_login.status_code, status.HTTP_200_OK)
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        employee_login = await self._login("codexactive", "Codex123456")
        self.assertEqual(employee_login.status_code, status.HTTP_200_OK)
        employee_token = employee_login.json()["access_token"]

        listed = await self.client.get(f"{API}/hr/employees", headers=admin_headers, params={"username": "codexactive"})
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        employee = listed.json()["items"][0]
        self.assertIs(employee["data"]["is_active"], True)

        updated = await self.client.patch(
            f"{API}/hr/employees/{employee['id']}",
            headers=admin_headers,
            json={
                "username": "codexactive",
                "display_name": "CODEX启停测试",
                "department": "上海分所",
                "role": "user",
                "position": "律师助理",
                "is_active": False,
                "email": "",
                "mobile": "",
                "office_phone": "",
                "joined_at": "2026-08-04",
                "left_at": None,
                "data": {**employee["data"], "account_type": "员工账号", "position": "律师助理"},
            },
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK, updated.text)
        self.assertIs(updated.json()["employee"]["data"]["is_active"], False)
        self.assertIs(updated.json()["user"]["is_active"], False)

        disabled_list = await self.client.get(f"{API}/hr/employees", headers=admin_headers, params={"username": "codexactive"})
        self.assertEqual(disabled_list.status_code, status.HTTP_200_OK)
        self.assertIs(disabled_list.json()["items"][0]["data"]["is_active"], False)

        failed_login = await self._login("codexactive", "Codex123456")
        self.assertEqual(failed_login.status_code, status.HTTP_401_UNAUTHORIZED)

        blocked_session = await self.client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {employee_token}"})
        self.assertEqual(blocked_session.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("停用", blocked_session.json()["detail"])

        async with self.sessions() as db:
            user = await db.scalar(select(User).where(User.username == "codexactive"))
            record = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == "CODEX-ACTIVE-001"))
            self.assertFalse(user.is_active)
            self.assertIs((record.data or {}).get("is_active"), False)


if __name__ == "__main__":
    unittest.main()
