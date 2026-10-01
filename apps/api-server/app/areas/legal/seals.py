"""按业务职责组织的 API 路由，保留原有端点行为与注册顺序。"""

from app.core.conflict_review import (assess_conflict_review, require_conflict_clear)
from app.core.constants import (
    REQUIRED_SEAL_TYPES, SEAL_APPLICATION_FILE_CATEGORY, SEAL_STAMPED_FILE_CATEGORY, UPLOAD_ROOT,
    logger,
)
from app.core.dependencies import (
    AsyncSession, BusinessRecord, Depends, File, FileAttachment, Form, HTTPException, Path, Query,
    Response, SealAsset, SealAssetAudit, StreamingResponse, UploadFile, WorkflowEvent,
    current_identity, date, datetime, delete, func, get_db, io, or_, re, select, settings, status,
    timedelta, uuid4, zipfile,
)
from app.models_shared import (
    AttachmentBatchInput, SealApplicationInput, SealApprovalInput, SealAssetInput, SealAssetUpdate,
    SealBatchApplicationInput, SealBatchStampInput, SealPackageDownloadInput, SealStampInput,
    TaskActionInput,
)
from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

router = APIRouter()


@router.post(f"{settings.api_prefix}/seals/applications/batch/files/delete")
async def batch_delete_seal_attachments(body: AttachmentBatchInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """原子删除草稿用印附件，并在数据库失败时恢复实体文件。"""
    from app.core.attachment_deletion import (
        attachment_path_referenced, defer_attachment_delete, finish_attachment_delete,
        restore_attachment_delete, stage_attachment_delete,
    )
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

    external_paths = set((await db.scalars(select(FileAttachment.path).where(
        FileAttachment.path.in_([str(path) for _, _, path in prepared]),
        FileAttachment.id.notin_(ids),
    ))).all())
    staged = []
    try:
        seen_paths = set()
        for item, _, path in prepared:
            if str(path) in seen_paths or str(path) in external_paths:
                continue
            seen_paths.add(str(path))
            operation = await run_in_threadpool(stage_attachment_delete, item.id, path, UPLOAD_ROOT)
            if operation is None:
                raise HTTPException(status_code=404, detail=f"附件文件 {item.original_name} 不存在")
            staged.append(operation)
        affected: dict[int, BusinessRecord] = {}
        for item, record, _ in prepared:
            affected[record.id] = record
            await db.delete(item)
            db.add(WorkflowEvent(record_id=record.id, action="批量删除用印文件", from_status=record.status, to_status=record.status, operator=identity["username"], comment=item.original_name))
        await db.flush()
        for record in affected.values():
            await _sync_seal_document_names(record, db)
        await db.commit()
    except Exception as transaction_error:
        rollback_error = None
        restore_errors = []
        try:
            await db.rollback()
        except Exception as exc:
            logger.exception("批量用印附件数据库回滚失败")
            rollback_error = exc
        finally:
            for operation in reversed(staged):
                try:
                    await run_in_threadpool(restore_attachment_delete, operation)
                except Exception as exc:
                    logger.exception("批量用印附件事务失败后，暂存文件恢复失败：%s", operation.staged.name)
                    restore_errors.append(exc)
        if rollback_error is not None or restore_errors:
            raise ExceptionGroup(
                "批量用印附件事务与补偿失败",
                [transaction_error, *([rollback_error] if rollback_error is not None else []), *restore_errors],
            )
        raise
    cleanup_error = None
    for operation in staged:
        try:
            if await attachment_path_referenced(db, operation.original):
                await run_in_threadpool(restore_attachment_delete, operation)
            else:
                await run_in_threadpool(finish_attachment_delete, operation)
        except Exception as exc:
            if not operation.lock_file.closed:
                await run_in_threadpool(defer_attachment_delete, operation)
            logger.exception("用印附件记录已删除，但暂存文件协调失败：%s", operation.staged.name)
            cleanup_error = cleanup_error or exc
    if cleanup_error is not None:
        raise HTTPException(status_code=500, detail="用印附件记录已删除，但文件清理未完成；后台将重试") from cleanup_error
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
    await assess_conflict_review(item, identity, db, trigger="contract_seal_submit")
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
    if body.approved:
        await require_conflict_clear(item, db, action="用印审批")
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
    await require_conflict_clear(item, db, action="实际用印")
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
            await require_conflict_clear(item, db, action="批量用印")
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
                        invoice_record_id=source_attachment.invoice_record_id,
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
