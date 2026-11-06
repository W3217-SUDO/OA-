"""501631：员工离职/停用前，名下未结束任务必须转交（tgn 11-05 确认）。

- 只强制“负责人”的未结束任务：有就不让办理离职/停用；
- 发起人、协作人的未结束任务一并列出，转交时把这个人换成接收人，不单独挡；
- 已离职人员的存量任务由管理员在“离职人员未结束任务”清单里按人批量转交，不自动迁移。
只拦“办理离职/停用”这个动作，不影响登录和权限。
"""
from __future__ import annotations

import json
from datetime import date

from fastapi import HTTPException
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BusinessRecord, User, WorkflowEvent

# 和任务转交一致：这些状态的任务已经结束，不算、也不能转交。
CLOSED_TASK_STATUSES = ("已完成", "已验收", "已撤回", "已停止", "已取消", "待确认", "已拒绝", "已删除", "已回收")
GONE_HR_STATUSES = ("离职", "停用")
# 501631（tgn 11-06 确认）：老系统“调查任务”（调查授权）不是案件任务，不算未结束任务、不列入离职清单、不挡离职/停用。
LEGACY_INVESTIGATION_SOURCE = "Legal_Investigation_Task"


def _people(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").replace("，", ",")
    return [item.strip() for item in text.split(",") if item.strip()]


def _open_task_conditions():
    source_table = func.coalesce(BusinessRecord.data["source_table"].as_string(), "")
    return [BusinessRecord.module == "task", or_(BusinessRecord.status.is_(None), BusinessRecord.status.not_in(CLOSED_TASK_STATUSES)),
            source_table != LEGACY_INVESTIGATION_SOURCE]


async def _open_task_rows(db: AsyncSession, *, mention: str | None = None) -> list[dict]:
    """未结束任务，只取列表要用的字段（data 是 json 列，取整列会很慢）。mention 给了就先按文本粗筛。"""
    data = BusinessRecord.data
    conditions = _open_task_conditions()
    if mention is not None:
        conditions.append(or_(BusinessRecord.owner == mention, cast(data["initiator"], String).contains(mention), cast(data["collaborators"], String).contains(mention)))
    rows = (await db.execute(select(
        BusinessRecord.id, BusinessRecord.serial_no, BusinessRecord.title, BusinessRecord.status, BusinessRecord.owner,
        data["initiator"].as_string(), cast(data["collaborators"], String), data["case_no"].as_string(),
        data["deadline"].as_string(), data["task_type"].as_string(), data["migration_source"].as_string(),
    ).where(*conditions).order_by(BusinessRecord.id))).all()
    result = []
    for task_id, serial_no, title, status, owner, initiator, collaborators, case_no, deadline, task_type, source in rows:
        try:
            parsed = json.loads(collaborators) if collaborators else []
        except ValueError:
            parsed = collaborators
        result.append({
            "id": task_id, "serial_no": serial_no, "title": title, "status": status, "owner": owner or "",
            "initiator": (initiator or "").strip(), "collaborators": _people(parsed), "case_no": case_no or "",
            "deadline": (deadline or "")[:10], "task_type": task_type or "", "legacy": bool(source),
        })
    return result


def _roles_of(task: dict, username: str) -> list[str]:
    roles = []
    if task["owner"] == username:
        roles.append("负责人")
    if task["initiator"] == username:
        roles.append("发起人")
    if username in task["collaborators"]:
        roles.append("协作人")
    return roles


async def _display_names(usernames: set[str], db: AsyncSession) -> dict[str, str]:
    if not usernames:
        return {}
    rows = (await db.execute(select(User.username, User.display_name).where(User.username.in_(usernames)))).all()
    return {username: display_name or username for username, display_name in rows}


async def person_open_tasks(username: str, db: AsyncSession) -> list[dict]:
    """某人名下的未结束任务（负责人在前），每条带 roles。"""
    username = username.strip()
    if not username:
        return []
    items = []
    for task in await _open_task_rows(db, mention=username):
        roles = _roles_of(task, username)
        if roles:
            items.append({**task, "username": username, "roles": roles})
    items.sort(key=lambda item: ("负责人" not in item["roles"], item["id"]))
    names = await _display_names({username, *(item["owner"] for item in items)}, db)
    for item in items:
        item["owner_name"] = names.get(item["owner"], item["owner"])
        item["person_name"] = names.get(username, username)
    return items


async def ensure_no_owned_open_tasks(username: str, db: AsyncSession, *, action: str) -> None:
    """办理离职/停用前调用：还负责未结束任务就拒绝。"""
    username = (username or "").strip()
    if not username:
        return
    count = len([item for item in await person_open_tasks(username, db) if "负责人" in item["roles"]])
    if count:
        raise HTTPException(status_code=409, detail=f"此人还负责 {count} 条未结束任务，请先转交给其他人再{action}")


async def departed_open_tasks(db: AsyncSession) -> dict:
    """已离职/停用人员（以及新系统里没有账号的负责人）名下的未结束任务，按人分组。"""
    users = {username: (is_active, display_name or username, department or "") for username, is_active, display_name, department in
             (await db.execute(select(User.username, User.is_active, User.display_name, User.department))).all()}
    hr_gone = {}
    for owner, status, linked, title, department in (await db.execute(select(
        BusinessRecord.owner, BusinessRecord.status, BusinessRecord.data["username"].as_string(), BusinessRecord.title, BusinessRecord.department,
    ).where(BusinessRecord.module == "hr", BusinessRecord.status.in_(GONE_HR_STATUSES)))).all():
        name = (linked or owner or "").strip()
        if name:
            hr_gone[name] = (title, department or "")

    def gone(username: str) -> bool:
        if not username:
            return False
        if username in users:
            return users[username][0] is False or username in hr_gone
        return True

    groups: dict[str, dict] = {}
    for task in await _open_task_rows(db):
        people = {task["owner"], task["initiator"], *task["collaborators"]}
        for username in sorted(person for person in people if gone(person)):
            roles = _roles_of(task, username)
            if not roles or (username not in users and username not in hr_gone and "负责人" not in roles):
                continue  # 新系统没账号的人只在当负责人时列出（发起人、协作人留着不影响办理）
            group = groups.get(username)
            if group is None:
                known = users.get(username)
                name, department = (known[1], known[2]) if known else hr_gone.get(username, (username, ""))
                group = groups[username] = {"username": username, "name": name, "department": department,
                                            "no_account": username not in users, "owner_count": 0, "items": []}
            group["items"].append({**task, "roles": roles})
            if "负责人" in roles:
                group["owner_count"] += 1
    owner_names = await _display_names({item["owner"] for group in groups.values() for item in group["items"]}, db)
    people = sorted(groups.values(), key=lambda group: (-group["owner_count"], -len(group["items"]), group["username"]))
    for group in people:
        for item in group["items"]:
            item["owner_name"] = owner_names.get(item["owner"], item["owner"])
        group["total"] = len(group["items"])
    return {"people": people, "owner_total": sum(group["owner_count"] for group in people)}


async def handover_tasks(*, from_username: str, task_ids: list[int], recipient: str, comment: str, identity: dict, db: AsyncSession) -> dict:
    """把 from_username 在这些任务里的负责人/发起人/协作人身份交给 recipient；负责人变了的任务走转交（待接收）。"""
    from app.core.archived_case_people import add_case_assistant, is_actual_system_admin
    from app.core.case_task_members import _case_records_of_task, require_case_task_members
    from app.core.tasks import _active_task_username, _add_task_message_notifications, _record_task_manual_intervention

    from_username = from_username.strip()
    if not from_username:
        raise HTTPException(status_code=422, detail="请指定离职人员")
    recipient = await _active_task_username(recipient, db, field_name="接收人")
    if recipient == from_username:
        raise HTTPException(status_code=422, detail="接收人不能是离职人员本人")
    ids = sorted({int(item) for item in task_ids})
    if not ids:
        raise HTTPException(status_code=422, detail="请勾选要转交的任务")
    tasks = list((await db.scalars(select(BusinessRecord).where(*_open_task_conditions(), BusinessRecord.id.in_(ids)))).all())
    if len(tasks) != len(ids):
        raise HTTPException(status_code=409, detail="部分任务已结束或不存在，请刷新后再转交")
    recipient_user = await db.scalar(select(User).where(User.username == recipient))
    today = str(date.today())
    owner_changed = 0
    admin = is_actual_system_admin(identity)
    outsiders: list[str] = []
    for task in tasks:
        data = dict(task.data or {})
        collaborators = _people(data.get("collaborators"))
        is_owner = task.owner == from_username
        is_initiator = str(data.get("initiator") or "").strip() == from_username
        is_collaborator = from_username in collaborators
        if not (is_owner or is_initiator or is_collaborator):
            raise HTTPException(status_code=409, detail=f"任务 {task.serial_no} 已不在此人名下，请刷新后再转交")
        if is_owner:
            try:
                await require_case_task_members([recipient], db, task_data=data)
            except HTTPException:
                # 501631（tgn 11-05）：管理员转交时，接收人不是本案人员就自动加进案件“律师助理”栏（含归档案件），记案件日志
                cases = [record for record in await _case_records_of_task(data, db) if record.module == "case"] if admin else []
                if not cases:
                    outsiders.append(task.serial_no)
                    continue
                await add_case_assistant(cases[0], recipient, reason=f"离职任务转交（{task.serial_no}，{from_username} → {recipient}）", identity=identity, db=db)
        roles = []
        if is_initiator:
            data["initiator"] = recipient; roles.append("发起人")
        if is_collaborator:
            replaced = [recipient if person == from_username else person for person in collaborators]
            data["collaborators"] = list(dict.fromkeys(person for person in replaced if person != (recipient if is_owner else None)))
            roles.append("协作人")
        data["departure_handover"] = [*(data.get("departure_handover") or []), {
            "from": from_username, "to": recipient, "roles": (["负责人"] if is_owner else []) + roles, "at": today, "by": identity["username"]}]
        previous_status = task.status
        if is_owner:
            task.owner = recipient
            if recipient_user and recipient_user.department:
                task.department = recipient_user.department
            task.status = "待接收"
            data.update({"handoff_from": from_username, "handoff_recipient": recipient, "handed_off_at": today,
                         "handoff_auto_complete_at": "", "handoff_restarted": False})
            owner_changed += 1
        task.data = data
        if is_owner:
            await _record_task_manual_intervention(task, identity, db, action="离职任务转交")
        role_text = "、".join((["负责人"] if is_owner else []) + roles)
        event = WorkflowEvent(record_id=task.id, action="离职任务转交", from_status=previous_status, to_status=task.status, operator=identity["username"],
                              comment=f"{from_username} 离职，{role_text}转交给 {recipient}。{comment}".strip())
        await _add_task_message_notifications(task, event, db, content="离职人员的任务已转交给您." if is_owner else "任务人员已变更.")
    if outsiders:
        await db.rollback()
        shown = "、".join(outsiders[:10]) + (f" 等 {len(outsiders)} 条" if len(outsiders) > 10 else "")
        raise HTTPException(status_code=422, detail=f"接收人不是这些案件任务的本案人员：{shown}。请系统管理员转交（会自动把接收人加为律师助理），或换一位接收人")
    await db.commit()
    return {"updated": len(tasks), "owner_changed": owner_changed, "recipient": recipient}
