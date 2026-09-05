"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.constants import (
    AI_SPACE_CATEGORY, CASE_DEFENDANT_FIELDS, CASE_DOCUMENT_FOLDER_HEADERS, CASE_EVENT_TIME_ZONE, CASE_PLAINTIFF_FIELDS,
    CONTRACT_PERSON_NAME_PLACEHOLDER, PERSON_NAME_PLACEHOLDER, RECORD_PERSON_FIELDS_BY_MODULE, RECORD_PERSON_LIST_FIELDS_BY_MODULE, UPLOAD_ROOT,
    WORD_DOCUMENT_CONTENT_TYPE,
)
from app.core.dependencies import (
    AgentDocument, AsyncSession, BusinessRecord, Cm, Document,
    FileAttachment, HTTPException, Path, Pt, SystemParameter,
    User, Warehouse, WarehouseStorageLocation, WorkflowEvent, date,
    datetime, func, or_, qn, re,
    select, settings, timezone, unicodedata, uuid4,
)


def _is_complete_person_display_name(display_name: object, username: object = "") -> bool:
    value = str(display_name or "").strip()
    return bool(value)


def _person_display_name(display_name: object, username: object = "") -> tuple[str, bool]:
    value = str(display_name or "").strip()
    if _is_complete_person_display_name(value, username):
        return value, False
    return PERSON_NAME_PLACEHOLDER, True


async def _user_display_map(usernames: set[str], db: AsyncSession) -> dict[str, User]:
    normalized = {str(username or "").strip().lower() for username in usernames if str(username or "").strip()}
    if not normalized:
        return {}
    users = (await db.scalars(select(User).where(func.lower(User.username).in_(normalized)))).all()
    return {user.username.lower(): user for user in users}


def _person_reference_display(username: object, users_by_username: dict[str, User]) -> tuple[str, bool]:
    key = str(username or "").strip()
    if not key:
        return "—", False
    if key == "system":
        return "系统", False
    user = users_by_username.get(key.lower())
    if not user:
        return PERSON_NAME_PLACEHOLDER, True
    return _person_display_name(user.display_name, key)


def _investigation_task_date(value: object) -> date | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _contract_person_display_name(value: object, names_by_username: dict[str, str] | None = None) -> str:
    from app.core.contracts import (
        _valid_contract_chinese_person_name, _valid_contract_person_name,
    )
    raw = unicodedata.normalize("NFKC", str(value or "")).strip()
    direct = _valid_contract_chinese_person_name(raw)
    if direct:
        return direct
    mapped = _valid_contract_person_name((names_by_username or {}).get(raw.lower(), ""), raw)
    return mapped or CONTRACT_PERSON_NAME_PLACEHOLDER


def _normalized_customer_name(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).strip().casefold().split())


def _case_assistant_display(data: dict, users_by_username: dict[str, User]) -> tuple[str, bool]:
    from app.core.contracts import (
        _contract_person_values,
    )
    legacy = data.get("legacy_record") if isinstance(data.get("legacy_record"), dict) else {}
    usernames = _contract_person_values(
        data.get("assistant_usernames") or data.get("assistant_username") or legacy.get("CaseAssistant")
    )
    stored_names = _contract_person_values(
        data.get("assistants") or data.get("assistant") or legacy.get("CaseAssistantName")
    )
    if not usernames and not stored_names:
        return "—", False
    username = usernames[0] if usernames else ""
    stored_name = stored_names[0] if stored_names else ""
    label = ""
    unresolved = False
    if username:
        label, unresolved = _person_reference_display(username, users_by_username)
    elif stored_name:
        label, unresolved = _person_reference_display(stored_name, users_by_username)
    if (not label or unresolved) and stored_name and stored_name != PERSON_NAME_PLACEHOLDER:
        label = stored_name
        unresolved = False
    if not label or label == PERSON_NAME_PLACEHOLDER:
        return CONTRACT_PERSON_NAME_PLACEHOLDER, True
    return label, unresolved


