"""财务路由编排。"""
from app.core.constants import (
    EXPENSE_SCOPE_FEE_TYPES, FINANCE_FEE_TYPES, REFUND_CASE_FEE_STATUSES, REFUND_CASE_FEE_STATUS_BY_LABEL,
)
from app.core.dependencies import (
    AsyncSession, BusinessRecord, Depends, FileAttachment,
    FinanceTransaction, HTTPException, LegacyFinanceAllocation, LegacyFinanceAudit, LegacyFinanceFile,
    LegacyFinanceRecord, Query, ReceivablePlan, Response, User, WorkflowEvent,
    current_identity, date, datetime,
    false, func, get_db, or_, quote, select, settings, status,
    uuid4, xml_escape,
)
from app.models_shared import (
    CaseFeeBatchUpdateInput, CaseFeeRefundLogInput,
    FinanceFeeBatchReviewInput, FinanceFeeInput, FinanceFeeUpdateInput, FinancePaymentCancelInput, ReceivableInput, ReceivePaymentInput, RefundBatchStatusInput, RefundCaseFeeBatchCreateInput,
)
from fastapi import APIRouter

router = APIRouter()
from app.core.incoming_settlement import (
    _active_settlements_by_receipt as _active_settlements_by_receipt,
    _revert_incoming_allocation as _revert_incoming_allocation,
)
from app.areas.finance.receipt_files import router as receipt_files_router
from app.areas.finance.payment_workflow import router as payment_workflow_router


from app.areas.finance.fee_action_guards import (
    _is_internal_application as _is_internal_application,
    _require_non_internal_application_action as _require_non_internal_application_action,
    _require_linked_case_fee_action as _require_linked_case_fee_action,
)


@router.put(f"{settings.api_prefix}/finance/fees/{{fee_id}}")
async def update_finance_fee(fee_id: int, body: FinanceFeeUpdateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _case_fee_type_snapshot, _editable_finance_fee, _finance_fee_commission_payload, _resolve_case_fee_contract, _resolve_case_fee_type_master,
        _round_fee_amount,
    )
    from app.core.permissions import (
        _case_detail_action_capabilities, _ensure_record_visible, _record_dict_for_identity, _validate_finance_fee_scope_subtype,
    )
    item = await _editable_finance_fee(fee_id, identity, db)
    amount = _round_fee_amount(body.amount)
    data = dict(item.data or {})
    case_record = None
    case_record_id = body.case_record_id or int(data.get("case_id") or 0) or None
    if case_record_id:
        case_record = await _ensure_record_visible(case_record_id, identity, db)
        if case_record.module != "case": raise HTTPException(status_code=422, detail="关联记录不是案件")
        if not (await _case_detail_action_capabilities(case_record, identity, db))["can_edit_finance"]:
            raise HTTPException(status_code=403, detail="当前账号没有修改案件费用权限")
    fee_snapshot = {
        "fee_type_id": None,
        "fee_type_code": "",
        "fee_type_name": body.expense_subtype or body.fee_type,
        "fee_type_path": body.expense_subtype or body.fee_type,
        "fee_type": body.fee_type,
        "expense_subtype": body.expense_subtype or "",
    }
    if case_record or body.fee_type_id:
        fee_parameter, fee_option = await _resolve_case_fee_type_master(
            body.fee_type_id, body.expense_scope, db,
            legacy_name=body.expense_subtype or "", legacy_base=body.fee_type,
        )
        fee_snapshot = _case_fee_type_snapshot(fee_parameter, fee_option)
        if body.fee_type != fee_snapshot["fee_type"] or (body.expense_subtype and body.expense_subtype != fee_parameter.name):
            raise HTTPException(status_code=422, detail="费用类型与系统费用分类不一致")
    else:
        if body.fee_type not in FINANCE_FEE_TYPES:
            raise HTTPException(status_code=422, detail="费用类型无效")
        if body.expense_scope and body.fee_type not in EXPENSE_SCOPE_FEE_TYPES[body.expense_scope]:
            raise HTTPException(status_code=422, detail="费用归属与费用类型不一致")
        _validate_finance_fee_scope_subtype(body.expense_scope, body.expense_subtype, body.fee_type)
    contract_record = None
    try:
        existing_contract_id = int(data.get("contract_id") or data.get("contract_record_id") or 0)
    except (TypeError, ValueError):
        existing_contract_id = 0
    requested_contract_id = body.contract_record_id or existing_contract_id or None
    if requested_contract_id:
        contract_record = await db.get(BusinessRecord, requested_contract_id) if case_record else await _ensure_record_visible(requested_contract_id, identity, db)
        if not contract_record: raise HTTPException(status_code=404, detail="关联合同不存在")
        if contract_record.module != "contract": raise HTTPException(status_code=422, detail="关联记录不是合同")
        if case_record and contract_record.customer != case_record.customer:
            raise HTTPException(status_code=409, detail="关联合同必须属于当前案件客户")
    contract_record = await _resolve_case_fee_contract(case_record, contract_record, body.expense_scope, identity, db)
    commission = await _finance_fee_commission_payload(body, amount, db, case_record=case_record, existing_data=data)
    data.update({"amount": amount, **fee_snapshot, "expense_scope": body.expense_scope or "", "handler": body.handler, "court": body.court, "document_no": body.document_no, "payee": body.payee, "base_amount": body.base_amount, "reference_commission": body.reference_commission, "case_no": case_record.serial_no if case_record else body.case_no, "case_id": case_record.id if case_record else body.case_record_id, "contract_id": contract_record.id if contract_record else None, "contract_no": contract_record.serial_no if contract_record else "", "deadline": str(body.deadline) if body.deadline else "", **commission, "is_refund": fee_snapshot["fee_type"] == "内部费用" and amount < 0})
    item.title = body.title; item.customer = body.customer; item.owner = body.handler; item.description = body.description; item.data = data
    db.add(WorkflowEvent(record_id=item.id, action="修改费用", from_status=item.status, to_status=item.status, operator=identity["username"], comment=f"{item.serial_no}：{body.title} {amount:.2f}"))
    await db.commit(); await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)


@router.delete(f"{settings.api_prefix}/finance/fees/{{fee_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_finance_fee(fee_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _editable_finance_fee,
    )
    item = await _editable_finance_fee(fee_id, identity, db, action="delete")
    await _require_linked_case_fee_action(item, "case.fee.delete", identity, db)
    db.add(WorkflowEvent(record_id=item.id, action="删除费用", from_status=item.status, to_status="已删除", operator=identity["username"], comment=item.serial_no))
    item.status = "已删除"
    await db.commit()
    return None


