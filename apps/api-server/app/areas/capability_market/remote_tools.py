"""自定义远程工具发现和确认后的单次调用，不向模型暴露连接配置。"""
import asyncio
from hashlib import sha256
import json

from fastapi import HTTPException
from sqlalchemy import select

from app.agent_mcp.auth import get_auth_context, require_human_decision
from app.agent_mcp.safety import reject_credentials, safe_result
from .connector_store import decrypt
from .personal_mcp import redact_verification
from .mcp_access import bound_scope, require_runtime_connection
from .remote_schema import checked_schema, schema_fingerprint, validate_arguments
from .remote_session import remote_error, remote_session, session_tools
from .remote_files import store_remote_files


async def current_configuration(identifier, revision, identity, db, *, scope, lock=False):
    record = await require_runtime_connection(identifier, bound_scope(scope), identity, db, lock=lock)
    if record.value['revision'] != revision:
        raise HTTPException(409, 'MCP配置已变更，请重新发现工具并确认')
    return record.value['display_name'], decrypt(record)


def safe_remote(value, configuration):
    return safe_result(redact_verification(value, configuration), get_auth_context().bearer)


async def discover_tools(identifier, revision, identity, db, *, scope):
    scope = bound_scope(scope)
    connection_name, configuration = await current_configuration(identifier, revision, identity, db, scope=scope)
    await db.rollback()
    descriptors = []
    async with asyncio.timeout(25):
        for server_name, server in configuration['mcp.json']['mcpServers'].items():
            async with remote_session(server) as (session, initialized):
                tools = await session_tools(session)
                for tool in tools:
                    schema = tool.input_schema
                    if redact_verification(schema, configuration) != schema:
                        raise HTTPException(502, '外部工具schema包含连接凭据回声，不能向模型提供或执行')
                    checked_schema(schema)
                    descriptor = {'scope': scope, 'connection_id': identifier, 'revision': revision, 'server_name': server_name,
                                  'connection_name': connection_name,
                                  'name': tool.name, 'description': (tool.description or '')[:1000],
                                  'inputSchema': schema, 'schema_fingerprint': schema_fingerprint(schema)}
                    descriptor['tool_id'] = sha256(json.dumps([scope, identifier, server_name, tool.name]).encode()).hexdigest()[:32]
                    descriptors.append(safe_remote(descriptor, configuration))
                    if len(descriptors) > 1000:
                        raise HTTPException(502, 'MCP连接的工具总数超过1000项限制')
    # 发现期间被修改的配置不能进入本轮可调用目录。
    await current_configuration(identifier, revision, identity, db, scope=scope)
    return descriptors


async def prepare_call(descriptor, arguments, identity, db):
    scope = bound_scope(descriptor.get('scope'))
    connection_name, configuration = await current_configuration(descriptor['connection_id'], descriptor['revision'], identity, db, scope=scope)
    reject_credentials(arguments)
    validate_arguments(descriptor['inputSchema'], arguments)
    bearer = get_auth_context().bearer
    encoded = json.dumps(arguments, ensure_ascii=False, allow_nan=False)
    if bearer in encoded or safe_remote(arguments, configuration) != arguments:
        raise HTTPException(422, '远程工具参数不能包含登录或连接凭据')
    return {'scope': scope, 'connection_id': descriptor['connection_id'], 'revision': descriptor['revision'],
            'server_name': descriptor['server_name'], 'tool_name': descriptor['name'],
            'schema_fingerprint': descriptor['schema_fingerprint'], 'arguments': arguments}


async def execute_call(payload, identity, db, *, action_id):
    require_human_decision(action_id)
    from app.models import BusinessRecord
    from app.areas.personal_agent.confirmation_history import PERSONAL_ACTION_MODULE
    request = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == PERSONAL_ACTION_MODULE, BusinessRecord.serial_no == 'PA-' + action_id,
        BusinessRecord.owner == identity['username'],
    ).execution_options(populate_existing=True))
    if (request is None or request.status != '执行中' or request.data.get('action_type') != 'personal_mcp.call'
            or request.data.get('payload') != payload):
        raise HTTPException(409, '个人MCP请求未通过当前人工确认或已处理，禁止执行')
    scope = bound_scope(payload.get('scope'))
    connection_name, configuration = await current_configuration(payload['connection_id'], payload['revision'], identity, db, scope=scope, lock=True)
    server = configuration['mcp.json']['mcpServers'].get(payload['server_name'])
    if server is None:
        raise HTTPException(409, '个人MCP服务已不存在，请重新准备调用')
    if safe_remote(payload['arguments'], configuration) != payload['arguments']:
        raise HTTPException(422, '远程工具参数不能包含凭据')
    # 持有当前连接行锁直到结果落库，防止确认后配置更换造成目的地漂移。
    async with asyncio.timeout(25):
        async with remote_session(server, file_results=True) as (session, initialized):
            tools = await session_tools(session)
            tool = next((tool for tool in tools if tool.name == payload['tool_name']), None)
            if tool is None or schema_fingerprint(tool.input_schema) != payload['schema_fingerprint']:
                raise HTTPException(409, '远程工具schema已变化或工具不存在，请重新发现并确认')
            if redact_verification(tool.input_schema, configuration) != tool.input_schema:
                raise HTTPException(502, '外部工具schema包含连接凭据回声，已阻断调用')
            validate_arguments(tool.input_schema, payload['arguments'])
            try:
                result = await session.call_tool(tool.name, arguments=payload['arguments'])
            except Exception as exc:
                raise HTTPException(502, remote_error(exc, 'tools/call', server)) from None
            if result.is_error:
                raise HTTPException(502, '外部MCP工具报告执行失败，请核对外部实际状态，禁止重复提交')
    return await store_remote_files(result, configuration, identity, db, tool_name=payload['tool_name'],
                                    conversation_id=request.data['conversation_id'], action_id=action_id)
