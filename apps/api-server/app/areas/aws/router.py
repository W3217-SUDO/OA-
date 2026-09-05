"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.constants import (
    ARCHIVE_REQUIRED_CATEGORIES, UPLOAD_ROOT, WORKFLOW_TRANSITIONS,
)
from app.core.dependencies import (
    AsyncSession, BusinessRecord, Depends, DocumentTemplate, File,
    FileAttachment, Form, HTTPException, OfficialOutgoingDocument, Path,
    SealAsset, StreamingResponse, UploadFile, User, WorkflowEvent,
    current_identity, date, datetime, delete, func,
    get_db, io, json, select, settings,
    status, uuid4, zipfile,
)
from app.models_shared import (
    DocumentTransitionInput, OfficialDocumentBatchCaseIdsInput, OfficialDocumentDeleteInput, OfficialDocumentProcessInput, OfficialDocumentReceiptDateInput,
    OfficialOutgoingBatchInput, OfficialOutgoingCreateInput, OfficialOutgoingReviewInput, OfficialOutgoingRollbackInput, OfficialOutgoingSubmitInput,
    OfficialOutgoingUpdateInput,
)
from fastapi import APIRouter

router = APIRouter()


@router.get(f"{settings.api_prefix}/documents/official/export")
async def export_official_documents(ids: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _scoped_export_records,
    )
    from app.core.system import (
        _csv_response,
    )
    records = await _scoped_export_records("document", ids, identity, db)
    records = [item for item in records if (item.data or {}).get("direction", "收文") == "收文"]
    rows = []
    for item in records:
        data = item.data or {}
        rows.append([data.get("case_no") or item.serial_no, data.get("plaintiff") or item.customer, data.get("defendant") or data.get("sender", ""), item.title, data.get("document_date") or data.get("received_at", ""), data.get("uploaded_at") or data.get("registered_at", ""), data.get("uploader") or item.owner, data.get("import_status", "已导入"), data.get("business_process_status", "未处理"), item.status])
    return _csv_response(f"官文收文-{date.today()}.csv", ["案号", "原告", "被告", "文件名称", "文件日期", "上传日期", "上传人", "导入状态", "业务处理状态", "办理状态"], rows)


@router.get(f"{settings.api_prefix}/documents/summary")
async def document_summary(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _filter_visible_attachments, _record_scope_conditions,
    )
    documents = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "document", *(await _record_scope_conditions(identity, db))))).all()
    attachments = (await db.scalars(select(FileAttachment))).all()
    attachments = await _filter_visible_attachments(attachments, identity, db)
    templates = (await db.scalars(select(DocumentTemplate))).all()
    return {
        "documents": len(documents),
        "pending_receipt": sum(1 for item in documents if item.status in {"待登记", "待签收"}),
        "received": sum(1 for item in documents if item.status == "已签收"),
        "attachments": len(attachments),
        "archive_materials": sum(1 for item in attachments if item.category in ARCHIVE_REQUIRED_CATEGORIES),
        "templates": sum(1 for item in templates if item.is_active),
    }