@router.post(f"{settings.api_prefix}/finance/internal-fees", status_code=status.HTTP_201_CREATED)
async def create_internal_fee(body: FinanceFeeInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Create an internal-fee draft through the internal settlement workbench."""
    from app.core.permissions import (
        _require_internal_fee_payload,
    )
    _require_internal_fee_payload(body)
    return await create_finance_fee(body, identity, db)


@router.put(f"{settings.api_prefix}/finance/internal-fees/{{fee_id}}")
async def update_internal_fee(fee_id: int, body: FinanceFeeUpdateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Edit only a visible, mutable internal-fee draft using the shared fee rules."""
    from app.core.finance import (
        _internal_fee_mutation_target,
    )
    from app.core.permissions import (
        _require_internal_fee_payload,
    )
    await _internal_fee_mutation_target(fee_id, identity, db)
    _require_internal_fee_payload(body)
    return await update_finance_fee(fee_id, body, identity, db)


@router.delete(f"{settings.api_prefix}/finance/internal-fees/{{fee_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_internal_fee(fee_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Delete only a visible, mutable internal-fee draft with its workflow audit."""
    from app.core.finance import (
        _editable_finance_fee, _internal_fee_mutation_target,
    )
    await _internal_fee_mutation_target(fee_id, identity, db)
    item = await _editable_finance_fee(fee_id, identity, db, action="delete")
    previous = item.status
    # Keep the deletion event queryable. The generic physical-delete route
    # cascades WorkflowEvent rows, which would erase this finance audit trail.
    item.status = "已删除"
    db.add(WorkflowEvent(record_id=item.id, action="删除内部费用", from_status=previous, to_status="已删除", operator=identity["username"], comment=item.serial_no))
    await db.commit()


from app.areas.finance.jar_fees import (
    router as jar_fees_router,
    list_jar_fees as list_jar_fees,
    export_jar_fees as export_jar_fees,
    create_jar_fee as create_jar_fee,
    get_jar_fee as get_jar_fee,
    update_jar_fee as update_jar_fee,
    delete_jar_fee as delete_jar_fee,
    update_jar_fee_status as update_jar_fee_status,
    list_jar_fee_files as list_jar_fee_files,
    list_jar_fee_operation_logs as list_jar_fee_operation_logs,
    upload_jar_fee_file as upload_jar_fee_file,
    download_jar_fee_file as download_jar_fee_file,
    delete_jar_fee_file as delete_jar_fee_file,
)
router.include_router(jar_fees_router)


from app.areas.finance.fee_notices import (
    router as fee_notices_router,
    list_finance_fee_informs as list_finance_fee_informs,
    create_finance_fee_inform as create_finance_fee_inform,
    confirm_finance_fee_inform_arrival as confirm_finance_fee_inform_arrival,
    upload_finance_fee_inform_bill as upload_finance_fee_inform_bill,
    download_finance_fee_inform_bill as download_finance_fee_inform_bill,
    unlock_finance_fee_inform as unlock_finance_fee_inform,
    link_finance_fee_inform as link_finance_fee_inform,
    delete_finance_fee_inform as delete_finance_fee_inform,
)
router.include_router(fee_notices_router)


@router.get(f"{settings.api_prefix}/finance/payment-source/{{source_id}}")
async def get_finance_payment_source(
    source_id: int,
    payment_no: str = Query(min_length=1, max_length=64),
    contract_no: str = Query(min_length=1, max_length=64),
    customer: str = Query(min_length=1, max_length=255),
    amount: float = Query(gt=0),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a contract-payment source by primary key and verify every source field.

    The source id is the indexed lookup key; the remaining values are an
    identity check so a stale or cross-contract URL cannot silently fall back
    to the ordinary payment list.
    """
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    payment = await _ensure_record_module(source_id, "contract_payment", identity, db)
    data = payment.data or {}
    try:
        stored_amount = float(data.get("amount") or 0)
    except (TypeError, ValueError):
        stored_amount = None
    matches = (
        payment.serial_no.strip() == payment_no.strip()
        and str(data.get("contract_no") or "").strip() == contract_no.strip()
        and (payment.customer or "").strip() == customer.strip()
        and stored_amount is not None
        and abs(stored_amount - float(amount)) <= 0.001
    )
    if not matches:
        raise HTTPException(status_code=404, detail="合同付款来源不存在或字段不匹配")
    return await _record_dict_for_identity(payment, identity, db)


@router.get(f"{settings.api_prefix}/receivables")
async def list_receivables(
    keyword: str = "", receivable_status: str = "",
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _receivable_dict,
    )
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    visible_contract_ids = select(BusinessRecord.id).where(*(await _record_scope_conditions(identity, db)))
    plans = (await db.scalars(select(ReceivablePlan).where(
        ReceivablePlan.contract_record_id.in_(visible_contract_ids),
    ).order_by(ReceivablePlan.due_date))).all()
    contract_ids = {plan.contract_record_id for plan in plans}
    contracts = {record.id: record for record in (await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(contract_ids), *(await _record_scope_conditions(identity, db))))).all()} if contract_ids else {}
    users_by_username = await _user_display_map({record.owner for record in contracts.values()}, db)
    items = [_receivable_dict(plan, contracts[plan.contract_record_id], users_by_username) for plan in plans if plan.contract_record_id in contracts]
    if keyword:
        needle = keyword.casefold()
        items = [item for item in items if needle in " ".join([item["contract_no"], item["contract_title"], item["customer"], item["phase"], item["payer"]]).casefold()]
    if receivable_status:
        items = [item for item in items if item["status"] == receivable_status]
    all_amount = sum(item["amount"] for item in items)
    received = sum(item["received_amount"] for item in items)
    overdue = sum(item["remaining_amount"] for item in items if item["status"] == "已逾期")
    return {"items": items, "total": len(items), "summary": {"amount": all_amount, "received": received, "remaining": all_amount - received, "overdue": overdue}}


@router.get(f"{settings.api_prefix}/receivables/detail")
async def list_receivable_details(
    dashboard_queue: str = "",
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.projections import (
        _receivable_detail_projection,
    )
    from app.core.dashboard_scope import dashboard_request_identity, dashboard_receivables
    identity = await dashboard_request_identity(dashboard_queue, {"official-fee-unreceived"}, identity, db)
    items = await dashboard_receivables(identity, db) if dashboard_queue else await _receivable_detail_projection(identity, db)
    return {
        "items": items,
        "total": len(items),
        "official_unreceived": round(sum(
            item["remaining_amount"] for item in items if item["fee_category"] == "official"
        ), 2),
    }


@router.get(f"{settings.api_prefix}/finance/invoices")
async def list_invoice_applications(
    scope: str = Query("company", pattern="^(mine|company|pending)$"),
    customer: str = "", application_no: str = "", invoice_type: str = Query("", pattern="^(|普票|专票)$"),
    invoice_title: str = "", invoice_no: str = "", invoice_status: str = "",
    invoiced_from: date | None = None, invoiced_to: date | None = None, case_no: str = "", applicant: str = "",
    page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _invoice_list_rows,
    )
    if invoiced_from and invoiced_to and invoiced_from > invoiced_to:
        raise HTTPException(status_code=422, detail="开票开始日期不能晚于结束日期")
    if scope == "pending":
        from app.core.invoice_permissions import invoice_permissions
        grants = await invoice_permissions(identity, db)
        if not any(grants[scope_name][action] for scope_name in ("firm", "platform") for action in ("review", "issue")):
            raise HTTPException(status_code=403, detail="当前账号没有待处理开票权限")
    rows = await _invoice_list_rows(identity, db, scope=scope, customer=customer, application_no=application_no, invoice_type=invoice_type, invoice_title=invoice_title, invoice_no=invoice_no, invoice_status=invoice_status, invoiced_from=invoiced_from, invoiced_to=invoiced_to, case_no=case_no, applicant_filter=applicant)
    total_amount = round(sum(float((row.get("data") or {}).get("amount", 0) or 0) for row in rows if row.get("status") not in {"已撤回", "已作废"}), 2)
    total_extra_amount = round(sum(float((row.get("data") or {}).get("extra_amount", 0) or 0) for row in rows if row.get("status") not in {"已撤回", "已作废"}), 2)
    start = (page - 1) * page_size
    return {"items": rows[start:start + page_size], "total": len(rows), "total_amount": total_amount, "total_extra_amount": total_extra_amount, "page": page, "page_size": page_size}


@router.get(f"{settings.api_prefix}/finance/invoices/export")
async def export_invoice_applications(
    scope: str = Query("company", pattern="^(mine|company|pending)$"), ids: str = "",
    customer: str = "", application_no: str = "", invoice_type: str = Query("", pattern="^(|普票|专票)$"),
    invoice_title: str = "", invoice_no: str = "", invoice_status: str = "",
    invoiced_from: date | None = None, invoiced_to: date | None = None, case_no: str = "", applicant: str = "",
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _invoice_list_rows,
    )
    from app.core.system import (
        _export_ids,
    )
    selected_ids = set(_export_ids(ids)) if ids.strip() else None
    if scope == "pending":
        from app.core.invoice_permissions import invoice_permissions
        grants = await invoice_permissions(identity, db)
        if not any(grants[scope_name][action] for scope_name in ("firm", "platform") for action in ("review", "issue")):
            raise HTTPException(status_code=403, detail="当前账号没有待处理开票权限")
    rows = await _invoice_list_rows(identity, db, scope=scope, customer=customer, application_no=application_no, invoice_type=invoice_type, invoice_title=invoice_title, invoice_no=invoice_no, invoice_status=invoice_status, invoiced_from=invoiced_from, invoiced_to=invoiced_to, case_no=case_no, applicant_filter=applicant, ids=selected_ids)
    if selected_ids is not None and not rows:
        raise HTTPException(status_code=422, detail="请选择需要导出的发票")
    headers = (
        ["请票单号", "申请人", "客户名称", "开票金额", "高开金额", "开票抬头", "备注"]
        if scope == "pending"
        else ["请票单号", "客户名称", "开票金额", "高开金额", "开票抬头", "发票号码", "申请人", "领票人", "开票日期", "状态"]
        if scope == "company"
        else ["请票单号", "客户名称", "开票金额", "高开金额", "发票编号", "领票人", "开票日期", "票据状态", "备注"]
    )
    def cell(value: object, *, number: bool = False) -> str:
        text_value = f"{float(value or 0):.2f}" if number else str(value or "")
        return f'<Cell><Data ss:Type="{"Number" if number else "String"}">{xml_escape(text_value)}</Data></Cell>'
    sheet_rows = ["<Row>" + "".join(cell(value) for value in headers) + "</Row>"]
    for row in rows:
        data = row.get("data") or {}
        values = (
            [row.get("serial_no"), data.get("applicant"), row.get("customer"), data.get("amount"), data.get("extra_amount"), data.get("invoice_title"), data.get("remark") or row.get("description")]
            if scope == "pending"
            else [row.get("serial_no"), row.get("customer"), data.get("amount"), data.get("extra_amount"), data.get("invoice_title"), data.get("invoice_no"), data.get("applicant"), data.get("recipient"), data.get("invoice_date"), row.get("status")]
            if scope == "company"
            else [row.get("serial_no"), row.get("customer"), data.get("amount"), data.get("extra_amount"), data.get("invoice_no"), data.get("recipient"), data.get("invoice_date"), row.get("status"), data.get("remark") or row.get("description")]
        )
        number_indexes = {3, 4} if scope == "pending" else {2, 3}
        sheet_rows.append("<Row>" + "".join(cell(value, number=index in number_indexes) for index, value in enumerate(values)) + "</Row>")
    sheet_name = "待处理开票" if scope == "pending" else "公司开票" if scope == "company" else "我的开票"
    workbook = '<?xml version="1.0" encoding="UTF-8"?><?mso-application progid="Excel.Sheet"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="' + sheet_name + '"><Table>' + "".join(sheet_rows) + "</Table></Worksheet></Workbook>"
    filename = f"{sheet_name}-{date.today()}.xls"
    disposition = f"attachment; filename=my-invoices.xls; filename*=UTF-8''{quote(filename)}"
    return Response(content=workbook.encode("utf-8"), media_type="application/vnd.ms-excel", headers={"Content-Disposition": disposition})


@router.get(f"{settings.api_prefix}/finance/case-fees/invoice-status")
async def list_invoice_case_fees(
    scope: str = Query("mine", pattern="^(mine|company)$"),
    case_no: str = "", court_case_no: str = "", notary_no: str = "",
    invoice_amount_from: float | None = None, invoice_amount_to: float | None = None,
    customer: str = "", paid_organization: str = "",
    invoice_status: str = Query("未开票", pattern="^(未开票|已开票)$"),
    invoice_from: date | None = None, invoice_to: date | None = None,
    hearing_lawyer: str = "", assistant: str = "", case_stages: str = "",
    paid_from: date | None = None, paid_to: date | None = None,
    fee_types: str = "律师代理费", payer_name: str = "",
    cashed_from: date | None = None, cashed_to: date | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _invoice_case_fee_rows,
    )
    if invoice_amount_from is not None and invoice_amount_to is not None and invoice_amount_from > invoice_amount_to:
        raise HTTPException(status_code=422, detail="开票最小金额不能大于最大金额")
    for start, end, label in [
        (invoice_from, invoice_to, "开票"), (paid_from, paid_to, "付款"), (cashed_from, cashed_to, "到账")
    ]:
        if start and end and start > end:
            raise HTTPException(status_code=422, detail=f"{label}开始日期不能晚于结束日期")
    rows = await _invoice_case_fee_rows(
        identity, db, scope=scope, case_no=case_no, court_case_no=court_case_no,
        notary_no=notary_no, invoice_amount_from=invoice_amount_from,
        invoice_amount_to=invoice_amount_to, customer=customer,
        paid_organization=paid_organization, invoice_status=invoice_status,
        invoice_from=invoice_from, invoice_to=invoice_to,
        hearing_lawyer=hearing_lawyer, assistant=assistant,
        case_stages=case_stages, paid_from=paid_from, paid_to=paid_to,
        fee_types=fee_types, payer_name=payer_name, cashed_from=cashed_from,
        cashed_to=cashed_to,
    )
    totals = {
        "amount": round(sum(float((row.get("data") or {}).get("amount") or 0) for row in rows), 2),
        "invoice_amount": round(sum(float((row.get("data") or {}).get("invoice_amount") or 0) for row in rows), 2),
        "cashed_amount": round(sum(float((row.get("data") or {}).get("cashed_amount") or 0) for row in rows), 2),
        "paid_amount": round(sum(float((row.get("data") or {}).get("paid_amount") or 0) for row in rows), 2),
    }
    start = (page - 1) * page_size
    return {"items": rows[start:start + page_size], "total": len(rows), "totals": totals, "page": page, "page_size": page_size}


@router.get(f"{settings.api_prefix}/finance/case-fees/invoice-status/export")
async def export_invoice_case_fees(
    scope: str = Query("mine", pattern="^(mine|company)$"), ids: str = "",
    case_no: str = "", court_case_no: str = "", notary_no: str = "",
    invoice_amount_from: float | None = None, invoice_amount_to: float | None = None,
    customer: str = "", paid_organization: str = "",
    invoice_status: str = Query("未开票", pattern="^(未开票|已开票)$"),
    invoice_from: date | None = None, invoice_to: date | None = None,
    hearing_lawyer: str = "", assistant: str = "", case_stages: str = "",
    paid_from: date | None = None, paid_to: date | None = None,
    fee_types: str = "律师代理费", payer_name: str = "",
    cashed_from: date | None = None, cashed_to: date | None = None,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _invoice_case_fee_rows,
    )
    from app.core.system import (
        _export_ids,
    )
    selected_ids = set(_export_ids(ids)) if ids.strip() else None
    rows = await _invoice_case_fee_rows(
        identity, db, scope=scope, case_no=case_no, court_case_no=court_case_no,
        notary_no=notary_no, invoice_amount_from=invoice_amount_from,
        invoice_amount_to=invoice_amount_to, customer=customer,
        paid_organization=paid_organization, invoice_status=invoice_status,
        invoice_from=invoice_from, invoice_to=invoice_to,
        hearing_lawyer=hearing_lawyer, assistant=assistant,
        case_stages=case_stages, paid_from=paid_from, paid_to=paid_to,
        fee_types=fee_types, payer_name=payer_name, cashed_from=cashed_from,
        cashed_to=cashed_to, ids=selected_ids,
    )
    if selected_ids is not None and not rows:
        raise HTTPException(status_code=422, detail="请选择需要导出的费用.")
    headers = ["案号", "客户", "案件阶段", "助理", "开庭律师", "法院案号", "费用类型", "金额", "开票日期", "开票金额", "发票查看", "到账时间", "到账金额", "到账单位", "付款时间", "付款金额", "法院名称", "付款状态", "合同号"]
    keys = ["case_no", "customer", "case_stage", "assistant", "hearing_lawyer", "court_case_no", "fee_type", "amount", "invoice_date", "invoice_amount", "invoice_no", "cashed_date", "cashed_amount", "received_payer_name", "paid_date", "paid_amount", "court_name", "payment_status", "contract_no"]
    number_keys = {"amount", "invoice_amount", "cashed_amount", "paid_amount"}
    def cell(value: object, *, number: bool = False) -> str:
        text_value = f"{float(value or 0):.2f}" if number else str(value or "")
        return f'<Cell><Data ss:Type="{"Number" if number else "String"}">{xml_escape(text_value)}</Data></Cell>'
    sheet_rows = ["<Row>" + "".join(cell(value) for value in headers) + "</Row>"]
    for row in rows:
        data = row.get("data") or {}
        values = {**data, "customer": row.get("customer", "")}
        sheet_rows.append("<Row>" + "".join(cell(values.get(key), number=key in number_keys) for key in keys) + "</Row>")
    workbook = '<?xml version="1.0" encoding="UTF-8"?><?mso-application progid="Excel.Sheet"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="未开票"><Table>' + "".join(sheet_rows) + "</Table></Worksheet></Workbook>"
    filename = f"{'公司未开票' if scope == 'company' else '未开票'}-{date.today()}.xls"
    disposition = f"attachment; filename=invoice-case-fees.xls; filename*=UTF-8''{quote(filename)}"
    return Response(content=workbook.encode("utf-8"), media_type="application/vnd.ms-excel", headers={"Content-Disposition": disposition})


@router.get(f"{settings.api_prefix}/finance/case-fees/refunds")
async def query_refund_case_fees(
    case_no: str = "", court_case_no: str = "", court_name: str = "",
    paid_from: date | None = None, paid_to: date | None = None,
    customer: str = "", paid_organization: str = "", refund_status: str = "",
    refund_amount_from: float | None = None, refund_amount_to: float | None = None,
    hearing_lawyer: str = "", assistant: str = "", case_stages: str = "", fee_types: str = "",
    page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=200),
    dashboard_queue: str = "",
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.dashboard_scope import dashboard_request_identity
    identity = await dashboard_request_identity(dashboard_queue, {"refund-pending"}, identity, db)
    from app.core.finance import (
        _refund_case_fee_rows,
    )
    if refund_amount_from is not None and refund_amount_to is not None and refund_amount_from > refund_amount_to:
        raise HTTPException(status_code=422, detail="退费最小金额不能大于最大金额")
    if paid_from and paid_to and paid_from > paid_to:
        raise HTTPException(status_code=422, detail="付款开始日期不能晚于结束日期")
    rows = await _refund_case_fee_rows(
        identity, db, case_no=case_no, court_case_no=court_case_no,
        court_name=court_name, paid_from=paid_from, paid_to=paid_to,
        customer=customer, paid_organization=paid_organization,
        refund_status=refund_status, refund_amount_from=refund_amount_from,
        refund_amount_to=refund_amount_to, hearing_lawyer=hearing_lawyer,
        assistant=assistant, case_stages=case_stages, fee_types=fee_types,
    )
    start = (page - 1) * page_size
    from app.core.dashboard_scope import dashboard_fee_cases
    related = await dashboard_fee_cases(rows[start:start + page_size], identity, db) if dashboard_queue else {}
    return {**related, "items": rows[start:start + page_size], "total": len(rows), "page": page, "page_size": page_size}


@router.post(f"{settings.api_prefix}/finance/case-fees/batch-update")
async def batch_update_case_fee_inform_date(
    body: CaseFeeBatchUpdateInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _record_scope_conditions, _require_record_module_menu,
    )
    await _require_record_module_menu("finance", identity, db, action="编辑")
    fee_ids = list(dict.fromkeys(body.fee_ids))
    items = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance",
        BusinessRecord.id.in_(fee_ids),
        *(await _record_scope_conditions(identity, db)),
    ).order_by(BusinessRecord.id))).all())
    if len(items) != len(fee_ids):
        raise HTTPException(status_code=404, detail="部分案件费用不存在或无权访问")

    inform_date = body.inform_date.isoformat()
    for item in items:
        await _require_linked_case_fee_action(item, "case.fee.notice", identity, db)
        data = dict(item.data or {})
        previous_inform_date = str(data.get("inform_date") or "").strip()
        data["inform_date"] = inform_date
        item.data = data
        db.add(WorkflowEvent(
            record_id=item.id,
            action="批量修改通知日期",
            from_status=item.status,
            to_status=item.status,
            operator=identity["username"],
            comment=f"通知日期：{previous_inform_date or '未设置'} -> {inform_date}",
        ))
    await db.commit()
    return {"updated": len(items), "fee_ids": fee_ids, "inform_date": inform_date}


@router.get(f"{settings.api_prefix}/finance/case-fees/refunds/export")
async def export_refund_case_fees(
    ids: str = "", case_no: str = "", court_case_no: str = "", court_name: str = "",
    paid_from: date | None = None, paid_to: date | None = None,
    customer: str = "", paid_organization: str = "", refund_status: str = "",
    refund_amount_from: float | None = None, refund_amount_to: float | None = None,
    hearing_lawyer: str = "", assistant: str = "", case_stages: str = "", fee_types: str = "",
    dashboard_queue: str = "",
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.dashboard_scope import dashboard_request_identity
    identity = await dashboard_request_identity(dashboard_queue, {"refund-pending"}, identity, db)
    from app.core.finance import (
        _refund_case_fee_rows,
    )
    from app.core.system import (
        _export_ids,
    )
    selected_ids = set(_export_ids(ids)) if ids.strip() else None
    rows = await _refund_case_fee_rows(
        identity, db, case_no=case_no, court_case_no=court_case_no,
        court_name=court_name, paid_from=paid_from, paid_to=paid_to,
        customer=customer, paid_organization=paid_organization,
        refund_status=refund_status, refund_amount_from=refund_amount_from,
        refund_amount_to=refund_amount_to, hearing_lawyer=hearing_lawyer,
        assistant=assistant, case_stages=case_stages, fee_types=fee_types, ids=selected_ids,
    )
    if selected_ids is not None and len(rows) != len(selected_ids):
        raise HTTPException(status_code=422, detail="部分退费记录不存在或无权导出")
    if not rows:
        raise HTTPException(status_code=422, detail="当前没有可导出的退费记录")
    headers = ["案号", "原告", "被告", "案件阶段", "律师助理", "开庭律师", "费用类型", "金额", "退费金额", "新建时间", "法院名称", "退费进度", "进度时长"]
    keys = ["case_no", "plaintiff", "opponent", "case_stage", "assistant", "hearing_lawyer", "fee_type", "amount", "refund_requested_amount", "created_at", "court_name", "refund_status_label", "refund_progress_days"]
    number_keys = {"amount", "refund_requested_amount", "refund_progress_days"}
    sheet_rows = ["<Row>" + "".join(f'<Cell><Data ss:Type="String">{xml_escape(value)}</Data></Cell>' for value in headers) + "</Row>"]
    for row in rows:
        data = row.get("data") or {}
        cells = []
        for key in keys:
            value = data.get(key)
            cell_type = "Number" if key in number_keys and value is not None else "String"
            cells.append(f'<Cell><Data ss:Type="{cell_type}">{xml_escape(str(value if value is not None else ""))}</Data></Cell>')
        sheet_rows.append("<Row>" + "".join(cells) + "</Row>")
    workbook = '<?xml version="1.0" encoding="UTF-8"?><?mso-application progid="Excel.Sheet"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="退费查询"><Table>' + "".join(sheet_rows) + "</Table></Worksheet></Workbook>"
    disposition = f"attachment; filename=refund-case-fees.xls; filename*=UTF-8''{quote(f'退费查询-{date.today()}.xls')}"
    return Response(content=workbook.encode("utf-8"), media_type="application/vnd.ms-excel", headers={"Content-Disposition": disposition})


@router.post(f"{settings.api_prefix}/finance/case-fees/refunds/status")
async def update_refund_case_fee_status(
    body: RefundBatchStatusInput,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _editable_refund_case_fees, _refund_case_fee_status,
    )
    from app.core.permissions import (
        _permission_payload_for_identity,
    )
    value = str(body.status).strip()
    code = value.upper() if value.upper() in REFUND_CASE_FEE_STATUSES else REFUND_CASE_FEE_STATUS_BY_LABEL.get(value, "")
    if not code:
        raise HTTPException(status_code=422, detail="退费进度无效")
    if code == "R100" and identity.get("role") not in {"admin", "manager"}:
        permission = await _permission_payload_for_identity(identity, db)
        if "*" not in permission.get("action_keys", []) and "finance.refund.not_required" not in permission.get("action_keys", []):
            raise HTTPException(status_code=403, detail="当前角色没有标记不再办理退费的权限")
    items = await _editable_refund_case_fees(body.ids, identity, db)
    changed_at = datetime.now().isoformat(timespec="seconds")
    for item in items:
        await _require_linked_case_fee_action(item, "case.fee.refund", identity, db)
        data = dict(item.data or {})
        previous_code, previous_label = _refund_case_fee_status(data)
        data.update({
            "refund_status": code,
            "refund_status_label": REFUND_CASE_FEE_STATUSES[code],
            "refund_status_started_at": changed_at,
            "refund_not_required": code == "R100",
        })
        item.data = data
        db.add(WorkflowEvent(
            record_id=item.id, action="标记不再办理退费" if code == "R100" else "修改退费进度",
            from_status=previous_label, to_status=REFUND_CASE_FEE_STATUSES[code],
            operator=identity["username"], comment=body.comment.strip(),
        ))
    await db.commit()
    return {"updated": len(items), "status": code, "status_label": REFUND_CASE_FEE_STATUSES[code]}


@router.post(f"{settings.api_prefix}/finance/case-fees/refunds/logs")
async def add_refund_case_fee_logs(
    body: CaseFeeRefundLogInput,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _editable_refund_case_fees,
    )
    from app.core.refund_logs import REFUND_LOG_LABELS, refund_fee_case
    items = await _editable_refund_case_fees(body.ids, identity, db)
    for item in items:
        await _require_linked_case_fee_action(item, "case.fee.refund", identity, db)
        data = item.data or {}
        label = REFUND_LOG_LABELS[body.kind]
        case_record = await refund_fee_case(item, db)
        log_record = BusinessRecord(
            module="case_log", serial_no=f"CASELOG-{uuid4().hex.upper()}", title=f"{label}退费日志",
            customer=item.customer, status="有效", owner=identity["username"], department=item.department,
            description=body.content.strip(), data={
                "kind": "refund", "refund_type": body.kind, "case_fee_id": item.id,
                "case_id": case_record.id if case_record else None,
                "case_no": case_record.serial_no if case_record else str(data.get("case_no") or ""),
            },
        )
        event = WorkflowEvent(
            record_id=item.id, action=f"添加{label}退费日志", operator=identity["username"],
            comment=body.content.strip(),
        )
        db.add_all([log_record, event])
        await db.flush()
        log_record.data = {**log_record.data, "workflow_event_id": event.id}
    await db.commit()
    return {"created": len(items), "kind": body.kind}


@router.get(f"{settings.api_prefix}/finance/case-fees/refunds/logs")
async def list_refund_case_fee_logs(
    fee_id: int = Query(..., ge=1),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import _ensure_record_module
    from app.core.refund_logs import refund_fee_log_items
    fee = await _ensure_record_module(fee_id, "finance", identity, db)
    result_items = await refund_fee_log_items(fee, db)
    return {"items": result_items, "total": len(result_items)}


@router.get(f"{settings.api_prefix}/finance/fees/query")
async def query_finance_fees(
    scope: str = Query("company", pattern="^(mine|company)$"),
    unpaid_official: bool = False,
    external_only: bool = False,
    case_no: str = "", court_case_no: str = "", notary_no: str = "",
    refund_amount_from: float | None = None, refund_amount_to: float | None = None,
    customer: str = "", paid_organization: str = "",
    payment_status: str = Query("", pattern="^(|创建待提交|待审批|待付款|待核销|已付款|已驳回|已作废)$"),
    paid_from: date | None = None, paid_to: date | None = None,
    hearing_lawyer: str = "", assistant: str = "", case_stages: str = "", fee_types: str = "",
    page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=200),
    dashboard_queue: str = "",
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.dashboard_scope import dashboard_request_identity
    identity = await dashboard_request_identity(dashboard_queue, {"official-fee-unpaid"}, identity, db)
    if dashboard_queue:
        unpaid_official = True
    from app.core.finance import (
        _fee_query_rows,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    if refund_amount_from is not None and refund_amount_to is not None and refund_amount_from > refund_amount_to:
        raise HTTPException(status_code=422, detail="退费最小金额不能大于最大金额")
    if paid_from and paid_to and paid_from > paid_to:
        raise HTTPException(status_code=422, detail="付款开始日期不能晚于结束日期")
    rows = await _fee_query_rows(
        identity, db, scope=scope, unpaid_official=unpaid_official, external_only=external_only,
        case_no=case_no, court_case_no=court_case_no,
        notary_no=notary_no, refund_amount_from=refund_amount_from,
        refund_amount_to=refund_amount_to, customer=customer,
        paid_organization=paid_organization, payment_status=payment_status,
        paid_from=paid_from, paid_to=paid_to, hearing_lawyer=hearing_lawyer,
        assistant=assistant, case_stages=case_stages, fee_types=fee_types,
    )
    amount_visible = "finance.amount" in await _allowed_field_keys(identity, db)
    totals = {
        key: round(sum(float((row.get("data") or {}).get(key) or 0) for row in rows), 2) if amount_visible else None
        for key in ("amount", "refund_requested_amount", "refunded_amount", "cashed_amount", "paid_amount")
    }
    start = (page - 1) * page_size
    from app.core.dashboard_scope import dashboard_fee_cases
    related = await dashboard_fee_cases(rows[start:start + page_size], identity, db) if dashboard_queue else {}
    return {**related, "items": rows[start:start + page_size], "total": len(rows), "totals": totals, "page": page, "page_size": page_size}


@router.get(f"{settings.api_prefix}/finance/fees/query/export")
async def export_finance_fee_query(
    ids: str = "", selected_only: bool = False,
    scope: str = Query("company", pattern="^(mine|company)$"),
    unpaid_official: bool = False,
    external_only: bool = False,
    case_no: str = "", court_case_no: str = "", notary_no: str = "",
    refund_amount_from: float | None = None, refund_amount_to: float | None = None,
    customer: str = "", paid_organization: str = "", payment_status: str = "",
    paid_from: date | None = None, paid_to: date | None = None,
    hearing_lawyer: str = "", assistant: str = "", case_stages: str = "", fee_types: str = "",
    dashboard_queue: str = "",
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.dashboard_scope import dashboard_request_identity
    identity = await dashboard_request_identity(dashboard_queue, {"official-fee-unpaid"}, identity, db)
    if dashboard_queue:
        unpaid_official = True
    from app.core.finance import (
        _fee_query_rows,
    )
    from app.core.system import (
        _export_ids,
    )
    if refund_amount_from is not None and refund_amount_to is not None and refund_amount_from > refund_amount_to:
        raise HTTPException(status_code=422, detail="退费最小金额不能大于最大金额")
    if paid_from and paid_to and paid_from > paid_to:
        raise HTTPException(status_code=422, detail="付款开始日期不能晚于结束日期")
    if payment_status not in {"", "创建待提交", "待审批", "待付款", "待核销", "已付款", "已驳回", "已作废"}:
        raise HTTPException(status_code=422, detail="付款状态无效")
    selected_ids = set(_export_ids(ids)) if ids.strip() else None
    if selected_only and not selected_ids:
        raise HTTPException(status_code=422, detail="请选择需要导出的费用.")
    rows = await _fee_query_rows(
        identity, db, scope=scope, unpaid_official=unpaid_official, external_only=external_only,
        case_no=case_no, court_case_no=court_case_no,
        notary_no=notary_no, refund_amount_from=refund_amount_from,
        refund_amount_to=refund_amount_to, customer=customer,
        paid_organization=paid_organization, payment_status=payment_status,
        paid_from=paid_from, paid_to=paid_to, hearing_lawyer=hearing_lawyer,
        assistant=assistant, case_stages=case_stages, fee_types=fee_types,
        ids=selected_ids,
    )
    if selected_ids is not None and len(rows) != len(selected_ids):
        raise HTTPException(status_code=422, detail="部分费用不存在或无权导出")
    if not rows:
        raise HTTPException(status_code=422, detail="当前没有可导出的费用")
    headers = ["案号", "客户", "案件阶段", "助理", "开庭律师", "法院案号", "费用类型", "金额", "退费金额", "已退金额", "到账时间", "到账金额", "付款时间", "付款金额", "法院名称", "付款状态"]
    keys = ["case_no", "customer", "case_stage", "assistant", "hearing_lawyer", "court_case_no", "fee_type", "amount", "refund_requested_amount", "refunded_amount", "cashed_date", "cashed_amount", "paid_date", "paid_amount", "court_name", "payment_status"]
    number_keys = {"amount", "refund_requested_amount", "refunded_amount", "cashed_amount", "paid_amount"}
    def cell(value: object, *, number: bool = False) -> str:
        text_value = f"{float(value):.2f}" if number and value is not None else str(value or "")
        return f'<Cell><Data ss:Type="{"Number" if number and value is not None else "String"}">{xml_escape(text_value)}</Data></Cell>'
    sheet_rows = ["<Row>" + "".join(cell(value) for value in headers) + "</Row>"]
    for row in rows:
        data = row.get("data") or {}
        values = {**data, "customer": row.get("customer", "")}
        sheet_rows.append("<Row>" + "".join(cell(values.get(key), number=key in number_keys) for key in keys) + "</Row>")
    workbook = '<?xml version="1.0" encoding="UTF-8"?><?mso-application progid="Excel.Sheet"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="费用查询"><Table>' + "".join(sheet_rows) + "</Table></Worksheet></Workbook>"
    filename = f"费用查询-{date.today()}.xls"
    disposition = f"attachment; filename=finance-fee-query.xls; filename*=UTF-8''{quote(filename)}"
    return Response(content=workbook.encode("utf-8"), media_type="application/vnd.ms-excel", headers={"Content-Disposition": disposition})


from app.areas.finance.invoice_operations import (
    router as invoice_operations_router,
    _invoice_source_metadata as _invoice_source_metadata,
    _invoice_current_external_number as _invoice_current_external_number,
    create_invoice_application as create_invoice_application,
    update_invoice_application as update_invoice_application,
    submit_invoice_application as submit_invoice_application,
    withdraw_invoice_application as withdraw_invoice_application,
    review_invoice_application as review_invoice_application,
    issue_invoice as issue_invoice,
    reject_invoice_issue as reject_invoice_issue,
    void_invoice as void_invoice,
    change_invoice_number as change_invoice_number,
    change_invoice_date as change_invoice_date,
)
router.include_router(invoice_operations_router)


from app.areas.finance.refund_operations import (
    router as refund_operations_router,
    query_refund_applications as query_refund_applications,
    export_refund_applications as export_refund_applications,
    export_selected_refund_applications as export_selected_refund_applications,
    update_refund_amount as update_refund_amount,
    batch_refund_status as batch_refund_status,
    reset_finance_fee_court_refund as reset_finance_fee_court_refund,
    create_litigation_refund as create_litigation_refund,
    submit_litigation_refund as submit_litigation_refund,
    review_litigation_refund as review_litigation_refund,
    complete_litigation_refund as complete_litigation_refund,
)
router.include_router(refund_operations_router)


@router.get(f"{settings.api_prefix}/finance/internal-fees")
async def list_internal_fees(
    scope: str = Query("company", pattern="^(mine|company|applications)$"),
    case_no: str = "", handling_lawyer: str = "", assistant: str = "", source_person: str = "",
    customer: str = "", customer_manager: str = "", investigator: str = "", payment_status: str = Query("", pattern="^(|已付|未付)$"),
    paid_from: date | None = None, paid_to: date | None = None, payee: str = "", case_stages: str = "", fee_types: str = "",
    page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _internal_fee_rows,
    )
    if paid_from and paid_to and paid_from > paid_to:
        raise HTTPException(status_code=422, detail="付款开始日期不能晚于结束日期")
    rows = await _internal_fee_rows(identity, db, scope=scope, case_no=case_no, handling_lawyer=handling_lawyer, assistant=assistant, source_person=source_person, customer=customer, customer_manager=customer_manager, investigator=investigator, payment_status=payment_status, paid_from=paid_from, paid_to=paid_to, payee=payee, case_stages=case_stages, fee_types=fee_types)
    total = len(rows)
    total_amount = round(sum(float((row.get("data") or {}).get("amount", 0) or 0) for row in rows), 2)
    start = (page - 1) * page_size
    return {"items": rows[start:start + page_size], "total": total, "total_amount": total_amount, "page": page, "page_size": page_size}


@router.get(f"{settings.api_prefix}/finance/internal-review-requests")
async def list_internal_review_requests(
    kind: str = Query(pattern="^(commission|other|refund)$"),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.internal_requests import internal_review_rows

    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(403, "当前角色没有内部请款审批权限")
    rows = await internal_review_rows(identity, db, kind)
    return {"items": rows, "total": len(rows)}


@router.post(f"{settings.api_prefix}/finance/internal-applications/{{fee_id}}/{{action}}")
async def change_internal_payment_application(
    fee_id: int, action: str, body: FinancePaymentCancelInput,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.internal_requests import change_internal_application

    if action not in {"withdraw", "rollback"}:
        raise HTTPException(404, "请款单操作不存在")
    return await change_internal_application(fee_id, action, body.reason, identity, db)


@router.post(f"{settings.api_prefix}/finance/internal-applications/batch-review")
async def batch_review_internal_applications(
    body: FinanceFeeBatchReviewInput,
    kind: str = Query(pattern="^(commission|other|refund)$"),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.internal_requests import review_internal_applications

    return await review_internal_applications(body.fee_ids, kind, body.approved, body.comment, identity, db)


@router.get(f"{settings.api_prefix}/finance/internal-fees/export")
async def export_internal_fees(
    scope: str = Query("company", pattern="^(mine|company|applications)$"), ids: str = "",
    case_no: str = "", handling_lawyer: str = "", assistant: str = "", source_person: str = "",
    customer: str = "", customer_manager: str = "", investigator: str = "", payment_status: str = Query("", pattern="^(|已付|未付)$"),
    paid_from: date | None = None, paid_to: date | None = None, payee: str = "", case_stages: str = "", fee_types: str = "",
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _internal_fee_rows,
    )
    from app.core.system import (
        _export_ids,
    )
    selected_ids = set(_export_ids(ids)) if ids.strip() else None
    rows = await _internal_fee_rows(identity, db, scope=scope, case_no=case_no, handling_lawyer=handling_lawyer, assistant=assistant, source_person=source_person, customer=customer, customer_manager=customer_manager, investigator=investigator, payment_status=payment_status, paid_from=paid_from, paid_to=paid_to, payee=payee, case_stages=case_stages, fee_types=fee_types, ids=selected_ids)
    if selected_ids is not None and not rows:
        raise HTTPException(status_code=422, detail="请选择需要导出的费用")
    headers = ["案号", "案件阶段", "原告", "被告", "经办律师", "律师助理", "案源人", "调查人", "归档时间", "申请时间", "内部费用类型", "金额", "收款人", "支付状态"]
    keys = ["case_no", "case_stage", "plaintiff", "defendant", "handling_lawyer", "lawyer_assistant", "case_source", "investigator", "archive_date", "application_date", "internal_fee_type", "amount", "payee", "payment_status"]
    def cell(value: object, *, number: bool = False) -> str:
        text_value = f"{float(value or 0):.2f}" if number else str(value or "")[:10] if isinstance(value, (date, datetime)) else str(value or "")
        data_type = "Number" if number else "String"
        return f'<Cell><Data ss:Type="{data_type}">{xml_escape(text_value)}</Data></Cell>'
    sheet_rows = ["<Row>" + "".join(cell(value) for value in headers) + "</Row>"]
    for row in rows:
        data = row.get("data") or {}
        sheet_rows.append("<Row>" + "".join(cell(data.get(key), number=key == "amount") for key in keys) + "</Row>")
    workbook = '<?xml version="1.0" encoding="UTF-8"?><?mso-application progid="Excel.Sheet"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="内部费用明细"><Table>' + "".join(sheet_rows) + "</Table></Worksheet></Workbook>"
    filename = f"内部费用明细-{date.today()}.xls"
    disposition = f"attachment; filename=internal-fees.xls; filename*=UTF-8''{quote(filename)}"
    return Response(content=workbook.encode("utf-8"), media_type="application/vnd.ms-excel", headers={"Content-Disposition": disposition})


@router.get(f"{settings.api_prefix}/finance/legacy-history")
async def list_legacy_finance_history(
    record_kind: str = Query(
        "",
        pattern="^(|ap_payment|ar_payment|invoice|ap_packing|case_fee|internal_fee|internal_payment|internal_packing)$",
    ),
    status_code: str = "", audit_status_code: str = "", keyword: str = "", include_inactive: bool = False,
    page: int = Query(1, ge=1), page_size: int = Query(30, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """Read-only source-of-truth ledger imported from legacy FAM tables."""
    from app.core.legacy_sync import (
        _legacy_finance_audit_table_exists, _legacy_finance_record_dict, _legacy_finance_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    conditions = await _legacy_finance_scope_conditions(identity, db)
    audit_table_exists = await _legacy_finance_audit_table_exists(db)
    if record_kind:
        conditions.append(LegacyFinanceRecord.record_kind == record_kind)
    if status_code.strip():
        conditions.append(LegacyFinanceRecord.status_code == status_code.strip())
    if audit_status_code.strip() and audit_table_exists:
        conditions.append(LegacyFinanceRecord.id.in_(
            select(LegacyFinanceAudit.legacy_finance_record_id).where(
                LegacyFinanceAudit.audit_status_code == audit_status_code.strip(),
                LegacyFinanceAudit.legacy_finance_record_id.is_not(None),
            )
        ))
    elif audit_status_code.strip():
        conditions.append(false())
    if not include_inactive:
        conditions.append(LegacyFinanceRecord.is_active.is_(True))
    if keyword.strip():
        needle = f"%{keyword.strip()}%"
        conditions.append(or_(
            LegacyFinanceRecord.legacy_id.like(needle),
            LegacyFinanceRecord.legacy_contract_no.like(needle),
            LegacyFinanceRecord.legacy_case_no.like(needle),
            LegacyFinanceRecord.legacy_customer_no.like(needle),
        ))
    total = int(await db.scalar(select(func.count()).select_from(LegacyFinanceRecord).where(*conditions)) or 0)
    rows = list((await db.scalars(
        select(LegacyFinanceRecord).where(*conditions).order_by(
            LegacyFinanceRecord.updated_at.desc(), LegacyFinanceRecord.id.desc()
        ).offset((page - 1) * page_size).limit(page_size)
    )).all())
    ids = [item.id for item in rows]
    allocation_counts = dict((await db.execute(
        select(LegacyFinanceAllocation.legacy_finance_record_id, func.count())
        .where(LegacyFinanceAllocation.legacy_finance_record_id.in_(ids))
        .group_by(LegacyFinanceAllocation.legacy_finance_record_id)
    )).all()) if ids else {}
    file_counts = dict((await db.execute(
        select(LegacyFinanceFile.legacy_finance_record_id, func.count())
        .where(LegacyFinanceFile.legacy_finance_record_id.in_(ids))
        .group_by(LegacyFinanceFile.legacy_finance_record_id)
    )).all()) if ids and audit_table_exists else {}
    audit_counts = dict((await db.execute(
        select(LegacyFinanceAudit.legacy_finance_record_id, func.count())
        .where(LegacyFinanceAudit.legacy_finance_record_id.in_(ids))
        .group_by(LegacyFinanceAudit.legacy_finance_record_id)
    )).all()) if ids and audit_table_exists else {}
    show_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    return {
        "items": [
            _legacy_finance_record_dict(
                item,
                allocation_count=int(allocation_counts.get(item.id, 0)),
                file_count=int(file_counts.get(item.id, 0)),
                audit_count=int(audit_counts.get(item.id, 0)),
                show_amount=show_amount,
            ) for item in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "amount_visible": show_amount,
        "read_only": True,
    }


@router.get(f"{settings.api_prefix}/finance/legacy-history/summary")
async def legacy_finance_history_summary(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.legacy_sync import (
        _legacy_finance_audit_table_exists, _legacy_finance_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    conditions = await _legacy_finance_scope_conditions(identity, db)
    audit_table_exists = await _legacy_finance_audit_table_exists(db)
    summary_rows = (await db.execute(
        select(
            LegacyFinanceRecord.record_kind,
            LegacyFinanceRecord.is_active,
            func.count(),
            func.coalesce(func.sum(LegacyFinanceRecord.primary_amount), 0),
        ).where(*conditions).group_by(LegacyFinanceRecord.record_kind, LegacyFinanceRecord.is_active)
    )).all()
    allocation_rows = (await db.execute(
        select(
            LegacyFinanceRecord.record_kind,
            LegacyFinanceAllocation.allocation_kind,
            LegacyFinanceAllocation.is_refund,
            func.count(),
            func.coalesce(func.sum(LegacyFinanceAllocation.amount), 0),
        ).join(
            LegacyFinanceRecord,
            LegacyFinanceAllocation.legacy_finance_record_id == LegacyFinanceRecord.id,
        ).where(*conditions).group_by(
            LegacyFinanceRecord.record_kind,
            LegacyFinanceAllocation.allocation_kind,
            LegacyFinanceAllocation.is_refund,
        )
    )).all()
    audit_rows = (await db.execute(
        select(
            LegacyFinanceRecord.record_kind,
            LegacyFinanceAudit.audit_status_code,
            func.count(),
        ).join(
            LegacyFinanceRecord,
            LegacyFinanceAudit.legacy_finance_record_id == LegacyFinanceRecord.id,
        ).where(*conditions).group_by(
            LegacyFinanceRecord.record_kind,
            LegacyFinanceAudit.audit_status_code,
        )
    )).all() if audit_table_exists else []
    orphan_allocation_rows = (await db.execute(
        select(
            LegacyFinanceAllocation.allocation_kind,
            LegacyFinanceAllocation.is_refund,
            LegacyFinanceAllocation.orphan_reason,
            func.count(),
            func.coalesce(func.sum(LegacyFinanceAllocation.amount), 0),
        ).where(LegacyFinanceAllocation.legacy_finance_record_id.is_(None)).group_by(
            LegacyFinanceAllocation.allocation_kind,
            LegacyFinanceAllocation.is_refund,
            LegacyFinanceAllocation.orphan_reason,
        )
    )).all() if identity.get("role") in {"admin", "auditor"} else []
    orphan_file_rows = (await db.execute(
        select(
            LegacyFinanceFile.orphan_reason,
            func.count(),
            func.coalesce(func.sum(LegacyFinanceFile.file_amount), 0),
        ).where(LegacyFinanceFile.legacy_finance_record_id.is_(None)).group_by(
            LegacyFinanceFile.orphan_reason,
        )
    )).all() if identity.get("role") in {"admin", "auditor"} else []
    orphan_audit_rows = (await db.execute(
        select(
            LegacyFinanceAudit.audit_kind,
            LegacyFinanceAudit.audit_status_code,
            LegacyFinanceAudit.orphan_reason,
            func.count(),
        ).where(LegacyFinanceAudit.legacy_finance_record_id.is_(None)).group_by(
            LegacyFinanceAudit.audit_kind,
            LegacyFinanceAudit.audit_status_code,
            LegacyFinanceAudit.orphan_reason,
        )
    )).all() if audit_table_exists and identity.get("role") in {"admin", "auditor"} else []
    show_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    return {
        "records": [
            {
                "record_kind": kind,
                "is_active": bool(active),
                "count": int(count),
                "primary_amount": round(float(amount or 0), 2) if show_amount else None,
            }
            for kind, active, count, amount in summary_rows
        ],
        "allocations": [
            {
                "record_kind": record_kind,
                "allocation_kind": allocation_kind,
                "is_refund": bool(is_refund),
                "count": int(count),
                "amount": round(float(amount or 0), 2) if show_amount else None,
            }
            for record_kind, allocation_kind, is_refund, count, amount in allocation_rows
        ],
        "audits": [
            {
                "record_kind": record_kind,
                "audit_status_code": audit_status_code,
                "count": int(count),
            }
            for record_kind, audit_status_code, count in audit_rows
        ],
        "orphan_allocations": [
            {
                "allocation_kind": allocation_kind,
                "is_refund": bool(is_refund),
                "orphan_reason": orphan_reason,
                "count": int(count),
                "amount": round(float(amount or 0), 2) if show_amount else None,
            }
            for allocation_kind, is_refund, orphan_reason, count, amount in orphan_allocation_rows
        ],
        "orphan_files": [
            {
                "orphan_reason": orphan_reason,
                "count": int(count),
                "file_amount": round(float(amount or 0), 2) if show_amount else None,
            }
            for orphan_reason, count, amount in orphan_file_rows
        ],
        "orphan_audits": [
            {
                "audit_kind": audit_kind,
                "audit_status_code": audit_status_code,
                "orphan_reason": orphan_reason,
                "count": int(count),
            }
            for audit_kind, audit_status_code, orphan_reason, count in orphan_audit_rows
        ],
        "amount_visible": show_amount,
        "read_only": True,
    }


@router.get(f"{settings.api_prefix}/finance/legacy-history/{{record_id}}")
async def get_legacy_finance_history_record(
    record_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.formatters import (
        _person_reference_display, _user_display_map,
    )
    from app.core.legacy_sync import (
        _legacy_finance_audit_table_exists, _legacy_finance_record_dict, _legacy_finance_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    conditions = await _legacy_finance_scope_conditions(identity, db)
    item = await db.scalar(select(LegacyFinanceRecord).where(LegacyFinanceRecord.id == record_id, *conditions))
    if not item:
        raise HTTPException(status_code=404, detail="历史财务记录不存在或无权查看")
    allocations = list((await db.scalars(select(LegacyFinanceAllocation).where(
        LegacyFinanceAllocation.legacy_finance_record_id == item.id
    ).order_by(LegacyFinanceAllocation.id))).all())
    files = list((await db.scalars(select(LegacyFinanceFile).where(
        LegacyFinanceFile.legacy_finance_record_id == item.id
    ).order_by(LegacyFinanceFile.id))).all())
    audit_table_exists = await _legacy_finance_audit_table_exists(db)
    audits = list((await db.scalars(select(LegacyFinanceAudit).where(
        LegacyFinanceAudit.legacy_finance_record_id == item.id
    ).order_by(LegacyFinanceAudit.audit_date, LegacyFinanceAudit.id))).all()) if audit_table_exists else []
    audit_display_users = await _user_display_map({row.auditor for row in audits}, db)
    show_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    result = _legacy_finance_record_dict(
        item, allocation_count=len(allocations), file_count=len(files), audit_count=len(audits), show_amount=show_amount, include_payload=True,
    )
    result["read_only"] = True
    result["allocations"] = [
        {
            "id": row.id, "source_table": row.source_table, "legacy_key": row.legacy_key,
            "allocation_kind": row.allocation_kind, "legacy_case_id": row.legacy_case_id,
            "legacy_case_no": row.legacy_case_no, "legacy_case_fee_id": row.legacy_case_fee_id,
            "amount": round(float(row.amount or 0), 2) if show_amount else None,
            "prepaid_amount": round(float(row.prepaid_amount or 0), 2) if show_amount else None,
            "settlement_amount": round(float(row.settlement_amount or 0), 2) if show_amount else None,
            "archive_amount": round(float(row.archive_amount or 0), 2) if show_amount else None,
            "is_refund": row.is_refund, "is_active": row.is_active,
            "case_record_id": row.case_record_id, "mapping_status": row.mapping_status,
            "source_payload": row.source_payload or {},
        } for row in allocations
    ]
    result["files"] = [
        {
            "id": row.id, "legacy_key": row.legacy_key, "legacy_case_fee_id": row.legacy_case_fee_id,
            "filename": row.filename, "size_bytes": row.size_bytes,
            "file_amount": round(float(row.file_amount or 0), 2) if show_amount else None,
            "invoice_date": row.invoice_date.isoformat() if row.invoice_date else None,
            "is_active": row.is_active, "physical_file_verified": row.physical_file_verified,
            "source_payload": row.source_payload or {},
        } for row in files
    ]
    result["legacy_statuses"] = {
        key: value for key, value in (item.source_payload or {}).items()
        if key in {"CaseFeeStatus", "RefundStatus", "SettlementStatus", "PaymentStatus", "InvoiceStatus", "PackingStatus"}
    }
    result["legacy_amounts"] = {
        key: value for key, value in (item.source_payload or {}).items()
        if key in {
            "Amount", "CashedAmount", "InvoicedAmount", "PaidAmount", "PrePaidAmount", "RefundAmount", "RefundedAmount",
            "AppliedAmount", "CaseOfficeFeeAppliedAmount", "CaseNonOfficeFeeAppliedAmount", "CaseCommissionFeeAppliedAmount",
            "CaseFeeSettlementAmount", "CaseNonOfficeFeeSettlementAmount", "CaseFeeArchiveAmount", "InvoiceAmount", "InvoiceOverAmount",
            "CaseOfficeFeeAmount", "CaseNonOfficeFeeAmount", "CaseCommissionFeeAmount",
        }
    }
    result["audits"] = [
        {
            "id": row.id, "source_table": row.source_table, "legacy_id": row.legacy_id,
            "parent_legacy_id": row.parent_legacy_id, "audit_kind": row.audit_kind,
            "audit_status_code": row.audit_status_code, "audit_flow_id": row.audit_flow_id,
            "audit_flow_node_id": row.audit_flow_node_id, "audit_round_id": row.audit_round_id,
            "auditor": row.auditor,
            "auditor_display_name": _person_reference_display(row.auditor, audit_display_users)[0],
            "audit_date": row.audit_date.isoformat() if row.audit_date else None,
            "audit_content": row.audit_content, "source_payload": row.source_payload or {},
        } for row in audits
    ]
    return result


@router.get(f"{settings.api_prefix}/finance/summary")
async def finance_summary(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance_readmodel import read_finance_summary

    return await read_finance_summary(identity, db)


from app.areas.finance.incoming_payments import (
    router as incoming_payments_router,
    list_incoming_payments as list_incoming_payments,
    list_finance_customer_options as list_finance_customer_options,
    create_incoming_payment as create_incoming_payment,
    import_incoming_payments as import_incoming_payments,
    export_incoming_payments as export_incoming_payments,
    get_incoming_payment as get_incoming_payment,
    view_assigned_incoming_payment as view_assigned_incoming_payment,
    claim_incoming_payment as claim_incoming_payment,
    incoming_payment_allocation_candidates as incoming_payment_allocation_candidates,
    allocate_incoming_payment as allocate_incoming_payment,
    delete_incoming_payment as delete_incoming_payment,
    update_incoming_payment as update_incoming_payment,
    incoming_payment_refund_candidates as incoming_payment_refund_candidates,
    refund_claim_incoming_payment as refund_claim_incoming_payment,
    revoke_incoming_payment_allocations as revoke_incoming_payment_allocations,
    get_allocation_records as get_allocation_records,
    cancel_selected_allocations as cancel_selected_allocations,
)
router.include_router(incoming_payments_router)


@router.get(f"{settings.api_prefix}/finance/ar-summary")
async def finance_ar_summary(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _receivable_dict, _round_fee_amount,
    )
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    visible_contract_ids = select(BusinessRecord.id).where(
        BusinessRecord.module == "contract", *(await _record_scope_conditions(identity, db)),
    )
    plans = (await db.scalars(select(ReceivablePlan).where(
        ReceivablePlan.contract_record_id.in_(visible_contract_ids),
    ).order_by(ReceivablePlan.due_date.asc(), ReceivablePlan.id.asc()))).all()
    contract_ids = {plan.contract_record_id for plan in plans}
    contracts = {record.id: record for record in (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "contract",
        BusinessRecord.id.in_(contract_ids),
    ))).all()} if contract_ids else {}
    attachments = (await db.scalars(select(FileAttachment).where(
        FileAttachment.record_id.in_(set(contracts)),
        FileAttachment.category == "合同附件",
    ).order_by(FileAttachment.created_at.asc(), FileAttachment.id.asc()))).all() if contracts else []
    first_attachment = {}
    for attachment in attachments:
        first_attachment.setdefault(int(attachment.record_id or 0), attachment)
    rows = []
    users_by_username = await _user_display_map({contract.owner for contract in contracts.values()}, db)
    for plan in plans:
        contract = contracts.get(plan.contract_record_id)
        if not contract:
            continue
        row = _receivable_dict(plan, contract, users_by_username)
        attachment = first_attachment.get(contract.id)
        row["contract_file"] = _attachment_dict(attachment, contract) if attachment else None
        row["ledger_url"] = f"{settings.api_prefix}/finance/contract-ledger/{contract.id}"
        rows.append(row)
    summary = {
        "amount": _round_fee_amount(sum(item["amount"] for item in rows)),
        "received": _round_fee_amount(sum(item["received_amount"] for item in rows)),
        "remaining": _round_fee_amount(sum(item["remaining_amount"] for item in rows)),
        "overdue": _round_fee_amount(sum(item["remaining_amount"] for item in rows if item["status"] == "已逾期")),
        "contracts": len({item["contract_record_id"] for item in rows}),
    }
    return {"items": rows, "total": len(rows), "summary": summary}


@router.get(f"{settings.api_prefix}/finance/contract-ledger/{{contract_id}}")
async def finance_contract_ledger(contract_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _finance_transaction_dict, _receivable_dict, _round_fee_amount,
    )
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    contract = await _ensure_record_module(contract_id, "contract", identity, db)
    plans = (await db.scalars(select(ReceivablePlan).where(ReceivablePlan.contract_record_id == contract.id).order_by(ReceivablePlan.due_date.asc(), ReceivablePlan.id.asc()))).all()
    contract_users = await _user_display_map({contract.owner}, db)
    ar_rows = [_receivable_dict(plan, contract, contract_users) for plan in plans]
    finance_records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance",
        *(await _record_scope_conditions(identity, db)),
    ).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all())
    linked_fees = [record for record in finance_records if int((record.data or {}).get("contract_id") or 0) == contract.id or str((record.data or {}).get("contract_no") or "") == contract.serial_no]
    fee_ids = [record.id for record in linked_fees]
    transactions = list((await db.scalars(select(FinanceTransaction).where(FinanceTransaction.finance_record_id.in_(fee_ids)).order_by(FinanceTransaction.transaction_date.asc(), FinanceTransaction.id.asc()))).all()) if fee_ids else []
    paid_by_fee: dict[int, float] = {}
    for transaction in transactions:
        if transaction.transaction_type != "付款" or not transaction.finance_record_id:
            continue
        paid_by_fee[transaction.finance_record_id] = paid_by_fee.get(transaction.finance_record_id, 0.0) + float(transaction.amount or 0)
    show_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    ap_rows = []
    for record in linked_fees:
        fee_data = record.data or {}
        amount = _round_fee_amount(abs(float(fee_data.get("amount") or 0)))
        paid = _round_fee_amount(float(paid_by_fee.get(record.id, 0)))
        ap_rows.append({
            "fee_record_id": record.id, "serial_no": record.serial_no, "title": record.title,
            "fee_type": fee_data.get("fee_type", ""), "case_no": fee_data.get("case_no", ""),
            "amount": amount if show_amount else None, "paid_amount": paid if show_amount else None,
            "unpaid_amount": max(amount - paid, 0) if show_amount else None, "status": record.status,
        })
    ar_amount = _round_fee_amount(sum(item["amount"] for item in ar_rows))
    ar_received = _round_fee_amount(sum(item["received_amount"] for item in ar_rows))
    ap_total = _round_fee_amount(sum(item["amount"] or 0 for item in ap_rows))
    ap_paid = _round_fee_amount(sum(item["paid_amount"] or 0 for item in ap_rows))
    summary = {
        "amount": ar_amount, "received": ar_received, "remaining": _round_fee_amount(ar_amount - ar_received),
        "ap_amount": ap_total, "ap_paid": ap_paid, "ap_unpaid": _round_fee_amount(ap_total - ap_paid),
        "transaction_count": len(transactions),
    }
    return {
        "contract": await _record_dict_for_identity(contract, identity, db),
        "ar_rows": ar_rows,
        "ap_rows": ap_rows,
        "transactions": [_finance_transaction_dict(transaction, None, show_amount=show_amount) for transaction in transactions],
        "summary": summary,
    }


@router.post(f"{settings.api_prefix}/finance/fees", status_code=status.HTTP_201_CREATED)
async def create_finance_fee(body: FinanceFeeInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _case_fee_type_snapshot, _finance_fee_commission_payload, _finance_linked_case, _resolve_case_fee_contract, _resolve_case_fee_type_master,
        _round_fee_amount,
    )
    from app.core.permissions import (
        _case_detail_action_capabilities, _ensure_record_visible, _record_dict_for_identity, _validate_finance_fee_scope_subtype,
    )
    if body.amount == 0: raise HTTPException(status_code=422, detail="费用金额不能为 0")
    case_record = await _finance_linked_case(body.case_no, identity, db)
    if body.case_record_id:
        linked_case = await _ensure_record_visible(body.case_record_id, identity, db)
        if linked_case.module != "case": raise HTTPException(status_code=422, detail="关联记录不是案件")
        if case_record and case_record.id != linked_case.id: raise HTTPException(status_code=409, detail="案件编号与案件记录不一致")
        case_record = linked_case
    fee_snapshot = {
        "fee_type_id": None,
        "fee_type_code": "",
        "fee_type_name": body.expense_subtype or body.fee_type,
        "fee_type_path": body.expense_subtype or body.fee_type,
        "fee_type": body.fee_type,
        "expense_subtype": body.expense_subtype or "",
    }
    if case_record or body.fee_type_id:
        fee_parameter, fee_option = await _resolve_case_fee_type_master(
            body.fee_type_id, body.expense_scope, db,
            legacy_name=body.expense_subtype or "", legacy_base=body.fee_type,
        )
        fee_snapshot = _case_fee_type_snapshot(fee_parameter, fee_option)
        if body.fee_type != fee_snapshot["fee_type"]:
            raise HTTPException(status_code=422, detail="费用类型与系统费用分类不一致")
        if body.expense_subtype and body.expense_subtype != fee_parameter.name:
            raise HTTPException(status_code=422, detail="费用子类型与系统费用分类不一致")
    else:
        if body.fee_type not in FINANCE_FEE_TYPES:
            raise HTTPException(status_code=422, detail="费用类型无效")
        if body.expense_scope and body.fee_type not in EXPENSE_SCOPE_FEE_TYPES[body.expense_scope]:
            raise HTTPException(status_code=422, detail="费用归属与费用类型不一致")
        _validate_finance_fee_scope_subtype(body.expense_scope, body.expense_subtype, body.fee_type)
    if body.amount < 0 and fee_snapshot["fee_type"] != "内部费用": raise HTTPException(status_code=422, detail="只有内部费用可以使用负数冲销")
    if case_record and not (await _case_detail_action_capabilities(case_record, identity, db))["can_create_finance"]:
        raise HTTPException(status_code=403, detail="当前账号没有新增案件费用权限")
    contract_record = None
    if body.contract_record_id:
        contract_record = await db.get(BusinessRecord, body.contract_record_id) if case_record else await _ensure_record_visible(body.contract_record_id, identity, db)
        if not contract_record: raise HTTPException(status_code=404, detail="关联合同不存在")
        if contract_record.module != "contract": raise HTTPException(status_code=422, detail="关联记录不是合同")
        if case_record and contract_record.customer != case_record.customer:
            raise HTTPException(status_code=409, detail="关联合同必须属于当前案件客户")
    contract_record = await _resolve_case_fee_contract(case_record, contract_record, body.expense_scope, identity, db)
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if not user: raise HTTPException(status_code=401, detail="当前用户不存在")
    handler = identity["username"] if identity.get("role") == "user" else body.handler
    amount = _round_fee_amount(body.amount)
    commission = await _finance_fee_commission_payload(body, amount, db, case_record=case_record)
    serial = f"FY{datetime.now():%Y%m%d%H%M%S%f}"
    item = BusinessRecord(module="finance", serial_no=serial, title=body.title, customer=body.customer, status="草稿", owner=handler, department=user.department, description=body.description, data={"amount": amount, **fee_snapshot, "expense_scope": body.expense_scope or "", "is_refund": fee_snapshot["fee_type"] == "内部费用" and amount < 0, "case_no": case_record.serial_no if case_record else body.case_no, "case_id": case_record.id if case_record else None, "contract_id": contract_record.id if contract_record else None, "contract_no": contract_record.serial_no if contract_record else "", "deadline": str(body.deadline) if body.deadline else "", "handler": handler, "court": body.court, "document_no": body.document_no, "payee": body.payee, "base_amount": body.base_amount, "reference_commission": body.reference_commission, **commission})
    db.add(item); await db.flush()
    db.add(WorkflowEvent(record_id=item.id, action="创建费用", to_status="草稿", operator=identity["username"], comment=f"{fee_snapshot['fee_type_path']}：{amount:.2f} 元"))
    await db.commit(); await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)


from app.areas.finance.settlements import (
    router as settlements_router,
    list_general_settlement_candidates as list_general_settlement_candidates,
    apply_general_settlements as apply_general_settlements,
    list_pending_archive_settlements as list_pending_archive_settlements,
    export_pending_archive_settlements as export_pending_archive_settlements,
    list_archive_settlement_payments as list_archive_settlement_payments,
    review_archive_settlement_payments as review_archive_settlement_payments,
    export_archive_settlement_payments as export_archive_settlement_payments,
    list_paid_archive_settlements as list_paid_archive_settlements,
    rollback_paid_archive_settlements as rollback_paid_archive_settlements,
    export_paid_archive_settlements as export_paid_archive_settlements,
    list_rejected_archive_settlements as list_rejected_archive_settlements,
    rollback_rejected_archive_settlements as rollback_rejected_archive_settlements,
    reapply_rejected_archive_settlements as reapply_rejected_archive_settlements,
    export_rejected_archive_settlements as export_rejected_archive_settlements,
    list_general_settlement_applications as list_general_settlement_applications,
    reapply_general_settlement_applications as reapply_general_settlement_applications,
    review_general_settlement_applications as review_general_settlement_applications,
    pay_or_rollback_general_settlement_applications as pay_or_rollback_general_settlement_applications,
    export_general_settlements as export_general_settlements,
    delete_general_settlement_application as delete_general_settlement_application,
)
router.include_router(settlements_router)


from app.areas.finance.internal_payments import (
    router as internal_payments_router,
    list_pending_finance_settlements as list_pending_finance_settlements,
    mark_finance_settlements_commission_paid as mark_finance_settlements_commission_paid,
    list_internal_refund_review_candidates as list_internal_refund_review_candidates,
    export_payment_package_word as export_payment_package_word,
    list_internal_payment_packages as list_internal_payment_packages,
    list_internal_payment_package_candidates as list_internal_payment_package_candidates,
    preview_internal_payment_package as preview_internal_payment_package,
    create_internal_payment_package as create_internal_payment_package,
    get_internal_payment_package as get_internal_payment_package,
    update_internal_payment_package as update_internal_payment_package,
    writeoff_internal_payment_package as writeoff_internal_payment_package,
    cancel_internal_payment_package as cancel_internal_payment_package,
)
router.include_router(internal_payments_router)


from app.areas.finance.fee_workflows import (
    router as fee_workflows_router,
    finance_fee_readiness as finance_fee_readiness,
    cancel_finance_payment as cancel_finance_payment,
    rollback_finance_payment as rollback_finance_payment,
    list_finance_fee_payment_types as list_finance_fee_payment_types,
    create_finance_fee_payment_type as create_finance_fee_payment_type,
    submit_finance_fee as submit_finance_fee,
    mark_finance_fee_no_payment as mark_finance_fee_no_payment,
    mark_finance_fee_refund_not_required as mark_finance_fee_refund_not_required,
    approve_finance_fee as approve_finance_fee,
    batch_review_finance_fees as batch_review_finance_fees,
    review_finance_fee as review_finance_fee,
    void_rejected_finance_fee as void_rejected_finance_fee,
    writeoff_finance_fee as writeoff_finance_fee,
)
router.include_router(fee_workflows_router)


from app.areas.finance.transactions import (
    router as transactions_router,
    list_finance_transactions as list_finance_transactions,
    create_finance_transaction as create_finance_transaction,
    delete_finance_transaction as delete_finance_transaction,
    list_reconciliations as list_reconciliations,
    create_reconciliation as create_reconciliation,
    confirm_reconciliation as confirm_reconciliation,
    delete_reconciliation as delete_reconciliation,
)
router.include_router(transactions_router)


@router.post(f"{settings.api_prefix}/finance/case-fees/batch", status_code=status.HTTP_201_CREATED)
async def create_refund_page_case_fees(
    body: RefundCaseFeeBatchCreateInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _active_payment_type, _case_fee_type_snapshot, _finance_payment_type_dict, _resolve_case_fee_contract, _resolve_case_fee_type_master,
        _round_fee_amount,
    )
    from app.core.formatters import (
        _contract_person_display_name,
    )
    from app.core.permissions import (
        _case_detail_action_capabilities, _record_dicts_for_identity, _record_scope_conditions,
    )
    case_ids = list(dict.fromkeys(item.case_id for item in body.items))
    visible_cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case",
        BusinessRecord.id.in_(case_ids),
        *(await _record_scope_conditions(identity, db)),
    ))).all())
    cases_by_id = {item.id: item for item in visible_cases}
    if len(cases_by_id) != len(case_ids):
        raise HTTPException(status_code=404, detail="存在无权访问或不存在的案件")

    handler = body.handler.strip() or identity["username"]
    if identity.get("role") == "user":
        handler = identity["username"]
    handler_user = await db.scalar(select(User).where(User.username == handler, User.is_active.is_(True)))
    if not handler_user:
        raise HTTPException(status_code=422, detail="费用经办人不存在或已停用")

    created: list[BusinessRecord] = []
    try:
        for index, request_item in enumerate(body.items, start=1):
            case_record = cases_by_id[request_item.case_id]
            if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
                raise HTTPException(status_code=409, detail=f"第 {index} 行案件 {case_record.serial_no} 已进入归档流程，不能新增费用")
            if not (await _case_detail_action_capabilities(case_record, identity, db))["can_create_finance"]:
                raise HTTPException(status_code=403, detail=f"第 {index} 行案件 {case_record.serial_no} 无新增费用权限")
            if request_item.amount == 0:
                raise HTTPException(status_code=422, detail=f"第 {index} 行费用金额不能为 0")
            if request_item.amount < 0 and request_item.fee_type != "内部费用":
                raise HTTPException(status_code=422, detail=f"第 {index} 行只有内部费用可以使用负数冲销")

            expense_scope = "内部" if request_item.fee_type == "内部费用" else "律所"
            if request_item.fee_type_id:
                fee_parameter, fee_option = await _resolve_case_fee_type_master(
                    request_item.fee_type_id, expense_scope, db,
                )
            else:
                fee_parameter, fee_option = await _resolve_case_fee_type_master(
                    None, expense_scope, db, legacy_name="", legacy_base=request_item.fee_type,
                )
            fee_snapshot = _case_fee_type_snapshot(fee_parameter, fee_option)
            contract_record = None
            if request_item.contract_record_id:
                contract_record = await db.get(BusinessRecord, request_item.contract_record_id)
                if not contract_record or contract_record.module != "contract":
                    raise HTTPException(status_code=422, detail=f"第 {index} 行关联合同不存在")
                if contract_record.customer != case_record.customer:
                    raise HTTPException(status_code=409, detail=f"第 {index} 行关联合同不属于当前案件客户")
            contract_record = await _resolve_case_fee_contract(
                case_record, contract_record, expense_scope, identity, db,
            )
            amount = _round_fee_amount(request_item.amount)
            payment_type = None
            payee_user = None
            payment_amount = None
            if body.submit_payment:
                payment_amount = _round_fee_amount(request_item.payment_amount or abs(amount))
                if payment_amount > abs(amount) + 0.001:
                    raise HTTPException(status_code=409, detail=f"第 {index} 行申请付款金额不能超过费用金额 {abs(amount):.2f}")
                if request_item.fee_type == "代理费":
                    raise HTTPException(status_code=409, detail=f"第 {index} 行代理费不允许申请付款")
                if request_item.fee_type == "内部费用":
                    payee_username = request_item.payee_username.strip()
                    payee_user = await db.scalar(select(User).where(User.username == payee_username, User.is_active.is_(True)))
                    if not payee_user:
                        raise HTTPException(status_code=422, detail=f"第 {index} 行内部费用支付对象不存在或已停用")
                else:
                    if not request_item.payment_type_id and request_item.fee_type != "官方费用":
                        raise HTTPException(status_code=422, detail=f"第 {index} 行请选择系统收款单位")
                    payment_type = await _active_payment_type(request_item.payment_type_id, db) if request_item.payment_type_id else None
            serial = f"FY{datetime.now():%Y%m%d%H%M%S%f}{uuid4().hex[:6]}"
            case_data = case_record.data or {}
            payment_type_data = _finance_payment_type_dict(payment_type) if payment_type else {}
            payee_name = (
                _contract_person_display_name(payee_user.display_name, {payee_user.username.lower(): payee_user.display_name})
                if payee_user else str(payment_type_data.get("payee") or ("" if body.submit_payment and request_item.fee_type == "官方费用" else case_data.get("court_name") or case_data.get("court") or ""))
            )
            record_status = "待审批" if body.submit_payment else "草稿"
            item = BusinessRecord(
                module="finance",
                serial_no=serial,
                title=f"{case_record.title}{fee_parameter.name}",
                customer=case_record.customer,
                status=record_status,
                owner=handler,
                department=case_record.department,
                description=request_item.remark,
                data={
                    "amount": amount,
                    **fee_snapshot,
                    "expense_scope": expense_scope,
                    "is_refund": request_item.fee_type == "内部费用" and amount < 0,
                    "case_no": case_record.serial_no,
                    "case_id": case_record.id,
                    "contract_id": contract_record.id if contract_record else None,
                    "contract_no": contract_record.serial_no if contract_record else str(case_data.get("contract_no") or ""),
                    "deadline": str(request_item.deadline) if request_item.deadline else "",
                    "handler": handler,
                    "court": str(case_data.get("court_name") or case_data.get("court") or ""),
                    "document_no": "",
                    "payee": payee_name,
                    "base_amount": _round_fee_amount(request_item.base_amount),
                    "reference_commission": _round_fee_amount(request_item.reference_commission),
                    "actual_commission": abs(amount) if request_item.fee_type == "内部费用" else 0,
                    "commission_type": fee_parameter.name if request_item.fee_type == "内部费用" else "",
                    "payment_requested_amount": payment_amount or 0,
                    "payment_type_id": payment_type.id if payment_type else None,
                    "payment_type_code": payment_type.code if payment_type else "",
                    "payment_type_name": payment_type.name if payment_type else "",
                    "payment_account": str(payment_type_data.get("account") or (payee_user.username if payee_user else "")),
                    "payment_account_bank": str(payment_type_data.get("account_bank") or ""),
                    "payment_payee": payee_name,
                    "payment_remark": request_item.payment_remark.strip(),
                    "payment_applied_at": datetime.now().isoformat(timespec="seconds") if body.submit_payment else "",
                    "payment_applied_by": identity["username"] if body.submit_payment else "",
                    "payment_status": "待审批" if body.submit_payment else "",
                },
            )
            db.add(item)
            await db.flush()
            created.append(item)
            detail = f"{case_record.serial_no}｜{fee_option['path']}：{amount:.2f} 元"
            db.add(WorkflowEvent(record_id=item.id, action="批量创建案件费用", to_status=record_status, operator=identity["username"], comment=detail))
            if body.submit_payment:
                db.add(WorkflowEvent(record_id=item.id, action="提交费用付款申请", from_status="草稿", to_status="待审批", operator=identity["username"], comment=request_item.payment_remark.strip() or f"申请付款 {payment_amount:.2f} 元"))
            db.add(WorkflowEvent(record_id=case_record.id, action="批量新增案件费用", from_status=case_record.status, to_status=case_record.status, operator=identity["username"], comment=f"{item.serial_no}｜{detail}"))
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    for item in created:
        await db.refresh(item)
    return {"created": len(created), "items": await _record_dicts_for_identity(created, identity, db)}


@router.get(f"{settings.api_prefix}/finance/payment-types")
async def list_finance_payment_types(
    keyword: str = "",
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _active_payment_type_rows,
    )
    return {"items": await _active_payment_type_rows(db, keyword)}


@router.post(f"{settings.api_prefix}/receivables", status_code=status.HTTP_201_CREATED)
async def create_receivable(body: ReceivableInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _receivable_dict,
    )
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    contract = await _ensure_record_module(body.contract_record_id, "contract", identity, db)
    await _require_record_owner_or_manager(contract, identity, db)
    plan = ReceivablePlan(**body.model_dump(), status="待收款")
    db.add(plan)
    await db.flush()
    db.add(WorkflowEvent(record_id=contract.id, action="新增应收计划", from_status=contract.status, to_status=contract.status, operator=identity["username"], comment=f"{body.phase}：{body.amount:.2f}元"))
    await db.commit()
    await db.refresh(plan)
    return _receivable_dict(plan, contract, await _user_display_map({contract.owner}, db))


@router.post(f"{settings.api_prefix}/receivables/{{plan_id}}/receive")
async def receive_payment(plan_id: int, body: ReceivePaymentInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _receivable_dict,
    )
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    plan = await db.get(ReceivablePlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="应收计划不存在")
    contract = await _ensure_record_module(plan.contract_record_id, "contract", identity, db)
    await _require_record_owner_or_manager(contract, identity, db)
    remaining = max(plan.amount - plan.received_amount, 0)
    if body.amount > remaining + 0.001:
        raise HTTPException(status_code=409, detail=f"登记金额不能超过未收金额 {remaining:.2f} 元")
    plan.received_amount += body.amount
    plan.status = "已收款" if plan.received_amount + 0.001 >= plan.amount else "部分收款"
    db.add(WorkflowEvent(record_id=contract.id, action="登记回款", from_status=contract.status, to_status=contract.status, operator=identity["username"], comment=f"{plan.phase}回款 {body.amount:.2f} 元。{body.comment}"))
    await db.commit()
    await db.refresh(plan)
    return _receivable_dict(plan, contract, await _user_display_map({contract.owner}, db))


@router.delete(f"{settings.api_prefix}/receivables/{{plan_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_receivable(plan_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    if identity["role"] != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可删除应收计划")
    plan = await db.get(ReceivablePlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="应收计划不存在")
    await db.delete(plan)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/finance/invoices/{{invoice_id}}")
async def get_invoice_application(invoice_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import _invoice_detail_record
    from app.core.permissions import _ensure_record_module

    item = await _ensure_record_module(invoice_id, "invoice", identity, db)
    return await _invoice_detail_record(item, identity, db)


@router.get(f"{settings.api_prefix}/finance/invoice-context")
async def invoice_application_context(
    customer: str = "", customer_no: str = "", customer_id: int | None = None,
    contract_ids: str = "", invoice_id: int | None = None, keyword: str = "", selected_fee_ids: str | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.contracts import _contract_allows_finance_application
    from app.core.finance import (
        _editable_invoice_application, _invoice_customer_defaults, _invoice_fee_details,
        _invoice_linked_fee_ids,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _record_scope_conditions,
        _require_record_module_menu,
    )

    await _require_record_module_menu("invoice", identity, db, action="查看")
    selected_ids = set()
    saved_selected_ids = set()
    if invoice_id is not None:
        invoice = await _editable_invoice_application(invoice_id, identity, db)
        if customer and customer.strip() != invoice.customer.strip():
            raise HTTPException(status_code=409, detail="编辑客户与原发票不一致")
        customer = invoice.customer
        selected_ids = _invoice_linked_fee_ids(invoice.data or {})
        saved_selected_ids = set(selected_ids)
    if selected_fee_ids is not None:
        try:
            selected_ids = {int(value.strip()) for value in selected_fee_ids.split(",") if value.strip()}
            if any(value <= 0 for value in selected_ids) or len(selected_ids) > 100:
                raise ValueError()
        except ValueError:
            raise HTTPException(status_code=422, detail="所选费用ID必须为正整数，最多100个") from None
    requested_contracts = []
    try:
        requested_ids = {int(value.strip()) for value in contract_ids.split(",") if value.strip()}
        if any(value <= 0 for value in requested_ids) or len(requested_ids) > 100:
            raise ValueError()
    except ValueError:
        raise HTTPException(status_code=422, detail="合同ID必须为正整数，最多100个") from None
    for record_id in sorted(requested_ids):
        contract = await _ensure_record_module(record_id, "contract", identity, db)
        if not _contract_allows_finance_application(contract):
            raise HTTPException(status_code=409, detail="归档或已终止合同不能新建开票申请")
        requested_contracts.append(contract)
    if requested_contracts:
        names = {item.customer.strip() for item in requested_contracts}
        if len(names) != 1 or (customer and customer.strip() not in names):
            raise HTTPException(status_code=409, detail="所选合同必须属于同一发票客户")
        customer = next(iter(names))
    customer_record = None
    if customer_id is not None:
        customer_record = await _ensure_record_module(customer_id, "customer", identity, db)
        if customer_no and customer_no != customer_record.serial_no:
            raise HTTPException(status_code=409, detail="客户编号与客户记录不一致")
    elif customer_no or customer:
        conditions = [BusinessRecord.module == "customer", *(await _record_scope_conditions(identity, db))]
        conditions.append(BusinessRecord.serial_no == customer_no if customer_no else or_(
            BusinessRecord.title == customer.strip(), BusinessRecord.customer == customer.strip(),
        ))
        matches = list((await db.scalars(select(BusinessRecord).where(*conditions).limit(2))).all())
        if len(matches) > 1:
            raise HTTPException(status_code=409, detail="客户名称不唯一，请指定客户记录ID或编号")
        customer_record = matches[0] if matches else None
        if customer_no and customer_record is None:
            raise HTTPException(status_code=404, detail="客户不存在或无权访问")
    if customer_record:
        if customer and customer.strip() not in {customer_record.title.strip(), customer_record.customer.strip()}:
            raise HTTPException(status_code=409, detail="客户资料与所选来源客户不一致")
        customer = customer or customer_record.title or customer_record.customer
    customer_result = await _record_dict_for_identity(customer_record, identity, db) if customer_record else None
    if not customer.strip():
        raise HTTPException(status_code=422, detail="请先指定客户、合同或编辑发票")
    conditions = [BusinessRecord.module == "finance", BusinessRecord.customer == customer.strip(),
                  *(await _record_scope_conditions(identity, db))]
    if requested_ids:
        conditions.append(or_(
            BusinessRecord.data["contract_id"].as_integer().in_(requested_ids),
            BusinessRecord.data["contract_record_id"].as_integer().in_(requested_ids),
            BusinessRecord.data["contract_no"].as_string().in_([item.serial_no for item in requested_contracts]),
        ))
    needle = keyword.strip().casefold()
    start = (page - 1) * page_size
    selected = await _invoice_fee_details(identity, db, ids=selected_ids, customer=customer, exclude_invoice_id=invoice_id) if selected_ids else []
    if {row["id"] for row in selected} != selected_ids:
        raise HTTPException(status_code=403, detail="所选开票费用不存在、无权访问或不属于当前客户")
    items, total, cursor = [], 0, 0
    # Eligibility depends on active allocations. Scan scoped IDs in bounded SQL
    # pages, hydrate one page at a time, and retain only the requested output page.
    while True:
        batch_ids = list((await db.scalars(select(BusinessRecord.id).where(
            *conditions, BusinessRecord.id > cursor,
        ).order_by(BusinessRecord.id).limit(100))).all())
        if not batch_ids:
            break
        cursor = batch_ids[-1]
        batch = await _invoice_fee_details(identity, db, ids=set(batch_ids), customer=customer, exclude_invoice_id=invoice_id)
        for row in sorted(batch, key=lambda value: value["id"]):
            data = row["data"]
            if requested_ids and data.get("contract_id") not in requested_ids:
                continue
            if row["id"] not in saved_selected_ids and (
                not data.get("contract_allows_invoice") or row["status"] in {"已删除", "已作废", "不缴费"}
                or data.get("remaining_invoice_amount") is None or data["remaining_invoice_amount"] <= 0
            ):
                continue
            if needle and not any(needle in str(value or "").casefold() for value in (
                row["serial_no"], row["title"], data.get("fee_type"), data.get("case_no"),
                data.get("contract_no"), data.get("external_contract_no"),
            )):
                continue
            if start <= total < start + page_size:
                items.append(row)
            total += 1
    return {
        "items": items, "total": total, "page": page, "page_size": page_size,
        "selected_items": selected, "customer_record": customer_result,
        "customer_defaults": _invoice_customer_defaults(customer_result, customer),
        "customer_missing_or_forbidden": bool(customer and customer_result is None),
    }


router.include_router(payment_workflow_router)
router.include_router(receipt_files_router)


@router.get(f"{settings.api_prefix}/finance/projection/fees")
async def list_unified_finance_projection(
    keyword: str = "",
    source: str = Query("all", pattern="^(all|modern|legacy)$"),
    status_filter: str = Query("", alias="status"),
    fee_type: str = "",
    include_inactive: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=200),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """合并现代费用记录与导入的 FAM 表头，仅用于展示。"""
    from app.core.finance_projection import read_unified_finance_projection

    return await read_unified_finance_projection(
        identity,
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        source=source,
        include_inactive=include_inactive,
        status=status_filter,
        fee_type=fee_type,
    )


@router.get(f"{settings.api_prefix}/finance/projection/transactions")
async def list_unified_finance_transactions_projection(
    keyword: str = "",
    source: str = Query("all", pattern="^(all|modern|legacy)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=200),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """合并现代流水与旧系统分配明细，不执行任何数据变更。"""
    from app.core.finance_projection import read_unified_finance_transactions

    return await read_unified_finance_transactions(
        identity,
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        source=source,
    )
