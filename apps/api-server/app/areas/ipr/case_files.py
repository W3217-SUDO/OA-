"""知识产权案件文件与自定义导入接口。"""
from fastapi import APIRouter
from app.core.constants import IPR_CASE_KINDS, UPLOAD_ROOT
from app.core.dependencies import AsyncSession, BusinessRecord, CPC_APPLICATION_CATEGORY, Depends, File, FileAttachment, Form, HTTPException, IprCaseFileCustomImportBatch, IprCaseFileCustomImportCandidate, Path, Query, Response, SystemParameter, UploadFile, User, WorkflowEvent, current_identity, date, datetime, func, get_db, io, is_cpc_application_attachment, json, or_, select, settings, status, uuid4, zipfile
from app.models_shared import IprCaseFileBatchTransmitInput, IprCaseFileCustomCandidateConfirmInput, IprCaseFileCustomCandidateCorrectInput, IprCaseFileCustomCandidateMatchInput, IprCaseFileTransmitInput

router = APIRouter()


@router.get(f"{settings.api_prefix}/ipr/cases/{{case_id}}/files")
async def list_ipr_case_files(
    case_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    total = int(await db.scalar(select(func.count()).select_from(FileAttachment).where(FileAttachment.record_id == record.id)) or 0)
    items = list((await db.scalars(
        select(FileAttachment)
        .where(FileAttachment.record_id == record.id)
        .order_by(FileAttachment.document_date.desc().nullslast(), FileAttachment.created_at.desc(), FileAttachment.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).all())
    return {
        "items": [_attachment_dict(item, record) for item in items],
        "total": total, "page": page, "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
    }

@router.get(f"{settings.api_prefix}/ipr/case-file-types")
async def list_ipr_case_file_types(case_kind: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _ipr_case_file_type_dict,
    )
    from app.core.permissions import (
        _require_record_module_menu,
    )
    await _require_record_module_menu("ipr_case", identity, db, action="查看")
    if case_kind and case_kind not in IPR_CASE_KINDS:
        raise HTTPException(status_code=422, detail="知识产权案件类型无效")
    rows = list((await db.scalars(select(SystemParameter).where(
        SystemParameter.category == "ipr_case_file_type", SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.sort_order, SystemParameter.id))).all())
    if case_kind:
        rows = [item for item in rows if not (item.extra or {}).get("case_kinds") or case_kind in (item.extra or {}).get("case_kinds", [])]
    return {"items": [_ipr_case_file_type_dict(item) for item in rows]}

@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/files", status_code=status.HTTP_201_CREATED)
async def upload_ipr_case_file(
    case_id: int, file: UploadFile = File(...), category: str = Form(...), document_date: date = Form(...),
    requires_transmission: bool = Form(False), remark: str = Form(""),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """上传带业务日期和移交要求的知识产权案件文件。"""
    from app.core.ipr import (
        _active_ipr_case_file_type,
    )
    from app.core.permissions import (
        _ensure_ipr_case_file_write,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    record = await _ensure_ipr_case_file_write(case_id, identity, db)
    normalized_category = category.strip()
    if not normalized_category or len(normalized_category) > 64:
        raise HTTPException(status_code=422, detail="文档类型不能为空且不能超过 64 个字符")
    if normalized_category == CPC_APPLICATION_CATEGORY:
        raise HTTPException(status_code=422, detail="CPC申报历史只能由专用生成入口创建")
    if len(remark.strip()) > 1000:
        raise HTTPException(status_code=422, detail="文档说明不能超过 1000 个字符")
    file_type = await _active_ipr_case_file_type(record, normalized_category, db)
    type_extra = file_type.extra or {}
    requires_transmission = bool(type_extra.get("requires_transmission"))
    suffix = Path(file.filename or "").suffix.lower()
    allowed = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".png", ".jpg", ".jpeg", ".zip", ".rar"}
    if suffix not in allowed:
        raise HTTPException(status_code=422, detail="不支持的案件文档格式")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="案件文档不能为空")
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="单个案件文档不能超过 20MB")
    original_name = Path(file.filename or "document").name
    if not bool(type_extra.get("allow_repeat", True)):
        duplicate = await db.scalar(select(FileAttachment.id).where(FileAttachment.record_id == record.id, FileAttachment.category == normalized_category))
        if duplicate:
            raise HTTPException(status_code=409, detail="该案件已存在同类型文档，当前文件类型不允许重复上传")
    stored_name = f"{uuid4().hex}{suffix}"
    target = UPLOAD_ROOT / stored_name
    target.write_bytes(content)
    attachment = FileAttachment(
        record_id=record.id, category=normalized_category, file_type_code=file_type.code, original_name=original_name, stored_name=stored_name,
        content_type=file.content_type or "application/octet-stream", size=len(content), path=str(target),
        uploader=identity["username"], remark=remark.strip(), document_date=document_date,
        requires_transmission=requires_transmission,
    )
    try:
        db.add(attachment); await db.flush()
        db.add(WorkflowEvent(record_id=record.id, action="上传知识产权案件文档", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{normalized_category}｜{original_name}｜文档日期 {document_date}" + ("｜待转文" if requires_transmission else "")))
        await db.commit(); await db.refresh(attachment)
    except Exception:
        await db.rollback(); target.unlink(missing_ok=True); raise
    return _attachment_dict(attachment, record)

@router.post(f"{settings.api_prefix}/ipr/case-files/custom-import-batches", status_code=status.HTTP_201_CREATED)
async def create_ipr_case_file_custom_import_batch(
    file: UploadFile = File(...), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """从历史命名文件解析候选项，此步不创建附件。"""
    from app.core.ipr import (
        _active_ipr_case_file_type, _custom_ipr_filename_parts, _ipr_custom_candidate_dict,
    )
    from app.core.permissions import (
        _find_visible_ipr_case_by_legacy_no, _require_record_module_menu,
    )
    await _require_record_module_menu("ipr_case", identity, db, action="导入")
    source_name = Path(file.filename or "").name
    suffix = Path(source_name).suffix.lower()
    allowed = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".png", ".jpg", ".jpeg", ".zip", ".rar"}
    if suffix not in allowed:
        raise HTTPException(status_code=422, detail="不支持的案件文档格式")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="自定义导入源文件不能为空")
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="自定义导入源文件不能超过 20MB")
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    source_path = UPLOAD_ROOT / f"{uuid4().hex}{suffix}"
    parts = _custom_ipr_filename_parts(source_name)
    parsed_case_no, parsed_document_no = parts or ("", "")
    errors: list[str] = []
    record = await _find_visible_ipr_case_by_legacy_no(parsed_case_no, identity, db) if parts else None
    if not parts:
        errors.append("文件名必须符合 A(系统案号)W(文档号).扩展名，例如 A1411137W210403.pdf")
    elif not record:
        errors.append("未匹配到知识产权案件，请人工选择")
    elif record.status != "在办":
        errors.append("匹配案件不是在办状态")
    default_type = "普通知识产权案件文档"
    if record:
        try:
            await _active_ipr_case_file_type(record, default_type, db)
        except HTTPException:
            default_type = ""
            errors.append("未配置可用的默认案件文档类型，请人工选择")
    try:
        source_path.write_bytes(content)
        batch = IprCaseFileCustomImportBatch(source_filename=source_name, source_path=str(source_path), source_size=len(content), is_test=False, created_by=identity["username"], department=user.department if user else "", total_count=1, error_count=1 if errors else 0)
        db.add(batch); await db.flush()
        data = record.data or {} if record else {}
        candidate = IprCaseFileCustomImportCandidate(batch_id=batch.id, ipr_case_id=record.id if record and record.status == "在办" else None, custom_filename=source_name, parsed_case_no=parsed_case_no, parsed_document_no=parsed_document_no, case_kind=str(data.get("case_kind") or ""), application_no=str(data.get("application_no") or ""), file_type=default_type, document_date=date.today(), case_officer=record.owner if record else "", errors=errors, status="待修正" if errors else "待确认")
        db.add(candidate); await db.commit()
    except Exception:
        await db.rollback()
        source_path.unlink(missing_ok=True)
        raise
    await db.refresh(candidate)
    return {"id": batch.id, "status": batch.status, "total_count": 1, "error_count": batch.error_count, "candidate": _ipr_custom_candidate_dict(candidate)}

@router.get(f"{settings.api_prefix}/ipr/case-files/custom-import-batches")
async def list_ipr_case_file_custom_import_batches(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_record_module_menu,
    )
    await _require_record_module_menu("ipr_case", identity, db, action="查看")
    conditions = []
    if identity.get("role") != "admin":
        user = await db.scalar(select(User).where(User.username == identity["username"]))
        if identity.get("role") == "manager" and user:
            conditions.append(or_(IprCaseFileCustomImportBatch.created_by == identity["username"], IprCaseFileCustomImportBatch.department == user.department))
        else:
            conditions.append(IprCaseFileCustomImportBatch.created_by == identity["username"])
    rows = list((await db.scalars(select(IprCaseFileCustomImportBatch).where(*conditions).order_by(IprCaseFileCustomImportBatch.created_at.desc()).limit(100))).all())
    return {"items": [{"id": row.id, "source_filename": row.source_filename, "source_size": row.source_size, "status": row.status, "total_count": row.total_count, "error_count": row.error_count, "imported_count": row.imported_count, "created_by": row.created_by, "department": row.department, "created_at": row.created_at} for row in rows]}

@router.get(f"{settings.api_prefix}/ipr/case-files/custom-import-batches/{{batch_id}}/candidates")
async def list_ipr_case_file_custom_import_candidates(batch_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _ipr_custom_candidate_dict,
    )
    from app.core.permissions import (
        _ensure_ipr_custom_import_batch_visible, _require_record_module_menu,
    )
    await _require_record_module_menu("ipr_case", identity, db, action="查看")
    await _ensure_ipr_custom_import_batch_visible(batch_id, identity, db)
    rows = list((await db.scalars(select(IprCaseFileCustomImportCandidate).where(IprCaseFileCustomImportCandidate.batch_id == batch_id).order_by(IprCaseFileCustomImportCandidate.id))).all())
    return {"items": [_ipr_custom_candidate_dict(row) for row in rows], "total": len(rows)}

@router.post(f"{settings.api_prefix}/ipr/case-files/custom-import-candidates/{{candidate_id}}/match")
async def match_ipr_case_file_custom_import_candidate(candidate_id: int, body: IprCaseFileCustomCandidateMatchInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _ipr_custom_candidate_dict, _refresh_ipr_custom_candidate,
    )
    from app.core.permissions import (
        _ensure_ipr_custom_import_batch_visible, _ensure_record_module, _require_record_module_menu,
    )
    await _require_record_module_menu("ipr_case", identity, db, action="导入")
    candidate = await db.get(IprCaseFileCustomImportCandidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="案件自定义文件候选不存在")
    await _ensure_ipr_custom_import_batch_visible(candidate.batch_id, identity, db)
    if candidate.status == "已导入":
        raise HTTPException(status_code=409, detail="已导入候选不能重新匹配案件")
    record = await _ensure_record_module(body.ipr_case_id, "ipr_case", identity, db)
    candidate.ipr_case_id = record.id; candidate.case_kind = str((record.data or {}).get("case_kind") or ""); candidate.application_no = str((record.data or {}).get("application_no") or ""); candidate.case_officer = candidate.case_officer or record.owner
    await _refresh_ipr_custom_candidate(candidate, identity, db)
    batch = await db.get(IprCaseFileCustomImportBatch, candidate.batch_id); batch.error_count = await db.scalar(select(func.count(IprCaseFileCustomImportCandidate.id)).where(IprCaseFileCustomImportCandidate.batch_id == batch.id, IprCaseFileCustomImportCandidate.status == "待修正")) or 0
    await db.commit(); await db.refresh(candidate)
    return _ipr_custom_candidate_dict(candidate)

@router.patch(f"{settings.api_prefix}/ipr/case-files/custom-import-candidates/{{candidate_id}}")
async def correct_ipr_case_file_custom_import_candidate(candidate_id: int, body: IprCaseFileCustomCandidateCorrectInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _ipr_custom_candidate_dict, _refresh_ipr_custom_candidate,
    )
    from app.core.permissions import (
        _ensure_ipr_custom_import_batch_visible, _require_record_module_menu,
    )
    await _require_record_module_menu("ipr_case", identity, db, action="导入")
    candidate = await db.get(IprCaseFileCustomImportCandidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="案件自定义文件候选不存在")
    await _ensure_ipr_custom_import_batch_visible(candidate.batch_id, identity, db)
    if candidate.status == "已导入":
        raise HTTPException(status_code=409, detail="已导入候选不能修改")
    for key in {"file_type", "document_date", "case_officer", "fee_amount", "fee_type", "fee_response_user"}:
        if key in body.model_fields_set:
            setattr(candidate, key, getattr(body, key))
    await _refresh_ipr_custom_candidate(candidate, identity, db)
    batch = await db.get(IprCaseFileCustomImportBatch, candidate.batch_id); batch.error_count = await db.scalar(select(func.count(IprCaseFileCustomImportCandidate.id)).where(IprCaseFileCustomImportCandidate.batch_id == batch.id, IprCaseFileCustomImportCandidate.status == "待修正")) or 0
    await db.commit(); await db.refresh(candidate)
    return _ipr_custom_candidate_dict(candidate)

@router.post(f"{settings.api_prefix}/ipr/case-files/custom-import-batches/{{batch_id}}/confirm")
async def confirm_ipr_case_file_custom_import_candidates(batch_id: int, body: IprCaseFileCustomCandidateConfirmInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _active_ipr_case_file_type,
    )
    from app.core.permissions import (
        _ensure_ipr_case_file_write, _ensure_ipr_custom_import_batch_visible, _require_record_module_menu,
    )
    await _require_record_module_menu("ipr_case", identity, db, action="导入")
    batch = await _ensure_ipr_custom_import_batch_visible(batch_id, identity, db)
    candidate_ids = list(dict.fromkeys(body.candidate_ids))
    rows = list((await db.scalars(select(IprCaseFileCustomImportCandidate).where(IprCaseFileCustomImportCandidate.batch_id == batch.id, IprCaseFileCustomImportCandidate.id.in_(candidate_ids)))).all())
    if len(rows) != len(candidate_ids):
        raise HTTPException(status_code=404, detail="存在不属于当前批次的案件自定义文件候选")
    ordered = {row.id: row for row in rows}
    source_path = Path(batch.source_path)
    if not source_path.is_file() or UPLOAD_ROOT.resolve() not in source_path.resolve().parents:
        raise HTTPException(status_code=409, detail="自定义导入源文件不存在或不安全，不能确认导入")
    content = source_path.read_bytes()
    paths: list[Path] = []; attachments: list[FileAttachment] = []
    try:
        for candidate_id in candidate_ids:
            candidate = ordered[candidate_id]
            if candidate.status != "待确认" or candidate.errors:
                raise HTTPException(status_code=409, detail=f"候选文件 {candidate.custom_filename} 仍有待修正内容，不能确认导入")
            record = await _ensure_ipr_case_file_write(candidate.ipr_case_id or 0, identity, db)
            file_type = await _active_ipr_case_file_type(record, candidate.file_type, db)
            suffix = Path(candidate.custom_filename).suffix.lower(); stored_name = f"{uuid4().hex}{suffix}"; path = UPLOAD_ROOT / stored_name
            path.write_bytes(content); paths.append(path)
            attachment = FileAttachment(record_id=record.id, category=candidate.file_type, file_type_code=file_type.code, original_name=candidate.custom_filename, stored_name=stored_name, content_type="application/octet-stream", size=len(content), path=str(path), uploader=identity["username"], remark=body.comment.strip(), document_date=candidate.document_date, requires_transmission=bool((file_type.extra or {}).get("requires_transmission")))
            db.add(attachment); await db.flush(); candidate.attachment_id = attachment.id; candidate.status = "已导入"; candidate.confirmed_by = identity["username"]; candidate.confirmed_at = datetime.now()
            db.add(WorkflowEvent(record_id=record.id, action="确认导入知识产权案件自定义文件", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"来源文件 {candidate.custom_filename}；文档号 {candidate.parsed_document_no}"))
            attachments.append(attachment)
        batch.imported_count += len(attachments); batch.error_count = 0; batch.status = "已完成"
        await db.commit()
    except Exception:
        await db.rollback()
        for path in paths: path.unlink(missing_ok=True)
        raise
    return {"created": len(attachments), "attachment_ids": [item.id for item in attachments], "batch_status": batch.status}

@router.post(f"{settings.api_prefix}/ipr/cases/files/batch-upload", status_code=status.HTTP_201_CREATED)
async def batch_upload_ipr_case_file(
    file: UploadFile = File(...), case_ids: str = Form(...), category: str = Form(...), document_date: date = Form(...),
    remark: str = Form(""), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """将一份来源文件批量关联案件，写入前先校验全部目标。"""
    from app.core.ipr import (
        _active_ipr_case_file_type,
    )
    from app.core.permissions import (
        _ensure_ipr_case_file_write,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    try:
        raw_ids = json.loads(case_ids)
    except (TypeError, ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=422, detail="批量上传案件必须是案件 ID 数组")
    if not isinstance(raw_ids, list) or not raw_ids:
        raise HTTPException(status_code=422, detail="请至少选择一个知识产权案件")
    try:
        target_ids = list(dict.fromkeys(int(value) for value in raw_ids))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="批量上传案件 ID 无效")
    if len(target_ids) > 200:
        raise HTTPException(status_code=422, detail="单次最多向 200 个案件批量上传")
    normalized_category = category.strip()
    if not normalized_category or len(normalized_category) > 64 or len(remark.strip()) > 1000:
        raise HTTPException(status_code=422, detail="文件类型或说明不符合要求")
    if normalized_category == CPC_APPLICATION_CATEGORY:
        raise HTTPException(status_code=422, detail="CPC申报历史只能由专用生成入口创建")
    suffix = Path(file.filename or "").suffix.lower()
    allowed = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".png", ".jpg", ".jpeg", ".zip", ".rar"}
    if suffix not in allowed:
        raise HTTPException(status_code=422, detail="不支持的案件文档格式")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="案件文档不能为空")
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="单个案件文档不能超过 20MB")
    # Preflight all targets. No target can receive a file until every target is valid.
    records: list[BusinessRecord] = []
    type_by_record: dict[int, SystemParameter] = {}
    for target_id in target_ids:
        record = await _ensure_ipr_case_file_write(target_id, identity, db)
        file_type = await _active_ipr_case_file_type(record, normalized_category, db)
        if not bool((file_type.extra or {}).get("allow_repeat", True)):
            existing = await db.scalar(select(FileAttachment.id).where(FileAttachment.record_id == record.id, FileAttachment.file_type_code == file_type.code))
            if existing:
                raise HTTPException(status_code=409, detail=f"案件 {record.serial_no} 已存在不允许重复的同类型文档；本批次未写入任何文件")
        records.append(record); type_by_record[record.id] = file_type
    original_name = Path(file.filename or "document").name
    paths: list[Path] = []
    attachments: list[FileAttachment] = []
    try:
        for record in records:
            file_type = type_by_record[record.id]
            stored_name = f"{uuid4().hex}{suffix}"; target = UPLOAD_ROOT / stored_name
            target.write_bytes(content); paths.append(target)
            attachment = FileAttachment(record_id=record.id, category=normalized_category, file_type_code=file_type.code, original_name=original_name, stored_name=stored_name, content_type=file.content_type or "application/octet-stream", size=len(content), path=str(target), uploader=identity["username"], remark=remark.strip(), document_date=document_date, requires_transmission=bool((file_type.extra or {}).get("requires_transmission")))
            attachments.append(attachment); db.add(attachment)
            db.add(WorkflowEvent(record_id=record.id, action="批量上传知识产权案件文档", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"批量上传 {normalized_category}｜{original_name}｜文档日期 {document_date}"))
        await db.commit()
        for attachment in attachments: await db.refresh(attachment)
    except Exception:
        await db.rollback()
        for path in paths: path.unlink(missing_ok=True)
        raise
    return {"created": len(attachments), "items": [_attachment_dict(item, next(record for record in records if record.id == item.record_id)) for item in attachments]}

