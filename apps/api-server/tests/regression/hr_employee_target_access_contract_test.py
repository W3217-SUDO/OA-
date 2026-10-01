"""Focused contracts for delegated HR employee edit boundaries."""

from __future__ import annotations

import unittest

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.main import _require_hr_employee_target_access
from app.models import BusinessRecord, JobRole, RolePermission, SystemParameter, User


class HrEmployeeTargetAccessContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        tables = [
            BusinessRecord.__table__, JobRole.__table__, RolePermission.__table__,
            SystemParameter.__table__, User.__table__,
        ]
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda sync: Base.metadata.create_all(sync, tables=tables))
        sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        self.db = sessions()
        self.db.add_all([
            JobRole(
                code="HR-DEPT-EDITOR", name="部门人事编辑",
                permissions=["员工修改"], data_scope="本部门数据",
            ),
            User(
                username="hr-editor", password_hash="unused", display_name="人事编辑",
                role="user", department="上海分所",
                profile={"permission_role": "部门人事编辑"}, is_active=True,
            ),
            User(
                username="admin-target", password_hash="unused", display_name="管理员目标",
                role="admin", role_ids=["admin"], department="上海分所", profile={}, is_active=True,
            ),
            User(
                username="other-target", password_hash="unused", display_name="外部门目标",
                role="user", department="北京分所", profile={}, is_active=True,
            ),
        ])
        await self.db.flush()
        self.same_department = BusinessRecord(
            module="hr", serial_no="HR-SAME", title="同部门员工", status="在职",
            owner="same-target", department="上海分所", data={"username": "same-target"},
        )
        self.admin_employee = BusinessRecord(
            module="hr", serial_no="HR-ADMIN", title="管理员目标", status="在职",
            owner="admin-target", department="上海分所", data={"username": "admin-target"},
        )
        self.other_department = BusinessRecord(
            module="hr", serial_no="HR-OTHER", title="外部门目标", status="在职",
            owner="other-target", department="北京分所", data={"username": "other-target"},
        )
        self.db.add_all([self.same_department, self.admin_employee, self.other_department])
        await self.db.commit()
        self.identity = {"username": "hr-editor", "role": "user"}

    async def asyncTearDown(self) -> None:
        await self.db.close()
        await self.engine.dispose()

    async def test_department_editor_can_edit_normal_employee_in_same_department(self) -> None:
        await _require_hr_employee_target_access(self.same_department, self.identity, self.db)

    async def test_department_editor_cannot_edit_system_admin(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            await _require_hr_employee_target_access(self.admin_employee, self.identity, self.db)
        self.assertEqual(raised.exception.status_code, 403)

    async def test_department_editor_cannot_cross_department_scope(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            await _require_hr_employee_target_access(self.other_department, self.identity, self.db)
        self.assertEqual(raised.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
