"""按独立业务职责组织的路由，注册顺序与端点行为保持稳定。"""
from app.core.dependencies import (
    AsyncSession,
    BusinessRecord,
    Depends,
    FinanceTransaction,
    HTTPException,
    User,
    WorkflowEvent,
    current_identity,
    date,
    datetime,
    get_db,
    or_,
    select,
    settings,
    status,
)
from app.models_shared import (
    FinanceActionInput,
    FinanceReviewInput,
    InvoiceApplicationInput,
    InvoiceDateChangeInput,
    InvoiceIssueInput,
    InvoiceNumberChangeInput,
    InvoiceVoidInput,
)
from fastapi import APIRouter

router = APIRouter()

async def _invoice_source_metadata(case_fees: list[BusinessRecord], db: AsyncSession) -> tuple[list[BusinessRecord], list[int], list[str], list[int], list[str]]:
    contract_ids: list[int] = []
    contract_nos: list[str] = []
    case_ids: list[int] = []
    case_nos: list[str] = []
    for fee in case_fees:
        data = fee.data or {}
        contract_id = int(data.get("contract_id") or data.get("contract_record_id") or 0)
        contract_no = str(data.get("contract_no") or "").strip()
        case_id = int(data.get("case_id") or data.get("case_record_id") or 0)
        case_no = str(data.get("case_no") or "").strip()
        if contract_id and contract_id not in contract_ids:
            contract_ids.append(contract_id)
        if contract_no and contract_no not in contract_nos:
            contract_nos.append(contract_no)
        if case_id and case_id not in case_ids:
            case_ids.append(case_id)
        if case_no and case_no not in case_nos:
            case_nos.append(case_no)
    contracts = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "contract",
        or_(BusinessRecord.id.in_(contract_ids), BusinessRecord.serial_no.in_(contract_nos)),
    ))).all()) if contract_ids or contract_nos else []
    for contract in contracts:
        if contract.id not in contract_ids:
            contract_ids.append(contract.id)
        if contract.serial_no not in contract_nos:
            contract_nos.append(contract.serial_no)
    return contracts, contract_ids, contract_nos, case_ids, case_nos


def _invoice_current_external_number(contracts: list[BusinessRecord]) -> str:
    from app.core.formatters import _normalize_external_contract_numbers

    if len(contracts) != 1:
        return ""
    data = dict(contracts[0].data or {})
    if "external_contract_numbers" not in data and "external_contract_no" not in data:
        data["external_contract_no"] = data.get("ref_contract_no") or ""
    return _normalize_external_contract_numbers(data)["external_contract_no"]


