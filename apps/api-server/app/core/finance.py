"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.constants import (
    CASE_DEFENDANT_FIELDS, CASE_PLAINTIFF_FIELDS, EXPENSE_SCOPE_FEE_TYPES, EXPENSE_SUBTYPE_FEE_TYPE, FEE_TYPE_BASE_SCOPES,
    FEE_TYPE_ROOT_BASES, FINANCE_FEE_TYPES, INVOICE_RELEASED_STATUSES, JAR_FEE_MODULE, REFUND_CASE_FEE_STATUSES,
    REFUND_CASE_FEE_STATUS_BY_LABEL, REFUND_GROUP_ALIASES, REFUND_LIST_STATUSES, _OFFICIAL_RECEIVABLE_FEE_WORDS,
)
from app.core.dependencies import (
    AsyncSession, BusinessRecord, CaseAssistedFee, ContractObject, ContractPaymentLine,
    Decimal, FileAttachment, FinanceTransaction, HTTPException, IncomingPayment,
    IprCaseAnnualFee, IprCaseAssistedFee, IprCaseReminder, IprCaseReminderSuppression, JarFeeAuditLog,
    ROUND_UP, ReceivablePlan, ReconciliationBatch, Response, SystemParameter,
    User, WorkflowEvent, date, datetime, false,
    func, or_, select, uuid4,
)
from app.models_shared import (
    FinanceFeeInput, FinancePaymentTypeCreateInput, InvoiceApplicationInput, IprCaseAnnualFeeMonitoringInput, JarFeeInput,
)


def _receivable_dict(plan: ReceivablePlan, contract: BusinessRecord, users_by_username: dict[str, User] | None = None) -> dict:
    from app.core.formatters import (
        _person_reference_display,
    )
    remaining = max(plan.amount - plan.received_amount, 0)
    effective_status = plan.status
    if remaining > 0 and plan.due_date < date.today() and plan.status != "已收款":
        effective_status = "已逾期"
    return {
        "id": plan.id, "contract_record_id": plan.contract_record_id,
        "contract_no": contract.serial_no, "contract_title": contract.title,
        "customer": contract.customer, "phase": plan.phase, "due_date": plan.due_date,
        "amount": plan.amount, "received_amount": plan.received_amount,
        "remaining_amount": remaining, "status": effective_status,
        "payer": plan.payer, "owner": contract.owner,
        "owner_display_name": _person_reference_display(contract.owner, users_by_username or {})[0], "remark": plan.remark,
        "updated_at": plan.updated_at,
    }


def _receivable_number(value: object) -> float:
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _receivable_relation_id(data: dict, *keys: str) -> int:
    for key in keys:
        try:
            value = int(data.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        if value:
            return value
    return 0


def _receivable_fee_category(value: object) -> str:
    label = str(value or "").strip()
    return "official" if any(word in label for word in _OFFICIAL_RECEIVABLE_FEE_WORDS) else "agency"


def _finance_transaction_dict(item: FinanceTransaction, record: BusinessRecord | None = None, attachments: list[FileAttachment] | None = None, *, show_amount: bool = True, users_by_username: dict[str, User] | None = None) -> dict:
    from app.core.formatters import (
        _person_reference_display,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    vouchers = attachments or []
    return {
        "id": item.id, "finance_record_id": item.finance_record_id,
        "finance_no": record.serial_no if record else "", "finance_title": record.title if record else "",
        "transaction_type": item.transaction_type, "amount": item.amount if show_amount else None, "transaction_date": item.transaction_date,
        "voucher_no": item.voucher_no, "counterparty": item.counterparty, "operator": item.operator,
        "operator_display_name": _person_reference_display(item.operator, users_by_username or {})[0],
        "remark": item.remark, "created_at": item.created_at,
        "voucher_count": len(vouchers), "voucher_categories": sorted({x.category for x in vouchers}),
        "vouchers": [_attachment_dict(x, record) for x in vouchers],
    }


def _incoming_payment_legacy_summary(item: IncomingPayment) -> dict:
    official_amount = 0.0
    agency_amount = 0.0
    other_amount = 0.0
    payment_methods: list[str] = []
    contract_nos: list[str] = []
    for allocation in item.allocations or []:
        payment_method = str(allocation.get("payment_method") or "").strip()
        contract_no = str(allocation.get("contract_no") or "").strip()
        if payment_method and payment_method not in payment_methods:
            payment_methods.append(payment_method)
        if contract_no and contract_no not in contract_nos:
            contract_nos.append(contract_no)
        settlement_items = allocation.get("settlement_items")
        amount_rows = settlement_items if isinstance(settlement_items, list) and settlement_items else [allocation]
        for row in amount_rows:
            if not isinstance(row, dict):
                continue
            amount = _round_fee_amount(float(row.get("amount") or row.get("settlement_amount") or 0))
            kind = _settlement_fee_kind(str(row.get("fee_type") or ""))
            if kind == "official":
                official_amount += amount
            elif kind == "agency":
                agency_amount += amount
            else:
                other_amount += amount
    return {
        "contract_no": item.contract_no or "、".join(contract_nos),
        "customer_name": item.claimed_customer,
        "payment_method": "、".join(payment_methods) or item.bank_source,
        "assigned_official_fee": _round_fee_amount(official_amount),
        "assigned_agency_fee": _round_fee_amount(agency_amount),
        "assigned_other_fee": _round_fee_amount(other_amount),
    }


def _incoming_payment_dict(item: IncomingPayment, *, show_amount: bool = True, users_by_username: dict[str, User] | None = None) -> dict:
    from app.core.formatters import (
        _person_reference_display,
    )
    amount = float(item.amount)
    allocated = float(item.allocated_amount or 0)
    if allocated <= 0 and item.allocations:
        allocated = _round_fee_amount(sum(
            float(allocation.get("amount") or 0)
            for allocation in item.allocations
            if isinstance(allocation, dict)
        ))
    users = users_by_username or {}
    legacy_summary = _incoming_payment_legacy_summary(item)
    if not show_amount:
        for key in ("assigned_official_fee", "assigned_agency_fee", "assigned_other_fee"):
            legacy_summary[key] = None
    return {"id": item.id, "receipt_no": item.receipt_no, "received_date": item.received_date, "amount": amount if show_amount else None, "payer_name": item.payer_name, "bank_reference": item.bank_reference, "status": item.status, "claimed_customer": item.claimed_customer, "contract_record_id": item.contract_record_id, "contract_no": item.contract_no, "case_no": item.case_no, "bank_source": item.bank_source, "claimant": item.claimant, "claimant_display_name": _person_reference_display(item.claimant, users)[0], "allocated_amount": allocated if show_amount else None, "remaining_amount": max(amount - allocated, 0) if show_amount else None, "allocations": item.allocations or [], "operator": item.operator, "operator_display_name": _person_reference_display(item.operator, users)[0], "remark": item.remark, "created_at": item.created_at, "updated_at": item.updated_at, **legacy_summary}


def _reconciliation_dict(item: ReconciliationBatch, *, show_amount: bool = True, users_by_username: dict[str, User] | None = None) -> dict:
    from app.core.formatters import (
        _person_reference_display,
    )
    return {"id": item.id, "period_type": item.period_type, "date_from": item.date_from, "date_to": item.date_to, "transaction_count": item.transaction_count, "total_amount": item.total_amount if show_amount else None, "discrepancy_amount": item.discrepancy_amount if show_amount else None, "status": item.status, "operator": item.operator, "operator_display_name": _person_reference_display(item.operator, users_by_username or {})[0], "remark": item.remark, "created_at": item.created_at}


def _fee_type_base_from_root(root: SystemParameter) -> str:
    configured = str((root.extra or {}).get("base_fee_type") or "").strip()
    if configured in FINANCE_FEE_TYPES:
        return configured
    if root.code in FEE_TYPE_ROOT_BASES:
        return FEE_TYPE_ROOT_BASES[root.code]
    name = root.name.strip()
    if "内部" in name:
        return "内部费用"
    if "代理" in name:
        return "代理费"
    if "官" in name or "诉讼" in name:
        return "官方费用"
    if "结算" in name:
        return "结算费用"
    if "归档" in name:
        return "归档费用"
    return "其他费用"


def _fee_type_catalog(items: list[SystemParameter]) -> list[dict]:
    from app.core.system import (
        _system_parameter_dict,
    )
    by_code = {item.code: item for item in items}
    child_codes: dict[str, list[str]] = {}
    for item in items:
        parent_code = str((item.extra or {}).get("parent_code") or "").strip()
        if parent_code:
            child_codes.setdefault(parent_code, []).append(item.code)

    result: list[dict] = []
    for item in items:
        lineage: list[SystemParameter] = []
        seen: set[str] = set()
        cursor: SystemParameter | None = item
        while cursor is not None and cursor.code not in seen:
            lineage.append(cursor)
            seen.add(cursor.code)
            parent_code = str((cursor.extra or {}).get("parent_code") or "").strip()
            cursor = by_code.get(parent_code) if parent_code else None
        lineage.reverse()
        root = lineage[0] if lineage else item
        base_fee_type = _fee_type_base_from_root(root)
        scopes = list(FEE_TYPE_BASE_SCOPES.get(base_fee_type, ["律所", "平台"]))
        row = _system_parameter_dict(item)
        row.update({
            "parent_code": str((item.extra or {}).get("parent_code") or "").strip(),
            "path": " / ".join(node.name for node in lineage),
            "depth": max(len(lineage) - 1, 0),
            "root_code": root.code,
            "base_fee_type": base_fee_type,
            "expense_scopes": scopes,
            "has_children": bool(child_codes.get(item.code)),
            "selectable": item.is_active and not any(by_code[code].is_active for code in child_codes.get(item.code, []) if code in by_code) and bool(scopes),
        })
        result.append(row)
    return result


async def _editable_finance_fee(fee_id: int, identity: dict, db: AsyncSession) -> BusinessRecord:
    # Resolve the mutation target by id first so a visible finance row owned by
    # another user returns the explicit 403 owner guard instead of being hidden
    # as a generic 404 by the list data-scope filter.
    from app.core.permissions import (
        _ensure_record_visible, _require_record_owner_or_manager,
    )
    item = await db.get(BusinessRecord, fee_id)
    if not item or item.module != "finance":
        raise HTTPException(status_code=404, detail="费用记录不存在")
    case_id = int((item.data or {}).get("case_id") or 0)
    if case_id:
        case = await _ensure_record_visible(case_id, identity, db)
        if case.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
            raise HTTPException(status_code=409, detail="归档中的案件费用不可修改或删除")
    else:
        await _require_record_owner_or_manager(item, identity, db)
    if item.status != "草稿":
        raise HTTPException(status_code=409, detail="仅草稿费用可以修改或删除")
    return item


async def _finance_fee_commission_details(
    body: FinanceFeeInput,
    fee_amount: float,
    db: AsyncSession,
) -> list[dict]:
    """Validate and normalize employee commissions attached to an agency fee."""
    from app.core.formatters import (
        _contract_person_display_name,
    )
    if body.fee_type != "代理费":
        if body.commission_details:
            raise HTTPException(status_code=422, detail="只有代理费可以新建员工提成")
        return []
    details = body.commission_details or []
    if not details:
        return []
    usernames = [detail.employee_username.strip().lower() for detail in details]
    if len(set(usernames)) != len(usernames):
        raise HTTPException(status_code=422, detail="同一员工只能新增一条提成")
    users = list((await db.scalars(select(User).where(
        func.lower(User.username).in_(usernames),
        User.is_active.is_(True),
    ))).all())
    users_by_username = {user.username.lower(): user for user in users}
    if len(users_by_username) != len(usernames):
        raise HTTPException(status_code=422, detail="员工提成只能选择系统中已启用的员工")
    normalized = []
    total = 0.0
    for detail, username in zip(details, usernames):
        amount = _round_fee_amount(detail.amount)
        total += amount
        user = users_by_username[username]
        normalized.append({
            "employee_username": user.username,
            "employee_display_name": _contract_person_display_name(user.display_name, {user.username.lower(): user.display_name}),
            "payee": _contract_person_display_name(user.display_name, {user.username.lower(): user.display_name}),
            "commission_type": detail.commission_type.strip(),
            "amount": amount,
            "actual_commission": amount,
            "remark": detail.remark.strip(),
        })
    if total > fee_amount + 0.001:
        raise HTTPException(status_code=422, detail="员工提成合计不能大于律师代理费金额")
    return normalized


def _case_fee_contract_body(contract: BusinessRecord) -> str:
    return str((contract.data or {}).get("contract_body") or "律所").strip()


async def _resolve_case_fee_contract(
    case_record: BusinessRecord | None,
    contract_record: BusinessRecord | None,
    expense_scope: str | None,
    identity: dict,
    db: AsyncSession,
) -> BusinessRecord | None:
    scope = str(expense_scope or "").strip()
    if not case_record or scope not in {"律所", "平台"}:
        return contract_record
    if contract_record:
        if contract_record.customer != case_record.customer:
            raise HTTPException(status_code=409, detail="关联合同必须属于当前案件客户")
        if _case_fee_contract_body(contract_record) != scope:
            raise HTTPException(status_code=409, detail=f"新增{scope}费用必须选择合同主体为{scope}的合同")
        return contract_record
    candidates = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "contract",
        BusinessRecord.customer == case_record.customer,
    ).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all())
    matched = next((item for item in candidates if _case_fee_contract_body(item) == scope), None)
    if not matched:
        raise HTTPException(status_code=409, detail=f"当前案件客户名下没有{scope}合同，无法新增{scope}费用")
    return matched


async def _internal_fee_mutation_target(fee_id: int, identity: dict, db: AsyncSession) -> BusinessRecord:
    """Resolve a dedicated internal-fee mutation without exposing other fee rows."""
    item = await db.get(BusinessRecord, fee_id)
    if not item or item.module != "finance" or (item.data or {}).get("fee_type") != "内部费用":
        raise HTTPException(status_code=404, detail="内部费用记录不存在")
    return item


def _jar_fee_dict(item: BusinessRecord, allowed_fields: set[str] | None = None) -> dict:
    from app.core.system import (
        _record_dict,
    )
    result = _record_dict(item, allowed_fields)
    data = result["data"]
    result.update({
        "contract_id": data.get("contract_id"), "contract_no": data.get("contract_no", ""),
        "payer_name": data.get("payer_name", ""), "bank_voucher_no": data.get("bank_voucher_no", ""),
        "received_date": data.get("received_date", ""), "amount": data.get("amount"),
        "official_fee_amount": data.get("official_fee_amount"), "agency_fee_amount": data.get("agency_fee_amount"),
        "other_fee_amount": data.get("other_fee_amount"), "payment_method": data.get("payment_method", ""),
        "handler": data.get("handler", item.owner), "remark": data.get("remark", item.description),
    })
    if allowed_fields is not None and "finance.amount" not in allowed_fields:
        for key in ("amount", "official_fee_amount", "agency_fee_amount", "other_fee_amount"):
            result[key] = None
            result["data"].pop(key, None)
    return result


