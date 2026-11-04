"""BUG20261104006（501310，范雨星 11-04）：角色权限里勾了大类（如“客户管理”），再取消下面某个页面，保存后取消不生效。

原因：大类的 key 照样保存，而已存的大类按兼容规则放开下面全部页面。修复后大类只有在下面能勾的页面全部勾上时才保存；
取消任何一个页面，大类就不存，只按勾上的页面授权。人人都有的公共页面（用户中心下的）和树里不显示的页面不影响判断。
"""
import unittest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api_schemas.organization import JobRolePermissionUpdate
from app.areas.hr.router import update_job_role_permissions
from app.core import soft_delete
from app.core.constants import MENU_CHILDREN_BY_KEY
from app.core.permissions import _drop_partial_parent_menu_keys, _user_permission_payload
from app.data_models.identity import JobRole
from app.database import Base
from app.models import User

ADMIN = {"username": "CODEX501310ADMIN", "display_name": "管理者", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"]}
CUSTOMER_PAGES = list(MENU_CHILDREN_BY_KEY["customer"])


class RoleParentMenuTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        soft_delete.set_actor(ADMIN["username"])
        async with self.sessions() as db:
            db.add_all([
                User(username=ADMIN["username"], display_name="管理者", password_hash="isolated-only", department="CODEX", role="admin"),
                JobRole(code="CODEX-501310", name="隔离律师助理", permissions=["user-center", "customer-mine"]),
                User(username="CODEX501310USER", display_name="助理", password_hash="isolated-only", department="CODEX", role="user",
                     profile={"permission_role_code": "CODEX-501310"}),
            ])
            await db.commit()
            self.role_id = (await db.scalar(select(JobRole).where(JobRole.code == "CODEX-501310"))).id

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def save(self, permissions):
        async with self.sessions() as db:
            await update_job_role_permissions(self.role_id, JobRolePermissionUpdate(permissions=permissions), identity=ADMIN, db=db)
            stored = list((await db.get(JobRole, self.role_id)).permissions)
            user = await db.scalar(select(User).where(User.username == "CODEX501310USER"))
            return stored, set((await _user_permission_payload(user, db))["menu_keys"])

    async def test_unchecked_child_takes_effect_when_parent_was_ticked(self):
        # 先点大类（树把大类和下面全部页面一起勾上），再取消“公海客户”和“公司客户”。
        partial = ["user-center", "customer", *[key for key in CUSTOMER_PAGES if key not in {"customer-public", "customer-company"}]]
        stored, menus = await self.save(partial)
        self.assertNotIn("customer", stored, "有页面没勾，大类不保存")
        self.assertNotIn("customer-public", menus)
        self.assertNotIn("customer-company", menus)
        self.assertIn("customer-mine", menus)
        self.assertIn("user-center", stored, "用户中心下面是公共页面，照样保留")

    async def test_parent_kept_when_all_pages_ticked(self):
        stored, menus = await self.save(["user-center", "customer", *CUSTOMER_PAGES])
        self.assertIn("customer", stored)
        self.assertTrue(set(CUSTOMER_PAGES) <= menus)

    def test_nested_parent_needs_every_leaf(self):
        seal_my = list(MENU_CHILDREN_BY_KEY["seal-my"])
        kept = _drop_partial_parent_menu_keys(["seal", "seal-my", *seal_my])
        self.assertEqual(kept, ["seal-my", *seal_my], "用印中心下还有审核、管理没勾：大类“用印中心”不存，“我的用印”全勾保留")
        self.assertEqual(_drop_partial_parent_menu_keys(["action:case.duplicate", "case-mine-civil"]), ["action:case.duplicate", "case-mine-civil"])


if __name__ == "__main__":
    unittest.main()
