"""In-process contract tests for HR/system-user backend parity gaps."""
import unittest

import httpx
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import FIELD_KEYS, app
from app.models import (
    BusinessRecord,
    JobRole,
    RolePermission,
    SecurityPolicy,
    SystemMenu,
    User,
    WorkflowEvent,
)
from app.security import hash_password


API = settings.api_prefix
DEPT = "default_department"
SCOPE_ALL = "全所数据"
SCOPE_DEPT = "本部门数据"
SCOPE_SELF = "本人及共享数据"
STATUS_ACTIVE = "在职"
STATUS_OFFBOARD = "离职"
JOB_PERMISSION = "案件承办"


class SystemHrBackendGapContractTest(unittest.IsolatedAsyncioTestCase):
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
                JobRole.__table__,
                BusinessRecord.__table__,
                WorkflowEvent.__table__,
            ]))
        async with self.sessions() as db:
            db.add(SecurityPolicy(id=1, min_password_length=8, max_failed_attempts=5, lock_minutes=30, token_minutes=720, updated_by="test"))
            db.add(User(
                username="admin",
                display_name="Admin",
                department=DEPT,
                role="admin",
                password_hash=hash_password("AdminPass2026!"),
                is_active=True,
                must_change_password=False,
            ))
            db.add(User(
                username="leader",
                display_name="Leader",
                department=DEPT,
                role="manager",
                password_hash=hash_password("LeaderPass2026!"),
                is_active=True,
                must_change_password=False,
                profile={"position": "Leader"},
            ))
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://system-hr-gap.test")

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

    async def _admin_headers(self) -> dict[str, str]:
        response = await self._login("admin", "AdminPass2026!")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    async def _leader_id(self) -> int:
        async with self.sessions() as db:
            leader = await db.scalar(select(User).where(User.username == "leader"))
            self.assertIsNotNone(leader)
            return int(leader.id)

    async def test_system_user_parity_fields_round_trip_and_clear(self):
        admin_headers = await self._admin_headers()
        leader_id = await self._leader_id()
        created = await self.client.post(
            f"{API}/system/users",
            headers=admin_headers,
            json={
                "username": "parity_user",
                "display_name": "Parity User",
                "department": DEPT,
                "password": "ParityPass2026!",
                "role": "user",
                "manager_id": leader_id,
                "access_level": SCOPE_DEPT,
                "lead_rate": "10",
                "copy_rate": "5",
            },
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.text)
        body = created.json()
        user_id = body["id"]
        self.assertEqual(body["manager_id"], leader_id)
        self.assertEqual(body["manager_name"], "Leader")
        self.assertEqual(body["access_level"], SCOPE_DEPT)
        self.assertEqual(body["lead_rate"], "10")
        self.assertEqual(body["copy_rate"], "5")

        listed = await self.client.get(f"{API}/system/users", headers=admin_headers)
        self.assertEqual(listed.status_code, status.HTTP_200_OK, listed.text)
        row = next(item for item in listed.json()["items"] if item["id"] == user_id)
        self.assertEqual(row["manager_id"], leader_id)
        self.assertEqual(row["manager_name"], "Leader")
        self.assertEqual(row["access_level"], SCOPE_DEPT)
        self.assertEqual(row["lead_rate"], "10")
        self.assertEqual(row["copy_rate"], "5")

        updated = await self.client.patch(
            f"{API}/system/users/{user_id}",
            headers=admin_headers,
            json={"manager_id": None, "access_level": SCOPE_ALL, "lead_rate": "20", "copy_rate": "8"},
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK, updated.text)
        updated_body = updated.json()
        self.assertIsNone(updated_body["manager_id"])
        self.assertEqual(updated_body["manager_name"], "")
        self.assertEqual(updated_body["access_level"], SCOPE_ALL)
        self.assertEqual(updated_body["lead_rate"], "20")
        self.assertEqual(updated_body["copy_rate"], "8")

        invalid_manager = await self.client.patch(
            f"{API}/system/users/{user_id}",
            headers=admin_headers,
            json={"manager_id": 999999},
        )
        self.assertEqual(invalid_manager.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    async def test_user_permission_overrides_contract(self):
        admin_headers = await self._admin_headers()
        created = await self.client.post(
            f"{API}/system/users",
            headers=admin_headers,
            json={
                "username": "override_user",
                "display_name": "Override User",
                "department": DEPT,
                "password": "OverridePass2026!",
                "role": "user",
            },
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.text)
        user_id = created.json()["id"]

        initial = await self.client.get(f"{API}/system/users/{user_id}/permissions", headers=admin_headers)
        self.assertEqual(initial.status_code, status.HTTP_200_OK, initial.text)
        self.assertEqual(initial.json()["overrides"], {})

        patched = await self.client.patch(
            f"{API}/system/users/{user_id}/permissions",
            headers=admin_headers,
            json={
                "menu_keys": ["user-center", "contract"],
                "field_keys": ["contract.amount"],
                "data_scope": SCOPE_DEPT,
            },
        )
        self.assertEqual(patched.status_code, status.HTTP_200_OK, patched.text)
        patched_body = patched.json()
        self.assertEqual(patched_body["overrides"]["menu_keys"], ["user-center", "contract"])
        self.assertEqual(patched_body["overrides"]["field_keys"], ["contract.amount"])
        self.assertEqual(patched_body["overrides"]["data_scope"], SCOPE_DEPT)
        self.assertIn("user-center", patched_body["effective"]["menu_keys"])
        self.assertIn("contract", patched_body["effective"]["menu_keys"])
        self.assertEqual(patched_body["effective"]["field_keys"], ["contract.amount"])
        self.assertEqual(patched_body["effective"]["data_scope"], SCOPE_DEPT)

        invalid_field = await self.client.patch(
            f"{API}/system/users/{user_id}/permissions",
            headers=admin_headers,
            json={"field_keys": ["bogus.field"]},
        )
        self.assertEqual(invalid_field.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        first_login = await self._login("override_user", "OverridePass2026!")
        self.assertEqual(first_login.status_code, status.HTTP_200_OK, first_login.text)
        user_token = first_login.json()["access_token"]
        changed = await self.client.patch(
            f"{API}/auth/me",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"current_password": "OverridePass2026!", "new_password": "OverrideChanged2026!"},
        )
        self.assertEqual(changed.status_code, status.HTTP_200_OK, changed.text)
        second_login = await self._login("override_user", "OverrideChanged2026!")
        user_token = second_login.json()["access_token"]
        me = await self.client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {user_token}"})
        self.assertEqual(me.status_code, status.HTTP_200_OK, me.text)
        self.assertEqual(me.json()["field_keys"], ["contract.amount"])
        self.assertEqual(me.json()["data_scope"], SCOPE_DEPT)

        cleared = await self.client.patch(
            f"{API}/system/users/{user_id}/permissions",
            headers=admin_headers,
            json={"clear": True},
        )
        self.assertEqual(cleared.status_code, status.HTTP_200_OK, cleared.text)
        self.assertEqual(cleared.json()["overrides"], {})

        admin_id = next(item["id"] for item in (await self.client.get(f"{API}/system/users", headers=admin_headers)).json()["items"] if item["username"] == "admin")
        admin_override = await self.client.patch(
            f"{API}/system/users/{admin_id}/permissions",
            headers=admin_headers,
            json={"field_keys": ["contract.amount"]},
        )
        self.assertEqual(admin_override.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    async def test_cache_clear_all_without_keys(self):
        admin_headers = await self._admin_headers()
        cleared_all = await self.client.post(f"{API}/system/caches/clear", headers=admin_headers, json={})
        self.assertEqual(cleared_all.status_code, status.HTTP_200_OK, cleared_all.text)
        self.assertEqual(len(cleared_all.json()["cleared"]), 8)
        self.assertNotIn("system-parameters", cleared_all.json()["cleared"])

        explicit = await self.client.post(
            f"{API}/system/caches/clear",
            headers=admin_headers,
            json={"cache_keys": ["USER_PREFIX_userlist"]},
        )
        self.assertEqual(explicit.status_code, status.HTTP_200_OK, explicit.text)
        self.assertEqual(explicit.json()["cleared"], ["USER_PREFIX_userlist"])

    async def test_contract_create_accepts_staff_id_and_prefills(self):
        admin_headers = await self._admin_headers()
        async with self.sessions() as db:
            customer = BusinessRecord(
                module="customer", serial_no="CUST-CODEX-001", title="Customer A", status="active",
                owner="admin", department=DEPT, data={"customer_managers": ["admin"]},
            )
            db.add(customer)
            await db.flush()
            staff = BusinessRecord(
                module="hr", serial_no="EMP-CODEX-001", title="Staff A", status=STATUS_ACTIVE,
                owner="staffuser", department=DEPT, data={"username": "staffuser"},
            )
            db.add(staff)
            await db.flush()
            customer_id = int(customer.id)
            staff_id = int(staff.id)
            await db.commit()

        created = await self.client.post(
            f"{API}/contracts",
            headers=admin_headers,
            json={
                "serial_no": "HT-CODEX-001",
                "title": "Contract A",
                "customer": "Customer A",
                "owner": "admin",
                "department": DEPT,
                "data": {"customer_id": customer_id},
                "staff_id": staff_id,
            },
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.text)
        data = created.json()["data"]
        self.assertEqual(data["staff_id"], staff_id)
        self.assertEqual(data["staff_no"], "EMP-CODEX-001")
        self.assertEqual(data["staff_name"], "Staff A")
        self.assertEqual(data["staff_username"], "staffuser")

        unknown = await self.client.post(
            f"{API}/contracts",
            headers=admin_headers,
            json={
                "serial_no": "HT-CODEX-002",
                "title": "Contract B",
                "customer": "Customer A",
                "owner": "admin",
                "department": DEPT,
                "data": {"customer_id": customer_id},
                "staff_id": 999999,
            },
        )
        self.assertEqual(unknown.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    async def test_job_role_field_permissions_model_and_api(self):
        admin_headers = await self._admin_headers()
        created = await self.client.post(
            f"{API}/hr/job-roles",
            headers=admin_headers,
            json={
                "code": "CODEX-FIELD",
                "name": "Field Role",
                "permissions": [JOB_PERMISSION],
                "field_keys": ["contract.amount"],
                "description": "",
                "sort_order": 99,
                "is_active": True,
            },
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.text)
        role = created.json()
        role_id = role["id"]
        self.assertEqual(role["field_keys"], ["contract.amount"])
        self.assertIn("field_keys", JobRole.__table__.columns)

        listed = await self.client.get(f"{API}/hr/job-roles?keyword=CODEX-FIELD", headers=admin_headers)
        self.assertEqual(listed.status_code, status.HTTP_200_OK, listed.text)
        row = next(item for item in listed.json()["items"] if item["id"] == role_id)
        self.assertEqual(row["field_keys"], ["contract.amount"])

        permissions = await self.client.get(f"{API}/hr/job-roles/{role_id}/permissions", headers=admin_headers)
        self.assertEqual(permissions.status_code, status.HTTP_200_OK, permissions.text)
        permissions_body = permissions.json()
        self.assertEqual(permissions_body["field_keys"], ["contract.amount"])
        self.assertEqual(permissions_body["available_field_keys"], FIELD_KEYS)
        self.assertIn("tree", permissions_body)

        updated_permissions = await self.client.patch(
            f"{API}/hr/job-roles/{role_id}/permissions",
            headers=admin_headers,
            json={"permissions": [JOB_PERMISSION], "field_keys": ["customer.legal"]},
        )
        self.assertEqual(updated_permissions.status_code, status.HTTP_200_OK, updated_permissions.text)
        self.assertEqual(updated_permissions.json()["field_keys"], ["customer.legal"])

        invalid_field = await self.client.patch(
            f"{API}/hr/job-roles/{role_id}/permissions",
            headers=admin_headers,
            json={"field_keys": ["bogus.field"]},
        )
        self.assertEqual(invalid_field.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        updated_role = await self.client.patch(
            f"{API}/hr/job-roles/{role_id}",
            headers=admin_headers,
            json={"field_keys": ["finance.amount"]},
        )
        self.assertEqual(updated_role.status_code, status.HTTP_200_OK, updated_role.text)
        self.assertEqual(updated_role.json()["field_keys"], ["finance.amount"])


if __name__ == "__main__":
    unittest.main()
