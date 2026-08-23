"""Executable contracts for case action capabilities from personnel roles."""

from __future__ import annotations

import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.main import _case_action_granted, _case_detail_action_capabilities
from app.models import BusinessRecord, JobRole, RolePermission, SystemParameter, User


class CaseJobActionCapabilitiesContractTest(unittest.IsolatedAsyncioTestCase):
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
            JobRole(code="CASE-VIEWER", name="案件只读岗", permissions=["案件查看"]),
            JobRole(code="CASE-HANDLER", name="案件承办岗", permissions=["案件承办"]),
            User(username="case-viewer", password_hash="unused", display_name="只读人员", role="user", department="上海分所", profile={"permission_role": "案件只读岗"}),
            User(username="case-handler", password_hash="unused", display_name="承办人员", role="user", department="上海分所", profile={"permission_role": "案件承办岗"}),
            User(username="case-unbound", password_hash="unused", display_name="未绑定岗位人员", role="user", department="上海分所", profile={}),
        ])
        await self.db.flush()
        self.viewer_case = BusinessRecord(module="case", serial_no="CASE-VIEWER-1", title="只读案件", customer="客户", status="一审", owner="case-viewer", department="上海分所", data={})
        self.handler_case = BusinessRecord(module="case", serial_no="CASE-HANDLER-1", title="承办案件", customer="客户", status="一审", owner="case-handler", department="上海分所", data={})
        self.db.add_all([self.viewer_case, self.handler_case])
        await self.db.commit()

    async def asyncTearDown(self) -> None:
        await self.db.close()
        await self.engine.dispose()

    async def test_configured_read_only_role_cannot_create_case_log(self) -> None:
        identity = {"username": "case-viewer", "role": "user"}
        self.assertFalse(await _case_action_granted(identity, self.db, "case.log.create"))
        capabilities = await _case_detail_action_capabilities(self.viewer_case, identity, self.db)
        self.assertFalse(capabilities["can_create_log"])
        self.assertFalse(capabilities["can_create_reminder"])

    async def test_configured_handler_role_gets_real_case_actions(self) -> None:
        identity = {"username": "case-handler", "role": "user"}
        self.assertTrue(await _case_action_granted(identity, self.db, "case.log.create"))
        capabilities = await _case_detail_action_capabilities(self.handler_case, identity, self.db)
        self.assertTrue(capabilities["can_create_log"])
        self.assertTrue(capabilities["can_create_reminder"])
        self.assertTrue(capabilities["can_update_progress"])

    async def test_unbound_user_does_not_receive_case_actions_by_default(self) -> None:
        identity = {"username": "case-unbound", "role": "user"}
        self.assertFalse(await _case_action_granted(identity, self.db, "case.log.create"))


if __name__ == "__main__":
    unittest.main()