def _apply_record_person_displays(
    result: dict,
    record: BusinessRecord,
    users_by_username: dict[str, User],
) -> dict:
    from app.core.contracts import (
        _contract_person_values,
    )
    if record.module not in RECORD_PERSON_FIELDS_BY_MODULE:
        return result
    result["owner_display_name"], result["owner_display_name_missing"] = _person_reference_display(record.owner, users_by_username)
    data = result.get("data") or {}
    for key in RECORD_PERSON_FIELDS_BY_MODULE[record.module]:
        if key not in data:
            continue
        reference = data.get(key)
        if record.module == "case" and key == "hearing_lawyer":
            reference = data.get("hearing_lawyer_username") or reference
        if record.module == "case" and key in {"assistant", "assistant_username"}:
            display_name, missing = _case_assistant_display(data, users_by_username)
        else:
            display_name, missing = _person_reference_display(reference, users_by_username)
        data[f"{key}_display_name"] = display_name
        data[f"{key}_display_name_missing"] = missing
    for key in RECORD_PERSON_LIST_FIELDS_BY_MODULE.get(record.module, ()):
        if key not in data:
            continue
        values = _contract_person_values(data.get(key))
        labels = [_person_reference_display(value, users_by_username)[0] for value in values]
        data[f"{key}_display_names"] = labels
        data[f"{key}_display_name"] = "、".join(labels)
    if record.module == "case" and isinstance(data.get("legacy_participants"), list):
        displayed_participants: list[dict] = []
        participant_names: list[str] = []
        participant_usernames: list[str] = []
        seen_usernames: set[str] = set()
        for raw_participant in data["legacy_participants"]:
            if not isinstance(raw_participant, dict):
                continue
            username = str(raw_participant.get("staff_name") or "").strip()
            if not username or username.lower() in seen_usernames:
                continue
            seen_usernames.add(username.lower())
            display_name, missing = _person_reference_display(username, users_by_username)
            displayed_participants.append({
                **raw_participant,
                "display_name": display_name,
                "display_name_missing": missing,
            })
            participant_usernames.append(username)
            participant_names.append(display_name)
        data["legacy_participants"] = displayed_participants
        data["legacy_participant_usernames"] = participant_usernames
        data["legacy_participant_display_names"] = participant_names
        data["legacy_participant_display_name"] = "、".join(participant_names)
    result["data"] = data
    return result


def _case_hearing_datetime(value: object, fallback_time: object = "") -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.combine(date.fromisoformat(text[:10]), datetime.min.time())
        except ValueError:
            return None
    if parsed.time() == datetime.min.time():
        time_text = str(fallback_time or "").strip()
        if time_text:
            try:
                parsed = datetime.combine(parsed.date(), datetime.strptime(time_text[:8], "%H:%M:%S").time())
            except ValueError:
                try:
                    parsed = datetime.combine(parsed.date(), datetime.strptime(time_text[:5], "%H:%M").time())
                except ValueError:
                    pass
    return parsed


def _task_display_with_users(record: BusinessRecord, users_by_username: dict[str, User]) -> dict:
    from app.core.contracts import (
        _contract_person_values,
    )
    from app.core.tasks import (
        _task_dict,
    )
    result = _task_dict(record)
    data = result.get("data") or {}
    result["owner_display_name"], result["owner_display_name_missing"] = _person_reference_display(record.owner, users_by_username)
    for key in ("initiator", "source_owner", "assigner", "reviewer", "customer_reviewer"):
        if key in data:
            display_name, display_missing = _person_reference_display(data.get(key), users_by_username)
            result[f"{key}_display_name"] = display_name
            result[f"{key}_display_name_missing"] = display_missing
    if data.get("customer_manager") is not None:
        manager_values = _contract_person_values(data.get("customer_manager"))
        manager_names = [_person_reference_display(value, users_by_username)[0] for value in manager_values]
        if manager_names:
            result["customer_manager_display_name"] = "、".join(manager_names)
    collaborator_values = _contract_person_values(data.get("collaborators"))
    result["collaborator_display_names"] = [
        _person_reference_display(value, users_by_username)[0] for value in collaborator_values
    ]
    result["collaborators_display_names"] = result["collaborator_display_names"]
    return result


