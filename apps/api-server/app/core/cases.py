"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.constants import (
    AI_SPACE_CATEGORY, AI_SPACE_EDITABLE_SUFFIXES, CASE_COMMISSION_ROLES, CASE_CREATE_PERMISSION_BY_TYPE, CASE_DEFENDANT_FIELDS,
    CASE_EVENT_COMPLETED_STATUS, CASE_EVENT_OVERDUE_STATUS, CASE_EVENT_TIME_ZONE, CASE_EXECUTION_STATUSES, CASE_EXECUTION_STATUS_ALIASES,
    CASE_PENDING_EXECUTION_PHASES, CASE_PHASE_STATUS_BY_CODE, CASE_PLAINTIFF_FIELDS, CASE_THIRD_PARTY_FIELDS, DASHBOARD_CASE_QUEUES,
    DASHBOARD_SUPPLEMENT_EVIDENCE_STATUSES, DASHBOARD_SUPPLEMENT_OPINION_STATUSES, PERSON_NAME_PLACEHOLDER, WORD_DOCUMENT_CONTENT_TYPE, _CASE_HEARING_LEVELS,
)
from app.core.dependencies import (
    AsyncSession, BusinessRecord, CaseEvent, CaseTypeCasePhaseRelation, FileAttachment,
    HTTPException, HearingSchedule, HrSubrecord, Path, ReceivablePlan,
    String, SystemParameter, User, WorkflowEvent, date,
    datetime, func, or_, re, select,
)
from app.models_shared import (
    CaseLitigantsInput, CasePhaseChangeInput, CounselCaseSearchInput,
)


def _is_pending_execution_case(record: BusinessRecord) -> bool:
    data = record.data or {}
    return any(
        str(value or "").strip() in CASE_PENDING_EXECUTION_PHASES
        for value in (record.status, data.get("case_phase"))
    )


def _hearing_dict(item: HearingSchedule, case_record: BusinessRecord) -> dict:
    return {
        "id": item.id, "case_record_id": item.case_record_id,
        "case_no": case_record.serial_no, "case_title": case_record.title,
        "customer": case_record.customer, "hearing_date": item.hearing_date,
        "weekday": "星期" + "一二三四五六日"[item.hearing_date.weekday()],
        "hearing_time": item.hearing_time, "court": item.court, "courtroom": item.courtroom,
        "hearing_type": item.hearing_type, "hearing_lawyer": item.hearing_lawyer,
        "status": item.status, "remark": item.remark,
    }


def _dashboard_case_hearing(case_record: BusinessRecord, today: date, cutoff: date) -> dict | None:
    """Project the legacy case court fields into the dashboard schedule."""
    from app.core.formatters import (
        _case_hearing_datetime,
    )
    data = case_record.data or {}
    candidates: list[tuple[str, str, object, object]] = [
        (prefix, hearing_type, data.get(f"{prefix}_court_hearing_date"), "")
        for prefix, hearing_type in _CASE_HEARING_LEVELS
    ]
    candidates.extend((
        ("generic", "开庭", data.get("hearing_date"), data.get("hearing_time")),
        ("generic", "开庭", data.get("next_hearing_date"), data.get("next_hearing_time")),
    ))
    for prefix, hearing_type, raw_date, fallback_time in candidates:
        hearing_at = _case_hearing_datetime(raw_date, fallback_time)
        if hearing_at is None or not today <= hearing_at.date() <= cutoff:
            continue
        if prefix == "first":
            court = data.get("first_court_name") or data.get("first_instance_court") or data.get("court")
            courtroom = data.get("first_court_courtroom") or data.get("courtroom")
        elif prefix == "second":
            court = data.get("second_court_name") or data.get("second_instance_court")
            courtroom = data.get("second_court_courtroom")
        elif prefix in {"execution", "retrial"}:
            court = data.get(f"{prefix}_court_name")
            courtroom = data.get(f"{prefix}_court_courtroom")
        else:
            court = data.get("court") or data.get("first_court_name") or data.get("first_instance_court")
            courtroom = data.get("courtroom") or data.get("first_court_courtroom")
        return {
            "case_record_id": case_record.id,
            "case_no": case_record.serial_no,
            "client": case_record.customer,
            "weekday": "星期" + "一二三四五六日"[hearing_at.weekday()],
            "date": str(hearing_at.date()),
            "time": hearing_at.strftime("%H:%M"),
            "court": str(court or ""),
            "lawyer": str(data.get("hearing_lawyer") or ""),
            "agent": ",".join(data.get("handling_lawyers", [])),
            "assistant": str(data.get("assistant") or ""),
            "hearing_type": hearing_type,
            "courtroom": str(courtroom or ""),
        }
    return None


async def _case_archive_checks(case_record: BusinessRecord, db: AsyncSession) -> dict[str, bool]:
    """Calculate archive readiness from persisted business facts, never client checkboxes."""
    from app.core.documents import (
        _sync_case_document_readiness,
    )
    from app.core.formatters import (
        _record_links_to_case,
    )
    data = dict(case_record.data or {})
    documents_complete = await _sync_case_document_readiness(case_record, db)
    related_rows = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module.in_({"finance", "invoice", "refund"})))).all()

    related = [item for item in related_rows if _record_links_to_case(item, case_record)]
    fees = [item for item in related if item.module == "finance"]
    invoices = [item for item in related if item.module == "invoice"]
    refunds = [item for item in related if item.module == "refund"]
    fee_terminal = {"已付款", "已核销", "已对账", "已作废", "已撤销", "不缴费"}
    invoice_terminal = {"已开票", "已作废", "已撤回"}
    refund_terminal = {"已退款", "已作废", "已撤回"}
    fees_settled = all(item.status in fee_terminal for item in fees)
    contract_id = int(data.get("contract_id") or 0)
    receivables = (await db.scalars(select(ReceivablePlan).where(ReceivablePlan.contract_record_id == contract_id))).all() if contract_id else []
    receivables_complete = all(float(item.amount) - float(item.received_amount or 0) <= 0.001 for item in receivables)
    finance_complete = fees_settled and all(item.status in invoice_terminal for item in invoices) and all(item.status in refund_terminal for item in refunds) and receivables_complete
    checks = {
        "case_closed": bool(data.get("case_closed_at") and data.get("case_closed_by")),
        "fees_settled": fees_settled,
        "documents_complete": documents_complete,
        "finance_complete": finance_complete,
    }
    case_record.data = {**(case_record.data or {}), **checks}
    return checks


async def _resolve_active_case_people(values: list[object], db: AsyncSession, *, field_name: str) -> tuple[list[str], list[str]]:
    """Resolve case-team inputs once and persist usernames alongside display values.

    The UI remains compatible with the old name-based forms, but access control
    never depends on a mutable/duplicate display name after a case is saved.
    """
    labels = list(dict.fromkeys(str(value or "").strip() for value in values if str(value or "").strip()))
    if not labels:
        return [], []
    users = list((await db.scalars(select(User).where(
        User.is_active.is_(True),
        or_(User.username.in_(labels), User.display_name.in_(labels)),
    ))).all())
    by_username = {user.username: user for user in users}
    by_display: dict[str, list[User]] = {}
    for user in users:
        by_display.setdefault(user.display_name, []).append(user)
    resolved_labels: list[str] = []
    resolved_usernames: list[str] = []
    invalid: list[str] = []
    for label in labels:
        user = by_username.get(label)
        if not user:
            matches = by_display.get(label, [])
            user = matches[0] if len(matches) == 1 else None
        if not user:
            invalid.append(label)
            continue
        # Persist a stable, human-readable display value; usernames remain the
        # authoritative ACL identity and are what new selection controls submit.
        # The legacy people picker allows every active staff account.  HR position
        # text is optional for migrated accounts and must not invalidate a person
        # that the authoritative picker already exposed.
        resolved_labels.append(user.display_name)
        if user.username not in resolved_usernames:
            resolved_usernames.append(user.username)
    if invalid:
        raise HTTPException(status_code=422, detail=f"{field_name}不存在、已停用或姓名不唯一：{'、'.join(invalid)}")
    return resolved_labels, resolved_usernames


