"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.constants import (
    IPR_CASE_CATEGORIES, IPR_CASE_DOCUMENT_TYPES, IPR_CASE_KINDS, IPR_REMINDER_EVENT_TYPE_BY_ID, IPR_WARNING_TIME_NODES,
    LEGACY_IPR_REMINDER_TYPE_SEEDS,
)
from app.core.dependencies import (
    AsyncSession, BusinessRecord, Document, HTTPException, IntegrityError,
    IprCaseCustomer, IprCaseFileCustomImportCandidate, IprCaseLawFirm, IprCaseLog, IprCaseReminder,
    IprCaseReminderSuppression, IprCaseReminderType, IprCaseWarning, IprCaseWarningRule, LawFirm,
    Notification, Path, SystemParameter, User, WorkflowEvent,
    date, datetime, io, or_, re,
    select, timedelta, uuid4,
)
from app.models_shared import (
    IprCaseReminderTypeQueryInput, IprCaseWarningRuleInput, IprCaseWarningRuleUpdateInput,
)


async def _next_ipr_case_serial(case_kind: str, db: AsyncSession) -> str:
    prefix = "ZL" if case_kind == "专利" else "SB"
    # The legacy system distinguishes patent and trademark case ledgers.  Keep
    # that distinction in the visible serial rather than reusing lawsuit IDs.
    for _ in range(20):
        serial = f"{prefix}{datetime.now():%y%m%d%H%M%S}{uuid4().hex[:4].upper()}"
        if not await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == serial)):
            return serial
    raise HTTPException(status_code=503, detail="知识产权案件编号生成失败，请稍后重试")


async def _next_ipr_reboot_serial(source: BusinessRecord, db: AsyncSession) -> tuple[str, str]:
    """Return the next legacy-style version number without changing the source case."""

    source_data = dict(source.data or {})
    root_serial = str(source_data.get("reboot_root_serial") or source.serial_no).strip()
    for sequence in range(1, 677):
        quotient = sequence
        suffix = ""
        while quotient:
            quotient, remainder = divmod(quotient - 1, 26)
            suffix = chr(ord("A") + remainder) + suffix
        candidate = f"{root_serial}{suffix}"
        exists = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == candidate))
        if not exists:
            return root_serial, candidate
    raise HTTPException(status_code=503, detail="知识产权案件重提编号生成失败，请稍后重试")


def _ipr_reminder_type_query_object(value: IprCaseReminderTypeQueryInput | dict | None) -> dict:
    raw = value.model_dump(mode="json") if isinstance(value, IprCaseReminderTypeQueryInput) else dict(value or {})
    case_kind = str(raw.get("case_kind") or "").strip()
    if case_kind and case_kind not in IPR_CASE_KINDS:
        raise HTTPException(status_code=422, detail="提醒类型的案件类型仅支持专利或商标")
    deadline_from = raw.get("deadline_from") or ""
    deadline_to = raw.get("deadline_to") or ""
    if deadline_from and deadline_to and str(deadline_from) > str(deadline_to):
        raise HTTPException(status_code=422, detail="提醒类型的开始期限不能晚于结束期限")
    return {
        "case_kind": case_kind,
        "case_type": str(raw.get("case_type") or "").strip(),
        "case_phase": str(raw.get("case_phase") or "").strip(),
        "statuses": list(dict.fromkeys(str(item).strip() for item in (raw.get("statuses") or []) if str(item).strip())),
        "event_type_ids": list(dict.fromkeys(int(item) for item in (raw.get("event_type_ids") or []) if isinstance(item, int) or str(item).strip().isdigit())),
        "annual_fee_monitoring": raw.get("annual_fee_monitoring"),
        "deadline_from": str(deadline_from),
        "deadline_to": str(deadline_to),
        "deadline_within_days": raw.get("deadline_within_days"),
    }


