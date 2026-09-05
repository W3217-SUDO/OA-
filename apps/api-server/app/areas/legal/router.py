"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.case_archive import ArchiveSearchInput, ArchiveBatchReviewInput, ArchiveExportInput, search_archive_cases
from app.core.constants import (
    ADMINISTRATIVE_CLIENT_POSITIONS, AI_SPACE_CATEGORY, AI_SPACE_EDITABLE_SUFFIXES, CASE_CLIENT_POSITIONS_BY_TYPE, CASE_CREATABLE_TYPES,
    CASE_CREATE_PERMISSION_BY_TYPE, CASE_CREATE_STATUS_ALIASES, CASE_CUSTOM_DOCUMENT_FOLDERS_KEY, CASE_DOCUMENT_CATEGORY, CASE_DOCUMENT_TYPES,
    CASE_EVENT_PENDING_STATUS, CIVIL_CASE_TYPES, CRIMINAL_JUDICIAL_PREFIXES, CUSTOMER_SYSTEM_DATA_FIELDS, EXPENSE_SUBTYPE_FEE_TYPE,
    GENERIC_RECORD_DELETABLE_MODULES, GENERIC_RECORD_EDITABLE_MODULES, GENERIC_RECORD_TRANSITION_MODULES, INVESTIGATION_RECORD_MODULES, INVOICE_RELEASED_STATUSES,
    JAR_FEE_MODULE, NORMAL_CASE_BASIC_TYPES, RECORD_IMPORT_COLUMNS, RECORD_IMPORT_SAMPLES, REQUIRED_SEAL_TYPES,
    SEAL_APPLICATION_FILE_CATEGORY, SEAL_STAMPED_FILE_CATEGORY, UPLOAD_ROOT, WORD_DOCUMENT_CONTENT_TYPE, WORD_EDITOR_LOCK_SECONDS,
    WORKFLOW_TRANSITIONS, _BUILTIN_DOCUMENT_TEMPLATES, case_agent_runtime, logger,
)
from app.core.dependencies import (
    Annotated, AsyncSession, BusinessRecord, CaseAssistedFee, CaseEvent,
    CaseTypeCasePhaseRelation, CaseTypeFileTypeRelation, CommunicationLog, ContractApprovalStep, ContractObject,
    ContractPaymentLine, Department, Depends, Document, File,
    FileAttachment, FinanceTransaction, Form, HTTPException, HearingSchedule,
    Inches, IncomingPayment, IntegrityError, LegacyCaseLog, Path,
    Pt, Query, ReceivablePlan, Response, SQLAlchemyError,
    SealAsset, SealAssetAudit, StreamingResponse, String, SystemParameter,
    UploadFile, User, WD_ALIGN_PARAGRAPH, Warehouse, WarehouseStorageLocation,
    WorkflowEvent, and_, asyncio, base64, build_case_workflow_guide,
    csv, current_identity, date, datetime, delete,
    false, func, get_db, io, json,
    or_, qn, qrcode, quote, re,
    read_attachment, secrets, select, settings, status,
    suppress, timedelta, timezone, update, uuid4,
    zipfile,
)
from app.models_shared import (
    ArchiveCheckInput, ArchiveReviewInput, AttachmentBatchInput, CaseAgentDecisionInput, CaseAgentMessageInput,
    CaseAiDraftCreateInput, CaseAiDraftPromoteInput, CaseAiDraftUpdateInput, CaseArbitrationBasicInput, CaseAssignmentInput,
    CaseAssistedFeeConfirmInput, CaseAssistedFeeCreateInput, CaseAssistedFeeUpdateInput, CaseAttachmentMoveInput, CaseAttachmentRenameInput,
    CaseBatchFeeInput, CaseBatchUpdateInput, CaseCommissionBatchInput, CaseCounselBasicInput, CaseCourtInfoInput,
    CaseCreateInput, CaseCreationCompleteInput, CaseCreationReviewInput, CaseDocumentFolderInput, CaseDocumentFolderRenameInput,
    CaseEventBatchDeleteInput, CaseEventInput, CaseEventUpdateInput, CaseExecutionStatusInput, CaseHearingLawyerInput,
    CaseJudicialInput, CaseLitigantsInput, CaseLogInput, CaseMergeInput, CaseNormalBasicInput,
    CaseNotaryInfoInput, CasePhaseChangeInput, CaseProgressInput, CaseReminderInput, CaseSettlementAmountInput,
    CaseTaskFinishedInput, CaseUnarchiveRequestInput, CaseUnarchiveReviewInput, CaseWordEditorLockInput, CaseWordEditorSaveInput,
    CommunicationLogInput, CommunicationLogUpdate, CounselCaseSearchInput, CriminalCourtMaintenanceInput, CriminalProcuratorateMaintenanceInput,
    CriminalPublicSecurityMaintenanceInput, HearingInput, RecordInput, RecordUpdate, SealApplicationInput,
    SealApprovalInput, SealAssetInput, SealAssetUpdate, SealBatchApplicationInput, SealBatchStampInput,
    SealPackageDownloadInput, SealStampInput, TaskActionInput, TransitionInput,
)
from fastapi import APIRouter

router = APIRouter()


