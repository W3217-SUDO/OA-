"""按独立业务职责组织的路由，注册顺序与端点行为保持稳定。"""
from app.core.constants import (
    CASE_EVENT_PENDING_STATUS,
)
from app.core.dependencies import (
    AsyncSession,
    BusinessRecord,
    CaseEvent,
    Depends,
    HTTPException,
    LegacyCaseLog,
    Response,
    WorkflowEvent,
    and_,
    current_identity,
    get_db,
    or_,
    select,
    settings,
    status,
)
from app.models_shared import (
    CaseEventBatchDeleteInput,
    CaseEventInput,
    CaseEventUpdateInput,
    CaseReminderInput,
)
from fastapi import APIRouter

router = APIRouter()

@router.get(f"{settings.api_prefix}/cases/{{case_id}}/reminders")
async def list_case_reminders(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _record_dict,
    )
    await _ensure_record_module(case_id, "case", identity, db)
    reminders = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case_reminder",
    ).order_by(BusinessRecord.data["reminder_date"].as_string(), BusinessRecord.id))).all())
    items = [item for item in reminders if int((item.data or {}).get("case_id") or 0) == case_id]
    return {"items": [_record_dict(item) for item in items], "total": len(items)}


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/events")
async def list_case_events(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_event_dict,
    )
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _case_event_access, _require_case_event_write_access,
    )
    case_record, _ = await _case_event_access(case_id, identity, db, write=False)
    items = list((await db.scalars(select(CaseEvent).where(
        CaseEvent.case_record_id == case_record.id,
    ).order_by(CaseEvent.event_time, CaseEvent.deadline, CaseEvent.id))).all())
    try:
        team_role = await _require_case_event_write_access(case_record, identity, db)
        can_manage = True
    except HTTPException:
        team_role, can_manage = "none", False
    users_by_username = await _user_display_map({item.creator for item in items}, db)
    return {
        "items": [_case_event_dict(item, users_by_username, identity, can_manage=can_manage, team_role=team_role) for item in items],
        "total": len(items),
        "capabilities": {"can_create": can_manage, "can_edit": can_manage, "can_delete": can_manage},
    }


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/events", status_code=status.HTTP_201_CREATED)
async def create_case_event(case_id: int, body: CaseEventInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_event_dict,
    )
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _case_event_access,
    )
    from app.core.storage import (
        _case_event_storage_time,
    )
    from app.core.tasks import (
        _sync_case_event_reminder, _validate_case_event_reminder,
    )
    case_record, team_role = await _case_event_access(case_id, identity, db, write=True)
    if not body.event_type.strip() or not body.content.strip():
        raise HTTPException(status_code=422, detail="事件类型和事件内容不能为空")
    remind_at = _validate_case_event_reminder(
        deadline=body.deadline, reminder_enabled=body.reminder_enabled,
        remind_at=_case_event_storage_time(body.remind_at or body.event_time) if body.reminder_enabled else None,
    )
    item = CaseEvent(
        case_record_id=case_record.id, event_type_id=body.event_type_id,
        event_type=body.event_type.strip(), event_time=_case_event_storage_time(body.event_time),
        content=body.content.strip(), deadline=body.deadline,
        reminder_enabled=body.reminder_enabled, remind_at=remind_at,
        status=CASE_EVENT_PENDING_STATUS, creator=identity["username"], updated_by=identity["username"],
    )
    db.add(item)
    await db.flush()
    await _sync_case_event_reminder(item, case_record, identity, db)
    db.add(WorkflowEvent(
        record_id=case_record.id, action="新增案件事件", from_status=case_record.status,
        to_status=case_record.status, operator=identity["username"],
        comment=f"事件#{item.id}｜{item.event_type}｜事件日期：{item.event_time}；截止日期：{item.deadline or '未设置'}；{item.content}",
    ))
    await db.commit()
    await db.refresh(item)
    users = await _user_display_map({item.creator}, db)
    return _case_event_dict(item, users, identity, can_manage=True, team_role=team_role or "none")


