"""多服务 MCP 分组：整组并行检测、个别服务失败不拖垮整组发现、智能体目录列出分组全部服务（只用假 Key）。"""
from contextlib import asynccontextmanager
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.capability_market import remote_session as sessions
from app.areas.capability_market import remote_tools
from app.areas.capability_market.connector_store import connector_config_key
from app.areas.capability_market.mcp_access import runtime_connection_catalog
from app.areas.capability_market.personal_mcp import SOURCE
from app.database import Base
from app.models import SystemConfig

FAKE = 'Bearer CODEX-fake-group-key'


def _configuration(*names):
    return {'mcp.json': {'mcpServers': {name: {'type': 'streamableHttp', 'url': f'https://agent.example.com/mcp/{name}/stream',
                                               'headers': {'Authorization': FAKE}} for name in names}}}


def _fake_session(failing):
    @asynccontextmanager
    async def session(server, **_):
        if any(name in server['url'] for name in failing):
            raise HTTPException(502, '服务返回HTTP401，请先授权或核对请求头中的凭据')
        tool = SimpleNamespace(name='tool_' + server['url'].split('/')[-2], description='假工具', input_schema={'type': 'object', 'properties': {}})
        yield SimpleNamespace(tools=[tool]), SimpleNamespace(server_info=SimpleNamespace(name='s', version='1'))
    return session


async def _tools(session):
    return session.tools


class GroupVerificationTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_services_checked_and_failures_named(self):
        with patch.object(sessions, 'remote_session', _fake_session({'ipr'})), patch.object(sessions, 'session_tools', _tools):
            result = await sessions.verify_personal_configuration(_configuration('company', 'risk', 'ipr'))
        self.assertEqual(result['status'], 'failed')
        self.assertEqual([server['name'] for server in result['servers']], ['company', 'risk', 'ipr'])
        self.assertEqual(result['servers'][0]['tools'][0]['name'], 'tool_company')
        self.assertIn('1/3 个服务检测失败：ipr', result['error'])
        self.assertIn('HTTP401', result['error'])
        with patch.object(sessions, 'remote_session', _fake_session(set())), patch.object(sessions, 'session_tools', _tools):
            result = await sessions.verify_personal_configuration(_configuration('company', 'risk'))
        self.assertEqual(result['status'], 'verified')
        self.assertEqual(sum(server['tool_count'] for server in result['servers']), 2)

    async def test_single_service_failure_keeps_previous_shape(self):
        with patch.object(sessions, 'remote_session', _fake_session({'company'})), patch.object(sessions, 'session_tools', _tools):
            result = await sessions.verify_personal_configuration(_configuration('company'))
        self.assertEqual(result, {'status': 'failed', 'servers': [], 'error': '服务返回HTTP401，请先授权或核对请求头中的凭据'})

    async def test_discovery_skips_unavailable_service_but_fails_when_all_fail(self):
        current = AsyncMock(return_value=('企查查', _configuration('company', 'risk', 'ipr')))
        db = SimpleNamespace(rollback=AsyncMock())
        with patch.object(remote_tools, 'current_configuration', current), patch.object(remote_tools, 'session_tools', _tools), \
                patch.object(remote_tools, 'remote_session', _fake_session({'ipr'})), \
                patch.object(remote_tools, 'get_auth_context', return_value=SimpleNamespace(bearer='CODEX-oa-login')):
            tools = await remote_tools.discover_tools('personal-mcp-' + 'a' * 32, 'r' * 32, {'username': 'u'}, db, scope='personal')
        self.assertEqual([(tool['server_name'], tool['name']) for tool in tools], [('company', 'tool_company'), ('risk', 'tool_risk')])
        self.assertNotIn('CODEX-fake-group-key', repr(tools))
        with patch.object(remote_tools, 'current_configuration', current), patch.object(remote_tools, 'session_tools', _tools), \
                patch.object(remote_tools, 'remote_session', _fake_session({'company', 'risk', 'ipr'})):
            with self.assertRaises(HTTPException):
                await remote_tools.discover_tools('personal-mcp-' + 'a' * 32, 'r' * 32, {'username': 'u'}, db, scope='personal')


class GroupCatalogTests(unittest.IsolatedAsyncioTestCase):
    async def test_catalog_lists_every_service_of_a_group_and_skips_disabled(self):
        engine = create_async_engine('sqlite+aiosqlite:///:memory:', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        def record(item_id, name, services, enabled=True):
            return SystemConfig(key=connector_config_key(item_id, 'global', 'global'), label=name, updated_by='t', value={
                'schema_version': 1, 'item_id': item_id, 'display_name': name, 'scope': 'global', 'owner': 'global', 'source': SOURCE,
                'revision': 'r1', 'status': 'verified', 'encrypted': 'SECRET-TOKEN', 'enabled': enabled, 'service_names': services,
                'servers': [{'name': service, 'tool_count': 1, 'tools': [{'name': 'get_' + service, 'description': 'd'}]} for service in services]})

        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            db.add_all([record('personal-mcp-' + 'a' * 32, '企查查', ['company', 'risk', 'ipr']),
                        record('personal-mcp-' + 'b' * 32, '停用分组', ['x', 'y'], enabled=False)])
            await db.commit()
            catalog = await runtime_connection_catalog({'username': 'alice', 'role': 'user'}, db)
        await engine.dispose()
        self.assertEqual([item['name'] for item in catalog], ['企查查'])
        self.assertEqual(catalog[0]['services'], [{'name': 'company', 'tools': ['get_company']}, {'name': 'risk', 'tools': ['get_risk']},
                                                  {'name': 'ipr', 'tools': ['get_ipr']}])
        self.assertNotIn('SECRET-TOKEN', repr(catalog))


if __name__ == '__main__':
    unittest.main()
