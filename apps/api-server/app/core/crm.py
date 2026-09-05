"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.constants import (
    CASE_DEFENDANT_FIELDS, CASE_PLAINTIFF_FIELDS, CASE_THIRD_PARTY_FIELDS, UPLOAD_ROOT,
)
from app.core.dependencies import (
    AsyncSession, BusinessRecord, FileAttachment, FinanceTransaction, HTTPException,
    LawFirm, LawFirmAudit, LawFirmContact, NAMESPACE_URL, Path,
    SystemParameter, User, WorkflowEvent, date, datetime,
    or_, select, uuid4, uuid5, verify_password,
)
from app.models_shared import (
    CustomerPortalLoginInput, LawFirmInput,
)


def _customer_guid(record: BusinessRecord) -> str:
    """Return a stable customer GUID, including for legacy rows without one."""
    stored = str((record.data or {}).get("customer_guid") or "").strip()
    return stored or str(uuid5(NAMESPACE_URL, f"customer:{record.id}"))


def _customer_contact_dict(contact: dict) -> dict:
    """Project legacy contacts with explicit independent boolean state fields."""
    projected = dict(contact or {})
    projected.setdefault("is_received_email", True)
    projected.setdefault("is_contacted", True)
    projected.setdefault("is_people_base", True)
    return projected


def _customer_reference_from_maps(
    customer_name: object,
    data: dict,
    customers_by_id: dict[int, BusinessRecord],
    customers_by_no: dict[str, list[BusinessRecord]],
    customers_by_name: dict[str, list[BusinessRecord]],
) -> tuple[BusinessRecord | None, str]:
    """Resolve ID, then customer number, then an unambiguous legacy name."""
    from app.core.formatters import (
        _normalized_customer_name,
    )
    from app.core.system import (
        _positive_record_id,
    )
    name = _normalized_customer_name(customer_name)
    customer_id = _positive_record_id(data.get("customer_id") or data.get("customer_record_id"))
    customer_no = str(data.get("customer_no") or "").strip()
    if customer_id:
        customer = customers_by_id.get(customer_id)
        if not customer:
            return None, "missing_id"
        if customer_no and customer.serial_no != customer_no:
            return None, "mismatched_reference"
        if name and _normalized_customer_name(customer.title) != name:
            return None, "mismatched_reference"
        return customer, "customer_id"
    if customer_no:
        candidates = customers_by_no.get(customer_no, [])
        if len(candidates) != 1:
            return None, "missing_number" if not candidates else "ambiguous_number"
        customer = candidates[0]
        if name and _normalized_customer_name(customer.title) != name:
            return None, "mismatched_reference"
        return customer, "customer_no"
    candidates = customers_by_name.get(name, []) if name else []
    if len(candidates) == 1:
        return candidates[0], "unique_name"
    return None, "missing_name" if not candidates else "ambiguous_name"


def _customer_has_vip_marker(customer: BusinessRecord | None) -> bool:
    from app.core.system import (
        _explicit_vip_value,
    )
    if not customer or customer.module != "customer":
        return False
    data = customer.data or {}
    if any(_explicit_vip_value(data.get(key)) for key in ("is_vip", "vip", "vip_customer")):
        return True
    return any(str(data.get(key) or "").strip().upper() == "VIP" for key in ("vip_level", "customer_level", "level"))


async def _case_customer_has_vip_marker(case_record: BusinessRecord, db: AsyncSession) -> bool:
    """Resolve a customer through record IDs before a unique legacy-name fallback."""
    case_data = case_record.data or {}
    candidate_ids: list[int] = []
    for key in ("customer_record_id", "customer_id"):
        try:
            value = int(case_data.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        if value > 0 and value not in candidate_ids:
            candidate_ids.append(value)
    try:
        contract_id = int(case_data.get("contract_record_id") or case_data.get("contract_id") or 0)
    except (TypeError, ValueError):
        contract_id = 0
    if contract_id > 0:
        contract = await db.get(BusinessRecord, contract_id)
        if contract and contract.module == "contract":
            for key in ("customer_record_id", "customer_id"):
                try:
                    value = int((contract.data or {}).get(key) or 0)
                except (TypeError, ValueError):
                    value = 0
                if value > 0 and value not in candidate_ids:
                    candidate_ids.append(value)
    for customer_id in candidate_ids:
        customer = await db.get(BusinessRecord, customer_id)
        if customer and customer.module == "customer":
            return _customer_has_vip_marker(customer)
    if candidate_ids:
        return False
    if str(case_record.customer or "").strip():
        matches = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "customer", BusinessRecord.title == case_record.customer,
        ))).all())
        if len(matches) == 1:
            return _customer_has_vip_marker(matches[0])
    return False