def _jar_fee_audit(item: BusinessRecord, action: str, identity: dict, detail: dict | None = None) -> JarFeeAuditLog:
    """Keep the audit trail after a JAR row is deleted (unlike workflow FK rows)."""
    return JarFeeAuditLog(jar_fee_record_id=item.id, jar_fee_serial_no=item.serial_no, action=action, operator=identity["username"], detail=detail or {})


async def _jar_fee_or_404(jar_fee_id: int, identity: dict, db: AsyncSession) -> BusinessRecord:
    from app.core.permissions import (
        _ensure_record_visible,
    )
    item = await _ensure_record_visible(jar_fee_id, identity, db)
    if item.module != JAR_FEE_MODULE:
        raise HTTPException(status_code=404, detail="交案费记录不存在")
    return item


async def _editable_jar_fee(jar_fee_id: int, identity: dict, db: AsyncSession) -> BusinessRecord:
    from app.core.permissions import (
        _require_jar_fee_access, _require_record_owner_or_manager,
    )
    await _require_jar_fee_access(identity, db, write=True)
    item = await _jar_fee_or_404(jar_fee_id, identity, db)
    await _require_record_owner_or_manager(item, identity, db)
    if item.status != "待确认":
        raise HTTPException(status_code=409, detail="仅待确认交案费可以修改或删除")
    return item


async def _jar_fee_contract(contract_id: int, identity: dict, db: AsyncSession) -> BusinessRecord:
    from app.core.permissions import (
        _ensure_record_visible,
    )
    contract = await _ensure_record_visible(contract_id, identity, db)
    if contract.module != "contract":
        raise HTTPException(status_code=422, detail="关联记录不是合同")
    return contract


def _jar_fee_data(body: JarFeeInput, contract: BusinessRecord) -> dict:
    amount = _round_fee_amount(body.amount)
    components = [_round_fee_amount(body.official_fee_amount), _round_fee_amount(body.agency_fee_amount), _round_fee_amount(body.other_fee_amount)]
    if sum(components) > amount + 0.001:
        raise HTTPException(status_code=422, detail="官费、代理费和其他费用合计不能大于交案费金额")
    return {
        "fee_kind": "JAR交案费", "contract_id": contract.id, "contract_no": contract.serial_no,
        "payer_name": body.payer_name.strip() or contract.customer, "bank_voucher_no": body.bank_voucher_no.strip(),
        "received_date": str(body.received_date) if body.received_date else "", "amount": amount,
        "official_fee_amount": components[0], "agency_fee_amount": components[1], "other_fee_amount": components[2],
        "payment_method": body.payment_method.strip(), "handler": body.handler.strip(), "remark": body.remark.strip(),
    }


async def _fee_inform_record(
    inform_id: int, identity: dict, db: AsyncSession, *, write: bool = False,
) -> tuple[BusinessRecord, BusinessRecord]:
    """Resolve an independent notice and its source fee without trusting IDs from the client."""
    from app.core.permissions import (
        _ensure_record_visible, _require_record_owner_or_manager,
    )
    notice = await db.get(BusinessRecord, inform_id) if write else await _ensure_record_visible(inform_id, identity, db)
    if not notice or notice.module != "finance_fee_inform":
        raise HTTPException(status_code=404, detail="费用通知不存在")
    source_fee_id = int((notice.data or {}).get("source_fee_id") or 0)
    source_fee = await db.get(BusinessRecord, source_fee_id) if write else await _ensure_record_visible(source_fee_id, identity, db)
    if not source_fee:
        raise HTTPException(status_code=409, detail="费用通知的关联费用无效")
    if source_fee.module != "finance":
        raise HTTPException(status_code=409, detail="费用通知的关联费用无效")
    if write:
        await _require_record_owner_or_manager(notice, identity, db)
        await _require_record_owner_or_manager(source_fee, identity, db)
        await _ensure_record_visible(notice.id, identity, db)
        await _ensure_record_visible(source_fee.id, identity, db)
    return notice, source_fee


async def _fee_inform_dict(notice: BusinessRecord, source_fee: BusinessRecord, db: AsyncSession) -> dict:
    from app.core.storage import (
        _attachment_dict,
    )
    from app.core.system import (
        _record_dict,
    )
    data = dict(notice.data or {})
    attachment_id = int(data.get("receipt_attachment_id") or 0)
    attachment = await db.get(FileAttachment, attachment_id) if attachment_id else None
    return {
        **_record_dict(notice),
        "source_fee": _record_dict(source_fee),
        "receipt_attachment": _attachment_dict(attachment, notice) if attachment else None,
    }


def _fee_matches_contract_object(fee: BusinessRecord, item: ContractObject, case: BusinessRecord) -> bool:
    from app.core.formatters import (
        _case_fee_display_type,
    )
    data = fee.data or {}
    try:
        explicit_object_id = int(data.get("contract_object_id") or 0)
    except (TypeError, ValueError):
        explicit_object_id = 0
    if explicit_object_id:
        return explicit_object_id == item.id
    try:
        linked_case_id = int(data.get("case_id") or 0)
    except (TypeError, ValueError):
        linked_case_id = 0
    if linked_case_id != case.id and str(data.get("case_no") or "").strip() != case.serial_no:
        return False
    object_fee_type = item.fee_type.strip()
    if not object_fee_type:
        return True
    fee_names = {
        str(data.get("fee_type") or "").strip(),
        str(data.get("fee_type_name") or "").strip(),
        str(data.get("case_fee_type_name") or "").strip(),
        _case_fee_display_type(fee),
    }
    aliases = {"代理费": "律师代理费", "官方费用": "官费"}
    normalized_object = aliases.get(object_fee_type, object_fee_type)
    return normalized_object in {aliases.get(value, value) for value in fee_names if value}


async def _contract_payment_candidate_rows(contract: BusinessRecord, identity: dict, db: AsyncSession) -> list[dict]:
    """Return each visible contract subject with its remaining payable amount.

    Pending, approved-for-payment and paid applications reserve the amount so
    the same subject cannot be submitted twice while an earlier request is in
    flight. Rejected requests deliberately release the amount.
    """
    from app.core.permissions import (
        _ensure_record_visible,
    )
    objects = (await db.scalars(select(ContractObject).where(
        ContractObject.contract_record_id == contract.id
    ).order_by(ContractObject.id))).all()
    object_ids = [item.id for item in objects]
    used_by_object: dict[int, float] = {}
    if object_ids:
        active_payment_ids = select(BusinessRecord.id).where(
            BusinessRecord.module == "contract_payment",
            BusinessRecord.status.in_(["待审批", "待付款", "已付款", "已核销"]),
        )
        lines = (await db.scalars(select(ContractPaymentLine).where(
            ContractPaymentLine.contract_object_id.in_(object_ids),
            ContractPaymentLine.payment_record_id.in_(active_payment_ids),
        ))).all()
        for line in lines:
            used_by_object[line.contract_object_id] = _round_fee_amount(
                used_by_object.get(line.contract_object_id, 0) + line.requested_amount
            )
    rows: list[dict] = []
    for item in objects:
        case = await _ensure_record_visible(item.case_record_id, identity, db)
        if case.module != "case":
            continue
        used = used_by_object.get(item.id, 0)
        rows.append({
            "contract_object_id": item.id,
            "case_record_id": case.id,
            "case_no": case.serial_no,
            "case_title": case.title,
            "fee_type": item.fee_type,
            "contract_amount": item.amount,
            "reserved_amount": used,
            "remaining_amount": max(_round_fee_amount(item.amount - used), 0),
            "remark": item.remark,
        })
    return rows


async def _resolve_case_fee_type_master(
    fee_type_id: int | None,
    expense_scope: str | None,
    db: AsyncSession,
    *,
    legacy_name: str = "",
    legacy_base: str = "",
) -> tuple[SystemParameter, dict]:
    from app.core.permissions import (
        _validate_finance_fee_scope_subtype,
    )
    items = list((await db.scalars(select(SystemParameter).where(
        SystemParameter.category == "fee_type",
        SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.sort_order, SystemParameter.id))).all())
    if not items:
        expected_base = EXPENSE_SUBTYPE_FEE_TYPE.get(legacy_name)
        if not legacy_name or not legacy_base or expected_base != legacy_base:
            raise HTTPException(status_code=422, detail="费用子类型与费用类型不一致")
        if expense_scope and legacy_base not in EXPENSE_SCOPE_FEE_TYPES[expense_scope]:
            raise HTTPException(status_code=422, detail="费用归属与费用类型不一致")
        _validate_finance_fee_scope_subtype(expense_scope, legacy_name, legacy_base)
        legacy = SystemParameter(
            category="fee_type", code="", name=legacy_name,
            extra={"parent_code": ""}, is_active=True,
        )
        return legacy, {
            "path": legacy_name, "base_fee_type": legacy_base,
            "expense_scopes": list(FEE_TYPE_BASE_SCOPES.get(legacy_base, [])),
            "selectable": True,
        }
    if not fee_type_id:
        raise HTTPException(status_code=422, detail="案件费用必须选择系统参数中的费用类型")
    catalog = _fee_type_catalog(items)
    option = next((row for row in catalog if row["id"] == fee_type_id), None)
    item = next((row for row in items if row.id == fee_type_id), None)
    if not item or not option:
        raise HTTPException(status_code=422, detail="费用类型不存在或已停用")
    if not option["selectable"]:
        raise HTTPException(status_code=422, detail="请选择没有下级分类的末级费用类型")
    scope = str(expense_scope or "").strip()
    if scope and scope not in option["expense_scopes"]:
        raise HTTPException(status_code=422, detail="费用归属与费用类型不一致")
    _validate_finance_fee_scope_subtype(scope, item.name, option["base_fee_type"])
    return item, option


def _case_fee_type_snapshot(item: SystemParameter, option: dict) -> dict:
    return {
        "fee_type_id": item.id,
        "fee_type_code": item.code,
        "fee_type_name": item.name,
        "fee_type_path": option["path"],
        "fee_type": option["base_fee_type"],
        "expense_subtype": item.name,
    }


def _round_fee_amount(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_UP))


async def _finance_linked_case(case_no: str, identity: dict, db: AsyncSession) -> BusinessRecord | None:
    from app.core.permissions import (
        _record_scope_conditions,
    )
    case_no = case_no.strip()
    if not case_no:
        return None
    item = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "case", BusinessRecord.serial_no == case_no, *(await _record_scope_conditions(identity, db))))
    if not item:
        raise HTTPException(status_code=404, detail="关联案件不存在或无权访问")
    return item


def _invoice_linked_fee_ids(data: dict) -> set[int]:
    values = list(data.get("case_fee_ids") or [])
    if data.get("case_fee_id") is not None:
        values.append(data.get("case_fee_id"))
    result: set[int] = set()
    for value in values:
        try:
            fee_id = int(value)
        except (TypeError, ValueError):
            continue
        if fee_id > 0:
            result.add(fee_id)
    return result


async def _validate_invoice_source_links(
    body: InvoiceApplicationInput,
    identity: dict,
    db: AsyncSession,
    *,
    require_source: bool,
    exclude_invoice_id: int | None = None,
) -> tuple[BusinessRecord | None, BusinessRecord | None, list[BusinessRecord], list[dict]]:
    from app.core.permissions import (
        _ensure_record_visible, _record_scope_conditions,
    )
    if require_source and not body.contract_record_id:
        raise HTTPException(status_code=422, detail="新建发票申请必须关联合同")
    case_record = await _finance_linked_case(body.case_no, identity, db)
    if body.case_record_id:
        linked_case = await _ensure_record_visible(body.case_record_id, identity, db)
        if linked_case.module != "case":
            raise HTTPException(status_code=422, detail="关联记录不是案件")
        if case_record and case_record.id != linked_case.id:
            raise HTTPException(status_code=409, detail="案件编号与案件记录不一致")
        case_record = linked_case
    contract_record = None
    if body.contract_record_id:
        contract_record = await _ensure_record_visible(body.contract_record_id, identity, db)
        if contract_record.module != "contract":
            raise HTTPException(status_code=422, detail="关联记录不是合同")
        if case_record and contract_record.customer != case_record.customer:
            raise HTTPException(status_code=409, detail="关联合同必须属于当前案件客户")
    case_fee_ids = list(dict.fromkeys(body.case_fee_ids))
    if require_source and not case_fee_ids:
        raise HTTPException(status_code=422, detail="新建发票申请至少关联一笔案件费用")
    case_fees: list[BusinessRecord] = []
    if case_fee_ids:
        case_fees = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.id.in_(case_fee_ids), BusinessRecord.module == "finance",
            *(await _record_scope_conditions(identity, db)),
        ))).all())
        if len(case_fees) != len(case_fee_ids):
            raise HTTPException(status_code=404, detail="部分案件费用不存在或无权访问")
        linked_case_nos = {str((item.data or {}).get("case_no") or "").strip() for item in case_fees} - {""}
        if len(linked_case_nos) > 1:
            raise HTTPException(status_code=409, detail="同一张发票只能关联同一案件的费用")
        if case_record and linked_case_nos and case_record.serial_no not in linked_case_nos:
            raise HTTPException(status_code=409, detail="发票案件与所选案件费用不一致")
        if not case_record and linked_case_nos:
            case_record = await _finance_linked_case(next(iter(linked_case_nos)), identity, db)
    if require_source and contract_record:
        contract_id = contract_record.id
        contract_no = contract_record.serial_no
        for fee in case_fees:
            data = fee.data or {}
            fee_contract_id = data.get("contract_id") or data.get("contract_record_id")
            fee_contract_no = str(data.get("contract_no") or "").strip()
            if fee_contract_id is None and case_record:
                case_data = case_record.data or {}
                fee_contract_id = case_data.get("contract_id") or case_data.get("contract_record_id")
                fee_contract_no = fee_contract_no or str(case_data.get("contract_no") or "").strip()
            if (fee_contract_id is not None and int(fee_contract_id) != contract_id) or (fee_contract_no and fee_contract_no != contract_no):
                raise HTTPException(status_code=409, detail="所选案件费用必须属于当前合同")
    active_invoices = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "invoice",
        BusinessRecord.status.not_in(INVOICE_RELEASED_STATUSES),
        *(await _record_scope_conditions(identity, db)),
    ))).all())
    active_by_fee: dict[int, BusinessRecord] = {}
    for invoice in active_invoices:
        if exclude_invoice_id is not None and invoice.id == exclude_invoice_id:
            continue
        for fee_id in _invoice_linked_fee_ids(invoice.data or {}):
            active_by_fee.setdefault(fee_id, invoice)
    if require_source:
        duplicate_ids = [fee.id for fee in case_fees if fee.id in active_by_fee]
        if duplicate_ids:
            raise HTTPException(status_code=409, detail="所选案件费用已经申请开票，不能重复申请")
        available = sum(max(float((fee.data or {}).get("amount") or 0), 0) for fee in case_fees)
        if float(body.amount) > available:
            raise HTTPException(status_code=422, detail="开票金额不能超过所选案件费用可开票金额")
    allocations: list[dict] = []
    remaining = float(body.amount)
    for index, fee in enumerate(case_fees):
        fee_amount = max(float((fee.data or {}).get("amount") or 0), 0)
        allocated = remaining if index == len(case_fees) - 1 else min(remaining, fee_amount)
        allocated = round(max(allocated, 0), 2)
        allocations.append({"fee_id": fee.id, "amount": allocated})
        remaining = round(max(remaining - allocated, 0), 2)
    return case_record, contract_record, case_fees, allocations


