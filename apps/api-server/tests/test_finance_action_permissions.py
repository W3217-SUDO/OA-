"""财务回款/付款/费用的编辑、删除（BUG20261027004，用户 2026-10-28 定）。

只有回款管理、付款打包-管理、请款单审批这类管理页面带出操作，律师能看的回款领取、到账查询、
付款单查询、费用查询等不带（陶威 2026-10-28）；员工管理里可以按人勾选或取消，取消的优先；
范明明这类被授权的人只能给别人配置这 6 项；只认账号真实可见的页面，不认 current_identity 的临时提升。
"""
import unittest

import httpx
from fastapi import FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.agent_permissions import FINANCE_CONFIGURE_ACTION, FINANCE_USER_ACTION_KEYS, USER_ACTION_KEYS
from app.core.constants import FINANCE_EDIT_DELETE_ACTIONS, SYSTEM_ACTION_BY_CODE
from app.core.dependencies import current_identity, get_db
from app.core.finance_action_permissions import (
    configured_action_keys, finance_action_granted, page_granted_finance_actions, require_fee_action,
    require_finance_action, set_user_finance_actions,
)
from app.database import Base
from app.models import BusinessRecord, RolePermission, User

ALL = [code for code, _menu, _label in FINANCE_EDIT_DELETE_ACTIONS]
# 页面可见时 current_identity 会把身份提升成 admin 和 "*"；这里模拟提升后的身份，检查不被它带过。
ELEVATED = {"role": "admin", "role_ids": ["admin", "auditor"], "action_keys": ["*"], "_page_menu_capability": True}


def menus(*keys):
    return {"permission_overrides": {"menu_keys": ["user-center", *keys]}}


class FinanceActionPermissionTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.sessions() as db:
            db.add_all([
                User(username="CODEXFAADMIN", display_name="管理者", password_hash="isolated-only", department="CODEXFA", role="admin"),
                # 回款人员：能打开回款管理；角色里单独勾了付款包编辑。
                User(username="CODEXFAAUDIT", display_name="回款", password_hash="isolated-only", department="CODEXFA", role="auditor"),
                User(username="CODEXFALAWYER", display_name="律师", password_hash="isolated-only", department="CODEXFA", role="user",
                     profile=menus("finance-payment-mine", "finance-invoice-mine", "finance-internal-audit",
                                   "finance-receipts-claim", "finance-receipts-pending", "finance-receipts-allocated",
                                   "finance-receipts-query", "finance-fee-query", "finance-payment-query")),
                User(username="CODEXFAPAY", display_name="付款", password_hash="isolated-only", department="CODEXFA", role="user",
                     profile={"permission_overrides": {"menu_keys": ["user-center", "finance-payment-package-manage", "finance-payment-audit"],
                                                       "action_denies": ["finance.fee.delete"]}}),
                User(username="CODEXFACONF", display_name="范明明", password_hash="isolated-only", department="CODEXFA", role="user",
                     profile={"permission_overrides": {"menu_keys": ["user-center", "hr-all"],
                                                       "action_keys": [FINANCE_CONFIGURE_ACTION, *ALL]}}),
                RolePermission(role="auditor", display_name="回款人员", data_scope="全所数据",
                               # 上线一次性全勾后的状态：角色带回款两项；付款包编辑没有对应管理页面，不生效。
                               menu_keys=["finance-receipts-manage", "@action:finance.receipt.update",
                                          "@action:finance.receipt.delete", "@action:finance.payment.update"], field_keys=[]),
            ])
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    def identity(self, username):
        return {**ELEVATED, "username": username, "_actual_role_ids": ["admin"] if username == "CODEXFAADMIN" else ["user"]}

    async def keys(self, username):
        async with self.sessions() as db:
            # 只比较财务动作；客户等其他模块功能默认全勾（BUG20261028012），不在本测试范围。
            return {key for key in await configured_action_keys(username, db) if not key.startswith(("crm.", "contract.", "ipr.", "task.", "investigation."))}

    def test_catalog(self):
        self.assertEqual(FINANCE_USER_ACTION_KEYS, set(ALL))
        self.assertTrue({FINANCE_CONFIGURE_ACTION, *ALL} <= USER_ACTION_KEYS)
        for code in ALL:
            self.assertIn(code, SYSTEM_ACTION_BY_CODE)
        self.assertEqual(page_granted_finance_actions(["finance-receipts-manage"]), ["finance.receipt.update", "finance.receipt.delete"])
        self.assertEqual(page_granted_finance_actions(["finance-payment-package-manage"]), ["finance.payment.update", "finance.payment.delete"])
        self.assertEqual(page_granted_finance_actions(["finance-payment-audit"]), ["finance.fee.update", "finance.fee.delete"])
        self.assertEqual(page_granted_finance_actions([
            "finance-receipts-icbc", "finance-receipts-claim", "finance-receipts-pending", "finance-receipts-allocated",
            "finance-receipts-query", "finance-payment-query", "finance-payment-writeoff", "finance-fee-query",
            "finance-payment-mine", "finance-invoice-mine", "finance-internal-audit"]), [])

    async def test_visible_page_grants_and_untick_wins(self):
        self.assertEqual(await self.keys("CODEXFAADMIN"), {"*"})
        self.assertEqual(await self.keys("CODEXFAAUDIT"), {"finance.receipt.update", "finance.receipt.delete"})
        self.assertEqual(await self.keys("CODEXFALAWYER"), set())
        # 付款打包-管理+请款单审批带出 4 项，按人取消的“删除费用”不给。
        self.assertEqual(await self.keys("CODEXFAPAY"),
                         {"finance.payment.update", "finance.payment.delete", "finance.fee.update"})
        async with self.sessions() as db:
            self.assertFalse(await finance_action_granted(self.identity("CODEXFAPAY"), db, "finance.fee.delete"))
            with self.assertRaises(HTTPException) as raised:
                await require_finance_action(self.identity("CODEXFALAWYER"), db, "finance.receipt.delete")
            self.assertEqual(raised.exception.status_code, 403)
            self.assertIn("删除回款", raised.exception.detail)

    async def test_role_untick_removes_and_person_tick_wins(self):
        """BUG20261028012：页面默认全有 → 角色取消即没有 → 员工管理按人勾选优先。"""
        async with self.sessions() as db:
            role = await db.scalar(select(RolePermission).where(RolePermission.role == "auditor"))
            role.menu_keys = [key for key in role.menu_keys if key != "@action:finance.receipt.delete"]
            await db.commit()
        self.assertEqual(await self.keys("CODEXFAAUDIT"), {"finance.receipt.update"})
        async with self.sessions() as db:
            auditor = await db.scalar(select(User).where(User.username == "CODEXFAAUDIT"))
            await set_user_finance_actions(auditor.id, ["finance.receipt.update", "finance.receipt.delete"], db, actor="CODEXFACONF", source="test")
            await db.commit()
        self.assertEqual(await self.keys("CODEXFAAUDIT"), {"finance.receipt.update", "finance.receipt.delete"})

    async def test_login_payload_matches(self):
        from app.core.system import _login_response
        async with self.sessions() as db:
            user = await db.scalar(select(User).where(User.username == "CODEXFAPAY"))
            login = await _login_response(user, db)
        self.assertEqual(set(login["user"]["configured_action_keys"]) & set(ALL),
                         {"finance.payment.update", "finance.payment.delete", "finance.fee.update"})

    async def test_set_user_finance_actions_stores_grants_and_denies(self):
        async with self.sessions() as db:
            lawyer = await db.scalar(select(User).where(User.username == "CODEXFALAWYER"))
            await set_user_finance_actions(lawyer.id, ["finance.fee.update"], db, actor="CODEXFACONF", source="test")
            await db.commit()
            payer = await db.scalar(select(User).where(User.username == "CODEXFAPAY"))
            await set_user_finance_actions(payer.id, ["finance.payment.update"], db, actor="CODEXFACONF", source="test")
            await db.commit()
        self.assertEqual(await self.keys("CODEXFALAWYER"), {"finance.fee.update"})
        self.assertEqual(await self.keys("CODEXFAPAY"), {"finance.payment.update"})

    async def test_configure_endpoint_only_for_admin_or_granted(self):
        from app.areas.system import router as system_router
        app = FastAPI()
        app.include_router(system_router.router)
        holder = {}

        async def session():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = session
        app.dependency_overrides[current_identity] = lambda: holder["identity"]
        async with self.sessions() as db:
            lawyer_id = (await db.scalar(select(User).where(User.username == "CODEXFALAWYER"))).id
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://isolated") as client:
            url = "/api/v1/system/finance-actions/CODEXFALAWYER"
            holder["identity"] = {"username": "CODEXFAPAY", "role": "user", "role_ids": ["user"], "_actual_role_ids": ["user"]}
            self.assertEqual((await client.get(url)).status_code, 403)
            self.assertEqual((await client.put(url, json={"action_keys": ALL})).status_code, 403)
            holder["identity"] = {"username": "CODEXFACONF", "role": "user", "role_ids": ["user"], "_actual_role_ids": ["user"]}
            self.assertEqual((await client.get(url)).json()["action_keys"], [])
            saved = await client.put(url, json={"action_keys": ["finance.receipt.update", "finance.receipt.delete"]})
            self.assertEqual(saved.status_code, 200, saved.text)
            self.assertEqual(saved.json()["action_keys"], ["finance.receipt.update", "finance.receipt.delete"])
            self.assertEqual((await client.put(url, json={"action_keys": ["system.users.delete"]})).status_code, 422)
            # 只给了配置财务动作，不能动别人的页面授权。
            self.assertEqual((await client.get(f"/api/v1/system/users/{lawyer_id}/permissions")).status_code, 403)

    async def test_own_unapproved_fee_stays_editable_without_configuration(self):
        own_draft = BusinessRecord(module="finance", serial_no="CODEXFA1", title="草稿", customer="", status="草稿",
                                   owner="CODEXFALAWYER", department="CODEXFA", description="", data={})
        approved = BusinessRecord(module="finance", serial_no="CODEXFA2", title="已审批", customer="", status="已审批",
                                  owner="CODEXFALAWYER", department="CODEXFA", description="", data={})
        async with self.sessions() as db:
            await require_fee_action(own_draft, self.identity("CODEXFALAWYER"), db, "finance.fee.update")
            with self.assertRaises(HTTPException):
                await require_fee_action(approved, self.identity("CODEXFALAWYER"), db, "finance.fee.delete")