@router.patch(f"{settings.api_prefix}/cases/{{case_id}}/events/{{event_id}}")
async def update_case_event(case_id: int, event_id: int, body: CaseEventUpdateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_event_dict, _case_event_mutable_by, _case_event_status,
    )
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _case_event_access,
    )
    from app.core.storage import (
        _case_event_storage_time,
    )
    from app.core.tasks import (
        _sync_case_event_reminder, _validate_case_event_reminder,
    )
    case_record, team_role = await _case_event_access(case_id, identity, db, write=True)
    item = await db.scalar(select(CaseEvent).where(CaseEvent.id == event_id, CaseEvent.case_record_id == case_record.id))
    if not item:
        raise HTTPException(status_code=404, detail="案件事件不存在或不属于当前案件")
    if not _case_event_mutable_by(item, identity, team_role or "none"):
        raise HTTPException(status_code=403, detail="只有事件创建人、部门负责人或系统管理员可以修改案件事件")
    fields = body.model_fields_set
    for required_field, label in (("event_type", "事件类型"), ("event_time", "事件时间"), ("content", "事件内容")):
        if required_field in fields and getattr(body, required_field) is None:
            raise HTTPException(status_code=422, detail=f"{label}不能为空")
    if "event_type" in fields and not (body.event_type or "").strip():
        raise HTTPException(status_code=422, detail="事件类型不能为空")
    if "content" in fields and not (body.content or "").strip():
        raise HTTPException(status_code=422, detail="事件内容不能为空")
    next_event_time = _case_event_storage_time(body.event_time) if "event_time" in fields else item.event_time
    next_deadline = body.deadline if "deadline" in fields else item.deadline
    next_reminder_enabled = body.reminder_enabled if "reminder_enabled" in fields else item.reminder_enabled
    next_remind_at = _case_event_storage_time(body.remind_at) if "remind_at" in fields and body.remind_at else (item.remind_at if "remind_at" not in fields else None)
    if next_reminder_enabled and next_remind_at is None:
        next_remind_at = next_event_time
    next_remind_at = _validate_case_event_reminder(
        deadline=next_deadline, reminder_enabled=next_reminder_enabled, remind_at=next_remind_at,
    )
    before_status = _case_event_status(item)
    if "event_type_id" in fields:
        item.event_type_id = body.event_type_id or 0
    if "event_type" in fields:
        item.event_type = (body.event_type or "").strip()
    if "event_time" in fields:
        item.event_time = next_event_time
    if "content" in fields:
        item.content = (body.content or "").strip()
    if "deadline" in fields:
        item.deadline = next_deadline
    item.reminder_enabled = bool(next_reminder_enabled)
    item.remind_at = next_remind_at
    if "status" in fields:
        item.status = body.status or CASE_EVENT_PENDING_STATUS
    item.updated_by = identity["username"]
    await _sync_case_event_reminder(item, case_record, identity, db)
    changes = []
    if "event_type_id" in fields or "event_type" in fields:
        changes.append("事件类型")
    if "event_time" in fields:
        changes.append("事件时间")
    if "content" in fields:
        changes.append("事件内容")
    if "deadline" in fields:
        changes.append("截止日期")
    if "reminder_enabled" in fields or "remind_at" in fields:
        changes.append("提醒设置")
    if "status" in fields:
        changes.append("状态")
    db.add(WorkflowEvent(
        record_id=case_record.id, action="修改案件事件", from_status=case_record.status,
        to_status=case_record.status, operator=identity["username"],
        comment=f"事件#{item.id}｜修改：{'、'.join(changes) or '无'}｜状态：{before_status} -> {_case_event_status(item)}",
    ))
    await db.commit()
    await db.refresh(item)
    users = await _user_display_map({item.creator}, db)
    return _case_event_dict(item, users, identity, can_manage=True, team_role=team_role or "none")


