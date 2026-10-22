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
from app.agent_mcp.service import call_tool, describe_tool, list_group_tools, list_tool_groups, search_tools
from app.agent_mcp import usage_skill
from app.agent_mcp.model_context import discovered_tools_view
from app.config import settings
from app.core.lifecycle import lifespan


SEARCH_SCHEMA = {
    "type": "object", "properties": {
        "query": {"type": "string", "minLength": 1, "description": "业务目标及同义词，例如财务回款附件上传，或上传/附件/文件/导入"},
        "group_id": {"type": "string", "pattern": "^(0[1-9]|1[0-9]|2[0-5])$"},
        "subgroup_id": {"type": "string", "enum": ["reporting", "notifications_feedback", "system_parameters", "ai_documents_skills"]},
        "limit": {"type": "integer", "minimum": 1, "maximum": 12, "default": 8, "description": "上传或导入涉及多个业务对象时建议使用 12"},
    }, "required": ["query"], "additionalProperties": False,
}
GROUP_SCHEMA = {
    "type": "object", "properties": {"query": {"type": "string", "minLength": 1}},
    "additionalProperties": False,
}


GROUP_TOOLS_SCHEMA = {
    "type": "object", "properties": {
        "group_id": {"type": "string", "pattern": "^(0[1-9]|1[0-9]|2[0-5])$", "description": "oa_list_tool_groups 返回的 group_id"},
        "subgroup_id": {"type": "string", "enum": ["reporting", "notifications_feedback", "system_parameters", "ai_documents_skills"], "description": "仅第 25 组需要"},
    }, "required": ["group_id"], "additionalProperties": False,
}
DESCRIBE_SCHEMA = {"type": "object", "properties": {"name": {"type": "string", "minLength": 1}}, "required": ["name"], "additionalProperties": False}
CALL_SCHEMA = {
    "type": "object", "properties": {
        "name": {"type": "string", "minLength": 1, "description": "要调用的业务工具名，来自 oa_list_group_tools / oa_search_tools"},
        "arguments": {"type": "object", "description": "该工具的参数，结构见 oa_describe_tool 返回的 inputSchema（path/query/body/files）"},
    }, "required": ["name"], "additionalProperties": False,
}
GUIDE_SCHEMA = {"type": "object", "properties": {}, "additionalProperties": False}
META_SCHEMAS = {
    usage_skill.GUIDE_TOOL: GUIDE_SCHEMA,
    "oa_list_tool_groups": GROUP_SCHEMA, "oa_search_tools": SEARCH_SCHEMA, "oa_list_group_tools": GROUP_TOOLS_SCHEMA,
    "oa_describe_tool": DESCRIBE_SCHEMA, "oa_call_read_tool": CALL_SCHEMA, "oa_call_write_tool": CALL_SCHEMA,
}


_LIGHT_SCHEMA = {"type": "object", "properties": {"path": {"type": "object"}, "query": {"type": "object"}, "body": {"type": "object"}, "files": {"type": "object"}}}


def _light_tool(spec) -> dict:
    """选了业务后列表里用精简形式：名称、标题、方法和路径；完整参数定义用 oa_describe_tool 按需取（服务端调用时仍按完整定义校验）。"""
    path = spec.path.removeprefix(settings.api_prefix)
    if spec.is_write:
        from app.agent_mcp.irreversible import irreversible_category
        kind = "【删除】" if spec.method == "DELETE" else "【写入】"
        category = irreversible_category(spec)
        note = f"不可撤回（{category}），调用后生成待确认，须用户在 OA 网页确认。" if category else "直接执行，留痕可还原。"
    else:
        kind, note = "【查询】", ""
    return {"name": spec.name, "title": f"{kind}{spec.title}", "description": f"{spec.title}（{spec.method} {path}）。{note}参数先用 oa_describe_tool 获取。",
            "inputSchema": _LIGHT_SCHEMA, "annotations": spec.to_mcp().get("annotations")}


def _guide_tool() -> types.Tool:
    return types.Tool(
        name=usage_skill.GUIDE_TOOL, title="【先读这个】OA 使用指南",
        description="连接后第一步先调用：返回 OA MCP 的使用指南（技能），写明怎么找接口、怎么调用、写入前必须向用户确认、权限和错误怎么处理，以及本次连接的业务范围和读写权限。",
        input_schema=GUIDE_SCHEMA, annotations=types.ToolAnnotations(read_only_hint=True, open_world_hint=False))


