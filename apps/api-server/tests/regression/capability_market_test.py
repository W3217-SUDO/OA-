"""真实隔离数据库验证目录、安装、权限和助手指令接入，不伪造模型回复。"""
import unittest
from copy import deepcopy
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, Department, JobRole, RolePermission, SystemConfig, SystemMenu, User, WorkflowEvent
from app.security import create_token, hash_password
from app.areas.capability_market.catalog import catalog
from app.areas.capability_market.catalog import entry
from app.config import settings
from app.core.permissions import _agent_skill_for_identity


class CapabilityMarketTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original_catalog_path = settings.capability_catalog_path
        if not settings.capability_catalog_path:
            settings.capability_catalog_path = str(Path(__file__).resolve().parents[1] / "resources/capability-market/catalog.json")
        catalog.cache_clear()
        entry.cache_clear()
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        tables = [model.__table__ for model in (User, BusinessRecord, SystemConfig, SystemMenu, RolePermission, Department, JobRole, WorkflowEvent)]
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda sync: Base.metadata.create_all(sync, tables=tables))
        async with self.sessions() as db:
            db.add_all([User(username="CODEX-CAPABILITY-USER", display_name="能力验证用户", role="user", password_hash=hash_password("isolated-verification-only")),
                        User(username="CODEX-CAPABILITY-OTHER", display_name="隔离验证用户", role="user", password_hash=hash_password("isolated-verification-only")),
                        User(username="CODEX-CAPABILITY-ADMIN", display_name="隔离验证管理员", role="admin", password_hash=hash_password("isolated-verification-only"))])
            await db.commit()

        async def isolated_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = isolated_db
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://isolated")
        self.headers = {"Authorization": "Bearer " + create_token("CODEX-CAPABILITY-USER", "user")}
        self.other_headers = {"Authorization": "Bearer " + create_token("CODEX-CAPABILITY-OTHER", "user")}
        self.admin_headers = {"Authorization": "Bearer " + create_token("CODEX-CAPABILITY-ADMIN", "admin")}
        self.item = next(item for item in catalog()["items"] if item["source_path"] == "experts/litigation-legal")
        self.base = "/api/v1/capability-market"

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.pop(get_db, None)
        await self.engine.dispose()
        settings.capability_catalog_path = self.original_catalog_path
        catalog.cache_clear()
        entry.cache_clear()

    async def test_real_install_readback_idempotency_and_assistant_selection(self):
        unauthenticated = await self.client.get(self.base)
        self.assertEqual(unauthenticated.status_code, 401)
        response = await self.client.get(self.base, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn(self.item["id"], [item["id"] for item in response.json()["items"]])
        detail = await self.client.get(self.base + "/items/" + self.item["id"], headers=self.headers)
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertIn("litigation", detail.json()["instruction"].lower())
        resource = detail.json()["resources"][0]
        forbidden = await self.client.get(self.base + "/resources/" + self.item["id"], params={"path": resource}, headers=self.headers)
        self.assertEqual(forbidden.status_code, 403)
        url = self.base + "/items/" + self.item["id"] + "/install"
        body = {"scope": "personal", "sha256": self.item["sha256"]}
        wrong = await self.client.post(url, json={**body, "sha256": "0" * 64}, headers=self.headers)
        self.assertEqual(wrong.status_code, 409)
        global_write = await self.client.post(url, json={**body, "scope": "global"}, headers=self.headers)
        self.assertEqual(global_write.status_code, 403)
        installed = await self.client.post(url, json=body, headers=self.headers)
        self.assertEqual(installed.status_code, 200, installed.text)
        skill = installed.json()
        repeated = await self.client.post(url, json=body, headers=self.headers)
        self.assertEqual(repeated.status_code, 200, repeated.text)
        self.assertEqual(repeated.json()["id"], skill["id"])
        listing = await self.client.get("/api/v1/agent/skills", headers=self.headers)
        self.assertEqual(listing.status_code, 200, listing.text)
        self.assertTrue(any(item["id"] == skill["id"] and item["available"] for item in listing.json()["items"]))
        other = await self.client.get(self.base + "/resources/" + self.item["id"], params={"path": resource}, headers=self.other_headers)
        self.assertEqual(other.status_code, 403)
        reading = await self.client.get(self.base + "/resources/" + self.item["id"], params={"path": resource}, headers=self.headers)
        self.assertEqual(reading.status_code, 200, reading.text)
        self.assertTrue(reading.json()["content"])
        traversal = await self.client.get(self.base + "/resources/" + self.item["id"], params={"path": "../../.env"}, headers=self.headers)
        self.assertEqual(traversal.status_code, 404)
        async with self.sessions() as db:
            resolved = await _agent_skill_for_identity(skill["id"], {"username": "CODEX-CAPABILITY-USER", "role": "user"}, db)
            self.assertEqual(resolved.id, skill["id"])
            self.assertIn("不得覆盖系统权限", resolved.instruction)
            configs = (await db.scalars(select(SystemConfig))).all()
            self.assertEqual(len([record for record in configs if record.key.startswith("agent_skills_")]), 1)

    async def test_catalog_counts_connector_configs_and_blocked_execution(self):
        counts = catalog().get("archive_counts")
        if counts is None:
            self.skipTest("本次使用独立的单项许可证夹具，未配置完整私有整库")
        self.assertEqual(counts, {"skills": 295, "experts": 429, "connectors": 316})
        items = catalog()["items"]
        self.assertEqual(len(items), 1040)
        self.assertEqual(len({item["id"] for item in items}), 1040)
        connector = next(item for item in items if item["source_path"] == "connectors/agent-earth")
        response = await self.client.get(self.base + "/items/" + connector["id"], headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        config = response.json()["connection_configs"]["mcp.json"]["mcpServers"]["agentearth"]
        self.assertTrue(config["url"].startswith("https://agentearth.ai/"))
        self.assertEqual(config["headers"]["X-Api-Key"], "${AGENT_EARTH_API_KEY}")
        blocked = await self.client.post(self.base + "/items/" + connector["id"] + "/install",
                                         json={"scope": "personal", "sha256": connector["sha256"]}, headers=self.headers)
        self.assertEqual(blocked.status_code, 422)

    async def test_connector_encryption_scope_revision_and_private_network_block(self):
        from app.areas.capability_market.connector_store import CONNECTOR_CONFIG_PREFIX, decrypt
        from app.core.system import _validate_system_config
        from fastapi import HTTPException
        item = next(item for item in catalog()['items'] if item['kind'] == 'connector' and (item['source_path'] == 'connectors/24haowan' or item['source_path'] == 'connectors/CODEX-isolated'))
        url = self.base + '/connectors/' + item['id']
        initial = await self.client.get(url + '/config', headers=self.headers)
        self.assertEqual(initial.status_code, 200, initial.text)
        self.assertFalse(initial.json()['saved'])
        configuration = {'mcp.json': {'mcpServers': {'CODEX-REMOTE': {'type': 'streamableHttp', 'url': 'https://127.0.0.1/mcp', 'headers': {'X-Api-Key': 'CODEX-private-verification-only'}}}}}
        body = {'scope': 'personal', 'configuration': configuration, 'revision': '', 'keep_credentials': []}
        denied = await self.client.put(url + '/config', json={**body, 'scope': 'global'}, headers=self.headers)
        self.assertEqual(denied.status_code, 403)
        saved = await self.client.put(url + '/config', json=body, headers=self.headers)
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(saved.json()['status'], 'configured')
        self.assertNotIn('CODEX-private-verification-only', saved.text)
        other = await self.client.get(url + '/config', headers=self.other_headers)
        self.assertFalse(other.json()['saved'])
        revision = saved.json()['revision']
        stale = await self.client.put(url + '/config', json=body, headers=self.headers)
        self.assertEqual(stale.status_code, 409)
        async with self.sessions() as db:
            row = (await db.scalars(select(SystemConfig).where(SystemConfig.key.startswith(CONNECTOR_CONFIG_PREFIX)))).one()
            self.assertNotIn('CODEX-private-verification-only', str(row.value))
            self.assertEqual(decrypt(row), configuration)
            with self.assertRaises(HTTPException):
                _validate_system_config(row.key, {})
        blank = deepcopy(configuration)
        blank['mcp.json']['mcpServers']['CODEX-REMOTE']['headers']['X-Api-Key'] = ''
        kept = await self.client.put(url + '/config', json={**body, 'configuration': blank, 'revision': revision,
            'keep_credentials': [['mcp.json', 'mcpServers', 'CODEX-REMOTE', 'headers', 'X-Api-Key']]}, headers=self.headers)
        self.assertEqual(kept.status_code, 200, kept.text)
        self.assertTrue(kept.json()['secret_fields'][0]['configured'])
        check = await self.client.post(url + '/verify', json={'scope': 'personal', 'revision': kept.json()['revision']}, headers=self.headers)
        self.assertEqual(check.status_code, 200, check.text)
        self.assertFalse(check.json()['ok'])
        self.assertEqual(check.json()['configuration']['status'], 'failed')
        self.assertNotIn('CODEX-private-verification-only', check.text)
        glob = await self.client.put(url + '/config', json={**body, 'scope': 'global'}, headers=self.admin_headers)
        self.assertEqual(glob.status_code, 200, glob.text)
        unavailable = await self.client.get(url + '/config', params={'scope': 'global'}, headers=self.headers)
        self.assertEqual(unavailable.status_code, 403)
        removed = await self.client.delete(url + '/config', params={'scope': 'personal', 'revision': kept.json()['revision']}, headers=self.headers)
        self.assertEqual(removed.status_code, 200, removed.text)
        self.assertFalse(removed.json()['saved'])


if __name__ == "__main__":
    unittest.main()