@router.delete(f"{settings.api_prefix}/cases/{{case_id}}/events/{{event_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case_event(case_id: int, event_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_event_mutable_by,
    )
    from app.core.permissions import (
        _case_event_access,
    )
    from app.core.tasks import (
        _sync_case_event_reminder,
    )
    case_record, team_role = await _case_event_access(case_id, identity, db, write=True)
    item = await db.scalar(select(CaseEvent).where(CaseEvent.id == event_id, CaseEvent.case_record_id == case_record.id))
    if not item:
        raise HTTPException(status_code=404, detail="案件事件不存在或不属于当前案件")
    if not _case_event_mutable_by(item, identity, team_role or "none"):
        raise HTTPException(status_code=403, detail="只有事件创建人、部门负责人或系统管理员可以删除案件事件")
    await _sync_case_event_reminder(CaseEvent(case_record_id=case_record.id, reminder_enabled=False, reminder_record_id=item.reminder_record_id), case_record, identity, db)
    db.add(WorkflowEvent(record_id=case_record.id, action="删除案件事件", from_status=case_record.status, to_status=case_record.status, operator=identity["username"], comment=f"事件#{item.id}｜{item.event_type}｜{item.content}"))
    await db.delete(item)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(f"{settings.api_prefix}/cases/{{case_id}}/events")
