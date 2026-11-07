"""任务交接的期限规则，单条转交和批量交接共用（501742）。"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import HTTPException


def _task_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    raw_value = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(raw_value).replace(tzinfo=None)
    except ValueError:
        try:
            return datetime.combine(date.fromisoformat(raw_value), datetime.max.time())
        except ValueError:
            return None


def resolve_handoff_deadline(task, requested_end_at: datetime | None, parameters, now: datetime) -> tuple[datetime | None, dict]:
    """返回 (交接后的结束时间, 要写进任务的期限字段)。填的时间不合规就报错；超过任务类型上限就缩短到上限。"""
    from app.core.task_type_rules import handoff_skip_days

    data = task.data or {}
    start_at = _task_datetime(data.get("start_at") or data.get("task_begin_time") or data.get("TaskBeginTime")) or _task_datetime(task.created_at)
    existing_end_at = _task_datetime(data.get("end_at") or data.get("deadline") or data.get("task_end_time") or data.get("TaskEndTime"))
    requested = requested_end_at.replace(tzinfo=None) if requested_end_at else None
    if requested is not None:
        if requested < now:
            raise HTTPException(status_code=422, detail="交接结束时间不能早于当前时间")
        if start_at and requested <= start_at:
            raise HTTPException(status_code=422, detail="交接结束时间必须晚于任务开始时间")
    handoff_limit_days = handoff_skip_days(data, parameters)
    handoff_end_at = requested or existing_end_at
    if handoff_end_at is not None and handoff_limit_days is not None:
        limit_at = now + timedelta(days=handoff_limit_days)
        # Legacy TaskNodeService uses NodeEndTime.Subtract(limit).Days > 0.
        # Keep that whole-day threshold instead of a stricter instant-by-instant min.
        if (handoff_end_at - limit_at).days > 0:
            handoff_end_at = limit_at
    if handoff_end_at is not None and start_at and handoff_end_at <= start_at:
        if requested is not None:
            raise HTTPException(status_code=422, detail="交接结束时间必须晚于任务开始时间且不超过任务类型期限")
        # A historical malformed range cannot be made valid by this handoff.
        # Preserve it rather than creating a new start/end inversion.
        handoff_end_at = existing_end_at
    if handoff_end_at is None or (requested is None and handoff_end_at == existing_end_at):
        return handoff_end_at, {}
    return handoff_end_at, {
        "deadline": str(handoff_end_at.date()), "end_at": handoff_end_at.isoformat(timespec="seconds"),
        "handoff_requested_end_at": requested_end_at.isoformat(timespec="seconds") if requested_end_at else "",
        "handoff_limit_days": handoff_limit_days,
    }