def _ipr_case_matches_reminder_type(record: BusinessRecord, query_object: dict) -> bool:
    """Evaluate the persisted legacy QueryObject against one IPR case row."""
    data = record.data or {}
    if query_object["case_kind"] and data.get("case_kind") != query_object["case_kind"]:
        return False
    if query_object["case_type"] and data.get("case_type") != query_object["case_type"]:
        return False
    if query_object["case_phase"] and data.get("case_phase") != query_object["case_phase"]:
        return False
    if query_object["statuses"] and record.status not in query_object["statuses"]:
        return False
    if query_object["annual_fee_monitoring"] is not None and bool(data.get("annual_fee_monitoring")) != bool(query_object["annual_fee_monitoring"]):
        return False
    deadline_text = str(data.get("deadline") or "")
    if query_object["deadline_from"] and deadline_text < query_object["deadline_from"]:
        return False
    if query_object["deadline_to"] and deadline_text > query_object["deadline_to"]:
        return False
    if query_object["deadline_within_days"] is not None:
        try:
            left_days = (date.fromisoformat(deadline_text) - date.today()).days
        except ValueError:
            return False
        if left_days < 0 or left_days > int(query_object["deadline_within_days"]):
            return False
    return True


async def _ipr_reminder_type_or_404(reminder_type_id: int, identity: dict, db: AsyncSession) -> IprCaseReminderType:
    row = await db.get(IprCaseReminderType, reminder_type_id)
    if not row or (not row.is_active and identity.get("role") not in {"admin", "manager"}):
        raise HTTPException(status_code=404, detail="案件提醒类型不存在或已停用")
    return row


async def _ipr_cases_for_reminder_type(reminder_type_id: int, identity: dict, db: AsyncSession, extra_conditions: list | None = None) -> tuple[IprCaseReminderType, list[BusinessRecord]]:
    from app.core.permissions import (
        _visible_ipr_cases,
    )
    reminder_type = await _ipr_reminder_type_or_404(reminder_type_id, identity, db)
    query_object = _ipr_reminder_type_query_object(reminder_type.query_object)
    rows = await _visible_ipr_cases(identity, db, extra_conditions)
    rows = [row for row in rows if _ipr_case_matches_reminder_type(row, query_object)]
    event_type_ids = query_object["event_type_ids"]
    if event_type_ids:
        matched_case_ids = set((await db.scalars(
            select(IprCaseReminder.case_record_id).where(IprCaseReminder.event_type_id.in_(event_type_ids))
        )).all())
        rows = [row for row in rows if row.id in matched_case_ids]
    rows.sort(key=lambda row: (str((row.data or {}).get("deadline") or "9999-12-31"), row.id))
    return reminder_type, rows


def _ipr_reminder_type_dict(row: IprCaseReminderType, case_count: int = 0) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "query_object": _ipr_reminder_type_query_object(row.query_object),
        "legacy_reminder_type_id": row.legacy_reminder_type_id,
        "legacy_query_object": row.legacy_query_object,
        "is_default": row.is_default,
        "is_active": row.is_active,
        "sort_order": row.sort_order,
        "case_count": case_count,
        "owner": row.owner,
        "created_by": row.created_by,
        "updated_by": row.updated_by,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