@router.get(f"{settings.api_prefix}/communications")
async def list_communications(keyword: str = "", date_from: date | None = None, date_to: date | None = None, mine_only: bool = True, customer_record_id: int | None = Query(default=None, ge=1), page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _visible_record_ids,
    )
    from app.core.system import (
        _communication_dict,
    )
    conditions = []
    if identity.get("role") != "admin" or mine_only: conditions.append(CommunicationLog.operator == identity["username"])
    if identity.get("role") != "admin": conditions.append(CommunicationLog.customer_record_id.in_(await _visible_record_ids(identity, db)))
    if customer_record_id:
        if identity.get("role") != "admin" and customer_record_id not in await _visible_record_ids(identity, db):
            raise HTTPException(status_code=404, detail="客户不存在或无权查看")
        conditions.append(CommunicationLog.customer_record_id == customer_record_id)
    if keyword.strip():
        term = f"%{keyword.strip()}%"; conditions.append(or_(CommunicationLog.customer_name.ilike(term), CommunicationLog.contact.ilike(term), CommunicationLog.phone.ilike(term), CommunicationLog.content.ilike(term)))
    if date_from: conditions.append(CommunicationLog.occurred_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to: conditions.append(CommunicationLog.occurred_at <= datetime.combine(date_to, datetime.max.time()))
    total = int(await db.scalar(select(func.count()).select_from(CommunicationLog).where(*conditions)) or 0)
    items = (await db.scalars(select(CommunicationLog).where(*conditions).order_by(CommunicationLog.occurred_at.desc(), CommunicationLog.id.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    users_by_username = await _user_display_map({item.operator for item in items}, db)
    return {"items": [_communication_dict(item, users_by_username) for item in items], "total": total, "page": page, "page_size": page_size}


@router.get(f"{settings.api_prefix}/communications/{{communication_id}}/attachments")
async def list_communication_attachments(communication_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.storage import (
        _attachment_dict, _communication_attachment_context,
    )
    _item, customer = await _communication_attachment_context(communication_id, identity, db)
    attachments = (await db.scalars(select(FileAttachment).where(
        FileAttachment.communication_log_id == communication_id,
    ).order_by(FileAttachment.created_at.desc(), FileAttachment.id.desc()))).all()
    return {"items": [_attachment_dict(attachment, customer) for attachment in attachments]}


@router.post(f"{settings.api_prefix}/communications/{{communication_id}}/attachments", status_code=status.HTTP_201_CREATED)
async def upload_communication_attachment(communication_id: int, file: UploadFile = File(...), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_event,
    )
    from app.core.storage import (
        _attachment_dict, _communication_attachment_context,
    )
    _item, customer = await _communication_attachment_context(communication_id, identity, db)
    suffix = Path(file.filename or "").suffix.lower()
    # Accept all ordinary file types. Browsers do not upload a directory as a
    # file; a directory must still be compressed as ZIP before selection.
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="单个文件不能超过 20MB")
    stored_name = f"{uuid4().hex}{suffix}"
    target = UPLOAD_ROOT / stored_name
    target.write_bytes(content)
    attachment = FileAttachment(
        record_id=customer.id, communication_log_id=communication_id, category="沟通记录附件",
        original_name=Path(file.filename or stored_name).name, stored_name=stored_name,
        content_type=file.content_type or "application/octet-stream", size=len(content), path=str(target),
        uploader=identity["username"], remark="",
    )
    try:
        db.add(attachment)
        db.add(_customer_event(customer, "上传沟通记录附件", identity, f"沟通记录 #{communication_id}：{attachment.original_name}"))
        await db.commit()
        await db.refresh(attachment)
    except Exception:
        await db.rollback()
        target.unlink(missing_ok=True)
        raise
    return _attachment_dict(attachment, customer)


@router.delete(f"{settings.api_prefix}/communications/{{communication_id}}/attachments/{{attachment_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_communication_attachment(communication_id: int, attachment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_event,
    )
    from app.core.storage import (
        _communication_attachment_context,
    )
    _item, customer = await _communication_attachment_context(communication_id, identity, db)
    attachment = await db.scalar(select(FileAttachment).where(
        FileAttachment.id == attachment_id, FileAttachment.communication_log_id == communication_id,
    ))
    if not attachment:
        raise HTTPException(status_code=404, detail="沟通记录附件不存在")
    path = Path(attachment.path)
    name = attachment.original_name
    await db.delete(attachment)
    db.add(_customer_event(customer, "删除沟通记录附件", identity, f"沟通记录 #{communication_id}：{name}"))
    await db.commit()
    if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
        path.unlink(missing_ok=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(f"{settings.api_prefix}/communications", status_code=status.HTTP_201_CREATED)
async def create_communication(body: CommunicationLogInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_event, _customer_or_404, _sync_customer_contact_metrics,
    )
    from app.core.formatters import (
        _parse_customer_contact_at, _user_display_map,
    )
    from app.core.permissions import (
        _require_record_owner_or_manager,
    )
    from app.core.system import (
        _communication_dict,
    )
    customer = await _customer_or_404(body.customer_record_id, identity, db)
    await _require_record_owner_or_manager(customer, identity, db)
    occurred_at = _parse_customer_contact_at(body.occurred_at)
    if occurred_at is None: raise HTTPException(status_code=422, detail="沟通时间格式无效")
    if occurred_at > datetime.now() + timedelta(minutes=5): raise HTTPException(status_code=422, detail="沟通时间不能晚于当前时间")
    note_id = uuid4().hex; contact, phone, content = body.contact.strip(), body.phone.strip(), body.content.strip()
    note = {"id": note_id, "type": "沟通日志", "content": content, "operator": identity["username"], "contact": contact, "phone": phone, "created_at": body.occurred_at.isoformat(timespec="seconds")}
    customer.data = {**(customer.data or {}), "notes": [note, *list((customer.data or {}).get("notes", []))]}
    _sync_customer_contact_metrics(customer)
    item = CommunicationLog(customer_record_id=customer.id, customer_name=customer.title, contact=contact, phone=phone, content=content, occurred_at=body.occurred_at, operator=identity["username"], note_id=note_id)
    db.add(item); db.add(_customer_event(customer, "新增沟通日志", identity, f"{contact or '客户联系人'}：{content[:120]}"))
    await db.commit(); await db.refresh(item)
    return _communication_dict(item, await _user_display_map({item.operator}, db))


@router.patch(f"{settings.api_prefix}/communications/{{communication_id}}")
async def update_communication(communication_id: int, body: CommunicationLogUpdate, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_event, _customer_or_404, _sync_customer_contact_metrics,
    )
    from app.core.formatters import (
        _parse_customer_contact_at, _user_display_map,
    )
    from app.core.permissions import (
        _require_record_owner_or_manager,
    )
    from app.core.system import (
        _communication_dict,
    )
    item = await db.get(CommunicationLog, communication_id)
    if not item or (identity.get("role") != "admin" and item.operator != identity["username"]): raise HTTPException(status_code=404, detail="沟通记录不存在")
    customer = await _customer_or_404(item.customer_record_id, identity, db)
    await _require_record_owner_or_manager(customer, identity, db)
    if body.occurred_at:
        occurred_at = _parse_customer_contact_at(body.occurred_at)
        if occurred_at is None: raise HTTPException(status_code=422, detail="沟通时间格式无效")
        if occurred_at > datetime.now() + timedelta(minutes=5): raise HTTPException(status_code=422, detail="沟通时间不能晚于当前时间")
    changes = body.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in changes.items(): setattr(item, key, value.strip() if key in {"contact", "phone", "content"} else value)
    data = dict(customer.data or {}); note_updates = {"content": item.content, "contact": item.contact, "phone": item.phone, "created_at": item.occurred_at.isoformat(timespec="seconds")}
    notes = [{**dict(note), **note_updates} if note.get("id") == item.note_id else dict(note) for note in list(data.get("notes", []))]
    customer.data = {**data, "notes": notes}
    _sync_customer_contact_metrics(customer)
    db.add(_customer_event(customer, "修改沟通日志", identity, item.content[:120]))
    await db.commit(); await db.refresh(item)
    return _communication_dict(item, await _user_display_map({item.operator}, db))


@router.delete(f"{settings.api_prefix}/communications/{{communication_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_communication(communication_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_event, _customer_or_404, _sync_customer_contact_metrics,
    )
    from app.core.permissions import (
        _require_record_owner_or_manager,
    )
    item = await db.get(CommunicationLog, communication_id)
    if not item or (identity.get("role") != "admin" and item.operator != identity["username"]): raise HTTPException(status_code=404, detail="沟通记录不存在")
    attachment_paths = (await db.scalars(select(FileAttachment.path).where(FileAttachment.communication_log_id == communication_id))).all()
    customer = await db.get(BusinessRecord, item.customer_record_id)
    if customer:
        customer = await _customer_or_404(customer.id, identity, db)
        await _require_record_owner_or_manager(customer, identity, db)
        data = customer.data or {}; customer.data = {**data, "notes": [note for note in list(data.get("notes", [])) if note.get("id") != item.note_id]}
        _sync_customer_contact_metrics(customer)
        db.add(_customer_event(customer, "删除沟通日志", identity, item.content[:120]))
    await db.delete(item); await db.commit()
    for raw_path in attachment_paths:
        path = Path(raw_path)
        if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
            path.unlink(missing_ok=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/records/export")
async def export_records(
    module: str = Query(min_length=1, max_length=32),
    title: str = "", serial_no: str = "", record_type: str = Query("", alias="type"),
    customer: str = "", case_no: str = "", fee_type: str = "", contract_body: str = "",
    source_person: str = "", signed_at_start: str = "", signed_at_end: str = "",
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _record_scope_conditions, _require_record_module_menu,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    await _require_record_module_menu(module, identity, db, action="导出")
    conditions = [BusinessRecord.module == module, *(await _record_scope_conditions(identity, db))]
    records = list((await db.scalars(select(BusinessRecord).where(*conditions).order_by(BusinessRecord.created_at))).all())
    def contains(value: object, needle: str) -> bool:
        return not needle or needle.lower() in str(value or "").lower()
    def matches(item: BusinessRecord) -> bool:
        data = item.data or {}
        if not contains(item.title, title) or not contains(item.serial_no, serial_no): return False
        if record_type and data.get("type") != record_type: return False
        if not contains(item.customer, customer) or not contains(data.get("case_no"), case_no): return False
        if fee_type and data.get("fee_type") != fee_type: return False
        if contract_body and data.get("contract_body") != contract_body: return False
        if source_person and not contains(data.get("source_person") or item.owner, source_person): return False
        signed = str(data.get("signed_at") or "")[:10]
        if signed_at_start and (not signed or signed < signed_at_start): return False
        if signed_at_end and (not signed or signed > signed_at_end): return False
        return True
    records = [item for item in records if matches(item)]
    allowed_fields = await _allowed_field_keys(identity, db)
    output = io.StringIO(); writer = csv.writer(output); writer.writerow(["业务编号", "标题", "客户/主体", "状态", "负责人", "部门", "说明", "扩展数据", "创建时间", "更新时间"])
    for item in records:
        visible = _record_dict(item, allowed_fields)
        writer.writerow([visible["serial_no"], visible["title"], visible["customer"], visible["status"], visible["owner"], visible["department"], visible["description"], json.dumps(visible.get("data") or {}, ensure_ascii=False), visible["created_at"], visible["updated_at"]])
    content = "\ufeff" + output.getvalue()
    return Response(content=content.encode("utf-8"), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{module}-{date.today()}.csv"'})


@router.get(f"{settings.api_prefix}/records/export-excel")
async def export_records_excel(
    module: str = Query(min_length=1, max_length=32),
    title: str = "", serial_no: str = "", record_type: str = Query("", alias="type"),
    customer: str = "", case_no: str = "", fee_type: str = "", contract_body: str = "",
    source_person: str = "", signed_at_start: str = "", signed_at_end: str = "",
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """Export scoped records as a real SpreadsheetML workbook for legacy Excel parity."""
    from app.core.permissions import (
        _record_scope_conditions, _require_record_module_menu,
    )
    from app.core.system import (
        _allowed_field_keys, _excel_response, _record_dict,
    )
    await _require_record_module_menu(module, identity, db, action="导出")
    conditions = [BusinessRecord.module == module, *(await _record_scope_conditions(identity, db))]
    records = list((await db.scalars(select(BusinessRecord).where(*conditions).order_by(BusinessRecord.created_at))).all())
    def contains(value: object, needle: str) -> bool:
        return not needle or needle.lower() in str(value or "").lower()
    def matches(item: BusinessRecord) -> bool:
        data = item.data or {}
        if not contains(item.title, title) or not contains(item.serial_no, serial_no): return False
        if record_type and data.get("type") != record_type: return False
        if not contains(item.customer, customer) or not contains(data.get("case_no"), case_no): return False
        if fee_type and data.get("fee_type") != fee_type: return False
        if contract_body and data.get("contract_body") != contract_body: return False
        if source_person and not contains(data.get("source_person") or item.owner, source_person): return False
        signed = str(data.get("signed_at") or "")[:10]
        if signed_at_start and (not signed or signed < signed_at_start): return False
        if signed_at_end and (not signed or signed > signed_at_end): return False
        return True
    records = [item for item in records if matches(item)]
    allowed_fields = await _allowed_field_keys(identity, db)
    headers = ["业务编号", "标题", "客户/主体", "状态", "负责人", "部门", "说明", "扩展数据", "创建时间", "更新时间"]
    rows = []
    for item in records:
        visible = _record_dict(item, allowed_fields)
        rows.append([
            visible["serial_no"], visible["title"], visible["customer"], visible["status"],
            visible["owner"], visible["department"], visible["description"],
            json.dumps(visible.get("data") or {}, ensure_ascii=False), visible["created_at"], visible["updated_at"],
        ])
    return _excel_response(f"{module}-{date.today()}.xls", headers, rows)


@router.get(f"{settings.api_prefix}/cases/export/excel")
async def export_selected_ordinary_cases_excel(ids: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _ordinary_case_export_rows, _selected_ordinary_case_export_records,
    )
    from app.core.system import (
        _excel_response,
    )
    records = await _selected_ordinary_case_export_records(ids, identity, db)
    return _excel_response(
        f"普通案件导出-{date.today()}.xls",
        ["案号", "案件名称", "案件类型", "案件阶段", "客户", "合同编号", "案由/罪名", "经办律师", "律师助理", "开庭律师", "法院/机构", "立案日期", "创建日期"],
        _ordinary_case_export_rows(records),
    )


@router.get(f"{settings.api_prefix}/cases/export/archive-manifest")
async def export_selected_case_archive_manifest(ids: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _selected_ordinary_case_export_records,
    )
    from app.core.system import (
        _excel_response,
    )
    records = await _selected_ordinary_case_export_records(ids, identity, db)
    attachment_counts = dict((await db.execute(
        select(FileAttachment.record_id, func.count(FileAttachment.id)).where(FileAttachment.record_id.in_([record.id for record in records])).group_by(FileAttachment.record_id)
    )).all())
    rows = []
    for record in records:
        data = record.data or {}
        rows.append([
            record.serial_no, record.title, record.customer, data.get("case_type", ""), record.status,
            data.get("contract_no", ""), record.owner, attachment_counts.get(record.id, 0),
            data.get("archive_no", ""), data.get("paper_archive_location", ""), data.get("paper_volume_count", ""),
        ])
    return _excel_response(
        f"案件归档清单-{date.today()}.xls",
        ["案号", "案件名称", "客户", "案件类型", "归档状态", "合同编号", "负责人", "附件数量", "归档号", "纸质卷宗位置", "纸质卷宗数量"],
        rows,
    )


@router.get(f"{settings.api_prefix}/cases/export/qr-word")
async def export_selected_case_qr_word(ids: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _selected_ordinary_case_export_records,
    )
    records = await _selected_ordinary_case_export_records(ids, identity, db)
    document = Document()
    document.add_heading("案件二维码清单", level=0)
    document.add_paragraph(f"生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}")
    document.add_paragraph("二维码包含案件记录编号与案号，用于内部扫描核对；扫描后仍须按当前账号权限在系统内查看案件详情。")
    for index, record in enumerate(records, 1):
        if index > 1:
            document.add_page_break()
        data = record.data or {}
        document.add_heading(f"{index}. {record.serial_no}", level=1)
        qr_payload = json.dumps({"case_record_id": record.id, "case_no": record.serial_no}, ensure_ascii=False, separators=(",", ":"))
        image = qrcode.make(qr_payload)
        image_buffer = io.BytesIO()
        image.save(image_buffer, format="PNG")
        image_buffer.seek(0)
        document.add_picture(image_buffer, width=Inches(1.5))
        document.add_paragraph(f"案件名称：{record.title}")
        document.add_paragraph(f"客户：{record.customer or '【待补充】'}")
        document.add_paragraph(f"案件类型：{data.get('case_type') or '【待补充】'}")
        document.add_paragraph(f"案件阶段：{record.status}")
    content = io.BytesIO()
    document.save(content)
    filename = f"案件二维码清单-{date.today()}.docx"
    disposition = f"attachment; filename=case-qr.docx; filename*=UTF-8''{quote(filename)}"
    return Response(content=content.getvalue(), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": disposition})


@router.get(f"{settings.api_prefix}/records/import-template")
async def records_import_template(module: str = Query(min_length=1, max_length=32), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_record_module_menu,
    )
    await _require_record_module_menu(module, identity, db, action="下载导入模板")
    if module == "case": raise HTTPException(status_code=409, detail="案件必须使用分阶段专用入口创建，不能使用通用导入模板")
    columns = RECORD_IMPORT_COLUMNS.get(module)
    if not columns: raise HTTPException(status_code=422, detail="该业务模块不支持批量导入")
    output = io.StringIO(); writer = csv.writer(output); writer.writerow(columns); writer.writerow(RECORD_IMPORT_SAMPLES[module])
    return Response(content=("\ufeff" + output.getvalue()).encode("utf-8"), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{module}-import-template.csv"'})


@router.post(f"{settings.api_prefix}/records/import")
async def import_business_records(module: str = Query(min_length=1, max_length=32), file: UploadFile = File(...), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _csv_date,
    )
    from app.core.permissions import (
        _record_scope_conditions, _require_record_module_menu,
    )
    from app.core.system import (
        _csv_value, _import_relation_data, _unique_import_record, _validate_import_relation_consistency,
    )
    from app.core.tasks import (
        _active_task_username, _validate_task_deadline,
    )
    await _require_record_module_menu(module, identity, db, action="批量导入")
    if module not in RECORD_IMPORT_COLUMNS: raise HTTPException(status_code=422, detail="该业务模块不支持批量导入")
    if module == "case": raise HTTPException(status_code=409, detail="案件必须使用分阶段专用入口创建，不能通过通用导入绕过")
    if module in {"hr", "warehouse"} and identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="当前角色不能批量导入该模块")
    if not (file.filename or "").lower().endswith(".csv"): raise HTTPException(status_code=422, detail="仅支持 UTF-8 CSV 文件")
    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024: raise HTTPException(status_code=413, detail="导入文件不能超过 5MB")
    try: csv_text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc: raise HTTPException(status_code=422, detail="CSV 必须使用 UTF-8 编码") from exc
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames: raise HTTPException(status_code=422, detail="CSV 缺少表头")
    existing = set((await db.scalars(select(BusinessRecord.serial_no))).all()); seen: set[str] = set(); errors: list[dict] = []; created_items: list[dict] = []
    scope = await _record_scope_conditions(identity, db)
    scoped_records = list((await db.scalars(select(BusinessRecord).where(*scope))).all())
    records_by_module = {name: [item for item in scoped_records if item.module == name] for name in ("customer", "contract", "case", "investigation", "task", "clue", "evidence")}
    seal_assets = {item.code: item for item in (await db.scalars(select(SealAsset).where(SealAsset.status == "可用"))).all()}
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    for row_no, row in enumerate(reader, 2):
        try:
            serial = _csv_value(row, "业务编号", "员工编号", "物品编号", "申请编号", "serial_no")
            title = _csv_value(row, "标题", "合同名称", "案件名称", "任务内容", "文件名称", "费用名称", "姓名", "物品名称", "申请标题", "title")
            if not serial or not title: raise ValueError("业务编号和名称不能为空")
            if serial in existing or serial in seen: raise ValueError(f"业务编号已存在：{serial}")
            owner = _csv_value(row, "负责人", "经办人", "owner", default=identity["username"])
            department = _csv_value(row, "部门", "department", default=(user.department if user else "上海分所"))
            if identity.get("role") != "admin":
                department = user.department if user else department
                if identity.get("role") == "user": owner = identity["username"]
            customer = _csv_value(row, "客户/主体", "customer")
            description = _csv_value(row, "说明", "description")
            data: dict = {"imported_at": datetime.now().isoformat(timespec="seconds"), "import_row": row_no}
            status_value = "草稿"
            if module == "contract":
                amount = float(_csv_value(row, "合同金额", "amount")); signed_at = _csv_date(_csv_value(row, "签订日期", "signed_at"), "签订日期")
                if amount < 0 or not customer: raise ValueError("客户不能为空，合同金额不能为负数")
                customer_record = _unique_import_record(records_by_module["customer"], customer, "关联客户")
                customer = customer_record.title
                data.update(_import_relation_data(customer=customer_record))
                data.update({"type": _csv_value(row, "合同类型", "type", default="专项服务"), "amount": f"{amount:.2f}", "signed_at": signed_at, "external_contract_no": _csv_value(row, "外部合同号", "external_contract_no")})
            elif module == "case":
                contract_no = _csv_value(row, "关联合同号", "contract_no"); contract = contracts.get(contract_no)
                if not contract: raise ValueError("关联合同不存在或无权访问")
                if contract.status in {"草稿", "审批中", "已拒绝", "已撤回", "已作废"}: raise ValueError("关联合同尚未审批通过")
                customer = contract.customer; department = contract.department; status_value = "新案待分配"; contract_data = contract.data or {}
                data.update({"contract_id": contract.id, "contract_no": contract.serial_no, "external_contract_no": contract_data.get("external_contract_no", ""), "contract_title": contract.title, "case_type": _csv_value(row, "案件类型", "case_type", default="民事案件"), "opponent": _csv_value(row, "对方当事人", "opponent"), "court": _csv_value(row, "法院", "court")})
            elif module == "task":
                deadline = _csv_date(_csv_value(row, "截止日期", "deadline"), "截止日期")
                priority = _csv_value(row, "优先级", "priority", default="普通")
                if priority not in {"普通", "重要", "紧急"}: raise ValueError("任务优先级无效")
                try:
                    _validate_task_deadline(date.fromisoformat(deadline))
                    owner = await _active_task_username(owner, db, field_name="负责人")
                    collaborators = []
                    for value in [name.strip() for name in re.split(r"[、,，;；]", _csv_value(row, "协作人", "collaborators")) if name.strip()]:
                        collaborator = await _active_task_username(value, db, field_name="协作人")
                        if collaborator != owner and collaborator not in collaborators:
                            collaborators.append(collaborator)
                except HTTPException as exc:
                    raise ValueError(str(exc.detail)) from exc
                case_record = _unique_import_record(records_by_module["case"], _csv_value(row, "关联案号", "case_no"), "关联案件")
                if case_record:
                    customer = case_record.customer
                status_value = "待接收"; data.update(_import_relation_data(case=case_record)); data.update({"deadline": deadline, "priority": priority, "source": _csv_value(row, "来源", "source", default="日常任务"), "initiator": identity["username"], "collaborators": collaborators})
            elif module == "document":
                direction = _csv_value(row, "收发类型", "direction"); case_no = _csv_value(row, "关联案号", "case_no")
                if direction not in {"收文", "发文"}: raise ValueError("收发类型必须为收文或发文")
                case_record = _unique_import_record(records_by_module["case"], case_no, "关联案件")
                if case_record:
                    customer = case_record.customer
                status_value = "待登记"; data.update(_import_relation_data(case=case_record)); data.update({"direction": direction, "document_date": _csv_date(_csv_value(row, "文件日期", "document_date"), "文件日期"), "sender": _csv_value(row, "来文/送达单位", "sender")})
            elif module == "finance":
                amount = float(_csv_value(row, "金额", "amount")); case_no = _csv_value(row, "关联案号", "case_no")
                if amount <= 0: raise ValueError("费用金额必须大于 0")
                case_record = _unique_import_record(records_by_module["case"], case_no, "关联案件")
                if case_record:
                    customer = case_record.customer
                data.update(_import_relation_data(case=case_record)); data.update({"fee_type": _csv_value(row, "费用类型", "fee_type", default="官方费用"), "amount": f"{amount:.2f}", "handler": _csv_value(row, "经办人", "handler", default=owner)})
            elif module == "hr":
                position = _csv_value(row, "岗位", "position"); joined_at = _csv_date(_csv_value(row, "入职日期", "joined_at"), "入职日期")
                if not position: raise ValueError("岗位不能为空")
                requested_status = _csv_value(row, "状态", "status", default="试用"); status_value = "在职" if requested_status == "在职" else "试用"
                data.update({"position": position, "phone": _csv_value(row, "联系电话", "phone"), "joined_at": joined_at, "employment_type": _csv_value(row, "用工类型", "employment_type", default="全职"), "id_no": _csv_value(row, "证件号码", "id_no"), "email": _csv_value(row, "邮箱", "email")})
            elif module == "warehouse":
                quantity = int(_csv_value(row, "数量", "quantity")); category = _csv_value(row, "物品类别", "category"); location = _csv_value(row, "存放位置", "location")
                if quantity < 1 or not category or not location: raise ValueError("物品类别、数量和存放位置不能为空")
                customer = _csv_value(row, "供应商", "vendor"); status_value = "在库"; data.update({"category": category, "quantity": quantity, "unit": _csv_value(row, "单位", "unit", default="件"), "location": location, "vendor": customer, "borrower": "", "due_date": "", "borrow_purpose": ""})
            elif module == "seal":
                asset_code = _csv_value(row, "印章编号", "seal_code"); asset = seal_assets.get(asset_code); copies = int(_csv_value(row, "份数", "copies"))
                if not asset: raise ValueError("印章编号不存在或印章不可用")
                if copies < 1: raise ValueError("用印份数必须大于 0")
                data.update({"seal_asset_id": asset.id, "seal_name": asset.name, "seal_type": asset.seal_type, "copies": copies, "purpose": _csv_value(row, "用途", "purpose"), "use_date": _csv_date(_csv_value(row, "计划日期", "use_date"), "计划日期"), "delivery_method": _csv_value(row, "办理方式", "delivery_method", default="现场用印"), "document_names": _csv_value(row, "文件名称", "document_names")})
            relation_inputs = {
                "customer": _csv_value(row, "客户编号", "customer_no", default=customer if module not in {"warehouse", "hr"} else ""),
                "contract": _csv_value(row, "关联合同号", "contract_no"),
                "case": _csv_value(row, "关联案号", "case_no"),
                "investigation": _csv_value(row, "调查编号", "investigation_no"),
                "task": _csv_value(row, "调查任务编号", "task_no"),
                "clue": _csv_value(row, "线索编号", "clue_no"),
                "evidence": _csv_value(row, "取证编号", "evidence_no"),
            }
            resolved_relations = {
                name: _unique_import_record(records_by_module[name], value, f"关联{name}")
                for name, value in relation_inputs.items()
                if value
            }
            _validate_import_relation_consistency(resolved_relations)
            data.update(_import_relation_data(**resolved_relations))
            if customer_record := resolved_relations.get("customer"):
                customer = customer_record.title
            item = BusinessRecord(module=module, serial_no=serial, title=title, customer=customer, status=status_value, owner=owner, department=department, description=description, data=data)
            db.add(item); await db.flush(); db.add(WorkflowEvent(record_id=item.id, action="批量导入", to_status=item.status, operator=identity["username"], comment=f"CSV 第 {row_no} 行"))
            seen.add(serial); created_items.append({"id": item.id, "serial_no": serial, "title": title})
        except (ValueError, TypeError) as exc:
            errors.append({"row": row_no, "error": str(exc) or "字段格式错误", "value": _csv_value(row, "业务编号", "员工编号", "物品编号", "申请编号", "serial_no")})
    await db.commit()
    return {"module": module, "created": len(created_items), "failed": len(errors), "items": created_items, "errors": errors}


@router.get(f"{settings.api_prefix}/records")
async def list_records(
    module: str = Query(min_length=1, max_length=32),
    keyword: str = "", record_status: str = "", scope: str = Query("all", pattern="^(all|mine|recycle|department|company|audit)$"), statuses: str = "",
    customer_id: int | None = Query(default=None, gt=0), customer: str = "", customer_no: str = "", exclude_archived: bool = False,
    title: str = "", serial_no: str = "", record_type: str = Query("", alias="type"),
    case_no: str = "", fee_type: str = "", contract_body: str = "", source_person: str = "",
    signed_at_start: str = "", signed_at_end: str = "",
    investigation_view: str = Query("", pattern="^(|published|assigned|unassigned)$"),
    archive_view: str = Query("", pattern="^(|pending|refused)$"),
    pending_approver_only: bool = False,
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.cases import (
        _case_action_granted,
    )
    from app.core.contracts import (
        _contract_customer_record_dicts,
    )
    from app.core.crm import (
        _customer_or_404,
    )
    from app.core.investigation import (
        _apply_notary_auto_conversion,
    )
    from app.core.permissions import (
        _case_mine_scope_condition, _record_scope_conditions, _require_record_module_menu,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    await _require_record_module_menu(module, identity, db, action="查看")
    if module in {"notary", "case"}:
        await _apply_notary_auto_conversion(db)
    conditions = [BusinessRecord.module == module]
    relation_customer = None
    if module == "contract" and customer_id:
        relation_customer = await _customer_or_404(customer_id, identity, db)
    elif not (
        module == "contract"
        and scope == "department"
        and identity.get("role") in {"admin", "manager"}
    ):
        # Department contracts are classified by the linked customer's active
        # managers below. Applying the contract row's stamped department first
        # would discard rows whose legacy department is stale.
        conditions.extend(await _record_scope_conditions(identity, db))
    if keyword:
        like = f"%{keyword}%"
        conditions.append(or_(BusinessRecord.serial_no.ilike(like), BusinessRecord.title.ilike(like), BusinessRecord.customer.ilike(like), BusinessRecord.owner.ilike(like)))
    if record_status:
        conditions.append(BusinessRecord.status == record_status)
    if module == "case" and archive_view:
        archive_submitter = func.trim(func.coalesce(BusinessRecord.data["archive_submitter"].as_string(), ""))
        if archive_view == "pending":
            if not await _case_action_granted(identity, db, "case.archive.review"):
                return {"items": [], "total": 0, "page": page, "page_size": page_size, "pages": 0}
            archive_reviewer = func.trim(func.coalesce(BusinessRecord.data["archive_reviewer"].as_string(), ""))
            archive_internal_reviewer = func.trim(func.coalesce(BusinessRecord.data["archive_internal_reviewer"].as_string(), ""))
            conditions.extend([
                BusinessRecord.status.in_({"待归档审核", "亏损内审", "亏损审核"}),
                or_(
                    archive_reviewer == identity["username"],
                    archive_internal_reviewer == identity["username"],
                    and_(
                        archive_reviewer == "",
                        archive_internal_reviewer == "",
                        BusinessRecord.owner == identity["username"],
                    ),
                ),
                archive_submitter != identity["username"],
            ])
        else:
            conditions.extend([
                archive_submitter == identity["username"],
                or_(
                    BusinessRecord.status == "亏损归档拒绝",
                    func.trim(func.coalesce(BusinessRecord.data["archive_reject_reason"].as_string(), "")) != "",
                ),
            ])
    if module == "case" and scope == "mine":
        conditions.append(await _case_mine_scope_condition(identity, db))
    if module == "clue" and statuses:
        requested_statuses = [value.strip() for value in statuses.split(",") if value.strip()]
        if requested_statuses:
            conditions.append(BusinessRecord.status.in_(requested_statuses))
    if module == "clue" and scope == "mine":
        # "My investigation clues" is an actor projection for every role,
        # including administrators.  Elevated data access must not turn a
        # personal queue into the company-wide clue list.
        conditions.append(func.lower(BusinessRecord.owner) == identity["username"].lower())
    if module in {"investigation", "task"} and investigation_view:
        publisher_expr = func.lower(func.coalesce(BusinessRecord.data["publisher"].as_string(), ""))
        legacy_publisher_missing = or_(
            BusinessRecord.data["publisher"].as_string().is_(None),
            BusinessRecord.data["publisher"].as_string() == "",
        )
        if module == "investigation" and investigation_view == "published":
            conditions.append(or_(
                publisher_expr == identity["username"].lower(),
                and_(legacy_publisher_missing, BusinessRecord.owner == identity["username"]),
            ))
        elif module == "task":
            investigation_subtask = or_(
                BusinessRecord.data["investigation_record_id"].as_integer() > 0,
                func.coalesce(BusinessRecord.data["investigation_no"].as_string(), "") != "",
                BusinessRecord.data["investigation_module"].as_string() == "investigation",
            )
            conditions.append(investigation_subtask)
            if investigation_view == "published" and identity.get("role") != "admin":
                publisher_expr = func.lower(func.coalesce(
                    BusinessRecord.data["initiator"].as_string(),
                    BusinessRecord.data["publisher"].as_string(),
                    BusinessRecord.data["assigned_by"].as_string(),
                    "",
                ))
                legacy_publisher_missing = and_(
                    or_(BusinessRecord.data["initiator"].as_string().is_(None), BusinessRecord.data["initiator"].as_string() == ""),
                    or_(BusinessRecord.data["publisher"].as_string().is_(None), BusinessRecord.data["publisher"].as_string() == ""),
                    or_(BusinessRecord.data["assigned_by"].as_string().is_(None), BusinessRecord.data["assigned_by"].as_string() == ""),
                )
                conditions.append(or_(
                    publisher_expr == identity["username"].lower(),
                    and_(legacy_publisher_missing, func.lower(BusinessRecord.owner) == identity["username"].lower()),
                ))
            elif investigation_view == "assigned" and identity.get("role") != "admin":
                # "My investigation tasks" must be private to the assignee.
                # The normal data scope may include a supervisor's department,
                # tasks they initiated, or records shared for collaboration,
                # none of which makes another investigator's child task a
                # personal task.
                conditions.append(func.lower(BusinessRecord.owner) == identity["username"].lower())
        elif investigation_view == "assigned" and identity.get("role") != "admin":
            # "My investigation tasks" must be private to the assignee.  The
            # normal data scope may include a supervisor's department, tasks
            # they initiated, or records shared for collaboration, none of
            # which makes another investigator's child task a personal task.
            conditions.append(func.lower(BusinessRecord.owner) == identity["username"].lower())
    if module == "contract":
        # Contract views pass scope/statuses from the frontend parity round; apply
        # them server-side so mine/dept/company/audit/recycle stay isolated.
        if title.strip():
            conditions.append(BusinessRecord.title.ilike(f"%{title.strip()}%"))
        if serial_no.strip():
            conditions.append(BusinessRecord.serial_no.ilike(f"%{serial_no.strip()}%"))
        if record_type.strip():
            conditions.append(BusinessRecord.data["type"].as_string() == record_type.strip())
        if case_no.strip():
            conditions.append(BusinessRecord.data["case_no"].as_string().ilike(f"%{case_no.strip()}%"))
        if fee_type.strip():
            conditions.append(BusinessRecord.data["fee_type"].as_string() == fee_type.strip())
        if contract_body.strip():
            conditions.append(BusinessRecord.data["contract_body"].as_string() == contract_body.strip())
        if source_person.strip():
            source_like = f"%{source_person.strip()}%"
            conditions.append(or_(
                BusinessRecord.data["source_person"].as_string().ilike(source_like),
                BusinessRecord.data["source_person_display_name"].as_string().ilike(source_like),
                BusinessRecord.owner.ilike(source_like),
            ))
        signed_at = func.substr(BusinessRecord.data["signed_at"].as_string(), 1, 10)
        if signed_at_start.strip():
            conditions.append(signed_at >= signed_at_start.strip())
        if signed_at_end.strip():
            conditions.append(signed_at <= signed_at_end.strip())
        if scope == "audit" and pending_approver_only:
            conditions.append(select(ContractApprovalStep.id).where(
                ContractApprovalStep.contract_record_id == BusinessRecord.id,
                ContractApprovalStep.approver == identity["username"],
                ContractApprovalStep.status == "待审批",
            ).exists())
        if statuses:
            requested_statuses = [value.strip() for value in statuses.split(",") if value.strip()]
            if requested_statuses:
                conditions.append(BusinessRecord.status.in_(requested_statuses))
        if scope == "recycle":
            conditions.append(BusinessRecord.status == "已回收")
        elif scope == "mine" and relation_customer is None:
            conditions.append(BusinessRecord.owner == identity["username"])
        elif scope == "department" and relation_customer is None:
            current_user = await db.scalar(select(User).where(User.username == identity["username"]))
            if current_user:
                department_users = (await db.scalars(select(User).where(
                    User.is_active.is_(True), User.department == current_user.department,
                ))).all()
                department_tokens = {
                    value
                    for user in department_users
                    for value in (str(user.username or "").strip(), str(user.display_name or "").strip())
                    if value
                }
                customers = (await db.scalars(select(BusinessRecord).where(
                    BusinessRecord.module == "customer",
                    BusinessRecord.status.not_in({"已回收", "公海"}),
                ))).all()
                customer_links = []
                for customer_record in customers:
                    managers = (customer_record.data or {}).get("customer_managers")
                    if not isinstance(managers, list) or not managers:
                        managers = [customer_record.owner]
                    if not (set(str(value).strip() for value in managers if str(value).strip()) & department_tokens):
                        continue
                    customer_links.append(BusinessRecord.data["customer_id"].as_integer() == customer_record.id)
                    if str(customer_record.serial_no or "").strip():
                        customer_links.append(BusinessRecord.data["customer_no"].as_string() == customer_record.serial_no)
                    if str(customer_record.title or "").strip():
                        customer_links.append(BusinessRecord.customer == customer_record.title)
                conditions.append(or_(*customer_links) if customer_links else false())
        if relation_customer is not None:
            relation_no = str(relation_customer.serial_no or "").strip()
            relation_name = str(relation_customer.title or "").strip()
            conditions.append(or_(
                BusinessRecord.data["customer_id"].as_integer() == relation_customer.id,
                BusinessRecord.data["customer_no"].as_string() == relation_no,
                func.lower(func.trim(BusinessRecord.customer)) == relation_name.casefold(),
            ))
        elif customer.strip():
            customer_like = f"%{customer.strip()}%"
            matching_customers = list((await db.scalars(select(BusinessRecord).where(
                BusinessRecord.module == "customer",
                BusinessRecord.title.ilike(customer_like),
            ))).all())
            customer_ids = [item.id for item in matching_customers]
            customer_nos = [
                str(item.serial_no or "").strip()
                for item in matching_customers
                if str(item.serial_no or "").strip()
            ]
            customer_conditions = [BusinessRecord.customer.ilike(customer_like)]
            if customer_ids:
                customer_conditions.extend([
                    BusinessRecord.data["customer_id"].as_integer().in_(customer_ids),
                    BusinessRecord.data["customer_record_id"].as_integer().in_(customer_ids),
                ])
            if customer_nos:
                customer_conditions.append(BusinessRecord.data["customer_no"].as_string().in_(customer_nos))
            conditions.append(or_(*customer_conditions))
        if relation_customer is None and customer_no.strip():
            conditions.append(BusinessRecord.data["customer_no"].as_string() == customer_no.strip())
        if exclude_archived:
            conditions.append(BusinessRecord.status.notin_(["已归档", "Archived", "archived"]))
    total = await db.scalar(select(func.count()).select_from(BusinessRecord).where(*conditions))
    result = list((await db.scalars(select(BusinessRecord).where(*conditions).order_by(BusinessRecord.updated_at.desc()).offset((page - 1) * page_size).limit(page_size))).all())
    allowed_fields = await _allowed_field_keys(identity, db)
    return {
        "items": await _contract_customer_record_dicts(result, allowed_fields, db, identity),
        "total": total or 0,
        "page": page,
        "page_size": page_size,
    }


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/commission-preview")
async def preview_case_commissions(
    case_id: int,
    source_fee_id: int = Query(gt=0),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.cases import (
        _case_commission_preview,
    )
    return await _case_commission_preview(case_id, source_fee_id, identity, db)


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/commissions", status_code=status.HTTP_201_CREATED)
async def create_case_commissions(
    case_id: int,
    body: CaseCommissionBatchInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.cases import (
        _case_commission_preview,
    )
    from app.core.finance import (
        _new_internal_payment_package_no, _round_fee_amount,
    )
    from app.core.permissions import (
        _record_dict_for_identity,
    )
    preview = await _case_commission_preview(case_id, body.source_fee_id, identity, db)
    templates = {item["preview_key"]: item for item in preview["items"]}
    normalized: list[tuple[dict, float, str]] = []
    for index, item in enumerate(body.items, start=1):
        template = templates.get(item.preview_key)
        if not template:
            raise HTTPException(status_code=422, detail=f"第{index}行提成项目已失效，请重新打开新增提成窗口")
        normalized.append((template, _round_fee_amount(item.actual_amount), item.remark.strip()))
    actor = await db.scalar(select(User).where(User.username == identity["username"]));
    if not actor:
        raise HTTPException(status_code=401, detail="当前用户不存在")
    case_record = await db.get(BusinessRecord, case_id)
    source_fee = await db.get(BusinessRecord, body.source_fee_id)
    application_no = _new_internal_payment_package_no()
    applied_at = datetime.now().isoformat(timespec="seconds")
    created: list[BusinessRecord] = []
    for template, amount, remark in normalized:
        serial = f"FY{datetime.now():%Y%m%d%H%M%S%f}{len(created):02d}"
        record = BusinessRecord(
            module="finance", serial_no=serial,
            title=f"{case_record.serial_no} {template['commission_type']}",
            customer=case_record.customer, status="待审批",
            owner=template["employee_username"] or identity["username"],
            department=actor.department, description=remark,
            data={
                "amount": amount, "fee_type": "内部费用", "expense_scope": "内部",
                "expense_subtype": template["expense_subtype"],
                "case_no": case_record.serial_no, "case_id": case_record.id,
                "contract_id": (case_record.data or {}).get("contract_id"),
                "contract_no": (case_record.data or {}).get("contract_no", ""),
                "handler": identity["username"], "payee": template["employee_username"],
                "payee_display_name": template["employee_display_name"],
                "base_amount": template["base_amount"],
                "reference_commission": template["reference_commission"],
                "commission_type": template["commission_type"],
                "commission_role": template["commission_role"],
                "source_fee_id": source_fee.id, "source_fee_no": source_fee.serial_no,
                "source_fee_amount": preview["source_fee"]["amount"],
                "payment_application_no": application_no,
                "payment_requested_amount": amount,
                "payment_status": "待审批",
                "payment_applied_at": applied_at,
                "payment_applied_by": identity["username"],
            },
        )
        db.add(record); await db.flush()
        db.add(WorkflowEvent(
            record_id=record.id, action="提交提成付款申请", to_status="待审批",
            operator=identity["username"],
            comment=f"{application_no}｜{template['employee_display_name']}｜{template['commission_type']}｜{amount:.2f} 元｜来源 {source_fee.serial_no}",
        ))
        created.append(record)
    await db.commit()
    for record in created:
        await db.refresh(record)
    return {
        "application_no": application_no,
        "application_date": applied_at[:10],
        "items": [await _record_dict_for_identity(record, identity, db) for record in created],
        "payment_items": [
            {
                "record_id": record.id,
                "application_no": application_no,
                "payee": str((record.data or {}).get("payee_display_name") or record.owner),
                "commission_type": str((record.data or {}).get("commission_type") or record.title),
                "amount": _round_fee_amount(float((record.data or {}).get("amount") or 0)),
                "case_no": case_record.serial_no,
                "application_date": applied_at[:10],
            }
            for record in created
        ],
        "total": len(created),
    }


@router.post(f"{settings.api_prefix}/cases/batch-update")
async def batch_update_cases(body: CaseBatchUpdateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_team_payload, _resolve_active_case_people,
    )
    from app.core.permissions import (
        _record_dict_for_identity, _record_scope_conditions, _require_case_creation_completed,
    )
    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以批量修改案件")
    changes_requested = any(value is not None for value in (body.hearing_lawyer, body.handling_lawyers, body.assistant, body.case_stage, body.source_lawyer, body.litigation_amount))
    if not changes_requested:
        raise HTTPException(status_code=422, detail="请至少提供一个需要修改的案件字段")
    case_ids = list(dict.fromkeys(body.case_ids))
    case_nos = list(dict.fromkeys(value.strip() for value in body.case_nos if value.strip()))
    if not case_ids and not case_nos:
        raise HTTPException(status_code=422, detail="请至少选择一个案件 ID 或案号")
    if len(case_ids) + len(case_nos) > 100:
        raise HTTPException(status_code=422, detail="单次最多批量修改 100 个案件")
    handling_lawyers: list[str] | None = None
    handling_usernames: list[str] | None = None
    assistant_value: str | None = None
    assistant_username: str | None = None
    if body.handling_lawyers is not None:
        handling_lawyers, handling_usernames = await _resolve_active_case_people(body.handling_lawyers, db, field_name="经办律师")
        if not handling_lawyers:
            raise HTTPException(status_code=422, detail="请至少保留一名有效经办律师")
    if body.assistant is not None:
        assistant_values, assistant_usernames = await _resolve_active_case_people([body.assistant] if body.assistant.strip() else [], db, field_name="律师助理")
        assistant_value = assistant_values[0] if assistant_values else ""
        assistant_username = assistant_usernames[0] if assistant_usernames else ""
    requested = []
    if case_ids: requested.append(BusinessRecord.id.in_(case_ids))
    if case_nos: requested.append(BusinessRecord.serial_no.in_(case_nos))
    visible_cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case", or_(*requested), *(await _record_scope_conditions(identity, db)),
    ))).all())
    by_id = {case.id: case for case in visible_cases}; by_no = {case.serial_no: case for case in visible_cases}
    missing_ids = [case_id for case_id in case_ids if case_id not in by_id]
    missing_nos = [case_no for case_no in case_nos if case_no not in by_no]
    if missing_ids or missing_nos:
        parts = []
        if missing_ids: parts.append("ID：" + "、".join(str(value) for value in missing_ids))
        if missing_nos: parts.append("案号：" + "、".join(missing_nos))
        raise HTTPException(status_code=404, detail="案件不存在或无权访问（" + "；".join(parts) + "）")
    cases = []
    for case in [*(by_id[value] for value in case_ids), *(by_no[value] for value in case_nos)]:
        if all(existing.id != case.id for existing in cases): cases.append(case)
    for case in cases:
        _require_case_creation_completed(case)
        if case.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
            raise HTTPException(status_code=409, detail=f"案件 {case.serial_no} 已进入归档流程，不能批量修改")
        data = dict(case.data or {})
        changes = []
        if body.hearing_lawyer is not None:
            changes.append(f"开庭律师：{data.get('hearing_lawyer', '')} → {body.hearing_lawyer.strip()}")
            data["hearing_lawyer"] = body.hearing_lawyer.strip()
        if body.handling_lawyers is not None:
            changes.append(f"经办律师：{','.join(data.get('handling_lawyers') or [])} → {','.join(handling_lawyers or [])}")
            data = _case_team_payload(data, handling_lawyers or [], handling_usernames or [], data.get("assistant", ""), str(data.get("assistant_username") or ""))
        if body.assistant is not None:
            changes.append(f"律师助理：{data.get('assistant', '')} → {assistant_value or ''}")
            data = _case_team_payload(data, list(data.get("handling_lawyers") or []), list(data.get("handling_lawyer_usernames") or []), assistant_value or "", assistant_username or "")
        if body.case_stage is not None:
            changes.append(f"案件阶段：{data.get('case_stage') or case.status} → {body.case_stage.strip()}")
            data["case_stage"] = body.case_stage.strip()
        if body.source_lawyer is not None:
            changes.append(f"案源人：{data.get('source_lawyer', '')} → {body.source_lawyer.strip()}")
            data["source_lawyer"] = body.source_lawyer.strip()
        if body.litigation_amount is not None:
            changes.append(f"诉讼标的：{data.get('litigation_amount', 0)} → {body.litigation_amount}")
            data["litigation_amount"] = body.litigation_amount
        case.data = data
        db.add(WorkflowEvent(record_id=case.id, action="批量修改案件", from_status=case.status, to_status=case.status, operator=identity["username"], comment="；".join(changes + ([body.comment.strip()] if body.comment.strip() else []))))
    await db.commit()
    for case in cases:
        await db.refresh(case)
    return {"updated": len(cases), "items": [await _record_dict_for_identity(case, identity, db) for case in cases]}


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/reminders")
async def list_case_reminders(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _record_dict,
    )
    await _ensure_record_module(case_id, "case", identity, db)
    reminders = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case_reminder",
    ).order_by(BusinessRecord.data["reminder_date"].as_string(), BusinessRecord.id))).all())
    items = [item for item in reminders if int((item.data or {}).get("case_id") or 0) == case_id]
    return {"items": [_record_dict(item) for item in items], "total": len(items)}


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/events")
async def list_case_events(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_event_dict,
    )
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _case_event_access, _require_case_event_write_access,
    )
    case_record, _ = await _case_event_access(case_id, identity, db, write=False)
    items = list((await db.scalars(select(CaseEvent).where(
        CaseEvent.case_record_id == case_record.id,
    ).order_by(CaseEvent.event_time, CaseEvent.deadline, CaseEvent.id))).all())
    try:
        team_role = await _require_case_event_write_access(case_record, identity, db)
        can_manage = True
    except HTTPException:
        team_role, can_manage = "none", False
    users_by_username = await _user_display_map({item.creator for item in items}, db)
    return {
        "items": [_case_event_dict(item, users_by_username, identity, can_manage=can_manage, team_role=team_role) for item in items],
        "total": len(items),
        "capabilities": {"can_create": can_manage, "can_edit": can_manage, "can_delete": can_manage},
    }


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/events", status_code=status.HTTP_201_CREATED)
async def create_case_event(case_id: int, body: CaseEventInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_event_dict,
    )
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _case_event_access,
    )
    from app.core.storage import (
        _case_event_storage_time,
    )
    from app.core.tasks import (
        _sync_case_event_reminder, _validate_case_event_reminder,
    )
    case_record, team_role = await _case_event_access(case_id, identity, db, write=True)
    if not body.event_type.strip() or not body.content.strip():
        raise HTTPException(status_code=422, detail="事件类型和事件内容不能为空")
    remind_at = _validate_case_event_reminder(
        deadline=body.deadline, reminder_enabled=body.reminder_enabled,
        remind_at=_case_event_storage_time(body.remind_at or body.event_time) if body.reminder_enabled else None,
    )
    item = CaseEvent(
        case_record_id=case_record.id, event_type_id=body.event_type_id,
        event_type=body.event_type.strip(), event_time=_case_event_storage_time(body.event_time),
        content=body.content.strip(), deadline=body.deadline,
        reminder_enabled=body.reminder_enabled, remind_at=remind_at,
        status=CASE_EVENT_PENDING_STATUS, creator=identity["username"], updated_by=identity["username"],
    )
    db.add(item)
    await db.flush()
    await _sync_case_event_reminder(item, case_record, identity, db)
    db.add(WorkflowEvent(
        record_id=case_record.id, action="新增案件事件", from_status=case_record.status,
        to_status=case_record.status, operator=identity["username"],
        comment=f"事件#{item.id}｜{item.event_type}｜事件日期：{item.event_time}；截止日期：{item.deadline or '未设置'}；{item.content}",
    ))
    await db.commit()
    await db.refresh(item)
    users = await _user_display_map({item.creator}, db)
    return _case_event_dict(item, users, identity, can_manage=True, team_role=team_role or "none")


@router.patch(f"{settings.api_prefix}/cases/{{case_id}}/events/{{event_id}}")
async def update_case_event(case_id: int, event_id: int, body: CaseEventUpdateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_event_dict, _case_event_mutable_by, _case_event_status,
    )
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _case_event_access,
    )
    from app.core.storage import (
        _case_event_storage_time,
    )
    from app.core.tasks import (
        _sync_case_event_reminder, _validate_case_event_reminder,
    )
    case_record, team_role = await _case_event_access(case_id, identity, db, write=True)
    item = await db.scalar(select(CaseEvent).where(CaseEvent.id == event_id, CaseEvent.case_record_id == case_record.id))
    if not item:
        raise HTTPException(status_code=404, detail="案件事件不存在或不属于当前案件")
    if not _case_event_mutable_by(item, identity, team_role or "none"):
        raise HTTPException(status_code=403, detail="只有事件创建人、部门负责人或系统管理员可以修改案件事件")
    fields = body.model_fields_set
    for required_field, label in (("event_type", "事件类型"), ("event_time", "事件时间"), ("content", "事件内容")):
        if required_field in fields and getattr(body, required_field) is None:
            raise HTTPException(status_code=422, detail=f"{label}不能为空")
    if "event_type" in fields and not (body.event_type or "").strip():
        raise HTTPException(status_code=422, detail="事件类型不能为空")
    if "content" in fields and not (body.content or "").strip():
        raise HTTPException(status_code=422, detail="事件内容不能为空")
    next_event_time = _case_event_storage_time(body.event_time) if "event_time" in fields else item.event_time
    next_deadline = body.deadline if "deadline" in fields else item.deadline
    next_reminder_enabled = body.reminder_enabled if "reminder_enabled" in fields else item.reminder_enabled
    next_remind_at = _case_event_storage_time(body.remind_at) if "remind_at" in fields and body.remind_at else (item.remind_at if "remind_at" not in fields else None)
    if next_reminder_enabled and next_remind_at is None:
        next_remind_at = next_event_time
    next_remind_at = _validate_case_event_reminder(
        deadline=next_deadline, reminder_enabled=next_reminder_enabled, remind_at=next_remind_at,
    )
    before_status = _case_event_status(item)
    if "event_type_id" in fields:
        item.event_type_id = body.event_type_id or 0
    if "event_type" in fields:
        item.event_type = (body.event_type or "").strip()
    if "event_time" in fields:
        item.event_time = next_event_time
    if "content" in fields:
        item.content = (body.content or "").strip()
    if "deadline" in fields:
        item.deadline = next_deadline
    item.reminder_enabled = bool(next_reminder_enabled)
    item.remind_at = next_remind_at
    if "status" in fields:
        item.status = body.status or CASE_EVENT_PENDING_STATUS
    item.updated_by = identity["username"]
    await _sync_case_event_reminder(item, case_record, identity, db)
    changes = []
    if "event_type_id" in fields or "event_type" in fields:
        changes.append("事件类型")
    if "event_time" in fields:
        changes.append("事件时间")
    if "content" in fields:
        changes.append("事件内容")
    if "deadline" in fields:
        changes.append("截止日期")
    if "reminder_enabled" in fields or "remind_at" in fields:
        changes.append("提醒设置")
    if "status" in fields:
        changes.append("状态")
    db.add(WorkflowEvent(
        record_id=case_record.id, action="修改案件事件", from_status=case_record.status,
        to_status=case_record.status, operator=identity["username"],
        comment=f"事件#{item.id}｜修改：{'、'.join(changes) or '无'}｜状态：{before_status} -> {_case_event_status(item)}",
    ))
    await db.commit()
    await db.refresh(item)
    users = await _user_display_map({item.creator}, db)
    return _case_event_dict(item, users, identity, can_manage=True, team_role=team_role or "none")


@router.delete(f"{settings.api_prefix}/cases/{{case_id}}/events/{{event_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case_event(case_id: int, event_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_event_mutable_by,
    )
    from app.core.permissions import (
        _case_event_access,
    )
    from app.core.tasks import (
        _sync_case_event_reminder,
    )
    case_record, team_role = await _case_event_access(case_id, identity, db, write=True)
    item = await db.scalar(select(CaseEvent).where(CaseEvent.id == event_id, CaseEvent.case_record_id == case_record.id))
    if not item:
        raise HTTPException(status_code=404, detail="案件事件不存在或不属于当前案件")
    if not _case_event_mutable_by(item, identity, team_role or "none"):
        raise HTTPException(status_code=403, detail="只有事件创建人、部门负责人或系统管理员可以删除案件事件")
    await _sync_case_event_reminder(CaseEvent(case_record_id=case_record.id, reminder_enabled=False, reminder_record_id=item.reminder_record_id), case_record, identity, db)
    db.add(WorkflowEvent(record_id=case_record.id, action="删除案件事件", from_status=case_record.status, to_status=case_record.status, operator=identity["username"], comment=f"事件#{item.id}｜{item.event_type}｜{item.content}"))
    await db.delete(item)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(f"{settings.api_prefix}/cases/{{case_id}}/events")
async def batch_delete_case_events(case_id: int, body: CaseEventBatchDeleteInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_event_mutable_by,
    )
    from app.core.permissions import (
        _case_event_access,
    )
    from app.core.tasks import (
        _sync_case_event_reminder,
    )
    case_record, team_role = await _case_event_access(case_id, identity, db, write=True)
    event_ids = list(dict.fromkeys(body.event_ids))
    items = list((await db.scalars(select(CaseEvent).where(CaseEvent.id.in_(event_ids)))).all())
    if len(items) != len(event_ids) or any(item.case_record_id != case_record.id for item in items):
        raise HTTPException(status_code=404, detail="存在不存在或不属于当前案件的事件，未执行删除")
    if any(not _case_event_mutable_by(item, identity, team_role or "none") for item in items):
        raise HTTPException(status_code=403, detail="存在无权删除的案件事件，未执行删除")
    for item in items:
        await _sync_case_event_reminder(CaseEvent(case_record_id=case_record.id, reminder_enabled=False, reminder_record_id=item.reminder_record_id), case_record, identity, db)
        await db.delete(item)
    db.add(WorkflowEvent(record_id=case_record.id, action="批量删除案件事件", from_status=case_record.status, to_status=case_record.status, operator=identity["username"], comment=f"事件数量：{len(items)}；ID：{','.join(map(str, event_ids))}"))
    await db.commit()
    return {"deleted": len(items), "deleted_ids": event_ids}


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/reminders", status_code=status.HTTP_201_CREATED)
async def create_case_reminder(case_id: int, body: CaseReminderInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _require_case_note_write_access,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_note_write_access(case_record, identity, db)
    if body.reminder_date > body.deadline:
        raise HTTPException(status_code=422, detail="提醒日期不能晚于截止日期")
    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="请输入提醒内容")
    item = BusinessRecord(
        module="case_reminder", serial_no=f"TX{datetime.now():%Y%m%d%H%M%S%f}",
        title=content[:255], customer=case_record.customer, status="有效",
        owner=identity["username"], department=case_record.department, description=content,
        data={"case_id": case_record.id, "case_no": case_record.serial_no,
              "reminder_date": str(body.reminder_date), "deadline": str(body.deadline)},
    )
    db.add(item)
    await db.flush()
    db.add(WorkflowEvent(
        record_id=case_record.id, action="新增案件提醒", from_status=case_record.status,
        to_status=case_record.status, operator=identity["username"],
        comment=f"提醒日期：{body.reminder_date}；截止日期：{body.deadline}；{content}",
    ))
    await db.commit()
    await db.refresh(item)
    return _record_dict(item)


@router.delete(f"{settings.api_prefix}/cases/{{case_id}}/reminders/{{reminder_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case_reminder(case_id: int, reminder_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_event_mutable_by,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_case_event_write_access, _require_case_note_write_access,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_note_write_access(case_record, identity, db)
    item = await db.get(BusinessRecord, reminder_id)
    if not item or item.module != "case_reminder" or int((item.data or {}).get("case_id") or 0) != case_id:
        raise HTTPException(status_code=404, detail="案件提醒不存在")
    linked_event_id = int((item.data or {}).get("case_event_id") or 0)
    if linked_event_id:
        linked_event = await db.scalar(select(CaseEvent).where(
            CaseEvent.id == linked_event_id,
            CaseEvent.case_record_id == case_record.id,
            CaseEvent.reminder_record_id == item.id,
        ))
        if linked_event:
            team_role = await _require_case_event_write_access(case_record, identity, db)
            if not _case_event_mutable_by(linked_event, identity, team_role):
                raise HTTPException(status_code=403, detail="只有事件创建人、部门负责人或系统管理员可以删除关联提醒")
            linked_event.reminder_enabled = False
            linked_event.reminder_record_id = None
            linked_event.updated_by = identity["username"]
    db.add(WorkflowEvent(
        record_id=case_record.id, action="删除案件提醒", from_status=case_record.status,
        to_status=case_record.status, operator=identity["username"],
        comment=f"提醒日期：{(item.data or {}).get('reminder_date', '')}；{item.description}",
    ))
    await db.delete(item)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/logs")
async def list_case_logs(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _person_reference_display, _user_display_map,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    events = list((await db.scalars(select(WorkflowEvent).where(
        WorkflowEvent.record_id == case_id, WorkflowEvent.action == "新增案件日志",
    ).order_by(WorkflowEvent.created_at.desc(), WorkflowEvent.id.desc()))).all())
    legacy_logs = list((await db.scalars(select(LegacyCaseLog).where(
        LegacyCaseLog.CaseNo == case_record.serial_no,
    ).order_by(LegacyCaseLog.CreateTime.desc(), LegacyCaseLog.LogId.desc()))).all())
    users_by_username = await _user_display_map(
        {item.operator for item in events} | {str(item.CreateUser or "").strip() for item in legacy_logs}, db
    )
    items = [{
        "id": item.id, "content": item.comment, "operator": item.operator,
        "operator_display_name": _person_reference_display(item.operator, users_by_username)[0],
        "created_at": item.created_at, "source": "current",
    } for item in events]
    event_ids = {item.id for item in events}
    items.extend({
        "id": -abs(item.LogId), "content": item.Content or "", "operator": item.CreateUser or "",
        "operator_display_name": _person_reference_display(item.CreateUser, users_by_username)[0],
        "created_at": item.CreateTime, "source": "legacy",
    } for item in legacy_logs if item.LogId >= 0 or abs(item.LogId) not in event_ids)
    items.sort(key=lambda item: (str(item["created_at"] or ""), item["id"]), reverse=True)
    return {"items": items, "total": len(items)}


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/relations")
async def list_case_relations(
    case_id: int,
    clue_page: Annotated[int | None, Query(ge=1)] = None,
    clue_page_size: Annotated[int | None, Query(ge=1, le=200)] = None,
    clue_keyword: str = "",
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Return one case's related records, with opt-in clue search and pagination.

    Existing consumers receive the original complete ``clues`` array when no
    clue query option is supplied.  The case-detail clue tab can opt into a
    page without changing the fee relation payload or the old response shape.
    """
    from app.core.finance import (
        _case_fee_link_maps, _incoming_payment_legacy_summary, _invoice_linked_fee_ids, _resolve_case_fee_link_id, _round_fee_amount,
    )
    from app.core.formatters import (
        _person_reference_display, _user_display_map,
    )
    from app.core.legacy_sync import (
        _legacy_case_fee_projection,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    case_data = case_record.data or {}
    raw_clue_nos = case_data.get("investigation_clue_nos") or case_data.get("clue_nos") or []
    if isinstance(raw_clue_nos, str):
        clue_nos = [value.strip() for value in re.split(r"[,，;；、|]+", raw_clue_nos) if value.strip()]
    else:
        clue_nos = [str(value or "").strip() for value in raw_clue_nos if str(value or "").strip()]
    for value in (case_data.get("clue_no"), case_data.get("investigation_clue"), case_data.get("source_clue_no")):
        normalized = str(value or "").strip()
        if normalized and normalized not in clue_nos:
            clue_nos.append(normalized)
    raw_clue_ids = case_data.get("investigation_clue_ids") if isinstance(case_data.get("investigation_clue_ids"), list) else []
    clue_ids = {
        int(value)
        for value in (
            case_data.get("clue_id"), case_data.get("clue_record_id"),
            case_data.get("investigation_clue_id"), *raw_clue_ids,
        )
        if str(value or "").isdigit() and int(value) > 0
    }
    link_condition = or_(
        BusinessRecord.data["case_id"].as_integer() == case_record.id,
        BusinessRecord.data["converted_case_id"].as_integer() == case_record.id,
        BusinessRecord.data["case_no"].as_string() == case_record.serial_no,
        BusinessRecord.data["converted_case_no"].as_string() == case_record.serial_no,
    )
    fees = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance", link_condition,
    ).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()))).all())
    # A converted case owns an explicit source-clue relation.  Do not union that
    # relation with stale reverse links left on other clues during migration or
    # an earlier conversion; doing so makes one selected clue look like many.
    if clue_ids:
        clue_condition = BusinessRecord.id.in_(clue_ids)
    elif clue_nos:
        clue_condition = BusinessRecord.serial_no.in_(list(dict.fromkeys(clue_nos)))
    else:
        clue_condition = link_condition
    clues = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "clue", clue_condition,
    ).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()))).all())
    clue_query_requested = clue_page is not None or clue_page_size is not None or bool(clue_keyword.strip())
    if clue_keyword.strip():
        keyword = clue_keyword.strip().casefold()
        clue_search_fields = (
            "shop_name", "store_name", "shop_address", "address", "location_address",
            "platform", "product", "certificate_no", "notary_no", "notarization_no",
        )
        clues = [
            item for item in clues
            if keyword in " ".join(
                str(value or "") for value in (
                    item.serial_no, item.title, item.customer, item.description,
                    *((item.data or {}).get(field) for field in clue_search_fields),
                )
            ).casefold()
        ]
    clue_total = len(clues)
    effective_clue_page = clue_page or 1
    effective_clue_page_size = clue_page_size or 15
    clue_pages = (clue_total + effective_clue_page_size - 1) // effective_clue_page_size if clue_total else 0
    if clue_query_requested:
        clue_start = (effective_clue_page - 1) * effective_clue_page_size
        paged_clues = clues[clue_start:clue_start + effective_clue_page_size]
    else:
        paged_clues = clues
    refunds = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "refund"))).all())
    refunds_by_fee: dict[int, list[BusinessRecord]] = {}
    for refund in refunds:
        try:
            fee_id = int((refund.data or {}).get("fee_record_id") or 0)
        except (TypeError, ValueError):
            fee_id = 0
        if fee_id:
            refunds_by_fee.setdefault(fee_id, []).append(refund)
    fee_ids, legacy_fee_ids = _case_fee_link_maps(fees)
    fees_by_id = {item.id: item for item in fees}
    active_invoices_by_fee: dict[int, BusinessRecord] = {}
    if fee_ids:
        invoices = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "invoice",
            BusinessRecord.status.not_in(INVOICE_RELEASED_STATUSES),
        ).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()))).all())
        for invoice in invoices:
            for fee_id in _invoice_linked_fee_ids(invoice.data or {}):
                if fee_id in fee_ids:
                    active_invoices_by_fee.setdefault(fee_id, invoice)
    incoming_by_fee: dict[int, dict] = {}
    if fee_ids:
        # Allocations are durable links to fees.  Customer names are snapshots and
        # may diverge after a customer rename, so they must not gate case-fee
        # receipt projection.
        incoming_payments = list((await db.scalars(select(IncomingPayment).order_by(
            IncomingPayment.received_date.desc(), IncomingPayment.id.desc(),
        ))).all())
        for payment in incoming_payments:
            for allocation in payment.allocations or []:
                allocation_case_no = str(allocation.get("case_no") or "").strip()
                direct_fee_id = _resolve_case_fee_link_id(allocation, fee_ids, legacy_fee_ids)
                settlement_rows = allocation.get("settlement_items") if isinstance(allocation.get("settlement_items"), list) else []
                matched_amounts: dict[int, float] = {}
                direct_fee = fees_by_id.get(direct_fee_id)
                direct_case_no = str(((direct_fee.data or {}) if direct_fee else {}).get("case_no") or "").strip()
                if direct_fee_id in fee_ids and (not allocation_case_no or allocation_case_no == direct_case_no):
                    matched_amounts[direct_fee_id] = float(allocation.get("amount") or 0)
                for settlement in settlement_rows:
                    if not isinstance(settlement, dict):
                        continue
                    settlement_fee_id = _resolve_case_fee_link_id(settlement, fee_ids, legacy_fee_ids)
                    settlement_fee = fees_by_id.get(settlement_fee_id)
                    settlement_case_no = str(((settlement_fee.data or {}) if settlement_fee else {}).get("case_no") or "").strip()
                    if (
                        settlement_fee_id in fee_ids
                        and settlement_fee_id not in matched_amounts
                        and (not allocation_case_no or allocation_case_no == settlement_case_no)
                    ):
                        matched_amounts[settlement_fee_id] = float(
                            settlement.get("amount") or settlement.get("settlement_amount") or 0
                        )
                for fee_id, matched_amount in matched_amounts.items():
                    summary = incoming_by_fee.setdefault(fee_id, {
                        "incoming_payment_id": payment.id,
                        "receipt_no": payment.receipt_no,
                        "received_at": payment.received_date.isoformat(),
                        "received_amount": 0.0,
                        "incoming_payments": [],
                    })
                    summary["received_amount"] = _round_fee_amount(summary["received_amount"] + matched_amount)
                    payment_summary = _incoming_payment_legacy_summary(payment)
                    summary["incoming_payments"].append({
                        "id": payment.id,
                        "receipt_no": payment.receipt_no,
                        "received_date": payment.received_date.isoformat(),
                        "allocated_amount": _round_fee_amount(matched_amount),
                        "amount": _round_fee_amount(float(payment.amount)),
                        "payer_name": payment.payer_name,
                        "bank_reference": payment.bank_reference,
                        "status": payment.status,
                        **payment_summary,
                    })
    users_by_username = await _user_display_map({item.owner for item in [*fees, *clues]}, db)

    def related_dict(item: BusinessRecord) -> dict:
        result = _record_dict(item)
        result["owner_display_name"] = _person_reference_display(item.owner, users_by_username)[0]
        result_data = _legacy_case_fee_projection(result.get("data") or {}) if item.module == "finance" else dict(result.get("data") or {})
        linked_invoice = active_invoices_by_fee.get(item.id)
        if linked_invoice:
            invoice_data = linked_invoice.data or {}
            result_data["invoice_status"] = "已开票" if linked_invoice.status == "已开票" else "已申请"
            result_data["invoice_application_no"] = linked_invoice.serial_no
            result_data["invoice_record_id"] = linked_invoice.id
            result_data["invoice_no"] = invoice_data.get("invoice_no") or result_data.get("invoice_no") or ""
            result_data["invoice_date"] = invoice_data.get("invoice_date") or result_data.get("invoice_date") or ""
        linked_incoming = incoming_by_fee.get(item.id)
        if linked_incoming:
            result_data.update(linked_incoming)
            result_data["cashed_date"] = linked_incoming["received_at"]
        if str((item.data or {}).get("fee_type") or "") == "官方费用":
            linked = refunds_by_fee.get(item.id, [])
            if linked:
                valid_refunds = [refund for refund in linked if refund.status not in {"已驳回", "已作废"}]
                total_refund = round(sum(float((refund.data or {}).get("amount") or 0) for refund in valid_refunds), 2)
                refunded_amount = round(sum(float((refund.data or {}).get("amount") or 0) for refund in valid_refunds if refund.status == "已退款"), 2)
                result_data["refund_amount"] = total_refund
                result_data["refund_requested_amount"] = total_refund
                result_data["refunded_amount"] = refunded_amount
        result["data"] = result_data
        return result

    return {
        "case_id": case_record.id,
        "case_no": case_record.serial_no,
        "fees": [related_dict(item) for item in fees],
        "clues": [related_dict(item) for item in paged_clues],
        "fee_total": len(fees),
        "clue_total": clue_total,
        "clue_page": effective_clue_page,
        "clue_page_size": effective_clue_page_size,
        "clue_pages": clue_pages,
    }


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/logs", status_code=status.HTTP_201_CREATED)
async def create_case_log(case_id: int, body: CaseLogInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _require_case_note_write_access,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_note_write_access(case_record, identity, db, "case.log.create")
    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="请输入日志内容")
    event = WorkflowEvent(
        record_id=case_record.id, action="新增案件日志", from_status=case_record.status,
        to_status=case_record.status, operator=identity["username"], comment=content,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return {"id": event.id, "content": event.comment, "operator": event.operator, "created_at": event.created_at}


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/documents/generate")
async def generate_case_document(
    case_id: int,
    doc_type: str = Query(..., description="文档类型：authorization(授权委托书)/law-firm-letter(律所函)/identity(身份证明)/settlement(结算提成表)"),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.documents import (
        _build_case_template_data, _fill_template,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    template = _BUILTIN_DOCUMENT_TEMPLATES.get(doc_type)
    if not template:
        raise HTTPException(status_code=400, detail="不支持的文档类型")
    case_data = _build_case_template_data(case_record)
    filled_content = _fill_template(template["content"], case_data)
    doc = Document()
    for paragraph_text in filled_content.split("\n"):
        paragraph = doc.add_paragraph()
        run = paragraph.add_run(paragraph_text)
        run.font.name = "宋体"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
        if paragraph_text.startswith("　　") or paragraph_text == paragraph_text.lstrip():
            pass
        if any(keyword in paragraph_text for keyword in ["授 权", "律师事务所函", "身 份", "案 件 结 算"]):
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run.font.size = Pt(18)
            run.bold = True
    import io
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    filename = f"{template['name']}-{case_data['case_no']}.docx"
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename.encode('utf-8').decode('latin-1')}"},
    )


@router.post(f"{settings.api_prefix}/cases/batch-fees", status_code=status.HTTP_201_CREATED)
async def create_case_batch_fees(body: CaseBatchFeeInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _case_fee_type_snapshot, _resolve_case_fee_contract, _resolve_case_fee_type_master, _round_fee_amount,
    )
    from app.core.permissions import (
        _record_dict_for_identity, _record_scope_conditions,
    )
    case_ids = list(dict.fromkeys(body.case_ids))
    cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case", BusinessRecord.id.in_(case_ids),
        *(await _record_scope_conditions(identity, db)),
    ))).all())
    if len(cases) != len(case_ids):
        raise HTTPException(status_code=404, detail="存在无权访问或不存在的案件")
    expected_fee_type = EXPENSE_SUBTYPE_FEE_TYPE.get(body.expense_subtype, "")
    fee_parameter, fee_option = await _resolve_case_fee_type_master(
        body.fee_type_id, body.expense_scope, db,
        legacy_name=body.expense_subtype, legacy_base=expected_fee_type,
    )
    fee_snapshot = _case_fee_type_snapshot(fee_parameter, fee_option)
    if body.expense_subtype != fee_parameter.name:
        raise HTTPException(status_code=422, detail="费用子类型与系统费用分类不一致")
    handler = body.handler.strip() or identity["username"]
    if identity.get("role") == "user":
        handler = identity["username"]
    handler_user = await db.scalar(select(User).where(User.username == handler, User.is_active.is_(True)))
    if not handler_user:
        raise HTTPException(status_code=422, detail="费用经办人不存在或已停用")
    ordered_cases = sorted(cases, key=lambda item: case_ids.index(item.id))
    contracts_by_case: dict[int, BusinessRecord | None] = {}
    for case_record in ordered_cases:
        if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
            raise HTTPException(status_code=409, detail=f"案件 {case_record.serial_no} 已进入归档流程，不能新增费用")
        contracts_by_case[case_record.id] = await _resolve_case_fee_contract(
            case_record, None, body.expense_scope, identity, db,
        )
    created: list[BusinessRecord] = []
    amount = _round_fee_amount(body.amount)
    for case_record in ordered_cases:
        contract_record = contracts_by_case[case_record.id]
        serial = f"FY{datetime.now():%Y%m%d%H%M%S%f}{uuid4().hex[:6]}"
        item = BusinessRecord(
            module="finance", serial_no=serial, title=f"{case_record.title}{fee_parameter.name}",
            customer=case_record.customer, status="草稿", owner=handler,
            department=case_record.department, description=body.description,
            data={"amount": amount, **fee_snapshot,
                  "expense_scope": body.expense_scope,
                  "is_refund": False, "case_no": case_record.serial_no, "case_id": case_record.id,
                  "contract_id": contract_record.id if contract_record else (case_record.data or {}).get("contract_record_id"),
                  "contract_no": contract_record.serial_no if contract_record else (case_record.data or {}).get("contract_no", ""),
                  "handler": handler, "court": (case_record.data or {}).get("court", ""),
                  "document_no": "", "payee": (case_record.data or {}).get("court", "")},
        )
        db.add(item)
        await db.flush()
        created.append(item)
        db.add(WorkflowEvent(record_id=item.id, action="批量创建案件费用", to_status="草稿", operator=identity["username"], comment=f"{case_record.serial_no}｜{fee_option['path']}：{amount:.2f} 元"))
        db.add(WorkflowEvent(record_id=case_record.id, action="批量新增案件费用", from_status=case_record.status, to_status=case_record.status, operator=identity["username"], comment=f"{item.serial_no}｜{fee_option['path']}：{amount:.2f} 元"))
    await db.commit()
    for item in created:
        await db.refresh(item)
    return {"created": len(created), "items": [await _record_dict_for_identity(item, identity, db) for item in created]}


@router.get(f"{settings.api_prefix}/cases/summary")
async def case_summary(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _record_scope_conditions,
    )
    cases = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "case", *(await _record_scope_conditions(identity, db))))).all()
    return {
        "total": len(cases),
        "pending_assignment": sum(1 for item in cases if item.status == "新案待分配"),
        "in_progress": sum(1 for item in cases if item.status not in {"新案待分配", "已归档"}),
        "execution": sum(1 for item in cases if item.status == "执行"),
        "archived": sum(1 for item in cases if item.status == "已归档"),
    }


@router.get(f"{settings.api_prefix}/cases/pending-execution")
async def list_pending_execution_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.cases import (
        _is_pending_execution_case,
    )
    from app.core.contracts import (
        _contract_customer_record_dicts,
    )
    from app.core.permissions import (
        _record_scope_conditions, _require_record_module_menu,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    await _require_record_module_menu("case", identity, db, action="查看")
    records = list((await db.scalars(
        select(BusinessRecord).where(
            BusinessRecord.module == "case",
            *(await _record_scope_conditions(identity, db)),
        ).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc())
    )).all())
    pending = [record for record in records if _is_pending_execution_case(record)]
    total = len(pending)
    start = (page - 1) * page_size
    allowed_fields = await _allowed_field_keys(identity, db)
    return {
        "items": await _contract_customer_record_dicts(
            pending[start:start + page_size], allowed_fields, db, identity=identity,
        ),
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
    }


@router.post(f"{settings.api_prefix}/cases/invoice-files/import")
async def import_case_invoice_files(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """把当前用户上传的案件发票文件按文件名中的案件编号匹配到案件。"""
    from app.core.permissions import (
        _record_scope_conditions,
    )
    pending = (await db.scalars(
        select(FileAttachment).where(
            FileAttachment.category == "案件发票文件",
            FileAttachment.uploader == identity["username"],
            FileAttachment.record_id.is_(None),
        ).order_by(FileAttachment.id)
    )).all()
    cases = (await db.scalars(
        select(BusinessRecord).where(
            BusinessRecord.module == "case",
            *(await _record_scope_conditions(identity, db)),
        )
    )).all()
    matched = 0
    unmatched = 0
    for attachment in pending:
        normalized = attachment.original_name.upper().replace(" ", "")
        case = next((item for item in cases if item.serial_no.upper() in normalized), None)
        if case:
            attachment.record_id = case.id
            attachment.remark = f"案件发票文件导入｜自动匹配 {case.serial_no}"
            db.add(WorkflowEvent(record_id=case.id, action="导入案件发票文件", from_status=case.status, to_status=case.status, operator=identity["username"], comment=attachment.original_name))
            matched += 1
        else:
            attachment.remark = "案件发票文件导入｜文件名未识别案件编号"
            unmatched += 1
    await db.commit()
    return {"processed": len(pending), "matched": matched, "unmatched": unmatched}


@router.post(f"{settings.api_prefix}/cases/counsel/search")
async def search_counsel_cases(body: CounselCaseSearchInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _query_counsel_cases,
    )
    from app.core.contracts import (
        _contract_customer_record_dicts,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    records = await _query_counsel_cases(body, identity, db)
    total = len(records)
    start = (body.page - 1) * body.page_size
    allowed_fields = await _allowed_field_keys(identity, db)
    return {
        "items": await _contract_customer_record_dicts(
            records[start:start + body.page_size], allowed_fields, db, identity=identity
        ),
        "total": total,
        "page": body.page,
        "page_size": body.page_size,
        "pages": (total + body.page_size - 1) // body.page_size if total else 0,
    }


@router.post(f"{settings.api_prefix}/cases/search")
async def search_ordinary_cases(body: CounselCaseSearchInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Server-side ordinary-case search; unlike the legacy UI it never truncates to the first 100 rows."""
    from app.core.cases import (
        _query_counsel_cases,
    )
    from app.core.contracts import (
        _contract_customer_record_dicts,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    records = await _query_counsel_cases(body, identity, db, counsel_only=False)
    total = len(records)
    # The legacy phase tree remains a dashboard for the current non-phase search
    # scope. Selecting a tree node must filter the table without erasing all of
    # the sibling counts to zero.
    has_phase_filter = bool(body.case_statuses or (body.case_status or body.status).strip())
    count_records = records if not has_phase_filter else await _query_counsel_cases(
        body,
        identity,
        db,
        counsel_only=False,
        include_status_filter=False,
    )
    phase_counts: dict[str, int] = {}
    for record in count_records:
        phase = str(record.status or "")
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
    start = (body.page - 1) * body.page_size
    allowed_fields = await _allowed_field_keys(identity, db)
    return {
        "items": await _contract_customer_record_dicts(
            records[start:start + body.page_size], allowed_fields, db, identity=identity
        ),
        "total": total,
        "page": body.page,
        "page_size": body.page_size,
        "pages": (total + body.page_size - 1) // body.page_size if total else 0,
        "phase_counts": phase_counts,
    }


@router.post(f"{settings.api_prefix}/cases/counsel/export")
async def export_counsel_cases(body: CounselCaseSearchInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _query_counsel_cases,
    )
    records = await _query_counsel_cases(body, identity, db)
    if body.selected_only:
        selected_ids = list(dict.fromkeys(body.selected_ids))
        if not selected_ids:
            raise HTTPException(status_code=422, detail="请选择需要导出的法律顾问案件")
        selected_set = set(selected_ids)
        records = [record for record in records if record.id in selected_set]
        if len(records) != len(selected_set):
            raise HTTPException(status_code=403, detail="选中的案件不存在、不可见或不符合当前查询条件")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["案件编号", "案件名称", "顾问类型", "客户", "顾问开始日期", "顾问结束日期", "经办律师", "律师助理", "案源人", "案件阶段", "所属部门"])
    for record in records:
        data = record.data or {}
        writer.writerow([
            record.serial_no, record.title, data.get("counsel_type", ""), record.customer,
            data.get("counsel_start", ""), data.get("counsel_end", ""),
            "、".join(data.get("handling_lawyers") or []), data.get("assistant", ""),
            data.get("source_person") or record.owner, record.status, record.department,
        ])
    scope_label = "selected" if body.selected_only else "all"
    content = ("\ufeff" + output.getvalue()).encode("utf-8")
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="counsel-cases-{scope_label}-{date.today()}.csv"'},
    )


@router.get(f"{settings.api_prefix}/cases/eligible-contracts")
async def list_case_eligible_contracts(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Return every visible contract that can actually start the staged case flow."""
    from app.core.contracts import (
        _contract_customer_record_dicts,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    conditions = [
        BusinessRecord.module == "contract",
        BusinessRecord.status != "草稿",
        *(await _record_scope_conditions(identity, db)),
    ]
    contracts = (await db.scalars(
        select(BusinessRecord).where(*conditions).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc())
    )).all()
    items = await _contract_customer_record_dicts(
        list(contracts), await _allowed_field_keys(identity, db), db, identity=identity,
    )
    return {"items": items, "total": len(contracts)}


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/fee-contracts")
async def list_case_fee_contracts(
    case_id: int,
    expense_scope: str = Query(pattern="^(律所|平台)$"),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Return every customer contract for a visible case and fee scope."""
    from app.core.finance import (
        _case_fee_contract_body,
    )
    from app.core.permissions import (
        _case_detail_action_capabilities, _ensure_record_module, _record_dict_for_identity,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    capabilities = await _case_detail_action_capabilities(case_record, identity, db)
    if not capabilities["can_create_finance"]:
        raise HTTPException(status_code=403, detail="当前账号没有新增案件费用权限")
    contracts = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "contract",
        BusinessRecord.customer == case_record.customer,
    ).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all())
    contracts = [item for item in contracts if _case_fee_contract_body(item) == expense_scope]
    return {"items": [await _record_dict_for_identity(item, identity, db) for item in contracts], "total": len(contracts)}


@router.get(f"{settings.api_prefix}/cases/reference-options")
async def list_case_reference_options(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Return active case dictionaries needed by the staged create form."""
    from app.core.system import (
        _is_smoke_test_username,
    )
    case_types = (await db.scalars(select(SystemParameter).where(
        SystemParameter.category == "case_type", SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.sort_order, SystemParameter.id))).all()
    causes = (await db.scalars(select(SystemParameter).where(
        SystemParameter.category == "cause", SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.sort_order, SystemParameter.id))).all()
    case_file_types = (await db.scalars(select(SystemParameter).where(
        SystemParameter.category == "case_file_type", SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.sort_order, SystemParameter.id))).all()
    courts = (await db.scalars(select(SystemParameter).where(
        SystemParameter.category == "court", SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.sort_order, SystemParameter.id))).all()
    court_officers = (await db.scalars(select(SystemParameter).where(
        SystemParameter.category == "court_officer", SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.sort_order, SystemParameter.id))).all()
    file_type_relations = list((await db.scalars(select(CaseTypeFileTypeRelation))).all())
    case_type_ids_by_file_type: dict[int, list[int]] = {}
    for relation in file_type_relations:
        case_type_ids_by_file_type.setdefault(relation.file_type_id, []).append(relation.case_type_id)
    serialized_case_file_types = [{
        "id": item.id, "value": item.name, "label": item.name, "code": item.code,
        "parent_code": (item.extra or {}).get("parent_code", ""),
        "case_type_ids": sorted(case_type_ids_by_file_type.get(item.id, [])),
    } for item in case_file_types]
    # 普通案件的通用上传接口接受“普通附件”作为合法兜底；向客户端公开它，
    # 防止旧租户尚未配置案件文件类型时页面提交无效的静态分类。
    if not any(item["value"] == "普通附件" for item in serialized_case_file_types):
        serialized_case_file_types.append({"id": 0, "value": "普通附件", "label": "普通附件", "code": "COMMON", "parent_code": "", "case_type_ids": []})
    employee_records = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "hr"))).all()
    # users 是人员主数据；HR 业务记录仅保存员工扩展资料，不能限制已创建账号出现在人员选择器中。
    # 旧系统的人员选择器展示所有在职账号，因此兼容没有 HR 记录但已在系统创建的真实账号。
    active_users = (await db.scalars(select(User).where(
        User.is_active.is_(True),
    ).order_by(User.display_name, User.username))).all()
    people_options = []
    seen_usernames: set[str] = set()
    for item in active_users:
        username = item.username.strip().lower()
        if _is_smoke_test_username(item.username):
            continue
        if username in seen_usernames:
            continue
        seen_usernames.add(username)
        # A task is assigned to a login username, so its label must come from
        # that same identity.  HR archives are extension records and legacy
        # imports can contain conflicting rows for one username; allowing the
        # last HR row to overwrite the account name hides the real employee
        # from both owner and collaborator searches.
        display_name = str(item.display_name or "").strip() or item.username
        people_options.append({
            "value": item.username,
            "label": f"{display_name}（{item.department}）",
            "position": str((item.profile or {}).get("position") or (item.profile or {}).get("staff_role") or "").strip(),
        })
    # The legacy AvailableUsers endpoint searches every active staff account by
    # Chinese display name.  Although the old control is named
    # AssociateAvailableUser_Laywer, it does not filter by the HR position text;
    # filtering here made valid active employees impossible to select.
    lawyer_options = people_options
    return {
        "case_types": [{
            "id": item.id,
            "value": "民事案件" if item.name == "民事争议" else item.name,
            "label": item.name,
            "code": item.code,
        } for item in case_types],
        "causes": [{"value": item.name, "label": item.name, "code": item.code} for item in causes],
        "case_file_types": serialized_case_file_types,
        "courts": [{"value": item.name, "label": item.name, "code": item.code} for item in courts],
        "court_officers": [{"value": item.name, "label": item.name, "code": item.code, "court_code": (item.extra or {}).get("court_code", ""), "role": (item.extra or {}).get("role", ""), "phone": (item.extra or {}).get("phone", "")} for item in court_officers],
        "case_lawyers": lawyer_options,
        "case_assistants": people_options,
        "right_types": ["商标权", "专利权", "著作权", "不正当竞争", "商业秘密", "其他"],
    }


@router.post(f"{settings.api_prefix}/cases", status_code=status.HTTP_201_CREATED)
async def create_case(body: CaseCreateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """从有效合同建立案件；客户、部门和合同编号均以合同资料为准。"""
    from app.core.cases import (
        _case_team_payload, _next_case_serial, _resolve_active_case_people,
    )
    from app.core.contracts import (
        _contract_allows_downstream_creation,
    )
    from app.core.crm import (
        _customer_reference_from_maps, _persist_case_litigant_customers,
    )
    from app.core.formatters import (
        _normalized_customer_name, _person_display_name,
    )
    from app.core.legacy_sync import (
        _sync_legacy_projection,
    )
    from app.core.permissions import (
        _ensure_record_visible, _permission_payload_for_identity,
    )
    from app.core.projections import (
        _contract_customer_projection_context,
    )
    from app.core.system import (
        _record_dict,
    )
    title = body.title.strip()
    case_type = body.case_type.strip()
    cause_or_charge = body.cause_or_charge.strip()
    if not title:
        raise HTTPException(status_code=422, detail="案件名称不能为空")
    if case_type not in CASE_CREATABLE_TYPES:
        raise HTTPException(status_code=422, detail="案件类型不是原系统允许的新建类型")
    serial_no = body.serial_no.strip() or await _next_case_serial(case_type, db)
    canonical_status = CASE_CREATE_STATUS_ALIASES.get(body.status.strip())
    if canonical_status is None:
        raise HTTPException(status_code=422, detail="新建案件阶段必须为待分配")
    counsel_type = body.counsel_type.strip()
    if case_type != "法律顾问" and not cause_or_charge:
        raise HTTPException(status_code=422, detail="罪名或案由不能为空")
    if case_type == "法律顾问":
        if not counsel_type:
            raise HTTPException(status_code=422, detail="顾问类型不能为空")
        if len(counsel_type) > 128:
            raise HTTPException(status_code=422, detail="顾问类型过长")
        if not body.counsel_start or not body.counsel_end:
            raise HTTPException(status_code=422, detail="顾问期限不能为空")
        if body.counsel_start > body.counsel_end:
            raise HTTPException(status_code=422, detail="顾问结束日期不能早于开始日期")
        cause_or_charge = ""
    elif counsel_type or body.counsel_start or body.counsel_end:
        raise HTTPException(status_code=422, detail="仅法律顾问案件可以填写顾问类型和顾问期限")
    handling_lawyers = list(dict.fromkeys(str(item or "").strip() for item in body.handling_lawyers if str(item or "").strip()))
    if not handling_lawyers or any(len(item) > 128 for item in handling_lawyers):
        raise HTTPException(status_code=422, detail="请按顺序录入有效的经办律师")
    client_position = body.client_position.strip()
    if case_type == "法律顾问":
        client_position = ""
    allowed_client_positions = CASE_CLIENT_POSITIONS_BY_TYPE.get(case_type)
    if allowed_client_positions and client_position not in allowed_client_positions:
        raise HTTPException(status_code=422, detail=f"{case_type}客户诉讼地位无效")
    if case_type == "行政案件及国家赔偿" and client_position not in ADMINISTRATIVE_CLIENT_POSITIONS:
        raise HTTPException(status_code=422, detail="行政案件客户诉讼地位无效")
    right_type = body.right_type.strip()
    if case_type == "法律顾问":
        right_type = ""
    if len(right_type) > 128:
        raise HTTPException(status_code=422, detail="权利类型过长")
    assistant = body.assistant.strip()
    if len(assistant) > 128:
        raise HTTPException(status_code=422, detail="律师助理姓名过长")
    creator_user = await db.scalar(select(User).where(User.username == identity["username"], User.is_active.is_(True)))
    creator_label = str(creator_user.display_name if creator_user else identity["username"]).strip()
    creator_selection = len(handling_lawyers) == 1 and handling_lawyers[0] in {identity["username"], creator_label}
    if creator_selection and creator_user:
        handling_lawyers, handling_usernames = [creator_label], [creator_user.username]
    else:
        handling_lawyers, handling_usernames = await _resolve_active_case_people(handling_lawyers, db, field_name="经办律师")
    assistant_values, assistant_usernames = await _resolve_active_case_people([assistant] if assistant else [], db, field_name="律师助理")
    assistant = assistant_values[0] if assistant_values else ""
    assistant_username = assistant_usernames[0] if assistant_usernames else ""
    permission_key = CASE_CREATE_PERMISSION_BY_TYPE[case_type]
    if identity.get("role") != "admin":
        permission = await _permission_payload_for_identity(identity, db)
        if permission_key not in set(permission.get("menu_keys", [])):
            raise HTTPException(status_code=403, detail="当前角色没有该案件类型的新建权限")
    contract = await _ensure_record_visible(body.contract_record_id, identity, db)
    if contract.module != "contract":
        raise HTTPException(status_code=422, detail="关联记录不是合同")
    if not _contract_allows_downstream_creation(contract):
        raise HTTPException(status_code=409, detail="草稿合同不能新建案件")
    contract_context = await _contract_customer_projection_context([contract], db)
    contract_customer, relation_status = _customer_reference_from_maps(
        contract.customer,
        contract.data or {},
        contract_context["customers_by_id"],
        contract_context["customers_by_no"],
        contract_context["customers_by_name"],
    )
    if not contract_customer:
        detail = "关联合同未绑定唯一有效客户，不能新建案件"
        if relation_status.startswith("ambiguous"):
            detail = "关联合同客户名称存在重名，必须先绑定明确客户后再新建案件"
        raise HTTPException(status_code=409, detail=detail)
    requested_customer_id = body.customer_record_id or body.customer_id
    if requested_customer_id and requested_customer_id != contract_customer.id:
        raise HTTPException(status_code=422, detail="所选客户与关联合同绑定客户不一致")
    if body.customer_no.strip() and body.customer_no.strip() != contract_customer.serial_no:
        raise HTTPException(status_code=422, detail="客户编号与关联合同绑定客户不一致")
    if body.customer.strip() and _normalized_customer_name(body.customer) != _normalized_customer_name(contract_customer.title):
        raise HTTPException(status_code=422, detail="客户名称与关联合同绑定客户不一致")
    contract.data = {
        **(contract.data or {}),
        "customer_id": contract_customer.id,
        "customer_record_id": contract_customer.id,
        "customer_no": contract_customer.serial_no,
    }
    contract.customer = contract_customer.title
    department = contract.department.strip()
    if not department or not await db.scalar(select(Department.id).where(Department.name == department, Department.is_active.is_(True))):
        raise HTTPException(status_code=409, detail="关联合同没有有效的所属部门")
    if await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == serial_no)):
        raise HTTPException(status_code=409, detail="业务编号已存在")
    contract_data = contract.data or {}
    opponent = body.opponent.strip()
    source_token = body.source_person.strip() or str(contract_data.get("source_person") or contract.owner or "").strip()
    source_user = await db.scalar(select(User).where(User.username == source_token)) if source_token else None
    source_person, _ = _person_display_name(source_user.display_name, source_user.username) if source_user else (source_token, False)
    owner = body.owner.strip() or identity["username"]
    if identity.get("role") != "admin":
        user = await db.scalar(select(User).where(User.username == identity["username"]))
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="当前用户不存在")
        owner = user.username
    owner_user = await db.scalar(select(User).where(User.username == owner, User.is_active.is_(True)))
    if not owner_user:
        raise HTTPException(status_code=422, detail="案件负责人必须是有效用户")
    record = BusinessRecord(
        module="case", serial_no=serial_no, title=title,
        customer=contract_customer.title, status=canonical_status, owner=owner,
        department=department, description="",
        data={
            "contract_id": contract.id,
            "contract_no": contract.serial_no,
            "external_contract_no": contract_data.get("external_contract_no", ""),
            "external_contract_numbers": contract_data.get("external_contract_numbers", []),
            "contract_title": contract.title,
            "customer_id": contract_customer.id,
            "customer_record_id": contract_customer.id,
            "customer_no": contract_customer.serial_no,
            "case_type": case_type,
            "client_position": client_position,
            "opponent": opponent,
            "defendants": [opponent] if opponent else [],
            "cause_or_charge": cause_or_charge,
            "right_type": right_type,
            "source_person": source_person,
            "source_person_username": source_user.username if source_user else "",
            "investigator": body.investigator.strip(),
            "investigation_clue": body.investigation_clue.strip(),
            "counsel_type": counsel_type,
            "counsel_start": str(body.counsel_start) if body.counsel_start else "",
            "counsel_end": str(body.counsel_end) if body.counsel_end else "",
            **_case_team_payload({}, handling_lawyers, handling_usernames, assistant, assistant_username),
            "case_creation_step": "basic",
            "case_creation_approval_status": "未提交",
            "business_stage": "立案",
        },
    )
    db.add(record)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="业务编号已存在") from exc
    await _persist_case_litigant_customers(
        record,
        {"对方当事人": [opponent] if opponent else []},
        identity,
        db,
    )
    db.add(WorkflowEvent(
        record_id=record.id, action="从合同新建案件", to_status=record.status,
        operator=identity["username"], comment=f"关联合同：{contract.serial_no}｜{contract.title}",
    ))
    await _sync_legacy_projection(record, identity, db)
    await db.commit()
    await db.refresh(record)
    return _record_dict(record)


@router.delete(f"{settings.api_prefix}/cases/{{case_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Delete a company case and its case-owned operational records."""
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.tasks import (
        _delete_task_notifications,
    )
    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="仅管理员或管理人员可以删除案件")
    record = await _ensure_record_module(case_id, "case", identity, db)
    if record.status in {"已归档", "已合并"}:
        raise HTTPException(status_code=409, detail="已归档或已合并案件不能删除")
    attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id == case_id))).all())
    attachment_paths = [Path(item.path) for item in attachments]
    for attachment in attachments:
        await db.delete(attachment)
    related_tasks = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "task",
        BusinessRecord.data["case_id"].as_integer() == case_id,
    ))).all())
    for task in related_tasks:
        await _delete_task_notifications(task.id, db)
        await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == task.id))
        await db.delete(task)
    await db.execute(delete(CaseAssistedFee).where(CaseAssistedFee.case_record_id == case_id))
    await db.execute(delete(HearingSchedule).where(HearingSchedule.case_record_id == case_id))
    await db.execute(delete(FinanceTransaction).where(FinanceTransaction.finance_record_id == case_id))
    await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == case_id))
    await db.delete(record)
    await db.commit()
    for path in attachment_paths:
        if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
            path.unlink()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/assisted-fees")