@router.post(f"{settings.api_prefix}/finance/invoices", status_code=status.HTTP_201_CREATED)
async def create_invoice_application(body: InvoiceApplicationInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.contracts import _contract_allows_finance_application
    from app.core.finance import (
        _round_fee_amount, _validate_invoice_source_links,
    )
    from app.core.permissions import (
        _record_dict_for_identity,
    )
    case_record, contract_record, case_fees, allocations = await _validate_invoice_source_links(
        body, identity, db, require_source=True,
    )
    source_contracts, contract_ids, contract_nos, case_ids, case_nos = await _invoice_source_metadata(case_fees, db)
    blocked_contracts = [item.serial_no for item in source_contracts if not _contract_allows_finance_application(item)]
    if blocked_contracts:
        raise HTTPException(status_code=409, detail="归档或已终止合同不能新建开票申请：" + "、".join(blocked_contracts))
    contract_bodies = {str((item.data or {}).get("contract_body") or "律所").strip() for item in source_contracts}
    if len(contract_bodies) > 1:
        raise HTTPException(status_code=409, detail="平台合同与律所合同不能合并开票")
    if "专用" in body.invoice_type and not all(value.strip() for value in (body.invoice_address, body.invoice_phone, body.bank_name, body.bank_account)):
        raise HTTPException(status_code=422, detail="增值税专用发票必须填写注册地址、注册电话、开户银行和银行账号")
    case_fee_ids = [fee.id for fee in case_fees]
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if not user: raise HTTPException(status_code=401, detail="当前用户不存在")
    serial = f"FP{datetime.now():%Y%m%d%H%M%S%f}"
    data = body.model_dump(); data["case_fee_ids"] = case_fee_ids; data["case_fee_allocations"] = allocations; data["invoice_over_amount"] = _round_fee_amount(sum(float(row.get("over_amount") or 0) for row in allocations)); data["amount"] = _round_fee_amount(body.amount); data["extra_amount"] = _round_fee_amount(body.extra_amount); data["applicant"] = identity.get("display_name") or identity["username"]; data["case_id"] = case_record.id if case_record else (case_ids[0] if len(case_ids) == 1 else None); data["contract_id"] = contract_record.id if contract_record else (contract_ids[0] if len(contract_ids) == 1 else None); data["case_ids"] = case_ids; data["case_nos"] = case_nos; data["contract_ids"] = contract_ids; data["contract_nos"] = contract_nos
    if contract_record:
        data["contract_body"] = (contract_record.data or {}).get("contract_body")
        data["accounting_center"] = "平台财务中心" if str(data["contract_body"] or "").strip() == "平台" else "财务中心"
        data["finance_scope"] = "platform" if data["accounting_center"] == "平台财务中心" else "firm"
    elif source_contracts:
        data["contract_body"] = next(iter(contract_bodies), "律所")
        data["accounting_center"] = "平台财务中心" if data["contract_body"] == "平台" else "财务中心"
        data["finance_scope"] = "platform" if data["accounting_center"] == "平台财务中心" else "firm"
    if case_record: data["case_no"] = case_record.serial_no
    elif len(case_nos) == 1: data["case_no"] = case_nos[0]
    if contract_record: data["contract_no"] = contract_record.serial_no
    elif len(contract_nos) == 1: data["contract_no"] = contract_nos[0]
    data["external_contract_no"] = _invoice_current_external_number(source_contracts)
    item = BusinessRecord(module="invoice", serial_no=serial, title=f"{body.customer}发票申请", customer=body.customer.strip(), status="草稿", owner=identity["username"], department=user.department, description=body.remark, data=data)
    db.add(item); await db.flush()
    db.add(WorkflowEvent(record_id=item.id, action="创建发票申请", to_status=item.status, operator=identity["username"], comment=f"{body.invoice_type}：{data['amount']:.2f} 元"))
    await db.commit(); await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)


@router.put(f"{settings.api_prefix}/finance/invoices/{{invoice_id}}")
@router.patch(f"{settings.api_prefix}/finance/invoices/{{invoice_id}}")
async def update_invoice_application(invoice_id: int, body: InvoiceApplicationInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _editable_invoice_application, _round_fee_amount, _validate_invoice_source_links,
    )
    from app.core.permissions import (
        _record_dict_for_identity,
    )
    try:
        item = await _editable_invoice_application(invoice_id, identity, db)
        from pydantic import ValidationError
        values = body.model_dump()
        existing = item.data or {}
        if "service_items" not in body.model_fields_set:
            values["service_items"] = existing.get("service_items") or []
        elif existing.get("service_items") and not body.service_items:
            raise HTTPException(status_code=422, detail="已有服务项不能全部清空")
        if ("case_fee_allocations" not in body.model_fields_set
                and set(body.case_fee_ids) == set(existing.get("case_fee_ids") or [])
                and body.amount == existing.get("amount")):
            values["case_fee_allocations"] = existing.get("case_fee_allocations") or []
        try:
            body = InvoiceApplicationInput.model_validate(values)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        case_record, contract_record, case_fees, allocations = await _validate_invoice_source_links(
            body,
            identity,
            db,
            require_source=True,
            exclude_invoice_id=invoice_id,
        )
        from app.core.contracts import _contract_allows_finance_application
        source_contracts, contract_ids, contract_nos, case_ids, case_nos = await _invoice_source_metadata(case_fees, db)
        blocked_contracts = [item.serial_no for item in source_contracts if not _contract_allows_finance_application(item)]
        if blocked_contracts:
            raise HTTPException(status_code=409, detail="归档或已终止合同不能新建开票申请：" + "、".join(blocked_contracts))
        contract_bodies = {str((item.data or {}).get("contract_body") or "律所").strip() for item in source_contracts}
        if len(contract_bodies) > 1:
            raise HTTPException(status_code=409, detail="平台合同与律所合同不能合并开票")
        case_fee_ids = [fee.id for fee in case_fees]
        existing_data = dict(item.data or {})
        data = {**existing_data, **body.model_dump()}
        data["case_fee_ids"] = case_fee_ids
        data["case_fee_allocations"] = allocations
        data["invoice_over_amount"] = _round_fee_amount(sum(float(row.get("over_amount") or 0) for row in allocations))
        data["amount"] = _round_fee_amount(body.amount)
        data["extra_amount"] = _round_fee_amount(body.extra_amount)
        data["applicant"] = existing_data.get("applicant") or identity.get("display_name") or identity["username"]
        data["case_id"] = case_record.id if case_record else (case_ids[0] if len(case_ids) == 1 else None)
        data["contract_id"] = contract_record.id if contract_record else (contract_ids[0] if len(contract_ids) == 1 else None)
        data["case_ids"] = case_ids
        data["case_nos"] = case_nos
        data["contract_ids"] = contract_ids
        data["contract_nos"] = contract_nos
        data["external_contract_no"] = _invoice_current_external_number(source_contracts)
        if case_record:
            data["case_no"] = case_record.serial_no
        elif len(case_nos) == 1:
            data["case_no"] = case_nos[0]
        else:
            data["case_no"] = ""
        if contract_record:
            data["contract_no"] = contract_record.serial_no
        elif len(contract_nos) == 1:
            data["contract_no"] = contract_nos[0]
        else:
            data["contract_no"] = ""
        if source_contracts:
            data["contract_body"] = next(iter(contract_bodies), "律所")
            data["accounting_center"] = "平台财务中心" if data["contract_body"] == "平台" else "财务中心"
            data["finance_scope"] = "platform" if data["accounting_center"] == "平台财务中心" else "firm"
        previous_status = item.status
        item.title = f"{body.customer}发票申请"
        item.customer = body.customer.strip()
        item.description = body.remark
        item.data = data
        db.add(WorkflowEvent(
            record_id=item.id,
            action="修改发票申请",
            from_status=previous_status,
            to_status=item.status,
            operator=identity["username"],
            comment=f"{body.invoice_type}：{data['amount']:.2f} 元",
        ))
        await db.commit(); await db.refresh(item)
        return await _record_dict_for_identity(item, identity, db)
    except HTTPException as exc:
        await db.rollback()
        raise exc