@router.post(f"{settings.api_prefix}/documents/{{document_id}}/transition")
async def transition_document(document_id: int, body: DocumentTransitionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_visible, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    item = await _ensure_record_visible(document_id, identity, db)
    if item.module != "document": raise HTTPException(status_code=404, detail="收发文记录不存在")
    await _require_record_owner_or_manager(item, identity, db)
    allowed = WORKFLOW_TRANSITIONS["document"].get(item.status, [])
    if body.to_status not in allowed:
        raise HTTPException(status_code=409, detail=f"不能从“{item.status}”流转到“{body.to_status}”")
    if body.action_date > date.today(): raise HTTPException(status_code=422, detail="办理日期不能晚于今天")
    handler = body.handler.strip()
    archive_no = body.archive_no.strip()
    if body.to_status == "已签收" and not handler:
        raise HTTPException(status_code=422, detail="确认签收时必须填写签收人")
    if body.to_status == "已归档" and not archive_no:
        raise HTTPException(status_code=422, detail="归档时必须填写归档编号")
    previous = item.status
    data = dict(item.data or {})
    if body.to_status == "待签收":
        data.update({"registered_at": str(body.action_date), "register_operator": identity["username"]})
        action = "完成登记"
    elif body.to_status == "已签收":
        data.update({"signed_at": str(body.action_date), "signer": handler})
        action = "确认签收" if data.get("direction") == "收文" else "确认送达"
    else:
        data.update({"archived_at": str(body.action_date), "archive_no": archive_no, "archive_location": body.archive_location.strip()})
        action = "文档归档"
    item.data = data
    item.status = body.to_status
    db.add(WorkflowEvent(record_id=item.id, action=action, from_status=previous, to_status=item.status, operator=identity["username"], comment=body.comment))
    await db.commit(); await db.refresh(item)
    return _record_dict(item, await _allowed_field_keys(identity, db))


@router.post(f"{settings.api_prefix}/documents/official/process")
async def process_official_documents(body: OfficialDocumentProcessInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Mark selected official incoming documents as business processed/unprocessed.

    This status is intentionally separate from registration, signing and archive
    lifecycle.  It mirrors the legacy Patent Office batch actions without
    allowing a generic record update to bypass document lifecycle controls.
    """
    from app.core.permissions import (
        _ensure_record_visible, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    record_ids = list(dict.fromkeys(body.record_ids))
    if not record_ids:
        raise HTTPException(status_code=422, detail="请选择至少一条官文收文记录")
    target_status = "已处理" if body.processed else "未处理"
    action = "标记官文已处理" if body.processed else "标记官文未处理"
    changed: list[BusinessRecord] = []
    for record_id in record_ids:
        item = await _ensure_record_visible(record_id, identity, db)
        if item.module != "document" or (item.data or {}).get("direction", "收文") != "收文":
            raise HTTPException(status_code=422, detail="所选记录不是官文收文")
        await _require_record_owner_or_manager(item, identity, db)
        data = dict(item.data or {})
        previous = data.get("business_process_status", "未处理")
        if previous == target_status:
            continue
        data.update({
            "business_process_status": target_status,
            "business_processed_at": datetime.now().isoformat(timespec="seconds"),
            "business_processed_by": identity["username"],
        })
        item.data = data
        # Do not change item.status: document registration/sign/archive has its
        # own dedicated state machine and must remain independently auditable.
        db.add(WorkflowEvent(
            record_id=item.id,
            action=action,
            from_status=item.status,
            to_status=item.status,
            operator=identity["username"],
            comment=body.comment.strip(),
        ))
        changed.append(item)
    await db.commit()
    for item in changed:
        await db.refresh(item)
    return {"processed": len(changed), "business_process_status": target_status, "items": [_record_dict(item, await _allowed_field_keys(identity, db)) for item in changed]}


@router.post(f"{settings.api_prefix}/documents/official/receipt-date")
async def update_official_receipt_date(body: OfficialDocumentReceiptDateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Correct the incoming-document date without using the generic record API.

    Legacy FIO supported this as a selected-row batch action.  It is metadata,
    not a document lifecycle transition, so registration/sign/archive status is
    deliberately left unchanged while every corrected document receives an
    independent audit event.
    """
    from app.core.permissions import (
        _ensure_record_visible, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    record_ids = list(dict.fromkeys(body.record_ids))
    if not record_ids:
        raise HTTPException(status_code=422, detail="请选择至少一条官文收文记录")
    changed: list[BusinessRecord] = []
    for record_id in record_ids:
        item = await _ensure_record_visible(record_id, identity, db)
        if item.module != "document" or (item.data or {}).get("direction", "收文") != "收文":
            raise HTTPException(status_code=422, detail="所选记录不是官文收文")
        await _require_record_owner_or_manager(item, identity, db)
        data = dict(item.data or {})
        previous_date = str(data.get("document_date") or data.get("received_at") or "")
        target_date = str(body.document_date)
        if previous_date == target_date:
            continue
        data.update({"document_date": target_date, "received_at": target_date})
        item.data = data
        db.add(WorkflowEvent(
            record_id=item.id,
            action="修改官文收文日期",
            from_status=item.status,
            to_status=item.status,
            operator=identity["username"],
            comment=body.comment.strip() or f"{previous_date or '未填写'} → {target_date}",
        ))
        changed.append(item)
    await db.commit()
    for item in changed:
        await db.refresh(item)
    return {"updated": len(changed), "document_date": str(body.document_date), "items": [_record_dict(item, await _allowed_field_keys(identity, db)) for item in changed]}


@router.post(f"{settings.api_prefix}/documents/official/delete")
async def delete_official_documents(body: OfficialDocumentDeleteInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Remove selected incoming documents only while they remain unprocessed.

    This is intentionally separate from generic record deletion so the official
    receipt lifecycle cannot be bypassed from a document list.
    """
    from app.core.permissions import (
        _ensure_record_visible, _require_record_owner_or_manager,
    )
    record_ids = list(dict.fromkeys(body.record_ids))
    attachment_paths: list[Path] = []
    deleted = 0
    for record_id in record_ids:
        item = await _ensure_record_visible(record_id, identity, db)
        if item.module != "document" or (item.data or {}).get("direction", "收文") != "收文":
            raise HTTPException(status_code=422, detail="所选记录不是官文收文")
        await _require_record_owner_or_manager(item, identity, db)
        if (item.data or {}).get("business_process_status", "未处理") == "已处理":
            raise HTTPException(status_code=409, detail="已处理的官文收文不能删除，请使用专用撤销或作废流程")
        attachments = (await db.scalars(select(FileAttachment).where(FileAttachment.record_id == item.id))).all()
        attachment_paths.extend(Path(attachment.path) for attachment in attachments)
        for attachment in attachments:
            await db.delete(attachment)
        await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == item.id))
        await db.delete(item)
        deleted += 1
    await db.commit()
    for path in attachment_paths:
        if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
            path.unlink(missing_ok=True)
    return {"deleted": deleted}


@router.post(f"{settings.api_prefix}/documents/official/batch-case-ids")
async def link_official_documents_to_cases(body: OfficialDocumentBatchCaseIdsInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Link selected official incoming documents to cases in one audited batch."""
    from app.core.permissions import (
        _ensure_record_module, _ensure_record_visible, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    record_ids = list(dict.fromkeys(body.record_ids))
    case_ids = list(dict.fromkeys(body.case_ids))
    if not record_ids:
        raise HTTPException(status_code=422, detail="请选择至少一条官文收文记录")
    if not case_ids:
        raise HTTPException(status_code=422, detail="请选择至少一个案件")
    cases: dict[int, BusinessRecord] = {}
    for case_id in case_ids:
        cases[case_id] = await _ensure_record_module(case_id, "case", identity, db)
    changed: list[BusinessRecord] = []
    for record_id in record_ids:
        item = await _ensure_record_visible(record_id, identity, db)
        if item.module != "document" or (item.data or {}).get("direction", "收文") != "收文":
            raise HTTPException(status_code=422, detail="所选记录不是官文收文")
        await _require_record_owner_or_manager(item, identity, db)
        data = dict(item.data or {})
        previous = list(data.get("case_ids") or ([data["case_id"]] if data.get("case_id") else []))
        if previous == case_ids:
            continue
        data["case_ids"] = case_ids
        data["case_id"] = cases[case_ids[0]].id
        data["case_no"] = cases[case_ids[0]].serial_no
        item.data = data
        db.add(WorkflowEvent(
            record_id=item.id, action="批量关联案件", from_status=item.status,
            to_status=item.status, operator=identity["username"],
            comment="、".join(cases[case_id].serial_no for case_id in case_ids),
        ))
        changed.append(item)
    await db.commit()
    for item in changed:
        await db.refresh(item)
    return {"updated": len(changed), "case_ids": case_ids, "items": [_record_dict(item, await _allowed_field_keys(identity, db)) for item in changed]}


@router.get(f"{settings.api_prefix}/official-outgoing")
async def list_official_outgoing_documents(
    status_value: str = "", official_no: str = "", owner: str = "", customer: str = "", case_no: str = "", contract_no: str = "", seal_type: str = "", file_name: str = "",
    application_date_from: date | None = None, application_date_to: date | None = None,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _official_outgoing_dict,
    )
    if application_date_from and application_date_to and application_date_from > application_date_to:
        raise HTTPException(status_code=422, detail="申请起始日期不能晚于结束日期")
    records = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "official_outgoing", *(await _record_scope_conditions(identity, db)),
    ).order_by(BusinessRecord.id.desc()))).all()
    if status_value:
        records = [item for item in records if item.status == status_value]
    if official_no.strip():
        needle = official_no.strip().lower(); records = [item for item in records if needle in item.serial_no.lower()]
    if owner.strip():
        needle = owner.strip().lower(); records = [item for item in records if needle in item.owner.lower()]
    if customer.strip():
        needle = customer.strip().lower(); records = [item for item in records if needle in item.customer.lower()]
    if case_no.strip():
        needle = case_no.strip().lower(); records = [item for item in records if (item.data or {}).get("source_type") == "case" and needle in str((item.data or {}).get("source_serial_no") or "").lower()]
    if contract_no.strip():
        needle = contract_no.strip().lower(); records = [item for item in records if (item.data or {}).get("source_type") == "contract" and needle in str((item.data or {}).get("source_serial_no") or "").lower()]
    if seal_type.strip():
        needle = seal_type.strip().lower(); records = [item for item in records if needle in str((item.data or {}).get("seal_type") or "").lower()]
    if application_date_from:
        records = [item for item in records if item.created_at.date() >= application_date_from]
    if application_date_to:
        records = [item for item in records if item.created_at.date() <= application_date_to]
    if file_name.strip():
        ids = [item.id for item in records]
        matched_ids = set((await db.scalars(select(FileAttachment.record_id).where(FileAttachment.record_id.in_(ids), FileAttachment.original_name.ilike(f"%{file_name.strip()}%")))).all()) if ids else set()
        records = [item for item in records if item.id in matched_ids]
    details = (await db.scalars(select(OfficialOutgoingDocument).where(OfficialOutgoingDocument.record_id.in_([item.id for item in records])))).all() if records else []
    detail_by_record = {item.record_id: item for item in details}
    return {"items": [await _official_outgoing_dict(detail_by_record[item.id], item, identity, db) for item in records if item.id in detail_by_record], "total": len(records)}


@router.post(f"{settings.api_prefix}/official-outgoing", status_code=status.HTTP_201_CREATED)
async def create_official_outgoing_document(body: OfficialOutgoingCreateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _official_outgoing_dict,
    )
    source = await _ensure_record_module(body.source_record_id, body.source_type, identity, db)
    source_file_ids = list(dict.fromkeys(body.source_file_ids))
    files: list[FileAttachment] = []
    if source_file_ids:
        files = (await db.scalars(select(FileAttachment).where(FileAttachment.id.in_(source_file_ids), FileAttachment.record_id == source.id))).all()
        if len(files) != len(source_file_ids):
            raise HTTPException(status_code=422, detail="部分选中文件不属于来源合同或案件，不能发起正式发文")
    elif body.source_type == "contract":
        # 旧系统“由合同创建”未显式选择文件时会带入该合同全部文件；案件仍保持仅带入用户选中文件。
        files = (await db.scalars(select(FileAttachment).where(FileAttachment.record_id == source.id).order_by(FileAttachment.id))).all()
        source_file_ids = [item.id for item in files]
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if not user: raise HTTPException(status_code=401, detail="当前用户不存在")
    if not body.seal_asset_id:
        raise HTTPException(status_code=422, detail="请先选择可用印章类型")
    asset = await db.get(SealAsset, body.seal_asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="所选印章不存在")
    if asset and asset.status != "可用":
        raise HTTPException(status_code=409, detail="所选印章当前不可用")
    official_no = f"FW{datetime.now():%Y%m%d%H%M%S%f}"
    target_status = "草稿"
    record = BusinessRecord(module="official_outgoing", serial_no=official_no, title=body.title.strip(), customer=source.customer, status=target_status, owner=identity["username"], department=user.department, description=body.remark.strip(), data={"content": body.content, "source_type": body.source_type, "source_record_id": source.id, "source_serial_no": source.serial_no, "source_file_ids": source_file_ids, "need_audit": body.need_audit, "seal_asset_id": asset.id if asset else None, "seal_type": asset.seal_type if asset else "", "seal_name": asset.name if asset else "", "is_electronic_seal": body.is_electronic_seal, "is_offline_print": body.is_offline_print, "print_quantity": body.print_quantity})
    db.add(record); await db.flush()
    detail = OfficialOutgoingDocument(record_id=record.id, official_no=official_no, source_type=body.source_type, source_record_id=source.id, source_file_ids=source_file_ids, need_audit=body.need_audit, created_by=identity["username"])
    db.add(detail)
    copied_paths: list[Path] = []
    try:
        for source_file in files:
            source_path = Path(source_file.path)
            if not source_path.is_file() or UPLOAD_ROOT.resolve() not in source_path.resolve().parents:
                raise HTTPException(status_code=409, detail=f"来源附件不存在或不可读取：{source_file.original_name}")
            target = UPLOAD_ROOT / f"{uuid4().hex}{source_path.suffix.lower()}"
            target.write_bytes(source_path.read_bytes())
            copied_paths.append(target)
            db.add(FileAttachment(
                record_id=record.id, category="正式发文附件", original_name=source_file.original_name,
                stored_name=target.name, content_type=source_file.content_type, size=target.stat().st_size,
                path=str(target), uploader=identity["username"], remark=f"从{body.source_type} {source.serial_no}带入；来源附件ID {source_file.id}",
            ))
        db.add(WorkflowEvent(record_id=record.id, action="创建正式发文草稿", to_status=target_status, operator=identity["username"], comment=f"来源{body.source_type} {source.serial_no}；带入附件{len(files)}个"))
        await db.commit(); await db.refresh(record); await db.refresh(detail)
    except Exception:
        await db.rollback()
        for target in copied_paths:
            target.unlink(missing_ok=True)
        raise
    return await _official_outgoing_dict(detail, record, identity, db)


@router.get(f"{settings.api_prefix}/official-outgoing/{{record_id}}")
async def get_official_outgoing_document(record_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _official_outgoing_dict,
    )
    record = await _ensure_record_module(record_id, "official_outgoing", identity, db)
    detail = await db.scalar(select(OfficialOutgoingDocument).where(OfficialOutgoingDocument.record_id == record.id))
    if not detail: raise HTTPException(status_code=404, detail="正式发文详情不存在")
    return await _official_outgoing_dict(detail, record, identity, db)


@router.patch(f"{settings.api_prefix}/official-outgoing/{{record_id}}")
async def update_official_outgoing_document(record_id: int, body: OfficialOutgoingUpdateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Edit the mutable draft fields without breaking source-file provenance.

    The legacy Edit action changes the outgoing document itself.  Source contract/case
    and copied files remain immutable here; changing either would make the stored
    attachment provenance and later stamp/audit history misleading.
    """
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _official_outgoing_dict,
    )
    record = await _ensure_record_module(record_id, "official_outgoing", identity, db)
    await _require_record_owner_or_manager(record, identity, db)
    if record.status not in {"草稿", "已拒绝", "已撤回"}:
        raise HTTPException(status_code=409, detail="仅草稿、已拒绝或已撤回正式发文可以编辑")
    detail = await db.scalar(select(OfficialOutgoingDocument).where(OfficialOutgoingDocument.record_id == record.id))
    if not detail:
        raise HTTPException(status_code=409, detail="正式发文详情已失效")
    asset = await db.get(SealAsset, body.seal_asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="所选印章不存在")
    if asset.status != "可用":
        raise HTTPException(status_code=409, detail="所选印章当前不可用")
    previous_data = dict(record.data or {})
    before = {
        "title": record.title, "need_audit": detail.need_audit,
        "seal_asset_id": previous_data.get("seal_asset_id"),
        "is_electronic_seal": bool(previous_data.get("is_electronic_seal")),
        "is_offline_print": bool(previous_data.get("is_offline_print", True)),
        "print_quantity": int(previous_data.get("print_quantity") or 1),
        "content": previous_data.get("content", ""), "remark": record.description,
    }
    record.title = body.title.strip()
    record.description = body.remark.strip()
    record.data = {
        **previous_data,
        "need_audit": body.need_audit,
        "seal_asset_id": asset.id,
        "seal_type": asset.seal_type,
        "seal_name": asset.name,
        "is_electronic_seal": body.is_electronic_seal,
        "is_offline_print": body.is_offline_print,
        "print_quantity": body.print_quantity,
        "content": body.content,
    }
    detail.need_audit = body.need_audit
    after = {
        "title": record.title, "need_audit": detail.need_audit,
        "seal_asset_id": asset.id, "is_electronic_seal": body.is_electronic_seal,
        "is_offline_print": body.is_offline_print, "print_quantity": body.print_quantity,
        "content": body.content, "remark": record.description,
    }
    db.add(WorkflowEvent(
        record_id=record.id, action="编辑正式发文", from_status=record.status,
        to_status=record.status, operator=identity["username"],
        comment=json.dumps({"before": before, "after": after}, ensure_ascii=False),
    ))
    await db.commit(); await db.refresh(record); await db.refresh(detail)
    return await _official_outgoing_dict(detail, record, identity, db)


@router.post(f"{settings.api_prefix}/official-outgoing/{{record_id}}/submit")
async def submit_official_outgoing_document(record_id: int, body: OfficialOutgoingSubmitInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _official_outgoing_dict,
    )
    record = await _ensure_record_module(record_id, "official_outgoing", identity, db)
    await _require_record_owner_or_manager(record, identity, db)
    if record.status not in {"草稿", "已拒绝", "已撤回"}: raise HTTPException(status_code=409, detail="仅草稿、已拒绝或已撤回正式发文可以提交")
    detail = await db.scalar(select(OfficialOutgoingDocument).where(OfficialOutgoingDocument.record_id == record.id))
    if not detail: raise HTTPException(status_code=409, detail="正式发文详情已失效")
    attachment_count = await db.scalar(select(func.count(FileAttachment.id)).where(FileAttachment.record_id == record.id)) or 0
    if attachment_count <= 0: raise HTTPException(status_code=422, detail="请至少上传或带入一份正式发文文件后再提交")
    asset_id = int((record.data or {}).get("seal_asset_id") or 0)
    asset = await db.get(SealAsset, asset_id) if asset_id else None
    if not asset: raise HTTPException(status_code=422, detail="请先选择可用印章类型")
    if asset.status != "可用": raise HTTPException(status_code=409, detail="所选印章当前不可用，不能提交")
    previous = record.status; need_audit = bool((record.data or {}).get("need_audit", True)); record.status = "待审批" if need_audit else "已通过"
    db.add(WorkflowEvent(record_id=record.id, action="提交正式发文审批" if need_audit else "提交免审正式发文", from_status=previous, to_status=record.status, operator=identity["username"], comment=body.comment.strip() or f"附件{attachment_count}份；印章：{asset.seal_type}"))
    await db.commit(); await db.refresh(record)
    return await _official_outgoing_dict(detail, record, identity, db)


@router.post(f"{settings.api_prefix}/official-outgoing/{{record_id}}/stamp-file")
async def upload_official_outgoing_stamp_file(record_id: int, file: UploadFile = File(...), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _official_outgoing_dict,
    )
    record = await _ensure_record_module(record_id, "official_outgoing", identity, db)
    if identity.get("role") not in {"admin", "manager", "auditor"}: raise HTTPException(status_code=403, detail="当前角色没有标记正式发文盖章权限")
    if record.status != "已通过": raise HTTPException(status_code=409, detail="仅审批通过的正式发文可以上传盖章文件")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".png", ".jpg", ".jpeg", ".zip"}: raise HTTPException(status_code=422, detail="不支持的盖章文件格式")
    content = await file.read()
    if not content: raise HTTPException(status_code=422, detail="请先选择盖章文件")
    if len(content) > 20 * 1024 * 1024: raise HTTPException(status_code=413, detail="单个盖章文件不能超过 20MB")
    detail = await db.scalar(select(OfficialOutgoingDocument).where(OfficialOutgoingDocument.record_id == record.id))
    if not detail: raise HTTPException(status_code=409, detail="正式发文详情已失效")
    target = UPLOAD_ROOT / f"{uuid4().hex}{suffix}"; target.write_bytes(content)
    previous_file = await db.get(FileAttachment, detail.stamp_attachment_id) if detail.stamp_attachment_id else None
    attachment = FileAttachment(record_id=record.id, category="正式发文盖章文件", original_name=Path(file.filename or target.name).name, stored_name=target.name, content_type=file.content_type or "application/octet-stream", size=len(content), path=str(target), uploader=identity["username"], remark="正式发文盖章后上传")
    db.add(attachment); await db.flush(); previous = record.status; detail.stamp_attachment_id = attachment.id; record.status = "已盖章"
    db.add(WorkflowEvent(record_id=record.id, action="上传正式发文盖章文件", from_status=previous, to_status="已盖章", operator=identity["username"], comment=attachment.original_name))
    await db.commit(); await db.refresh(record); await db.refresh(detail)
    if previous_file:
        previous_path = Path(previous_file.path); await db.delete(previous_file); await db.commit()
        if previous_path.is_file() and UPLOAD_ROOT.resolve() in previous_path.resolve().parents: previous_path.unlink(missing_ok=True)
    return await _official_outgoing_dict(detail, record, identity, db)


@router.post(f"{settings.api_prefix}/official-outgoing/download")
async def download_official_outgoing_documents(body: OfficialOutgoingBatchInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    record_ids = list(dict.fromkeys(body.record_ids)); records = [await _ensure_record_module(record_id, "official_outgoing", identity, db) for record_id in record_ids]
    if any(record.status not in {"已通过", "已盖章"} for record in records): raise HTTPException(status_code=409, detail="仅审批通过或已盖章的正式发文可以打包下载")
    attachments = (await db.scalars(select(FileAttachment).where(FileAttachment.record_id.in_(record_ids)).order_by(FileAttachment.id))).all()
    output = io.BytesIO(); included = 0
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for attachment in attachments:
            path = Path(attachment.path)
            if not path.is_file() or UPLOAD_ROOT.resolve() not in path.resolve().parents: continue
            record = next(item for item in records if item.id == attachment.record_id)
            archive.writestr(f"{record.serial_no}/{attachment.id}-{Path(attachment.original_name).name}", path.read_bytes()); included += 1
    if not included: raise HTTPException(status_code=404, detail="所选正式发文没有可下载的附件")
    output.seek(0); filename = f"official-outgoing-{date.today():%Y%m%d}.zip"
    return StreamingResponse(output, media_type="application/zip", headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.post(f"{settings.api_prefix}/official-outgoing/mark-stamped")
async def mark_official_outgoing_documents_stamped(body: OfficialOutgoingBatchInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Mark approved outgoing documents as stamped without fabricating a file.

    The legacy Print action records the seal completion itself and its optional
    stamp-file upload is a separate action.  Keep the two commands independent
    so a missing scan does not block the real seal-status lifecycle.
    """
    from app.core.permissions import (
        _ensure_record_module,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有标记正式发文盖章权限")
    record_ids = list(dict.fromkeys(body.record_ids))
    records = [await _ensure_record_module(record_id, "official_outgoing", identity, db) for record_id in record_ids]
    invalid = [record.serial_no for record in records if record.status != "已通过"]
    if invalid:
        raise HTTPException(status_code=409, detail=f"仅审批通过的正式发文可以标记已盖章：{'、'.join(invalid[:3])}")
    for record in records:
        record.status = "已盖章"
        db.add(WorkflowEvent(record_id=record.id, action="标记正式发文已盖章", from_status="已通过", to_status="已盖章", operator=identity["username"], comment="未上传盖章文件；沿用旧系统标记用印操作"))
    await db.commit()
    return {"processed": len(records), "record_ids": record_ids, "status": "已盖章"}


@router.post(f"{settings.api_prefix}/official-outgoing/{{record_id}}/review")
async def review_official_outgoing_document(record_id: int, body: OfficialOutgoingReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _official_outgoing_dict,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}: raise HTTPException(status_code=403, detail="当前角色没有正式发文审批权限")
    record = await _ensure_record_module(record_id, "official_outgoing", identity, db)
    if record.status != "待审批": raise HTTPException(status_code=409, detail="仅待审批正式发文可以审核")
    detail = await db.scalar(select(OfficialOutgoingDocument).where(OfficialOutgoingDocument.record_id == record.id))
    if not detail: raise HTTPException(status_code=409, detail="正式发文详情已失效")
    comment = body.comment.strip()
    if not body.approved and not comment:
        raise HTTPException(status_code=422, detail="拒绝正式发文必须填写审核意见")
    target = "已通过" if body.approved else "已拒绝"; previous = record.status; record.status = target
    db.add(WorkflowEvent(record_id=record.id, action="正式发文审批通过" if body.approved else "正式发文审批拒绝", from_status=previous, to_status=target, operator=identity["username"], comment=comment))
    await db.commit(); await db.refresh(record); return await _official_outgoing_dict(detail, record, identity, db)


@router.post(f"{settings.api_prefix}/official-outgoing/{{record_id}}/rollback")
async def rollback_official_outgoing_document(record_id: int, body: OfficialOutgoingRollbackInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _official_outgoing_dict,
    )
    record = await _ensure_record_module(record_id, "official_outgoing", identity, db)
    await _require_record_owner_or_manager(record, identity, db)
    if record.status not in {"待审批", "已拒绝"}: raise HTTPException(status_code=409, detail="仅待审批或已拒绝正式发文可以撤回")
    previous = record.status; record.status = "已撤回"
    db.add(WorkflowEvent(record_id=record.id, action="撤回正式发文", from_status=previous, to_status="已撤回", operator=identity["username"], comment=body.reason))
    await db.commit(); await db.refresh(record)
    detail = await db.scalar(select(OfficialOutgoingDocument).where(OfficialOutgoingDocument.record_id == record.id))
    return await _official_outgoing_dict(detail, record, identity, db)


@router.post(f"{settings.api_prefix}/documents/official/upload", status_code=status.HTTP_201_CREATED)
async def upload_official_document(
    file: UploadFile = File(...), document_date: date = Form(...),
    category: str = Form("收文附件"), remark: str = Form(""), case_ids: str = Form(""),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    from app.core.system import (
        _record_dict,
    )
    suffix = Path(file.filename or "").suffix.lower()
    allowed = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".png", ".jpg", ".jpeg", ".zip", ".rar"}
    if suffix not in allowed:
        raise HTTPException(status_code=422, detail="不支持的文件格式")
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="单个文件不能超过 20MB")
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if not user:
        raise HTTPException(status_code=401, detail="当前用户不存在")
    original_name = Path(file.filename or f"official{suffix}").name
    stored_name = f"{uuid4().hex}{suffix}"
    target = UPLOAD_ROOT / stored_name
    target.write_bytes(content)
    linked_case_ids = [int(value) for value in case_ids.replace("，", ",").replace(";", ",").split(",") if str(value).strip().isdigit()]
    linked_cases: dict[int, BusinessRecord] = {}
    for case_id in dict.fromkeys(linked_case_ids):
        linked_cases[case_id] = await _ensure_record_module(case_id, "case", identity, db)
    now = datetime.now()
    official_data = {
        "direction": "收文", "document_date": str(document_date), "received_at": str(document_date),
        "uploaded_at": str(document_date), "uploader": identity["username"],
        "import_status": "已导入", "business_process_status": "未处理",
    }
    if linked_cases:
        first_case = linked_cases[linked_case_ids[0]]
        official_data.update({
            "case_ids": list(dict.fromkeys(linked_case_ids)),
            "case_id": first_case.id, "case_no": first_case.serial_no,
        })
    record = BusinessRecord(
        module="document", serial_no=f"SW{now:%Y%m%d%H%M%S%f}", title=original_name,
        customer="", status="待签收", owner=identity["username"], department=user.department,
        description=remark,
        data=official_data,
    )
    try:
        db.add(record)
        await db.flush()
        attachment = FileAttachment(
            record_id=record.id, category=category or "收文附件", original_name=original_name,
            stored_name=stored_name, content_type=file.content_type or "application/octet-stream",
            size=len(content), path=str(target), uploader=identity["username"], remark=remark,
        )
        db.add(attachment)
        db.add(WorkflowEvent(record_id=record.id, action="上传官文收文", from_status="", to_status="待签收", operator=identity["username"], comment=original_name))
        await db.commit()
        await db.refresh(record)
        await db.refresh(attachment)
    except Exception:
        await db.rollback()
        target.unlink(missing_ok=True)
        raise
    return {"record": _record_dict(record), "attachment": _attachment_dict(attachment, record)}