async def list_case_assisted_fees(
    case_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """List the visible ordinary case's standalone assistance applications."""
    from app.core.finance import (
        _case_assisted_fee_dict,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    total = int(await db.scalar(select(func.count()).select_from(CaseAssistedFee).where(
        CaseAssistedFee.case_record_id == case_record.id,
    )) or 0)
    rows = list((await db.scalars(
        select(CaseAssistedFee).where(CaseAssistedFee.case_record_id == case_record.id)
        .order_by(CaseAssistedFee.created_at.desc(), CaseAssistedFee.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).all())
    return {
        "items": [_case_assisted_fee_dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
    }


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/assisted-fees", status_code=status.HTTP_201_CREATED)
async def create_case_assisted_fee(
    case_id: int,
    body: CaseAssistedFeeCreateInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _case_assisted_fee_dict,
    )
    from app.core.permissions import (
        _ensure_case_assisted_fee_write,
    )
    case_record = await _ensure_case_assisted_fee_write(case_id, identity, db)
    assisted_type = body.assisted_type.strip()
    if not assisted_type:
        raise HTTPException(status_code=422, detail="资助类别不能为空")
    row = CaseAssistedFee(
        case_record_id=case_record.id,
        assisted_type=assisted_type,
        amount=body.amount,
        request_user=identity["username"],
        remark=body.remark.strip(),
    )
    db.add(row)
    await db.flush()
    db.add(WorkflowEvent(
        record_id=case_record.id,
        action="新建案件资助费用",
        from_status=case_record.status,
        to_status=case_record.status,
        operator=identity["username"],
        comment=f"资助费用 #{row.id}；类别：{row.assisted_type}" + (f"；金额：{row.amount:.2f}" if row.amount is not None else "") + (f"；{row.remark}" if row.remark else ""),
    ))
    await db.commit()
    await db.refresh(row)
    return _case_assisted_fee_dict(row)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/assisted-fees/{{assisted_fee_id}}")
async def update_case_assisted_fee(
    case_id: int,
    assisted_fee_id: int,
    body: CaseAssistedFeeUpdateInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _case_assisted_fee_dict, _case_assisted_fee_for_case,
    )
    from app.core.permissions import (
        _ensure_case_assisted_fee_write,
    )
    if not body.model_fields_set:
        raise HTTPException(status_code=422, detail="请至少填写一项要修改的资助费用信息")
    case_record = await _ensure_case_assisted_fee_write(case_id, identity, db)
    row = await _case_assisted_fee_for_case(case_record, assisted_fee_id, db)
    if row.status != "待办理":
        raise HTTPException(status_code=409, detail="已办理的资助费用必须保留确认记录，不能修改")
    before = (row.assisted_type, row.amount, row.remark)
    if "assisted_type" in body.model_fields_set:
        assisted_type = (body.assisted_type or "").strip()
        if not assisted_type:
            raise HTTPException(status_code=422, detail="资助类别不能为空")
        row.assisted_type = assisted_type
    if "amount" in body.model_fields_set:
        row.amount = body.amount
    if "remark" in body.model_fields_set:
        row.remark = (body.remark or "").strip()
    db.add(WorkflowEvent(
        record_id=case_record.id,
        action="修改案件资助费用",
        from_status=case_record.status,
        to_status=case_record.status,
        operator=identity["username"],
        comment=(
            f"资助费用 #{row.id}：类别 {before[0]} → {row.assisted_type}；"
            f"金额 {before[1] if before[1] is not None else '未填'} → {row.amount if row.amount is not None else '未填'}；"
            f"备注 {before[2] or '未填'} → {row.remark or '未填'}"
        ),
    ))
    await db.commit()
    await db.refresh(row)
    return _case_assisted_fee_dict(row)


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/assisted-fees/{{assisted_fee_id}}/confirm")
async def confirm_case_assisted_fee(
    case_id: int,
    assisted_fee_id: int,
    body: CaseAssistedFeeConfirmInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _case_assisted_fee_dict, _case_assisted_fee_for_case,
    )
    from app.core.permissions import (
        _ensure_case_assisted_fee_write,
    )
    case_record = await _ensure_case_assisted_fee_write(case_id, identity, db)
    row = await _case_assisted_fee_for_case(case_record, assisted_fee_id, db)
    if row.status != "待办理":
        raise HTTPException(status_code=409, detail="该资助费用已办理，不能重复确认")
    row.status = "已办理"
    row.confirmed_date = body.confirmed_date or date.today()
    row.confirmed_user = identity["username"]
    if body.remark.strip():
        row.remark = (row.remark + "\n" + body.remark.strip()).strip()
    db.add(WorkflowEvent(
        record_id=case_record.id,
        action="办理案件资助费用",
        from_status=case_record.status,
        to_status=case_record.status,
        operator=identity["username"],
        comment=f"资助费用 #{row.id}；类别：{row.assisted_type}；办理日期：{row.confirmed_date}",
    ))
    await db.commit()
    await db.refresh(row)
    return _case_assisted_fee_dict(row)


@router.delete(f"{settings.api_prefix}/cases/{{case_id}}/assisted-fees/{{assisted_fee_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case_assisted_fee(
    case_id: int,
    assisted_fee_id: int,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _case_assisted_fee_for_case,
    )
    from app.core.permissions import (
        _ensure_case_assisted_fee_write,
    )
    case_record = await _ensure_case_assisted_fee_write(case_id, identity, db)
    row = await _case_assisted_fee_for_case(case_record, assisted_fee_id, db)
    if row.status != "待办理":
        raise HTTPException(status_code=409, detail="已办理的资助费用必须保留确认记录，不能删除")
    db.add(WorkflowEvent(
        record_id=case_record.id,
        action="删除案件资助费用",
        from_status=case_record.status,
        to_status=case_record.status,
        operator=identity["username"],
        comment=f"资助费用 #{row.id}；类别：{row.assisted_type}",
    ))
    await db.delete(row)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/duplicate", status_code=status.HTTP_201_CREATED)
async def duplicate_case(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Copy only the case's basic business data into a new, unstarted case.

    The legacy action preserves the source case number as the original case.
    Never clone downstream facts (tasks, files, fees, reminders, schedules or
    workflow history): those records describe work already performed and must
    not be silently recreated under the new case.
    """
    from app.core.cases import (
        _case_copy_root, _next_case_copy_serial,
    )
    from app.core.permissions import (
        _ensure_record_module, _ensure_record_visible,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    source = await _ensure_record_module(case_id, "case", identity, db)
    source_data = dict(source.data or {})
    case_type = str(source_data.get("case_type") or "").strip()
    if case_type not in CASE_CREATABLE_TYPES and case_type not in CIVIL_CASE_TYPES:
        raise HTTPException(status_code=409, detail="原案件类型不支持复制新建")
    contract_id = int(source_data.get("contract_id") or source_data.get("contract_record_id") or 0)
    contract: BusinessRecord | None = None
    if contract_id:
        contract = await _ensure_record_visible(contract_id, identity, db)
        if contract.module != "contract":
            raise HTTPException(status_code=409, detail="原案件关联记录不是合同，不能复制")
    root = await _case_copy_root(source, db)
    root_serial_no = root.serial_no
    owner = source.owner if identity.get("role") == "admin" else identity["username"]
    owner_user = await db.scalar(select(User).where(User.username == owner, User.is_active.is_(True)))
    if not owner_user:
        owner = identity["username"]
    source_id = source.id
    source_serial_no = source.serial_no
    source_title = source.title
    source_status = source.status
    source_description = source.description
    contract_customer = contract.customer if contract else source.customer
    contract_department = contract.department if contract else source.department
    contract_data = dict(contract.data or {}) if contract else {}
    root_record_id = root.id or source_id
    copied_data = dict(source_data)
    for key in {
        "fixed_tasks_generated", "fixed_task_ids", "case_reminder_ids", "task_ids", "schedule_ids",
        "archived_at", "archived_by", "archive_comment", "submitted_at", "submitted_by",
        "approval_comment", "approval_by", "approval_at", "progress_logs",
    }:
        copied_data.pop(key, None)
    contract_snapshot = {
        "contract_id": contract.id, "contract_record_id": contract.id, "contract_no": contract.serial_no,
        "contract_title": contract.title, "external_contract_no": contract_data.get("external_contract_no", ""),
        "external_contract_numbers": contract_data.get("external_contract_numbers", []),
    } if contract else {}
    copied_data.update({
        **contract_snapshot,
        "original_case_no": source_serial_no, "original_case_record_id": source_id,
        "copied_from_case_id": source_id, "copy_root_case_no": root_serial_no,
        "copy_root_case_record_id": root_record_id,
        "copied_at": datetime.now().isoformat(timespec="seconds"),
        "copied_by": identity["username"], "case_creation_step": "basic",
        "case_creation_approval_status": "未提交", "business_stage": "立案",
    })
    copied: BusinessRecord | None = None
    for _ in range(128):
        serial_no = await _next_case_copy_serial(root_serial_no, db)
        copied = BusinessRecord(
            module="case", serial_no=serial_no, title=f"{source_title}（副本）", customer=contract_customer,
            status="新案待分配", owner=owner, department=contract_department, description=source_description,
            data=copied_data,
        )
        db.add(copied)
        try:
            await db.flush()
            break
        except IntegrityError:
            await db.rollback()
            copied = None
    if not copied:
        raise HTTPException(status_code=409, detail="复制案件编号生成冲突，请稍后重试")
    db.add(WorkflowEvent(
        record_id=copied.id, action="复制案件", to_status=copied.status, operator=identity["username"],
        comment=f"来源案件：{source_serial_no}；未复制任务、附件、费用、提醒、排期和历史记录。",
    ))
    db.add(WorkflowEvent(
        record_id=source_id, action="案件被复制", from_status=source_status, to_status=source_status,
        operator=identity["username"], comment=f"新案件：{copied.serial_no}",
    ))
    await db.commit(); await db.refresh(copied)
    return _record_dict(copied, await _allowed_field_keys(identity, db))


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/merge")
async def merge_case(case_id: int, body: CaseMergeInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Merge a same-customer source case into the current case with an audit trail.

    Legacy behaviour moved case fees, internal fees and case documents then
    deleted the entered case.  We retain the source row as ``已合并`` instead
    of physically deleting it, so historic audit, notification and relation
    evidence remains reviewable.  Tasks, reminders, hearings and workflow
    history are deliberately not moved: they record work performed for the
    original matter.
    """
    from app.core.formatters import (
        _record_links_to_case,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _record_scope_conditions,
    )
    target = await _ensure_record_module(case_id, "case", identity, db)
    source_no = body.source_case_no.strip()
    if source_no == target.serial_no:
        raise HTTPException(status_code=422, detail="待合并案件不能与当前案件相同")
    source = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == "case", BusinessRecord.serial_no == source_no,
        *(await _record_scope_conditions(identity, db)),
    ))
    if not source:
        raise HTTPException(status_code=404, detail="未找到待合并案件，或当前账号无权查看")
    blocked_statuses = {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档", "已合并"}
    if target.status in blocked_statuses or source.status in blocked_statuses:
        raise HTTPException(status_code=409, detail="归档中、已归档或已合并案件不能参与合并")
    if source.customer != target.customer:
        raise HTTPException(status_code=422, detail="待合并案件的客户与当前案件不一致，不允许操作")
    source_type = str((source.data or {}).get("case_type") or "").strip()
    target_type = str((target.data or {}).get("case_type") or "").strip()
    if source_type != target_type:
        raise HTTPException(status_code=422, detail="仅允许合并同一案件类型的案件")

    finance_rows = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "finance"))).all())
    moved_fees = 0
    for fee in finance_rows:
        if not _record_links_to_case(fee, source):
            continue
        fee_data = dict(fee.data or {})
        fee.data = {
            **fee_data,
            "case_id": target.id,
            "case_record_id": target.id,
            "case_no": target.serial_no,
            "merged_from_case_id": source.id,
            "merged_from_case_no": source.serial_no,
            "merged_at": datetime.now().isoformat(timespec="seconds"),
        }
        db.add(WorkflowEvent(
            record_id=fee.id, action="案件合并迁移费用", from_status=fee.status, to_status=fee.status,
            operator=identity["username"], comment=f"{source.serial_no} → {target.serial_no}",
        ))
        moved_fees += 1

    assisted_fees = list((await db.scalars(select(CaseAssistedFee).where(
        CaseAssistedFee.case_record_id == source.id,
    ))).all())
    for assisted_fee in assisted_fees:
        assisted_fee.case_record_id = target.id
    moved_assisted_fees = len(assisted_fees)

    attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id == source.id))).all())
    for attachment in attachments:
        attachment.record_id = target.id
        attachment.remark = f"{attachment.remark}｜案件合并迁移：{source.serial_no}→{target.serial_no}".strip("｜")

    source_previous = source.status
    source.status = "已合并"
    source.data = {
        **(source.data or {}), "merged_into_case_id": target.id,
        "merged_into_case_no": target.serial_no, "merged_at": datetime.now().isoformat(timespec="seconds"),
        "merged_by": identity["username"], "merge_comment": body.comment.strip(),
    }
    db.add_all([
        WorkflowEvent(
            record_id=target.id, action="合并案件", from_status=target.status, to_status=target.status,
            operator=identity["username"],
            comment=f"合并来源案件 {source.serial_no}；迁移费用 {moved_fees} 条、资助费用 {moved_assisted_fees} 条、案件文件 {len(attachments)} 个。{body.comment.strip()}",
        ),
        WorkflowEvent(
            record_id=source.id, action="案件已合并", from_status=source_previous, to_status=source.status,
            operator=identity["username"],
            comment=f"已合并至 {target.serial_no}；迁移费用 {moved_fees} 条、资助费用 {moved_assisted_fees} 条、案件文件 {len(attachments)} 个。{body.comment.strip()}",
        ),
    ])
    await db.commit(); await db.refresh(target); await db.refresh(source)
    return {
        "target": await _record_dict_for_identity(target, identity, db),
        "source": await _record_dict_for_identity(source, identity, db),
        "moved_fees": moved_fees, "moved_assisted_fees": moved_assisted_fees, "moved_attachments": len(attachments),
        "not_moved": ["tasks", "reminders", "hearings", "workflow_history"],
    }


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/notary-info")
async def update_case_notary_info(case_id: int, body: CaseNotaryInfoInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.investigation import (
        _sync_case_notary_warehouse_evidence,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _require_case_action,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_action(identity, db, "case.detail.update")
    data = dict(case_record.data or {})
    if str(data.get("case_type") or "") not in CIVIL_CASE_TYPES:
        raise HTTPException(status_code=409, detail="仅民事案件可以维护公证信息")
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档", "已合并"}:
        raise HTTPException(status_code=409, detail="当前案件状态不能维护公证信息")
    previous_notary = str(data.get("notary_nos") or data.get("notary_no") or "")
    previous_address = str(data.get("deposit_address") or "")
    location_ids = list(dict.fromkeys(body.warehouse_location_ids))
    locations = list((await db.scalars(
        select(WarehouseStorageLocation).where(WarehouseStorageLocation.id.in_(location_ids))
    )).all())
    locations_by_id = {location.id: location for location in locations}
    if len(locations_by_id) != len(location_ids):
        raise HTTPException(status_code=422, detail="仓库库位不存在")
    warehouse_ids = {location.warehouse_id for location in locations}
    warehouses = list((await db.scalars(select(Warehouse).where(Warehouse.id.in_(warehouse_ids)))).all())
    warehouses_by_id = {warehouse.id: warehouse for warehouse in warehouses}
    resolved_locations = []
    for location_id in location_ids:
        location = locations_by_id[location_id]
        warehouse = warehouses_by_id.get(location.warehouse_id)
        if not warehouse or not warehouse.is_active or not location.is_active:
            raise HTTPException(status_code=422, detail="仓库库位已停用")
        resolved_locations.append({
            "warehouse_id": warehouse.id,
            "warehouse_no": warehouse.warehouse_no,
            "warehouse_name": warehouse.name,
            "storage_location_id": location.id,
            "storage_location_no": location.storage_location_no,
            "storage_location_name": location.name,
            "display_name": f"{warehouse.name}（{location.name}）",
        })
    deposit_address = "，".join(item["display_name"] for item in resolved_locations)
    case_record.data = {
        **data, "notary_nos": body.notary_nos.strip(), "notary_no": body.notary_nos.strip(),
        "deposit_address": deposit_address,
        "warehouse_location_ids": location_ids,
        "warehouse_locations": resolved_locations,
    }
    await _sync_case_notary_warehouse_evidence(
        case_record,
        [(warehouses_by_id[locations_by_id[location_id].warehouse_id], locations_by_id[location_id]) for location_id in location_ids],
        body.notary_nos.strip(),
        identity["username"],
        db,
    )
    db.add(WorkflowEvent(
        record_id=case_record.id, action="修改案件公证信息", from_status=case_record.status, to_status=case_record.status,
        operator=identity["username"],
        comment=f"公证书号：{previous_notary or '空'} → {body.notary_nos.strip()}；存放位置：{previous_address or '空'} → {deposit_address}。{body.comment.strip()}",
    ))
    await db.commit(); await db.refresh(case_record)
    return await _record_dict_for_identity(case_record, identity, db)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/settlement-amount")
async def update_case_settlement_amount(case_id: int, body: CaseSettlementAmountInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _round_fee_amount,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _require_case_action,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_action(identity, db, "case.detail.update")
    data = dict(case_record.data or {})
    if str(data.get("case_type") or "") not in NORMAL_CASE_BASIC_TYPES | {"仲裁"}:
        raise HTTPException(status_code=409, detail="当前案件类型不能维护诉讼或判决金额")
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档", "已合并"}:
        raise HTTPException(status_code=409, detail="当前案件状态不能维护诉讼或判决金额")
    previous_litigation = data.get("litigation_amount", 0)
    previous_settlement = data.get("settlement_amount", 0)
    case_record.data = {
        **data, "litigation_amount": _round_fee_amount(body.litigation_amount),
        "settlement_amount": _round_fee_amount(body.settlement_amount),
    }
    db.add(WorkflowEvent(
        record_id=case_record.id, action="修改案件诉讼或判决金额", from_status=case_record.status, to_status=case_record.status,
        operator=identity["username"],
        comment=f"诉讼标的：{previous_litigation} → {_round_fee_amount(body.litigation_amount)}；判决金额：{previous_settlement} → {_round_fee_amount(body.settlement_amount)}。{body.comment.strip()}",
    ))
    await db.commit(); await db.refresh(case_record)
    return await _record_dict_for_identity(case_record, identity, db)


@router.get(f"{settings.api_prefix}/case-litigant-candidates")
async def list_case_litigant_candidates(
    keyword: str = Query(default="", max_length=100),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Search visible customer/party records for the legacy litigant tag editor."""
    from app.core.permissions import (
        _record_scope_conditions, _require_case_action,
    )
    await _require_case_action(identity, db, "case.detail.update")
    conditions = [
        BusinessRecord.module == "customer",
        BusinessRecord.status != "已回收",
        *(await _record_scope_conditions(identity, db)),
    ]
    normalized_keyword = keyword.strip()
    if normalized_keyword:
        like = f"%{normalized_keyword}%"
        conditions.append(or_(BusinessRecord.title.ilike(like), BusinessRecord.serial_no.ilike(like)))
    candidates = list((await db.scalars(
        select(BusinessRecord)
        .where(*conditions)
        .order_by(BusinessRecord.title, BusinessRecord.id)
        .limit(50)
    )).all())
    return {
        "items": [
            {
                "id": item.id,
                "serial_no": item.serial_no,
                "title": item.title,
                "customer_type": str((item.data or {}).get("customer_type") or "客户"),
            }
            for item in candidates
        ]
    }


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/litigants")
async def update_case_litigants(case_id: int, body: CaseLitigantsInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Creation-wizard endpoint; it may advance the wizard to the litigants step."""
    from app.core.cases import (
        _persist_case_litigants,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_case_action, _require_record_owner_or_manager,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    creation_step = str((case_record.data or {}).get("case_creation_step") or "")
    if creation_step:
        await _require_record_owner_or_manager(case_record, identity, db)
    else:
        await _require_case_action(identity, db, "case.detail.update")
    return await _persist_case_litigants(
        case_record, body, identity, db,
        advance_creation=True,
        enforce_create_permission=True,
        action="维护当事人信息",
    )


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/litigants-detail")
async def update_case_litigants_from_detail(case_id: int, body: CaseLitigantsInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Legacy detail editor: update only parties, regardless of stale wizard markers."""
    from app.core.cases import (
        _persist_case_litigants,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_case_action,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_action(identity, db, "case.detail.update")
    return await _persist_case_litigants(
        case_record, body, identity, db,
        advance_creation=False,
        enforce_create_permission=False,
        action="修改案件当事人",
    )


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/complete-creation")
async def complete_case_creation(case_id: int, body: CaseCreationCompleteInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _permission_payload_for_identity, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_record_owner_or_manager(case_record, identity, db)
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
        raise HTTPException(status_code=409, detail="归档中的案件不能完成新建")
    case_data = case_record.data or {}
    if str(case_data.get("case_type") or "") != "法律顾问":
        raise HTTPException(status_code=409, detail="当前案件类型必须通过司法机关步骤完成新建")
    if str(case_data.get("case_creation_step") or "") != "litigants":
        raise HTTPException(status_code=409, detail="请先完成当事人信息")
    permission_key = CASE_CREATE_PERMISSION_BY_TYPE["法律顾问"]
    if identity.get("role") != "admin":
        permission = await _permission_payload_for_identity(identity, db)
        if permission_key not in set(permission.get("menu_keys", [])):
            raise HTTPException(status_code=403, detail="当前角色没有法律顾问案件新建权限")
    previous_status = case_record.status
    case_record.status = "待立案审批"
    case_record.data = {
        **case_data,
        "case_creation_step": "completed",
        "case_creation_completed_at": datetime.now().isoformat(timespec="seconds"),
        "case_creation_completed_by": identity["username"],
        "case_creation_approval_status": "待审批",
        "case_creation_submitted_at": datetime.now().isoformat(timespec="seconds"),
        "case_creation_submitted_by": identity["username"],
    }
    db.add(WorkflowEvent(
        record_id=case_record.id,
        action="完成法律顾问案件新建",
        from_status=previous_status,
        to_status=case_record.status,
        operator=identity["username"],
        comment=body.comment or "案件资料填写完成，提交案件主管审批",
    ))
    await db.commit()
    await db.refresh(case_record)
    return _record_dict(case_record)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/counsel-basic")
async def update_counsel_case_basic(case_id: int, body: CaseCounselBasicInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_team_payload, _resolve_active_case_people,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_case_action,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_action(identity, db, "case.detail.update")
    case_data = case_record.data or {}
    if str(case_data.get("case_type") or "") != "法律顾问":
        raise HTTPException(status_code=409, detail="该接口仅用于法律顾问案件")
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
        raise HTTPException(status_code=409, detail="归档中的法律顾问案件不能修改基本信息")
    if str(case_data.get("case_creation_step") or "") != "completed":
        raise HTTPException(status_code=409, detail="请先完成法律顾问案件新建流程")
    title = body.title.strip()
    counsel_type = body.counsel_type.strip()
    if not title or not counsel_type:
        raise HTTPException(status_code=422, detail="案件名称和顾问类型不能为空")
    if body.counsel_start > body.counsel_end:
        raise HTTPException(status_code=422, detail="顾问结束日期不能早于开始日期")
    handling_lawyers = list(dict.fromkeys(str(item or "").strip() for item in body.handling_lawyers if str(item or "").strip()))
    assistant = body.assistant.strip()
    handling_lawyers, handling_usernames = await _resolve_active_case_people(handling_lawyers, db, field_name="经办律师")
    assistant_values, assistant_usernames = await _resolve_active_case_people([assistant] if assistant else [], db, field_name="律师助理")
    assistant = assistant_values[0] if assistant_values else ""
    assistant_username = assistant_usernames[0] if assistant_usernames else ""
    if not handling_lawyers:
        raise HTTPException(status_code=422, detail="请至少保留一名有效经办律师")
    old_summary = f"{case_record.title}｜{case_data.get('counsel_type', '')}｜{case_data.get('counsel_start', '')}至{case_data.get('counsel_end', '')}"
    case_record.title = title
    case_record.data = _case_team_payload({
        **case_data,
        "counsel_type": counsel_type,
        "counsel_start": str(body.counsel_start),
        "counsel_end": str(body.counsel_end),
    }, handling_lawyers, handling_usernames, assistant, assistant_username)
    db.add(WorkflowEvent(
        record_id=case_record.id,
        action="修改法律顾问案件基本信息",
        from_status=case_record.status,
        to_status=case_record.status,
        operator=identity["username"],
        comment=f"修改前：{old_summary}" + (f"｜说明：{body.comment.strip()}" if body.comment.strip() else ""),
    ))
    await db.commit()
    await db.refresh(case_record)
    return _record_dict(case_record)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/normal-basic")
async def update_normal_case_basic(case_id: int, body: CaseNormalBasicInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Update the evidenced civil/criminal/administrative basic-information branch.

    The endpoint is intentionally separate from counsel-basic and from generic
    record PATCH so archived cases and the case lifecycle cannot be bypassed.
    """
    from app.core.cases import (
        _active_case_phase_values, _case_team_payload, _prioritize_new_case_assistants, _resolve_active_case_people,
    )
    from app.core.crm import (
        _customer_or_404,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_scope_conditions, _require_case_action,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_action(identity, db, "case.detail.update")
    case_data = case_record.data or {}
    case_type = str(case_data.get("case_type") or "")
    if case_type not in NORMAL_CASE_BASIC_TYPES:
        raise HTTPException(status_code=409, detail="该接口仅用于民事、刑事、行政及国家赔偿案件")
    # This is the detail-page maintenance endpoint, not a creation-wizard step.
    # Historical and duplicated cases may retain ``basic``/``litigants`` in the
    # JSON marker even though they are already active.  Keep authorization and
    # archive locks below, but do not let that stale wizard marker block edits.
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
        raise HTTPException(status_code=409, detail="归档中的案件不能修改基本信息")
    title = body.title.strip()
    phase = body.case_phase.strip()
    cause_or_charge = body.cause_or_charge.strip()
    if phase != case_record.status:
        active_phase_values = await _active_case_phase_values(db)
        if phase not in active_phase_values:
            raise HTTPException(status_code=422, detail="案件阶段不是允许的办理阶段")
    if not title or not cause_or_charge:
        raise HTTPException(status_code=422, detail="案件名称、案由或罪名不能为空")
    customer = await _customer_or_404(body.customer_record_id, identity, db)
    if customer.status in {"公海", "已回收"}:
        raise HTTPException(status_code=409, detail="不能关联公海或回收站客户")
    handling_lawyers = list(dict.fromkeys(str(item or "").strip() for item in body.handling_lawyers if str(item or "").strip()))
    handling_lawyers, handling_usernames = await _resolve_active_case_people(handling_lawyers, db, field_name="经办律师")
    if not handling_lawyers:
        raise HTTPException(status_code=422, detail="请至少保留一名有效经办律师")
    requested_assistants = body.assistants if body.assistants is not None else ([body.assistant.strip()] if body.assistant.strip() else [])
    assistant_values, assistant_usernames = await _resolve_active_case_people(requested_assistants, db, field_name="律师助理")
    assistant_values, assistant_usernames = _prioritize_new_case_assistants(
        case_data, assistant_values, assistant_usernames,
    )
    investigator_values, _ = await _resolve_active_case_people([body.investigator.strip()] if body.investigator.strip() else [], db, field_name="调查员")
    business_owner_values, _ = await _resolve_active_case_people([body.business_owner.strip()] if body.business_owner.strip() else [], db, field_name="案源人")
    clue_ids = list(dict.fromkeys(body.investigation_clue_ids))
    clues = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(clue_ids), BusinessRecord.module == "clue", *(await _record_scope_conditions(identity, db)),
    ))).all()) if clue_ids else []
    clues_by_id = {item.id: item for item in clues}
    if len(clues_by_id) != len(clue_ids):
        raise HTTPException(status_code=404, detail="关联调查线索不存在或无权访问")
    ordered_clues = [clues_by_id[item_id] for item_id in clue_ids]
    right_type = body.right_type.strip()
    if case_type != "行政案件及国家赔偿" and right_type:
        raise HTTPException(status_code=422, detail="仅行政及国家赔偿案件可以修改权利类型")
    old_summary = f"{case_record.customer}｜{case_record.title}｜{case_record.status}｜{case_data.get('cause_or_charge', '')}"
    previous_status = case_record.status
    investigator = investigator_values[0] if investigator_values else ""
    business_owner = business_owner_values[0] if business_owner_values else ""
    clue_nos = [item.serial_no for item in ordered_clues]
    case_record.title = title
    case_record.customer = customer.title
    case_record.status = phase
    case_record.data = _case_team_payload({
        **case_data,
        "customer_record_id": customer.id,
        "customer_id": customer.id,
        "customer_no": customer.serial_no,
        "cause_or_charge": cause_or_charge,
        "right_type": right_type if case_type == "行政案件及国家赔偿" else str(case_data.get("right_type") or ""),
        "source_person": business_owner or str(case_data.get("source_person") or ""),
        "business_owner": business_owner or str(case_data.get("business_owner") or ""),
        "investigator": investigator,
        "investigation_clue_ids": clue_ids,
        "investigation_clue_nos": clue_nos,
        "investigation_clue_id": clue_ids[0] if clue_ids else None,
        "investigation_clue": "、".join(clue_nos),
        "clue_record_id": clue_ids[0] if clue_ids else None,
        "clue_no": clue_nos[0] if clue_nos else "",
    }, handling_lawyers, handling_usernames, assistant_values, assistant_usernames)
    if phase != previous_status:
        case_record.data = {**case_record.data, "phase_changed_at": datetime.now().isoformat(timespec="seconds")}
    db.add(WorkflowEvent(
        record_id=case_record.id, action="修改普通案件基本信息",
        from_status=previous_status, to_status=case_record.status, operator=identity["username"],
        comment=f"修改前：{old_summary}" + (f"｜说明：{body.comment.strip()}" if body.comment.strip() else ""),
    ))
    await db.commit()
    await db.refresh(case_record)
    return _record_dict(case_record)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/arbitration-basic")
async def update_arbitration_case_basic(case_id: int, body: CaseArbitrationBasicInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Keep the old arbitration edit branch isolated from normal/counsel cases."""
    from app.core.cases import (
        _active_case_phase_values, _case_team_payload, _resolve_active_case_people,
    )
    from app.core.crm import (
        _customer_or_404,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_scope_conditions, _require_case_action, _require_case_creation_completed,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_action(identity, db, "case.detail.update")
    case_data = case_record.data or {}
    if str(case_data.get("case_type") or "") != "仲裁":
        raise HTTPException(status_code=409, detail="该接口仅用于仲裁案件")
    _require_case_creation_completed(case_record, require_approval=False)
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
        raise HTTPException(status_code=409, detail="归档中的仲裁案件不能修改基本信息")
    title, phase, cause_or_charge = body.title.strip(), body.case_phase.strip(), body.cause_or_charge.strip()
    active_phase_values = await _active_case_phase_values(db)
    if phase not in active_phase_values:
        raise HTTPException(status_code=422, detail="案件阶段不是允许的办理阶段")
    if not title or not cause_or_charge:
        raise HTTPException(status_code=422, detail="案件名称和案由不能为空")
    customer = await _customer_or_404(body.customer_record_id, identity, db)
    if customer.status in {"公海", "已回收"}:
        raise HTTPException(status_code=409, detail="不能关联公海或回收站客户")
    lawyers = list(dict.fromkeys(str(item or "").strip() for item in body.handling_lawyers if str(item or "").strip()))
    lawyers, lawyer_usernames = await _resolve_active_case_people(lawyers, db, field_name="经办律师")
    if not lawyers:
        raise HTTPException(status_code=422, detail="请至少保留一名有效经办律师")
    assistant_values, assistant_usernames = await _resolve_active_case_people([body.assistant.strip()] if body.assistant.strip() else [], db, field_name="律师助理")
    investigator_values, _ = await _resolve_active_case_people([body.investigator.strip()] if body.investigator.strip() else [], db, field_name="调查员")
    clue_ids = list(dict.fromkeys(body.investigation_clue_ids))
    clues = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(clue_ids), BusinessRecord.module == "clue", *(await _record_scope_conditions(identity, db))))).all()) if clue_ids else []
    if len({item.id for item in clues}) != len(clue_ids):
        raise HTTPException(status_code=404, detail="关联调查线索不存在或无权访问")
    by_id = {item.id: item for item in clues}; clue_nos = [by_id[item_id].serial_no for item_id in clue_ids]
    previous_status = case_record.status
    old_summary = f"{case_record.customer}｜{case_record.title}｜{case_record.status}｜{case_data.get('cause_or_charge', '')}"
    case_record.title, case_record.customer, case_record.status = title, customer.title, phase
    case_record.data = _case_team_payload({
        **case_data, "customer_record_id": customer.id, "customer_id": customer.id, "customer_no": customer.serial_no,
        "cause_or_charge": cause_or_charge, "investigator": investigator_values[0] if investigator_values else "",
        "investigation_clue_ids": clue_ids, "investigation_clue_nos": clue_nos,
        "investigation_clue_id": clue_ids[0] if clue_ids else None, "investigation_clue": "、".join(clue_nos),
        "clue_record_id": clue_ids[0] if clue_ids else None, "clue_no": clue_nos[0] if clue_nos else "",
    }, lawyers, lawyer_usernames, assistant_values[0] if assistant_values else "", assistant_usernames[0] if assistant_usernames else "")
    if phase != previous_status:
        case_record.data = {**case_record.data, "phase_changed_at": datetime.now().isoformat(timespec="seconds")}
    db.add(WorkflowEvent(record_id=case_record.id, action="修改仲裁案件基本信息", from_status=previous_status, to_status=case_record.status, operator=identity["username"], comment=f"修改前：{old_summary}" + (f"｜说明：{body.comment.strip()}" if body.comment.strip() else "")))
    await db.commit(); await db.refresh(case_record)
    return _record_dict(case_record)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/criminal/litigants")
async def maintain_criminal_litigants(case_id: int, body: CaseLitigantsInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _clean_case_litigant_values, _criminal_detail_maintenance_case,
    )
    from app.core.crm import (
        _persist_case_litigant_customers,
    )
    from app.core.documents import (
        _clean_case_litigant_agents,
    )
    from app.core.system import (
        _save_criminal_detail,
    )
    record = await _criminal_detail_maintenance_case(case_id, identity, db)
    payload = {
        "plaintiffs": _clean_case_litigant_values(body.plaintiffs),
        "plaintiff_agents": _clean_case_litigant_agents(body.plaintiff_agents),
        "defendants": _clean_case_litigant_values(body.defendants),
        "defendant_agents": _clean_case_litigant_agents(body.defendant_agents),
        "third_parties": _clean_case_litigant_values(body.third_parties),
        "third_party_agents": _clean_case_litigant_agents(body.third_party_agents),
    }
    await _persist_case_litigant_customers(
        record,
        {"原告": payload["plaintiffs"], "被告": payload["defendants"], "第三人": payload["third_parties"]},
        identity,
        db,
    )
    return await _save_criminal_detail(record, payload, "修改刑事案件当事人", body.comment, identity, db)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/criminal/public-security")
async def maintain_criminal_public_security(case_id: int, body: CriminalPublicSecurityMaintenanceInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _criminal_detail_maintenance_case,
    )
    from app.core.system import (
        _criminal_maintenance_payload, _save_criminal_detail,
    )
    record = await _criminal_detail_maintenance_case(case_id, identity, db)
    return await _save_criminal_detail(record, _criminal_maintenance_payload(body), "修改刑事案件公安机关信息", body.comment, identity, db)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/criminal/procuratorates")
async def maintain_criminal_procuratorates(case_id: int, body: CriminalProcuratorateMaintenanceInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _criminal_detail_maintenance_case,
    )
    from app.core.system import (
        _criminal_maintenance_payload, _save_criminal_detail,
    )
    record = await _criminal_detail_maintenance_case(case_id, identity, db)
    return await _save_criminal_detail(record, _criminal_maintenance_payload(body), "修改刑事案件检察院信息", body.comment, identity, db)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/criminal/courts")
async def maintain_criminal_courts(case_id: int, body: CriminalCourtMaintenanceInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _criminal_detail_maintenance_case,
    )
    from app.core.system import (
        _criminal_maintenance_payload, _save_criminal_detail,
    )
    record = await _criminal_detail_maintenance_case(case_id, identity, db)
    return await _save_criminal_detail(record, _criminal_maintenance_payload(body), "修改刑事案件审级法院信息", body.comment, identity, db)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/judicial")
async def update_case_judicial(case_id: int, body: CaseJudicialInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _permission_payload_for_identity, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_record_owner_or_manager(case_record, identity, db)
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
        raise HTTPException(status_code=409, detail="归档中的案件不能修改司法机关信息")
    if str((case_record.data or {}).get("case_creation_step") or "") != "litigants":
        raise HTTPException(status_code=409, detail="请先完成当事人信息")
    case_type = str((case_record.data or {}).get("case_type") or "")
    if case_type == "法律顾问":
        raise HTTPException(status_code=409, detail="法律顾问案件不使用司法机关步骤")
    permission_key = CASE_CREATE_PERMISSION_BY_TYPE.get(case_type)
    if permission_key and identity.get("role") != "admin":
        permission = await _permission_payload_for_identity(identity, db)
        if permission_key not in set(permission.get("menu_keys", [])):
            raise HTTPException(status_code=403, detail="当前角色没有该案件类型的新建权限")
    hearing_time = body.hearing_time.strip()
    if hearing_time and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?", hearing_time):
        raise HTTPException(status_code=422, detail="开庭时间格式必须为 HH:MM 或 HH:MM:SS")
    judicial_data: dict[str, object] = {}
    for key, value in body.model_dump().items():
        if isinstance(value, str):
            judicial_data[key] = value.strip()
        elif isinstance(value, date):
            judicial_data[key] = str(value)
        else:
            judicial_data[key] = value
    enabled_court_specs = (
        ("first_court_enabled", "first_court_name", "first_court_judge", "first_court_clerk"),
        ("second_court_enabled", "second_court_name", "second_court_judge", "second_court_clerk"),
        ("retrial_court_enabled", "retrial_court_name", "retrial_court_judge", "retrial_court_clerk"),
    )
    enabled_court_names = [str(judicial_data.get(name_key) or "").strip() for enabled_key, name_key, _, _ in enabled_court_specs if judicial_data.get(enabled_key)]
    if enabled_court_names:
        courts = (await db.scalars(select(SystemParameter).where(SystemParameter.category == "court", SystemParameter.is_active.is_(True)))).all()
        court_codes = {court.name: court.code for court in courts}
        for enabled_key, name_key, judge_key, clerk_key in enabled_court_specs:
            if not judicial_data.get(enabled_key):
                continue
            court_name = str(judicial_data.get(name_key) or "").strip()
            if not court_name or court_name not in court_codes:
                raise HTTPException(status_code=422, detail="启用的法院信息必须选择有效法院")
            for officer_key, officer_role in ((judge_key, "法官"), (clerk_key, "书记员")):
                officer_name = str(judicial_data.get(officer_key) or "").strip()
                if not officer_name:
                    continue
                officer = await db.scalar(select(SystemParameter).where(
                    SystemParameter.category == "court_officer", SystemParameter.name == officer_name,
                    SystemParameter.is_active.is_(True)
                ))
                if not officer or str((officer.extra or {}).get("court_code") or "") != court_codes[court_name] or str((officer.extra or {}).get("role") or "") != officer_role:
                    raise HTTPException(status_code=422, detail=f"{officer_role}必须属于所选法院且处于启用状态")
    case_record.description = str(judicial_data.pop("description", ""))
    if case_type == "行政案件及国家赔偿":
        enabled_court_names = [
            str(judicial_data.get("first_court_name") or "").strip() if judicial_data.get("first_court_enabled") else "",
            str(judicial_data.get("second_court_name") or "").strip() if judicial_data.get("second_court_enabled") else "",
            str(judicial_data.get("retrial_court_name") or "").strip() if judicial_data.get("retrial_court_enabled") else "",
            str(judicial_data.get("court") or "").strip(),
        ]
        if not any(enabled_court_names):
            raise HTTPException(status_code=422, detail="行政案件请至少录入一个法院信息")
        for forbidden_key in (key for key in judicial_data if key.startswith(CRIMINAL_JUDICIAL_PREFIXES)):
            if str(judicial_data.get(forbidden_key) or "").strip():
                raise HTTPException(status_code=422, detail="行政案件不能填写公安或检察院信息")
    previous_status = case_record.status
    case_record.status = "待立案审批"
    case_record.data = {
        **(case_record.data or {}),
        **judicial_data,
        "case_creation_step": "completed",
        "case_creation_completed_at": datetime.now().isoformat(timespec="seconds"),
        "case_creation_completed_by": identity["username"],
        "case_creation_approval_status": "待审批",
        "case_creation_submitted_at": datetime.now().isoformat(timespec="seconds"),
        "case_creation_submitted_by": identity["username"],
    }
    nonempty_fields = [
        key for key, value in judicial_data.items()
        if value not in {"", None, False}
    ]
    db.add(WorkflowEvent(
        record_id=case_record.id,
        action="完成司法机关信息",
        from_status=previous_status,
        to_status=case_record.status,
        operator=identity["username"],
        comment=f"保存司法机关字段 {len(nonempty_fields)} 项并提交案件主管审批",
    ))
    await db.commit()
    await db.refresh(case_record)
    return _record_dict(case_record)


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/creation/review")
async def review_case_creation(case_id: int, body: CaseCreationReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_case_fixed_tasks, _ensure_record_module,
    )
    from app.core.system import (
        _record_dict,
    )
    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="只有管理员或案件主管可以审批新建案件")
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    data = case_record.data or {}
    if data.get("batch_converted"):
        raise HTTPException(status_code=409, detail="线索自动生成案件无需人工立案审批")
    if data.get("case_creation_step") != "completed" or data.get("case_creation_approval_status") != "待审批" or case_record.status != "待立案审批":
        raise HTTPException(status_code=409, detail="该案件不在待立案审批状态")
    if not body.approved and not body.comment.strip():
        raise HTTPException(status_code=422, detail="驳回时必须填写原因")
    previous = case_record.status
    if body.approved:
        case_record.status = "新案待分配"
        approval_status = "已通过"
    else:
        case_record.status = "新案待分配"
        approval_status = "已驳回"
    case_record.data = {
        **data, "case_creation_approval_status": approval_status, "business_stage": "立案",
        "case_creation_reviewer": identity["username"], "case_creation_reviewed_at": datetime.now().isoformat(timespec="seconds"),
        "case_creation_review_comment": body.comment.strip(),
        **({"case_creation_step": "litigants"} if not body.approved else {}),
    }
    action = "案件创建审批通过" if body.approved else "案件创建审批驳回"
    db.add(WorkflowEvent(record_id=case_record.id, action=action, from_status=previous, to_status=case_record.status, operator=identity["username"], comment=body.comment))
    if body.approved:
        await _ensure_case_fixed_tasks(case_record, db, operator="system")
    await db.commit(); await db.refresh(case_record)
    return _record_dict(case_record)


@router.get(f"{settings.api_prefix}/cases/action-capabilities")
async def case_list_action_capabilities(
    record_ids: str = Query(default="", max_length=1200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """Return case capabilities for one visible list page in a single request."""
    from app.core.permissions import (
        _case_detail_action_capabilities, _record_scope_conditions,
    )
    try:
        requested_ids = list(dict.fromkeys(int(value) for value in record_ids.split(",") if value.strip()))
    except ValueError:
        raise HTTPException(status_code=422, detail="案件编号格式无效")
    if not requested_ids:
        return {"items": {}}
    if len(requested_ids) > 100:
        raise HTTPException(status_code=422, detail="一次最多查询 100 条案件的操作权限")
    records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(requested_ids),
        BusinessRecord.module == "case",
        *(await _record_scope_conditions(identity, db)),
    ))).all())
    return {
        "items": {
            str(record.id): await _case_detail_action_capabilities(record, identity, db)
            for record in records
        },
    }


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/action-capabilities")
async def case_detail_action_capabilities(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _case_detail_action_capabilities, _ensure_record_module,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    return {"case_id": case_record.id, **(await _case_detail_action_capabilities(case_record, identity, db))}


@router.get(f"{settings.api_prefix}/case-spaces/{{case_id}}/context")
async def get_case_space_context(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Aggregate one authorized case into the stable context contract used by agents."""
    from app.core.finance import (
        _incoming_payment_dict, _receivable_dict,
    )
    from app.core.formatters import (
        _task_display_dict,
    )
    from app.core.permissions import (
        _case_detail_action_capabilities, _ensure_record_module, _filter_visible_attachments, _record_dict_for_identity, _record_scope_conditions,
        _require_record_owner_or_manager,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    case_data = case_record.data or {}
    allowed_fields = await _allowed_field_keys(identity, db)
    scope_conditions = await _record_scope_conditions(identity, db)

    contract_ids = {
        int(value)
        for value in (case_data.get("contract_id"), case_data.get("contract_record_id"))
        if str(value or "").isdigit() and int(value) > 0
    }
    contract_objects = list((await db.scalars(select(ContractObject).where(
        ContractObject.case_record_id == case_record.id,
    ).order_by(ContractObject.id))).all())
    contract_ids.update(item.contract_record_id for item in contract_objects)
    contract_no = str(case_data.get("contract_no") or "").strip()
    contract_match = BusinessRecord.id.in_(contract_ids)
    if contract_no:
        contract_match = or_(contract_match, BusinessRecord.serial_no == contract_no)
    contracts = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "contract", contract_match, *scope_conditions,
    ).order_by(BusinessRecord.id))).all()) if contract_ids or contract_no else []
    contract_ids = {item.id for item in contracts}

    payment_record_ids = set((await db.scalars(select(ContractPaymentLine.payment_record_id).where(
        ContractPaymentLine.case_record_id == case_record.id,
    ))).all())
    linked_records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module.in_(["finance", "invoice", "task", "contract_payment"]),
        or_(
            BusinessRecord.data["case_id"].as_integer() == case_record.id,
            BusinessRecord.data["case_record_id"].as_integer() == case_record.id,
            BusinessRecord.data["case_no"].as_string() == case_record.serial_no,
            BusinessRecord.id.in_(payment_record_ids),
        ),
        *scope_conditions,
    ).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all())
    finance_records = [item for item in linked_records if item.module == "finance"]
    invoice_records = [item for item in linked_records if item.module == "invoice"]
    tasks = [item for item in linked_records if item.module == "task"]
    payment_records = [item for item in linked_records if item.module == "contract_payment"]

    reminders = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case_reminder",
        BusinessRecord.data["case_id"].as_integer() == case_record.id,
    ).order_by(BusinessRecord.data["deadline"].as_string(), BusinessRecord.id))).all())
    hearings = list((await db.scalars(select(HearingSchedule).where(
        HearingSchedule.case_record_id == case_record.id,
    ).order_by(HearingSchedule.hearing_date, HearingSchedule.hearing_time, HearingSchedule.id))).all())

    customer_id = int(case_data.get("customer_id") or case_data.get("customer_record_id") or 0)
    customer_conditions = [BusinessRecord.module == "customer", *scope_conditions]
    customer_conditions.append(BusinessRecord.id == customer_id if customer_id else BusinessRecord.title == case_record.customer)
    customer = await db.scalar(select(BusinessRecord).where(*customer_conditions).order_by(BusinessRecord.id))

    clue_ids = {
        int(value)
        for value in (
            case_data.get("clue_record_id"), case_data.get("investigation_clue_id"),
        )
        if str(value or "").isdigit() and int(value) > 0
    }
    clue_nos = {
        str(value or "").strip()
        for value in [
            case_data.get("clue_no"), case_data.get("investigation_clue"),
            case_data.get("source_clue_no"), *(case_data.get("investigation_clue_nos") or []),
        ]
        if str(value or "").strip()
    }
    clue_matches = [
        BusinessRecord.data["converted_case_id"].as_integer() == case_record.id,
        BusinessRecord.data["case_id"].as_integer() == case_record.id,
        BusinessRecord.data["case_record_id"].as_integer() == case_record.id,
        BusinessRecord.data["case_no"].as_string() == case_record.serial_no,
    ]
    if clue_ids:
        clue_matches.append(BusinessRecord.id.in_(clue_ids))
    if clue_nos:
        clue_matches.append(BusinessRecord.serial_no.in_(clue_nos))
    clues = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "clue", or_(*clue_matches), *scope_conditions,
    ).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all())

    source_task_ids = {
        int((item.data or {}).get("source_task_id") or 0)
        for item in clues
        if str((item.data or {}).get("source_task_id") or "").isdigit()
        and int((item.data or {}).get("source_task_id") or 0) > 0
    }
    source_tasks = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(source_task_ids),
        BusinessRecord.module.in_(["investigation", "task"]),
        *scope_conditions,
    ))).all()) if source_task_ids else []
    investigation_ids = {
        int(value)
        for value in [
            case_data.get("investigation_record_id"),
            *[(item.data or {}).get("investigation_record_id") for item in clues],
            *[item.id if item.module == "investigation" else (item.data or {}).get("investigation_record_id") for item in source_tasks],
        ]
        if str(value or "").isdigit() and int(value) > 0
    }
    investigation_nos = {
        str(value or "").strip()
        for value in [
            case_data.get("investigation_no"),
            *[(item.data or {}).get("investigation_no") for item in clues],
            *[item.serial_no if item.module == "investigation" else (item.data or {}).get("investigation_no") for item in source_tasks],
        ]
        if str(value or "").strip()
    }
    investigation_matches = [
        BusinessRecord.data["case_id"].as_integer() == case_record.id,
        BusinessRecord.data["case_record_id"].as_integer() == case_record.id,
        BusinessRecord.data["case_no"].as_string() == case_record.serial_no,
    ]
    if investigation_ids:
        investigation_matches.append(BusinessRecord.id.in_(investigation_ids))
    if investigation_nos:
        investigation_matches.append(BusinessRecord.serial_no.in_(investigation_nos))
    investigations = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "investigation", or_(*investigation_matches), *scope_conditions,
    ).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all())

    receivables = list((await db.scalars(select(ReceivablePlan).where(
        ReceivablePlan.contract_record_id.in_(contract_ids),
    ).order_by(ReceivablePlan.due_date, ReceivablePlan.id))).all()) if contract_ids else []
    incoming = list((await db.scalars(select(IncomingPayment).where(or_(
        IncomingPayment.case_no == case_record.serial_no,
        IncomingPayment.contract_record_id.in_(contract_ids) if contract_ids else false(),
    )).order_by(IncomingPayment.received_date.desc(), IncomingPayment.id.desc()))).all())

    source_records = [case_record, *contracts, *clues, *investigations, *finance_records, *invoice_records, *tasks, *payment_records]
    source_by_id = {item.id: item for item in source_records}
    source_ids = set(source_by_id)
    attachments = list((await db.scalars(select(FileAttachment).where(
        FileAttachment.record_id.in_(source_ids),
    ).order_by(FileAttachment.created_at.desc(), FileAttachment.id.desc()))).all()) if source_ids else []
    attachments = await _filter_visible_attachments(attachments, identity, db)

    users = list((await db.scalars(select(User).where(User.is_active.is_(True)))).all())
    users_by_username = {item.username.casefold(): item for item in users}
    users_by_name = {str(item.display_name or "").strip().casefold(): item for item in users if str(item.display_name or "").strip()}

    def person(role: str, value: object) -> dict | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        user = users_by_username.get(raw.casefold()) or users_by_name.get(raw.casefold())
        return {"role": role, "username": user.username if user else "", "name": user.display_name if user else raw}

    people_values = [
        person("案件负责人", case_record.owner),
        *[person("经办律师", item) for item in list(case_data.get("handling_lawyers") or [])],
        person("律师助理", case_data.get("assistant") or case_data.get("assistant_username")),
        person("开庭律师", case_data.get("hearing_lawyer")),
        person("客户管理人", case_data.get("customer_manager")),
        person("案源人", case_data.get("business_owner") or case_data.get("source_person")),
        person("调查员", case_data.get("investigator")),
    ]
    people = []
    seen_people = set()
    for item in filter(None, people_values):
        key = (item["role"], item["username"] or item["name"])
        if key not in seen_people:
            seen_people.add(key)
            people.append(item)

    show_finance_amount = "finance.amount" in allowed_fields
    contract_payload = []
    for contract in contracts:
        objects = [item for item in contract_objects if item.contract_record_id == contract.id]
        plans = [item for item in receivables if item.contract_record_id == contract.id]
        contract_payload.append({
            **_record_dict(contract, allowed_fields),
            "objects": [{"id": item.id, "case_record_id": item.case_record_id, "fee_type": item.fee_type, "amount": item.amount if "contract.amount" in allowed_fields else None, "remark": item.remark} for item in objects],
            "receivables": [{**_receivable_dict(item, contract), **({} if show_finance_amount else {"amount": None, "received_amount": None, "remaining_amount": None})} for item in plans],
        })

    document_payload = []
    for item in attachments:
        source = source_by_id.get(item.record_id)
        document_payload.append({**_attachment_dict(item, source), "source_module": source.module if source else "", "source_status": source.status if source else ""})

    deadline_items = [
        {"type": "案件提醒", "id": item.id, "title": item.title, "reminder_date": (item.data or {}).get("reminder_date", ""), "deadline": (item.data or {}).get("deadline", ""), "status": item.status}
        for item in reminders
    ] + [
        {"type": "开庭排期", "id": item.id, "title": item.hearing_type, "deadline": str(item.hearing_date), "time": item.hearing_time, "court": item.court, "courtroom": item.courtroom, "status": item.status}
        for item in hearings
    ] + [
        {"type": "案件任务", "id": item.id, "title": item.title, "deadline": str((item.data or {}).get("deadline") or ""), "status": item.status, "owner": item.owner}
        for item in tasks if (item.data or {}).get("deadline")
    ]

    capabilities = await _case_detail_action_capabilities(case_record, identity, db)
    capabilities["can_update_customer"] = False
    if customer:
        try:
            await _require_record_owner_or_manager(customer, identity, db)
            capabilities["can_update_customer"] = True
        except HTTPException:
            pass
    capabilities["can_update_contract"] = False
    for contract in contracts:
        try:
            await _require_record_owner_or_manager(contract, identity, db)
            if contract.status in {"草稿", "已拒绝"}:
                capabilities["can_update_contract"] = True
                break
        except HTTPException:
            continue

    context = {
        "schema_version": "1.1",
        "space": {"id": f"case:{case_record.id}", "kind": "business_graph", "case_id": case_record.id, "case_no": case_record.serial_no, "generated_at": datetime.now(timezone.utc)},
        "case": await _record_dict_for_identity(case_record, identity, db),
        "customer": await _record_dict_for_identity(customer, identity, db) if customer else None,
        "people": people,
        "contracts": contract_payload,
        "finances": {
            "fees": [_record_dict(item, allowed_fields) for item in finance_records],
            "invoices": [_record_dict(item, allowed_fields) for item in invoice_records],
            "contract_payments": [_record_dict(item, allowed_fields) for item in payment_records],
            "incoming_payments": [_incoming_payment_dict(item, show_amount=show_finance_amount) for item in incoming],
        },
        "deadlines": deadline_items,
        "documents": document_payload,
        "tasks": [await _task_display_dict(item, db) for item in tasks],
        "relationships": {
            "clues": [await _record_dict_for_identity(item, identity, db) for item in clues],
            "investigations": [await _record_dict_for_identity(item, identity, db) for item in investigations],
            "edges": [
                *([{"from": f"case:{case_record.id}", "to": f"customer:{customer.id}", "type": "belongs_to_customer"}] if customer else []),
                *[{"from": f"case:{case_record.id}", "to": f"contract:{item.id}", "type": "covered_by_contract"} for item in contracts],
                *[{"from": f"clue:{item.id}", "to": f"case:{case_record.id}", "type": "converted_to_case"} for item in clues],
                *[{"from": f"investigation:{item.id}", "to": f"case:{case_record.id}", "type": "supports_case"} for item in investigations],
                *[{"from": f"finance:{item.id}", "to": f"case:{case_record.id}", "type": "financial_record"} for item in finance_records],
                *[{"from": f"invoice:{item.id}", "to": f"case:{case_record.id}", "type": "invoice_record"} for item in invoice_records],
            ],
        },
        "capabilities": capabilities,
        "agent": {
            **case_agent_runtime.status(),
            "shared_space_id": f"case:{case_record.id}",
            "private_thread_id": case_agent_runtime.thread_id(case_record.id, identity["username"]),
        },
    }
    context["standard_workflow"] = build_case_workflow_guide(context)
    return context


