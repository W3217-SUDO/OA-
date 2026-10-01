"""按独立业务职责组织的路由，注册顺序与端点行为保持稳定。"""
from app.areas.finance.fee_action_guards import (
    _require_linked_case_fee_action,
)
from app.core.constants import (
    UPLOAD_ROOT,
)
from app.core.dependencies import (
    AsyncSession,
    BusinessRecord,
    Depends,
    File,
    FileAttachment,
    FileResponse,
    Form,
    HTTPException,
    IncomingPayment,
    IntegrityError,
    Path,
    UploadFile,
    WorkflowEvent,
    current_identity,
    date,
    datetime,
    get_db,
    select,
    settings,
    status,
    uuid4,
)
from app.models_shared import (
    FinanceFeeArrivalInput,
    FinanceFeeInformInput,
    FinanceFeeInformLinksInput,
)
from fastapi import APIRouter

router = APIRouter()

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
    await _require_linked_case_fee_action(source_fee, "case.fee.notice", identity, db)
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
    await _require_linked_case_fee_action(source_fee, "case.fee.arrival", identity, db)
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
        source_kind="system",
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
    await _require_linked_case_fee_action(source_fee, "case.fee.update", identity, db)
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
    notice, source_fee = await _fee_inform_record(inform_id, identity, db)
    await _require_linked_case_fee_action(source_fee, "case.fee.receipt.view", identity, db)
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
    await _require_linked_case_fee_action(source_fee, "case.fee.notice", identity, db)
    data = dict(notice.data or {})
    if notice.status != "已票据确认" or not data.get("locked"):
        raise HTTPException(status_code=409, detail="仅已确认票据的费用通知可以解锁")
    previous_attachment_id = int(data.get("receipt_attachment_id") or 0)
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
    await _require_linked_case_fee_action(source_fee, "case.fee.notice", identity, db)
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
    await _require_linked_case_fee_action(source_fee, "case.fee.notice", identity, db)
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