async def _active_customer_usernames(db: AsyncSession) -> set[str]:
    """Return active customer-service login identities from HR customer accounts."""
    from app.core.system import (
        _is_smoke_test_username,
    )
    employees = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "hr",
        BusinessRecord.status.not_in({"离职", "停用"}),
    ))).all()
    return {
        username
        for item in employees
        for username in [str((item.data or {}).get("username") or item.owner or "").strip().lower()]
        if username
        and str((item.data or {}).get("account_type") or "").strip() == "客户账号"
        and not _is_smoke_test_username(username)
    }


async def _resolve_active_customer_managers(values: list[object], db: AsyncSession) -> list[str]:
    """Resolve customer managers to stable usernames, accepting unique display names and keywords for legacy UI clients."""
    from app.core.system import (
        _is_smoke_test_username,
    )
    tokens = list(dict.fromkeys(str(value or "").strip() for value in values if str(value or "").strip()))
    if not tokens:
        raise HTTPException(status_code=422, detail="至少保留一名客户管理人")
    users = list((await db.scalars(select(User).where(User.is_active.is_(True), or_(User.username.in_(tokens), User.display_name.in_(tokens))))).all())
    by_username = {user.username: user.username for user in users}
    by_display: dict[str, list[str]] = {}
    for user in users:
        by_display.setdefault(user.display_name, []).append(user.username)
    resolved: list[str] = []
    invalid: list[str] = []
    for token in tokens:
        username = by_username.get(token)
        if not username:
            matches = by_display.get(token, [])
            if len(matches) == 1:
                username = matches[0]
        if not username:
            invalid.append(token)
        elif username not in resolved:
            resolved.append(username)
    if invalid:
        unresolved: list[str] = []
        for token in invalid:
            like = f"%{token}%"
            matches = list((await db.scalars(select(User).where(
                User.is_active.is_(True),
                or_(User.username.ilike(like), User.display_name.ilike(like)),
            ))).all())
            match_usernames = sorted({user.username for user in matches})
            if len(match_usernames) == 1:
                username = match_usernames[0]
                if username not in resolved:
                    resolved.append(username)
            else:
                unresolved.append(token)
        if unresolved:
            raise HTTPException(status_code=422, detail=f"客户管理人不存在、已停用或姓名不唯一：{'、'.join(unresolved)}")
    smoke_accounts = [username for username in resolved if _is_smoke_test_username(username)]
    if smoke_accounts:
        raise HTTPException(status_code=422, detail=f"测试账号不能作为客户管理人：{'、'.join(smoke_accounts)}")
    return resolved


def _prioritize_new_customer_managers(existing: list[object], requested: list[str]) -> list[str]:
    """Preserve the caller's newest-first priority block ahead of retained managers."""
    existing_names = list(dict.fromkeys(str(value or "").strip() for value in existing if str(value or "").strip()))
    requested_names = list(dict.fromkeys(requested))
    added = [manager for manager in requested_names if manager not in existing_names]
    retained = [manager for manager in existing_names if manager in requested_names]
    return [*added, *retained]


def _law_firm_contact_dict(item: LawFirmContact, *, is_default: bool = False) -> dict:
    return {
        "id": item.id, "law_firm_id": item.law_firm_id, "name": item.name,
        "address": item.address, "postal_code": item.postal_code, "phone": item.phone,
        "fax": item.fax, "email": item.email, "is_active": item.is_active,
        "is_default": is_default, "created_by": item.created_by, "updated_by": item.updated_by,
        "created_at": item.created_at, "updated_at": item.updated_at,
    }