@router.get(f"{settings.api_prefix}/case-spaces/{{case_id}}/workflow-guide")
async def get_case_workflow_guide(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    context = await get_case_space_context(case_id, identity, db)
    return context["standard_workflow"]


@router.get(f"{settings.api_prefix}/case-spaces/{{case_id}}/agent/status")
async def case_agent_status(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _agent_skill_catalog_for_identity, _ensure_record_module,
    )
    await _ensure_record_module(case_id, "case", identity, db)
    runtime_status = case_agent_runtime.status()
    return {
        "case_id": case_id,
        "shared_space_id": f"case:{case_id}",
        "thread_id": case_agent_runtime.thread_id(case_id, identity["username"]),
        **runtime_status,
        "skills": await _agent_skill_catalog_for_identity(identity, db),
    }


@router.get(f"{settings.api_prefix}/case-spaces/{{case_id}}/agent/state")
async def case_agent_state(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    await _ensure_record_module(case_id, "case", identity, db)
    if not case_agent_runtime.status()["ready"]:
        raise HTTPException(status_code=503, detail="案件智能体尚未就绪")
    try:
        return await case_agent_runtime.get_state(case_id, identity["username"])
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="案件智能体状态读取失败") from exc


@router.post(f"{settings.api_prefix}/case-spaces/{{case_id}}/agent/messages")
async def send_case_agent_message(
    case_id: int,
    body: CaseAgentMessageInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _agent_skill_for_identity,
    )
    context = await get_case_space_context(case_id, identity, db)
    if not case_agent_runtime.status()["ready"]:
        raise HTTPException(status_code=503, detail="案件智能体尚未就绪")
    proposed_action = body.proposed_action.model_dump() if body.proposed_action else None
    selected_skill = await _agent_skill_for_identity(body.skill_id, identity, db)
    if proposed_action and not context["capabilities"].get("can_write"):
        raise HTTPException(status_code=403, detail="当前账号无权为该案件发起写操作")
    images: list[dict[str, object]] = []
    attachment_ids = list(dict.fromkeys(body.attachment_ids))
    if attachment_ids:
        attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.id.in_(attachment_ids)))).all())
        if len(attachments) != len(attachment_ids) or any(item.record_id != case_id for item in attachments):
            raise HTTPException(status_code=404, detail="截图附件不存在或不属于当前案件")
        by_id = {item.id: item for item in attachments}
        total_size = 0
        mime_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
        for attachment_id in attachment_ids:
            item = by_id[attachment_id]
            suffix = Path(item.original_name or item.path).suffix.lower()
            mime_type = mime_types.get(suffix)
            if not mime_type:
                raise HTTPException(status_code=422, detail="截图证据仅支持 PNG、JPG、JPEG 或 WebP")
            path = Path(item.path)
            if not path.is_file() or UPLOAD_ROOT.resolve() not in path.resolve().parents:
                raise HTTPException(status_code=404, detail="截图附件文件不存在")
            content = path.read_bytes()
            total_size += len(content)
            if len(content) > 6 * 1024 * 1024 or total_size > 12 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="单张截图不能超过 6MB，单次分析总计不能超过 12MB")
            images.append({
                "id": item.id,
                "name": item.original_name,
                "mime_type": mime_type,
                "data_url": f"data:{mime_type};base64,{base64.b64encode(content).decode('ascii')}",
            })
    allowed_document_ids = [int(item.get("id") or 0) for item in context.get("documents", []) if int(item.get("id") or 0) > 0]
    document_ids = allowed_document_ids if body.document_ids is None else list(dict.fromkeys(body.document_ids))
    if any(item not in allowed_document_ids for item in document_ids):
        raise HTTPException(status_code=404, detail="所选材料不存在或不在当前账号可见的案件空间内")
    document_readings: list[dict[str, object]] = []
    if document_ids:
        visible_documents = list((await db.scalars(select(FileAttachment).where(FileAttachment.id.in_(document_ids)))).all())
        visible_by_id = {item.id: item for item in visible_documents}
        remaining_chars = 60_000
        visual_bytes = sum(len(str(item.get("data_url") or "")) for item in images)
        document_visual_groups: list[tuple[FileAttachment, tuple[dict[str, str], ...]]] = []
        seen_files: set[tuple[str, int]] = set()
        for attachment_id in document_ids:
            item = visible_by_id.get(attachment_id)
            if not item or len(document_readings) >= 12:
                continue
            dedupe_key = (str(item.original_name or "").strip().casefold(), int(item.size or 0))
            if dedupe_key in seen_files:
                continue
            seen_files.add(dedupe_key)
            path = Path(item.path)
            if not path.is_file() or UPLOAD_ROOT.resolve() not in path.resolve().parents or path.stat().st_size > 30 * 1024 * 1024:
                continue
            try:
                reading = await asyncio.to_thread(read_attachment, path, item.original_name)
            except Exception:
                logger.exception("agent attachment parse failed: attachment_id=%s", item.id)
                document_readings.append({"attachment_id": item.id, "file_name": item.original_name, "category": item.category, "status": "parse_failed"})
                continue
            text_content = reading.text[:remaining_chars]
            remaining_chars -= len(text_content)
            document_readings.append({
                "attachment_id": item.id,
                "file_name": item.original_name,
                "category": item.category,
                "status": reading.status,
                "page_count": reading.page_count,
                "content": text_content,
            })
            if reading.images:
                document_visual_groups.append((item, reading.images))
        document_visual_count = 0
        for page_index in range(4):
            for item, visual_pages in document_visual_groups:
                if page_index >= len(visual_pages) or document_visual_count >= 12:
                    continue
                visual = visual_pages[page_index]
                data_url = visual.get("data_url", "")
                if not data_url or visual_bytes + len(data_url) > 12 * 1024 * 1024:
                    continue
                visual_bytes += len(data_url)
                document_visual_count += 1
                images.append({
                    "id": f"document:{item.id}:page:{visual.get('page', '1')}",
                    "name": f"{item.original_name}（第 {visual.get('page', '1')} 页）",
                    "mime_type": visual.get("mime_type", "image/jpeg"),
                    "data_url": data_url,
                    "page": visual.get("page", "1"),
                })
    context["document_readings"] = document_readings
    invoke_arguments = {
        "case_id": case_id,
        "operator": identity["username"],
        "message": body.message,
        "case_snapshot": context,
        "proposed_action": proposed_action,
        "images": images,
        "skill_override": selected_skill,
    }
    if body.stream:
        async def stream_events():
            async for event in case_agent_runtime.invoke_stream(**invoke_arguments):
                yield json.dumps(event, ensure_ascii=False, default=str) + "\n"

        return StreamingResponse(
            stream_events(), media_type="application/x-ndjson",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
        )
    try:
        return await case_agent_runtime.invoke(
            **invoke_arguments,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="案件智能体调用失败") from exc


