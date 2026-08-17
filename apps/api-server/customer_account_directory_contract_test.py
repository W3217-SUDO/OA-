import unittest

import httpx
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import DEFAULT_JOB_ROLES, app
from app.models import BusinessRecord, Department, JobRole, RolePermission, SecurityPolicy, User, WorkflowEvent
from app.security import hash_password


API = settings.api_prefix


class CustomerAccountDirectoryContractTest(unittest.IsolatedAsyncioTestCase):
    def test_default_customer_contact_job_role_is_seeded(self):
        role = next((item for item in DEFAULT_JOB_ROLES if item[0] == "CUSTOMER-CONTACT"), None)
        self.assertEqual(role, ("CUSTOMER-CONTACT", "客户联系人", ["客户服务端登录"]))

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
                Department.__table__,
                JobRole.__table__,
                BusinessRecord.__table__,
                WorkflowEvent.__table__,
            ]))

        async with self.sessions() as db:
            db.add(SecurityPolicy(id=1, min_password_length=8, max_failed_attempts=5, lock_minutes=30, token_minutes=720, updated_by="test"))
            db.add(Department(code="SH", name="上海分所", is_active=True))
            db.add(JobRole(code="CUSTOMER", name="客户联系人", is_active=True))
            db.add(User(
                username="admin",
                display_name="管理员",
                department="上海分所",
                role="admin",
                password_hash=hash_password("..123456"),
                is_active=True,
                must_change_password=False,
            ))
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://customer-account.test")

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

    async def test_customer_account_is_login_backed_and_only_in_customer_contact_directory(self):
        admin_login = await self._login("admin", "..123456")
        self.assertEqual(admin_login.status_code, status.HTTP_200_OK, admin_login.text)
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

        created = await self.client.post(
            f"{API}/hr/employees",
            headers=admin_headers,
            json={
                "username": "codexcustomer12",
                "display_name": "CODEX客户账号12",
                "employee_no": "CODEX-CUSTOMER-12",
                "company": "上海申浩律师事务所",
                "department": "上海分所",
                "password": "CodexCustomer123",
                "role": "user",
                "position": "客户联系人",
                "is_active": True,
                "account_type": "客户账号",
                "data": {"account_type": "客户账号", "staff_role": "客户联系人"},
            },
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.text)
        self.assertEqual(created.json()["user"]["username"], "codexcustomer12")

        customer_directory = await self.client.get(
            f"{API}/users/directory", headers=admin_headers, params={"purpose": "customer_contact"},
        )
        self.assertEqual(customer_directory.status_code, status.HTTP_200_OK, customer_directory.text)
        customer = next(item for item in customer_directory.json()["items"] if item["username"] == "codexcustomer12")
        self.assertEqual(customer["account_type"], "客户账号")
        self.assertEqual(customer["display_name"], "CODEX客户账号12")

        staff_directory = await self.client.get(
            f"{API}/users/directory", headers=admin_headers, params={"purpose": "customer_manager"},
        )
        self.assertEqual(staff_directory.status_code, status.HTTP_200_OK, staff_directory.text)
        self.assertNotIn("codexcustomer12", {item["username"] for item in staff_directory.json()["items"]})

        customer_login = await self._login("codexcustomer12", "CodexCustomer123")
        self.assertEqual(customer_login.status_code, status.HTTP_200_OK, customer_login.text)

        async with self.sessions() as db:
            user = await db.scalar(select(User).where(User.username == "codexcustomer12"))
            record = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == "CODEX-CUSTOMER-12"))
            self.assertIsNotNone(user)
            self.assertIsNotNone(record)
            self.assertEqual((record.data or {}).get("account_type"), "客户账号")
            self.assertEqual((record.data or {}).get("username"), "codexcustomer12")

    async def test_existing_non_admin_login_can_be_restored_as_customer_account(self):
        async with self.sessions() as db:
            db.add(User(
                username="codexlegacycustomer",
                display_name="CODEX旧客户账号",
                department="上海分所",
                role="manager",
                role_ids=["manager"],
                profile={"account_type": "员工账号"},
                password_hash=hash_password("CodexLegacy123"),
                is_active=True,
                must_change_password=False,
            ))
            await db.commit()

        admin_login = await self._login("admin", "..123456")
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        restored = await self.client.post(
            f"{API}/hr/employees",
            headers=admin_headers,
            json={
                "username": "codexlegacycustomer",
                "display_name": "CODEX旧客户账号",
                "employee_no": "SYS-0099",
                "company": "上海申浩律师事务所",
                "department": "上海分所",
                "password": "",
                "role": "user",
                "position": "客户联系人",
                "is_active": True,
                "account_type": "客户账号",
                "data": {"account_type": "客户账号", "staff_role": "客户联系人"},
            },
        )
        self.assertEqual(restored.status_code, status.HTTP_201_CREATED, restored.text)
        self.assertEqual(restored.json()["user"]["role"], "user")
        self.assertEqual(restored.json()["user"]["role_ids"], ["user"])

        directory = await self.client.get(
            f"{API}/users/directory", headers=admin_headers, params={"purpose": "customer_contact"},
        )
        self.assertEqual(directory.status_code, status.HTTP_200_OK, directory.text)
        restored_item = next(item for item in directory.json()["items"] if item["username"] == "codexlegacycustomer")
        self.assertEqual(restored_item["account_type"], "客户账号")
        self.assertTrue(restored_item["eligible_customer_person"])

        customer_login = await self._login("codexlegacycustomer", "CodexLegacy123")
        self.assertEqual(customer_login.status_code, status.HTTP_200_OK, customer_login.text)


if __name__ == "__main__":
    unittest.main()
