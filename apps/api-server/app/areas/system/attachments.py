"""系统附件上传、查看与删除接口。"""
from fastapi import APIRouter
import jwt
from app.core.storage import _xls_preview_sheets
from app.core.constants import AI_SPACE_CATEGORY, ARCHIVE_REQUIRED_CATEGORIES, ATTACHMENT_TEXT_PREVIEW_MAX_CHARS, CASE_FORMAL_DOCUMENT_FOLDERS, FINANCE_DEFAULT_VOUCHER_CATEGORY, INVESTIGATION_MATERIAL_CATEGORIES, JAR_FEE_MODULE, PDF_PREVIEW_MAX_DIMENSION, PDF_PREVIEW_MAX_PIXELS, PDF_PREVIEW_MAX_WIDTH, PDF_PREVIEW_MIN_WIDTH, SEAL_APPLICATION_FILE_CATEGORY, SEAL_STAMPED_FILE_CATEGORY, UPLOAD_ROOT, logger
from app.core.dependencies import AsyncSession, BusinessRecord, CaseTypeFileTypeRelation, Depends, Document, File, FileAttachment, FileResponse, FinanceTransaction, Form, HTTPException, JSONResponse, Path, Query, Response, SystemParameter, UploadFile, User, WorkflowEvent, current_identity, date, datetime, func, get_db, select, settings, status, timedelta, timezone, uuid4
from starlette.concurrency import run_in_threadpool

router = APIRouter()


def _docx_preview_text(path: Path) -> str:
    document = Document(path)
    parts = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    for index, table in enumerate(document.tables, start=1):
        rows = [" | ".join(cell.text.strip() for cell in row.cells) for row in table.rows]
        if rows:
            parts.append(f"表格 {index}：\n" + "\n".join(rows))
    return "\n\n".join(parts) or "（该 DOCX 文档没有可提取的文字内容）"