@router.post(f"{settings.api_prefix}/case-spaces/{{case_id}}/agent/actions/{{action_id}}/decision")
async def decide_case_agent_action(
    case_id: int,
    action_id: str,
    body: CaseAgentDecisionInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.documents import (
        _execute_case_agent_action,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_case_agent_action_access,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    context = await get_case_space_context(case_id, identity, db)
    capabilities = context.get("capabilities") or {}
    try:
        state = await case_agent_runtime.get_state(case_id, identity["username"])
        action = next((item for item in state.get("pending_actions") or [] if item.get("id") == action_id), None)
        if not action:
            raise KeyError(action_id)
        if action.get("status") != "pending":
            raise ValueError("action_already_decided")
        _require_case_agent_action_access(str(action.get("type") or ""), capabilities)
        execution_result = None
        if body.decision == "approved":
            execution_result = await _execute_case_agent_action(case_record, action, identity, db, context)
        return await case_agent_runtime.decide_action(
            case_id=case_id,
            action_id=action_id,
            decision=body.decision,
            operator=identity["username"],
            comment=body.comment,
            execution_result=execution_result,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="待审批操作不存在") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="该操作已经完成审批") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="案件智能体尚未就绪") from exc


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/assign")
async def assign_case(case_id: int, body: CaseAssignmentInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_team_payload, _resolve_active_case_people,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _record_dict,
    )
    from app.core.tasks import (
        _add_task_message_notifications, _next_manual_task_serial,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    previous = case_record.status
    handling_lawyers, handling_usernames = await _resolve_active_case_people(body.handling_lawyers, db, field_name="经办律师")
    if not handling_lawyers and not body.hearing_lawyer.strip():
        raise HTTPException(status_code=422, detail="请至少分配一名有效经办律师")
    assistant_values, assistant_usernames = await _resolve_active_case_people([body.assistant] if body.assistant.strip() else [], db, field_name="律师助理")
    hearing_values, _ = await _resolve_active_case_people([body.hearing_lawyer], db, field_name="开庭律师")
    manager_values, _ = await _resolve_active_case_people([body.customer_manager] if body.customer_manager.strip() else [], db, field_name="客户管理人")
    assistant = assistant_values[0] if assistant_values else ""
    assistant_username = assistant_usernames[0] if assistant_usernames else ""
    case_data = _case_team_payload({
        **(case_record.data or {}), "customer_manager": manager_values[0] if manager_values else "",
        "hearing_lawyer": hearing_values[0],
    }, handling_lawyers, handling_usernames, assistant, assistant_username)
    case_record.data = case_data
    if case_record.status == "新案待分配":
        case_record.status = "文书准备"
    db.add(WorkflowEvent(record_id=case_record.id, action="案件人员分配", from_status=previous, to_status=case_record.status, operator=identity["username"], comment=f"开庭律师：{case_data['hearing_lawyer']}；经办律师：{','.join(handling_lawyers)}；助理：{assistant}。{body.comment}"))
    notary_id = int(case_data.get("notary_id") or 0)
    if notary_id and not case_data.get("notary_handoff_task_id"):
        notary = await db.get(BusinessRecord, notary_id)
        if notary:
            notary_data = notary.data or {}; scanner = str(notary_data.get("scan_uploaded_by") or notary.owner or identity["username"]).strip(); recipient = (assistant_username or next(iter(handling_usernames), "") or case_data["hearing_lawyer"])
            task = BusinessRecord(module="task", serial_no=await _next_manual_task_serial(db), title=f"公证书及公证费发票原件交接—{case_record.serial_no}", customer=case_record.customer, status="待接收", owner=scanner, department=case_record.department, description=f"扫描文员向案件文书人员 {recipient} 交接公证书及公证费发票原件", data={"deadline": str(date.today() + timedelta(days=5)), "priority": "紧急", "source": "案件任务", "creation_mode": "自动", "task_type": "自动任务", "initiator": recipient, "collaborators": [recipient] if recipient != scanner else [], "case_no": case_record.serial_no, "case_id": case_record.id, "notary_id": notary.id, "notary_no": notary.serial_no, "auto_task_type": "notary_original_handoff", "handoff_recipient": recipient, "system_created_by": identity["username"]})
            db.add(task); await db.flush(); case_record.data = {**case_record.data, "notary_handoff_task_id": task.id}; notary.data = {**notary_data, "handoff_task_id": task.id, "handoff_recipient": recipient}
            await _add_task_message_notifications(task, WorkflowEvent(record_id=task.id, action="系统生成原件交接任务", to_status="待接收", operator="system", comment=f"扫描文员 {scanner} 向 {recipient} 交接；来源案件 {case_record.serial_no}"), db, content="任务已分派.")
            db.add(WorkflowEvent(record_id=case_record.id, action="生成公证原件交接任务", from_status=case_record.status, to_status=case_record.status, operator="system", comment=f"任务 {task.serial_no}；负责人 {scanner}；接收人 {recipient}"))
    await db.commit()
    await db.refresh(case_record)
    return _record_dict(case_record)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/hearing-lawyer")
async def update_case_hearing_lawyer(
    case_id: int,
    body: CaseHearingLawyerInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Update the hearing lawyer independently from the creation wizard.

    The legacy action writes only the hearing-lawyer fields. Historical cases
    may retain an incomplete creation-step marker, which must not block this
    detail-page maintenance operation.
    """
    from app.core.cases import (
        _resolve_active_case_people,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
        raise HTTPException(status_code=409, detail="归档中的案件不能修改开庭律师")

    hearing_values, hearing_usernames = await _resolve_active_case_people(
        [body.hearing_lawyer], db, field_name="开庭律师",
    )
    case_data = dict(case_record.data or {})
    previous_hearing_lawyer = str(case_data.get("hearing_lawyer") or "")
    case_data["hearing_lawyer"] = hearing_values[0]
    case_data["hearing_lawyer_username"] = hearing_usernames[0]
    case_record.data = case_data
    db.add(WorkflowEvent(
        record_id=case_record.id,
        action="修改开庭律师",
        from_status=case_record.status,
        to_status=case_record.status,
        operator=identity["username"],
        comment=(
            f"开庭律师：{previous_hearing_lawyer or '未设置'} → {hearing_values[0]}"
            + (f"；说明：{body.comment.strip()}" if body.comment.strip() else "")
        ),
    ))
    await db.commit()
    await db.refresh(case_record)
    return _record_dict(case_record)


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/tasks")
async def list_case_tasks(
    case_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200),
    scope: str = Query("", pattern="^(|case|customer)$"),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
    is_vip: bool | None = None,
):
    from app.core.formatters import (
        _task_display_dict,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    link_condition = or_(
        BusinessRecord.data["case_id"].as_integer() == case_record.id,
        BusinessRecord.data["case_no"].as_string() == case_record.serial_no,
        BusinessRecord.data.cast(String).contains(f'"{case_record.serial_no}"'),
    )
    base_task_condition = [BusinessRecord.module == "task", link_condition]
    task_condition = list(base_task_condition)
    if identity.get("role") != "admin":
        username_token = f'"{identity["username"]}"'
        task_condition.append(or_(
            BusinessRecord.owner == identity["username"],
            BusinessRecord.data["initiator"].as_string() == identity["username"],
            BusinessRecord.data["collaborators"].as_string().contains(username_token),
        ))
    visible_total = int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(*task_condition)) or 0)
    if scope == "customer":
        task_condition.append(BusinessRecord.data["source"].as_string() == "客户任务")
    elif scope == "case":
        task_condition.append(func.coalesce(BusinessRecord.data["source"].as_string(), "") != "客户任务")
    if is_vip is True:
        task_condition.append(BusinessRecord.data["is_vip"].as_boolean().is_(True))
    elif is_vip is False:
        task_condition.append(or_(
            BusinessRecord.data["is_vip"].as_boolean().is_(False),
            BusinessRecord.data["is_vip"].as_boolean().is_(None),
        ))
    total = int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(*task_condition)) or 0)
    if identity.get("role") != "admin" and visible_total == 0:
        all_linked = int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
            BusinessRecord.module == "task", link_condition,
        )) or 0)
        if all_linked:
            raise HTTPException(status_code=403, detail="只有任务参与人可以查看案件任务")
    deadline_expr = func.coalesce(
        BusinessRecord.data["deadline"].as_string(),
        BusinessRecord.data["task_end_time"].as_string(),
        BusinessRecord.data["TaskEndTime"].as_string(),
    )
    rows = list((await db.scalars(
        select(BusinessRecord).where(*task_condition)
        .order_by(deadline_expr.desc(), BusinessRecord.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).all())
    pages = (total + page_size - 1) // page_size if total else 0
    items = [await _task_display_dict(item, db) for item in rows]
    for item in items:
        if item.get("workflow_status") in {"待接收", "待处理"} and item.get("source") == "案件任务":
            item["status"] = "进行中"
    return {
        "case": _record_dict(case_record),
        "items": items,
        "total": total, "page": page, "page_size": page_size, "pages": pages,
    }


@router.post(f"{settings.api_prefix}/cases/tasks/finished")
async def finish_case_tasks(
    body: CaseTaskFinishedInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Atomically implement legacy CaseTaskController.Finished(caseIds).

    The endpoint intentionally accepts case_ids only.  It resolves every linked
    task, checks case and task participation/status for the complete selection,
    then writes all status/events/notifications in one transaction.
    """
    from app.core.permissions import (
        _record_scope_conditions, _require_case_progress_write_access,
    )
    from app.core.tasks import (
        _add_task_message_notifications, _is_task_participant, _task_dict,
    )
    case_ids = list(dict.fromkeys(int(value) for value in body.case_ids))
    scope = await _record_scope_conditions(identity, db)
    cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case", BusinessRecord.id.in_(case_ids), *scope,
    ))).all())
    by_id = {case_record.id: case_record for case_record in cases}
    missing = [case_id for case_id in case_ids if case_id not in by_id]
    if missing:
        raise HTTPException(status_code=404, detail=f"未找到案件或当前账号无权查看: {','.join(str(value) for value in missing)}")
    for case_record in cases:
        await _require_case_progress_write_access(case_record, identity, db)

    links = [
        or_(BusinessRecord.data["case_id"].as_integer() == case_record.id, BusinessRecord.data["case_no"].as_string() == case_record.serial_no)
        for case_record in cases
    ]
    all_tasks = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "task", or_(*links),
    ))).all()) if links else []
    grouped: dict[int, list[BusinessRecord]] = {case_record.id: [] for case_record in cases}
    for task in all_tasks:
        data = task.data or {}
        for case_record in cases:
            if str(data.get("case_id") or "") == str(case_record.id) or str(data.get("case_no") or "") == case_record.serial_no:
                grouped[case_record.id].append(task)
                break
    for case_record in cases:
        linked = grouped[case_record.id]
        if not linked:
            raise HTTPException(status_code=409, detail="案件没有可完成的任务")
        for task in linked:
            if not _is_task_participant(task, identity):
                raise HTTPException(status_code=403, detail="只有任务参与人可以结束案件任务")
            if task.status != "处理中":
                raise HTTPException(status_code=409, detail="存在当前状态不能结束的任务")

    try:
        updated: list[BusinessRecord] = []
        comment = body.comment.strip()
        for case_record in cases:
            for task in grouped[case_record.id]:
                previous = task.status
                task.status = "已完成"
                task.data = {
                    **(task.data or {}),
                    "completion_submitted_at": datetime.now().isoformat(timespec="seconds"),
                    "completion_comment": comment,
                    "completion_case_id": case_record.id,
                }
                await _add_task_message_notifications(
                    task,
                    WorkflowEvent(
                        record_id=task.id, action="案件任务批量完成", from_status=previous,
                        to_status=task.status, operator=identity["username"], comment=comment,
                    ),
                    db,
                    content="任务结束成功！",
                )
                updated.append(task)
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="标记失败！")
    for task in updated:
        await db.refresh(task)
    return {
        "message": "标记成功！", "case_ids": case_ids, "updated": len(updated),
        "items": [_task_dict(task) for task in updated],
    }


