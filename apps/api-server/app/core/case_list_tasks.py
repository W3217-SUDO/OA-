"""案件列表中的真实任务投影，沿用旧系统未完成任务的优先顺序。"""
from sqlalchemy import String, func, or_, select
from app.models import BusinessRecord


async def attach_case_list_tasks(items, identity, db):
    if not items:
        return items
    from app.core.formatters import _task_display_dicts
    ids = {item["id"] for item in items}
    numbers = {item["serial_no"] for item in items}
    text_ids = [str(case_id) for case_id in ids]
    links = [BusinessRecord.data["case_id"].as_string().cast(String).in_(text_ids),
             BusinessRecord.data["case_record_id"].as_string().cast(String).in_(text_ids),
             BusinessRecord.data["case_no"].as_string().in_(numbers)]
    links.extend(BusinessRecord.data["case_nos"].cast(String).contains(f'"{number}"') for number in numbers)
    array_ids = func.replace(func.replace(func.replace(BusinessRecord.data["case_ids"].cast(String), " ", ""), "[", ","), "]", ",")
    links.extend(or_(array_ids.contains(f",{case_id},"), array_ids.contains(f',"{case_id}",')) for case_id in ids)
    conditions = [BusinessRecord.module == "task", or_(*links),
                  BusinessRecord.status.in_({"待接收", "待处理", "处理中", "进行中"})]
    if identity.get("role") != "admin":
        conditions.append(or_(BusinessRecord.owner == identity["username"],
            BusinessRecord.data["initiator"].as_string() == identity["username"],
            BusinessRecord.data["collaborators"].cast(String).contains(f'"{identity["username"]}"')))
    tasks = list((await db.scalars(select(BusinessRecord).where(*conditions))).all())
    tasks = [task for task in tasks if (task.data or {}).get("is_active") is not False and (task.data or {}).get("IsActived") != "F"]
    displays = await _task_display_dicts(tasks, db) if tasks else []
    def order(task):
        data = task.get("data") or {}
        deadline = data.get("deadline") or data.get("task_end_time") or data.get("TaskEndTime") or "9999"
        return (0 if task.get("workflow_status") in {"待接收", "待处理"} else 1, str(deadline), task["id"])
    displays.sort(key=order)
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
        item["data"] = data
    return items
