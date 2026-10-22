"""管理员“变更记录”：查看每次新增、修改、删除、恢复的前后内容、操作人和来源（网页/MCP/智能体/系统），并一键还原。"""
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.areas.system.recycle_bin import TABLE_LABELS
from app.config import settings
from app.core import change_log
from app.core.permissions import _require_actual_system_admin
from app.data_models.change_logs import DataChangeLog
from app.database import get_db
from app.security import current_identity

router = APIRouter(prefix=settings.api_prefix + "/system/change-logs", tags=["变更记录"])
SOURCES = {"web": "网页", "mcp": "MCP", "agent": "智能体", "system": "系统"}
ACTIONS = {"insert": "新增", "update": "修改", "delete": "删除", "restore": "恢复"}
_VALUE_LIMIT = 300


def _short(value):
    text = value if isinstance(value, str) else str(value)
    return text if len(text) <= _VALUE_LIMIT else text[:_VALUE_LIMIT] + "…"


def _changes_view(changes: dict, full: bool) -> list[dict]:
    rows = []
    for column, change in (changes or {}).items():
        if isinstance(change, dict) and "__json__" in change:
            for key, (before, after) in change["__json__"].items():
                rows.append({"field": f"{column}.{key}", "before": before if full else _short(before), "after": after if full else _short(after)})
        elif isinstance(change, list) and len(change) == 2:
            rows.append({"field": column, "before": change[0] if full else _short(change[0]), "after": change[1] if full else _short(change[1])})
        else:
            rows.append({"field": column, "before": None, "after": _short(change)})
    return rows


def _view(log: DataChangeLog, full: bool = False) -> dict:
    return {
        "id": log.id, "table": log.table_name, "table_label": TABLE_LABELS.get(log.table_name, log.table_name), "row_id": log.row_id,
        "action": log.action, "action_label": ACTIONS.get(log.action, log.action), "summary": log.summary,
        "changes": _changes_view(log.changes, full), "actor": log.actor, "source": log.source, "source_label": SOURCES.get(log.source, log.source),
        "created_at": log.created_at, "reverted_at": log.reverted_at, "reverted_by": log.reverted_by, "revert_of": log.revert_of,
    }


class RevertInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    force: bool = False


@router.get("")
async def list_change_logs(
    table: str = Query("", max_length=64), row_id: str = Query("", max_length=128), actor: str = Query("", max_length=64),
    source: str = Query("", max_length=16), action: str = Query("", max_length=16), keyword: str = Query("", max_length=100),
    date_from: date | None = None, date_to: date | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    identity=Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    _require_actual_system_admin(identity)
    conditions = []
    if table:
        conditions.append(DataChangeLog.table_name == table)
    if row_id:
        conditions.append(DataChangeLog.row_id == row_id)
    if actor:
        conditions.append(DataChangeLog.actor == actor)
    if source:
        conditions.append(DataChangeLog.source == source)
    if action:
        conditions.append(DataChangeLog.action == action)
    if keyword.strip():
        conditions.append(DataChangeLog.summary.icontains(keyword.strip(), autoescape=True))
    if date_from:
        conditions.append(DataChangeLog.created_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc))
    if date_to:
        conditions.append(DataChangeLog.created_at <= datetime.combine(date_to, time.max, tzinfo=timezone.utc))
    total = await db.scalar(select(func.count()).select_from(DataChangeLog).where(*conditions))
    rows = (await db.scalars(select(DataChangeLog).where(*conditions).order_by(DataChangeLog.id.desc())
                             .offset((page - 1) * page_size).limit(page_size))).all()
    tables = [{"table": name, "label": TABLE_LABELS.get(name, name)} for name in sorted(change_log.soft_delete.soft_tables()) if change_log.loggable(name)]
    return {"items": [_view(row) for row in rows], "total": total or 0, "page": page, "page_size": page_size,
            "sources": SOURCES, "actions": ACTIONS, "tables": tables}


@router.get("/operations")
async def list_operation_logs(
    username: str = Query("", max_length=64), source: str = Query("", pattern="^(|mcp|agent)$"), write_only: bool = False,
    failed_only: bool = False, tool: str = Query("", max_length=100), date_from: date | None = None, date_to: date | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    identity=Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """智能体与 MCP 的每一次调用（查询、写入、失败、待确认）：谁、什么时候、调了什么、参数和结果。"""
    from app.data_models.mcp_tokens import McpAccessToken, McpCallLog
    _require_actual_system_admin(identity)
    conditions = []
    if username:
        conditions.append(McpCallLog.username == username)
    if source == "mcp":
        conditions.append(McpCallLog.token_id != 0)
    elif source == "agent":
        conditions.append(McpCallLog.token_id == 0)
    if write_only:
        conditions.append(McpCallLog.is_write == 1)
    if failed_only:
        conditions.append(McpCallLog.ok == 0)
    if tool.strip():
        conditions.append(McpCallLog.tool_name.icontains(tool.strip(), autoescape=True))
    if date_from:
        conditions.append(McpCallLog.created_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc))
    if date_to:
        conditions.append(McpCallLog.created_at <= datetime.combine(date_to, time.max, tzinfo=timezone.utc))
    total = await db.scalar(select(func.count()).select_from(McpCallLog).where(*conditions))
    rows = (await db.execute(select(McpCallLog, McpAccessToken.name).outerjoin(McpAccessToken, McpAccessToken.id == McpCallLog.token_id)
                             .where(*conditions).order_by(McpCallLog.id.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    items = [{"id": log.id, "username": log.username, "source": "agent" if log.token_id == 0 else "mcp",
              "source_label": "站内智能体" if log.token_id == 0 else "MCP", "token_name": token_name, "tool_name": log.tool_name,
              "is_write": bool(log.is_write), "ok": bool(log.ok), "pending": '"status": "pending"' in (log.detail or ""),
              "detail": log.detail, "created_at": log.created_at} for log, token_name in rows]
    return {"items": items, "total": total or 0, "page": page, "page_size": page_size}


@router.get("/{log_id}")
async def get_change_log(log_id: int, identity=Depends(current_identity), db: AsyncSession = Depends(get_db)):
    _require_actual_system_admin(identity)
    log = await db.get(DataChangeLog, log_id)
    if log is None:
        raise HTTPException(404, "变更记录不存在")
    return _view(log, full=True)


@router.post("/{log_id}/revert")
async def revert_change_log(log_id: int, body: RevertInput, identity=Depends(current_identity), db: AsyncSession = Depends(get_db)):
    _require_actual_system_admin(identity)
    return await change_log.revert(db, log_id, identity["username"], force=body.force)
