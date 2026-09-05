"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.models_shared import IncomingPaymentAllocationItem
from app.core.constants import (
    EXPENSE_SCOPE_FEE_TYPES, FINANCE_FEE_TYPES, FINANCE_PAYMENT_CANCELABLE_STATUSES, FINANCE_PAYMENT_ROLLBACKABLE_STATUSES, FINANCE_TRANSACTION_TYPES,
    JAR_FEE_MODULE, JAR_FEE_STATUSES, JAR_FEE_TRANSITIONS, REFUND_CASE_FEE_STATUSES, REFUND_CASE_FEE_STATUS_BY_LABEL,
    REFUND_PAGE_SIZES, UPLOAD_ROOT,
)
from app.core.dependencies import (
    AsyncSession, BusinessRecord, Depends, File, FileAttachment,
    FileResponse, FinanceTransaction, Form, HTTPException, IncomingPayment,
    IntegrityError, JarFeeAuditLog, LegacyFinanceAllocation, LegacyFinanceAudit, LegacyFinanceFile,
    LegacyFinanceRecord, Path, Query, ReceivablePlan, ReconciliationBatch,
    Response, StreamingResponse, UploadFile, User, WorkflowEvent,
    and_, csv, current_identity, date, datetime,
    delete, false, func, get_db, io,
    or_, quote, select, settings, status,
    uuid4, xml_escape,
)
from app.models_shared import (
    ArchiveSettlementPaymentReviewInput, ArchiveSettlementRejectedActionInput, ArchiveSettlementRollbackInput, CaseFeeBatchUpdateInput, CaseFeeRefundLogInput,
    FinanceActionInput, FinanceFeeArrivalInput, FinanceFeeBatchReviewInput, FinanceFeeInformInput, FinanceFeeInformLinksInput,
    FinanceFeeInput, FinanceFeeReviewInput, FinanceFeeUpdateInput, FinancePaymentCancelInput, FinancePaymentPackageCreateInput,
    FinancePaymentPackagePreviewInput, FinancePaymentPackageUpdateInput, FinancePaymentPackageWriteoffInput, FinancePaymentRollbackInput, FinancePaymentTypeCreateInput,
    FinanceReviewInput, FinanceSettlementApplyInput, FinanceSettlementMarkInput, FinanceSettlementPaymentInput, FinanceSettlementReapplyInput,
    FinanceSettlementReviewInput, FinanceTransactionInput, FinanceWriteoffInput, IncomingPaymentAllocateInput, IncomingPaymentClaimInput,
    IncomingPaymentInput, IncomingPaymentRefundClaimInput, IncomingPaymentRevokeInput, IncomingPaymentUpdateInput, InvoiceApplicationInput,
    InvoiceDateChangeInput, InvoiceIssueInput, InvoiceNumberChangeInput, InvoiceVoidInput, JarFeeInput,
    JarFeeStatusInput, LitigationRefundInput, ReceivableInput, ReceivePaymentInput, ReconciliationInput,
    RefundAmountUpdateInput, RefundBatchStatusInput, RefundCaseFeeBatchCreateInput, RefundCompleteInput,
)
from fastapi import APIRouter

router = APIRouter()


@router.put(f"{settings.api_prefix}/finance/fees/{{fee_id}}")
async def update_finance_fee(fee_id: int, body: FinanceFeeUpdateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _case_fee_type_snapshot, _editable_finance_fee, _finance_fee_commission_details, _resolve_case_fee_contract, _resolve_case_fee_type_master,
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
        if not (await _case_detail_action_capabilities(case_record, identity, db))["can_create_finance"]:
            raise HTTPException(status_code=403, detail="当前账号没有新增案件费用权限")
    fee_snapshot = {
        "fee_type_id": None,
        "fee_type_code": "",
        "fee_type_name": body.expense_subtype or body.fee_type,
        "fee_type_path": body.expense_subtype or body.fee_type,
        "fee_type": body.fee_type,
        "expense_subtype": body.expense_subtype or "",
    }
    if case_record:
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
    if body.contract_record_id:
        contract_record = await db.get(BusinessRecord, body.contract_record_id) if case_record else await _ensure_record_visible(body.contract_record_id, identity, db)
        if not contract_record: raise HTTPException(status_code=404, detail="关联合同不存在")
        if contract_record.module != "contract": raise HTTPException(status_code=422, detail="关联记录不是合同")
        if case_record and contract_record.customer != case_record.customer:
            raise HTTPException(status_code=409, detail="关联合同必须属于当前案件客户")
    contract_record = await _resolve_case_fee_contract(case_record, contract_record, body.expense_scope, identity, db)
    commission_details = await _finance_fee_commission_details(body, amount, db)
    data.update({"amount": amount, **fee_snapshot, "expense_scope": body.expense_scope or "", "handler": body.handler, "court": body.court, "document_no": body.document_no, "payee": body.payee, "base_amount": body.base_amount, "reference_commission": body.reference_commission, "case_no": body.case_no, "case_id": case_record.id if case_record else body.case_record_id, "contract_id": body.contract_record_id, "contract_no": contract_record.serial_no if contract_record else str(data.get("contract_no") or ""), "deadline": str(body.deadline) if body.deadline else "", "commission_details": commission_details, "is_refund": fee_snapshot["fee_type"] == "内部费用" and amount < 0})
    item.title = body.title; item.customer = body.customer; item.owner = body.handler; item.description = body.description; item.data = data
    db.add(WorkflowEvent(record_id=item.id, action="修改费用草稿", from_status=item.status, to_status=item.status, operator=identity["username"], comment=f"{item.serial_no}：{body.title} {amount:.2f}"))
    await db.commit(); await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)


@router.delete(f"{settings.api_prefix}/finance/fees/{{fee_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_finance_fee(fee_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _editable_finance_fee,
    )
    item = await _editable_finance_fee(fee_id, identity, db)
    db.add(WorkflowEvent(record_id=item.id, action="删除费用草稿", from_status=item.status, to_status="已删除", operator=identity["username"], comment=item.serial_no))
    await db.flush()
    await db.delete(item)
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
    item = await _editable_finance_fee(fee_id, identity, db)
    previous = item.status
    # Keep the deletion event queryable. The generic physical-delete route
    # cascades WorkflowEvent rows, which would erase this finance audit trail.
    item.status = "已删除"
    db.add(WorkflowEvent(record_id=item.id, action="删除内部费用草稿", from_status=previous, to_status="已删除", operator=identity["username"], comment=item.serial_no))
    await db.commit()


@router.get(f"{settings.api_prefix}/finance/jar-fees")
async def list_jar_fees(keyword: str = "", status_filter: str = Query(default="", alias="status"), contract_id: str = "", page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=200), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _jar_fee_dict,
    )
    from app.core.permissions import (
        _jar_fee_capabilities, _record_scope_conditions, _require_jar_fee_access,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    await _require_jar_fee_access(identity, db)
    conditions = [BusinessRecord.module == JAR_FEE_MODULE, *(await _record_scope_conditions(identity, db))]
    if status_filter:
        if status_filter not in JAR_FEE_STATUSES: raise HTTPException(status_code=422, detail="交案费状态无效")
        conditions.append(BusinessRecord.status == status_filter)
    try: contract_filter = int(contract_id) if contract_id.strip() else None
    except ValueError: raise HTTPException(status_code=422, detail="合同编号格式无效")
    if contract_filter is not None and contract_filter <= 0: raise HTTPException(status_code=422, detail="合同编号格式无效")
    if contract_filter: conditions.append(BusinessRecord.data["contract_id"].as_integer() == contract_filter)
    if keyword.strip():
        term = f"%{keyword.strip()}%"
        conditions.append(or_(BusinessRecord.serial_no.ilike(term), BusinessRecord.title.ilike(term), BusinessRecord.customer.ilike(term), BusinessRecord.description.ilike(term), BusinessRecord.data["contract_no"].as_string().ilike(term), BusinessRecord.data["payer_name"].as_string().ilike(term), BusinessRecord.data["bank_voucher_no"].as_string().ilike(term), BusinessRecord.data["remark"].as_string().ilike(term)))
    total = int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(*conditions)) or 0)
    rows = (await db.scalars(select(BusinessRecord).where(*conditions).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    allowed_fields = await _allowed_field_keys(identity, db)
    items = []
    for row in rows:
        projected = _jar_fee_dict(row, allowed_fields); projected["capabilities"] = await _jar_fee_capabilities(row, identity, db); items.append(projected)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get(f"{settings.api_prefix}/finance/jar-fees/export")
async def export_jar_fees(keyword: str = "", status_filter: str = Query(default="", alias="status"), contract_id: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _jar_fee_dict,
    )
    from app.core.permissions import (
        _record_scope_conditions, _require_jar_fee_access,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    await _require_jar_fee_access(identity, db)
    conditions = [BusinessRecord.module == JAR_FEE_MODULE, *(await _record_scope_conditions(identity, db))]
    if status_filter:
        if status_filter not in JAR_FEE_STATUSES: raise HTTPException(status_code=422, detail="交案费状态无效")
        conditions.append(BusinessRecord.status == status_filter)
    try: contract_filter = int(contract_id) if contract_id.strip() else None
    except ValueError: raise HTTPException(status_code=422, detail="合同编号格式无效")
    if contract_filter is not None and contract_filter <= 0: raise HTTPException(status_code=422, detail="合同编号格式无效")
    if contract_filter: conditions.append(BusinessRecord.data["contract_id"].as_integer() == contract_filter)
    if keyword.strip():
        term = f"%{keyword.strip()}%"; conditions.append(or_(BusinessRecord.serial_no.ilike(term), BusinessRecord.title.ilike(term), BusinessRecord.customer.ilike(term), BusinessRecord.description.ilike(term), BusinessRecord.data["contract_no"].as_string().ilike(term), BusinessRecord.data["payer_name"].as_string().ilike(term), BusinessRecord.data["bank_voucher_no"].as_string().ilike(term), BusinessRecord.data["remark"].as_string().ilike(term)))
    allowed_fields = await _allowed_field_keys(identity, db)
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["交案费编号", "合同编号", "客户名称", "回款单位", "经办人", "回款日期", "回款金额", "官费", "代理费", "其他费用", "回款方式", "状态", "银行单据号"])
    for item in (await db.scalars(select(BusinessRecord).where(*conditions).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()))).all():
        row = _jar_fee_dict(item, allowed_fields)
        writer.writerow([row["serial_no"], row["contract_no"], row["customer"], row["payer_name"], row["handler"], row["received_date"], row["amount"], row["official_fee_amount"], row["agency_fee_amount"], row["other_fee_amount"], row["payment_method"], row["status"], row["bank_voucher_no"]])
    return StreamingResponse(iter(["\ufeff" + output.getvalue()]), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=jar-fees.csv"})


@router.post(f"{settings.api_prefix}/finance/jar-fees", status_code=status.HTTP_201_CREATED)
async def create_jar_fee(body: JarFeeInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _jar_fee_audit, _jar_fee_contract, _jar_fee_data, _jar_fee_dict,
    )
    from app.core.permissions import (
        _require_jar_fee_access,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    await _require_jar_fee_access(identity, db, write=True)
    contract = await _jar_fee_contract(body.contract_id, identity, db)
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    data = _jar_fee_data(body, contract)
    item = BusinessRecord(module=JAR_FEE_MODULE, serial_no=f"JAR{datetime.now():%Y%m%d%H%M%S}{uuid4().hex[:6].upper()}", title=body.title.strip(), customer=contract.customer, status="待确认", owner=identity["username"], department=user.department if user else contract.department, description=body.remark.strip(), data=data)
    db.add(item); await db.flush()
    db.add(WorkflowEvent(record_id=item.id, action="创建交案费", to_status=item.status, operator=identity["username"], comment=f"合同 {contract.serial_no}"))
    db.add(_jar_fee_audit(item, "创建交案费", identity, {"contract_id": contract.id, "amount": data["amount"]}))
    await db.commit(); await db.refresh(item)
    return _jar_fee_dict(item, await _allowed_field_keys(identity, db))


@router.get(f"{settings.api_prefix}/finance/jar-fees/{{jar_fee_id}}")
async def get_jar_fee(jar_fee_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _jar_fee_dict, _jar_fee_or_404,
    )
    from app.core.permissions import (
        _jar_fee_capabilities, _require_jar_fee_access,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    await _require_jar_fee_access(identity, db)
    item = await _jar_fee_or_404(jar_fee_id, identity, db); result = _jar_fee_dict(item, await _allowed_field_keys(identity, db)); result["capabilities"] = await _jar_fee_capabilities(item, identity, db); return result


@router.put(f"{settings.api_prefix}/finance/jar-fees/{{jar_fee_id}}")
async def update_jar_fee(jar_fee_id: int, body: JarFeeInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _editable_jar_fee, _jar_fee_audit, _jar_fee_contract, _jar_fee_data, _jar_fee_dict,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    item = await _editable_jar_fee(jar_fee_id, identity, db); contract = await _jar_fee_contract(body.contract_id, identity, db)
    item.title = body.title.strip(); item.customer = contract.customer; item.description = body.remark.strip(); item.data = _jar_fee_data(body, contract)
    db.add(WorkflowEvent(record_id=item.id, action="修改交案费", from_status=item.status, to_status=item.status, operator=identity["username"], comment=item.serial_no))
    db.add(_jar_fee_audit(item, "修改交案费", identity, {"contract_id": contract.id, "amount": item.data["amount"]}))
    await db.commit(); await db.refresh(item)
    return _jar_fee_dict(item, await _allowed_field_keys(identity, db))


@router.delete(f"{settings.api_prefix}/finance/jar-fees/{{jar_fee_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_jar_fee(jar_fee_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _editable_jar_fee, _jar_fee_audit,
    )
    from app.core.storage import (
        _attachment_storage_path,
    )
    item = await _editable_jar_fee(jar_fee_id, identity, db)
    files = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id == item.id))).all())
    db.add(WorkflowEvent(record_id=item.id, action="删除交案费", from_status=item.status, to_status="已删除", operator=identity["username"], comment=item.serial_no)); db.add(_jar_fee_audit(item, "删除交案费", identity)); await db.flush(); await db.delete(item); await db.commit()
    for attachment in files:
        path = _attachment_storage_path(attachment)
        if path: path.unlink(missing_ok=True)
    return None


@router.post(f"{settings.api_prefix}/finance/jar-fees/{{jar_fee_id}}/status")
async def update_jar_fee_status(jar_fee_id: int, body: JarFeeStatusInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _jar_fee_audit, _jar_fee_dict, _jar_fee_or_404,
    )
    from app.core.permissions import (
        _require_jar_fee_access, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    await _require_jar_fee_access(identity, db, write=True)
    item = await _jar_fee_or_404(jar_fee_id, identity, db); await _require_record_owner_or_manager(item, identity, db)
    if body.status not in JAR_FEE_TRANSITIONS.get(item.status, set()): raise HTTPException(status_code=409, detail=f"不允许从{item.status}变更为{body.status}")
    previous = item.status; item.status = body.status; item.data = {**(item.data or {}), "status_changed_at": datetime.now().isoformat(timespec="seconds"), "status_changed_by": identity["username"]}
    db.add(WorkflowEvent(record_id=item.id, action="变更交案费状态", from_status=previous, to_status=item.status, operator=identity["username"], comment=body.comment.strip()))
    db.add(_jar_fee_audit(item, "变更交案费状态", identity, {"from_status": previous, "to_status": item.status, "comment": body.comment.strip()}))
    await db.commit(); await db.refresh(item)
    return _jar_fee_dict(item, await _allowed_field_keys(identity, db))


@router.get(f"{settings.api_prefix}/finance/jar-fees/{{jar_fee_id}}/files")
async def list_jar_fee_files(jar_fee_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _jar_fee_dict, _jar_fee_or_404,
    )
    from app.core.permissions import (
        _require_jar_fee_access,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    await _require_jar_fee_access(identity, db); item = await _jar_fee_or_404(jar_fee_id, identity, db)
    files = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id == item.id).order_by(FileAttachment.created_at.desc(), FileAttachment.id.desc()))).all())
    return {"record": _jar_fee_dict(item, await _allowed_field_keys(identity, db)), "items": [_attachment_dict(file, item) for file in files], "total": len(files)}


@router.get(f"{settings.api_prefix}/finance/jar-fees/{{jar_fee_id}}/operation-logs")
async def list_jar_fee_operation_logs(jar_fee_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _jar_fee_or_404,
    )
    from app.core.permissions import (
        _require_jar_fee_access,
    )
    await _require_jar_fee_access(identity, db); item = await _jar_fee_or_404(jar_fee_id, identity, db)
    rows = list((await db.scalars(select(JarFeeAuditLog).where(JarFeeAuditLog.jar_fee_record_id == item.id).order_by(JarFeeAuditLog.created_at.desc(), JarFeeAuditLog.id.desc()))).all())
    return {"items": [{"id": row.id, "action": row.action, "operator": row.operator, "detail": row.detail or {}, "created_at": row.created_at} for row in rows], "total": len(rows)}


@router.post(f"{settings.api_prefix}/finance/jar-fees/{{jar_fee_id}}/files", status_code=status.HTTP_201_CREATED)
async def upload_jar_fee_file(jar_fee_id: int, file: UploadFile = File(...), category: str = Form(default="JAR交案费附件"), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _editable_jar_fee, _jar_fee_audit,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    item = await _editable_jar_fee(jar_fee_id, identity, db)
    suffix = Path(file.filename or "").suffix.lower(); allowed = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".png", ".jpg", ".jpeg", ".zip"}
    if suffix not in allowed: raise HTTPException(status_code=422, detail="不支持的交案费附件格式")
    content = await file.read()
    if not content: raise HTTPException(status_code=422, detail="上传文件不能为空")
    if len(content) > 20 * 1024 * 1024: raise HTTPException(status_code=413, detail="单个文件不能超过20MB")
    stored_name = f"jar-{uuid4().hex}{suffix}"; target = UPLOAD_ROOT / stored_name
    try:
        target.write_bytes(content); attachment = FileAttachment(record_id=item.id, category=category.strip() or "JAR交案费附件", original_name=Path(file.filename or stored_name).name, stored_name=stored_name, content_type=file.content_type or "application/octet-stream", size=len(content), path=str(target), uploader=identity["username"], remark="JAR交案费文件")
        db.add(attachment); await db.flush(); db.add(WorkflowEvent(record_id=item.id, action="上传交案费文件", from_status=item.status, to_status=item.status, operator=identity["username"], comment=attachment.original_name)); db.add(_jar_fee_audit(item, "上传交案费文件", identity, {"attachment_id": attachment.id, "name": attachment.original_name})); await db.commit(); await db.refresh(attachment)
    except Exception:
        await db.rollback(); target.unlink(missing_ok=True); raise
    return _attachment_dict(attachment, item)


@router.get(f"{settings.api_prefix}/finance/jar-fees/{{jar_fee_id}}/files/{{attachment_id}}/download")
async def download_jar_fee_file(jar_fee_id: int, attachment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _jar_fee_or_404,
    )
    from app.core.permissions import (
        _require_jar_fee_access,
    )
    from app.core.storage import (
        _attachment_storage_path,
    )
    await _require_jar_fee_access(identity, db); item = await _jar_fee_or_404(jar_fee_id, identity, db); attachment = await db.get(FileAttachment, attachment_id)
    if not attachment or attachment.record_id != item.id: raise HTTPException(status_code=404, detail="交案费文件不存在")
    path = _attachment_storage_path(attachment)
    if path is None: raise HTTPException(status_code=404, detail="交案费文件不存在")
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.original_name)


@router.delete(f"{settings.api_prefix}/finance/jar-fees/{{jar_fee_id}}/files/{{attachment_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_jar_fee_file(jar_fee_id: int, attachment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _editable_jar_fee, _jar_fee_audit,
    )
    from app.core.storage import (
        _attachment_storage_path,
    )
    item = await _editable_jar_fee(jar_fee_id, identity, db); attachment = await db.get(FileAttachment, attachment_id)
    if not attachment or attachment.record_id != item.id: raise HTTPException(status_code=404, detail="交案费文件不存在")
    path = _attachment_storage_path(attachment); db.add(WorkflowEvent(record_id=item.id, action="删除交案费文件", from_status=item.status, to_status=item.status, operator=identity["username"], comment=attachment.original_name)); db.add(_jar_fee_audit(item, "删除交案费文件", identity, {"attachment_id": attachment.id, "name": attachment.original_name})); await db.delete(attachment); await db.commit()
    if path: path.unlink(missing_ok=True)
    return None


@router.get(f"{settings.api_prefix}/finance/fees/{{fee_id}}/informs")
async def list_finance_fee_informs(fee_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _fee_inform_dict,
    )
    from app.core.permissions import (
        _ensure_record_visible,
    )
    fee = await _ensure_record_visible(fee_id, identity, db)
    if fee.module != "finance":
        raise HTTPException(status_code=404, detail="费用记录不存在")
    candidates = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance_fee_inform",
    ).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()))).all())
    informs = [item for item in candidates if int((item.data or {}).get("source_fee_id") or 0) == fee.id]
    return {"items": [await _fee_inform_dict(item, fee, db) for item in informs]}


@router.post(f"{settings.api_prefix}/finance/fees/{{fee_id}}/informs", status_code=status.HTTP_201_CREATED)
async def create_finance_fee_inform(
    fee_id: int, body: FinanceFeeInformInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _fee_inform_dict, _round_fee_amount,
    )
    from app.core.permissions import (
        _ensure_record_visible, _require_record_owner_or_manager,
    )
    source_fee = await _ensure_record_visible(fee_id, identity, db)
    if source_fee.module != "finance":
        raise HTTPException(status_code=404, detail="费用记录不存在")
    await _require_record_owner_or_manager(source_fee, identity, db)
    source_data = dict(source_fee.data or {})
    amount = _round_fee_amount(float(source_data.get("amount") or 0))
    if amount <= 0:
        raise HTTPException(status_code=422, detail="仅正数费用可以新建费用通知")
    if _round_fee_amount(float(source_data.get("received_amount") or source_data.get("cashed_amount") or 0)) > 0:
        raise HTTPException(status_code=409, detail="已到账费用不能新建费用通知")
    existing_notices = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance_fee_inform",
    ))).all())
    if any(int((item.data or {}).get("source_fee_id") or 0) == source_fee.id and item.status in {"已通知", "已到账", "已票据确认"} for item in existing_notices):
        raise HTTPException(status_code=409, detail="该费用已有进行中的费用通知，不能重复新建")
    case_id = int(source_data.get("case_id") or source_data.get("case_record_id") or 0)
    if case_id:
        case = await _ensure_record_visible(case_id, identity, db)
        if case.module != "case":
            raise HTTPException(status_code=409, detail="费用关联案件无效")
        if case.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
            raise HTTPException(status_code=409, detail="归档中的案件不能新建费用通知")
    serial_no = f"FNI{datetime.now():%Y%m%d%H%M%S%f}"
    notice = BusinessRecord(
        module="finance_fee_inform", serial_no=serial_no,
        title=f"{source_fee.title}费用通知", customer=source_fee.customer, status="已通知",
        owner=identity["username"], department=source_fee.department,
        description=body.remark.strip(),
        data={
            "source_fee_id": source_fee.id, "source_fee_no": source_fee.serial_no,
            "case_id": case_id, "case_no": source_data.get("case_no", ""),
            "fee_type": source_data.get("fee_type", ""), "fee_type_id": source_data.get("fee_type_id"),
            "receivable_amount": amount, "inform_date": str(body.inform_date),
            "inform_status": "已通知", "locked": False, "linked_fee_ids": [],
        },
    )
    db.add(notice); await db.flush()
    source_fee.data = {**source_data, "fee_inform_ids": [*list(source_data.get("fee_inform_ids") or []), notice.id]}
    db.add(WorkflowEvent(record_id=source_fee.id, action="新建费用通知", from_status=source_fee.status, to_status=source_fee.status, operator=identity["username"], comment=f"费用通知 {notice.serial_no}｜通知日期 {body.inform_date}"))
    db.add(WorkflowEvent(record_id=notice.id, action="新建费用通知", to_status=notice.status, operator=identity["username"], comment=f"关联费用 {source_fee.serial_no}｜应收 {amount:.2f}"))
    await db.commit(); await db.refresh(notice); await db.refresh(source_fee)
    return await _fee_inform_dict(notice, source_fee, db)


