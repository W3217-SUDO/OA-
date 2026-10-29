"""BUG20261028012（范文玲 2026-10-29 定）：角色权限按页面给。

客户、合同、知识产权、任务、调查以及案件其余功能给了页面就有；案件分三块显示（右上角“操作”、
律所/平台费用“其他操作”、内部结算），块下每个功能单独勾选、区块可全选；财务回款/付款包/费用的编辑删除仍单独设。
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
                # 只勾了“操作”里的修改法院信息、案件合并。
                JobRole(code="CODEX-BLK-OPS", name="单个功能", permissions=[*PAGES, "action:case.court.update", "action:case.merge"]),
                # 1.2.34 按整块存的开关。
                JobRole(code="CODEX-BLK-LEGACY", name="整块", permissions=[*PAGES, "action:case.block.fee_other", "action:case.delete"]),
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

    async def test_single_functions_and_page_grants(self):
        actions = await self.actions("CODEXBLKOPS")
        # 只有勾了的单个功能；案件其余功能、客户功能跟页面带出。
        self.assertTrue({"case.court.update", "case.merge"} <= actions)
        self.assertFalse({"case.detail.update", "case.archive.submit", "case.fee.update", "case.internal_fee.delete"} & actions)
        self.assertTrue({"case.document.delete", "case.delete", "case.fee.create", "crm.customer.note.manage"} <= actions)
        # 客户“更多操作”按页面勾选，没勾就没有。
        self.assertNotIn("crm.customer.recycle", actions)
        self.assertFalse({"contract.delete", "ipr.case.update", "task.create"} & actions)

    async def test_block_saved_by_previous_version_still_counts(self):
        actions = await self.actions("CODEXBLKLEGACY")
        self.assertTrue({"case.fee.update", "case.fee.refund", "case.fee.mark_unpaid", "case.delete"} <= actions)
        self.assertNotIn("case.internal_fee.update", actions)

    async def test_save_stores_single_functions(self):
        async with self.sessions() as db:
            role = await db.scalar(select(JobRole).where(JobRole.code == "CODEX-BLK-LEGACY"))
            await update_job_role_permissions(role.id, JobRolePermissionUpdate(
                permissions=[*PAGES, "action:case.fee.refund", "action:case.internal_fee.create", "action:case.delete"],
                case_actions_explicit=True), identity=ADMIN, db=db)
            stored = set((await db.get(JobRole, role.id)).permissions)
        self.assertTrue({"action:case.fee.refund", "action:case.internal_fee.create"} <= stored)
        # 跟页面带出的功能、旧整块开关都不再存。
        self.assertFalse({"action:case.delete", "action:case.block.fee_other"} & stored)
        actions = await self.actions("CODEXBLKLEGACY")
        self.assertIn("case.fee.refund", actions)
        self.assertFalse({"case.fee.update", "case.internal_fee.update"} & actions)
        self.assertIn("case.delete", actions)

    async def test_internal_fee_uses_its_own_switch(self):
        identity = {"username": "CODEXBLKOPS", "role": "user", "role_ids": ["user"], "department": "CODEXBLK"}
        internal = BusinessRecord(module="finance", serial_no="F1", title="内部", owner="CODEXBLKOPS", status="草稿",
                                  data={"case_id": 900, "expense_scope": "内部"})
        firm = BusinessRecord(module="finance", serial_no="F2", title="律所", owner="CODEXBLKOPS", status="草稿",
                              data={"case_id": 900, "expense_scope": "律所"})
        async with self.sessions() as db:
            role = await db.scalar(select(JobRole).where(JobRole.code == "CODEX-BLK-OPS"))
            role.permissions = [*PAGES, "action:case.internal_fee.delete"]
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
        self.assertEqual(codes["menu:case-mine"], {"group:case-operations", "group:case-fee-other", "group:case-internal-fee"})
        groups = {group["key"]: [child["node_code"] for child in group["children"]] for group in tree[0]["children"]}
        self.assertEqual(groups["group:case-internal-fee"], ["case.internal_fee.create", "case.internal_fee.payment",
                                                             "case.internal_fee.update", "case.internal_fee.delete"])
        self.assertIn("case.court.update", groups["group:case-operations"])
        self.assertNotIn("case.criminal.court.update", groups["group:case-operations"])
        self.assertEqual(codes["menu:customer-mine"], {f"{code}@customer-mine" for code in (
            "crm.customer.update", "crm.customer.recycle", "crm.customer.assign", "crm.customer.release", "crm.customer.share")})
        self.assertEqual(codes["menu:finance-receipts-manage"], {"finance.receipt.update", "finance.receipt.delete"})

    def test_platform_receipt_manage_page_carries_receipt_switches(self):
        self.assertEqual(set(page_granted_finance_actions(["platform-finance-overview-manage"])),
                         {"finance.receipt.update", "finance.receipt.delete"})
        self.assertEqual(page_granted_finance_actions(["platform-finance-overview-claim", "finance-receipts-pending"]),
                         ["finance.receipt.claim.delete", "finance.receipt.pending.delete"])
        self.assertEqual(page_granted_finance_actions(["finance-receipts-query"]), [])

    def test_customer_functions_per_page(self):
        from app.core.constants import expand_role_action_codes
        # 旧授权只有基础码：各客户页面都有。
        legacy = set(expand_role_action_codes(["crm.customer.recycle"], []))
        self.assertTrue({"crm.customer.recycle@customer-mine", "crm.customer.recycle@customer-dept", "crm.customer.recycle@customer-company"} <= legacy)
        # 按页面勾选后：只有勾了的页面，后台按任一页面有即允许基础码。
        scoped = set(expand_role_action_codes(["crm.customer.recycle@customer-dept"], []))
        self.assertIn("crm.customer.recycle", scoped)
        self.assertNotIn("crm.customer.recycle@customer-mine", scoped)

    async def test_receipt_delete_by_page_status(self):
        from app.core.finance_action_permissions import require_receipt_delete
        async with self.sessions() as db:
            user = await db.scalar(select(User).where(User.username == "CODEXBLKOPS"))
            user.profile = {**user.profile, "permission_overrides": {"menu_keys": ["user-center", "finance-receipts-claim"],
                                                                     "action_keys": ["finance.receipt.claim.delete"]}}
            await db.commit()
            identity = {"username": "CODEXBLKOPS", "role": "manager", "role_ids": ["manager"]}
            await require_receipt_delete(identity, db, "待认领")
            with self.assertRaises(HTTPException):
                await require_receipt_delete(identity, db, "待分配")

    def test_tree_matches_page_buttons(self):
        # 范文玲 2026-10-29 13:19：每个页面下只挂该页实际有的按钮。
        menus = [SystemMenu(id=1, key="finance-payment-audit", label="请款单审批", parent_key=""),
                 SystemMenu(id=2, key="finance-jar", label="JAR交案费管理", parent_key=""),
                 SystemMenu(id=3, key="finance-internal-audit", label="内部提成-待审核", parent_key=""),
                 SystemMenu(id=4, key="finance-internal-fee-audit", label="内部费用-待审核", parent_key=""),
                 SystemMenu(id=5, key="system-parameters-court", label="法院设置", parent_key=""),
                 SystemMenu(id=6, key="customer-mine", label="我的客户", parent_key="")]
        tree = _organization_permission_tree(menus, ["客户修改", "费用申请", "合同付款申请"], {"action:finance.internal.review.approve"})
        nodes = {node["key"]: node["children"] for node in tree}
        # 请款单审批只有“审批”（同意/拒绝），没有编辑、删除费用。
        self.assertEqual([c["title"] for c in nodes["menu:finance-payment-audit"]], ["审批（同意）", "审批（拒绝）"])
        # 左侧菜单不显示的页面不在角色权限里。
        self.assertNotIn("menu:finance-jar", nodes)
        self.assertEqual(nodes["menu:system-parameters-court"], [])
        # 旧系统岗位名称不当功能显示。
        titles = {c["title"] for children in nodes.values() for c in children} | {node["title"] for node in tree}
        self.assertFalse({"客户修改", "费用申请", "合同付款申请"} & titles)
        # 内部费用审批在两个待审核页面下都显示，同一开关。
        fee_audit = {c["key"]: c["state"]["checked"] for c in nodes["menu:finance-internal-fee-audit"]}
        self.assertEqual(fee_audit, {"action:finance.internal.review.approve#finance-internal-fee-audit": True,
                                     "action:finance.internal.review.reject#finance-internal-fee-audit": False})

    async def test_legacy_label_shown_as_pages_and_kept_on_save(self):
        async with self.sessions() as db:
            role = JobRole(code="CODEX-BLK-LABEL", name="旧岗位", permissions=["user-center", "员工修改", "合同付款申请"])
            db.add(role)
            await db.commit()
            checked = set(_job_role_tree_checked_permissions(role))
            self.assertIn("hr-all", checked)
            self.assertNotIn("员工修改", checked)
            # 页面仍勾着：保留原名称（连同员工修改动作）。
            await update_job_role_permissions(role.id, JobRolePermissionUpdate(permissions=["user-center", "hr-all"]), identity=ADMIN, db=db)
            self.assertEqual(set((await db.get(JobRole, role.id)).permissions), {"user-center", "hr-all", "员工修改", "合同付款申请"})
            # 左侧菜单不显示的页面原有授权保存时保留。
            role.permissions = [*role.permissions, "finance-jar"]
            await db.commit()
            await update_job_role_permissions(role.id, JobRolePermissionUpdate(permissions=["user-center", "hr-all"]), identity=ADMIN, db=db)
            self.assertIn("finance-jar", (await db.get(JobRole, role.id)).permissions)
            # 取消了它开的页面：名称一并去掉。
            await update_job_role_permissions(role.id, JobRolePermissionUpdate(permissions=["user-center"]), identity=ADMIN, db=db)
            self.assertEqual(set((await db.get(JobRole, role.id)).permissions), {"user-center", "合同付款申请", "finance-jar"})


if __name__ == "__main__":
    unittest.main()
