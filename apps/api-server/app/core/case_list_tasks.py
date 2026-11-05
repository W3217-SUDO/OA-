"""案件列表中的真实任务投影，沿用旧系统未完成任务的优先顺序。"""
from sqlalchemy import String, func, or_, select
from app.models import BusinessRecord


OPEN_TASK_STATUSES = {"待接收", "待处理", "处理中", "进行中"}


def _case_task_links(ids, numbers):
    text_ids = [str(case_id) for case_id in ids]
    links = [BusinessRecord.data["case_id"].as_string().cast(String).in_(text_ids),
             BusinessRecord.data["case_record_id"].as_string().cast(String).in_(text_ids),
             BusinessRecord.data["case_no"].as_string().in_(numbers)]
    links.extend(BusinessRecord.data["case_nos"].cast(String).contains(f'"{number}"') for number in numbers)
    array_ids = func.replace(func.replace(func.replace(BusinessRecord.data["case_ids"].cast(String), " ", ""), "[", ","), "]", ",")
    links.extend(or_(array_ids.contains(f",{case_id},"), array_ids.contains(f',"{case_id}",')) for case_id in ids)
    return links


_LINK_FIELDS = ("case_id", "case_record_id", "case_no", "case_nos", "case_ids")


async def _linked_task_ids(db, ids, numbers) -> list[int]:
    """501629：先只读未完成任务的几个关联字段，在内存里粗筛出可能关联这些案件的任务 id。

    原来直接对全部任务逐条做几十个 JSON 文本 LIKE，案件列表这一步要 6 秒多；粗筛用的是同样的字段文本、
    只要出现案件 id 或案号就留下（只多不少），最后仍用原来的条件精确判断，结果不变。
    """
    tokens = {str(value) for value in ids} | {str(value) for value in numbers if value}
    if not tokens:
        return []
    rows = (await db.execute(select(
        BusinessRecord.id, *(BusinessRecord.data[key].cast(String) for key in _LINK_FIELDS),
        BusinessRecord.data["case_no"].as_string(),  # 原条件对 case_no 按解析后的文本比，这里也带上
    ).where(BusinessRecord.module == "task", BusinessRecord.status.in_(OPEN_TASK_STATUSES)))).all()
    return [row[0] for row in rows if any(text and any(token in text for token in tokens) for text in row[1:])]


def _task_case_keys(task):
    data = task.data or {}
    ids = {str(data.get(key)) for key in ("case_id", "case_record_id") if data.get(key) not in (None, "")}
    ids.update(str(value) for value in (data.get("case_ids") or []) if value not in (None, ""))
    numbers = {str(data.get("case_no"))} if data.get("case_no") else set()
    numbers.update(str(value) for value in (data.get("case_nos") or []) if value)
    return ids, numbers


def _task_due(task):
    data = task.data or {}
    raw = str(data.get("deadline") or data.get("task_end_time") or data.get("TaskEndTime") or "").strip()
    return raw[:10] if len(raw) >= 10 and raw[4] == "-" else ""


def _open_task(task):
    data = task.data or {}
    return task.status in OPEN_TASK_STATUSES and data.get("is_active") is not False and data.get("IsActived") != "F"


async def case_deadlines(cases, db):
    """案件期限：有未完成的案件任务取最早截止日，没有就是今天加一年（旧系统 P_Legal_Case_AutoUpdate，陶威 11-02 同意）。

    不看办理人；已完成、已取消（含作废的迁移案件自动任务）等终态不算。显示和查询时现算，不再用同步来的 data.deadline。
    """
    from datetime import datetime, timedelta, timezone

    today = datetime.now(timezone(timedelta(hours=8))).date()
    default = today.replace(year=today.year + 1) if not (today.month == 2 and today.day == 29) else today + timedelta(days=365)
    result = {case["id"]: default.isoformat() for case in cases}
    if not cases:
        return result
    ids = {case["id"] for case in cases}
    by_no = {case["serial_no"]: case["id"] for case in cases}
    candidates = await _linked_task_ids(db, ids, set(by_no))
    if not candidates:
        return result
    tasks = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "task", BusinessRecord.id.in_(candidates), or_(*_case_task_links(ids, set(by_no))),
        BusinessRecord.status.in_(OPEN_TASK_STATUSES),
    ))).all()
    earliest = {}
    for task in tasks:
        due = _task_due(task)
        if not due or not _open_task(task):
            continue
        task_ids, task_nos = _task_case_keys(task)
        for case_id in {int(value) for value in task_ids if value.isdigit() and int(value) in ids} | {by_no[no] for no in task_nos if no in by_no}:
            if case_id not in earliest or due < earliest[case_id]:
                earliest[case_id] = due
    result.update(earliest)
    return result


async def attach_case_list_tasks(items, identity, db):
    if not items:
        return items
    from app.core.formatters import _task_display_dicts
    ids = {item["id"] for item in items}
    numbers = {item["serial_no"] for item in items}
    links = _case_task_links(ids, numbers)
    candidates = await _linked_task_ids(db, ids, numbers)
    conditions = [BusinessRecord.module == "task", BusinessRecord.id.in_(candidates), or_(*links),
                  BusinessRecord.status.in_(OPEN_TASK_STATUSES)]
    if identity.get("role") != "admin":
        conditions.append(or_(BusinessRecord.owner == identity["username"],
            BusinessRecord.data["initiator"].as_string() == identity["username"],
            BusinessRecord.data["collaborators"].cast(String).contains(f'"{identity["username"]}"')))
    tasks = list((await db.scalars(select(BusinessRecord).where(*conditions))).all()) if candidates else []
    tasks = [task for task in tasks if (task.data or {}).get("is_active") is not False and (task.data or {}).get("IsActived") != "F"]
    displays = await _task_display_dicts(tasks, db) if tasks else []
    def order(task):
        data = task.get("data") or {}
        deadline = data.get("deadline") or data.get("task_end_time") or data.get("TaskEndTime") or "9999"
        return (0 if task.get("workflow_status") in {"待接收", "待处理"} else 1, str(deadline), task["id"])
    displays.sort(key=order)
    deadlines = await case_deadlines(items, db)
    for item in items:
        match = next((task for task in displays if item["id"] in task.get("case_ids", []) or item["serial_no"] in task.get("case_nos", [])), None)
        data = dict(item.get("data") or {})
        for key in ("task_id", "task_serial_no", "task_name", "task_content", "task_handler", "task_handler_display_name", "task_due_date", "task_deadline", "task_owner", "task_owner_display_name"):
            data.pop(key, None)
        if match:
            source = match.get("data") or {}
            data.update(task_id=match["id"], task_serial_no=match["serial_no"], task_name=match["title"],
                task_content=source.get("content") or source.get("task_content") or match.get("description") or "",
                task_handler=match["owner"], task_handler_display_name=match.get("owner_display_name"),
                task_due_date=source.get("deadline") or source.get("task_end_time") or source.get("TaskEndTime") or "")
        # 案件期限按任务现算，覆盖同步来的旧值（列表“到期日期”显示它）。
        data["deadline"] = data["case_deadline"] = deadlines[item["id"]]
        item["data"] = data
    return items