@router.post(f"{settings.api_prefix}/finance/fee-informs/{{inform_id}}/arrival")
async def confirm_finance_fee_inform_arrival(
    inform_id: int, body: FinanceFeeArrivalInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _fee_inform_dict, _fee_inform_record, _round_fee_amount,
    )
    notice, source_fee = await _fee_inform_record(inform_id, identity, db, write=True)
    # PostgreSQL serializes concurrent confirmation attempts; the unique receipt
    # reference below supplies the same final guard on SQLite.
    notice = await db.scalar(select(BusinessRecord).where(BusinessRecord.id == notice.id).with_for_update())
    source_fee = await db.scalar(select(BusinessRecord).where(BusinessRecord.id == source_fee.id).with_for_update())
    if not notice or not source_fee:
        raise HTTPException(status_code=404, detail="费用通知或来源费用不存在")
    data = dict(notice.data or {})
    if data.get("locked"):
        raise HTTPException(status_code=409, detail="费用通知已锁定，请先解锁")
    if notice.status not in {"已通知", "已到账"}:
        raise HTTPException(status_code=409, detail="当前费用通知不能确认到账")
    receivable = _round_fee_amount(body.receivable_amount)
    received = _round_fee_amount(body.received_amount)
    if abs(receivable - received) > 0.001:
        raise HTTPException(status_code=422, detail="到账确认要求应收金额与实收金额一致")
    expected = _round_fee_amount(float(data.get("receivable_amount") or 0))
    if abs(receivable - expected) > 0.001:
        raise HTTPException(status_code=422, detail="应收金额必须与费用通知一致")
    source_data = dict(source_fee.data or {})
    if _round_fee_amount(float(source_data.get("received_amount") or source_data.get("cashed_amount") or 0)) > 0:
        raise HTTPException(status_code=409, detail="来源费用已登记到账，不能重复确认")
    previous = notice.status
    receipt = IncomingPayment(
        receipt_no=f"FNIHK{datetime.now():%Y%m%d%H%M%S%f}", received_date=body.received_date,
        amount=received, payer_name=source_fee.customer or "费用通知到账", bank_reference=f"fee-source:{source_fee.id}",
        status="已分配", claimed_customer=source_fee.customer,
        contract_record_id=int(source_data.get("contract_id") or source_data.get("contract_record_id") or 0) or None,
        contract_no=str(source_data.get("contract_no") or ""), case_no=str(source_data.get("case_no") or ""),
        bank_source="费用通知到账确认", claimant=identity["username"], allocated_amount=received,
        allocations=[{
            "fee_record_id": source_fee.id, "case_no": str(source_data.get("case_no") or ""),
            "amount": received, "payment_method": "费用通知到账确认",
            "settlement_items": [{"fee_record_id": source_fee.id, "fee_type": source_data.get("fee_type") or source_fee.title, "amount": received, "settlement_amount": received, "archive_fee": 0}],
        }], operator=identity["username"], remark=f"费用通知 {notice.serial_no} 到账确认：{body.remark.strip()}",
    )
    try:
        db.add(receipt); await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="该费用通知已经确认到账，不能重复确认") from exc
    notice.status = "已到账"
    notice.data = {**data, "received_amount": received, "received_date": str(body.received_date), "arrival_status": "已到账", "arrival_confirmed_by": identity["username"], "arrival_remark": body.remark.strip()}
    source_fee.data = {**source_data, "received_amount": received, "received_at": str(body.received_date), "cashed_amount": received, "cashed_date": str(body.received_date), "incoming_payment_id": receipt.id, "receipt_no": receipt.receipt_no, "received_payer_name": receipt.payer_name, "fee_inform_id": notice.id, "fee_inform_arrival_status": "已到账"}
    db.add(WorkflowEvent(record_id=notice.id, action="费用通知到账确认", from_status=previous, to_status=notice.status, operator=identity["username"], comment=f"实收 {received:.2f}｜到账日期 {body.received_date}"))
    db.add(WorkflowEvent(record_id=source_fee.id, action="关联费用通知到账确认", from_status=source_fee.status, to_status=source_fee.status, operator=identity["username"], comment=f"费用通知 {notice.serial_no} 已到账"))
    await db.commit(); await db.refresh(notice); await db.refresh(source_fee)
    return await _fee_inform_dict(notice, source_fee, db)


@router.post(f"{settings.api_prefix}/finance/fee-informs/{{inform_id}}/bill", status_code=status.HTTP_201_CREATED)
async def upload_finance_fee_inform_bill(
    inform_id: int, bill_no: str = Form(...), bill_amount: float = Form(...), bill_date: date = Form(...),
    file: UploadFile = File(...), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _fee_inform_dict, _fee_inform_record, _round_fee_amount,
    )
    notice, source_fee = await _fee_inform_record(inform_id, identity, db, write=True)
    data = dict(notice.data or {})
    if notice.status != "已到账":
        raise HTTPException(status_code=409, detail="仅已到账费用通知可以上传票据")
    if data.get("locked") or data.get("receipt_attachment_id"):
        raise HTTPException(status_code=409, detail="该费用通知票据已锁定")
    if not bill_no.strip() or bill_amount <= 0:
        raise HTTPException(status_code=422, detail="票据编号和票据金额必须有效")
    received = _round_fee_amount(float(data.get("received_amount") or 0))
    if abs(_round_fee_amount(bill_amount) - received) > 0.001:
        raise HTTPException(status_code=422, detail="票据金额必须与实收金额一致")
    filename = Path(file.filename or "").name
    suffix = Path(filename).suffix.lower()
    if suffix not in {".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx", ".xls", ".xlsx"}:
        raise HTTPException(status_code=422, detail="票据文件仅支持 PDF、图片和常用 Office 文档")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="票据文件不能为空")
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="票据文件不能超过 20MB")
    target = UPLOAD_ROOT / f"{uuid4().hex}{suffix}"
    target.write_bytes(content)
    try:
        attachment = FileAttachment(record_id=notice.id, category="案件费用通知票据", original_name=filename, stored_name=target.name, content_type=file.content_type or "application/octet-stream", size=len(content), path=str(target), uploader=identity["username"], remark=f"费用通知 {notice.serial_no}｜票据 {bill_no.strip()}")
        db.add(attachment); await db.flush()
        notice.status = "已票据确认"
        notice.data = {**data, "bill_no": bill_no.strip(), "bill_amount": _round_fee_amount(bill_amount), "bill_date": str(bill_date), "receipt_attachment_id": attachment.id, "locked": True, "bill_status": "已票据确认"}
        db.add(WorkflowEvent(record_id=notice.id, action="上传费用通知票据", from_status="已到账", to_status=notice.status, operator=identity["username"], comment=f"{bill_no.strip()}｜附件 {attachment.original_name}"))
        db.add(WorkflowEvent(record_id=source_fee.id, action="关联费用通知上传票据", from_status=source_fee.status, to_status=source_fee.status, operator=identity["username"], comment=f"费用通知 {notice.serial_no}｜票据 {bill_no.strip()}"))
        await db.commit(); await db.refresh(notice)
    except Exception:
        await db.rollback(); target.unlink(missing_ok=True); raise
    return await _fee_inform_dict(notice, source_fee, db)


@router.get(f"{settings.api_prefix}/finance/fee-informs/{{inform_id}}/bill/download")
async def download_finance_fee_inform_bill(inform_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _fee_inform_record,
    )
    from app.core.storage import (
        _attachment_storage_path,
    )
    notice, _ = await _fee_inform_record(inform_id, identity, db)
    attachment_id = int((notice.data or {}).get("receipt_attachment_id") or 0)
    attachment = await db.get(FileAttachment, attachment_id) if attachment_id else None
    if not attachment or attachment.record_id != notice.id:
        raise HTTPException(status_code=404, detail="费用通知票据文件不存在")
    path = _attachment_storage_path(attachment)
    if path is None:
        raise HTTPException(status_code=404, detail="费用通知票据文件不存在")
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.original_name)


@router.post(f"{settings.api_prefix}/finance/fee-informs/{{inform_id}}/unlock")
async def unlock_finance_fee_inform(inform_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _fee_inform_dict, _fee_inform_record,
    )
    notice, source_fee = await _fee_inform_record(inform_id, identity, db, write=True)
    data = dict(notice.data or {})
    if notice.status != "已票据确认" or not data.get("locked"):
        raise HTTPException(status_code=409, detail="仅已确认票据的费用通知可以解锁")
    previous_attachment_id = int(data.get("receipt_attachment_id") or 0)
    previous_attachment = await db.get(FileAttachment, previous_attachment_id) if previous_attachment_id else None
    notice.status = "已到账"
    history_ids = [int(item) for item in list(data.get("receipt_attachment_history_ids") or []) if int(item) > 0]
    if previous_attachment_id and previous_attachment_id not in history_ids:
        history_ids.append(previous_attachment_id)
    notice.data = {**data, "locked": False, "bill_status": "待上传", "receipt_attachment_id": None, "receipt_attachment_history_ids": history_ids, "unlocked_by": identity["username"], "unlocked_at": datetime.now().isoformat(timespec="seconds")}
    db.add(WorkflowEvent(record_id=notice.id, action="费用通知解锁", from_status="已票据确认", to_status=notice.status, operator=identity["username"], comment="允许重新上传票据"))
    await db.commit(); await db.refresh(notice); await db.refresh(source_fee)
    return await _fee_inform_dict(notice, source_fee, db)


@router.post(f"{settings.api_prefix}/finance/fee-informs/{{inform_id}}/links")
async def link_finance_fee_inform(inform_id: int, body: FinanceFeeInformLinksInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _fee_inform_dict, _fee_inform_record,
    )
    from app.core.permissions import (
        _ensure_record_visible, _require_record_owner_or_manager,
    )
    notice, source_fee = await _fee_inform_record(inform_id, identity, db, write=True)
    requested_ids = [int(item) for item in body.fee_ids]
    if len(set(requested_ids)) != len(requested_ids):
        raise HTTPException(status_code=422, detail="关联费用不能重复选择")
    if source_fee.id in requested_ids:
        raise HTTPException(status_code=422, detail="关联费用不能包含通知来源费用自身")
    source_case_id = int((source_fee.data or {}).get("case_id") or 0)
    linked_fees = []
    for fee_id in requested_ids:
        fee = await _ensure_record_visible(fee_id, identity, db)
        if fee.module != "finance":
            raise HTTPException(status_code=404, detail="关联费用不存在")
        await _require_record_owner_or_manager(fee, identity, db)
        if int((fee.data or {}).get("case_id") or 0) != source_case_id:
            raise HTTPException(status_code=409, detail="关联费用必须属于同一案件")
        linked_fees.append(fee)
    other_notices = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "finance_fee_inform"))).all())
    for other in other_notices:
        if other.id == notice.id:
            continue
        occupied = {int(item) for item in list((other.data or {}).get("linked_fee_ids") or [])}
        overlap = occupied.intersection(requested_ids)
        if overlap:
            raise HTTPException(status_code=409, detail=f"关联费用已被费用通知 {other.serial_no} 使用，不能重复关联")
    notice.data = {**(notice.data or {}), "linked_fee_ids": requested_ids}
    db.add(WorkflowEvent(record_id=notice.id, action="关联费用信息", from_status=notice.status, to_status=notice.status, operator=identity["username"], comment="、".join(item.serial_no for item in linked_fees)))
    await db.commit(); await db.refresh(notice); await db.refresh(source_fee)
    return await _fee_inform_dict(notice, source_fee, db)


@router.delete(f"{settings.api_prefix}/finance/fee-informs/{{inform_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_finance_fee_inform(inform_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _fee_inform_record,
    )
    from app.core.storage import (
        _attachment_storage_path,
    )
    notice, source_fee = await _fee_inform_record(inform_id, identity, db, write=True)
    if notice.status != "已通知":
        raise HTTPException(status_code=409, detail="仅未到账的费用通知可以删除；到账后请保留财务审计记录")
    attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id == notice.id))).all())
    attachment_paths = [path for item in attachments if (path := _attachment_storage_path(item)) is not None]
    source_data = dict(source_fee.data or {})
    source_fee.data = {**source_data, "fee_inform_ids": [item for item in list(source_data.get("fee_inform_ids") or []) if int(item) != notice.id]}
    db.add(WorkflowEvent(record_id=source_fee.id, action="删除费用通知", from_status=source_fee.status, to_status=source_fee.status, operator=identity["username"], comment=notice.serial_no))
    for attachment in attachments:
        await db.delete(attachment)
    await db.delete(notice)
    await db.commit()
    for attachment_path in attachment_paths:
        attachment_path.unlink(missing_ok=True)
    return None


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
    plans = (await db.scalars(select(ReceivablePlan).order_by(ReceivablePlan.due_date))).all()
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
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.projections import (
        _receivable_detail_projection,
    )
    items = await _receivable_detail_projection(identity, db)
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
    if scope == "pending" and identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以处理开票")
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
    if scope == "pending" and identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以处理开票")
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
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
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
    return {"items": rows[start:start + page_size], "total": len(rows), "page": page, "page_size": page_size}


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
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
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
    items = await _editable_refund_case_fees(body.ids, identity, db)
    labels = {"court": "法院", "received": "到账", "other": "其他"}
    case_events: set[int] = set()
    for item in items:
        data = item.data or {}
        label = labels[body.kind]
        db.add(WorkflowEvent(
            record_id=item.id, action=f"添加{label}退费日志", operator=identity["username"],
            comment=body.content.strip(),
        ))
        try:
            case_id = int(data.get("case_id") or 0)
        except (TypeError, ValueError):
            case_id = 0
        if case_id and case_id not in case_events:
            case_events.add(case_id)
            db.add(WorkflowEvent(
                record_id=case_id, action="新增案件日志", operator=identity["username"],
                comment=f"{label}退费日志：{body.content.strip()}",
            ))
    await db.commit()
    return {"created": len(items), "kind": body.kind}


@router.get(f"{settings.api_prefix}/finance/fees/query")
async def query_finance_fees(
    scope: str = Query("company", pattern="^(mine|company)$"),
    unpaid_official: bool = False,
    case_no: str = "", court_case_no: str = "", notary_no: str = "",
    refund_amount_from: float | None = None, refund_amount_to: float | None = None,
    customer: str = "", paid_organization: str = "",
    payment_status: str = Query("", pattern="^(|创建待提交|待审批|待付款|待核销|已付款|已驳回|已作废)$"),
    paid_from: date | None = None, paid_to: date | None = None,
    hearing_lawyer: str = "", assistant: str = "", case_stages: str = "", fee_types: str = "",
    page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
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
        identity, db, scope=scope, unpaid_official=unpaid_official,
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
    return {"items": rows[start:start + page_size], "total": len(rows), "totals": totals, "page": page, "page_size": page_size}


@router.get(f"{settings.api_prefix}/finance/fees/query/export")
async def export_finance_fee_query(
    ids: str = "", selected_only: bool = False,
    scope: str = Query("company", pattern="^(mine|company)$"),
    unpaid_official: bool = False,
    case_no: str = "", court_case_no: str = "", notary_no: str = "",
    refund_amount_from: float | None = None, refund_amount_to: float | None = None,
    customer: str = "", paid_organization: str = "", payment_status: str = "",
    paid_from: date | None = None, paid_to: date | None = None,
    hearing_lawyer: str = "", assistant: str = "", case_stages: str = "", fee_types: str = "",
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
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
        identity, db, scope=scope, unpaid_official=unpaid_official,
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


@router.post(f"{settings.api_prefix}/finance/invoices", status_code=status.HTTP_201_CREATED)
async def create_invoice_application(body: InvoiceApplicationInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _round_fee_amount, _validate_invoice_source_links,
    )
    from app.core.permissions import (
        _record_dict_for_identity,
    )
    case_record, contract_record, case_fees, allocations = await _validate_invoice_source_links(
        body, identity, db, require_source=True,
    )
    case_fee_ids = [fee.id for fee in case_fees]
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if not user: raise HTTPException(status_code=401, detail="当前用户不存在")
    serial = f"FP{datetime.now():%Y%m%d%H%M%S%f}"
    data = body.model_dump(); data["case_fee_ids"] = case_fee_ids; data["case_fee_allocations"] = allocations; data["amount"] = _round_fee_amount(body.amount); data["extra_amount"] = _round_fee_amount(body.extra_amount); data["applicant"] = identity.get("display_name") or identity["username"]; data["case_id"] = case_record.id if case_record else None; data["contract_id"] = contract_record.id if contract_record else None
    if case_record: data["case_no"] = case_record.serial_no
    if contract_record: data["contract_no"] = contract_record.serial_no
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
        case_record, contract_record, case_fees, allocations = await _validate_invoice_source_links(
            body,
            identity,
            db,
            require_source=True,
            exclude_invoice_id=invoice_id,
        )
        case_fee_ids = [fee.id for fee in case_fees]
        existing_data = dict(item.data or {})
        data = {**existing_data, **body.model_dump()}
        data["case_fee_ids"] = case_fee_ids
        data["case_fee_allocations"] = allocations
        data["amount"] = _round_fee_amount(body.amount)
        data["extra_amount"] = _round_fee_amount(body.extra_amount)
        data["applicant"] = existing_data.get("applicant") or identity.get("display_name") or identity["username"]
        data["case_id"] = case_record.id if case_record else None
        data["contract_id"] = contract_record.id if contract_record else None
        if case_record:
            data["case_no"] = case_record.serial_no
        if contract_record:
            data["contract_no"] = contract_record.serial_no
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
    data = item.data or {}; missing = [name for name, value in {"客户名称": item.customer, "发票抬头": data.get("invoice_title"), "纳税人识别号": data.get("taxpayer_id"), "开票金额": data.get("amount")}.items() if not value]
    if data.get("delivery_method") == "电子发票" and not data.get("email"): missing.append("电子邮箱")
    if data.get("delivery_method") != "电子发票" and not data.get("delivery_address"): missing.append("邮寄地址")
    if missing: raise HTTPException(status_code=422, detail="发票申请缺少：" + "、".join(missing))
    previous = item.status
    submitted_at = datetime.now().isoformat(timespec="seconds")
    item.status = "待审批"
    item.data = {**data, "submitted_at": submitted_at, "submitted_by": identity["username"]}
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
    if identity.get("role") not in {"admin", "manager", "auditor"}: raise HTTPException(status_code=403, detail="当前角色没有发票审批权限")
    item = await _ensure_record_module(invoice_id, "invoice", identity, db)
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
    if identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以登记开票")
    item = await _ensure_record_module(invoice_id, "invoice", identity, db)
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
    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以驳回开票")
    reason = body.comment.strip()
    if not reason:
        raise HTTPException(status_code=422, detail="请输入驳回原因")
    item = await _ensure_record_module(invoice_id, "invoice", identity, db)
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


@router.get(f"{settings.api_prefix}/finance/refunds/query")
async def query_refund_applications(
    status_filter: str = Query("", alias="status"), group: str = "", scope: str = Query("company", pattern="^(mine|company)$"),
    page: int = Query(1, ge=1), page_size: int = Query(15, ge=10, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _refund_query_rows,
    )
    if page_size not in REFUND_PAGE_SIZES:
        raise HTTPException(status_code=422, detail="退款列表页长必须为 10、15、20、50、100 或 200")
    rows = await _refund_query_rows(identity, db, status_filter=status_filter, group=group, scope=scope)
    start = (page - 1) * page_size
    total = len(rows)
    return {"items": rows[start:start + page_size], "total": total, "page": page, "page_size": page_size, "pages": (total + page_size - 1) // page_size if total else 0}


@router.get(f"{settings.api_prefix}/finance/refunds/export")
async def export_refund_applications(
    status_filter: str = Query("", alias="status"), group: str = "", scope: str = Query("company", pattern="^(mine|company)$"),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _refund_export_request,
    )
    return await _refund_export_request(ids="", selected_only=False, status_filter=status_filter, group=group, scope=scope, identity=identity, db=db)


@router.get(f"{settings.api_prefix}/finance/refunds/export-selected")
async def export_selected_refund_applications(
    ids: str = "", status_filter: str = Query("", alias="status"), group: str = "", scope: str = Query("company", pattern="^(mine|company)$"),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _refund_export_request,
    )
    return await _refund_export_request(ids=ids, selected_only=True, status_filter=status_filter, group=group, scope=scope, identity=identity, db=db)


@router.patch(f"{settings.api_prefix}/finance/refunds/{{refund_id}}/amount")
async def update_refund_amount(refund_id: int, body: RefundAmountUpdateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _round_fee_amount,
    )
    from app.core.permissions import (
        _ensure_record_visible, _ensure_refund_company_record, _record_dict_for_identity, _require_record_owner_or_manager,
    )
    item = await _ensure_refund_company_record(refund_id, identity, db)
    await _require_record_owner_or_manager(item, identity, db)
    if item.status not in {"草稿", "已驳回"}:
        raise HTTPException(status_code=409, detail="当前退款状态不能修改金额")
    data = dict(item.data or {})
    fee_id = int(data.get("fee_record_id") or 0)
    if fee_id:
        fee = await _ensure_record_visible(fee_id, identity, db)
        if fee.module != "finance":
            raise HTTPException(status_code=404, detail="关联费用不存在")
        original_amount = float((fee.data or {}).get("amount") or 0)
        if body.amount > original_amount:
            raise HTTPException(status_code=422, detail="退款金额不能超过原费用金额")
    old_amount = float(data.get("amount") or 0)
    item.data = {**data, "amount": _round_fee_amount(body.amount), "amount_updated_by": identity["username"], "amount_updated_at": datetime.now().isoformat(timespec="seconds")}
    db.add(WorkflowEvent(record_id=item.id, action="修改退款金额", from_status=item.status, to_status=item.status, operator=identity["username"], comment=f"{old_amount:.2f} → {body.amount:.2f}；{body.comment}"))
    await db.commit(); await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)


@router.post(f"{settings.api_prefix}/finance/refunds/status")
async def batch_refund_status(body: RefundBatchStatusInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_refund_company_record, _record_dict_for_identity, _require_record_owner_or_manager,
    )
    ids = list(dict.fromkeys(body.ids))
    if body.status not in {"待审批", "退款办理中", "已驳回"}:
        raise HTTPException(status_code=422, detail="退款批量状态无效")
    items = [await _ensure_refund_company_record(record_id, identity, db) for record_id in ids]
    if body.status in {"退款办理中", "已驳回"} and identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有退款审批权限")
    for item in items:
        await _require_record_owner_or_manager(item, identity, db) if body.status == "待审批" else None
        allowed = {"待审批": {"草稿", "已驳回"}, "退款办理中": {"待审批"}, "已驳回": {"待审批"}}[body.status]
        if item.status not in allowed:
            raise HTTPException(status_code=409, detail=f"退款 {item.serial_no} 当前状态不能变更为 {body.status}")
    for item in items:
        previous = item.status; item.status = body.status
        db.add(WorkflowEvent(record_id=item.id, action="批量退款状态变更", from_status=previous, to_status=item.status, operator=identity["username"], comment=body.comment))
    await db.commit()
    for item in items:
        await db.refresh(item)
    return {"items": [await _record_dict_for_identity(item, identity, db) for item in items], "status": body.status, "count": len(items)}


@router.post(f"{settings.api_prefix}/finance/refunds", status_code=status.HTTP_201_CREATED)
async def create_litigation_refund(body: LitigationRefundInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _finance_linked_case, _round_fee_amount,
    )
    from app.core.permissions import (
        _ensure_record_visible, _record_dict_for_identity,
    )
    case_record = await _finance_linked_case(body.case_no, identity, db)
    if not case_record: raise HTTPException(status_code=422, detail="诉讼费退款必须关联案件")
    if body.fee_record_id:
        fee_record = await _ensure_record_visible(body.fee_record_id, identity, db)
        if fee_record.module != "finance" or str((fee_record.data or {}).get("fee_type") or "") != "官方费用":
            raise HTTPException(status_code=422, detail="诉讼费退款只能关联官方费用")
        if str((fee_record.data or {}).get("case_no") or "") != case_record.serial_no:
            raise HTTPException(status_code=409, detail="退款费用与案件不一致")
        original_amount = _round_fee_amount(abs(float((fee_record.data or {}).get("amount") or 0)))
        linked_refunds = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "refund",
            BusinessRecord.data["fee_record_id"].as_integer() == fee_record.id,
            ~BusinessRecord.status.in_({"已驳回", "已作废"}),
        ))).all())
        already_requested = _round_fee_amount(sum(float((refund.data or {}).get("amount") or 0) for refund in linked_refunds))
        if _round_fee_amount(body.amount) + already_requested > original_amount:
            raise HTTPException(status_code=422, detail="退款金额不能超过原费用金额")
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if not user: raise HTTPException(status_code=401, detail="当前用户不存在")
    serial = f"TF{datetime.now():%Y%m%d%H%M%S%f}"; data = body.model_dump(mode="json"); data["amount"] = _round_fee_amount(body.amount); data["case_id"] = case_record.id; data["case_record_id"] = case_record.id; data["case_no"] = case_record.serial_no
    item = BusinessRecord(module="refund", serial_no=serial, title=f"{body.case_no}诉讼费退款", customer=body.customer.strip(), status="草稿", owner=identity["username"], department=user.department, description=body.remark, data=data)
    db.add(item); await db.flush(); db.add(WorkflowEvent(record_id=item.id, action="创建诉讼费退款申请", to_status=item.status, operator=identity["username"], comment=f"{body.court}：{data['amount']:.2f} 元"))
    await db.commit(); await db.refresh(item); return await _record_dict_for_identity(item, identity, db)


