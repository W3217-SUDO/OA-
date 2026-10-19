"""自定义MCP的管理授权与运行可见性分离，运行摘要不解密凭据。"""
import re

from fastapi import HTTPException
from sqlalchemy import and_, or_, select

from app.agent_permissions import can_manage_agent_settings, is_actual_system_admin
from app.models import SystemConfig
from .connector_store import CONNECTOR_CONFIG_PREFIX, connector_config_key, stored
from .personal_mcp import ID_PATTERN, SOURCE


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
    return record


async def connection_records(identity, db, *, management):
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
    return [record for record in records if matches_connection(record, identity)]


async def runtime_connection_groups(identity, db):
    can_manage_global = can_manage_agent_settings(identity)
    return [{'id': record.value['item_id'], 'name': record.value['display_name'],
             'scope': record.value['scope'], 'revision': record.value['revision'], 'status': record.value['status'],
             'can_manage': record.value['scope'] == 'personal' or can_manage_global}
            for record in await connection_records(identity, db, management=False)]