def _law_firm_dict(item: LawFirm, license_attachment: FileAttachment | None = None, contacts: list[LawFirmContact] | None = None) -> dict:
    from app.core.storage import (
        _attachment_dict,
    )
    result = {
        "id": item.id, "code": item.code, "name": item.name,
        "registered_address": item.registered_address, "business_address": item.business_address,
        "detail_address": item.detail_address, "postal_code": item.postal_code, "phone": item.phone,
        "fax": item.fax, "email": item.email, "organization_code": item.organization_code,
        "company_code": item.company_code, "firm_type": item.firm_type, "firm_level": item.firm_level,
        "country": item.country, "is_active": item.is_active,
        "default_contact_id": item.default_contact_id, "license_attachment_id": item.license_attachment_id,
        "license": _attachment_dict(license_attachment) if license_attachment else None,
        "created_by": item.created_by, "updated_by": item.updated_by,
        "created_at": item.created_at, "updated_at": item.updated_at,
    }
    if contacts is not None:
        contact_dicts = [_law_firm_contact_dict(contact, is_default=contact.id == item.default_contact_id) for contact in contacts]
        result["contacts"] = contact_dicts
        result["default_contact"] = next((contact for contact in contact_dicts if contact["is_default"]), None)
    return result


def _law_firm_audit_dict(item: LawFirmAudit) -> dict:
    return {"id": item.id, "law_firm_id": item.law_firm_id, "action": item.action, "operator": item.operator, "detail": item.detail, "created_at": item.created_at}


async def _law_firm_or_404(law_firm_id: int, db: AsyncSession) -> LawFirm:
    item = await db.get(LawFirm, law_firm_id)
    if not item: raise HTTPException(status_code=404, detail="律所不存在")
    return item


async def _law_firm_license(item: LawFirm, db: AsyncSession) -> FileAttachment | None:
    return await db.get(FileAttachment, item.license_attachment_id) if item.license_attachment_id else None


async def _create_law_firm_record(body: LawFirmInput, identity: dict, db: AsyncSession, *, license_bytes: bytes | None = None, license_filename: str | None = None) -> dict:
    from app.core.permissions import (
        _require_admin,
    )
    _require_admin(identity)
    code, name = body.code.strip().upper(), body.name.strip()
    if await db.scalar(select(LawFirm.id).where(or_(LawFirm.code == code, LawFirm.name == name))):
        raise HTTPException(status_code=409, detail="律所编号或名称已存在")
    default_contact_payload = body.default_contact
    item = LawFirm(code=code, name=name, **body.model_dump(exclude={"code", "name", "default_contact"}), created_by=identity["username"], updated_by=identity["username"])
    db.add(item); await db.flush()
    if default_contact_payload is not None:
        contact = LawFirmContact(law_firm_id=item.id, **default_contact_payload.model_dump(), created_by=identity["username"], updated_by=identity["username"])
        db.add(contact); await db.flush(); item.default_contact_id = contact.id
    if license_bytes:
        filename = Path(license_filename or "营业执照").name
        suffix = Path(filename).suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".gif"}: raise HTTPException(status_code=422, detail="营业执照仅支持 JPG、PNG 或 GIF 图片")
        if len(license_bytes) > 20 * 1024 * 1024: raise HTTPException(status_code=422, detail="营业执照文件不能超过 20MB")
        target = UPLOAD_ROOT / f"law-firm-{item.id}-{uuid4().hex}{suffix}"
        target.write_bytes(license_bytes)
        attachment = FileAttachment(law_firm_id=item.id, category="律所营业执照", original_name=filename, stored_name=target.name, content_type="image/*", size=len(license_bytes), path=str(target), uploader=identity["username"], remark=f"律所 {item.code} 营业执照")
        db.add(attachment); await db.flush(); item.license_attachment_id = attachment.id
    db.add(LawFirmAudit(law_firm_id=item.id, action="新建律所档案", operator=identity["username"], detail={"code": code, "name": name}))
    await db.commit(); await db.refresh(item)
    contacts = list((await db.scalars(select(LawFirmContact).where(LawFirmContact.law_firm_id == item.id).order_by(LawFirmContact.id))).all())
    return _law_firm_dict(item, await _law_firm_license(item, db), contacts)


def _dashboard_customer_for_case(
    record: BusinessRecord,
    customers_by_id: dict[int, BusinessRecord],
    customers_by_no: dict[str, list[BusinessRecord]],
    customers_by_name: dict[str, list[BusinessRecord]],
) -> BusinessRecord | None:
    data = record.data or {}
    customer, _ = _customer_reference_from_maps(
        record.customer,
        data,
        customers_by_id,
        customers_by_no,
        customers_by_name,
    )
    return customer