@router.post(f"{settings.api_prefix}/finance/refunds/{{refund_id}}/submit")
async def submit_litigation_refund(refund_id: int, body: FinanceActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_refund_company_record, _record_dict_for_identity, _require_record_owner_or_manager,
    )
    item = await _ensure_refund_company_record(refund_id, identity, db); await _require_record_owner_or_manager(item, identity, db)
    if item.status not in {"草稿", "已驳回"}: raise HTTPException(status_code=409, detail="当前退款申请不能提交")
    data = item.data or {}; required = {"法院": data.get("court"), "原缴费票号": data.get("original_payment_no"), "申请人": data.get("applicant")}
    missing = [name for name, value in required.items() if not value]
    if missing: raise HTTPException(status_code=422, detail="退款申请缺少：" + "、".join(missing))
    previous = item.status; item.status = "待审批"; db.add(WorkflowEvent(record_id=item.id, action="提交诉讼费退款", from_status=previous, to_status=item.status, operator=identity["username"], comment=body.comment))
    await db.commit(); await db.refresh(item); return await _record_dict_for_identity(item, identity, db)


@router.post(f"{settings.api_prefix}/finance/refunds/{{refund_id}}/review")
async def review_litigation_refund(refund_id: int, body: FinanceReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_refund_company_record, _record_dict_for_identity,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}: raise HTTPException(status_code=403, detail="当前角色没有退款审批权限")
    item = await _ensure_refund_company_record(refund_id, identity, db)
    if item.status != "待审批": raise HTTPException(status_code=409, detail="只有待审批退款申请可以审核")
    item.status = "退款办理中" if body.approved else "已驳回"; item.data = {**(item.data or {}), "reviewer": identity["username"], "reviewed_at": datetime.now().isoformat(timespec="seconds"), "review_comment": body.comment}
    db.add(WorkflowEvent(record_id=item.id, action="退款审批通过" if body.approved else "退款审批驳回", from_status="待审批", to_status=item.status, operator=identity["username"], comment=body.comment))
    await db.commit(); await db.refresh(item); return await _record_dict_for_identity(item, identity, db)


@router.post(f"{settings.api_prefix}/finance/refunds/{{refund_id}}/complete")
async def complete_litigation_refund(refund_id: int, body: RefundCompleteInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_refund_company_record, _record_dict_for_identity,
    )
    if identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以登记退款到账")
    item = await _ensure_refund_company_record(refund_id, identity, db)
    if item.status != "退款办理中": raise HTTPException(status_code=409, detail="退款审批通过后才能登记到账")
    data = item.data or {}; tx = FinanceTransaction(finance_record_id=item.id, transaction_type="退费", amount=float(data.get("amount", 0)), transaction_date=body.actual_date, voucher_no=body.voucher_no.strip(), counterparty=str(data.get("court", item.customer)), operator=identity["username"], remark=f"诉讼费退款 {item.serial_no}；{body.comment}")
    db.add(tx); await db.flush(); item.status = "已退款"; item.data = {**data, "actual_date": str(body.actual_date), "refund_voucher_no": body.voucher_no.strip(), "refund_transaction_id": tx.id, "completed_by": identity["username"], "completed_at": datetime.now().isoformat(timespec="seconds")}
    db.add(WorkflowEvent(record_id=item.id, action="登记退款到账", from_status="退款办理中", to_status=item.status, operator=identity["username"], comment=f"凭证号：{body.voucher_no}。{body.comment}"))
    await db.commit(); await db.refresh(item); return await _record_dict_for_identity(item, identity, db)


@router.get(f"{settings.api_prefix}/finance/internal-fees")
async def list_internal_fees(
    scope: str = Query("company", pattern="^(mine|company)$"),
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


@router.get(f"{settings.api_prefix}/finance/internal-fees/export")
async def export_internal_fees(
    scope: str = Query("company", pattern="^(mine|company)$"), ids: str = "",
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
    record_kind: str = Query("", pattern="^(|ap_payment|ar_payment|invoice|ap_packing|case_fee)$"),
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
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    finance_records = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module.in_(["finance", "invoice", "refund"]), *(await _record_scope_conditions(identity, db))))).all()
    fees = [item for item in finance_records if item.module == "finance"]
    invoices = [item for item in finance_records if item.module == "invoice"]
    refunds = [item for item in finance_records if item.module == "refund"]
    transactions = (await db.scalars(select(FinanceTransaction))).all()
    visible_record_ids = {item.id for item in finance_records}
    if identity.get("role") != "admin": transactions = [item for item in transactions if (item.finance_record_id and item.finance_record_id in visible_record_ids) or (not item.finance_record_id and item.operator == identity["username"])]
    amounts = {fee_type: sum(float((item.data or {}).get("amount", 0)) for item in fees if (item.data or {}).get("fee_type") == fee_type) for fee_type in FINANCE_FEE_TYPES}
    can_view_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    incoming = (await db.scalars(select(IncomingPayment))).all()
    if identity.get("role") not in {"admin", "auditor"}:
        visible_customer_titles = set((await db.scalars(select(BusinessRecord.title).where(BusinessRecord.module == "customer", *(await _record_scope_conditions(identity, db))))).all())
        incoming = [item for item in incoming if item.operator == identity["username"] or item.claimant == identity["username"] or item.claimed_customer in visible_customer_titles]
    return {
        "fees": len(fees), "draft": sum(1 for item in fees if item.status == "草稿"),
        "pending": sum(1 for item in fees if item.status == "待审批"),
        "approved": sum(1 for item in fees if item.status in {"已审批", "部分付款"}),
        "paid": sum(1 for item in fees if item.status == "已付款"),
        "invoice_applications": len(invoices), "invoice_pending": sum(1 for item in invoices if item.status == "待审批"),
        "refund_applications": len(refunds), "refund_pending": sum(1 for item in refunds if item.status == "待审批"),
        "amount_visible": can_view_amount,
        "total_fee_amount": sum(amounts.values()) if can_view_amount else None, "amounts_by_type": amounts if can_view_amount else {},
        "paid_amount": sum(item.amount for item in transactions if item.transaction_type == "付款") if can_view_amount else None,
        "invoice_amount": sum(item.amount for item in transactions if item.transaction_type == "开票") if can_view_amount else None,
        "refund_amount": sum(item.amount for item in transactions if item.transaction_type == "退费") if can_view_amount else None,
        "incoming_payments": len(incoming), "incoming_unclaimed": sum(1 for item in incoming if item.status == "待认领"), "incoming_unallocated": sum(1 for item in incoming if item.status in {"待分配", "部分分配"}),
    }


@router.get(f"{settings.api_prefix}/finance/incoming-payments")
async def list_incoming_payments(payment_status: str = "", keyword: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.contracts import (
        _contract_person_values,
    )
    from app.core.finance import (
        _incoming_payment_dict,
    )
    from app.core.formatters import (
        _person_reference_display,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    items = (await db.scalars(select(IncomingPayment).order_by(IncomingPayment.received_date.desc(), IncomingPayment.id.desc()))).all()
    if identity.get("role") not in {"admin", "auditor"}:
        visible_customer_titles = set((await db.scalars(select(BusinessRecord.title).where(BusinessRecord.module == "customer", *(await _record_scope_conditions(identity, db))))).all())
        items = [item for item in items if item.operator == identity["username"] or item.claimant == identity["username"] or item.claimed_customer in visible_customer_titles]
    if payment_status: items = [item for item in items if item.status == payment_status]
    if keyword:
        key = keyword.casefold(); items = [item for item in items if key in f"{item.receipt_no} {item.payer_name} {item.bank_reference} {item.claimed_customer}".casefold()]
    can_view_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    users = list((await db.scalars(select(User).where(User.is_active.is_(True)))).all())
    users_by_username = {user.username.lower(): user for user in users}
    claimed_names = {item.claimed_customer.strip() for item in items if item.claimed_customer.strip()}
    customer_rows = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "customer", BusinessRecord.title.in_(claimed_names),
    ))).all()) if claimed_names else []
    customers_by_title = {row.title.strip(): row for row in customer_rows}
    rows = []
    for item in items:
        payload = _incoming_payment_dict(item, show_amount=can_view_amount, users_by_username=users_by_username)
        customer = customers_by_title.get(item.claimed_customer.strip())
        if customer:
            manager_values = _contract_person_values((customer.data or {}).get("customer_managers") or [customer.owner])
            payload["customer_manager"] = "、".join(manager_values)
            payload["customer_manager_display_name"] = "、".join(
                _person_reference_display(value, users_by_username)[0] for value in manager_values
            )
        else:
            payload["customer_manager"] = ""
            payload["customer_manager_display_name"] = ""
        rows.append(payload)
    return {"items": rows, "total": len(items), "summary": {"total": len(items), "unclaimed": sum(1 for item in items if item.status == "待认领"), "unallocated": sum(1 for item in items if item.status in {"待分配", "部分分配"}), "completed": sum(1 for item in items if item.status == "已分配"), "amount": sum(item.amount for item in items) if can_view_amount else None, "remaining": sum(max(item.amount - item.allocated_amount, 0) for item in items) if can_view_amount else None}}