async def _task_display_dicts(records: list[BusinessRecord], db: AsyncSession) -> list[dict]:
    from app.core.cases import (
        _case_party_values,
    )
    from app.core.contracts import (
        _contract_person_values,
    )
    usernames: set[str] = set()
    case_ids: set[int] = set()
    case_nos: set[str] = set()
    for record in records:
        usernames.add(record.owner)
        data = record.data or {}
        raw_ids = data.get("case_ids") if isinstance(data.get("case_ids"), list) else []
        raw_ids = [data.get("case_record_id") or data.get("case_id"), *raw_ids]
        for raw_case_id in raw_ids:
            try:
                if raw_case_id:
                    case_ids.add(int(raw_case_id))
            except (TypeError, ValueError):
                pass
        raw_nos = data.get("case_nos") if isinstance(data.get("case_nos"), list) else []
        for raw_case_no in [data.get("case_no"), *raw_nos]:
            case_no = str(raw_case_no or "").strip()
            if case_no:
                case_nos.add(case_no)
        for key in ("initiator", "source_owner", "assigner", "reviewer", "customer_reviewer", "customer_manager", "collaborators"):
            usernames.update(_contract_person_values(data.get(key)))
    users_by_username = await _user_display_map(usernames, db)
    employees = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "hr",
        BusinessRecord.status.not_in({"离职", "停用"}),
    ))).all())
    employee_names = {
        str((employee.data or {}).get("username") or employee.owner or "").strip().lower(): str(employee.title or "").strip()
        for employee in employees
        if str((employee.data or {}).get("username") or employee.owner or "").strip()
    }
    case_conditions = []
    if case_ids:
        case_conditions.append(BusinessRecord.id.in_(case_ids))
    if case_nos:
        case_conditions.append(BusinessRecord.serial_no.in_(case_nos))
    linked_cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module.in_({"case", "ipr_case"}), or_(*case_conditions),
    ))).all()) if case_conditions else []
    cases_by_id = {item.id: item for item in linked_cases}
    cases_by_no = {item.serial_no: item for item in linked_cases}

    results: list[dict] = []
    for record in records:
        result = _task_display_with_users(record, users_by_username)
        employee_name = employee_names.get(str(record.owner or "").strip().lower())
        if employee_name:
            result["owner_display_name"] = employee_name
            result["owner_display_name_missing"] = False
        data = record.data or {}
        linked_case_rows: list[BusinessRecord] = []
        raw_ids = data.get("case_ids") if isinstance(data.get("case_ids"), list) else []
        raw_ids = [data.get("case_record_id") or data.get("case_id"), *raw_ids]
        for raw_case_id in raw_ids:
            try:
                linked_case = cases_by_id.get(int(raw_case_id)) if raw_case_id else None
            except (TypeError, ValueError):
                linked_case = None
            if linked_case and linked_case not in linked_case_rows:
                linked_case_rows.append(linked_case)
        raw_nos = data.get("case_nos") if isinstance(data.get("case_nos"), list) else []
        for raw_case_no in [data.get("case_no"), *raw_nos]:
            linked_case = cases_by_no.get(str(raw_case_no or "").strip())
            if linked_case and linked_case not in linked_case_rows:
                linked_case_rows.append(linked_case)
        linked_case = linked_case_rows[0] if linked_case_rows else None
        if linked_case:
            case_data = linked_case.data or {}
            result["case_no"] = linked_case.serial_no
            result["plaintiff"] = "、".join(_case_party_values(case_data, CASE_PLAINTIFF_FIELDS)) or result["plaintiff"] or linked_case.customer
            result["defendant"] = "、".join(_case_party_values(case_data, CASE_DEFENDANT_FIELDS)) or result["defendant"]
            result["case_stage"] = str(case_data.get("case_stage") or linked_case.status or result["case_stage"])
        result["cases"] = [
            {"id": item.id, "case_no": item.serial_no, "title": item.title, "customer": item.customer, "status": item.status}
            for item in linked_case_rows
        ]
        result["case_ids"] = [item.id for item in linked_case_rows]
        result["case_nos"] = [item.serial_no for item in linked_case_rows]
        result["case_module"] = linked_case.module if linked_case else str(data.get("case_module") or "")
        results.append(result)
    return results


async def _task_display_dict(record: BusinessRecord, db: AsyncSession) -> dict:
    return (await _task_display_dicts([record], db))[0]


def _record_links_to_case(record: BusinessRecord, case_record: BusinessRecord) -> bool:
    """Prefer the persisted case id; use the case number only for legacy rows."""
    record_data = record.data or {}
    linked_case_id = int(record_data.get("case_id") or record_data.get("case_record_id") or 0)
    if linked_case_id:
        return linked_case_id == case_record.id
    return str(record_data.get("case_no") or "") == case_record.serial_no