def _sync_customer_contact_metrics(customer: BusinessRecord) -> None:
    """Recompute the denormalized contact date/count from real contact notes.

    Communication-log rows are mirrored into ``data.notes`` with the same
    stable note id.  Keeping one source of truth here also covers ordinary
    customer follow-up notes and makes edits/deletes recalculate the maximum
    event time instead of blindly overwriting it with the last API request.
    Customer-directory changes (for example adding a contact person) are not
    communication events and must never call this helper.
    """
    from app.core.formatters import (
        _parse_customer_contact_at,
    )
    data = dict(customer.data or {})
    notes = [dict(note) for note in list(data.get("notes", [])) if isinstance(note, dict)]
    occurred_values: list[tuple[datetime, str]] = []
    for note in notes:
        raw_value = str(note.get("created_at") or "").strip()
        parsed = _parse_customer_contact_at(raw_value)
        if parsed is not None:
            occurred_values.append((parsed, raw_value))
    latest = max(occurred_values, key=lambda value: value[0])[1] if occurred_values else ""
    customer.data = {**data, "notes": notes, "last_contact_at": latest, "contact_count": len(occurred_values)}


def _mark_customer_modified(customer: BusinessRecord, identity: dict) -> None:
    """Maintain the actor used by the original ``最近更新的客户`` projection.

    ``updated_at`` is the authoritative modification time maintained by the
    database.  The actor is kept in customer JSON because the legacy schema has
    no dedicated column.  A historical ``last_modified_date`` value must not
    override the authoritative database timestamp after a real local change.
    """
    data = dict(customer.data or {})
    data.pop("last_modified_date", None)
    data["last_modified_by"] = identity["username"]
    customer.data = data


