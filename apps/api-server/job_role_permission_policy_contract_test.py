"""Focused contract tests for the unified HR job-role permission policy."""
import unittest

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import (
    FIELD_KEYS,
    _record_scope_conditions,
    _require_hr_employee_action,
    _require_record_module_menu,
    _user_permission_payload,
)
from app.models import JobRole, RolePermission, User
from app.security import hash_password


class JobRolePermissionPolicyContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda sync: Base.metadata.create_all(sync, tables=[
                User.__table__, RolePermission.__table__, JobRole.__table__,
            ]))
        async with self.sessions() as db:
            db.add_all([
                User(username="admin", display_name="Admin", department="D", role="admin", password_hash=hash_password("AdminPass2026!")),
                User(username="historic", display_name="Historic", department="D", role="user", password_hash=hash_password("HistoricPass2026!")),
                User(username="operator", display_name="Operator", department="D", role="user", password_hash=hash_password("OperatorPass2026!"), profile={"permission_role_code": "HR-OP"}),
                User(username="viewer", display_name="Viewer", department="D", role="user", password_hash=hash_password("ViewerPass2026!"), profile={"permission_role_code": "HR-VIEW"}),
                JobRole(code="HR-OP", name="HR Operator", permissions=["员工查看", "员工新建", "员工修改", "客户新建", "客户修改"], field_keys=[], field_keys_configured=True, data_scope="全所数据"),
                JobRole(code="HR-VIEW", name="HR Viewer", permissions=["员工查看"], field_keys_configured=True, data_scope="本人及共享数据"),
            ])
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_explicit_job_role_unifies_menu_actions_fields_and_scope(self):
        async with self.sessions() as db:
            operator = await db.scalar(select(User).where(User.username == "operator"))
            payload = await _user_permission_payload(operator, db)
            self.assertIn("hr-new", payload["menu_keys"])
            self.assertIn("hr.employee.create", payload["action_keys"])
            self.assertIn("record.customer.update", payload["action_keys"])
            self.assertEqual(payload["field_keys"], [])
            self.assertEqual(payload["data_scope"], "全所数据")
            identity = {"username": "operator", "role": "user", "role_ids": ["user"]}
            self.assertEqual(await _record_scope_conditions(identity, db), [])
            await _require_hr_employee_action(identity, db, "hr.employee.create", "新建")
            await _require_hr_employee_action(identity, db, "hr.employee.update", "修改")
            await _require_record_module_menu("customer", identity, db, action="新建")
            await _require_record_module_menu("customer", identity, db, action="编辑")

    async def test_view_only_and_unbound_accounts_cannot_gain_write_actions(self):
        async with self.sessions() as db:
            viewer_identity = {"username": "viewer", "role": "user", "role_ids": ["user"]}
            with self.assertRaises(HTTPException) as error:
                await _require_hr_employee_action(viewer_identity, db, "hr.employee.create", "新建")
            self.assertEqual(error.exception.status_code, 403)
            historic = await db.scalar(select(User).where(User.username == "historic"))
            fallback = await _user_permission_payload(historic, db)
            self.assertEqual(fallback["action_keys"], [])
            self.assertNotEqual(fallback["field_keys"], [])

    async def test_admin_remains_full_access_even_without_hr_binding(self):
        async with self.sessions() as db:
            admin = await db.scalar(select(User).where(User.username == "admin"))
            payload = await _user_permission_payload(admin, db)
            self.assertEqual(payload["action_keys"], ["*"])
            self.assertEqual(set(payload["field_keys"]), set(FIELD_KEYS))
            await _require_hr_employee_action({"username": "admin", "role": "admin", "role_ids": ["admin"]}, db, "hr.employee.create", "新建")


if __name__ == "__main__":
    unittest.main()
