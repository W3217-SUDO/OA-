"""官方 MCP SDK 的无状态 HTTP 协议和 OA 生命周期组合。"""

import base64
from contextlib import asynccontextmanager
import json
import re
from urllib.parse import urlsplit

from fastapi import HTTPException
from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.transport_security import TransportSecuritySettings
from mcp.shared.exceptions import MCPError

from app.agent_mcp.artifacts import list_resources, read_resource
from app.agent_mcp.auth import RequestAuthContextMiddleware, get_auth_context
from app.agent_mcp.catalog import get_catalog
from app.agent_mcp.config import trusted_origins
from app.agent_mcp.router import router
from app.agent_mcp.safety import safe_result
from app.agent_mcp.service import call_tool, search_tools
from app.config import settings
from app.core.lifecycle import lifespan


SEARCH_SCHEMA = {
    "type": "object", "properties": {
        "query": {"type": "string", "minLength": 1},
        "limit": {"type": "integer", "minimum": 1, "maximum": 12, "default": 8},
    }, "required": ["query"], "additionalProperties": False,
}


async def _list_tools(_, params):
    if params is not None and params.cursor:
        raise MCPError(-32602, "工具目录不接收未知分页游标")
    catalog = get_catalog(get_auth_context().application)
    tools = [types.Tool.model_validate(spec.to_mcp()) for spec in catalog.tools]
    tools.insert(0, types.Tool(
        name="oa_search_tools", title="发现 OA 业务操作", description="按业务目标搜索全部已挂载的 OA 工具与真实参数模式。",
        input_schema=SEARCH_SCHEMA, annotations=types.ToolAnnotations(read_only_hint=True, open_world_hint=False),
    ))
    return types.ListToolsResult(tools=tools)


async def _call_tool(_, params):
    try:
        arguments = params.arguments or {}
        if params.name == "oa_search_tools":
            if set(arguments) - {"query", "limit"}:
                raise HTTPException(422, "工具发现不接受未知参数")
            result = {"tools": search_tools(arguments.get("query"), arguments.get("limit", 8))}
        else:
            result = await call_tool(params.name, arguments)
        content = [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, allow_nan=False))]
        if isinstance(result, dict) and result.get("type") == "resource_link":
            content = [types.ResourceLink(uri=result["uri"], name=result["name"], mime_type=result["mimeType"])]
        return types.CallToolResult(content=content, structured_content=result if isinstance(result, dict) else {"result": result})
    except HTTPException as exc:
        error = safe_result({"status_code": exc.status_code, "detail": exc.detail}, get_auth_context().bearer)
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(error, ensure_ascii=False))],
            structured_content=error, is_error=True,
        )
    except Exception as exc:
        error = {"status_code": 502, "type": type(exc).__name__, "detail": "工具处理失败，请核对请求状态和服务日志"}
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(error, ensure_ascii=False))],
            structured_content=error, is_error=True,
        )


async def _read_resource(_, params):
    uri = str(params.uri)
    match = re.fullmatch(r"oa-mcp-(artifact|source)://([0-9a-f]{32})", uri)
    if match is None:
        raise MCPError(-32602, "只允许读取本 OA 生成的受控资源标识")
    try:
        metadata, content = await read_resource(match[2], expected_kind=match[1])
    except HTTPException as exc:
        error = safe_result({"status_code": exc.status_code, "detail": exc.detail}, get_auth_context().bearer)
        raise MCPError(-32002, json.dumps(error, ensure_ascii=False)) from exc
    except Exception as exc:
        raise MCPError(-32603, f"工具资源读取失败（{type(exc).__name__}）") from exc
    return types.ReadResourceResult(contents=[types.BlobResourceContents(
        uri=uri, mime_type=metadata["mime_type"], blob=base64.b64encode(content).decode("ascii"),
    )])


async def _list_resources(_, __):
    try:
        resources = await list_resources()
    except HTTPException as exc:
        error = safe_result({"status_code": exc.status_code, "detail": exc.detail}, get_auth_context().bearer)
        raise MCPError(-32002, json.dumps(error, ensure_ascii=False)) from exc
    except Exception as exc:
        raise MCPError(-32603, f"工具资源目录读取失败（{type(exc).__name__}）") from exc
    return types.ListResourcesResult(resources=[types.Resource(
        uri=item["uri"], name=item["name"], mime_type=item["mimeType"], size=item["size"],
    ) for item in resources])


def install_gateway(application) -> None:
    origins = trusted_origins()
    hosts = set()
    for origin in origins:
        parsed = urlsplit(origin)
        hosts.add(parsed.netloc)
        # nginx 的 $host 不携带端口，只增加已明确信任的同一主机，不扩大 Origin 范围。
        hostname = parsed.hostname
        hosts.add(f"[{hostname}]" if ":" in hostname else hostname)
    server = Server(
        "sunhold-oa", title="OA业务操作", on_list_tools=_list_tools, on_call_tool=_call_tool,
        on_list_resources=_list_resources, on_read_resource=_read_resource,
        get_tool_input_schema=lambda name: SEARCH_SCHEMA if name == "oa_search_tools" else get_catalog(application).get(name).input_schema,
    )
    http_application = server.streamable_http_app(
        streamable_http_path="/mcp", json_response=True, stateless_http=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True, allowed_hosts=sorted(hosts), allowed_origins=origins,
        ),
    )
    application.state.agent_mcp_http = http_application
    application.state.agent_mcp_server = server
    application.include_router(router)
    application.mount(settings.api_prefix, http_application)
    application.add_middleware(RequestAuthContextMiddleware, application=application)
    get_catalog(application)


@asynccontextmanager
async def mcp_lifespan(application):
    async with lifespan(application):
        http_application = application.state.agent_mcp_http
        async with http_application.router.lifespan_context(http_application):
            yield