async def _ipr_case_list_conditions(
    identity: dict,
    db: AsyncSession,
    *,
    case_kind: str = "",
    record_status: str = "",
    keyword: str = "",
    annual_fee_monitoring: bool | None = None,
    case_type: str = "",
    case_phase: str = "",
    reminder_type: str = "",
    case_category: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
    search_by_month_day: bool = False,
    month_day: str = "",
    role_view: str = "",
) -> list:
    """Build the shared visible-scope conditions for the IPR list and exports."""
    from app.core.permissions import (
        _ipr_case_role_view_conditions, _record_scope_conditions,
    )
    conditions = [BusinessRecord.module == "ipr_case", *(await _record_scope_conditions(identity, db))]
    conditions.extend(_ipr_case_role_view_conditions(role_view, identity))
    if case_category:
        if case_category not in IPR_CASE_CATEGORIES:
            raise HTTPException(status_code=422, detail="知识产权案件诉讼类型无效")
        if case_category == "non_litigation":
            conditions.append(or_(
                BusinessRecord.data["case_category"].as_string() == "non_litigation",
                BusinessRecord.data["case_category"].as_string().is_(None),
            ))
        else:
            conditions.append(BusinessRecord.data["case_category"].as_string() == "litigation")
    if case_kind:
        if case_kind not in IPR_CASE_KINDS:
            raise HTTPException(status_code=422, detail="知识产权案件类型无效")
        conditions.append(BusinessRecord.data["case_kind"].as_string() == case_kind)
    if record_status:
        conditions.append(BusinessRecord.status == record_status)
    if annual_fee_monitoring is not None:
        conditions.append(BusinessRecord.data["annual_fee_monitoring"].as_boolean().is_(annual_fee_monitoring))
    if case_type:
        conditions.append(BusinessRecord.data["case_type"].as_string() == case_type)
    if case_phase:
        conditions.append(BusinessRecord.data["case_phase"].as_string() == case_phase)
    if reminder_type:
        conditions.append(
            select(IprCaseReminder.id)
            .where(
                IprCaseReminder.case_record_id == BusinessRecord.id,
                IprCaseReminder.event_type == reminder_type,
            )
            .exists()
        )
    if keyword:
        like = f"%{keyword.strip()}%"
        conditions.append(or_(BusinessRecord.serial_no.ilike(like), BusinessRecord.title.ilike(like), BusinessRecord.customer.ilike(like), BusinessRecord.data["application_no"].as_string().ilike(like)))
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="开始日期不能晚于结束日期")
    if date_from:
        conditions.append(BusinessRecord.data["application_date"].as_string() >= str(date_from))
    if date_to:
        conditions.append(BusinessRecord.data["application_date"].as_string() <= str(date_to))
    if search_by_month_day:
        if not month_day:
            raise HTTPException(status_code=422, detail="按月日查询必须填写月日")
        if not re.fullmatch(r"\d{2}-\d{2}", month_day):
            raise HTTPException(status_code=422, detail="月日格式必须为 MM-DD")
        conditions.append(or_(
            BusinessRecord.data["application_date"].as_string().like(f"%{month_day}"),
            BusinessRecord.data["deadline"].as_string().like(f"%{month_day}"),
        ))
    return conditions


def _ipr_case_export_headers() -> list[str]:
    return ["案件编号", "案件类型", "案件名称", "客户", "申请号", "申请类型", "申请人/权利人", "案件阶段", "案件负责人", "代理人", "撰稿人", "案源人", "申请日", "受理日", "案源日", "提交人", "提交日", "发明人", "办理期限", "年费年度", "年费监控", "费率", "状态"]


def _ipr_case_export_values(row: BusinessRecord) -> list[object]:
    data = row.data or {}
    return [
        row.serial_no, data.get("case_kind"), row.title, row.customer,
        data.get("application_no"), data.get("application_type"), data.get("applicant"),
        data.get("case_phase") or "", data.get("case_manager") or row.owner,
        data.get("agent") or "", data.get("writer") or data.get("copywriter_name") or "",
        data.get("case_source") or data.get("case_origin_people_name") or "",
        data.get("application_date") or "",
        data.get("accepted_at") or data.get("acceptance_date") or data.get("register_date") or "",
        data.get("case_origin_date") or data.get("origin_date") or "",
        data.get("case_submitter_name") or data.get("submitter_name") or "",
        data.get("case_submit_date") or data.get("submit_date") or "",
        data.get("case_inventor") or data.get("inventor") or "",
        data.get("deadline") or "", data.get("annual_fee_year") or "",
        "是" if data.get("annual_fee_monitoring") else "否", data.get("rate") or "", row.status,
    ]


