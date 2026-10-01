"""智能文档生成与审核接口。"""
from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool
from app.core.constants import UPLOAD_ROOT
from app.core.dependencies import AgentDocument, AsyncSession, BusinessRecord, Depends, DocumentTemplate, FileAttachment, HTTPException, Path, Response, StreamingResponse, WorkflowEvent, current_identity, datetime, get_db, io, json, select, settings, status, timezone, uuid4
from app.models_shared import AgentDocumentConfirmInput, AgentDocumentInput, AgentDocumentUpdate

router = APIRouter()


@router.get(f"{settings.api_prefix}/agent/documents")
async def list_agent_documents(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _agent_document_dict,
    )
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _agent_document_capabilities, _ensure_agent_document_access,
    )
    items = (await db.scalars(select(AgentDocument).order_by(AgentDocument.created_at.desc()).limit(100))).all()
    accessible_items: list[tuple[AgentDocument, BusinessRecord | None]] = []
    for item in items:
        try:
            _, record = await _ensure_agent_document_access(item.id, identity, db)
        except HTTPException:
            continue
        accessible_items.append((item, record))
    template_ids = {item.template_id for item, _ in accessible_items}; record_ids = {item.record_id for item, _ in accessible_items if item.record_id}
    templates = {x.id: x for x in (await db.scalars(select(DocumentTemplate).where(DocumentTemplate.id.in_(template_ids)))).all()} if template_ids else {}
    records = {x.id: x for x in (await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(record_ids)))).all()} if record_ids else {}
    users_by_username = await _user_display_map({value for item, _record in accessible_items for value in (item.creator, item.confirmed_by)}, db)
    result = []
    for item, visible_record in accessible_items:
        record = visible_record or records.get(item.record_id)
        capabilities = await _agent_document_capabilities(item, identity, db, record)
        result.append(_agent_document_dict(item, templates.get(item.template_id), record, capabilities, users_by_username))
    return {"items": result, "dify_configured": bool(settings.dify_base_url and settings.dify_api_key)}

