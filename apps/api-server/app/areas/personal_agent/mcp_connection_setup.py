"""由模型准备无密钥的连接计划，人工确认时才保存凭据并验证连接。"""
from typing import Literal
from uuid import uuid4

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from app.config import settings

from app.areas.capability_market.connector_format import _HEADER
from app.areas.capability_market.connector_store import save_configuration, save_verification
from app.areas.capability_market.mcp_access import default_connection_scope
from app.areas.capability_market.personal_mcp import item_for, normalize_configuration, redact_verification
from app.areas.capability_market.remote_session import verify_personal_configuration


class ConnectionPlan(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=80, pattern=r'^[^\x00-\x1f\x7f]+$')
    server_url: str = Field(min_length=1, max_length=2048)
    transport: Literal['streamable_http', 'sse'] = 'streamable_http'
    authentication: Literal['none', 'bearer', 'api_key']
    header_name: str = Field(default='X-API-Key', max_length=100)

    def configuration(self, value=''):
        server = {'url': self.server_url, 'type': 'sse' if self.transport == 'sse' else 'streamableHttp'}
        if self.authentication == 'bearer':
            server['headers'] = {'Authorization': 'Bearer ' + value}
        elif self.authentication == 'api_key':
            server['headers'] = {self.header_name: value}
        return {'mcp.json': {'mcpServers': {'default': server}}}


def read_plan(value):
    try:
        plan = ConnectionPlan.model_validate(value)
    except ValidationError:
        raise HTTPException(422, '请提供连接名称、HTTPS MCP 地址和认证方式，不要向模型提供密钥') from None
    if not plan.name.strip():
        raise HTTPException(422, '连接名称不能为空')
    if (not _HEADER.fullmatch(plan.header_name)
            or plan.header_name.lower() in {'authorization', 'host', 'content-length', 'connection', 'proxy-authorization'}):
        raise HTTPException(422, 'API Key 请求头名称无效')
    # 此处只核对公开连接声明；真实凭据不进入模型参数或待确认记录。
    normalize_configuration({'mcp.json': {'mcpServers': {'default': {
        'url': plan.server_url, 'type': 'sse' if plan.transport == 'sse' else 'streamableHttp',
    }}}})
    return plan


def prepare_connection(arguments, identity):
    plan = read_plan(arguments)
    scope = default_connection_scope(identity)
    scope_label = '全局共享，所有用户可使用' if scope == 'global' else '个人专用，仅本人可使用'
    summary = f'连接 MCP「{plan.name}」（{scope_label}）'
    payload = {'plan': plan.model_dump(), 'scope': scope, 'connection_id': 'personal-mcp-' + uuid4().hex}
    preview = {'operation_name': summary, 'target': plan.server_url, 'method': 'POST',
               'path': settings.api_prefix + '/capability-market/personal-mcp',
               'params': {'body': plan.model_dump(), 'scope': scope}, 'requires_confirmation': True}
    return {'type': 'personal_mcp.connect', 'summary': summary, 'payload': payload, 'preview': preview}


def validate_confirmation(action, identity, credential):
    payload = action.get('payload') or {}
    if set(payload) != {'plan', 'scope', 'connection_id'} or payload['scope'] != default_connection_scope(identity):
        raise HTTPException(409, '连接范围或登录权限已变化，请在对话中重新准备连接')
    plan = read_plan(payload['plan'])
    if plan.authentication == 'none' and credential:
        raise HTTPException(422, '当前计划无需 Token，请修改认证方式后重新确认')
    if plan.authentication != 'none':
        if not credential or not credential.strip():
            raise HTTPException(422, '请在安全输入中填写此服务的 Key / Token')
        if (credential != credential.strip() or any(char in credential for char in '\r\n\0')
                or '${' in credential or '{{' in credential or '***' in credential
                or credential.startswith('<') or credential.lower().startswith('bearer ')):
            raise HTTPException(422, '请填写真实 Token 本体，不要重复填写 Bearer 或占位符')
    normalize_configuration(plan.configuration(credential or ''))
    return plan


async def connect(action, identity, db, credential):
    plan = validate_confirmation(action, identity, credential)
    payload = action['payload']
    item = item_for(payload['connection_id'], plan.name.strip())
    configuration = normalize_configuration(plan.configuration(credential or ''))
    record = await save_configuration(item, payload['scope'], identity, db, configuration, [], '')
    revision = record.value['revision']
    await db.rollback()
    result = redact_verification(await verify_personal_configuration(configuration), configuration)
    record = await save_verification(item, payload['scope'], identity, db, revision, result)
    # 返回值进入确认历史和模型上下文，只允许摘要，不返回配置或原始供应商错误。
    status = record.value['status']
    code = ('upstream_auth_failed' if any(value in result.get('error', '') for value in ('HTTP401', 'HTTP403'))
            else 'upstream_unreachable') if status == 'failed' else ''
    return {'id': payload['connection_id'], 'name': plan.name.strip(), 'scope': payload['scope'],
            'status': status, 'error_code': code,
            'tool_count': sum(server['tool_count'] for server in result.get('servers', []))}


def completion_message(result):
    if result['status'] == 'verified':
        return f'已连接 MCP「{result["name"]}」，握手和工具目录验证通过，共发现 {result["tool_count"]} 个工具。你可以继续告诉我需要办理什么；实际调用外部工具时仍会请你确认。'
    detail = ('服务拒绝了认证，请核对 Token 是否有效及认证方式是否正确。'
              if result['error_code'] == 'upstream_auth_failed' else '握手或工具目录读取未通过，请核对 MCP 地址和服务状态。')
    return f'MCP「{result["name"]}」的配置已保存，但尚未连接成功。{detail}不要重复新建连接，可以从连接管理中修改或重试。'