def _dingtalk_allowed_display_names() -> set[str]:
    raw = str(settings.dingtalk_allowed_display_names or "")
    for separator in ("，", ";", "；", "\n"):
        raw = raw.replace(separator, ",")
    return {name.strip() for name in raw.split(",") if name.strip()}


async def _normalized_fee_type_extra(code: str, extra: dict, db: AsyncSession) -> dict:
    parent_code = str((extra or {}).get("parent_code") or "").strip()
    normalized = {"parent_code": parent_code}
    if not parent_code:
        return normalized
    parent = await db.scalar(select(SystemParameter).where(
        SystemParameter.category == "fee_type",
        SystemParameter.code == parent_code,
        SystemParameter.is_active.is_(True),
    ))
    if not parent or parent.code == code:
        raise HTTPException(status_code=422, detail="上级费用类型不存在或不可用")
    return normalized


def _case_phase_changed_date(item: BusinessRecord) -> date:
    data = item.data or {}
    legacy = data.get("legacy_record") if isinstance(data.get("legacy_record"), dict) else {}
    for raw in (
        data.get("phase_changed_at"),
        legacy.get("PhaseChangedTime"),
        legacy.get("ChangeTime"),
        data.get("case_register_date"),
        item.created_at,
    ):
        if isinstance(raw, datetime):
            return raw.date()
        if isinstance(raw, date):
            return raw
        text = str(raw or "").strip()
        if not text:
            continue
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return date.fromisoformat(text[:10])
            except ValueError:
                continue
    return date.today()


def _dashboard_case_date(record: BusinessRecord) -> datetime:
    def as_utc_naive(value: datetime) -> datetime:
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    data = record.data or {}
    legacy = data.get("legacy_record") if isinstance(data.get("legacy_record"), dict) else {}
    raw = data.get("case_register_date") or legacy.get("CaseRegisterDate")
    if isinstance(raw, datetime):
        return as_utc_naive(raw)
    if isinstance(raw, date):
        return datetime.combine(raw, time.min)
    text = str(raw or "").strip()
    if text:
        try:
            return as_utc_naive(datetime.fromisoformat(text.replace("Z", "+00:00")))
        except ValueError:
            pass
    return as_utc_naive(record.created_at) if record.created_at else datetime.min


def _dashboard_text(value: object) -> str:
    from app.core.contracts import (
        _contract_person_values,
    )
    values = _contract_person_values(value)
    return "、".join(dict.fromkeys(values))


def _parse_customer_contact_at(value: object) -> datetime | None:
    raw_value = str(value or "").strip()
    if not raw_value:
        return None
    try:
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError:
        return None
    # Normalize explicit offsets and Z to one UTC-naive timeline.  Historical
    # naive values keep their wall-clock meaning for backward compatibility.
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _staff_roi_date_matches(value: date, start_date: date | None, end_date: date | None) -> bool:
    return (not start_date or value >= start_date) and (not end_date or value <= end_date)


def _csv_date(value: str, label: str, *, required: bool = True) -> str:
    if not value and not required: return ""
    try: return str(date.fromisoformat(value))
    except ValueError as exc: raise ValueError(f"{label}必须为 YYYY-MM-DD") from exc


def _normalize_customer_yes_no(value: object, field_name: str) -> str:
    if isinstance(value, bool):
        return "是" if value else "否"
    normalized = str(value or "").strip().casefold()
    if normalized in {"是", "yes", "true", "1"}: return "是"
    if normalized in {"否", "no", "false", "0", ""}: return "否"
    raise HTTPException(status_code=422, detail=f"{field_name}只能填写是或否")


def _normalize_customer_name(value: object) -> str:
    return unicodedata.normalize("NFKC", str(value or "").strip()).casefold()


def _record_belongs_to_customer(record: BusinessRecord, customer: BusinessRecord | None, customer_title: str) -> bool:
    """Match legacy-linked records through the customer master, not only a copied name."""
    data = record.data or {}
    if customer is not None:
        customer_id = int(customer.id)
        customer_no = str(customer.serial_no or "").strip()
        linked_id = int(data.get("customer_id") or data.get("customer_record_id") or 0)
        linked_no = str(data.get("customer_no") or "").strip()
        if linked_id and linked_id == customer_id:
            return True
        if customer_no and linked_no and linked_no == customer_no:
            return True
    return _normalize_customer_name(record.customer) == _normalize_customer_name(customer_title)


