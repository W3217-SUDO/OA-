"""本人跨对话的确认历史及非 MCP 操作存档，不从聊天内容推断决定。"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import and_, func, or_, select, update

from app.agent_mcp.auth import get_auth_context
from app.agent_mcp.action_summary import summary_from_preview
from app.agent_mcp.safety import safe_result
from app.agent_mcp.service import ACTION_MODULE, STATUS_NAMES
from app.models import BusinessRecord, WorkflowEvent
from app.areas.personal_agent import conversations
from app.areas.personal_agent.project_workspaces import state_workspace, workspace_catalog, workspace_key


PERSONAL_ACTION_MODULE = "personal_agent_action"
HISTORY_STATUSES = ("pending", "executing", "succeeded", "failed", "rejected")


async def project_personal_actions(state, identity, db):
    """按本人持久请求投影旧卡状态，只返回副本，不回写会话或业务记录。"""
    actions = state.get("pending_actions", [])
    references = {}
    for action in actions:
        action_type = action.get("type")
        if action_type not in {"mcp.call", "create_task", "approve_contract", "personal_mcp.call", "personal_mcp.connect"}:
            continue
        if action.get("requested_by") != identity["username"]:
            raise HTTPException(403, "待确认操作不属于当前账号")
        if action_type == "mcp.call":
            request_id = (action.get("payload") or {}).get("request_id")
            if not isinstance(request_id, str) or not request_id:
                raise HTTPException(422, "工具请求缺少有效编号")
            references[action["id"]] = "MCP-" + request_id
        else:
            references[action["id"]] = "PA-" + action["id"]
    if not references:
        return {**state, "pending_actions": [dict(action) for action in actions]}
    records = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.owner == identity["username"],
        or_(
            and_(BusinessRecord.module == ACTION_MODULE, BusinessRecord.serial_no.in_(
                [serial for serial in references.values() if serial.startswith("MCP-")])),
            and_(BusinessRecord.module == PERSONAL_ACTION_MODULE, BusinessRecord.serial_no.in_(
                [serial for serial in references.values() if serial.startswith("PA-")])),
        ),
    ).execution_options(populate_existing=True))).all()
    requests = {record.serial_no: record for record in records}
    legacy = [serial for serial in references.values() if serial.startswith("PA-") and serial not in requests]
    if legacy:
        # 无存档的升级前请求仍可人工决定；他人已存档请求不能冒充为旧请求。
        foreign = (await db.scalars(select(BusinessRecord.serial_no).where(
            BusinessRecord.module == PERSONAL_ACTION_MODULE,
            BusinessRecord.serial_no.in_(legacy), BusinessRecord.owner != identity["username"],
        ))).all()
        if foreign:
            raise HTTPException(403, "确认请求不属于当前账号")
    projected = []
    for action in actions:
        serial_no = references.get(action["id"])
        if serial_no is None:
            projected.append(dict(action))
            continue
        record = requests.get(serial_no)
        if record is None:
            if serial_no in legacy:
                projected.append(dict(action))
                continue
            raise HTTPException(404, "确认请求不存在或不属于当前账号")
        projected.append({**action, "status": STATUS_NAMES[record.status],
                          "error": record.data.get("error")})
    return {**state, "pending_actions": projected}


def _event(record_id, identity, before, after, comment=""):
    return WorkflowEvent(
        record_id=record_id, action="个人智能体人工确认" if before else "个人智能体准备操作",
        from_status=before, to_status=after, operator=identity["username"], comment=comment,
    )


def _personal_query(action_id, identity):
    return select(BusinessRecord).where(
        BusinessRecord.module == PERSONAL_ACTION_MODULE,
        BusinessRecord.serial_no == "PA-" + action_id,
        BusinessRecord.owner == identity["username"],
    )


async def prepare_personal_action(action, identity, state, db):
    if action.get("type") not in {"create_task", "approve_contract", "personal_mcp.call", "personal_mcp.connect"}:
        raise HTTPException(422, "不支持的待确认操作")
    if action.get("requested_by") != identity["username"]:
        raise HTTPException(403, "只能存档本人请求的操作")
    record = BusinessRecord(
        module=PERSONAL_ACTION_MODULE, serial_no="PA-" + action["id"],
        title=action["summary"][:255], status="待确认", owner=identity["username"],
        department=identity["department"], data={
            "action_id": action["id"], "action_type": action["type"],
            "payload": action["payload"], "summary": action["summary"],
            "requested_at": action.get("created_at") or None,
            "conversation_id": state["conversation_id"],
            "conversation_title": state["conversation_title"],
        },
    )
    db.add(record)
    await db.flush()
    db.add(_event(record.id, identity, "", "待确认"))
    return record


async def begin_personal_decision(action, decision, comment, identity, state, db):
    record = await db.scalar(_personal_query(action["id"], identity).with_for_update().execution_options(populate_existing=True))
    if record is None:
        if action.get('type') in {'personal_mcp.call', 'personal_mcp.connect'}:
            raise HTTPException(404, '个人MCP待确认请求不存在，禁止执行')
        # 升级前仍在原会话待确认的结构化请求，只在真实决定时存档，不回填聊天推测。
        record = await prepare_personal_action(action, identity, state, db)
    if record.status != "待确认":
        raise HTTPException(409, "请求已决定或执行结果尚待核对，禁止重复执行")
    if (record.data["action_type"] != action["type"] or record.data["payload"] != action["payload"]
            or record.data["conversation_id"] != state["conversation_id"]):
        raise HTTPException(409, "待确认内容与原请求不一致，请重新准备")
    execution_id = uuid4().hex
    data = {
        **record.data, "decision": decision, "operator": identity["username"],
        "comment": safe_result(comment[:1000], get_auth_context().bearer),
        "decided_at": datetime.now(timezone.utc).isoformat(), "execution_id": execution_id,
    }
    status = "执行中" if decision == "approved" else "已拒绝"
    changed = await db.execute(update(BusinessRecord).where(
        BusinessRecord.id == record.id, BusinessRecord.module == PERSONAL_ACTION_MODULE,
        BusinessRecord.owner == identity["username"], BusinessRecord.status == "待确认",
    ).values(status=status, data=data).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        await db.rollback()
        raise HTTPException(409, "请求正在被其他确认操作处理，禁止重复执行")
    db.add(_event(record.id, identity, "待确认", status, data["comment"]))
    # 原业务接口可能自行提交；先保存不可重放状态，不能等业务完成后才写确认记录。
    await db.commit()
    return record.id, execution_id


async def finish_personal_decision(record_id, execution_id, identity, db, *, result=None, error=None):
    record = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.id == record_id, BusinessRecord.module == PERSONAL_ACTION_MODULE,
        BusinessRecord.owner == identity["username"],
    ).with_for_update().execution_options(populate_existing=True))
    if record is None or record.status != "执行中" or record.data.get("execution_id") != execution_id:
        raise HTTPException(409, "执行后的确认记录状态不一致，请核对实际结果，禁止重试")
    status = "执行失败" if error is not None else "已执行"
    record.data = {
        **record.data, "finished_at": datetime.now(timezone.utc).isoformat(),
        "result": safe_result(jsonable_encoder(result), get_auth_context().bearer),
        "error": safe_result(jsonable_encoder(error), get_auth_context().bearer),
    }
    record.status = status
    db.add(_event(record.id, identity, "执行中", status, "已记录真实业务接口执行结果"))
    await db.commit()


def _history_item(record, decision_event):
    data = record.data
    personal = record.module == PERSONAL_ACTION_MODULE
    conversation_id = data.get("conversation_id")
    conversation_title = data.get("conversation_title")
    if not personal and data.get("context") is not None:
        context = data["context"]
        if not isinstance(context, dict):
            raise HTTPException(409, "工具请求的会话来源格式错误")
        contextual_id = context.get("conversation_id")
        if conversation_id and contextual_id and conversation_id != contextual_id:
            raise HTTPException(409, "工具请求的会话来源不一致")
        if contextual_id is not None:
            conversation_id = contextual_id
            conversation_title = context.get("conversation_title")
    return safe_result({
        "id": data["action_id"] if personal else data["request_id"],
        "source": "personal_action" if personal else "mcp",
        "action_type": data["action_type"] if personal else data["tool_name"],
        "summary": (data.get("summary") or record.title) if personal
                   else data.get("summary") or summary_from_preview(data["preview"]),
        "status": STATUS_NAMES[record.status],
        "requested_at": data.get("requested_at") if personal else record.created_at,
        "decided_at": data.get("decided_at"), "finished_at": data.get("finished_at"),
        "operator": decision_event.operator if decision_event else data.get("operator"),
        "comment": data.get("comment") or "", "result": data.get("result"), "error": data.get("error"),
        "conversation_id": conversation_id, "conversation_title": conversation_title,
    })


async def _with_operator_names(items, db):
    # 页面显示操作人姓名而不是登录账号（BUG20261031001）。
    from app.core.formatters import _person_reference_display, _user_display_map
    users = await _user_display_map({item.get("operator") for item in items if item.get("operator")}, db)
    for item in items:
        item["operator_display_name"] = _person_reference_display(item["operator"], users)[0] if item.get("operator") else None
    return items


async def _action_contexts(directory, identity, db):
    contexts = {}
    if directory is None:
        return contexts
    states = await conversations.read_conversation_states(directory)
    scopes = {workspace_key(state_workspace(state)): state_workspace(state) for state in states}
    catalog = await workspace_catalog(scopes.values(), identity, db)
    visible = {workspace_key(item) for item in catalog if item["available"]}
    for state in states:
        if workspace_key(state_workspace(state)) not in visible:
            continue
        for action in state["pending_actions"]:
            if not isinstance(action, dict) or action.get("type") not in {"mcp.call", "create_task", "approve_contract", "personal_mcp.call", "personal_mcp.connect"}:
                continue
            if action.get("requested_by") != identity["username"]:
                raise HTTPException(403, "操作卡不属于当前账号")
            if action["type"] == "mcp.call":
                request_id = (action.get("payload") or {}).get("request_id")
                if not isinstance(request_id, str) or not request_id:
                    raise HTTPException(422, "工具请求缺少有效编号")
                key = ("mcp", request_id)
            else:
                key = ("personal_action", action["id"])
            if key in contexts:
                raise HTTPException(409, "确认请求存在多个会话来源，不能猜测原会话")
            contexts[key] = (state, action)
    return contexts


def _context_item(item, context):
    if context is None:
        return {**item, "action_id": None, "can_decide": False}
    state, action = context
    if item.get("conversation_id") and item["conversation_id"] != state["conversation_id"]:
        raise HTTPException(409, "存档与原会话来源不一致")
    return {**item, "conversation_id": state["conversation_id"],
            "conversation_title": state["conversation_title"], "action_id": action["id"],
            "can_decide": item["status"] == "pending" and action.get("status") == "pending"}


def _legacy_item(state, action):
    return {
        "id": action["id"], "source": "personal_action", "action_type": action["type"],
        "summary": action["summary"], "status": "pending", "requested_at": action.get("created_at"),
        "decided_at": None, "finished_at": None, "operator": None, "comment": "", "result": None,
        "error": None, "conversation_id": state["conversation_id"], "conversation_title": state["conversation_title"],
        "action_id": action["id"], "can_decide": True,
    }


async def read_confirmation_history(identity, db, *, status="", page=1, page_size=20, directory=None):
    if status and status not in HISTORY_STATUSES:
        raise HTTPException(422, "确认历史状态无效")
    conditions = [
        BusinessRecord.module.in_((ACTION_MODULE, PERSONAL_ACTION_MODULE)),
        BusinessRecord.owner == identity["username"],
        BusinessRecord.status.in_([name for name, value in STATUS_NAMES.items()
                                  if value == status or (not status and value in HISTORY_STATUSES)]),
    ]
    contexts = await _action_contexts(directory, identity, db)
    legacy = []
    personal_ids = ["PA-" + key[1] for key in contexts if key[0] == "personal_action"]
    if personal_ids and status in ("", "pending"):
        archived = (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == PERSONAL_ACTION_MODULE, BusinessRecord.serial_no.in_(personal_ids),
        ))).all()
        if any(record.owner != identity["username"] for record in archived):
            raise HTTPException(403, "确认请求不属于当前账号")
        archived_ids = {record.serial_no for record in archived}
        legacy = [_legacy_item(state, action) for key, (state, action) in contexts.items()
                  if key[0] == "personal_action" and "PA-" + key[1] not in archived_ids
                  and action.get("status") == "pending"]
        legacy.sort(key=lambda item: (item["requested_at"] or "", item["id"]), reverse=True)
    total = await db.scalar(select(func.count()).select_from(BusinessRecord).where(*conditions))
    # 两类确认均写入 UTC ISO 时间；缺失真实决定时间的旧记录排后，不冒用创建时间。
    records = (await db.scalars(select(BusinessRecord).where(*conditions).order_by(
        BusinessRecord.data["decided_at"].as_string().desc().nulls_last(),
        BusinessRecord.id.desc(),
    ).offset((page - 1) * page_size).limit(page_size))).all()
    events = (await db.scalars(select(WorkflowEvent).where(
        WorkflowEvent.record_id.in_([record.id for record in records]),
        WorkflowEvent.from_status == "待确认", WorkflowEvent.to_status.in_(("执行中", "已拒绝")),
        WorkflowEvent.action.in_(("MCP人工确认", "个人智能体人工确认")),
    ).order_by(WorkflowEvent.id))).all() if records else []
    decisions = {event.record_id: event for event in events}
    items = []
    for record in records:
        item = _history_item(record, decisions.get(record.id))
        items.append(_context_item(item, contexts.get((item["source"], item["id"]))))
    await _with_operator_names(items, db)
    legacy_offset = max(0, (page - 1) * page_size - total)
    if len(items) < page_size:
        items.extend(legacy[legacy_offset:legacy_offset + page_size - len(items)])
    return {"items": safe_result(items), "total": total + len(legacy), "page": page, "page_size": page_size}


async def read_confirmation_detail(source, request_id, identity, db, *, directory):
    modules = {"mcp": (ACTION_MODULE, "MCP-"), "personal_action": (PERSONAL_ACTION_MODULE, "PA-")}
    if source not in modules:
        raise HTTPException(422, "确认历史来源无效")
    module, prefix = modules[source]
    record = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == module, BusinessRecord.serial_no == prefix + request_id,
    ).execution_options(populate_existing=True))
    if record is not None and record.owner != identity["username"]:
        raise HTTPException(403, "确认请求不属于当前账号")
    contexts = await _action_contexts(directory, identity, db)
    context = contexts.get((source, request_id))
    if record is None:
        if source != "personal_action" or context is None or context[1].get("status") != "pending":
            raise HTTPException(404, "确认请求不存在")
        item = _legacy_item(*context)
    else:
        event = await db.scalar(select(WorkflowEvent).where(
            WorkflowEvent.record_id == record.id, WorkflowEvent.from_status == "待确认",
            WorkflowEvent.to_status.in_(("执行中", "已拒绝")),
            WorkflowEvent.action.in_(("MCP人工确认", "个人智能体人工确认")),
        ).order_by(WorkflowEvent.id.desc()).limit(1))
        item = _context_item(_history_item(record, event), context)
    await _with_operator_names([item], db)
    action = None
    if context is not None:
        state, original = context
        if record is not None and source == "personal_action" and (
            record.data["action_type"] != original["type"] or record.data["payload"] != original["payload"]
        ):
            raise HTTPException(409, "存档与原操作内容不一致")
        if record is not None and source == "mcp" and original.get("preview") != record.data.get("preview"):
            raise HTTPException(409, "存档与原工具预览不一致")
        action = {**original, "status": item["status"], "error": item["error"]}
    elif record is not None and source == "personal_action":
        action = {"id": record.data["action_id"], "type": record.data["action_type"],
                  "payload": record.data["payload"], "summary": item["summary"], "status": item["status"],
                  "requested_by": record.owner, "created_at": record.data.get("requested_at"), "error": item["error"]}
    return safe_result({"item": item, "action": action, "conversation_id": item["conversation_id"],
                        "conversation_title": item["conversation_title"], "can_decide": item["can_decide"],
                        "request_preview": record.data.get("preview") if record is not None and source == "mcp" else None})
