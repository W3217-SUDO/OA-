"""1028 陶威反馈：钉钉工作台反复要求绑定。

陶威和陶国南共用 admin 账号，原来一个账号只存一个钉钉身份，谁绑定就顶掉另一个人，两人轮流被要求重新绑定。
现在共用账号可绑定多个钉钉身份免登，主身份（接收通知）不被后绑定的人顶掉。
"""

from __future__ import annotations

import unittest

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.system.dingtalk_auth import bind_verified_employee, dingtalk_bindings, login_verified_employee, remove_dingtalk_binding
from app.core.permissions import _profile_dingtalk_login_ids
from app.database import Base
from app.models import User
from app.security import hash_password


class DingTalkSharedAccountBindingTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username="admin", display_name="管理者", password_hash=hash_password("Secret-1028"), role="admin", role_ids=["admin"],
                     profile={"dingtalk_user_id": "ding-tgn"}, is_active=True),
                User(username="other", display_name="其他员工", password_hash=hash_password("Secret-1028"), role="user", role_ids=["user"],
                     profile={"dingtalk_user_id": "ding-other"}, is_active=True),
            ])
            await db.commit()

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_second_person_binding_keeps_first_binding(self) -> None:
        async with self.sessions() as db:
            await bind_verified_employee({"user_id": "ding-taowei"}, "admin", "Secret-1028", db)
        async with self.sessions() as db:
            admin = await db.scalar(select(User).where(User.username == "admin"))
            self.assertEqual(admin.profile["dingtalk_user_id"], "ding-tgn", "通知主身份不被顶掉")
            self.assertEqual(_profile_dingtalk_login_ids(admin.profile), ["ding-tgn", "ding-taowei"])
            for ding_user_id in ("ding-tgn", "ding-taowei"):
                data = await login_verified_employee({"user_id": ding_user_id}, db)
                self.assertIsNotNone(data, f"{ding_user_id} 从工作台打开应直接登录")
                self.assertEqual(data["user"]["username"], "admin")
            # 重复绑定不产生重复记录。
            await bind_verified_employee({"user_id": "ding-taowei"}, "admin", "Secret-1028", db)
            admin = await db.scalar(select(User).where(User.username == "admin"))
            self.assertEqual(admin.profile["dingtalk_login_ids"], ["ding-taowei"])

    async def test_dingtalk_identity_bound_elsewhere_is_rejected(self) -> None:
        async with self.sessions() as db:
            with self.assertRaises(HTTPException) as caught:
                await bind_verified_employee({"user_id": "ding-other"}, "admin", "Secret-1028", db)
            self.assertEqual(caught.exception.status_code, 409)
            await bind_verified_employee({"user_id": "ding-taowei"}, "admin", "Secret-1028", db)
            with self.assertRaises(HTTPException) as caught:
                await bind_verified_employee({"user_id": "ding-taowei"}, "other", "Secret-1028", db)
            self.assertEqual(caught.exception.status_code, 409, "附加绑定的身份同样不能再绑到别的账号")

    async def test_remove_single_binding_promotes_next_and_keeps_record(self) -> None:
        """1029：个人设置/员工账号里逐个解绑；主身份被解绑时由下一个接替，解绑记录保留。"""
        async with self.sessions() as db:
            await bind_verified_employee({"user_id": "ding-taowei", "name": "陶威"}, "admin", "Secret-1028", db)
            admin = await db.scalar(select(User).where(User.username == "admin"))
            self.assertEqual([item["name"] for item in await dingtalk_bindings(admin)], ["", "陶威"])
            remove_dingtalk_binding(admin, "ding-tgn", "admin")
            await db.commit()
            self.assertEqual(admin.profile["dingtalk_user_id"], "ding-taowei")
            self.assertNotIn("dingtalk_login_ids", admin.profile)
            self.assertEqual(admin.profile["dingtalk_unbound"][0]["user_id"], "ding-tgn")
            self.assertIsNone(await login_verified_employee({"user_id": "ding-tgn"}, db), "解绑后再从钉钉打开需要重新绑定")
            self.assertIsNotNone(await login_verified_employee({"user_id": "ding-taowei"}, db))
            remove_dingtalk_binding(admin, "ding-taowei", "admin")
            self.assertNotIn("dingtalk_user_id", admin.profile)
            with self.assertRaises(HTTPException) as caught:
                remove_dingtalk_binding(admin, "ding-taowei", "admin")
            self.assertEqual(caught.exception.status_code, 404)

    async def test_self_unbind_outside_dingtalk_only_when_single_binding(self) -> None:
        from app.api_schemas.identity import DingTalkSelfUnbindInput
        from app.areas.system.router import unbind_own_dingtalk

        async with self.sessions() as db:
            await bind_verified_employee({"user_id": "ding-taowei"}, "admin", "Secret-1028", db)
            with self.assertRaises(HTTPException) as caught:
                await unbind_own_dingtalk(DingTalkSelfUnbindInput(), {"username": "admin"}, db)
            self.assertEqual(caught.exception.status_code, 409, "共用账号在电脑上不能一键解绑，免得顶掉别人")
            result = await unbind_own_dingtalk(DingTalkSelfUnbindInput(), {"username": "other"}, db)
            self.assertEqual(result, {"dingtalk_binding_count": 0})

    async def test_self_unbind_in_dingtalk_removes_only_current_identity(self) -> None:
        from unittest.mock import AsyncMock, PropertyMock, patch
        from app.api_schemas.identity import DingTalkSelfUnbindInput
        from app.areas.system import router as system_router

        async with self.sessions() as db:
            await bind_verified_employee({"user_id": "ding-taowei"}, "admin", "Secret-1028", db)
            client = system_router.dingtalk_client
            with patch.object(type(client), "configured", new_callable=PropertyMock, return_value=True), \
                    patch.object(client, "user_by_auth_code", AsyncMock(return_value={"user_id": "ding-taowei"})):
                result = await system_router.unbind_own_dingtalk(DingTalkSelfUnbindInput(auth_code="code"), {"username": "admin"}, db)
            self.assertEqual(result, {"dingtalk_binding_count": 1})
            admin = await db.scalar(select(User).where(User.username == "admin"))
            self.assertEqual(_profile_dingtalk_login_ids(admin.profile), ["ding-tgn"], "共用账号另一人的绑定不受影响")


if __name__ == "__main__":
    unittest.main()