def _normalize_conflict_entity(value: object) -> str:
    """Normalize typography without weakening whole-entity equality."""
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).split()).casefold()


def _case_filing_date(record: BusinessRecord) -> date | None:
    raw_value = str((record.data or {}).get("filing_date") or "").strip()
    if not raw_value:
        return None
    try:
        return date.fromisoformat(raw_value[:10])
    except ValueError:
        return None


def _normalize_external_contract_numbers(data: dict) -> dict:
    raw_values = data.get("external_contract_numbers")
    if raw_values is None:
        raw_values = [data.get("external_contract_no", "")]
    if not isinstance(raw_values, list):
        raise HTTPException(status_code=422, detail="外部合同号必须为数组")
    values = list(dict.fromkeys(str(value or "").strip() for value in raw_values if str(value or "").strip()))
    if len(values) > 50:
        raise HTTPException(status_code=422, detail="一个合同最多关联 50 个外部合同号")
    if any(len(value) > 128 for value in values):
        raise HTTPException(status_code=422, detail="外部合同号长度不能超过 128 个字符")
    return {**data, "external_contract_numbers": values, "external_contract_no": values[0] if values else ""}


async def _convert_notary_to_case(
    notary: BusinessRecord,
    clue: BusinessRecord,
    db: AsyncSession,
    *,
    operator: str,
    comment: str,
    case_type: str = "民事案件",
    court: str = "",
    automatic: bool = False,
) -> BusinessRecord:
    """将公证审核记录转为新案；人工审核和 30 日超期规则共用同一闭环。"""
    clue_data = clue.data or {}
    case_record = await db.get(BusinessRecord, int(clue_data.get("converted_case_id") or 0))
    if not case_record or case_record.module != "case":
        raise HTTPException(status_code=409, detail="请先从已取证线索批量生成“等待公证书”案件")
    if case_record.status not in {"等待公证书", "等待审核公证书"}:
        raise HTTPException(status_code=409, detail=f"案件 {case_record.serial_no} 当前阶段不允许公证审核")
    case_serial = case_record.serial_no
    previous_case_status = case_record.status
    case_record.status = "新案待分配"
    case_record.data = {**(case_record.data or {}), "notary_id": notary.id, "notary_no": notary.serial_no, "case_type": case_type or (case_record.data or {}).get("case_type", "民事案件"), "court": court or (case_record.data or {}).get("court", ""), "notary_review_automatic": automatic, "case_creation_step": "completed", "case_creation_approval_status": "自动通过", "case_creation_approved_by": "system"}
    action = "公证审核超期自动转案" if automatic else "公证审核通过"
    notary.status = "审核通过"
    notary.data = {
        **(notary.data or {}), "case_id": case_record.id, "case_no": case_serial,
        "auto_reviewed": automatic,
        **({"auto_reviewed_at": str(date.today())} if automatic else {}),
    }
    clue.status = "已转案件"
    clue.data = {
        **clue_data, "notary": "超期自动通过" if automatic else "审核通过",
        "converted_case_id": case_record.id, "converted_case_no": case_serial,
    }
    db.add_all([
        WorkflowEvent(record_id=notary.id, action=action, from_status="待审核", to_status="审核通过", operator=operator, comment=comment),
        WorkflowEvent(record_id=clue.id, action="自动转案件", from_status="待公证", to_status="已转案件", operator=operator, comment=f"生成案件 {case_serial}"),
        WorkflowEvent(record_id=case_record.id, action="公证审核完成", from_status=previous_case_status, to_status="新案待分配", operator=operator, comment=f"来源线索 {clue.serial_no} / 公证 {notary.serial_no}"),
    ])
    return case_record


def _case_fee_display_type(item: BusinessRecord) -> str:
    data = item.data or {}
    explicit = str(data.get("fee_type_name") or data.get("case_fee_type_name") or "").strip()
    if explicit:
        return explicit
    fee_type = str(data.get("fee_type") or "").strip()
    if fee_type == "代理费":
        return "律师代理费"
    if fee_type == "官方费用":
        return "官费"
    return fee_type or item.title


