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
from app.agent_mcp.business_preflight import prepare_business_arguments
from app.agent_mcp.safety import reject_credentials, render_path, require_business_record_target, safe_result
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
    return {
        **spec.to_mcp(), "method": spec.method, "path": spec.path, "is_write": spec.is_write,
        "request_media_type": spec.request_media_type, "domain": spec.domain,
        "parameter_groups": parameter_groups,
        "required_parameters": {
            group: [field["name"] for field in fields if field["required"]]
            for group, fields in parameter_groups.items()
        },
    }


def search_tools(query: str, limit: int = 8) -> list[dict]:
    if not isinstance(query, str) or not query.strip() or type(limit) is not int or not 1 <= limit <= 12:
        raise HTTPException(422, "工具搜索需要非空关键词和 1 至 12 的结果数量")
    catalog = get_catalog(get_auth_context().application)
    return [public_tool(spec) for spec in catalog.search(query.strip(), limit=limit)]


def descriptor_fingerprint(spec) -> str:
    descriptor = {
        "name": spec.name, "method": spec.method, "path": spec.path,
        "input_schema": spec.input_schema, "is_write": spec.is_write,
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
    context = get_auth_context()
    identity = await authenticated_identity()
    spec = get_catalog(context.application).get(name)
    reject_credentials(arguments)
    if context.bearer in json.dumps(arguments, ensure_ascii=False):
        raise HTTPException(422, "工具参数不能包含当前登录凭据")
    params = spec.validate_arguments(arguments)
    reject_credentials(params)
    async with SessionLocal() as db:
        await require_business_record_target(spec, params, db)
        if not spec.is_write:
            return await execute_original(spec, params, case_origin=trusted_case_origin(), conversation_id=conversation_id)
        arguments = await prepare_business_arguments(spec, arguments, params, identity, db)
        params = spec.validate_arguments(arguments)
        reject_credentials(params)
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
            "params": params, "preview": preview, "case_origin": trusted_case_origin(), "summary": summary,
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