@router.get(f"{settings.api_prefix}/finance/customer-options")
async def list_finance_customer_options(
    keyword: str = Query("", max_length=255),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Search active system customers for receipt registration, never litigants."""
    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以登记银行到账")
    conditions = [
        BusinessRecord.module == "customer",
        BusinessRecord.status.not_in(["已回收"]),
        func.coalesce(BusinessRecord.data["customer_type"].as_string(), "客户") == "客户",
    ]
    normalized_keyword = keyword.strip()
    if normalized_keyword:
        like = f"%{normalized_keyword}%"
        conditions.append(or_(BusinessRecord.title.ilike(like), BusinessRecord.serial_no.ilike(like)))
    rows = list((await db.scalars(
        select(BusinessRecord).where(*conditions).order_by(BusinessRecord.title, BusinessRecord.id).limit(50)
    )).all())
    return {
        "items": [
            {"id": row.id, "title": row.title, "serial_no": row.serial_no}
            for row in rows
        ]
    }


@router.post(f"{settings.api_prefix}/finance/incoming-payments", status_code=status.HTTP_201_CREATED)
async def create_incoming_payment(body: IncomingPaymentInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _incoming_payment_dict, _round_fee_amount,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    if identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以登记银行到账")
    bank_reference = body.bank_reference.strip()
    if bank_reference and await db.scalar(select(IncomingPayment.id).where(IncomingPayment.bank_reference == bank_reference)): raise HTTPException(status_code=409, detail="银行流水号已经登记")
    contract_no = body.contract_no.strip()
    case_no = body.case_no.strip()
    customer = body.customer.strip()
    contract = None
    if contract_no:
        contract = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "contract", BusinessRecord.serial_no == contract_no))
        if not contract: raise HTTPException(status_code=422, detail="关联合同不存在")
        if customer and contract.customer != customer: raise HTTPException(status_code=422, detail="关联合同与所选客户不一致")
        customer = customer or contract.customer
    case_record = None
    if case_no:
        case_record = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "case", BusinessRecord.serial_no == case_no, *(await _record_scope_conditions(identity, db))))
        if not case_record: raise HTTPException(status_code=422, detail="关联案件不存在或无权查看")
        linked_contract_id = int((case_record.data or {}).get("contract_id") or 0)
        if contract:
            if linked_contract_id and linked_contract_id != contract.id:
                raise HTTPException(status_code=422, detail="关联案件不属于所选合同")
        elif linked_contract_id:
            contract = await db.get(BusinessRecord, linked_contract_id)
            if not contract or contract.module != "contract":
                raise HTTPException(status_code=422, detail="关联案件的合同不存在")
            contract_no = contract.serial_no
        customer = customer or case_record.customer
    item = IncomingPayment(receipt_no=f"HK{datetime.now():%Y%m%d%H%M%S%f}", received_date=body.received_date, amount=_round_fee_amount(body.amount), payer_name=body.payer_name.strip(), bank_reference=bank_reference or None, status="待认领", contract_record_id=contract.id if contract else None, contract_no=contract.serial_no if contract else "", case_no=case_no, bank_source=body.bank_source.strip(), operator=identity["username"], remark=body.remark)
    db.add(item); await db.flush()
    if body.claim:
        if not customer: raise HTTPException(status_code=422, detail="自动认领需要填写客户名称")
        claimed = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "customer", BusinessRecord.title == customer, *(await _record_scope_conditions(identity, db))))
        if not claimed: raise HTTPException(status_code=404, detail="客户不存在或无权认领")
        item.claimed_customer = claimed.title; item.claimant = identity["username"]; item.status = "待分配"
        item.remark = "；".join(part for part in [item.remark, "回款登记时自动认领"] if part)
        db.add(WorkflowEvent(record_id=claimed.id, action="认领银行到账", from_status=claimed.status, to_status=claimed.status, operator=identity["username"], comment=f"{item.receipt_no}｜{item.payer_name}｜{item.amount:.2f} 元。回款登记时自动认领"))
    await db.commit(); await db.refresh(item); return _incoming_payment_dict(item)


@router.post(f"{settings.api_prefix}/finance/incoming-payments/import")
async def import_incoming_payments(file: UploadFile = File(...), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _round_fee_amount,
    )
    from app.core.system import (
        _csv_value,
    )
    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以导入银行到账")
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="仅支持 UTF-8 CSV 文件")
    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="CSV 文件不能超过 5MB")
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="CSV 文件必须使用 UTF-8 编码") from exc
    existing = set((await db.scalars(select(IncomingPayment.bank_reference))).all())
    created = 0
    errors: list[dict] = []
    for row_no, row in enumerate(csv.DictReader(io.StringIO(content)), 2):
        try:
            payer = _csv_value(row, "对方户名", "付款人", "付款方", "payer_name")
            bank_reference = _csv_value(row, "银行流水号", "交易流水号", "业务编号", "bank_reference")
            received_text = _csv_value(row, "到账日期", "交易日期", "记账日期", "received_date")
            amount_text = _csv_value(row, "到账金额", "交易金额", "贷方发生额", "amount")
            if not payer or not bank_reference or not received_text or not amount_text:
                raise ValueError("缺少对方户名、银行流水号、到账日期或到账金额")
            if bank_reference in existing:
                raise ValueError("银行流水号已经登记")
            received_date = date.fromisoformat(received_text.replace("/", "-").strip())
            amount = _round_fee_amount(float(amount_text.replace(",", "").strip()))
            if amount <= 0:
                raise ValueError("到账金额必须大于 0")
            db.add(IncomingPayment(
                receipt_no=f"HK{datetime.now():%Y%m%d%H%M%S%f}{row_no}",
                received_date=received_date,
                amount=amount,
                payer_name=payer,
                bank_reference=bank_reference,
                status="待认领",
                operator=identity["username"],
                remark=_csv_value(row, "摘要", "备注", "remark"),
            ))
            existing.add(bank_reference)
            created += 1
        except (ValueError, TypeError) as exc:
            errors.append({"row": row_no, "error": str(exc) or "字段格式错误"})
    if created:
        await db.commit()
    return {"created": created, "errors": errors}


@router.get(f"{settings.api_prefix}/finance/incoming-payments/export")
async def export_incoming_payments(payment_status: str = "", keyword: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys, _excel_response,
    )
    items = (await db.scalars(select(IncomingPayment).order_by(IncomingPayment.received_date.desc(), IncomingPayment.id.desc()))).all()
    if identity.get("role") not in {"admin", "auditor"}:
        visible_customer_titles = set((await db.scalars(select(BusinessRecord.title).where(BusinessRecord.module == "customer", *(await _record_scope_conditions(identity, db))))).all())
        items = [item for item in items if item.operator == identity["username"] or item.claimant == identity["username"] or item.claimed_customer in visible_customer_titles]
    if payment_status: items = [item for item in items if item.status == payment_status]
    if keyword:
        key = keyword.casefold(); items = [item for item in items if key in f"{item.receipt_no} {item.payer_name} {item.bank_reference} {item.claimed_customer}".casefold()]
    can_view_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    headers = ["回款流水号", "到账日期", "回款单位", "银行流水号", "客户", "合同编号", "案件编号", "银行来源", "金额", "已分配金额", "剩余金额", "状态", "领取人", "登记人", "备注"]
    rows = []
    for item in items:
        amount = float(item.amount); allocated = float(item.allocated_amount or 0)
        rows.append([
            item.receipt_no, str(item.received_date), item.payer_name, item.bank_reference,
            item.claimed_customer, item.contract_no, item.case_no, item.bank_source,
            f"{amount:.2f}" if can_view_amount else "", f"{allocated:.2f}" if can_view_amount else "",
            f"{max(amount - allocated, 0):.2f}" if can_view_amount else "", item.status,
            item.claimant, item.operator, item.remark,
        ])
    return _excel_response(f"银行到账-{date.today()}.xls", headers, rows)


@router.get(f"{settings.api_prefix}/finance/incoming-payments/{{payment_id}}")
async def get_incoming_payment(payment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _general_settlement_rows, _incoming_payment_dict,
    )
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    item = await db.get(IncomingPayment, payment_id)
    if not item: raise HTTPException(status_code=404, detail="银行到账记录不存在")
    if identity.get("role") not in {"admin", "auditor"}:
        visible_customer_titles = set((await db.scalars(select(BusinessRecord.title).where(BusinessRecord.module == "customer", *(await _record_scope_conditions(identity, db))))).all())
        if item.operator != identity["username"] and item.claimant != identity["username"] and item.claimed_customer not in visible_customer_titles:
            raise HTTPException(status_code=404, detail="银行到账记录不存在")
    show_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    users_by_username = await _user_display_map({item.claimant, item.operator}, db)
    result = _incoming_payment_dict(item, show_amount=show_amount, users_by_username=users_by_username)
    settlement_rows = await _general_settlement_rows(
        identity,
        db,
        receipt_ids={payment_id},
        include_active_receipts=True,
    )
    if settlement_rows:
        settlement_data = settlement_rows[0]["data"]
        result.update({
            "payment_method": settlement_data.get("payment_method") or result.get("payment_method"),
            "assigned_official_fee": settlement_data.get("assigned_official_fee"),
            "assigned_agency_fee": settlement_data.get("assigned_agency_fee"),
            "assigned_other_fee": settlement_data.get("assigned_other_fee"),
            "allocation_details": settlement_data.get("allocation_details") or [],
        })
    else:
        result["allocation_details"] = []
    return result


@router.get(f"{settings.api_prefix}/finance/incoming-payments/{{payment_id}}/view-assigned")
async def view_assigned_incoming_payment(payment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _incoming_payment_dict,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    item = await db.get(IncomingPayment, payment_id)
    if not item: raise HTTPException(status_code=404, detail="银行到账记录不存在")
    if identity.get("role") not in {"admin", "auditor"}:
        visible_customer_titles = set((await db.scalars(select(BusinessRecord.title).where(BusinessRecord.module == "customer", *(await _record_scope_conditions(identity, db))))).all())
        if item.operator != identity["username"] and item.claimant != identity["username"] and item.claimed_customer not in visible_customer_titles:
            raise HTTPException(status_code=404, detail="银行到账记录不存在")
    rows = []
    for allocation in item.allocations or []:
        plan = await db.get(ReceivablePlan, int(allocation.get("receivable_plan_id") or 0))
        contract = await db.get(BusinessRecord, int(allocation.get("contract_id") or 0))
        case_record = await db.get(BusinessRecord, int(allocation.get("case_id") or 0))
        rows.append({
            **allocation,
            "plan": {"id": plan.id, "phase": plan.phase, "amount": plan.amount, "received_amount": plan.received_amount, "status": plan.status} if plan else None,
            "contract": {"id": contract.id, "serial_no": contract.serial_no, "title": contract.title} if contract else None,
            "case": {"id": case_record.id, "serial_no": case_record.serial_no, "title": case_record.title} if case_record else None,
        })
    return {"items": rows, "total": len(rows), "payment": _incoming_payment_dict(item, show_amount="finance.amount" in await _allowed_field_keys(identity, db))}


@router.post(f"{settings.api_prefix}/finance/incoming-payments/{{payment_id}}/claim")
async def claim_incoming_payment(payment_id: int, body: IncomingPaymentClaimInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _incoming_payment_dict,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    item = await db.get(IncomingPayment, payment_id)
    if not item: raise HTTPException(status_code=404, detail="银行到账记录不存在")
    if item.status not in {"待认领", "待分配"} or item.allocated_amount > 0: raise HTTPException(status_code=409, detail="已发生分配的到账不能重新认领")
    customer = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "customer", BusinessRecord.title == body.customer.strip(), *(await _record_scope_conditions(identity, db))))
    if not customer: raise HTTPException(status_code=404, detail="客户不存在或无权认领")
    item.claimed_customer = customer.title; item.claimant = identity["username"]; item.status = "待分配"; item.remark = "；".join(part for part in [item.remark, body.comment] if part)
    db.add(WorkflowEvent(record_id=customer.id, action="认领银行到账", from_status=customer.status, to_status=customer.status, operator=identity["username"], comment=f"{item.receipt_no}｜{item.payer_name}｜{item.amount:.2f} 元。{body.comment}"))
    await db.commit(); await db.refresh(item); return _incoming_payment_dict(item, show_amount="finance.amount" in await _allowed_field_keys(identity, db))


@router.get(f"{settings.api_prefix}/finance/incoming-payments/{{payment_id}}/allocation-candidates")
async def incoming_payment_allocation_candidates(payment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _case_is_for_allocation_customer,
    )
    from app.core.finance import (
        _round_fee_amount,
    )
    from app.core.formatters import (
        _record_belongs_to_customer,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    item = await db.get(IncomingPayment, payment_id)
    if not item:
        raise HTTPException(status_code=404, detail="银行到账记录不存在")
    if item.status not in {"待分配", "部分分配"} or not item.claimed_customer:
        raise HTTPException(status_code=409, detail="到账认领到客户后才能查看可分配案件费用")

    claimed_customer_record = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == "customer",
        BusinessRecord.title == item.claimed_customer,
        *(await _record_scope_conditions(identity, db)),
    ))
    customer_links = [BusinessRecord.customer == item.claimed_customer]
    if claimed_customer_record is not None:
        customer_links.extend([
            BusinessRecord.data["customer_id"].as_integer() == claimed_customer_record.id,
            BusinessRecord.data["customer_record_id"].as_integer() == claimed_customer_record.id,
        ])
        if str(claimed_customer_record.serial_no or "").strip():
            customer_links.append(BusinessRecord.data["customer_no"].as_string() == claimed_customer_record.serial_no)
    contracts = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "contract",
        or_(*customer_links),
        *(await _record_scope_conditions(identity, db)),
    ))).all())
    contracts_by_id = {contract.id: contract for contract in contracts}
    contract_ids = set(contracts_by_id)
    plans = list((await db.scalars(select(ReceivablePlan).where(
        ReceivablePlan.contract_record_id.in_(contract_ids),
    ).order_by(ReceivablePlan.due_date.asc(), ReceivablePlan.id.asc()))).all()) if contract_ids else []
    plans = [plan for plan in plans if _round_fee_amount(plan.amount - plan.received_amount) > 0]

    cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case",
        or_(*customer_links),
        *(await _record_scope_conditions(identity, db)),
    ).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()))).all())
    cases_by_contract: dict[int, list[BusinessRecord]] = {}
    case_count_by_contract: dict[int, int] = {}
    contract_no_to_id = {contract.serial_no: contract.id for contract in contracts}
    for case_record in cases:
        if not _record_belongs_to_customer(case_record, claimed_customer_record, item.claimed_customer):
            continue
        case_data = case_record.data or {}
        contract_id = int(case_data.get("contract_id") or case_data.get("contract_record_id") or 0)
        if not contract_id:
            contract_id = contract_no_to_id.get(str(case_data.get("contract_no") or "").strip(), 0)
        if contract_id in contracts_by_id:
            case_count_by_contract[contract_id] = case_count_by_contract.get(contract_id, 0) + 1
            if _case_is_for_allocation_customer(case_record, claimed_customer_record, item.claimed_customer):
                cases_by_contract.setdefault(contract_id, []).append(case_record)

    rows = []
    for plan in plans:
        contract = contracts_by_id[plan.contract_record_id]
        remaining = _round_fee_amount(plan.amount - plan.received_amount)
        linked_cases = cases_by_contract.get(contract.id)
        if not linked_cases and case_count_by_contract.get(contract.id):
            continue
        linked_cases = linked_cases or [None]
        for case_record in linked_cases:
            case_data = case_record.data or {} if case_record else {}
            submitted_at = (
                case_data.get("case_register_date")
                or case_data.get("submission_date")
                or case_data.get("filing_date")
                or (case_record.created_at.isoformat() if case_record and case_record.created_at else "")
            )
            rows.append({
                "key": f"{plan.id}:{case_record.id if case_record else 0}",
                "receivable_plan_id": plan.id,
                "contract_id": contract.id,
                "contract_no": contract.serial_no,
                "case_id": case_record.id if case_record else None,
                "case_no": case_record.serial_no if case_record else "",
                "case_title": case_record.title if case_record else contract.title,
                "plaintiff": str(case_data.get("plaintiff") or case_data.get("appellant_names") or contract.customer),
                "defendant": str(case_data.get("defendant") or case_data.get("appellee_names") or case_data.get("opponent") or ""),
                "case_stage": str(case_data.get("case_stage") or case_data.get("business_stage") or (case_record.status if case_record else "合同应收")),
                "submission_date": str(submitted_at)[:10],
                "fee_type": plan.phase,
                "total_amount": _round_fee_amount(plan.amount),
                "received_amount": _round_fee_amount(plan.received_amount),
                "remaining_amount": remaining,
            })
    # Some legacy case fees were created without a receivable-plan row.  They
    # are still payable case expenses and must appear in the same allocation
    # dialog, but only when their contract and case belong to the claimed
    # customer.
    plan_ids = {plan.id for plan in plans}
    fees = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance",
        or_(*customer_links),
        *(await _record_scope_conditions(identity, db)),
    ).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()))).all())
    for fee_record in fees:
        fee_data = fee_record.data or {}
        fee_contract_id = int(fee_data.get("contract_id") or fee_data.get("contract_record_id") or 0)
        fee_contract_no = str(fee_data.get("contract_no") or "").strip()
        fee_case_id = int(fee_data.get("case_id") or fee_data.get("case_record_id") or 0)
        fee_case_no = str(fee_data.get("case_no") or "").strip()
        fee_cases = [case for case in cases if case.id == fee_case_id or (fee_case_no and case.serial_no == fee_case_no)]
        if fee_case_id or fee_case_no:
            fee_cases = [case for case in fee_cases if _case_is_for_allocation_customer(case, claimed_customer_record, item.claimed_customer)]
            if not fee_cases:
                continue
        contract = contracts_by_id.get(fee_contract_id)
        if contract is None and fee_contract_no:
            contract = next((item for item in contracts if item.serial_no == fee_contract_no), None)
        has_explicit_contract = bool(fee_contract_id or fee_contract_no)
        if contract is None and not has_explicit_contract and fee_cases:
            case_data = fee_cases[0].data or {}
            case_contract_id = int(case_data.get("contract_id") or case_data.get("contract_record_id") or 0)
            case_contract_no = str(case_data.get("contract_no") or "").strip()
            contract = contracts_by_id.get(case_contract_id)
            if contract is None and case_contract_no:
                contract = next((item for item in contracts if item.serial_no == case_contract_no), None)
        if contract is None or not _record_belongs_to_customer(fee_record, claimed_customer_record, item.claimed_customer):
            continue
        if fee_data.get("receivable_plan_id") and int(fee_data["receivable_plan_id"]) in plan_ids:
            continue
        total_amount = _round_fee_amount(float(fee_data.get("amount") or 0))
        received_amount = _round_fee_amount(float(fee_data.get("received_amount") or fee_data.get("cashed_amount") or 0))
        remaining = _round_fee_amount(total_amount - received_amount)
        if remaining <= 0:
            continue
        for case_record in (fee_cases or [None]):
            case_data = case_record.data or {} if case_record else {}
            rows.append({
                "key": f"fee:{fee_record.id}:{case_record.id if case_record else 0}",
                "receivable_plan_id": None,
                "fee_record_id": fee_record.id,
                "contract_id": contract.id,
                "contract_no": contract.serial_no,
                "case_id": case_record.id if case_record else None,
                "case_no": case_record.serial_no if case_record else fee_case_no,
                "case_title": case_record.title if case_record else fee_record.title,
                "plaintiff": str(case_data.get("plaintiff") or case_data.get("appellant_names") or contract.customer),
                "defendant": str(case_data.get("defendant") or case_data.get("appellee_names") or case_data.get("opponent") or ""),
                "case_stage": str(case_data.get("case_stage") or case_data.get("business_stage") or (case_record.status if case_record else "案件费用")),
                "submission_date": str(case_data.get("case_register_date") or case_data.get("submission_date") or "")[:10],
                "fee_type": str(fee_data.get("fee_type") or fee_record.title or "案件费用"),
                "total_amount": total_amount,
                "received_amount": received_amount,
                "remaining_amount": remaining,
            })
    return {
        "items": rows,
        "total": len(rows),
        "customer": item.claimed_customer,
        "remaining_amount": _round_fee_amount(item.amount - item.allocated_amount),
    }


@router.post(f"{settings.api_prefix}/finance/incoming-payments/{{payment_id}}/allocate")
async def allocate_incoming_payment(payment_id: int, body: IncomingPaymentAllocateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _case_is_for_allocation_customer,
    )
    from app.core.finance import (
        _incoming_payment_dict, _round_fee_amount,
    )
    from app.core.formatters import (
        _record_belongs_to_customer,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    item = await db.get(IncomingPayment, payment_id)
    if not item: raise HTTPException(status_code=404, detail="银行到账记录不存在")
    if item.status not in {"待分配", "部分分配"} or not item.claimed_customer: raise HTTPException(status_code=409, detail="到账认领到客户后才能分配")
    claimed_customer_record = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == "customer",
        BusinessRecord.title == item.claimed_customer,
        *(await _record_scope_conditions(identity, db)),
    ))
    total = _round_fee_amount(sum(entry.amount for entry in body.allocations)); remaining_payment = _round_fee_amount(item.amount - item.allocated_amount)
    if total > remaining_payment + 0.001: raise HTTPException(status_code=409, detail=f"分配金额超过到账未分配余额 {remaining_payment:.2f} 元")
    prepared: list[tuple[IncomingPaymentAllocationItem, ReceivablePlan, BusinessRecord, BusinessRecord | None, BusinessRecord | None]] = []
    plan_totals: dict[int, float] = {}
    fee_totals: dict[int, float] = {}
    for entry in body.allocations:
        if entry.settlement_items:
            classified_total = _round_fee_amount(sum(item.amount for item in entry.settlement_items))
            if abs(classified_total - _round_fee_amount(entry.amount)) > 0.001:
                raise HTTPException(status_code=422, detail="结算费用明细金额之和必须等于本次分配金额")
            invalid_settlement = [item.fee_type for item in entry.settlement_items if item.settlement_amount + 0.001 < item.archive_fee]
            if invalid_settlement:
                raise HTTPException(status_code=422, detail="归档费不能大于结算金额：" + "、".join(invalid_settlement))
            excessive_settlement = [item.fee_type for item in entry.settlement_items if item.settlement_amount > item.amount + 0.001]
            if excessive_settlement:
                raise HTTPException(status_code=422, detail="结算金额不能大于分配金额：" + "、".join(excessive_settlement))
        plan = await db.get(ReceivablePlan, entry.receivable_plan_id) if entry.receivable_plan_id else None
        fee_record = await _ensure_record_module(entry.fee_record_id, "finance", identity, db) if entry.fee_record_id else None
        if not plan and not fee_record:
            raise HTTPException(status_code=422, detail="分配项目必须关联应收计划或案件费用")
        if plan:
            contract = await _ensure_record_module(plan.contract_record_id, "contract", identity, db)
            phase = plan.phase
            remaining_plan = _round_fee_amount(plan.amount - plan.received_amount)
            plan_totals[plan.id] = _round_fee_amount(plan_totals.get(plan.id, 0) + entry.amount)
            if plan_totals[plan.id] > remaining_plan + 0.001: raise HTTPException(status_code=409, detail=f"{contract.serial_no}｜{phase} 分配金额合计超过未收 {remaining_plan:.2f} 元")
        else:
            fee_data = fee_record.data or {}
            contract_id = int(fee_data.get("contract_id") or fee_data.get("contract_record_id") or 0)
            contract_no = str(fee_data.get("contract_no") or "").strip()
            contract = await db.get(BusinessRecord, contract_id) if contract_id else None
            if not contract and contract_no:
                contract = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "contract", BusinessRecord.serial_no == contract_no))
            has_explicit_contract = bool(contract_id or contract_no)
            if not contract and not has_explicit_contract:
                fee_case_id = int(fee_data.get("case_id") or fee_data.get("case_record_id") or 0)
                fee_case_no = str(fee_data.get("case_no") or "").strip()
                linked_case = await db.get(BusinessRecord, fee_case_id) if fee_case_id else None
                if not linked_case and fee_case_no:
                    linked_case = await db.scalar(select(BusinessRecord).where(
                        BusinessRecord.module == "case",
                        BusinessRecord.serial_no == fee_case_no,
                        *(await _record_scope_conditions(identity, db)),
                    ))
                if linked_case and linked_case.module == "case":
                    linked_case_data = linked_case.data or {}
                    linked_contract_id = int(linked_case_data.get("contract_id") or linked_case_data.get("contract_record_id") or 0)
                    linked_contract_no = str(linked_case_data.get("contract_no") or "").strip()
                    contract = await db.get(BusinessRecord, linked_contract_id) if linked_contract_id else None
                    if not contract and linked_contract_no:
                        contract = await db.scalar(select(BusinessRecord).where(
                            BusinessRecord.module == "contract",
                            BusinessRecord.serial_no == linked_contract_no,
                        ))
            if not contract or contract.module != "contract":
                raise HTTPException(status_code=409, detail=f"费用 {fee_record.serial_no} 未关联有效合同")
            phase = str(fee_data.get("fee_type") or fee_record.title or "案件费用")
            fee_total = _round_fee_amount(float(fee_data.get("amount") or 0))
            fee_received = _round_fee_amount(float(fee_data.get("received_amount") or fee_data.get("cashed_amount") or 0))
            remaining_plan = _round_fee_amount(fee_total - fee_received)
            fee_totals[fee_record.id] = _round_fee_amount(fee_totals.get(fee_record.id, 0) + entry.amount)
            if fee_totals[fee_record.id] > remaining_plan + 0.001: raise HTTPException(status_code=409, detail=f"{fee_record.serial_no} 分配金额合计超过未收 {remaining_plan:.2f} 元")
            plan = ReceivablePlan(contract_record_id=contract.id, phase=phase, due_date=item.received_date, amount=fee_total, received_amount=fee_received, status="部分收款" if fee_received else "待收款", payer=item.claimed_customer, remark=f"案件费用 {fee_record.serial_no}")
            db.add(plan); await db.flush()
        if not _record_belongs_to_customer(contract, claimed_customer_record, item.claimed_customer): raise HTTPException(status_code=409, detail=f"应收项目 {phase} 的客户与到账认领客户不一致")
        case_record = None
        if entry.case_no.strip():
            case_record = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "case", BusinessRecord.serial_no == entry.case_no.strip(), *(await _record_scope_conditions(identity, db))))
            case_data = case_record.data or {} if case_record else {}
            linked_contract_id = int(case_data.get("contract_id") or case_data.get("contract_record_id") or 0)
            linked_contract_no = str(case_data.get("contract_no") or "").strip()
            case_contract_matches = linked_contract_id == contract.id or (
                not linked_contract_id and linked_contract_no == contract.serial_no
            )
            fee_data = fee_record.data or {} if fee_record else {}
            fee_case_id = int(fee_data.get("case_id") or fee_data.get("case_record_id") or 0)
            fee_case_no = str(fee_data.get("case_no") or "").strip()
            fee_contract_id = int(fee_data.get("contract_id") or fee_data.get("contract_record_id") or 0)
            fee_contract_no = str(fee_data.get("contract_no") or "").strip()
            legacy_fee_relation_matches = bool(
                case_record
                and not linked_contract_id
                and not linked_contract_no
                and (fee_case_id == case_record.id or (not fee_case_id and fee_case_no == case_record.serial_no))
                and (fee_contract_id == contract.id or (not fee_contract_id and fee_contract_no == contract.serial_no))
            )
            if not case_record or not (case_contract_matches or legacy_fee_relation_matches):
                raise HTTPException(status_code=409, detail=f"案件 {entry.case_no} 不属于所选合同")
            if not _record_belongs_to_customer(case_record, claimed_customer_record, item.claimed_customer):
                raise HTTPException(status_code=409, detail=f"案件 {entry.case_no} 的客户与到账认领客户不一致")
            if not _case_is_for_allocation_customer(case_record, claimed_customer_record, item.claimed_customer):
                raise HTTPException(status_code=409, detail=f"案件 {entry.case_no} 的诉讼当事人与到账认领客户不一致")
        for settlement in entry.settlement_items:
            if settlement.fee_record_id is None:
                continue
            fee_record = await _ensure_record_module(settlement.fee_record_id, "finance", identity, db)
            fee_data = fee_record.data or {}
            if not _record_belongs_to_customer(fee_record, claimed_customer_record, item.claimed_customer):
                raise HTTPException(status_code=409, detail=f"费用 {fee_record.serial_no} 的客户与到账认领客户不一致")
            if case_record and int(fee_data.get("case_id") or 0) not in {0, case_record.id} and str(fee_data.get("case_no") or "") != case_record.serial_no:
                raise HTTPException(status_code=409, detail=f"费用 {fee_record.serial_no} 不属于案件 {case_record.serial_no}")
        prepared.append((entry, plan, contract, case_record, fee_record))
    allocation_rows = list(item.allocations or [])
    for entry, plan, contract, case_record, fee_record in prepared:
        amount = _round_fee_amount(entry.amount); plan.received_amount = _round_fee_amount(plan.received_amount + amount); plan.status = "已收款" if plan.received_amount + 0.001 >= plan.amount else "部分收款"
        if fee_record:
            fee_data = dict(fee_record.data or {})
            fee_data["received_amount"] = _round_fee_amount(float(fee_data.get("received_amount") or fee_data.get("cashed_amount") or 0) + amount)
            fee_data["received_at"] = item.received_date.isoformat()
            fee_data["cashed_date"] = item.received_date.isoformat()
            fee_data["incoming_payment_id"] = item.id
            fee_data["receipt_no"] = item.receipt_no
            fee_record.data = fee_data
        tx = FinanceTransaction(finance_record_id=contract.id, transaction_type="回款", amount=amount, transaction_date=item.received_date, voucher_no=item.bank_reference, counterparty=item.payer_name, operator=identity["username"], remark=f"银行到账 {item.receipt_no} 分配至 {contract.serial_no}｜{plan.phase}" + (f"｜案件 {case_record.serial_no}" if case_record else ""))
        db.add(tx); await db.flush(); row = {"receivable_plan_id": plan.id, "fee_record_id": fee_record.id if fee_record else None, "contract_id": contract.id, "contract_no": contract.serial_no, "phase": plan.phase, "case_id": case_record.id if case_record else None, "case_no": case_record.serial_no if case_record else "", "amount": amount, "payment_method": entry.payment_method.strip(), "settlement_items": [settlement.model_dump() for settlement in entry.settlement_items], "transaction_id": tx.id, "allocated_by": identity["username"], "allocated_at": datetime.now().isoformat(timespec="seconds")}; allocation_rows.append(row)
        db.add(WorkflowEvent(record_id=contract.id, action="分配银行回款", from_status=contract.status, to_status=contract.status, operator=identity["username"], comment=f"{item.receipt_no}｜{plan.phase}｜{amount:.2f} 元。{body.comment}"))
    item.allocated_amount = _round_fee_amount(item.allocated_amount + total); item.allocations = allocation_rows; item.status = "已分配" if item.allocated_amount + 0.001 >= item.amount else "部分分配"
    await db.commit(); await db.refresh(item); return _incoming_payment_dict(item, show_amount="finance.amount" in await _allowed_field_keys(identity, db))


@router.delete(f"{settings.api_prefix}/finance/incoming-payments/{{payment_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_incoming_payment(payment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _round_fee_amount,
    )
    if identity.get("role") != "admin": raise HTTPException(status_code=403, detail="仅管理员可删除银行到账")
    item = await db.get(IncomingPayment, payment_id)
    if not item: raise HTTPException(status_code=404, detail="银行到账记录不存在")
    for allocation in item.allocations or []:
        plan = await db.get(ReceivablePlan, int(allocation.get("receivable_plan_id") or 0)); amount = float(allocation.get("amount") or 0)
        if plan:
            plan.received_amount = max(_round_fee_amount(plan.received_amount - amount), 0); plan.status = "待收款" if plan.received_amount <= 0 else "部分收款"
        tx = await db.get(FinanceTransaction, int(allocation.get("transaction_id") or 0))
        if tx: await db.delete(tx)
    await db.delete(item); await db.commit(); return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(f"{settings.api_prefix}/finance/incoming-payments/{{payment_id}}")
async def update_incoming_payment(payment_id: int, body: IncomingPaymentUpdateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _incoming_payment_dict, _round_fee_amount,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    if identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以编辑银行到账")
    item = await db.get(IncomingPayment, payment_id)
    if not item: raise HTTPException(status_code=404, detail="银行到账记录不存在")
    if item.allocations or item.allocated_amount > 0: raise HTTPException(status_code=409, detail="已发生分配的到账不能编辑")
    bank_reference = body.bank_reference.strip()
    if bank_reference and await db.scalar(select(IncomingPayment.id).where(IncomingPayment.bank_reference == bank_reference, IncomingPayment.id != payment_id)): raise HTTPException(status_code=409, detail="银行流水号已经登记")
    contract_no = body.contract_no.strip(); case_no = body.case_no.strip(); customer = body.customer.strip(); contract = None
    if contract_no:
        contract = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "contract", BusinessRecord.serial_no == contract_no))
        if not contract: raise HTTPException(status_code=422, detail="关联合同不存在")
        if customer and contract.customer != customer: raise HTTPException(status_code=422, detail="关联合同与所选客户不一致")
        customer = customer or contract.customer
    if case_no:
        case_record = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "case", BusinessRecord.serial_no == case_no, *(await _record_scope_conditions(identity, db))))
        if not case_record: raise HTTPException(status_code=422, detail="关联案件不存在或无权查看")
        linked_contract_id = int((case_record.data or {}).get("contract_id") or 0)
        if contract:
            if linked_contract_id and linked_contract_id != contract.id:
                raise HTTPException(status_code=422, detail="关联案件不属于所选合同")
        elif linked_contract_id:
            contract = await db.get(BusinessRecord, linked_contract_id)
            if not contract or contract.module != "contract":
                raise HTTPException(status_code=422, detail="关联案件的合同不存在")
            contract_no = contract.serial_no
        customer = customer or case_record.customer
    item.received_date = body.received_date; item.amount = _round_fee_amount(body.amount); item.payer_name = body.payer_name.strip(); item.bank_reference = bank_reference or None; item.contract_record_id = contract.id if contract else None; item.contract_no = contract.serial_no if contract else ""; item.case_no = case_no; item.bank_source = body.bank_source.strip(); item.remark = body.remark
    if customer and not item.allocations:
        item.claimed_customer = customer
    await db.commit(); await db.refresh(item); return _incoming_payment_dict(item, show_amount="finance.amount" in await _allowed_field_keys(identity, db))


@router.get(f"{settings.api_prefix}/finance/incoming-payments/{{payment_id}}/refund-candidates")
async def incoming_payment_refund_candidates(payment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _round_fee_amount,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    item = await db.get(IncomingPayment, payment_id)
    if not item: raise HTTPException(status_code=404, detail="银行到账记录不存在")
    if item.allocations or item.allocated_amount > 0: raise HTTPException(status_code=409, detail="已发生分配的到账不能领取退费")
    if "法院" not in item.payer_name: raise HTTPException(status_code=422, detail="只有法院退款到账可以匹配官方费用")
    remaining = _round_fee_amount(item.amount - item.allocated_amount)
    fees = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "finance", *(await _record_scope_conditions(identity, db))))).all()
    candidates = []
    for fee in fees:
        data = fee.data or {}
        if str(data.get("fee_type") or "") != "官方费用": continue
        if fee.status not in {"已付款", "部分付款"}: continue
        court = str(data.get("court") or "").strip()
        if court and court not in item.payer_name and item.payer_name not in court: continue
        amount = _round_fee_amount(float(data.get("amount") or 0))
        candidates.append({"fee_record_id": fee.id, "serial_no": fee.serial_no, "title": fee.title, "case_no": data.get("case_no", ""), "court": court or item.payer_name, "amount": amount, "match_amount": _round_fee_amount(min(amount, remaining))})
    return {"items": candidates, "total": len(candidates), "remaining_amount": remaining}


@router.post(f"{settings.api_prefix}/finance/incoming-payments/{{payment_id}}/refund-claim")
async def refund_claim_incoming_payment(payment_id: int, body: IncomingPaymentRefundClaimInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _incoming_payment_dict,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    item = await db.get(IncomingPayment, payment_id)
    if not item: raise HTTPException(status_code=404, detail="银行到账记录不存在")
    if item.status not in {"待认领", "待分配"} or item.allocated_amount > 0: raise HTTPException(status_code=409, detail="已发生分配的到账不能重新认领")
    if "法院" not in item.payer_name: raise HTTPException(status_code=422, detail="只有法院退款到账可以领取退费")
    customer = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "customer", BusinessRecord.title == body.customer.strip(), *(await _record_scope_conditions(identity, db))))
    if not customer: raise HTTPException(status_code=404, detail="客户不存在或无权认领")
    fee_record = None
    if body.fee_record_id:
        fee_record = await _ensure_record_module(body.fee_record_id, "finance", identity, db)
        if str((fee_record.data or {}).get("fee_type") or "") != "官方费用": raise HTTPException(status_code=422, detail="匹配的退费记录不是官方费用")
    item.claimed_customer = customer.title; item.claimant = identity["username"]; item.status = "待分配"; item.remark = "；".join(part for part in [item.remark, body.comment] if part)
    db.add(WorkflowEvent(record_id=customer.id, action="认领退费到账", from_status=customer.status, to_status=customer.status, operator=identity["username"], comment=f"{item.receipt_no}｜{item.payer_name}｜{item.amount:.2f} 元。{body.comment}"))
    if fee_record:
        db.add(WorkflowEvent(record_id=fee_record.id, action="匹配退费到账", from_status=fee_record.status, to_status=fee_record.status, operator=identity["username"], comment=f"{item.receipt_no} 匹配 {fee_record.serial_no}"))
    await db.commit(); await db.refresh(item); return _incoming_payment_dict(item, show_amount="finance.amount" in await _allowed_field_keys(identity, db))


@router.post(f"{settings.api_prefix}/finance/incoming-payments/revoke-allocations")
async def revoke_incoming_payment_allocations(body: IncomingPaymentRevokeInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _incoming_payment_dict, _round_fee_amount,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    if identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以批量撤销分配")
    payment_ids = list(dict.fromkeys(body.payment_ids))
    items = list((await db.scalars(select(IncomingPayment).where(IncomingPayment.id.in_(payment_ids)))).all())
    if len(items) != len(payment_ids): raise HTTPException(status_code=404, detail="部分银行到账记录不存在")
    revoked = 0
    for item in items:
        if not (item.allocations or item.allocated_amount > 0):
            continue
        for allocation in item.allocations or []:
            plan = await db.get(ReceivablePlan, int(allocation.get("receivable_plan_id") or 0)); amount = float(allocation.get("amount") or 0)
            if plan:
                plan.received_amount = max(_round_fee_amount(plan.received_amount - amount), 0); plan.status = "待收款" if plan.received_amount <= 0 else "部分收款"
            contract = await db.get(BusinessRecord, int(allocation.get("contract_id") or 0))
            if contract:
                db.add(WorkflowEvent(record_id=contract.id, action="撤销银行回款分配", from_status=contract.status, to_status=contract.status, operator=identity["username"], comment=f"{item.receipt_no}｜{plan.phase if plan else ''}｜{amount:.2f} 元。{body.comment}"))
            tx = await db.get(FinanceTransaction, int(allocation.get("transaction_id") or 0))
            if tx: await db.delete(tx)
        item.allocations = []; item.allocated_amount = 0; item.status = "待分配"
        revoked += 1
    await db.commit()
    for item in items:
        await db.refresh(item)
    return {"revoked": revoked, "items": [_incoming_payment_dict(item, show_amount="finance.amount" in await _allowed_field_keys(identity, db)) for item in items]}


@router.get(f"{settings.api_prefix}/finance/ar-summary")
async def finance_ar_summary(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _receivable_dict, _round_fee_amount,
    )
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _visible_record_ids,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    plans = (await db.scalars(select(ReceivablePlan).order_by(ReceivablePlan.due_date.asc(), ReceivablePlan.id.asc()))).all()
    contract_ids = {plan.contract_record_id for plan in plans}
    visible_ids = await _visible_record_ids(identity, db)
    contracts = {record.id: record for record in (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "contract",
        BusinessRecord.id.in_(contract_ids & visible_ids),
    ))).all()} if contract_ids and visible_ids else {}
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
        _case_fee_type_snapshot, _finance_fee_commission_details, _finance_linked_case, _resolve_case_fee_contract, _resolve_case_fee_type_master,
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
    if case_record:
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
    commission_details = await _finance_fee_commission_details(body, amount, db)
    serial = f"FY{datetime.now():%Y%m%d%H%M%S%f}"
    item = BusinessRecord(module="finance", serial_no=serial, title=body.title, customer=body.customer, status="草稿", owner=handler, department=user.department, description=body.description, data={"amount": amount, **fee_snapshot, "expense_scope": body.expense_scope or "", "is_refund": fee_snapshot["fee_type"] == "内部费用" and amount < 0, "case_no": case_record.serial_no if case_record else body.case_no, "case_id": case_record.id if case_record else None, "contract_id": contract_record.id if contract_record else None, "contract_no": contract_record.serial_no if contract_record else "", "deadline": str(body.deadline) if body.deadline else "", "handler": handler, "court": body.court, "document_no": body.document_no, "payee": body.payee, "base_amount": body.base_amount, "reference_commission": body.reference_commission, "commission_details": commission_details})
    db.add(item); await db.flush()
    db.add(WorkflowEvent(record_id=item.id, action="创建费用", to_status="草稿", operator=identity["username"], comment=f"{fee_snapshot['fee_type_path']}：{amount:.2f} 元"))
    await db.commit(); await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)


@router.get(f"{settings.api_prefix}/finance/general-settlements/pending")
async def list_general_settlement_candidates(
    customer: str = "", case_no: str = "",
    received_from: date | None = None, received_to: date | None = None,
    payer: str = "", payment_method: str = "", case_customer: str = "",
    hearing_lawyer: str = "", assistant: str = "", customer_manager: str = "", source_person: str = "",
    page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _general_settlement_rows, _round_fee_amount,
    )
    if received_from and received_to and received_from > received_to:
        raise HTTPException(status_code=422, detail="回款开始日期不能晚于结束日期")
    rows = await _general_settlement_rows(
        identity, db, customer=customer, case_no=case_no,
        received_from=received_from, received_to=received_to, payer=payer,
        payment_method=payment_method, case_customer=case_customer,
        hearing_lawyer=hearing_lawyer, assistant=assistant,
        customer_manager=customer_manager, source_person=source_person,
    )
    amount_keys = ["receipt_amount", "allocated_amount", "remaining_amount", "assigned_official_fee", "assigned_agency_fee", "assigned_other_fee", "agency_settlement_amount", "archive_fee", "actual_settlement_amount"]
    totals = {key: _round_fee_amount(sum(float((row.get("data") or {}).get(key) or 0) for row in rows)) for key in amount_keys}
    start = (page - 1) * page_size
    return {"items": rows[start:start + page_size], "total": len(rows), "totals": totals, "page": page, "page_size": page_size}


@router.post(f"{settings.api_prefix}/finance/general-settlements/apply", status_code=status.HTTP_201_CREATED)
async def apply_general_settlements(body: FinanceSettlementApplyInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _general_settlement_rows,
    )
    receipt_ids = list(dict.fromkeys(body.receipt_ids))
    rows = await _general_settlement_rows(identity, db, receipt_ids=set(receipt_ids))
    rows_by_id = {int(row["id"]): row for row in rows}
    missing = [str(receipt_id) for receipt_id in receipt_ids if receipt_id not in rows_by_id]
    if missing:
        raise HTTPException(status_code=409, detail="部分回款已申请结算、尚未分配或无权办理：" + "、".join(missing))
    created: list[BusinessRecord] = []
    now_key = datetime.now().strftime("%Y%m%d%H%M%S%f")
    for index, receipt_id in enumerate(receipt_ids):
        row = rows_by_id[receipt_id]
        row_data = dict(row.get("data") or {})
        application = BusinessRecord(
            module="finance_settlement",
            serial_no=f"JS{now_key}{index:02d}",
            title=f"{row.get('customer') or row_data.get('payer_name')}结算申请",
            customer=str(row.get("customer") or ""),
            status="待审批",
            owner=identity["username"],
            department=str(identity.get("department") or "上海分所"),
            description=body.comment.strip(),
            data={**row_data, "applied_by": identity["username"], "applied_at": datetime.now().isoformat(timespec="seconds")},
        )
        db.add(application)
        await db.flush()
        db.add(WorkflowEvent(record_id=application.id, action="申请结算", to_status="待审批", operator=identity["username"], comment=body.comment.strip()))
        created.append(application)
    await db.commit()
    return {"created": len(created), "application_ids": [item.id for item in created], "application_nos": [item.serial_no for item in created]}


@router.get(f"{settings.api_prefix}/finance/archive-settlements/pending")
async def list_pending_archive_settlements(
    case_type: str = "", case_stage: str = "", payer: str = "",
    received_from: date | None = None, received_to: date | None = None,
    hearing_lawyer: str = "", assistant: str = "", submitted_by: str = "",
    settled_from: date | None = None, settled_to: date | None = None,
    case_no: str = "", customer: str = "", reviewer: str = "",
    page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _pending_archive_settlement_rows, _round_fee_amount,
    )
    for start_date, end_date, label in (
        (received_from, received_to, "回款"),
        (settled_from, settled_to, "结算支付"),
    ):
        if start_date and end_date and start_date > end_date:
            raise HTTPException(status_code=422, detail=f"{label}开始日期不能晚于结束日期")
    rows = await _pending_archive_settlement_rows(
        identity, db, case_type=case_type, case_stage=case_stage, payer=payer,
        received_from=received_from, received_to=received_to,
        hearing_lawyer=hearing_lawyer, assistant=assistant, submitted_by=submitted_by,
        settled_from=settled_from, settled_to=settled_to, case_no=case_no,
        customer=customer, reviewer=reviewer,
    )
    totals = {
        "receipt_amount": _round_fee_amount(sum(float((row.get("data") or {}).get("receipt_amount") or 0) for row in rows)),
        "archive_fee_amount": _round_fee_amount(sum(float((row.get("data") or {}).get("archive_fee_amount") or 0) for row in rows)),
    }
    start = (page - 1) * page_size
    return {"items": rows[start:start + page_size], "total": len(rows), "totals": totals, "page": page, "page_size": page_size}


@router.get(f"{settings.api_prefix}/finance/archive-settlements/export")
async def export_pending_archive_settlements(
    ids: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _pending_archive_settlement_rows,
    )
    selected_ids = {item.strip() for item in ids.split(",") if item.strip()}
    if not selected_ids:
        raise HTTPException(status_code=422, detail="请选择需要导出的归档费.")
    rows = await _pending_archive_settlement_rows(identity, db, selected_ids=selected_ids)
    if len(rows) != len(selected_ids):
        raise HTTPException(status_code=409, detail="部分归档费不存在、已进入下一环节或无权导出")
    headers = ["案号", "客户", "案件阶段", "律师助理", "开庭律师", "客户管理人", "费用类型", "回款方式", "回款时间", "回款金额", "归档费金额", "结算时间"]
    numeric = {9, 10}
    values = [[
        row["data"].get("case_no"), row.get("customer"), row["data"].get("case_stage"),
        row["data"].get("assistant"), row["data"].get("hearing_lawyer"), row["data"].get("customer_manager"),
        row["data"].get("fee_type"), row["data"].get("payment_method"), row["data"].get("received_date"),
        row["data"].get("receipt_amount"), row["data"].get("archive_fee_amount"), row["data"].get("settlement_paid_at"),
    ] for row in rows]
    def cell(value: object, *, number: bool = False) -> str:
        value_text = f"{float(value or 0):.2f}" if number else str(value or "")
        return f'<Cell><Data ss:Type="{"Number" if number else "String"}">{xml_escape(value_text)}</Data></Cell>'
    sheet_rows = ["<Row>" + "".join(cell(value) for value in headers) + "</Row>"]
    sheet_rows.extend("<Row>" + "".join(cell(value, number=index in numeric and value is not None) for index, value in enumerate(row)) + "</Row>" for row in values)
    workbook = '<?xml version="1.0" encoding="UTF-8"?><?mso-application progid="Excel.Sheet"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="待归档"><Table>' + "".join(sheet_rows) + "</Table></Worksheet></Workbook>"
    filename = f"待归档-{date.today()}.xls"
    disposition = f"attachment; filename=archive-settlement-pending.xls; filename*=UTF-8''{quote(filename)}"
    return Response(content=workbook.encode("utf-8"), media_type="application/vnd.ms-excel", headers={"Content-Disposition": disposition})


@router.get(f"{settings.api_prefix}/finance/archive-settlements/payment")
async def list_archive_settlement_payments(
    case_type: str = "", case_stage: str = "", payer: str = "",
    received_from: date | None = None, received_to: date | None = None,
    hearing_lawyer: str = "", assistant: str = "", submitted_by: str = "",
    settled_from: date | None = None, settled_to: date | None = None,
    case_no: str = "", customer: str = "", reviewer: str = "",
    archive_from: date | None = None, archive_to: date | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _pending_archive_settlement_rows, _round_fee_amount,
    )
    for start_date, end_date, label in (
        (received_from, received_to, "回款"),
        (settled_from, settled_to, "结算支付"),
        (archive_from, archive_to, "归档"),
    ):
        if start_date and end_date and start_date > end_date:
            raise HTTPException(status_code=422, detail=f"{label}开始日期不能晚于结束日期")
    rows = await _pending_archive_settlement_rows(
        identity, db, case_type=case_type, case_stage=case_stage, payer=payer,
        received_from=received_from, received_to=received_to,
        hearing_lawyer=hearing_lawyer, assistant=assistant, submitted_by=submitted_by,
        settled_from=settled_from, settled_to=settled_to, case_no=case_no,
        customer=customer, reviewer=reviewer, archive_from=archive_from,
        archive_to=archive_to, require_archived=True,
    )
    totals = {
        "receipt_amount": _round_fee_amount(sum(float((row.get("data") or {}).get("receipt_amount") or 0) for row in rows)),
        "archive_fee_amount": _round_fee_amount(sum(float((row.get("data") or {}).get("archive_fee_amount") or 0) for row in rows)),
    }
    start = (page - 1) * page_size
    return {"items": rows[start:start + page_size], "total": len(rows), "totals": totals, "page": page, "page_size": page_size}


@router.post(f"{settings.api_prefix}/finance/archive-settlements/payment/review")
async def review_archive_settlement_payments(
    body: ArchiveSettlementPaymentReviewInput,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _pending_archive_settlement_rows,
    )
    from app.core.permissions import (
        _settlement_application_scope,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有归档费支付审核权限")
    settlement_ids = list(dict.fromkeys(item.strip() for item in body.settlement_ids if item.strip()))
    if len(settlement_ids) != len(body.settlement_ids):
        raise HTTPException(status_code=422, detail="归档费记录不能为空或重复")
    if not body.approved and not body.comment.strip():
        raise HTTPException(status_code=422, detail="拒绝支付时请输入备注.")
    rows = await _pending_archive_settlement_rows(
        identity, db, require_archived=True, selected_ids=set(settlement_ids),
    )
    if len(rows) != len(settlement_ids):
        raise HTTPException(status_code=409, detail="部分归档费不存在、已处理或无权审核")
    row_map = {row["id"]: row for row in rows}
    decided_at = datetime.now().isoformat(timespec="seconds")
    reusable = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance_archive_settlement",
        BusinessRecord.status == "已回滚",
        *_settlement_application_scope(identity),
    ))).all())
    reusable_by_source = {str((item.data or {}).get("source_row_id") or ""): item for item in reusable}
    created: list[BusinessRecord] = []
    for source_id in settlement_ids:
        row = row_map[source_id]
        data = row.get("data") or {}
        target_status = "已支付" if body.approved else "已拒绝"
        decision = reusable_by_source.get(source_id)
        if decision:
            previous_status = decision.status
            decision.status = target_status
            decision.title = row.get("title") or "归档费支付"
            decision.customer = row.get("customer") or ""
            decision.owner = row.get("owner") or identity["username"]
            decision.department = row.get("department") or str(identity.get("department") or "")
            decision.data = {
                **data,
                "source_row_id": source_id,
                "source_application_id": data.get("application_id"),
                "archive_payment_submitted_by": data.get("submitted_by") or row.get("owner") or identity["username"],
                "archive_payment_submitted_at": data.get("settlement_paid_at") or decided_at,
                "archive_payment_reviewer": identity["username"],
                "archive_payment_reviewed_at": decided_at,
                "archive_payment_comment": body.comment.strip(),
            }
        else:
            previous_status = "待支付"
            decision = BusinessRecord(
                module="finance_archive_settlement",
                serial_no=f"ARCP-{source_id.replace(':', '-')}",
                title=row.get("title") or "归档费支付",
                customer=row.get("customer") or "",
                status=target_status,
                owner=row.get("owner") or identity["username"],
                department=row.get("department") or str(identity.get("department") or ""),
                data={
                    **data,
                    "source_row_id": source_id,
                    "source_application_id": data.get("application_id"),
                    "archive_payment_submitted_by": data.get("submitted_by") or row.get("owner") or identity["username"],
                    "archive_payment_submitted_at": data.get("settlement_paid_at") or decided_at,
                    "archive_payment_reviewer": identity["username"],
                    "archive_payment_reviewed_at": decided_at,
                    "archive_payment_comment": body.comment.strip(),
                },
            )
        db.add(decision)
        await db.flush()
        db.add(WorkflowEvent(
            record_id=decision.id,
            action="归档费同意支付" if body.approved else "归档费拒绝支付",
            from_status=previous_status, to_status=target_status,
            operator=identity["username"], comment=body.comment.strip(),
        ))
        created.append(decision)
    await db.commit()
    return {"reviewed": len(created), "status": "已支付" if body.approved else "已拒绝", "record_ids": [item.id for item in created]}


@router.get(f"{settings.api_prefix}/finance/archive-settlements/payment/export")
async def export_archive_settlement_payments(
    ids: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _pending_archive_settlement_rows,
    )
    selected_ids = {item.strip() for item in ids.split(",") if item.strip()}
    if not selected_ids:
        raise HTTPException(status_code=422, detail="请选择需要导出的归档费.")
    rows = await _pending_archive_settlement_rows(identity, db, require_archived=True, selected_ids=selected_ids)
    if len(rows) != len(selected_ids):
        raise HTTPException(status_code=409, detail="部分归档费不存在、已处理或无权导出")
    headers = ["案号", "客户", "案件阶段", "律师助理", "开庭律师", "客户管理人", "费用类型", "回款方式", "回款时间", "回款金额", "归档费金额", "支付时间", "归档号", "归档日期"]
    numeric = {9, 10}
    values = [[
        row["data"].get("case_no"), row.get("customer"), row["data"].get("case_stage"),
        row["data"].get("assistant"), row["data"].get("hearing_lawyer"), row["data"].get("customer_manager"),
        row["data"].get("fee_type"), row["data"].get("payment_method"), row["data"].get("received_date"),
        row["data"].get("receipt_amount"), row["data"].get("archive_fee_amount"), row["data"].get("settlement_paid_at"),
        row["data"].get("archive_no"), row["data"].get("archive_date"),
    ] for row in rows]
    def cell(value: object, *, number: bool = False) -> str:
        value_text = f"{float(value or 0):.2f}" if number else str(value or "")
        return f'<Cell><Data ss:Type="{"Number" if number else "String"}">{xml_escape(value_text)}</Data></Cell>'
    sheet_rows = ["<Row>" + "".join(cell(value) for value in headers) + "</Row>"]
    sheet_rows.extend("<Row>" + "".join(cell(value, number=index in numeric) for index, value in enumerate(row)) + "</Row>" for row in values)
    workbook = '<?xml version="1.0" encoding="UTF-8"?><?mso-application progid="Excel.Sheet"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="待支付"><Table>' + "".join(sheet_rows) + "</Table></Worksheet></Workbook>"
    filename = f"待支付归档费-{date.today()}.xls"
    disposition = f"attachment; filename=archive-settlement-payment.xls; filename*=UTF-8''{quote(filename)}"
    return Response(content=workbook.encode("utf-8"), media_type="application/vnd.ms-excel", headers={"Content-Disposition": disposition})


@router.get(f"{settings.api_prefix}/finance/archive-settlements/paid")
async def list_paid_archive_settlements(
    case_type: str = "", case_stage: str = "", payer: str = "",
    received_from: date | None = None, received_to: date | None = None,
    hearing_lawyer: str = "", assistant: str = "", submitted_by: str = "",
    settled_from: date | None = None, settled_to: date | None = None,
    case_no: str = "", customer: str = "", reviewer: str = "",
    archive_from: date | None = None, archive_to: date | None = None,
    payment_from: date | None = None, payment_to: date | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _archive_settlement_decision_rows, _round_fee_amount,
    )
    for start_date, end_date, label in (
        (received_from, received_to, "回款"), (settled_from, settled_to, "结算支付"),
        (archive_from, archive_to, "归档"), (payment_from, payment_to, "归档费支付"),
    ):
        if start_date and end_date and start_date > end_date:
            raise HTTPException(status_code=422, detail=f"{label}开始日期不能晚于结束日期")
    rows = await _archive_settlement_decision_rows(
        identity, db, statuses={"已支付"}, case_type=case_type, case_stage=case_stage,
        payer=payer, received_from=received_from, received_to=received_to,
        hearing_lawyer=hearing_lawyer, assistant=assistant, submitted_by=submitted_by,
        settled_from=settled_from, settled_to=settled_to, case_no=case_no,
        customer=customer, reviewer=reviewer, archive_from=archive_from,
        archive_to=archive_to, payment_from=payment_from, payment_to=payment_to,
    )
    totals = {
        "receipt_amount": _round_fee_amount(sum(float((row.get("data") or {}).get("receipt_amount") or 0) for row in rows)),
        "archive_fee_amount": _round_fee_amount(sum(float((row.get("data") or {}).get("archive_fee_amount") or 0) for row in rows)),
    }
    start = (page - 1) * page_size
    return {"items": rows[start:start + page_size], "total": len(rows), "totals": totals, "page": page, "page_size": page_size}


@router.post(f"{settings.api_prefix}/finance/archive-settlements/paid/rollback")
async def rollback_paid_archive_settlements(
    body: ArchiveSettlementRollbackInput,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _settlement_application_scope,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有归档费支付回滚权限")
    if not body.comment.strip():
        raise HTTPException(status_code=422, detail="请输入备注.")
    record_ids = list(dict.fromkeys(body.record_ids))
    if len(record_ids) != len(body.record_ids):
        raise HTTPException(status_code=422, detail="归档费记录不能重复")
    records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(record_ids),
        BusinessRecord.module == "finance_archive_settlement",
        BusinessRecord.status == "已支付",
        *_settlement_application_scope(identity),
    ))).all())
    if len(records) != len(record_ids):
        raise HTTPException(status_code=409, detail="部分归档费不存在、不是已支付状态或无权回滚")
    rolled_back_at = datetime.now().isoformat(timespec="seconds")
    for record in records:
        record.status = "已回滚"
        record.data = {
            **(record.data or {}),
            "archive_payment_rollback_by": identity["username"],
            "archive_payment_rollback_at": rolled_back_at,
            "archive_payment_rollback_comment": body.comment.strip(),
        }
        db.add(WorkflowEvent(
            record_id=record.id, action="回滚归档费支付",
            from_status="已支付", to_status="已回滚",
            operator=identity["username"], comment=body.comment.strip(),
        ))
    await db.commit()
    return {"rolled_back": len(records), "status": "已回滚"}


@router.get(f"{settings.api_prefix}/finance/archive-settlements/paid/export")
async def export_paid_archive_settlements(
    ids: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _archive_settlement_decision_rows,
    )
    try:
        selected_ids = {int(item.strip()) for item in ids.split(",") if item.strip()}
    except ValueError:
        raise HTTPException(status_code=422, detail="归档费记录编号无效")
    if not selected_ids:
        raise HTTPException(status_code=422, detail="请选择需要导出的归档费.")
    rows = await _archive_settlement_decision_rows(identity, db, statuses={"已支付"}, selected_ids=selected_ids)
    if len(rows) != len(selected_ids):
        raise HTTPException(status_code=409, detail="部分归档费不存在、已回滚或无权导出")
    headers = ["案号", "客户", "案件阶段", "律师助理", "开庭律师", "客户管理人", "费用类型", "回款方式", "回款时间", "回款金额", "归档费金额", "结算时间", "归档费支付日期"]
    numeric = {9, 10}
    values = [[
        row["data"].get("case_no"), row.get("customer"), row["data"].get("case_stage"),
        row["data"].get("assistant"), row["data"].get("hearing_lawyer"), row["data"].get("customer_manager"),
        row["data"].get("fee_type"), row["data"].get("payment_method"), row["data"].get("received_date"),
        row["data"].get("receipt_amount"), row["data"].get("archive_fee_amount"), row["data"].get("settlement_paid_at"),
        row["data"].get("archive_payment_reviewed_at"),
    ] for row in rows]
    def cell(value: object, *, number: bool = False) -> str:
        value_text = f"{float(value or 0):.2f}" if number else str(value or "")
        return f'<Cell><Data ss:Type="{"Number" if number else "String"}">{xml_escape(value_text)}</Data></Cell>'
    sheet_rows = ["<Row>" + "".join(cell(value) for value in headers) + "</Row>"]
    sheet_rows.extend("<Row>" + "".join(cell(value, number=index in numeric and value is not None) for index, value in enumerate(row)) + "</Row>" for row in values)
    workbook = '<?xml version="1.0" encoding="UTF-8"?><?mso-application progid="Excel.Sheet"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="已支付"><Table>' + "".join(sheet_rows) + "</Table></Worksheet></Workbook>"
    filename = f"已支付归档费-{date.today()}.xls"
    disposition = f"attachment; filename=archive-settlement-paid.xls; filename*=UTF-8''{quote(filename)}"
    return Response(content=workbook.encode("utf-8"), media_type="application/vnd.ms-excel", headers={"Content-Disposition": disposition})


@router.get(f"{settings.api_prefix}/finance/archive-settlements/rejected")
async def list_rejected_archive_settlements(
    case_type: str = "", case_stage: str = "", payer: str = "",
    received_from: date | None = None, received_to: date | None = None,
    hearing_lawyer: str = "", assistant: str = "", submitted_by: str = "",
    submitted_from: date | None = None, submitted_to: date | None = None,
    case_no: str = "", customer: str = "", reviewer: str = "",
    reviewed_from: date | None = None, reviewed_to: date | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _archive_settlement_decision_rows, _round_fee_amount,
    )
    for start_date, end_date, label in (
        (received_from, received_to, "回款"),
        (submitted_from, submitted_to, "提交"),
        (reviewed_from, reviewed_to, "审核"),
    ):
        if start_date and end_date and start_date > end_date:
            raise HTTPException(status_code=422, detail=f"{label}开始日期不能晚于结束日期")
    rows = await _archive_settlement_decision_rows(
        identity, db, statuses={"已拒绝"}, case_type=case_type, case_stage=case_stage,
        payer=payer, received_from=received_from, received_to=received_to,
        hearing_lawyer=hearing_lawyer, assistant=assistant, submitted_by=submitted_by,
        submitted_from=submitted_from, submitted_to=submitted_to,
        case_no=case_no, customer=customer, reviewer=reviewer,
        reviewed_from=reviewed_from, reviewed_to=reviewed_to,
    )
    totals = {
        "receipt_amount": _round_fee_amount(sum(float((row.get("data") or {}).get("receipt_amount") or 0) for row in rows)),
        "archive_fee_amount": _round_fee_amount(sum(float((row.get("data") or {}).get("archive_fee_amount") or 0) for row in rows)),
    }
    start = (page - 1) * page_size
    return {"items": rows[start:start + page_size], "total": len(rows), "totals": totals, "page": page, "page_size": page_size}


@router.post(f"{settings.api_prefix}/finance/archive-settlements/rejected/rollback")
async def rollback_rejected_archive_settlements(
    body: ArchiveSettlementRejectedActionInput,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _rejected_archive_settlement_records,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有归档费拒绝回滚权限")
    if not body.comment.strip():
        raise HTTPException(status_code=422, detail="请输入审核备注.")
    records = await _rejected_archive_settlement_records(body.record_ids, identity, db)
    changed_at = datetime.now().isoformat(timespec="seconds")
    for record in records:
        record.status = "已支付"
        record.data = {
            **(record.data or {}),
            "archive_rejection_rollback_by": identity["username"],
            "archive_rejection_rollback_at": changed_at,
            "archive_rejection_rollback_comment": body.comment.strip(),
        }
        db.add(WorkflowEvent(
            record_id=record.id, action="回滚归档费拒绝",
            from_status="已拒绝", to_status="已支付",
            operator=identity["username"], comment=body.comment.strip(),
        ))
    await db.commit()
    return {"rolled_back": len(records), "status": "已支付"}


@router.post(f"{settings.api_prefix}/finance/archive-settlements/rejected/reapply")
async def reapply_rejected_archive_settlements(
    body: ArchiveSettlementRejectedActionInput,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _rejected_archive_settlement_records,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有归档费重新申请权限")
    records = await _rejected_archive_settlement_records(body.record_ids, identity, db)
    changed_at = datetime.now().isoformat(timespec="seconds")
    for record in records:
        record.status = "已回滚"
        record.data = {
            **(record.data or {}),
            "archive_payment_reapplied_by": identity["username"],
            "archive_payment_reapplied_at": changed_at,
            "archive_payment_reapply_comment": body.comment.strip(),
        }
        db.add(WorkflowEvent(
            record_id=record.id, action="重新申请归档费",
            from_status="已拒绝", to_status="已回滚",
            operator=identity["username"], comment=body.comment.strip(),
        ))
    await db.commit()
    return {"reapplied": len(records), "status": "待支付"}


@router.get(f"{settings.api_prefix}/finance/archive-settlements/rejected/export")
async def export_rejected_archive_settlements(
    ids: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _archive_settlement_decision_rows,
    )
    try:
        selected_ids = {int(item.strip()) for item in ids.split(",") if item.strip()}
    except ValueError:
        raise HTTPException(status_code=422, detail="归档费记录编号无效")
    if not selected_ids:
        raise HTTPException(status_code=422, detail="请选择案件.")
    rows = await _archive_settlement_decision_rows(identity, db, statuses={"已拒绝"}, selected_ids=selected_ids)
    if len(rows) != len(selected_ids):
        raise HTTPException(status_code=409, detail="部分归档费不存在、已重新申请或无权导出")
    headers = ["案号", "客户", "案件阶段", "律师助理", "开庭律师", "客户管理人", "费用类型", "回款方式", "回款时间", "回款金额", "归档费金额", "结算时间", "支付状态"]
    numeric = {9, 10}
    values = [[
        row["data"].get("case_no"), row.get("customer"), row["data"].get("case_stage"),
        row["data"].get("assistant"), row["data"].get("hearing_lawyer"), row["data"].get("customer_manager"),
        row["data"].get("fee_type"), row["data"].get("payment_method"), row["data"].get("received_date"),
        row["data"].get("receipt_amount"), row["data"].get("archive_fee_amount"), row["data"].get("settlement_paid_at"),
        row.get("status"),
    ] for row in rows]
    def cell(value: object, *, number: bool = False) -> str:
        value_text = f"{float(value or 0):.2f}" if number else str(value or "")
        return f'<Cell><Data ss:Type="{"Number" if number else "String"}">{xml_escape(value_text)}</Data></Cell>'
    sheet_rows = ["<Row>" + "".join(cell(value) for value in headers) + "</Row>"]
    sheet_rows.extend("<Row>" + "".join(cell(value, number=index in numeric and value is not None) for index, value in enumerate(row)) + "</Row>" for row in values)
    workbook = '<?xml version="1.0" encoding="UTF-8"?><?mso-application progid="Excel.Sheet"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="已拒绝"><Table>' + "".join(sheet_rows) + "</Table></Worksheet></Workbook>"
    filename = f"已拒绝归档费-{date.today()}.xls"
    disposition = f"attachment; filename=archive-settlement-rejected.xls; filename*=UTF-8''{quote(filename)}"
    return Response(content=workbook.encode("utf-8"), media_type="application/vnd.ms-excel", headers={"Content-Disposition": disposition})


@router.get(f"{settings.api_prefix}/finance/general-settlements/applications")
async def list_general_settlement_applications(
    customer: str = "", case_no: str = "", customer_manager: str = "",
    received_from: date | None = None, received_to: date | None = None,
    payer: str = "", payment_method: str = "", applied_by: str = "",
    applied_from: date | None = None, applied_to: date | None = None,
    hearing_lawyer: str = "", assistant: str = "", reviewer: str = "",
    reviewed_from: date | None = None, reviewed_to: date | None = None,
    paid_from: date | None = None, paid_to: date | None = None,
    source_person: str = "", application_status: str = Query("待审批", alias="status"),
    page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _round_fee_amount,
    )
    from app.core.permissions import (
        _record_dict_for_identity, _settlement_application_scope,
    )
    for start_date, end_date, label in (
        (received_from, received_to, "回款"),
        (applied_from, applied_to, "提交"),
        (reviewed_from, reviewed_to, "审核"),
        (paid_from, paid_to, "付款"),
    ):
        if start_date and end_date and start_date > end_date:
            raise HTTPException(status_code=422, detail=f"{label}开始日期不能晚于结束日期")
    allowed_statuses = {"待审批", "待付款", "部分付款", "已付款", "已拒绝", "已驳回", "已退回"}
    application_statuses = {item.strip() for item in application_status.split(",") if item.strip()}
    if not application_statuses or not application_statuses.issubset(allowed_statuses):
        raise HTTPException(status_code=422, detail="结算申请状态无效")
    records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance_settlement",
        BusinessRecord.status.in_(application_statuses),
        *_settlement_application_scope(identity),
    ).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()))).all())

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

    filtered: list[BusinessRecord] = []
    for record in records:
        data = record.data or {}
        # CaseCenter writes handling_lawyers as an array, while older rows
        # may contain a singular string.  Normalize before any legacy join so
        # a string is never iterated character-by-character.
        handling_values = data.get("handling_lawyers")
        if isinstance(handling_values, str):
            data = {**data, "handling_lawyers": [handling_values]}
        elif not handling_values and isinstance(data.get("handling_lawyer"), str):
            data = {**data, "handling_lawyers": [data["handling_lawyer"]]}
        if not contains(record.customer, customer) or not contains(data.get("case_nos"), case_no):
            continue
        if not contains(data.get("customer_manager"), customer_manager):
            continue
        if not date_in_range(data.get("received_date"), received_from, received_to):
            continue
        if not contains(data.get("payer_name"), payer) or not contains(data.get("payment_method"), payment_method):
            continue
        if not contains(data.get("applied_by") or record.owner, applied_by):
            continue
        if not date_in_range(data.get("applied_at") or record.created_at, applied_from, applied_to):
            continue
        if not contains(data.get("hearing_lawyer"), hearing_lawyer) or not contains(data.get("assistant"), assistant):
            continue
        if not contains(data.get("reviewer"), reviewer):
            continue
        if not date_in_range(data.get("reviewed_at"), reviewed_from, reviewed_to):
            continue
        if not date_in_range(data.get("paid_at"), paid_from, paid_to):
            continue
        if not contains(data.get("source_person"), source_person):
            continue
        filtered.append(record)

    items = [await _record_dict_for_identity(record, identity, db) for record in filtered]
    amount_keys = ["receipt_amount", "allocated_amount", "remaining_amount", "assigned_official_fee", "assigned_agency_fee", "assigned_other_fee", "agency_settlement_amount", "archive_fee", "actual_settlement_amount"]
    totals = {key: _round_fee_amount(sum(float((item.get("data") or {}).get(key) or 0) for item in items)) for key in amount_keys}
    start = (page - 1) * page_size
    return {"items": items[start:start + page_size], "total": len(items), "totals": totals, "page": page, "page_size": page_size}


@router.post(f"{settings.api_prefix}/finance/general-settlements/applications/reapply")
async def reapply_general_settlement_applications(body: FinanceSettlementReapplyInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _settlement_application_scope,
    )
    comment = body.comment.strip()
    if not comment:
        raise HTTPException(status_code=422, detail="请输入备注.")
    application_ids = list(dict.fromkeys(body.application_ids))
    records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(application_ids),
        BusinessRecord.module == "finance_settlement",
        *_settlement_application_scope(identity),
    ))).all())
    if len(records) != len(application_ids):
        raise HTTPException(status_code=404, detail="部分结算申请不存在或无权访问")
    allowed_from = {"已拒绝", "已驳回", "已退回"}
    invalid = [record.serial_no for record in records if record.status not in allowed_from]
    if invalid:
        raise HTTPException(status_code=409, detail="仅已拒绝或已退回结算可以重新申请：" + "、".join(invalid))
    reapplied_at = datetime.now().isoformat(timespec="seconds")
    for record in records:
        previous_status = record.status
        record.status = "待审批"
        record.description = comment
        record.data = {
            **(record.data or {}),
            "applied_by": identity["username"],
            "applied_at": reapplied_at,
            "reapplied_by": identity["username"],
            "reapplied_at": reapplied_at,
            "reapply_comment": comment,
        }
        db.add(WorkflowEvent(
            record_id=record.id,
            action="重新申请结算",
            from_status=previous_status,
            to_status="待审批",
            operator=identity["username"],
            comment=comment,
        ))
    await db.commit()
    return {"reapplied": len(records), "application_ids": application_ids, "status": "待审批"}


@router.post(f"{settings.api_prefix}/finance/general-settlements/applications/review")
async def review_general_settlement_applications(body: FinanceSettlementReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _settlement_application_scope,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有结算审批权限")
    application_ids = list(dict.fromkeys(body.application_ids))
    records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(application_ids),
        BusinessRecord.module == "finance_settlement",
        *_settlement_application_scope(identity),
    ))).all())
    if len(records) != len(application_ids):
        raise HTTPException(status_code=404, detail="部分结算申请不存在或无权访问")
    invalid = [record.serial_no for record in records if record.status != "待审批"]
    if invalid:
        raise HTTPException(status_code=409, detail="仅待审批结算申请可以审核：" + "、".join(invalid))
    target_status = "待付款" if body.approved else "已拒绝"
    action = "同意结算" if body.approved else "拒绝结算"
    reviewed_at = datetime.now().isoformat(timespec="seconds")
    comment = body.comment.strip()
    for record in records:
        record.status = target_status
        record.data = {
            **(record.data or {}),
            "reviewer": identity["username"],
            "reviewed_at": reviewed_at,
            "review_comment": comment,
        }
        db.add(WorkflowEvent(
            record_id=record.id, action=action, from_status="待审批",
            to_status=target_status, operator=identity["username"], comment=comment,
        ))
    await db.commit()
    return {"reviewed": len(records), "application_ids": application_ids, "status": target_status}


@router.post(f"{settings.api_prefix}/finance/general-settlements/applications/payment")
async def pay_or_rollback_general_settlement_applications(body: FinanceSettlementPaymentInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _settlement_application_scope,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有结算付款权限")
    application_ids = list(dict.fromkeys(body.application_ids))
    records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(application_ids),
        BusinessRecord.module == "finance_settlement",
        *_settlement_application_scope(identity),
    ))).all())
    if len(records) != len(application_ids):
        raise HTTPException(status_code=404, detail="部分结算申请不存在或无权访问")
    invalid = [record.serial_no for record in records if record.status not in {"待付款", "已付款"}]
    if invalid:
        raise HTTPException(status_code=409, detail="仅待付款或已付款结算申请可以处理付款：" + "、".join(invalid))
    paid_again = [record.serial_no for record in records if record.status == "已付款" and body.action == "paid"]
    if paid_again:
        raise HTTPException(status_code=409, detail="已付款结算申请只能回退：" + "、".join(paid_again))
    comment = body.comment.strip()
    if body.action == "rollback" and not comment:
        raise HTTPException(status_code=422, detail="请输入审核备注.")
    if body.action == "rollback":
        archive_decisions = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "finance_archive_settlement",
            BusinessRecord.status.in_({"已支付", "已拒绝"}),
            *_settlement_application_scope(identity),
        ))).all())
        blocked_application_ids = {
            int((decision.data or {}).get("source_application_id") or 0)
            for decision in archive_decisions
        } & set(application_ids)
        if blocked_application_ids:
            raise HTTPException(
                status_code=409,
                detail="请先回滚或重新申请关联归档费，再回退结算",
            )
    processed_at = datetime.now().isoformat(timespec="seconds")
    if body.action == "paid":
        target_status = "已付款"
        action = "标记已支付"
        data_updates = {
            "paid_by": identity["username"],
            "paid_at": processed_at,
            "paid_comment": comment,
        }
    else:
        target_status = "已退回"
        action = "回退结算"
        data_updates = {
            "rollback_by": identity["username"],
            "rollback_at": processed_at,
            "rollback_comment": comment,
            "rejection_comment": comment,
        }
    for record in records:
        previous_status = record.status
        record.status = target_status
        record.data = {**(record.data or {}), **data_updates}
        db.add(WorkflowEvent(
            record_id=record.id,
            action=action,
            from_status=previous_status,
            to_status=target_status,
            operator=identity["username"],
            comment=comment,
        ))
    await db.commit()
    return {
        "processed": len(records),
        "application_ids": application_ids,
        "status": target_status,
        "action": action,
    }


@router.get(f"{settings.api_prefix}/finance/general-settlements/export")
async def export_general_settlements(
    kind: str = Query("settlement", pattern="^(settlement|receipt|case)$"), ids: str = "", application_ids: str = "",
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _general_settlement_rows,
    )
    from app.core.permissions import (
        _settlement_application_scope,
    )
    from app.core.system import (
        _export_ids,
    )
    if application_ids.strip():
        selected_application_ids = set(_export_ids(application_ids))
        if not selected_application_ids:
            raise HTTPException(status_code=422, detail="请选择需要导出的结算申请.")
        records = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.id.in_(selected_application_ids),
            BusinessRecord.module == "finance_settlement",
            *_settlement_application_scope(identity),
        ))).all())
        if len(records) != len(selected_application_ids):
            raise HTTPException(status_code=409, detail="部分结算申请不存在或无权导出")
        rows = [{
            "id": record.id,
            "serial_no": str((record.data or {}).get("receipt_no") or record.serial_no),
            "customer": record.customer,
            "data": record.data or {},
        } for record in records]
    else:
        selected_ids = set(_export_ids(ids)) if ids.strip() else None
        if selected_ids is not None and not selected_ids:
            raise HTTPException(status_code=422, detail="请选择需要导出的回款.")
        rows = await _general_settlement_rows(identity, db, receipt_ids=selected_ids)
        if selected_ids is not None and len({int(row["id"]) for row in rows}) != len(selected_ids):
            raise HTTPException(status_code=409, detail="部分回款已申请结算、尚未分配或无权导出")
    if not rows:
        raise HTTPException(status_code=422, detail="没有可导出的待结算记录")
    def cell(value: object, *, number: bool = False) -> str:
        value_text = f"{float(value or 0):.2f}" if number else str(value or "")
        return f'<Cell><Data ss:Type="{"Number" if number else "String"}">{xml_escape(value_text)}</Data></Cell>'
    if kind == "receipt":
        headers = ["回款编号", "客户名称", "回款单位", "回款日期", "回款金额", "已分金额", "未分金额", "回款方式", "银行备注"]
        values = [[row["serial_no"], row["customer"], row["data"].get("payer_name"), row["data"].get("received_date"), row["data"].get("receipt_amount"), row["data"].get("allocated_amount"), row["data"].get("remaining_amount"), row["data"].get("payment_method"), row["data"].get("bank_remark")] for row in rows]
        numeric = {4, 5, 6}
        sheet_name = "到账清单"
    elif kind == "case":
        headers = ["回款编号", "案号", "阶段", "费用类型", "本笔分配金额", "本笔结算金额", "本笔归档费", "客户", "经办律师", "律师助理", "合同号"]
        values = [[row["serial_no"], detail.get("case_no"), detail.get("case_stage"), detail.get("fee_type"), detail.get("current_amount"), detail.get("settlement_amount"), detail.get("archive_fee"), detail.get("customer"), detail.get("handling_lawyer"), detail.get("assistant"), detail.get("contract_no")] for row in rows for detail in row["data"].get("allocation_details", [])]
        numeric = {4, 5, 6}
        sheet_name = "案件清单"
    else:
        headers = ["回款编号", "客户名称", "客户管理人", "回款单位", "回款日期", "回款金额", "已分金额", "未分金额", "已分官费", "已分代理费", "已分其他费用", "代理费结算金额", "扣归档费", "实际结算金额"]
        values = [[row["serial_no"], row["customer"], row["data"].get("customer_manager"), row["data"].get("payer_name"), row["data"].get("received_date"), row["data"].get("receipt_amount"), row["data"].get("allocated_amount"), row["data"].get("remaining_amount"), row["data"].get("assigned_official_fee"), row["data"].get("assigned_agency_fee"), row["data"].get("assigned_other_fee"), row["data"].get("agency_settlement_amount"), row["data"].get("archive_fee"), row["data"].get("actual_settlement_amount")] for row in rows]
        numeric = set(range(5, 14))
        sheet_name = "结算清单"
    sheet_rows = ["<Row>" + "".join(cell(value) for value in headers) + "</Row>"]
    sheet_rows.extend("<Row>" + "".join(cell(value, number=index in numeric) for index, value in enumerate(row)) + "</Row>" for row in values)
    workbook = '<?xml version="1.0" encoding="UTF-8"?><?mso-application progid="Excel.Sheet"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="' + sheet_name + '"><Table>' + "".join(sheet_rows) + "</Table></Worksheet></Workbook>"
    filename = f"{sheet_name}-{date.today()}.xls"
    disposition = f"attachment; filename=settlement-export.xls; filename*=UTF-8''{quote(filename)}"
    return Response(content=workbook.encode("utf-8"), media_type="application/vnd.ms-excel", headers={"Content-Disposition": disposition})


@router.delete(f"{settings.api_prefix}/finance/general-settlements/applications/{{application_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_general_settlement_application(application_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    if identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可以删除结算申请")
    item = await db.get(BusinessRecord, application_id)
    if not item or item.module != "finance_settlement":
        raise HTTPException(status_code=404, detail="结算申请不存在")
    archive_decisions = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance_archive_settlement",
    ))).all()
    for decision in archive_decisions:
        if int((decision.data or {}).get("source_application_id") or 0) == item.id:
            await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == decision.id))
            await db.delete(decision)
    await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == item.id))
    await db.delete(item)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/finance/settlements/pending")
async def list_pending_finance_settlements(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Return paid internal fees enriched with their case and bank-receipt context."""
    from app.core.permissions import (
        _record_dict_for_identity, _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    fees = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance",
        BusinessRecord.status == "已付款",
        *(await _record_scope_conditions(identity, db)),
    ).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all()
    fees = [item for item in fees if (item.data or {}).get("fee_type") == "内部费用" and not (item.data or {}).get("commission_paid")]
    case_ids = {int((item.data or {}).get("case_id") or 0) for item in fees if (item.data or {}).get("case_id")}
    case_nos = {str((item.data or {}).get("case_no") or "") for item in fees if (item.data or {}).get("case_no")}
    cases = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case",
        or_(BusinessRecord.id.in_(case_ids), BusinessRecord.serial_no.in_(case_nos)),
        *(await _record_scope_conditions(identity, db)),
    ))).all() if case_ids or case_nos else []
    cases_by_id = {item.id: item for item in cases}
    cases_by_no = {item.serial_no: item for item in cases}
    payments = (await db.scalars(select(IncomingPayment).order_by(IncomingPayment.received_date.desc(), IncomingPayment.id.desc()))).all()
    if identity.get("role") not in {"admin", "auditor"}:
        visible_customers = {item.customer for item in cases}
        payments = [item for item in payments if item.operator == identity["username"] or item.claimant == identity["username"] or item.claimed_customer in visible_customers]
    can_view_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    rows = []
    for fee in fees:
        fee_data = fee.data or {}
        case = cases_by_id.get(int(fee_data.get("case_id") or 0)) or cases_by_no.get(str(fee_data.get("case_no") or ""))
        case_data = (case.data or {}) if case else {}
        receipt_matches: list[tuple[IncomingPayment, dict]] = []
        for payment in payments:
            for allocation in payment.allocations or []:
                if (case and int(allocation.get("case_id") or 0) == case.id) or (fee_data.get("case_no") and allocation.get("case_no") == fee_data.get("case_no")):
                    receipt_matches.append((payment, allocation))
        receipt_amount = sum(float(allocation.get("amount") or 0) for _, allocation in receipt_matches)
        latest_payment = receipt_matches[0][0] if receipt_matches else None
        record = await _record_dict_for_identity(fee, identity, db)
        record["data"] = {
            **record.get("data", {}),
            "case_id": case.id if case else fee_data.get("case_id"),
            "case_no": case.serial_no if case else fee_data.get("case_no", ""),
            "plaintiff": case_data.get("plaintiff", ""),
            "defendant": case_data.get("defendant") or case_data.get("opponent", ""),
            "court_case_no": case_data.get("court_case_no", ""),
            "certificate_no": case_data.get("certificate_no", ""),
            "case_stage": case_data.get("case_stage") or case.status if case else "",
            "case_source": case_data.get("case_source") or case_data.get("source_person", ""),
            "hearing_lawyer": case_data.get("hearing_lawyer", ""),
            "assistant": case_data.get("assistant") or case_data.get("lawyer_assistant", ""),
            "investigator": case_data.get("investigator", ""),
            "quality_manager": case_data.get("quality_manager") or case_data.get("quality_control", ""),
            "receipt_amount": receipt_amount if can_view_amount else None,
            "receipt_date": str(latest_payment.received_date) if latest_payment else "",
            "payee": latest_payment.payer_name if latest_payment else fee_data.get("payee", ""),
            "settlement_status": fee.status,
        }
        rows.append(record)
    return {"items": rows, "total": len(rows)}