@router.post(f"{settings.api_prefix}/cases/execution-status")
async def update_case_execution_status(body: CaseExecutionStatusInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _validate_case_execution_status,
    )
    from app.core.formatters import (
        _normalize_case_numbers,
    )
    from app.core.permissions import (
        _record_scope_conditions, _require_case_progress_write_access,
    )
    from app.core.system import (
        _record_dict,
    )
    case_nos = _normalize_case_numbers(body.case_nos)
    if not case_nos:
        raise HTTPException(status_code=422, detail="至少选择一件案件")
    execution_status = _validate_case_execution_status(body.execution_status)
    scope = await _record_scope_conditions(identity, db)
    # The legacy case_nos.in_(case_nos) filter is represented by the serial_no column below.
    all_cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case", BusinessRecord.serial_no.in_(case_nos), *scope,
    ))).all())
    by_no = {case_record.serial_no: case_record for case_record in all_cases}
    missing = [case_no for case_no in case_nos if case_no not in by_no]
    if missing:
        raise HTTPException(status_code=404, detail=f"未找到案件或当前账号无权查看：{','.join(missing)}")
    for case_record in all_cases:
        await _require_case_progress_write_access(case_record, identity, db)
    for case_record in all_cases:
        previous_status = str((case_record.data or {}).get("execution_status") or "")
        case_record.data = {**(case_record.data or {}), "execution_status": execution_status}
        db.add(WorkflowEvent(
            record_id=case_record.id, action="修改案件执行状态", from_status=case_record.status,
            to_status=case_record.status, operator=identity["username"],
            comment=body.comment.strip() or f"{previous_status or '未设置'} → {execution_status}",
        ))
    await db.commit()
    for case_record in all_cases:
        await db.refresh(case_record)
    return {
        "message": "修改成功！", "updated": len(all_cases), "case_nos": case_nos,
        "execution_status": execution_status, "items": [_record_dict(case_record) for case_record in all_cases],
    }


@router.get(f"{settings.api_prefix}/cases/phases")
async def list_case_phases(case_type: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_phase_option, _case_type_parameter_for_value, _phase_is_builtin_for_case_type,
    )
    from app.core.permissions import (
        _require_record_module_menu,
    )
    await _require_record_module_menu("case", identity, db, action="查看")
    phases = list((await db.scalars(select(SystemParameter).where(
        SystemParameter.category == "case_phase", SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.sort_order, SystemParameter.id))).all())
    case_type_parameter = await _case_type_parameter_for_value(case_type, db)
    if case_type_parameter:
        related_ids = set((await db.scalars(select(CaseTypeCasePhaseRelation.case_phase_id).where(
            CaseTypeCasePhaseRelation.case_type_id == case_type_parameter.id,
        ))).all())
        builtin_ids = {phase.id for phase in phases if _phase_is_builtin_for_case_type(phase, case_type_parameter)}
        if related_ids or builtin_ids:
            phases = [phase for phase in phases if phase.id in related_ids or phase.id in builtin_ids]
    return {"items": [_case_phase_option(item) for item in phases]}


