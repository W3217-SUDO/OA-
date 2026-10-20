"""真实隔离数据库验证目录、安装、权限和助手指令接入，不伪造模型回复。"""
import unittest
import json
from contextlib import AsyncExitStack, contextmanager
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI, Header
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from copy import deepcopy
from pathlib import Path
import hashlib
from io import BytesIO
import tempfile
from zipfile import ZipFile

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
from app.security import current_identity
from app.areas.capability_market.router import router
from app.areas.capability_market.connector_store import decrypt
from app.areas.personal_agent.router import router as personal_router
from app.agent_mcp.semantic_metadata import exclusion_reasons
from app.agent_mcp.safety import reject_credentials
from app.core.lifecycle import request_validation_error_handler


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

    async def test_native_market_install_keeps_resources_owner_idempotency_and_disabled_state(self):
        from fastapi import HTTPException
        from app.harness_agent.bundles import _unpack, read_resource
        from app.github_agent_skills import github_skill_location
        from app.areas.capability_market.catalog import legacy_definition
        from app.core.documents import _save_user_agent_skills
        from app.user_agent_skills import normalize_custom_skill

        item = next(entry(value['id']) for value in catalog()['items'] if value['name'] == 'china-litigation-toolkit')
        raw = item['resources']['SKILL.md'].encode()
        archive = BytesIO()
        location = github_skill_location(item['source'])
        root = 'repo/' + str(Path(location['path']).parent).replace('\\', '/') + '/'
        with ZipFile(archive, 'w') as package:
            package.writestr(root + 'SKILL.md', raw)
            package.writestr(root + 'scripts/calculate_lawsuit_fee.py', b'print(100)\n')
        with tempfile.TemporaryDirectory() as temporary, patch('app.harness_agent.bundles.storage_root', return_value=Path(temporary)):
            bundle = _unpack(archive.getvalue(), location, hashlib.sha256(raw).hexdigest())
            bundle['commit'] = location['ref']
            existing = normalize_custom_skill({**legacy_definition(item), 'sha256': item['sha256'], 'enabled': False}, source=item['source'])
            async with self.sessions() as db:
                await _save_user_agent_skills('CODEX-CAPABILITY-USER', [existing], {'username': 'CODEX-CAPABILITY-USER'}, db)
            url = self.base + '/items/' + item['id'] + '/install'
            body = {'scope': 'personal', 'sha256': item['sha256']}
            with patch('app.areas.capability_market.native_install.install_bundle', AsyncMock(return_value=bundle)) as download:
                installed = await self.client.post(url, json=body, headers=self.headers)
                self.assertEqual(installed.status_code, 200, installed.text)
                self.assertEqual(installed.json()['id'], existing['id'])
                self.assertFalse(installed.json()['enabled'])
                self.assertEqual(installed.json()['instruction'], item['instruction'])
                repeated = await self.client.post(url, json=body, headers=self.headers)
                self.assertEqual(repeated.status_code, 200, repeated.text)
                self.assertEqual(download.await_count, 1)
            async with self.sessions() as db:
                row = await db.scalar(select(SystemConfig).where(SystemConfig.key.startswith('agent_skills_')))
                saved = deepcopy(row.value['skills'][0])
                self.assertEqual(read_resource(saved['bundle'], 'scripts/calculate_lawsuit_fee.py'), b'print(100)\n')
                self.assertEqual(saved['id'], existing['id'])
                self.assertFalse(saved['enabled'])
                saved['instruction'] += '\n用户编辑内容必须保留'
                row.value = {**row.value, 'skills': [saved]}
                await db.commit()
            async with self.sessions() as db:
                row = await db.scalar(select(SystemConfig).where(SystemConfig.key.startswith('agent_skills_')))
                self.assertTrue(row.value['skills'][0]['instruction'].endswith('用户编辑内容必须保留'))
            with patch('app.areas.capability_market.native_install.install_bundle', AsyncMock()) as download:
                conflict = await self.client.post(url, json=body, headers=self.headers)
                self.assertEqual(conflict.status_code, 409, conflict.text)
                download.assert_not_awaited()
            async with self.sessions() as db:
                with self.assertRaises(HTTPException):
                    await _agent_skill_for_identity(existing['id'], {'username': 'CODEX-CAPABILITY-OTHER', 'role': 'user'}, db)

    async def test_native_global_requires_manager_and_preserves_unrelated_adaptation_errors(self):
        from app.areas.capability_market.native_install import installation_reason
        from app.harness_agent.bundles import _unpack
        from app.github_agent_skills import github_skill_location
        item = next(entry(value['id']) for value in catalog()['items'] if value['name'] == 'china-litigation-toolkit')
        self.assertFalse(installation_reason(item))
        for changed in ({'kind': 'team'}, {'dependencies': ['external-service']}, {'instruction': 'TeamCreate protected tool'},
                        {'unavailable_reason': '包格式需要适配，未安装：ValueError'}):
            self.assertTrue(installation_reason({**item, **changed}))
        location = github_skill_location(item['source'])
        content = BytesIO()
        raw = item['resources']['SKILL.md'].encode()
        with ZipFile(content, 'w') as archive:
            archive.writestr('repo/' + str(Path(location['path']).parent).replace('\\', '/') + '/SKILL.md', raw)
        url = self.base + '/items/' + item['id'] + '/install'
        body = {'scope': 'global', 'sha256': item['sha256']}
        with tempfile.TemporaryDirectory() as temporary, patch('app.harness_agent.bundles.storage_root', return_value=Path(temporary)):
            bundle = _unpack(content.getvalue(), location, hashlib.sha256(raw).hexdigest())
            bundle['commit'] = location['ref']
            download = AsyncMock(return_value=bundle)
            with patch('app.areas.capability_market.native_install.install_bundle', download):
                denied = await self.client.post(url, json=body, headers=self.headers)
                self.assertEqual(denied.status_code, 403)
                download.assert_not_awaited()
                installed = await self.client.post(url, json=body, headers=self.admin_headers)
                self.assertEqual(installed.status_code, 200, installed.text)
                repeated = await self.client.post(url, json=body, headers=self.admin_headers)
                self.assertEqual(repeated.status_code, 200, repeated.text)
                self.assertEqual(installed.json()['id'], repeated.json()['id'])
                self.assertEqual(download.await_count, 1)
        async with self.sessions() as db:
            row = await db.scalar(select(SystemConfig).where(SystemConfig.key == 'agent_global_skills_v1'))
            self.assertEqual(len(row.value['skills']), 1)
            self.assertEqual(row.value['skills'][0]['bundle'], bundle)

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