def _ipr_litigation_rows(data: dict, key: str) -> list[dict]:
    rows = data.get(key, [])
    return [dict(row) for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


async def _save_ipr_litigation_data(record: BusinessRecord, data: dict, identity: dict, db: AsyncSession, action: str, comment: str = "") -> None:
    record.data = data
    db.add(WorkflowEvent(record_id=record.id, action=action, from_status=record.status, to_status=record.status, operator=identity["username"], comment=comment))
    await db.commit()
    await db.refresh(record)


def _ipr_law_firm_dict(link: IprCaseLawFirm, firm: LawFirm) -> dict:
    return {
        "id": link.id, "law_firm_id": firm.id, "code": firm.code, "name": firm.name,
        "phone": firm.phone, "email": firm.email, "default_contact_id": firm.default_contact_id,
        "created_by": link.created_by, "created_at": link.created_at,
    }


async def _ipr_case_customer_links(case_record: BusinessRecord, identity: dict, db: AsyncSession) -> list[IprCaseCustomer]:
    """Return explicit customer links, retaining a safe read-only fallback for pre-link records."""
    from app.core.permissions import (
        _record_scope_conditions,
    )
    links = list((await db.scalars(
        select(IprCaseCustomer).where(IprCaseCustomer.case_record_id == case_record.id).order_by(IprCaseCustomer.is_primary.desc(), IprCaseCustomer.sorting_index, IprCaseCustomer.id)
    )).all())
    if links:
        return links
    if not case_record.customer.strip():
        return []
    fallback = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == "customer", BusinessRecord.title == case_record.customer,
        *(await _record_scope_conditions(identity, db)),
    ).order_by(BusinessRecord.id))
    return [IprCaseCustomer(case_record_id=case_record.id, customer_record_id=fallback.id, is_primary=True, created_by="legacy-fallback")] if fallback else []


def _ipr_case_customer_dict(link: IprCaseCustomer, customer: BusinessRecord) -> dict:
    return {
        "id": link.id if link.id else None, "customer_id": customer.id, "customer_no": customer.serial_no,
        "name": customer.title, "status": customer.status, "is_primary": bool(link.is_primary),
        "department": customer.department, "owner": customer.owner,
    }


async def _ipr_case_contact_candidates(case_record: BusinessRecord, customer_id: int, identity: dict, db: AsyncSession) -> tuple[BusinessRecord, list[dict]]:
    from app.core.crm import (
        _customer_contact_dict, _customer_or_404,
    )
    links = await _ipr_case_customer_links(case_record, identity, db)
    if customer_id not in {item.customer_record_id for item in links}:
        raise HTTPException(status_code=422, detail="该客户尚未关联到当前知识产权案件")
    customer = await _customer_or_404(customer_id, identity, db)
    contacts = [_customer_contact_dict(item) for item in list((customer.data or {}).get("contacts", [])) if item.get("id") and item.get("is_valid", True)]
    return customer, contacts


def _ipr_case_log_dict(item: IprCaseLog, users_by_username: dict[str, User] | None = None) -> dict:
    from app.core.formatters import (
        _person_reference_display,
    )
    return {"id": item.id, "content": item.content, "created_by": item.created_by, "created_by_display_name": _person_reference_display(item.created_by, users_by_username or {})[0], "created_at": item.created_at}


async def _seed_legacy_ipr_reminder_types(db: AsyncSession) -> None:
    """Idempotently project IPR_Case_ReminderType defaults into the new schema."""
    for legacy_id, name, is_default, is_active, owner, actor, changed_at in LEGACY_IPR_REMINDER_TYPE_SEEDS:
        row = await db.scalar(select(IprCaseReminderType).where(IprCaseReminderType.legacy_reminder_type_id == legacy_id))
        if row is None:
            # A manually created row with the exact legacy name is safely
            # adopted so a normal startup cannot create a duplicate.
            row = await db.scalar(select(IprCaseReminderType).where(IprCaseReminderType.name == name))
        if row is None:
            row = IprCaseReminderType(name=name)
            db.add(row)
        row.legacy_reminder_type_id = legacy_id
        row.name = name
        row.query_object = _ipr_reminder_type_query_object({"event_type_ids": [legacy_id]})
        row.legacy_query_object = ""
        row.is_default = is_default
        row.is_active = is_active
        row.sort_order = legacy_id
        row.owner = owner
        row.created_by = actor
        row.updated_by = actor
        row.created_at = datetime.fromisoformat(changed_at)
        row.updated_at = datetime.fromisoformat(changed_at)


def _ipr_case_reminder_dict(row: IprCaseReminder, users_by_username: dict[str, User] | None = None) -> dict:
    from app.core.formatters import (
        _person_reference_display,
    )
    return {
        "id": row.id, "case_record_id": row.case_record_id, "event_type_id": row.event_type_id,
        "event_type": row.event_type, "event_date": row.reminder_date,
        "reminder_date": row.reminder_date, "deadline": row.deadline,
        "content": row.content, "creator": row.creator, "creator_display_name": _person_reference_display(row.creator, users_by_username or {})[0], "created_at": row.created_at, "updated_at": row.updated_at,
    }


