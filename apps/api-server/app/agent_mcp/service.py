"""业务工具的只读调用、持久准备和人工确认状态机。"""

from datetime import datetime, timezone
import hashlib
import json
import logging
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select, update

from app.agent_mcp.auth import (
    authenticated_identity, get_auth_context, require_human_decision, trusted_case_origin,
)
from app.agent_mcp.action_summary import summary_from_preview
from app.agent_mcp.catalog import get_catalog
from app.agent_mcp.operation_guidance import get_operation_guidance, parameter_documentation
from app.agent_mcp.business_preflight import prepare_business_arguments
from app.agent_mcp.safety import reject_credentials, render_path, require_business_record_target, require_case_scoped_target, safe_result
from app.agent_mcp.transport import execute_original
from app.config import settings
from app.database import SessionLocal
from app.models import BusinessRecord, WorkflowEvent


logger = logging.getLogger(__name__)
ACTION_MODULE = "agent_mcp_action"
_UNSET = object()
STATUS_NAMES = {"待确认": "pending", "执行中": "executing", "已执行": "succeeded", "执行失败": "failed", "已拒绝": "rejected"}


def _parameter_groups(spec) -> dict[str, list[dict]]:
    """把完整 inputSchema 转成模型可快速阅读的分组参数清单。"""
    def schema_type(value: dict) -> str:
        if value.get("type"):
            return str(value["type"])
        if value.get("format"):
            return str(value["format"])
        branches = value.get("anyOf") or value.get("oneOf")
        if isinstance(branches, list):
            types = [schema_type(item) for item in branches if isinstance(item, dict) and item.get("type") != "null"]
            if types:
                return " or ".join(dict.fromkeys(types))
        if value.get("$ref"):
            return "object"
        return "object"

    properties = spec.input_schema.get("properties", {})
    groups = {}
    for group in ("path", "query", "body", "files"):
        schema = properties.get(group)
        if not isinstance(schema, dict) or schema.get("type") == "null":
            continue
        fields = schema.get("properties", {})
        if not isinstance(fields, dict):
            fields = {}
        required = set(schema.get("required", []))
        groups[group] = [
            {
                "name": name,
                "required": name in required,
                "type": schema_type(value) if isinstance(value, dict) else "object",
                "description": value.get("description", "") if isinstance(value, dict) else "",
                **({"enum": value["enum"]} if isinstance(value, dict) and "enum" in value else {}),
            }
            for name, value in fields.items()
        ]
    return groups


def public_tool(spec) -> dict:
    parameter_groups = _parameter_groups(spec)
    guidance = get_operation_guidance(spec._route, spec.method)
    if guidance["documentation_status"] == "unknown":
        guidance["purpose"] = f"{spec.title}；对应原接口 {spec.method} {spec.path}。业务前置条件尚未逐项核实。"
    return {
        **spec.to_mcp(), "method": spec.method, "path": spec.path, "is_write": spec.is_write,
        "request_media_type": spec.request_media_type, "domain": spec.domain,
        "group_id": spec.group_id, "group_name": spec.group_name, "subgroup_id": spec.subgroup_id,
        "file_fields": dict(spec.file_fields), "response_media_types": list(spec.response_media_types),
        "is_binary_response": spec.is_binary_response,
        "usage": guidance, "documentation_status": guidance["documentation_status"],
        "documentation_gaps": guidance["documentation_gaps"],
        "parameter_documentation": parameter_documentation(spec.input_schema),
        "parameter_groups": parameter_groups,
        "required_parameters": {
            group: [field["name"] for field in fields if field["required"]]
            for group, fields in parameter_groups.items()
        },
    }


def token_visible_tools(context, catalog):
    """个人令牌能用到的工具：去掉系统管理类，没有写入授权时再去掉写入类。"""
    from app.agent_mcp.personal_tokens import token_tool_allowed
    return [spec for spec in catalog.tools if token_tool_allowed(spec) and (context.write_allowed or not spec.is_write)
            and (not context.groups or spec.group_id in context.groups)]


