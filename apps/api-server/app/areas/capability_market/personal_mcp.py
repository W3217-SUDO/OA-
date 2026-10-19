"""个人自定义远程MCP的声明与安全投影，不依赖市场条目。"""
from copy import deepcopy
import json
import re
from urllib.parse import parse_qsl, urlsplit

from fastapi import HTTPException
from sqlalchemy import select
from app.models import SystemConfig

from .connector_format import public_configuration, validate_configuration
from .connector_store import CONNECTOR_CONFIG_PREFIX, config_key, decrypt, public_state, stored
from .connector_transport import validate_endpoint

SOURCE = 'personal-mcp'
ID_PATTERN = r'^personal-mcp-[a-f0-9]{32}$'
CAPABILITIES = {'discovery': True, 'tool_call': True}
VERIFICATION_KIND = 'initialize_and_tools_list'
_URL_CREDENTIAL = re.compile(r'^(?:key|(?:api|access|secret|private|client|x[-_]?api)[_-]?key(?:[_-]?id)?|credentials?|signature|(?:(?:access|refresh|id|auth)[_-]?)?token|secret|client[_-]?secret|password|authorization|passwd|sig|auth|ossaccesskeyid|x[-_]amz[-_](?:signature|credential|security[-_]token))$', re.I)


def validate_personal_endpoint(url):
    validate_endpoint(url)
    parsed = urlsplit(url)
    if parsed.username is not None or parsed.password is not None or any(_URL_CREDENTIAL.search(key) for key, _ in parse_qsl(parsed.query)):
        raise HTTPException(422, 'MCP地址不能包含凭据；请移除查询参数中的密钥并改用请求头')


def item_for(identifier, name):
    return {'id': identifier, 'name': name, 'source': SOURCE, 'kind': 'connector',
            'connection_configs': {'mcp.json': {'mcpServers': {}}}}


def normalize_configuration(value):
    if isinstance(value, str):
        if len(value.encode('utf-8')) > 65536:
            raise HTTPException(422, '连接配置超过64KB限制')
        text = value.strip()
        if text.startswith('https://'):
            value = {'mcpServers': {'default': {'type': 'streamableHttp', 'url': text}}}
        else:
            try:
                value = json.loads(text)
            except (ValueError, RecursionError):
                raise HTTPException(422, '请填写HTTPS地址或有效MCP JSON配置') from None
    if not isinstance(value, dict):
        raise HTTPException(422, 'MCP配置必须为JSON对象')
    if set(value) == {'mcpServers'}:
        value = {'mcp.json': value}
    template = item_for('', '')
    config = validate_configuration(value, template)
    declaration = config['mcp.json']
    if set(declaration) != {'mcpServers'}:
        raise HTTPException(422, 'MCP声明只允许mcpServers字段')
    for name, server in declaration['mcpServers'].items():
        if not 1 <= len(name) <= 80 or not name.strip() or not name.isprintable():
            raise HTTPException(422, '服务名称须为1至80个可打印字符，不能包含控制字符或仅有空白')
        if set(server) - {'type', 'url', 'headers', 'authUrl'}:
            raise HTTPException(422, '个人MCP仅接受远程服务类型、地址、请求头和授权页面，不支持本地命令或其他字段')
        if not isinstance(server.get('type'), str) or server['type'] not in {'streamableHttp', 'streamable-http', 'http', 'sse'}:
            raise HTTPException(422, '请选择远程MCP接入类型')
        try:
            validate_personal_endpoint(server.get('url'))
            if server.get('authUrl') and any(_URL_CREDENTIAL.search(key) for key, _ in parse_qsl(urlsplit(server['authUrl']).query)):
                raise HTTPException(422, '授权页面地址不能包含密钥或签名参数')
        except ValueError:
            raise HTTPException(422, '服务地址格式无效') from None
    return config


def personal_record(record, identity):
    value = record.value
    return (record.key.startswith(CONNECTOR_CONFIG_PREFIX)
            and value.get('schema_version') == 1 and value.get('scope') == 'personal'
            and value.get('owner') == identity['username'] and value.get('source') == SOURCE
            and isinstance(value.get('item_id'), str) and re.fullmatch(ID_PATTERN, value['item_id']))


async def require_personal_record(identifier, identity, db, *, lock=False):
    record = await stored(identifier, 'personal', identity, db, lock=lock)
    if record is None or not personal_record(record, identity):
        raise HTTPException(404, '个人MCP连接不存在')
    if record.key != config_key(identifier, 'personal', identity):
        raise HTTPException(409, '个人MCP连接归属不一致')
    return record


async def personal_records(identity, db):
    records = (await db.scalars(select(SystemConfig).where(
        SystemConfig.key.startswith(CONNECTOR_CONFIG_PREFIX),
        SystemConfig.value['scope'].as_string() == 'personal',
        SystemConfig.value['owner'].as_string() == identity['username'],
        SystemConfig.value['source'].as_string() == SOURCE,
    ))).all()
    return [record for record in records if personal_record(record, identity)
            and record.key == config_key(record.value['item_id'], 'personal', identity)]


async def list_personal_connections(identity, db):
    return [personal_state(record) for record in await personal_records(identity, db)]


async def personal_connection_groups(identity, db):
    return [{'id': record.value['item_id'], 'name': record.value['display_name'],
             'revision': record.value['revision'], 'status': record.value['status']}
            for record in await personal_records(identity, db)]


def redact_verification(result, configuration):
    # 外部服务可能在名称或描述中回显请求头，不能将凭据回声写库或返回。
    secrets = []
    for server in configuration['mcp.json']['mcpServers'].values():
        for value in server.get('headers', {}).values():
            if value:
                secrets.append(value)
                if value.lower().startswith('bearer '):
                    secrets.append(value[7:])

    def redact(value):
        if isinstance(value, str):
            for secret in sorted(set(secrets), key=len, reverse=True):
                if secret:
                    value = value.replace(secret, '[已脱敏]')
            return value
        if isinstance(value, list):
            return [redact(child) for child in value]
        if isinstance(value, dict):
            result = {}
            for key, child in value.items():
                safe_key = redact(key)
                if safe_key in result:
                    raise HTTPException(502, '外部MCP返回的字段脱敏后存在冲突，不能安全展示')
                result[safe_key] = redact(child)
            return result
        return value

    return redact(deepcopy(result))


def personal_state(record):
    item = item_for(record.value['item_id'], record.value['display_name'])
    state = public_state(item, record)
    state['servers'] = redact_verification(state['servers'], decrypt(record))
    # 自定义输入没有模板凭据，任何非空请求头均为秘密，不回传占位符文本。
    _, fields = public_configuration(decrypt(record))
    for field in fields:
        field['template'] = ''
    state['secret_fields'] = fields
    if state['status'] == 'failed':
        state['error_code'] = ('upstream_auth_failed' if any(code in state['error'] for code in ('HTTP401', 'HTTP403'))
                               else 'upstream_unreachable')
    else:
        state['error_code'] = ''
    return {**state, 'id': item['id'], 'name': item['name'], 'scope': 'personal',
            'capabilities': dict(CAPABILITIES), 'verification_kind': VERIFICATION_KIND}