def _validate_ipr_warning_rule_payload(payload: IprCaseWarningRuleInput | IprCaseWarningRuleUpdateInput) -> None:
    if "name" in payload.model_fields_set and not str(payload.name or "").strip():
        raise HTTPException(status_code=422, detail="案件预警规则名称不能为空")
    if isinstance(payload, IprCaseWarningRuleUpdateInput):
        required_fields = {"case_kind", "case_type", "case_phase", "time_node", "event_type_id", "days_before", "is_active"}
        if any(name in payload.model_fields_set and getattr(payload, name) is None for name in required_fields):
            raise HTTPException(status_code=422, detail="预警规则字段不能为 null")
    if payload.case_kind is not None and payload.case_kind and payload.case_kind not in IPR_CASE_KINDS:
        raise HTTPException(status_code=422, detail="预警规则的案件类型仅支持专利或商标")
    if payload.time_node is not None and payload.time_node not in IPR_WARNING_TIME_NODES:
        raise HTTPException(status_code=422, detail="预警时间节点仅支持案件期限或提醒期限")
    if payload.event_type_id is not None and payload.event_type_id and payload.event_type_id not in IPR_REMINDER_EVENT_TYPE_BY_ID:
        raise HTTPException(status_code=422, detail="预警规则的提醒类型无效")


def _ipr_warning_rule_dict(row: IprCaseWarningRule) -> dict:
    return {"id": row.id, "name": row.name, "case_kind": row.case_kind, "case_type": row.case_type,
            "case_phase": row.case_phase, "time_node": row.time_node, "event_type_id": row.event_type_id,
            "days_before": row.days_before, "is_active": row.is_active, "created_by": row.created_by,
            "updated_by": row.updated_by, "created_at": row.created_at, "updated_at": row.updated_at}


async def _materialize_ipr_case_warnings(identity: dict, db: AsyncSession) -> int:
    """Create due warning rows and inbox notices idempotently for visible active IPR cases."""
    from app.core.permissions import (
        _require_record_module_menu, _visible_ipr_cases,
    )
    await _require_record_module_menu("ipr_case", identity, db, action="查看")
    today = date.today()
    rules = list((await db.scalars(select(IprCaseWarningRule).where(IprCaseWarningRule.is_active.is_(True)))).all())
    cases = await _visible_ipr_cases(identity, db)
    created = 0
    for case_record in cases:
        if case_record.status != "在办" or not str(case_record.owner or "").strip():
            continue
        data = case_record.data or {}
        for rule in rules:
            if rule.case_kind and data.get("case_kind") != rule.case_kind:
                continue
            if rule.case_type and data.get("case_type") != rule.case_type:
                continue
            if rule.case_phase and data.get("case_phase") != rule.case_phase:
                continue
            sources: list[tuple[int | None, date, str]] = []
            if rule.time_node == "case_deadline":
                try:
                    sources.append((None, date.fromisoformat(str(data.get("deadline") or "")), "案件期限"))
                except ValueError:
                    pass
            else:
                reminders = list((await db.scalars(select(IprCaseReminder).where(IprCaseReminder.case_record_id == case_record.id))).all())
                suppressed = set((await db.scalars(select(IprCaseReminderSuppression.event_type_id).where(IprCaseReminderSuppression.case_record_id == case_record.id))).all())
                for reminder in reminders:
                    if rule.event_type_id and reminder.event_type_id != rule.event_type_id:
                        continue
                    if reminder.event_type_id in suppressed:
                        continue
                    sources.append((reminder.id, reminder.deadline, reminder.event_type or "提醒期限"))
            for reminder_id, due_date, node_name in sources:
                if due_date > today + timedelta(days=rule.days_before):
                    continue
                warning_source_key = f"rule-{rule.id}-case-{case_record.id}-reminder-{reminder_id or 0}-due-{due_date.isoformat()}-recipient-{case_record.owner}"
                existing = await db.scalar(select(IprCaseWarning).where(IprCaseWarning.source_key == warning_source_key))
                if existing:
                    continue
                warning = IprCaseWarning(rule_id=rule.id, case_record_id=case_record.id, reminder_id=reminder_id,
                                         due_date=due_date, recipient=case_record.owner, source_key=warning_source_key)
                try:
                    async with db.begin_nested():
                        db.add(warning)
                        await db.flush()
                except IntegrityError:
                    continue
                notice = Notification(source_key=f"ipr-warning-{warning.id}-{warning.recipient}", source_type="ipr_warning",
                                      source_id=case_record.id, sender="system", recipient=warning.recipient,
                                      notification_type="系统通知", title=f"知识产权案件预警：{rule.name}",
                                      content=f"{case_record.serial_no}｜{case_record.title}｜{node_name}：{due_date.isoformat()}",
                                      level="error" if due_date <= today else "warning", dingtalk_status="skipped")
                db.add(notice)
                await db.flush()
                warning.notification_id = notice.id
                created += 1
    return created


