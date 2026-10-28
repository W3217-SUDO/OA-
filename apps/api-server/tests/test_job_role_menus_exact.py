"""岗位“只按岗位页面授权”（陶威 2026-10-28）。

默认（不打标记）：绑定岗位的人 = 岗位页面 + 已审计确认的系统角色（如普通用户）页面，和原来一样。
打了 config:menus-exact：只用岗位自己的页面。员工管理里按人设置的页面始终优先（冲突时以个人设置为准）。
岗位权限页面保存时不带该开关，标记保持不变；带 menus_exact 才打开或关闭。
"""
import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api_schemas.identity import RolePermissionUpdate
from app.api_schemas.organization import JobRolePermissionUpdate
from app.areas.hr.router import update_job_role_permissions
from app.areas.system.router import update_role_permission
from app.core import soft_delete
from app.core.constants import MENUS_EXACT_MARKER
from app.core.permissions import _user_permission_payload
from app.data_models.identity import JobRole
from app.database import Base
from app.models import User

ADMIN = {"username": "CODEXMEADMIN", "display_name": "管理者", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"]}
ROLE_PAGES = ["user-center", "case-mine-civil"]
USER_ROLE_PAGES = ["user-center", "case-mine-civil", "customer-mine", "task-my-created"]


class JobRoleMenusExactTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        soft_delete.set_actor(ADMIN["username"])
        async with self.sessions() as db:
            db.add_all([
                User(username=ADMIN["username"], display_name="管理者", password_hash="isolated-only", department="CODEXME", role="admin"),
                JobRole(code="CODEX-ME-ROLE", name="隔离岗位", permissions=list(ROLE_PAGES)),
                User(username="CODEXMEBOUND", display_name="绑定人", password_hash="isolated-only", department="CODEXME", role="user",
                     profile={"permission_role_code": "CODEX-ME-ROLE"}),
                User(username="CODEXMEPERSONAL", display_name="个人设置", password_hash="isolated-only", department="CODEXME", role="user",
                     profile={"permission_role_code": "CODEX-ME-ROLE",
                              "permission_overrides": {"menu_keys": ["user-center", "customer-mine", "documents-my"]}}),
            ])
            await db.commit()
            # 普通用户角色经审计修改过：绑定岗位的人会合入这些页面。
            await update_role_permission("user", RolePermissionUpdate(data_scope="本人及共享数据", menu_keys=USER_ROLE_PAGES, field_keys=[]),
                                         identity=ADMIN, db=db)
            self.role_id = (await db.get(JobRole, 1)).id

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def menus(self, username):
        async with self.sessions() as db:
            from sqlalchemy import select
            user = await db.scalar(select(User).where(User.username == username))
            return set((await _user_permission_payload(user, db))["menu_keys"])

    async def set_permissions(self, permissions, **flags):
        async with self.sessions() as db:
            await update_job_role_permissions(self.role_id, JobRolePermissionUpdate(permissions=permissions, **flags), identity=ADMIN, db=db)
            return list((await db.get(JobRole, self.role_id)).permissions)

    async def test_default_merges_system_role_pages(self):
        menus = await self.menus("CODEXMEBOUND")
        self.assertTrue({"customer-mine", "task-my-created", "case-mine-civil"} <= menus)

    async def test_marker_uses_only_role_pages(self):
        stored = await self.set_permissions(ROLE_PAGES, menus_exact=True)
        self.assertIn(MENUS_EXACT_MARKER, stored)
        menus = await self.menus("CODEXMEBOUND")
        self.assertIn("case-mine-civil", menus)
        self.assertFalse({"customer-mine", "task-my-created"} & menus)

    async def test_personal_pages_win_with_and_without_marker(self):
        for flag in (False, True):
            await self.set_permissions(ROLE_PAGES, menus_exact=flag)
            menus = await self.menus("CODEXMEPERSONAL")
            # 个人加的页面显示，岗位有但个人没勾的页面不显示。
            self.assertTrue({"customer-mine", "documents-my"} <= menus, flag)
            self.assertNotIn("case-mine-civil", menus, flag)

    async def test_page_save_keeps_marker_and_flag_turns_it_off(self):
        await self.set_permissions(ROLE_PAGES, menus_exact=True)
        # 岗位权限页面保存（不带开关、也不带标记）不会把标记弄丢。
        self.assertIn(MENUS_EXACT_MARKER, await self.set_permissions([*ROLE_PAGES, "customer-mine"]))
        self.assertNotIn(MENUS_EXACT_MARKER, await self.set_permissions(ROLE_PAGES, menus_exact=False))
        self.assertTrue({"customer-mine", "task-my-created"} <= await self.menus("CODEXMEBOUND"))