def list_tool_groups(query: str | None = None) -> dict:
    from app.agent_mcp.tool_groups import group_summaries
    context = get_auth_context()
    catalog = get_catalog(context.application)
    if context.readonly:  # 分组数量只统计这把令牌实际能用的工具
        tools = token_visible_tools(context, catalog)
        return {"groups": group_summaries(tools, query), "total_tool_count": len(tools)}
    return {"groups": catalog.list_groups(query), "total_tool_count": len(catalog.tools)}


def list_group_tools(group_id: str, subgroup_id: str | None = None) -> dict:
    """某个分组里的工具清单（只有名称、标题、方法、路径和读/写，不含参数 schema），按需再用 oa_describe_tool 取参数。"""
    from app.agent_mcp.tool_groups import require_group
    context = get_auth_context()
    catalog = get_catalog(context.application)
    require_group(group_id, subgroup_id)
    tools = [spec for spec in token_visible_tools(context, catalog) if spec.group_id == group_id and (subgroup_id is None or spec.subgroup_id == subgroup_id)]
    if group_id == "25" and subgroup_id is None:
        raise HTTPException(422, "第 25 组必须指定 subgroup_id")
    return {"group_id": group_id, "subgroup_id": subgroup_id, "count": len(tools),
            "tools": [{"name": spec.name, "title": spec.title, "method": spec.method, "path": spec.path.removeprefix(settings.api_prefix),
                       "is_write": spec.is_write} for spec in tools]}


def describe_tool(name: str) -> dict:
    """单个工具的完整定义（含参数 schema）。"""
    from app.agent_mcp.personal_tokens import direct_write_view, token_tool_allowed
    context = get_auth_context()
    spec = get_catalog(context.application).get(name)
    if context.readonly and (not token_tool_allowed(spec) or (spec.is_write and not context.write_allowed)
                             or (context.groups and spec.group_id not in context.groups)):
        raise HTTPException(403, "该接口不对当前令牌或当前连接的业务范围开放")
    view = public_tool(spec)
    return direct_write_view(view, spec.method) if context.readonly and spec.is_write else view


def search_tools(query: str, limit: int = 8, *, group_id: str | None = None, subgroup_id: str | None = None) -> list[dict]:
    if not isinstance(query, str) or not query.strip() or type(limit) is not int or not 1 <= limit <= 12:
        raise HTTPException(422, "工具搜索需要非空关键词和 1 至 12 的结果数量")
    context = get_auth_context()
    catalog = get_catalog(context.application)
    if context.readonly:  # 令牌：多取一些再按读写范围过滤，避免结果被不可用的工具占满
        from app.agent_mcp.personal_tokens import direct_write_view
        found = catalog.search(query.strip(), limit=50, group_id=group_id, subgroup_id=subgroup_id)
        from app.agent_mcp.personal_tokens import token_tool_allowed
        usable = [spec for spec in found if (context.write_allowed or not spec.is_write) and token_tool_allowed(spec)
                  and (not context.groups or spec.group_id in context.groups)][:limit]
        return [direct_write_view(public_tool(spec), spec.method) if spec.is_write else public_tool(spec) for spec in usable]
    return [public_tool(spec) for spec in catalog.search(query.strip(), limit=limit, group_id=group_id, subgroup_id=subgroup_id)]