@router.post(f"{settings.api_prefix}/finance/invoices/{{invoice_id}}/submit")
async def submit_invoice_application(invoice_id: int, body: FinanceActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _require_record_owner_or_manager,
    )
    item = await _ensure_record_module(invoice_id, "invoice", identity, db); await _require_record_owner_or_manager(item, identity, db)
    if item.status not in {"草稿", "已驳回"}: raise HTTPException(status_code=409, detail="当前发票申请不能提交")
    from app.core.invoice_sources import invoice_source_fees, validate_invoice_fee_policy
    source_fees = await invoice_source_fees(item, identity, db)
    await validate_invoice_fee_policy(source_fees, db)
    source_contracts, _, _, _, _ = await _invoice_source_metadata(source_fees, db)
    data = item.data or {}; missing = [name for name, value in {"客户名称": item.customer, "发票抬头": data.get("invoice_title"), "纳税人识别号": data.get("taxpayer_id"), "开票金额": data.get("amount")}.items() if not value]
    if data.get("delivery_method") == "电子发票" and not data.get("email"): missing.append("电子邮箱")
    if data.get("delivery_method") != "电子发票" and not data.get("delivery_address"): missing.append("邮寄地址")
    if missing: raise HTTPException(status_code=422, detail="发票申请缺少：" + "、".join(missing))
    previous = item.status
    submitted_at = datetime.now().isoformat(timespec="seconds")
    item.status = "待审批"
    item.data = {**data, "external_contract_no": _invoice_current_external_number(source_contracts), "submitted_at": submitted_at, "submitted_by": identity["username"]}
    db.add(WorkflowEvent(record_id=item.id, action="提交发票申请", from_status=previous, to_status=item.status, operator=identity["username"], comment=body.comment))
    await db.commit(); await db.refresh(item); return await _record_dict_for_identity(item, identity, db)


@router.post(f"{settings.api_prefix}/finance/invoices/{{invoice_id}}/withdraw")
async def withdraw_invoice_application(invoice_id: int, body: FinanceActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _require_record_owner_or_manager,
    )
    item = await _ensure_record_module(invoice_id, "invoice", identity, db)
    await _require_record_owner_or_manager(item, identity, db)
    if item.status not in {"草稿", "待审批", "待开票", "已驳回"}:
        raise HTTPException(status_code=409, detail="当前发票申请不能撤回")
    previous = item.status
    item.status = "已撤回"
    item.data = {**(item.data or {}), "withdrawn_by": identity["username"], "withdrawn_at": datetime.now().isoformat(timespec="seconds"), "withdraw_comment": body.comment}
    db.add(WorkflowEvent(record_id=item.id, action="撤回发票申请", from_status=previous, to_status=item.status, operator=identity["username"], comment=body.comment))
    await db.commit(); await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)


