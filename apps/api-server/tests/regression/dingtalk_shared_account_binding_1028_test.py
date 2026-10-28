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

from app.areas.system.dingtalk_auth import bind_verified_employee, login_verified_employee
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


if __name__ == "__main__":
    unittest.main()