async def _customer_roi_analytics(
    identity: dict,
    db: AsyncSession,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    department: str = "",
    employee: str = "",
) -> dict:
    """Aggregate settled cash movements by an unambiguous, visible customer.

    This is deliberately distinct from the legacy-style ``brand`` chart above:
    it counts only posted ``回款`` plus ``付款``/``合同付款`` transactions,
    rather than fee applications or their denormalized received fields.  That
    makes the result a net ROI: (income - cost) / cost * 100.
    """
    from app.core.formatters import (
        _normalized_customer_name,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys, _positive_record_id,
    )
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="收付款开始日期不能晚于结束日期")
    if "finance.amount" not in await _allowed_field_keys(identity, db):
        raise HTTPException(status_code=403, detail="当前账号没有查看财务金额的权限")

    scope = await _record_scope_conditions(identity, db)
    source_records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module.in_({"finance", "contract", "contract_payment"}), *scope,
    ))).all())
    if not source_records:
        return {
            "view": "customer-roi", "rows": [],
            "totals": {"income": 0.0, "cost": 0.0, "profit": 0.0, "roi": None},
            "filter_options": {"departments": [], "employees": []},
            "formula": "ROI=(已确认回款-已确认付款)/已确认付款×100%；成本为0时不计算ROI",
            "date_basis": "收付款流水日期", "source": "realtime",
        }

    source_by_id = {record.id: record for record in source_records}
    related_ids: set[int] = set()
    related_serials: set[str] = set()
    for record in source_records:
        if record.module == "contract":
            continue
        data = record.data or {}
        related_ids.update(_positive_record_id(data.get(key)) for key in ("case_id", "contract_id", "contract_record_id"))
        related_serials.update(str(data.get(key) or "").strip() for key in ("case_no", "contract_no"))
    related_ids.discard(0)
    related_serials.discard("")
    related_conditions = [BusinessRecord.module.in_({"case", "contract"}), *scope]
    related_links = []
    if related_ids:
        related_links.append(BusinessRecord.id.in_(related_ids))
    if related_serials:
        related_links.append(BusinessRecord.serial_no.in_(related_serials))
    related_records = list((await db.scalars(select(BusinessRecord).where(
        *related_conditions, or_(*related_links),
    ))).all()) if related_links else []
    related_by_id = {record.id: record for record in related_records}
    related_by_serial = {record.serial_no: record for record in related_records}

    customer_ids: set[int] = set()
    customer_nos: set[str] = set()
    for record in [*source_records, *related_records]:
        data = record.data or {}
        customer_ids.add(_positive_record_id(data.get("customer_id") or data.get("customer_record_id")))
        customer_nos.add(str(data.get("customer_no") or "").strip())
    customer_ids.discard(0)
    customer_nos.discard("")
    customer_links = []
    if customer_ids:
        customer_links.append(BusinessRecord.id.in_(customer_ids))
    if customer_nos:
        customer_links.append(BusinessRecord.serial_no.in_(customer_nos))
    customers = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "customer", *scope, or_(*customer_links),
    ))).all()) if customer_links else []
    customers_by_id = {record.id: record for record in customers}
    customers_by_no: dict[str, list[BusinessRecord]] = {}
    for customer_record in customers:
        customers_by_no.setdefault(customer_record.serial_no, []).append(customer_record)

    def linked_records(source: BusinessRecord) -> list[BusinessRecord]:
        if source.module == "contract":
            return [source]
        data = source.data or {}
        result = [source]
        for key in ("contract_id", "contract_record_id", "case_id"):
            candidate = related_by_id.get(_positive_record_id(data.get(key)))
            if candidate and candidate not in result:
                result.append(candidate)
        for key in ("contract_no", "case_no"):
            candidate = related_by_serial.get(str(data.get(key) or "").strip())
            if candidate and candidate not in result:
                result.append(candidate)
        return result

    def resolve_customer(source: BusinessRecord) -> BusinessRecord | None:
        # Never fall back to a copied customer name.  A missing, ambiguous, or
        # out-of-scope customer relation is excluded instead of risking a merge
        # of same-named customers or disclosure of an inaccessible master row.
        for record in linked_records(source):
            data = record.data or {}
            customer_id = _positive_record_id(data.get("customer_id") or data.get("customer_record_id"))
            customer_no = str(data.get("customer_no") or "").strip()
            customer_record = customers_by_id.get(customer_id) if customer_id else None
            if customer_record is None and customer_no:
                candidates = customers_by_no.get(customer_no, [])
                customer_record = candidates[0] if len(candidates) == 1 else None
            if not customer_record:
                continue
            if customer_no and customer_record.serial_no != customer_no:
                continue
            if record.customer and _normalized_customer_name(record.customer) != _normalized_customer_name(customer_record.title):
                continue
            return customer_record
        return None

    transaction_conditions = [
        FinanceTransaction.finance_record_id.in_(set(source_by_id)),
        FinanceTransaction.transaction_type.in_({"回款", "付款", "合同付款"}),
    ]
    if date_from:
        transaction_conditions.append(FinanceTransaction.transaction_date >= date_from)
    if date_to:
        transaction_conditions.append(FinanceTransaction.transaction_date <= date_to)
    transactions = list((await db.scalars(select(FinanceTransaction).where(*transaction_conditions))).all())

    grouped: dict[int, dict] = {}
    eligible_sources: set[int] = set()
    for transaction in transactions:
        source = source_by_id.get(int(transaction.finance_record_id or 0))
        if not source:
            continue
        customer_record = resolve_customer(source)
        if not customer_record:
            continue
        eligible_sources.add(source.id)
        if department.strip() and source.department != department.strip():
            continue
        if employee.strip() and source.owner != employee.strip():
            continue
        bucket = grouped.setdefault(customer_record.id, {
            "customer_id": customer_record.id, "customer": customer_record.title,
            "customer_no": customer_record.serial_no, "income": 0.0, "cost": 0.0,
            "departments": set(), "employees": set(),
        })
        bucket["departments"].add(source.department)
        bucket["employees"].add(source.owner)
        amount = abs(float(transaction.amount or 0))
        if transaction.transaction_type == "回款":
            bucket["income"] += amount
        else:
            bucket["cost"] += amount

    rows = []
    for bucket in sorted(grouped.values(), key=lambda value: (value["customer"], value["customer_id"])):
        income, cost = round(bucket["income"], 2), round(bucket["cost"], 2)
        profit = round(income - cost, 2)
        rows.append({
            "customer_id": bucket["customer_id"], "customer": bucket["customer"], "customer_no": bucket["customer_no"],
            "department": "、".join(sorted(value for value in bucket["departments"] if value)),
            "employee": "、".join(sorted(value for value in bucket["employees"] if value)),
            "income": income, "cost": cost, "profit": profit,
            "roi": round(profit / cost * 100, 2) if cost else None,
        })
    total_income = round(sum(row["income"] for row in rows), 2)
    total_cost = round(sum(row["cost"] for row in rows), 2)
    total_profit = round(total_income - total_cost, 2)
    visible_sources = [source_by_id[source_id] for source_id in eligible_sources]
    return {
        "view": "customer-roi", "rows": rows,
        "totals": {"income": total_income, "cost": total_cost, "profit": total_profit, "roi": round(total_profit / total_cost * 100, 2) if total_cost else None},
        "filter_options": {
            "departments": sorted({source.department for source in visible_sources if source and source.department}),
            "employees": sorted({source.owner for source in visible_sources if source and source.owner}),
        },
        "formula": "ROI=(已确认回款-已确认付款)/已确认付款×100%；成本为0时不计算ROI",
        "date_basis": "收付款流水日期", "source": "realtime",
    }


