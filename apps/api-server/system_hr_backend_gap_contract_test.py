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
    Department,
    FileAttachment,
    JobRole,
    LegacyContract,
    LegacyContractFile,
    LegacyCustomer,
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
                Department.__table__,
                BusinessRecord.__table__,
                FileAttachment.__table__,
                LegacyContract.__table__,
                LegacyContractFile.__table__,
                LegacyCustomer.__table__,
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
            db.add(User(
                username="codex_missing_name",
                display_name="codex_missing_name",
                department=DEPT,
                role="user",
                password_hash=hash_password("MissingPass2026!"),
                is_active=True,
                must_change_password=False,
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

    async def test_maintained_english_person_name_remains_visible(self):
        admin_headers = await self._admin_headers()

        users = await self.client.get(f"{API}/system/users?keyword=codex_missing_name", headers=admin_headers)
        self.assertEqual(users.status_code, status.HTTP_200_OK, users.text)
        user_row = users.json()["items"][0]
        self.assertEqual(user_row["username"], "codex_missing_name")
        self.assertEqual(user_row["display_name"], "codex_missing_name")
        self.assertEqual(user_row["person_display_name"], "codex_missing_name")
        self.assertFalse(user_row["display_name_missing"])

        employees = await self.client.get(f"{API}/hr/employees?username=codex_missing_name", headers=admin_headers)
        self.assertEqual(employees.status_code, status.HTTP_200_OK, employees.text)
        employee_row = employees.json()["items"][0]
        self.assertEqual(employee_row["data"]["username"], "codex_missing_name")
        self.assertEqual(employee_row["title"], "codex_missing_name")
        self.assertEqual(employee_row["person_display_name"], "codex_missing_name")
        self.assertFalse(employee_row["display_name_missing"])

    async def test_administrator_cannot_reset_the_current_login_password(self):
        admin_headers = await self._admin_headers()
        async with self.sessions() as db:
            admin = await db.scalar(select(User).where(User.username == "admin"))
            self.assertIsNotNone(admin)
            admin_id = int(admin.id)

        reset = await self.client.post(
            f"{API}/system/users/{admin_id}/reset-password",
            headers=admin_headers,
            json={"new_password": "AdminReset2026!"},
        )
        self.assertEqual(reset.status_code, status.HTTP_409_CONFLICT, reset.text)

    async def test_hr_employee_uses_linked_account_name_when_archive_title_is_empty(self):
        admin_headers = await self._admin_headers()
        async with self.sessions() as db:
            db.add(User(
                username="codex_account_name",
                display_name="律师助理2",
                department=DEPT,
                role="user",
                password_hash=hash_password("AccountNamePass2026!"),
                is_active=True,
                must_change_password=False,
            ))
            await db.flush()
            db.add(BusinessRecord(
                module="hr",
                serial_no="CODEX-HR-NAME-FALLBACK",
                title="",
                customer="上海申浩律师事务所",
                status=STATUS_ACTIVE,
                owner="codex_account_name",
                department=DEPT,
                data={"username": "codex_account_name"},
            ))
            await db.commit()

        response = await self.client.get(
            f"{API}/hr/employees?username=codex_account_name",
            headers=admin_headers,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.text)
        row = response.json()["items"][0]
        self.assertEqual(row["person_display_name"], "律师助理2")
        self.assertEqual(row["title"], "")
        self.assertFalse(row["display_name_missing"])

    async def test_organization_person_display_fields_use_maintained_english_names(self):
        admin_headers = await self._admin_headers()
        async with self.sessions() as db:
            db.add(Department(
                code="CODEX-NAME",
                name="姓名显示测试部",
                manager="codex_missing_name",
                created_by="codex_missing_name",
                updated_by="leader",
            ))
            await db.commit()

        departments = await self.client.get(f"{API}/hr/departments?keyword=CODEX-NAME", headers=admin_headers)
        self.assertEqual(departments.status_code, status.HTTP_200_OK, departments.text)
        department_row = departments.json()["items"][0]
        self.assertEqual(department_row["manager"], "codex_missing_name")
        self.assertEqual(department_row["manager_display_name"], "codex_missing_name")
        self.assertFalse(department_row["manager_display_name_missing"])
        self.assertEqual(department_row["created_by_display_name"], "codex_missing_name")
        self.assertFalse(department_row["created_by_display_name_missing"])
        self.assertEqual(department_row["updated_by"], "leader")
        self.assertEqual(department_row["updated_by_display_name"], "Leader")
        self.assertFalse(department_row["updated_by_display_name_missing"])

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
        self.assertIn("user-center", me.json()["menu_keys"])
        self.assertIn("contract", me.json()["menu_keys"])
        self.assertNotIn("customer", me.json()["menu_keys"])
        self.assertNotIn("case", me.json()["menu_keys"])

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

    async def test_hr_employee_edit_persists_contract_approval_flag_to_system_user(self):
        admin_headers = await self._admin_headers()
        async with self.sessions() as db:
            db.add(Department(code="CODEX-APPROVAL", name=DEPT, is_active=True))
            db.add(JobRole(code="CODEX-APPROVER", name="审批员", is_active=True))
            user = User(
                username="approval_user",
                display_name="张测试",
                department=DEPT,
                role="user",
                password_hash=hash_password("ApprovalPass2026!"),
                is_active=True,
                must_change_password=False,
                profile={},
            )
            db.add(user)
            employee = BusinessRecord(
                module="hr",
                serial_no="HR-APPROVER-01",
                title="张测试",
                status=STATUS_ACTIVE,
                owner="approval_user",
                department=DEPT,
                data={"username": "approval_user"},
            )
            db.add(employee)
            await db.flush()
            employee_id = int(employee.id)
            await db.commit()

        patched = await self.client.patch(
            f"{API}/hr/employees/{employee_id}",
            headers=admin_headers,
            json={
                "username": "approval_user",
                "display_name": "张测试",
                "department": DEPT,
                "role": "user",
                "position": "审批员",
                "is_active": True,
                "email": "",
                "mobile": "",
                "office_phone": "",
                "joined_at": "2026-08-05",
                "left_at": None,
                "data": {"contract_approval_enabled": True},
            },
        )
        self.assertEqual(patched.status_code, status.HTTP_200_OK, patched.text)
        self.assertTrue(patched.json()["user"]["contract_approval_enabled"])
        self.assertTrue(patched.json()["employee"]["data"]["contract_approval_enabled"])

        users = await self.client.get(f"{API}/system/users?keyword=approval_user", headers=admin_headers)
        self.assertEqual(users.status_code, status.HTTP_200_OK, users.text)
        self.assertTrue(users.json()["items"][0]["contract_approval_enabled"])

        employees = await self.client.get(f"{API}/hr/employees?username=approval_user", headers=admin_headers)
        self.assertEqual(employees.status_code, status.HTTP_200_OK, employees.text)
        self.assertTrue(employees.json()["items"][0]["data"]["contract_approval_enabled"])

        settings = await self.client.get(f"{API}/contracts/approver-settings", headers=admin_headers)
        self.assertEqual(settings.status_code, status.HTTP_200_OK, settings.text)
        approver_row = next(item for item in settings.json()["items"] if item["username"] == "approval_user")
        self.assertTrue(approver_row["selected"])

        directory = await self.client.get(f"{API}/users/directory", headers=admin_headers)
        self.assertEqual(directory.status_code, status.HTTP_200_OK, directory.text)
        directory_row = next(item for item in directory.json()["items"] if item["username"] == "approval_user")
        self.assertTrue(directory_row["can_approve_contract"])

    async def test_hr_employee_edit_keeps_legacy_position_but_rejects_unknown_replacement(self):
        admin_headers = await self._admin_headers()
        async with self.sessions() as db:
            db.add(Department(code="CODEX-LEGACY", name="Legacy Department", is_active=True))
            user = User(
                username="legacy_position_user",
                display_name="Legacy Position User",
                department="Legacy Department",
                role="user",
                password_hash=hash_password("LegacyPositionPass2026!"),
                is_active=True,
                must_change_password=False,
                profile={"position": "已归档历史职务"},
            )
            db.add(user)
            employee = BusinessRecord(
                module="hr",
                serial_no="HR-LEGACY-POSITION-01",
                title="Legacy Position User",
                status=STATUS_ACTIVE,
                owner="legacy_position_user",
                department="Legacy Department",
                data={"username": "legacy_position_user", "position": "已归档历史职务"},
            )
            db.add(employee)
            await db.flush()
            employee_id = int(employee.id)
            await db.commit()

        payload = {
            "username": "legacy_position_user",
            "display_name": "Legacy Position User",
            "department": "Legacy Department",
            "role": "user",
            "position": "已归档历史职务",
            "is_active": True,
            "email": "legacy@example.com",
            "mobile": "13800000001",
            "office_phone": "021-12345678",
            "joined_at": "2026-08-12",
            "left_at": None,
            "data": {"position": "已归档历史职务"},
        }
        preserved = await self.client.patch(f"{API}/hr/employees/{employee_id}", headers=admin_headers, json=payload)
        self.assertEqual(preserved.status_code, status.HTTP_200_OK, preserved.text)
        self.assertEqual(preserved.json()["employee"]["data"]["mobile"], "13800000001")

        payload["position"] = "不存在的新职务"
        replaced = await self.client.patch(f"{API}/hr/employees/{employee_id}", headers=admin_headers, json=payload)
        self.assertEqual(replaced.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, replaced.text)

    async def test_hr_contract_approval_switch_endpoint_controls_contract_directory(self):
        admin_headers = await self._admin_headers()
        async with self.sessions() as db:
            db.add(Department(code="CODEX-SWITCH", name=DEPT, is_active=True))
            db.add(JobRole(code="CODEX-SWITCH-ROLE", name="审批助理", is_active=True))
            user = User(
                username="switch_approver",
                display_name="李测试",
                department=DEPT,
                role="user",
                password_hash=hash_password("SwitchPass2026!"),
                is_active=True,
                must_change_password=False,
                profile={"account_type": "员工账号", "position": "审批助理", "contract_approval_enabled": False},
            )
            db.add(user)
            employee = BusinessRecord(
                module="hr",
                serial_no="HR-SWITCH-01",
                title="李测试",
                status=STATUS_ACTIVE,
                owner="switch_approver",
                department=DEPT,
                data={"username": "switch_approver", "account_type": "员工账号", "contract_approval_enabled": False},
            )
            db.add(employee)
            await db.flush()
            employee_id = int(employee.id)
            await db.commit()

        enabled = await self.client.patch(
            f"{API}/hr/employees/{employee_id}/contract-approval-status",
            headers=admin_headers,
            json={"contract_approval_enabled": True},
        )
        self.assertEqual(enabled.status_code, status.HTTP_200_OK, enabled.text)
        self.assertTrue(enabled.json()["employee"]["data"]["contract_approval_enabled"])
        self.assertTrue(enabled.json()["user"]["contract_approval_enabled"])
        self.assertTrue(enabled.json()["can_approve_contract"])

        directory = await self.client.get(f"{API}/users/directory", headers=admin_headers)
        self.assertEqual(directory.status_code, status.HTTP_200_OK, directory.text)
        directory_row = next(item for item in directory.json()["items"] if item["username"] == "switch_approver")
        self.assertTrue(directory_row["can_approve_contract"])

        disabled = await self.client.patch(
            f"{API}/hr/employees/{employee_id}/contract-approval-status",
            headers=admin_headers,
            json={"contract_approval_enabled": False},
        )
        self.assertEqual(disabled.status_code, status.HTTP_200_OK, disabled.text)
        self.assertFalse(disabled.json()["employee"]["data"]["contract_approval_enabled"])
        self.assertFalse(disabled.json()["user"]["contract_approval_enabled"])
        self.assertFalse(disabled.json()["can_approve_contract"])

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

    async def test_job_role_menu_permissions_can_be_saved_and_reach_login_session(self):
        admin_headers = await self._admin_headers()
        async with self.sessions() as db:
            role = JobRole(
                code="CODEX-ASSISTANT",
                name="律师助理测试",
                permissions=["合同审批"],
                is_active=True,
                created_by="admin",
                updated_by="admin",
            )
            user = User(
                username="assistant_menu_user",
                display_name="助理测试",
                department=DEPT,
                role="user",
                password_hash=hash_password("AssistantPass2026!"),
                is_active=True,
                must_change_password=False,
                profile={"position": "律师助理测试"},
            )
            db.add_all([role, user])
            await db.commit()
            role_id = role.id

        updated = await self.client.patch(
            f"{API}/hr/job-roles/{role_id}/permissions",
            headers=admin_headers,
            json={
                "permissions": [
                    "contract-audit",
                    "contract-audit-pending",
                    "seal",
                    "seal-my",
                    "seal-audit",
                    "seal-audit-pending",
                    "合同审批",
                    "用印审批",
                ],
            },
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK, updated.text)

        login = await self._login("assistant_menu_user", "AssistantPass2026!")
        self.assertEqual(login.status_code, status.HTTP_200_OK, login.text)
        me = await self.client.get(
            f"{API}/auth/me",
            headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        )
        self.assertEqual(me.status_code, status.HTTP_200_OK, me.text)
        self.assertIn("contract-audit-pending", me.json()["menu_keys"])
        self.assertIn("seal-audit-pending", me.json()["menu_keys"])
        self.assertNotIn("customer", me.json()["menu_keys"])


if __name__ == "__main__":
    unittest.main()