def _case_team_payload(
    case_data: dict, handling_lawyers: list[str], handling_usernames: list[str], assistant: str | list[str], assistant_username: str | list[str],
) -> dict:
    """Keep legacy display fields and the stable access-control projection in sync."""
    assistants = list(dict.fromkeys(
        str(value or "").strip() for value in (assistant if isinstance(assistant, list) else [assistant]) if str(value or "").strip()
    ))
    assistant_usernames = list(dict.fromkeys(
        str(value or "").strip() for value in (assistant_username if isinstance(assistant_username, list) else [assistant_username]) if str(value or "").strip()
    ))
    return {
        **case_data,
        "handling_lawyers": handling_lawyers,
        "assistant": assistants[0] if assistants else "",
        "assistants": assistants,
        "handling_lawyer_usernames": handling_usernames,
        "assistant_username": assistant_usernames[0] if assistant_usernames else "",
        "assistant_usernames": assistant_usernames,
        "case_team_usernames": list(dict.fromkeys([*handling_usernames, *assistant_usernames])),
    }


def _prioritize_new_case_assistants(
    case_data: dict,
    assistant_values: list[str],
    assistant_usernames: list[str],
) -> tuple[list[str], list[str]]:
    """Place newly added assistants first while retaining the stored relative order."""
    from app.core.contracts import (
        _contract_person_values,
    )
    existing_usernames = set(_contract_person_values(
        case_data.get("assistant_usernames") or case_data.get("assistant_username")
    ))
    existing_names = set(_contract_person_values(
        case_data.get("assistants") or case_data.get("assistant")
    ))
    pairs = list(zip(assistant_values, assistant_usernames))
    added = [pair for pair in pairs if pair[1] not in existing_usernames and pair[0] not in existing_names]
    retained = [pair for pair in pairs if pair[1] in existing_usernames or pair[0] in existing_names]
    ordered = [*reversed(added), *retained]
    return [pair[0] for pair in ordered], [pair[1] for pair in ordered]


async def _case_team_role(case_record: BusinessRecord, identity: dict, db: AsyncSession) -> str:
    """Return manager/handling_lawyer/assistant/none for a visible case.

    New writes use stable usernames.  The narrowly-scoped legacy fallback keeps
    old rows usable only where the current user's display name is unique.
    """
    if identity.get("role") == "admin" or case_record.owner == identity["username"]:
        return "manager"
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if identity.get("role") == "manager" and user and case_record.department == user.department:
        return "manager"
    data = case_record.data or {}
    username = identity["username"]
    handling_usernames = {str(value or "").strip() for value in data.get("handling_lawyer_usernames", [])}
    assistant_usernames = {str(value or "").strip() for value in (data.get("assistant_usernames") or [])}
    assistant_username = str(data.get("assistant_username") or "").strip()
    if username in handling_usernames:
        return "handling_lawyer"
    if username and (username == assistant_username or username in assistant_usernames):
        return "assistant"
    if data.get("case_team_usernames"):
        return "none"
    # Legacy-only fallback.  Display names may be used only when unique.
    display_name = str(user.display_name or "").strip() if user else ""
    display_is_unique = bool(display_name) and (await db.scalar(select(func.count(User.id)).where(User.is_active.is_(True), User.display_name == display_name)) == 1)
    handler_labels = {str(value or "").strip() for value in data.get("handling_lawyers", [])}
    assistant_label = str(data.get("assistant") or "").strip()
    if username in handler_labels or (display_is_unique and display_name in handler_labels):
        return "handling_lawyer"
    if username == assistant_label or (display_is_unique and display_name == assistant_label):
        return "assistant"
    return "none"


def _case_file_type_tree(items: list[SystemParameter]) -> list[dict]:
    flat: list[dict] = []
    for item in items:
        extra = item.extra or {}
        flat.append({
            "id": item.id,
            "code": item.code,
            "value": item.name,
            "title": item.name,
            "parent_code": str(extra.get("parent_code") or "").strip(),
            "children": [],
        })
    by_code = {row["code"]: row for row in flat}
    roots: list[dict] = []
    for row in flat:
        parent_code = row["parent_code"]
        if parent_code and parent_code in by_code:
            by_code[parent_code]["children"].append(row)
        else:
            roots.append(row)
    def _clean(nodes: list[dict]) -> list[dict]:
        result = []
        for node in nodes:
            children = _clean(node["children"])
            entry = {
                "id": node["id"],
                "code": node["code"],
                "value": node["value"],
                "title": node["title"],
            }
            if children:
                entry["children"] = children
            result.append(entry)
        return result
    tree = _clean(roots)
    if not any(node["value"] == "普通附件" for node in flat):
        tree.append({"id": 0, "code": "COMMON", "value": "普通附件", "title": "普通附件"})
    return tree


def _case_phase_changed_days(item: BusinessRecord, *, as_of: date | None = None) -> int:
    from app.core.formatters import (
        _case_phase_changed_date,
    )
    return max(((as_of or date.today()) - _case_phase_changed_date(item)).days, 0)


def _is_urgent_case(item: BusinessRecord, *, as_of: date | None = None) -> bool:
    return _case_phase_changed_days(item, as_of=as_of) > 365


def _matches_dashboard_case_queue(item: BusinessRecord, queue: str) -> bool:
    data = item.data or {}
    legacy = data.get("legacy_record") if isinstance(data.get("legacy_record"), dict) else {}
    case_type = str(data.get("case_type") or "").strip()
    status_name = str(
        data.get("case_phase_name")
        or legacy.get("CasePhaseName")
        or item.status
        or ""
    ).strip()
    if queue == "supplement_evidence":
        return case_type in {"民事争议", "民事案件"} and status_name in DASHBOARD_SUPPLEMENT_EVIDENCE_STATUSES
    if queue == "supplement_opinion":
        return case_type in {"民事争议", "民事案件"} and status_name in DASHBOARD_SUPPLEMENT_OPINION_STATUSES
    if queue == "urgent":
        return _is_urgent_case(item)
    return False