@router.post(f"{settings.api_prefix}/cases/phase-change")
async def update_case_phase(body: CasePhaseChangeInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_phase_is_allowed, _resolve_case_phase,
    )
    from app.core.formatters import (
        _normalize_case_numbers,
    )
    from app.core.permissions import (
        _record_scope_conditions, _require_case_phase_change_access,
    )
    from app.core.system import (
        _record_dict,
    )
    case_nos = _normalize_case_numbers(body.case_nos)
    if not case_nos:
        raise HTTPException(status_code=422, detail="至少选择一件案件")
    phase = await _resolve_case_phase(body, db)
    scope = await _record_scope_conditions(identity, db)
    # Preflight every selected case before changing any record, matching the legacy batch contract.
    all_cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case", BusinessRecord.serial_no.in_(case_nos), *scope,
    ))).all())
    by_no = {case_record.serial_no: case_record for case_record in all_cases}
    missing = [case_no for case_no in case_nos if case_no not in by_no]
    if missing:
        raise HTTPException(status_code=404, detail=f"未找到案件或当前账号无权查看：{','.join(missing)}")
    for case_record in all_cases:
        if case_record.status == "已合并":
            raise HTTPException(status_code=409, detail="已合并案件不能修改案件阶段")
        await _require_case_phase_change_access(case_record, identity, db)
        case_data = case_record.data or {}
        if not await _case_phase_is_allowed(str(case_data.get("case_type") or ""), phase["id"], db):
            raise HTTPException(status_code=422, detail=f"案件 {case_record.serial_no} 的类型不允许使用阶段“{phase['name']}”")
        if int(case_data.get("case_phase_id") or 0) == phase["id"] or case_record.status == phase["canonical_name"]:
            raise HTTPException(status_code=409, detail="当前案件已处于所选阶段")
    try:
        changed_at = datetime.now().isoformat(timespec="seconds")
        for case_record in all_cases:
            previous_status = case_record.status
            case_record.status = phase["canonical_name"]
            case_record.data = {
                **(case_record.data or {}),
                "case_phase_id": phase["id"], "case_phase_code": phase["code"],
                "case_phase_name": phase["name"], "phase_changed_at": changed_at,
            }
            db.add(WorkflowEvent(
                record_id=case_record.id, action="修改案件阶段", from_status=previous_status,
                to_status=case_record.status, operator=identity["username"],
                comment=f"{phase['name']}（{phase['id']}）" + (f"｜{body.comment.strip()}" if body.comment.strip() else ""),
            ))
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="修改失败！")
    for case_record in all_cases:
        await db.refresh(case_record)
    return {
        "message": "修改成功！", "updated": len(all_cases), "case_nos": case_nos,
        "phase": phase, "items": [_record_dict(case_record) for case_record in all_cases],
    }


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/progress")
async def update_case_progress(case_id: int, body: CaseProgressInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _require_case_progress_write_access,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db); await _require_case_progress_write_access(case_record, identity, db)
    if case_record.status in {"等待公证书", "等待审核公证书", "待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}: raise HTTPException(status_code=409, detail="当前案件阶段不能登记诉讼进展")
    values = body.model_dump()
    for key, value in list(values.items()):
        if isinstance(value, date):
            values[key] = str(value)
    progress_keys = [
        "first_instance_court", "first_instance_case_no", "courtroom", "judge", "clerk", "judgment_date", "judgment_document_no",
        "second_instance_court", "second_instance_case_no", "first_court_name", "first_court_case_no", "second_court_name", "second_court_case_no",
        "execution_court_name", "execution_court_case_no", "retrial_court_name", "retrial_court_case_no",
        "first_court_courtroom", "first_court_judge", "first_court_clerk", "first_court_filing_date", "first_court_hearing_date", "first_court_judgment_date",
        "second_court_courtroom", "second_court_judge", "second_court_clerk", "second_court_filing_date", "second_court_hearing_date", "second_court_judgment_date",
        "execution_court_courtroom", "execution_court_judge", "execution_court_clerk", "execution_court_filing_date", "execution_court_hearing_date", "execution_court_judgment_date",
        "retrial_court_courtroom", "retrial_court_judge", "retrial_court_clerk", "retrial_court_filing_date", "retrial_court_hearing_date", "retrial_court_judgment_date",
    ]
    if not any(values.get(key) for key in progress_keys): raise HTTPException(status_code=422, detail="请至少填写一项案件进展信息")
    previous = case_record.status; target = previous
    if body.retrial_court_name.strip() or body.retrial_court_case_no.strip(): target = "再审"
    elif body.execution_court_name.strip() or body.execution_court_case_no.strip(): target = "执行"
    elif body.second_instance_case_no.strip() or body.second_court_name.strip() or body.second_court_case_no.strip(): target = "二审"
    elif body.judgment_date or body.judgment_document_no.strip(): target = "待上诉"
    elif body.first_instance_case_no.strip(): target = "一审立案受理"
    stage_rank = {"新案待分配": 0, "文书准备": 1, "一审立案受理": 2, "一审准备开庭": 3, "待上诉": 4, "二审": 5, "再审": 6, "执行": 7}
    if stage_rank.get(target, -1) < stage_rank.get(previous, -1): target = previous
    canonical_stage = "再审" if (body.retrial_court_name.strip() or body.retrial_court_case_no.strip()) else "执行" if (body.execution_court_name.strip() or body.execution_court_case_no.strip()) else "判决" if (body.judgment_date or body.judgment_document_no.strip()) else "审理" if (body.second_instance_case_no.strip() or body.second_court_name.strip() or body.second_court_case_no.strip()) else "立案"
    submitted_fields = body.model_fields_set
    merged_progress = {
        **(case_record.data or {}),
        **{
            key: value.strip() if isinstance(value, str) else value
            for key, value in values.items()
            if key != "comment" and key in submitted_fields
        },
        "business_stage": canonical_stage,
    }
    # Keep the legacy progress aliases and the detail-page canonical fields in sync.
    # Older cases use first_instance_court/second_instance_court while the detail
    # view reads first_court_name/second_court_name.
    if body.first_instance_court.strip():
        merged_progress["first_court_name"] = body.first_instance_court.strip()
        merged_progress["court"] = body.first_instance_court.strip()
    if body.first_instance_case_no.strip():
        merged_progress["first_court_case_no"] = body.first_instance_case_no.strip()
    if body.first_court_name.strip():
        merged_progress["first_instance_court"] = body.first_court_name.strip()
        merged_progress["court"] = body.first_court_name.strip()
    if body.second_instance_court.strip():
        merged_progress["second_court_name"] = body.second_instance_court.strip()
    if body.second_instance_case_no.strip():
        merged_progress["second_court_case_no"] = body.second_instance_case_no.strip()
    if body.second_court_name.strip():
        merged_progress["second_instance_court"] = body.second_court_name.strip()
    if target != previous:
        merged_progress["phase_changed_at"] = datetime.now().isoformat(timespec="seconds")
    case_record.status = target; case_record.data = merged_progress
    db.add(WorkflowEvent(record_id=case_record.id, action="登记案件诉讼进展", from_status=previous, to_status=target, operator=identity["username"], comment=body.comment or "根据法院案号、裁判日期等案件要素自动推进阶段"))
    await db.commit(); await db.refresh(case_record); return _record_dict(case_record)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/court-info")
async def update_case_court_info(case_id: int, body: CaseCourtInfoInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Persist one or more court-dialog fields without changing case workflow state."""
    from app.core.permissions import (
        _ensure_record_module, _require_case_court_info_write_access,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_court_info_write_access(case_record, identity, db)
    submitted_fields = set(body.model_fields_set) - {"comment"}
    if not submitted_fields:
        raise HTTPException(status_code=422, detail="请至少提交一项法院信息")
    values = body.model_dump()
    payload = {
        key: (str(value) if isinstance(value, date) else value.strip() if isinstance(value, str) else value)
        for key, value in values.items()
        if key in submitted_fields
    }
    merged = {**(case_record.data or {}), **payload}
    # Keep old and current field names synchronized, including deliberate clears.
    if "first_instance_court" in payload:
        merged["first_court_name"] = payload["first_instance_court"]
        merged["court"] = payload["first_instance_court"]
    if "first_instance_case_no" in payload:
        merged["first_court_case_no"] = payload["first_instance_case_no"]
    if "first_court_name" in payload:
        merged["first_instance_court"] = payload["first_court_name"]
        merged["court"] = payload["first_court_name"]
    if "first_court_case_no" in payload:
        merged["first_instance_case_no"] = payload["first_court_case_no"]
    if "second_instance_court" in payload:
        merged["second_court_name"] = payload["second_instance_court"]
    if "second_instance_case_no" in payload:
        merged["second_court_case_no"] = payload["second_instance_case_no"]
    if "second_court_name" in payload:
        merged["second_instance_court"] = payload["second_court_name"]
    if "second_court_case_no" in payload:
        merged["second_instance_case_no"] = payload["second_court_case_no"]
    case_record.data = merged
    db.add(WorkflowEvent(
        record_id=case_record.id,
        action="修改法院信息",
        from_status=case_record.status,
        to_status=case_record.status,
        operator=identity["username"],
        comment=body.comment.strip() or "直接维护法院信息",
    ))
    await db.commit()
    await db.refresh(case_record)
    return _record_dict(case_record)


@router.get(f"{settings.api_prefix}/hearings")
async def list_hearings(
    date_from: date | None = None, date_to: date | None = None,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.cases import (
        _hearing_dict,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    conditions = []
    if date_from:
        conditions.append(HearingSchedule.hearing_date >= date_from)
    if date_to:
        conditions.append(HearingSchedule.hearing_date <= date_to)
    schedules = (await db.scalars(select(HearingSchedule).where(*conditions).order_by(HearingSchedule.hearing_date, HearingSchedule.hearing_time))).all()
    case_ids = {item.case_record_id for item in schedules}
    cases = {item.id: item for item in (await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(case_ids), *(await _record_scope_conditions(identity, db))))).all()} if case_ids else {}
    items = [_hearing_dict(item, cases[item.case_record_id]) for item in schedules if item.case_record_id in cases]
    return {"items": items, "total": len(items)}


@router.post(f"{settings.api_prefix}/hearings", status_code=status.HTTP_201_CREATED)
async def create_hearing(body: HearingInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _hearing_dict,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_case_progress_write_access,
    )
    case_record = await _ensure_record_module(body.case_record_id, "case", identity, db)
    await _require_case_progress_write_access(case_record, identity, db)
    item = HearingSchedule(**body.model_dump(), status="已排期")
    db.add(item)
    await db.flush()
    previous_status = case_record.status
    case_record.data = {**(case_record.data or {}), "court": body.court, "next_hearing_date": str(body.hearing_date), "next_hearing_time": body.hearing_time, "hearing_lawyer": body.hearing_lawyer, "business_stage": "审理"}
    if body.hearing_type.startswith("二审"):
        case_record.status = "二审"
    elif case_record.status in {"新案待分配", "文书准备", "一审立案受理"}:
        case_record.status = "一审准备开庭"
    db.add(WorkflowEvent(record_id=case_record.id, action="新增开庭排期并推进阶段", from_status=previous_status, to_status=case_record.status, operator=identity["username"], comment=f"{body.hearing_date} {body.hearing_time} {body.court} {body.courtroom}"))
    await db.commit()
    await db.refresh(item)
    return _hearing_dict(item, case_record)


@router.delete(f"{settings.api_prefix}/hearings/{{hearing_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hearing(hearing_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    if identity["role"] != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可删除排期")
    item = await db.get(HearingSchedule, hearing_id)
    if not item:
        raise HTTPException(status_code=404, detail="排期不存在")
    await db.delete(item)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/hearing-sms/outbox")
async def hearing_sms_outbox(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _record_dict,
    )
    from app.core.tasks import (
        _apply_hearing_sms_reminders,
    )
    if identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以查看短信发送记录")
    await _apply_hearing_sms_reminders(db)
    items = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "sms", *(await _record_scope_conditions(identity, db))).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()).limit(200))).all())
    return {"items": [_record_dict(item) for item in items], "total": len(items), "provider_configured": bool(settings.sms_webhook_url)}


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/archive-readiness")
async def archive_readiness(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_archive_checks,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    data = case_record.data or {}
    checks = await _case_archive_checks(case_record, db)
    await db.commit()
    return {"case_id": case_id, "case_no": case_record.serial_no, "status": case_record.status, "checks": checks, "archive_no": data.get("archive_no", ""), "paper_archive_location": data.get("paper_archive_location", ""), "paper_volume_count": data.get("paper_volume_count", 1), "archive_type": data.get("archive_type", "normal"), "archive_reject_reason": data.get("archive_reject_reason", ""), "ready": all(checks.values())}


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/close")
async def close_case_for_archive(case_id: int, body: TaskActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _record_links_to_case,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}: raise HTTPException(status_code=409, detail="归档审核中或已归档案件不能重复办结")
    if (case_record.data or {}).get("case_closed_at"): raise HTTPException(status_code=409, detail="案件已经办理办结确认")
    tasks = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "task"))).all()
    active_tasks = [
        item for item in tasks
        if _record_links_to_case(item, case_record)
        and item.status not in {"已完成", "已验收", "已停止", "已撤回", "已拒绝"}
    ]
    if active_tasks: raise HTTPException(status_code=409, detail=f"仍有 {len(active_tasks)} 项案件任务未办结，不能确认案件办结")
    now = datetime.now(timezone.utc)
    case_record.data = {**(case_record.data or {}), "case_closed": True, "case_closed_at": now.isoformat(), "case_closed_by": identity["username"], "case_close_comment": body.comment.strip(), "business_stage": "结案"}
    db.add(WorkflowEvent(record_id=case_record.id, action="确认案件办结", from_status=case_record.status, to_status=case_record.status, operator=identity["username"], comment=body.comment.strip()))
    await db.commit(); await db.refresh(case_record)
    return await _record_dict_for_identity(case_record, identity, db)


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/archive")
async def archive_case(case_id: int, body: ArchiveCheckInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_archive_checks,
    )
    from app.core.legacy_sync import (
        _sync_legacy_case,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    if case_record.status == "已归档": raise HTTPException(status_code=409, detail="案件已经归档")
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核"} and body.submit: raise HTTPException(status_code=409, detail="案件已提交归档审核，请等待审核")
    checks = await _case_archive_checks(case_record, db)
    archive_type = body.archive_type if body.archive_type in {"normal", "deficit"} else "normal"
    if body.submit and archive_type == "deficit" and not body.comment.strip():
        raise HTTPException(status_code=422, detail="亏损归档必须填写亏损原因")
    details = {"archive_no": body.archive_no.strip(), "paper_archive_location": body.paper_archive_location.strip(), "paper_volume_count": body.paper_volume_count, "archive_type": archive_type}
    case_record.data = {**(case_record.data or {}), **checks, **details}
    if body.submit and archive_type == "normal" and not checks["fees_settled"]:
        raise HTTPException(status_code=409, detail="正常归档申请前请先结清案件费用")
    previous = case_record.status
    action = "保存归档检查"
    if body.submit:
        case_record.data = {
            **(case_record.data or {}),
            "status_before_archive": previous,
            "archive_submitted_at": datetime.now().isoformat(timespec="seconds"),
            "archive_submitter": identity["username"],
            "archive_submit_comment": body.comment.strip(),
            "archive_reject_reason": "",
        }
        if archive_type == "deficit":
            case_record.status = "亏损内审"
            case_record.data = {
                **(case_record.data or {}),
                "case_phase": "亏损内审",
                "case_phase_id": 106016,
                "archive_status": "待内部审核",
                "archive_status_code": 7,
                "archive_internal_reviewer": "",
                "archive_internal_review_comment": "",
                "archive_internal_reviewed_at": None,
            }
            action = "提交亏损归档内部审核"
        else:
            case_record.status = "待归档审核"
            case_record.data = {
                **(case_record.data or {}),
                "archive_status": "待审核",
                "archive_status_code": 10,
            }
            action = "提交归档审核"
    type_label = "亏损归档" if archive_type == "deficit" else "正常归档"
    db.add(WorkflowEvent(record_id=case_record.id, action=action, from_status=previous, to_status=case_record.status, operator=identity["username"], comment=body.comment or (f"{type_label}；归档号：{details['archive_no']}；纸质卷宗：{details['paper_archive_location']}，{details['paper_volume_count']} 卷" if body.submit else f"更新{type_label}检查项")))
    await _sync_legacy_case(case_record, identity, db)
    await db.commit()
    await db.refresh(case_record)
    return {"record": _record_dict(case_record), "checks": checks, "ready": all(checks.values())}


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/archive/review")
async def review_case_archive(case_id: int, body: ArchiveReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.system import _record_dict
    try:
        await db.scalar(select(BusinessRecord).where(BusinessRecord.id == case_id).with_for_update())
        record = await _apply_case_archive_review(case_id, body, identity, db)
        await db.commit()
        await db.refresh(record)
        return _record_dict(record)
    except Exception:
        await db.rollback()
        raise


async def _apply_case_archive_review(case_id: int, body: ArchiveReviewInput, identity: dict, db: AsyncSession):
    """Apply one review inside the caller's transaction; never commit here."""
    from app.core.cases import (
        _case_archive_checks,
    )
    from app.core.legacy_sync import (
        _sync_legacy_case,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_case_action,
    )
    from app.core.system import (
        _record_dict,
    )
    await _require_case_action(identity, db, "case.archive.review")
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    if case_record.status not in {"待归档审核", "亏损内审", "亏损审核"}: raise HTTPException(status_code=409, detail="只有待归档审核案件可以审核")
    if len(body.comment.strip()) < 2:
        raise HTTPException(status_code=422, detail="审核备注至少填写两个字")
    data = dict(case_record.data or {})
    if str(data.get("archive_submitter") or "").strip() == identity["username"]:
        raise HTTPException(status_code=403, detail="归档申请人不能审核本人提交的归档申请")
    if (
        case_record.status == "亏损审核"
        and str(data.get("archive_internal_reviewer") or "").strip() == identity["username"]
    ):
        raise HTTPException(status_code=403, detail="亏损归档内审人与最终审核人必须相互独立")
    archive_type = str(data.get("archive_type") or "normal")
    if archive_type == "deficit" and case_record.status == "待归档审核" and not data.get("archive_internal_reviewed_at"):
        case_record.status = "亏损内审"
    if body.approved and case_record.status != "亏损内审" and archive_type != "deficit":
        checks = await _case_archive_checks(case_record, db)
        # The legacy workflow treats material completeness and refund status as
        # reviewer guidance. Only unsettled case fees are a hard blocker.
        if not checks["fees_settled"]:
            raise HTTPException(status_code=409, detail="案件费用未到账，不允许通过归档审核")
    previous = case_record.status
    reviewed_at = datetime.now()
    if previous == "亏损内审":
        case_record.data = {
            **data,
            "archive_internal_reviewer": identity["username"],
            "archive_internal_reviewed_at": reviewed_at.isoformat(timespec="seconds"),
            "archive_internal_review_comment": body.comment.strip(),
        }
        if body.approved:
            case_record.status = "亏损审核"
            case_record.data = {
                **(case_record.data or {}),
                "case_phase": "亏损审核",
                "case_phase_id": 106017,
                "archive_status": "待审核",
                "archive_status_code": 10,
                "archive_reject_reason": "",
            }
            action = "亏损归档内部审核通过"
        else:
            case_record.status = "亏损归档拒绝"
            case_record.data = {
                **(case_record.data or {}),
                "case_phase": "亏损归档拒绝",
                "case_phase_id": 106019,
                "archive_status": "已拒绝",
                "archive_reject_reason": body.comment.strip(),
            }
            action = "亏损归档内部审核驳回"
    elif body.approved:
        case_record.status = "亏损归档" if archive_type == "deficit" else "已归档"
        archived_at = datetime.now()
        archive_no = body.archive_no.strip() or str(data.get("archive_no") or "").strip()
        if archive_type != "deficit" and not archive_no:
            raise HTTPException(status_code=422, detail="请填写归档号")
        case_record.data = {
            **data,
            "case_phase": "亏损归档" if archive_type == "deficit" else data.get("case_phase", "已归档"),
            "case_phase_id": 106018 if archive_type == "deficit" else data.get("case_phase_id"),
            "archive_status": "审核通过",
            "archive_status_code": 20,
            "archived_at": archived_at.isoformat(timespec="seconds"),
            "archive_reviewed_at": archived_at.isoformat(timespec="seconds"),
            "archive_no": archive_no,
            "archive_reviewer": identity["username"],
            "archive_review_comment": body.comment.strip(),
            "archive_reject_reason": "",
        }
        action = "亏损归档审核通过" if archive_type == "deficit" else "归档审核通过"
    else:
        restored_status = str(data.get("status_before_archive") or "执行")
        if archive_type == "deficit":
            case_record.status = "亏损归档拒绝"
            case_record.data = {
                **data,
                "case_phase": "亏损归档拒绝",
                "case_phase_id": 106019,
                "archive_status": "已拒绝",
                "archive_reviewer": identity["username"],
                "archive_reviewed_at": reviewed_at.isoformat(timespec="seconds"),
                "archive_reject_reason": body.comment.strip(),
            }
            action = "亏损归档审核驳回"
        else:
            if restored_status in {"待归档审核", "已归档"}: restored_status = "执行"
            case_record.status = restored_status
            case_record.data = {**data, "archive_reviewer": identity["username"], "archive_reviewed_at": reviewed_at.isoformat(timespec="seconds"), "archive_reject_reason": body.comment.strip()}
            action = "归档审核驳回"
    db.add(WorkflowEvent(record_id=case_record.id, action=action, from_status=previous, to_status=case_record.status, operator=identity["username"], comment=body.comment))
    await _sync_legacy_case(case_record, identity, db)
    return case_record


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/unarchive/request")
async def request_case_unarchive(case_id: int, body: CaseUnarchiveRequestInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    if case_record.status != "已归档":
        raise HTTPException(status_code=409, detail="只有已归档案件可以申请解档")
    data = case_record.data or {}; pending = data.get("unarchive_request") or {}
    if pending.get("status") == "待审批":
        raise HTTPException(status_code=409, detail="该案件已有解档申请正在审批")
    request_data = {
        "status": "待审批", "reason": body.reason.strip(), "requested_by": identity["username"],
        "requested_at": datetime.now().isoformat(timespec="seconds"),
    }
    case_record.data = {**data, "unarchive_request": request_data}
    db.add(WorkflowEvent(record_id=case_record.id, action="提交解档申请", from_status="已归档", to_status="已归档", operator=identity["username"], comment=body.reason.strip()))
    await db.commit(); await db.refresh(case_record)
    return _record_dict(case_record)


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/unarchive/review")
async def review_case_unarchive(case_id: int, body: CaseUnarchiveReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _record_dict,
    )
    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以审批解档")
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    data = case_record.data or {}; pending = data.get("unarchive_request") or {}
    if case_record.status != "已归档" or pending.get("status") != "待审批":
        raise HTTPException(status_code=409, detail="该案件没有待审批的解档申请")
    if pending.get("requested_by") == identity["username"] and identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="解档申请人不能审批自己的申请")
    if not body.approved and not body.comment.strip():
        raise HTTPException(status_code=422, detail="驳回时必须填写原因")
    previous = case_record.status
    reviewed = {
        **pending, "status": "已通过" if body.approved else "已驳回", "reviewed_by": identity["username"],
        "reviewed_at": datetime.now().isoformat(timespec="seconds"), "review_comment": body.comment.strip(),
    }
    if body.approved:
        restored_status = str(data.get("status_before_archive") or "执行")
        if restored_status in {"已归档", "待归档审核", "待立案审批"}: restored_status = "执行"
        case_record.status = restored_status
        case_record.data = {**data, "unarchive_request": reviewed, "unarchived_at": datetime.now().isoformat(timespec="seconds"), "unarchived_by": identity["username"], "archive_locked": False}
        action = "解档审批通过"
    else:
        case_record.data = {**data, "unarchive_request": reviewed}
        action = "解档审批驳回"
    db.add(WorkflowEvent(record_id=case_record.id, action=action, from_status=previous, to_status=case_record.status, operator=identity["username"], comment=body.comment))
    await db.commit(); await db.refresh(case_record)
    return _record_dict(case_record)


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/document-folders")
async def list_case_document_folders(
    case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.documents import (
        _case_formal_document_folder_payload,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    record = await _ensure_record_module(case_id, "case", identity, db)
    return {"case_id": record.id, **(await _case_formal_document_folder_payload(record, db))}


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/document-folders", status_code=status.HTTP_201_CREATED)
async def create_case_document_folder(
    case_id: int, body: CaseDocumentFolderInput,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.documents import (
        _case_custom_document_folders,
    )
    from app.core.formatters import (
        _normalize_case_document_folder_name,
    )
    from app.core.permissions import (
        _ensure_case_document_folder_name_available, _ensure_record_module, _require_case_detail_write_access,
    )
    record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_detail_write_access(record, identity, db)
    name = _normalize_case_document_folder_name(body.name)
    await _ensure_case_document_folder_name_available(name, record, db)
    folders = [*_case_custom_document_folders(record), name]
    record.data = {**(record.data or {}), CASE_CUSTOM_DOCUMENT_FOLDERS_KEY: folders}
    db.add(WorkflowEvent(record_id=record.id, action="新增案件文档目录", from_status=record.status, to_status=record.status, operator=identity["username"], comment=name))
    await db.commit()
    return {"case_id": record.id, "folders": folders}


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/document-folders")
async def rename_case_document_folder(case_id: int, body: CaseDocumentFolderRenameInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _case_custom_document_folders,
    )
    from app.core.formatters import (
        _normalize_case_document_folder_name,
    )
    from app.core.permissions import (
        _ensure_case_document_folder_name_available, _ensure_record_module, _require_case_detail_write_access,
    )
    record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_detail_write_access(record, identity, db)
    original_name = _normalize_case_document_folder_name(body.original_name)
    name = _normalize_case_document_folder_name(body.name)
    folders = _case_custom_document_folders(record)
    if original_name not in folders:
        raise HTTPException(status_code=404, detail="自定义案件文档目录不存在")
    if name == original_name:
        return {"case_id": record.id, "folders": folders}
    await _ensure_case_document_folder_name_available(name, record, db, ignored_name=original_name)
    folders = [name if value == original_name else value for value in folders]
    record.data = {**(record.data or {}), CASE_CUSTOM_DOCUMENT_FOLDERS_KEY: folders}
    attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id == record.id, FileAttachment.category == original_name))).all())
    for attachment in attachments:
        attachment.category = name
    db.add(WorkflowEvent(record_id=record.id, action="重命名案件文档目录", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{original_name} → {name}"))
    await db.commit()
    return {"case_id": record.id, "folders": folders, "moved_files": len(attachments)}


@router.delete(f"{settings.api_prefix}/cases/{{case_id}}/document-folders")
async def delete_case_document_folder(case_id: int, body: CaseDocumentFolderInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _case_custom_document_folders,
    )
    from app.core.formatters import (
        _normalize_case_document_folder_name,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_case_detail_write_access,
    )
    record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_detail_write_access(record, identity, db)
    name = _normalize_case_document_folder_name(body.name)
    folders = _case_custom_document_folders(record)
    if name not in folders:
        raise HTTPException(status_code=404, detail="自定义案件文档目录不存在")
    has_files = await db.scalar(select(FileAttachment.id).where(FileAttachment.record_id == record.id, FileAttachment.category == name).limit(1))
    if has_files:
        raise HTTPException(status_code=409, detail="目录中已有文件，请先移动或删除文件后再删除目录")
    folders = [value for value in folders if value != name]
    record.data = {**(record.data or {}), CASE_CUSTOM_DOCUMENT_FOLDERS_KEY: folders}
    db.add(WorkflowEvent(record_id=record.id, action="删除案件文档目录", from_status=record.status, to_status=record.status, operator=identity["username"], comment=name))
    await db.commit()
    return {"case_id": record.id, "folders": folders}


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/ai-space")
async def get_case_ai_space(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _person_display_name, _user_display_map,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    record = await _ensure_record_module(case_id, "case", identity, db)
    items = list((await db.scalars(select(FileAttachment).where(
        FileAttachment.record_id == record.id,
        FileAttachment.category == AI_SPACE_CATEGORY,
    ).order_by(FileAttachment.created_at.desc(), FileAttachment.id.desc()))).all())
    uploader_users = await _user_display_map({item.uploader for item in items}, db)
    uploader_names = {username: _person_display_name(user.display_name, user.username)[0] for username, user in uploader_users.items()}
    return {
        "case_id": record.id,
        "folder": AI_SPACE_CATEGORY,
        "items": [
            {**_attachment_dict(item, record, uploader_names), "content_editable": Path(item.original_name).suffix.lower() in AI_SPACE_EDITABLE_SUFFIXES}
            for item in items
        ],
    }


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/ai-space/files", status_code=status.HTTP_201_CREATED)
async def create_case_ai_draft(
    case_id: int, body: CaseAiDraftCreateInput,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.cases import (
        _case_ai_draft_bytes, _case_ai_draft_name,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_case_attachment_upload_access,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_attachment_upload_access(record, identity, db)
    name = _case_ai_draft_name(body.name)
    content, content_type = _case_ai_draft_bytes(name, body.content)
    stored_name = f"{uuid4().hex}{Path(name).suffix.lower()}"
    target = UPLOAD_ROOT / stored_name
    target.write_bytes(content)
    try:
        item = FileAttachment(
            record_id=record.id,
            category=AI_SPACE_CATEGORY,
            original_name=name,
            stored_name=stored_name,
            content_type=content_type,
            size=len(content),
            path=str(target),
            uploader=identity["username"],
            remark="AI 生成草稿，尚未转入正式案件文档",
        )
        db.add(item)
        db.add(WorkflowEvent(
            record_id=record.id, action="新增 AI 空间草稿", from_status=record.status,
            to_status=record.status, operator=identity["username"], comment=name,
        ))
        await db.commit()
        await db.refresh(item)
    except Exception:
        await db.rollback()
        target.unlink(missing_ok=True)
        raise
    return {**_attachment_dict(item, record), "content_editable": True}


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/ai-space/files/{{attachment_id}}/content")
async def get_case_ai_draft_content(
    case_id: int, attachment_id: int,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.cases import (
        _case_ai_draft,
    )
    from app.core.formatters import (
        _case_ai_draft_text,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    record = await _ensure_record_module(case_id, "case", identity, db)
    item = await _case_ai_draft(record, attachment_id, db)
    if Path(item.original_name).suffix.lower() not in AI_SPACE_EDITABLE_SUFFIXES:
        raise HTTPException(status_code=422, detail="当前草稿格式不支持在线编辑")
    path = Path(item.path)
    if not path.is_file() or UPLOAD_ROOT.resolve() not in path.resolve().parents:
        raise HTTPException(status_code=404, detail="AI 空间草稿实体不存在")
    return {"id": item.id, "name": item.original_name, "content": _case_ai_draft_text(item, path)}


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/ai-space/files/{{attachment_id}}/content")
async def update_case_ai_draft_content(
    case_id: int, attachment_id: int, body: CaseAiDraftUpdateInput,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.cases import (
        _case_ai_draft, _case_ai_draft_bytes,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_case_detail_write_access,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_detail_write_access(record, identity, db)
    item = await _case_ai_draft(record, attachment_id, db)
    if Path(item.original_name).suffix.lower() not in AI_SPACE_EDITABLE_SUFFIXES:
        raise HTTPException(status_code=422, detail="当前草稿格式不支持在线编辑")
    path = Path(item.path)
    if not path.is_file() or UPLOAD_ROOT.resolve() not in path.resolve().parents:
        raise HTTPException(status_code=404, detail="AI 空间草稿实体不存在")
    content, content_type = _case_ai_draft_bytes(item.original_name, body.content)
    temporary = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
    temporary.write_bytes(content)
    temporary.replace(path)
    item.size = len(content)
    item.content_type = content_type
    db.add(WorkflowEvent(
        record_id=record.id, action="编辑 AI 空间草稿", from_status=record.status,
        to_status=record.status, operator=identity["username"], comment=item.original_name,
    ))
    await db.commit()
    return {**_attachment_dict(item, record), "content_editable": True}


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/ai-space/files/{{attachment_id}}/promote")
async def promote_case_ai_draft(
    case_id: int, attachment_id: int, body: CaseAiDraftPromoteInput,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.cases import (
        _case_ai_draft,
    )
    from app.core.documents import (
        _case_related_document_record, _sync_case_document_readiness, _validate_case_formal_document_category,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_case_attachment_upload_access,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_attachment_upload_access(record, identity, db)
    item = await _case_ai_draft(record, attachment_id, db)
    target_category = await _validate_case_formal_document_category(record, body.category, db)
    destination_record = record
    if target_category in {"客户文档", "合同文档"}:
        destination_module = "customer" if target_category == "客户文档" else "contract"
        destination_record = await _case_related_document_record(record, destination_module, db) or record
    item.record_id = destination_record.id
    item.category = target_category
    item.remark = f"由 AI 空间转入正式案件文档；原草稿创建人：{item.uploader}"
    db.add(WorkflowEvent(
        record_id=record.id, action="AI 草稿转入正式系统", from_status=record.status,
        to_status=record.status, operator=identity["username"],
        comment=f"{item.original_name} → {target_category}",
    ))
    await _sync_case_document_readiness(record, db)
    await db.commit()
    await db.refresh(item)
    return _attachment_dict(item, destination_record)


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/attachments/{{attachment_id}}/word-editor/content")
async def get_case_word_editor_content(
    case_id: int, attachment_id: int,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """Open a formal DOCX in the limited, format-preserving online editor."""
    from app.core.documents import (
        _acquire_case_word_editor_lock, _word_editor_blocks, _word_editor_lock_payload, _word_editor_version,
    )
    from app.core.storage import (
        _case_word_editor_attachment,
    )
    _record, item, path = await _case_word_editor_attachment(case_id, attachment_id, identity, db)
    item = await _acquire_case_word_editor_lock(item, identity, db)
    try:
        content = path.read_bytes()
        document = Document(io.BytesIO(content))
        blocks = _word_editor_blocks(document)
    except Exception as exc:
        # Do not leave a lease for a document that could not be opened.
        item.word_editor_lock_token = ""; item.word_editor_locked_by = ""; item.word_editor_lock_expires_at = None
        await db.commit()
        raise HTTPException(status_code=422, detail="DOCX 文件无法在线读取") from exc
    return {
        "id": item.id,
        "name": item.original_name,
        "content": "\n".join(block["text"] for block in blocks),
        "blocks": blocks,
        "version": _word_editor_version(content),
        **_word_editor_lock_payload(item, include_token=True),
    }


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/attachments/{{attachment_id}}/word-editor/lock")
async def acquire_case_word_editor_lock(
    case_id: int, attachment_id: int,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.documents import (
        _acquire_case_word_editor_lock, _word_editor_lock_payload,
    )
    from app.core.storage import (
        _case_word_editor_attachment,
    )
    _record, item, _path = await _case_word_editor_attachment(case_id, attachment_id, identity, db)
    item = await _acquire_case_word_editor_lock(item, identity, db)
    return {"id": item.id, **_word_editor_lock_payload(item, include_token=True)}


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/attachments/{{attachment_id}}/word-editor/lock/renew")
async def renew_case_word_editor_lock(
    case_id: int, attachment_id: int, body: CaseWordEditorLockInput,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.documents import (
        _word_editor_lock_payload, _word_editor_now,
    )
    from app.core.storage import (
        _case_word_editor_attachment,
    )
    _record, item, _path = await _case_word_editor_attachment(case_id, attachment_id, identity, db)
    now = _word_editor_now()
    result = await db.execute(update(FileAttachment).where(
        FileAttachment.id == item.id,
        FileAttachment.word_editor_lock_token == body.lock_token,
        FileAttachment.word_editor_locked_by == identity["username"],
        FileAttachment.word_editor_lock_expires_at > now,
    ).values(word_editor_lock_expires_at=now + timedelta(seconds=WORD_EDITOR_LOCK_SECONDS)).execution_options(synchronize_session=False))
    if not result.rowcount:
        await db.rollback()
        current = await db.get(FileAttachment, attachment_id)
        raise HTTPException(status_code=409, detail={"message": "Word 编辑锁已过期或已被释放，请重新打开文件", **_word_editor_lock_payload(current or item)})
    await db.commit(); await db.refresh(item)
    return {"id": item.id, **_word_editor_lock_payload(item)}


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/attachments/{{attachment_id}}/word-editor/content")
async def update_case_word_editor_content(
    case_id: int, attachment_id: int, body: CaseWordEditorSaveInput,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.documents import (
        _replace_word_editor_blocks, _word_editor_lock_payload, _word_editor_now, _word_editor_version,
    )
    from app.core.storage import (
        _attachment_storage_path, _case_word_editor_attachment,
    )
    record, item, path = await _case_word_editor_attachment(case_id, attachment_id, identity, db)
    # Rotate the lease token in one conditional UPDATE.  This gives SQLite and
    # PostgreSQL the same single-writer guarantee; a second save using the old
    # token fails before it can read or replace the file.
    now = _word_editor_now()
    next_token = secrets.token_urlsafe(48)
    lock_result = await db.execute(update(FileAttachment).where(
        FileAttachment.id == attachment_id,
        FileAttachment.record_id == record.id,
        FileAttachment.word_editor_lock_token == body.lock_token,
        FileAttachment.word_editor_locked_by == identity["username"],
        FileAttachment.word_editor_lock_expires_at > now,
    ).values(
        word_editor_lock_token=next_token,
        word_editor_lock_expires_at=now + timedelta(seconds=WORD_EDITOR_LOCK_SECONDS),
    ).execution_options(synchronize_session=False))
    if not lock_result.rowcount:
        await db.rollback()
        current = await db.get(FileAttachment, attachment_id)
        raise HTTPException(status_code=409, detail={"message": "Word 编辑锁已过期、已释放或正在保存，请重新打开", **_word_editor_lock_payload(current or item)})
    await db.refresh(item)
    path = _attachment_storage_path(item)
    if path is None:
        await db.rollback()
        raise HTTPException(status_code=404, detail="案件 Word 文件不存在")
    source = path.read_bytes()
    if not secrets.compare_digest(_word_editor_version(source), body.version):
        raise HTTPException(status_code=409, detail="Word 文件已被更新，请重新打开后再保存")
    try:
        document = Document(io.BytesIO(source))
        _replace_word_editor_blocks(document, body.blocks)
        output = io.BytesIO(); document.save(output)
        content = output.getvalue()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Word 文档保存失败，原文件未修改") from exc
    replacement_path = UPLOAD_ROOT / f"{uuid4().hex}.docx"
    try:
        replacement_path.write_bytes(content)
        # Point at a completed immutable object only after it is fully written;
        # a failed DB transaction leaves the original attachment untouched.
        item.path = str(replacement_path)
        item.stored_name = replacement_path.name
        item.size = len(content)
        item.content_type = WORD_DOCUMENT_CONTENT_TYPE
        db.add(WorkflowEvent(
            record_id=record.id, action="在线编辑案件 Word 文件", from_status=record.status,
            to_status=record.status, operator=identity["username"], comment=item.original_name,
        ))
        await db.commit()
    except Exception:
        replacement_path.unlink(missing_ok=True)
        await db.rollback()
        raise
    # The original object becomes unreferenced only after the metadata commit.
    # Do not delete an imported legacy-root source; it may be retained for audit.
    still_referenced = True
    try:
        still_referenced = bool(await db.scalar(select(FileAttachment.id).where(
            FileAttachment.id != item.id, FileAttachment.path == str(path),
        ).limit(1)))
    except SQLAlchemyError:
        # Metadata is already committed.  Retaining one old object is safer
        # than surfacing a false save failure or deleting a shared reference.
        logger.warning("Word editor saved attachment %s but could not check old-object references", item.id)
    with suppress(OSError):
        if not still_referenced and path != replacement_path and UPLOAD_ROOT.resolve() in path.resolve().parents:
            path.unlink(missing_ok=True)
    return {
        "id": item.id, "name": item.original_name, "size": item.size,
        "version": _word_editor_version(content), **_word_editor_lock_payload(item, include_token=True),
    }


@router.delete(f"{settings.api_prefix}/cases/{{case_id}}/attachments/{{attachment_id}}/word-editor/lock")
async def release_case_word_editor_lock(
    case_id: int, attachment_id: int, body: CaseWordEditorLockInput,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.documents import (
        _word_editor_lock_payload, _word_editor_now,
    )
    from app.core.storage import (
        _case_word_editor_attachment,
    )
    _record, item, _path = await _case_word_editor_attachment(case_id, attachment_id, identity, db)
    now = _word_editor_now()
    result = await db.execute(update(FileAttachment).where(
        FileAttachment.id == item.id,
        FileAttachment.word_editor_lock_token == body.lock_token,
        FileAttachment.word_editor_locked_by == identity["username"],
        FileAttachment.word_editor_lock_expires_at > now,
    ).values(word_editor_lock_token="", word_editor_locked_by="", word_editor_lock_expires_at=None).execution_options(synchronize_session=False))
    if not result.rowcount:
        await db.rollback()
        current = await db.get(FileAttachment, attachment_id)
        raise HTTPException(status_code=409, detail={"message": "Word 编辑锁已过期或已被释放", **_word_editor_lock_payload(current or item)})
    await db.commit()
    return {"released": True}


@router.post(f"{settings.api_prefix}/cases/attachments/download")
async def download_case_attachments(body: AttachmentBatchInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    attachment_ids = list(dict.fromkeys(body.attachment_ids))
    attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.id.in_(attachment_ids)))).all())
    if len(attachments) != len(attachment_ids):
        raise HTTPException(status_code=404, detail="存在已删除或不存在的案件文件")
    ordered = sorted(attachments, key=lambda item: attachment_ids.index(item.id))
    paths: list[tuple[FileAttachment, Path]] = []
    for item in ordered:
        if not item.record_id:
            raise HTTPException(status_code=422, detail="所选文件不是案件文件")
        record = await _ensure_record_module(item.record_id, "case", identity, db)
        path = Path(item.path)
        if not path.is_file() or UPLOAD_ROOT.resolve() not in path.resolve().parents:
            raise HTTPException(status_code=404, detail=f"文件 {item.original_name} 的实体不存在")
        paths.append((item, path))
    output = io.BytesIO()
    used_names: set[str] = set()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item, path in paths:
            filename = Path(item.original_name).name
            if filename in used_names:
                filename = f"{item.id}-{filename}"
            used_names.add(filename)
            archive.write(path, arcname=filename)
    output.seek(0)
    return StreamingResponse(
        output, media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="case-files-{date.today():%Y%m%d}.zip"'},
    )


@router.post(f"{settings.api_prefix}/cases/attachments/delete")
async def delete_case_attachments(body: AttachmentBatchInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _sync_case_document_readiness,
    )
    from app.core.permissions import (
        _ensure_attachment_record_visible, _ensure_case_word_editor_not_locked, _ensure_record_module, _identity_role_ids, _require_case_detail_write_access,
        _require_case_related_attachment_target,
    )
    attachment_ids = list(dict.fromkeys(body.attachment_ids))
    attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.id.in_(attachment_ids)))).all())
    if len(attachments) != len(attachment_ids):
        raise HTTPException(status_code=404, detail="存在已删除或不存在的案件文件")
    context_case = await _ensure_record_module(body.case_id, "case", identity, db) if body.case_id else None
    if context_case:
        await _require_case_detail_write_access(context_case, identity, db)
    prepared: list[tuple[FileAttachment, BusinessRecord, Path]] = []
    for item in attachments:
        if not item.record_id:
            raise HTTPException(status_code=422, detail="所选文件不是案件文件")
        if "admin" not in _identity_role_ids(identity) and item.uploader != identity["username"]:
            raise HTTPException(status_code=403, detail=f"只能删除本人上传的文件：{item.original_name}")
        record = await _ensure_attachment_record_visible(item.record_id, identity, db)
        if context_case:
            await _require_case_related_attachment_target(context_case, record)
            record = context_case
        else:
            if record.module != "case":
                raise HTTPException(status_code=422, detail="所选文件不是案件文件")
            await _require_case_detail_write_access(record, identity, db)
        prepared.append((item, record, Path(item.path)))
    affected_cases: dict[int, BusinessRecord] = {}
    for item, record, path in prepared:
        _ensure_case_word_editor_not_locked(item)
        affected_cases[record.id] = record
        await db.delete(item)
        db.add(WorkflowEvent(
            record_id=record.id, action="批量删除案件文件", from_status=record.status,
            to_status=record.status, operator=identity["username"],
            comment=f"{item.category}：{item.original_name}",
        ))
    await db.flush()
    for record in affected_cases.values():
        await _sync_case_document_readiness(record, db)
    await db.commit()
    for _, _, path in prepared:
        if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
            path.unlink()
    return {"deleted": len(prepared)}


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/attachments/{{attachment_id}}/unlock")
async def unlock_case_attachment(case_id: int, attachment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Unlock one civil case document after enforcing the case-detail write gate."""
    from app.core.permissions import (
        _ensure_record_module, _require_case_detail_write_access,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_detail_write_access(case_record, identity, db)
    if case_record.status == "已合并":
        raise HTTPException(status_code=409, detail="已合并案件不能解锁案件文件")
    attachment = await db.scalar(select(FileAttachment).where(
        FileAttachment.id == attachment_id,
        FileAttachment.record_id == case_record.id,
    ))
    if not attachment:
        raise HTTPException(status_code=404, detail="案件文件不存在或不属于当前案件")
    if not attachment.is_locked:
        raise HTTPException(status_code=409, detail="该文件未锁定，无需解锁")
    attachment.is_locked = False
    attachment.locked_at = None
    attachment.locked_by = ""
    db.add(WorkflowEvent(
        record_id=case_record.id, action="解锁民事案件文件", from_status=case_record.status,
        to_status=case_record.status, operator=identity["username"],
        comment=f"{attachment.category}｜{attachment.original_name}",
    ))
    await db.commit()
    await db.refresh(attachment)
    return _attachment_dict(attachment, case_record)


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/attachments/move")
async def move_case_attachments(case_id: int, body: CaseAttachmentMoveInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _case_custom_document_folders, _sync_case_document_readiness,
    )
    from app.core.permissions import (
        _ensure_case_word_editor_not_locked, _ensure_record_module, _require_case_detail_write_access,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_detail_write_access(case_record, identity, db)
    category = body.category.strip()
    custom_folders = set(_case_custom_document_folders(case_record))
    configured = await db.scalar(select(SystemParameter.id).where(
        SystemParameter.category == "case_file_type",
        SystemParameter.name == category,
        SystemParameter.is_active.is_(True),
    ))
    if category not in custom_folders and not configured:
        raise HTTPException(status_code=422, detail="目标案件文档目录不存在或已停用")
    attachment_ids = list(dict.fromkeys(body.attachment_ids))
    attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.id.in_(attachment_ids)))).all())
    if len(attachments) != len(attachment_ids):
        raise HTTPException(status_code=404, detail="存在已删除或不存在的案件文件")
    for item in attachments:
        if item.record_id != case_record.id:
            raise HTTPException(status_code=409, detail="客户、合同或其他案件的文件不能移动到当前案件目录")
        _ensure_case_word_editor_not_locked(item)
    for item in attachments:
        previous = item.category
        item.category = category
        db.add(WorkflowEvent(
            record_id=case_record.id, action="更改案件文档目录", from_status=case_record.status,
            to_status=case_record.status, operator=identity["username"],
            comment=f"{item.original_name}：{previous} → {category}",
        ))
    await _sync_case_document_readiness(case_record, db)
    await db.commit()
    return {"moved": len(attachments), "category": category}


@router.put(f"{settings.api_prefix}/cases/attachments/{{attachment_id}}/rename")
async def rename_case_attachment(attachment_id: int, body: CaseAttachmentRenameInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Rename only the display/download name of one case attachment; never move its stored file."""
    from app.core.permissions import (
        _ensure_case_word_editor_not_locked, _ensure_record_module, _require_case_detail_write_access,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    item = await db.get(FileAttachment, attachment_id)
    if not item or not item.record_id:
        raise HTTPException(status_code=404, detail="案件文件不存在")
    case_record = await _ensure_record_module(item.record_id, "case", identity, db)
    await _require_case_detail_write_access(case_record, identity, db)
    _ensure_case_word_editor_not_locked(item)
    requested_name = body.original_name.strip()
    if not requested_name or "/" in requested_name or "\\" in requested_name or Path(requested_name).name != requested_name or requested_name in {".", ".."}:
        raise HTTPException(status_code=422, detail="文件名不能为空，且不能包含路径")
    if Path(requested_name).suffix.lower() != Path(item.original_name).suffix.lower():
        raise HTTPException(status_code=422, detail="重命名不能修改文件扩展名")
    previous_name = item.original_name
    if requested_name == previous_name:
        return _attachment_dict(item, case_record)
    item.original_name = requested_name
    db.add(WorkflowEvent(
        record_id=case_record.id, action="重命名案件文件", from_status=case_record.status,
        to_status=case_record.status, operator=identity["username"],
        comment=f"{item.category}：{previous_name} → {requested_name}",
    ))
    await db.commit()
    await db.refresh(item)
    return _attachment_dict(item, case_record)


@router.post(f"{settings.api_prefix}/seals/applications/batch/files/delete")
async def batch_delete_seal_attachments(body: AttachmentBatchInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Delete selected draft seal files atomically, including physical-file compensation."""
    from app.core.documents import (
        _sync_seal_document_names,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    ids = list(dict.fromkeys(body.attachment_ids))
    attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.id.in_(ids)))).all())
    if len(attachments) != len(ids):
        raise HTTPException(status_code=404, detail="选中的用印附件不存在")
    by_id = {item.id: item for item in attachments}
    ordered = [by_id[item_id] for item_id in ids]
    prepared: list[tuple[FileAttachment, BusinessRecord, Path]] = []
    for item in ordered:
        if not item.record_id:
            raise HTTPException(status_code=422, detail="选中的附件未关联用印申请")
        record = await _ensure_record_module(item.record_id, "seal", identity, db)
        await _require_record_owner_or_manager(record, identity, db)
        if record.status != "草稿":
            raise HTTPException(status_code=409, detail="只有草稿用印申请可以删除用印文件")
        if item.category != "用印文件":
            raise HTTPException(status_code=422, detail="用印申请附件类型无效")
        path = Path(item.path)
        if not path.is_file() or UPLOAD_ROOT.resolve() not in path.resolve().parents:
            raise HTTPException(status_code=404, detail=f"附件文件 {item.original_name} 不存在")
        prepared.append((item, record, path))

    staged: list[tuple[Path, Path]] = []
    try:
        for item, _, path in prepared:
            staged_path = path.with_name(f".seal-delete-{uuid4().hex}-{path.name}")
            path.replace(staged_path)
            staged.append((path, staged_path))
        affected: dict[int, BusinessRecord] = {}
        for item, record, _ in prepared:
            affected[record.id] = record
            await db.delete(item)
            db.add(WorkflowEvent(record_id=record.id, action="批量删除用印文件", from_status=record.status, to_status=record.status, operator=identity["username"], comment=item.original_name))
        await db.flush()
        for record in affected.values():
            await _sync_seal_document_names(record, db)
        await db.commit()
    except Exception:
        await db.rollback()
        for original, staged_path in reversed(staged):
            if staged_path.is_file():
                staged_path.replace(original)
        raise
    for _, staged_path in staged:
        try:
            staged_path.unlink(missing_ok=True)
        except OSError:
            logger.exception("无法清理已删除的用印附件临时文件: %s", staged_path)
    return {"deleted": len(prepared), "attachment_ids": ids}


@router.get(f"{settings.api_prefix}/seals/applications")
async def list_seal_applications(view: str = "my", keyword: str = "", record_status: str = "", serial_no: str = "", applicant: str = "", date_from: date | None = None, date_to: date | None = None, case_no: str = "", contract_no: str = "", customer: str = "", use_type: str = "", file_name: str = "", page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=100), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _seal_authorization_context, _seal_record_dict,
    )
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _record_person_usernames,
    )
    if view not in {"my", "audit", "all"}: raise HTTPException(status_code=422, detail="无效的用印视图")
    scope_conditions = await _record_scope_conditions(identity, db)
    context = await _seal_authorization_context(identity, db)
    if view == "all" and not context["manage_assets"]:
        raise HTTPException(status_code=403, detail="当前账号没有印章管理权限")
    conditions = [BusinessRecord.module == "seal"]
    if view == "my": conditions.append(BusinessRecord.owner == identity["username"])
    elif view == "audit":
        if not (context["approve"] or context["reject"]):
            return {"items": [], "total": 0, "page": page, "page_size": page_size, "summary": {"total": 0, "pending": 0, "waiting_stamp": 0, "completed": 0}}
        approver = func.trim(func.coalesce(BusinessRecord.data["approver"].as_string(), ""))
        conditions.extend([
            BusinessRecord.status.in_({"待审批", "待用印", "已拒绝"}),
            or_(approver == "", approver == identity["username"]),
        ])
    else:
        conditions.extend(scope_conditions)
    if record_status: conditions.append(BusinessRecord.status == record_status)
    def text_filter(column, value: str):
        if value.strip():
            conditions.append(column.ilike(f"%{value.strip()}%"))
    text_filter(BusinessRecord.serial_no, serial_no)
    text_filter(BusinessRecord.owner, applicant)
    text_filter(BusinessRecord.customer, customer)
    text_filter(BusinessRecord.data["case_no"].as_string(), case_no)
    text_filter(BusinessRecord.data["contract_no"].as_string(), contract_no)
    text_filter(BusinessRecord.data["document_names"].as_string(), file_name)
    if use_type.strip(): conditions.append(BusinessRecord.data["use_type"].as_string() == use_type.strip())
    if date_from: conditions.append(func.date(BusinessRecord.created_at) >= date_from)
    if date_to: conditions.append(func.date(BusinessRecord.created_at) <= date_to)
    if keyword:
        like = f"%{keyword.strip()}%"
        conditions.append(or_(BusinessRecord.serial_no.ilike(like), BusinessRecord.title.ilike(like), BusinessRecord.customer.ilike(like), BusinessRecord.owner.ilike(like), BusinessRecord.data["case_no"].as_string().ilike(like), BusinessRecord.data["contract_no"].as_string().ilike(like), BusinessRecord.data["document_names"].as_string().ilike(like)))
    total = int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(*conditions)) or 0)
    rows = (await db.scalars(select(BusinessRecord).where(*conditions).order_by(BusinessRecord.updated_at.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    status_counts = dict((await db.execute(
        select(BusinessRecord.status, func.count()).where(*conditions).group_by(BusinessRecord.status)
    )).all())
    summary = {
        "total": total,
        "pending": int(status_counts.get("待审批", 0)),
        "waiting_stamp": int(status_counts.get("待用印", 0)),
        "completed": int(status_counts.get("已用印", 0)) + int(status_counts.get("已归档", 0)),
    }
    seal_usernames = set().union(*(_record_person_usernames(row) for row in rows)) if rows else set()
    users_by_username = await _user_display_map(seal_usernames, db)
    row_ids = [row.id for row in rows]
    attachments = list((await db.scalars(
        select(FileAttachment).where(
            FileAttachment.record_id.in_(row_ids),
            FileAttachment.category.in_({SEAL_APPLICATION_FILE_CATEGORY, SEAL_STAMPED_FILE_CATEGORY}),
        ).order_by(FileAttachment.record_id, FileAttachment.created_at, FileAttachment.id)
    )).all()) if row_ids else []
    attachments_by_record: dict[int, list[FileAttachment]] = {}
    for attachment in attachments:
        attachments_by_record.setdefault(attachment.record_id, []).append(attachment)
    asset_ids = {
        int((row.data or {}).get("seal_asset_id") or 0)
        for row in rows
        if int((row.data or {}).get("seal_asset_id") or 0) > 0
    }
    assets = list((await db.scalars(select(SealAsset).where(SealAsset.id.in_(asset_ids)))).all()) if asset_ids else []
    assets_by_id = {asset.id: asset for asset in assets}
    return {
        "items": [await _seal_record_dict(
            row,
            db,
            users_by_username,
            identity,
            attachments_by_record,
            assets_by_id,
            context,
        ) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "summary": summary,
    }


@router.post(f"{settings.api_prefix}/seals/applications/batch-download")
async def batch_download_seal_files(body: SealPackageDownloadInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.storage import (
        _attachment_storage_path,
    )
    record_ids = list(dict.fromkeys(body.application_ids))
    records: dict[int, BusinessRecord] = {}
    for record_id in record_ids:
        records[record_id] = await _ensure_record_module(record_id, "seal", identity, db)
    attachments = (await db.scalars(
        select(FileAttachment)
        .where(
            FileAttachment.record_id.in_(record_ids),
            FileAttachment.category.in_({SEAL_APPLICATION_FILE_CATEGORY, SEAL_STAMPED_FILE_CATEGORY}),
        )
        .order_by(FileAttachment.record_id, FileAttachment.created_at, FileAttachment.id)
    )).all()
    if not attachments:
        raise HTTPException(status_code=404, detail="所选用印申请暂无可下载附件")

    output = io.BytesIO()
    included = 0
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for attachment in attachments:
            record = records[int(attachment.record_id)]
            path = _attachment_storage_path(attachment)
            if path is None:
                continue
            safe_name = Path(str(attachment.original_name or attachment.stored_name).replace("\\", "/")).name
            safe_name = re.sub(r"[\x00-\x1f]+", "_", safe_name).strip(" .") or attachment.stored_name
            safe_serial = re.sub(r"[\\/\x00-\x1f]+", "_", record.serial_no).strip(" .") or f"seal-{record.id}"
            archive.writestr(f"{safe_serial}/{attachment.id}-{safe_name}", path.read_bytes())
            included += 1
    if not included:
        raise HTTPException(status_code=404, detail="所选附件文件不存在")
    output.seek(0)
    filename = f"seal-files-{date.today():%Y%m%d}.zip"
    return StreamingResponse(
        output,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(f"{settings.api_prefix}/seals/applications/package-download")
async def package_download_seal_files(body: SealPackageDownloadInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Compatibility alias for callers that used the earlier package endpoint."""
    return await batch_download_seal_files(body, identity, db)


@router.post(f"{settings.api_prefix}/seals/applications", status_code=status.HTTP_201_CREATED)
async def create_seal_application(body: SealApplicationInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
            _next_seal_application_serial, _seal_record_dict, _validated_seal_relations,
        )
    from app.core.legacy_sync import (
            _sync_legacy_official_document,
        )
    from app.core.permissions import (
            _require_seal_base_action,
        )
    from app.core.storage import (
            _copy_seal_source_attachments, _resolve_seal_source_attachment_ids,
        )
    await _require_seal_base_action(identity, db, "apply")
    asset = await db.get(SealAsset, body.seal_asset_id)
    if not asset: raise HTTPException(status_code=404, detail="印章不存在")
    if asset.status != "可用": raise HTTPException(status_code=409, detail=f"印章当前状态为“{asset.status}”，不能申请")
    seal_types = list(dict.fromkeys([asset.seal_type, *body.seal_types]))
    if any(item not in REQUIRED_SEAL_TYPES for item in seal_types):
        raise HTTPException(status_code=422, detail="印章类型不在系统允许范围内")
    case_no, contract_no, customer, use_type, case_record_id, contract_record_id, customer_record_id = await _validated_seal_relations(body, identity, db)
    serial = await _next_seal_application_serial(db)
    item = BusinessRecord(module="seal", serial_no=serial, title=body.title, customer=customer, status="草稿", owner=identity["username"], description=body.description, data={"case_record_id": case_record_id, "case_no": case_no, "contract_record_id": contract_record_id, "contract_no": contract_no, "use_type": use_type, "seal_asset_id": body.seal_asset_id, "seal_type": asset.seal_type, "seal_name": asset.name, "seal_types": seal_types, "copies": body.copies, "print_quantity": body.print_quantity if body.print_quantity is not None else body.copies, "remark": body.remark.strip(), "purpose": body.purpose, "use_date": str(body.use_date), "delivery_method": body.delivery_method, "is_electronic_seal": body.is_electronic_seal, "is_offline_print": body.is_offline_print, "document_names": body.document_names})
    copied_targets: list[Path] = []
    source_attachment_ids = await _resolve_seal_source_attachment_ids(
        body, case_no, contract_no, case_record_id, contract_record_id, customer_record_id, identity, db
    )
    # FileAttachment copies are created inside the same transaction as the draft.
    try:
        db.add(item); await db.flush()
        copied_targets = await _copy_seal_source_attachments(item, source_attachment_ids, identity, db)
        db.add(WorkflowEvent(record_id=item.id, action="创建用印申请", to_status="草稿", operator=identity["username"], comment=f"{asset.name}｜{body.copies}份｜{body.purpose}"))
        await _sync_legacy_official_document(item, identity, db)
        await db.commit(); await db.refresh(item)
    except Exception:
        await db.rollback()
        for target in copied_targets:
            target.unlink(missing_ok=True)
        raise
    return await _seal_record_dict(item, db, identity=identity)


@router.patch(f"{settings.api_prefix}/seals/applications/{{record_id}}")
async def update_seal_application(record_id: int, body: SealApplicationInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
            _get_seal_application, _seal_record_dict, _validated_seal_relations,
        )
    from app.core.legacy_sync import (
            _sync_legacy_official_document,
        )
    from app.core.permissions import (
            _require_record_owner_or_manager, _require_seal_base_action,
        )
    item = await _get_seal_application(record_id, identity, db)
    await _require_record_owner_or_manager(item, identity, db)
    await _require_seal_base_action(identity, db, "apply")
    if item.status != "草稿": raise HTTPException(status_code=409, detail="只有草稿用印申请可以修改")
    asset = await db.get(SealAsset, body.seal_asset_id)
    if not asset: raise HTTPException(status_code=404, detail="印章不存在")
    if asset.status != "可用": raise HTTPException(status_code=409, detail=f"印章当前状态为“{asset.status}”，不能申请")
    seal_types = list(dict.fromkeys([asset.seal_type, *body.seal_types]))
    if any(item not in REQUIRED_SEAL_TYPES for item in seal_types):
        raise HTTPException(status_code=422, detail="印章类型不在系统允许范围内")
    case_no, contract_no, customer, use_type, case_record_id, contract_record_id, _customer_record_id = await _validated_seal_relations(body, identity, db)
    item.title = body.title.strip(); item.customer = customer; item.description = body.description.strip()
    existing_names = str((item.data or {}).get("document_names") or "")
    item.data = {"case_record_id": case_record_id, "case_no": case_no, "contract_record_id": contract_record_id, "contract_no": contract_no, "use_type": use_type, "seal_asset_id": body.seal_asset_id, "seal_type": asset.seal_type, "seal_name": asset.name, "seal_types": seal_types, "copies": body.copies, "print_quantity": body.print_quantity if body.print_quantity is not None else body.copies, "remark": body.remark.strip(), "purpose": body.purpose, "use_date": str(body.use_date), "delivery_method": body.delivery_method, "is_electronic_seal": body.is_electronic_seal, "is_offline_print": body.is_offline_print, "document_names": existing_names or body.document_names}
    db.add(WorkflowEvent(record_id=item.id, action="修改用印草稿", from_status="草稿", to_status="草稿", operator=identity["username"], comment=f"{asset.name}｜{body.copies}份｜{body.purpose}"))
    await _sync_legacy_official_document(item, identity, db)
    await db.commit(); await db.refresh(item)
    return await _seal_record_dict(item, db, identity=identity)


@router.delete(f"{settings.api_prefix}/seals/applications/{{record_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_seal_application(record_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Remove only an untouched draft so page-created test data can be safely cleaned."""
    from app.core.documents import (
        _get_seal_application,
    )
    from app.core.permissions import (
        _require_record_owner_or_manager,
    )
    item = await _get_seal_application(record_id, identity, db)
    await _require_record_owner_or_manager(item, identity, db)
    if item.status != "草稿":
        raise HTTPException(status_code=409, detail="只有草稿用印申请可以删除；已提交申请请按流程撤回")
    attachment_count = int(await db.scalar(select(func.count()).select_from(FileAttachment).where(FileAttachment.record_id == item.id)) or 0)
    if attachment_count:
        raise HTTPException(status_code=409, detail="草稿已有关联附件，请先通过附件流程处理后再删除")
    await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == item.id))
    await db.delete(item)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/seals/applications/{{record_id}}/files")
async def list_seal_application_files(
    record_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.documents import (
        _get_seal_application,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    record = await _get_seal_application(record_id, identity, db)
    conditions = [
        FileAttachment.record_id == record.id,
        FileAttachment.category.in_({SEAL_APPLICATION_FILE_CATEGORY, SEAL_STAMPED_FILE_CATEGORY}),
    ]
    total = int(await db.scalar(select(func.count()).select_from(FileAttachment).where(*conditions)) or 0)
    rows = (await db.scalars(
        select(FileAttachment)
        .where(*conditions)
        .order_by(FileAttachment.created_at.desc(), FileAttachment.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).all()
    return {
        "items": [_attachment_dict(item, record) for item in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
    }


@router.post(f"{settings.api_prefix}/seals/applications/{{record_id}}/files", status_code=status.HTTP_201_CREATED)
async def upload_seal_application_files(
    record_id: int,
    files: list[UploadFile] = File(...),
    remark: str = Form(""),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.documents import (
        _get_seal_application, _sync_seal_document_names,
    )
    from app.core.legacy_sync import (
        _sync_legacy_official_document,
    )
    from app.core.permissions import (
        _require_record_owner_or_manager, _require_seal_base_action,
    )
    record = await _get_seal_application(record_id, identity, db)
    await _require_record_owner_or_manager(record, identity, db)
    if record.status not in {"草稿", "待用印"}:
        raise HTTPException(status_code=409, detail="仅草稿或待用印用印申请可以上传用印文件")
    if record.status == "待用印":
        await _require_seal_base_action(identity, db, "stamp")
    else:
        await _require_seal_base_action(identity, db, "apply")
    if not files:
        raise HTTPException(status_code=422, detail="请至少选择一个用印文件")
    category = SEAL_STAMPED_FILE_CATEGORY if record.status == "待用印" else SEAL_APPLICATION_FILE_CATEGORY
    allowed = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".png", ".jpg", ".jpeg", ".zip", ".rar"}
    prepared: list[tuple[UploadFile, bytes, Path, str]] = []
    try:
        for file in files:
            suffix = Path(file.filename or "").suffix.lower()
            if suffix not in allowed:
                raise HTTPException(status_code=422, detail="不支持的文件格式")
            content = await file.read()
            if len(content) > 20 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="单个文件不能超过 20MB")
            target = UPLOAD_ROOT / f"{uuid4().hex}{suffix}"
            target.write_bytes(content)
            prepared.append((file, content, target, suffix))
        for file, content, target, _ in prepared:
            db.add(FileAttachment(
                record_id=record.id,
                category=category,
                original_name=Path(file.filename or target.name).name,
                stored_name=target.name,
                content_type=file.content_type or "application/octet-stream",
                size=len(content),
                path=str(target),
                uploader=identity["username"],
                remark=remark,
            ))
        await db.flush()
        if category == SEAL_APPLICATION_FILE_CATEGORY:
            await _sync_seal_document_names(record, db)
        action = "上传盖章文件" if category == SEAL_STAMPED_FILE_CATEGORY else "上传用印文件"
        db.add(WorkflowEvent(record_id=record.id, action=action, from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{len(prepared)} 个文件"))
        await _sync_legacy_official_document(record, identity, db)
        await db.commit()
    except Exception:
        await db.rollback()
        for _, _, target, _ in prepared:
            target.unlink(missing_ok=True)
        raise
    return await list_seal_application_files(record.id, 1, min(200, max(15, len(prepared))), identity, db)


@router.post(f"{settings.api_prefix}/seals/applications/{{record_id}}/submit")
async def submit_seal_application(record_id: int, body: TaskActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _get_seal_application, _seal_record_dict,
    )
    from app.core.legacy_sync import (
        _sync_legacy_official_audit,
    )
    from app.core.permissions import (
        _require_record_owner_or_manager, _require_seal_base_action,
    )
    item = await _get_seal_application(record_id, identity, db)
    await _require_record_owner_or_manager(item, identity, db)
    await _require_seal_base_action(identity, db, "apply")
    if item.status != "草稿": raise HTTPException(status_code=409, detail="只有草稿可以提交审批")
    attachment_count = int(await db.scalar(select(func.count()).select_from(FileAttachment).where(FileAttachment.record_id == item.id, FileAttachment.category == "用印文件")) or 0)
    if not attachment_count:
        raise HTTPException(status_code=409, detail="请先上传至少一个用印文件后再提交审批")
    old = item.status; item.status = "待审批"
    db.add(WorkflowEvent(record_id=item.id, action="提交用印审批", from_status=old, to_status=item.status, operator=identity["username"], comment=body.comment))
    await _sync_legacy_official_audit(item, identity, db, 10, body.comment)
    await db.commit(); await db.refresh(item); return await _seal_record_dict(item, db, identity=identity)


@router.post(f"{settings.api_prefix}/seals/applications/{{record_id}}/withdraw")
async def withdraw_seal_application(record_id: int, body: TaskActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _get_seal_application, _seal_record_dict,
    )
    from app.core.legacy_sync import (
        _sync_legacy_official_audit,
    )
    item = await _get_seal_application(record_id, identity, db)
    if identity.get("role") != "admin" and item.owner != identity["username"]:
        raise HTTPException(status_code=403, detail="只有申请人或管理员可以撤回用印申请")
    if item.status not in {"待审批", "待用印"}:
        raise HTTPException(status_code=409, detail="只有待审批或已审待用印的申请可以撤回")
    previous = item.status
    item.status = "已撤回"
    db.add(WorkflowEvent(record_id=item.id, action="撤回用印申请", from_status=previous, to_status="已撤回", operator=identity["username"], comment=body.comment))
    await _sync_legacy_official_audit(item, identity, db, 40, body.comment)
    await db.commit(); await db.refresh(item); return await _seal_record_dict(item, db)


@router.post(f"{settings.api_prefix}/seals/applications/batch/withdraw")
async def batch_withdraw_seal_applications(body: SealBatchApplicationInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Withdraw selected pending seal applications as one atomic workflow action."""
    from app.core.legacy_sync import (
        _sync_legacy_official_audit,
    )
    from app.core.permissions import (
        _ensure_record_visible,
    )
    ids = list(dict.fromkeys(body.application_ids))
    records = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(ids), BusinessRecord.module == "seal"))).all())
    if len(records) != len(ids):
        raise HTTPException(status_code=404, detail="选中的用印申请不存在")
    by_id = {record.id: record for record in records}
    ordered = [by_id[item_id] for item_id in ids]
    try:
        for item in ordered:
            await _ensure_record_visible(item.id, identity, db)
            if identity.get("role") != "admin" and item.owner != identity["username"]:
                raise HTTPException(status_code=403, detail="只有申请人或管理员可以撤回用印申请")
            if item.status not in {"待审批", "待用印"}:
                raise HTTPException(status_code=409, detail=f"申请 {item.serial_no} 只有待审批或已审待用印状态可以撤回")
        for item in ordered:
            previous = item.status
            item.status = "已撤回"
            db.add(WorkflowEvent(record_id=item.id, action="批量撤回用印申请", from_status=previous, to_status=item.status, operator=identity["username"], comment=body.comment.strip()))
            await _sync_legacy_official_audit(item, identity, db, 40, body.comment.strip())
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return {"processed": len(ordered), "ids": ids, "status": "已撤回"}


@router.post(f"{settings.api_prefix}/seals/applications/{{record_id}}/approve")
async def approve_seal_application(record_id: int, body: SealApprovalInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _get_seal_application_for_action, _seal_record_dict,
    )
    from app.core.legacy_sync import (
        _sync_legacy_official_audit,
    )
    item = await _get_seal_application_for_action(record_id, "approve" if body.approved else "reject", identity, db)
    if not body.approved and not body.comment.strip():
        raise HTTPException(status_code=422, detail="驳回时必须填写审批意见")
    old = item.status; item.status = "待用印" if body.approved else "已拒绝"
    item.data = {
        **(item.data or {}),
        "approver": identity["username"],
        "approved_at": datetime.now().isoformat(timespec="seconds"),
        "approval_comment": body.comment.strip(),
    }
    db.add(WorkflowEvent(record_id=item.id, action="用印审批通过" if body.approved else "用印审批拒绝", from_status=old, to_status=item.status, operator=identity["username"], comment=body.comment))
    await _sync_legacy_official_audit(item, identity, db, 20 if body.approved else 30, body.comment)
    await db.commit(); await db.refresh(item); return await _seal_record_dict(item, db, identity=identity)


@router.post(f"{settings.api_prefix}/seals/applications/{{record_id}}/stamp")
async def stamp_seal_application(record_id: int, body: SealStampInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _seal_record_dict,
    )
    from app.core.legacy_sync import (
        _sync_legacy_official_audit,
    )
    from app.core.permissions import (
        _require_seal_base_action,
    )
    await _require_seal_base_action(identity, db, "stamp")
    item = await db.get(BusinessRecord, record_id)
    if not item or item.module != "seal":
        raise HTTPException(status_code=404, detail="用印申请不存在或无权访问")
    if item.status == "已用印" and (item.data or {}).get("stamped_at"):
        return await _seal_record_dict(item, db, identity=identity)
    if item.status != "待用印": raise HTTPException(status_code=409, detail="申请尚未审批通过或已经用印")
    requested = int((item.data or {}).get("copies") or 0)
    if body.actual_copies > requested: raise HTTPException(status_code=409, detail=f"实际用印份数不能超过申请份数 {requested}")
    asset = await db.get(SealAsset, int((item.data or {}).get("seal_asset_id") or 0))
    if not asset or asset.status != "可用": raise HTTPException(status_code=409, detail="关联印章不存在或当前不可用")
    stamp_attachment_ids = list(dict.fromkeys([
        *body.stamp_attachment_ids,
        *([body.stamp_attachment_id] if body.stamp_attachment_id else []),
    ]))
    for attachment_id in stamp_attachment_ids:
        stamp_attachment = await db.get(FileAttachment, attachment_id)
        if not stamp_attachment or stamp_attachment.record_id != item.id or stamp_attachment.category != SEAL_STAMPED_FILE_CATEGORY:
            raise HTTPException(status_code=404, detail="所选盖章附件不存在")
        stamp_path = Path(stamp_attachment.path)
        if not stamp_path.is_file() or UPLOAD_ROOT.resolve() not in stamp_path.resolve().parents:
            raise HTTPException(status_code=404, detail="所选盖章附件文件不存在")
    old = item.status; item.status = "已用印"; data = dict(item.data or {})
    data.update({"actual_copies": body.actual_copies, "stamp_operator": body.operator or identity["username"], "stamped_at": datetime.now().isoformat(), "archive_no": body.archive_no}); item.data = data
    if stamp_attachment_ids:
        data["stamp_attachment_id"] = stamp_attachment_ids[0]
        data["stamp_attachment_ids"] = stamp_attachment_ids
        item.data = data
    asset.usage_count += body.actual_copies; asset.last_used_at = datetime.now()
    db.add(WorkflowEvent(record_id=item.id, action="完成实际用印", from_status=old, to_status=item.status, operator=identity["username"], comment=f"实际 {body.actual_copies} 份；归档号：{body.archive_no}。{body.comment}"))
    db.add(SealAssetAudit(asset_id=asset.id, asset_code=asset.code, asset_name=asset.name, action="完成实际用印", operator=identity["username"], comment=f"用印申请 {item.serial_no}；实际 {body.actual_copies} 份"))
    await _sync_legacy_official_audit(item, identity, db, 60, body.comment)
    await db.commit(); await db.refresh(item); await db.refresh(asset); return await _seal_record_dict(item, db, identity=identity)


@router.post(f"{settings.api_prefix}/seals/applications/batch-stamp")
async def batch_stamp_seal_applications(body: SealBatchStampInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Stamp selected approved applications in one transaction."""
    from app.core.documents import (
        _sync_seal_document_names,
    )
    from app.core.legacy_sync import (
        _sync_legacy_official_audit,
    )
    from app.core.permissions import (
        _require_seal_base_action, _seal_application_capabilities,
    )
    await _require_seal_base_action(identity, db, "stamp")
    ids = list(dict.fromkeys(body.application_ids))
    records = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(ids), BusinessRecord.module == "seal"))).all())
    if len(records) != len(ids):
        raise HTTPException(status_code=404, detail="选中的用印申请不存在")
    by_id = {record.id: record for record in records}
    ordered = [by_id[item_id] for item_id in ids]
    prepared: list[tuple[BusinessRecord, SealAsset]] = []
    source_attachment: FileAttachment | None = None
    created_targets: list[Path] = []
    try:
        if body.stamp_attachment_id:
            source_attachment = await db.get(FileAttachment, body.stamp_attachment_id)
            if not source_attachment or source_attachment.category != SEAL_STAMPED_FILE_CATEGORY or source_attachment.record_id not in ids:
                raise HTTPException(status_code=404, detail="所选盖章附件不存在")
            source_path = Path(source_attachment.path)
            if not source_path.is_file() or UPLOAD_ROOT.resolve() not in source_path.resolve().parents:
                raise HTTPException(status_code=404, detail="所选盖章附件文件不存在")
        for item in ordered:
            capabilities = await _seal_application_capabilities(item, identity, db)
            if not capabilities["stamp"]:
                raise HTTPException(status_code=403, detail=f"当前账号没有登记申请 {item.serial_no} 实际用印的权限")
            requested = int((item.data or {}).get("copies") or 0)
            if body.actual_copies > requested:
                raise HTTPException(status_code=409, detail=f"申请 {item.serial_no} 实际用印份数不能超过申请份数 {requested}")
            asset = await db.get(SealAsset, int((item.data or {}).get("seal_asset_id") or 0))
            if not asset or asset.status != "可用":
                raise HTTPException(status_code=409, detail=f"申请 {item.serial_no} 关联印章不存在或当前不可用")
            prepared.append((item, asset))
        for item, asset in prepared:
            stamp_attachment_id = body.stamp_attachment_id
            if source_attachment is not None:
                if item.id != source_attachment.record_id:
                    source_path = Path(source_attachment.path)
                    target = UPLOAD_ROOT / f"{uuid4().hex}{source_path.suffix.lower()}"
                    target.write_bytes(source_path.read_bytes())
                    created_targets.append(target)
                    copied = FileAttachment(
                        record_id=item.id,
                        category=SEAL_STAMPED_FILE_CATEGORY,
                        original_name=source_attachment.original_name,
                        stored_name=target.name,
                        content_type=source_attachment.content_type or "application/octet-stream",
                        size=target.stat().st_size,
                        path=str(target),
                        uploader=identity["username"],
                        remark="批量用印盖章附件",
                    )
                    db.add(copied)
                    await db.flush()
                    stamp_attachment_id = copied.id
                await _sync_seal_document_names(item, db)
            previous = item.status
            item.status = "已用印"
            data = dict(item.data or {})
            data.update({"actual_copies": body.actual_copies, "stamp_operator": body.operator or identity["username"], "stamped_at": datetime.now().isoformat(), "archive_no": body.archive_no})
            if stamp_attachment_id is not None:
                data["stamp_attachment_id"] = stamp_attachment_id
            item.data = data
            asset.usage_count += body.actual_copies
            asset.last_used_at = datetime.now()
            db.add(WorkflowEvent(record_id=item.id, action="批量完成实际用印", from_status=previous, to_status=item.status, operator=identity["username"], comment=f"实际 {body.actual_copies} 份；归档号：{body.archive_no}。{body.comment}"))
            db.add(SealAssetAudit(asset_id=asset.id, asset_code=asset.code, asset_name=asset.name, action="批量完成实际用印", operator=identity["username"], comment=f"用印申请 {item.serial_no}；实际 {body.actual_copies} 份"))
            await _sync_legacy_official_audit(item, identity, db, 60, body.comment)
        await db.commit()
    except Exception:
        await db.rollback()
        for target in created_targets:
            target.unlink(missing_ok=True)
        raise
    return {"processed": len(prepared), "ids": ids, "status": "已用印"}


@router.post(f"{settings.api_prefix}/seals/applications/{{record_id}}/archive")
async def archive_seal_application(record_id: int, body: TaskActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _get_seal_application_for_action, _seal_record_dict,
    )
    from app.core.legacy_sync import (
        _sync_legacy_official_document,
    )
    item = await _get_seal_application_for_action(record_id, "archive", identity, db)
    if not (item.data or {}).get("archive_no"): raise HTTPException(status_code=409, detail="请先在用印登记中填写归档号")
    item.status = "已归档"
    db.add(WorkflowEvent(record_id=item.id, action="用印材料归档", from_status="已用印", to_status="已归档", operator=identity["username"], comment=body.comment))
    await _sync_legacy_official_document(item, identity, db)
    await db.commit(); await db.refresh(item); return await _seal_record_dict(item, db, identity=identity)


@router.get(f"{settings.api_prefix}/seals/assets")
async def list_seal_assets(keyword: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _seal_asset_dict, _seal_authorization_context,
    )
    context = await _seal_authorization_context(identity, db)
    conditions = []
    if keyword:
        like = f"%{keyword.strip()}%"; conditions.append(or_(SealAsset.code.ilike(like), SealAsset.name.ilike(like), SealAsset.seal_type.ilike(like), SealAsset.custodian.ilike(like)))
    items = (await db.scalars(select(SealAsset).where(*conditions).order_by(SealAsset.code))).all()
    capabilities = {"manage_assets": bool(context["manage_assets"])}
    return {
        "items": [{**_seal_asset_dict(x), "capabilities": capabilities, "action_keys": ["manage_assets"] if capabilities["manage_assets"] else []} for x in items],
        "total": len(items),
        "capabilities": capabilities,
        "action_keys": ["manage_assets"] if capabilities["manage_assets"] else [],
    }


@router.get(f"{settings.api_prefix}/seals/assets/{{asset_id}}/audit")
async def list_seal_asset_audit(
    asset_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200),
    action: str = "",
    operator: str = "",
    keyword: str = "",
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Read-only, bounded history for one seal asset."""
    from app.core.documents import (
        _seal_asset_audit_dict,
    )
    from app.core.permissions import (
        _require_seal_base_action,
    )
    await _require_seal_base_action(identity, db, "manage_assets")
    asset = await db.get(SealAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="印章不存在")
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="审计日期范围无效")
    conditions = [SealAssetAudit.asset_id == asset_id]
    if action.strip():
        conditions.append(SealAssetAudit.action.ilike(f"%{action.strip()}%"))
    if operator.strip():
        conditions.append(SealAssetAudit.operator.ilike(f"%{operator.strip()}%"))
    if keyword.strip():
        like = f"%{keyword.strip()}%"
        conditions.append(or_(SealAssetAudit.action.ilike(like), SealAssetAudit.operator.ilike(like), SealAssetAudit.comment.ilike(like)))
    if date_from:
        conditions.append(SealAssetAudit.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        conditions.append(SealAssetAudit.created_at < datetime.combine(date_to + timedelta(days=1), datetime.min.time()))
    total = int(await db.scalar(select(func.count()).select_from(SealAssetAudit).where(*conditions)) or 0)
    rows = (await db.scalars(select(SealAssetAudit).where(*conditions).order_by(SealAssetAudit.created_at.desc(), SealAssetAudit.id.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    return {"items": [_seal_asset_audit_dict(item) for item in rows], "total": total, "page": page, "page_size": page_size, "pages": (total + page_size - 1) // page_size if total else 0}


@router.post(f"{settings.api_prefix}/seals/assets", status_code=status.HTTP_201_CREATED)
async def create_seal_asset(body: SealAssetInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _seal_asset_dict,
    )
    from app.core.permissions import (
        _require_seal_base_action,
    )
    await _require_seal_base_action(identity, db, "manage_assets")
    if body.seal_type not in REQUIRED_SEAL_TYPES: raise HTTPException(status_code=422, detail="印章类型不在系统允许范围内")
    if await db.scalar(select(SealAsset.id).where(SealAsset.code == body.code)): raise HTTPException(status_code=409, detail="印章编号已存在")
    item = SealAsset(**body.model_dump()); db.add(item); await db.flush()
    db.add(SealAssetAudit(asset_id=item.id, asset_code=item.code, asset_name=item.name, action="创建印章资产", operator=identity["username"], comment="新增印章资产"))
    await db.commit(); await db.refresh(item); return _seal_asset_dict(item)


@router.patch(f"{settings.api_prefix}/seals/assets/{{asset_id}}")
async def update_seal_asset(asset_id: int, body: SealAssetUpdate, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _seal_asset_dict,
    )
    from app.core.permissions import (
        _require_seal_base_action,
    )
    await _require_seal_base_action(identity, db, "manage_assets")
    item = await db.get(SealAsset, asset_id)
    if not item: raise HTTPException(status_code=404, detail="印章不存在")
    changes = body.model_dump(exclude_unset=True)
    if changes.get("status") not in {None, "可用", "停用", "维修", "遗失"}: raise HTTPException(status_code=422, detail="无效的印章状态")
    if changes.get("seal_type") not in {None, *REQUIRED_SEAL_TYPES}: raise HTTPException(status_code=422, detail="印章类型不在系统允许范围内")
    previous = {key: getattr(item, key) for key in changes}
    for key, value in changes.items(): setattr(item, key, value)
    db.add(SealAssetAudit(asset_id=item.id, asset_code=item.code, asset_name=item.name, action="修改印章资产", operator=identity["username"], comment=f"变更 {previous} -> {changes}"))
    await db.commit(); await db.refresh(item); return _seal_asset_dict(item)


@router.delete(f"{settings.api_prefix}/seals/assets/{{asset_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_seal_asset(asset_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_seal_base_action,
    )
    await _require_seal_base_action(identity, db, "manage_assets")
    item = await db.get(SealAsset, asset_id)
    if not item: raise HTTPException(status_code=404, detail="印章不存在")
    referenced = int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
        BusinessRecord.module == "seal",
        BusinessRecord.data["seal_asset_id"].as_integer() == item.id,
    )) or 0)
    if referenced:
        raise HTTPException(status_code=409, detail=f"该印章已被 {referenced} 条用印申请引用，不能删除；请维护为停用、维修或遗失")
    db.add(SealAssetAudit(
        asset_id=item.id,
        asset_code=item.code,
        asset_name=item.name,
        action="删除印章资产",
        operator=identity["username"],
        comment="管理员删除未被用印申请引用的印章资产",
    ))
    await db.delete(item)
    await db.commit()


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/documents/{{document_type}}", status_code=status.HTTP_201_CREATED)
async def generate_case_document(case_id: int, document_type: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _case_document_bytes, _case_document_context, _case_document_required_fields,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_case_document_write_access,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    if document_type not in CASE_DOCUMENT_TYPES:
        raise HTTPException(status_code=404, detail="不支持的案件文书类型")
    record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_document_write_access(record, identity, db)
    if record.status in {"已合并", "已归档"}:
        raise HTTPException(status_code=409, detail="已合并或已归档案件不能再生成办理文书")
    context = await _case_document_context(record, db)
    missing_fields = _case_document_required_fields(record, document_type, context)
    if missing_fields:
        raise HTTPException(status_code=422, detail=f"{record.serial_no} 缺少{'、'.join(missing_fields)}，不能生成{CASE_DOCUMENT_TYPES[document_type]}")
    title, content = _case_document_bytes(record, document_type, context)
    stored_name = f"{uuid4().hex}.docx"
    path = UPLOAD_ROOT / stored_name
    path.write_bytes(content)
    attachment = FileAttachment(record_id=record.id, category=CASE_DOCUMENT_CATEGORY.get(document_type, "案件生成文书"), original_name=f"{record.serial_no}-{title}-{datetime.now():%Y%m%d%H%M%S}.docx", stored_name=stored_name, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", size=len(content), path=str(path), uploader=identity["username"], remark=f"系统生成案件文书：{document_type}")
    try:
        db.add(attachment); await db.flush()
        db.add(WorkflowEvent(record_id=record.id, action="生成案件文书", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{title}｜附件 {attachment.original_name}"))
        await db.commit(); await db.refresh(attachment)
    except Exception:
        await db.rollback()
        path.unlink(missing_ok=True)
        raise
    return _attachment_dict(attachment, record)


@router.post(f"{settings.api_prefix}/records", status_code=status.HTTP_201_CREATED)
async def create_record(body: RecordInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _resolve_active_customer_managers,
    )
    from app.core.legacy_sync import (
        _sync_legacy_projection,
    )
    from app.core.permissions import (
        _ensure_record_visible, _require_record_module_menu,
    )
    from app.core.system import (
        _record_dict,
    )
    if body.module == "finance_fee_inform":
        raise HTTPException(status_code=422, detail="费用通知必须使用案件费用的专用通知入口创建")
    await _require_record_module_menu(body.module, identity, db, action="新建")
    if body.module in INVESTIGATION_RECORD_MODULES:
        raise HTTPException(status_code=422, detail="调查、公证和证据记录必须使用调查中心专用入口创建")
    if body.module == "customer":
        raise HTTPException(status_code=422, detail="新建客户必须使用客户专用入口")
    if body.module == "contract":
        raise HTTPException(status_code=422, detail="新建合同必须使用合同专用入口")
    if body.module == "case":
        raise HTTPException(status_code=422, detail="新建案件必须选择已审批合同，请使用案件创建入口")
    if body.module == "task":
        raise HTTPException(status_code=422, detail="任务必须使用任务专用入口创建")
    if body.module == "finance_package":
        raise HTTPException(status_code=422, detail="付款包必须使用打包付款专用入口创建")
    if body.module == "finance_settlement":
        raise HTTPException(status_code=422, detail="结算申请必须使用结算管理专用入口创建")
    if body.module == "case_reminder":
        raise HTTPException(status_code=422, detail="案件提醒必须使用案件提醒专用入口创建")
    if body.module == "finance_archive_settlement":
        raise HTTPException(status_code=422, detail="归档费支付必须使用归档费结算专用入口创建")
    if body.module == "finance":
        raise HTTPException(status_code=422, detail="费用必须使用费用管理专用入口创建")
    if body.module == JAR_FEE_MODULE:
        raise HTTPException(status_code=422, detail="JAR fees must use the dedicated finance endpoint")
    if body.module in {"hr", "warehouse"} and identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="当前角色不能新建人事或仓库记录")
    if await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == body.serial_no)):
        raise HTTPException(status_code=409, detail="业务编号已存在")
    payload = body.model_dump()
    if body.module == "clue":
        payload["status"] = "草稿"
    if body.module == "document":
        direction = str((body.data or {}).get("direction") or "").strip()
        if direction not in {"收文", "发文"}: raise HTTPException(status_code=422, detail="收发类型必须为收文或发文")
        case_no = str((body.data or {}).get("case_no") or "").strip()
        if case_no:
            case_record = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "case", BusinessRecord.serial_no == case_no))
            if not case_record: raise HTTPException(status_code=422, detail="关联案件不存在")
            await _ensure_record_visible(case_record.id, identity, db)
        payload["status"] = "待登记"
    if body.module == "hr":
        joined_at = str((body.data or {}).get("joined_at") or "").strip()
        if not body.title.strip() or not (body.data or {}).get("position") or not joined_at: raise HTTPException(status_code=422, detail="员工姓名、岗位和入职日期不能为空")
        payload["status"] = "在职" if body.status == "在职" else "试用"
    if body.module == "warehouse":
        data = dict(body.data or {}); quantity = int(data.get("quantity") or 0)
        if data.get("evidence_status"): raise HTTPException(status_code=422, detail="证物必须使用证物登记入口创建")
        if quantity < 1 or not str(data.get("category") or "").strip() or not str(data.get("location") or "").strip(): raise HTTPException(status_code=422, detail="物品类别、数量和存放位置不能为空")
        data.update({"quantity": quantity, "borrower": "", "due_date": "", "borrow_purpose": ""}); payload["data"] = data; payload["status"] = "在库"
    if identity.get("role") != "admin":
        user = await db.scalar(select(User).where(User.username == identity["username"]))
        if not user: raise HTTPException(status_code=401, detail="当前用户不存在")
        payload["department"] = user.department
        if identity.get("role") == "user": payload["owner"] = user.username
    if body.module == "customer":
        managers = await _resolve_active_customer_managers(list((payload.get("data") or {}).get("customer_managers") or [payload.get("owner")]), db)
        owner = (await _resolve_active_customer_managers([payload.get("owner")], db))[0]
        managers = [owner, *[manager for manager in managers if manager != owner]]
        payload["owner"] = owner
        payload["data"] = {**(payload.get("data") or {}), "customer_managers": managers}
    record = BusinessRecord(**payload)
    db.add(record)
    await db.flush()
    db.add(WorkflowEvent(record_id=record.id, action="创建", to_status=record.status, operator=identity["username"], comment="创建业务记录"))
    await _sync_legacy_projection(record, identity, db)
    await db.commit()
    await db.refresh(record)
    return _record_dict(record)


@router.get(f"{settings.api_prefix}/records/{{record_id}}")
async def get_record(record_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_visible, _record_dict_for_identity, _require_record_module_menu,
    )
    record = await _ensure_record_visible(record_id, identity, db)
    await _require_record_module_menu(record.module, identity, db, action="查看")
    return await _record_dict_for_identity(record, identity, db)


@router.get(f"{settings.api_prefix}/records/{{record_id}}/history")
async def record_history(record_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _person_reference_display, _user_display_map,
    )
    from app.core.permissions import (
        _ensure_record_visible, _require_record_module_menu,
    )
    record = await _ensure_record_visible(record_id, identity, db)
    await _require_record_module_menu(record.module, identity, db, action="查看")
    events = list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == record_id).order_by(WorkflowEvent.created_at.desc(), WorkflowEvent.id.desc()))).all())
    users_by_username = await _user_display_map({event.operator for event in events}, db)
    return {
        "transitions": WORKFLOW_TRANSITIONS.get(record.module, {}).get(record.status, []),
        "items": [{
            "id": event.id, "action": event.action, "from_status": event.from_status,
            "to_status": event.to_status, "operator": event.operator,
            "operator_display_name": _person_reference_display(event.operator, users_by_username)[0],
            "comment": event.comment, "created_at": event.created_at,
        } for event in events],
    }


@router.patch(f"{settings.api_prefix}/records/{{record_id}}")
async def update_record(record_id: int, body: RecordUpdate, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _mark_customer_modified, _resolve_active_customer_managers,
    )
    from app.core.legacy_sync import (
        _legacy_failure_response, _sync_legacy_projection,
    )
    from app.core.permissions import (
        _ensure_record_visible, _ensure_unique_customer_name, _record_dict_for_identity, _require_record_module_menu, _require_record_owner_or_manager,
    )
    record = await _ensure_record_visible(record_id, identity, db)
    await _require_record_module_menu(record.module, identity, db, action="编辑")
    await _require_record_owner_or_manager(record, identity, db)
    changes = body.model_dump(exclude_unset=True)
    if record.module not in GENERIC_RECORD_EDITABLE_MODULES:
        return _legacy_failure_response("该业务必须使用专用入口办理")
    if record.module in {"hr", "warehouse"} and identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="当前角色不能修改人事或仓库资料")
    if "status" in changes and record.module in {"clue", "evidence", "invoice", "refund", "document", "hr", "warehouse"}:
        return _legacy_failure_response("该业务必须使用专用审批或办理入口变更状态")
    if record.module == "customer" and "status" in changes and changes["status"] != record.status:
        return _legacy_failure_response("客户生命周期状态必须通过领取、释放、回收或恢复专用入口变更")
    if record.module == "warehouse" and "data" in changes:
        if record.status != "在库": return _legacy_failure_response("借出或归还中的物品不能直接修改资料")
        protected = {"borrower", "due_date", "borrow_purpose", "borrowed_at", "borrowed_by", "return_requested_at", "returned_at", "return_condition", "scrapped_at", "scrap_reason", "evidence_status", "checked_in_at", "checked_in_by", "checked_out_at", "checked_out_by", "recipient", "checkout_purpose", "rechecked_in_at", "rechecked_in_by", "destroyed_at", "destroyed_by", "destroy_reason"}
        incoming_data = dict(changes.get("data") or {})
        for key in protected:
            if incoming_data.get(key) != (record.data or {}).get(key): return _legacy_failure_response("借还及报废信息必须通过专用办理入口修改")
    if identity.get("role") != "admin":
        user = await db.scalar(select(User).where(User.username == identity["username"]))
        if not user: raise HTTPException(status_code=401, detail="当前用户不存在")
        if "department" in changes: changes["department"] = user.department
        if identity.get("role") == "user" and "owner" in changes: changes["owner"] = user.username
    if record.module == "customer":
        requested_title = str(changes.get("title", record.title) or "").strip()
        await _ensure_unique_customer_name(requested_title, db, exclude_id=record.id)
        changes["title"] = requested_title
        if "title" in body.model_fields_set:
            changes["customer"] = requested_title
        owner = record.owner
        if "owner" in changes:
            requested_owner = (await _resolve_active_customer_managers([changes["owner"]], db))[0]
            if requested_owner != record.owner:
                return _legacy_failure_response("客户负责人必须通过客户管理人专用入口修改")
            changes["owner"] = record.owner
        if "data" in changes:
            customer_data = dict(changes.get("data") or {})
            existing_customer_data = dict(record.data or {})
            for protected_contact_field in CUSTOMER_SYSTEM_DATA_FIELDS:
                if (
                    protected_contact_field in customer_data
                    and customer_data.get(protected_contact_field) != existing_customer_data.get(protected_contact_field)
                ):
                    return _legacy_failure_response("客户系统维护字段必须通过对应专用入口修改")
                if protected_contact_field in existing_customer_data:
                    customer_data[protected_contact_field] = existing_customer_data[protected_contact_field]
                else:
                    customer_data.pop(protected_contact_field, None)
            existing_managers = [
                str(manager).strip()
                for manager in existing_customer_data.get("customer_managers", [])
                if str(manager).strip()
            ] or [record.owner]
            if "customer_managers" in customer_data:
                incoming_managers = [
                    str(manager).strip()
                    for manager in (customer_data.get("customer_managers") or [])
                    if str(manager).strip()
                ]
                if incoming_managers != existing_managers:
                    return _legacy_failure_response("客户管理人必须通过客户管理人专用入口修改")
            customer_data["customer_managers"] = existing_managers
            changes["data"] = customer_data
    old_status = record.status
    for field, value in changes.items():
        setattr(record, field, value)
    if record.module == "customer":
        _mark_customer_modified(record, identity)
    if "status" in changes and changes["status"] != old_status:
        db.add(WorkflowEvent(record_id=record.id, action="编辑变更", from_status=old_status, to_status=record.status, operator=identity["username"], comment="通过编辑表单变更状态"))
    else:
        db.add(WorkflowEvent(record_id=record.id, action="编辑", from_status=record.status, to_status=record.status, operator=identity["username"], comment="修改业务资料"))
    await _sync_legacy_projection(record, identity, db)
    await db.commit()
    await db.refresh(record)
    return await _record_dict_for_identity(record, identity, db)


@router.post(f"{settings.api_prefix}/records/{{record_id}}/transition")
async def transition_record(record_id: int, body: TransitionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.legacy_sync import (
        _legacy_failure_response, _sync_legacy_projection,
    )
    from app.core.permissions import (
        _ensure_record_visible, _require_record_module_menu, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _record_dict,
    )
    record = await _ensure_record_visible(record_id, identity, db)
    await _require_record_module_menu(record.module, identity, db, action="流转")
    if record.module not in GENERIC_RECORD_TRANSITION_MODULES:
        return _legacy_failure_response("该业务必须使用专用审批或办理入口变更状态")
    approval_access = identity.get("role") == "auditor" and record.module in {"contract", "finance", "invoice", "refund", "seal", "clue", "notary"} and record.status in {"待审批", "审批中", "待审核"}
    if not approval_access:
        await _require_record_owner_or_manager(record, identity, db)
    allowed = WORKFLOW_TRANSITIONS.get(record.module, {}).get(record.status, [])
    if body.to_status not in allowed:
        return _legacy_failure_response(f"不能从“{record.status}”流转到“{body.to_status}”")
    previous = record.status
    record.status = body.to_status
    action = "审批通过"
    if body.to_status in {"已拒绝", "已驳回", "已退回", "已撤回"}:
        action = "驳回/撤回"
    elif body.to_status in {"已完成", "已归档", "已用印", "已付款", "已对账", "已发布"}:
        action = "办结"
    db.add(WorkflowEvent(record_id=record.id, action=action, from_status=previous, to_status=body.to_status, operator=identity["username"], comment=body.comment))
    await _sync_legacy_projection(record, identity, db)
    await db.commit()
    await db.refresh(record)
    return _record_dict(record)


@router.delete(f"{settings.api_prefix}/records/{{record_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(record_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _delete_case_events_for_case_cleanup,
    )
    from app.core.tasks import (
        _delete_task_notifications,
    )
    if identity["role"] != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可删除")
    record = await db.get(BusinessRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    if record.module not in GENERIC_RECORD_DELETABLE_MODULES:
        raise HTTPException(status_code=409, detail="该业务记录不能通过通用入口物理删除，请使用专用撤销、作废或冲正流程")
    if record.module == "hr":
        linked_username = str((record.data or {}).get("username") or "").strip().lower()
        if linked_username and await db.scalar(select(User.id).where(User.username == linked_username)):
            # A generic record delete must never leave an active login account
            # behind.  Employee exits are handled by the HR edit/disable flow.
            raise HTTPException(status_code=409, detail="该员工档案关联可登录账号，不能直接删除；请在员工资料中停用账号以保持同步")
    if record.module == "seal" and (record.data or {}).get("actual_copies"):
        asset = await db.get(SealAsset, int((record.data or {}).get("seal_asset_id") or 0))
        if asset:
            asset.usage_count = max(0, asset.usage_count - int((record.data or {}).get("actual_copies") or 0))
    attachments = (await db.scalars(select(FileAttachment).where(FileAttachment.record_id == record_id))).all()
    attachment_paths = [Path(item.path) for item in attachments]
    for attachment in attachments:
        await db.delete(attachment)
    await db.execute(delete(FinanceTransaction).where(FinanceTransaction.finance_record_id == record_id))
    await db.execute(delete(ContractApprovalStep).where(ContractApprovalStep.contract_record_id == record_id))
    await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == record_id))
    if record.module == "case":
        await _delete_case_events_for_case_cleanup(record_id, db)
    if record.module == "task":
        await _delete_task_notifications(record_id, db)
    await db.delete(record)
    await db.commit()
    for path in attachment_paths:
        if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
            path.unlink()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(f"{settings.api_prefix}/cases/archive/search")
async def search_case_archive(body: ArchiveSearchInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    return await search_archive_cases(body, identity, db)


@router.post(f"{settings.api_prefix}/cases/archive/batch-review")
async def batch_review_case_archive(body: ArchiveBatchReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import _record_scope_conditions, _require_case_action
    from app.core.system import _record_dict
    ids = [item.case_id for item in body.items]
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=422, detail="批量审核不能包含重复案件")
    await _require_case_action(identity, db, "case.archive.review")
    try:
        records = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.id.in_(ids), BusinessRecord.module == "case", *(await _record_scope_conditions(identity, db)),
        ).order_by(BusinessRecord.id).with_for_update())).all())
        if len(records) != len(ids):
            raise HTTPException(status_code=404, detail="选中的案件不存在或无权访问，整批未审核")
        by_id = {record.id: record for record in records}
        for item in body.items:
            try:
                await _apply_case_archive_review(item.case_id, item, identity, db)
            except HTTPException as exc:
                raise HTTPException(status_code=exc.status_code, detail=f"案件 {by_id[item.case_id].serial_no}：{exc.detail}；整批未审核") from exc
        await db.commit()
        for record in records:
            await db.refresh(record)
        return {"processed": len(records), "items": [_record_dict(by_id[item_id]) for item_id in ids]}
    except Exception:
        await db.rollback()
        raise


@router.post(f"{settings.api_prefix}/cases/archive/export")
async def export_case_archive(body: ArchiveExportInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.system import _csv_response, _excel_response
    records = await search_archive_cases(body, identity, db, export=True)
    if not records:
        raise HTTPException(status_code=422, detail="当前筛选没有可导出的归档案件")
    # Count each page of IDs separately to stay below database bind limits.
    counts = {}
    ids = [record.id for record in records]
    for start in range(0, len(ids), 400):
        counts.update(dict((await db.execute(select(FileAttachment.record_id, func.count(FileAttachment.id)).where(
            FileAttachment.record_id.in_(ids[start:start + 400]),
        ).group_by(FileAttachment.record_id))).all()))
    headers = ["案号", "案件名称", "客户", "案件类型", "归档状态", "合同编号", "负责人", "附件数量", "归档号", "纸质卷宗位置", "纸质卷宗数量"]
    rows = [[record.serial_no, record.title, record.customer, (record.data or {}).get("case_type", ""), record.status,
             (record.data or {}).get("contract_no", ""), record.owner, counts.get(record.id, 0),
             (record.data or {}).get("archive_no", ""), (record.data or {}).get("paper_archive_location", ""),
             (record.data or {}).get("paper_volume_count", "")] for record in records]
    if body.format == "csv":
        return _csv_response(f"案件归档清单-{date.today()}.csv", headers, rows)
    return _excel_response(f"案件归档清单-{date.today()}.xls", headers, rows)
