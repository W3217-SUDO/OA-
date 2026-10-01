"""任务创建的共享业务命令；提交由入口负责。"""

from app.core.dependencies import (
    AsyncSession,
    BusinessRecord,
    HTTPException,
    User,
    WorkflowEvent,
    select,
)
from app.models_shared import TaskInput


async def create_task_record(body: TaskInput, identity: dict, db: AsyncSession):
    from app.core.crm import (
        _case_customer_has_vip_marker,
    )
    from app.core.permissions import (
        _case_detail_action_capabilities,
        _ensure_active_ipr_case_write,
        _ensure_record_module,
    )
    from app.core.tasks import (
        _active_task_username,
        _add_task_message_notifications,
        _next_manual_task_serial,
        _validate_task_deadline,
    )

    _validate_task_deadline(body.deadline)
    if body.start_at and body.end_at and body.start_at >= body.end_at:
        raise HTTPException(status_code=422, detail="任务结束时间必须晚于开始时间")
    if body.end_at and body.end_at.date() != body.deadline:
        raise HTTPException(
            status_code=422, detail="截止日期必须与任务结束时间的日期一致"
        )
    requested_case_nos = [
        body.case_no.strip(),
        *(str(value).strip() for value in body.case_nos),
    ]
    case_nos = list(dict.fromkeys(value for value in requested_case_nos if value))
    case_no = case_nos[0] if case_nos else ""
    source = body.source.strip() or "日常任务"
    if source == "客户任务":
        raise HTTPException(status_code=403, detail="客户任务只能由客户通过客户端发布")
    if body.case_record_id and case_nos:
        raise HTTPException(status_code=422, detail="案件 ID 与案号列表不能同时提交")
    if source == "案件任务" and not case_nos and not body.case_record_id:
        raise HTTPException(status_code=422, detail="案件任务必须关联有效案件")
    case_records: list[BusinessRecord] = []
    if body.case_record_id:
        case_record = await _ensure_record_module(
            body.case_record_id, body.case_module, identity, db
        )
        if body.case_module == "case":
            capabilities = await _case_detail_action_capabilities(
                case_record, identity, db
            )
            if not capabilities["can_create_case_task"]:
                raise HTTPException(
                    status_code=403,
                    detail=f"当前账号没有创建案件 {case_record.serial_no} 任务的权限",
                )
        else:
            await _ensure_active_ipr_case_write(case_record.id, identity, db)
        case_records.append(case_record)
    for linked_case_no in case_nos:
        case_record = await db.scalar(
            select(BusinessRecord).where(
                BusinessRecord.module == "case",
                BusinessRecord.serial_no == linked_case_no,
            )
        )
        if not case_record:
            raise HTTPException(
                status_code=404, detail=f"关联案件不存在：{linked_case_no}"
            )
        case_record = await _ensure_record_module(case_record.id, "case", identity, db)
        capabilities = await _case_detail_action_capabilities(case_record, identity, db)
        if not capabilities["can_create_case_task"]:
            raise HTTPException(
                status_code=403,
                detail=f"当前账号没有创建案件 {linked_case_no} 任务的权限",
            )
        case_records.append(case_record)
    case_record = case_records[0] if case_records else None
    case_no = case_record.serial_no if case_record else case_no
    serial = await _next_manual_task_serial(db)
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    owner = await _active_task_username(body.owner, db, field_name="负责人")
    collaborators = []
    for value in body.collaborators:
        collaborator = await _active_task_username(value, db, field_name="协作人")
        if collaborator != owner and collaborator not in collaborators:
            collaborators.append(collaborator)
    initial_status = "待处理" if source == "案件任务" else "待接收"
    clue_task_data = {}
    creation_comment = f"负责人：{owner}；截止日期：{body.deadline}"
    if body.clue_ids:
        from app.core.case_relations import case_clues, clue_header_values

        if len(case_records) != 1 or case_record.module != "case":
            raise HTTPException(422, "公证书领取任务必须关联一个案件")
        linked_clues = {item.id: item for item in await case_clues(case_record, db)}
        selected_ids = list(dict.fromkeys(body.clue_ids))
        if any(clue_id not in linked_clues for clue_id in selected_ids):
            raise HTTPException(409, "所选线索不属于该案件")
        selected_clues = [linked_clues[clue_id] for clue_id in selected_ids]
        certificates = clue_header_values(selected_clues)["notary_no"]
        if not certificates:
            raise HTTPException(422, "所选线索尚未填写公证书号")
        people = (
            await db.scalars(
                select(User).where(User.username.in_([owner, *collaborators]))
            )
        ).all()
        names = {
            person.username: person.display_name or person.username for person in people
        }
        initiator_name = (
            user.display_name or user.username if user else identity["username"]
        )
        collaborator_names = "、".join(names[value] for value in collaborators) or "无"
        creation_comment = f"{initiator_name}新建任务给负责人({names[owner]})，协作人({collaborator_names})，附言：领取公证书（{certificates}）"
        clue_task_data = {
            "clue_ids": selected_ids,
            "clue_nos": [item.serial_no for item in selected_clues],
            "certificate_nos": certificates,
            "task_type": "公证书领取",
        }
    inherited_vip = False
    for linked_case in case_records:
        if await _case_customer_has_vip_marker(linked_case, db):
            inherited_vip = True
            break
    task = BusinessRecord(
        module="task",
        serial_no=serial,
        title=body.title,
        customer=case_record.customer if case_record else body.customer,
        status=initial_status,
        owner=owner,
        department=user.department if user else "上海分所",
        description=body.description,
        data={
            "deadline": str(body.deadline),
            "start_at": body.start_at.isoformat() if body.start_at else "",
            "end_at": body.end_at.isoformat() if body.end_at else "",
            "priority": body.priority,
            "source": source,
            "creation_mode": "人工",
            "task_type": "手动任务",
            "initiator": identity["username"],
            "collaborators": collaborators,
            "case_no": case_no,
            "case_nos": [item.serial_no for item in case_records],
            "case_id": case_record.id if case_record else None,
            "case_record_id": case_record.id if case_record else None,
            "case_ids": [item.id for item in case_records],
            "case_module": body.case_module if case_record else "",
            "is_vip": bool(body.is_vip or inherited_vip),
        },
    )
    task.data = {**task.data, **clue_task_data}
    db.add(task)
    await db.flush()
    await _add_task_message_notifications(
        task,
        WorkflowEvent(
            record_id=task.id,
            action="发起任务",
            to_status=initial_status,
            operator=identity["username"],
            comment=creation_comment,
        ),
        db,
        content="任务已分派.",
    )
    return task