def _dashboard_latest_case_row(
    record: BusinessRecord,
    customer: BusinessRecord | None,
    users_by_username: dict[str, User],
) -> dict:
    from app.core.formatters import (
        _dashboard_case_date, _dashboard_text,
    )
    from app.core.system import (
        _dashboard_people,
    )
    data = record.data or {}
    legacy = data.get("legacy_record") if isinstance(data.get("legacy_record"), dict) else {}
    customer_data = customer.data or {} if customer else {}
    manager_values = (
        customer_data.get("customer_managers")
        or ([customer.owner] if customer and customer.owner else [])
    )
    registered_at = _dashboard_case_date(record)
    return {
        "case_no": record.serial_no,
        "stage": str(data.get("case_phase_name") or legacy.get("CasePhaseName") or record.status or ""),
        "plaintiff": _dashboard_text(
            data.get("plaintiff") or data.get("plaintiffs") or legacy.get("AppellantNames") or record.customer
        ),
        "defendant": _dashboard_text(
            data.get("opponent") or data.get("defendant") or data.get("defendants") or legacy.get("AppelleeNames")
        ),
        "date": registered_at.date().isoformat() if registered_at != datetime.min else "",
        "manager": _dashboard_people(
            users_by_username,
            data.get("customer_manager_usernames"),
            data.get("customer_manager_username"),
            data.get("customer_managers"),
            data.get("customer_manager"),
            manager_values,
            data.get("customer_manager_display_names"),
            data.get("customer_manager_display_name"),
            customer_data.get("customer_manager_display_names"),
            customer_data.get("customer_manager_display_name"),
            legacy.get("CoordinatorName"),
        ),
        "lawyer": _dashboard_people(
            users_by_username,
            data.get("hearing_lawyer_usernames"),
            data.get("hearing_lawyer_username"),
            data.get("hearing_lawyers"),
            data.get("hearing_lawyer"),
            data.get("hearing_lawyer_display_names"),
            data.get("hearing_lawyer_display_name"),
            legacy.get("CourtLawyerName"),
        ),
        "agent": _dashboard_people(
            users_by_username,
            data.get("handling_lawyer_usernames"),
            data.get("handling_lawyers"),
            data.get("handling_lawyer_display_names"),
            data.get("handling_lawyer_display_name"),
            legacy.get("CaseLawyerName"),
        ),
        "assistant": _dashboard_people(
            users_by_username,
            data.get("assistant_usernames"),
            data.get("assistant_username"),
            data.get("assistants"),
            data.get("assistant"),
            data.get("assistant_display_names"),
            data.get("assistant_display_name"),
            legacy.get("CaseAssistantName"),
        ),
    }


def _large_screen_case_is_excluded(case: BusinessRecord) -> bool:
    """Keep drafts and cancelled/merged records out of operational case totals."""
    status_value = str(case.status or "").strip()
    return status_value in {"草稿", "已撤销", "已撤回", "已作废", "已删除", "已合并"}


def _large_screen_case_is_closed(case: BusinessRecord) -> bool:
    """Use the dedicated close marker, with archived legacy rows as a fallback."""
    data = case.data or {}
    record_status = str(case.status or "").strip()
    phase = str(data.get("case_phase_name") or data.get("case_phase") or "").strip()
    closed_phases = {
        "已结案", "一审和解结案", "一审判决结案", "二审和解结案",
        "二审判决结案", "再审和解结案", "再审判决结案", "执行结案",
    }
    return bool(data.get("case_closed_at")) or record_status in {"已归档", "亏损归档"} or phase in closed_phases or record_status in closed_phases


async def _selected_ordinary_case_export_records(ids: str, identity: dict, db: AsyncSession) -> list[BusinessRecord]:
    """Resolve only selected, visible ordinary cases; never broaden export scope."""
    from app.core.permissions import (
        _require_record_module_menu, _scoped_export_records,
    )
    from app.core.system import (
        _export_ids,
    )
    await _require_record_module_menu("case", identity, db, action="导出")
    selected_ids = _export_ids(ids)
    if not selected_ids:
        raise HTTPException(status_code=422, detail="请至少选择一条案件记录")
    records = await _scoped_export_records("case", ids, identity, db)
    if len(records) != len(selected_ids):
        raise HTTPException(status_code=404, detail="存在案件记录不存在或当前账号无权导出")
    counsel_cases = [record for record in records if (record.data or {}).get("case_type") == "法律顾问"]
    if counsel_cases:
        raise HTTPException(status_code=422, detail="法律顾问案件请使用法律顾问专用导出")
    return records


def _ordinary_case_export_rows(records: list[BusinessRecord]) -> list[list[object]]:
    rows: list[list[object]] = []
    for record in records:
        data = record.data or {}
        handling_lawyers = data.get("handling_lawyers") or data.get("handling_lawyer") or ""
        if isinstance(handling_lawyers, list):
            handling_lawyers = "、".join(str(item) for item in handling_lawyers if str(item).strip())
        rows.append([
            record.serial_no, record.title, data.get("case_type", ""), record.status, record.customer,
            data.get("contract_no", ""), data.get("cause_or_charge") or data.get("cause", ""), handling_lawyers,
            data.get("assistant", ""), data.get("hearing_lawyer", ""), data.get("court") or data.get("first_court_name", ""),
            data.get("filing_date", ""), record.created_at.strftime("%Y-%m-%d") if record.created_at else "",
        ])
    return rows


def _is_civil_case_type(value: object) -> bool:
    return str(value or "").strip() in {
        "民事案件",
        "民事争议",
    }


def _case_party_values(data: dict, fields: tuple[str, ...]) -> list[str]:
    """Use the first populated historical field family, preserving stored order."""
    from app.core.system import (
        _conflict_entity_tokens,
    )
    for field in fields:
        tokens = _conflict_entity_tokens(data.get(field))
        if tokens:
            return tokens
    return []


def _case_party_match_values(data: dict, fields: tuple[str, ...]) -> list[str]:
    """Match only the same highest-priority field that the result will show."""
    from app.core.system import (
        _conflict_entity_tokens,
    )
    for field in fields:
        raw_value = data.get(field)
        displayed = _conflict_entity_tokens(raw_value)
        if not displayed:
            continue
        if isinstance(raw_value, (list, tuple, set)):
            return displayed
        full_value = str(raw_value or "").strip()
        # Keep the complete scalar as an exact candidate so an English legal
        # name containing a comma remains searchable, while retaining legacy
        # comma-delimited entities as additional exact candidates.
        return list(dict.fromkeys([full_value, *displayed]))
    return []


def _case_conflict_entities(record: BusinessRecord) -> list[str]:
    data = record.data or {}
    values = [record.customer.strip()] if record.customer.strip() else []
    for fields in (CASE_PLAINTIFF_FIELDS, CASE_DEFENDANT_FIELDS, CASE_THIRD_PARTY_FIELDS):
        for value in _case_party_match_values(data, fields):
            if value not in values:
                values.append(value)
    return values


def _case_commission_person_tokens(data: dict, fields: tuple[str, ...]) -> list[str]:
    # A role is stored in both stable username and legacy display-name aliases.
    # Use the first populated projection so migrated aliases cannot add stale or
    # duplicate people to the same commission calculation.
    for field in fields:
        raw = data.get(field)
        tokens: list[str] = []
        values = raw if isinstance(raw, list) else [raw]
        for value in values:
            for token in re.split(r"[,，、;/；\n]+", str(value or "")):
                normalized = token.strip()
                if normalized and normalized not in {"—", "-", "无", "未分配", PERSON_NAME_PLACEHOLDER}:
                    tokens.append(normalized)
        if tokens:
            return list(dict.fromkeys(tokens))
    return []


async def _commission_scheme_for_case(employee_id: int, case_date: date, db: AsyncSession) -> dict | None:
    records = list((await db.scalars(select(HrSubrecord).where(
        HrSubrecord.employee_id == employee_id,
        HrSubrecord.kind == "commission",
    ).order_by(HrSubrecord.created_at.desc(), HrSubrecord.id.desc()))).all())
    for record in records:
        data = record.data or {}
        try:
            start = date.fromisoformat(str(data.get("start_date") or ""))
            end = date.fromisoformat(str(data.get("end_date") or "")) if data.get("end_date") else None
        except ValueError:
            continue
        if start <= case_date and (end is None or case_date <= end):
            return data
    return None


