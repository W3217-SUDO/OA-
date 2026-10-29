"""BUG20261028012（范文玲 2026-10-29 定）：角色权限按页面给。

客户、合同、知识产权、任务、调查以及案件其余功能给了页面就有；案件只设三块开关（右上角“操作”、
律所/平台费用“其他操作”、内部结算）；财务回款/付款包/费用的编辑删除仍单独设。上线时现有人员不少权限。
"""
import unittest

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api_schemas.organization import JobRolePermissionUpdate
from app.areas.finance.fee_action_guards import _require_linked_case_fee_action
from app.areas.hr.router import update_job_role_permissions
from app.core import soft_delete
from app.core.finance_action_permissions import page_granted_finance_actions
from app.core.permissions import _job_role_tree_checked_permissions, _organization_permission_tree, _user_permission_payload
from app.data_models.identity import JobRole
from app.database import Base
from app.models import BusinessRecord, SystemMenu, User

ADMIN = {"username": "CODEXBLKADMIN", "display_name": "管理者", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"]}
PAGES = ["user-center", "case-mine-civil", "customer-mine"]


class RolePermissionBlocksTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        soft_delete.set_actor(ADMIN["username"])
        async with self.sessions() as db:
            db.add_all([
                User(username=ADMIN["username"], display_name="管理者", password_hash="isolated-only", department="CODEXBLK", role="admin"),
                # 新方式保存的岗位：只勾了“操作”这一块。
                JobRole(code="CODEX-BLK-OPS", name="只勾操作", permissions=[*PAGES, "action:case.block.operations"]),
                # 上线前的旧岗位：存的是单个功能（律所费用修改），没有开关。
                JobRole(code="CODEX-BLK-LEGACY", name="旧岗位", permissions=[*PAGES, "action:case.fee.update", "action:case.delete"]),
                User(username="CODEXBLKOPS", display_name="操作", password_hash="isolated-only", department="CODEXBLK", role="user",
                     profile={"permission_role_code": "CODEX-BLK-OPS"}),
                User(username="CODEXBLKLEGACY", display_name="旧", password_hash="isolated-only", department="CODEXBLK", role="user",
                     profile={"permission_role_code": "CODEX-BLK-LEGACY"}),
                BusinessRecord(id=900, module="case", serial_no="CODEX-BLK-CASE", title="案件", owner="CODEXBLKOPS", status="在办", data={}),
            ])
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def actions(self, username):
        async with self.sessions() as db:
            user = await db.scalar(select(User).where(User.username == username))
            return set((await _user_permission_payload(user, db))["action_keys"])

    async def test_block_and_page_grants(self):
        actions = await self.actions("CODEXBLKOPS")
        # “操作”块内功能全有；案件其余功能、客户功能跟页面带出。
        self.assertTrue({"case.court.update", "case.merge", "case.archive.submit"} <= actions)
        self.assertTrue({"case.document.delete", "case.delete", "case.fee.create", "crm.customer.recycle"} <= actions)
        # 没勾的两块没有；没给页面的模块不带出。
        self.assertFalse({"case.fee.update", "case.fee.refund", "case.internal_fee.delete"} & actions)
        self.assertFalse({"contract.delete", "ipr.case.update", "task.create"} & actions)

    async def test_legacy_role_keeps_everything_until_saved(self):
        actions = await self.actions("CODEXBLKLEGACY")
        # 旧岗位有律所费用修改：带出整个“其他操作”块，内部结算原来共用也带上；原有删除案件不少。
        self.assertTrue({"case.fee.update", "case.fee.refund", "case.internal_fee.update", "case.internal_fee.create", "case.delete"} <= actions)
        async with self.sessions() as db:
            role = await db.scalar(select(JobRole).where(JobRole.code == "CODEX-BLK-LEGACY"))
            checked = set(_job_role_tree_checked_permissions(role))
        self.assertTrue({"action:case.block.fee_other", "action:case.block.internal_fee"} <= checked)
        self.assertNotIn("action:case.block.operations", checked)

    async def test_save_stores_only_switches(self):
        async with self.sessions() as db:
            role = await db.scalar(select(JobRole).where(JobRole.code == "CODEX-BLK-LEGACY"))
            # 管理员在角色权限里只留“其他操作”，取消内部结算。
            await update_job_role_permissions(role.id, JobRolePermissionUpdate(
                permissions=[*PAGES, "action:case.block.fee_other"], case_actions_explicit=True), identity=ADMIN, db=db)
            stored = set((await db.get(JobRole, role.id)).permissions)
        self.assertIn("action:case.block.fee_other", stored)
        self.assertFalse({"action:case.fee.update", "action:case.delete"} & stored)
        actions = await self.actions("CODEXBLKLEGACY")
        self.assertIn("case.fee.refund", actions)
        self.assertFalse({"case.internal_fee.create", "case.internal_fee.update"} & actions)
        self.assertIn("case.delete", actions)  # 跟页面带出

    async def test_internal_fee_uses_its_own_switch(self):
        identity = {"username": "CODEXBLKOPS", "role": "user", "role_ids": ["user"], "department": "CODEXBLK"}
        internal = BusinessRecord(module="finance", serial_no="F1", title="内部", owner="CODEXBLKOPS", status="草稿",
                                  data={"case_id": 900, "expense_scope": "内部"})
        firm = BusinessRecord(module="finance", serial_no="F2", title="律所", owner="CODEXBLKOPS", status="草稿",
                              data={"case_id": 900, "expense_scope": "律所"})
        async with self.sessions() as db:
            role = await db.scalar(select(JobRole).where(JobRole.code == "CODEX-BLK-OPS"))
            role.permissions = [*PAGES, "action:case.block.internal_fee"]
            await db.commit()
            await _require_linked_case_fee_action(internal, "case.fee.delete", identity, db)
            with self.assertRaises(HTTPException):
                await _require_linked_case_fee_action(firm, "case.fee.delete", identity, db)

    def test_role_tree_shows_only_switches(self):
        menus = [SystemMenu(id=1, key="case-mine", label="我的案件", parent_key=""),
                 SystemMenu(id=2, key="customer-mine", label="我的客户", parent_key=""),
                 SystemMenu(id=3, key="finance-receipts-manage", label="回款管理", parent_key="")]
        tree = _organization_permission_tree(menus, [], set())
        codes = {node["key"]: {child["node_code"] for child in node["children"]} for node in tree}
        self.assertEqual(codes["menu:case-mine"], {"case.block.operations", "case.block.fee_other", "case.block.internal_fee"})
        self.assertEqual(codes["menu:customer-mine"], set())
        self.assertEqual(codes["menu:finance-receipts-manage"], {"finance.receipt.update", "finance.receipt.delete"})

    def test_platform_receipt_manage_page_carries_receipt_switches(self):
        self.assertEqual(set(page_granted_finance_actions(["platform-finance-overview-manage"])),
                         {"finance.receipt.update", "finance.receipt.delete"})
        self.assertEqual(page_granted_finance_actions(["platform-finance-overview-claim", "finance-receipts-pending"]), [])


if __name__ == "__main__":
    unittest.main()
