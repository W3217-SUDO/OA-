"""知识产权案件提醒与预警规则接口。"""
from fastapi import APIRouter
from app.core.constants import IPR_REMINDER_EVENT_TYPES, IPR_REMINDER_EVENT_TYPE_BY_ID
from app.core.dependencies import AsyncSession, Decimal, Depends, HTTPException, IntegrityError, IprCaseAnnualFee, IprCaseReminder, IprCaseReminderSuppression, IprCaseWarning, IprCaseWarningRule, Notification, Query, Response, WorkflowEvent, current_identity, delete, func, get_db, select, settings, status
from app.models_shared import IprCaseAnnualFeeCreateInput, IprCaseAnnualFeeUpdateInput, IprCaseReminderInput, IprCaseReminderSuppressionInput, IprCaseReminderUpdate, IprCaseWarningRuleInput, IprCaseWarningRuleUpdateInput

router = APIRouter()


@router.get(f"{settings.api_prefix}/ipr/reminder-event-types")
async def list_ipr_reminder_event_types(
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """提供已保存提醒查询配置使用的稳定历史编号。"""
    from app.core.permissions import (
        _require_record_module_menu,
    )
    await _require_record_module_menu("ipr_case", identity, db, action="查看")
    return {"items": [{"id": event_type_id, "name": name} for event_type_id, name in IPR_REMINDER_EVENT_TYPES]}

@router.get(f"{settings.api_prefix}/ipr/cases/{{case_id}}/events")
@router.get(f"{settings.api_prefix}/ipr/cases/{{case_id}}/reminders")
async def list_ipr_case_reminders(
    case_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.ipr import (
        _ipr_case_reminder_dict,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    total = int(await db.scalar(select(func.count()).select_from(IprCaseReminder).where(IprCaseReminder.case_record_id == record.id)) or 0)
    rows = list((await db.scalars(
        select(IprCaseReminder)
        .where(IprCaseReminder.case_record_id == record.id)
        .order_by(IprCaseReminder.reminder_date, IprCaseReminder.id)
        .offset((page - 1) * page_size).limit(page_size)
    )).all())
    users_by_username = await _user_display_map({row.creator for row in rows}, db)
    return {
        "items": [_ipr_case_reminder_dict(row, users_by_username) for row in rows],
        "total": total, "page": page, "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
    }

@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/events", status_code=status.HTTP_201_CREATED)
@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/reminders", status_code=status.HTTP_201_CREATED)
async def create_ipr_case_reminder(case_id: int, body: IprCaseReminderInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _ipr_case_reminder_dict,
    )
    from app.core.permissions import (
        _ensure_active_ipr_case_write,
    )
    record = await _ensure_active_ipr_case_write(case_id, identity, db)
    event_date = body.event_date or body.reminder_date
    if event_date is None:
        raise HTTPException(status_code=422, detail="事件日期不能为空")
    if event_date > body.deadline:
        raise HTTPException(status_code=422, detail="事件日期不能晚于截止日期")
    if body.event_type_id and body.event_type_id not in IPR_REMINDER_EVENT_TYPE_BY_ID:
        raise HTTPException(status_code=422, detail="案件事件类型无效")
    event_type = IPR_REMINDER_EVENT_TYPE_BY_ID.get(body.event_type_id, "自定义提醒")
    row = IprCaseReminder(case_record_id=record.id, event_type_id=body.event_type_id, event_type=event_type, reminder_date=event_date, deadline=body.deadline, content=body.content.strip(), creator=identity["username"])
    db.add(row); await db.flush()
    db.add(WorkflowEvent(record_id=record.id, action="新增知识产权案件事件", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"事件日期：{row.reminder_date}；截止日期：{row.deadline}；{row.content}"))
    await db.commit(); await db.refresh(row)
    return _ipr_case_reminder_dict(row)

@router.patch(f"{settings.api_prefix}/ipr/cases/{{case_id}}/events/{{event_id}}")
@router.patch(f"{settings.api_prefix}/ipr/cases/{{case_id}}/reminders/{{event_id}}")
async def update_ipr_case_reminder(case_id: int, event_id: int, body: IprCaseReminderUpdate, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _ipr_case_reminder_dict,
    )
    from app.core.permissions import (
        _ensure_active_ipr_case_write,
    )
    record = await _ensure_active_ipr_case_write(case_id, identity, db)
    row = await db.scalar(select(IprCaseReminder).where(IprCaseReminder.id == event_id, IprCaseReminder.case_record_id == record.id))
    if not row:
        raise HTTPException(status_code=404, detail="知识产权案件事件不存在")
    if identity.get("role") not in {"admin", "manager"} and row.creator != identity["username"]:
        raise HTTPException(status_code=403, detail="只有事件创建人、部门负责人或系统管理员可以修改")
    next_type_id = row.event_type_id if body.event_type_id is None else body.event_type_id
    if next_type_id and next_type_id not in IPR_REMINDER_EVENT_TYPE_BY_ID:
        raise HTTPException(status_code=422, detail="案件事件类型无效")
    next_reminder_date = body.event_date or body.reminder_date or row.reminder_date
    next_deadline = body.deadline or row.deadline
    if next_reminder_date > next_deadline:
        raise HTTPException(status_code=422, detail="事件日期不能晚于截止日期")
    before = _ipr_case_reminder_dict(row)
    row.event_type_id = next_type_id
    row.event_type = IPR_REMINDER_EVENT_TYPE_BY_ID.get(next_type_id, "自定义提醒")
    row.reminder_date = next_reminder_date
    row.deadline = next_deadline
    if body.content is not None:
        row.content = body.content.strip()
    db.add(WorkflowEvent(
        record_id=record.id, action="修改知识产权案件事件", from_status=record.status,
        to_status=record.status, operator=identity["username"],
        comment=f"事件#{row.id}；{before['event_type']} -> {row.event_type}",
    ))
    await db.commit(); await db.refresh(row)
    return _ipr_case_reminder_dict(row)

@router.delete(f"{settings.api_prefix}/ipr/cases/{{case_id}}/events/{{reminder_id}}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete(f"{settings.api_prefix}/ipr/cases/{{case_id}}/reminders/{{reminder_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ipr_case_reminder(case_id: int, reminder_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_active_ipr_case_write,
    )
    record = await _ensure_active_ipr_case_write(case_id, identity, db)
    row = await db.scalar(select(IprCaseReminder).where(IprCaseReminder.id == reminder_id, IprCaseReminder.case_record_id == record.id))
    if not row:
        raise HTTPException(status_code=404, detail="知识产权案件事件不存在")
    if identity.get("role") != "admin" and identity.get("role") != "manager" and row.creator != identity["username"]:
        raise HTTPException(status_code=403, detail="只有事件创建人、部门负责人或系统管理员可以删除")
    db.add(WorkflowEvent(record_id=record.id, action="删除知识产权案件事件", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"事件日期：{row.reminder_date}；{row.content}"))
    await db.delete(row); await db.commit()

@router.get(f"{settings.api_prefix}/ipr/cases/{{case_id}}/reminder-suppressions")
async def get_ipr_case_reminder_suppressions(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    rows = list((await db.scalars(select(IprCaseReminderSuppression).where(IprCaseReminderSuppression.case_record_id == record.id).order_by(IprCaseReminderSuppression.event_type_id))).all())
    ids = [row.event_type_id for row in rows]
    return {"event_types": [{"id": event_id, "name": name, "suppressed": event_id in ids} for event_id, name in IPR_REMINDER_EVENT_TYPES], "suppressed_ids": ids}

@router.put(f"{settings.api_prefix}/ipr/cases/{{case_id}}/reminder-suppressions")
async def replace_ipr_case_reminder_suppressions(case_id: int, body: IprCaseReminderSuppressionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_active_ipr_case_write,
    )
    record = await _ensure_active_ipr_case_write(case_id, identity, db)
    requested = set(body.event_type_ids)
    invalid = requested - set(IPR_REMINDER_EVENT_TYPE_BY_ID)
    if invalid:
        raise HTTPException(status_code=422, detail=f"存在无效提醒类型：{', '.join(map(str, sorted(invalid)))}")
    existing = list((await db.scalars(select(IprCaseReminderSuppression).where(IprCaseReminderSuppression.case_record_id == record.id))).all())
    before = {row.event_type_id for row in existing}
    for row in existing:
        await db.delete(row)
    for event_type_id in sorted(requested):
        db.add(IprCaseReminderSuppression(case_record_id=record.id, event_type_id=event_type_id, event_type=IPR_REMINDER_EVENT_TYPE_BY_ID[event_type_id], operator=identity["username"]))
    added = [IPR_REMINDER_EVENT_TYPE_BY_ID[item] for item in sorted(requested - before)]
    removed = [IPR_REMINDER_EVENT_TYPE_BY_ID[item] for item in sorted(before - requested)]
    db.add(WorkflowEvent(record_id=record.id, action="设置知识产权案件提醒不监控", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"新增不监控：{'、'.join(added) or '无'}；恢复监控：{'、'.join(removed) or '无'}"))
    await db.commit()
    return {"suppressed_ids": sorted(requested)}

@router.get(f"{settings.api_prefix}/ipr/cases/{{case_id}}/annual-fees")
async def list_ipr_case_annual_fees(
    case_id: int, fee_year: int | None = Query(default=None, ge=2000, le=2100),
    page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _ipr_annual_fee_dict,
    )
    from app.core.permissions import (
        _ensure_record_module, _ipr_annual_fee_capabilities,
    )
    case_record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    conditions = [IprCaseAnnualFee.case_record_id == case_record.id]
    if fee_year is not None:
        conditions.append(IprCaseAnnualFee.fee_year == fee_year)
    total = int(await db.scalar(select(func.count()).select_from(IprCaseAnnualFee).where(*conditions)) or 0)
    rows = list((await db.scalars(select(IprCaseAnnualFee).where(*conditions)
        .order_by(IprCaseAnnualFee.fee_year.desc(), IprCaseAnnualFee.due_date.asc(), IprCaseAnnualFee.id.desc())
        .offset((page - 1) * page_size).limit(page_size))).all())
    reminder_ids = [row.reminder_id for row in rows if row.reminder_id]
    reminders = list((await db.scalars(select(IprCaseReminder).where(IprCaseReminder.id.in_(reminder_ids)))).all()) if reminder_ids else []
    by_id = {item.id: item for item in reminders}
    return {
        "items": [_ipr_annual_fee_dict(row, by_id.get(row.reminder_id)) for row in rows],
        "total": total, "page": page, "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
        "capabilities": await _ipr_annual_fee_capabilities(case_record, identity, db),
    }

@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/annual-fees", status_code=status.HTTP_201_CREATED)
async def create_ipr_case_annual_fee(case_id: int, body: IprCaseAnnualFeeCreateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _ipr_annual_fee_dict, _sync_ipr_annual_fee_reminder, _validate_ipr_annual_fee_values,
    )
    from app.core.permissions import (
        _ensure_active_ipr_case_write,
    )
    case_record = await _ensure_active_ipr_case_write(case_id, identity, db)
    _validate_ipr_annual_fee_values(status_value=body.status, paid_date=body.paid_date, reminder_date=body.reminder_date, due_date=body.due_date)
    row = IprCaseAnnualFee(
        case_record_id=case_record.id, fee_year=body.fee_year, fee_name=body.fee_name.strip(),
        amount=Decimal(str(body.amount)), currency=body.currency.strip().upper(), due_date=body.due_date,
        paid_date=body.paid_date, status=body.status, reminder_date=body.reminder_date,
        notes=body.notes.strip(), created_by=identity["username"],
    )
    db.add(row)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="该案件的缴费年度已存在年费记录")
    reminder = await _sync_ipr_annual_fee_reminder(row, case_record, identity, db)
    db.add(WorkflowEvent(record_id=case_record.id, action="新增知识产权案件年费", from_status=case_record.status, to_status=case_record.status, operator=identity["username"], comment=f"缴费年度：{row.fee_year}；状态：{row.status}"))
    await db.commit(); await db.refresh(row)
    return _ipr_annual_fee_dict(row, reminder)

@router.put(f"{settings.api_prefix}/ipr/cases/{{case_id}}/annual-fees/{{annual_fee_id}}")
async def update_ipr_case_annual_fee(case_id: int, annual_fee_id: int, body: IprCaseAnnualFeeUpdateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _ipr_annual_fee_dict, _sync_ipr_annual_fee_reminder, _validate_ipr_annual_fee_values,
    )
    from app.core.permissions import (
        _ensure_active_ipr_case_write,
    )
    case_record = await _ensure_active_ipr_case_write(case_id, identity, db)
    row = await db.scalar(select(IprCaseAnnualFee).where(IprCaseAnnualFee.id == annual_fee_id, IprCaseAnnualFee.case_record_id == case_record.id))
    if not row:
        raise HTTPException(status_code=404, detail="知识产权案件年费不存在或不属于当前案件")
    values = body.model_dump(exclude_unset=True)
    if not values:
        raise HTTPException(status_code=422, detail="请至少提交一个需要修改的年费字段")
    for field in {"fee_year", "fee_name", "amount", "currency", "due_date", "paid_date", "status", "reminder_date", "notes"} & values.keys():
        value = values[field]
        if field in {"fee_name", "currency", "notes"} and value is not None:
            value = value.strip()
        if field == "currency" and value:
            value = value.upper()
        if field == "amount" and value is not None:
            value = Decimal(str(value))
        setattr(row, field, value)
    _validate_ipr_annual_fee_values(status_value=row.status, paid_date=row.paid_date, reminder_date=row.reminder_date, due_date=row.due_date)
    reminder = await _sync_ipr_annual_fee_reminder(row, case_record, identity, db)
    db.add(WorkflowEvent(record_id=case_record.id, action="修改知识产权案件年费", from_status=case_record.status, to_status=case_record.status, operator=identity["username"], comment=f"年费#{row.id}；缴费年度：{row.fee_year}；状态：{row.status}"))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="该案件的缴费年度已存在年费记录")
    await db.refresh(row)
    return _ipr_annual_fee_dict(row, reminder)

@router.delete(f"{settings.api_prefix}/ipr/cases/{{case_id}}/annual-fees/{{annual_fee_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ipr_case_annual_fee(case_id: int, annual_fee_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_active_ipr_case_write,
    )
    case_record = await _ensure_active_ipr_case_write(case_id, identity, db)
    row = await db.scalar(select(IprCaseAnnualFee).where(IprCaseAnnualFee.id == annual_fee_id, IprCaseAnnualFee.case_record_id == case_record.id))
    if not row:
        raise HTTPException(status_code=404, detail="知识产权案件年费不存在或不属于当前案件")
    reminder = await db.scalar(select(IprCaseReminder).where(IprCaseReminder.id == row.reminder_id, IprCaseReminder.case_record_id == case_record.id)) if row.reminder_id else None
    if reminder:
        await db.delete(reminder)
    db.add(WorkflowEvent(record_id=case_record.id, action="删除知识产权案件年费", from_status=case_record.status, to_status=case_record.status, operator=identity["username"], comment=f"缴费年度：{row.fee_year}；年费：{row.fee_name}"))
    await db.delete(row); await db.commit()

@router.get(f"{settings.api_prefix}/ipr/warning-rules")
async def list_ipr_warning_rules(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _ipr_warning_rule_dict,
    )
    from app.core.permissions import (
        _require_record_module_menu,
    )
    await _require_record_module_menu("ipr_case", identity, db, action="查看")
    rows = list((await db.scalars(select(IprCaseWarningRule).order_by(IprCaseWarningRule.id))).all())
    return {"items": [_ipr_warning_rule_dict(row) for row in rows], "total": len(rows)}

@router.post(f"{settings.api_prefix}/ipr/warning-rules", status_code=status.HTTP_201_CREATED)
async def create_ipr_warning_rule(body: IprCaseWarningRuleInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _ipr_warning_rule_dict, _validate_ipr_warning_rule_payload,
    )
    from app.core.permissions import (
        _require_ipr_reminder_type_manage,
    )
    _require_ipr_reminder_type_manage(identity); _validate_ipr_warning_rule_payload(body)
    if await db.scalar(select(IprCaseWarningRule.id).where(IprCaseWarningRule.name == body.name.strip())):
        raise HTTPException(status_code=409, detail="案件预警规则名称已存在")
    row = IprCaseWarningRule(**body.model_dump(exclude={"name"}), name=body.name.strip(), created_by=identity["username"], updated_by=identity["username"])
    db.add(row); await db.commit(); await db.refresh(row)
    return _ipr_warning_rule_dict(row)

@router.patch(f"{settings.api_prefix}/ipr/warning-rules/{{rule_id}}")
async def update_ipr_warning_rule(rule_id: int, body: IprCaseWarningRuleUpdateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _ipr_warning_rule_dict, _validate_ipr_warning_rule_payload,
    )
    from app.core.permissions import (
        _require_ipr_reminder_type_manage,
    )
    _require_ipr_reminder_type_manage(identity); _validate_ipr_warning_rule_payload(body)
    row = await db.get(IprCaseWarningRule, rule_id)
    if not row: raise HTTPException(status_code=404, detail="案件预警规则不存在")
    values = body.model_dump(exclude_unset=True)
    if "name" in values:
        values["name"] = values["name"].strip()
        duplicate = await db.scalar(select(IprCaseWarningRule.id).where(IprCaseWarningRule.name == values["name"], IprCaseWarningRule.id != rule_id))
        if duplicate: raise HTTPException(status_code=409, detail="案件预警规则名称已存在")
    for key, value in values.items(): setattr(row, key, value)
    row.updated_by = identity["username"]
    await db.commit(); await db.refresh(row)
    return _ipr_warning_rule_dict(row)

@router.delete(f"{settings.api_prefix}/ipr/warning-rules/{{rule_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ipr_warning_rule(rule_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_ipr_reminder_type_manage,
    )
    _require_ipr_reminder_type_manage(identity)
    row = await db.get(IprCaseWarningRule, rule_id)
    if not row: raise HTTPException(status_code=404, detail="案件预警规则不存在")
    notification_ids = list((await db.scalars(select(IprCaseWarning.notification_id).where(IprCaseWarning.rule_id == row.id, IprCaseWarning.notification_id.is_not(None)))).all())
    if notification_ids:
        await db.execute(delete(Notification).where(Notification.id.in_(notification_ids)))
    await db.execute(delete(IprCaseWarning).where(IprCaseWarning.rule_id == row.id))
    await db.delete(row); await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
