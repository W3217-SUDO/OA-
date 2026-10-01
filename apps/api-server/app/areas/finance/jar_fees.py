"""按独立业务职责组织的路由，注册顺序与端点行为保持稳定。"""
from app.core.constants import (
    JAR_FEE_MODULE,
    JAR_FEE_STATUSES,
    JAR_FEE_TRANSITIONS,
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
    JarFeeAuditLog,
    Path,
    Query,
    StreamingResponse,
    UploadFile,
    User,
    WorkflowEvent,
    csv,
    current_identity,
    datetime,
    func,
    get_db,
    io,
    or_,
    select,
    settings,
    status,
    uuid4,
)
from app.models_shared import (
    JarFeeInput,
    JarFeeStatusInput,
)
from fastapi import APIRouter

router = APIRouter()

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
