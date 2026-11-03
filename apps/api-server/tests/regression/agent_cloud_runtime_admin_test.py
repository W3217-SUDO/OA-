"""智能体设置 › 云端智能体：只有系统管理员能改，Key 加密保存不回显，没填 Key 不能启用，启用后智能体走云端。"""
import json
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import SystemConfig
from app.security import current_identity

API = settings.api_prefix + "/agent-admin/cloud-runtime"
ADMIN = {"username": "cloud-admin", "display_name": "系统管理员", "role": "admin", "_actual_role": "admin", "department": "上海分所"}
PAGE_ADMIN = {"username": "cloud-page", "display_name": "页面管理员", "role": "admin", "_actual_role": "user", "department": "上海分所"}
FAKE_KEY = "ark-fake-cloud-key-2222"


class AgentCloudRuntimeAdminTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.identity = ADMIN
        app.dependency_overrides[get_db] = self._db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://cloud.test")

    async def _db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_default_disabled_and_dsh_stays_in_use(self):
        response = await self.client.get(API)
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.json()["enabled"], response.json()["key_set"]), (False, False))
        from app.cloud_agent.config import active
        async with self.sessions() as db:
            self.assertIsNone(await active(db))

    async def test_cannot_enable_without_key_and_key_never_echoed(self):
        refused = await self.client.put(API, json={"enabled": True, "model": "deepseek-v4-1-flash-261017"})
        self.assertEqual(refused.status_code, 422)
        saved = await self.client.put(API, json={"enabled": True, "model": "deepseek-v4-1-flash-261017", "api_key": FAKE_KEY})
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertNotIn(FAKE_KEY, saved.text)
        self.assertTrue(saved.json()["key_set"])
        async with self.sessions() as db:
            record = await db.scalar(select(SystemConfig).where(SystemConfig.key == "agent_cloud_runtime"))
        self.assertNotIn(FAKE_KEY, json.dumps(record.value))
        # 编辑时 Key 留空不改
        kept = await self.client.put(API, json={"enabled": True, "model": "doubao-seed-2-1-pro-260915"})
        self.assertEqual(kept.status_code, 200)
        from app.cloud_agent.config import active
        async with self.sessions() as db:
            current = await active(db)
        self.assertEqual((current.api_key, current.model), (FAKE_KEY, "doubao-seed-2-1-pro-260915"))

    async def test_only_actual_system_admin(self):
        self.identity = PAGE_ADMIN
        self.assertEqual((await self.client.get(API)).status_code, 403)
        self.assertEqual((await self.client.put(API, json={"enabled": False, "model": "x"})).status_code, 403)

    async def test_test_endpoint_records_result(self):
        await self.client.put(API, json={"enabled": False, "model": "deepseek-v4-1-flash-261017", "api_key": FAKE_KEY})
        with patch("app.areas.agent_admin.cloud_runtime.probe", AsyncMock(return_value=(False, "HTTP 400，模型还没在方舟“开通管理”里开通"))) as probe:
            response = await self.client.post(API + "/test")
        self.assertEqual(response.json()["ok"], False)
        probe.assert_awaited_once_with(FAKE_KEY, "deepseek-v4-1-flash-261017")
        self.assertIn("开通", (await self.client.get(API)).json()["verify_message"])

    async def test_usage_summary_admin_only(self):
        rows = [{"time": "2026-11-03T10:00:00+08:00", "username": "a", "display_name": "甲", "workspace": "personal", "ok": True,
                 "input_tokens": 1, "cache_tokens": 1, "output_tokens": 1, "active_seconds": 1, "oa_tools": 1, "datapro": {},
                 "searches": 0, "harness_afp": 0, "model_yuan": 0.01, "runtime_yuan": 0.0, "harness_yuan": 0.0}]
        with patch("app.cloud_agent.usage.read_month", return_value=rows):
            data = (await self.client.get(API + "/usage", params={"month": "2026-11"})).json()
            self.assertEqual((data["month"], data["total"]["turns"], data["people"][0]["display_name"]), ("2026-11", 1, "甲"))
            records = (await self.client.get(API + "/usage/records", params={"month": "2026-11", "username": "a"})).json()
            self.assertEqual(records["total"], 1)
            self.assertEqual((await self.client.get(API + "/usage", params={"month": "2026/11"})).status_code, 422)
            self.identity = PAGE_ADMIN
            self.assertEqual((await self.client.get(API + "/usage")).status_code, 403)

    async def test_my_usage_only_returns_logged_in_user(self):
        def row(username, yuan):
            return {"time": "2026-11-03T10:00:00+08:00", "username": username, "display_name": username, "workspace": "personal",
                    "ok": True, "input_tokens": 1, "cache_tokens": 1, "output_tokens": 1, "active_seconds": 1, "oa_tools": 2,
                    "datapro": {}, "searches": 0, "harness_afp": 0, "model_yuan": yuan, "runtime_yuan": 0.0, "harness_yuan": 0.0}
        rows = [row("cloud-page", 0.02), row("someone-else", 9.99)]
        self.identity = PAGE_ADMIN  # 普通人（非系统管理员）也能看自己的
        with patch("app.cloud_agent.usage.read_month", return_value=rows), \
                patch("app.areas.personal_agent.router.personal_identity", AsyncMock(return_value={"username": "cloud-page"})):
            data = (await self.client.get(settings.api_prefix + "/personal-agent/cloud-usage",
                                          params={"month": "2026-11", "username": "someone-else"})).json()
        self.assertEqual((data["summary"]["turns"], data["summary"]["total_yuan"], data["total_records"]), (1, 0.02, 1))
        self.assertTrue(all(item["model_yuan"] == 0.02 for item in data["records"]))
        self.assertIn("估算", data["note"])