def _invoice_original_type(value: object) -> str:
    text = str(value or "").strip()
    return "专票" if "专用" in text or text == "专票" else "普票"


async def _invoice_list_rows(
    identity: dict,
    db: AsyncSession,
    *,
    scope: str,
    customer: str,
    application_no: str,
    invoice_type: str,
    invoice_title: str,
    invoice_no: str,
    invoice_status: str,
    invoiced_from: date | None,
    invoiced_to: date | None,
    case_no: str,
    applicant_filter: str = "",
    ids: set[int] | None = None,
) -> list[dict]:
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "invoice",
        *(await _record_scope_conditions(identity, db)),
    ).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all())
    if ids is not None:
        records = [item for item in records if item.id in ids]
    allowed_fields = await _allowed_field_keys(identity, db)
    personal_names = {str(identity.get("username", "")).strip(), str(identity.get("display_name", "")).strip()} - {""}
    user_display_names = {
        username: (display_name or username)
        for username, display_name in (await db.execute(select(User.username, User.display_name))).all()
    }

    def contains(value: object, needle: str) -> bool:
        return not needle.strip() or needle.strip().casefold() in str(value or "").casefold()

    rows: list[dict] = []
    for item in records:
        data = item.data or {}
        applicant_account = str(data.get("applicant") or item.owner or "").strip()
        applicant = user_display_names.get(applicant_account, applicant_account)
        if scope == "mine" and not ({applicant_account, applicant} & personal_names):
            continue
        if scope == "pending" and item.status != "待开票":
            continue
        if not contains(applicant, applicant_filter):
            continue
        if not contains(item.customer, customer) or not contains(item.serial_no, application_no):
            continue
        display_type = _invoice_original_type(data.get("invoice_type"))
        if invoice_type and display_type != invoice_type:
            continue
        if not contains(data.get("invoice_title"), invoice_title) or not contains(data.get("invoice_no"), invoice_no):
            continue
        if invoice_status and item.status != invoice_status:
            continue
        if not contains(data.get("case_no"), case_no):
            continue
        invoice_date_text = str(data.get("invoice_date") or "").strip()
        parsed_invoice_date = None
        if invoice_date_text:
            try:
                parsed_invoice_date = date.fromisoformat(invoice_date_text[:10])
            except ValueError:
                pass
        if invoiced_from and (not parsed_invoice_date or parsed_invoice_date < invoiced_from):
            continue
        if invoiced_to and (not parsed_invoice_date or parsed_invoice_date > invoiced_to):
            continue
        result = _record_dict(item, allowed_fields)
        result_data = dict(result.get("data") or {})
        result_data.update({
            "invoice_type_display": display_type,
            "applicant": applicant,
            "application_date": str(data.get("application_date") or item.created_at),
            "extra_amount": float(data.get("extra_amount", 0) or 0) if "finance.amount" in allowed_fields else None,
        })
        result["data"] = result_data
        rows.append(result)
    return rows


def _case_fee_link_maps(fees: list[BusinessRecord]) -> tuple[set[int], dict[int, int]]:
    fee_ids = {item.id for item in fees}
    legacy_candidates: dict[int, set[int]] = {}
    for item in fees:
        data = item.data or {}
        for key in ("legacy_case_fee_id", "legacy_fee_id"):
            try:
                legacy_id = int(data.get(key) or 0)
            except (TypeError, ValueError):
                legacy_id = 0
            if legacy_id:
                legacy_candidates.setdefault(legacy_id, set()).add(item.id)
    return fee_ids, {
        legacy_id: next(iter(candidate_ids))
        for legacy_id, candidate_ids in legacy_candidates.items()
        if len(candidate_ids) == 1
    }


def _resolve_case_fee_link_id(
    link: dict,
    fee_ids: set[int],
    legacy_fee_ids: dict[int, int],
) -> int:
    for key in ("fee_record_id", "fee_id"):
        try:
            linked_id = int(link.get(key) or 0)
        except (AttributeError, TypeError, ValueError):
            linked_id = 0
        if linked_id in fee_ids:
            return linked_id
        if linked_id in legacy_fee_ids:
            return legacy_fee_ids[linked_id]
    for key in ("legacy_case_fee_id", "legacy_fee_id"):
        try:
            legacy_id = int(link.get(key) or 0)
        except (AttributeError, TypeError, ValueError):
            legacy_id = 0
        if legacy_id in legacy_fee_ids:
            return legacy_fee_ids[legacy_id]
    return 0


async def _invoice_case_fee_rows(
    identity: dict,
    db: AsyncSession,
    *,
    scope: str,
    case_no: str = "",
    court_case_no: str = "",
    notary_no: str = "",
    invoice_amount_from: float | None = None,
    invoice_amount_to: float | None = None,
    customer: str = "",
    paid_organization: str = "",
    invoice_status: str = "",
    invoice_from: date | None = None,
    invoice_to: date | None = None,
    hearing_lawyer: str = "",
    assistant: str = "",
    case_stages: str = "",
    paid_from: date | None = None,
    paid_to: date | None = None,
    fee_types: str = "",
    payer_name: str = "",
    cashed_from: date | None = None,
    cashed_to: date | None = None,
    ids: set[int] | None = None,
    include_all_fee_types: bool = False,
    scope_authorized_fee_ids: set[int] | None = None,
    force_amount_projection: bool = False,
) -> list[dict]:
    from app.core.cases import (
        _case_party_values,
    )
    from app.core.formatters import (
        _case_fee_date, _case_fee_display_type,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    from app.core.query_batches import _scalars_in_batches

    scope_conditions = await _record_scope_conditions(identity, db)
    fee_conditions = list(scope_conditions)
    if scope == "mine":
        fee_conditions.append(BusinessRecord.owner == identity["username"])
    if scope_authorized_fee_ids is not None:
        # Keep the full authorized fee context for ambiguous legacy links and
        # invoice allocation; only the SQL retrieval is partitioned.
        fees = await _scalars_in_batches(
            db, scope_authorized_fee_ids,
            lambda batch: select(BusinessRecord).where(
                BusinessRecord.module == "finance", BusinessRecord.id.in_(batch),
            ),
        )
        fees.sort(key=lambda item: (item.updated_at, item.id), reverse=True)
    else:
        fees = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "finance", *fee_conditions
        ).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all())
    if not include_all_fee_types:
        fees = [
            item for item in fees
            if str((item.data or {}).get("fee_type") or "")
            not in {"结算费用", "预损费用", "归档费用"}
        ]
    if ids is not None:
        fees = [item for item in fees if item.id in ids]
    if not fees:
        return []

    case_ids = {int((item.data or {}).get("case_id") or 0) for item in fees if (item.data or {}).get("case_id")}
    case_nos = {str((item.data or {}).get("case_no") or "") for item in fees if (item.data or {}).get("case_no")}
    cases_by_key = {}
    for column, values in ((BusinessRecord.id, case_ids), (BusinessRecord.serial_no, case_nos)):
        matching_cases = await _scalars_in_batches(
            db, values,
            lambda batch: select(BusinessRecord).where(
                BusinessRecord.module.in_(("case", "ipr_case")),
                column.in_(batch), *scope_conditions,
            ),
        )
        cases_by_key.update((item.id, item) for item in matching_cases)
    cases = list(cases_by_key.values())
    cases_by_id = {item.id: item for item in cases}
    cases_by_no = {item.serial_no: item for item in cases}

    fees_by_case: dict[str, list[BusinessRecord]] = {}
    for item in fees:
        data = item.data or {}
        linked_case = cases_by_id.get(int(data.get("case_id") or 0)) or cases_by_no.get(str(data.get("case_no") or ""))
        linked_no = linked_case.serial_no if linked_case else str(data.get("case_no") or "")
        if linked_no:
            fees_by_case.setdefault(linked_no, []).append(item)

    invoices = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "invoice", *scope_conditions
    ).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all())
    invoice_by_fee: dict[int, list[tuple[BusinessRecord, float]]] = {}
    fee_ids, legacy_fee_ids = _case_fee_link_maps(fees)
    fees_by_id = {item.id: item for item in fees}
    for invoice in invoices:
        data = invoice.data or {}
        explicit_ids = []
        raw_case_fee_ids = list(data.get("case_fee_ids") or [])
        has_explicit_link = bool(raw_case_fee_ids or data.get("case_fee_id"))
        for value in raw_case_fee_ids:
            try:
                fee_id = int(value)
            except (TypeError, ValueError):
                continue
            if fee_id in fee_ids and fee_id not in explicit_ids:
                explicit_ids.append(fee_id)
        if not explicit_ids and data.get("case_fee_id"):
            try:
                fee_id = int(data.get("case_fee_id"))
                if fee_id in fee_ids:
                    explicit_ids = [fee_id]
            except (TypeError, ValueError):
                pass
        if not explicit_ids and not has_explicit_link:
            candidates = fees_by_case.get(str(data.get("case_no") or ""), [])
            if len(candidates) == 1:
                explicit_ids = [candidates[0].id]
        if not explicit_ids:
            continue
        allocation_map: dict[int, float] = {}
        for allocation in data.get("case_fee_allocations") or []:
            try:
                allocation_map[int(allocation.get("fee_id"))] = float(allocation.get("amount") or 0)
            except (AttributeError, TypeError, ValueError):
                continue
        invoice_amount = float(data.get("amount") or 0)
        if not allocation_map:
            if len(explicit_ids) == 1:
                allocation_map[explicit_ids[0]] = invoice_amount
            else:
                weights = [abs(float((next(item for item in fees if item.id == fee_id).data or {}).get("amount") or 0)) for fee_id in explicit_ids]
                weight_total = sum(weights) or float(len(explicit_ids))
                allocated = 0.0
                for index, fee_id in enumerate(explicit_ids):
                    amount = invoice_amount - allocated if index == len(explicit_ids) - 1 else round(invoice_amount * (weights[index] or 1) / weight_total, 2)
                    allocation_map[fee_id] = amount
                    allocated += amount
        for fee_id in explicit_ids:
            invoice_by_fee.setdefault(fee_id, []).append((invoice, float(allocation_map.get(fee_id, 0))))

    transactions = await _scalars_in_batches(
        db, fee_ids,
        lambda batch: select(FinanceTransaction).where(
            FinanceTransaction.finance_record_id.in_(batch),
        ),
    )
    transactions.sort(key=lambda item: (item.transaction_date, item.id), reverse=True)
    payments_by_fee: dict[int, list[FinanceTransaction]] = {}
    for transaction in transactions:
        if transaction.transaction_type == "付款" and transaction.finance_record_id:
            payments_by_fee.setdefault(transaction.finance_record_id, []).append(transaction)

    incoming = list((await db.scalars(select(IncomingPayment).order_by(
        IncomingPayment.received_date.desc(), IncomingPayment.id.desc()
    ))).all())
    receipts_by_fee: dict[int, list[tuple[IncomingPayment, float]]] = {}
    for payment in incoming:
        for allocation in payment.allocations or []:
            if not isinstance(allocation, dict):
                continue
            allocation_case_no = str(allocation.get("case_no") or "").strip()
            linked_nested = False
            for settlement_item in allocation.get("settlement_items") or []:
                if not isinstance(settlement_item, dict):
                    continue
                nested_fee_id = _resolve_case_fee_link_id(settlement_item, fee_ids, legacy_fee_ids)
                linked_fee = fees_by_id.get(nested_fee_id)
                linked_case_no = str(((linked_fee.data or {}) if linked_fee else {}).get("case_no") or "").strip()
                if nested_fee_id in fee_ids and (not allocation_case_no or allocation_case_no == linked_case_no):
                    nested_amount = float(settlement_item.get("amount") or settlement_item.get("settlement_amount") or 0)
                    receipts_by_fee.setdefault(nested_fee_id, []).append((payment, nested_amount))
                    linked_nested = True
            if linked_nested:
                continue
            fee_id = 0
            fee_id = _resolve_case_fee_link_id(allocation, fee_ids, legacy_fee_ids)
            if not fee_id:
                try:
                    fee_id = int(allocation.get("finance_record_id") or 0)
                except (AttributeError, TypeError, ValueError):
                    pass
            if fee_id not in fee_ids:
                candidates = fees_by_case.get(str(allocation.get("case_no") or ""), []) if isinstance(allocation, dict) else []
                if len(candidates) == 1:
                    fee_id = candidates[0].id
            linked_fee = fees_by_id.get(fee_id)
            linked_case_no = str(((linked_fee.data or {}) if linked_fee else {}).get("case_no") or "").strip()
            if fee_id in fee_ids and (not allocation_case_no or allocation_case_no == linked_case_no):
                receipts_by_fee.setdefault(fee_id, []).append((payment, float(allocation.get("amount") or 0)))

    refund_scope_conditions = [] if scope_authorized_fee_ids is not None else scope_conditions
    refunds = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "refund", *refund_scope_conditions
    ).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all())
    refunds_by_fee: dict[int, list[BusinessRecord]] = {}
    official_by_case: dict[str, list[BusinessRecord]] = {}
    fee_by_document_no: dict[str, BusinessRecord] = {}
    for fee in fees:
        fee_data = fee.data or {}
        if str(fee_data.get("fee_type") or "") == "官方费用":
            official_by_case.setdefault(str(fee_data.get("case_no") or ""), []).append(fee)
        document_no = str(fee_data.get("document_no") or "").strip()
        if document_no:
            fee_by_document_no[document_no] = fee
    for refund in refunds:
        refund_data = refund.data or {}
        linked_fee: BusinessRecord | None = None
        try:
            linked_fee_id = int(refund_data.get("fee_record_id") or 0)
        except (TypeError, ValueError):
            linked_fee_id = 0
        if linked_fee_id in fee_ids:
            linked_fee = next((fee for fee in fees if fee.id == linked_fee_id), None)
        if linked_fee is None:
            linked_fee = fee_by_document_no.get(str(refund_data.get("original_payment_no") or "").strip())
        if linked_fee is None:
            candidates = official_by_case.get(str(refund_data.get("case_no") or ""), [])
            if len(candidates) == 1:
                linked_fee = candidates[0]
        if linked_fee:
            refunds_by_fee.setdefault(linked_fee.id, []).append(refund)

    allowed_fields = await _allowed_field_keys(identity, db)
    # The receivable projection exposes only contract-level aggregates that
    # the caller is already authorized to view, not the underlying finance
    # record.  It therefore needs the linked transaction totals even when the
    # finance module's raw amount field is hidden for that role.
    show_amount = force_amount_projection or "finance.amount" in allowed_fields
    selected_stages = {value.strip() for value in case_stages.split(",") if value.strip()}
    selected_types = {value.strip() for value in fee_types.split(",") if value.strip()}
    normalized_types = {"代理费" if value == "律师代理费" else "官方费用" if value == "官费" else value for value in selected_types}

    def contains(value: object, needle: str) -> bool:
        return not needle.strip() or needle.strip().casefold() in str(value or "").casefold()

    rows: list[dict] = []
    for item in fees:
        data = item.data or {}
        linked_case = cases_by_id.get(int(data.get("case_id") or 0)) or cases_by_no.get(str(data.get("case_no") or ""))
        case_data = (linked_case.data or {}) if linked_case else {}
        linked_invoices = [
            pair for pair in invoice_by_fee.get(item.id, [])
            if pair[0].status not in INVOICE_RELEASED_STATUSES
        ]
        invoiced_amount = round(sum(amount for _, amount in linked_invoices), 2)
        latest_invoice = linked_invoices[0][0] if linked_invoices else None
        latest_invoice_data = (latest_invoice.data or {}) if latest_invoice else {}
        invoice_date = _case_fee_date(latest_invoice_data.get("invoice_date"))
        payments = payments_by_fee.get(item.id, [])
        transaction_paid_amount = round(sum(float(tx.amount or 0) for tx in payments), 2)
        paid_amount = max(transaction_paid_amount, round(float(data.get("paid_amount") or 0), 2))
        paid_date = payments[0].transaction_date if payments else _case_fee_date(data.get("paid_date") or data.get("payment_date"))
        receipts = receipts_by_fee.get(item.id, [])
        cashed_amount = round(sum(amount for _, amount in receipts), 2)
        latest_receipt = receipts[0][0] if receipts else None
        cashed_date = latest_receipt.received_date if latest_receipt else _case_fee_date(data.get("cashed_date") or data.get("receipt_date"))
        received_payer = latest_receipt.payer_name if latest_receipt else str(data.get("received_payer_name") or data.get("payer_name") or "")
        linked_refunds = refunds_by_fee.get(item.id, [])
        refund_requested_amount = round(sum(float((refund.data or {}).get("amount") or 0) for refund in linked_refunds if refund.status not in {"已驳回", "已作废"}), 2)
        refunded_amount = round(sum(float((refund.data or {}).get("amount") or 0) for refund in linked_refunds if refund.status == "已退款"), 2)
        fee_amount = float(data.get("amount") or 0)
        display_type = _case_fee_display_type(item)
        base_type = str(data.get("fee_type") or "")
        has_issued_invoice = any(invoice.status == "已开票" for invoice, _ in linked_invoices)
        has_active_application = bool(linked_invoices)
        display_status = "已开票" if has_issued_invoice else ("已申请" if has_active_application else "未开票")
        remaining_invoice_amount = round(max(fee_amount - invoiced_amount, 0), 2)
        if invoice_status == "未开票" and has_active_application:
            continue
        if invoice_status == "已开票" and not has_issued_invoice:
            continue
        case_stage = str(data.get("case_stage") or case_data.get("case_stage") or (linked_case.status if linked_case else ""))
        assistant_name = str(data.get("assistant") or data.get("lawyer_assistant") or case_data.get("assistant") or case_data.get("lawyer_assistant") or "")
        hearing_name = str(data.get("hearing_lawyer") or case_data.get("hearing_lawyer") or case_data.get("court_lawyer") or "")
        court_no = str(data.get("court_case_no") or case_data.get("court_case_no") or case_data.get("first_instance_case_no") or case_data.get("official_no") or "")
        certificate_no = str(data.get("certificate_no") or data.get("notary_no") or case_data.get("certificate_no") or case_data.get("notary_no") or "")
        court_name = str(data.get("court_name") or data.get("court") or case_data.get("court_name") or case_data.get("first_instance_court") or "")
        paid_org = str(data.get("paid_organization") or data.get("payee") or court_name)
        display_payment_status = str(data.get("payment_status") or "").strip()
        if not display_payment_status:
            if str(data.get("writeoff_status") or "") == "待核销":
                display_payment_status = "待核销"
            else:
                display_payment_status = {
                    "草稿": "创建待提交",
                    "待审批": "待审批",
                    "已审批": "待付款",
                    "部分付款": "待付款",
                    "已付款": "已付款",
                    "已退回": "已驳回",
                    "已驳回": "已驳回",
                    "已拒绝": "已驳回",
                    "已作废": "已作废",
                }.get(item.status, item.status)
        if not contains(data.get("case_no") or (linked_case.serial_no if linked_case else ""), case_no):
            continue
        if not contains(court_no, court_case_no) or not contains(certificate_no, notary_no):
            continue
        if invoice_amount_from is not None and invoiced_amount < invoice_amount_from:
            continue
        if invoice_amount_to is not None and invoiced_amount > invoice_amount_to:
            continue
        if not contains(item.customer or (linked_case.customer if linked_case else ""), customer) or not contains(paid_org, paid_organization):
            continue
        if invoice_status and display_status != invoice_status:
            continue
        if invoice_from and (not invoice_date or invoice_date < invoice_from):
            continue
        if invoice_to and (not invoice_date or invoice_date > invoice_to):
            continue
        if not contains(hearing_name, hearing_lawyer) or not contains(assistant_name, assistant):
            continue
        if selected_stages and case_stage not in selected_stages:
            continue
        if paid_from and (not paid_date or paid_date < paid_from):
            continue
        if paid_to and (not paid_date or paid_date > paid_to):
            continue
        if normalized_types and base_type not in normalized_types and display_type not in selected_types:
            continue
        if not contains(received_payer, payer_name):
            continue
        if cashed_from and (not cashed_date or cashed_date < cashed_from):
            continue
        if cashed_to and (not cashed_date or cashed_date > cashed_to):
            continue
        result = _record_dict(item, allowed_fields)
        result_data = dict(result.get("data") or {})
        plaintiff = "、".join(_case_party_values(case_data, CASE_PLAINTIFF_FIELDS))
        opponent = "、".join(_case_party_values(case_data, CASE_DEFENDANT_FIELDS))
        result_data.update({
            "case_id": linked_case.id if linked_case else data.get("case_id"),
            "case_no": linked_case.serial_no if linked_case else data.get("case_no", ""),
            "plaintiff": data.get("plaintiff") or plaintiff or (linked_case.customer if linked_case else item.customer),
            "opponent": data.get("opponent") or opponent,
            "case_stage": case_stage,
            "assistant": assistant_name,
            "hearing_lawyer": hearing_name,
            "court_case_no": court_no,
            "certificate_no": certificate_no,
            "fee_type": display_type,
            "base_fee_type": base_type,
            "amount": fee_amount if show_amount else None,
            "invoice_status": display_status,
            "invoice_date": invoice_date.isoformat() if invoice_date else "",
            "invoice_amount": invoiced_amount if show_amount else None,
            "remaining_invoice_amount": remaining_invoice_amount if show_amount else None,
            "invoice_no": latest_invoice_data.get("invoice_no", ""),
            "invoice_record_id": latest_invoice.id if latest_invoice else None,
            "cashed_date": cashed_date.isoformat() if cashed_date else "",
            "cashed_amount": cashed_amount if show_amount else None,
            "received_payer_name": received_payer,
            "paid_date": paid_date.isoformat() if paid_date else "",
            "paid_amount": paid_amount if show_amount else None,
            "refund_requested_amount": refund_requested_amount if show_amount else None,
            "refunded_amount": refunded_amount if show_amount else None,
            "court_name": court_name,
            "payment_status": display_payment_status,
            "paid_organization": paid_org,
            "contract_no": data.get("contract_no") or case_data.get("contract_no") or "",
        })
        result["data"] = result_data
        rows.append(result)
    return rows


