"""工作台审批驳回提醒：当前账号提交后被驳回的单据、驳回原因和跳转入口。"""
from datetime import datetime, timezone

from app.core.constants import CASE_EVENT_TIME_ZONE
from app.core.dashboard import dashboard_scope
from app.core.dependencies import BusinessRecord, WorkflowEvent, and_, func, or_, select
from app.core.investigation import _is_investigation_task
from app.core.record_json_text_query import projected_record_condition, record_json_text_projection

# 每类单据最多读取最新的若干条，合并排序后只展示其中最新的这些记录。
REJECTION_LIMIT = 20
REJECTED_STATUSES = ("已拒绝", "已驳回", "亏损归档拒绝")


def _event_time(value: datetime) -> str:
    # SQLite 保存无时区的 UTC 时间，PostgreSQL 返回带时区时间，统一换算为业务时区。
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(CASE_EVENT_TIME_ZONE).strftime("%Y-%m-%d %H:%M")


def _data_time(value) -> str:
    return str(value or "").replace("T", " ")[:16]


def _row(item: BusinessRecord, label: str, route: str, reason="", by="", at="") -> dict:
    return {
        "id": item.id, "type": label, "serial_no": item.serial_no, "title": item.title,
        "reason": str(reason or "").strip(), "rejected_by": str(by or "").strip(),
        "rejected_at": at, "route": route,
    }


async def _event_rows(db, items: list[BusinessRecord], label: str, route: str) -> list[dict]:
    """驳回原因、驳回人和时间取自把记录推入驳回状态的最近一次流转事件。"""
    latest: dict[int, WorkflowEvent] = {}
    if items:
        events = (await db.scalars(select(WorkflowEvent).where(
            WorkflowEvent.record_id.in_([item.id for item in items]),
            WorkflowEvent.to_status.in_(REJECTED_STATUSES),
        ).order_by(WorkflowEvent.created_at.desc(), WorkflowEvent.id.desc()))).all()
        for event in events:
            latest.setdefault(event.record_id, event)
    rows = []
    for item in items:
        event = latest.get(item.id)
        if event is None:
            rows.append(_row(item, label, route))
        else:
            rows.append(_row(item, label, route, event.comment, event.operator, _event_time(event.created_at)))
    return rows


async def _limited_records(db, conditions) -> tuple[int, list[BusinessRecord]]:
    total = await db.scalar(select(func.count()).select_from(BusinessRecord).where(*conditions)) or 0
    items = (await db.scalars(select(BusinessRecord).where(*conditions).order_by(
        BusinessRecord.updated_at.desc(), BusinessRecord.id.desc(),
    ).limit(REJECTION_LIMIT))).all()
    return total, list(items)


async def _task_rejections(username: str, db) -> tuple[int, list[dict]]:
    # 任务由发起人收到被拒绝的提醒；调查子任务不属于一般任务中心，与待办统计保持一致。
    initiator = func.trim(func.coalesce(BusinessRecord.data["initiator"].as_string(), ""))
    items = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "task", BusinessRecord.status == "已拒绝", initiator == username,
    ).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all()
    items = [item for item in items if not _is_investigation_task(item)]
    return len(items), await _event_rows(db, items[:REJECTION_LIMIT], "任务", "task-my-created")


async def _contract_rejections(username: str, db) -> tuple[int, list[dict]]:
    total, items = await _limited_records(db, [
        BusinessRecord.module == "contract", BusinessRecord.owner == username,
        BusinessRecord.status.in_(("已拒绝", "已驳回")),
    ])
    return total, await _event_rows(db, items, "合同", "contract-audit-refused")


async def _clue_rejections(username: str, db) -> tuple[int, list[dict]]:
    total, items = await _limited_records(db, [
        BusinessRecord.module == "clue", BusinessRecord.owner == username,
        BusinessRecord.status.in_(("已驳回", "已拒绝")),
    ])
    return total, await _event_rows(db, items, "调查线索", "clue-my-refused")


async def _seal_rejections(username: str, db) -> tuple[int, list[dict]]:
    # 用印驳回时审批意见、审批人和时间已直接写入申请记录。
    total, items = await _limited_records(db, [
        BusinessRecord.module == "seal", BusinessRecord.owner == username,
        BusinessRecord.status == "已拒绝",
    ])
    rows = []
    for item in items:
        data = item.data or {}
        rows.append(_row(item, "用印", "seal-my-refused", data.get("approval_comment"), data.get("approver"), _data_time(data.get("approved_at"))))
    return total, rows


async def _case_archive_rejections(username: str, db) -> tuple[int, list[dict]]:
    # 普通归档被驳回后案件状态会恢复，驳回原因保留在案件数据中，口径与待办统计一致。
    projection, data_text = record_json_text_projection(db, ("archive_submitter", "archive_reject_reason"))
    submitter = func.trim(func.coalesce(data_text["archive_submitter"], ""))
    reject_reason = func.trim(func.coalesce(data_text["archive_reject_reason"], ""))
    total, items = await _limited_records(db, [
        BusinessRecord.module == "case",
        projected_record_condition(projection, and_(
            submitter == username,
            or_(BusinessRecord.status == "亏损归档拒绝", reject_reason != ""),
        )),
    ])
    rows = []
    for item in items:
        data = item.data or {}
        # 终审与内部审核各自记录审核人和时间，驳回发生在较晚的那一次。
        internal_at, final_at = str(data.get("archive_internal_reviewed_at") or ""), str(data.get("archive_reviewed_at") or "")
        if internal_at > final_at:
            by, at = data.get("archive_internal_reviewer"), internal_at
        else:
            by, at = data.get("archive_reviewer"), final_at
        rows.append(_row(item, "案件归档", "case-archive-refused", data.get("archive_reject_reason"), by, _data_time(at)))
    return total, rows


_SOURCES = (
    ("task", _task_rejections), ("contract", _contract_rejections), ("clue", _clue_rejections),
    ("seal", _seal_rejections), ("case", _case_archive_rejections),
)


async def dashboard_rejections(identity, db):
    _, modules = await dashboard_scope(identity, db)
    total = 0
    rows: list[dict] = []
    for module, load in _SOURCES:
        if module not in modules:
            continue
        count, items = await load(identity["username"], db)
        total += count
        rows.extend(items)
    rows.sort(key=lambda row: row["rejected_at"], reverse=True)
    return {"rejections": rows[:REJECTION_LIMIT], "rejection_total": total}
