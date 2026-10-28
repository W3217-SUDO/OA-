"""问题反馈 BUG20261027004：财务回款/付款/费用的编辑、删除只认角色配置或员工管理里按人勾选的动作，不随页面可见全开。"""
import unittest

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.constants import SYSTEM_ACTION_BY_CODE
from app.core.finance_action_permissions import (
    configured_action_keys, finance_action_granted, require_fee_action, require_finance_action,
)
from app.database import Base
from sqlalchemy import select

from app.core.constants import FINANCE_EDIT_DELETE_ACTIONS as FINANCE_EDIT_DELETE_ACTIONS_ALL
from app.models import BusinessRecord, RolePermission, User

# 页面可见时 current_identity 会把身份提升成 admin 和 "*"；这里模拟提升后的身份，检查不被它带过。
ELEVATED = {"role": "admin", "role_ids": ["admin", "auditor"], "action_keys": ["*"], "_page_menu_capability": True}


class FinanceActionPermissionTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.sessions() as db:
            db.add_all([
                User(username="CODEXFAADMIN", display_name="管理者", password_hash="isolated-only", department="CODEXFA", role="admin"),
                User(username="CODEXFAAUDIT", display_name="审核", password_hash="isolated-only", department="CODEXFA", role="auditor"),
                User(username="CODEXFAUSER", display_name="员工", password_hash="isolated-only", department="CODEXFA", role="user"),
                # 员工管理里按人勾选（2026-10-28）：存在 permission_overrides.action_keys。
                User(username="CODEXFAPERSON", display_name="按人授权", password_hash="isolated-only", department="CODEXFA", role="user",
                     profile={"permission_overrides": {"action_keys": ["finance.payment.delete", "finance.fee.update"]}}),
                RolePermission(role="auditor", display_name="审批人员", data_scope="全所数据",
                               menu_keys=["finance", "finance-receipts-manage", "@action:finance.receipt.update"], field_keys=[]),
            ])
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    def identity(self, username):
        return {**ELEVATED, "username": username}

    async def test_actions_are_listed_in_role_configuration(self):
        for code in ("finance.receipt.update", "finance.receipt.delete", "finance.payment.update",
                     "finance.payment.delete", "finance.fee.update", "finance.fee.delete"):
            self.assertIn(code, SYSTEM_ACTION_BY_CODE)

    async def test_real_admin_keeps_everything_and_others_only_configured(self):
        async with self.sessions() as db:
            self.assertEqual(await configured_action_keys("CODEXFAADMIN", db), ["*"])
            self.assertTrue(await finance_action_granted(self.identity("CODEXFAADMIN"), db, "finance.receipt.delete"))
            self.assertTrue(await finance_action_granted(self.identity("CODEXFAAUDIT"), db, "finance.receipt.update"))
            self.assertFalse(await finance_action_granted(self.identity("CODEXFAAUDIT"), db, "finance.receipt.delete"))
            self.assertFalse(await finance_action_granted(self.identity("CODEXFAUSER"), db, "finance.fee.update"))
            with self.assertRaises(HTTPException) as raised:
                await require_finance_action(self.identity("CODEXFAAUDIT"), db, "finance.receipt.delete")
            self.assertEqual(raised.exception.status_code, 403)
            self.assertIn("删除回款", raised.exception.detail)

    async def test_own_unapproved_fee_stays_editable_without_configuration(self):
        own_draft = BusinessRecord(module="finance", serial_no="CODEXFA1", title="草稿", customer="", status="草稿",
                                   owner="CODEXFAUSER", department="CODEXFA", description="", data={})
        approved = BusinessRecord(module="finance", serial_no="CODEXFA2", title="已审批", customer="", status="已审批",
                                  owner="CODEXFAUSER", department="CODEXFA", description="", data={})
        others = BusinessRecord(module="finance", serial_no="CODEXFA3", title="他人草稿", customer="", status="草稿",
                                owner="CODEXFAADMIN", department="CODEXFA", description="", data={})
        async with self.sessions() as db:
            await require_fee_action(own_draft, self.identity("CODEXFAUSER"), db, "finance.fee.update")
            for item in (approved, others):
                with self.assertRaises(HTTPException):
                    await require_fee_action(item, self.identity("CODEXFAUSER"), db, "finance.fee.delete")


    async def test_per_user_grant_from_employee_page(self):
        from app.agent_permissions import FINANCE_USER_ACTION_KEYS, USER_ACTION_KEYS
        from app.core.constants import FINANCE_EDIT_DELETE_ACTIONS
        from app.core.system import _login_response
        self.assertEqual(FINANCE_USER_ACTION_KEYS, {code for code, _menu, _label in FINANCE_EDIT_DELETE_ACTIONS})
        self.assertTrue(FINANCE_USER_ACTION_KEYS <= USER_ACTION_KEYS)
        async with self.sessions() as db:
            keys = await configured_action_keys("CODEXFAPERSON", db)
            self.assertTrue({"finance.payment.delete", "finance.fee.update"} <= set(keys))
            self.assertTrue(await finance_action_granted(self.identity("CODEXFAPERSON"), db, "finance.payment.delete"))
            self.assertFalse(await finance_action_granted(self.identity("CODEXFAPERSON"), db, "finance.receipt.delete"))
            user = await db.scalar(select(User).where(User.username == "CODEXFAPERSON"))
            login = await _login_response(user, db)
            self.assertIn("finance.payment.delete", login["user"]["configured_action_keys"])

    async def test_employee_page_saves_finance_actions(self):
        from app.api_schemas.identity import UserPermissionOverrideUpdate
        from app.core.user_permission_overrides import update_user_permission_overrides
        async with self.sessions() as db:
            user = await db.scalar(select(User).where(User.username == "CODEXFAUSER"))
            codes = sorted(code for code, _menu, _label in FINANCE_EDIT_DELETE_ACTIONS_ALL)
            await update_user_permission_overrides(user.id, UserPermissionOverrideUpdate(action_keys=codes), db,
                                                   actor="CODEXFAADMIN", authorization_source="test")
            await db.commit()
        async with self.sessions() as db:
            self.assertTrue(set(codes) <= set(await configured_action_keys("CODEXFAUSER", db)))


if __name__ == "__main__":
    unittest.main()