async def _fee_query_rows(
    identity: dict, db: AsyncSession, *,
    scope: str = "company", unpaid_official: bool = False,
    case_no: str = "", court_case_no: str = "", notary_no: str = "",
    refund_amount_from: float | None = None, refund_amount_to: float | None = None,
    customer: str = "", paid_organization: str = "", payment_status: str = "",
    paid_from: date | None = None, paid_to: date | None = None,
    hearing_lawyer: str = "", assistant: str = "", case_stages: str = "",
    fee_types: str = "", ids: set[int] | None = None,
    scope_authorized_fee_ids: set[int] | None = None,
) -> list[dict]:
    rows = await _invoice_case_fee_rows(
        identity, db, scope=scope, case_no=case_no,
        court_case_no=court_case_no, notary_no=notary_no,
        invoice_amount_from=None, invoice_amount_to=None, customer=customer,
        paid_organization=paid_organization, invoice_status="",
        invoice_from=None, invoice_to=None, hearing_lawyer=hearing_lawyer,
        assistant=assistant, case_stages=case_stages, paid_from=paid_from,
        paid_to=paid_to, fee_types=fee_types, payer_name="",
        cashed_from=None, cashed_to=None, ids=ids, include_all_fee_types=True,
        scope_authorized_fee_ids=scope_authorized_fee_ids,
    )
    filtered: list[dict] = []
    for row in rows:
        data = row.get("data") or {}
        refund_amount = data.get("refund_requested_amount")
        if refund_amount_from is not None and (refund_amount is None or float(refund_amount) < refund_amount_from):
            continue
        if refund_amount_to is not None and (refund_amount is None or float(refund_amount) > refund_amount_to):
            continue
        if payment_status and str(data.get("payment_status") or "") != payment_status:
            continue
        if unpaid_official:
            base_type = str(data.get("base_fee_type") or "")
            display_type = str(data.get("fee_type") or "")
            amount_due = float(data.get("amount") or 0) - float(data.get("paid_amount") or 0)
            if (
                base_type != "官方费用"
                and "官费" not in display_type
                and "诉讼费" not in display_type
                and display_type not in {"保全费", "执行费"}
            ):
                continue
            if str(data.get("payment_status") or "") in {"已付款", "已驳回", "已作废"} or amount_due <= 0:
                continue
        filtered.append(row)
    return filtered


def _refund_case_fee_status(data: dict) -> tuple[str, str]:
    legacy = data.get("legacy_record") if isinstance(data.get("legacy_record"), dict) else {}
    raw = data.get("refund_status") or legacy.get("RefundStatus") or "R10"
    if isinstance(raw, (int, float)) or str(raw).strip().isdigit():
        code = f"R{int(raw)}"
    else:
        value = str(raw).strip()
        code = value.upper() if value.upper() in REFUND_CASE_FEE_STATUSES else REFUND_CASE_FEE_STATUS_BY_LABEL.get(value, "R10")
    label = str(data.get("refund_status_label") or REFUND_CASE_FEE_STATUSES.get(code) or raw).strip()
    return code, label


def _refund_case_fee_started_at(data: dict, status_code: str) -> str:
    legacy = data.get("legacy_record") if isinstance(data.get("legacy_record"), dict) else {}
    return str(
        data.get("refund_status_started_at")
        or data.get("refund_status_start_time")
        or legacy.get(f"RefundStatus{status_code.removeprefix('R')}StartTime")
        or data.get("created_at")
        or ""
    )


async def _refund_case_fee_authorized_ids(identity: dict, db: AsyncSession) -> set[int] | None:
    from app.core.permissions import (
        _case_personal_scope_condition, _identity_role_ids, _require_record_module_menu, _user_permission_payload,
    )
    await _require_record_module_menu("finance", identity, db, action="查看")
    if "admin" in _identity_role_ids(identity):
        return None
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if not user:
        raise HTTPException(status_code=401, detail="当前用户不存在")
    if (await _user_permission_payload(user, db))["data_scope"] == "全所数据":
        return None
    cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module.in_(("case", "ipr_case")),
        _case_personal_scope_condition(user.username),
    ))).all())
    case_ids = {item.id for item in cases}
    case_nos = {item.serial_no for item in cases if item.serial_no}
    if not case_ids and not case_nos:
        return set()
    conditions = []
    if case_ids:
        conditions.append(BusinessRecord.data["case_id"].as_integer().in_(case_ids))
    if case_nos:
        conditions.append(BusinessRecord.data["case_no"].as_string().in_(case_nos))
    return set((await db.scalars(select(BusinessRecord.id).where(
        BusinessRecord.module == "finance", or_(*conditions),
    ))).all())


async def _refund_case_fee_rows(
    identity: dict,
    db: AsyncSession,
    *,
    case_no: str = "",
    court_case_no: str = "",
    court_name: str = "",
    paid_from: date | None = None,
    paid_to: date | None = None,
    customer: str = "",
    paid_organization: str = "",
    refund_status: str = "",
    refund_amount_from: float | None = None,
    refund_amount_to: float | None = None,
    hearing_lawyer: str = "",
    assistant: str = "",
    case_stages: str = "",
    fee_types: str = "",
    ids: set[int] | None = None,
    pending_only: bool = True,
    include_not_required: bool = False,
) -> list[dict]:
    from app.core.legacy_sync import (
        _legacy_case_fee_projection,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    authorized_ids = await _refund_case_fee_authorized_ids(identity, db)
    selected_ids = ids
    if authorized_ids is not None:
        selected_ids = authorized_ids if selected_ids is None else selected_ids.intersection(authorized_ids)
    rows = await _fee_query_rows(
        identity, db, scope="company", case_no=case_no,
        court_case_no=court_case_no, refund_amount_from=None,
        refund_amount_to=None, customer=customer,
        paid_organization=paid_organization, paid_from=paid_from,
        paid_to=paid_to, hearing_lawyer=hearing_lawyer,
        assistant=assistant, case_stages=case_stages, fee_types=fee_types,
        ids=selected_ids, scope_authorized_fee_ids=authorized_ids,
    )
    fee_ids = {int(row["id"]) for row in rows}
    records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance", BusinessRecord.id.in_(fee_ids),
    ))).all()) if fee_ids else []
    records_by_id = {item.id: item for item in records}
    show_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    result: list[dict] = []
    for row in rows:
        item = records_by_id[int(row["id"])]
        raw_data = _legacy_case_fee_projection(item.data or {})
        data = dict(row.get("data") or {})
        requested = max(float(data.get("refund_requested_amount") or 0), float(raw_data.get("refund_requested_amount") or raw_data.get("refund_amount") or 0))
        refunded = max(float(data.get("refunded_amount") or 0), float(raw_data.get("refunded_amount") or 0))
        status_code, status_label = _refund_case_fee_status(raw_data)
        started_at = _refund_case_fee_started_at(raw_data, status_code) or str(item.created_at or "")
        try:
            progress_days = max((date.today() - date.fromisoformat(started_at[:10])).days, 0)
        except (TypeError, ValueError):
            progress_days = 0
        case_data = data.get("case_data") if isinstance(data.get("case_data"), dict) else {}
        data.update({
            "refund_requested_amount": requested if show_amount else None,
            "refunded_amount": refunded if show_amount else None,
            "refund_status": status_code,
            "refund_status_label": status_label,
            "refund_status_started_at": started_at,
            "refund_progress_days": progress_days,
            "plaintiff": data.get("plaintiff") or raw_data.get("plaintiff") or case_data.get("plaintiff") or row.get("customer") or "",
            "opponent": data.get("opponent") or raw_data.get("opponent") or case_data.get("opponent") or "",
            "court_name": data.get("court_name") or raw_data.get("court_name") or raw_data.get("court") or "",
            "created_at": str(item.created_at or ""),
        })
        if pending_only and requested <= refunded:
            continue
        if not include_not_required and status_code == "R100":
            continue
        expected_status = str(refund_status or "").strip()
        if expected_status and expected_status not in {status_code, status_label}:
            continue
        if court_name.strip() and court_name.strip().casefold() not in str(data.get("court_name") or "").casefold():
            continue
        if refund_amount_from is not None and requested < refund_amount_from:
            continue
        if refund_amount_to is not None and requested > refund_amount_to:
            continue
        row["data"] = data
        result.append(row)
    result.sort(key=lambda row: (str((row.get("data") or {}).get("refund_status_started_at") or ""), int(row["id"])))
    return result