class PersonalMcpTest(unittest.IsolatedAsyncioTestCase):
    @contextmanager
    def sdk_transport(self, identity=None):
        import httpx2
        from app.agent_mcp.auth import AuthContext, _auth_context
        self.sdk_calls = []
        self.sdk_sse = False
        self.sdk_schema = {'type': 'object', 'properties': {'query': {'type': 'string'}},
                           'required': ['query'], 'additionalProperties': False}
        self.sdk_result = {'content': [{'type': 'text', 'text': 'CODEX远程真实协议返回'}],
                           'structuredContent': {self.secret: 'Bearer ' + self.secret}, 'isError': False}

        async def handler(request):
            if request.method != 'POST':
                return httpx2.Response(204 if request.method == 'DELETE' else 405)
            payload = json.loads(await request.aread())
            self.sdk_calls.append(payload)
            method = payload['method']
            if 'id' not in payload:
                return httpx2.Response(202)
            if method == 'initialize':
                result = {'protocolVersion': '2025-06-18', 'capabilities': {'tools': {}},
                          'serverInfo': {'name': 'CODEX-MCP', 'version': '1'}}
            elif method == 'tools/list':
                result = {'tools': [{'name': 'lookup', 'description': 'CODEX查询', 'inputSchema': self.sdk_schema,
                                     'annotations': {'readOnlyHint': True}}]}
            elif method == 'tools/call':
                result = self.sdk_result
            else:
                raise AssertionError('意外协议方法')
            envelope = {'jsonrpc': '2.0', 'id': payload['id'], 'result': result}
            if self.sdk_sse and method == 'tools/call':
                return httpx2.Response(200, content=('event: message\ndata: ' + json.dumps(envelope) + '\n\n').encode(),
                                       headers={'content-type': 'text/event-stream'})
            return httpx2.Response(200, json=envelope)

        def network_init(instance):
            instance.inner = httpx2.MockTransport(handler)
            instance.failure = ''

        identity = identity or self.identities['CODEX-MCP-OWNER']
        context = AuthContext(self.app, 'CODEX-isolated-oa-bearer', {
            'type': 'http', 'method': 'POST', 'path': '/api/v1/personal-agent/messages',
            'headers': [(b'origin', b'http://localhost:5173'), (b'x-oa-agent-confirmation', b'frontend')],
        })
        token = _auth_context.set(context)
        try:
            with patch('app.areas.capability_market.remote_session.PublicHttpsTransport.__init__', new=network_init), \
                 patch('app.areas.capability_market.connector_transport.public_address', new=AsyncMock(return_value='93.184.216.34')), \
                 patch('app.areas.personal_agent.mcp_tools.authenticated_identity', new=AsyncMock(return_value=identity)), \
                 patch('app.agent_mcp.auth.authenticated_identity', new=AsyncMock(return_value=identity)):
                yield identity, context
        finally:
            _auth_context.reset(token)

    async def asyncSetUp(self):
        self.engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as connection:
            tables = [model.__table__ for model in (User, BusinessRecord, SystemConfig, WorkflowEvent)]
            await connection.run_sync(lambda sync: Base.metadata.create_all(sync, tables=tables))
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.include_router(personal_router)
        self.app.add_exception_handler(RequestValidationError, request_validation_error_handler)

        self.identities = {}
        for name in ('CODEX-MCP-OWNER', 'CODEX-MCP-OTHER', 'CODEX-MCP-ADMIN', 'CODEX-MCP-PAGE-ADMIN', 'CODEX-MCP-DELEGATE'):
            actual_role = 'admin' if name == 'CODEX-MCP-ADMIN' else 'user'
            self.identities[name] = {'username': name, 'role': actual_role, 'department': '',
                                     '_actual_role': actual_role, '_actual_role_ids': [actual_role],
                                     'menu_keys': [], 'action_keys': [], '_user_action_keys': []}
        self.identities['CODEX-MCP-PAGE-ADMIN'].update(role='admin', role_ids=['admin'], _page_menu_capability=True)
        self.identities['CODEX-MCP-DELEGATE']['_user_action_keys'] = ['agent.settings.global.manage']

        async def identity(x_user: str = Header(default='CODEX-MCP-OWNER')):
            return dict(self.identities[x_user])

        async def database():
            async with self.sessions() as db:
                yield db

        self.app.dependency_overrides[current_identity] = identity
        self.app.dependency_overrides[get_db] = database
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url='http://isolated')
        self.base = '/api/v1/capability-market/personal-mcp'
        self.secret = 'CODEX-MCP-isolated-secret-never-echo'
        self.configuration = {'mcp.json': {'mcpServers': {'default': {
            'type': 'streamableHttp', 'url': 'https://example.com/mcp',
            'headers': {'Authorization': 'Bearer ' + self.secret}}}}}

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def create(self):
        response = await self.client.post(self.base, json={'name': 'CODEX个人连接', 'configuration': self.configuration})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn(self.secret, response.text)
        return response.json()

    async def create_for(self, username):
        response = await self.client.post(self.base, headers={'X-User': username},
                                          json={'name': 'CODEX连接-' + username, 'configuration': self.configuration})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn(self.secret, response.text)
        return response.json()

    async def test_scope_default_uses_actual_admin_not_page_role_or_delegated_management(self):
        from app.areas.capability_market.connector_store import config_key
        personal = await self.create()
        async with self.sessions() as db:
            original = deepcopy((await db.scalars(select(SystemConfig))).one().value)
        for username, expected in [('CODEX-MCP-PAGE-ADMIN', 'personal'), ('CODEX-MCP-DELEGATE', 'personal'),
                                    ('CODEX-MCP-ADMIN', 'global')]:
            created = await self.create_for(username)
            self.assertEqual(created['scope'], expected)
            listing = (await self.client.get(self.base, headers={'X-User': username})).json()
            self.assertEqual(listing['default_scope'], expected)
            self.assertEqual(listing['can_manage_global'], username != 'CODEX-MCP-PAGE-ADMIN')
        # 原个人连接不迁移；同一账号成为真实管理员后只影响新建默认值。
        self.identities['CODEX-MCP-OWNER'].update(role='user', _actual_role='admin', _actual_role_ids=['admin'])
        promoted = await self.create()
        self.assertEqual(promoted['scope'], 'global')
        async with self.sessions() as db:
            row = await db.scalar(select(SystemConfig).where(SystemConfig.key == config_key(
                personal['id'], 'personal', self.identities['CODEX-MCP-OWNER'])))
            self.assertEqual(row.value, original)
        own_legacy = await self.client.get(self.base + '/' + personal['id'])
        self.assertEqual(own_legacy.json()['scope'], 'personal')
        self.assertEqual(own_legacy.json()['revision'], personal['revision'])

    async def test_no_settings_permissions_personal_crud_verify_and_global_config_denied(self):
        from app.areas.capability_market.connector_store import owner_for
        from fastapi import HTTPException
        identity = self.identities['CODEX-MCP-OWNER']
        self.assertEqual(identity['menu_keys'], [])
        self.assertEqual(identity['action_keys'], [])
        self.assertEqual(identity['_user_action_keys'], [])
        shared = await self.create_for('CODEX-MCP-ADMIN')
        shared_url = self.base + '/' + shared['id']
        listing = (await self.client.get(self.base)).json()
        self.assertEqual(listing['items'], [])
        self.assertFalse(listing['can_manage_global'])
        summary = listing['available_connections'][0]
        self.assertEqual(set(summary), {'id', 'name', 'scope', 'revision', 'status', 'can_manage'})
        self.assertEqual(summary['scope'], 'global')
        self.assertFalse(summary['can_manage'])
        self.assertNotIn(self.secret, json.dumps(listing))
        with self.assertRaises(HTTPException):
            owner_for('global', identity)
        self.assertEqual((await self.client.get(shared_url, params={'scope': 'global'})).status_code, 403)
        body = {'name': 'CODEX尝试管理全局', 'configuration': self.configuration, 'revision': shared['revision']}
        self.assertEqual((await self.client.put(shared_url, params={'scope': 'global'}, json=body)).status_code, 403)
        with patch('app.areas.capability_market.personal_mcp_routes.verify_configuration', new=AsyncMock()) as verify:
            rejected = await self.client.post(shared_url + '/verify', params={'scope': 'global'}, json={'revision': shared['revision']})
            self.assertEqual(rejected.status_code, 403)
            verify.assert_not_awaited()
        self.assertEqual((await self.client.delete(shared_url, params={'scope': 'global', 'revision': shared['revision']})).status_code, 403)
        delegated = await self.client.get(shared_url, params={'scope': 'global'}, headers={'X-User': 'CODEX-MCP-DELEGATE'})
        self.assertEqual(delegated.status_code, 200, delegated.text)
        self.assertEqual(delegated.json()['scope'], 'global')
        own = await self.create()
        own_url = self.base + '/' + own['id']
        self.assertEqual((await self.client.get(own_url)).status_code, 200)
        updated = await self.client.put(own_url, json={**body, 'name': 'CODEX本人连接', 'revision': own['revision']})
        self.assertEqual(updated.status_code, 200, updated.text)
        with patch('app.areas.capability_market.personal_mcp_routes.verify_configuration', new=AsyncMock(return_value={
            'status': 'verified', 'servers': [], 'error': ''})) as verify:
            verified = await self.client.post(own_url + '/verify', json={'revision': updated.json()['revision']})
            self.assertEqual(verified.status_code, 200, verified.text)
            self.assertTrue(verified.json()['ok'])
            verify.assert_awaited_once()
        removed = await self.client.delete(own_url, params={'revision': updated.json()['revision']})
        self.assertEqual(removed.status_code, 200, removed.text)
        self.assertEqual((await self.client.get(own_url)).status_code, 404)

    async def test_ordinary_user_global_discovery_and_confirmed_call_without_configuration_access(self):
        from app.areas.personal_agent.mcp_tools import PersonalMcpToolSession
        from app.areas.personal_agent.confirmation_history import prepare_personal_action
        from app.areas.personal_agent.service import _decide_action
        shared = await self.create_for('CODEX-MCP-ADMIN')
        async with self.sessions() as db, AsyncExitStack() as stack:
            identity, context = stack.enter_context(self.sdk_transport())
            tools = PersonalMcpToolSession(identity, db, conversation_id='CODEX-GLOBAL-MCP')
            with patch('app.areas.capability_market.personal_mcp.decrypt', side_effect=AssertionError('组摘要不得解密')):
                groups = await tools.execute('personal_mcp_list_groups', {})
            group = groups['groups'][0]
            self.assertEqual(group['scope'], 'global')
            self.assertEqual(group['connection_id'], shared['id'])
            discovered = await tools.execute('personal_mcp_search_tools', {'group_id': group['group_id']})
            self.assertIn('tools', discovered, discovered)
            descriptor = discovered['tools'][0]
            self.assertEqual(descriptor['scope'], 'global')
            self.assertNotIn(self.secret, json.dumps(discovered))
            self.assertNotIn('configuration', descriptor)
            self.assertNotIn('headers', descriptor)
            prepared = await tools.execute('personal_mcp_call_tool', {'tool_id': descriptor['tool_id'], 'arguments': {'query': 'CODEX'}})
            self.assertEqual(prepared['result']['status'], 'pending')
            self.assertFalse(any(call['method'] == 'tools/call' for call in self.sdk_calls))
            action = {**tools.pending_actions[0], 'id': str(uuid4()), 'status': 'pending', 'requested_by': identity['username']}
            self.assertEqual(action['payload']['scope'], 'global')
            self.assertEqual(action['payload']['connection_id'], shared['id'])
            self.assertEqual(action['payload']['revision'], shared['revision'])
            conversation = {'conversation_id': 'CODEX-GLOBAL-MCP', 'conversation_title': 'CODEX全局调用',
                            'messages': [], 'pending_actions': [action]}
            await prepare_personal_action(action, identity, conversation, db)
            await db.commit()
            context.scope['path'] = '/api/v1/personal-agent/actions/' + action['id'] + '/decision'
            with patch('app.areas.personal_agent.service._save_state', new=AsyncMock()):
                outcome = await _decide_action(identity, db, action['id'], 'approved', '', conversation)
            self.assertEqual(outcome['status'], 'approved')
            self.assertEqual(len([call for call in self.sdk_calls if call['method'] == 'tools/call']), 1)
            self.assertNotIn(self.secret, json.dumps(outcome, ensure_ascii=False))

    async def test_global_confirmation_rejects_scope_target_revision_and_legacy_payload_changes(self):
        from fastapi import HTTPException
        from app.areas.personal_agent.mcp_tools import PersonalMcpToolSession
        from app.areas.personal_agent.confirmation_history import prepare_personal_action, begin_personal_decision
        from app.areas.capability_market.remote_tools import execute_call
        shared = await self.create_for('CODEX-MCP-ADMIN')
        own = await self.create()
        async with self.sessions() as db, AsyncExitStack() as stack:
            identity, context = stack.enter_context(self.sdk_transport())
            tools = PersonalMcpToolSession(identity, db, conversation_id='CODEX-BOUND-MCP')
            await tools.execute('personal_mcp_list_groups', {})
            discovered = await tools.execute('personal_mcp_search_tools', {'group_id': 'global:' + shared['id']})
            await tools.execute('personal_mcp_call_tool', {'tool_id': discovered['tools'][0]['tool_id'], 'arguments': {'query': 'CODEX'}})
            action = {**tools.pending_actions[0], 'id': str(uuid4()), 'status': 'pending', 'requested_by': identity['username']}
            conversation = {'conversation_id': 'CODEX-BOUND-MCP', 'conversation_title': 'CODEX范围绑定'}
            await prepare_personal_action(action, identity, conversation, db)
            await db.commit()
            context.scope['path'] = '/api/v1/personal-agent/actions/' + action['id'] + '/decision'
            await begin_personal_decision(action, 'approved', '', identity, conversation, db)
            for changed in [dict(action['payload'], scope='personal'), dict(action['payload'], connection_id=own['id']),
                            dict(action['payload'], revision='0' * 32)]:
                with self.assertRaises(HTTPException):
                    await execute_call(changed, identity, db, action_id=action['id'])
            with self.assertRaises(HTTPException):
                await execute_call(action['payload'], self.identities['CODEX-MCP-OTHER'], db, action_id=action['id'])
            await db.rollback()
            updated = await self.client.put(self.base + '/' + shared['id'], params={'scope': 'global'},
                                            headers={'X-User': 'CODEX-MCP-ADMIN'}, json={
                'name': shared['name'], 'configuration': self.configuration, 'revision': shared['revision']})
            self.assertEqual(updated.status_code, 200, updated.text)
            with self.assertRaises(HTTPException) as stale:
                await execute_call(action['payload'], identity, db, action_id=action['id'])
            self.assertEqual(stale.exception.status_code, 409)
            self.assertFalse(any(call['method'] == 'tools/call' for call in self.sdk_calls))
            await db.rollback()
            legacy = {**action, 'id': str(uuid4()), 'payload': {key: value for key, value in action['payload'].items() if key != 'scope'}}
            await prepare_personal_action(legacy, identity, conversation, db)
            await db.commit()
            await begin_personal_decision(legacy, 'approved', '', identity, conversation, db)
            with self.assertRaises(HTTPException) as missing:
                await execute_call(legacy['payload'], identity, db, action_id=legacy['id'])
            self.assertEqual(missing.exception.status_code, 409)
            self.assertIn('范围缺失', missing.exception.detail)
            self.assertFalse(any(call['method'] == 'tools/call' for call in self.sdk_calls))

    async def test_same_identifier_in_personal_and_global_has_distinct_runtime_targets(self):
        from app.areas.capability_market.connector_store import save_configuration
        from app.areas.capability_market.personal_mcp import item_for
        from app.areas.personal_agent.mcp_tools import PersonalMcpToolSession
        shared = await self.create_for('CODEX-MCP-ADMIN')
        hidden = await self.create_for('CODEX-MCP-OTHER')
        async with self.sessions() as db, AsyncExitStack() as stack:
            identity, context = stack.enter_context(self.sdk_transport())
            await save_configuration(item_for(shared['id'], 'CODEX同编号个人连接'), 'personal', identity, db,
                                     self.configuration, [], '')
            tools = PersonalMcpToolSession(identity, db, conversation_id='CODEX-SCOPED-MCP')
            groups = await tools.execute('personal_mcp_list_groups', {})
            self.assertEqual({item['group_id'] for item in groups['groups']},
                             {'personal:' + shared['id'], 'global:' + shared['id']})
            self.assertNotIn(hidden['id'], json.dumps(groups))
            tool_ids = []
            for scope in ('personal', 'global'):
                discovered = await tools.execute('personal_mcp_search_tools', {'group_id': scope + ':' + shared['id']})
                descriptor = discovered['tools'][0]
                self.assertEqual(descriptor['scope'], scope)
                self.assertEqual(descriptor['connection_id'], shared['id'])
                tool_ids.append(descriptor['tool_id'])
                await tools.execute('personal_mcp_call_tool', {'tool_id': descriptor['tool_id'], 'arguments': {'query': 'CODEX'}})
            self.assertNotEqual(*tool_ids)
            self.assertEqual([action['payload']['scope'] for action in tools.pending_actions], ['personal', 'global'])
            self.assertFalse(any(call['method'] == 'tools/call' for call in self.sdk_calls))

    async def test_lifecycle_encryption_owner_revision_preservation_and_cleanup(self):
        state = await self.create()
        url = self.base + '/' + state['id']
        self.assertEqual(state['capabilities'], {'discovery': True, 'tool_call': True})
        self.assertEqual(state['servers'], [])
        self.assertTrue(state['secret_fields'][0]['configured'])
        async with self.sessions() as db:
            row = (await db.scalars(select(SystemConfig))).one()
            self.assertNotIn(self.secret, json.dumps(row.value))
            self.assertEqual(decrypt(row), self.configuration)
        other = {'X-User': 'CODEX-MCP-OTHER'}
        self.assertEqual((await self.client.get(url, headers=other)).status_code, 404)
        self.assertEqual((await self.client.get(self.base, headers=other)).json()['items'], [])
        self.assertEqual((await self.client.get(self.base)).json()['items'][0]['id'], state['id'])
        body = {'name': state['name'], 'configuration': state['configuration'], 'revision': state['revision'],
                'keep_credentials': [['mcp.json', 'mcpServers', 'default', 'headers', 'Authorization']]}
        self.assertEqual((await self.client.put(url, json=body, headers=other)).status_code, 404)
        self.assertEqual((await self.client.post(url + '/verify', json={'revision': state['revision']}, headers=other)).status_code, 404)
        self.assertEqual((await self.client.delete(url, params={'revision': state['revision']}, headers=other)).status_code, 404)
        updated = await self.client.put(url, json=body)
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertNotEqual(updated.json()['revision'], state['revision'])
        self.assertEqual((await self.client.put(url, json=body)).status_code, 409)
        self.assertEqual((await self.client.post(url + '/verify', json={'revision': state['revision']})).status_code, 409)
        self.assertEqual((await self.client.delete(url, params={'revision': state['revision']})).status_code, 409)
        async with self.sessions() as db:
            row = (await db.scalars(select(SystemConfig))).one()
            self.assertEqual(decrypt(row), self.configuration)
        deleted = await self.client.delete(url, params={'revision': updated.json()['revision']})
        self.assertEqual(deleted.json(), {'id': state['id'], 'scope': 'personal', 'deleted': True})
        self.assertEqual((await self.client.get(url)).status_code, 404)
        async with self.sessions() as db:
            self.assertEqual((await db.scalars(select(SystemConfig))).all(), [])

    async def test_url_json_shapes_and_rejected_secret_locations(self):
        for config in ['https://example.com/mcp', {'mcpServers': self.configuration['mcp.json']['mcpServers']},
                       json.dumps(self.configuration), {'mcpServers': {'北大法宝': {'type': 'streamableHttp', 'url': 'https://example.com/mcp'}}}]:
            response = await self.client.post(self.base, json={'name': 'CODEX连接', 'configuration': config})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn(self.secret, response.text)
        for configuration in [
            'https://example.com/mcp?token=' + self.secret,
            'https://user:' + self.secret + '@example.com/mcp',
            'http://example.com/mcp',
            *['https://example.com/mcp?' + key + '=' + self.secret for key in ('key', 'credential', 'signature', 'accessKey')],
            {'mcpServers': {'default': {'type': 'stdio', 'command': self.secret}}},
            {'mcpServers': {'default': {'type': 'sse', 'url': 'https://example.com', 'unknown': self.secret}}},
            {'mcpServers': {'default': {'type': [], 'url': 'https://example.com'}}},
        ]:
            response = await self.client.post(self.base, json={'name': 'CODEX连接', 'configuration': configuration})
            self.assertEqual(response.status_code, 422, response.text)
            self.assertNotIn(self.secret, response.text)
        denied = await self.client.post(self.base, json={'name': 'CODEX连接', 'configuration': self.configuration, 'scope': 'global'})
        self.assertEqual(denied.status_code, 422)
        invalid = await self.client.post(self.base, json={'name': {'secret': self.secret}, 'configuration': self.configuration})
        self.assertEqual(invalid.status_code, 422)
        self.assertNotIn(self.secret, invalid.text)
        leaked_name = await self.client.post(self.base, json={'name': self.secret, 'configuration': self.configuration})
        self.assertEqual(leaked_name.status_code, 422)
        self.assertNotIn(self.secret, leaked_name.text)
        public_search = await self.client.post(self.base, json={'name': 'CODEX检索', 'configuration': 'https://example.com/search?keyword=合同&monkey=value'})
        self.assertEqual(public_search.status_code, 200, public_search.text)

    async def test_probe_redacts_echo_and_private_network_rejection(self):
        state = await self.create()
        url = self.base + '/' + state['id']
        result = {'status': 'verified', 'error': '', 'servers': [{'name': 'default', 'server_name': self.secret,
                  'server_version': '1', 'tool_count': 1, 'tools': [{'name': 'tool', 'description': self.secret}]}]}
        with patch('app.areas.capability_market.personal_mcp_routes.verify_configuration', new=AsyncMock(return_value=result)):
            response = await self.client.post(url + '/verify', json={'revision': state['revision']})
        self.assertTrue(response.json()['ok'])
        self.assertNotIn(self.secret, response.text)
        self.assertTrue(response.json()['configuration']['capabilities']['tool_call'])
        private = deepcopy(self.configuration)
        private['mcp.json']['mcpServers']['default']['url'] = 'https://127.0.0.1/mcp'
        saved = await self.client.put(url, json={'name': state['name'], 'configuration': private, 'revision': state['revision']})
        self.assertEqual(saved.status_code, 200, saved.text)
        denied = await self.client.post(url + '/verify', json={'revision': saved.json()['revision']})
        self.assertFalse(denied.json()['ok'])
        self.assertEqual(denied.json()['configuration']['status'], 'failed')
        self.assertNotIn(self.secret, denied.text)
        async with self.sessions() as db:
            row = (await db.scalars(select(SystemConfig))).one()
            self.assertNotIn(self.secret, json.dumps(row.value))

    async def test_secret_routes_excluded_and_chat_blocked_before_persistence(self):
        from app.areas.personal_agent.mcp_credentials import reject_mcp_chat_credentials
        reject_mcp_chat_credentials('https://example.com/search?keyword=合同&monkey=value')
        reject_mcp_chat_credentials('解释一下 {"headers":{"Accept":"application/json"},"env":{"MODE":"dev"}}')
        routes = [route for route in self.app.routes if isinstance(route, APIRoute) and self.base in route.path]
        self.assertEqual(len(routes), 6)
        self.assertTrue(all(exclusion_reasons(route) for route in routes))
        for content in ['连接MCP token=' + self.secret,
                        'https://example.com/mcp?api_key=' + self.secret]:
            with patch('app.areas.personal_agent.router.personal_identity', new=AsyncMock()) as identity:
                response = await self.client.post('/api/v1/personal-agent/messages', json={'content': content})
                self.assertEqual(response.status_code, 422, response.text)
                identity.assert_not_awaited()
                self.assertNotIn(self.secret, response.text)
        from fastapi import HTTPException
        with self.assertRaises(HTTPException):
            reject_credentials({'api_key': self.secret})

    async def test_chat_configures_supplied_secret_without_model_or_confirmation_card(self):
        from app.areas.personal_agent.mcp_chat_input import extract_chat_connection
        from app.areas.personal_agent.mcp_chat_connection import configure_chat_connection
        submission = extract_chat_connection(json.dumps(self.configuration))
        self.assertNotIn(self.secret, repr(submission))
        self.assertNotIn(self.secret, submission.message())
        for content in ['连接MCP 名称：CODEX https://example.com/mcp Bearer ' + self.secret,
                        '连接MCP https://example.com/mcp API Key: ' + self.secret]:
            parsed = extract_chat_connection(content)
            self.assertEqual(parsed.credential.get_secret_value(), self.secret)
            self.assertNotIn(self.secret, parsed.message())
        state = {'conversation_id': 'CODEX-CONNECT-IN-CHAT', 'messages': [], 'pending_actions': []}
        snapshots = []

        async def capture(owner, value):
            snapshots.append(deepcopy(value))

        async with self.sessions() as db, AsyncExitStack() as stack:
            identity, context = stack.enter_context(self.sdk_transport())
            with patch('app.areas.personal_agent.mcp_chat_connection.authenticated_identity', AsyncMock(return_value=identity)), \
                 patch('app.areas.personal_agent.service._save_state', side_effect=capture):
                result = await configure_chat_connection(submission, identity, db, state, AsyncMock(), AsyncMock())
            self.assertEqual(result['state']['messages'][-1]['connection_result']['status'], 'verified')
            self.assertEqual(state['pending_actions'], [])
            self.assertEqual([call['method'] for call in self.sdk_calls].count('initialize'), 1)
            self.assertEqual([call['method'] for call in self.sdk_calls].count('tools/list'), 1)
            self.assertFalse(any(call['method'] == 'tools/call' for call in self.sdk_calls))
            self.assertNotIn(self.secret, json.dumps(snapshots))
            record = (await db.scalars(select(SystemConfig))).one()
            self.assertNotIn(self.secret, json.dumps(record.value))
            self.assertEqual(decrypt(record), self.configuration)

    async def test_sdk_tools_call_only_after_confirmation_and_result_visible_in_current_dialog(self):
        from app.areas.personal_agent.mcp_tools import PersonalMcpToolSession
        from app.areas.personal_agent.confirmation_history import prepare_personal_action, project_personal_actions
        from app.areas.personal_agent.service import _decide_action, _prompt_history
        state = await self.create()
        async with self.sessions() as db, AsyncExitStack() as stack:
            identity, context = stack.enter_context(self.sdk_transport())
            tools = PersonalMcpToolSession(identity, db, conversation_id='CODEX-MCP-CONVERSATION')
            with patch('app.areas.capability_market.personal_mcp.decrypt', side_effect=AssertionError('组发现不得解密配置')):
                groups = await tools.execute('personal_mcp_list_groups', {})
            self.assertEqual(groups['groups'][0]['name'], state['name'])
            discovered = await tools.execute('personal_mcp_search_tools', {'group_id': state['scope'] + ':' + state['id']})
            self.assertIn('tools', discovered, discovered)
            tool = discovered['tools'][0]
            prepared = await tools.execute('personal_mcp_call_tool', {'tool_id': tool['tool_id'], 'arguments': {'query': 'CODEX'}})
            self.assertEqual(prepared['result']['status'], 'pending')
            self.assertFalse(any(call['method'] == 'tools/call' for call in self.sdk_calls))
            self.assertIn(state['name'], prepared['result']['summary'])
            self.assertIn('发送到该外部服务', prepared['result']['summary'])
            action = {**tools.pending_actions[0], 'id': str(uuid4()), 'status': 'pending', 'requested_by': identity['username']}
            conversation = {'conversation_id': 'CODEX-MCP-CONVERSATION', 'conversation_title': 'CODEX确认',
                            'messages': [], 'pending_actions': [action]}
            await prepare_personal_action(action, identity, conversation, db)
            await db.commit()
            context.scope['path'] = '/api/v1/personal-agent/actions/' + action['id'] + '/decision'
            with patch('app.areas.personal_agent.service._save_state', new=AsyncMock()):
                outcome = await _decide_action(identity, db, action['id'], 'approved', '', conversation)
            self.assertEqual(outcome['status'], 'approved')
            self.assertEqual(len([call for call in self.sdk_calls if call['method'] == 'tools/call']), 1)
            self.assertNotIn(self.secret, json.dumps(outcome, ensure_ascii=False))
            followup = {**conversation, 'messages': [*conversation['messages'], {'role': 'user', 'content': '解释刚才的结果'}]}
            self.assertIn('CODEX远程真实协议返回', json.dumps(_prompt_history(followup), ensure_ascii=False))
            self.assertNotIn('系统数据已更新', conversation['messages'][-1]['content'])
            self.assertEqual((await project_personal_actions(conversation, identity, db))['pending_actions'], [])
            archived = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == 'personal_agent_action'))).one()
            self.assertEqual(archived.status, '已执行')
            self.assertNotIn(self.secret, json.dumps(archived.data, ensure_ascii=False))

    async def test_large_sse_pdf_becomes_workspace_file_without_binary_chat_history(self):
        import base64
        import hashlib
        from app.areas.personal_agent.mcp_tools import PersonalMcpToolSession
        from app.areas.personal_agent.confirmation_history import prepare_personal_action
        from app.areas.personal_agent.service import _decide_action

        state = await self.create()
        pdf = b'%PDF-1.7\n' + b'0' * (2 * 1024 * 1024) + b'\n%%EOF'
        encoded = base64.b64encode(pdf).decode()
        for workspace in ({'kind': 'personal'}, {'kind': 'case', 'case_id': 789}):
            async with self.sessions() as db, AsyncExitStack() as stack:
                identity, context = stack.enter_context(self.sdk_transport())
                tools = PersonalMcpToolSession(identity, db, conversation_id='CODEX-MCP-CONVERSATION')
                await tools.execute('personal_mcp_list_groups', {})
                found = await tools.execute('personal_mcp_search_tools', {'group_id': state['scope'] + ':' + state['id']})
                await tools.execute('personal_mcp_call_tool', {'tool_id': found['tools'][0]['tool_id'], 'arguments': {'query': 'CODEX'}})
                action = {**tools.pending_actions[0], 'id': str(uuid4()), 'status': 'pending', 'requested_by': identity['username']}
                conversation = {'conversation_id': 'CODEX-MCP-CONVERSATION', 'conversation_title': 'CODEX文件确认',
                                'workspace': workspace, 'messages': [], 'pending_actions': [action]}
                await prepare_personal_action(action, identity, conversation, db)
                await db.commit()
                context.scope['path'] = '/api/v1/personal-agent/actions/' + action['id'] + '/decision'
                self.sdk_sse = True
                self.sdk_result = {'content': [{'type': 'resource', 'resource': {
                    'uri': 'file:///external/patent.pdf', 'mimeType': 'application/pdf', 'blob': encoded}}], 'isError': False}
                file_id = uuid4().hex
                saved = AsyncMock(return_value={'file': {'id': file_id, 'attachment_id': 987,
                    'name': 'lookup-1.pdf', 'content_type': 'application/pdf', 'size': len(pdf),
                    'sha256': hashlib.sha256(pdf).hexdigest()}})
                case = object() if workspace['kind'] == 'case' else None
                scope = AsyncMock(return_value=case)
                stack.enter_context(patch('app.areas.personal_agent.service._save_state', new=AsyncMock()))
                stack.enter_context(patch('app.areas.personal_agent.service._user_dir', return_value=Path('CODEX-isolated')))
                stack.enter_context(patch('app.areas.personal_agent.conversations.get_conversation_state', new=AsyncMock(return_value=conversation)))
                stack.enter_context(patch('app.areas.personal_agent.project_workspaces.require_workspace_access', new=scope))
                stack.enter_context(patch('app.areas.capability_market.remote_files.save_generated_file', new=saved))
                outcome = await _decide_action(identity, db, action['id'], 'approved', '', conversation)
                self.assertEqual(outcome['status'], 'approved')
                self.assertEqual(len([call for call in self.sdk_calls if call['method'] == 'tools/call']), 1)
                saved.assert_awaited_once()
                self.assertEqual(saved.await_args.kwargs['content'], pdf)
                self.assertIs(saved.await_args.kwargs['case_record'], case)
                self.assertEqual(saved.await_args.kwargs['source_request_id'], action['id'])
                scope.assert_awaited_once_with(workspace, identity, db)
                self.assertLess(len(json.dumps(outcome)), 10000)
                self.assertNotIn(encoded, json.dumps(conversation))
                self.assertEqual(conversation['messages'][-1]['tool_result']['files'][0]['file_id'], file_id)
                archived = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == 'PA-' + action['id']))
                self.assertEqual(archived.status, '已执行')

    async def test_file_encoding_metadata_limits_and_protocol_errors_are_explicit(self):
        import base64
        from fastapi import HTTPException
        from mcp.types import CallToolResult
        from mcp.shared.exceptions import MCPError
        from app.areas.capability_market.remote_files import store_remote_files
        from app.areas.capability_market.remote_session import remote_error

        async with self.sessions() as db:
            with self.sdk_transport() as (identity, context), patch('app.areas.capability_market.remote_files.save_generated_file', new=AsyncMock()) as save:
                for blob in ('not base64!', base64.b64encode(b'<html>not PDF</html>').decode()):
                    result = CallToolResult.model_validate({'content': [{'type': 'resource', 'resource': {
                        'uri': 'file:///external/patent.pdf', 'mimeType': 'application/pdf', 'blob': blob}}]})
                    with self.assertRaises(HTTPException):
                        await store_remote_files(result, self.configuration, identity, db,
                            tool_name='lookup', conversation_id='CODEX-MCP-CONVERSATION', action_id='CODEX-invalid')
                result = CallToolResult.model_validate({'content': [{'type': 'text', 'text': 'x' * 65537}]})
                with self.assertRaises(HTTPException):
                    await store_remote_files(result, self.configuration, identity, db,
                        tool_name='lookup', conversation_id='CODEX-MCP-CONVERSATION', action_id='CODEX-oversize')
                save.assert_not_awaited()
                detail = remote_error(MCPError(-32000, 'SSE stream failed ' + self.secret), 'tools/call',
                                      self.configuration['mcp.json']['mcpServers']['default'])
                self.assertIn('tools/call', detail)
                self.assertIn('-32000', detail)
                self.assertNotIn(self.secret, detail)

    async def test_runtime_schema_ref_invalid_arguments_revision_and_schema_changes_block_call(self):
        from fastapi import HTTPException
        from app.areas.personal_agent.mcp_tools import PersonalMcpToolSession
        from app.areas.capability_market.remote_schema import checked_schema
        from app.areas.capability_market.remote_tools import execute_call
        from app.areas.personal_agent.confirmation_history import prepare_personal_action, begin_personal_decision
        for reference in ['http://127.0.0.1/private', 'file:///private', '//example.com/schema', '#named']:
            with self.assertRaises(HTTPException):
                checked_schema({'type': 'object', 'properties': {'query': {'$ref': reference}}})
        checked_schema({'type': 'object', '$defs': {'query': {'type': 'string'}}, 'properties': {'query': {'$ref': '#/$defs/query'}}})
        for schema in [
            {'type': 'object', '$schema': 'https://example.com/unknown-schema'},
            {'type': 'object', 'properties': {'query': {'type': 'string', 'pattern': '^(a+)+$'}}},
            {'type': 'object', 'patternProperties': {'^(a+)+$': {'type': 'string'}}},
            {'type': 'object', '$ref': '#'},
        ]:
            with self.assertRaises(HTTPException):
                checked_schema(schema)
        state = await self.create()
        async with self.sessions() as db, AsyncExitStack() as stack:
            identity, context = stack.enter_context(self.sdk_transport())
            tools = PersonalMcpToolSession(identity, db, conversation_id='CODEX-MCP-CONVERSATION')
            await tools.execute('personal_mcp_list_groups', {})
            found = await tools.execute('personal_mcp_search_tools', {'group_id': state['scope'] + ':' + state['id']})
            descriptor = found['tools'][0]
            bad = await tools.execute('personal_mcp_call_tool', {'tool_id': descriptor['tool_id'], 'arguments': {'query': 5}})
            self.assertTrue(bad['isError'])
            await tools.execute('personal_mcp_call_tool', {'tool_id': descriptor['tool_id'], 'arguments': {'query': 'CODEX'}})
            action = {**tools.pending_actions[0], 'id': str(uuid4()), 'status': 'pending', 'requested_by': identity['username']}
            conversation = {'conversation_id': 'CODEX-MCP-CONVERSATION', 'conversation_title': 'CODEX确认'}
            await prepare_personal_action(action, identity, conversation, db)
            await db.commit()
            with self.assertRaises(HTTPException):
                await execute_call(action['payload'], identity, db, action_id=action['id'])
            context.scope['path'] = '/api/v1/personal-agent/actions/' + action['id'] + '/decision'
            await begin_personal_decision(action, 'approved', '', identity, conversation, db)
            self.sdk_schema['properties']['query']['maxLength'] = 2
            with self.assertRaises(HTTPException):
                await execute_call(action['payload'], identity, db, action_id=action['id'])
            self.assertFalse(any(call['method'] == 'tools/call' for call in self.sdk_calls))
            with self.assertRaises(HTTPException):
                await begin_personal_decision(action, 'approved', '', identity, conversation, db)
            await db.rollback()
        saved = await self.client.put(self.base + '/' + state['id'], json={'name': state['name'],
                                     'configuration': self.configuration, 'revision': state['revision']})
        self.assertEqual(saved.status_code, 200)
        async with self.sessions() as db, AsyncExitStack() as stack:
            identity, context = stack.enter_context(self.sdk_transport())
            from app.areas.capability_market.remote_tools import current_configuration
            with self.assertRaises(HTTPException) as changed:
                await current_configuration(state['id'], state['revision'], identity, db, scope='personal')
            self.assertEqual(changed.exception.status_code, 409)

    async def test_runtime_schema_secret_echo_logs_and_service_direct_credential_guard(self):
        from fastapi import HTTPException
        from app.areas.personal_agent.mcp_tools import PersonalMcpToolSession
        from app.areas.personal_agent.service import generate_response
        from app.areas.capability_market.remote_logging import safe_sdk_logs
        import logging
        with self.assertLogs('mcp.client.streamable_http', level='DEBUG') as captured:
            with safe_sdk_logs():
                logging.getLogger('mcp.client.streamable_http').error('raw header %s', self.secret)
        self.assertNotIn(self.secret, str(captured.output))
        with self.assertLogs('mcp.review', level='DEBUG') as dynamic:
            with safe_sdk_logs():
                logging.getLogger('mcp.review.' + uuid4().hex).warning('raw dynamic credential %s', self.secret)
        self.assertNotIn(self.secret, str(dynamic.output))
        state = await self.create()
        async with self.sessions() as db, AsyncExitStack() as stack:
            identity, context = stack.enter_context(self.sdk_transport())
            tools = PersonalMcpToolSession(identity, db, conversation_id='CODEX-MCP-CONVERSATION')
            await tools.execute('personal_mcp_list_groups', {})
            self.sdk_schema['properties'][self.secret] = {'type': 'string'}
            result = await tools.execute('personal_mcp_search_tools', {'group_id': state['scope'] + ':' + state['id']})
            self.assertTrue(result['isError'])
            self.assertNotIn(self.secret, json.dumps(result))
            with patch('app.areas.personal_agent.service._user_dir') as directory:
                with self.assertRaises(HTTPException):
                    await generate_response(identity, db, '连接MCP https://example.com/mcp?api_key=' + self.secret, AsyncMock())
                directory.assert_not_called()

    async def test_schema_keyword_names_are_data_but_real_constraints_remain_rejected(self):
        from fastapi import HTTPException
        from app.areas.capability_market.remote_schema import checked_schema, validate_arguments
        schema = {'type': 'object', '$defs': {'pattern': {'type': 'string'}, '$ref': {'type': 'string'}},
                  'definitions': {'patternProperties': {'type': 'string'}, '$id': {'type': 'string'}},
                  'properties': {'pattern': {'$ref': '#/$defs/pattern'},
                                 'patternProperties': {'$ref': '#/definitions/patternProperties'},
                                 '$id': {'$ref': '#/definitions/$id'}, '$ref': {'$ref': '#/$defs/$ref'}},
                  'required': ['pattern'], 'additionalProperties': False,
                  'default': {'$ref': 'http://127.0.0.1/not-a-reference', 'pattern': '普通数据', '$id': '普通编号'},
                  'examples': [{'$ref': 'file:///not-a-reference', 'patternProperties': {'example': '普通数据'}}]}
        original = deepcopy(schema)
        validate_arguments(schema, {'pattern': 'CODEX', 'patternProperties': '普通参数', '$id': '编号', '$ref': '引用名'})
        self.assertEqual(schema, original)
        for restricted in [
            {'type': 'object', 'pattern': '^(a+)+$'},
            {'type': 'object', '$defs': {'pattern': {'type': 'string', 'pattern': '^(a+)+$'}}},
            {'type': 'object', 'properties': {'pattern': {'type': 'string', 'pattern': '^(a+)+$'}}},
            {'type': 'object', '$defs': {'pattern': {'$id': 'https://example.com/schema'}}},
            {'type': 'object', 'properties': {'pattern': {'$ref': '#/custom'}}, 'custom': {'$ref': 'http://127.0.0.1/schema'}},
        ]:
            with self.assertRaises(HTTPException):
                checked_schema(restricted)

    async def test_public_metadata_rejects_credential_echo_after_preservation(self):
        for location in ('server_name', 'url', 'authUrl', 'header_name'):
            configuration = deepcopy(self.configuration)
            servers = configuration['mcp.json']['mcpServers']
            server = servers['default']
            if location == 'server_name':
                servers[self.secret] = servers.pop('default')
            elif location == 'header_name':
                server['headers'][self.secret] = 'CODEX-other-credential'
            else:
                server[location] = 'https://example.com/' + self.secret
            response = await self.client.post(self.base, json={'name': 'CODEX安全名称', 'configuration': configuration})
            self.assertEqual(response.status_code, 422, response.text)
            self.assertNotIn(self.secret, response.text)
        state = await self.create()
        configuration = deepcopy(state['configuration'])
        configuration['mcp.json']['mcpServers']['default']['url'] = 'https://example.com/' + self.secret
        response = await self.client.put(self.base + '/' + state['id'], json={
            'name': 'CODEX安全名称', 'configuration': configuration, 'revision': state['revision'],
            'keep_credentials': [['mcp.json', 'mcpServers', 'default', 'headers', 'Authorization']],
        })
        self.assertEqual(response.status_code, 422)
        self.assertNotIn(self.secret, response.text)
        current = await self.client.get(self.base + '/' + state['id'])
        self.assertEqual(current.json()['revision'], state['revision'])

    async def test_outbound_oa_bearer_is_rejected_before_any_network(self):
        from fastapi import HTTPException
        from app.areas.capability_market.remote_session import remote_session
        with self.sdk_transport() as (identity, context):
            for location in ('header', 'url', 'encoded_url'):
                server = deepcopy(self.configuration['mcp.json']['mcpServers']['default'])
                if location == 'header':
                    server['headers']['Authorization'] = 'Bearer ' + context.bearer
                elif location == 'url':
                    server['url'] = 'https://example.com/' + context.bearer
                else:
                    server['url'] = 'https://example.com/' + ''.join('%%%02X' % ord(char) for char in context.bearer)
                with patch('app.areas.capability_market.remote_session.OriginBoundTransport') as network:
                    with self.assertRaises(HTTPException) as blocked:
                        async with remote_session(server):
                            self.fail('OA令牌不应进入远程会话')
                    self.assertEqual(blocked.exception.status_code, 422)
                    self.assertNotIn(context.bearer, str(blocked.exception.detail))
                    network.assert_not_called()
                self.assertEqual(self.sdk_calls, [])

    async def test_failed_and_timeout_confirmation_cannot_replay(self):
        from fastapi import HTTPException
        from app.areas.personal_agent.mcp_tools import PersonalMcpToolSession
        from app.areas.personal_agent.confirmation_history import prepare_personal_action
        from app.areas.personal_agent.service import _decide_action
        state = await self.create()
        for mode in ('upstream_error', 'timeout'):
            async with self.sessions() as db, AsyncExitStack() as stack:
                identity, context = stack.enter_context(self.sdk_transport())
                tools = PersonalMcpToolSession(identity, db, conversation_id='CODEX-MCP-CONVERSATION')
                await tools.execute('personal_mcp_list_groups', {})
                found = await tools.execute('personal_mcp_search_tools', {'group_id': state['scope'] + ':' + state['id']})
                await tools.execute('personal_mcp_call_tool', {'tool_id': found['tools'][0]['tool_id'], 'arguments': {'query': 'CODEX'}})
                action = {**tools.pending_actions[0], 'id': str(uuid4()), 'status': 'pending', 'requested_by': identity['username']}
                conversation = {'conversation_id': 'CODEX-MCP-CONVERSATION', 'conversation_title': 'CODEX确认',
                                'messages': [], 'pending_actions': [action]}
                await prepare_personal_action(action, identity, conversation, db)
                await db.commit()
                context.scope['path'] = '/api/v1/personal-agent/actions/' + action['id'] + '/decision'
                stack.enter_context(patch('app.areas.personal_agent.service._save_state', new=AsyncMock()))
                if mode == 'timeout':
                    stack.enter_context(patch('app.areas.personal_agent.service._execute_personal_action', new=AsyncMock(side_effect=TimeoutError())))
                else:
                    self.sdk_result['isError'] = True
                with self.assertRaises((HTTPException, TimeoutError)):
                    await _decide_action(identity, db, action['id'], 'approved', '', conversation)
                row = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == 'PA-' + action['id']))
                self.assertEqual(row.status, '执行失败')
                calls = len([call for call in self.sdk_calls if call['method'] == 'tools/call'])
                with self.assertRaises(HTTPException):
                    await _decide_action(identity, db, action['id'], 'approved', '', conversation)
                self.assertEqual(len([call for call in self.sdk_calls if call['method'] == 'tools/call']), calls)


if __name__ == "__main__":
    unittest.main()