@router.post(f"{settings.api_prefix}/finance/settlements/mark-commission-paid")
async def mark_finance_settlements_commission_paid(body: FinanceSettlementMarkInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _record_scope_conditions,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有标识提成发放权限")
    fee_ids = list(dict.fromkeys(body.fee_ids))
    fees = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(fee_ids),
        BusinessRecord.module == "finance",
        *(await _record_scope_conditions(identity, db)),
    ))).all()
    if len(fees) != len(fee_ids):
        raise HTTPException(status_code=404, detail="部分案件费用不存在或无权访问")
    invalid = [item.serial_no for item in fees if item.status != "已付款" or (item.data or {}).get("fee_type") != "内部费用" or (item.data or {}).get("commission_paid")]
    if invalid:
        raise HTTPException(status_code=409, detail="仅可标识尚未发放提成的已付款内部费用：" + "、".join(invalid))
    marked_at = datetime.now().isoformat(timespec="seconds")
    for item in fees:
        item.data = {
            **(item.data or {}),
            "commission_paid": True,
            "commission_paid_by": identity["username"],
            "commission_paid_at": marked_at,
            "commission_paid_comment": body.comment.strip(),
        }
        db.add(WorkflowEvent(record_id=item.id, action="标识提成已发", from_status=item.status, to_status=item.status, operator=identity["username"], comment=body.comment.strip()))
    await db.commit()
    return {"marked": len(fees), "fee_ids": fee_ids, "marked_at": marked_at}


