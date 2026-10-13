"""本人跨对话的确认历史及非 MCP 操作存档，不从聊天内容推断决定。"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select, update

from app.agent_mcp.auth import get_auth_context
from app.agent_mcp.action_summary import summary_from_preview
from app.agent_mcp.safety import safe_result
from app.agent_mcp.service import ACTION_MODULE, STATUS_NAMES
from app.models import BusinessRecord, WorkflowEvent


PERSONAL_ACTION_MODULE = "personal_agent_action"
HISTORY_STATUSES = ("executing", "succeeded", "failed", "rejected")


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
    if action.get("type") not in {"create_task", "approve_contract"}:
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
        "conversation_id": data.get("conversation_id"), "conversation_title": data.get("conversation_title"),
    })


async def read_confirmation_history(identity, db, *, status="", page=1, page_size=20):
    if status and status not in HISTORY_STATUSES:
        raise HTTPException(422, "确认历史状态无效")
    conditions = [
        BusinessRecord.module.in_((ACTION_MODULE, PERSONAL_ACTION_MODULE)),
        BusinessRecord.owner == identity["username"],
        BusinessRecord.status.in_([name for name, value in STATUS_NAMES.items()
                                  if value == status or (not status and value in HISTORY_STATUSES)]),
    ]
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
    return {
        "items": [_history_item(record, decisions.get(record.id)) for record in records],
        "total": total, "page": page, "page_size": page_size,
    }