def _case_fee_date(value: object) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _case_event_display_time(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(CASE_EVENT_TIME_ZONE)


def _parse_ipr_batch_date(raw_value: object, field_label: str) -> tuple[date | None, str]:
    value = str(raw_value or "").strip()
    if not value:
        return None, f"{field_label}不能为空"
    try:
        return date.fromisoformat(value[:10]), ""
    except ValueError:
        return None, f"{field_label}格式必须为 YYYY-MM-DD"


def _normalize_case_numbers(values: str | list[str]) -> list[str]:
    raw_values = values.split(",") if isinstance(values, str) else values
    return list(dict.fromkeys(str(value or "").strip() for value in raw_values if str(value or "").strip()))


def _case_agent_date(value: object, field_name: str) -> date:
    try:
        return date.fromisoformat(str(value or "").strip())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{field_name}必须使用 YYYY-MM-DD 日期格式") from exc


def _case_agent_required_text(value: object, field_name: str, max_length: int = 1000) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise HTTPException(status_code=422, detail=f"{field_name}不能为空")
    if len(normalized) > max_length:
        raise HTTPException(status_code=422, detail=f"{field_name}内容过长")
    return normalized


def _normalize_case_document_folder_name(value: str) -> str:
    name = str(value or "").strip()
    if not name or len(name) > 64 or any(character in name for character in "/\\") or any(ord(character) < 32 for character in name):
        raise HTTPException(status_code=422, detail="目录名称不能为空、不能超过 64 个字符，且不能包含路径字符")
    if name in CASE_DOCUMENT_FOLDER_HEADERS:
        raise HTTPException(status_code=409, detail="该名称是系统目录，不能作为自定义目录")
    return name


def _case_ai_draft_text(item: FileAttachment, path: Path) -> str:
    if Path(item.original_name).suffix.lower() != ".docx":
        return path.read_text(encoding="utf-8")
    document = Document(path)
    lines = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        lines.extend("\t".join(cell.text for cell in row.cells) for row in table.rows)
    return "\n".join(lines).strip()


def _warehouse_location_display(warehouse: Warehouse, location: WarehouseStorageLocation) -> str:
    return f"{warehouse.name} / {location.name}"


def _format_case_document(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.8)
    section.right_margin = Cm(2.8)
    normal = document.styles["Normal"]
    normal.font.name = "SimSun"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    normal.font.size = Pt(12)
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(6)


def _parse_ipr_official_candidate_date(value: str, field: str, errors: list[str]) -> date | None:
    value = value.strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{field}必须使用 YYYY-MM-DD 格式")
        return None


async def _sync_agent_document_to_case_ai_space(
    item: AgentDocument, record: BusinessRecord | None, db: AsyncSession,
) -> FileAttachment | None:
    """Keep every case-bound AI document in the case AI draft workspace."""
    from app.core.storage import (
        _docx_bytes,
    )
    if not record or record.module != "case":
        return None
    marker = f"智能文档草稿:{item.job_no}"
    attachment = await db.scalar(select(FileAttachment).where(
        FileAttachment.record_id == record.id,
        FileAttachment.category == AI_SPACE_CATEGORY,
        FileAttachment.remark == marker,
    ))
    safe_title = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "_", item.title.strip()).strip(" .") or item.job_no
    name = f"{safe_title}.docx"
    content = _docx_bytes(item.title, item.content)
    if attachment:
        path = Path(attachment.path)
        if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
            temporary = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
            temporary.write_bytes(content)
            temporary.replace(path)
        else:
            attachment.stored_name = f"{uuid4().hex}.docx"
            attachment.path = str(UPLOAD_ROOT / attachment.stored_name)
            Path(attachment.path).write_bytes(content)
        attachment.original_name = name
        attachment.content_type = WORD_DOCUMENT_CONTENT_TYPE
        attachment.size = len(content)
        return attachment
    stored_name = f"{uuid4().hex}.docx"
    target = UPLOAD_ROOT / stored_name
    target.write_bytes(content)
    attachment = FileAttachment(
        record_id=record.id,
        category=AI_SPACE_CATEGORY,
        original_name=name,
        stored_name=stored_name,
        content_type=WORD_DOCUMENT_CONTENT_TYPE,
        size=len(content),
        path=str(target),
        uploader=item.creator,
        remark=marker,
    )
    db.add(attachment)
    db.add(WorkflowEvent(
        record_id=record.id, action="智能文档写入 AI 空间", from_status=record.status,
        to_status=record.status, operator=item.creator, comment=f"{item.job_no}｜{name}",
    ))
    return attachment
