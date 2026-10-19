"""自定义MCP连接管理专用接口，全局运行摘要不含配置或凭据。"""
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.security import current_identity
from app.agent_permissions import can_manage_agent_settings
from .remote_session import verify_personal_configuration as verify_configuration
from .connector_store import decrypt, save_configuration, save_verification
from .personal_mcp import ID_PATTERN, item_for, normalize_configuration, personal_state, redact_verification
from .mcp_access import connection_records, default_connection_scope, require_managed_connection, runtime_connection_groups

router = APIRouter(prefix='/personal-mcp')
Identifier = Annotated[str, Path(pattern=ID_PATTERN)]
Scope = Literal['personal', 'global']


class PersonalMcpInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=80, pattern=r'^[^\x00-\x1f\x7f]+$')
    configuration: dict | str


class PersonalMcpUpdate(PersonalMcpInput):
    revision: str = Field(pattern=r'^[a-f0-9]{32}$')
    keep_credentials: list[list[str]] = Field(default_factory=list, max_length=384)


class RevisionInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: str = Field(pattern=r'^[a-f0-9]{32}$')


@router.get('')
async def list_connections(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    return {'items': [personal_state(record) for record in await connection_records(identity, db, management=True)],
            'available_connections': await runtime_connection_groups(identity, db),
            'default_scope': default_connection_scope(identity), 'can_manage_global': can_manage_agent_settings(identity)}


@router.post('')
async def create_connection(body: PersonalMcpInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    configuration = normalize_configuration(body.configuration)
    item = item_for('personal-mcp-' + uuid4().hex, body.name)
    scope = default_connection_scope(identity)
    record = await save_configuration(item, scope, identity, db, configuration, [], '')
    return personal_state(record)


@router.get('/{identifier}')
async def read_connection(identifier: Identifier, scope: Scope = 'personal', identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    return personal_state(await require_managed_connection(identifier, scope, identity, db))


@router.put('/{identifier}')
async def update_connection(identifier: Identifier, body: PersonalMcpUpdate, scope: Scope = 'personal', identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    await require_managed_connection(identifier, scope, identity, db, lock=True)
    configuration = normalize_configuration(body.configuration)
    record = await save_configuration(item_for(identifier, body.name), scope, identity, db,
                                      configuration, body.keep_credentials, body.revision)
    return personal_state(record)


@router.post('/{identifier}/verify')
async def verify_connection(identifier: Identifier, body: RevisionInput, scope: Scope = 'personal', identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    record = await require_managed_connection(identifier, scope, identity, db)
    if record.value['revision'] != body.revision:
        raise HTTPException(409, '连接配置已被修改，请刷新后验证')
    item = item_for(identifier, record.value['display_name'])
    configuration = decrypt(record)
    await db.rollback()
    result = redact_verification(await verify_configuration(configuration), configuration)
    record = await save_verification(item, scope, identity, db, body.revision, result)
    return {'ok': result['status'] == 'verified', 'configuration': personal_state(record)}


@router.delete('/{identifier}')
async def delete_connection(identifier: Identifier, revision: Annotated[str, Query(pattern=r'^[a-f0-9]{32}$')],
                            scope: Scope = 'personal', identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    record = await require_managed_connection(identifier, scope, identity, db, lock=True)
    if record.value['revision'] != revision:
        raise HTTPException(409, '连接配置已被修改，请刷新后删除')
    from app.core.system import _system_audit
    try:
        await db.delete(record)
        await _system_audit(db, identity, '删除MCP连接', 'MCP连接', {'item_id': identifier, 'scope': scope})
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return {'id': identifier, 'scope': scope, 'deleted': True}