def descriptor_fingerprint(spec) -> str:
    descriptor = {
        "name": spec.name, "method": spec.method, "path": spec.path,
        "input_schema": spec.original_input_schema if spec.original_input_schema is not None else spec.input_schema,
        "is_write": spec.is_write,
        "request_media_type": spec.request_media_type, "file_fields": spec.file_fields,
        "response_media_types": spec.response_media_types, "is_binary_response": spec.is_binary_response,
        "handler": spec._route.endpoint.__module__ + "." + spec._route.endpoint.__qualname__,
    }
    encoded = json.dumps(descriptor, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _event(record_id: int, identity: dict, before: str, after: str, comment: str = "") -> WorkflowEvent:
    return WorkflowEvent(
        record_id=record_id, action="MCP人工确认" if before else "MCP准备业务操作",
        from_status=before, to_status=after, operator=identity["username"], comment=comment,
    )


def request_view(record: BusinessRecord) -> dict:
    data = record.data
    return {
        "request_id": data["request_id"], "id": data["request_id"], "status": STATUS_NAMES[record.status],
        "summary": data.get("summary") or summary_from_preview(data["preview"]),
        "preview": data["preview"], "owner": record.owner,
        "case_origin": data["case_origin"], "created_at": record.created_at, "updated_at": record.updated_at,
        "result": data.get("result"), "error": data.get("error"),
        "decided_at": data.get("decided_at"), "finished_at": data.get("finished_at"),
        "decision": data.get("decision"), "comment": data.get("comment"),
        "confirmation_url": settings.api_prefix + f"/agent-tools/requests/{data['request_id']}",
    }


def _request_query(request_id: str, identity: dict):
    return select(BusinessRecord).where(
        BusinessRecord.module == ACTION_MODULE,
        BusinessRecord.serial_no == "MCP-" + request_id,
        BusinessRecord.owner == identity["username"],
    )


async def get_tool_request(request_id: str, identity: dict, db) -> dict:
    record = await db.scalar(_request_query(request_id, identity).execution_options(populate_existing=True))
    if record is None:
        raise HTTPException(404, "确认请求不存在或不属于当前账号")
    return request_view(record)


async def list_tool_requests(identity: dict, db, *, status: str = "pending", page: int = 1, page_size: int = 20) -> dict:
    conditions = [BusinessRecord.module == ACTION_MODULE, BusinessRecord.owner == identity["username"]]
    if status:
        states = [key for key, value in STATUS_NAMES.items() if value == status]
        if not states:
            raise HTTPException(422, "确认请求状态无效")
        conditions.append(BusinessRecord.status.in_(states))
    total = await db.scalar(select(func.count()).select_from(BusinessRecord).where(*conditions))
    records = (await db.scalars(select(BusinessRecord).where(*conditions).order_by(
        BusinessRecord.id.desc(),
    ).offset((page - 1) * page_size).limit(page_size))).all()
    return {"items": [request_view(record) for record in records], "total": total, "page": page, "page_size": page_size}


async def call_tool(name: str, arguments: dict, *, conversation_id: str | None = None):
    """整次调用（包括不可撤回操作生成的待确认记录）在变更留痕里都记为 MCP 或智能体来源；
    站内智能体的每次调用（查询、写入、失败、待确认）也写入操作日志（MCP 的调用由网关记录）。"""
    from app.core import change_log
    context = get_auth_context()
    token = change_log.set_source("mcp" if context.readonly else "agent")
    ok, outcome = False, None
    try:
        outcome = await _call_tool(name, arguments, conversation_id=conversation_id)
        ok = True
        return outcome
    except HTTPException as exc:
        outcome = {"status_code": exc.status_code, "detail": exc.detail}
        raise
    finally:
        change_log.source_var.reset(token)
        if not context.readonly:
            await _record_agent_call(context, name, arguments, ok, outcome)


async def _record_agent_call(context, name, arguments, ok, outcome) -> None:
    """站内智能体调用写入操作日志（token_id=0 表示站内智能体），失败只记服务日志，不影响调用本身。"""
    try:
        from app.agent_mcp.personal_tokens import record_call
        from app.core.soft_delete import actor_var
        spec = None
        try:
            spec = get_catalog(context.application).get(name)
        except Exception:
            pass
        is_write = bool(spec is not None and spec.is_write)
        extra = {}
        if isinstance(outcome, dict) and outcome.get("status") == "pending":
            extra["status"] = "pending"
        if not ok and isinstance(outcome, dict):
            extra["error"] = str(outcome)[:300]
        detail = json.dumps({**({"method": spec.method, "path": spec.path} if spec is not None else {}), "arguments": arguments, **extra},
                            ensure_ascii=False, default=str)
        await record_call(0, actor_var.get(), name, ok, arguments, detail=detail, is_write=is_write)
    except Exception:
        logger.exception("站内智能体操作日志写入失败 tool=%s", name)


async def _call_tool(name: str, arguments: dict, *, conversation_id: str | None = None):
    context = get_auth_context()
    identity = await authenticated_identity()
    spec = get_catalog(context.application).get(name)
    if context.readonly:
        from app.agent_mcp.personal_tokens import token_tool_allowed
        if not token_tool_allowed(spec):
            raise HTTPException(403, "该接口属于系统管理类，不对个人访问令牌开放；个人令牌只开放业务接口")
        if context.groups and spec.group_id not in context.groups:
            raise HTTPException(403, "该接口不在这个连接地址选定的业务范围内；请用包含该业务的连接地址")
    if context.readonly and spec.is_write and not context.write_allowed:
        raise HTTPException(403, "该账号没有 MCP 写入授权，只能读取；需要新增、修改、删除请联系管理员授予")
    reject_credentials(arguments)
    if context.bearer in json.dumps(arguments, ensure_ascii=False) or "oamcp_" in json.dumps(arguments, ensure_ascii=False):
        raise HTTPException(422, "工具参数不能包含当前登录凭据")
    params = spec.validate_arguments(arguments)
    reject_credentials(params)
    async with SessionLocal() as db:
        case_origin = trusted_case_origin()
        if case_origin is not None:
            await require_case_scoped_target(spec, params, case_origin, db)
        await require_business_record_target(spec, params, db)
        if not spec.is_write:
            return await execute_original(spec, params, case_origin=case_origin, conversation_id=conversation_id)
        arguments = await prepare_business_arguments(spec, arguments, params, identity, db)
        params = spec.validate_arguments(arguments)
        reject_credentials(params)
        from app.agent_mcp.irreversible import irreversible_category
        category = irreversible_category(spec)
        if category is None:
            # 普通写入：直接执行原接口（原权限、数据范围、校验、审批流程照常生效），每次变更在服务器留痕、可还原。
            if context.readonly:
                from app.agent_mcp.personal_tokens import check_write_rate
                check_write_rate(context.token_id)
            return await execute_original(spec, params, case_origin=case_origin, conversation_id=conversation_id)
        # 需要网页确认的四类（审批、盖章与对外转交、付款与核销、开具或作废发票）：仍生成待确认请求，须用户在 OA 网页确认。
        path = render_path(spec, params)
        # 写操作只落准备记录，不调用任何业务写入或新建附件。
        request_id = uuid4().hex
        preview = {
            "operation_name": spec.title, "tool_name": spec.name, "method": spec.method,
            "path": path, "path_template": spec.path, "params": params,
            "original_values": "未读取原值", "requires_confirmation": True,
        }
        summary = summary_from_preview(preview)
        preview["summary"] = summary
        data = {
            "request_id": request_id, "tool_name": spec.name, "descriptor_fingerprint": descriptor_fingerprint(spec),
            "arguments": json.loads(json.dumps(arguments, ensure_ascii=False, allow_nan=False)),
            "params": params, "preview": preview, "case_origin": case_origin, "summary": summary,
            "conversation_id": conversation_id,
        }
        record = BusinessRecord(
            module=ACTION_MODULE, serial_no="MCP-" + request_id, title=summary[:255],
            status="待确认", owner=identity["username"], department=identity["department"], data=data,
        )
        db.add(record)
        await db.flush()
        db.add(_event(record.id, identity, "", "待确认"))
        await db.commit()
        return {
            "request_id": request_id, "status": "pending", "summary": summary, "preview": preview,
            "irreversible_category": category,
            "next_step": f"这是不可撤回的操作（{category}），已生成待确认请求，需要用户在 OA 网页的智能体中心确认后才会执行。",
            "confirmation_url": settings.api_prefix + f"/agent-tools/requests/{request_id}",
        }


async def decide_tool_request(
    request_id: str, decision: str, identity: dict, db, *, comment: str = "", expected_case_id=_UNSET,
) -> dict:
    require_human_decision(request_id)
    actual_identity = await authenticated_identity(db)
    if identity.get("username") != actual_identity["username"]:
        raise HTTPException(403, "确认身份与当前原始登录身份不一致")
    if decision not in {"approved", "rejected"}:
        raise HTTPException(422, "只能确认或拒绝业务请求")
    reject_credentials(comment)
    record = await db.scalar(_request_query(request_id, actual_identity).with_for_update().execution_options(populate_existing=True))
    if record is None:
        raise HTTPException(404, "确认请求不存在或不属于当前账号")
    if record.status != "待确认":
        raise HTTPException(409, {"request_id": request_id, "status": STATUS_NAMES[record.status], "detail": "请求已决定或执行结果不确定，禁止重放"})
    data = dict(record.data)
    if expected_case_id is not _UNSET and data["case_origin"] != expected_case_id:
        raise HTTPException(403, "确认请求与当前案件或个人智能体入口不一致")
    if decision == "approved":
        spec = get_catalog(get_auth_context().application).get(data["tool_name"])
        if not spec.is_write or descriptor_fingerprint(spec) != data["descriptor_fingerprint"]:
            raise HTTPException(409, "业务接口定义已变化，请重新准备并在前端确认")
        params = spec.validate_arguments(data["arguments"])
        reject_credentials(params)
        if params != data["params"] or render_path(spec, params) != data["preview"]["path"]:
            raise HTTPException(409, "准备参数与当前校验结果不一致，请重新准备")
        await require_business_record_target(spec, params, db)
    new_status = "执行中" if decision == "approved" else "已拒绝"
    execution_id = uuid4().hex
    data.update(decision=decision, comment=safe_result(comment, get_auth_context().bearer), execution_id=execution_id,
                decided_at=datetime.now(timezone.utc).isoformat())
    changed = await db.execute(update(BusinessRecord).where(
        BusinessRecord.id == record.id, BusinessRecord.status == "待确认", BusinessRecord.owner == actual_identity["username"],
    ).values(status=new_status, data=data).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        await db.rollback()
        raise HTTPException(409, "请求正在被其他确认操作处理，禁止重复执行")
    db.add(_event(record.id, actual_identity, "待确认", new_status, data["comment"]))
    # 原业务路由自行提交事务；先持久标记执行中，崩溃后不能自动再次执行。
    await db.commit()
    if decision == "rejected":
        return await get_tool_request(request_id, actual_identity, db)
    from app.core import change_log
    source_token = change_log.set_source("agent")  # 智能体准备、用户在网页确认后执行
    try:
        result = await execute_original(
            spec, params, case_origin=data["case_origin"],
            conversation_id=data.get("conversation_id"), source_request_id=request_id,
        )
    except Exception as exc:
        error = safe_result(
            {"status_code": exc.status_code, "detail": exc.detail} if isinstance(exc, HTTPException)
            else {"type": type(exc).__name__, "detail": "原业务接口执行失败，请人工核对实际结果，禁止自动重试"}, get_auth_context().bearer,
        )
        await _finish_request(record.id, execution_id, actual_identity, db, "执行失败", error=error)
        logger.error("MCP business execution failed request_id=%s error_type=%s", request_id, type(exc).__name__)
        raise HTTPException(
            exc.status_code if isinstance(exc, HTTPException) else 502,
            {"request_id": request_id, "status": "failed", "error": error},
        ) from exc
    finally:
        change_log.source_var.reset(source_token)
    await _finish_request(record.id, execution_id, actual_identity, db, "已执行", result=result)
    return await get_tool_request(request_id, actual_identity, db)


async def _finish_request(record_id: int, execution_id: str, identity: dict, db, status: str, **outcome) -> None:
    record = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.id == record_id, BusinessRecord.module == ACTION_MODULE, BusinessRecord.owner == identity["username"],
    ).with_for_update().execution_options(populate_existing=True))
    if record is None or record.status != "执行中" or record.data.get("execution_id") != execution_id:
        raise HTTPException(409, "业务执行后的确认记录状态不一致，请人工核对实际结果，禁止重试")
    data = {**record.data, **outcome, "finished_at": datetime.now(timezone.utc).isoformat()}
    record.status = status
    record.data = data
    db.add(_event(record.id, identity, "执行中", status, "已记录真实业务接口执行结果"))
    await db.commit()