class RecordFromAuthorizedPageTest(unittest.TestCase):
    """BUG20261028006：从有权打开的业务页面点开的非案件记录按页面授权读取。"""

    def test_request_page_opens_record(self):
        from app.core.permissions import _request_page_opens_record
        fee = BusinessRecord(module="finance", serial_no="FY1", title="", customer="", status="待审批", owner="x", department="", data={})
        case = BusinessRecord(module="case", serial_no="AJ1", title="", customer="", status="", owner="x", department="", data={})
        auditor = {"_request_page": "finance-payment-audit", "menu_keys": ["finance-payment-audit", "finance-payment-mine", "case-mine"]}
        self.assertTrue(_request_page_opens_record(auditor, fee))
        self.assertFalse(_request_page_opens_record({**auditor, "_request_page": "finance-payment-mine"}, fee))
        self.assertFalse(_request_page_opens_record({**auditor, "_request_page": "finance-settlement-audit"}, fee))
        self.assertFalse(_request_page_opens_record({**auditor, "_request_page": "case-mine"}, fee))
        self.assertFalse(_request_page_opens_record({**auditor, "_request_page": "case-mine"}, case))
        self.assertFalse(_request_page_opens_record({"menu_keys": ["finance-payment-audit"]}, fee))


if __name__ == "__main__":
    unittest.main()
