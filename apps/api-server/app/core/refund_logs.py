"""按案件共享和指定费用范围归集退费日志，保留历史人工记录。"""

from collections import Counter

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.case_document_sources import case_document_sources
from app.core.formatters import _person_reference_display, _user_display_map
from app.models import BusinessRecord, LegacyCaseLog, WorkflowEvent


REFUND_LOG_LABELS = {"court": "法院", "received": "到账", "other": "其他"}


def _case_ids(data: dict) -> set[int]:
    return {int(data[key]) for key in ("case_id", "case_record_id")
            if str(data.get(key) or "").isdigit() and int(data[key]) > 0}


async def refund_fee_case(fee: BusinessRecord, db: AsyncSession) -> BusinessRecord | None:
    """验证费用实际案件关联；历史仅有案号时按唯一业务编号解析。"""
    data = fee.data or {}
    case_ids = _case_ids(data)
    if any(data.get(key) not in (None, "", 0, "0") and str(data[key]) not in {str(item) for item in case_ids}
           for key in ("case_id", "case_record_id")):
        raise HTTPException(status_code=409, detail="案件费用的案件ID无效，请先修正关联资料")
    case_no = str(data.get("case_no") or "").strip()
    if not case_ids and not case_no:
        return None
    cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module.in_(("case", "ipr_case")),
        or_(BusinessRecord.id.in_(case_ids), BusinessRecord.serial_no == case_no),
    ))).all())
    linked_by_id = [item for item in cases if item.id in case_ids]
    if len(linked_by_id) != len(case_ids):
        raise HTTPException(status_code=409, detail="案件费用关联的案件不存在，请先修正关联资料")
    if len(linked_by_id) > 1:
        raise HTTPException(status_code=409, detail="案件费用关联了不同案件，请先修正关联资料")
    if linked_by_id:
        case = linked_by_id[0]
        valid_numbers = {item["serial_no"] for item in case_document_sources(case) if item.get("serial_no")}
        if case_no and case_no not in valid_numbers:
            raise HTTPException(status_code=409, detail="案件费用的案件ID与案号不一致，请先修正关联资料")
        return case
    return next((item for item in cases if item.serial_no == case_no), None)


def _belongs_to_case(data: dict, case_ids: set[int], case_nos: set[str], *, fee_specific: bool) -> bool:
    linked_ids = _case_ids(data)
    linked_no = str(data.get("case_no") or "").strip()
    if linked_ids and not linked_ids.issubset(case_ids):
        return False
    if linked_no and linked_no not in case_nos:
        return False
    return bool(linked_ids or linked_no or fee_specific)


def _mirror_signature(operator: str, content: str, created_at, label: str) -> tuple:
    # 两种当前模型均由同一事务的func.now()生成时间，保留完整精度，不猜测时间窗口。
    return operator, content or "", created_at, label


async def refund_fee_log_items(fee: BusinessRecord, db: AsyncSession) -> list[dict]:
    case = await refund_fee_case(fee, db)
    sources = case_document_sources(case) if case else []
    case_ids = {item["id"] for item in sources if item.get("id")}
    case_nos = {item["serial_no"] for item in sources if item.get("serial_no")}
    fee_column = BusinessRecord.data["case_fee_id"].as_integer()
    candidates = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case_log",
        BusinessRecord.data["kind"].as_string() == "refund",
        or_(
            fee_column == fee.id,
            and_(fee_column.is_(None), or_(
                BusinessRecord.data["case_id"].as_integer().in_(case_ids),
                BusinessRecord.data["case_record_id"].as_integer().in_(case_ids),
                BusinessRecord.data["case_no"].as_string().in_(case_nos),
            )),
        ),
    ).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()))).all())
    records = [item for item in candidates if not case or _belongs_to_case(
        item.data or {}, case_ids, case_nos, fee_specific=(item.data or {}).get("case_fee_id") == fee.id,
    )]
    items = [{
        "id": item.id, "content": item.description, "operator": item.owner,
        "kind": "refund", "type": REFUND_LOG_LABELS.get(str((item.data or {}).get("refund_type") or ""), "退费"),
        "created_at": item.created_at, "source": "current",
    } for item in records if item.status != "已删除"]

    # 新记录按事件ID去重；旧记录仅在同一费用、时间和分类内逐条消除镜像。
    fee_records = [item for item in records if (item.data or {}).get("case_fee_id") == fee.id]
    mirrored_ids = {(item.data or {}).get("workflow_event_id") for item in fee_records if (item.data or {}).get("workflow_event_id")}
    signatures = Counter(_mirror_signature(
        item.owner, item.description, item.created_at, REFUND_LOG_LABELS.get(str((item.data or {}).get("refund_type") or ""), "退费"),
    ) for item in fee_records if not (item.data or {}).get("workflow_event_id"))
    events = list((await db.scalars(select(WorkflowEvent).where(
        WorkflowEvent.record_id == fee.id, WorkflowEvent.action.like("添加%退费日志"),
    ).order_by(WorkflowEvent.created_at.desc(), WorkflowEvent.id.desc()))).all())
    for event in events:
        label = event.action.removeprefix("添加").removesuffix("退费日志")
        signature = _mirror_signature(event.operator, event.comment, event.created_at, label)
        if event.id in mirrored_ids:
            continue
        if signatures[signature]:
            signatures[signature] -= 1
            continue
        items.append({"id": f"legacy-{event.id}", "content": event.comment, "operator": event.operator,
                      "kind": "refund", "type": label, "created_at": event.created_at, "source": "current"})

    historical_logs = list((await db.scalars(select(LegacyCaseLog).where(
        LegacyCaseLog.CaseNo.in_(case_nos), LegacyCaseLog.LogId > 0,
        LegacyCaseLog.LogType == 1,
        or_(LegacyCaseLog.IsActived.is_(None), LegacyCaseLog.IsActived == "T"),
    ).order_by(LegacyCaseLog.CreateTime.desc(), LegacyCaseLog.LogId.desc()))).all()) if case_nos else []
    items.extend({"id": f"legacy-case-{item.LogId}", "content": item.Content or "", "operator": item.CreateUser or "",
                  "kind": "case", "type": "历史案件日志", "created_at": item.CreateTime, "source": "legacy"}
                 for item in historical_logs)
    users_by_username = await _user_display_map({item["operator"] for item in items}, db)
    for item in items:
        item["operator_display_name"] = _person_reference_display(item["operator"], users_by_username)[0]
    items.sort(key=lambda item: (str(item["created_at"] or ""), str(item["id"])), reverse=True)
    return items
