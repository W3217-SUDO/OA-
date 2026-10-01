"""知识产权案件费用接口。"""
from fastapi import APIRouter
from app.core.constants import EXPENSE_SCOPE_FEE_TYPES, FINANCE_FEE_TYPES, UPLOAD_ROOT
from app.core.dependencies import AsyncSession, BusinessRecord, Depends, File, FileAttachment, Form, HTTPException, IncomingPayment, IprCaseAssistedFee, Path, Query, Response, UploadFile, User, WorkflowEvent, current_identity, date, datetime, func, get_db, select, settings, status, uuid4
from app.models_shared import FinancePaymentTypeCreateInput, IprCaseAssistedFeeConfirmInput, IprCaseAssistedFeeCreateInput, IprCaseAssistedFeeUpdateInput, IprCaseFeeActionInput, IprCaseFeeArrivalInput, IprCaseFeeCreateInput, IprCaseFeeInvoiceInput, IprCaseFeePaymentApplicationInput

router = APIRouter()


@router.get(f"{settings.api_prefix}/ipr/cases/{{case_id}}/assisted-fees")
async def list_ipr_case_assisted_fees(
    case_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """列出可见知识产权案件的资助申请与回执文件。"""
    from app.core.finance import (
        _ipr_assisted_fee_dict,
    )
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _ensure_record_module, _ipr_case_assisted_fee_capabilities,
    )
    case_record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    total = int(await db.scalar(select(func.count()).select_from(IprCaseAssistedFee).where(IprCaseAssistedFee.case_record_id == case_record.id)) or 0)
    rows = list((await db.scalars(
        select(IprCaseAssistedFee)
        .where(IprCaseAssistedFee.case_record_id == case_record.id)
        .order_by(IprCaseAssistedFee.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).all())
    attachment_ids = [row.receipt_attachment_id for row in rows if row.receipt_attachment_id]
    attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.id.in_(attachment_ids)))).all()) if attachment_ids else []
    by_id = {item.id: item for item in attachments}
    users_by_username = await _user_display_map(
        {row.request_user for row in rows} | {row.response_user for row in rows if row.response_user}, db,
    )
    return {
        "items": [_ipr_assisted_fee_dict(row, by_id.get(row.receipt_attachment_id), users_by_username) for row in rows],
        "total": total, "page": page, "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
        "capabilities": await _ipr_case_assisted_fee_capabilities(case_record, identity, db),
    }