async def _editable_refund_case_fees(ids: list[int], identity: dict, db: AsyncSession) -> list[BusinessRecord]:
    unique_ids = set(ids)
    rows = await _refund_case_fee_rows(identity, db, ids=unique_ids, pending_only=False, include_not_required=True)
    if len(rows) != len(unique_ids):
        raise HTTPException(status_code=422, detail="部分退费记录不存在或无权操作")
    return list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance", BusinessRecord.id.in_(unique_ids),
    ).order_by(BusinessRecord.id))).all())


async def _editable_invoice_application(invoice_id: int, identity: dict, db: AsyncSession) -> BusinessRecord:
    from app.core.permissions import (
        _require_record_owner_or_manager,
    )
    item = await db.get(BusinessRecord, invoice_id)
    if not item or item.module != "invoice":
        raise HTTPException(status_code=404, detail="发票申请不存在")
    await _require_record_owner_or_manager(item, identity, db)
    if item.status not in {"草稿", "已驳回"}:
        raise HTTPException(status_code=409, detail="仅草稿或已驳回发票申请可以修改")
    return item


def _refund_group(value: str) -> str:
    normalized = str(value or "").strip().casefold()
    if not normalized:
        return ""
    if normalized not in REFUND_GROUP_ALIASES:
        raise HTTPException(status_code=422, detail="退款业务组无效")
    return REFUND_GROUP_ALIASES[normalized]


async def _refund_query_rows(
    identity: dict,
    db: AsyncSession,
    *,
    status_filter: str = "",
    group: str = "",
    scope: str = "company",
    ids: set[int] | None = None,
) -> list[dict]:
    from app.core.permissions import (
        _record_scope_conditions, _refund_identity_department,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    if status_filter == "全部":
        status_filter = ""
    if status_filter and status_filter not in REFUND_LIST_STATUSES:
        raise HTTPException(status_code=422, detail="退款状态无效")
    if scope not in {"mine", "company"}:
        raise HTTPException(status_code=422, detail="退款数据范围无效")
    group_value = _refund_group(group)
    conditions = [BusinessRecord.module == "refund", *(await _record_scope_conditions(identity, db))]
    if scope == "mine":
        conditions.append(BusinessRecord.owner == identity["username"])
    else:
        conditions.append(BusinessRecord.department == await _refund_identity_department(identity, db))
    if ids is not None:
        conditions.append(BusinessRecord.id.in_(ids))
    if status_filter:
        conditions.append(BusinessRecord.status == status_filter)
    records = list((await db.scalars(select(BusinessRecord).where(*conditions).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all())
    allowed_fields = await _allowed_field_keys(identity, db)
    rows = []
    for item in records:
        data = item.data or {}
        item_group = str(data.get("group_id") or data.get("group") or "").strip().casefold()
        item_group = REFUND_GROUP_ALIASES.get(item_group, item_group)
        if group_value and item_group != group_value:
            continue
        row = _record_dict(item, allowed_fields)
        visible = dict(row.get("data") or {})
        visible.update({
            "case_no": data.get("case_no", ""),
            "court": data.get("court", ""),
            "original_payment_no": data.get("original_payment_no", ""),
            "amount": _round_fee_amount(float(data.get("amount") or 0)) if "finance.amount" in allowed_fields else None,
            "expected_date": data.get("expected_date", ""),
            "actual_date": data.get("actual_date", ""),
            "voucher_no": data.get("refund_voucher_no") or data.get("voucher_no", ""),
            "group_id": item_group,
        })
        row["data"] = visible
        rows.append(row)
    return rows


async def _refund_export_response(rows: list[dict], filename: str) -> Response:
    from app.core.system import (
        _excel_response,
    )
    headers = ["申请编号", "案号", "客户", "法院", "原缴费票号", "退款金额", "状态", "预计到账", "实际到账", "退款凭证号"]
    export_rows: list[list[object]] = []
    for row in rows:
        data = row.get("data") or {}
        export_rows.append([
            row.get("serial_no", ""), data.get("case_no", ""), row.get("customer", ""),
            data.get("court", ""), data.get("original_payment_no", ""), data.get("amount"),
            row.get("status", ""), data.get("expected_date", ""), data.get("actual_date", ""),
            data.get("voucher_no", ""),
        ])
    # The legacy CaseFeeController generates an Excel workbook and then serves
    # an .xls download.  Reuse the existing SpreadsheetML helper so refund
    # exports are a real, parseable workbook rather than CSV with an Excel name.
    return _excel_response(f"{filename}-{date.today()}.xls", headers, export_rows)


async def _refund_export_request(
    *, ids: str, selected_only: bool, status_filter: str, group: str, scope: str, identity: dict, db: AsyncSession,
) -> Response:
    from app.core.system import (
        _export_ids,
    )
    selected = set(_export_ids(ids)) if ids.strip() else None
    if selected_only and not selected:
        raise HTTPException(status_code=422, detail="请选择需要导出的退款记录")
    rows = await _refund_query_rows(identity, db, status_filter=status_filter, group=group, scope=scope, ids=selected)
    if selected is not None and len(rows) != len(selected):
        raise HTTPException(status_code=422, detail="部分退款记录不存在或无权导出")
    if not rows:
        raise HTTPException(status_code=422, detail="当前没有可导出的退款记录")
    return await _refund_export_response(rows, "诉讼费退款")


async def _finance_fee_readiness(item: BusinessRecord, identity: dict, db: AsyncSession) -> dict:
    from app.core.permissions import (
        _record_scope_conditions,
    )
    data = item.data or {}
    case_no = str(data.get("case_no", "")).strip()
    case_record = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "case", BusinessRecord.serial_no == case_no, *(await _record_scope_conditions(identity, db)))) if case_no else None
    case_data = (case_record.data or {}) if case_record else {}
    personnel = {
        "客户管理人": bool(case_data.get("customer_manager")),
        "开庭律师": bool(case_data.get("hearing_lawyer")),
        "经办律师": bool(case_data.get("handling_lawyers")),
        "律师助理/文书": bool(case_data.get("assistant")),
    }
    court = {
        "关联案件": bool(case_record),
        "法院名称": bool(data.get("court") or case_data.get("court")),
        "缴费通知文号": bool(data.get("document_no")),
    }
    attachment_categories = set((await db.scalars(select(FileAttachment.category).where(FileAttachment.record_id == case_record.id))).all()) if case_record else set()
    document = {"法院缴费通知书": bool(data.get("document_no") or attachment_categories.intersection({"法院缴费通知书", "缴费通知书"}))}
    missing = [f"人员要素：{name}" for name, ready in personnel.items() if not ready]
    missing.extend(f"法院要素：{name}" for name, ready in court.items() if not ready)
    missing.extend(f"文档要素：{name}" for name, ready in document.items() if not ready)
    return {"case_id": case_record.id if case_record else None, "case_no": case_no, "personnel": personnel, "court": court, "document": document, "ready": not missing, "missing": missing}


def _internal_fee_payment_status(item: BusinessRecord, paid_amount: float) -> str:
    data = item.data or {}
    amount = float(data.get("amount", 0) or 0)
    explicit = str(data.get("payment_status", "")).strip()
    if explicit in {"已付", "已付款"} or item.status == "已付款" or (amount > 0 and paid_amount >= amount):
        return "已付"
    return "未付"


def _internal_fee_row(item: BusinessRecord, case_record: BusinessRecord | None, paid_amount: float, allowed_fields: set[str]) -> dict:
    from app.core.system import (
        _record_dict,
    )
    data = item.data or {}
    case_data = (case_record.data or {}) if case_record else {}
    result = _record_dict(item, allowed_fields)
    visible_data = dict(result.get("data") or {})
    enriched = {
        **visible_data,
        "case_no": data.get("case_no") or (case_record.serial_no if case_record else ""),
        "case_stage": data.get("case_stage") or case_data.get("case_stage") or (case_record.status if case_record else ""),
        "plaintiff": data.get("plaintiff") or case_data.get("plaintiff") or case_data.get("appellant_names") or (case_record.customer if case_record else ""),
        "defendant": data.get("defendant") or case_data.get("defendant") or case_data.get("appellee_names") or case_data.get("opponent") or "",
        "handling_lawyer": data.get("handling_lawyer") or data.get("handler") or case_data.get("handling_lawyer") or case_data.get("case_lawyer") or ",".join(case_data.get("handling_lawyers") or []) or "",
        "lawyer_assistant": data.get("lawyer_assistant") or data.get("assistant") or case_data.get("lawyer_assistant") or case_data.get("assistant") or "",
        "case_source": data.get("case_source") or data.get("source_person") or case_data.get("case_source") or case_data.get("business_owner") or (case_record.owner if case_record else ""),
        "investigator": data.get("investigator") or case_data.get("investigator") or "",
        "archive_date": data.get("archive_date") or data.get("audited_time") or case_data.get("archive_date") or case_data.get("audited_time") or "",
        "application_date": data.get("application_date") or item.created_at,
        "internal_fee_type": data.get("commission_type") or data.get("fee_type_name") or item.title or data.get("fee_type") or "",
        "payee": data.get("payee") or "",
        "payment_status": _internal_fee_payment_status(item, paid_amount),
    }
    if "finance.amount" in allowed_fields:
        enriched["paid_amount"] = round(paid_amount, 2)
    result["data"] = enriched
    return result


async def _internal_fee_rows(
    identity: dict,
    db: AsyncSession,
    *,
    scope: str,
    case_no: str,
    handling_lawyer: str,
    assistant: str,
    source_person: str,
    customer: str,
    customer_manager: str,
    investigator: str,
    payment_status: str,
    paid_from: date | None,
    paid_to: date | None,
    payee: str,
    case_stages: str,
    fee_types: str,
    ids: set[int] | None = None,
) -> list[dict]:
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    scope_conditions = await _record_scope_conditions(identity, db)
    fees = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "finance", *scope_conditions).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all())
    fees = [item for item in fees if (item.data or {}).get("fee_type") == "内部费用" and item.status != "已删除"]
    if ids is not None:
        fees = [item for item in fees if item.id in ids]
    case_records = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "case", *scope_conditions))).all())
    cases_by_id = {item.id: item for item in case_records}
    cases_by_no = {item.serial_no: item for item in case_records}
    fee_ids = [item.id for item in fees]
    transactions = list((await db.scalars(select(FinanceTransaction).where(FinanceTransaction.finance_record_id.in_(fee_ids)))).all()) if fee_ids else []
    paid_by_fee: dict[int, float] = {}
    paid_dates_by_fee: dict[int, list[date]] = {}
    for transaction in transactions:
        if transaction.transaction_type != "付款" or not transaction.finance_record_id:
            continue
        paid_by_fee[transaction.finance_record_id] = paid_by_fee.get(transaction.finance_record_id, 0.0) + float(transaction.amount or 0)
        paid_dates_by_fee.setdefault(transaction.finance_record_id, []).append(transaction.transaction_date)
    allowed_fields = await _allowed_field_keys(identity, db)
    selected_stages = {value.strip() for value in case_stages.split(",") if value.strip()}
    selected_types = {value.strip() for value in fee_types.split(",") if value.strip()}
    personal_names = {str(identity.get("username", "")).strip(), str(identity.get("display_name", "")).strip()} - {""}

    def contains(value: object, needle: str) -> bool:
        return not needle.strip() or needle.strip().casefold() in str(value or "").casefold()

    rows: list[dict] = []
    for item in fees:
        data = item.data or {}
        linked_case = cases_by_id.get(int(data.get("case_id") or 0)) or cases_by_no.get(str(data.get("case_no") or ""))
        row = _internal_fee_row(item, linked_case, paid_by_fee.get(item.id, 0.0), allowed_fields)
        row_data = row["data"]
        paid_dates = list(paid_dates_by_fee.get(item.id, []))
        stored_paid_date = str(data.get("paid_date") or data.get("payment_date") or "").strip()
        if stored_paid_date:
            try:
                paid_dates.append(date.fromisoformat(stored_paid_date[:10]))
            except ValueError:
                pass
        row_data["paid_date"] = max(paid_dates).isoformat() if paid_dates else stored_paid_date
        payment_object = str(row_data.get("payee") or "").strip()
        if scope == "mine" and payment_object not in personal_names:
            continue
        if payee.strip() and not contains(payment_object, payee):
            continue
        if not contains(row_data.get("case_no"), case_no) or not contains(row_data.get("handling_lawyer"), handling_lawyer):
            continue
        if not contains(row_data.get("lawyer_assistant"), assistant) or not contains(row_data.get("case_source"), source_person):
            continue
        if not contains(item.customer, customer) or not contains((linked_case.data or {}).get("customer_manager") if linked_case else data.get("customer_manager"), customer_manager):
            continue
        if not contains(row_data.get("investigator"), investigator):
            continue
        if payment_status and row_data.get("payment_status") != payment_status:
            continue
        if paid_from and not any(value >= paid_from for value in paid_dates):
            continue
        if paid_to and not any(value <= paid_to for value in paid_dates):
            continue
        if selected_stages and str(row_data.get("case_stage") or "") not in selected_stages:
            continue
        if selected_types and str(row_data.get("internal_fee_type") or "") not in selected_types:
            continue
        rows.append(row)
    return rows


def _settlement_fee_kind(fee_type: str) -> str:
    normalized = fee_type.strip()
    normalized_lower = normalized.casefold()
    if "代理" in normalized or "agency" in normalized_lower:
        return "agency"
    if (
        any(token in normalized for token in ("官费", "官方", "诉讼", "公证", "保全", "鉴定", "公告"))
        or any(token in normalized for token in ("\u5b98\u8d39", "\u5b98\u65b9", "\u8bc9\u8bbc", "\u6cd5\u9662", "\u516c\u8bc1", "\u4fdd\u5168", "\u9274\u5b9a", "\u516c\u544a"))
        or any(token in normalized_lower for token in ("official", "court", "notary", "appraisal"))
    ):
        return "official"
    return "other"