def _ipr_warning_dict(row: IprCaseWarning, rule: IprCaseWarningRule, case_record: BusinessRecord) -> dict:
    data = case_record.data or {}
    return {"id": row.id, "rule_id": row.rule_id, "rule_name": rule.name, "case_id": case_record.id,
            "case_no": case_record.serial_no, "case_title": case_record.title, "case_kind": data.get("case_kind", ""),
            "reminder_id": row.reminder_id, "due_date": row.due_date, "title": f"知识产权案件预警：{rule.name}",
            "content": f"{case_record.serial_no}｜{case_record.title}｜期限：{row.due_date.isoformat()}",
            "recipient": row.recipient, "status": row.status, "is_read": row.status != "未读", "read_at": row.read_at,
            "processed_at": row.processed_at, "processed_by": row.processed_by, "process_comment": row.process_comment,
            "notification_id": row.notification_id, "created_at": row.created_at}


async def _ipr_warning_for_recipient(warning_id: int, identity: dict, db: AsyncSession) -> IprCaseWarning:
    from app.core.permissions import (
        _ensure_record_module,
    )
    row = await db.get(IprCaseWarning, warning_id)
    if not row or (row.recipient != identity["username"] and identity.get("role") != "admin"):
        raise HTTPException(status_code=404, detail="案件预警不存在或无权处理")
    await _ensure_record_module(row.case_record_id, "ipr_case", identity, db)
    return row


def _ipr_case_file_type_dict(item: SystemParameter) -> dict:
    extra = item.extra or {}
    return {
        "id": item.id, "code": item.code, "name": item.name, "sort_order": item.sort_order,
        "case_kinds": list(extra.get("case_kinds") or []), "is_official": bool(extra.get("is_official")),
        "requires_transmission": bool(extra.get("requires_transmission")), "allow_repeat": bool(extra.get("allow_repeat", True)),
        "hedging_file_type_codes": list(extra.get("hedging_file_type_codes") or []),
        "hedging_fee_type_codes": list(extra.get("hedging_fee_type_codes") or []),
    }


async def _active_ipr_case_file_type(record: BusinessRecord, name: str, db: AsyncSession) -> SystemParameter:
    item = await db.scalar(select(SystemParameter).where(
        SystemParameter.category == "ipr_case_file_type", SystemParameter.name == name, SystemParameter.is_active.is_(True),
    ))
    if not item:
        raise HTTPException(status_code=422, detail="案件文档类型不存在或已停用")
    case_kinds = list((item.extra or {}).get("case_kinds") or [])
    if case_kinds and str((record.data or {}).get("case_kind") or "") not in case_kinds:
        raise HTTPException(status_code=422, detail="该文档类型不适用于当前知识产权案件类型")
    return item


def _custom_ipr_filename_parts(filename: str) -> tuple[str, str] | None:
    """Legacy rule: A(system-case-number)W(document-number).ext, case-insensitive."""
    stem = Path(filename).stem.strip()
    match = re.fullmatch(r"A(\d{1,16})W(\d{1,16})", stem, flags=re.IGNORECASE)
    return (match.group(1), match.group(2)) if match else None