async def _case_commission_preview(
    case_id: int,
    source_fee_id: int,
    identity: dict,
    db: AsyncSession,
) -> dict:
    from app.core.finance import (
        _round_fee_amount,
    )
    from app.core.formatters import (
        _dashboard_case_date,
    )
    from app.core.permissions import (
        _case_detail_action_capabilities, _ensure_record_module,
    )
    from app.core.system import (
        _commission_employee_index,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    if not (await _case_detail_action_capabilities(case_record, identity, db))["can_create_finance"]:
        raise HTTPException(status_code=403, detail="当前账号没有新增案件提成权限")
    source_fee = await db.get(BusinessRecord, source_fee_id)
    source_data = source_fee.data if source_fee else {}
    if not source_fee or source_fee.module != "finance":
        raise HTTPException(status_code=404, detail="所选案件费用不存在")
    if int(source_data.get("case_id") or 0) != case_record.id and str(source_data.get("case_no") or "") != case_record.serial_no:
        raise HTTPException(status_code=409, detail="所选费用不属于当前案件")
    source_fee_types = {
        str(value or "").strip()
        for value in (
            source_data.get("expense_subtype"), source_data.get("fee_type"),
            source_data.get("base_fee_type"), source_fee.title,
        )
        if str(value or "").strip()
    }
    if not any("代理费" in fee_type for fee_type in source_fee_types):
        raise HTTPException(status_code=422, detail="新建提成必须选择一条代理费")
    base_amount = _round_fee_amount(float(source_data.get("amount") or 0))
    if base_amount <= 0:
        raise HTTPException(status_code=422, detail="所选代理费金额必须大于 0")

    employee_index = await _commission_employee_index(db)
    case_data = case_record.data or {}
    resolved_case_date = _dashboard_case_date(case_record)
    case_date = resolved_case_date.date() if resolved_case_date != datetime.min else date.today()
    rows: list[dict] = []
    missing: list[str] = []
    personnel: list[dict] = []
    seen_role_employees: set[tuple[str, int]] = set()
    for role in CASE_COMMISSION_ROLES:
        for token in _case_commission_person_tokens(case_data, role["fields"]):
            employee = employee_index.get(token.lower())
            if not employee:
                missing.append(f"{token}未设{role['label']}提成")
                continue
            pair = (str(role["key"]), employee.id)
            if pair in seen_role_employees:
                continue
            seen_role_employees.add(pair)
            employee_data = employee.data or {}
            username = str(employee_data.get("username") or employee.owner or "").strip()
            display_name = str(employee.title or token).strip()
            personnel.append({"role": role["label"], "username": username, "display_name": display_name})
            scheme = await _commission_scheme_for_case(employee.id, case_date, db)
            rate = float((scheme or {}).get(role["rate_field"]) or 0)
            fixed = float((scheme or {}).get(role["fixed_field"]) or 0)
            if rate <= 0 and fixed <= 0:
                missing.append(f"{display_name}未设{role['label']}提成")
                continue
            if rate > 0:
                amount = _round_fee_amount(base_amount * rate)
                rows.append({
                    "preview_key": f"{role['key']}:{employee.id}:rate",
                    "case_no": case_record.serial_no, "commission_role": role["label"],
                    "commission_type": role["rate_name"], "expense_subtype": role["subtype"],
                    "employee_username": username, "employee_display_name": display_name,
                    "base_amount": base_amount, "rate": rate, "fixed_amount": 0,
                    "reference_commission": amount, "actual_amount": amount, "remark": "",
                })
            if fixed > 0:
                amount = _round_fee_amount(fixed)
                rows.append({
                    "preview_key": f"{role['key']}:{employee.id}:fixed",
                    "case_no": case_record.serial_no, "commission_role": role["label"],
                    "commission_type": role["fixed_name"], "expense_subtype": role["subtype"],
                    "employee_username": username, "employee_display_name": display_name,
                    "base_amount": base_amount, "rate": 0, "fixed_amount": amount,
                    "reference_commission": amount, "actual_amount": amount, "remark": "",
                })
    return {
        "case": {"id": case_record.id, "serial_no": case_record.serial_no, "title": case_record.title},
        "source_fee": {
            "id": source_fee.id, "serial_no": source_fee.serial_no,
            "amount": base_amount, "fee_type": "代理费",
            "refund_amount": _round_fee_amount(float(source_data.get("refund_amount") or source_data.get("refund_requested_amount") or 0)),
            "invoice_over_amount": _round_fee_amount(float(source_data.get("invoice_over_amount") or source_data.get("over_invoice_amount") or 0)),
            "cost_over_amount": _round_fee_amount(float(source_data.get("cost_over_amount") or source_data.get("over_invoice_cost") or 0)),
        },
        "case_date": str(case_date), "personnel": personnel, "items": rows,
        "missing_messages": list(dict.fromkeys(missing)),
    }


def _case_event_status(item: CaseEvent) -> str:
    if item.status != CASE_EVENT_COMPLETED_STATUS and item.deadline and item.deadline < datetime.now(CASE_EVENT_TIME_ZONE).date():
        return CASE_EVENT_OVERDUE_STATUS
    return item.status


def _case_event_mutable_by(item: CaseEvent, identity: dict, team_role: str) -> bool:
    return bool(
        team_role == "manager"
        or identity.get("role") in {"admin", "manager"}
        or item.creator == identity["username"]
    )


def _case_event_dict(item: CaseEvent, users_by_username: dict[str, User], identity: dict, *, can_manage: bool, team_role: str) -> dict:
    from app.core.formatters import (
        _case_event_display_time, _person_reference_display,
    )
    return {
        "id": item.id,
        "case_id": item.case_record_id,
        "case_record_id": item.case_record_id,
        "event_type_id": item.event_type_id,
        "event_type": item.event_type,
        "event_time": _case_event_display_time(item.event_time),
        "content": item.content,
        "deadline": item.deadline,
        "reminder_enabled": item.reminder_enabled,
        "remind_at": _case_event_display_time(item.remind_at),
        "reminder_record_id": item.reminder_record_id,
        "status": _case_event_status(item),
        "stored_status": item.status,
        "is_active": item.is_active,
        "creator": item.creator,
        "creator_display_name": _person_reference_display(item.creator, users_by_username)[0],
        "updated_by": item.updated_by,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "can_edit": can_manage and _case_event_mutable_by(item, identity, team_role),
        "can_delete": can_manage and _case_event_mutable_by(item, identity, team_role),
    }


async def _delete_case_events_for_case_cleanup(case_id: int, db: AsyncSession) -> None:
    """Remove event rows and their reminder projections before a test case is removed.

    This is explicit even though production databases enforce the CaseEvent FK:
    SQLite test connections may not have foreign-key pragmas enabled.
    """
    items = list((await db.scalars(select(CaseEvent).where(CaseEvent.case_record_id == case_id))).all())
    reminder_ids = [item.reminder_record_id for item in items if item.reminder_record_id]
    if reminder_ids:
        reminders = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.id.in_(reminder_ids), BusinessRecord.module == "case_reminder",
        ))).all())
        for reminder in reminders:
            if int((reminder.data or {}).get("case_id") or 0) == case_id:
                await db.delete(reminder)
    for item in items:
        await db.delete(item)


