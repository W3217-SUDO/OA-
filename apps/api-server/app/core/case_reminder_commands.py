"""案件提醒创建的共享业务命令；提交由入口负责。"""

from app.core.dependencies import (
    AsyncSession,
    BusinessRecord,
    HTTPException,
    WorkflowEvent,
    datetime,
)
from app.models_shared import CaseReminderInput


async def create_case_reminder_record(
    case_id: int, body: CaseReminderInput, identity: dict, db: AsyncSession
):
    from app.core.permissions import (
        _ensure_record_module,
        _require_case_note_write_access,
    )

    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_note_write_access(case_record, identity, db)
    if body.reminder_date > body.deadline:
        raise HTTPException(status_code=422, detail="提醒日期不能晚于截止日期")
    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="请输入提醒内容")
    item = BusinessRecord(
        module="case_reminder",
        serial_no=f"TX{datetime.now():%Y%m%d%H%M%S%f}",
        title=content[:255],
        customer=case_record.customer,
        status="有效",
        owner=identity["username"],
        department=case_record.department,
        description=content,
        data={
            "case_id": case_record.id,
            "case_no": case_record.serial_no,
            "reminder_date": str(body.reminder_date),
            "deadline": str(body.deadline),
        },
    )
    db.add(item)
    await db.flush()
    db.add(
        WorkflowEvent(
            record_id=case_record.id,
            action="新增案件提醒",
            from_status=case_record.status,
            to_status=case_record.status,
            operator=identity["username"],
            comment=f"提醒日期：{body.reminder_date}；截止日期：{body.deadline}；{content}",
        )
    )
    return item