def _token_entry_tools(write_allowed: bool) -> list:
    """个人令牌的工具列表只放几个入口工具：按分组/关键词找接口，再按需取定义和调用，不一次加载全部业务接口。"""
    read_hint = types.ToolAnnotations(read_only_hint=True, open_world_hint=False)
    tools = [
        _guide_tool(),
        types.Tool(name="oa_list_tool_groups", title="列出 OA 业务分组", description="先调用这个：返回业务分组（案件、客户、合同、财务……）及各组可用工具数量，不含接口定义。",
                   input_schema=GROUP_SCHEMA, annotations=read_hint),
        types.Tool(name="oa_list_group_tools", title="列出某个分组的接口", description="返回指定分组里的接口清单（名称、标题、方法、路径、读/写），不含参数定义。",
                   input_schema=GROUP_TOOLS_SCHEMA, annotations=read_hint),
        types.Tool(name="oa_search_tools", title="按关键词查找接口", description="按业务目标或关键词查找接口，返回匹配接口的完整参数定义。",
                   input_schema=SEARCH_SCHEMA, annotations=read_hint),
        types.Tool(name="oa_describe_tool", title="查看接口参数定义", description="按接口名取完整参数定义（path/query/body/files 与必填项）。",
                   input_schema=DESCRIBE_SCHEMA, annotations=read_hint),
        types.Tool(name="oa_call_read_tool", title="调用只读接口（查询）", description="调用一个只读业务接口。name 和 arguments 来自 oa_list_group_tools / oa_describe_tool；写入类接口请用 oa_call_write_tool。",
                   input_schema=CALL_SCHEMA, annotations=types.ToolAnnotations(read_only_hint=True, open_world_hint=False)),
    ]
    if write_allowed:
        tools.append(types.Tool(
            name="oa_call_write_tool", title="调用写入接口（新增/修改/删除）",
            description="调用一个写入类业务接口（新增、修改、删除、状态流转等）。普通写入直接执行，每次变更在服务器留痕、可由管理员还原；审批、盖章与对外转交、付款与核销、开具或作废发票等不可撤回操作只生成待确认请求，须用户在 OA 网页确认。",
            input_schema=CALL_SCHEMA, annotations=types.ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=False)))
    return tools


async def _list_tools(_, params):
    if params is not None and params.cursor:
        raise MCPError(-32602, "工具目录不接收未知分页游标")
    context = get_auth_context()
    if context.readonly and not context.groups:
        return types.ListToolsResult(tools=_token_entry_tools(context.write_allowed))  # 没选业务：只给入口工具，按需发现
    catalog = get_catalog(context.application)
    from app.agent_mcp.personal_tokens import direct_write_view, token_tool_allowed
    scoped = bool(context.readonly and context.groups)
    tools = [
        types.Tool.model_validate(_light_tool(spec) if scoped
                                  else direct_write_view(spec.to_mcp(), spec.method) if context.readonly and spec.is_write else spec.to_mcp())
        for spec in catalog.tools
        if not (context.readonly and ((spec.is_write and not context.write_allowed) or not token_tool_allowed(spec)
                                      or (context.groups and spec.group_id not in context.groups)))
    ]  # 选了业务：只直接列出所选业务的接口（含完整参数定义）
    tools.insert(0, types.Tool(
        name="oa_search_tools", title="发现 OA 业务操作", description="按业务目标搜索全部已挂载的 OA 工具；结果按 domain 业务域分组，并返回真实参数模式、必填参数和 files 参数说明。",
        input_schema=SEARCH_SCHEMA, annotations=types.ToolAnnotations(read_only_hint=True, open_world_hint=False),
    ))
    tools.insert(0, types.Tool(
        name="oa_list_tool_groups", title="发现 OA 业务工具组", description="仅返回 25 个一级组及第 25 组四个子组的用途摘要与数量，不包含工具 schema。",
        input_schema=GROUP_SCHEMA, annotations=types.ToolAnnotations(read_only_hint=True, open_world_hint=False),
    ))
    if scoped:  # 选了业务时也带上按需取参数定义的入口
        tools.insert(0, types.Tool(name="oa_describe_tool", title="查看接口参数定义", description="按接口名取完整参数定义（path/query/body/files 与必填项）。调用任何业务接口前先用它。",
                                   input_schema=DESCRIBE_SCHEMA, annotations=types.ToolAnnotations(read_only_hint=True, open_world_hint=False)))
    tools.insert(0, _guide_tool())  # “先读这个”永远排第一
    return types.ListToolsResult(tools=tools)


async def _call_tool(_, params):
    result = await _dispatch_tool(params)
    context = get_auth_context()
    if context.readonly:
        from app.agent_mcp.personal_tokens import record_call
        name, arguments = params.name, params.arguments or {}
        if name in ("oa_call_read_tool", "oa_call_write_tool"):  # 审计记录实际被调用的业务接口，而不是入口工具
            name, arguments = str(arguments.get("name", "")), arguments.get("arguments") or {}
        spec = None
        try:
            spec = get_catalog(context.application).get(name)
        except Exception:  # 发现类工具或未知名称：不是业务接口，按只读记
            pass
        is_write = bool(spec is not None and spec.is_write)
        detail = ""
        if is_write:  # 写入类调用留完整请求（方法、路径、参数）和失败原因
            pending = isinstance(result.structured_content, dict) and result.structured_content.get("status") == "pending"
            detail = json.dumps({"method": spec.method, "path": spec.path, "arguments": arguments,
                                 **({"status": "pending"} if pending else {}),
                                 **({"error": str(result.structured_content)[:300]} if result.is_error else {})},
                                ensure_ascii=False, default=str)
        await record_call(context.token_id, context.username, name, not result.is_error, arguments,
                          detail=detail, is_write=is_write)
    return result