async def _query_counsel_cases(
    body: CounselCaseSearchInput,
    identity: dict,
    db: AsyncSession,
    *,
    counsel_only: bool = True,
    include_status_filter: bool = True,
) -> list[BusinessRecord]:
    from app.core.crm import (
        _customer_or_404,
    )
    from app.core.formatters import (
        _record_belongs_to_customer,
    )
    from app.core.permissions import (
        _case_mine_scope_condition, _record_scope_conditions,
    )
    if body.scope not in {"mine", "department", "company"}:
        raise HTTPException(status_code=422, detail="法律顾问案件查询范围无效")
    if body.case_queue and body.case_queue not in DASHBOARD_CASE_QUEUES:
        raise HTTPException(status_code=422, detail="案件工作队列无效")
    if body.sort_order not in {"updated_desc", "updated_asc", "created_desc", "created_asc", "status_asc", "case_no_asc", "case_no_desc"}:
        raise HTTPException(status_code=422, detail="法律顾问案件排序方式无效")
    logic_aliases = {"and": "and", "or": "or", "intersection": "and", "union": "or", "交集": "and", "并集": "or"}
    advanced_logic = logic_aliases.get(str(body.advanced_logic or "").strip().casefold())
    if not advanced_logic:
        raise HTTPException(status_code=422, detail="高级查询组合方式无效")
    date_ranges = (
        ("source date", body.source_from, body.source_to),
        ("hearing date", body.hearing_from, body.hearing_to),
        ("资助申请日期", body.assisted_request_date_from, body.assisted_request_date_to),
        ("资助办理日期", body.assisted_response_date_from, body.assisted_response_date_to),
        ("费用通知日期", body.finance_inform_date_from, body.finance_inform_date_to),
        ("费用到账日期", body.finance_gained_date_from, body.finance_gained_date_to),
        ("账单日期", body.finance_bill_date_from, body.finance_bill_date_to),
        ("文档上传日期", body.file_uploading_time_from, body.file_uploading_time_to),
    )
    for label, start_date, end_date in date_ranges:
        if start_date and end_date and start_date > end_date:
            raise HTTPException(status_code=422, detail=f"{label}范围无效")
    relation_customer = await _customer_or_404(body.customer_id, identity, db) if body.customer_id else None
    record_conditions = [BusinessRecord.module == "case"]
    if relation_customer is None:
        record_conditions.extend(await _record_scope_conditions(identity, db))
        if body.scope == "mine":
            record_conditions.append(await _case_mine_scope_condition(identity, db))
    keyword = body.keyword.strip()
    if keyword:
        keyword_pattern = f"%{keyword}%"
        record_conditions.append(or_(
            BusinessRecord.serial_no.ilike(keyword_pattern),
            BusinessRecord.title.ilike(keyword_pattern),
            BusinessRecord.customer.ilike(keyword_pattern),
            BusinessRecord.data.cast(String).ilike(keyword_pattern),
        ))
    records = list((await db.scalars(select(BusinessRecord).where(*record_conditions))).all())
    requested_types = {str(item).strip() for item in body.case_types if str(item).strip()}
    if body.case_type.strip():
        requested_types.add(body.case_type.strip())
    if counsel_only:
        records = [record for record in records if str((record.data or {}).get("case_type") or "") == "法律顾问"]
    elif requested_types:
        records = [record for record in records if str((record.data or {}).get("case_type") or "") in requested_types]
    elif not body.case_queue:
        records = [record for record in records if str((record.data or {}).get("case_type") or "") != "法律顾问"]
    if body.case_queue:
        records = [record for record in records if _matches_dashboard_case_queue(record, body.case_queue)]
    # ``mine`` is applied in SQL above with stable owner/team/legacy-participant
    # identities.  This keeps administrator personal lists personal without
    # dropping migrated participant cases.  Department is the only additional
    # in-memory boundary.
    if body.scope == "department" and relation_customer is None:
        department = str(identity.get("department") or "").strip()
        records = [record for record in records if department and record.department == department]

    document_names: dict[int, str] = {}
    record_attachments: dict[int, list[FileAttachment]] = {}
    log_content_by_record: dict[int, str] = {}
    finance_by_case_id: dict[int, list[BusinessRecord]] = {}
    finance_by_case_no: dict[str, list[BusinessRecord]] = {}
    record_ids = [record.id for record in records]
    needs_attachments = bool(
        body.document_name.strip() or body.file_uploading_user.strip()
        or body.file_uploading_time_from or body.file_uploading_time_to
        or body.file_type_ids
    )
    needs_finance = bool(
        body.finance_inform_date_from or body.finance_inform_date_to
        or body.finance_gained_date_from or body.finance_gained_date_to
        or body.finance_response_user.strip() or body.finance_bill_no.strip()
        or body.finance_bill_statuses
        or body.finance_bill_date_from or body.finance_bill_date_to
        or body.finance_fee_type_ids
    )
    # Related rows are only search inputs, never part of this helper's result.
    # Avoid materializing every case's audit history on an unfiltered first page.
    if record_ids and needs_attachments:
        attachments = (await db.scalars(select(FileAttachment).where(FileAttachment.record_id.in_(record_ids)))).all()
        for attachment in attachments:
            if attachment.record_id is not None:
                record_attachments.setdefault(attachment.record_id, []).append(attachment)
                document_names[attachment.record_id] = f"{document_names.get(attachment.record_id, '')} {attachment.original_name}".strip()
    if record_ids and body.log_content.strip():
        events = (await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id.in_(record_ids)))).all()
        for event in events:
            event_text = " ".join(part for part in (event.action, event.comment, event.operator) if part)
            log_content_by_record[event.record_id] = f"{log_content_by_record.get(event.record_id, '')} {event_text}".strip()
    finance_records: list[BusinessRecord] = []
    if record_ids and needs_finance:
        candidate_serial_nos = [record.serial_no for record in records if record.serial_no]
        finance_link = or_(
            BusinessRecord.data["case_id"].as_integer().in_(record_ids),
            BusinessRecord.data["case_no"].as_string().in_(candidate_serial_nos),
        )
        finance_records = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "finance",
            finance_link,
            *(await _record_scope_conditions(identity, db)),
        ))).all())
    for finance_record in finance_records:
        finance_data = finance_record.data or {}
        linked_case_id = finance_data.get("case_id")
        try:
            if linked_case_id is not None:
                finance_by_case_id.setdefault(int(linked_case_id), []).append(finance_record)
        except (TypeError, ValueError):
            pass
        linked_case_no = str(finance_data.get("case_no") or "").strip()
        if linked_case_no:
            finance_by_case_no.setdefault(linked_case_no, []).append(finance_record)

    def contains(value: object, expected: str) -> bool:
        return not expected.strip() or expected.strip().casefold() in str(value or "").casefold()

    def value(data: dict, *keys: str) -> object:
        for key in keys:
            candidate = data.get(key)
            if candidate not in (None, "", []):
                return candidate
        return ""

    def parse_value_date(raw: object) -> date | None:
        if isinstance(raw, datetime):
            return raw.date()
        if isinstance(raw, date):
            return raw
        text_value = str(raw or "").strip()
        if not text_value:
            return None
        try:
            return date.fromisoformat(text_value[:10])
        except ValueError:
            return None

    def searchable_text(raw: object) -> str:
        if isinstance(raw, dict):
            return " ".join(searchable_text(item) for item in raw.values())
        if isinstance(raw, (list, tuple, set)):
            return " ".join(searchable_text(item) for item in raw)
        return str(raw or "")

    def text_condition(raw: object, expected: str, negate: bool = False) -> bool:
        if not expected.strip():
            return True
        found = expected.strip().casefold() in searchable_text(raw).casefold()
        return not found if negate else found

    def list_condition(raw: object, expected: list[str], negate: bool = False) -> bool:
        wanted = {str(item).strip().casefold() for item in expected if str(item).strip()}
        if not wanted:
            return True
        values = raw if isinstance(raw, (list, tuple, set)) else [raw]
        found = bool(wanted.intersection({str(item).strip().casefold() for item in values if str(item).strip()}))
        return not found if negate else found

    def date_condition(raw: object, start_date: date | None, end_date: date | None, negate: bool = False) -> bool:
        if not start_date and not end_date:
            return True
        candidate = parse_value_date(raw)
        found = candidate is not None and (not start_date or candidate >= start_date) and (not end_date or candidate <= end_date)
        return not found if negate else found

    filtered: list[BusinessRecord] = []
    for record in records:
        data = record.data or {}
        if relation_customer is not None:
            if not _record_belongs_to_customer(record, relation_customer, relation_customer.title): continue
        elif body.customer_no.strip():
            if str(data.get("customer_no") or "").strip() != body.customer_no.strip(): continue
        elif not contains(record.customer, body.customer): continue
        if not contains(record.serial_no, body.serial_no): continue
        keyword_fields = (
            record.serial_no,
            record.title,
            record.customer,
            value(data, "plaintiff", "plaintiffs"),
            value(data, "defendant", "defendants", "opponent"),
            value(data, "court", "court_name", "first_court_name"),
            value(data, "court_case_no", "first_court_case_no", "first_instance_no"),
            value(data, "second_court_case_no", "second_instance_no"),
            value(data, "execution_case_no", "retrial_case_no"),
            value(data, "notary_no", "notary_nos", "certificate_no"),
            value(data, "clue_no", "clue_nos", "investigation_clue", "investigation_clue_nos", "source_clue_no"),
        )
        if body.keyword and not contains(" ".join(searchable_text(item) for item in keyword_fields), body.keyword): continue
        if not contains(value(data, "plaintiff", "plaintiffs") or record.customer, body.plaintiff): continue
        if not contains(value(data, "prosecutor", "procuratorate", "first_procuratorate_name"), body.prosecutor): continue
        if not contains(value(data, "defendant", "defendants", "opponent"), body.defendant): continue
        if not contains(value(data, "evidence_org", "evidence_organization"), body.evidence_org): continue
        if not contains(value(data, "notary_no", "notary_nos", "certificate_no"), body.notary_no): continue
        if not contains(value(data, "hearing_lawyer", "hearing_lawyers", "court_lawyer"), body.hearing_lawyer): continue
        if not contains(value(data, "investigator", "investigators", "investigation_user"), body.investigator): continue
        if not contains(value(data, "court", "court_name", "first_court_name"), body.court): continue
        if not contains(value(data, "channel", "case_channel"), body.channel): continue
        if not contains(value(data, "warehouse", "evidence_warehouse"), body.warehouse): continue
        if not contains(value(data, "area", "case_area"), body.area): continue
        if not contains(value(data, "location", "case_location"), body.location): continue
        if not contains(log_content_by_record.get(record.id, "") + " " + str(data.get("log_content") or ""), body.log_content): continue
        if not date_condition(value(data, "source_date", "source_at"), body.source_from, body.source_to): continue
        hearing_dates = [data.get(key) for key in ("hearing_date", "first_court_hearing_date", "second_court_hearing_date", "retrial_court_hearing_date")]
        if (body.hearing_from or body.hearing_to) and not any(date_condition(candidate, body.hearing_from, body.hearing_to) for candidate in hearing_dates): continue
        if not contains(data.get("counsel_type"), body.counsel_type): continue
        if include_status_filter and body.case_statuses:
            allowed_statuses = {str(status or "").strip() for status in body.case_statuses if str(status or "").strip()}
            if str(record.status or "").strip() not in allowed_statuses: continue
        elif include_status_filter and not contains(record.status, body.case_status or body.status): continue
        if not contains("、".join(data.get("handling_lawyers") or []), body.handling_lawyer): continue
        if not contains(data.get("assistant"), body.assistant): continue
        if not contains(document_names.get(record.id, ""), body.document_name): continue
        try:
            record_start = date.fromisoformat(str(data.get("counsel_start") or ""))
            record_end = date.fromisoformat(str(data.get("counsel_end") or ""))
        except ValueError:
            record_start = record_end = None
        if body.counsel_start and (not record_end or record_end < body.counsel_start): continue
        if body.counsel_end and (not record_start or record_start > body.counsel_end): continue
        attachments_for_record = record_attachments.get(record.id, [])
        linked_finance = list(finance_by_case_id.get(record.id, []))
        for finance_record in finance_by_case_no.get(record.serial_no, []):
            if finance_record not in linked_finance:
                linked_finance.append(finance_record)
        finance_data_rows = [item.data or {} for item in linked_finance]

        def finance_text_condition(*keys: str, expected: str, negate: bool = False) -> bool:
            found = any(text_condition(value(row, *keys), expected) for row in finance_data_rows)
            return not found if negate else found

        def finance_date_condition(*keys: str, start_date: date | None, end_date: date | None, negate: bool = False) -> bool:
            found = any(date_condition(value(row, *keys), start_date, end_date) for row in finance_data_rows)
            return not found if negate else found

        def finance_list_condition(*keys: str, expected: list[str], negate: bool = False) -> bool:
            found = any(list_condition(value(row, *keys), expected) for row in finance_data_rows)
            return not found if negate else found

        advanced_conditions: list[bool] = []
        if body.assisted_response_user.strip():
            advanced_conditions.append(text_condition(value(data, "assisted_response_user", "response_user"), body.assisted_response_user, body.assisted_response_user_not))
        if body.assisted_request_date_from or body.assisted_request_date_to:
            advanced_conditions.append(date_condition(value(data, "assisted_request_date", "request_date"), body.assisted_request_date_from, body.assisted_request_date_to, body.assisted_request_date_not))
        if body.assisted_response_date_from or body.assisted_response_date_to:
            advanced_conditions.append(date_condition(value(data, "assisted_response_date", "response_date"), body.assisted_response_date_from, body.assisted_response_date_to, body.assisted_response_date_not))
        if body.finance_inform_date_from or body.finance_inform_date_to:
            advanced_conditions.append(finance_date_condition("inform_date", "fee_inform_date", "finance_inform_date", start_date=body.finance_inform_date_from, end_date=body.finance_inform_date_to, negate=body.finance_inform_date_not))
        if body.finance_gained_date_from or body.finance_gained_date_to:
            advanced_conditions.append(finance_date_condition("gained_date", "fee_gained_date", "finance_gained_date", start_date=body.finance_gained_date_from, end_date=body.finance_gained_date_to, negate=body.finance_gained_date_not))
        if body.finance_response_user.strip():
            advanced_conditions.append(finance_text_condition("response_user", "fee_response_user", "finance_response_user", expected=body.finance_response_user, negate=body.finance_response_user_not))
        if body.finance_bill_no.strip():
            advanced_conditions.append(finance_text_condition("bill_no", "fee_bill_no", "finance_bill_no", expected=body.finance_bill_no, negate=body.finance_bill_no_not))
        if body.finance_bill_statuses:
            advanced_conditions.append(finance_list_condition("bill_status", "fee_bill_status", "finance_bill_status", expected=body.finance_bill_statuses, negate=body.finance_bill_status_not))
        if body.finance_bill_date_from or body.finance_bill_date_to:
            advanced_conditions.append(finance_date_condition("bill_date", "fee_bill_date", "finance_bill_date", start_date=body.finance_bill_date_from, end_date=body.finance_bill_date_to, negate=body.finance_bill_date_not))
        if body.finance_fee_type_ids:
            advanced_conditions.append(finance_list_condition("fee_type_ids", "finance_fee_type_ids", "fee_type_id", expected=body.finance_fee_type_ids, negate=body.finance_fee_type_not))
        if body.file_uploading_user.strip():
            found_uploader = any(text_condition(item.uploader, body.file_uploading_user) for item in attachments_for_record)
            advanced_conditions.append(not found_uploader if body.file_uploading_user_not else found_uploader)
        if body.file_uploading_time_from or body.file_uploading_time_to:
            found_upload_time = any(date_condition(item.created_at, body.file_uploading_time_from, body.file_uploading_time_to) for item in attachments_for_record)
            advanced_conditions.append(not found_upload_time if body.file_uploading_time_not else found_upload_time)
        if body.file_type_ids:
            found_file_type = any(list_condition(item.file_type_code or item.category, body.file_type_ids) for item in attachments_for_record)
            advanced_conditions.append(not found_file_type if body.file_type_not else found_file_type)
        if advanced_conditions:
            advanced_passed = all(advanced_conditions) if advanced_logic == "and" else any(advanced_conditions)
            if not advanced_passed:
                continue
        filtered.append(record)
    if body.sort_order == "case_no_asc":
        filtered.sort(key=lambda item: (item.serial_no, item.id))
    elif body.sort_order == "case_no_desc":
        filtered.sort(key=lambda item: (item.serial_no, item.id), reverse=True)
    elif body.sort_order == "created_asc":
        filtered.sort(key=lambda item: (item.created_at or datetime.min, item.id))
    elif body.sort_order == "created_desc":
        filtered.sort(key=lambda item: (item.created_at or datetime.min, item.id), reverse=True)
    elif body.sort_order == "updated_asc":
        filtered.sort(key=lambda item: (item.updated_at or item.created_at or datetime.min, item.id))
    elif body.sort_order == "status_asc":
        filtered.sort(key=lambda item: (item.status or "", item.serial_no, item.id))
    else:
        filtered.sort(key=lambda item: (item.updated_at or item.created_at, item.id), reverse=True)
    return filtered


