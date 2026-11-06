"""501684（范文玲 11-06 15:23）：“给别人配置财务操作”在角色权限里也有对应项，可以按角色勾选、关闭。

挂在员工管理（hr-all）下；不做全角色默认勾选，上线时谁都不多出权限；员工管理里按人勾的照常有效。
"""
import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.agent_permissions import FINANCE_CONFIGURE_ACTION
from app.core.constants import FINANCE_EDIT_DELETE_ACTIONS, ROLE_TREE_DERIVED_ACTION_CODES, ROLE_TREE_HIDDEN_ACTION_CODES, SYSTEM_ACTION_BY_CODE
from app.core.finance_action_permissions import can_configure_finance_actions, configured_action_keys
from app.database import Base
from app.models import JobRole, User

ROLE_PAGES = ["hr", "hr-all", "finance-receipts-manage", "action:finance.receipt.update"]


class FinanceConfigureRoleAction501684Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.sessions() as db:
            db.add(JobRole(code="CODEXFIN684", name="财务684", permissions=list(ROLE_PAGES), is_active=True))
            db.add_all([
                User(username="CODEXFIN684A", display_name="跟随角色", password_hash="isolated-only", role="auditor",
                     profile={"permission_role_code": "CODEXFIN684"}),
                User(username="CODEXFIN684B", display_name="按人勾选", password_hash="isolated-only", role="auditor",
                     profile={"permission_role_code": "CODEXFIN684",
                              "permission_overrides": {"action_keys": [FINANCE_CONFIGURE_ACTION]}}),
            ])
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def can_configure(self, username):
        async with self.sessions() as db:
            return await can_configure_finance_actions({"username": username, "role": "auditor", "role_ids": ["auditor"]}, db)

    async def set_role(self, permissions):
        async with self.sessions() as db:
            role = (await db.execute(JobRole.__table__.select().where(JobRole.code == "CODEXFIN684"))).first()
            item = await db.get(JobRole, role.id)
            item.permissions = permissions
            await db.commit()

    def test_role_tree_has_configure_under_employee_management(self):
        definition = SYSTEM_ACTION_BY_CODE[FINANCE_CONFIGURE_ACTION]
        self.assertEqual(definition["menu_key"], "hr-all")
        self.assertEqual(definition["label"], "给别人配置财务操作")
        # 要在角色权限里显示成可勾选的项，而不是给了页面就自动有。
        self.assertNotIn(FINANCE_CONFIGURE_ACTION, ROLE_TREE_HIDDEN_ACTION_CODES | ROLE_TREE_DERIVED_ACTION_CODES)
        # 上线时的全角色默认勾选只有 9 项编辑删除，不含这一项。
        self.assertNotIn(FINANCE_CONFIGURE_ACTION, [code for code, *_ in FINANCE_EDIT_DELETE_ACTIONS])

    async def test_role_page_alone_does_not_grant(self):
        self.assertFalse(await self.can_configure("CODEXFIN684A"))

    async def test_role_tick_grants_and_untick_removes(self):
        await self.set_role([*ROLE_PAGES, f"action:{FINANCE_CONFIGURE_ACTION}"])
        self.assertTrue(await self.can_configure("CODEXFIN684A"))
        await self.set_role(list(ROLE_PAGES))
        self.assertFalse(await self.can_configure("CODEXFIN684A"))

    async def test_person_tick_still_works_without_role(self):
        self.assertTrue(await self.can_configure("CODEXFIN684B"))
        async with self.sessions() as db:
            self.assertIn(FINANCE_CONFIGURE_ACTION, await configured_action_keys("CODEXFIN684B", db))


if __name__ == "__main__":
    unittest.main()