async def _customer_linked_business_counts(customer: BusinessRecord, db: AsyncSession) -> dict[str, int]:
    from app.core.cases import (
        _is_civil_case_type,
    )
    from app.core.formatters import (
        _normalize_customer_name,
    )
    customer_no = str(customer.serial_no or "").strip()
    customer_name = _normalize_customer_name(customer.title)
    related_records = list((await db.scalars(
        select(BusinessRecord).where(BusinessRecord.module.in_(["contract", "case", "ipr_case"]))
    )).all())
    counts = {"contract_count": 0, "case_count": 0, "civil_case_count": 0}
    for related in related_records:
        data = related.data or {}
        linked = False
        try:
            linked = int(data.get("customer_id") or data.get("customer_record_id") or 0) == customer.id
        except (TypeError, ValueError):
            linked = False
        if not linked and customer_no:
            linked = str(data.get("customer_no") or "").strip() == customer_no
        if not linked and related.customer:
            linked = _normalize_customer_name(related.customer) == customer_name
        if not linked:
            continue
        if related.module == "contract":
            counts["contract_count"] += 1
        else:
            counts["case_count"] += 1
            if related.module == "case" and _is_civil_case_type(data.get("case_type")):
                counts["civil_case_count"] += 1
    return counts


async def _next_customer_serial_no(db: AsyncSession) -> str:
    """Allocate the next visible customer number using the legacy SHKH rule."""
    serial_prefix = f"SHKH{datetime.now():%y}"
    serial_candidates = (await db.scalars(
        select(BusinessRecord.serial_no).where(
            BusinessRecord.module == "customer",
            BusinessRecord.serial_no.like(f"{serial_prefix}%"),
        )
    )).all()
    serial_sequence = max(
        (
            int(item[len(serial_prefix):])
            for item in serial_candidates
            if item[len(serial_prefix):].isdigit()
            and len(item[len(serial_prefix):]) == 5
        ),
        default=0,
    ) + 1
    return f"{serial_prefix}{serial_sequence:05d}"


def _case_is_for_allocation_customer(record: BusinessRecord, customer: BusinessRecord | None, customer_title: str) -> bool:
    """Require the claimed customer to be the party in its stored litigation role."""
    from app.core.cases import (
        _case_party_values,
    )
    from app.core.formatters import (
        _normalize_customer_name, _record_belongs_to_customer,
    )
    if not _record_belongs_to_customer(record, customer, customer_title):
        return False
    data = record.data or {}
    role = str(data.get("client_position") or "").strip()
    if "原告" in role or "申请人" in role or "上诉人" in role:
        party_values = _case_party_values(data, CASE_PLAINTIFF_FIELDS)
    elif "被告" in role or "被申请人" in role or "被上诉人" in role:
        party_values = _case_party_values(data, CASE_DEFENDANT_FIELDS)
    elif "第三人" in role:
        party_values = _case_party_values(data, CASE_THIRD_PARTY_FIELDS)
    else:
        return True
    if not party_values:
        return True
    expected = _normalize_customer_name(customer_title)
    return any(_normalize_customer_name(value) == expected for value in party_values)