async def _next_case_serial(case_type: str, db: AsyncSession) -> str:
    """Generate the compact legacy-style case number: SH + type + YY + 5 digits."""
    parameter_names = {case_type}
    if case_type == "民事案件":
        parameter_names.add("民事争议")
    parameter = await db.scalar(select(SystemParameter).where(
        SystemParameter.category == "case_type",
        SystemParameter.name.in_(parameter_names),
        SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.sort_order, SystemParameter.id))
    default_codes = {"民事案件": "MS", "刑事案件": "XS", "行政案件及国家赔偿": "XZ", "法律顾问": "GW", "仲裁": "ZC"}
    type_code = str((parameter.extra or {}).get("letter_code") if parameter else default_codes.get(case_type, "AJ")).strip().upper()
    prefix = f"SH{type_code}{datetime.now():%y}"
    existing = (await db.scalars(select(BusinessRecord.serial_no).where(
        BusinessRecord.module == "case",
        BusinessRecord.serial_no.like(f"{prefix}%"),
    ).order_by(BusinessRecord.serial_no.desc()))).all()
    sequence = max((int(match.group(1)) for value in existing if (match := re.fullmatch(rf"{re.escape(prefix)}(\d{{5}})", value))), default=0) + 1
    if sequence > 99999:
        raise HTTPException(status_code=409, detail=f"{datetime.now():%Y} 年{case_type}案件编号已用尽")
    return f"{prefix}{sequence:05d}"


