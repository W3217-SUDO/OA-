"""501631（tgn 11-05）：归档类案件仍锁定，只有真实系统管理员能增减本案人员；
管理员做离职任务转交时，接收人不是本案人员就自动加进该案件的“律师助理”栏。都记案件日志，不改阶段、不重算提成。"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BusinessRecord, User, WorkflowEvent

ARCHIVE_LOCKED_CASE_STATUSES = frozenset({"待归档审核", "归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"})


def is_archive_locked(case_record: BusinessRecord) -> bool:
    return case_record.status in ARCHIVE_LOCKED_CASE_STATUSES


def is_actual_system_admin(identity: dict) -> bool:
    from app.core.permissions import _require_actual_system_admin
    try:
        _require_actual_system_admin(identity)
    except HTTPException:
        return False
    return True


def require_archived_people_admin(identity: dict) -> None:
    if not is_actual_system_admin(identity):
        raise HTTPException(status_code=409, detail="案件已进入归档流程，只有系统管理员可以调整本案人员")


def _names(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item or "").strip()]
    return [part.strip() for part in str(value or "").replace("，", ",").split(",") if part.strip()]


def team_summary(data: dict) -> str:
    return "；".join([
        f"开庭律师 {data.get('hearing_lawyer') or '—'}",
        f"经办律师 {'、'.join(_names(data.get('handling_lawyers'))) or '—'}",
        f"律师助理 {'、'.join(_names(data.get('assistants') or data.get('assistant'))) or '—'}",
        f"客户管理人 {data.get('customer_manager') or '—'}",
    ])


async def add_case_assistant(case_record: BusinessRecord, username: str, *, reason: str, identity: dict, db: AsyncSession) -> None:
    """把 username 加进案件“律师助理”栏（追加在末尾，已在就不动），记案件日志。"""
    from app.core.cases import _case_team_payload
    data = dict(case_record.data or {})
    usernames = _names(data.get("assistant_usernames") or data.get("assistant_username"))
    if username.lower() in {name.lower() for name in usernames}:
        return
    user = await db.scalar(select(User).where(User.username == username))
    display = (user.display_name if user else "") or username
    names = _names(data.get("assistants") or data.get("assistant"))
    case_record.data = _case_team_payload(data, _names(data.get("handling_lawyers")), _names(data.get("handling_lawyer_usernames")),
                                          [*names, display], [*usernames, username])
    db.add(WorkflowEvent(record_id=case_record.id, action="自动加入律师助理", from_status=case_record.status, to_status=case_record.status,
                         operator=identity["username"], comment=f"{reason}：{display}（{username}）加入律师助理"))
