"""智能体设置 › DSH API 配置（陶威 11-03）：服务商增删改、切换、测试连接；Key 加密不回显。只用假 Key。"""
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

API = settings.api_prefix + "/agent-admin/model-providers"
ADMIN = {"username": "dsh-admin", "display_name": "系统管理员", "role": "admin", "_actual_role": "admin", "department": "上海分所"}
PAGE_ADMIN = {"username": "dsh-page", "display_name": "页面管理员", "role": "admin", "_actual_role": "user", "department": "上海分所"}
SERVER_KEY = "fake-server-key-0000"
PAGE_KEY = "sk-fake-page-key-1111"


class AgentModelProvidersTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.identity = ADMIN
        app.dependency_overrides[get_db] = self._db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://dsh.test")
        self.settings = patch.multiple(settings, langgraph_api_base_url="https://api.deepseek.com", langgraph_model="deepseek-flash",
                                       langgraph_api_key=SERVER_KEY)
        self.settings.start()

    async def _db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        self.settings.stop()
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def _stored(self) -> dict:
        async with self.sessions() as db:
            record = await db.scalar(select(SystemConfig).where(SystemConfig.key == "agent_model_providers"))
            return record.value if record else {}

    async def test_server_config_is_first_provider_and_active(self):
        response = await self.client.get(API)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["active_id"], "server")
        self.assertEqual([(item["id"], item["type"], item["model"], item["key_source"], item["key_set"]) for item in data["providers"]],
                         [("server", "deepseek", "deepseek-flash", "server", True)])
        self.assertNotIn(SERVER_KEY, response.text)
        ark = next(item for item in data["types"] if item["value"] == "ark")
        self.assertEqual((ark["label"], ark["api"], ark["base_url"], ark["model"]),
                         ("火山方舟（Ark）", "openai-completions", "https://ark.cn-beijing.volces.com/api/plan/v3", "ark-code-latest"))
        self.assertIn("ark-code-latest", ark["models"])
        from app.harness_agent.model_providers import active_model
        async with self.sessions() as db:
            active = await active_model(db)
        self.assertEqual((active.base_url, active.model, active.api_key, active.api), ("https://api.deepseek.com", "deepseek-flash", SERVER_KEY, "openai-completions"))

    async def test_create_switch_edit_delete_without_echoing_key(self):
        created = await self.client.post(API, json={"name": "通义", "type": "qwen", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/",
                                                    "model": "qwen-plus", "api_key": PAGE_KEY})
        self.assertEqual(created.status_code, 200, created.text)
        self.assertNotIn(PAGE_KEY, created.text)
        provider = next(item for item in created.json()["providers"] if item["id"] != "server")
        self.assertEqual((provider["base_url"], provider["key_set"], provider["key_source"]), ("https://dashscope.aliyuncs.com/compatible-mode/v1", True, "page"))
        stored = await self._stored()
        self.assertNotIn(PAGE_KEY, json.dumps(stored))
        self.assertEqual([item["id"] for item in stored["providers"]][0], "server", "服务器配置保存成第一个服务商")

        switched = await self.client.post(API + "/activate", json={"id": provider["id"]})
        self.assertEqual(switched.json()["active_id"], provider["id"])
        from app.harness_agent.model_providers import active_model
        async with self.sessions() as db:
            active = await active_model(db)
        self.assertEqual((active.model, active.api_key), ("qwen-plus", PAGE_KEY), "切换后下一次请求就用新服务商")
        before = active.fingerprint()

        edited = await self.client.put(f"{API}/{provider['id']}", json={"name": "通义千问", "type": "qwen",
                                       "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-max", "api_key": ""})
        self.assertEqual(edited.status_code, 200)
        async with self.sessions() as db:
            active = await active_model(db)
        self.assertEqual((active.name, active.model, active.api_key), ("通义千问", "qwen-max", PAGE_KEY), "Key 留空表示不改")
        self.assertNotEqual(active.fingerprint(), before, "改了模型，常驻会话要重建")

        refused = await self.client.delete(f"{API}/{provider['id']}")
        self.assertEqual(refused.status_code, 409, "当前使用的不能删")
        await self.client.post(API + "/activate", json={"id": "server"})
        removed = await self.client.delete(f"{API}/{provider['id']}")
        self.assertEqual([item["id"] for item in removed.json()["providers"]], ["server"])
        kept = next(item for item in (await self._stored())["providers"] if item["id"] == provider["id"])
        self.assertTrue(kept["deleted_at"], "删除只做逻辑删除")

    async def test_any_openai_compatible_address_and_model_id(self):
        # 陶威 11-03：接口地址、模型、Key 都能自己填；模型不限于下拉里的。
        created = await self.client.post(API, json={"name": "自建网关", "type": "openai_compatible", "base_url": "https://llm.example.com/v1",
                                                    "model": "my-custom-model-2026", "api_key": PAGE_KEY})
        item = next(p for p in created.json()["providers"] if p["id"] != "server")
        self.assertEqual((item["base_url"], item["model"]), ("https://llm.example.com/v1", "my-custom-model-2026"))
        ark = await self.client.post(API, json={"name": "方舟", "type": "ark", "base_url": "https://ark.cn-beijing.volces.com/api/plan/v3",
                                                "model": "ark-code-latest", "api_key": PAGE_KEY})
        ark_id = next(p["id"] for p in ark.json()["providers"] if p["name"] == "方舟")
        await self.client.post(API + "/activate", json={"id": ark_id})
        from app.harness_agent.model_providers import active_model, supports_response_modes
        async with self.sessions() as db:
            active = await active_model(db)
        self.assertEqual((active.api, active.base_url), ("openai-completions", "https://ark.cn-beijing.volces.com/api/plan/v3"))
        self.assertTrue(supports_response_modes(active), "方舟 ark-code-latest 支持快速/深度切换")

    async def test_rejects_incomplete_or_insecure_input(self):
        self.assertEqual((await self.client.post(API, json={"name": "x", "type": "deepseek", "base_url": "http://api.deepseek.com",
                                                            "model": "m", "api_key": PAGE_KEY})).status_code, 422)
        self.assertEqual((await self.client.post(API, json={"name": "x", "type": "deepseek", "base_url": "https://api.deepseek.com",
                                                            "model": "m", "api_key": ""})).status_code, 422)
        with patch.object(settings, "langgraph_api_key", ""):
            self.assertEqual((await self.client.post(API + "/activate", json={"id": "server"})).status_code, 422, "没有 Key 不能设为当前使用")

    async def test_only_actual_system_admin(self):
        self.identity = PAGE_ADMIN
        for response in (await self.client.get(API), await self.client.post(API + "/activate", json={"id": "server"})):
            self.assertEqual(response.status_code, 403)

    async def test_connection_test_records_result_without_key(self):
        created = await self.client.post(API, json={"name": "Claude", "type": "anthropic", "base_url": "https://api.anthropic.com",
                                                    "model": "claude-sonnet-5-5", "api_key": PAGE_KEY})
        provider_id = next(item["id"] for item in created.json()["providers"] if item["id"] != "server")
        probe = AsyncMock(return_value=(False, "HTTP 401，API Key 无效"))
        with patch("app.areas.agent_admin.model_providers._probe", probe):
            result = await self.client.post(f"{API}/{provider_id}/test")
        self.assertEqual(result.json(), {"ok": False, "message": "HTTP 401，API Key 无效"})
        self.assertEqual(probe.await_args.args, ("anthropic-messages", "https://api.anthropic.com", "claude-sonnet-5-5", PAGE_KEY))
        listed = next(item for item in (await self.client.get(API)).json()["providers"] if item["id"] == provider_id)
        self.assertEqual((listed["verify_ok"], listed["verify_message"]), (False, "HTTP 401，API Key 无效"))

    async def test_generic_system_config_cannot_touch_providers(self):
        await self.client.post(API, json={"name": "Kimi", "type": "moonshot", "base_url": "https://api.moonshot.cn/v1",
                                          "model": "kimi", "api_key": PAGE_KEY})
        listing = await self.client.get(settings.api_prefix + "/system/configs")
        self.assertNotIn("agent_model_providers", listing.text)
        patched = await self.client.patch(settings.api_prefix + "/system/configs/agent_model_providers", json={"value": {}})
        self.assertIn(patched.status_code, {404, 409})

    async def test_probe_sends_minimal_request_per_protocol(self):
        from app.areas.agent_admin import model_providers as module
        seen = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append((str(request.url), request.headers.get("authorization"), request.headers.get("x-api-key"), json.loads(request.content)["max_tokens"]))
            return httpx.Response(200, json={}) if "deepseek" in str(request.url) else httpx.Response(401, json={"error": {"message": "invalid x-api-key"}})

        original = httpx.AsyncClient
        with patch.object(module.httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs)):
            ok = await module._probe("openai-completions", "https://api.deepseek.com", "deepseek-flash", PAGE_KEY)
            bad = await module._probe("anthropic-messages", "https://api.anthropic.com", "claude-sonnet-5-5", PAGE_KEY)
        self.assertTrue(ok[0])
        self.assertEqual(bad, (False, "HTTP 401，API Key 无效，invalid x-api-key"))
        self.assertEqual(seen, [("https://api.deepseek.com/chat/completions", "Bearer " + PAGE_KEY, None, 1),
                                ("https://api.anthropic.com/v1/messages", None, PAGE_KEY, 1)])

    def test_runtime_patch_and_environment_follow_active_provider(self):
        from app.harness_agent.model_providers import ActiveModel
        from app.harness_agent.runtime import _environment, _patch
        active = ActiveModel(id="p-1", name="Claude", type="anthropic", api="anthropic-messages", base_url="https://api.anthropic.com",
                             model="claude-sonnet-5-5", api_key=PAGE_KEY)
        patch_items = _patch("http://127.0.0.1:1/mcp", "token", [], {}, False, "fast", active=active)
        provider = next(item for item in patch_items if item.get("id") == "llm-pi-ai")["config"]["providers"]["huzhi-oa"]
        self.assertEqual((provider["api"], provider["baseURL"], provider["models"][0]["id"], provider["displayName"]),
                         ("anthropic-messages", "https://api.anthropic.com", "claude-sonnet-5-5", "Claude"))
        self.assertNotIn(PAGE_KEY, json.dumps(patch_items), "Key 只走环境变量，不写进配置文件")
        self.assertEqual(_environment(PAGE_KEY)["OA_MODEL_API_KEY"], PAGE_KEY)


if __name__ == "__main__":
    unittest.main()
