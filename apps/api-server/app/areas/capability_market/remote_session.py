"""固定公网HTTPS目的地的MCP会话；不接受OA登录令牌。"""
from contextlib import AsyncExitStack, asynccontextmanager
import asyncio
import json
from urllib.parse import unquote, urlsplit

from fastapi import HTTPException
import httpx2
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import PaginatedRequestParams
from mcp.shared.exceptions import MCPError
from app.agent_mcp.auth import get_auth_context

from .connector_format import configured_secret
from .connector_probe import verification_error
from .connector_transport import PublicHttpsTransport, validate_endpoint
from .personal_mcp import validate_personal_endpoint
from .remote_logging import safe_sdk_logs
from .remote_files import MAX_REMOTE_RESULT_BYTES


class OriginBoundTransport(PublicHttpsTransport):
    def __init__(self, endpoint, *, file_results=False):
        super().__init__()
        self.host = urlsplit(endpoint).hostname
        self.file_results = file_results

    def response_limit(self, request):
        if self.file_results and request.method == 'POST' and json.loads(request.content).get('method') == 'tools/call':
            return MAX_REMOTE_RESULT_BYTES
        return super().response_limit(request)

    async def handle_async_request(self, request):
        if request.url.host != self.host:
            self.failure = 'MCP会话不能将请求或凭据转发到其他域名'
            raise HTTPException(422, self.failure)
        validate_personal_endpoint(str(request.url))
        if self.file_results and request.method == 'POST':
            await request.aread()
        return await super().handle_async_request(request)


@asynccontextmanager
async def remote_session(server, *, file_results=False):
    url = server['url']
    validate_endpoint(url)
    headers = server.get('headers', {})
    bearer = get_auth_context().bearer
    if any(bearer in value for value in [url, unquote(url), *headers, *headers.values()]):
        raise HTTPException(422, '个人MCP不能使用当前OA登录令牌作为第三方凭据')
    if any(not configured_secret(value) for value in headers.values()):
        raise HTTPException(422, '请先在个人MCP连接卡片填写完整请求头凭据')
    network = OriginBoundTransport(url, file_results=file_results)
    stage = 'initialize'
    try:
        async with AsyncExitStack() as stack:
            stack.enter_context(safe_sdk_logs())
            await stack.enter_async_context(network)
            if server['type'] == 'sse':
                def factory(headers=None, timeout=None, auth=None):
                    return httpx2.AsyncClient(headers=headers, timeout=timeout, auth=auth,
                                             follow_redirects=False, trust_env=False, transport=network)
                transport = sse_client(url, headers=headers, timeout=8, sse_read_timeout=12, httpx_client_factory=factory)
            else:
                client = await stack.enter_async_context(httpx2.AsyncClient(
                    headers=headers, timeout=httpx2.Timeout(8, read=12), follow_redirects=False,
                    trust_env=False, transport=network))
                transport = streamable_http_client(url, http_client=client,
                    max_sse_event_size=MAX_REMOTE_RESULT_BYTES if file_results else 256 * 1024)
            streams = await stack.enter_async_context(transport)
            session = await stack.enter_async_context(ClientSession(*streams, read_timeout_seconds=12))
            initialized = await session.initialize()
            stage = 'session'
            yield session, initialized
    except HTTPException:
        raise
    except Exception as exc:
        try:
            detail = network.failure or remote_error(exc, stage, server)
        except (AttributeError, NameError, TypeError, ImportError):
            detail = '远程MCP会话处理失败（' + type(exc).__name__ + '）'
        raise HTTPException(502, detail) from None


def remote_error(exc, stage, server):
    from .personal_mcp import redact_verification
    from app.agent_mcp.safety import safe_result

    if isinstance(exc, BaseExceptionGroup):
        return remote_error(exc.exceptions[0], stage, server)
    if isinstance(exc, MCPError):
        detail = f'MCP {stage}失败（{exc.code}）：{exc.message[:1000]}'
        return safe_result(redact_verification(detail, {'mcp.json': {'mcpServers': {'remote': server}}}), get_auth_context().bearer)
    return f'MCP {stage}失败：{verification_error(exc)}'


async def session_tools(session):
    result = await session.list_tools()
    tools = list(result.tools)
    cursors = set()
    while result.next_cursor:
        if result.next_cursor in cursors or len(tools) >= 1000:
            raise HTTPException(502, '服务工具目录分页异常或超过1000项限制')
        cursors.add(result.next_cursor)
        result = await session.list_tools(params=PaginatedRequestParams(cursor=result.next_cursor))
        tools.extend(result.tools)
    names = [tool.name for tool in tools]
    if len(tools) > 1000 or len(names) != len(set(names)):
        raise HTTPException(502, '服务工具目录超过限制或存在重复名称')
    return tools


async def verify_personal_configuration(configuration):
    try:
        servers = []
        async with asyncio.timeout(25):
            for name, server in configuration['mcp.json']['mcpServers'].items():
                async with remote_session(server) as (session, initialized):
                    tools = await session_tools(session)
                    servers.append({'name': name, 'server_name': initialized.server_info.name,
                                    'server_version': initialized.server_info.version, 'tool_count': len(tools),
                                    'tools': [{'name': tool.name, 'description': (tool.description or '')[:1000]} for tool in tools]})
        return {'status': 'verified', 'servers': servers, 'error': ''}
    except (HTTPException, TimeoutError) as exc:
        return {'status': 'failed', 'servers': [], 'error': verification_error(exc)}
