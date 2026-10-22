"""案件系统操作日志：读取真实旧操作记录与当前工作流事件。"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.case_document_sources import case_document_sources
from app.core.constants import CASE_EVENT_TIME_ZONE
from app.core.formatters import _case_event_display_time, _person_reference_display, _user_display_map
from app.database import get_db
from app.models import LegacyCaseLog, WorkflowEvent
from app.security import current_identity

router = APIRouter()
LogSource = Literal["current", "legacy"]


async def _log_queries(case_id: int, identity: dict, db: AsyncSession):
    from app.core.permissions import _ensure_case_read_module

    record = await _ensure_case_read_module(case_id, identity, db)
    sources = case_document_sources(record)
    source_ids = {int(item["id"]) for item in sources if item.get("id")}
    source_nos = {item["serial_no"] for item in sources if item.get("serial_no")}
    current = select(WorkflowEvent).where(WorkflowEvent.record_id.in_(source_ids))
    legacy = select(LegacyCaseLog).where(
        LegacyCaseLog.CaseNo.in_(source_nos), LegacyCaseLog.LogId > 0,
        LegacyCaseLog.LogType == 2,
        or_(LegacyCaseLog.IsActived.is_(None), LegacyCaseLog.IsActived == "T"),
    )
    return current, legacy, {int(item["id"]): item.get("serial_no", "") for item in sources if item.get("id")}


def _log_item(item, source: LogSource, source_nos: dict[int, str]) -> dict:
    if source == "current":
        return {
            "id": f"current:{item.id}", "source": source, "source_id": item.id,
            "action": item.action, "comment": item.comment, "operator": item.operator,
            "created_at": _case_event_display_time(item.created_at),
            "source_case_no": source_nos[item.record_id],
        }
    return {
        "id": f"legacy:{item.LogId}", "source": source, "source_id": item.LogId,
        "action": "历史系统操作", "comment": item.Content or "", "operator": item.CreateUser or "",
        # 旧表保存上海本地时间，不能按工作流的 UTC 时间转换。
        "created_at": item.CreateTime.replace(tzinfo=CASE_EVENT_TIME_ZONE) if item.CreateTime else None,
        "source_case_no": item.CaseNo,
    }


async def _display_names(items: list[dict], db: AsyncSession) -> None:
    users = await _user_display_map({item["operator"] for item in items}, db)
    for item in items:
        item["operator_display_name"] = _person_reference_display(item["operator"], users)[0]


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/system-logs")
async def list_case_system_logs(
    case_id: int, page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=100),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    current, legacy, source_nos = await _log_queries(case_id, identity, db)
    total = 0
    for query in (current, legacy):
        total += int(await db.scalar(select(func.count()).select_from(query.subquery())))
    pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, pages)
    end = page * page_size
    # 每个来源只读到目标页末；全局前 N 条必定包含在各来源前 N 条的并集中。
    events = (await db.scalars(current.order_by(WorkflowEvent.created_at.desc().nullslast(), WorkflowEvent.id.desc()).limit(end))).all()
    old_logs = (await db.scalars(legacy.order_by(LegacyCaseLog.CreateTime.desc().nullslast(), LegacyCaseLog.LogId.desc()).limit(end))).all()
    items = [_log_item(item, "current", source_nos) for item in events]
    items.extend(_log_item(item, "legacy", source_nos) for item in old_logs)
    oldest = datetime.min.replace(tzinfo=CASE_EVENT_TIME_ZONE)
    items.sort(key=lambda item: (item["created_at"] or oldest, item["source"], item["source_id"]), reverse=True)
    items = items[(page - 1) * page_size:end]
    await _display_names(items, db)
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/system-logs/{{source}}/{{log_id}}")
async def get_case_system_log(
    case_id: int, source: LogSource, log_id: int,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    current, legacy, source_nos = await _log_queries(case_id, identity, db)
    query = current.where(WorkflowEvent.id == log_id) if source == "current" else legacy.where(LegacyCaseLog.LogId == log_id)
    item = await db.scalar(query)
    if item is None:
        raise HTTPException(status_code=404, detail="案件系统日志不存在")
    result = _log_item(item, source, source_nos)
    await _display_names([result], db)
    return result
