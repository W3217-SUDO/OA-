import unittest

import httpx
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import RolePermission, SecurityPolicy, User
from app.security import hash_password


API = settings.api_prefix


class SystemUserMultiRoleContractTest(unittest.IsolatedAsyncioTestCase):
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
            ]))
        async with self.sessions() as db:
            db.add(SecurityPolicy(id=1, min_password_length=8, max_failed_attempts=5, lock_minutes=30, token_minutes=720, updated_by="test"))
            db.add(User(
                username="admin",
                display_name="管理员",
                department="上海分所",
                role="admin",
                password_hash=hash_password("AdminPass2026!"),
                is_active=True,
                must_change_password=False,
            ))
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://system-multi-role.test")

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

    async def test_role_ids_keep_legacy_role_compatible_and_project_permissions(self):
        admin_headers = await self._admin_headers()

        legacy = await self.client.post(
            f"{API}/system/users",
            headers=admin_headers,
            json={
                "username": "legacy_manager",
                "display_name": "旧协议单角色",
                "password": "LegacyPass2026!",
                "role": "manager",
            },
        )
        self.assertEqual(legacy.status_code, status.HTTP_201_CREATED, legacy.text)
        self.assertEqual(legacy.json()["role"], "manager")
        self.assertEqual(legacy.json()["role_ids"], ["manager"])

        created = await self.client.post(
            f"{API}/system/users",
            headers=admin_headers,
            json={
                "username": "multi_user",
                "display_name": "多角色用户",
                "password": "MultiPass2026!",
                "role_ids": ["user", "manager"],
            },
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.text)
        self.assertEqual(created.json()["role"], "user")
        self.assertEqual(created.json()["role_ids"], ["user", "manager"])
        user_id = created.json()["id"]

        listed = await self.client.get(f"{API}/system/users", headers=admin_headers)
        self.assertEqual(listed.status_code, status.HTTP_200_OK, listed.text)
        listed_user = next(item for item in listed.json()["items"] if item["id"] == user_id)
        self.assertEqual(listed_user["role_ids"], ["user", "manager"])

        user_login = await self._login("multi_user", "MultiPass2026!")
        self.assertEqual(user_login.status_code, status.HTTP_200_OK, user_login.text)
        user_payload = user_login.json()["user"]
        self.assertEqual(user_payload["role_ids"], ["user", "manager"])
        self.assertIn("hr", user_payload["menu_keys"])
        self.assertIn("finance.amount", user_payload["field_keys"])
        self.assertEqual(user_payload["data_scope"], "本人及共享数据")

        changed_password = await self.client.patch(
            f"{API}/auth/me",
            headers={"Authorization": f"Bearer {user_login.json()['access_token']}"},
            json={"current_password": "MultiPass2026!", "new_password": "MultiChanged2026!"},
        )
        self.assertEqual(changed_password.status_code, status.HTTP_200_OK, changed_password.text)

        updated = await self.client.patch(
            f"{API}/system/users/{user_id}",
            headers=admin_headers,
            json={"role_ids": ["auditor", "user"]},
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK, updated.text)
        self.assertEqual(updated.json()["role"], "auditor")
        self.assertEqual(updated.json()["role_ids"], ["auditor", "user"])

    async def test_role_ids_reject_invalid_or_duplicate_values_and_keep_admin(self):
        admin_headers = await self._admin_headers()
        invalid = await self.client.post(
            f"{API}/system/users",
            headers=admin_headers,
            json={
                "username": "invalid_role",
                "display_name": "无效角色",
                "password": "InvalidPass2026!",
                "role_ids": ["user", "unknown"],
            },
        )
        self.assertEqual(invalid.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        duplicate = await self.client.post(
            f"{API}/system/users",
            headers=admin_headers,
            json={
                "username": "duplicate_role",
                "display_name": "重复角色",
                "password": "DuplicatePass2026!",
                "role_ids": ["user", "user"],
            },
        )
        self.assertEqual(duplicate.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        users = await self.client.get(f"{API}/system/users", headers=admin_headers)
        admin = next(item for item in users.json()["items"] if item["username"] == "admin")
        cannot_downgrade = await self.client.patch(
            f"{API}/system/users/{admin['id']}",
            headers=admin_headers,
            json={"role_ids": ["user"]},
        )
        self.assertEqual(cannot_downgrade.status_code, status.HTTP_409_CONFLICT)


if __name__ == "__main__":
    unittest.main()