def _ipr_custom_candidate_dict(row: IprCaseFileCustomImportCandidate) -> dict:
    return {
        "id": row.id, "batch_id": row.batch_id, "ipr_case_id": row.ipr_case_id,
        "custom_filename": row.custom_filename, "parsed_case_no": row.parsed_case_no,
        "parsed_document_no": row.parsed_document_no, "case_kind": row.case_kind,
        "application_no": row.application_no, "file_type": row.file_type,
        "document_date": row.document_date, "case_officer": row.case_officer,
        "fee_amount": row.fee_amount, "fee_type": row.fee_type,
        "fee_response_user": row.fee_response_user, "errors": row.errors or [],
        "status": row.status, "attachment_id": row.attachment_id,
    }


async def _refresh_ipr_custom_candidate(candidate: IprCaseFileCustomImportCandidate, identity: dict, db: AsyncSession) -> None:
    from app.core.permissions import (
        _ensure_record_module,
    )
    errors: list[str] = []
    if not candidate.parsed_case_no or not candidate.parsed_document_no:
        errors.append("文件名必须符合 A(系统案号)W(文档号).扩展名，例如 A1411137W210403.pdf")
    record = None
    if candidate.ipr_case_id:
        record = await _ensure_record_module(candidate.ipr_case_id, "ipr_case", identity, db)
        if record.status != "在办":
            errors.append("匹配案件不是在办状态")
    else:
        errors.append("未匹配到知识产权案件，请人工选择")
    if not candidate.file_type.strip():
        errors.append("缺少文档类型")
    if record and candidate.file_type.strip():
        try:
            await _active_ipr_case_file_type(record, candidate.file_type.strip(), db)
        except HTTPException as exc:
            errors.append(str(exc.detail))
    candidate.errors = list(dict.fromkeys(errors))
    candidate.status = "待确认" if not candidate.errors else "待修正"


def _ipr_case_document_bytes(record: BusinessRecord, document_type: str) -> tuple[str, bytes]:
    """Generate a real DOCX from persisted IPR case data, never from browser text."""
    document_title = IPR_CASE_DOCUMENT_TYPES[document_type]
    data = record.data or {}
    document = Document()
    document.add_heading(document_title, level=0)
    document.add_paragraph(f"案件编号：{record.serial_no}")
    document.add_paragraph(f"生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}")
    document.add_paragraph("")
    table = document.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    fields = [
        ("案件类型", data.get("case_kind") or "【待补充】"),
        ("案件名称", record.title or "【待补充】"),
        ("客户", record.customer or "【待补充】"),
        ("申请号/注册号", data.get("application_no") or "【待补充】"),
        ("申请类型", data.get("application_type") or "【待补充】"),
        ("申请人/权利人", data.get("applicant") or "【待补充】"),
        ("案件负责人", data.get("case_manager") or "【待补充】"),
        ("申请日期", data.get("application_date") or "【待补充】"),
        ("办理期限", data.get("deadline") or "【待补充】"),
        ("年费年度", data.get("annual_fee_year") or "【待补充】"),
        ("费率", data.get("rate") if data.get("rate") is not None else "【待补充】"),
    ]
    for label, value in fields:
        cells = table.add_row().cells
        cells[0].text = str(label)
        cells[1].text = str(value)
    if document_type == "authorization-letter":
        document.add_paragraph("\n兹委托本所就上述知识产权案件办理申请、答复、缴费及相关程序事项。授权范围以双方另行签署的正式委托文件为准。")
    elif document_type == "law-firm-letter":
        document.add_paragraph("\n本函用于说明本所受委托办理上述知识产权事项。具体办理范围、费用及期限以合同和书面确认文件为准。")
    elif document_type == "identity-certificate":
        document.add_paragraph("\n请核对客户主体名称、申请人/权利人信息及相关证明材料；未提供的信息已用【待补充】明确标识。")
    else:
        document.add_paragraph("\n本信息表由系统依据已保存的案件数据生成，供内部核对与交付使用。")
    output = io.BytesIO(); document.save(output)
    return document_title, output.getvalue()


async def _next_ipr_official_file_serial(db: AsyncSession) -> str:
    for _ in range(20):
        serial = f"GW{datetime.now():%y%m%d%H%M%S}{uuid4().hex[:4].upper()}"
        if not await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == serial)):
            return serial
    raise HTTPException(status_code=503, detail="知识产权官文编号生成失败，请稍后重试")