async def _conflict_customer_managers(entity_name: str, db: AsyncSession) -> list[str]:
    from app.core.formatters import (
        _normalize_conflict_entity,
    )
    from app.core.system import (
        _conflict_entity_tokens,
    )
    normalized_name = _normalize_conflict_entity(entity_name)
    customers = list((await db.scalars(
        select(BusinessRecord).where(BusinessRecord.module == "customer")
    )).all())
    matching_customers = [
        customer for customer in customers
        if normalized_name in {
            _normalize_conflict_entity(customer.title),
            _normalize_conflict_entity(customer.customer),
        }
    ]
    if not matching_customers:
        return []
    # A current customer record wins over a recycled historical copy; within
    # the same lifecycle class the most recently updated row, then id, wins.
    matching_customers.sort(
        key=lambda customer: (
            customer.status != "已回收",
            customer.updated_at or customer.created_at,
            customer.id,
        ),
        reverse=True,
    )
    customer = matching_customers[0]
    manager_tokens = _conflict_entity_tokens((customer.data or {}).get("customer_managers"))
    if not manager_tokens and customer.owner:
        manager_tokens = [customer.owner]
    if not manager_tokens:
        return []
    users = list((await db.scalars(select(User).where(User.is_active.is_(True), User.username.in_(manager_tokens)))).all())
    display_names = {user.username: user.display_name or user.username for user in users}
    return [display_names.get(manager, manager) for manager in manager_tokens]


def _empty_customer_conflict_result(query: str) -> dict:
    return {
        "found": False, "query": query, "enterprise_name": query,
        "latest_case_no": "", "latest_case_date": "",
        "plaintiffs": [], "defendants": [], "third_parties": [],
        "our_customer": "", "customer_managers": [],
    }


async def _customer_or_404(customer_id: int, identity: dict, db: AsyncSession) -> BusinessRecord:
    from app.core.permissions import (
        _ensure_record_module,
    )
    try:
        return await _ensure_record_module(customer_id, "customer", identity, db)
    except HTTPException as exc:
        if exc.status_code == 404:
            raise HTTPException(status_code=404, detail="客户不存在或无权访问") from exc
        raise


async def _locked_customer_or_404(customer_id: int, identity: dict, db: AsyncSession) -> BusinessRecord:
    """Lock a visible customer and refresh it after waiting for a concurrent writer."""
    from app.core.permissions import (
        _record_scope_conditions,
    )
    conditions = [
        BusinessRecord.id == customer_id,
        BusinessRecord.module == "customer",
        *(await _record_scope_conditions(identity, db)),
    ]
    customer = await db.scalar(
        select(BusinessRecord)
        .where(*conditions)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在或无权访问")
    return customer


def _customer_event(customer: BusinessRecord, action: str, identity: dict, comment: str, from_status: str | None = None) -> WorkflowEvent:
    _mark_customer_modified(customer, identity)
    return WorkflowEvent(record_id=customer.id, action=action, from_status=from_status or customer.status, to_status=customer.status, operator=identity["username"], comment=comment)


async def _customer_by_guid(customer_guid: str, identity: dict, db: AsyncSession) -> BusinessRecord:
    guid = str(customer_guid or "").strip()
    if not guid:
        raise HTTPException(status_code=422, detail="客户 Guid 不能为空")
    customers = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "customer"))).all()
    customer = next((item for item in customers if _customer_guid(item) == guid), None)
    if not customer:
        raise HTTPException(status_code=404, detail="客户不存在或无权访问")
    return await _customer_or_404(customer.id, identity, db)


async def _customer_files_by_guid(customer_guid: str, identity: dict, db: AsyncSession) -> tuple[BusinessRecord, list[FileAttachment]]:
    customer = await _customer_by_guid(customer_guid, identity, db)
    files = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id == customer.id).order_by(FileAttachment.created_at, FileAttachment.id))).all())
    return customer, files


async def _customer_contact_or_404(customer_id: int, contact_id: str, identity: dict, db: AsyncSession) -> tuple[BusinessRecord, list[dict], int]:
    from app.core.permissions import (
        _require_record_owner_or_manager,
    )
    customer = await _customer_or_404(customer_id, identity, db)
    await _require_record_owner_or_manager(customer, identity, db)
    contacts = list((customer.data or {}).get("contacts", []))
    index = next((i for i, item in enumerate(contacts) if item.get("id") == contact_id), None)
    if index is None: raise HTTPException(status_code=404, detail="联系人不存在")
    return customer, contacts, index