async def batch_delete_case_events(case_id: int, body: CaseEventBatchDeleteInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_event_mutable_by,
    )
    from app.core.permissions import (
        _case_event_access,
    )
    from app.core.tasks import (
        _sync_case_event_reminder,
    )
    case_record, team_role = await _case_event_access(case_id, identity, db, write=True)
    event_ids = list(dict.fromkeys(body.event_ids))
    items = list((await db.scalars(select(CaseEvent).where(CaseEvent.id.in_(event_ids)))).all())
    if len(items) != len(event_ids) or any(item.case_record_id != case_record.id for item in items):
        raise HTTPException(status_code=404, detail="存在不存在或不属于当前案件的事件，未执行删除")
    if any(not _case_event_mutable_by(item, identity, team_role or "none") for item in items):
        raise HTTPException(status_code=403, detail="存在无权删除的案件事件，未执行删除")
    for item in items:
        await _sync_case_event_reminder(CaseEvent(case_record_id=case_record.id, reminder_enabled=False, reminder_record_id=item.reminder_record_id), case_record, identity, db)
        await db.delete(item)
    db.add(WorkflowEvent(record_id=case_record.id, action="批量删除案件事件", from_status=case_record.status, to_status=case_record.status, operator=identity["username"], comment=f"事件数量：{len(items)}；ID：{','.join(map(str, event_ids))}"))
    await db.commit()
    return {"deleted": len(items), "deleted_ids": event_ids}


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/reminders", status_code=status.HTTP_201_CREATED)
async def create_case_reminder(case_id: int, body: CaseReminderInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.case_reminder_commands import create_case_reminder_record
    from app.core.system import _record_dict
    item = await create_case_reminder_record(case_id, body, identity, db)
    await db.commit()
    await db.refresh(item)
    return _record_dict(item)


@router.delete(f"{settings.api_prefix}/cases/{{case_id}}/reminders/{{reminder_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case_reminder(case_id: int, reminder_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_event_mutable_by,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_case_event_write_access, _require_case_note_write_access,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_note_write_access(case_record, identity, db)
    item = await db.get(BusinessRecord, reminder_id)
    if not item or item.module != "case_reminder" or int((item.data or {}).get("case_id") or 0) != case_id:
        raise HTTPException(status_code=404, detail="案件提醒不存在")
    linked_event_id = int((item.data or {}).get("case_event_id") or 0)
    if linked_event_id:
        linked_event = await db.scalar(select(CaseEvent).where(
            CaseEvent.id == linked_event_id,
            CaseEvent.case_record_id == case_record.id,
            CaseEvent.reminder_record_id == item.id,
        ))
        if linked_event:
            team_role = await _require_case_event_write_access(case_record, identity, db)
            if not _case_event_mutable_by(linked_event, identity, team_role):
                raise HTTPException(status_code=403, detail="只有事件创建人、部门负责人或系统管理员可以删除关联提醒")
            linked_event.reminder_enabled = False
            linked_event.reminder_record_id = None
            linked_event.updated_by = identity["username"]
    db.add(WorkflowEvent(
        record_id=case_record.id, action="删除案件提醒", from_status=case_record.status,
        to_status=case_record.status, operator=identity["username"],
        comment=f"提醒日期：{(item.data or {}).get('reminder_date', '')}；{item.description}",
    ))
    await db.delete(item)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/logs")
async def list_case_logs(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _person_reference_display, _user_display_map,
    )
    from app.core.permissions import (
        _ensure_case_read_module,
    )
    case_record = await _ensure_case_read_module(case_id, identity, db)
    from app.core.case_document_sources import case_document_sources
    source_case_nos = [item["serial_no"] for item in case_document_sources(case_record) if item.get("serial_no")]
    business_logs = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case_log", BusinessRecord.status != "已删除",
        or_(
            BusinessRecord.data["case_id"].as_integer() == case_id,
            BusinessRecord.data["case_no"].as_string().in_(source_case_nos),
        ),
    ).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()))).all())
    related_finance_ids = list((await db.scalars(select(BusinessRecord.id).where(
        BusinessRecord.module == "finance",
        or_(BusinessRecord.data["case_id"].as_integer() == case_id, BusinessRecord.data["case_record_id"].as_integer() == case_id),
    ))).all())
    events = list((await db.scalars(select(WorkflowEvent).where(
        or_(
            and_(WorkflowEvent.record_id == case_id, WorkflowEvent.action == "新增案件日志"),
            and_(WorkflowEvent.record_id.in_(related_finance_ids), WorkflowEvent.action.like("添加%退费日志")),
        ),
    ).order_by(WorkflowEvent.created_at.desc(), WorkflowEvent.id.desc()))).all())
    business_signatures = {(item.owner, item.description or "") for item in business_logs}
    events = [item for item in events if (item.operator, item.comment or "") not in business_signatures]
    # 旧系统人工日志类型为 1；负 ID 是当前工作流事件的兼容投影，不重复作为人工日志读取。
    legacy_logs = list((await db.scalars(select(LegacyCaseLog).where(
        LegacyCaseLog.CaseNo.in_(source_case_nos),
        LegacyCaseLog.LogId > 0,
        LegacyCaseLog.LogType == 1,
    ).order_by(LegacyCaseLog.CreateTime.desc(), LegacyCaseLog.LogId.desc()))).all())
    users_by_username = await _user_display_map(
        {item.operator for item in events} | {item.owner for item in business_logs} | {str(item.CreateUser or "").strip() for item in legacy_logs}, db
    )
    items = [{
        "id": f"business-{item.id}", "content": item.description or "", "operator": item.owner,
        "operator_display_name": _person_reference_display(item.owner, users_by_username)[0],
        "created_at": item.created_at, "source": "current",
        "kind": str((item.data or {}).get("kind") or "case"),
        "case_fee_id": (item.data or {}).get("case_fee_id"),
        "source_case_no": (item.data or {}).get("case_no"),
    } for item in business_logs]
    items.extend({
        "id": item.id, "content": item.comment, "operator": item.operator,
        "operator_display_name": _person_reference_display(item.operator, users_by_username)[0],
        "created_at": item.created_at, "source": "current",
        "kind": "refund" if item.action.startswith("添加") and item.action.endswith("退费日志") else "case",
    } for item in events)
    items.extend({
        "id": -abs(item.LogId), "content": item.Content or "", "operator": item.CreateUser or "",
        "operator_display_name": _person_reference_display(item.CreateUser, users_by_username)[0],
        "created_at": item.CreateTime, "source": "legacy", "kind": "case",
    } for item in legacy_logs)
    items.sort(key=lambda item: (str(item["created_at"] or ""), str(item["id"])), reverse=True)
    return {"items": items, "total": len(items)}
