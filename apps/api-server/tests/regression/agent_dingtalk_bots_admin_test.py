"""智能体中心 › 钉钉机器人中心：只有系统管理员能改，AppSecret 加密保存不回显，测试连接不外传钉钉返回内容。"""
import json
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.agent_admin.dingtalk_bots import probe
from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import SystemConfig
from app.security import current_identity

API = settings.api_prefix + "/agent-admin/dingtalk-bots"
ADMIN = {"username": "bot-admin", "display_name": "系统管理员", "role": "admin", "_actual_role": "admin", "department": "上海分所"}
PAGE_ADMIN = {"username": "bot-page", "display_name": "页面管理员", "role": "admin", "_actual_role": "user", "department": "上海分所"}
FAKE_SECRET = "fake-dingtalk-secret-3333"


class AgentDingtalkBotsAdminTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.identity = ADMIN
        app.dependency_overrides[get_db] = self._db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://bot.test")

    async def _db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def _record(self):
        async with self.sessions() as db:
            return await db.scalar(select(SystemConfig).where(SystemConfig.key == "dingtalk_receipt_bot"))

    async def test_page_admin_cannot_read_or_change(self):
        self.identity = PAGE_ADMIN
        self.assertEqual((await self.client.get(API)).status_code, 403)
        self.assertEqual((await self.client.put(API, json={"app_key": "dingabc"})).status_code, 403)
        self.assertEqual((await self.client.post(API + "/test")).status_code, 403)
        self.assertIsNone(await self._record())

    async def test_secret_sealed_never_echoed_and_kept_when_blank(self):
        saved = await self.client.put(API, json={"app_key": "dingabc", "app_secret": FAKE_SECRET})
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertNotIn(FAKE_SECRET, saved.text)
        self.assertTrue(saved.json()["secret_set"])
        stored = (await self._record()).value
        self.assertNotIn(FAKE_SECRET, json.dumps(stored))
        fetched = await self.client.get(API)
        self.assertNotIn(FAKE_SECRET, fetched.text)
        self.assertNotIn("encrypted_secret", fetched.json())
        kept = await self.client.put(API, json={"app_key": "dingabc", "app_secret": ""})
        self.assertTrue(kept.json()["secret_set"])
        self.assertEqual((await self._record()).value["encrypted_secret"], stored["encrypted_secret"])

    async def test_test_requires_credentials_and_records_result(self):
        self.assertEqual((await self.client.post(API + "/test")).status_code, 422)
        await self.client.put(API, json={"app_key": "dingabc", "app_secret": FAKE_SECRET})
        with patch("app.areas.agent_admin.dingtalk_bots.probe", AsyncMock(return_value=(True, "连接正常"))) as called:
            tested = await self.client.post(API + "/test")
        called.assert_awaited_once_with("dingabc", FAKE_SECRET)
        self.assertTrue(tested.json()["ok"])
        self.assertTrue((await self.client.get(API)).json()["verify_ok"])
        changed = await self.client.put(API, json={"app_key": "dingother"})
        self.assertIsNone(changed.json()["verify_ok"])

    async def test_generic_config_list_hides_bot_config(self):
        await self.client.put(API, json={"app_key": "dingabc", "app_secret": FAKE_SECRET})
        for identity in (PAGE_ADMIN, ADMIN):
            self.identity = identity
            listing = await self.client.get(settings.api_prefix + "/system/configs")
            self.assertEqual(listing.status_code, 200, listing.text)
            self.assertNotIn("dingtalk_receipt_bot", [item["key"] for item in listing.json()["items"]])
            self.assertNotIn("dingabc", listing.text)

    async def test_bad_seal_reports_bot_message(self):
        await self.client.put(API, json={"app_key": "dingabc", "app_secret": FAKE_SECRET})
        async with self.sessions() as db:
            record = await db.scalar(select(SystemConfig).where(SystemConfig.key == "dingtalk_receipt_bot"))
            record.value = {**record.value, "encrypted_secret": "not-valid"}
            await db.commit()
        refused = await self.client.post(API + "/test")
        self.assertEqual(refused.status_code, 409)
        self.assertIn("AppSecret", refused.text)

    async def test_routes_are_not_agent_tools(self):
        from app.agent_mcp.semantic_metadata import exclusion_reasons
        routes = [route for route in app.routes if "dingtalk-bots" in getattr(route, "path", "")]
        self.assertEqual(len(routes), 3)
        for route in routes:
            self.assertTrue(exclusion_reasons(route), route.path)

    async def test_probe_does_not_leak_dingtalk_response(self):
        def reply(status, body):
            return httpx.MockTransport(lambda request: httpx.Response(status, json=body))
        ok, _ = await probe("k", "s", transport=reply(200, {"accessToken": "tok-secret", "expireIn": 7200}))
        self.assertTrue(ok)
        ok, _ = await probe("k", "s", transport=reply(200, ["unexpected"]))
        self.assertFalse(ok)
        ok, text = await probe("k", "s", transport=reply(400, {"message": "bad secret s"}))
        self.assertFalse(ok)
        self.assertNotIn("bad secret", text)


if __name__ == "__main__":
    unittest.main()
