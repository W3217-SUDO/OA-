import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.dingtalk import dingtalk_client
from app.main import _dispatch_dingtalk_notifications, app
from app.models import Notification, RolePermission, SecurityPolicy, SystemMenu, User
from app.security import hash_password


class DingTalkIntegrationContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda sync_connection: Base.metadata.create_all(sync_connection, tables=[User.__table__, SecurityPolicy.__table__, RolePermission.__table__, SystemMenu.__table__, Notification.__table__]))
        async with self.sessions() as db:
            db.add(SecurityPolicy(id=1, token_minutes=720, updated_by="test"))
            db.add(RolePermission(role="user", display_name="普通用户", data_scope="本人及共享数据", menu_keys=[], field_keys=[]))
            db.add(User(username="staff", display_name="测试员工", department="调查部", role="user", role_ids=["user"], password_hash=hash_password("StaffPass2026!"), profile={"mobile": "13800000000"}, is_active=True))
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://dingtalk.test")
        self.old_config = (settings.dingtalk_corp_id, settings.dingtalk_agent_id, settings.dingtalk_app_key, settings.dingtalk_app_secret, settings.dingtalk_app_url)
        settings.dingtalk_corp_id = "ding-corp"
        settings.dingtalk_agent_id = "123"
        settings.dingtalk_app_key = "app-key"
        settings.dingtalk_app_secret = "app-secret"
        settings.dingtalk_app_url = "https://oa.example.com/"
        self.old_user_lookup = dingtalk_client.user_by_auth_code
        self.old_sender = dingtalk_client.send_work_notification

        async def fake_user_lookup(_code: str):
            return {"user_id": "ding-user-1", "name": "测试员工", "mobile": "13800000000"}

        dingtalk_client.user_by_auth_code = fake_user_lookup

    async def asyncTearDown(self):
        dingtalk_client.user_by_auth_code = self.old_user_lookup
        dingtalk_client.send_work_notification = self.old_sender
        (settings.dingtalk_corp_id, settings.dingtalk_agent_id, settings.dingtalk_app_key, settings.dingtalk_app_secret, settings.dingtalk_app_url) = self.old_config
        app.dependency_overrides.clear()
        await self.client.aclose()
        await self.engine.dispose()

    async def test_first_login_binds_existing_oa_account_then_allows_sso(self):
        response = await self.client.post("/api/v1/auth/dingtalk/bind", json={"auth_code": "one-time-code", "username": "staff", "password": "StaffPass2026!"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["user"]["display_name"], "测试员工")
        async with self.sessions() as db:
            user = await db.scalar(select(User).where(User.username == "staff"))
            self.assertEqual(user.profile["dingtalk_user_id"], "ding-user-1")
        sso = await self.client.post("/api/v1/auth/dingtalk/login", json={"auth_code": "next-code"})
        self.assertEqual(sso.status_code, 200, sso.text)

    async def test_pending_notification_is_sent_to_bound_dingtalk_user(self):
        sent = []

        async def fake_sender(user_id: str, title: str, content: str):
            sent.append((user_id, title, content))
            return "task-1"

        dingtalk_client.send_work_notification = fake_sender
        async with self.sessions() as db:
            user = await db.scalar(select(User).where(User.username == "staff"))
            user.profile = {**user.profile, "dingtalk_user_id": "ding-user-1"}
            db.add(Notification(source_key="test-ding-notice", source_type="task", recipient="staff", title="任务通知", content="有一条新任务"))
            await db.commit()
        original_session_local = __import__("app.main", fromlist=["SessionLocal"]).SessionLocal
        main_module = __import__("app.main", fromlist=["SessionLocal"])
        main_module.SessionLocal = self.sessions
        try:
            await _dispatch_dingtalk_notifications()
        finally:
            main_module.SessionLocal = original_session_local
        self.assertEqual(sent, [("ding-user-1", "任务通知", "有一条新任务")])
        async with self.sessions() as db:
            notice = await db.scalar(select(Notification).where(Notification.source_key == "test-ding-notice"))
            self.assertEqual(notice.dingtalk_status, "sent")


if __name__ == "__main__":
    unittest.main()