def _case_copy_suffix(index: int) -> str:
    """Return the Excel-style suffix for a one-based copy sequence."""
    if index < 1:
        raise ValueError("Copy suffix index must be positive")
    letters: list[str] = []
    while index:
        index, remainder = divmod(index - 1, 26)
        letters.append(chr(ord("A") + remainder))
    return "".join(reversed(letters))


async def _case_copy_root(source: BusinessRecord, db: AsyncSession) -> BusinessRecord:
    """Follow a legacy copy chain so every copy stays under its first case number."""
    current = source
    seen_ids: set[int] = set()
    while current.id not in seen_ids:
        seen_ids.add(current.id)
        data = current.data or {}
        declared_root = str(data.get("copy_root_case_no") or "").strip()
        if declared_root:
            root_id = int(data.get("copy_root_case_record_id") or 0)
            if root_id:
                root = await db.get(BusinessRecord, root_id)
                if root and root.module == "case" and root.serial_no == declared_root:
                    return root
            return current if current.serial_no == declared_root else BusinessRecord(module="case", serial_no=declared_root)
        parent_id = int(data.get("copied_from_case_id") or data.get("original_case_record_id") or 0)
        if not parent_id:
            return current
        parent = await db.get(BusinessRecord, parent_id)
        if not parent or parent.module != "case":
            return current
        current = parent
    return source


async def _next_case_copy_serial(root_serial: str, db: AsyncSession) -> str:
    """Allocate the first available A..Z, AA.. suffix for a copied case."""
    escaped_root = root_serial.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    existing = set((await db.scalars(select(BusinessRecord.serial_no).where(
        BusinessRecord.module == "case",
        BusinessRecord.serial_no.like(f"{escaped_root}%", escape="\\"),
    ))).all())
    index = 1
    while f"{root_serial}{_case_copy_suffix(index)}" in existing:
        index += 1
    return f"{root_serial}{_case_copy_suffix(index)}"


def _clean_case_litigant_values(values: list[str]) -> list[str]:
    result = list(dict.fromkeys(str(value or "").strip() for value in values if str(value or "").strip()))
    if any(len(value) > 256 for value in result):
        raise HTTPException(status_code=422, detail="当事人名称过长")
    return result


async def _persist_case_litigants(
    case_record: BusinessRecord,
    body: CaseLitigantsInput,
    identity: dict,
    db: AsyncSession,
    *,
    advance_creation: bool,
    enforce_create_permission: bool,
    action: str,
):
    from app.core.crm import (
        _persist_case_litigant_customers,
    )
    from app.core.documents import (
        _clean_case_litigant_agents,
    )
    from app.core.legacy_sync import (
        _sync_legacy_projection,
    )
    from app.core.permissions import (
        _permission_payload_for_identity,
    )
    from app.core.system import (
        _record_dict,
    )
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
        raise HTTPException(status_code=409, detail="归档中的案件不能修改当事人")
    plaintiffs = _clean_case_litigant_values(body.plaintiffs)
    plaintiff_agents = _clean_case_litigant_agents(body.plaintiff_agents)
    defendants = _clean_case_litigant_values(body.defendants)
    defendant_agents = _clean_case_litigant_agents(body.defendant_agents)
    third_parties = _clean_case_litigant_values(body.third_parties)
    third_party_agents = _clean_case_litigant_agents(body.third_party_agents)
    case_type = str((case_record.data or {}).get("case_type") or "")
    permission_key = CASE_CREATE_PERMISSION_BY_TYPE.get(case_type)
    if enforce_create_permission and permission_key and identity.get("role") != "admin":
        permission = await _permission_payload_for_identity(identity, db)
        if permission_key not in set(permission.get("menu_keys", [])):
            raise HTTPException(status_code=403, detail="当前角色没有该案件类型的新建权限")
    if case_type in {"行政案件及国家赔偿", "仲裁"} and (not plaintiffs or not defendants):
        raise HTTPException(status_code=422, detail="请录入原告/申请人与被告/被申请人")
    await _persist_case_litigant_customers(
        case_record,
        {"原告": plaintiffs, "被告": defendants, "第三人": third_parties},
        identity,
        db,
    )
    current_data = dict(case_record.data or {})
    next_creation_step = current_data.get("case_creation_step")
    if advance_creation and str(next_creation_step or "") in {"basic", "litigants"}:
        next_creation_step = "litigants"
    updated_data = {
        **current_data,
        "plaintiffs": plaintiffs,
        "plaintiff_agents": plaintiff_agents,
        "defendants": defendants,
        "defendant_agents": defendant_agents,
        "third_parties": third_parties,
        "third_party_agents": third_party_agents,
        "plaintiff": "、".join(plaintiffs),
        "opponent": "、".join(defendants),
    }
    if "case_creation_step" in current_data or advance_creation:
        updated_data["case_creation_step"] = next_creation_step
    case_record.data = updated_data
    db.add(WorkflowEvent(
        record_id=case_record.id,
        action=action,
        from_status=case_record.status,
        to_status=case_record.status,
        operator=identity["username"],
        comment=body.comment,
    ))
    await _sync_legacy_projection(case_record, identity, db)
    await db.commit()
    await db.refresh(case_record)
    return _record_dict(case_record)