async def _dispatch_tool(params):
    try:
        arguments = params.arguments or {}
        if params.name == usage_skill.GUIDE_TOOL:
            if arguments:
                raise HTTPException(422, "使用指南不需要参数")
            context = get_auth_context()
            guide = usage_skill.build_skill(context, get_catalog(context.application))
            return types.CallToolResult(content=[types.TextContent(type="text", text=guide)], structured_content={"guide": guide})
        if params.name == "oa_list_tool_groups":
            if set(arguments) - {"query"}:
                raise HTTPException(422, "组发现只接受可选 query")
            result = list_tool_groups(arguments.get("query"))
        elif params.name == "oa_search_tools":
            if set(arguments) - {"query", "limit", "group_id", "subgroup_id"}:
                raise HTTPException(422, "工具发现不接受未知参数")
            result = discovered_tools_view(search_tools(
                arguments.get("query"), arguments.get("limit", 8),
                group_id=arguments.get("group_id"), subgroup_id=arguments.get("subgroup_id"),
            ))
        elif params.name == "oa_list_group_tools":
            if set(arguments) - {"group_id", "subgroup_id"} or "group_id" not in arguments:
                raise HTTPException(422, "分组工具清单需要 group_id，第 25 组还需要 subgroup_id")
            result = list_group_tools(arguments["group_id"], arguments.get("subgroup_id"))
        elif params.name == "oa_describe_tool":
            if set(arguments) != {"name"} or not isinstance(arguments["name"], str):
                raise HTTPException(422, "接口定义只接受 name")
            result = describe_tool(arguments["name"])
        elif params.name in ("oa_call_read_tool", "oa_call_write_tool"):
            context = get_auth_context()
            if not context.readonly:
                raise HTTPException(403, "入口调用工具仅用于个人访问令牌")
            if set(arguments) - {"name", "arguments"} or not isinstance(arguments.get("name"), str):
                raise HTTPException(422, "调用需要 name 和可选 arguments")
            target = get_catalog(context.application).get(arguments["name"])
            if target.is_write and params.name == "oa_call_read_tool":
                raise HTTPException(422, "这是写入类接口，请改用 oa_call_write_tool")
            if not target.is_write and params.name == "oa_call_write_tool":
                raise HTTPException(422, "这是只读接口，请改用 oa_call_read_tool")
            result = await call_tool(arguments["name"], arguments.get("arguments") or {})
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
    if uri == usage_skill.SKILL_URI:
        context = get_auth_context()
        return types.ReadResourceResult(contents=[types.TextResourceContents(
            uri=uri, mime_type="text/markdown", text=usage_skill.build_skill(context, get_catalog(context.application)))])
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
    skill = types.Resource(uri=usage_skill.SKILL_URI, name=usage_skill.SKILL_NAME, title="OA MCP 使用指南（技能）",
                           description="连接 OA 后先读：怎么找接口、怎么调用、写入前向用户确认、错误处理。", mime_type="text/markdown")
    return types.ListResourcesResult(resources=[skill, *[types.Resource(
        uri=item["uri"], name=item["name"], mime_type=item["mimeType"], size=item["size"],
    ) for item in resources]])


async def _list_prompts(_, params):
    return types.ListPromptsResult(prompts=[types.Prompt(
        name=usage_skill.PROMPT_NAME, title="OA 使用指南", description="先阅读 OA MCP 的使用指南，再开始操作。")])


async def _get_prompt(_, params):
    if params.name != usage_skill.PROMPT_NAME:
        raise MCPError(-32602, "未知提示")
    context = get_auth_context()
    guide = usage_skill.build_skill(context, get_catalog(context.application))
    return types.GetPromptResult(description="OA MCP 使用指南", messages=[types.PromptMessage(
        role="user", content=types.TextContent(type="text", text="请先阅读下面的 OA 使用指南，之后严格按它操作：\n\n" + guide))])


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
        "sunhold-oa", title="OA业务操作", instructions=usage_skill.INSTRUCTIONS, on_list_tools=_list_tools, on_call_tool=_call_tool,
        on_list_resources=_list_resources, on_read_resource=_read_resource, on_list_prompts=_list_prompts, on_get_prompt=_get_prompt,
        get_tool_input_schema=lambda name: (
            META_SCHEMAS[name] if name in META_SCHEMAS else get_catalog(application).get(name).input_schema
        ),
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
            try:
                yield
            finally:
                # 服务停止时关停常驻的智能体运行时，避免残留子进程。
                from app.harness_agent.runtime import close_all_residents
                await close_all_residents()
                from app.harness_agent.affinity import close
                await close()
