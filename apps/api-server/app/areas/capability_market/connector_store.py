"""按OA身份隔离并加密保存连接配置，不向普通配置接口暴露。"""
import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.agent_permissions import require_agent_settings_management
from app.models import SystemConfig
from .connector_format import configured_secret, configuration_links, path_value, public_configuration, reference_links, secret_paths, set_path, validate_configuration

CONNECTOR_CONFIG_PREFIX = 'agent_connector_'


def owner_for(scope, identity):
    if scope == 'global':
        require_agent_settings_management(identity)
        return 'global'
    return identity['username']


def config_key(item_id, scope, identity):
    owner = owner_for(scope, identity)
    digest = hashlib.sha256(json.dumps([scope, owner, item_id], separators=(',', ':')).encode()).hexdigest()[:40]
    return CONNECTOR_CONFIG_PREFIX + digest


def cipher():
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b'oa.connector.config.v1').derive(settings.secret_key.encode())
    return Fernet(base64.urlsafe_b64encode(key))


def decrypt(record):
    try:
        return json.loads(cipher().decrypt(record.value['encrypted'].encode()))
    except (InvalidToken, ValueError, KeyError) as exc:
        raise HTTPException(409, '连接配置解密失败，请由管理员核对系统密钥和原配置') from exc


async def stored(item_id, scope, identity, db, *, lock=False):
    query = select(SystemConfig).where(SystemConfig.key == config_key(item_id, scope, identity))
    record = await db.scalar(query.with_for_update().execution_options(populate_existing=True) if lock else query)
    if record is not None:
        value = record.value
        if value.get('schema_version') != 1 or value.get('scope') != scope or value.get('owner') != owner_for(scope, identity) or value.get('item_id') != item_id:
            raise HTTPException(409, '连接配置归属或结构不一致')
    return record


def public_state(item, record):
    value = record.value if record else {}
    configuration = decrypt(record) if record else deepcopy(item['connection_configs'])
    config, fields = public_configuration(configuration)
    links = configuration_links(config)
    existing_urls = {link['url'] for link in links}
    links.extend(link for link in reference_links(item) if link['url'] not in existing_urls)
    return {'configuration': config, 'secret_fields': fields, 'links': links,
            'revision': value.get('revision', ''), 'status': value.get('status', 'unconfigured'),
            'last_checked': value.get('last_checked'), 'error': value.get('error', ''),
            'servers': value.get('servers', []), 'saved': record is not None}


async def persist(record, item, scope, identity, db, value, action):
    from app.core.system import _system_audit
    try:
        if record is None:
            record = SystemConfig(key=config_key(item['id'], scope, identity), label=item['name'] + '连接配置', group='智能体连接器', description='仅连接器专用接口可管理')
            db.add(record)
        record.value = value
        record.updated_by = identity['username']
        await _system_audit(db, identity, action, item['name'], {'item_id': item['id'], 'scope': scope, 'status': value['status']})
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, '此连接配置刚被其他请求创建，请刷新后重试') from exc
    except Exception:
        await db.rollback()
        raise
    return record


async def save_configuration(item, scope, identity, db, configuration, keep_credentials, revision):
    record = await stored(item['id'], scope, identity, db, lock=True)
    if (record.value['revision'] if record else '') != revision:
        raise HTTPException(409, '连接配置已被修改，请重新载入后保存')
    config = validate_configuration(configuration, item)
    if keep_credentials:
        previous = decrypt(record) if record else None
        allowed = secret_paths(config)
        if previous is None or any(path not in allowed or path not in secret_paths(previous) for path in keep_credentials):
            raise HTTPException(422, '保留凭据的字段不存在或不属于本连接器')
        for path in keep_credentials:
            if path_value(config, path):
                raise HTTPException(422, '同一凭据字段不能同时保留原值并提交新值')
            set_path(config, path, path_value(previous, path))
    if item['source'] == 'personal-mcp':
        credentials = {path_value(config, path) for path in secret_paths(config) if configured_secret(path_value(config, path))}
        credentials.update(value[7:] for value in list(credentials) if value.lower().startswith('bearer ') and value[7:])
        public_config, fields = public_configuration(config)

        def contains_credential(value):
            if isinstance(value, str):
                return any(credential in value for credential in credentials)
            if isinstance(value, dict):
                return any(contains_credential(key) or contains_credential(child) for key, child in value.items())
            if isinstance(value, list):
                return any(contains_credential(child) for child in value)
            return False

        if contains_credential([item['name'], public_config, fields]):
            raise HTTPException(422, '个人MCP名称或公开配置不能包含已配置的凭据')
    value = {'schema_version': 1, 'scope': scope, 'owner': owner_for(scope, identity), 'item_id': item['id'],
             'source': item['source'], 'revision': uuid4().hex, 'status': 'configured', 'servers': [], 'error': '',
             'last_checked': None, 'encrypted': cipher().encrypt(json.dumps(config, ensure_ascii=False).encode()).decode()}
    if item['source'] == 'personal-mcp':
        value['display_name'] = item['name']
    return await persist(record, item, scope, identity, db, value, '保存连接器配置')


async def save_verification(item, scope, identity, db, revision, result):
    record = await stored(item['id'], scope, identity, db, lock=True)
    if record is None or record.value['revision'] != revision:
        raise HTTPException(409, '连接验证期间配置已改变，请对当前版本重新测试')
    value = {**record.value, **result, 'last_checked': datetime.now(timezone.utc).isoformat()}
    return await persist(record, item, scope, identity, db, value, '验证连接器')


async def connection_states(scope, identity, db):
    owner = 'global' if scope == 'global' else identity['username']
    records = (await db.scalars(select(SystemConfig).where(
        SystemConfig.key.startswith(CONNECTOR_CONFIG_PREFIX),
        SystemConfig.value['scope'].as_string() == scope,
        SystemConfig.value['owner'].as_string() == owner,
    ))).all()
    return {record.value['item_id']: {'status': record.value['status'], 'saved': True}
            for record in records if record.value.get('scope') == scope and record.value.get('owner') == owner}