async def _criminal_detail_maintenance_case(case_id: int, identity: dict, db: AsyncSession) -> BusinessRecord:
    from app.core.permissions import (
        _ensure_record_module, _require_case_action, _require_case_creation_completed,
    )
    record = await _ensure_record_module(case_id, "case", identity, db); await _require_case_action(identity, db, "case.detail.update")
    if str((record.data or {}).get("case_type") or "") != "刑事案件": raise HTTPException(status_code=409, detail="该接口仅用于刑事案件")
    _require_case_creation_completed(record)
    if record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}: raise HTTPException(status_code=409, detail="归档中的刑事案件不能维护资料")
    return record


async def _case_action_granted(identity: dict, db: AsyncSession, action_code: str) -> bool:
    from app.core.permissions import (
        _identity_role_ids, _permission_payload_for_identity,
    )
    if action_code.startswith("case.") and action_code != "case.assisted_fee.manage":
        return True
    if "admin" in _identity_role_ids(identity):
        return True
    permission = await _permission_payload_for_identity(identity, db)
    action_keys = set(permission.get("action_keys") or [])
    return "*" in action_keys or action_code in action_keys


def _validate_case_execution_status(value: str) -> str:
    normalized = str(value or "").strip()
    normalized = CASE_EXECUTION_STATUS_ALIASES.get(normalized, normalized)
    if not normalized:
        raise HTTPException(status_code=422, detail="执行状态不能为空")
    if normalized not in CASE_EXECUTION_STATUSES:
        raise HTTPException(status_code=422, detail="执行状态无效")
    return normalized


def _case_phase_option(item: SystemParameter) -> dict:
    extra = item.extra or {}
    return {
        "id": item.id,
        "code": item.code,
        "name": item.name,
        "canonical_name": CASE_PHASE_STATUS_BY_CODE.get(item.code, item.name),
        "case_type": extra.get("case_type", ""),
        "parent_code": extra.get("parent_code", ""),
        "sort_order": extra.get("sort_order", item.sort_order or 0),
    }


async def _case_type_parameter_for_value(value: str, db: AsyncSession) -> SystemParameter | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    names = {normalized}
    if normalized == "民事案件":
        names.add("民事争议")
    elif normalized == "民事争议":
        names.add("民事案件")
    return await db.scalar(select(SystemParameter).where(
        SystemParameter.category == "case_type",
        SystemParameter.name.in_(names),
        SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.id))


def _phase_is_builtin_for_case_type(phase: SystemParameter, case_type: SystemParameter | None) -> bool:
    """Keep seeded phase catalogs available alongside administrator relations."""
    if not case_type:
        return False
    configured_type = str((phase.extra or {}).get("case_type") or "").strip()
    if not configured_type:
        return False
    names = {case_type.name}
    if case_type.name == "民事争议":
        names.add("民事案件")
    elif case_type.name == "民事案件":
        names.add("民事争议")
    return configured_type in names


async def _case_phase_is_allowed(case_type_value: str, phase_id: int, db: AsyncSession) -> bool:
    case_type = await _case_type_parameter_for_value(case_type_value, db)
    if not case_type:
        return True
    phase = await db.get(SystemParameter, phase_id)
    if phase and _phase_is_builtin_for_case_type(phase, case_type):
        return True
    configured_count = int(await db.scalar(select(func.count()).select_from(CaseTypeCasePhaseRelation).where(
        CaseTypeCasePhaseRelation.case_type_id == case_type.id,
    )) or 0)
    if not configured_count:
        return True
    return bool(await db.scalar(select(CaseTypeCasePhaseRelation.id).where(
        CaseTypeCasePhaseRelation.case_type_id == case_type.id,
        CaseTypeCasePhaseRelation.case_phase_id == phase_id,
    ).limit(1)))


async def _active_case_phase_values(db: AsyncSession) -> set[str]:
    """Return every active system phase name accepted by the legacy edit form.

    The old form reads its phase options from the maintained parameter table.
    Keep both the parameter display name and the canonical status projection so
    migrated records and newly configured phases can be edited consistently.
    """
    phases = list((await db.scalars(select(SystemParameter).where(
        SystemParameter.category == "case_phase",
        SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.sort_order, SystemParameter.id))).all())
    values: set[str] = set()
    for item in phases:
        if item.name:
            values.add(str(item.name).strip())
        canonical = CASE_PHASE_STATUS_BY_CODE.get(item.code, item.name)
        if canonical:
            values.add(str(canonical).strip())
    return values


async def _resolve_case_phase(body: CasePhaseChangeInput, db: AsyncSession) -> dict:
    phase_id = int(body.case_phase_id or 0)
    phase_name = body.case_phase_name.strip()
    phase = await db.get(SystemParameter, phase_id) if phase_id else None
    if phase_id and (not phase or phase.category != "case_phase" or not phase.is_active):
        raise HTTPException(status_code=422, detail="案件阶段不存在或已停用")
    if phase_name:
        named_phase = await db.scalar(select(SystemParameter).where(
            SystemParameter.category == "case_phase", SystemParameter.name == phase_name,
            SystemParameter.is_active.is_(True),
        ))
        if not named_phase:
            raise HTTPException(status_code=422, detail="案件阶段不存在或已停用")
        if phase and phase.id != named_phase.id:
            raise HTTPException(status_code=422, detail="案件阶段 ID 与名称不匹配")
        phase = named_phase
    if not phase:
        raise HTTPException(status_code=422, detail="阶段名称不能为空")
    canonical_name = CASE_PHASE_STATUS_BY_CODE.get(phase.code, phase.name)
    if canonical_name not in await _active_case_phase_values(db):
        raise HTTPException(status_code=422, detail="案件阶段不是允许的办理阶段")
    return {**_case_phase_option(phase), "canonical_name": canonical_name}


def _case_ai_draft_name(value: str) -> str:
    name = str(value or "").strip()
    if not name or Path(name).name != name or name in {".", ".."}:
        raise HTTPException(status_code=422, detail="AI 草稿文件名不能为空，且不能包含路径")
    suffix = Path(name).suffix.lower()
    if suffix not in AI_SPACE_EDITABLE_SUFFIXES:
        raise HTTPException(status_code=422, detail="AI 空间文档支持 .docx、.md 和 .txt 格式")
    return name


def _case_ai_draft_bytes(name: str, content: str) -> tuple[bytes, str]:
    from app.core.storage import (
        _docx_bytes,
    )
    suffix = Path(name).suffix.lower()
    if suffix == ".docx":
        return _docx_bytes(Path(name).stem, content), WORD_DOCUMENT_CONTENT_TYPE
    return content.encode("utf-8"), "text/markdown" if suffix == ".md" else "text/plain"


async def _case_ai_draft(
    case_record: BusinessRecord, attachment_id: int, db: AsyncSession,
) -> FileAttachment:
    item = await db.get(FileAttachment, attachment_id)
    if not item or item.record_id != case_record.id or item.category != AI_SPACE_CATEGORY:
        raise HTTPException(status_code=404, detail="AI 空间草稿不存在")
    return item