async def _portal_customer(body: CustomerPortalLoginInput, db: AsyncSession) -> BusinessRecord:
    customers = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "customer"))).all())
    customer = next((item for item in customers if str(((item.data or {}).get("portal_access") or {}).get("account") or "").casefold() == body.account.strip().casefold()), None)
    portal = (customer.data or {}).get("portal_access") if customer else None
    if not customer or not portal or not portal.get("enabled") or not portal.get("activated_at") or not portal.get("password_hash") or not verify_password(body.password, portal["password_hash"]):
        raise HTTPException(status_code=401, detail="客户服务账号或密码无效")
    return customer


async def _persist_case_litigant_customers(
    case_record: BusinessRecord,
    parties_by_role: dict[str, list[str]],
    identity: dict,
    db: AsyncSession,
) -> list[BusinessRecord]:
    """Materialize newly typed case parties in the customer register.

    The legacy case editor creates a CRM customer with the party/applicant
    type before it links the person to the case.  Keep that invariant in one
    backend transaction so every case entry point feeds customer conflict
    searches and both personal and company party lists.
    """
    from app.core.formatters import (
        _normalize_customer_name,
    )
    from app.core.legacy_sync import (
        _sync_legacy_projection,
    )
    requested: dict[str, dict[str, object]] = {}
    for role, values in parties_by_role.items():
        for title in values:
            normalized = _normalize_customer_name(title)
            entry = requested.setdefault(normalized, {"title": title, "roles": []})
            roles = entry["roles"]
            if isinstance(roles, list) and role not in roles:
                roles.append(role)
    if not requested:
        return []

    current_user = await db.scalar(select(User).where(
        User.username == identity["username"], User.is_active.is_(True),
    ))
    if not current_user:
        raise HTTPException(status_code=401, detail="当前用户不存在或已停用")
    active_party_type = await db.scalar(select(SystemParameter.id).where(
        SystemParameter.category == "customer_type",
        SystemParameter.name == "当事人",
        SystemParameter.is_active.is_(True),
    ))
    if not active_party_type:
        raise HTTPException(status_code=422, detail="客户类型“当事人”不存在或已停用")

    existing_customers = list((await db.scalars(
        select(BusinessRecord).where(BusinessRecord.module == "customer")
    )).all())
    existing_by_name = {
        _normalize_customer_name(item.title): item
        for item in existing_customers
        if _normalize_customer_name(item.title)
    }
    created: list[BusinessRecord] = []
    for normalized, entry in requested.items():
        if normalized in existing_by_name:
            continue
        title = str(entry["title"])
        roles = list(entry["roles"]) if isinstance(entry["roles"], list) else []
        serial_no = await _next_customer_serial_no(db)
        data = {
            "customer_type": "当事人",
            "level": "潜在客户",
            "customer_managers": [current_user.username],
            "shared_with": [],
            "is_shared": "否",
            "is_assisted": "否",
            "fee_reduction": "否",
            "customer_guid": str(uuid4()),
            "customer_source": "案件当事人",
            "file_date": date.today().isoformat(),
            "contact_accounts": [],
            "contact": "",
            "case_litigant_origin": {
                "case_id": case_record.id,
                "case_no": case_record.serial_no,
                "roles": roles,
            },
        }
        party = BusinessRecord(
            module="customer",
            serial_no=serial_no,
            title=title,
            customer=title,
            status="潜在",
            owner=current_user.username,
            department=current_user.department,
            description=f"由案件 {case_record.serial_no} 当事人信息自动建档",
            data=data,
        )
        _mark_customer_modified(party, identity)
        db.add(party)
        await db.flush()
        db.add(WorkflowEvent(
            record_id=party.id,
            action="创建当事人",
            to_status=party.status,
            operator=identity["username"],
            comment=f"由案件 {case_record.serial_no} 自动同步：{'、'.join(roles)}",
        ))
        await _sync_legacy_projection(party, identity, db)
        existing_by_name[normalized] = party
        created.append(party)
    return created
