"""自定义MCP的管理授权与运行可见性分离，运行摘要不解密凭据。"""
import re

from fastapi import HTTPException
from sqlalchemy import and_, or_, select

from app.agent_permissions import can_manage_agent_settings, is_actual_system_admin
from app.models import SystemConfig
from .connector_store import CONNECTOR_CONFIG_PREFIX, connector_config_key, stored
from .personal_mcp import ID_PATTERN, SOURCE, service_summaries


def default_connection_scope(identity):
    return 'global' if is_actual_system_admin(identity) else 'personal'


def bound_scope(scope):
    if scope not in ('personal', 'global'):
        raise HTTPException(409, 'MCP连接范围缺失或无效，请重新发现工具并确认')
    return scope


def matches_connection(record, identity):
    value = record.value
    scope = value.get('scope')
    if scope not in ('personal', 'global'):
        return False
    owner = 'global' if scope == 'global' else identity['username']
    identifier = value.get('item_id')
    return (value.get('schema_version') == 1 and value.get('owner') == owner and value.get('source') == SOURCE
            and isinstance(identifier, str) and re.fullmatch(ID_PATTERN, identifier)
            and record.key == connector_config_key(identifier, scope, owner))


async def require_managed_connection(identifier, scope, identity, db, *, lock=False):
    bound_scope(scope)
    # stored保留owner_for原管理授权；普通运行读取不得经过此入口。
    record = await stored(identifier, scope, identity, db, lock=lock)
    if record is None or not matches_connection(record, identity):
        raise HTTPException(404, 'MCP连接不存在或不属于当前账号')
    return record


async def require_runtime_connection(identifier, scope, identity, db, *, lock=False):
    bound_scope(scope)
    owner = 'global' if scope == 'global' else identity['username']
    query = select(SystemConfig).where(
        SystemConfig.key == connector_config_key(identifier, scope, owner),
        SystemConfig.value['scope'].as_string() == scope,
        SystemConfig.value['owner'].as_string() == owner,
        SystemConfig.value['source'].as_string() == SOURCE,
    ).execution_options(populate_existing=True)
    record = await db.scalar(query.with_for_update() if lock else query)
    if record is None or not matches_connection(record, identity):
        raise HTTPException(404, 'MCP连接不存在或不在当前运行范围')
    if not enabled(record):
        raise HTTPException(409, '此MCP连接已停用，请在连接列表中启用后再使用')
    return record


def enabled(record):
    return (record.value or {}).get('enabled', True) is not False


async def connection_records(identity, db, *, management, include_disabled=None):
    # 停用的连接只在管理列表出现，运行（智能体发现、目录、调用）不再使用。
    if include_disabled is None:
        include_disabled = management
    scopes = [and_(SystemConfig.value['scope'].as_string() == 'personal',
                   SystemConfig.value['owner'].as_string() == identity['username'])]
    if not management or can_manage_agent_settings(identity):
        scopes.append(and_(SystemConfig.value['scope'].as_string() == 'global',
                           SystemConfig.value['owner'].as_string() == 'global'))
    records = (await db.scalars(select(SystemConfig).where(
        SystemConfig.key.startswith(CONNECTOR_CONFIG_PREFIX),
        SystemConfig.value['source'].as_string() == SOURCE,
        or_(*scopes),
    ).execution_options(populate_existing=True))).all()
    return [record for record in records if matches_connection(record, identity) and (include_disabled or enabled(record))]


async def runtime_connection_groups(identity, db, *, include_disabled=False):
    can_manage_global = can_manage_agent_settings(identity)
    return [{'id': record.value['item_id'], 'name': record.value['display_name'],
             'scope': record.value['scope'], 'revision': record.value['revision'], 'status': record.value['status'],
             'can_manage': record.value['scope'] == 'personal' or can_manage_global,
             'enabled': enabled(record), 'services': service_summaries(record.value)}
            for record in await connection_records(identity, db, management=False, include_disabled=include_disabled)]


async def runtime_connection_catalog(identity, db, *, limit=20):
    """本轮可用的本人及全局共享MCP连接目录（名称、范围、已验证的工具名和简短说明），给模型知道有哪些外部服务；
    只读已保存的工具摘要，不解密凭据、不连外部服务。"""
    catalog = []
    for record in (await connection_records(identity, db, management=False))[:limit]:
        value = record.value or {}
        entry = {'name': value.get('display_name') or value.get('item_id'), 'scope': value.get('scope'), 'status': value.get('status')}
        services = service_summaries(value, tool_limit=15)
        if len(services) > 1:
            # 分组（如企查查的多个服务）列出全部服务及各自工具名，模型据此判断用哪组；工具说明在搜索工具时再读。
            entry['services'] = [{'name': service['name'], 'tools': service['tools']} for service in services]
        else:
            tools = []
            for server in value.get('servers') or []:
                for tool in (server.get('tools') or [])[:10] if isinstance(server, dict) else []:
                    if isinstance(tool, dict) and tool.get('name'):
                        tools.append({'name': str(tool['name'])[:80], 'description': str(tool.get('description') or '')[:80]})
            entry['tools'] = tools[:10]
        catalog.append(entry)
    return catalog