@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/assisted-fees", status_code=status.HTTP_201_CREATED)
async def create_ipr_case_assisted_fee(case_id: int, body: IprCaseAssistedFeeCreateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """创建知识产权案件资助申请，保持原有专属数据模型。"""
    from app.core.finance import (
        _ipr_assisted_fee_dict,
    )
    from app.core.permissions import (
        _ensure_ipr_case_assisted_fee_write,
    )
    case_record = await _ensure_ipr_case_assisted_fee_write(case_id, identity, db)
    row = IprCaseAssistedFee(case_record_id=case_record.id, assisted_type=body.assisted_type.strip(), request_user=identity["username"], remark=body.remark.strip())
    db.add(row); await db.flush()
    db.add(WorkflowEvent(record_id=case_record.id, action="新建知识产权案件协助费", from_status=case_record.status, to_status=case_record.status, operator=identity["username"], comment=f"协助费 #{row.id}；协助类别：{row.assisted_type}" + (f"；{row.remark}" if row.remark else "")))
    await db.commit(); await db.refresh(row)
    return _ipr_assisted_fee_dict(row)

@router.patch(f"{settings.api_prefix}/ipr/cases/{{case_id}}/assisted-fees/{{assisted_fee_id}}")
async def update_ipr_case_assisted_fee(
    case_id: int, assisted_fee_id: int, body: IprCaseAssistedFeeUpdateInput,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _ipr_assisted_fee_dict, _ipr_case_assisted_fee_row,
    )
    from app.core.permissions import (
        _ensure_ipr_case_assisted_fee_write,
    )
    case_record = await _ensure_ipr_case_assisted_fee_write(case_id, identity, db)
    row = await _ipr_case_assisted_fee_row(case_record, assisted_fee_id, db)
    if row.status != "待确认":
        raise HTTPException(status_code=409, detail="仅待确认的协助费可以编辑")
    before = f"类别：{row.assisted_type}" + (f"；{row.remark}" if row.remark else "")
    row.assisted_type = body.assisted_type.strip()
    row.remark = body.remark.strip()
    db.add(WorkflowEvent(
        record_id=case_record.id, action="编辑知识产权案件协助费",
        from_status=case_record.status, to_status=case_record.status,
        operator=identity["username"],
        comment=f"协助费 #{row.id}；原{before}；新类别：{row.assisted_type}" + (f"；{row.remark}" if row.remark else ""),
    ))
    await db.commit(); await db.refresh(row)
    return _ipr_assisted_fee_dict(row)

@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/assisted-fees/{{assisted_fee_id}}/confirm")
async def confirm_ipr_case_assisted_fee(
    case_id: int, assisted_fee_id: int, body: IprCaseAssistedFeeConfirmInput,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _ipr_assisted_fee_dict, _ipr_case_assisted_fee_row,
    )
    from app.core.permissions import (
        _ensure_ipr_case_assisted_fee_write,
    )
    case_record = await _ensure_ipr_case_assisted_fee_write(case_id, identity, db)
    row = await _ipr_case_assisted_fee_row(case_record, assisted_fee_id, db)
    if row.status != "待确认":
        raise HTTPException(status_code=409, detail="仅待确认的协助费可以确认")
    row.status = "待办理"
    confirmation_remark = body.remark.strip()
    if confirmation_remark:
        row.remark = (row.remark + "\n确认说明：" + confirmation_remark).strip()
    db.add(WorkflowEvent(
        record_id=case_record.id, action="确认知识产权案件协助费",
        from_status="待确认", to_status="待办理", operator=identity["username"],
        comment=f"协助费 #{row.id}；协助类别：{row.assisted_type}" + (f"；{confirmation_remark}" if confirmation_remark else ""),
    ))
    await db.commit(); await db.refresh(row)
    return _ipr_assisted_fee_dict(row)

@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/assisted-fees/{{assisted_fee_id}}/transact")
async def transact_ipr_case_assisted_fee(
    case_id: int, assisted_fee_id: int, response_date: date = Form(...), receipt_file: UploadFile = File(..., alias="file"), remark: str = Form(""),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """仅在回执日期和文件均可持久化时完成资助申请。"""
    from app.core.finance import (
        _ipr_assisted_fee_dict, _ipr_case_assisted_fee_row,
    )
    from app.core.permissions import (
        _ensure_ipr_case_assisted_fee_write,
    )
    case_record = await _ensure_ipr_case_assisted_fee_write(case_id, identity, db)
    row = await _ipr_case_assisted_fee_row(case_record, assisted_fee_id, db)
    if row.status != "待办理":
        raise HTTPException(status_code=409, detail="协助费须先确认且只能办理一次")
    suffix = Path(receipt_file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".jpg", ".jpeg", ".png"}:
        raise HTTPException(status_code=422, detail="不支持的资助回执文件格式")
    content = await receipt_file.read()
    if not content:
        raise HTTPException(status_code=422, detail="资助回执文件不能为空")
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="资助回执文件不能超过 20MB")
    target = UPLOAD_ROOT / f"{uuid4().hex}{suffix}"
    target.write_bytes(content)
    attachment = FileAttachment(record_id=case_record.id, category="知识产权资助回执", original_name=Path(receipt_file.filename or target.name).name, stored_name=target.name, content_type=receipt_file.content_type or "application/octet-stream", size=len(content), path=str(target), uploader=identity["username"], remark=f"资助费用 #{row.id} 回执")
    try:
        db.add(attachment); await db.flush()
        row.status = "已办理"; row.response_date = response_date; row.response_user = identity["username"]; row.receipt_attachment_id = attachment.id
        if remark.strip(): row.remark = (row.remark + "\n" + remark.strip()).strip()
        db.add(WorkflowEvent(record_id=case_record.id, action="办理知识产权案件协助费", from_status="待办理", to_status="已办理", operator=identity["username"], comment=f"协助类别：{row.assisted_type}；办理日期：{response_date}；回执：{attachment.original_name}"))
        await db.commit()
    except Exception:
        await db.rollback()
        target.unlink(missing_ok=True)
        raise
    await db.refresh(row)
    return _ipr_assisted_fee_dict(row, attachment)

@router.delete(f"{settings.api_prefix}/ipr/cases/{{case_id}}/assisted-fees/{{assisted_fee_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ipr_case_assisted_fee(case_id: int, assisted_fee_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _ipr_case_assisted_fee_row,
    )
    from app.core.permissions import (
        _ensure_ipr_case_assisted_fee_write,
    )
    case_record = await _ensure_ipr_case_assisted_fee_write(case_id, identity, db)
    row = await _ipr_case_assisted_fee_row(case_record, assisted_fee_id, db)
    if row.status not in {"待确认", "待办理"}:
        raise HTTPException(status_code=409, detail="已办理的协助费必须保留回执和审计记录，不能删除")
    db.add(WorkflowEvent(record_id=case_record.id, action="删除知识产权案件协助费", from_status=row.status, to_status="已删除", operator=identity["username"], comment=f"协助费 #{row.id}；协助类别：{row.assisted_type}"))
    await db.delete(row); await db.commit()

@router.get(f"{settings.api_prefix}/ipr/cases/{{case_id}}/fees")
async def list_ipr_case_fees(
    case_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _ipr_case_fee_rows,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    rows = await _ipr_case_fee_rows(record, identity, db)
    total = len(rows)
    start = (page - 1) * page_size
    return {
        "items": rows[start:start + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
        "totals": {
            "amount": round(sum(float((row.get("data") or {}).get("amount") or 0) for row in rows), 2),
            "invoice_amount": round(sum(float((row.get("data") or {}).get("invoice_amount") or 0) for row in rows), 2),
            "cashed_amount": round(sum(float((row.get("data") or {}).get("cashed_amount") or 0) for row in rows), 2),
            "paid_amount": round(sum(float((row.get("data") or {}).get("paid_amount") or 0) for row in rows), 2),
        },
    }

@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/fees", status_code=status.HTTP_201_CREATED)
async def create_ipr_case_fee(case_id: int, body: IprCaseFeeCreateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _ipr_case_fee_row, _round_fee_amount,
    )
    from app.core.permissions import (
        _ensure_ipr_case_fee_write, _ensure_record_module, _validate_finance_fee_scope_subtype,
    )
    record = await _ensure_ipr_case_fee_write(case_id, identity, db)
    if body.fee_type not in FINANCE_FEE_TYPES:
        raise HTTPException(status_code=422, detail="费用类型无效")
    if body.expense_scope and body.fee_type not in EXPENSE_SCOPE_FEE_TYPES[body.expense_scope]:
        raise HTTPException(status_code=422, detail="费用归属与费用类型不一致")
    _validate_finance_fee_scope_subtype(body.expense_scope, body.expense_subtype, body.fee_type)
    amount = _round_fee_amount(body.amount)
    if amount == 0:
        raise HTTPException(status_code=422, detail="费用金额不能为 0")
    if amount < 0 and body.fee_type != "内部费用":
        raise HTTPException(status_code=422, detail="只有内部费用可以使用负数冲销")
    contract_record = None
    if body.contract_record_id:
        contract_record = await _ensure_record_module(body.contract_record_id, "contract", identity, db)
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if not user:
        raise HTTPException(status_code=401, detail="当前用户不存在")
    handler = identity["username"] if identity.get("role") == "user" else (body.handler.strip() or identity["username"])
    serial = f"FY{datetime.now():%Y%m%d%H%M%S%f}"
    fee = BusinessRecord(
        module="finance", serial_no=serial,
        title=body.title.strip() or f"{record.serial_no}费用",
        customer=body.customer.strip() or record.customer,
        status="草稿", owner=handler, department=user.department,
        description=body.description.strip(),
        data={
            "amount": amount, "fee_type": body.fee_type,
            "expense_scope": body.expense_scope or "", "expense_subtype": body.expense_subtype or "",
            "is_refund": body.fee_type == "内部费用" and amount < 0,
            "case_id": record.id, "case_no": record.serial_no,
            "case_kind": (record.data or {}).get("case_kind", ""),
            "fee_date": str(body.fee_date) if body.fee_date else str(date.today()),
            "handler": handler, "court": body.court.strip(), "document_no": body.document_no.strip(),
            "payee": body.payee.strip(), "payment_status": "创建待提交",
            "contract_id": contract_record.id if contract_record else None,
            "contract_no": contract_record.serial_no if contract_record else "",
            "locked": False, "is_locked": False,
        },
    )
    db.add(fee); await db.flush()
    db.add(WorkflowEvent(record_id=fee.id, action="创建费用", to_status="草稿", operator=identity["username"], comment=f"{body.fee_type}：{amount:.2f} 元"))
    db.add(WorkflowEvent(record_id=record.id, action="新建知识产权案件费用", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{fee.serial_no}｜{body.fee_type}｜{amount:.2f} 元"))
    await db.commit()
    return await _ipr_case_fee_row(record, fee.id, identity, db)

@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/fees/{{fee_id}}/invoice", status_code=status.HTTP_201_CREATED)
async def create_ipr_case_fee_invoice(case_id: int, fee_id: int, body: IprCaseFeeInvoiceInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _ipr_case_fee, _round_fee_amount,
    )
    from app.core.permissions import (
        _ensure_ipr_case_fee_write, _ensure_record_module, _record_dict_for_identity,
    )
    record = await _ensure_ipr_case_fee_write(case_id, identity, db)
    fee = await _ipr_case_fee(record, fee_id, identity, db)
    if fee.status == "已作废":
        raise HTTPException(status_code=409, detail="已作废费用不能登记开票")
    contract_record = None
    if body.contract_record_id:
        contract_record = await _ensure_record_module(body.contract_record_id, "contract", identity, db)
    serial = f"FP{datetime.now():%Y%m%d%H%M%S%f}"
    data = body.model_dump()
    data["case_fee_ids"] = [fee.id]
    data["case_id"] = record.id
    data["case_no"] = record.serial_no
    data["amount"] = _round_fee_amount(body.amount)
    data["extra_amount"] = _round_fee_amount(body.extra_amount)
    data["applicant"] = identity.get("display_name") or identity["username"]
    data["contract_id"] = contract_record.id if contract_record else None
    data["contract_no"] = contract_record.serial_no if contract_record else ""
    item = BusinessRecord(module="invoice", serial_no=serial, title=f"{body.customer}发票申请", customer=body.customer.strip(), status="草稿", owner=identity["username"], department=record.department, description=body.remark, data=data)
    db.add(item); await db.flush()
    db.add(WorkflowEvent(record_id=item.id, action="创建发票申请", to_status="草稿", operator=identity["username"], comment=f"{body.invoice_type}：{data['amount']:.2f} 元"))
    db.add(WorkflowEvent(record_id=record.id, action="知识产权案件费用开票申请", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"费用 {fee.serial_no}｜发票申请 {item.serial_no}"))
    await db.commit()
    return await _record_dict_for_identity(item, identity, db)

@router.get(f"{settings.api_prefix}/ipr/cases/{{case_id}}/fees/{{fee_id}}/payment-types")
async def list_ipr_case_fee_payment_types(case_id: int, fee_id: int, keyword: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _active_payment_type_rows, _ipr_case_fee,
    )
    from app.core.permissions import (
        _ensure_ipr_case_fee_write,
    )
    record = await _ensure_ipr_case_fee_write(case_id, identity, db)
    await _ipr_case_fee(record, fee_id, identity, db)
    return {"items": await _active_payment_type_rows(db, keyword)}

@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/fees/{{fee_id}}/payment-types", status_code=status.HTTP_201_CREATED)
async def create_ipr_case_fee_payment_type(case_id: int, fee_id: int, body: FinancePaymentTypeCreateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _create_payment_type, _finance_payment_type_dict, _ipr_case_fee,
    )
    from app.core.permissions import (
        _ensure_ipr_case_fee_write,
    )
    record = await _ensure_ipr_case_fee_write(case_id, identity, db)
    fee = await _ipr_case_fee(record, fee_id, identity, db)
    item = await _create_payment_type(body, identity, db, {"case_id": record.id, "case_no": record.serial_no, "fee_id": fee.id, "fee_no": fee.serial_no})
    return _finance_payment_type_dict(item)

@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/fees/{{fee_id}}/payment-application", status_code=status.HTTP_201_CREATED)
async def create_ipr_case_fee_payment_application(case_id: int, fee_id: int, body: IprCaseFeePaymentApplicationInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _active_payment_type, _finance_payment_type_dict, _ipr_case_fee,
    )
    from app.core.permissions import (
        _ensure_ipr_case_fee_write, _record_dict_for_identity,
    )
    record = await _ensure_ipr_case_fee_write(case_id, identity, db)
    fee = await _ipr_case_fee(record, fee_id, identity, db)
    if fee.status == "已作废":
        raise HTTPException(status_code=409, detail="已作废费用不能提交付款申请")
    fee_data = dict(fee.data or {})
    payment_type = await _active_payment_type(body.payment_type_id, db)
    payment_type_data = _finance_payment_type_dict(payment_type)
    serial = f"QK{datetime.now():%Y%m%d%H%M%S%f}"
    payment = BusinessRecord(
        module="contract_payment", serial_no=serial, title=f"{record.serial_no}费用付款申请",
        customer=record.customer, status="待审批", owner=fee.owner,
        department=record.department, description=body.remark.strip(),
        data={
            "case_id": record.id, "case_no": record.serial_no,
            "fee_id": fee.id, "fee_no": fee.serial_no,
            "fee_type": fee_data.get("fee_type"), "amount": fee_data.get("amount"),
            "payment_type_id": payment_type.id, "payment_type_code": payment_type.code,
            "payment_type": payment_type.name, "payment_nature": payment_type_data["nature"],
            "payee": payment_type_data["payee"], "account_bank": payment_type_data["account_bank"],
            "account": payment_type_data["account"], "application_date": str(body.application_date),
            "applicant": identity["username"],
            "contract_record_id": fee_data.get("contract_id"), "contract_no": fee_data.get("contract_no") or "",
        },
    )
    db.add(payment); await db.flush()
    fee.data = {**fee_data, "payment_status": "待审批", "payment_application_no": payment.serial_no, "payment_application_id": payment.id}
    db.add(WorkflowEvent(record_id=payment.id, action="提交知识产权案件费用付款申请", to_status="待审批", operator=identity["username"], comment=f"{fee.serial_no}｜{payment_type_data['payee']}"))
    db.add(WorkflowEvent(record_id=record.id, action="知识产权案件费用付款申请", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"费用 {fee.serial_no}｜付款申请 {payment.serial_no}"))
    await db.commit()
    return await _record_dict_for_identity(payment, identity, db)

@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/fees/{{fee_id}}/arrival", status_code=status.HTTP_201_CREATED)
async def create_ipr_case_fee_arrival(case_id: int, fee_id: int, body: IprCaseFeeArrivalInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _ipr_case_fee, _ipr_case_fee_row, _round_fee_amount,
    )
    from app.core.permissions import (
        _ensure_ipr_case_fee_write,
    )
    record = await _ensure_ipr_case_fee_write(case_id, identity, db)
    fee = await _ipr_case_fee(record, fee_id, identity, db)
    if fee.status == "已作废":
        raise HTTPException(status_code=409, detail="已作废费用不能登记到账")
    if await db.scalar(select(IncomingPayment.id).where(IncomingPayment.bank_reference == body.bank_reference.strip())):
        raise HTTPException(status_code=409, detail="银行流水号已经登记")
    fee_data = dict(fee.data or {})
    amount = _round_fee_amount(body.amount)
    item = IncomingPayment(
        source_kind="system",
        receipt_no=f"HK{datetime.now():%Y%m%d%H%M%S%f}",
        received_date=body.received_date, amount=amount,
        payer_name=body.payer_name.strip(), bank_reference=body.bank_reference.strip(),
        status="已分配", claimed_customer=record.customer, claimant=identity["username"],
        allocated_amount=amount,
        contract_record_id=int(fee_data.get("contract_id") or 0) or None,
        contract_no=str(fee_data.get("contract_no") or ""),
        allocations=[{
            "fee_id": fee.id, "fee_no": fee.serial_no, "case_id": record.id, "case_no": record.serial_no,
            "amount": amount,
            "settlement_items": [{"fee_record_id": fee.id, "fee_type": fee_data.get("fee_type"), "amount": amount, "settlement_amount": amount, "archive_fee": 0}],
        }],
        operator=identity["username"], remark=body.remark.strip(),
    )
    db.add(item); await db.flush()
    fee.data = {**fee_data, "cashed_date": str(body.received_date), "cashed_amount": amount, "received_payer_name": body.payer_name.strip(), "arrival_receipt_no": item.receipt_no}
    db.add(WorkflowEvent(record_id=record.id, action="知识产权案件费用到账", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"费用 {fee.serial_no}｜{item.receipt_no}｜{amount:.2f} 元"))
    await db.commit()
    return await _ipr_case_fee_row(record, fee.id, identity, db)

@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/fees/{{fee_id}}/unlock")
async def unlock_ipr_case_fee(case_id: int, fee_id: int, body: IprCaseFeeActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _ipr_case_fee, _ipr_case_fee_row,
    )
    from app.core.permissions import (
        _ensure_ipr_case_fee_write,
    )
    record = await _ensure_ipr_case_fee_write(case_id, identity, db)
    fee = await _ipr_case_fee(record, fee_id, identity, db)
    data = dict(fee.data or {})
    data["locked"] = False
    data["is_locked"] = False
    data.pop("locked_at", None)
    data.pop("locked_by", None)
    data["unlocked_at"] = datetime.now().isoformat(timespec="seconds")
    data["unlocked_by"] = identity["username"]
    fee.data = data
    comment = body.comment.strip()
    db.add(WorkflowEvent(record_id=record.id, action="解锁知识产权案件费用", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{fee.serial_no}" + (f"｜{comment}" if comment else "")))
    await db.commit()
    return await _ipr_case_fee_row(record, fee.id, identity, db)

@router.delete(f"{settings.api_prefix}/ipr/cases/{{case_id}}/fees/{{fee_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ipr_case_fee(case_id: int, fee_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _ipr_case_fee,
    )
    from app.core.permissions import (
        _ensure_ipr_case_fee_write,
    )
    record = await _ensure_ipr_case_fee_write(case_id, identity, db)
    fee = await _ipr_case_fee(record, fee_id, identity, db)
    if fee.status != "草稿":
        raise HTTPException(status_code=409, detail="仅草稿费用可以删除")
    db.add(WorkflowEvent(record_id=record.id, action="删除知识产权案件费用", from_status=record.status, to_status=record.status, operator=identity["username"], comment=fee.serial_no))
    db.add(WorkflowEvent(record_id=fee.id, action="删除费用草稿", from_status="草稿", to_status="已删除", operator=identity["username"], comment=fee.serial_no))
    await db.flush()
    await db.delete(fee)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