@router.post(f"{settings.api_prefix}/finance/invoices/{{invoice_id}}/review")
async def review_invoice_application(invoice_id: int, body: FinanceReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    item = await _ensure_record_module(invoice_id, "invoice", identity, db)
    from app.core.invoice_permissions import require_invoice_action
    await require_invoice_action(item, "review", identity, db)
    if item.status != "待审批": raise HTTPException(status_code=409, detail="只有待审批发票申请可以审核")
    item.status = "待开票" if body.approved else "已驳回"
    item.data = {**(item.data or {}), "reviewer": identity["username"], "reviewed_at": datetime.now().isoformat(timespec="seconds"), "review_comment": body.comment}
    db.add(WorkflowEvent(record_id=item.id, action="发票审批通过" if body.approved else "发票审批驳回", from_status="待审批", to_status=item.status, operator=identity["username"], comment=body.comment))
    await db.commit(); await db.refresh(item); return await _record_dict_for_identity(item, identity, db)


@router.post(f"{settings.api_prefix}/finance/invoices/{{invoice_id}}/issue")
async def issue_invoice(invoice_id: int, body: InvoiceIssueInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _round_fee_amount,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    item = await _ensure_record_module(invoice_id, "invoice", identity, db)
    from app.core.invoice_permissions import require_invoice_action
    await require_invoice_action(item, "issue", identity, db)
    if item.status != "待开票": raise HTTPException(status_code=409, detail="发票审批通过后才能登记开票")
    if await db.scalar(select(FinanceTransaction.id).where(FinanceTransaction.transaction_type == "开票", FinanceTransaction.voucher_no == body.invoice_no)): raise HTTPException(status_code=409, detail="发票号码已经登记")
    data = item.data or {}; tx = FinanceTransaction(finance_record_id=item.id, transaction_type="开票", amount=float(data.get("amount", 0)), transaction_date=body.invoice_date, voucher_no=body.invoice_no.strip(), counterparty=item.customer, operator=identity["username"], remark=f"发票申请 {item.serial_no}；{body.comment}")
    db.add(tx); await db.flush()
    item.status = "已开票"; item.data = {**data, "invoice_no": body.invoice_no.strip(), "invoice_date": str(body.invoice_date), "recipient": body.invoice_holder.strip(), "extra_amount": _round_fee_amount(body.extra_amount), "invoiced_opinion": body.comment.strip(), "invoice_transaction_id": tx.id, "issued_by": identity["username"], "issued_at": datetime.now().isoformat(timespec="seconds")}
    db.add(WorkflowEvent(record_id=item.id, action="登记开票", from_status="待开票", to_status=item.status, operator=identity["username"], comment=f"发票号：{body.invoice_no}。{body.comment}"))
    await db.commit(); await db.refresh(item); return await _record_dict_for_identity(item, identity, db)


@router.post(f"{settings.api_prefix}/finance/invoices/{{invoice_id}}/reject-issue")
async def reject_invoice_issue(invoice_id: int, body: FinanceActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )

    reason = body.comment.strip()
    if not reason:
        raise HTTPException(status_code=422, detail="请输入驳回原因")
    item = await _ensure_record_module(invoice_id, "invoice", identity, db)
    from app.core.invoice_permissions import require_invoice_action
    await require_invoice_action(item, "issue", identity, db)
    if item.status != "待开票":
        raise HTTPException(status_code=409, detail="只有待开票申请可以驳回")
    item.status = "已驳回"
    item.data = {**(item.data or {}), "invoiced_opinion": reason, "issue_rejected_by": identity["username"], "issue_rejected_at": datetime.now().isoformat(timespec="seconds")}
    db.add(WorkflowEvent(record_id=item.id, action="开票驳回", from_status="待开票", to_status=item.status, operator=identity["username"], comment=reason))
    await db.commit(); await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)


@router.post(f"{settings.api_prefix}/finance/invoices/{{invoice_id}}/void")
async def void_invoice(invoice_id: int, body: InvoiceVoidInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    if identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以作废发票")
    item = await _ensure_record_module(invoice_id, "invoice", identity, db)
    if item.status != "已开票": raise HTTPException(status_code=409, detail="只有已开票记录可以作废")
    data = item.data or {}; amount = float(data.get("amount", 0))
    db.add(FinanceTransaction(finance_record_id=item.id, transaction_type="开票", amount=-amount, transaction_date=date.today(), voucher_no=str(data.get("invoice_no", "")), counterparty=item.customer, operator=identity["username"], remark=f"作废冲销 {item.serial_no}：{body.reason}"))
    item.status = "已作废"; item.data = {**data, "void_reason": body.reason, "voided_by": identity["username"], "voided_at": datetime.now().isoformat(timespec="seconds")}
    db.add(WorkflowEvent(record_id=item.id, action="发票作废", from_status="已开票", to_status=item.status, operator=identity["username"], comment=body.reason))
    await db.commit(); await db.refresh(item); return await _record_dict_for_identity(item, identity, db)


@router.post(f"{settings.api_prefix}/finance/invoices/{{invoice_id}}/change-number")
async def change_invoice_number(invoice_id: int, body: InvoiceNumberChangeInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以修改发票号码")
    invoice_no = body.invoice_no.strip()
    if not invoice_no:
        raise HTTPException(status_code=422, detail="请输入新发票号码.")
    item = await _ensure_record_module(invoice_id, "invoice", identity, db)
    if item.status in {"已撤回", "已作废"}:
        raise HTTPException(status_code=409, detail="已撤回或已作废发票不能修改号码")
    duplicate = await db.scalar(select(FinanceTransaction.id).where(
        FinanceTransaction.transaction_type == "开票",
        FinanceTransaction.voucher_no == invoice_no,
        FinanceTransaction.finance_record_id != item.id,
    ))
    if duplicate:
        raise HTTPException(status_code=409, detail="发票号码已经登记")
    data = item.data or {}
    old_invoice_no = str(data.get("invoice_no") or "")
    transaction_id = data.get("invoice_transaction_id")
    if transaction_id:
        transaction = await db.scalar(select(FinanceTransaction).where(
            FinanceTransaction.id == int(transaction_id),
            FinanceTransaction.finance_record_id == item.id,
            FinanceTransaction.transaction_type == "开票",
        ))
        if transaction:
            transaction.voucher_no = invoice_no
    item.data = {**data, "invoice_no": invoice_no, "invoice_no_changed_by": identity["username"], "invoice_no_changed_at": datetime.now().isoformat(timespec="seconds")}
    db.add(WorkflowEvent(record_id=item.id, action="修改发票号", from_status=item.status, to_status=item.status, operator=identity["username"], comment=f"{old_invoice_no} → {invoice_no}"))
    await db.commit(); await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)


@router.post(f"{settings.api_prefix}/finance/invoices/{{invoice_id}}/change-date")
async def change_invoice_date(invoice_id: int, body: InvoiceDateChangeInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以修改发票日期")
    item = await _ensure_record_module(invoice_id, "invoice", identity, db)
    if item.status in {"已撤回", "已作废"}:
        raise HTTPException(status_code=409, detail="已撤回或已作废发票不能修改日期")
    data = item.data or {}
    old_application_date = str(data.get("application_date") or item.created_at)[:10]
    old_invoice_date = str(data.get("invoice_date") or "")[:10]
    transaction_id = data.get("invoice_transaction_id")
    if transaction_id:
        transaction = await db.scalar(select(FinanceTransaction).where(
            FinanceTransaction.id == int(transaction_id),
            FinanceTransaction.finance_record_id == item.id,
            FinanceTransaction.transaction_type == "开票",
        ))
        if transaction:
            transaction.transaction_date = body.invoice_date
    item.data = {
        **data,
        "application_date": str(body.application_date),
        "invoice_date": str(body.invoice_date),
        "invoice_date_changed_by": identity["username"],
        "invoice_date_changed_at": datetime.now().isoformat(timespec="seconds"),
    }
    db.add(WorkflowEvent(
        record_id=item.id,
        action="修改发票日期",
        from_status=item.status,
        to_status=item.status,
        operator=identity["username"],
        comment=f"申请日期 {old_application_date} → {body.application_date}；开票日期 {old_invoice_date} → {body.invoice_date}",
    ))
    await db.commit(); await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)
