"""使用MCP SDK完成握手与只读工具发现，不执行外部业务工具。"""
import asyncio
from contextlib import AsyncExitStack

from fastapi import HTTPException
import httpx2
from mcp import ClientSession
from mcp.types import PaginatedRequestParams
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client

from .connector_format import configured_secret, remote_servers
from .connector_transport import PublicHttpsTransport, validate_endpoint


def verification_error(exc):
    if isinstance(exc, BaseExceptionGroup):
        return verification_error(exc.exceptions[0])
    if isinstance(exc, HTTPException):
        return exc.detail
    if isinstance(exc, httpx2.HTTPStatusError):
        code = exc.response.status_code
        if code in (401, 403):
            return f'服务返回HTTP{code}，请先授权或核对请求头中的凭据'
        return f'服务返回HTTP{code}，请核对MCP地址和接入方式'
    if isinstance(exc, (TimeoutError, httpx2.TimeoutException)):
        return '连接验证超时，未取得完整握手和工具目录'
    if isinstance(exc, httpx2.RequestError):
        return '网络或TLS连接失败，请核对服务域名与证书'
    if isinstance(exc, (AttributeError, NameError, TypeError, ImportError)):
        raise exc
    return 'MCP握手或工具目录读取失败（' + type(exc).__name__ + '）'


async def list_server_tools(name, server):
    url = server['url']
    validate_endpoint(url)
    headers = server.get('headers', {})
    if any(not configured_secret(value) for value in headers.values()):
        raise HTTPException(422, '请先填写服务请求头中的授权凭据')
    network = PublicHttpsTransport()
    async with AsyncExitStack() as stack:
        if server.get('type') == 'sse':
            def factory(headers=None, timeout=None, auth=None):
                return httpx2.AsyncClient(headers=headers, timeout=timeout, auth=auth, follow_redirects=False,
                                         trust_env=False, transport=network)
            transport = sse_client(url, headers=headers, timeout=8, sse_read_timeout=12, httpx_client_factory=factory)
        else:
            client = await stack.enter_async_context(httpx2.AsyncClient(headers=headers, timeout=httpx2.Timeout(8, read=12),
                follow_redirects=False, trust_env=False, transport=network))
            transport = streamable_http_client(url, http_client=client, max_sse_event_size=256 * 1024)
        try:
            streams = await stack.enter_async_context(transport)
            session = await stack.enter_async_context(ClientSession(*streams, read_timeout_seconds=12))
            initialized = await session.initialize()
            result = await session.list_tools()
            tools = list(result.tools)
            cursors = set()
            while result.next_cursor:
                if result.next_cursor in cursors or len(tools) >= 1000:
                    raise HTTPException(502, '服务工具目录分页异常或超过1000项限制')
                cursors.add(result.next_cursor)
                result = await session.list_tools(params=PaginatedRequestParams(cursor=result.next_cursor))
                tools.extend(result.tools)
            if len(tools) > 1000:
                raise HTTPException(502, '服务工具目录超过1000项限制')
            return {'name': name, 'server_name': initialized.server_info.name, 'server_version': initialized.server_info.version,
                    'tool_count': len(tools), 'tools': [{'name': tool.name, 'description': (tool.description or '')[:1000]} for tool in tools]}
        except Exception as exc:
            if network.failure:
                raise HTTPException(502, network.failure) from exc
            raise


async def verify_configuration(configuration):
    servers = remote_servers(configuration)
    if not servers:
        raise HTTPException(422, '此配置需要本地CLI或stdio运行器，当前只支持远程MCP连接验证')
    if len(servers) != len(configuration.get('mcp.json', {}).get('mcpServers', {})):
        raise HTTPException(422, '配置中包含尚未接入的本地服务，不能标记整组验证通过')
    try:
        async with asyncio.timeout(25):
            results = [await list_server_tools(name, server) for name, server in servers]
        return {'status': 'verified', 'servers': results, 'error': ''}
    except Exception as exc:
        return {'status': 'failed', 'servers': [], 'error': verification_error(exc)}
