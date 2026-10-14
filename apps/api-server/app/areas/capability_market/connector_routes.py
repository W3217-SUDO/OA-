"""人工配置与连接验证接口，模型不能读取凭据或自行连接。"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.security import current_identity
from .catalog import entry
from .connector_format import connector_item
from .connector_probe import verify_configuration
from .connector_store import decrypt, owner_for, public_state, save_configuration, save_verification, stored

router = APIRouter()


class ConnectorInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    scope: Literal['personal', 'global'] = 'personal'
    configuration: dict
    keep_credentials: list[list[str]] = Field(default_factory=list, max_length=384)
    revision: str = Field(default='', max_length=32)


class VerifyInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    scope: Literal['personal', 'global'] = 'personal'
    revision: str = Field(pattern=r'^[a-f0-9]{32}$')


@router.get('/connectors/{item_id}/config')
async def read_connector_config(item_id: str, scope: Literal['personal', 'global'] = 'personal',
                                identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    owner_for(scope, identity)
    item = connector_item(entry(item_id))
    return public_state(item, await stored(item_id, scope, identity, db))


@router.put('/connectors/{item_id}/config')
async def update_connector_config(item_id: str, body: ConnectorInput,
                                  identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    owner_for(body.scope, identity)
    item = connector_item(entry(item_id))
    record = await save_configuration(item, body.scope, identity, db, body.configuration, body.keep_credentials, body.revision)
    return public_state(item, record)


@router.post('/connectors/{item_id}/verify')
async def verify_connector(item_id: str, body: VerifyInput,
                           identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    owner_for(body.scope, identity)
    item = connector_item(entry(item_id))
    record = await stored(item_id, body.scope, identity, db)
    if record is None or record.value['revision'] != body.revision:
        raise HTTPException(409, '请先保存当前连接配置，再测试此版本')
    configuration = decrypt(record)
    # 网络握手期间不占用数据库连接，回写时重新锁定并核对配置版本。
    await db.rollback()
    result = await verify_configuration(configuration)
    record = await save_verification(item, body.scope, identity, db, body.revision, result)
    return {'ok': result['status'] == 'verified', 'configuration': public_state(item, record)}


@router.delete('/connectors/{item_id}/config')
async def delete_connector_config(item_id: str, scope: Literal['personal', 'global'] = 'personal',
                                  revision: str = Query(pattern=r'^[a-f0-9]{32}$'),
                                  identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    owner_for(scope, identity)
    item = connector_item(entry(item_id))
    record = await stored(item_id, scope, identity, db, lock=True)
    if record is None or record.value['revision'] != revision:
        raise HTTPException(409, '连接配置已不存在或已被修改，请刷新')
    from app.core.system import _system_audit
    try:
        await db.delete(record)
        await _system_audit(db, identity, '删除连接器配置', item['name'], {'item_id': item_id, 'scope': scope})
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return public_state(item, None)