@router.get(f"{settings.api_prefix}/finance/fees/refund-review-candidates")
async def list_internal_refund_review_candidates(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """List internal negative-amount requests for the dedicated refund review page."""
    from app.core.permissions import (
        _record_dict_for_identity, _record_scope_conditions,
    )
    items = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance",
        *(await _record_scope_conditions(identity, db)),
    ).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all()
    refund_items = [
        item for item in items
        if (item.data or {}).get("fee_type") == "内部费用"
        and (
            bool((item.data or {}).get("is_refund"))
            or float((item.data or {}).get("amount") or 0) < 0
        )
    ]
    return {
        "items": [await _record_dict_for_identity(item, identity, db) for item in refund_items],
        "total": len(refund_items),
    }


@router.get(f"{settings.api_prefix}/finance/payment-packages/{{package_no}}/print-word")
async def export_payment_package_word(
    package_no: str,
    scope: str = Query("internal_fee"),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _payment_package_for_word,
    )
    from app.core.storage import (
        _payment_package_docx_bytes,
    )
    package, fees, normalized_scope = await _payment_package_for_word(package_no, scope, identity, db)
    filename, content = _payment_package_docx_bytes(package, fees, scope=normalized_scope)
    disposition = f"attachment; filename=payment-package.docx; filename*=UTF-8''{quote(filename)}"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": disposition},
    )