async def _general_settlement_rows(
    identity: dict,
    db: AsyncSession,
    *,
    customer: str = "",
    case_no: str = "",
    received_from: date | None = None,
    received_to: date | None = None,
    payer: str = "",
    payment_method: str = "",
    case_customer: str = "",
    hearing_lawyer: str = "",
    assistant: str = "",
    customer_manager: str = "",
    source_person: str = "",
    receipt_ids: set[int] | None = None,
    include_active_receipts: bool = False,
) -> list[dict]:
    """Build the original settlement candidates from bank receipts and their case allocations."""
    from app.core.formatters import (
        _case_fee_display_type,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    payments = list((await db.scalars(select(IncomingPayment).order_by(
        IncomingPayment.received_date.asc(), IncomingPayment.id.asc()
    ))).all())
    if receipt_ids is not None:
        payments = [item for item in payments if item.id in receipt_ids]

    allocations = [allocation for payment in payments for allocation in (payment.allocations or [])]
    case_ids = {int(row.get("case_id") or 0) for row in allocations if row.get("case_id")}
    case_nos = {str(row.get("case_no") or "").strip() for row in allocations if str(row.get("case_no") or "").strip()}
    cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case",
        or_(BusinessRecord.id.in_(case_ids), BusinessRecord.serial_no.in_(case_nos)),
        *(await _record_scope_conditions(identity, db)),
    ))).all()) if case_ids or case_nos else []
    cases_by_id = {item.id: item for item in cases}
    cases_by_no = {item.serial_no: item for item in cases}

    visible_case_ids = set(cases_by_id)
    visible_case_nos = set(cases_by_no)
    fee_records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance",
        *(await _record_scope_conditions(identity, db)),
    ).order_by(BusinessRecord.id.asc()))).all())
    fees_by_id = {item.id: item for item in fee_records}
    fees_by_case: dict[str, list[BusinessRecord]] = {}
    for fee in fee_records:
        data = fee.data or {}
        fee_case_id = int(data.get("case_id") or 0)
        fee_case_no = str(data.get("case_no") or "").strip()
        if fee_case_id not in visible_case_ids and fee_case_no not in visible_case_nos:
            continue
        fee_type = _case_fee_display_type(fee)
        if not fee_type or fee_type in {"内部费用", "结算费用", "归档费用", "预损费用"}:
            continue
        key = str(fee_case_id or fee_case_no)
        fees_by_case.setdefault(key, []).append(fee)

    settlement_records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance_settlement"
    ).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()))).all())
    inactive_statuses = {"已拒绝", "已驳回", "已退回", "已撤回", "已作废"}
    active_receipt_ids = {
        int((record.data or {}).get("receipt_id") or 0)
        for record in settlement_records
        if record.status not in inactive_statuses
    }
    rejection_by_receipt: dict[int, str] = {}
    for record in settlement_records:
        receipt_id = int((record.data or {}).get("receipt_id") or 0)
        if receipt_id and record.status in inactive_statuses and receipt_id not in rejection_by_receipt:
            rejection_by_receipt[receipt_id] = str((record.data or {}).get("review_comment") or record.description or "")

    consumed_by_fee: dict[int, float] = {}
    rows: list[dict] = []
    can_view_amount = "finance.amount" in await _allowed_field_keys(identity, db)

    def contains(value: object, needle: str) -> bool:
        return not needle.strip() or needle.strip().casefold() in str(value or "").casefold()

    for payment in payments:
        payment_allocations = list(payment.allocations or [])
        if not payment_allocations or (not include_active_receipts and payment.id in active_receipt_ids):
            continue
        details: list[dict] = []
        for allocation in payment_allocations:
            linked_case = cases_by_id.get(int(allocation.get("case_id") or 0)) or cases_by_no.get(str(allocation.get("case_no") or ""))
            if not linked_case and identity.get("role") not in {"admin", "auditor"}:
                continue
            case_data = (linked_case.data or {}) if linked_case else {}
            remaining = _round_fee_amount(float(allocation.get("amount") or 0))
            explicit_items = list(allocation.get("settlement_items") or [])
            if explicit_items:
                for explicit in explicit_items:
                    fee_type = str(explicit.get("fee_type") or "其他费用")
                    current_amount = _round_fee_amount(float(explicit.get("amount") or explicit.get("settlement_amount") or 0))
                    explicit_fee = fees_by_id.get(int(explicit.get("fee_record_id") or 0))
                    explicit_fee_total = abs(_round_fee_amount(float(((explicit_fee.data or {}) if explicit_fee else {}).get("amount") or current_amount)))
                    details.append({
                        "fee_id": explicit.get("fee_record_id"),
                        "case_id": linked_case.id if linked_case else allocation.get("case_id"),
                        "case_no": linked_case.serial_no if linked_case else allocation.get("case_no", ""),
                        "case_type": case_data.get("case_type") or case_data.get("case_kind") or case_data.get("type") or "",
                        "case_name": linked_case.title if linked_case else "",
                        "case_stage": (case_data.get("case_stage") or linked_case.status) if linked_case else "",
                        "fee_type": fee_type,
                        "fee_total_amount": explicit_fee_total,
                        "fee_allocated_amount": current_amount,
                        "current_amount": current_amount,
                        "allocated_at": allocation.get("allocated_at", ""),
                        "settlement_amount": _round_fee_amount(float(explicit.get("settlement_amount") or 0)),
                        "archive_fee": _round_fee_amount(float(explicit.get("archive_fee") or 0)),
                        "customer": linked_case.customer if linked_case else payment.claimed_customer,
                        "handling_lawyer": case_data.get("handling_lawyers") or case_data.get("handling_lawyer") or linked_case.owner if linked_case else "",
                        "assistant": case_data.get("assistant") or case_data.get("lawyer_assistant", ""),
                        "contract_no": allocation.get("contract_no", ""),
                        "kind": _settlement_fee_kind(fee_type),
                    })
                continue
            case_key = str((linked_case.id if linked_case else 0) or allocation.get("case_no") or "")
            candidates = fees_by_case.get(case_key, [])
            for fee in candidates:
                if remaining <= 0.001:
                    break
                fee_data = fee.data or {}
                fee_total = abs(_round_fee_amount(float(fee_data.get("amount") or 0)))
                available = max(_round_fee_amount(fee_total - consumed_by_fee.get(fee.id, 0)), 0)
                current_amount = min(remaining, available)
                if current_amount <= 0.001:
                    continue
                fee_type = _case_fee_display_type(fee)
                kind = _settlement_fee_kind(fee_type)
                explicit_total = fee_data.get("settlement_amount")
                if explicit_total is not None and fee_total:
                    settlement_amount = _round_fee_amount(float(explicit_total) * current_amount / fee_total)
                elif kind == "agency":
                    settlement_amount = _round_fee_amount(current_amount * 0.8)
                else:
                    settlement_amount = current_amount
                explicit_archive = fee_data.get("archive_fee")
                if explicit_archive is not None and fee_total:
                    archive_fee = _round_fee_amount(float(explicit_archive) * current_amount / fee_total)
                elif kind == "agency" and "退费" not in fee_type:
                    archive_fee = _round_fee_amount(settlement_amount * 0.1)
                else:
                    archive_fee = 0.0
                details.append({
                    "fee_id": fee.id,
                    "case_id": linked_case.id if linked_case else allocation.get("case_id"),
                    "case_no": linked_case.serial_no if linked_case else allocation.get("case_no", ""),
                    "case_type": case_data.get("case_type") or case_data.get("case_kind") or case_data.get("type") or "",
                    "case_name": linked_case.title if linked_case else "",
                    "case_stage": (case_data.get("case_stage") or linked_case.status) if linked_case else "",
                    "fee_type": fee_type,
                    "fee_total_amount": fee_total,
                    "fee_allocated_amount": current_amount,
                    "current_amount": current_amount,
                    "allocated_at": allocation.get("allocated_at", ""),
                    "settlement_amount": settlement_amount,
                    "archive_fee": archive_fee,
                    "customer": linked_case.customer if linked_case else payment.claimed_customer,
                    "handling_lawyer": case_data.get("handling_lawyers") or case_data.get("handling_lawyer") or linked_case.owner if linked_case else "",
                    "assistant": case_data.get("assistant") or case_data.get("lawyer_assistant", ""),
                    "contract_no": allocation.get("contract_no", ""),
                    "kind": kind,
                })
                consumed_by_fee[fee.id] = _round_fee_amount(consumed_by_fee.get(fee.id, 0) + current_amount)
                remaining = _round_fee_amount(remaining - current_amount)
            if remaining > 0.001:
                details.append({
                    "fee_id": None,
                    "case_id": linked_case.id if linked_case else allocation.get("case_id"),
                    "case_no": linked_case.serial_no if linked_case else allocation.get("case_no", ""),
                    "case_type": case_data.get("case_type") or case_data.get("case_kind") or case_data.get("type") or "",
                    "case_name": linked_case.title if linked_case else "",
                    "case_stage": (case_data.get("case_stage") or linked_case.status) if linked_case else "",
                    "fee_type": "其他费用",
                    "fee_total_amount": remaining,
                    "fee_allocated_amount": remaining,
                    "current_amount": remaining,
                    "allocated_at": allocation.get("allocated_at", ""),
                    "settlement_amount": remaining,
                    "archive_fee": 0.0,
                    "customer": linked_case.customer if linked_case else payment.claimed_customer,
                    "handling_lawyer": case_data.get("handling_lawyers") or case_data.get("handling_lawyer") or linked_case.owner if linked_case else "",
                    "assistant": case_data.get("assistant") or case_data.get("lawyer_assistant", ""),
                    "contract_no": allocation.get("contract_no", ""),
                    "kind": "other",
                })
        if not details:
            continue
        for detail_index, detail in enumerate(details, start=1):
            detail["detail_id"] = f"{payment.id}-{detail_index}"
        detail_cases = [cases_by_id.get(int(item.get("case_id") or 0)) for item in details]
        detail_cases = [item for item in detail_cases if item]
        case_data_rows = [item.data or {} for item in detail_cases]
        row_customer = payment.claimed_customer or (details[0].get("customer") if details else "")
        row_case_customers = "、".join(dict.fromkeys(str(item.get("customer") or "") for item in details if item.get("customer")))
        row_case_nos = "、".join(dict.fromkeys(str(item.get("case_no") or "") for item in details if item.get("case_no")))
        row_hearing = "、".join(dict.fromkeys(str(data.get("hearing_lawyer") or "") for data in case_data_rows if data.get("hearing_lawyer")))
        row_assistant = "、".join(dict.fromkeys(str(data.get("assistant") or data.get("lawyer_assistant") or "") for data in case_data_rows if data.get("assistant") or data.get("lawyer_assistant")))
        row_manager = "、".join(dict.fromkeys(str(data.get("customer_manager") or "") for data in case_data_rows if data.get("customer_manager")))
        row_source = "、".join(dict.fromkeys(str(data.get("source_person") or data.get("case_source") or "") for data in case_data_rows if data.get("source_person") or data.get("case_source")))
        row_method = "、".join(dict.fromkeys(str(item.get("payment_method") or "") for item in payment_allocations if item.get("payment_method")))
        if not contains(row_customer, customer) or not contains(row_case_nos, case_no):
            continue
        if received_from and payment.received_date < received_from:
            continue
        if received_to and payment.received_date > received_to:
            continue
        if not contains(payment.payer_name, payer) or not contains(row_method, payment_method):
            continue
        if not contains(row_case_customers, case_customer) or not contains(row_hearing, hearing_lawyer):
            continue
        if not contains(row_assistant, assistant) or not contains(row_manager, customer_manager) or not contains(row_source, source_person):
            continue
        assigned = _round_fee_amount(sum(float(item["current_amount"]) for item in details))
        official = _round_fee_amount(sum(float(item["current_amount"]) for item in details if item["kind"] == "official"))
        agency = _round_fee_amount(sum(float(item["current_amount"]) for item in details if item["kind"] == "agency"))
        other = _round_fee_amount(sum(float(item["current_amount"]) for item in details if item["kind"] == "other"))
        agency_settlement = _round_fee_amount(sum(float(item["settlement_amount"]) for item in details if item["kind"] == "agency"))
        archive_fee = _round_fee_amount(sum(float(item["archive_fee"]) for item in details))
        actual = _round_fee_amount(sum(float(item["settlement_amount"]) for item in details) - archive_fee)
        rows.append({
            "id": payment.id,
            "serial_no": payment.receipt_no,
            "title": f"{row_customer}待结算回款",
            "customer": row_customer,
            "status": "待结算",
            "owner": payment.claimant or payment.operator,
            "data": {
                "receipt_id": payment.id,
                "receipt_no": payment.receipt_no,
                "customer_manager": row_manager,
                "payer_name": payment.payer_name,
                "received_date": str(payment.received_date),
                "receipt_amount": float(payment.amount) if can_view_amount else None,
                "allocated_amount": assigned if can_view_amount else None,
                "remaining_amount": max(_round_fee_amount(float(payment.amount) - assigned), 0) if can_view_amount else None,
                "assigned_official_fee": official if can_view_amount else None,
                "assigned_agency_fee": agency if can_view_amount else None,
                "assigned_other_fee": other if can_view_amount else None,
                "agency_settlement_amount": agency_settlement if can_view_amount else None,
                "archive_fee": archive_fee if can_view_amount else None,
                "actual_settlement_amount": actual if can_view_amount else None,
                "payment_method": row_method,
                "bank_remark": payment.remark or payment.bank_reference,
                "rejection_comment": rejection_by_receipt.get(payment.id, ""),
                "case_nos": row_case_nos,
                "case_customers": row_case_customers,
                "hearing_lawyer": row_hearing,
                "assistant": row_assistant,
                "source_person": row_source,
                "allocation_details": details if can_view_amount else [{**detail, "fee_total_amount": None, "fee_allocated_amount": None, "current_amount": None, "settlement_amount": None, "archive_fee": None} for detail in details],
            },
        })
    return sorted(rows, key=lambda row: (row["data"]["received_date"], row["id"]), reverse=True)