@router.post(f"{settings.api_prefix}/agent/documents", status_code=status.HTTP_201_CREATED)
async def create_agent_document(body: AgentDocumentInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _agent_document_operation_result, _run_document_agent,
    )
    from app.core.formatters import (
        _sync_agent_document_to_case_ai_space,
    )
    from app.core.permissions import (
        _ensure_record_visible, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    template = await db.get(DocumentTemplate, body.template_id)
    if not template or not template.is_active: raise HTTPException(status_code=404, detail="文书模板不存在或已停用")
    record = await _ensure_record_visible(body.record_id, identity, db) if body.record_id else None
    if record and record.module == "customer":
        await _require_record_owner_or_manager(record, identity, db)
    context = {"模板": template.name, "模板分类": template.category, "要求字段": template.fields, "用户要求": body.instruction}
    if record:
        safe_record = _record_dict(record, await _allowed_field_keys(identity, db))
        context["业务数据"] = {"编号": safe_record["serial_no"], "标题": safe_record["title"], "客户": safe_record["customer"], "负责人": safe_record["owner"], "部门": safe_record["department"], "说明": safe_record["description"], "扩展字段": safe_record["data"]}
    prompt = "请根据以下结构化信息生成正式、严谨、可直接审核的中文法律文书。不得虚构未提供的事实，对缺失信息使用【待补充】标记。\n" + json.dumps(context, ensure_ascii=False, indent=2)
    outline = "\n".join([f"## {field}\n【待补充】" for field in template.fields]) or "## 正文\n【待补充】"
    item = AgentDocument(job_no=f"AI{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid4().hex[:4].upper()}", template_id=template.id, record_id=record.id if record else None, title=body.title.strip(), instruction=body.instruction.strip(), prompt=prompt, content=outline, status="等待生成", creator=identity["username"])
    db.add(item)
    await db.flush()
    await _run_document_agent(item)
    attachment = await _sync_agent_document_to_case_ai_space(item, record, db)
    new_attachment_path = Path(attachment.path) if attachment and attachment.id is None else None
    if record:
        db.add(WorkflowEvent(record_id=record.id, action="创建智能文档", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{item.job_no}｜{template.name}"))
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        if new_attachment_path and UPLOAD_ROOT.resolve() in new_attachment_path.resolve().parents:
            new_attachment_path.unlink(missing_ok=True)
        raise
    await db.refresh(item)
    return _agent_document_operation_result(item, template, record)

@router.post(f"{settings.api_prefix}/agent/documents/{{document_id}}/retry")
async def retry_agent_document(document_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _agent_document_operation_result, _run_document_agent,
    )
    from app.core.formatters import (
        _sync_agent_document_to_case_ai_space,
    )
    from app.core.permissions import (
        _ensure_agent_document_access,
    )
    item, record = await _ensure_agent_document_access(document_id, identity, db, write=True)
    if item.status == "生成中": raise HTTPException(status_code=409, detail="文档正在生成中")
    item.confirmed_by = ""; item.confirmed_at = None; item.confirmed_content_hash = ""
    item.content_version = int(item.content_version or 1) + 1
    await _run_document_agent(item); await _sync_agent_document_to_case_ai_space(item, record, db); await db.commit(); await db.refresh(item)
    return _agent_document_operation_result(item)

@router.patch(f"{settings.api_prefix}/agent/documents/{{document_id}}")
async def update_agent_document(document_id: int, body: AgentDocumentUpdate, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _agent_document_dict,
    )
    from app.core.formatters import (
        _sync_agent_document_to_case_ai_space,
    )
    from app.core.permissions import (
        _ensure_agent_document_access,
    )
    item, record = await _ensure_agent_document_access(document_id, identity, db, write=True)
    if body.title is not None: item.title = body.title.strip()
    if body.content is not None:
        item.content = body.content; item.status = "已编辑"
        item.content_version = int(item.content_version or 1) + 1
        item.confirmed_by = ""; item.confirmed_at = None; item.confirmed_content_hash = ""
    await _sync_agent_document_to_case_ai_space(item, record, db)
    await db.commit(); await db.refresh(item); return _agent_document_dict(item)

@router.post(f"{settings.api_prefix}/agent/documents/{{document_id}}/confirm")
async def confirm_agent_document(document_id: int, body: AgentDocumentConfirmInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _agent_content_hash, _agent_document_dict,
    )
    from app.core.permissions import (
        _ensure_agent_document_access,
    )
    item, record = await _ensure_agent_document_access(document_id, identity, db, write=True)
    if item.status not in {"已生成", "已编辑", "已人工确认"}:
        raise HTTPException(status_code=409, detail="文档生成完成并经人工检查后才能确认")
    if not item.content.strip():
        raise HTTPException(status_code=409, detail="空文档不能确认")
    item.status = "已人工确认"
    item.confirmed_by = identity["username"]
    item.confirmed_at = datetime.now(timezone.utc)
    item.confirmed_content_hash = _agent_content_hash(item.content)
    if record:
        db.add(WorkflowEvent(record_id=record.id, action="人工确认智能文档", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{item.job_no}｜版本 {item.content_version}。{body.comment}"))
    await db.commit(); await db.refresh(item)
    return _agent_document_dict(item, record=record)

@router.get(f"{settings.api_prefix}/agent/documents/{{document_id}}/download")
async def download_agent_document(document_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _agent_content_hash,
    )
    from app.core.permissions import (
        _ensure_agent_document_access,
    )
    from app.core.storage import (
        _docx_bytes,
    )
    item, _ = await _ensure_agent_document_access(document_id, identity, db)
    if item.status != "已人工确认" or not item.confirmed_by or not item.confirmed_at:
        raise HTTPException(status_code=409, detail="智能文档必须先经人工核对确认，才能下载正式 DOCX")
    if item.confirmed_content_hash != _agent_content_hash(item.content):
        raise HTTPException(status_code=409, detail="文档内容在确认后已变化，请重新人工确认后再下载")
    content = await run_in_threadpool(_docx_bytes, item.title, item.content)
    return StreamingResponse(io.BytesIO(content), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": f'attachment; filename="{item.job_no}.docx"'})

@router.post(f"{settings.api_prefix}/agent/documents/{{document_id}}/writeback")
async def writeback_agent_document(document_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _agent_content_hash,
    )
    from app.core.permissions import (
        _ensure_agent_document_access, _require_case_detail_write_access,
    )
    from app.core.storage import (
        _docx_bytes,
    )
    item, record = await _ensure_agent_document_access(document_id, identity, db, write=True)
    if not item.record_id: raise HTTPException(status_code=409, detail="文档未关联业务记录，不能回写")
    if not record: raise HTTPException(status_code=404, detail="关联业务记录已不存在")
    if record.module == "case":
        await _require_case_detail_write_access(record, identity, db)
    if item.status != "已人工确认" or not item.confirmed_by or not item.confirmed_at:
        raise HTTPException(status_code=409, detail="智能文档必须先由人工审核确认，才能回写业务附件")
    if item.confirmed_content_hash != _agent_content_hash(item.content):
        raise HTTPException(status_code=409, detail="文档内容在确认后已变化，请重新人工确认")
    existing = await db.scalar(select(FileAttachment).where(FileAttachment.record_id == record.id, FileAttachment.remark == f"Dify任务 {item.job_no}"))
    if existing:
        raise HTTPException(status_code=409, detail=f"该智能文档已经回写为附件 {existing.original_name}，请勿重复操作")
    content = await run_in_threadpool(_docx_bytes, item.title, item.content)
    stored_name = f"{uuid4().hex}.docx"
    path = UPLOAD_ROOT / stored_name
    temporary = UPLOAD_ROOT / f".{stored_name}.{uuid4().hex}.tmp"
    try:
        await run_in_threadpool(temporary.write_bytes, content)
        await run_in_threadpool(temporary.replace, path)
        attachment = FileAttachment(record_id=record.id, category="智能生成文书", original_name=f"{item.title}.docx", stored_name=stored_name, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", size=len(content), path=str(path), uploader=identity["username"], remark=f"Dify任务 {item.job_no}")
        db.add(attachment)
        db.add(WorkflowEvent(record_id=record.id, action="智能文档回写", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{item.job_no}｜{item.title}"))
        await db.commit()
    except BaseException as original_error:
        failures = [original_error]
        try:
            await db.rollback()
        except BaseException as rollback_error:
            failures.append(rollback_error)
        finally:
            for candidate in (temporary, path):
                try:
                    await run_in_threadpool(candidate.unlink, missing_ok=True)
                except BaseException as cleanup_error:
                    failures.append(cleanup_error)
        if len(failures) > 1:
            raise BaseExceptionGroup("智能文档回写失败且补偿失败", failures) from original_error
        raise
    await db.refresh(attachment)
    return {"attachment_id": attachment.id, "record_id": record.id, "filename": attachment.original_name}

@router.delete(f"{settings.api_prefix}/agent/documents/{{document_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent_document(document_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_agent_document_access,
    )
    item, record = await _ensure_agent_document_access(document_id, identity, db, write=True)
    if identity.get("role") != "admin" and item.creator != identity["username"]: raise HTTPException(status_code=403, detail="只能删除本人创建的智能文档任务")
    if item.confirmed_by or item.confirmed_at or item.status == "已人工确认":
        raise HTTPException(status_code=409, detail="已人工确认的智能文档不得删除，请保留审核与回写审计记录")
    if record:
        written_attachment = await db.scalar(select(FileAttachment).where(FileAttachment.record_id == record.id, FileAttachment.remark == f"Dify任务 {item.job_no}"))
        if written_attachment:
            raise HTTPException(status_code=409, detail="已回写业务附件的智能文档不得删除，请保留附件与审计记录")
        db.add(WorkflowEvent(record_id=record.id, action="删除智能文档任务", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{item.job_no}｜{item.title}"))
    await db.delete(item); await db.commit(); return Response(status_code=status.HTTP_204_NO_CONTENT)