@router.get(f"{settings.api_prefix}/finance/payment-packages")
async def list_internal_payment_packages(
    page: int = Query(1, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    status_filter: str = Query("", alias="status"),
    page_id: str = Query("", alias="page_id"),
    package_no: str = Query(""),
    payee: str = Query(""),
    payment_date_from: date | None = Query(None),
    payment_date_to: date | None = Query(None),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _record_dict_for_identity, _record_scope_conditions,
    )
    legacy_status_by_page_id = {
        "5001003006": "待核销",
        "50001003006": "待核销",
    }
    effective_page_id = page_id.strip() if isinstance(page_id, str) else ""
    effective_status = status_filter.strip() or legacy_status_by_page_id.get(effective_page_id, "")
    conditions = [
        BusinessRecord.module == "finance_package",
        *(await _record_scope_conditions(identity, db)),
    ]
    if effective_status:
        conditions.append(BusinessRecord.status == effective_status)
    if package_no.strip():
        conditions.append(BusinessRecord.serial_no.ilike(f"%{package_no.strip()}%"))
    if payee.strip():
        conditions.append(BusinessRecord.data["payee"].as_string().ilike(f"%{payee.strip()}%"))
    if payment_date_from:
        conditions.append(BusinessRecord.data["payment_date"].as_string() >= str(payment_date_from))
    if payment_date_to:
        conditions.append(BusinessRecord.data["payment_date"].as_string() <= str(payment_date_to))
    total = await db.scalar(select(func.count()).select_from(BusinessRecord).where(*conditions)) or 0
    query = select(BusinessRecord).where(*conditions).order_by(
        BusinessRecord.created_at.desc(), BusinessRecord.id.desc()
    )
    if page_size is not None:
        query = query.offset((page - 1) * page_size).limit(page_size)
    items = (await db.scalars(query)).all()
    return {
        "items": [await _record_dict_for_identity(item, identity, db) for item in items],
        "total": int(total),
        "page": page,
        "page_size": page_size if page_size is not None else len(items),
    }


@router.get(f"{settings.api_prefix}/finance/payment-packages/candidates")
async def list_internal_payment_package_candidates(
    package_id: int | None = Query(None),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _record_dict_for_identity, _record_scope_conditions,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有打包付款权限")
    conditions = [BusinessRecord.module == "finance", *(await _record_scope_conditions(identity, db))]
    rows = (await db.scalars(select(BusinessRecord).where(*conditions).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()))).all()
    items = [
        row for row in rows
        if (row.data or {}).get("fee_type") == "内部费用"
        and (row.status == "已审批" or (package_id is not None and row.status == "待核销" and int((row.data or {}).get("payment_package_id") or 0) == package_id))
    ]
    return {"items": [await _record_dict_for_identity(item, identity, db) for item in items], "total": len(items)}


@router.post(f"{settings.api_prefix}/finance/payment-packages/preview")
async def preview_internal_payment_package(body: FinancePaymentPackagePreviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _new_internal_payment_package_no, _prepare_internal_payment_package,
    )
    _fees, details, payee, total_amount = await _prepare_internal_payment_package(body.fee_ids, identity, db)
    return {
        "package_no": _new_internal_payment_package_no(),
        "print_date": str(date.today()),
        "payee": payee,
        "total_amount": total_amount,
        "items": details,
    }


@router.post(f"{settings.api_prefix}/finance/payment-packages", status_code=status.HTTP_201_CREATED)
async def create_internal_payment_package(body: FinancePaymentPackageCreateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _prepare_internal_payment_package, _round_fee_amount,
    )
    from app.core.permissions import (
        _record_dict_for_identity,
    )
    fees, details, payee, total_amount = await _prepare_internal_payment_package(body.fee_ids, identity, db)
    if await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == body.package_no)):
        raise HTTPException(status_code=409, detail="付款包号码已经存在")
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    paid_at = datetime.now().isoformat(timespec="seconds")
    payment_date = str(date.today())
    package = BusinessRecord(
        module="finance_package",
        serial_no=body.package_no,
        title=f"{payee}提成付款申请单",
        customer="",
        status="待核销",
        owner=identity["username"],
        department=user.department if user else "上海分所",
        description=body.comment.strip(),
        data={
            "fee_ids": [item.id for item in fees],
            "payee": payee,
            "amount": total_amount,
            "total_amount": total_amount,
            "payment_date": payment_date,
            "payment_status": "待核销",
            "fee_type": "内部提成",
            "items": details,
            "submitted_at": paid_at,
            "submitted_by": identity["username"],
            "comment": body.comment.strip(),
        },
    )
    db.add(package)
    await db.flush()
    db.add(WorkflowEvent(record_id=package.id, action="创建付款包", from_status="", to_status="待核销", operator=identity["username"], comment=body.comment.strip() or "同一收款人提成打包付款"))
    for fee in fees:
        previous = fee.status
        fee_amount = _round_fee_amount(float((fee.data or {}).get("actual_commission") if (fee.data or {}).get("actual_commission") is not None else (fee.data or {}).get("amount") or 0))
        fee.status = "待核销"
        fee.data = {
            **(fee.data or {}),
            "payment_status": "待核销",
            "payment_requested_amount": fee_amount,
            "paid_amount": 0,
            "payment_package_id": package.id,
            "payment_package_no": package.serial_no,
            "payment_applied_at": paid_at,
            "payment_applied_by": identity["username"],
        }
        db.add(WorkflowEvent(record_id=fee.id, action="申请打包付款", from_status=previous, to_status="待核销", operator=identity["username"], comment=f"付款包 {package.serial_no}；{body.comment.strip()}"))
    await db.commit()
    await db.refresh(package)
    return await _record_dict_for_identity(package, identity, db)


@router.get(f"{settings.api_prefix}/finance/payment-packages/{{package_id}}")
async def get_internal_payment_package(package_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    package = await _ensure_record_module(package_id, "finance_package", identity, db)
    return await _record_dict_for_identity(package, identity, db)


@router.put(f"{settings.api_prefix}/finance/payment-packages/{{package_id}}")
async def update_internal_payment_package(package_id: int, body: FinancePaymentPackageUpdateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _prepare_internal_payment_package, _round_fee_amount,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有编辑付款包权限")
    package = await _ensure_record_module(package_id, "finance_package", identity, db)
    if package.status != "待核销":
        raise HTTPException(status_code=409, detail="仅待核销付款包可以编辑费用构成")
    previous_data = package.data or {}
    raw_previous_ids = list(previous_data.get("fee_ids", []))
    if not raw_previous_ids or any(not str(item_id).strip().isdigit() for item_id in raw_previous_ids):
        raise HTTPException(status_code=409, detail="付款包原费用关联无效，不能编辑")
    previous_ids = [int(item_id) for item_id in raw_previous_ids]
    fees, details, payee, total_amount = await _prepare_internal_payment_package(
        body.fee_ids, identity, db, editable_package_id=package.id,
    )
    next_ids = [item.id for item in fees]
    current_fees = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(previous_ids), BusinessRecord.module == "finance"
    ))).all() if previous_ids else []
    if len({item.id for item in current_fees}) != len(set(previous_ids)):
        raise HTTPException(status_code=409, detail="付款包原费用关联不完整，不能编辑")
    inconsistent = [
        item.serial_no for item in current_fees
        if item.status != "待核销"
        or int((item.data or {}).get("payment_package_id") or 0) != package.id
        or str((item.data or {}).get("payment_package_no") or "").strip() != package.serial_no
    ]
    if inconsistent:
        raise HTTPException(status_code=409, detail="付款包原费用关联不一致：" + "、".join(inconsistent))
    payment_keys = {
        "payment_status", "payment_date", "payment_package_id", "payment_package_no",
        "payment_requested_amount", "paid_amount", "payment_applied_at", "payment_applied_by",
        "paid_at", "paid_by", "writeoff_status", "writeoff_voucher_no", "payment_method",
        "written_off_at", "written_off_by",
    }
    removed = [item for item in current_fees if item.id not in next_ids]
    for fee in removed:
        data = fee.data or {}
        if int(data.get("payment_package_id") or 0) != package.id:
            raise HTTPException(status_code=409, detail=f"费用 {fee.serial_no} 的付款包关联不一致")
        fee.status = "已审批"
        fee.data = {key: value for key, value in data.items() if key not in payment_keys}
        db.add(WorkflowEvent(record_id=fee.id, action="编辑付款包移除费用", from_status="待核销", to_status="已审批", operator=identity["username"], comment=package.serial_no))
    now = datetime.now().isoformat(timespec="seconds")
    for fee in fees:
        data = fee.data or {}
        if fee.id not in previous_ids and data.get("payment_package_id"):
            raise HTTPException(status_code=409, detail=f"费用 {fee.serial_no} 已关联其他付款包")
        previous_status = fee.status
        amount = _round_fee_amount(float(data.get("actual_commission") if data.get("actual_commission") is not None else data.get("amount") or 0))
        fee.status = "待核销"
        fee.data = {**data, "payment_status": "待核销", "payment_requested_amount": amount, "paid_amount": 0,
                    "payment_package_id": package.id, "payment_package_no": package.serial_no,
                    "payment_applied_at": now, "payment_applied_by": identity["username"]}
        if fee.id not in previous_ids:
            db.add(WorkflowEvent(record_id=fee.id, action="编辑付款包加入费用", from_status=previous_status, to_status="待核销", operator=identity["username"], comment=package.serial_no))
    comment = body.comment.strip()
    package.title = f"{payee}提成付款申请单"
    package.description = comment
    package.data = {**previous_data, "fee_ids": next_ids, "payee": payee, "amount": total_amount,
                    "total_amount": total_amount, "items": details, "comment": comment,
                    "updated_at": now, "updated_by": identity["username"]}
    db.add(WorkflowEvent(record_id=package.id, action="编辑付款包", from_status="待核销", to_status="待核销", operator=identity["username"], comment=comment or "更新费用构成"))
    await db.commit()
    await db.refresh(package)
    return await _record_dict_for_identity(package, identity, db)


@router.post(f"{settings.api_prefix}/finance/payment-packages/{{package_id}}/writeoff")
async def writeoff_internal_payment_package(package_id: int, body: FinancePaymentPackageWriteoffInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _round_fee_amount,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有付款核销权限")
    package = await _ensure_record_module(package_id, "finance_package", identity, db)
    if package.status != "待核销":
        raise HTTPException(status_code=409, detail="仅待核销付款包可以核销")
    if body.payment_method not in {"自动扣款", "银行卡", "现金"}:
        raise HTTPException(status_code=422, detail="付款方式无效")
    if not body.invoice_no.strip():
        raise HTTPException(status_code=422, detail="请输入付款单据号.")
    package_data = package.data or {}
    expected_amount = _round_fee_amount(float(package_data.get("total_amount") or package_data.get("amount") or 0))
    confirmed_amount = _round_fee_amount(body.amount)
    if abs(confirmed_amount - expected_amount) > 0.001:
        raise HTTPException(status_code=409, detail=f"确认付款金额必须等于付款包金额 {expected_amount:.2f}")
    written_off_at = datetime.now().isoformat(timespec="seconds")
    package.status = "已付款"
    package.data = {
        **package_data,
        "payment_status": "已付款",
        "paid_date": str(body.paid_date),
        "payment_method": body.payment_method,
        "invoice_no": body.invoice_no.strip(),
        "remark": body.remark.strip(),
        "writeoff_status": "已核销",
        "written_off_at": written_off_at,
        "written_off_by": identity["username"],
    }
    fee_ids = [int(item_id) for item_id in package_data.get("fee_ids", [])]
    fees = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(fee_ids), BusinessRecord.module == "finance"
    ))).all() if fee_ids else []
    if len(fees) != len(set(fee_ids)):
        raise HTTPException(status_code=409, detail="付款包关联的费用记录不完整")
    for fee in fees:
        data = fee.data or {}
        if int(data.get("payment_package_id") or 0) != package.id:
            raise HTTPException(status_code=409, detail=f"费用 {fee.serial_no} 的付款包关联不一致")
        previous = fee.status
        fee_amount = _round_fee_amount(float(data.get("actual_commission") if data.get("actual_commission") is not None else data.get("amount") or 0))
        fee.status = "已付款"
        fee.data = {
            **data,
            "payment_status": "已付款",
            "payment_date": str(body.paid_date),
            "paid_amount": fee_amount,
            "paid_at": written_off_at,
            "paid_by": identity["username"],
            "writeoff_status": "已核销",
            "writeoff_voucher_no": body.invoice_no.strip(),
            "payment_method": body.payment_method,
            "written_off_at": written_off_at,
            "written_off_by": identity["username"],
        }
        db.add(WorkflowEvent(record_id=fee.id, action="付款包核销", from_status=previous, to_status="已付款", operator=identity["username"], comment=f"付款包 {package.serial_no}；单据号 {body.invoice_no.strip()}；{body.remark.strip()}"))
    db.add(WorkflowEvent(record_id=package.id, action="付款核销", from_status="待核销", to_status="已付款", operator=identity["username"], comment=f"{body.payment_method}；单据号 {body.invoice_no.strip()}；{body.remark.strip()}"))
    await db.commit()
    await db.refresh(package)
    return await _record_dict_for_identity(package, identity, db)


@router.delete(f"{settings.api_prefix}/finance/payment-packages/{{package_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_internal_payment_package(package_id: int, reverse_paid: bool = Query(False), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    if identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可以撤销付款包")
    package = await _ensure_record_module(package_id, "finance_package", identity, db)
    if package.status == "已付款" and not reverse_paid:
        raise HTTPException(status_code=409, detail="已核销付款包必须显式冲正后才能撤销")
    if package.status not in {"待核销", "已付款"}:
        raise HTTPException(status_code=409, detail="当前付款包状态不能撤销")
    package_data = package.data or {}
    raw_fee_ids = list(package_data.get("fee_ids", []))
    if not raw_fee_ids or any(not str(item_id).strip().isdigit() for item_id in raw_fee_ids):
        raise HTTPException(status_code=409, detail="付款包费用关联无效，不能撤销")
    fee_ids = [int(item_id) for item_id in raw_fee_ids]
    fees = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(fee_ids), BusinessRecord.module == "finance"
    ))).all() if fee_ids else []
    if len({item.id for item in fees}) != len(set(fee_ids)):
        raise HTTPException(status_code=409, detail="付款包关联费用不完整，不能撤销")
    payment_keys = {
        "payment_status", "payment_date", "payment_package_id",
        "payment_package_no", "payment_requested_amount", "paid_amount",
        "payment_applied_at", "payment_applied_by", "paid_at", "paid_by", "writeoff_status",
        "writeoff_voucher_no", "payment_method", "written_off_at",
        "written_off_by",
    }
    for fee in fees:
        data = fee.data or {}
        if (
            int(data.get("payment_package_id") or 0) != package.id
            or str(data.get("payment_package_no") or "").strip() != package.serial_no
        ):
            raise HTTPException(status_code=409, detail=f"费用 {fee.serial_no} 的付款包关联不一致")
        previous = fee.status
        fee.status = "已审批"
        fee.data = {key: value for key, value in data.items() if key not in payment_keys}
        action = "冲正已核销付款包" if package.status == "已付款" else "撤销打包付款"
        db.add(WorkflowEvent(record_id=fee.id, action=action, from_status=previous, to_status="已审批", operator=identity["username"], comment=f"撤销付款包 {package.serial_no}"))
    await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == package.id))
    await db.delete(package)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/finance/fees/{{fee_id}}/readiness")
async def finance_fee_readiness(fee_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _finance_fee_readiness,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    item = await _ensure_record_module(fee_id, "finance", identity, db)
    return await _finance_fee_readiness(item, identity, db)


@router.post(f"{settings.api_prefix}/finance/fees/{{fee_id}}/cancel")
async def cancel_finance_payment(
    fee_id: int,
    body: FinancePaymentCancelInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _require_record_owner_or_manager,
    )
    item = await _ensure_record_module(fee_id, "finance", identity, db)
    await _require_record_owner_or_manager(item, identity, db)
    if item.status not in FINANCE_PAYMENT_CANCELABLE_STATUSES:
        raise HTTPException(status_code=409, detail="当前付款申请状态不能撤回")
    reason = body.reason.strip()
    if not reason:
        raise HTTPException(status_code=422, detail="请输入撤回原因")
    previous = item.status
    changed_at = datetime.now().isoformat(timespec="seconds")
    item.status = "已撤回"
    item.data = {
        **(item.data or {}),
        "cancel_reason": reason,
        "canceled_by": identity["username"],
        "canceled_at": changed_at,
    }
    db.add(WorkflowEvent(
        record_id=item.id,
        action="付款申请撤回",
        from_status=previous,
        to_status=item.status,
        operator=identity["username"],
        comment=reason,
    ))
    await db.commit()
    await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)