async def _pending_archive_settlement_rows(
    identity: dict,
    db: AsyncSession,
    *,
    case_type: str = "",
    case_stage: str = "",
    payer: str = "",
    received_from: date | None = None,
    received_to: date | None = None,
    hearing_lawyer: str = "",
    assistant: str = "",
    submitted_by: str = "",
    settled_from: date | None = None,
    settled_to: date | None = None,
    case_no: str = "",
    customer: str = "",
    reviewer: str = "",
    archive_from: date | None = None,
    archive_to: date | None = None,
    require_archived: bool = False,
    selected_ids: set[str] | None = None,
) -> list[dict]:
    """Flatten paid settlement details into the pending-archive or pending-payment list."""
    from app.core.permissions import (
        _record_scope_conditions, _settlement_application_scope,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance_settlement",
        BusinessRecord.status == "已付款",
        *_settlement_application_scope(identity),
    ).order_by(BusinessRecord.id.asc()))).all())
    details = [
        detail
        for record in records
        for detail in list((record.data or {}).get("allocation_details") or [])
        if float(detail.get("archive_fee") or 0) > 0.001
    ]
    case_ids = {int(detail.get("case_id") or 0) for detail in details if detail.get("case_id")}
    case_nos = {str(detail.get("case_no") or "").strip() for detail in details if str(detail.get("case_no") or "").strip()}
    cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case",
        or_(BusinessRecord.id.in_(case_ids), BusinessRecord.serial_no.in_(case_nos)),
        *(await _record_scope_conditions(identity, db)),
    ))).all()) if case_ids or case_nos else []
    cases_by_id = {item.id: item for item in cases}
    cases_by_no = {item.serial_no: item for item in cases}
    archive_events: dict[int, list[WorkflowEvent]] = {}
    visible_case_ids = {item.id for item in cases}
    if require_archived and visible_case_ids:
        for event in (await db.scalars(select(WorkflowEvent).where(
            WorkflowEvent.record_id.in_(visible_case_ids),
            WorkflowEvent.action.in_({"提交归档审核", "归档审核通过"}),
        ).order_by(WorkflowEvent.created_at.desc(), WorkflowEvent.id.desc()))).all():
            archive_events.setdefault(event.record_id, []).append(event)
    decisions = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance_archive_settlement",
        BusinessRecord.status.in_({"已支付", "已拒绝"}),
        *_settlement_application_scope(identity),
    ))).all()) if require_archived else []
    decided_source_ids = {str((item.data or {}).get("source_row_id") or "") for item in decisions}
    can_view_amount = "finance.amount" in await _allowed_field_keys(identity, db)

    def contains(value: object, needle: str) -> bool:
        return not needle.strip() or needle.strip().casefold() in str(value or "").casefold()

    def date_in_range(value: object, start_date: date | None, end_date: date | None) -> bool:
        if not start_date and not end_date:
            return True
        try:
            current = date.fromisoformat(str(value or "")[:10])
        except ValueError:
            return False
        return (not start_date or current >= start_date) and (not end_date or current <= end_date)

    rows: list[dict] = []
    for record in records:
        data = record.data or {}
        for index, detail in enumerate(list(data.get("allocation_details") or []), start=1):
            archive_fee = _round_fee_amount(float(detail.get("archive_fee") or 0))
            if archive_fee <= 0.001:
                continue
            linked_case = cases_by_id.get(int(detail.get("case_id") or 0)) or cases_by_no.get(str(detail.get("case_no") or ""))
            if not linked_case:
                continue
            if require_archived and linked_case.status != "已归档":
                continue
            # Once a case is archived, the original workflow moves the fee to the pending-payment page.
            if not require_archived and linked_case.status == "已归档":
                continue
            case_data = linked_case.data or {}
            row_id = f"{record.id}:{detail.get('detail_id') or index}"
            if require_archived and row_id in decided_source_ids:
                continue
            if selected_ids is not None and row_id not in selected_ids:
                continue
            row_case_type = str(case_data.get("case_type") or "")
            if row_case_type in {"民事案件", "民事"}:
                row_case_type = "民事争议"
            row_case_stage = str(case_data.get("case_stage") or linked_case.status or "")
            row_hearing = case_data.get("hearing_lawyer") or detail.get("handling_lawyer") or ""
            row_assistant = case_data.get("assistant") or case_data.get("lawyer_assistant") or detail.get("assistant") or ""
            row_submitted_by = data.get("applied_by") or record.owner
            row_settled_at = data.get("paid_at") or record.updated_at
            case_events = archive_events.get(linked_case.id, [])
            archive_review_event = next((item for item in case_events if item.action == "归档审核通过"), None)
            archive_submit_event = next((item for item in case_events if item.action == "提交归档审核"), None)
            archive_date = case_data.get("archived_at") or (archive_review_event.created_at if archive_review_event else "")
            if not contains(row_case_type, case_type) or not contains(row_case_stage, case_stage):
                continue
            if not contains(data.get("payer_name"), payer) or not date_in_range(data.get("received_date"), received_from, received_to):
                continue
            if not contains(row_hearing, hearing_lawyer) or not contains(row_assistant, assistant):
                continue
            if not contains(row_submitted_by, submitted_by) or not date_in_range(row_settled_at, settled_from, settled_to):
                continue
            if not contains(linked_case.serial_no, case_no) or not contains(linked_case.customer, customer):
                continue
            if not contains(data.get("reviewer"), reviewer):
                continue
            if require_archived and not date_in_range(archive_date, archive_from, archive_to):
                continue
            rows.append({
                "id": row_id,
                "serial_no": row_id,
                "title": f"{linked_case.serial_no}归档费",
                "customer": linked_case.customer,
                "status": "待支付" if require_archived else "待归档",
                "owner": record.owner,
                "department": record.department,
                "created_at": record.created_at.isoformat() if record.created_at else "",
                "updated_at": record.updated_at.isoformat() if record.updated_at else "",
                "data": {
                    "application_id": record.id,
                    "receipt_id": data.get("receipt_id"),
                    "case_id": linked_case.id,
                    "case_no": linked_case.serial_no,
                    "case_type": row_case_type,
                    "case_stage": row_case_stage,
                    "assistant": row_assistant,
                    "hearing_lawyer": row_hearing,
                    "customer_manager": case_data.get("customer_manager") or "",
                    "fee_type": detail.get("fee_type") or "律师代理费",
                    "payment_method": data.get("payment_method") or "",
                    "payer_name": data.get("payer_name") or "",
                    "received_date": data.get("received_date") or "",
                    "receipt_amount": _round_fee_amount(float(detail.get("current_amount") or 0)) if can_view_amount else None,
                    "archive_fee_amount": archive_fee if can_view_amount else None,
                    "settlement_paid_at": str(row_settled_at or ""),
                    "submitted_by": row_submitted_by,
                    "reviewer": data.get("reviewer") or "",
                    "archive_reviewer": case_data.get("archive_reviewer") or (archive_review_event.operator if archive_review_event else ""),
                    "archive_reviewed_at": str(archive_review_event.created_at if archive_review_event else case_data.get("archived_at") or ""),
                    "archive_review_comment": case_data.get("archive_review_comment") or (archive_review_event.comment if archive_review_event else ""),
                    "archive_submitter": archive_submit_event.operator if archive_submit_event else linked_case.owner,
                    "archive_submitted_at": str(archive_submit_event.created_at if archive_submit_event else ""),
                    "archive_submit_comment": archive_submit_event.comment if archive_submit_event else "",
                    "archive_no": case_data.get("archive_no") or "",
                    "archive_date": str(archive_date or "")[:10],
                    "archive_status": "审核通过" if require_archived else "",
                },
            })
    return sorted(rows, key=lambda row: (str((row.get("data") or {}).get("case_no") or ""), str((row.get("data") or {}).get("received_date") or ""), row["id"]))


async def _archive_settlement_decision_rows(
    identity: dict, db: AsyncSession, *, statuses: set[str],
    case_type: str = "", case_stage: str = "", payer: str = "",
    received_from: date | None = None, received_to: date | None = None,
    hearing_lawyer: str = "", assistant: str = "", submitted_by: str = "",
    settled_from: date | None = None, settled_to: date | None = None,
    submitted_from: date | None = None, submitted_to: date | None = None,
    case_no: str = "", customer: str = "", reviewer: str = "",
    reviewed_from: date | None = None, reviewed_to: date | None = None,
    archive_from: date | None = None, archive_to: date | None = None,
    payment_from: date | None = None, payment_to: date | None = None,
    selected_ids: set[int] | None = None,
) -> list[dict]:
    from app.core.permissions import (
        _settlement_application_scope,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance_archive_settlement",
        BusinessRecord.status.in_(statuses),
        *_settlement_application_scope(identity),
    ).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all())
    can_view_amount = "finance.amount" in await _allowed_field_keys(identity, db)

    def contains(value: object, needle: str) -> bool:
        return not needle.strip() or needle.strip().casefold() in str(value or "").casefold()

    def date_in_range(value: object, start_date: date | None, end_date: date | None) -> bool:
        if not start_date and not end_date:
            return True
        try:
            current = date.fromisoformat(str(value or "")[:10])
        except ValueError:
            return False
        return (not start_date or current >= start_date) and (not end_date or current <= end_date)

    rows: list[dict] = []
    for record in records:
        if selected_ids is not None and record.id not in selected_ids:
            continue
        data = dict(record.data or {})
        if not contains(data.get("case_type"), case_type) or not contains(data.get("case_stage"), case_stage):
            continue
        if not contains(data.get("payer_name"), payer) or not date_in_range(data.get("received_date"), received_from, received_to):
            continue
        if not contains(data.get("hearing_lawyer"), hearing_lawyer) or not contains(data.get("assistant"), assistant):
            continue
        if not contains(data.get("archive_payment_submitted_by") or data.get("submitted_by"), submitted_by):
            continue
        if not date_in_range(data.get("settlement_paid_at"), settled_from, settled_to):
            continue
        if not date_in_range(data.get("archive_payment_submitted_at") or data.get("settlement_paid_at"), submitted_from, submitted_to):
            continue
        if not contains(data.get("case_no"), case_no) or not contains(record.customer, customer):
            continue
        if not contains(data.get("archive_payment_reviewer") or data.get("reviewer"), reviewer):
            continue
        if not date_in_range(data.get("archive_payment_reviewed_at"), reviewed_from, reviewed_to):
            continue
        if not date_in_range(data.get("archive_date"), archive_from, archive_to):
            continue
        if not date_in_range(data.get("archive_payment_reviewed_at"), payment_from, payment_to):
            continue
        if not can_view_amount:
            data["receipt_amount"] = None
            data["archive_fee_amount"] = None
        rows.append({
            "id": record.id,
            "serial_no": record.serial_no,
            "title": record.title,
            "customer": record.customer,
            "status": record.status,
            "owner": record.owner,
            "department": record.department,
            "created_at": record.created_at.isoformat() if record.created_at else "",
            "updated_at": record.updated_at.isoformat() if record.updated_at else "",
            "data": data,
        })
    return rows


async def _rejected_archive_settlement_records(
    record_ids: list[int], identity: dict, db: AsyncSession,
) -> list[BusinessRecord]:
    from app.core.permissions import (
        _settlement_application_scope,
    )
    unique_ids = list(dict.fromkeys(record_ids))
    if len(unique_ids) != len(record_ids):
        raise HTTPException(status_code=422, detail="归档费记录不能重复")
    records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(unique_ids),
        BusinessRecord.module == "finance_archive_settlement",
        BusinessRecord.status == "已拒绝",
        *_settlement_application_scope(identity),
    ))).all())
    if len(records) != len(unique_ids):
        raise HTTPException(status_code=409, detail="部分归档费不存在、不是已拒绝状态或无权处理")
    return records


async def _prepare_internal_payment_package(
    fee_ids: list[int], identity: dict, db: AsyncSession, editable_package_id: int | None = None,
) -> tuple[list[BusinessRecord], list[dict], str, float]:
    from app.core.permissions import (
        _record_scope_conditions,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有打包付款权限")
    unique_ids = list(dict.fromkeys(fee_ids))
    rows = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(unique_ids),
        BusinessRecord.module == "finance",
        *(await _record_scope_conditions(identity, db)),
    ))).all()
    by_id = {item.id: item for item in rows}
    if len(by_id) != len(unique_ids):
        raise HTTPException(status_code=404, detail="部分提成不存在或无权访问")
    fees = [by_id[item_id] for item_id in unique_ids]
    invalid_type = [item.serial_no for item in fees if (item.data or {}).get("fee_type") != "内部费用"]
    if invalid_type:
        raise HTTPException(status_code=409, detail="仅内部费用提成可以打包付款：" + "、".join(invalid_type))
    invalid_status = [
        item.serial_no
        for item in fees
        if not (
            item.status == "已审批"
            or (
                editable_package_id is not None
                and item.status == "待核销"
                and int((item.data or {}).get("payment_package_id") or 0) == editable_package_id
            )
        )
    ]
    if invalid_status:
        raise HTTPException(status_code=409, detail="仅待付款提成可以打包付款：" + "、".join(invalid_status))
    payees = {
        str((item.data or {}).get("payee") or (item.data or {}).get("applicant") or item.owner or "").strip()
        for item in fees
    }
    if "" in payees:
        raise HTTPException(status_code=422, detail="提成收款人不能为空")
    if len(payees) != 1:
        raise HTTPException(status_code=409, detail="请选择同一收款人的提成进行打包付款")
    payee = next(iter(payees))
    case_ids = {int((item.data or {}).get("case_id") or 0) for item in fees if (item.data or {}).get("case_id")}
    cases = {
        item.id: item
        for item in (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.id.in_(case_ids),
            BusinessRecord.module == "case",
            *(await _record_scope_conditions(identity, db)),
        ))).all()
    } if case_ids else {}
    details: list[dict] = []
    for item in fees:
        data = item.data or {}
        amount = _round_fee_amount(float(data.get("actual_commission") if data.get("actual_commission") is not None else data.get("amount") or 0))
        linked_case = cases.get(int(data.get("case_id") or 0))
        details.append({
            "fee_id": item.id,
            "request_no": item.serial_no,
            "case_no": data.get("case_no", ""),
            "case_name": linked_case.title if linked_case else data.get("case_name") or item.title,
            "amount": amount,
            "commission_type": data.get("commission_type") or item.title or data.get("fee_type", ""),
            "payee": payee,
            "remark": data.get("remark") or item.description or "",
        })
    total_amount = _round_fee_amount(sum(float(item["amount"]) for item in details))
    return fees, details, payee, total_amount


def _new_internal_payment_package_no() -> str:
    numeric_suffix = int(uuid4().hex[:12], 16) % 100_000_000
    return f"P{datetime.now():%y%m%d}-{numeric_suffix:08d}"


