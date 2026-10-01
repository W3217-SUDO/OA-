"""按独立业务职责组织的路由，注册顺序与端点行为保持稳定。"""
from app.core.constants import (
    AI_SPACE_CATEGORY,
    AI_SPACE_EDITABLE_SUFFIXES,
    CASE_CUSTOM_DOCUMENT_FOLDERS_KEY,
    UPLOAD_ROOT,
    WORD_DOCUMENT_CONTENT_TYPE,
    WORD_EDITOR_LOCK_SECONDS,
    logger,
)
from app.core.dependencies import (
    AsyncSession,
    BusinessRecord,
    Depends,
    Document,
    FileAttachment,
    HTTPException,
    Path,
    SQLAlchemyError,
    StreamingResponse,
    SystemParameter,
    WorkflowEvent,
    current_identity,
    date,
    get_db,
    io,
    secrets,
    select,
    settings,
    status,
    suppress,
    timedelta,
    update,
    uuid4,
    zipfile,
)
from app.models_shared import (
    AttachmentBatchInput,
    CaseAiDraftCreateInput,
    CaseAiDraftPromoteInput,
    CaseAiDraftUpdateInput,
    CaseAttachmentMoveInput,
    CaseAttachmentRenameInput,
    CaseDocumentFolderInput,
    CaseDocumentFolderRenameInput,
    CaseWordEditorLockInput,
    CaseWordEditorSaveInput,
)
from fastapi import APIRouter

router = APIRouter()

@router.get(f"{settings.api_prefix}/cases/{{case_id}}/document-folders")
async def list_case_document_folders(
    case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.documents import (
        _case_formal_document_folder_payload,
    )
    from app.core.permissions import (
        _ensure_case_read_module,
    )
    record = await _ensure_case_read_module(case_id, identity, db)
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
        _ensure_case_document_folder_name_available, _ensure_record_module, _require_case_action, _require_case_detail_write_access,
    )
    record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_detail_write_access(record, identity, db)
    await _require_case_action(identity, db, "case.document.manage")
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
        _ensure_case_document_folder_name_available, _ensure_record_module, _require_case_action, _require_case_detail_write_access,
    )
    record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_detail_write_access(record, identity, db)
    await _require_case_action(identity, db, "case.document.manage")
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
        _ensure_record_module, _require_case_action, _require_case_detail_write_access,
    )
    record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_detail_write_access(record, identity, db)
    await _require_case_action(identity, db, "case.document.manage")
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
        _ensure_record_module, _require_case_action, _require_case_detail_write_access,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_detail_write_access(record, identity, db)
    await _require_case_action(identity, db, "case.document.manage")
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
        await _ensure_record_module(item.record_id, "case", identity, db)
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
        _require_case_action, _require_case_related_attachment_target,
    )
    await _require_case_action(identity, db, "case.document.delete")
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
        _ensure_record_module, _require_case_action, _require_case_detail_write_access,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_detail_write_access(case_record, identity, db)
    await _require_case_action(identity, db, "case.document.manage")
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
        _ensure_case_word_editor_not_locked, _ensure_record_module, _require_case_action, _require_case_detail_write_access,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_detail_write_access(case_record, identity, db)
    await _require_case_action(identity, db, "case.document.manage")
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
        _ensure_case_word_editor_not_locked, _ensure_record_module, _require_case_action, _require_case_detail_write_access,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    item = await db.get(FileAttachment, attachment_id)
    if not item or not item.record_id:
        raise HTTPException(status_code=404, detail="案件文件不存在")
    case_record = await _ensure_record_module(item.record_id, "case", identity, db)
    await _require_case_detail_write_access(case_record, identity, db)
    await _require_case_action(identity, db, "case.document.manage")
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
