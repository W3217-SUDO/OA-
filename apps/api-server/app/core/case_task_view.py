"""案件上下文中的任务只读详情，不授予任务处理权限。"""
from fastapi import HTTPException
from sqlalchemy import String, or_, select

from app.models import BusinessRecord, FileAttachment, WorkflowEvent
from app.core.case_document_sources import case_document_sources


def case_task_relation(case):
    sources = case_document_sources(case)
    ids = [item["id"] for item in sources]
    numbers = [item["serial_no"] for item in sources if item.get("serial_no")]
    return or_(
        BusinessRecord.data["case_id"].as_integer().in_(ids),
        BusinessRecord.data["case_record_id"].as_integer().in_(ids),
        BusinessRecord.data["case_no"].as_string().in_(numbers),
        *[BusinessRecord.data["case_nos"].cast(String).contains(f'"{number}"') for number in numbers],
    )


async def visible_case_task(case_id, task_id, identity, db):
    from app.core.permissions import _ensure_record_module
    case = await _ensure_record_module(case_id, "case", identity, db)
    task = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.id == task_id, BusinessRecord.module == "task", case_task_relation(case),
    ))
    if task is None:
        raise HTTPException(404, "该案件不存在此任务")
    return task


async def case_task_detail(case_id, task_id, identity, db):
    from app.core.formatters import _task_display_dict, _person_reference_display, _user_display_map
    from app.core.storage import _attachment_dict
    task = await visible_case_task(case_id, task_id, identity, db)
    events = list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == task.id)
        .order_by(WorkflowEvent.created_at.desc(), WorkflowEvent.id.desc()))).all())
    files = list((await db.scalars(select(FileAttachment).where(
        FileAttachment.record_id == task.id,
        FileAttachment.category.in_(["任务资料附件", "任务反馈附件"]),
    ).order_by(FileAttachment.id))).all())
    users = await _user_display_map({event.operator for event in events} | {item.uploader for item in files}, db)
    attachments = [{**_attachment_dict(item, task), "case_context_id": case_id, "task_context_id": task.id,
                    "uploader_display_name": _person_reference_display(item.uploader, users)[0]} for item in files]
    return {
        "record": await _task_display_dict(task, db),
        "history": [{"id": item.id, "action": item.action, "operator": item.operator,
                     "operator_display_name": _person_reference_display(item.operator, users)[0],
                     "comment": item.comment, "from_status": item.from_status, "to_status": item.to_status,
                     "created_at": item.created_at} for item in events],
        "materials": [item for item in attachments if item["category"] == "任务资料附件"],
        "feedbacks": [item for item in attachments if item["category"] == "任务反馈附件"],
    }