@router.get(f"{settings.api_prefix}/attachments")
async def list_attachments(
    record_id: int | None = None,
    case_id: int | None = Query(default=None, ge=1),
    finance_transaction_id: int | None = None,
    category: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.formatters import (
        _person_display_name, _user_display_map,
    )
    from app.core.permissions import (
        _ensure_attachment_record_visible, _filter_visible_attachments,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    record = None
    if case_id is not None and record_id is None:
        raise HTTPException(status_code=422, detail="案件附件查询必须指定关联记录")
    if record_id is not None:
        if case_id is not None:
            from app.core.case_documents import case_attachment_parent
            record = await case_attachment_parent(case_id, record_id, identity, db)
        else:
            record = await _ensure_attachment_record_visible(record_id, identity, db)
        if record.module == JAR_FEE_MODULE:
            raise HTTPException(status_code=409, detail="JAR交案费文件必须使用交案费专用文件接口")
    conditions = []
    if record_id is not None:
        conditions.append(FileAttachment.record_id == record_id)
    if finance_transaction_id is not None:
        conditions.append(FileAttachment.finance_transaction_id == finance_transaction_id)
    if category:
        conditions.append(FileAttachment.category == category)
    items = (await db.scalars(select(FileAttachment).where(*conditions).order_by(FileAttachment.created_at.desc(), FileAttachment.id.desc()))).all()
    if case_id is None and not (record and record.module == "task"):
        items = await _filter_visible_attachments(items, identity, db)
    total = len(items)
    items = items[(page - 1) * page_size:(page - 1) * page_size + page_size]
    record_ids = {item.record_id for item in items if item.record_id}
    records = {record.id: record for record in (await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(record_ids)))).all()} if record_ids else {}
    uploader_usernames = {item.uploader for item in items if item.uploader}
    uploader_users = await _user_display_map(uploader_usernames, db)
    uploader_names = {username: _person_display_name(user.display_name, user.username)[0] for username, user in uploader_users.items()}
    return {
        "items": [_attachment_dict(item, records.get(item.record_id), uploader_names) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
        "required_archive_categories": sorted(ARCHIVE_REQUIRED_CATEGORIES),
    }

@router.get(f"{settings.api_prefix}/attachments/{{attachment_id}}")
async def get_attachment(attachment_id: int, case_id: int | None = Query(default=None, ge=1), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.areas.aws.receipt_sources import can_read_receipt_attachment
    from app.core.formatters import (
        _person_display_name, _user_display_map,
    )
    from app.core.permissions import (
        _ensure_attachment_record_visible,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    item = await db.get(FileAttachment, attachment_id)
    if not item:
        raise HTTPException(status_code=404, detail="附件不存在")
    record = None
    if item.record_id:
        if case_id is not None:
            from app.core.case_documents import case_attachment_parent
            record = await case_attachment_parent(case_id, item.record_id, identity, db)
        elif await can_read_receipt_attachment(item, identity, db):
            record = await db.get(BusinessRecord, item.record_id)
        else:
            record = await _ensure_attachment_record_visible(item.record_id, identity, db)
    elif case_id is not None:
        raise HTTPException(status_code=404, detail="附件不属于该案件")
    elif identity.get("role") != "admin" and item.uploader != identity["username"]:
        raise HTTPException(status_code=404, detail="附件不存在或无权访问")
    uploader_users = await _user_display_map({item.uploader}, db)
    uploader_names = {username: _person_display_name(user.display_name, user.username)[0] for username, user in uploader_users.items()}
    return _attachment_dict(item, record, uploader_names)

@router.post(f"{settings.api_prefix}/attachments", status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    file: UploadFile = File(...), record_id: int | None = Form(None),
    finance_transaction_id: int | None = Form(None),
    source_case_id: int | None = Form(None),
    customer_guid: str | None = Form(None), is_license: bool | None = Form(None), document_date: date | None = Form(None),
    category: str = Form("普通附件"), remark: str = Form(""),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.cases import (
        _case_type_parameter_for_value,
    )
    from app.core.crm import (
        _customer_guid,
    )
    from app.core.documents import (
        _case_custom_document_folders, _sync_case_document_readiness, _sync_seal_document_names,
    )
    from app.core.investigation import (
        _sync_investigation_materials,
    )
    from app.core.permissions import (
        _ensure_attachment_record_visible, _ensure_record_module, _ensure_record_visible, _require_case_attachment_upload_access, _require_case_related_attachment_target,
        _require_contract_attachment_write_access, _require_hr_attachment_write_access, _require_record_owner_or_manager, _user_has_job_permission,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    from app.core.tasks import (
        _add_task_message_notifications, _is_task_participant,
    )
    from app.core.investigation_access import ensure_investigation_material_access
    record = None
    source_case = None
    transaction = None
    resolved_case_file_type = None
    customer_metadata_provided = customer_guid is not None or is_license is not None
    if source_case_id is not None and record_id is None:
        raise HTTPException(status_code=422, detail="案件关联文档必须指定客户或合同记录")
    if customer_metadata_provided and record_id is None:
        raise HTTPException(status_code=422, detail="客户专属附件字段只能用于客户记录")
    if finance_transaction_id is not None:
        transaction = await db.get(FinanceTransaction, finance_transaction_id)
        if not transaction:
            raise HTTPException(status_code=404, detail="关联财务流水不存在")
        if record_id is not None and record_id != transaction.finance_record_id:
            raise HTTPException(status_code=409, detail="附件关联费用与财务流水不一致")
        record_id = transaction.finance_record_id
        await _ensure_record_visible(record_id, identity, db)
        expected_category = FINANCE_DEFAULT_VOUCHER_CATEGORY[transaction.transaction_type]
        if category == "普通附件":
            category = expected_category
    if record_id is not None:
        await ensure_investigation_material_access(record_id, identity, db, write=True)
        record = await _ensure_attachment_record_visible(record_id, identity, db)
        if record.module in {"clue", "evidence"}:
            # 审核菜单只授予读取能力，上传仍按真实身份校验原记录和写入范围。
            identity = {**identity, "role": identity["_actual_role"],
                        "role_ids": identity["_actual_role_ids"], "_page_menu_capability": False}
            record = await _ensure_attachment_record_visible(record_id, identity, db)
            await _require_record_owner_or_manager(record, identity, db)
        if record.module == "conflict_review":
            raise HTTPException(status_code=409, detail="利益冲突审查附件必须使用审查专用入口上传")
        if record.module == JAR_FEE_MODULE:
            raise HTTPException(status_code=409, detail="JAR交案费文件必须使用交案费专用文件接口")
        if source_case_id is not None:
            source_case = await _ensure_record_module(source_case_id, "case", identity, db)
            await _require_case_attachment_upload_access(source_case, identity, db)
            await _require_case_related_attachment_target(source_case, record)
            expected_related_category = "合同文档" if record.module == "contract" else "客户文档"
            if category != expected_related_category:
                raise HTTPException(status_code=422, detail=f"案件关联文档类型必须为{expected_related_category}")
        if customer_metadata_provided:
            if record.module != "customer":
                raise HTTPException(status_code=422, detail="客户专属附件字段只能用于客户记录")
            normalized_customer_guid = str(customer_guid or "").strip()
            if not normalized_customer_guid:
                raise HTTPException(status_code=422, detail="客户 Guid 不能为空")
            stored_customer_guid = (record.data or {}).get("customer_guid")
            if "customer_guid" in (record.data or {}) and not str(stored_customer_guid or "").strip():
                raise HTTPException(status_code=422, detail="客户记录 customer_guid 不能为空")
            if normalized_customer_guid != _customer_guid(record):
                raise HTTPException(status_code=409, detail="附件 customer_guid 与客户记录不一致")
        if record.module == "hr" and category != "员工头像":
            category = "员工档案"
        await _require_hr_attachment_write_access(record, category, identity, db)
        if record.module == "ipr_case":
            raise HTTPException(status_code=409, detail="知识产权案件文档请使用案件详情中的专用文档入口上传")
        if record.module == "contract" and not source_case:
            await _require_contract_attachment_write_access(record, identity, db)
        if record.module == "case":
            await _require_case_attachment_upload_access(record, identity, db)
            if category not in {
                "普通附件",
                "案件票据文件",
                AI_SPACE_CATEGORY,
                *CASE_FORMAL_DOCUMENT_FOLDERS,
                *_case_custom_document_folders(record),
            }:
                file_types = list((await db.scalars(select(SystemParameter).where(
                    SystemParameter.category == "case_file_type",
                    SystemParameter.name == category,
                    SystemParameter.is_active.is_(True),
                ).order_by(SystemParameter.id))).all())
                if not file_types:
                    raise HTTPException(status_code=422, detail="案件文件类型不存在或已停用")
                case_type = await _case_type_parameter_for_value(str((record.data or {}).get("case_type") or ""), db)
                if case_type:
                    configured_count = int(await db.scalar(select(func.count()).select_from(CaseTypeFileTypeRelation).where(
                        CaseTypeFileTypeRelation.case_type_id == case_type.id,
                    )) or 0)
                    allowed_ids = set((await db.scalars(select(CaseTypeFileTypeRelation.file_type_id).where(
                        CaseTypeFileTypeRelation.case_type_id == case_type.id,
                    ))).all()) if configured_count else set()
                    resolved_case_file_type = next((item for item in file_types if item.id in allowed_ids), None) if configured_count else file_types[0]
                    if configured_count and not resolved_case_file_type:
                        raise HTTPException(status_code=422, detail="该案件类型不允许使用所选文件类型")
                else:
                    resolved_case_file_type = file_types[0]
        if record.module == "task":
            if not _is_task_participant(record, identity):
                raise HTTPException(status_code=403, detail="只有任务参与人可以上传任务反馈附件")
            if category not in {"任务反馈附件", "任务资料附件"}:
                category = "任务资料附件"
        if record.module == "customer" and not source_case:
            await _require_record_owner_or_manager(record, identity, db)
        if record.module == "seal":
            await _require_record_owner_or_manager(record, identity, db)
            if record.status not in {"草稿", "待用印"}:
                raise HTTPException(status_code=409, detail="仅草稿或待用印用印申请可以上传用印文件")
            if record.status == "待用印":
                if identity.get("role") not in {"admin", "manager"}:
                    raise HTTPException(status_code=403, detail="只有用印管理员可以上传盖章文件")
                category = SEAL_STAMPED_FILE_CATEGORY
            else:
                category = SEAL_APPLICATION_FILE_CATEGORY
        if record.module == "official_outgoing":
            await _require_record_owner_or_manager(record, identity, db)
            if record.status not in {"草稿", "已拒绝", "已撤回"}:
                raise HTTPException(status_code=409, detail="仅草稿、已拒绝或已撤回正式发文可以上传或替换发文文件")
            if category != "正式发文附件":
                category = "正式发文附件"
        if record.module in INVESTIGATION_MATERIAL_CATEGORIES:
            await _require_record_owner_or_manager(record, identity, db)
            if category == "公证书扫描件":
                operator = await db.scalar(select(User).where(User.username == identity["username"]))
                if not operator or not await _user_has_job_permission(operator, "扫描上传", db):
                    raise HTTPException(status_code=403, detail="当前账号没有公证书扫描上传岗位权限")
    suffix = Path(file.filename or "").suffix.lower()
    # 旧普通案件文件库不按扩展名拒收：案件资料常含法院专用格式、加密包和
    # 其他业务文件。文件仍受大小、案件权限和受控下载约束；知识产权
    # 案件继续走自己的专用格式校验接口。
    allowed = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".png", ".jpg", ".jpeg", ".zip", ".rar"}
    is_employee_avatar = bool(record and record.module == "hr" and category == "员工头像")
    if not is_employee_avatar and (not record or record.module != "case") and suffix not in allowed:
        raise HTTPException(status_code=422, detail="不支持的文件格式")
    content = await file.read()
    if is_employee_avatar:
        if suffix not in {".png", ".jpg", ".jpeg", ".gif", ".webp"} or not str(file.content_type or "").lower().startswith("image/"):
            raise HTTPException(status_code=422, detail="头像仅支持 PNG、JPG、GIF 或 WebP 图片")
        if not content:
            raise HTTPException(status_code=422, detail="头像图片不能为空")
        image_signature_valid = (
            (suffix == ".png" and content.startswith(b"\x89PNG\r\n\x1a\n"))
            or (suffix in {".jpg", ".jpeg"} and content.startswith(b"\xff\xd8\xff"))
            or (suffix == ".gif" and content[:6] in {b"GIF87a", b"GIF89a"})
            or (suffix == ".webp" and content.startswith(b"RIFF") and content[8:12] == b"WEBP")
        )
        if not image_signature_valid:
            raise HTTPException(status_code=422, detail="头像文件内容不是有效图片")
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="头像图片不能超过 5MB")
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="单个文件不能超过 20MB")
    try:
        stored_name = f"{uuid4().hex}{suffix}"
        target = UPLOAD_ROOT / stored_name
        target.write_bytes(content)
        item = FileAttachment(record_id=record_id, finance_transaction_id=finance_transaction_id, category=category, file_type_code=resolved_case_file_type.code if resolved_case_file_type else "", original_name=Path(file.filename or stored_name).name, stored_name=stored_name, content_type=file.content_type or "application/octet-stream", size=len(content), path=str(target), uploader=identity["username"], remark=remark, is_license=bool(is_license), document_date=document_date)
        db.add(item)
        await db.flush()
        if record and record.module == "hr" and category == "员工头像":
            record.data = {**(record.data or {}), "avatar_attachment_id": item.id}
            linked_username = str((record.data or {}).get("username") or record.owner or "").strip().lower()
            linked_user = await db.scalar(select(User).where(User.username == linked_username)) if linked_username else None
            if linked_user:
                linked_user.profile = {**(linked_user.profile or {}), "avatar_attachment_id": item.id}
            db.add(WorkflowEvent(record_id=record.id, action="更新员工头像", from_status=record.status, to_status=record.status, operator=identity["username"], comment=item.original_name))
        if source_case:
            db.add(WorkflowEvent(record_id=source_case.id, action="上传案件关联文档", from_status=source_case.status, to_status=source_case.status, operator=identity["username"], comment=f"{category}：{item.original_name}"))
        elif record and record.module == "case":
            await _sync_case_document_readiness(record, db)
            db.add(WorkflowEvent(record_id=record.id, action="上传归档材料", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{category}：{item.original_name}"))
        elif record and record.module in INVESTIGATION_MATERIAL_CATEGORIES:
            await _sync_investigation_materials(record, db)
            db.add(WorkflowEvent(record_id=record.id, action="上传调查材料", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{category}：{item.original_name}"))
            if record.module == "notary" and category == "公证书扫描件" and record.status in {"等待材料", "审核驳回"}:
                previous_notary_status = record.status; record.status = "待审核"; record.data = {**(record.data or {}), "review_due_date": str(date.today() + timedelta(days=30)), "scan_uploaded_at": datetime.now().isoformat(timespec="seconds"), "scan_uploaded_by": identity["username"]}
                clue = await db.get(BusinessRecord, int((record.data or {}).get("clue_id") or 0)); case_record = await db.get(BusinessRecord, int(((record.data or {}).get("case_id") or ((clue.data or {}).get("converted_case_id") if clue else 0)) or 0))
                if case_record and case_record.status == "等待公证书":
                    case_record.status = "等待审核公证书"; db.add(WorkflowEvent(record_id=case_record.id, action="公证书扫描件已上传", from_status="等待公证书", to_status="等待审核公证书", operator=identity["username"], comment=f"公证记录 {record.serial_no}"))
                db.add(WorkflowEvent(record_id=record.id, action="提交公证书审核", from_status=previous_notary_status, to_status="待审核", operator=identity["username"], comment=f"扫描件 {item.original_name}；审核期限 30 日"))
        elif record and record.module == "customer":
            db.add(WorkflowEvent(record_id=record.id, action="上传客户文档", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{category}：{item.original_name}"))
        elif record and record.module == "seal":
            if category == SEAL_APPLICATION_FILE_CATEGORY:
                await _sync_seal_document_names(record, db)
            action = "上传盖章文件" if category == SEAL_STAMPED_FILE_CATEGORY else "上传用印文件"
            db.add(WorkflowEvent(record_id=record.id, action=action, from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{category}：{item.original_name}"))
        elif record and record.module == "official_outgoing":
            db.add(WorkflowEvent(record_id=record.id, action="上传正式发文附件", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{category}：{item.original_name}"))
        elif record and record.module == "task":
            await _add_task_message_notifications(
                record,
                WorkflowEvent(
                    record_id=record.id, action=f"上传{category}",
                    from_status=record.status, to_status=record.status,
                    operator=identity["username"], comment=f"{category}：{item.original_name}",
                ),
                db,
                content=f"已上传{category}：{item.original_name}",
            )
        elif record and transaction:
            db.add(WorkflowEvent(record_id=record.id, action="上传财务凭证", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{transaction.transaction_type}流水 #{transaction.id}｜{category}：{item.original_name}"))
        await db.commit()
    except Exception:
        await db.rollback()
        target.unlink(missing_ok=True)
        raise
    await db.refresh(item)
    return _attachment_dict(item, record)

@router.get(f"{settings.api_prefix}/attachments/{{attachment_id}}/download")
async def download_attachment(attachment_id: int, case_id: int | None = Query(default=None, ge=1), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.areas.aws.receipt_sources import can_read_receipt_attachment
    from app.core.investigation_access import ensure_investigation_material_access
    from app.core.permissions import (
        _ensure_attachment_record_visible,
    )
    from app.core.storage import (
        _attachment_storage_path,
    )
    item = await db.get(FileAttachment, attachment_id)
    if not item:
        raise HTTPException(status_code=404, detail="附件不存在")
    if item.record_id:
        if case_id is not None:
            from app.core.case_documents import case_attachment_parent
            record = await case_attachment_parent(case_id, item.record_id, identity, db)
        elif await can_read_receipt_attachment(item, identity, db) or await ensure_investigation_material_access(item.record_id, identity, db):
            record = await db.get(BusinessRecord, item.record_id)
        else:
            record = await _ensure_attachment_record_visible(item.record_id, identity, db, allow_clue_audit_read=True)
        if record.module == JAR_FEE_MODULE:
            raise HTTPException(status_code=409, detail="JAR交案费文件必须使用交案费专用下载接口")
    elif case_id is not None:
        raise HTTPException(status_code=404, detail="附件不属于该案件")
    elif identity.get("role") != "admin" and item.uploader != identity["username"]:
        raise HTTPException(status_code=404, detail="附件不存在或无权访问")
    path = _attachment_storage_path(item)
    if path is None:
        raise HTTPException(status_code=404, detail="附件文件不存在")
    return FileResponse(path, media_type=item.content_type, filename=item.original_name)

@router.get(f"{settings.api_prefix}/attachments/{{attachment_id}}/preview")
async def preview_attachment(attachment_id: int, case_id: int | None = Query(default=None, ge=1), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """校验访问范围并返回附件在线预览所需内容。"""
    from app.areas.aws.receipt_sources import can_read_receipt_attachment
    from app.core.investigation_access import ensure_investigation_material_access
    from app.core.permissions import (
            _ensure_attachment_record_visible,
        )
    from app.core.storage import (
            _attachment_storage_path, _xlsx_preview_text,
        )
    item = await db.get(FileAttachment, attachment_id)
    if not item:
        raise HTTPException(status_code=404, detail="附件不存在")
    if item.record_id:
        if case_id is not None:
            from app.core.case_documents import case_attachment_parent
            await case_attachment_parent(case_id, item.record_id, identity, db)
        elif not (await can_read_receipt_attachment(item, identity, db) or await ensure_investigation_material_access(item.record_id, identity, db)):
            await _ensure_attachment_record_visible(item.record_id, identity, db, allow_clue_audit_read=True)
    elif case_id is not None:
        raise HTTPException(status_code=404, detail="附件不属于该案件")
    elif identity.get("role") != "admin" and item.uploader != identity["username"]:
        raise HTTPException(status_code=404, detail="附件不存在或无权访问")

    path = _attachment_storage_path(item)
    if path is None:
        raise HTTPException(status_code=404, detail="附件文件不存在")

    suffix = Path(item.original_name).suffix.lower()
    content_type = str(item.content_type or "").lower()
    base = {"original_name": item.original_name, "content_type": content_type}
    if suffix == ".docx" and path.stat().st_size == 0:
        return {**base, "kind": "unsupported", "detail": "DOCX 文件为空，无法在线查看，请重新上传有效文件"}
    if content_type.startswith("image/") or suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}:
        return {**base, "kind": "image"}
    if content_type == "application/pdf" or suffix == ".pdf":
        return {**base, "kind": "pdf"}
    if suffix == ".docx":
        try:
            preview_text = await run_in_threadpool(_docx_preview_text, path)
        except Exception as exc:
            raise HTTPException(status_code=422, detail="DOCX 文件无法在线读取") from exc
        if len(preview_text) > ATTACHMENT_TEXT_PREVIEW_MAX_CHARS:
            preview_text = f"{preview_text[:ATTACHMENT_TEXT_PREVIEW_MAX_CHARS]}\n\n[文档内容过长，在线预览仅显示前 200000 个字符]"
        return {**base, "kind": "docx", "text": preview_text}
    if suffix == ".xlsx":
        if path.stat().st_size == 0:
            return {**base, "kind": "unsupported", "detail": "XLSX 文件为空，无法在线查看，请重新上传有效文件"}
        try:
            preview_text = await run_in_threadpool(_xlsx_preview_text, path)
        except Exception as exc:
            raise HTTPException(status_code=422, detail="XLSX 文件无法在线读取") from exc
        return {**base, "kind": "xlsx", "text": preview_text}
    if suffix == ".xls":
        if path.stat().st_size == 0:
            return {**base, "kind": "unsupported", "detail": "XLS 文件为空，无法在线查看，请重新上传有效文件"}
        try:
            sheets, truncated = await run_in_threadpool(_xls_preview_sheets, path)
        except Exception as exc:
            raise HTTPException(status_code=422, detail="XLS 文件无法在线读取") from exc
        return {**base, "kind": "workbook", "sheets": sheets, "truncated": truncated}
    if suffix in {".txt", ".md", ".csv", ".json", ".xml", ".log", ".yaml", ".yml", ".html", ".htm"}:
        try:
            preview_text = await run_in_threadpool(path.read_text, encoding="utf-8", errors="replace")
        except OSError as exc:
            raise HTTPException(status_code=422, detail="文本文件无法在线读取") from exc
        if len(preview_text) > ATTACHMENT_TEXT_PREVIEW_MAX_CHARS:
            preview_text = f"{preview_text[:ATTACHMENT_TEXT_PREVIEW_MAX_CHARS]}\n\n[文件内容过长，在线预览仅显示前 200000 个字符]"
        return {**base, "kind": "text", "text": preview_text}
    return {**base, "kind": "unsupported", "detail": "当前文件格式暂不支持在线预览，请下载后查看"}

@router.get(f"{settings.api_prefix}/attachments/{{attachment_id}}/office-preview")
async def create_office_preview_link(
    attachment_id: int,
    case_id: int | None = Query(default=None, ge=1),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """校验附件访问权限后签发短时 Office 预览地址。"""
    from app.core.investigation_access import ensure_investigation_material_access
    from app.core.permissions import (
        _ensure_attachment_record_visible,
    )
    from app.core.storage import (
        _attachment_storage_path,
    )

    item = await db.get(FileAttachment, attachment_id)
    if not item:
        raise HTTPException(status_code=404, detail="附件不存在")
    if item.record_id:
        if case_id is not None:
            from app.core.case_documents import case_attachment_parent
            await case_attachment_parent(case_id, item.record_id, identity, db)
        elif not await ensure_investigation_material_access(item.record_id, identity, db):
            await _ensure_attachment_record_visible(item.record_id, identity, db, allow_clue_audit_read=True)
    elif case_id is not None:
        raise HTTPException(status_code=404, detail="附件不属于该案件")
    elif identity.get("role") != "admin" and item.uploader != identity["username"]:
        raise HTTPException(status_code=404, detail="附件不存在或无权访问")
    path = _attachment_storage_path(item)
    if path is None:
        raise HTTPException(status_code=404, detail="附件文件不存在")
    suffix = Path(item.original_name).suffix.lower()
    if suffix not in {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}:
        raise HTTPException(status_code=422, detail="该文件不是 Office 文档")
    token = jwt.encode(
        {
            "attachment_id": item.id,
            "purpose": "office-online-preview",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        },
        settings.secret_key,
        algorithm="HS256",
    )
    public_base = settings.office_preview_public_base_url.strip().rstrip("/")
    public_file_name = f"attachment-{item.id}{suffix}"
    source_path = f"{settings.api_prefix}/public/attachments/office-preview/{token}/{public_file_name}"
    return {
        "kind": "office",
        "source_url": f"{public_base}{source_path}" if public_base else source_path,
        "expires_in": 600,
    }

@router.get(f"{settings.api_prefix}/public/attachments/office-preview/{{token}}/{{file_name}}")
async def stream_office_preview_attachment(token: str, file_name: str, db: AsyncSession = Depends(get_db)):
    """使用十分钟有效的令牌提供 Office 文件。"""
    from app.core.storage import (
        _attachment_storage_path,
    )

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("purpose") != "office-online-preview":
            raise ValueError("invalid token purpose")
        attachment_id = int(payload["attachment_id"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Office 预览地址无效或已过期") from exc
    item = await db.get(FileAttachment, attachment_id)
    if not item:
        raise HTTPException(status_code=404, detail="附件不存在")
    suffix = Path(item.original_name).suffix.lower()
    if suffix not in {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}:
        raise HTTPException(status_code=422, detail="该文件不是 Office 文档")
    if file_name != f"attachment-{item.id}{suffix}":
        raise HTTPException(status_code=404, detail="Office 预览文件名不匹配")
    path = _attachment_storage_path(item)
    if path is None:
        raise HTTPException(status_code=404, detail="附件文件不存在")
    return FileResponse(
        path,
        media_type=item.content_type or "application/octet-stream",
        filename=item.original_name,
        content_disposition_type="inline",
        headers={"Cache-Control": "private, max-age=600", "X-Content-Type-Options": "nosniff"},
    )

@router.get(f"{settings.api_prefix}/attachments/{{attachment_id}}/pdf-preview")
async def get_pdf_preview_metadata(
    attachment_id: int, case_id: int | None = Query(default=None, ge=1), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """返回已授权 PDF 的页面信息，页面图像由独立接口提供。"""
    from app.core.storage import (
        _authorized_pdf_preview_attachment, _pdf_preview_page_count, _pdf_preview_response_headers,
    )
    item, path = await _authorized_pdf_preview_attachment(attachment_id, identity, db, case_id)
    page_count = await run_in_threadpool(_pdf_preview_page_count, path)
    page_url_template = (
        f"{settings.api_prefix}/attachments/{item.id}/pdf-preview/pages/{{page}}.png"
        f"?width={{width}}{f'&case_id={case_id}' if case_id is not None else ''}"
    )
    return JSONResponse(
        content={
            "kind": "pdf_pages",
            "original_name": item.original_name,
            "content_type": "application/pdf",
            "page_count": page_count,
            "min_width": PDF_PREVIEW_MIN_WIDTH,
            "max_width": PDF_PREVIEW_MAX_WIDTH,
            "max_dimension": PDF_PREVIEW_MAX_DIMENSION,
            "max_pixels": PDF_PREVIEW_MAX_PIXELS,
            "page_url_template": page_url_template,
        },
        headers=_pdf_preview_response_headers(),
    )

@router.get(f"{settings.api_prefix}/attachments/{{attachment_id}}/pdf-preview/pages/{{page_number}}.png")
async def render_pdf_preview_page(
    attachment_id: int,
    page_number: int,
    width: int = Query(1440, ge=PDF_PREVIEW_MIN_WIDTH, le=PDF_PREVIEW_MAX_WIDTH),
    case_id: int | None = Query(default=None, ge=1),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """在像素上限内渲染已授权的单页 PDF 预览图。"""
    from app.core.storage import (
        _authorized_pdf_preview_attachment, _pdf_preview_response_headers, _render_pdf_preview_page,
    )
    _item, path = await _authorized_pdf_preview_attachment(attachment_id, identity, db, case_id)
    payload = await run_in_threadpool(_render_pdf_preview_page, path, page_number, width)
    headers = _pdf_preview_response_headers()
    headers["Content-Disposition"] = f'inline; filename="attachment-{attachment_id}-page-{page_number}.png"'
    return Response(content=payload, media_type="image/png", headers=headers)

@router.delete(f"{settings.api_prefix}/attachments/{{attachment_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(attachment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.attachment_deletion import (
        attachment_path_referenced, defer_attachment_delete, finish_attachment_delete, restore_attachment_delete, stage_attachment_delete,
    )
    from app.core.documents import (
        _sync_case_document_readiness, _sync_seal_document_names,
    )
    from app.core.investigation import (
        _sync_investigation_materials,
    )
    from app.core.permissions import (
        _ensure_attachment_record_visible, _ensure_case_word_editor_not_locked, _ensure_record_module, _require_case_detail_write_access, _require_contract_attachment_write_access,
        _require_hr_attachment_write_access, _require_record_owner_or_manager,
    )
    from app.core.tasks import (
        _add_task_message_notifications,
    )
    from app.core.investigation_access import ensure_investigation_material_access
    item = await db.get(FileAttachment, attachment_id)
    if not item:
        raise HTTPException(status_code=404, detail="附件不存在")
    if item.record_id:
        await ensure_investigation_material_access(item.record_id, identity, db, write=True)
    # 联系人照片的附件 ID 保存在客户 contacts JSON 中。若允许通用附件接口删除，
    # 会留下指向已删除文件的引用；必须从联系人维护入口替换或随联系人删除。
    if item.category == "客户联系人照片":
        raise HTTPException(status_code=409, detail="联系人照片请在客户联系人中维护")
    record = await db.get(BusinessRecord, item.record_id) if item.record_id else None
    if record and record.module in {"clue", "evidence"} and "admin" not in identity["_actual_role_ids"]:
        raise HTTPException(status_code=403, detail="仅系统管理员可以删除线索或证据附件")
    if record and record.module == "conflict_review":
        raise HTTPException(status_code=409, detail="利益冲突审查证据必须使用审查专用入口管理")
    if record and record.module == "hr" and item.category == "员工头像" and int((record.data or {}).get("avatar_attachment_id") or 0) == item.id:
        raise HTTPException(status_code=409, detail="当前员工头像不能通过附件接口删除，请上传新头像替换")
    if record and record.module == JAR_FEE_MODULE:
        raise HTTPException(status_code=409, detail="JAR fee files must use the dedicated finance endpoint")
    if record and record.module == "ipr_case":
        raise HTTPException(status_code=409, detail="知识产权案件文档请使用案件详情中的专用文档入口删除")
    may_manage_customer_document = False
    may_manage_case_document = False
    may_manage_task_attachment = False
    may_manage_seal_attachment = False
    may_manage_official_outgoing_attachment = False
    if record and record.module == "contract":
        await _require_contract_attachment_write_access(record, identity, db)
    if record and record.module == "task":
        record = await _ensure_attachment_record_visible(record.id, identity, db)
        if item.category not in {"任务反馈附件", "任务资料附件"}:
            raise HTTPException(status_code=422, detail="任务附件类型无效")
        if identity.get("role") != "admin" and item.uploader != identity["username"]:
            raise HTTPException(status_code=403, detail="任务参与人只能删除自己上传的任务附件")
        may_manage_task_attachment = True
    if record and record.module == "case":
        record = await _ensure_record_module(record.id, "case", identity, db)
        await _require_case_detail_write_access(record, identity, db)
        _ensure_case_word_editor_not_locked(item)
        may_manage_case_document = True
    if record and record.module == "customer":
        record = await _ensure_record_module(record.id, "customer", identity, db)
        await _require_record_owner_or_manager(record, identity, db)
        may_manage_customer_document = True
    if record and record.module == "seal":
        record = await _ensure_record_module(record.id, "seal", identity, db)
        await _require_record_owner_or_manager(record, identity, db)
        may_delete_application_file = record.status == "草稿" and item.category == SEAL_APPLICATION_FILE_CATEGORY
        may_delete_stamped_file = (
            record.status == "待用印"
            and item.category == SEAL_STAMPED_FILE_CATEGORY
            and identity.get("role") in {"admin", "manager"}
        )
        if not (may_delete_application_file or may_delete_stamped_file):
            raise HTTPException(status_code=409, detail="当前状态不允许删除该用印附件")
        if item.category not in {SEAL_APPLICATION_FILE_CATEGORY, SEAL_STAMPED_FILE_CATEGORY}:
            raise HTTPException(status_code=422, detail="用印申请附件类型无效")
        may_manage_seal_attachment = True
    if record and record.module == "official_outgoing":
        record = await _ensure_record_module(record.id, "official_outgoing", identity, db)
        await _require_record_owner_or_manager(record, identity, db)
        if record.status not in {"草稿", "已拒绝", "已撤回"}:
            raise HTTPException(status_code=409, detail="仅草稿、已拒绝或已撤回正式发文可以删除发文文件")
        if item.category != "正式发文附件":
            raise HTTPException(status_code=422, detail="已提交正式发文的盖章文件不能通过普通附件删除")
        may_manage_official_outgoing_attachment = True
    may_manage_hr_document = False
    if record and record.module == "hr":
        await _require_hr_attachment_write_access(record, item.category, identity, db)
        may_manage_hr_document = True
    if identity["role"] != "admin" and not may_manage_hr_document and not may_manage_customer_document and not may_manage_case_document and not may_manage_task_attachment and not may_manage_seal_attachment and not may_manage_official_outgoing_attachment:
        raise HTTPException(status_code=403, detail="仅管理员可删除附件；客户负责人可删除客户文档，部门负责人可删除员工档案")
    path = Path(item.path)
    await db.delete(item)
    await db.flush()
    if record and record.module == "case":
        await _sync_case_document_readiness(record, db)
        db.add(WorkflowEvent(record_id=record.id, action="删除归档材料", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{item.category}：{item.original_name}"))
    elif record and record.module in INVESTIGATION_MATERIAL_CATEGORIES:
        material_categories = await _sync_investigation_materials(record, db)
        db.add(WorkflowEvent(record_id=record.id, action="删除调查材料", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{item.category}：{item.original_name}"))
        if record.module == "notary" and item.category == "公证书扫描件" and "公证书扫描件" not in material_categories and record.status == "待审核":
            record.status = "等待材料"; record.data = {**(record.data or {}), "review_due_date": "", "scan_uploaded_at": ""}
            clue = await db.get(BusinessRecord, int((record.data or {}).get("clue_id") or 0)); case_record = await db.get(BusinessRecord, int(((record.data or {}).get("case_id") or ((clue.data or {}).get("converted_case_id") if clue else 0)) or 0))
            if case_record and case_record.status == "等待审核公证书":
                case_record.status = "等待公证书"; db.add(WorkflowEvent(record_id=case_record.id, action="撤回公证书审核", from_status="等待审核公证书", to_status="等待公证书", operator=identity["username"], comment="公证书扫描件已删除"))
            db.add(WorkflowEvent(record_id=record.id, action="撤回公证书审核", from_status="待审核", to_status="等待材料", operator=identity["username"], comment="公证书扫描件已删除"))
    elif record and record.module == "customer":
        db.add(WorkflowEvent(record_id=record.id, action="删除客户文档", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{item.category}：{item.original_name}"))
    elif record and record.module == "seal":
        if item.category == SEAL_APPLICATION_FILE_CATEGORY:
            await _sync_seal_document_names(record, db)
        action = "删除盖章文件" if item.category == SEAL_STAMPED_FILE_CATEGORY else "删除用印文件"
        db.add(WorkflowEvent(record_id=record.id, action=action, from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{item.category}：{item.original_name}"))
    elif record and record.module == "official_outgoing":
        db.add(WorkflowEvent(record_id=record.id, action="删除正式发文附件", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{item.category}：{item.original_name}"))
    elif record and record.module == "task":
        await _add_task_message_notifications(
            record,
            WorkflowEvent(record_id=record.id, action=f"删除{item.category}", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{item.category}：{item.original_name}"),
            db,
            content=f"已删除{item.category}：{item.original_name}",
        )
    elif record and item.finance_transaction_id:
        db.add(WorkflowEvent(record_id=record.id, action="删除财务凭证", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"流水 #{item.finance_transaction_id}｜{item.category}：{item.original_name}"))
    staged = None
    try:
        shared_path = await attachment_path_referenced(db, path, (attachment_id,))
        if not shared_path:
            staged = await run_in_threadpool(stage_attachment_delete, attachment_id, path, UPLOAD_ROOT)
        await db.commit()
    except Exception:
        try:
            await db.rollback()
        finally:
            if staged is not None:
                try:
                    await run_in_threadpool(restore_attachment_delete, staged)
                except Exception:
                    logger.exception("附件删除事务失败后，暂存文件恢复失败：%s", staged.staged.name)
                    raise
        raise
    if staged is not None:
        try:
            still_referenced = await attachment_path_referenced(db, path)
        except Exception as exc:
            await run_in_threadpool(defer_attachment_delete, staged)
            logger.exception("附件记录已删除，但文件引用核验失败：%s", staged.staged.name)
            raise HTTPException(status_code=500, detail="附件记录已删除，但文件引用核验失败；后台将重试") from exc
        try:
            if still_referenced:
                await run_in_threadpool(restore_attachment_delete, staged)
            else:
                await run_in_threadpool(finish_attachment_delete, staged)
        except Exception as exc:
            logger.exception("附件记录已删除，但暂存文件清理失败：%s", staged.staged.name)
            raise HTTPException(status_code=500, detail="附件记录已删除，但文件清理未完成；后台将重试") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
