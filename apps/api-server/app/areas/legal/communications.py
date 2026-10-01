"""按业务职责组织的 API 路由，保留原有端点行为与注册顺序。"""

from app.core.constants import UPLOAD_ROOT
from app.core.dependencies import (
    AsyncSession, BusinessRecord, CommunicationLog, Depends, File, FileAttachment, HTTPException, Path,
    Query, Response, UploadFile, current_identity, date, datetime, func, get_db, or_, select, settings,
    status, timedelta, uuid4,
)
from app.models_shared import (CommunicationLogInput, CommunicationLogUpdate)
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