@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/files/{{attachment_id}}/mark-transmitted")
async def mark_ipr_case_file_transmitted(case_id: int, attachment_id: int, body: IprCaseFileTransmitInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_ipr_case_file_write,
    )
    from app.core.storage import (
        _attachment_dict, _ipr_case_file_attachment,
    )
    record = await _ensure_ipr_case_file_write(case_id, identity, db)
    attachment = await _ipr_case_file_attachment(record, attachment_id, identity, db)
    if not attachment.requires_transmission:
        raise HTTPException(status_code=409, detail="该文档未标记为待转文，不能执行标记已转")
    if attachment.is_transmitted:
        raise HTTPException(status_code=409, detail="该文档已标记为已转")
    attachment.is_transmitted = True; attachment.transmitted_at = datetime.now(); attachment.transmitted_by = identity["username"]
    db.add(WorkflowEvent(record_id=record.id, action="标记知识产权案件文档已转", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{attachment.category}｜{attachment.original_name}" + (f"｜{body.comment.strip()}" if body.comment.strip() else "")))
    await db.commit(); await db.refresh(attachment)
    return _attachment_dict(attachment, record)

@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/files/mark-transmitted")
async def mark_ipr_case_files_transmitted(case_id: int, body: IprCaseFileBatchTransmitInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """按历史移交规则先校验全部待处理文件，再统一写入。"""
    from app.core.permissions import (
        _ensure_ipr_case_file_write,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    record = await _ensure_ipr_case_file_write(case_id, identity, db)
    attachment_ids = list(dict.fromkeys(body.attachment_ids))
    if any(item <= 0 for item in attachment_ids):
        raise HTTPException(status_code=422, detail="待转文文件编号无效")
    rows = list((await db.scalars(select(FileAttachment).where(FileAttachment.id.in_(attachment_ids), FileAttachment.record_id == record.id))).all())
    if len(rows) != len(attachment_ids):
        raise HTTPException(status_code=404, detail="存在不属于当前案件的待转文文件")
    invalid = [item.original_name for item in rows if not item.requires_transmission or item.is_transmitted]
    if invalid:
        raise HTTPException(status_code=409, detail=f"所选文件中存在非待转文或已转文记录：{'、'.join(invalid)}")
    now = datetime.now()
    for item in rows:
        item.is_transmitted = True
        item.transmitted_at = now
        item.transmitted_by = identity["username"]
    db.add(WorkflowEvent(record_id=record.id, action="批量标记知识产权案件文档已转", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"文件数：{len(rows)}；{'、'.join(item.original_name for item in rows)}" + (f"；{body.comment.strip()}" if body.comment.strip() else "")))
    await db.commit()
    return {"updated": len(rows), "items": [_attachment_dict(item, record) for item in rows]}

@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/files/{{attachment_id}}/unlock")
async def unlock_ipr_case_file(case_id: int, attachment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """按历史解锁规则处理生成的申请文件包，解锁后才允许删除。"""
    from app.core.permissions import (
        _ensure_ipr_case_file_write,
    )
    from app.core.storage import (
        _attachment_dict, _ipr_case_file_attachment,
    )
    record = await _ensure_ipr_case_file_write(case_id, identity, db)
    attachment = await _ipr_case_file_attachment(record, attachment_id, identity, db)
    if is_cpc_application_attachment(attachment):
        raise HTTPException(status_code=409, detail="CPC申报历史快照不可解锁或改写")
    if not attachment.is_locked:
        raise HTTPException(status_code=409, detail="该文档未锁定，无需解锁")
    attachment.is_locked = False
    attachment.locked_at = None
    attachment.locked_by = ""
    db.add(WorkflowEvent(record_id=record.id, action="解锁知识产权案件文档", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{attachment.category}｜{attachment.original_name}"))
    await db.commit(); await db.refresh(attachment)
    return _attachment_dict(attachment, record)

@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/files/{{attachment_id}}/generate-application", status_code=status.HTTP_201_CREATED)
async def generate_ipr_case_application_file(case_id: int, attachment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """按历史申请文件规则生成并保存锁定的 ZIP 文件包。"""
    from app.core.permissions import (
        _ensure_ipr_case_file_write,
    )
    from app.core.storage import (
        _attachment_dict, _ipr_case_file_attachment,
    )
    record = await _ensure_ipr_case_file_write(case_id, identity, db)
    attachment = await _ipr_case_file_attachment(record, attachment_id, identity, db)
    if is_cpc_application_attachment(attachment):
        raise HTTPException(status_code=409, detail="CPC申报历史快照不可重新打包")
    if attachment.is_locked:
        raise HTTPException(status_code=409, detail="已生成申请文件包的文档处于锁定状态，请先解锁")
    source_path = Path(attachment.path)
    if not source_path.is_file():
        raise HTTPException(status_code=422, detail="案件文档源文件不存在，无法生成申请文件包")
    source_bytes = source_path.read_bytes()
    if not source_bytes:
        raise HTTPException(status_code=422, detail="案件文档源文件为空，无法生成申请文件包")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(attachment.original_name or attachment.stored_name, source_bytes)
    content = buffer.getvalue()
    stored_name = f"{uuid4().hex}.zip"
    target = UPLOAD_ROOT / stored_name
    target.write_bytes(content)
    package = FileAttachment(
        record_id=record.id, category="知识产权申请文件包", file_type_code="",
        original_name=f"{record.serial_no}-申请文件包-{date.today()}.zip",
        stored_name=stored_name, content_type="application/zip", size=len(content), path=str(target),
        uploader=identity["username"], remark=f"由 {attachment.original_name} 生成", document_date=date.today(),
        is_locked=True, locked_at=datetime.now(), locked_by=identity["username"],
    )
    db.add(package); await db.flush()
    attachment.is_locked = True
    attachment.locked_at = datetime.now()
    attachment.locked_by = identity["username"]
    db.add(WorkflowEvent(record_id=record.id, action="生成知识产权申请文件包", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"源文档：{attachment.original_name}；申请包：{package.original_name}"))
    await db.commit(); await db.refresh(package)
    return _attachment_dict(package, record)

@router.delete(f"{settings.api_prefix}/ipr/cases/{{case_id}}/files/{{attachment_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ipr_case_file(case_id: int, attachment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_ipr_case_file_write,
    )
    from app.core.storage import (
        _ipr_case_file_attachment,
    )
    record = await _ensure_ipr_case_file_write(case_id, identity, db)
    attachment = await _ipr_case_file_attachment(record, attachment_id, identity, db)
    if is_cpc_application_attachment(attachment):
        raise HTTPException(status_code=409, detail="CPC申报历史快照不可删除")
    if attachment.is_locked:
        raise HTTPException(status_code=409, detail="锁定文档必须先解锁才能删除")
    path = Path(attachment.path)
    db.add(WorkflowEvent(record_id=record.id, action="删除知识产权案件文档", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{attachment.category}｜{attachment.original_name}"))
    await db.delete(attachment); await db.commit()
    if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
        path.unlink(missing_ok=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