@router.post(f"{settings.api_prefix}/finance/fees/{{fee_id}}/rollback")
async def rollback_finance_payment(
    fee_id: int,
    body: FinancePaymentRollbackInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有付款回滚权限")
    item = await _ensure_record_module(fee_id, "finance", identity, db)
    if item.status not in FINANCE_PAYMENT_ROLLBACKABLE_STATUSES:
        raise HTTPException(status_code=409, detail="当前付款申请状态不能回滚")
    previous = item.status
    changed_at = datetime.now().isoformat(timespec="seconds")
    comment = body.comment.strip()
    item.status = "草稿"
    item.data = {
        **(item.data or {}),
        "rollback_comment": comment,
        "rolled_back_by": identity["username"],
        "rolled_back_at": changed_at,
    }
    db.add(WorkflowEvent(
        record_id=item.id,
        action="付款申请回滚",
        from_status=previous,
        to_status=item.status,
        operator=identity["username"],
        comment=comment,
    ))
    await db.commit()
    await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)


@router.get(f"{settings.api_prefix}/finance/fees/{{fee_id}}/payment-types")
async def list_finance_fee_payment_types(
    fee_id: int,
    keyword: str = "",
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _active_payment_type_rows, _finance_payment_type_for_fee,
    )
    await _finance_payment_type_for_fee(fee_id, identity, db)
    return {"items": await _active_payment_type_rows(db, keyword)}


@router.post(f"{settings.api_prefix}/finance/fees/{{fee_id}}/payment-types", status_code=status.HTTP_201_CREATED)
async def create_finance_fee_payment_type(
    fee_id: int,
    body: FinancePaymentTypeCreateInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _create_payment_type, _finance_payment_type_dict, _finance_payment_type_for_fee,
    )
    fee = await _finance_payment_type_for_fee(fee_id, identity, db)
    item = await _create_payment_type(body, identity, db, {"fee_id": fee.id, "fee_no": fee.serial_no})
    return _finance_payment_type_dict(item)


@router.post(f"{settings.api_prefix}/finance/fees/{{fee_id}}/submit")
async def submit_finance_fee(fee_id: int, body: FinanceActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _active_payment_type, _finance_fee_readiness, _finance_payment_type_dict, _round_fee_amount,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _require_record_owner_or_manager,
    )
    item = await _ensure_record_module(fee_id, "finance", identity, db)
    await _require_record_owner_or_manager(item, identity, db)
    is_payment_request = body.amount is not None
    allowed_statuses = {"草稿", "已退回", "已审批", "部分付款"} if is_payment_request else {"草稿", "已退回"}
    if item.status not in allowed_statuses:
        raise HTTPException(status_code=409, detail="当前状态不能申请付款" if is_payment_request else "当前状态不能提交审批")
    data = item.data or {}
    if not is_payment_request:
        missing = []
        if not data.get("handler"): missing.append("经办人员")
        if not data.get("case_no"): missing.append("关联案号")
        if data.get("fee_type") == "官方费用":
            if not data.get("court"): missing.append("缴费法院/机构")
            if not data.get("document_no"): missing.append("缴费通知文号")
        if missing: raise HTTPException(status_code=422, detail="缺少费用审批要素：" + "、".join(missing))
        if data.get("fee_type") == "官方费用":
            readiness = await _finance_fee_readiness(item, identity, db)
            if not readiness["ready"]: raise HTTPException(status_code=422, detail="案件付款三要素不完整：" + "；".join(readiness["missing"]))
    if body.amount is not None:
        payment_type = None
        if data.get("expense_scope") != "内部" and data.get("fee_type") != "内部费用":
            if not body.payment_type_id:
                raise HTTPException(status_code=422, detail="请选择系统付款单位")
            payment_type = await _active_payment_type(body.payment_type_id, db)
            payment_type_data = _finance_payment_type_dict(payment_type)
            payee = payment_type_data["payee"]
            account = payment_type_data["account"]
        else:
            account = body.payment_account.strip()
            if not account:
                raise HTTPException(status_code=422, detail="请输入付款账号")
            payee = body.payment_payee.strip()
            if not payee:
                raise HTTPException(status_code=422, detail="请输入收款单位")
        payment_remark = body.payment_remark.strip()
        requested = _round_fee_amount(body.amount)
        paid = _round_fee_amount(float(await db.scalar(select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(
            FinanceTransaction.finance_record_id == item.id,
            FinanceTransaction.transaction_type == "付款",
        )) or 0))
        previous_requested = _round_fee_amount(float(data.get("payment_requested_amount") or 0))
        remaining = _round_fee_amount(abs(float(data.get("amount") or 0)) - paid - previous_requested)
        if requested > remaining + 0.001:
            raise HTTPException(status_code=409, detail=f"申请付款金额不能超过未付款金额 {remaining:.2f}")
        applied_at = datetime.now().isoformat(timespec="seconds")
        previous = item.status
        item.status = "待审批"
        item.data = {
            **data,
            "payment_requested_amount": _round_fee_amount(previous_requested + requested),
            "payment_account": account,
            "payment_payee": payee,
            "payment_type_id": payment_type.id if payment_type else None,
            "payment_type_code": payment_type.code if payment_type else "",
            "payment_type_name": payment_type.name if payment_type else "",
            "payment_nature": str((payment_type.extra or {}).get("nature") or payment_type.name or "") if payment_type else "",
            "payment_account_bank": str((payment_type.extra or {}).get("account_bank") or (payment_type.extra or {}).get("bank") or "") if payment_type else "",
            "payment_remark": payment_remark,
            "payee": payee,
            "payment_applied_at": applied_at,
            "payment_applied_by": identity["username"],
            "payment_status": "待审批",
        }
        db.add(WorkflowEvent(record_id=item.id, action="提交费用付款申请", from_status=previous, to_status="待审批", operator=identity["username"], comment=payment_remark or body.comment.strip() or f"申请付款 {requested:.2f} 元"))
        await db.commit(); await db.refresh(item)
        return await _record_dict_for_identity(item, identity, db)
    previous = item.status; item.status = "待审批"
    db.add(WorkflowEvent(record_id=item.id, action="提交费用审批", from_status=previous, to_status="待审批", operator=identity["username"], comment=body.comment))
    await db.commit(); await db.refresh(item); return await _record_dict_for_identity(item, identity, db)


@router.post(f"{settings.api_prefix}/finance/fees/{{fee_id}}/mark-no-payment")
async def mark_finance_fee_no_payment(fee_id: int, body: FinanceActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _require_record_owner_or_manager,
    )
    item = await _ensure_record_module(fee_id, "finance", identity, db)
    await _require_record_owner_or_manager(item, identity, db)
    if item.status not in {"草稿", "已退回"}:
        raise HTTPException(status_code=409, detail="仅草稿或已退回费用可以标记不缴费")
    previous = item.status
    changed_at = datetime.now().isoformat(timespec="seconds")
    item.status = "不缴费"
    item.data = {
        **(item.data or {}),
        "payment_status": "不缴费",
        "no_payment_comment": body.comment.strip(),
        "no_payment_by": identity["username"],
        "no_payment_at": changed_at,
    }
    db.add(WorkflowEvent(
        record_id=item.id,
        action="案件费用标记不缴费",
        from_status=previous,
        to_status="不缴费",
        operator=identity["username"],
        comment=body.comment.strip() or "案件费用标记不缴费",
    ))
    await db.commit()
    await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)


@router.post(f"{settings.api_prefix}/finance/fees/{{fee_id}}/mark-refund-not-required")
async def mark_finance_fee_refund_not_required(fee_id: int, body: FinanceActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _editable_refund_case_fees, _receivable_number, _refund_case_fee_status,
    )
    from app.core.permissions import (
        _permission_payload_for_identity, _record_dict_for_identity,
    )
    if identity.get("role") not in {"admin", "manager"}:
        permission = await _permission_payload_for_identity(identity, db)
        if "*" not in permission.get("action_keys", []) and "finance.refund.not_required" not in permission.get("action_keys", []):
            raise HTTPException(status_code=403, detail="当前角色没有标记不再办理退费的权限")
    item = (await _editable_refund_case_fees([fee_id], identity, db))[0]
    data = dict(item.data or {})
    previous_code, previous_label = _refund_case_fee_status(data)
    if previous_code == "R100":
        raise HTTPException(status_code=409, detail="该费用已标记为不再办理退费")
    legacy = data.get("legacy_record") if isinstance(data.get("legacy_record"), dict) else {}
    has_explicit_refund_status = any(
        value is not None and str(value).strip()
        for value in (data.get("refund_status"), data.get("refund_status_label"), legacy.get("RefundStatus"))
    )
    has_refund_amount = any(
        _receivable_number(data.get(field)) > 0
        for field in ("refund_requested_amount", "refund_amount", "refunded_amount")
    )
    if not has_explicit_refund_status and not has_refund_amount:
        raise HTTPException(status_code=409, detail="仅有退费记录的费用可以标记不再办理退费")
    changed_at = datetime.now().isoformat(timespec="seconds")
    comment = body.comment.strip()
    item.data = {
        **data,
        "refund_status": "R100",
        "refund_status_label": REFUND_CASE_FEE_STATUSES["R100"],
        "refund_status_started_at": changed_at,
        "refund_not_required": True,
        "refund_not_required_comment": comment,
        "refund_not_required_by": identity["username"],
        "refund_not_required_at": changed_at,
    }
    db.add(WorkflowEvent(
        record_id=item.id,
        action="标记不再办理退费",
        from_status=previous_label,
        to_status=REFUND_CASE_FEE_STATUSES["R100"],
        operator=identity["username"],
        comment=comment or "案件费用标记不再办理退费",
    ))
    await db.commit()
    await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)


@router.post(f"{settings.api_prefix}/finance/fees/{{fee_id}}/approve")
async def approve_finance_fee(fee_id: int, body: FinanceActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    item = await _ensure_record_module(fee_id, "finance", identity, db)
    if identity.get("role") not in {"admin", "manager", "auditor"}: raise HTTPException(status_code=403, detail="当前角色没有费用审批权限")
    if item.status != "待审批": raise HTTPException(status_code=409, detail="仅待审批费用可以通过")
    item.status = "已审批"
    db.add(WorkflowEvent(record_id=item.id, action="费用审批通过", from_status="待审批", to_status="已审批", operator=identity["username"], comment=body.comment))
    await db.commit(); await db.refresh(item); return await _record_dict_for_identity(item, identity, db)


@router.post(f"{settings.api_prefix}/finance/fees/batch-review")
async def batch_review_finance_fees(body: FinanceFeeBatchReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _review_finance_fee_records,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    fee_ids = list(dict.fromkeys(body.fee_ids))
    items = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(fee_ids),
        BusinessRecord.module == "finance",
        *(await _record_scope_conditions(identity, db)),
    ))).all()
    if len(items) != len(fee_ids):
        raise HTTPException(status_code=404, detail="部分费用不存在或无权访问")
    await _review_finance_fee_records(items, body.approved, body.comment, identity, db)
    await db.commit()
    return {"reviewed": len(items), "fee_ids": fee_ids, "status": "已审批" if body.approved else "已驳回"}


@router.post(f"{settings.api_prefix}/finance/fees/{{fee_id}}/review")
async def review_finance_fee(fee_id: int, body: FinanceFeeReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _review_finance_fee_records,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    item = await _ensure_record_module(fee_id, "finance", identity, db)
    await _review_finance_fee_records([item], body.approved, body.comment, identity, db)
    await db.commit(); await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)


@router.post(f"{settings.api_prefix}/finance/fees/{{fee_id}}/void")
async def void_rejected_finance_fee(fee_id: int, body: FinanceActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有请款单作废权限")
    item = await _ensure_record_module(fee_id, "finance", identity, db)
    data = item.data or {}
    if data.get("fee_type") != "内部费用":
        raise HTTPException(status_code=409, detail="该入口仅可作废内部费用请款单")
    if item.status not in {"已拒绝", "已退回", "已驳回"}:
        raise HTTPException(status_code=409, detail="仅已拒绝的内部费用请款单可以作废")
    previous = item.status
    voided_at = datetime.now().isoformat(timespec="seconds")
    item.status = "已作废"
    item.data = {
        **data,
        "payment_status": "已作废",
        "voided_by": identity["username"],
        "voided_at": voided_at,
        "void_comment": body.comment.strip(),
    }
    db.add(WorkflowEvent(
        record_id=item.id,
        action="请款单作废",
        from_status=previous,
        to_status="已作废",
        operator=identity["username"],
        comment=body.comment.strip() or "已拒绝请款单作废",
    ))
    await db.commit(); await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)


@router.post(f"{settings.api_prefix}/finance/fees/{{fee_id}}/writeoff")
async def writeoff_finance_fee(fee_id: int, body: FinanceWriteoffInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有付款核销权限")
    item = await _ensure_record_module(fee_id, "finance", identity, db)
    if item.status != "已付款":
        raise HTTPException(status_code=409, detail="费用全部付款后才能核销")
    data = item.data or {}
    if data.get("writeoff_status") == "已核销":
        raise HTTPException(status_code=409, detail="付款已经核销")
    payment_total = float(await db.scalar(select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(FinanceTransaction.finance_record_id == item.id, FinanceTransaction.transaction_type == "付款")) or 0)
    if payment_total + 0.001 < abs(float(data.get("amount", 0) or 0)):
        raise HTTPException(status_code=409, detail="付款流水合计未达到申请金额，不能核销")
    item.data = {
        **data,
        "payment_status": "已付款",
        "writeoff_status": "已核销",
        "writeoff_voucher_no": body.voucher_no.strip(),
        "writeoff_comment": body.comment.strip(),
        "written_off_by": identity["username"],
        "written_off_at": datetime.now().isoformat(timespec="seconds"),
    }
    db.add(WorkflowEvent(record_id=item.id, action="付款核销", from_status=item.status, to_status=item.status, operator=identity["username"], comment=f"核销凭证：{body.voucher_no.strip()}。{body.comment}"))
    await db.commit(); await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)


@router.get(f"{settings.api_prefix}/finance/transactions")
async def list_finance_transactions(
    page: int = Query(1, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    finance_record_id: int | None = Query(None, ge=1),
    transaction_type: str = "",
    keyword: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _finance_transaction_dict,
    )
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _visible_record_ids,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    conditions = []
    if finance_record_id is not None:
        conditions.append(FinanceTransaction.finance_record_id == finance_record_id)
    if transaction_type.strip():
        conditions.append(FinanceTransaction.transaction_type == transaction_type.strip())
    if keyword.strip():
        like = f"%{keyword.strip()}%"
        conditions.append(or_(
            FinanceTransaction.voucher_no.ilike(like),
            FinanceTransaction.counterparty.ilike(like),
            FinanceTransaction.remark.ilike(like),
        ))
    if date_from:
        conditions.append(FinanceTransaction.transaction_date >= date_from)
    if date_to:
        conditions.append(FinanceTransaction.transaction_date <= date_to)
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="流水开始日期不能晚于结束日期")
    if identity.get("role") != "admin":
        visible_record_ids = await _visible_record_ids(identity, db)
        conditions.append(or_(
            and_(FinanceTransaction.finance_record_id.is_not(None), FinanceTransaction.finance_record_id.in_(visible_record_ids)),
            and_(FinanceTransaction.finance_record_id.is_(None), FinanceTransaction.operator == identity["username"]),
        ))
    total = await db.scalar(select(func.count()).select_from(FinanceTransaction).where(*conditions)) or 0
    query = select(FinanceTransaction).where(*conditions).order_by(
        FinanceTransaction.transaction_date.desc(), FinanceTransaction.id.desc()
    )
    if page_size is not None:
        query = query.offset((page - 1) * page_size).limit(page_size)
    items = (await db.scalars(query)).all()
    ids = {item.finance_record_id for item in items if item.finance_record_id}
    records = {item.id: item for item in (await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(ids)))).all()} if ids else {}
    transaction_ids = {item.id for item in items}
    voucher_rows = (await db.scalars(select(FileAttachment).where(FileAttachment.finance_transaction_id.in_(transaction_ids)).order_by(FileAttachment.created_at.desc()))).all() if transaction_ids else []
    vouchers: dict[int, list[FileAttachment]] = {}
    for voucher in voucher_rows:
        vouchers.setdefault(int(voucher.finance_transaction_id or 0), []).append(voucher)
    show_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    users_by_username = await _user_display_map({item.operator for item in items}, db)
    return {
        "items": [_finance_transaction_dict(item, records.get(item.finance_record_id), vouchers.get(item.id, []), show_amount=show_amount, users_by_username=users_by_username) for item in items],
        "total": int(total),
        "page": page,
        "page_size": page_size if page_size is not None else len(items),
    }


@router.post(f"{settings.api_prefix}/finance/transactions", status_code=status.HTTP_201_CREATED)
async def create_finance_transaction(body: FinanceTransactionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _finance_transaction_dict,
    )
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    if body.transaction_type not in FINANCE_TRANSACTION_TYPES: raise HTTPException(status_code=422, detail="流水类型无效")
    if body.transaction_type == "回款": raise HTTPException(status_code=409, detail="银行回款必须先进入回款管理，完成客户认领和应收分配")
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有登记财务流水的权限")
    if not body.finance_record_id:
        raise HTTPException(status_code=409, detail="付款、开票和退款流水必须关联费用记录并通过专用财务流程办理")
    record = await _ensure_record_module(body.finance_record_id, "finance", identity, db)
    if body.transaction_type != "付款":
        raise HTTPException(status_code=409, detail="开票和退款流水必须由发票或退费专用流程生成")
    if record.status not in {"已审批", "部分付款"}: raise HTTPException(status_code=409, detail="费用审批通过后才能付款")
    paid = await db.scalar(select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(FinanceTransaction.finance_record_id == record.id, FinanceTransaction.transaction_type == "付款"))
    if float(paid or 0) + body.amount > float((record.data or {}).get("amount", 0)) + 0.001: raise HTTPException(status_code=409, detail="付款金额不能超过费用金额")
    item = FinanceTransaction(**body.model_dump(), operator=identity["username"]); db.add(item); await db.flush()
    if record:
        previous = record.status
        if body.transaction_type == "付款":
            paid_total = float(paid or 0) + body.amount
            record.status = "已付款" if paid_total + 0.001 >= float((record.data or {}).get("amount", 0)) else "部分付款"
        db.add(WorkflowEvent(record_id=record.id, action=f"登记{body.transaction_type}", from_status=previous, to_status=record.status, operator=identity["username"], comment=f"{body.amount:.2f} 元；{body.remark}"))
    await db.commit(); await db.refresh(item)
    return _finance_transaction_dict(item, record, users_by_username=await _user_display_map({item.operator}, db))


@router.delete(f"{settings.api_prefix}/finance/transactions/{{transaction_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_finance_transaction(transaction_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    if identity["role"] != "admin": raise HTTPException(status_code=403, detail="仅管理员可删除")
    item = await db.get(FinanceTransaction, transaction_id)
    if not item: raise HTTPException(status_code=404, detail="财务流水不存在")
    record = await db.get(BusinessRecord, item.finance_record_id) if item.finance_record_id else None
    attachments = (await db.scalars(select(FileAttachment).where(FileAttachment.finance_transaction_id == item.id))).all()
    paths = [Path(x.path) for x in attachments]
    for attachment in attachments:
        await db.delete(attachment)
    await db.delete(item); await db.flush()
    if record and item.transaction_type == "付款":
        paid = float(await db.scalar(select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(FinanceTransaction.finance_record_id == record.id, FinanceTransaction.transaction_type == "付款")) or 0)
        fee_amount = float((record.data or {}).get("amount", 0))
        record.status = "已审批" if paid <= 0 else ("已付款" if paid + 0.001 >= fee_amount else "部分付款")
    await db.commit()
    for path in paths:
        if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
            path.unlink()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/finance/reconciliations")
async def list_reconciliations(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _reconciliation_dict,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    items = (await db.scalars(select(ReconciliationBatch).order_by(ReconciliationBatch.date_to.desc(), ReconciliationBatch.id.desc()))).all()
    if identity.get("role") not in {"admin", "auditor"}: items = [item for item in items if item.operator == identity["username"]]
    show_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    return {"items": [_reconciliation_dict(item, show_amount=show_amount) for item in items], "total": len(items)}


@router.post(f"{settings.api_prefix}/finance/reconciliations", status_code=status.HTTP_201_CREATED)
async def create_reconciliation(body: ReconciliationInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _reconciliation_dict,
    )
    from app.core.permissions import (
        _visible_record_ids,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}: raise HTTPException(status_code=403, detail="当前角色没有对账权限")
    if body.period_type not in {"周对账", "月对账"}: raise HTTPException(status_code=422, detail="对账周期无效")
    if body.date_from > body.date_to: raise HTTPException(status_code=422, detail="开始日期不能晚于结束日期")
    duplicate = await db.scalar(select(ReconciliationBatch.id).where(ReconciliationBatch.period_type == body.period_type, ReconciliationBatch.date_from == body.date_from, ReconciliationBatch.date_to == body.date_to))
    if duplicate: raise HTTPException(status_code=409, detail="该周期已经生成对账单")
    txs = (await db.scalars(select(FinanceTransaction).where(FinanceTransaction.transaction_date >= body.date_from, FinanceTransaction.transaction_date <= body.date_to))).all()
    if identity.get("role") != "admin":
        visible_record_ids = await _visible_record_ids(identity, db)
        txs = [item for item in txs if (item.finance_record_id and item.finance_record_id in visible_record_ids) or (not item.finance_record_id and item.operator == identity["username"])]
    item = ReconciliationBatch(**body.model_dump(), transaction_count=len(txs), total_amount=sum(tx.amount for tx in txs), status="待确认", operator=identity["username"])
    db.add(item); await db.commit(); await db.refresh(item); return _reconciliation_dict(item, show_amount="finance.amount" in await _allowed_field_keys(identity, db))


@router.post(f"{settings.api_prefix}/finance/reconciliations/{{batch_id}}/confirm")
async def confirm_reconciliation(batch_id: int, body: FinanceActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _reconciliation_dict,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}: raise HTTPException(status_code=403, detail="当前角色没有对账权限")
    item = await db.get(ReconciliationBatch, batch_id)
    if not item: raise HTTPException(status_code=404, detail="对账单不存在")
    if item.status == "已确认": raise HTTPException(status_code=409, detail="对账单已经确认")
    item.status = "已确认"; item.operator = identity["username"]; item.remark = body.comment or item.remark
    await db.commit(); await db.refresh(item); return _reconciliation_dict(item, show_amount="finance.amount" in await _allowed_field_keys(identity, db))


@router.delete(f"{settings.api_prefix}/finance/reconciliations/{{batch_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reconciliation(batch_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    if identity["role"] != "admin": raise HTTPException(status_code=403, detail="仅管理员可删除")
    item = await db.get(ReconciliationBatch, batch_id)
    if not item: raise HTTPException(status_code=404, detail="对账单不存在")
    await db.delete(item); await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
        _case_detail_action_capabilities, _record_dict_for_identity, _record_scope_conditions,
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
                    if not request_item.payment_type_id:
                        raise HTTPException(status_code=422, detail=f"第 {index} 行请选择系统收款单位")
                    payment_type = await _active_payment_type(request_item.payment_type_id, db)
            serial = f"FY{datetime.now():%Y%m%d%H%M%S%f}{uuid4().hex[:6]}"
            case_data = case_record.data or {}
            payment_type_data = _finance_payment_type_dict(payment_type) if payment_type else {}
            payee_name = (
                _contract_person_display_name(payee_user.display_name, {payee_user.username.lower(): payee_user.display_name})
                if payee_user else str(payment_type_data.get("payee") or case_data.get("court_name") or case_data.get("court") or "")
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
    return {"created": len(created), "items": [await _record_dict_for_identity(item, identity, db) for item in created]}


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
