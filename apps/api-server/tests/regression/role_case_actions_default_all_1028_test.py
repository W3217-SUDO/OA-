"""BUG20261028012：角色权限细到案件功能。

上线时所有角色默认全勾案件功能（一次性），管理员之后按角色取消的功能不会在重启时补回；
“更多操作”里的案件任务、案件日志、导出案件打印表也按功能授权，导出接口后台拒绝。
"""

from __future__ import annotations

import unittest

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.constants import CASE_ACTIONS_EXPLICIT_MARKER, CONTRACT_ROLE_ACTIONS, CUSTOMER_ROLE_ACTIONS, IPR_ROLE_ACTIONS, TASK_INVESTIGATION_ROLE_ACTIONS, SYSTEM_ACTION_BY_CODE, SYSTEM_ACTION_DEFINITIONS
from app.core.permissions import _effective_job_role_action_keys
from app.core.startup_data import CASE_ACTIONS_DEFAULT_ALL_REVISION, _grant_case_actions_to_all_roles_once
from app.database import Base
from app.models import JobRole, RolePermission


CASE_CODES = [item["code"] for item in SYSTEM_ACTION_DEFINITIONS if item["code"].startswith("case.")]


class RoleCaseActionsDefaultAllTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                RolePermission(role="user", display_name="普通用户", data_scope="本人及共享数据",
                               menu_keys=["case", "case-mine", "@action:case.detail.update"], field_keys=[]),
                RolePermission(role="admin", display_name="管理员", data_scope="全所数据", menu_keys=["case"], field_keys=[]),
                JobRole(code="CODEX-1028-12-ASSISTANT", name="CODEX 律师助理",
                        permissions=["case", "case-mine", "案件费用申请", CASE_ACTIONS_EXPLICIT_MARKER]),
                JobRole(code="CODEX-1028-12-LAWYER", name="CODEX 承办律师", permissions=["案件办理"]),
                JobRole(code="SYSTEM-ADMIN", name="系统管理员", permissions=["case"]),
            ])
            await db.commit()

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    def test_customer_functions_are_catalogued_under_my_customers(self) -> None:
        for code, _ in CUSTOMER_ROLE_ACTIONS:
            self.assertEqual(SYSTEM_ACTION_BY_CODE[code]["menu_key"], "customer-mine")
        for code, _ in CONTRACT_ROLE_ACTIONS:
            self.assertEqual(SYSTEM_ACTION_BY_CODE[code]["menu_key"], "contract-mine")
        for code, _, menu_key in (*IPR_ROLE_ACTIONS, *TASK_INVESTIGATION_ROLE_ACTIONS):
            self.assertEqual(SYSTEM_ACTION_BY_CODE[code]["menu_key"], menu_key)

    def test_new_case_functions_are_catalogued_under_my_cases(self) -> None:
        for code in ("case.task.view", "case.log.view", "case.export.print"):
            self.assertEqual(SYSTEM_ACTION_BY_CODE[code]["menu_key"], "case-mine")

    def test_removed_fee_menu_functions_are_hidden_from_role_tree(self) -> None:
        """BUG20261028015：费用“其他操作”去掉的入口，角色权限里也不再显示。"""
        from app.core.constants import ROLE_TREE_HIDDEN_ACTION_CODES
        from app.core.permissions import _organization_permission_tree
        from app.models import SystemMenu

        tree = _organization_permission_tree([SystemMenu(id=1, key="case-mine", label="我的案件", parent_key="")], [], set())
        codes = {child["node_code"] for child in tree[0]["children"]}
        # BUG20261028012（2026-10-29）：案件分三块显示，块下每个功能单独勾选；其他案件功能给了页面就有。
        self.assertEqual(codes, {"group:case-operations", "group:case-fee-other", "group:case-internal-fee"})
        codes = {child["node_code"] for group in tree[0]["children"] for child in group["children"]}
        self.assertIn("case.fee.update", codes)
        self.assertFalse(codes & ROLE_TREE_HIDDEN_ACTION_CODES)

    async def test_all_roles_get_every_case_function_once(self) -> None:
        async with self.sessions() as db:
            await _grant_case_actions_to_all_roles_once(db)
            await db.commit()
        async with self.sessions() as db:
            user_permission = await db.scalar(select(RolePermission).where(RolePermission.role == "user"))
            admin_permission = await db.scalar(select(RolePermission).where(RolePermission.role == "admin"))
            self.assertTrue({f"@action:{code}" for code in CASE_CODES} <= set(user_permission.menu_keys))
            self.assertEqual(admin_permission.menu_keys, ["case"])
            # 第二批：客户功能同样默认全勾。
            customer_codes = [code for code, _ in CUSTOMER_ROLE_ACTIONS]
            self.assertTrue({f"@action:{code}" for code in customer_codes} <= set(user_permission.menu_keys))
            self.assertTrue({f"@action:{code}" for code, _ in CONTRACT_ROLE_ACTIONS} <= set(user_permission.menu_keys))
            self.assertTrue({f"@action:{code}" for code, *_ in IPR_ROLE_ACTIONS} <= set(user_permission.menu_keys))
            self.assertTrue({f"@action:{code}" for code, *_ in TASK_INVESTIGATION_ROLE_ACTIONS} <= set(user_permission.menu_keys))
            from app.core.constants import FINANCE_EDIT_DELETE_ACTIONS
            self.assertTrue({f"@action:{code}" for code, *_ in FINANCE_EDIT_DELETE_ACTIONS} <= set(user_permission.menu_keys))
            jobs = {role.code: role for role in (await db.scalars(select(JobRole))).all()}
            for code in ("CODEX-1028-12-ASSISTANT", "CODEX-1028-12-LAWYER"):
                role = jobs[code]
                self.assertEqual(set(_effective_job_role_action_keys(role)) & set(CASE_CODES), set(CASE_CODES))
                self.assertTrue(set(customer_codes) <= set(_effective_job_role_action_keys(role)))
            # 旧标签保留，菜单和其他动作不因此改变。
            self.assertIn("案件办理", jobs["CODEX-1028-12-LAWYER"].permissions)
            self.assertIn("案件费用申请", jobs["CODEX-1028-12-ASSISTANT"].permissions)
            self.assertEqual(jobs["SYSTEM-ADMIN"].permissions, ["case"])

            # 管理员取消某个功能后，重启不会补回。
            lawyer = jobs["CODEX-1028-12-LAWYER"]
            lawyer.permissions = [value for value in lawyer.permissions if value != "action:case.export.print"]
            await db.commit()
        async with self.sessions() as db:
            await _grant_case_actions_to_all_roles_once(db)
            await db.commit()
            lawyer = await db.scalar(select(JobRole).where(JobRole.code == "CODEX-1028-12-LAWYER"))
            self.assertNotIn("case.export.print", _effective_job_role_action_keys(lawyer))
            self.assertTrue((await db.execute(
                text("SELECT key FROM schema_migrations WHERE key = :key"), {"key": CASE_ACTIONS_DEFAULT_ALL_REVISION},
            )).first())


if __name__ == "__main__":
    unittest.main()