async def _payment_package_for_word(
    package_no: str,
    scope: str,
    identity: dict,
    db: AsyncSession,
) -> tuple[BusinessRecord, list[BusinessRecord], str]:
    from app.core.permissions import (
        _record_scope_conditions,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有付款单导出权限")
    normalized_scope = (scope or "").strip() or "internal_fee"
    if normalized_scope != "internal_fee":
        raise HTTPException(status_code=422, detail="不支持的付款包导出范围")
    normalized_package_no = package_no.strip()
    if not normalized_package_no:
        raise HTTPException(status_code=422, detail="付款包号不能为空")
    package = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == "finance_package",
        BusinessRecord.serial_no == normalized_package_no,
        *(await _record_scope_conditions(identity, db)),
    ))
    if not package:
        raise HTTPException(status_code=404, detail="付款包不存在或无权访问")
    if package.status not in {"待核销", "已付款"}:
        raise HTTPException(status_code=409, detail="仅待核销或已付款付款包可以导出付款单")
    package_data = package.data or {}
    if normalized_scope == "internal_fee" and package_data.get("fee_type") != "内部提成":
        raise HTTPException(status_code=404, detail="付款包不属于内部费用付款范围")
    fee_ids = [
        int(item_id)
        for item_id in package_data.get("fee_ids", [])
        if str(item_id).strip().isdigit()
    ]
    if not fee_ids:
        raise HTTPException(status_code=409, detail="付款包缺少真实费用明细")
    fees = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(fee_ids),
        BusinessRecord.module == "finance",
        *(await _record_scope_conditions(identity, db)),
    ))).all()
    fee_by_id = {item.id: item for item in fees}
    if len(fee_by_id) != len(set(fee_ids)):
        raise HTTPException(status_code=409, detail="付款包关联费用不存在或无权访问")
    missing_links: list[str] = []
    for fee in fees:
        fee_data = fee.data or {}
        linked_id = int(fee_data.get("payment_package_id") or 0)
        linked_no = str(fee_data.get("payment_package_no") or "").strip()
        if linked_id != package.id and linked_no != package.serial_no:
            missing_links.append(fee.serial_no)
    if missing_links:
        raise HTTPException(status_code=409, detail="费用付款包关联不一致：" + "、".join(missing_links))
    if not package_data.get("items"):
        raise HTTPException(status_code=409, detail="付款包缺少可导出的付款明细")
    return package, fees, normalized_scope


def _finance_payment_type_dict(item: SystemParameter) -> dict:
    extra = item.extra or {}
    return {
        "id": item.id,
        "code": item.code,
        "name": item.name,
        "nature": str(extra.get("nature") or item.name or "").strip(),
        "payee": str(extra.get("payee") or "").strip(),
        "account_bank": str(extra.get("account_bank") or extra.get("bank") or "").strip(),
        "account": str(extra.get("account") or "").strip(),
    }


async def _active_payment_type_rows(db: AsyncSession, keyword: str = "") -> list[dict]:
    items = list((await db.scalars(select(SystemParameter).where(
        SystemParameter.category == "payment_type",
        SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.sort_order, SystemParameter.id))).all())
    term = keyword.strip().casefold()
    result = [
        data for data in (_finance_payment_type_dict(item) for item in items)
        if data["payee"] and data["account_bank"] and data["account"]
    ]
    result = [item for item in result if item["payee"]]
    if term:
        result = [item for item in result if term in " ".join(
            str(item.get(key) or "") for key in ("code", "name", "nature", "payee", "account_bank", "account")
        ).casefold()]
    return result


async def _active_payment_type(payment_type_id: int, db: AsyncSession) -> SystemParameter:
    item = await db.scalar(select(SystemParameter).where(
        SystemParameter.id == payment_type_id,
        SystemParameter.category == "payment_type",
        SystemParameter.is_active.is_(True),
    ))
    if not item:
        raise HTTPException(status_code=422, detail="付款单位不存在或已停用")
    data = _finance_payment_type_dict(item)
    if not data["payee"] or not data["account_bank"] or not data["account"]:
        raise HTTPException(status_code=422, detail="付款单位的收款单位、开户行或账号信息不完整")
    return item


async def _create_payment_type(
    body: FinancePaymentTypeCreateInput,
    identity: dict,
    db: AsyncSession,
    audit_context: dict | None = None,
) -> SystemParameter:
    from app.core.system import (
        _clear_parameter_cache, _system_audit,
    )
    nature = body.nature.strip()
    payee = body.payee.strip()
    account_bank = body.account_bank.strip()
    account = body.account.strip()
    existing_items = list((await db.scalars(select(SystemParameter).where(
        SystemParameter.category == "payment_type",
    ))).all())
    duplicate = next((item for item in existing_items if str((item.extra or {}).get("payee") or "").strip().casefold() == payee.casefold()), None)
    if duplicate:
        raise HTTPException(status_code=409, detail="收款单位已存在，请从候选列表选择")
    sort_order = int(await db.scalar(select(func.coalesce(func.max(SystemParameter.sort_order), 0)).where(
        SystemParameter.category == "payment_type",
    )) or 0) + 1
    item = SystemParameter(
        category="payment_type",
        code=f"PAYEE-{datetime.now():%Y%m%d%H%M%S%f}",
        name=nature,
        extra={"nature": nature, "payee": payee, "account_bank": account_bank, "account": account},
        sort_order=sort_order,
        is_active=True,
        created_by=identity["username"],
        updated_by=identity["username"],
    )
    db.add(item)
    await db.flush()
    await _system_audit(db, identity, "创建付款单位", f"系统参数:payment_type/{item.code}", {
        "id": item.id, "payee": payee, **(audit_context or {}),
    })
    await db.commit()
    await db.refresh(item)
    _clear_parameter_cache("payment_type", identity["username"])
    return item


async def _finance_payment_type_for_fee(fee_id: int, identity: dict, db: AsyncSession) -> BusinessRecord:
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    item = await _ensure_record_module(fee_id, "finance", identity, db)
    await _require_record_owner_or_manager(item, identity, db)
    data = item.data or {}
    if data.get("expense_scope") == "内部" or data.get("fee_type") == "内部费用":
        raise HTTPException(status_code=422, detail="内部费用不使用案件付款单位")
    return item


async def _review_finance_fee_records(items: list[BusinessRecord], approved: bool, comment: str, identity: dict, db: AsyncSession) -> None:
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有费用审批权限")
    invalid = [item.serial_no for item in items if item.status != "待审批"]
    if invalid:
        raise HTTPException(status_code=409, detail="仅待审批费用可以审核：" + "、".join(invalid))
    target_status = "已审批" if approved else "已驳回"
    normalized_comment = comment.strip() or ("审批通过" if approved else "审批拒绝")
    for item in items:
        data = item.data or {}
        is_refund = data.get("fee_type") == "内部费用" and (
            bool(data.get("is_refund")) or float(data.get("amount") or 0) < 0
        )
        action = (
            "内部提成退费审批通过" if approved else "内部提成退费审批驳回"
        ) if is_refund else ("费用审批通过" if approved else "费用审批驳回")
        item.status = target_status
        if is_refund and not data.get("is_refund"):
            item.data = {**data, "is_refund": True}
        db.add(WorkflowEvent(record_id=item.id, action=action, from_status="待审批", to_status=target_status, operator=identity["username"], comment=normalized_comment))


def _case_assisted_fee_dict(row: CaseAssistedFee) -> dict:
    return {
        "id": row.id,
        "case_record_id": row.case_record_id,
        "assisted_type": row.assisted_type,
        "amount": row.amount,
        "status": row.status,
        "request_date": row.request_date,
        "request_user": row.request_user,
        "confirmed_date": row.confirmed_date,
        "confirmed_user": row.confirmed_user,
        "remark": row.remark,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


async def _case_assisted_fee_for_case(
    case_record: BusinessRecord, assisted_fee_id: int, db: AsyncSession,
) -> CaseAssistedFee:
    row = await db.scalar(select(CaseAssistedFee).where(
        CaseAssistedFee.id == assisted_fee_id,
        CaseAssistedFee.case_record_id == case_record.id,
    ).with_for_update())
    if not row:
        raise HTTPException(status_code=404, detail="资助费用不存在或不属于当前案件")
    return row


async def _set_ipr_annual_fee_monitoring(
    body: IprCaseAnnualFeeMonitoringInput, enabled: bool, identity: dict, db: AsyncSession,
) -> dict:
    """Atomically apply the legacy AFM batch action without treating annual year as monitoring consent."""
    from app.core.permissions import (
        _record_scope_conditions, _require_record_owner_or_manager,
    )
    case_ids = list(dict.fromkeys(body.case_ids))
    records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(case_ids), BusinessRecord.module == "ipr_case", *(await _record_scope_conditions(identity, db)),
    ).with_for_update())).all())
    if len(records) != len(case_ids):
        raise HTTPException(status_code=404, detail="存在知识产权案件不存在或无权访问")
    by_id = {item.id: item for item in records}
    ordered = [by_id[item] for item in case_ids]
    for record in ordered:
        await _require_record_owner_or_manager(record, identity, db)
        if record.status != "在办":
            raise HTTPException(status_code=409, detail=f"案件 {record.serial_no} 不在办理中，不能调整年费监控")
    action = "加入年费监控" if enabled else "放弃年费监控"
    updated: list[dict] = []
    for record in ordered:
        data = dict(record.data or {})
        changed = bool(data.get("annual_fee_monitoring")) != enabled
        if changed:
            data["annual_fee_monitoring"] = enabled
            data["annual_fee_monitoring_at"] = datetime.now().isoformat()
            data["annual_fee_monitoring_by"] = identity["username"]
            record.data = data
            db.add(WorkflowEvent(
                record_id=record.id, action=f"知识产权案件{action}", from_status=record.status,
                to_status=record.status, operator=identity["username"],
                comment=body.comment.strip(),
            ))
        updated.append({"id": record.id, "serial_no": record.serial_no, "changed": changed})
    await db.commit()
    return {"updated": sum(1 for item in updated if item["changed"]), "items": updated, "annual_fee_monitoring": enabled}


def _ipr_assisted_fee_dict(
    row: IprCaseAssistedFee,
    attachment: FileAttachment | None = None,
    users_by_username: dict[str, User] | None = None,
) -> dict:
    from app.core.formatters import (
        _person_reference_display,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    users_by_username = users_by_username or {}
    return {
        "id": row.id, "case_record_id": row.case_record_id, "assisted_type": row.assisted_type,
        "status": row.status, "request_date": row.request_date, "request_user": row.request_user,
        "request_user_display_name": _person_reference_display(row.request_user, users_by_username)[0],
        "response_date": row.response_date, "response_user": row.response_user,
        "response_user_display_name": _person_reference_display(row.response_user, users_by_username)[0],
        "remark": row.remark,
        "receipt_attachment_id": row.receipt_attachment_id,
        "receipt": _attachment_dict(attachment) if attachment else None,
        "created_at": row.created_at, "updated_at": row.updated_at,
    }


async def _ipr_case_assisted_fee_row(
    case_record: BusinessRecord, assisted_fee_id: int, db: AsyncSession,
) -> IprCaseAssistedFee:
    row = await db.scalar(select(IprCaseAssistedFee).where(
        IprCaseAssistedFee.id == assisted_fee_id,
        IprCaseAssistedFee.case_record_id == case_record.id,
    ).with_for_update())
    if not row:
        raise HTTPException(status_code=404, detail="协助费不存在或不属于当前案件")
    return row


async def _ipr_case_fee(case_record: BusinessRecord, fee_id: int, identity: dict, db: AsyncSession) -> BusinessRecord:
    fee = await db.get(BusinessRecord, fee_id)
    if not fee or fee.module != "finance":
        raise HTTPException(status_code=404, detail="知识产权案件费用不存在")
    fee_data = fee.data or {}
    linked_case_id = int(fee_data.get("case_id") or 0)
    if linked_case_id and linked_case_id != case_record.id:
        raise HTTPException(status_code=409, detail="费用不属于当前知识产权案件")
    if not linked_case_id and str(fee_data.get("case_no") or "") != case_record.serial_no:
        raise HTTPException(status_code=409, detail="费用不属于当前知识产权案件")
    return fee


async def _ipr_case_fee_rows(case_record: BusinessRecord, identity: dict, db: AsyncSession) -> list[dict]:
    rows = await _invoice_case_fee_rows(
        identity, db, scope="company", case_no=case_record.serial_no,
        include_all_fee_types=True,
    )
    return [
        row for row in rows
        if int((row.get("data") or {}).get("case_id") or 0) == case_record.id
        or str((row.get("data") or {}).get("case_no") or "") == case_record.serial_no
    ]


async def _ipr_case_fee_row(case_record: BusinessRecord, fee_id: int, identity: dict, db: AsyncSession) -> dict:
    for row in await _ipr_case_fee_rows(case_record, identity, db):
        if row.get("id") == fee_id:
            return row
    raise HTTPException(status_code=404, detail="知识产权案件费用不存在")


def _ipr_annual_fee_reminder_content(row: IprCaseAnnualFee) -> str:
    return f"年费#{row.id}｜{row.fee_year}年度｜{row.fee_name}｜应缴日期：{row.due_date}"


def _ipr_annual_fee_dict(row: IprCaseAnnualFee, reminder: IprCaseReminder | None = None) -> dict:
    from app.core.ipr import (
        _ipr_case_reminder_dict,
    )
    return {
        "id": row.id, "case_record_id": row.case_record_id, "fee_year": row.fee_year,
        "fee_name": row.fee_name, "amount": float(row.amount), "currency": row.currency,
        "due_date": row.due_date, "paid_date": row.paid_date, "status": row.status,
        "reminder_date": row.reminder_date, "reminder_id": row.reminder_id,
        "reminder": _ipr_case_reminder_dict(reminder) if reminder else None,
        "notes": row.notes, "created_by": row.created_by,
        "created_at": row.created_at, "updated_at": row.updated_at,
    }


def _validate_ipr_annual_fee_values(*, status_value: str, paid_date: date | None, reminder_date: date | None, due_date: date) -> None:
    if status_value == "已缴" and not paid_date:
        raise HTTPException(status_code=422, detail="已缴年费必须填写实际缴费日期")
    if status_value != "已缴" and paid_date:
        raise HTTPException(status_code=422, detail="待缴或未缴年费不能填写实际缴费日期")
    if reminder_date and reminder_date > due_date:
        raise HTTPException(status_code=422, detail="年费提醒日期不能晚于应缴日期")


async def _sync_ipr_annual_fee_reminder(row: IprCaseAnnualFee, case_record: BusinessRecord, identity: dict, db: AsyncSession) -> IprCaseReminder | None:
    """Persist one IPR in-app reminder per unpaid annual fee; paid fees clear it."""
    reminder = None
    if row.reminder_id:
        reminder = await db.scalar(select(IprCaseReminder).where(
            IprCaseReminder.id == row.reminder_id,
            IprCaseReminder.case_record_id == case_record.id,
        ))
    suppressed = await db.scalar(select(IprCaseReminderSuppression.id).where(
        IprCaseReminderSuppression.case_record_id == case_record.id,
        IprCaseReminderSuppression.event_type_id == 4,
    ))
    if row.status == "已缴":
        row.reminder_date = None
    if row.status == "已缴" or suppressed or not row.reminder_date:
        if reminder:
            await db.delete(reminder)
        row.reminder_id = None
        return None
    if not reminder:
        reminder = IprCaseReminder(
            case_record_id=case_record.id, event_type_id=4, event_type="缴纳年费",
            reminder_date=row.reminder_date, deadline=row.due_date,
            content=_ipr_annual_fee_reminder_content(row), creator=identity["username"],
        )
        db.add(reminder)
        await db.flush()
        row.reminder_id = reminder.id
        return reminder
    reminder.reminder_date = row.reminder_date
    reminder.deadline = row.due_date
    reminder.content = _ipr_annual_fee_reminder_content(row)
    return reminder
