"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.constants import (
    CASE_DEFENDANT_FIELDS, CASE_PLAINTIFF_FIELDS, CASE_THIRD_PARTY_FIELDS, CUSTOMER_CREATE_DATA_FIELDS, CUSTOMER_CREATE_STATUSES,
    CUSTOMER_LEVELS, CUSTOMER_MODIFICATION_ACTIONS, CUSTOMER_SYSTEM_DATA_FIELDS, FIELD_PERMISSION_DATA_KEYS, UPLOAD_ROOT,
)
from app.core.dependencies import (
    AsyncSession, BusinessRecord, Depends, File, FileAttachment,
    FileResponse, HTTPException, IprCaseCustomerContact, IprCaseLawFirm, LawFirm,
    LawFirmAudit, LawFirmContact, LegacyCustomerHistoryBaseline, LegacyCustomerHistoryContact, LegacyCustomerHistoryCoordinator,
    LegacyCustomerHistoryEvent, LegacyCustomerHistoryFile, Path, Query, Request,
    Response, SystemParameter, UploadFile, User, WorkflowEvent,
    csv, current_identity, date, datetime, func,
    get_db, hash_password, io, json, or_,
    select, settings, status, timedelta, uuid4,
)
from app.models_shared import (
    CustomerActionInput, CustomerContactInput, CustomerContactStatusInput, CustomerCreateInput, CustomerEventInput,
    CustomerKeyChangeInput, CustomerKeyChangeReviewInput, CustomerLevelChangeInput, CustomerLevelReviewInput, CustomerManagersInput,
    CustomerNoteInput, CustomerPatchInput, CustomerPortalActionInput, CustomerPortalActivationInput, CustomerPortalDemandInput,
    CustomerPortalLoginInput, CustomerShareInput, LawFirmContactInput, LawFirmInput, NotaryCertificateInput,
    NotaryReviewInput,
)
from fastapi import APIRouter

router = APIRouter()


@router.get(f"{settings.api_prefix}/law-firms")
async def list_law_firms(keyword: str = "", include_inactive: bool = False, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _law_firm_dict, _law_firm_license,
    )
    from app.core.permissions import (
        _require_admin,
    )
    _require_admin(identity)
    conditions = []
    if not include_inactive: conditions.append(LawFirm.is_active.is_(True))
    if keyword.strip():
        like = f"%{keyword.strip()}%"
        conditions.append(or_(LawFirm.code.ilike(like), LawFirm.name.ilike(like), LawFirm.phone.ilike(like), LawFirm.email.ilike(like), LawFirm.firm_type.ilike(like)))
    total = int(await db.scalar(select(func.count()).select_from(LawFirm).where(*conditions)) or 0)
    items = (await db.scalars(select(LawFirm).where(*conditions).order_by(LawFirm.is_active.desc(), LawFirm.name, LawFirm.id).offset((page - 1) * page_size).limit(page_size))).all()
    licenses = {item.id: await _law_firm_license(item, db) for item in items}
    return {"items": [_law_firm_dict(item, licenses[item.id]) for item in items], "total": total, "page": page, "page_size": page_size}


@router.get(f"{settings.api_prefix}/law-firms/{{law_firm_id}}")
async def get_law_firm(law_firm_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _law_firm_dict, _law_firm_license, _law_firm_or_404,
    )
    from app.core.permissions import (
        _require_admin,
    )
    _require_admin(identity)
    item = await _law_firm_or_404(law_firm_id, db)
    contacts = list((await db.scalars(select(LawFirmContact).where(LawFirmContact.law_firm_id == item.id).order_by(LawFirmContact.id))).all())
    return _law_firm_dict(item, await _law_firm_license(item, db), contacts)


@router.get(f"{settings.api_prefix}/law-firms/{{law_firm_id}}/audits")
async def list_law_firm_audits(law_firm_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _law_firm_audit_dict, _law_firm_or_404,
    )
    from app.core.permissions import (
        _require_admin,
    )
    _require_admin(identity)
    await _law_firm_or_404(law_firm_id, db)
    items = list((await db.scalars(select(LawFirmAudit).where(LawFirmAudit.law_firm_id == law_firm_id).order_by(LawFirmAudit.id.desc()))).all())
    return {"items": [_law_firm_audit_dict(item) for item in items], "total": len(items)}


@router.post(f"{settings.api_prefix}/law-firms", status_code=status.HTTP_201_CREATED)
async def create_law_firm(request: Request, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _create_law_firm_record,
    )
    content_type = (request.headers.get("content-type") or "").lower()
    if "multipart/form-data" in content_type:
        form = await request.form()
        raw: dict[str, object] = {}
        file_value: UploadFile | None = None
        for key, value in form.items():
            if hasattr(value, "read") and hasattr(value, "filename"):
                file_value = value
            else:
                raw[key] = str(value)
        if raw.get("default_contact"):
            raw["default_contact"] = json.loads(str(raw["default_contact"]))
        body = LawFirmInput.model_validate(raw)
        license_bytes = await file_value.read() if file_value else None
        return await _create_law_firm_record(body, identity, db, license_bytes=license_bytes or None, license_filename=file_value.filename if file_value else None)
    raw_body = await request.body()
    if not raw_body:
        raise HTTPException(status_code=422, detail="请求体不能为空")
    body = LawFirmInput.model_validate(json.loads(raw_body.decode("utf-8")))
    return await _create_law_firm_record(body, identity, db)


@router.put(f"{settings.api_prefix}/law-firms/{{law_firm_id}}")
async def update_law_firm(law_firm_id: int, body: LawFirmInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _law_firm_dict, _law_firm_license, _law_firm_or_404,
    )
    from app.core.permissions import (
        _require_admin,
    )
    _require_admin(identity)
    item = await _law_firm_or_404(law_firm_id, db)
    code, name = body.code.strip().upper(), body.name.strip()
    duplicate = await db.scalar(select(LawFirm.id).where(LawFirm.id != item.id, or_(LawFirm.code == code, LawFirm.name == name)))
    if duplicate: raise HTTPException(status_code=409, detail="律所编号或名称已被其他档案使用")
    before = {key: getattr(item, key) for key in body.model_fields if key != "default_contact"}
    for key, value in body.model_dump(exclude={"default_contact"}).items(): setattr(item, key, code if key == "code" else name if key == "name" else value)
    item.updated_by = identity["username"]
    changed = {key: {"before": before[key], "after": getattr(item, key)} for key in before if before[key] != getattr(item, key)}
    if changed: db.add(LawFirmAudit(law_firm_id=item.id, action="修改律所档案", operator=identity["username"], detail=changed))
    await db.commit(); await db.refresh(item)
    return _law_firm_dict(item, await _law_firm_license(item, db))


@router.delete(f"{settings.api_prefix}/law-firms/{{law_firm_id}}")
async def delete_law_firm(law_firm_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _law_firm_license, _law_firm_or_404,
    )
    from app.core.permissions import (
        _require_admin,
    )
    _require_admin(identity)
    item = await _law_firm_or_404(law_firm_id, db)
    linked_case_count = await db.scalar(select(func.count(IprCaseLawFirm.id)).where(IprCaseLawFirm.law_firm_id == item.id)) or 0
    if linked_case_count:
        raise HTTPException(status_code=409, detail=f"该律所已关联 {linked_case_count} 个知识产权案件，解除关联后才能删除")
    attachment = await _law_firm_license(item, db)
    # 当前律所档案尚未允许被合同、用印、财务或文书引用；引用接入后必须先增加相应的删除阻断检查。
    contacts = (await db.scalars(select(LawFirmContact).where(LawFirmContact.law_firm_id == item.id))).all()
    db.add(LawFirmAudit(law_firm_id=item.id, action="删除律所档案", operator=identity["username"], detail={"code": item.code, "name": item.name, "contact_count": len(contacts), "license_attachment_id": attachment.id if attachment else None}))
    await db.flush()
    if attachment:
        await db.delete(attachment)
    for contact in contacts:
        await db.delete(contact)
    await db.delete(item)
    await db.commit()
    if attachment:
        try:
            Path(attachment.path).unlink(missing_ok=True)
        except OSError:
            pass
    return {"deleted": True, "id": law_firm_id}


@router.get(f"{settings.api_prefix}/law-firms/{{law_firm_id}}/contacts")
async def list_law_firm_contacts(law_firm_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _law_firm_contact_dict, _law_firm_or_404,
    )
    from app.core.permissions import (
        _require_admin,
    )
    _require_admin(identity); firm = await _law_firm_or_404(law_firm_id, db)
    items = (await db.scalars(select(LawFirmContact).where(LawFirmContact.law_firm_id == firm.id).order_by(LawFirmContact.is_active.desc(), LawFirmContact.name, LawFirmContact.id))).all()
    return {"items": [_law_firm_contact_dict(item, is_default=item.id == firm.default_contact_id) for item in items], "total": len(items)}


@router.post(f"{settings.api_prefix}/law-firms/{{law_firm_id}}/contacts", status_code=status.HTTP_201_CREATED)
async def create_law_firm_contact(law_firm_id: int, body: LawFirmContactInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _law_firm_contact_dict, _law_firm_or_404,
    )
    from app.core.permissions import (
        _require_admin,
    )
    _require_admin(identity); firm = await _law_firm_or_404(law_firm_id, db)
    item = LawFirmContact(law_firm_id=firm.id, **body.model_dump(), created_by=identity["username"], updated_by=identity["username"])
    db.add(item); await db.flush()
    if firm.default_contact_id is None and item.is_active: firm.default_contact_id = item.id
    db.add(LawFirmAudit(law_firm_id=firm.id, action="新增律所联系人", operator=identity["username"], detail={"contact_id": item.id, "name": item.name}))
    await db.commit(); await db.refresh(item); await db.refresh(firm)
    return _law_firm_contact_dict(item, is_default=item.id == firm.default_contact_id)


@router.put(f"{settings.api_prefix}/law-firms/{{law_firm_id}}/contacts/{{contact_id}}")
async def update_law_firm_contact(law_firm_id: int, contact_id: int, body: LawFirmContactInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _law_firm_contact_dict, _law_firm_or_404,
    )
    from app.core.permissions import (
        _require_admin,
    )
    _require_admin(identity); firm = await _law_firm_or_404(law_firm_id, db)
    item = await db.get(LawFirmContact, contact_id)
    if not item or item.law_firm_id != firm.id: raise HTTPException(status_code=404, detail="律所联系人不存在")
    if item.id == firm.default_contact_id and not body.is_active: raise HTTPException(status_code=409, detail="默认联系人不能直接停用，请先设置其他有效联系人为默认联系人")
    before = {key: getattr(item, key) for key in body.model_fields}
    for key, value in body.model_dump().items(): setattr(item, key, value)
    item.updated_by = identity["username"]
    db.add(LawFirmAudit(law_firm_id=firm.id, action="修改律所联系人", operator=identity["username"], detail={"contact_id": item.id, "before": before, "after": body.model_dump()}))
    await db.commit(); await db.refresh(item)
    return _law_firm_contact_dict(item, is_default=item.id == firm.default_contact_id)


@router.post(f"{settings.api_prefix}/law-firms/{{law_firm_id}}/contacts/{{contact_id}}/default")
async def set_law_firm_default_contact(law_firm_id: int, contact_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _law_firm_contact_dict, _law_firm_or_404,
    )
    from app.core.permissions import (
        _require_admin,
    )
    _require_admin(identity); firm = await _law_firm_or_404(law_firm_id, db)
    item = await db.get(LawFirmContact, contact_id)
    if not item or item.law_firm_id != firm.id: raise HTTPException(status_code=404, detail="律所联系人不存在")
    if not item.is_active: raise HTTPException(status_code=409, detail="停用联系人不能设为默认联系人")
    previous = firm.default_contact_id; firm.default_contact_id = item.id; firm.updated_by = identity["username"]
    db.add(LawFirmAudit(law_firm_id=firm.id, action="设置默认联系人", operator=identity["username"], detail={"before_contact_id": previous, "after_contact_id": item.id}))
    await db.commit(); await db.refresh(item)
    return _law_firm_contact_dict(item, is_default=True)


@router.post(f"{settings.api_prefix}/law-firms/{{law_firm_id}}/license", status_code=status.HTTP_201_CREATED)
async def upload_law_firm_license(law_firm_id: int, file: UploadFile = File(...), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _law_firm_license, _law_firm_or_404,
    )
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    _require_admin(identity); firm = await _law_firm_or_404(law_firm_id, db)
    filename = Path(file.filename or "营业执照").name
    suffix = Path(filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".gif"}: raise HTTPException(status_code=422, detail="营业执照仅支持 JPG、PNG 或 GIF 图片")
    content = await file.read()
    if not content: raise HTTPException(status_code=422, detail="营业执照文件不能为空")
    if len(content) > 20 * 1024 * 1024: raise HTTPException(status_code=422, detail="营业执照文件不能超过 20MB")
    old_attachment = await _law_firm_license(firm, db)
    target = UPLOAD_ROOT / f"law-firm-{firm.id}-{uuid4().hex}{suffix}"
    target.write_bytes(content)
    attachment = FileAttachment(law_firm_id=firm.id, category="律所营业执照", original_name=filename, stored_name=target.name, content_type=file.content_type or "image/*", size=len(content), path=str(target), uploader=identity["username"], remark=f"律所 {firm.code} 营业执照")
    db.add(attachment); await db.flush()
    firm.license_attachment_id = attachment.id; firm.updated_by = identity["username"]
    db.add(LawFirmAudit(law_firm_id=firm.id, action="替换营业执照", operator=identity["username"], detail={"previous_attachment_id": old_attachment.id if old_attachment else None, "attachment_id": attachment.id, "name": filename}))
    if old_attachment: await db.delete(old_attachment)
    await db.commit(); await db.refresh(attachment)
    if old_attachment:
        old_path = Path(old_attachment.path)
        if old_path.is_file() and UPLOAD_ROOT.resolve() in old_path.resolve().parents: old_path.unlink(missing_ok=True)
    return _attachment_dict(attachment)


@router.get(f"{settings.api_prefix}/law-firms/{{law_firm_id}}/license/download")
async def download_law_firm_license(law_firm_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _law_firm_license, _law_firm_or_404,
    )
    from app.core.permissions import (
        _require_admin,
    )
    _require_admin(identity); firm = await _law_firm_or_404(law_firm_id, db); attachment = await _law_firm_license(firm, db)
    if not attachment: raise HTTPException(status_code=404, detail="该律所尚未上传营业执照")
    path = Path(attachment.path)
    if not path.is_file() or UPLOAD_ROOT.resolve() not in path.resolve().parents: raise HTTPException(status_code=404, detail="营业执照文件不存在")
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.original_name)


@router.post(f"{settings.api_prefix}/customers/import")
async def import_customers(file: UploadFile = File(...), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _resolve_active_customer_managers,
    )
    if not (file.filename or "").lower().endswith(".csv"): raise HTTPException(status_code=422, detail="仅支持 UTF-8 CSV 文件")
    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024: raise HTTPException(status_code=413, detail="导入文件不能超过 5MB")
    try: text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc: raise HTTPException(status_code=422, detail="CSV 必须使用 UTF-8 编码") from exc
    reader = csv.DictReader(io.StringIO(text)); existing = set((await db.scalars(select(BusinessRecord.title).where(BusinessRecord.module == "customer"))).all()); seen: set[str] = set(); created_items: list[dict] = []; errors: list[dict] = []
    current_user = await db.scalar(select(User).where(User.username == identity["username"], User.is_active.is_(True)))
    if not current_user: raise HTTPException(status_code=401, detail="当前用户不存在或已停用")
    for row_no, row in enumerate(reader, 2):
        title = (row.get("客户名称") or row.get("title") or "").strip()
        if not title: errors.append({"row": row_no, "error": "客户名称为空"}); continue
        if title in existing or title in seen: errors.append({"row": row_no, "error": "客户名称已存在", "value": title}); continue
        seen.add(title); serial = f"KH{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid4().hex[:4].upper()}"
        requested_owner = (row.get("负责人") or row.get("owner") or identity["username"]).strip()
        department = (row.get("部门") or row.get("department") or current_user.department).strip()
        try:
            if identity.get("role") == "user":
                owner = current_user.username; department = current_user.department
            else:
                owner = (await _resolve_active_customer_managers([requested_owner], db))[0]
                owner_user = await db.scalar(select(User).where(User.username == owner))
                if identity.get("role") != "admin":
                    department = current_user.department
                    if not owner_user or owner_user.department != current_user.department:
                        raise HTTPException(status_code=422, detail="部门负责人只能导入本部门负责人名下的客户")
            item = BusinessRecord(module="customer", serial_no=serial, title=title, customer=title, status="跟进中", owner=owner, department=department, data={"contact": (row.get("联系人") or row.get("contact") or "").strip(), "phone": (row.get("电话") or row.get("phone") or "").strip(), "level": (row.get("客户等级") or row.get("level") or "普通客户").strip(), "customer_managers": [owner], "imported_at": datetime.now().isoformat(timespec="seconds"), "last_modified_by": identity["username"]})
            db.add(item); await db.flush(); db.add(WorkflowEvent(record_id=item.id, action="批量导入", to_status="跟进中", operator=identity["username"], comment=f"CSV 第 {row_no} 行")); created_items.append({"id": item.id, "serial_no": item.serial_no, "title": item.title, "owner": owner, "department": department})
        except HTTPException as exc:
            errors.append({"row": row_no, "error": str(exc.detail), "value": requested_owner})
    await db.commit()
    return {"created": len(created_items), "failed": len(errors), "items": created_items, "errors": errors}


@router.post(f"{settings.api_prefix}/customers", status_code=status.HTTP_201_CREATED)
async def create_customer(body: CustomerCreateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _mark_customer_modified, _next_customer_serial_no, _resolve_active_customer_managers,
    )
    from app.core.formatters import (
        _normalize_customer_yes_no,
    )
    from app.core.legacy_sync import (
        _sync_legacy_projection,
    )
    from app.core.permissions import (
        _ensure_unique_customer_name, _record_dict_for_identity,
    )
    title = body.title.strip()
    await _ensure_unique_customer_name(title, db)
    customer_status = body.status.strip()
    if customer_status and customer_status not in CUSTOMER_CREATE_STATUSES:
        raise HTTPException(status_code=422, detail="客户状态无效")
    data = dict(body.data or {})
    for field_name in CUSTOMER_CREATE_DATA_FIELDS:
        if field_name in body.model_fields_set:
            data[field_name] = getattr(body, field_name)
    # New customers have no lifecycle or sharing history.  Drop every
    # client-supplied system field after merging both ``data`` and top-level
    # aliases so neither input shape can forge audit state or list membership.
    for protected_customer_field in CUSTOMER_SYSTEM_DATA_FIELDS:
        data.pop(protected_customer_field, None)
    data["shared_with"] = []
    data["is_shared"] = "否"
    data["customer_guid"] = str(uuid4())
    customer_type = str(data.get("customer_type") or "客户").strip()
    active_customer_types = set((await db.scalars(select(SystemParameter.name).where(
        SystemParameter.category == "customer_type", SystemParameter.is_active.is_(True),
    ))).all())
    if customer_type not in active_customer_types:
        raise HTTPException(status_code=422, detail="客户类型不存在或已停用")
    level = str(data.get("level") or "立案客户").strip()
    if level not in CUSTOMER_LEVELS: raise HTTPException(status_code=422, detail="客户等级无效")
    data["customer_type"] = customer_type; data["level"] = level
    for key, label in {"is_shared": "是否共享", "is_assisted": "上海市资助信息", "fee_reduction": "是否费减"}.items():
        data[key] = _normalize_customer_yes_no(data.get(key), label)
    credit_code = str(data.get("credit_code") or "").strip()
    if credit_code and any(character.isspace() for character in str(data.get("credit_code") or "")):
        raise HTTPException(status_code=422, detail="统一社会信用代码不允许包含空格")
    if credit_code:
        existing_customers = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "customer"))).all()
        if any(str((item.data or {}).get("credit_code") or "").strip().casefold() == credit_code.casefold() for item in existing_customers):
            raise HTTPException(status_code=409, detail="统一社会信用代码已存在")
    data["credit_code"] = credit_code
    contact_values: list[str] = []
    raw_contact = body.contact if "contact" in body.model_fields_set else data.get("contact")
    if isinstance(raw_contact, list):
        contact_values.extend(str(value).strip() for value in raw_contact if str(value).strip())
    elif str(raw_contact or "").strip():
        contact_values.append(str(raw_contact).strip())
    contact_values.extend(
        str(value).strip()
        for value in list(body.contact_accounts or [])
        if str(value).strip()
    )
    contact_values = list(dict.fromkeys(contact_values))
    data["contact_accounts"] = contact_values
    data["contact"] = contact_values[0] if contact_values else ""
    current_user = await db.scalar(select(User).where(User.username == identity["username"], User.is_active.is_(True)))
    if not current_user: raise HTTPException(status_code=401, detail="当前用户不存在或已停用")
    requested_owner = body.owner.strip() or current_user.username
    department = body.department.strip() or current_user.department
    if identity.get("role") != "admin":
        department = current_user.department
        if identity.get("role") == "user": requested_owner = current_user.username
    owner = (await _resolve_active_customer_managers([requested_owner], db))[0]
    raw_managers = body.customer_managers if "customer_managers" in body.model_fields_set else data.get("customer_managers", [])
    managers = await _resolve_active_customer_managers(list(raw_managers or [owner]), db)
    data["customer_managers"] = [owner, *[manager for manager in managers if manager != owner]]
    serial_no = body.serial_no.strip()
    if not serial_no:
        serial_no = await _next_customer_serial_no(db)
    if await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == serial_no)):
        raise HTTPException(status_code=409, detail="业务编号已存在")
    record = BusinessRecord(
        module="customer", serial_no=serial_no, title=title, customer=title, status=customer_status,
        owner=owner, department=department, description=body.description.strip(), data=data,
    )
    _mark_customer_modified(record, identity)
    db.add(record); await db.flush()
    db.add(WorkflowEvent(record_id=record.id, action="创建客户", to_status=record.status, operator=identity["username"], comment="通过新建客户专用入口创建"))
    await _sync_legacy_projection(record, identity, db)
    await db.commit(); await db.refresh(record)
    return await _record_dict_for_identity(record, identity, db)


@router.get(f"{settings.api_prefix}/customers/conflicts")
async def customer_conflicts(
    name: str = Query(min_length=1, max_length=100),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """Return the latest case containing one exact, normalized enterprise party."""
    from app.core.cases import (
        _case_conflict_entities, _case_party_values,
    )
    from app.core.crm import (
        _conflict_customer_managers, _empty_customer_conflict_result,
    )
    from app.core.formatters import (
        _case_filing_date, _normalize_conflict_entity,
    )
    from app.core.permissions import (
        _require_customer_conflict_permission,
    )
    from app.core.system import (
        _conflict_entity_tokens,
    )
    await _require_customer_conflict_permission(identity, db)
    query = name.strip()
    if not query:
        raise HTTPException(status_code=422, detail="企业名称不能为空")
    needle = _normalize_conflict_entity(query)

    # Conflict checking deliberately spans the whole firm.  Only the minimum
    # original-page disclosure is returned and no source record id is exposed.
    cases = list((await db.scalars(
        select(BusinessRecord).where(BusinessRecord.module == "case")
    )).all())
    matching_cases = cases if not needle else [
        case_record for case_record in cases
        if any(_normalize_conflict_entity(entity) == needle for entity in _case_conflict_entities(case_record))
    ]
    if not matching_cases:
        return _empty_customer_conflict_result(query)
    latest_case = max(
        matching_cases,
        key=lambda case_record: (_case_filing_date(case_record) or date.min, case_record.id),
    )
    data = latest_case.data or {}
    filing_date = _case_filing_date(latest_case)
    plaintiffs = _case_party_values(data, CASE_PLAINTIFF_FIELDS) or _conflict_entity_tokens(latest_case.customer)
    return {
        "found": True,
        "query": query,
        "enterprise_name": query,
        "latest_case_no": latest_case.serial_no,
        "latest_case_date": filing_date.isoformat() if filing_date else "",
        "plaintiffs": plaintiffs,
        "defendants": _case_party_values(data, CASE_DEFENDANT_FIELDS),
        "third_parties": _case_party_values(data, CASE_THIRD_PARTY_FIELDS),
        "our_customer": latest_case.customer,
        "customer_managers": await _conflict_customer_managers(query, db),
    }


@router.api_route(f"{settings.api_prefix}/customers/{{customer_id}}/shared-objects", methods=["GET", "POST"])
async def list_customer_shared_objects(customer_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_guid, _customer_or_404,
    )
    customer = await _customer_or_404(customer_id, identity, db)
    data = customer.data or {}
    return {
        "customer_id": customer.id, "customer_guid": _customer_guid(customer),
        "items": list(data.get("shared_with") or [{}]),
        "customer_managers": list(data.get("customer_managers") or [customer.owner]),
        "is_shared": data.get("is_shared", "否"),
    }


@router.get(f"{settings.api_prefix}/customers/{{customer_id}}/assignment-history")
async def list_customer_assignment_history(customer_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_guid, _customer_or_404,
    )
    customer = await _customer_or_404(customer_id, identity, db)
    items = list((customer.data or {}).get("assignment_history") or [])
    return {"customer_id": customer.id, "customer_guid": _customer_guid(customer), "items": items, "total": len(items)}


@router.get(f"{settings.api_prefix}/customers/guid/{{customer_guid}}/events")
async def list_customer_events_by_guid(customer_guid: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_by_guid, _customer_guid,
    )
    customer = await _customer_by_guid(customer_guid, identity, db)
    events = (await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == customer.id).order_by(WorkflowEvent.created_at, WorkflowEvent.id))).all()
    return {"customer_id": customer.id, "customer_guid": _customer_guid(customer), "items": [{"id": event.id, "action": event.action, "comment": event.comment, "operator": event.operator, "from_status": event.from_status, "to_status": event.to_status, "created_at": event.created_at} for event in events], "total": len(events)}


@router.post(f"{settings.api_prefix}/customers/guid/{{customer_guid}}/events", status_code=status.HTTP_201_CREATED)
async def create_customer_event_by_guid(customer_guid: str, body: CustomerEventInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_by_guid, _customer_event, _customer_guid,
    )
    customer = await _customer_by_guid(customer_guid, identity, db)
    event = _customer_event(customer, body.action.strip(), identity, body.comment.strip())
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return {"id": event.id, "customer_id": customer.id, "customer_guid": _customer_guid(customer), "action": event.action, "comment": event.comment, "operator": event.operator, "created_at": event.created_at}


@router.get(f"{settings.api_prefix}/customers/guid/{{customer_guid}}/files")
async def list_customer_files_by_guid(customer_guid: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_files_by_guid, _customer_guid,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    customer, files = await _customer_files_by_guid(customer_guid, identity, db)
    return {"customer_id": customer.id, "customer_guid": _customer_guid(customer), "items": [_attachment_dict(item, customer) for item in files], "total": len(files)}


@router.get(f"{settings.api_prefix}/customers/guid/{{customer_guid}}/legacy-history")
async def get_customer_legacy_history(customer_guid: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Read-only CRM history projection; never blends legacy rows into live logs/files."""
    from app.core.crm import (
        _customer_by_guid, _customer_guid,
    )
    from app.core.legacy_sync import (
        _legacy_customer_history_item, _legacy_customer_history_users,
    )
    customer = await _customer_by_guid(customer_guid, identity, db)
    customer_id = customer.id
    coordinators = list((await db.scalars(select(LegacyCustomerHistoryCoordinator).where(
        LegacyCustomerHistoryCoordinator.customer_record_id == customer_id
    ).order_by(LegacyCustomerHistoryCoordinator.id))).all())
    contacts = list((await db.scalars(select(LegacyCustomerHistoryContact).where(
        LegacyCustomerHistoryContact.customer_record_id == customer_id
    ).order_by(LegacyCustomerHistoryContact.id))).all())
    events = list((await db.scalars(select(LegacyCustomerHistoryEvent).where(
        LegacyCustomerHistoryEvent.customer_record_id == customer_id
    ).order_by(LegacyCustomerHistoryEvent.operated_at, LegacyCustomerHistoryEvent.id))).all())
    files = list((await db.scalars(select(LegacyCustomerHistoryFile).where(
        LegacyCustomerHistoryFile.customer_record_id == customer_id
    ).order_by(LegacyCustomerHistoryFile.uploaded_at, LegacyCustomerHistoryFile.id))).all())
    baselines = list((await db.scalars(select(LegacyCustomerHistoryBaseline).where(
        LegacyCustomerHistoryBaseline.source_system == "legacy_crm"
    ).order_by(LegacyCustomerHistoryBaseline.source_table))).all())
    user_ids = {item.mapped_user_id for item in [*coordinators, *contacts, *events, *files] if item.mapped_user_id}
    users = await _legacy_customer_history_users({int(item) for item in user_ids}, db)
    return {
        "customer_id": customer_id,
        "customer_guid": _customer_guid(customer),
        "read_only": True,
        "coordinators": [_legacy_customer_history_item(item, user=users.get(item.mapped_user_id), kind="coordinator") for item in coordinators],
        "contacts": [_legacy_customer_history_item(item, user=users.get(item.mapped_user_id), kind="contact") for item in contacts],
        "events": [_legacy_customer_history_item(item, user=users.get(item.mapped_user_id), kind="event") for item in events],
        "files": [_legacy_customer_history_item(item, user=users.get(item.mapped_user_id), kind="file") for item in files],
        "zero_baselines": [{"source_table": item.source_table, "source_row_count": item.source_row_count, "audit_status": item.audit_status} for item in baselines],
        "counts": {"coordinators": len(coordinators), "contacts": len(contacts), "events": len(events), "files": len(files)},
    }


@router.get(f"{settings.api_prefix}/customers/guid/{{customer_guid}}/files/{{attachment_id}}/download")
async def download_customer_file_by_guid(customer_guid: str, attachment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_files_by_guid,
    )
    customer, _ = await _customer_files_by_guid(customer_guid, identity, db)
    attachment = await db.get(FileAttachment, attachment_id)
    if not attachment or attachment.record_id != customer.id:
        raise HTTPException(status_code=404, detail="客户文件不存在")
    path = Path(attachment.path)
    if not path.is_file() or UPLOAD_ROOT.resolve() not in path.resolve().parents:
        raise HTTPException(status_code=404, detail="客户文件不存在")
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.original_name)


@router.get(f"{settings.api_prefix}/customers/{{customer_id}}/contacts")
async def list_customer_contacts(customer_id: int, page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=200), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_contact_dict, _customer_guid, _customer_or_404,
    )
    customer = await _customer_or_404(customer_id, identity, db)
    contacts = [_customer_contact_dict(item) for item in list((customer.data or {}).get("contacts") or [])]
    total = len(contacts); start = (page - 1) * page_size
    return {"customer_id": customer.id, "customer_guid": _customer_guid(customer), "items": contacts[start:start + page_size], "total": total, "page": page, "page_size": page_size}


@router.patch(f"{settings.api_prefix}/customers/{{customer_id}}/contacts/{{contact_id}}/status")
async def update_customer_contact_status(customer_id: int, contact_id: str, body: CustomerContactStatusInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_contact_dict, _customer_event, _customer_or_404,
    )
    from app.core.permissions import (
        _require_record_owner_or_manager,
    )
    if body.is_valid is None and body.is_primary is None:
        raise HTTPException(status_code=422, detail="联系人状态至少指定一项")
    customer = await _customer_or_404(customer_id, identity, db)
    await _require_record_owner_or_manager(customer, identity, db)
    data = customer.data or {}; contacts = [_customer_contact_dict(item) for item in list(data.get("contacts") or [])]
    index = next((i for i, item in enumerate(contacts) if item.get("id") == contact_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="联系人不存在")
    previous = contacts[index]
    changes_valid = body.is_valid is not None and body.is_valid != previous.get("is_valid")
    changes_primary = body.is_primary is True and not previous.get("is_primary")
    if not changes_valid and not changes_primary:
        raise HTTPException(status_code=422, detail="联系人状态未发生变化")
    updated = {**previous}
    if body.is_valid is not None:
        updated["is_valid"] = body.is_valid
    if body.is_primary:
        contacts = [{**item, "is_primary": item.get("id") == contact_id} for item in contacts]
    else:
        contacts[index] = updated
    if body.is_primary:
        contacts[index] = {**updated, "is_primary": True}
    customer.data = {**data, "contacts": contacts}
    db.add(_customer_event(customer, "设置联系人状态", identity, f"联系人：{contact_id}"))
    await db.commit()
    return contacts[index]


@router.patch(f"{settings.api_prefix}/customers/{{customer_id}}")
async def patch_customer(customer_id: int, body: CustomerPatchInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_event, _customer_or_404,
    )
    from app.core.permissions import (
        _record_dict_for_identity, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    customer = await _customer_or_404(customer_id, identity, db)
    await _require_record_owner_or_manager(customer, identity, db)
    allowed_fields = await _allowed_field_keys(identity, db)
    current = dict(customer.data or {})
    accepted: dict[str, object] = {}
    for key, value in (body.data or {}).items():
        if key not in CUSTOMER_CREATE_DATA_FIELDS:
            continue
        permission = next((permission for permission, keys in FIELD_PERMISSION_DATA_KEYS.items() if key in keys), None)
        if permission and permission not in allowed_fields:
            continue
        accepted[key] = value
    customer.data = {**current, **accepted}
    if body.description is not None:
        customer.description = body.description.strip()
    db.add(_customer_event(customer, "更新客户资料", identity, f"更新字段：{'、'.join(accepted) or '无可写字段'}"))
    await db.commit()
    await db.refresh(customer)
    return await _record_dict_for_identity(customer, identity, db)


@router.post(f"{settings.api_prefix}/customers/{{customer_id}}/claim")
async def claim_customer(customer_id: int, body: CustomerActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_event, _locked_customer_or_404,
    )
    from app.core.legacy_sync import (
        _legacy_customer_business_failure_response,
    )
    from app.core.permissions import (
        _record_dict_for_identity,
    )
    try:
        if identity.get("role") not in {"admin", "manager", "user"}:
            raise HTTPException(status_code=403, detail="当前角色不能领取公海客户")
        customer = await _locked_customer_or_404(customer_id, identity, db)
        if customer.status != "公海": raise HTTPException(status_code=409, detail="只有公海客户可以领取")
        current_user = await db.scalar(select(User).where(User.username == identity["username"], User.is_active.is_(True)))
        if not current_user: raise HTTPException(status_code=401, detail="当前用户不存在或已停用")
        old = customer.status; customer.status = "潜在"; customer.owner = current_user.username; customer.department = current_user.department
        customer.data = {
            **(customer.data or {}),
            "customer_managers": [identity["username"]],
            "shared_with": [],
            "is_shared": "否",
            "claimed_at": datetime.now().isoformat(timespec="seconds"),
            "claimed_by": identity["username"],
        }
        db.add(_customer_event(customer, "领取客户", identity, body.comment or "从公海领取客户", old)); await db.commit(); await db.refresh(customer)
        return await _record_dict_for_identity(customer, identity, db)
    except HTTPException as exc:
        return _legacy_customer_business_failure_response(exc)


@router.post(f"{settings.api_prefix}/customers/{{customer_id}}/release")
async def release_customer(customer_id: int, body: CustomerActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_event, _locked_customer_or_404,
    )
    from app.core.legacy_sync import (
        _legacy_customer_business_failure_response,
    )
    from app.core.permissions import (
        _record_dict_for_identity,
    )
    try:
        customer = await _locked_customer_or_404(customer_id, identity, db)
        if customer.status in {"公海", "已回收"}: raise HTTPException(status_code=409, detail="当前客户状态不能释放到公海")
        old = customer.status; customer.status = "公海"; customer.owner = "公海"
        customer.data = {
            **(customer.data or {}),
            "shared_with": [],
            "is_shared": "否",
            "released_at": datetime.now().isoformat(timespec="seconds"),
            "released_by": identity["username"],
        }
        db.add(_customer_event(customer, "释放公海", identity, body.comment or "客户释放到公海", old)); await db.commit(); await db.refresh(customer)
        return await _record_dict_for_identity(customer, identity, db)
    except HTTPException as exc:
        return _legacy_customer_business_failure_response(exc)


@router.post(f"{settings.api_prefix}/customers/{{customer_id}}/share")
async def share_customer(customer_id: int, body: CustomerShareInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_event, _locked_customer_or_404, _resolve_active_customer_managers,
    )
    from app.core.legacy_sync import (
        _legacy_customer_business_failure_response,
    )
    from app.core.permissions import (
        _record_dict_for_identity, _require_record_owner_or_manager,
    )
    try:
        customer = await _locked_customer_or_404(customer_id, identity, db)
        await _require_record_owner_or_manager(customer, identity, db)
        if customer.status in {"公海", "已回收"}: raise HTTPException(status_code=409, detail="公海或回收站客户不能共享")
        recipients = await _resolve_active_customer_managers(body.recipients, db)
        active_employees = (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "hr",
            BusinessRecord.status.not_in({"离职", "停用"}),
        ))).all()
        eligible_recipients = {
            str((employee.data or {}).get("username") or employee.owner or "").strip().lower()
            for employee in active_employees
            if str((employee.data or {}).get("username") or employee.owner or "").strip()
        }
        ineligible = [username for username in recipients if username.lower() not in eligible_recipients]
        if ineligible:
            raise HTTPException(status_code=422, detail=f"共享接收人必须是启用的在职员工：{'、'.join(ineligible)}")
        customer_managers = {
            str(value).strip()
            for value in (customer.data or {}).get("customer_managers", [])
            if str(value).strip()
        }
        redundant = sorted(set(recipients) & ({str(customer.owner or "").strip()} | customer_managers))
        if redundant:
            raise HTTPException(status_code=422, detail=f"客户负责人或管理人无需重复共享：{'、'.join(redundant)}")
        existing = set((customer.data or {}).get("shared_with", [])); existing.update(recipients)
        customer.data = {**(customer.data or {}), "shared_with": sorted(existing), "is_shared": "是", "shared_at": datetime.now().isoformat(timespec="seconds")}
        db.add(_customer_event(customer, "共享客户", identity, body.comment or f"共享给：{'、'.join(recipients)}")); await db.commit(); await db.refresh(customer)
        return await _record_dict_for_identity(customer, identity, db)
    except HTTPException as exc:
        return _legacy_customer_business_failure_response(exc)


@router.post(f"{settings.api_prefix}/customers/{{customer_id}}/recycle")
async def recycle_customer(customer_id: int, body: CustomerActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_event, _customer_linked_business_counts, _locked_customer_or_404,
    )
    from app.core.legacy_sync import (
        _legacy_customer_business_failure_response,
    )
    from app.core.permissions import (
        _record_dict_for_identity, _require_record_owner_or_manager,
    )
    try:
        customer = await _locked_customer_or_404(customer_id, identity, db)
        await _require_record_owner_or_manager(customer, identity, db)
        if customer.status == "公海": raise HTTPException(status_code=409, detail="公海客户必须先领取，不能直接移入回收站")
        if customer.status == "已回收": raise HTTPException(status_code=409, detail="客户已在回收站")
        linked_counts = await _customer_linked_business_counts(customer, db)
        if linked_counts["contract_count"] or linked_counts["case_count"]:
            blockers = []
            if linked_counts["contract_count"]:
                blockers.append(f"{linked_counts['contract_count']} 个合同")
            if linked_counts["case_count"]:
                blockers.append(f"{linked_counts['case_count']} 个案件")
            raise HTTPException(status_code=409, detail=f"客户存在{'、'.join(blockers)}，不能删除；请先处理关联合同和案件")
        old = customer.status
        customer.data = {
            **(customer.data or {}),
            "shared_with": [],
            "is_shared": "否",
            "status_before_recycle": old,
            "recycled_at": datetime.now().isoformat(timespec="seconds"),
            "recycled_by": identity["username"],
        }
        customer.status = "已回收"; db.add(_customer_event(customer, "移入回收站", identity, body.comment or "客户移入回收站", old)); await db.commit(); await db.refresh(customer)
        return await _record_dict_for_identity(customer, identity, db)
    except HTTPException as exc:
        return _legacy_customer_business_failure_response(exc)


@router.post(f"{settings.api_prefix}/customers/{{customer_id}}/restore")
async def restore_customer(customer_id: int, body: CustomerActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_event, _locked_customer_or_404,
    )
    from app.core.legacy_sync import (
        _legacy_customer_business_failure_response,
    )
    from app.core.permissions import (
        _record_dict_for_identity, _require_record_owner_or_manager,
    )
    try:
        customer = await _locked_customer_or_404(customer_id, identity, db)
        await _require_record_owner_or_manager(customer, identity, db)
        if customer.status != "已回收": raise HTTPException(status_code=409, detail="只有回收站客户可以恢复")
        old = customer.status; previous = str((customer.data or {}).get("status_before_recycle", "跟进中"))
        if previous not in {"正常", "跟进中", "公海", *CUSTOMER_CREATE_STATUSES}: previous = "潜在"
        customer.status = previous; customer.data = {**(customer.data or {}), "restored_at": datetime.now().isoformat(timespec="seconds"), "restored_by": identity["username"]}
        db.add(_customer_event(customer, "恢复客户", identity, body.comment or f"恢复为{previous}", old)); await db.commit(); await db.refresh(customer)
        return await _record_dict_for_identity(customer, identity, db)
    except HTTPException as exc:
        return _legacy_customer_business_failure_response(exc)


@router.post(f"{settings.api_prefix}/customers/{{customer_id}}/contacts", status_code=status.HTTP_201_CREATED)
async def add_customer_contact(customer_id: int, body: CustomerContactInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_event, _customer_or_404,
    )
    from app.core.permissions import (
        _require_record_owner_or_manager,
    )
    customer = await _customer_or_404(customer_id, identity, db); await _require_record_owner_or_manager(customer, identity, db); data = customer.data or {}; contacts = list(data.get("contacts", []))
    if any(x.get("name") == body.name.strip() and x.get("phone", "") == body.phone.strip() for x in contacts): raise HTTPException(status_code=409, detail="相同联系人已存在")
    if body.is_primary: contacts = [{**x, "is_primary": False} for x in contacts]
    contact = {
        "id": uuid4().hex,
        "name": body.name.strip(),
        "project_role": body.project_role.strip(),
        "position": body.position.strip(),
        "phone": body.phone.strip(),
        "office_phone": body.office_phone.strip(),
        "im_account": body.im_account.strip(),
        "email": body.email.strip(),
        "contact_status": body.contact_status.strip() or "正常联系",
        "is_valid": body.is_valid,
        "is_primary": body.is_primary,
        "is_received_email": body.is_received_email,
        "is_contacted": body.is_contacted,
        "is_people_base": body.is_people_base,
        "remark": body.remark.strip(),
    }
    contacts.append(contact); customer.data = {**data, "contacts": contacts}
    db.add(_customer_event(customer, "新增联系人", identity, f"联系人：{contact['name']}")); await db.commit()
    return contact


@router.put(f"{settings.api_prefix}/customers/{{customer_id}}/contacts/{{contact_id}}")
async def update_customer_contact(customer_id: int, contact_id: str, body: CustomerContactInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Update an existing contact in place; customer scope and edit authority are never bypassed."""
    from app.core.crm import (
        _customer_event, _customer_or_404,
    )
    from app.core.permissions import (
        _require_record_owner_or_manager,
    )
    customer = await _customer_or_404(customer_id, identity, db)
    await _require_record_owner_or_manager(customer, identity, db)
    data = customer.data or {}
    contacts = list(data.get("contacts", []))
    index = next((i for i, item in enumerate(contacts) if item.get("id") == contact_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="联系人不存在")
    name = body.name.strip()
    phone = body.phone.strip()
    if not name:
        raise HTTPException(status_code=422, detail="请输入联系人姓名")
    if any(item.get("id") != contact_id and item.get("name") == name and item.get("phone", "") == phone for item in contacts):
        raise HTTPException(status_code=409, detail="相同联系人已存在")
    previous = contacts[index]
    updated = {
        **previous,
        "name": name,
        "project_role": body.project_role.strip(),
        "position": body.position.strip(),
        "phone": phone,
        "office_phone": body.office_phone.strip(),
        "im_account": body.im_account.strip(),
        "email": body.email.strip(),
        "contact_status": body.contact_status.strip() or "正常联系",
        "is_valid": body.is_valid,
        "is_primary": body.is_primary,
        "is_received_email": body.is_received_email,
        "is_contacted": body.is_contacted,
        "is_people_base": body.is_people_base,
        "remark": body.remark.strip(),
    }
    if body.is_primary:
        contacts = [{**item, "is_primary": False} if item.get("id") != contact_id else updated for item in contacts]
    else:
        contacts[index] = updated
    changed_labels = {
        "name": "姓名", "position": "职务", "project_role": "项目角色", "phone": "移动电话",
        "office_phone": "办公电话", "im_account": "IM", "email": "邮箱",
        "contact_status": "联系状态", "is_valid": "有效状态", "is_primary": "主要联系人", "remark": "备注",
    }
    changed_labels.update({
        "is_received_email": "is_received_email",
        "is_contacted": "is_contacted",
        "is_people_base": "is_people_base",
    })
    changed = [label for key, label in changed_labels.items() if previous.get(key) != updated.get(key)]
    customer.data = {**data, "contacts": contacts}
    if changed:
        db.add(_customer_event(customer, "修改联系人", identity, f"联系人：{previous.get('name', '')} → {updated['name']}；修改字段：{'、'.join(changed)}"))
    await db.commit()
    return updated


@router.delete(f"{settings.api_prefix}/customers/{{customer_id}}/contacts/{{contact_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer_contact(customer_id: int, contact_id: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_event, _customer_or_404,
    )
    from app.core.permissions import (
        _require_record_owner_or_manager,
    )
    customer = await _customer_or_404(customer_id, identity, db); await _require_record_owner_or_manager(customer, identity, db); data = customer.data or {}; contacts = list(data.get("contacts", [])); contact = next((x for x in contacts if x.get("id") == contact_id), None); remaining = [x for x in contacts if x.get("id") != contact_id]
    if len(remaining) == len(contacts): raise HTTPException(status_code=404, detail="联系人不存在")
    linked_case_count = await db.scalar(select(func.count(IprCaseCustomerContact.id)).where(IprCaseCustomerContact.customer_record_id == customer.id, IprCaseCustomerContact.contact_id == contact_id)) or 0
    if linked_case_count:
        raise HTTPException(status_code=409, detail=f"该联系人已关联 {linked_case_count} 个知识产权案件，请先解除案件联系人关联")
    attachment = await db.get(FileAttachment, int(contact["photo_attachment_id"])) if contact and contact.get("photo_attachment_id") else None
    customer.data = {**data, "contacts": remaining}; db.add(_customer_event(customer, "删除联系人", identity, f"删除客户联系人：{contact.get('name', '')}"));
    if attachment: await db.delete(attachment)
    await db.commit()
    if attachment:
        path = Path(attachment.path)
        if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents: path.unlink(missing_ok=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(f"{settings.api_prefix}/customers/{{customer_id}}/contacts/{{contact_id}}/photo", status_code=status.HTTP_201_CREATED)
async def upload_customer_contact_photo(customer_id: int, contact_id: str, file: UploadFile = File(...), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_contact_or_404, _customer_event,
    )
    customer, contacts, index = await _customer_contact_or_404(customer_id, contact_id, identity, db)
    filename = Path(file.filename or "联系人照片").name; suffix = Path(filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}: raise HTTPException(status_code=422, detail="联系人照片仅支持 JPG、PNG、GIF 或 WEBP 图片")
    content = await file.read()
    if not content: raise HTTPException(status_code=422, detail="联系人照片文件不能为空")
    if len(content) > 10 * 1024 * 1024: raise HTTPException(status_code=413, detail="联系人照片不能超过 10MB")
    previous = contacts[index]; old_attachment = await db.get(FileAttachment, int(previous["photo_attachment_id"])) if previous.get("photo_attachment_id") else None
    target = UPLOAD_ROOT / f"customer-contact-{customer.id}-{contact_id}-{uuid4().hex}{suffix}"; target.write_bytes(content)
    attachment = FileAttachment(record_id=customer.id, category="客户联系人照片", original_name=filename, stored_name=target.name, content_type=file.content_type or "image/*", size=len(content), path=str(target), uploader=identity["username"], remark=f"联系人 {contact_id} 照片")
    db.add(attachment); await db.flush()
    contacts[index] = {**previous, "photo_attachment_id": attachment.id, "photo_original_name": filename}
    customer.data = {**(customer.data or {}), "contacts": contacts}
    db.add(_customer_event(customer, "上传联系人照片", identity, f"联系人：{previous.get('name', '')}；{'替换' if old_attachment else '上传'}照片：{filename}"))
    if old_attachment: await db.delete(old_attachment)
    await db.commit(); await db.refresh(attachment)
    if old_attachment:
        old_path = Path(old_attachment.path)
        if old_path.is_file() and UPLOAD_ROOT.resolve() in old_path.resolve().parents: old_path.unlink(missing_ok=True)
    return {"attachment_id": attachment.id, "original_name": filename, "size": attachment.size}


@router.get(f"{settings.api_prefix}/customers/{{customer_id}}/contacts/{{contact_id}}/photo/download")
async def download_customer_contact_photo(customer_id: int, contact_id: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_contact_or_404,
    )
    _, contacts, index = await _customer_contact_or_404(customer_id, contact_id, identity, db)
    attachment_id = contacts[index].get("photo_attachment_id")
    if not attachment_id: raise HTTPException(status_code=404, detail="该联系人尚未上传照片")
    attachment = await db.get(FileAttachment, int(attachment_id))
    if not attachment: raise HTTPException(status_code=404, detail="联系人照片记录不存在")
    path = Path(attachment.path)
    if not path.is_file() or UPLOAD_ROOT.resolve() not in path.resolve().parents: raise HTTPException(status_code=404, detail="联系人照片文件不存在")
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.original_name)


@router.put(f"{settings.api_prefix}/customers/{{customer_id}}/managers")
async def update_customer_managers(customer_id: int, body: CustomerManagersInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_event, _customer_or_404, _prioritize_new_customer_managers, _resolve_active_customer_managers,
    )
    from app.core.legacy_sync import (
        _legacy_customer_business_failure_response,
    )
    from app.core.permissions import (
        _record_dict_for_identity, _require_record_owner_or_manager,
    )
    try:
        customer = await _customer_or_404(customer_id, identity, db)
        if customer.status == "公海": raise HTTPException(status_code=409, detail="公海客户必须先领取后才能分配管理人")
        await _require_record_owner_or_manager(customer, identity, db)
        data = dict(customer.data or {})
        existing_managers = list(data.get("customer_managers") or [customer.owner])
        requested_managers = await _resolve_active_customer_managers(body.managers, db)
        managers = _prioritize_new_customer_managers(existing_managers, requested_managers)
        history = list(data.get("assignment_history") or [])
        history.append({
            "from_owner": customer.owner,
            "to_owner": managers[0],
            "managers": managers,
            "operator": identity["username"],
            "comment": body.comment.strip(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })
        customer.owner = managers[0]
        customer.data = {**data, "customer_managers": managers, "assignment_history": history}
        db.add(_customer_event(customer, "更新客户管理人", identity, body.comment or f"客户管理人：{'、'.join(managers)}"))
        await db.commit(); await db.refresh(customer)
        return await _record_dict_for_identity(customer, identity, db)
    except HTTPException as exc:
        return _legacy_customer_business_failure_response(exc)


@router.post(f"{settings.api_prefix}/customers/{{customer_id}}/notes", status_code=status.HTTP_201_CREATED)
async def add_customer_note(customer_id: int, body: CustomerNoteInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_event, _customer_or_404, _sync_customer_contact_metrics,
    )
    from app.core.permissions import (
        _require_record_owner_or_manager,
    )
    customer = await _customer_or_404(customer_id, identity, db)
    await _require_record_owner_or_manager(customer, identity, db)
    data = customer.data or {}
    notes = list(data.get("notes", []))
    note = {"id": uuid4().hex, "type": body.note_type.strip() or "跟进记录", "content": body.content.strip(), "operator": identity["username"], "created_at": datetime.now().isoformat(timespec="seconds")}
    notes.insert(0, note)
    customer.data = {**data, "notes": notes}
    _sync_customer_contact_metrics(customer)
    db.add(_customer_event(customer, "新增客户跟进", identity, f"{note['type']}：{note['content'][:120]}"))
    await db.commit(); await db.refresh(customer)
    return note


@router.put(f"{settings.api_prefix}/customers/{{customer_id}}/notes/{{note_id}}")
async def update_customer_note(customer_id: int, note_id: str, body: CustomerNoteInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Update one customer note in place without changing its identity or audit origin."""
    from app.core.crm import (
        _customer_event, _customer_or_404, _sync_customer_contact_metrics,
    )
    from app.core.permissions import (
        _require_record_owner_or_manager,
    )
    customer = await _customer_or_404(customer_id, identity, db)
    await _require_record_owner_or_manager(customer, identity, db)
    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="事项内容不能为空")
    data = customer.data or {}
    notes = list(data.get("notes", []))
    index = next((i for i, note in enumerate(notes) if note.get("id") == note_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="跟进记录不存在")
    original = dict(notes[index])
    note = {
        **original,
        "type": body.note_type.strip() or "跟进记录",
        "content": content,
    }
    notes[index] = note
    customer.data = {**data, "notes": notes}
    _sync_customer_contact_metrics(customer)
    db.add(_customer_event(customer, "编辑客户跟进", identity, f"{note['type']}：{note['content'][:120]}"))
    await db.commit(); await db.refresh(customer)
    return note


@router.delete(f"{settings.api_prefix}/customers/{{customer_id}}/notes/{{note_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer_note(customer_id: int, note_id: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_event, _customer_or_404, _sync_customer_contact_metrics,
    )
    from app.core.permissions import (
        _require_record_owner_or_manager,
    )
    customer = await _customer_or_404(customer_id, identity, db)
    await _require_record_owner_or_manager(customer, identity, db)
    data = customer.data or {}; notes = list(data.get("notes", [])); remaining = [note for note in notes if note.get("id") != note_id]
    if len(remaining) == len(notes):
        raise HTTPException(status_code=404, detail="跟进记录不存在")
    customer.data = {**data, "notes": remaining}
    _sync_customer_contact_metrics(customer)
    db.add(_customer_event(customer, "删除客户跟进", identity, "删除一条客户跟进记录"))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(f"{settings.api_prefix}/customers/{{customer_id}}/level-change")
async def submit_customer_level_change(customer_id: int, body: CustomerLevelChangeInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_event, _customer_or_404,
    )
    from app.core.permissions import (
        _record_dict_for_identity, _require_record_owner_or_manager,
    )
    raise HTTPException(status_code=410, detail="客户分级调整审批已取消，请在客户编辑中直接修改客户等级")
    customer = await _customer_or_404(customer_id, identity, db)
    await _require_record_owner_or_manager(customer, identity, db)
    requested_level = body.level.strip()
    if requested_level not in CUSTOMER_LEVELS:
        raise HTTPException(status_code=422, detail="客户等级无效")
    data = customer.data or {}
    if requested_level == str(data.get("level") or ""):
        raise HTTPException(status_code=409, detail="客户当前已经是该等级")
    pending = data.get("level_change") or {}
    if pending.get("status") == "待审批":
        raise HTTPException(status_code=409, detail="已有客户分级调整正在审批")
    customer.data = {
        **data,
        "level_change": {
            "status": "待审批", "from_level": data.get("level", ""), "to_level": requested_level,
            "requested_by": identity["username"], "requested_at": datetime.now().isoformat(timespec="seconds"),
            "comment": body.comment.strip(),
        },
    }
    db.add(_customer_event(customer, "提交客户分级调整", identity, body.comment or f"{data.get('level', '')} → {requested_level}"))
    await db.commit(); await db.refresh(customer)
    return await _record_dict_for_identity(customer, identity, db)


@router.post(f"{settings.api_prefix}/customers/{{customer_id}}/level-change/review")
async def review_customer_level_change(customer_id: int, body: CustomerLevelReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_event, _customer_or_404, _mark_customer_modified,
    )
    from app.core.permissions import (
        _record_dict_for_identity,
    )
    raise HTTPException(status_code=410, detail="客户分级调整审批已取消，请在客户编辑中直接修改客户等级")
    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="只有管理员或客户主管可以审批客户分级")
    customer = await _customer_or_404(customer_id, identity, db)
    data = customer.data or {}; pending = data.get("level_change") or {}
    if pending.get("status") != "待审批":
        raise HTTPException(status_code=409, detail="该客户没有待审批的分级调整")
    if not body.approved and not body.comment.strip():
        raise HTTPException(status_code=422, detail="驳回时必须填写原因")
    previous_level = str(data.get("level") or "")
    requested_level = str(pending.get("to_level") or "")
    if requested_level not in CUSTOMER_LEVELS:
        raise HTTPException(status_code=409, detail="待审批的客户等级已失效")
    reviewed = {
        **pending, "status": "已通过" if body.approved else "已驳回",
        "reviewed_by": identity["username"], "reviewed_at": datetime.now().isoformat(timespec="seconds"),
        "review_comment": body.comment.strip(),
    }
    customer.data = {**data, "level": requested_level if body.approved else previous_level, "level_change": reviewed}
    _mark_customer_modified(customer, identity)
    action = "客户分级审批通过" if body.approved else "客户分级审批驳回"
    db.add(_customer_event(customer, action, identity, body.comment or f"{previous_level} → {requested_level}"))
    await db.commit(); await db.refresh(customer)
    return await _record_dict_for_identity(customer, identity, db)


@router.post(f"{settings.api_prefix}/customers/{{customer_id}}/key-change")
async def submit_customer_key_change(customer_id: int, body: CustomerKeyChangeInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_event, _customer_or_404,
    )
    from app.core.permissions import (
        _ensure_unique_customer_name, _record_dict_for_identity, _require_record_owner_or_manager,
    )
    raise HTTPException(status_code=410, detail="客户关键字段审批已取消，请在客户编辑中直接修改")
    customer = await _customer_or_404(customer_id, identity, db)
    await _require_record_owner_or_manager(customer, identity, db)
    data = customer.data or {}; pending = data.get("key_change") or {}
    if pending.get("status") == "待审批": raise HTTPException(status_code=409, detail="已有客户关键字段变更正在审批")
    title = body.title.strip(); credit_code = body.credit_code.strip()
    await _ensure_unique_customer_name(title, db, exclude_id=customer.id)
    if title == customer.title and credit_code == str(data.get("credit_code") or ""):
        raise HTTPException(status_code=422, detail="客户名称和统一社会信用代码均未变化")
    if credit_code and any(character.isspace() for character in credit_code): raise HTTPException(status_code=422, detail="统一社会信用代码不允许包含空格")
    request_data = {"status": "待审批", "before": {"title": customer.title, "credit_code": data.get("credit_code", "")}, "after": {"title": title, "credit_code": credit_code}, "requested_by": identity["username"], "requested_at": datetime.now().isoformat(timespec="seconds"), "comment": body.comment.strip()}
    customer.data = {**data, "key_change": request_data}
    db.add(_customer_event(customer, "提交客户关键字段变更", identity, body.comment))
    await db.commit(); await db.refresh(customer)
    return await _record_dict_for_identity(customer, identity, db)


@router.post(f"{settings.api_prefix}/customers/{{customer_id}}/key-change/review")
async def review_customer_key_change(customer_id: int, body: CustomerKeyChangeReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_event, _customer_or_404, _mark_customer_modified,
    )
    from app.core.permissions import (
        _ensure_unique_customer_name, _record_dict_for_identity,
    )
    raise HTTPException(status_code=410, detail="客户关键字段审批已取消，请在客户编辑中直接修改")
    if identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="只有管理员或客户主管可以审批客户关键字段变更")
    customer = await _customer_or_404(customer_id, identity, db)
    data = customer.data or {}; pending = data.get("key_change") or {}
    if pending.get("status") != "待审批": raise HTTPException(status_code=409, detail="该客户没有待审批的关键字段变更")
    if not body.approved and not body.comment.strip(): raise HTTPException(status_code=422, detail="驳回时必须填写原因")
    after = pending.get("after") or {}; new_title = str(after.get("title") or "").strip(); new_credit_code = str(after.get("credit_code") or "").strip()
    if body.approved:
        await _ensure_unique_customer_name(new_title, db, exclude_id=customer.id)
    if body.approved and new_credit_code:
        customers = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "customer", BusinessRecord.id != customer.id))).all())
        if any(str((item.data or {}).get("credit_code") or "").strip().casefold() == new_credit_code.casefold() for item in customers):
            raise HTTPException(status_code=409, detail="统一社会信用代码已被其他客户使用")
    reviewed = {**pending, "status": "已通过" if body.approved else "已驳回", "reviewed_by": identity["username"], "reviewed_at": datetime.now().isoformat(timespec="seconds"), "review_comment": body.comment.strip()}
    if body.approved:
        old_title = customer.title; customer.title = new_title; customer.customer = new_title
        customer.data = {**data, "credit_code": new_credit_code, "key_change": reviewed}
        linked = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.customer == old_title, BusinessRecord.module.in_(["contract", "case", "task", "finance"])))).all())
        for item in linked: item.customer = new_title
    else:
        customer.data = {**data, "key_change": reviewed}
    _mark_customer_modified(customer, identity)
    db.add(_customer_event(customer, "客户关键字段审批通过" if body.approved else "客户关键字段审批驳回", identity, body.comment))
    await db.commit(); await db.refresh(customer)
    return await _record_dict_for_identity(customer, identity, db)


@router.post(f"{settings.api_prefix}/customers/{{customer_id}}/portal/open")
async def open_customer_portal(customer_id: int, body: CustomerPortalActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.contracts import (
        _contract_person_values,
    )
    from app.core.crm import (
        _customer_event, _customer_or_404,
    )
    from app.core.system import (
        _portal_code_hash,
    )
    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="只有管理员或客户主管可以开通客户服务端")
    customer = await _customer_or_404(customer_id, identity, db)
    contracts = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "contract", BusinessRecord.customer == customer.title,
        BusinessRecord.status != "草稿",
    ))).all())
    if (customer.data or {}).get("level") != "签约客户" and not contracts:
        raise HTTPException(status_code=409, detail="客户签约或存在审批通过的合同后才能开通客户服务端")
    data = customer.data or {}
    contacts = list(dict.fromkeys(
        value.strip() for value in _contract_person_values(data.get("contact_accounts") or data.get("contact"))
        if value.strip()
    ))
    if not contacts:
        raise HTTPException(status_code=409, detail="请先在客户编辑中绑定客户联系人账号，再开通客户服务端")
    requested_account = body.account.strip()
    if requested_account and requested_account not in contacts:
        raise HTTPException(status_code=422, detail="服务账号必须从该客户已绑定的联系人账号中选择")
    if len(contacts) > 1 and not requested_account:
        raise HTTPException(status_code=422, detail="该客户绑定了多个联系人账号，请选择本次开通的客户服务账号")
    account = requested_account or contacts[0]
    account_user = await db.scalar(select(User).where(
        func.lower(User.username) == account.lower(), User.is_active.is_(True),
    ))
    if not account_user:
        raise HTTPException(status_code=422, detail="已绑定的客户联系人账号不存在或已停用，请在客户编辑中重新选择")
    old_portal = data.get("portal_access") or {}
    activation_code = uuid4().hex
    portal = {
        "account": account, "enabled": True, "activation_code_hash": _portal_code_hash(activation_code),
        "activated_at": None, "password_hash": "",
        "opened_by": identity["username"], "opened_at": datetime.now().isoformat(timespec="seconds"),
        "comment": body.comment.strip(),
    }
    customer.data = {**data, "portal_access": portal}
    db.add(_customer_event(customer, "开通客户服务端", identity, body.comment or f"服务账号：{account}"))
    await db.commit()
    return {"customer_id": customer.id, "account": account, "activation_code": activation_code, "notice": "激活码仅本次显示，请安全交付客户"}


@router.post(f"{settings.api_prefix}/customer-portal/activate")
async def activate_customer_portal(body: CustomerPortalActivationInput, db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_event,
    )
    from app.core.system import (
        _portal_code_hash,
    )
    customers = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "customer"))).all())
    customer = next((item for item in customers if str(((item.data or {}).get("portal_access") or {}).get("account") or "").casefold() == body.account.strip().casefold()), None)
    portal = (customer.data or {}).get("portal_access") if customer else None
    if not customer or not portal or not portal.get("enabled") or portal.get("activated_at") or not portal.get("activation_code_hash") or portal["activation_code_hash"] != _portal_code_hash(body.activation_code.strip()):
        raise HTTPException(status_code=401, detail="客户服务账号或激活码无效")
    customer.data = {**(customer.data or {}), "portal_access": {
        **portal, "password_hash": hash_password(body.password), "activation_code_hash": "",
        "activated_at": datetime.now().isoformat(timespec="seconds"),
    }}
    db.add(_customer_event(customer, "激活客户服务端", {"username": body.account.strip()}, "客户已设置服务端登录密码"))
    await db.commit()
    return {"account": portal["account"], "activated": True}


@router.post(f"{settings.api_prefix}/customers/{{customer_id}}/portal/close")
async def close_customer_portal(customer_id: int, body: CustomerPortalActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _customer_event, _customer_or_404,
    )
    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="只有管理员或客户主管可以停用客户服务端")
    customer = await _customer_or_404(customer_id, identity, db)
    portal = (customer.data or {}).get("portal_access") or {}
    if not portal.get("enabled"):
        raise HTTPException(status_code=409, detail="客户服务端尚未开通或已经停用")
    customer.data = {**(customer.data or {}), "portal_access": {**portal, "enabled": False, "closed_by": identity["username"], "closed_at": datetime.now().isoformat(timespec="seconds"), "close_comment": body.comment.strip()}}
    db.add(_customer_event(customer, "停用客户服务端", identity, body.comment))
    await db.commit()
    return {"customer_id": customer.id, "account": portal.get("account", ""), "enabled": False}


@router.post(f"{settings.api_prefix}/customer-portal/overview")
async def customer_portal_overview(body: CustomerPortalLoginInput, db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _portal_customer,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    from app.core.system import (
        _record_dict,
    )
    customer = await _portal_customer(body, db)
    records = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.customer == customer.title, BusinessRecord.module.in_(["contract", "case"])))).all())
    record_ids = [item.id for item in records]
    files = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id.in_(record_ids)))).all()) if record_ids else []
    return {
        "customer": {"id": customer.id, "serial_no": customer.serial_no, "name": customer.title, "level": (customer.data or {}).get("level", "")},
        "contracts": [_record_dict(item) for item in records if item.module == "contract"],
        "cases": [_record_dict(item) for item in records if item.module == "case"],
        "documents": [_attachment_dict(item, next((record for record in records if record.id == item.record_id), None)) for item in files],
    }


@router.post(f"{settings.api_prefix}/customer-portal/files/{{attachment_id}}/download")
async def customer_portal_download(attachment_id: int, body: CustomerPortalLoginInput, db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _portal_customer,
    )
    customer = await _portal_customer(body, db)
    attachment = await db.get(FileAttachment, attachment_id)
    record = await db.get(BusinessRecord, attachment.record_id) if attachment and attachment.record_id else None
    if not attachment or not record or record.customer != customer.title or record.module not in {"contract", "case"}:
        raise HTTPException(status_code=404, detail="客户文档不存在")
    path = Path(attachment.path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="客户文档文件不存在")
    return FileResponse(path, media_type=attachment.content_type, filename=Path(attachment.original_name).name)


@router.post(f"{settings.api_prefix}/customer-portal/demands", status_code=status.HTTP_201_CREATED)
async def customer_portal_create_demand(body: CustomerPortalDemandInput, db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _portal_customer,
    )
    from app.core.tasks import (
        _add_task_message_notifications, _next_rw_task_serial_no,
    )
    customer = await _portal_customer(body, db)
    case_record = None
    if body.case_no.strip():
        case_record = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "case", BusinessRecord.customer == customer.title, BusinessRecord.serial_no == body.case_no.strip()))
        if not case_record:
            raise HTTPException(status_code=422, detail="所选案件不属于当前客户")
    owner = customer.owner
    if not await db.scalar(select(User.id).where(User.username == owner, User.is_active.is_(True))):
        raise HTTPException(status_code=409, detail="客户负责人不存在或已停用，暂不能提交需求")
    serial_no = await _next_rw_task_serial_no(db)
    task = BusinessRecord(
        module="task", serial_no=serial_no, title=f"客户需求—{body.title.strip()}",
        customer=customer.title, status="待接收", owner=owner, department=customer.department, description=body.content.strip(),
        data={"deadline": str(date.today() + timedelta(days=7)), "priority": "普通", "source": "客户任务", "task_type": "手动任务", "initiator": owner, "collaborators": [], "case_no": case_record.serial_no if case_record else "", "case_id": case_record.id if case_record else None, "portal_customer_id": customer.id, "portal_account": body.account.strip()},
    )
    db.add(task); await db.flush()
    await _add_task_message_notifications(task, WorkflowEvent(record_id=task.id, action="客户服务端提交需求", to_status="待接收", operator=body.account.strip(), comment=body.content.strip()), db, content="客户提交了新的服务需求.")
    await db.commit(); await db.refresh(task)
    return {"id": task.id, "serial_no": task.serial_no, "status": task.status, "owner": task.owner}


@router.get(f"{settings.api_prefix}/notaries/lookup")
async def lookup_notary_by_certificate(certificate_no: str = Query(min_length=2, max_length=128), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    lookup = certificate_no.strip().casefold()
    records = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "notary", *(await _record_scope_conditions(identity, db))))).all()
    matches = [item for item in records if str((item.data or {}).get("certificate_no", "")).strip().casefold() == lookup]
    if not matches:
        raise HTTPException(status_code=404, detail="未找到关联公证记录或当前账号无权查看")
    if len(matches) > 1:
        raise HTTPException(status_code=409, detail="公证书号匹配到多条记录，请先处理重复编号")
    return _record_dict(matches[0], await _allowed_field_keys(identity, db))


@router.post(f"{settings.api_prefix}/notaries/{{notary_id}}/certificate")
async def register_notary_certificate(notary_id: int, body: NotaryCertificateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _warehouse_location_display,
    )
    from app.core.investigation import (
        _resolve_warehouse_location, _warehouse_location_data,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager, _user_has_job_permission,
    )
    from app.core.system import (
        _record_dict,
    )
    notary = await _ensure_record_module(notary_id, "notary", identity, db); await _require_record_owner_or_manager(notary, identity, db)
    operator = await db.scalar(select(User).where(User.username == identity["username"]))
    if not operator or not await _user_has_job_permission(operator, "公证书号码登记", db):
        raise HTTPException(status_code=403, detail="当前账号没有公证书号码登记岗位权限")
    if notary.status not in {"等待材料", "待审核", "审核驳回", "审核通过"}: raise HTTPException(status_code=409, detail="当前公证记录不能登记公证书信息")
    duplicate = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.module == "notary", BusinessRecord.id != notary.id, BusinessRecord.data["certificate_no"].as_string() == body.certificate_no.strip()))
    if duplicate: raise HTTPException(status_code=409, detail="公证书编号已经登记")
    if not body.storage_location_id:
        raise HTTPException(status_code=422, detail="请选择仓库库位")
    warehouse, location = await _resolve_warehouse_location(body, db)
    storage_location = _warehouse_location_display(warehouse, location)
    notary.data = {**(notary.data or {}), "certificate_no": body.certificate_no.strip(), "certificate_issued_date": str(body.issued_date), "certificate_storage_location": storage_location, **_warehouse_location_data(warehouse, location), "physical_received": body.physical_received, "certificate_registered_at": datetime.now().isoformat(timespec="seconds"), "certificate_operator": identity["username"]}
    db.add(WorkflowEvent(record_id=notary.id, action="登记公证书", from_status=notary.status, to_status=notary.status, operator=identity["username"], comment=f"{body.certificate_no}；{storage_location}。{body.comment}")); await db.commit(); await db.refresh(notary); return _record_dict(notary)


@router.post(f"{settings.api_prefix}/notaries/{{notary_id}}/review")
async def review_notary(notary_id: int, body: NotaryReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _convert_notary_to_case,
    )
    from app.core.permissions import (
        _ensure_record_module, _user_has_job_permission,
    )
    from app.core.system import (
        _record_dict,
    )
    reviewer = await db.scalar(select(User).where(User.username == identity["username"]))
    if not reviewer or not await _user_has_job_permission(reviewer, "公证审核", db):
        raise HTTPException(status_code=403, detail="当前账号没有公证审核岗位权限")
    notary = await _ensure_record_module(notary_id, "notary", identity, db)
    if notary.status != "待审核":
        raise HTTPException(status_code=409, detail="该公证记录已完成审核")
    clue_id = int((notary.data or {}).get("clue_id", 0))
    clue = await db.get(BusinessRecord, clue_id)
    if not clue:
        raise HTTPException(status_code=409, detail="关联线索不存在")
    if not body.approved:
        notary.status = "审核驳回"
        clue.data = {**(clue.data or {}), "notary": "审核驳回，等待补正扫描件"}
        case_record = await db.get(BusinessRecord, int((clue.data or {}).get("converted_case_id") or 0))
        if case_record and case_record.status == "等待审核公证书": case_record.status = "等待公证书"
        db.add_all([
            WorkflowEvent(record_id=notary.id, action="公证审核驳回", from_status="待审核", to_status="审核驳回", operator=identity["username"], comment=body.comment),
            WorkflowEvent(record_id=clue.id, action="公证材料退回补正", from_status=clue.status, to_status=clue.status, operator=identity["username"], comment=body.comment),
        ])
        if case_record: db.add(WorkflowEvent(record_id=case_record.id, action="公证材料退回补正", from_status="等待审核公证书", to_status=case_record.status, operator=identity["username"], comment=body.comment))
        await db.commit()
        await db.refresh(notary)
        return {"notary": _record_dict(notary), "case": None}
    case_record = await _convert_notary_to_case(
        notary, clue, db, operator=identity["username"], comment=body.comment,
        case_type=body.case_type, court=body.court,
    )
    await db.commit()
    await db.refresh(notary)
    await db.refresh(case_record)
    return {"notary": _record_dict(notary), "case": _record_dict(case_record)}


@router.get(f"{settings.api_prefix}/customers/reference-options")
async def customer_reference_options(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Return customer-facing dictionaries without granting system-parameter administration."""
    customer_types = (await db.scalars(select(SystemParameter).where(
        SystemParameter.category == "customer_type", SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.sort_order, SystemParameter.id))).all()
    return {"customer_types": [{"value": item.name, "label": item.name, "code": item.code} for item in customer_types]}


@router.get(f"{settings.api_prefix}/customers")
async def list_customers(
    scope: str = Query("mine", pattern="^(mine|recycle|department|department_recycle|company|company_recycle|public|shared|recent_contact|recent_update)$"),
    customer_name: str = "",
    customer_type: str = Query("客户", min_length=1, max_length=64),
    manager: str = "",
    page: int = Query(1, ge=0),
    page_size: int = Query(15, ge=0, le=200),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Original customer-list scopes with authoritative server-side filtering and paging."""
    from app.core.cases import (
        _is_civil_case_type,
    )
    from app.core.formatters import (
        _normalize_customer_name, _parse_customer_contact_at,
    )
    from app.core.permissions import (
        _visible_record_ids,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    # The legacy POST contract treats zero as an omitted pager value. Keep
    # that compatibility at the API boundary while still rejecting negatives.
    page = page or 1
    page_size = page_size or 15
    current_user = await db.scalar(
        select(User).where(User.username == identity["username"], User.is_active.is_(True))
    )
    if not current_user:
        raise HTTPException(status_code=401, detail="当前用户不存在或已停用")
    active_customer_types = set((await db.scalars(select(SystemParameter.name).where(
        SystemParameter.category == "customer_type", SystemParameter.is_active.is_(True),
    ))).all())
    if customer_type not in active_customer_types:
        raise HTTPException(status_code=422, detail="客户类型不存在或已停用")
    # Customer managers are stored as a JSON array.  Do not use a serialized
    # JSON ``contains`` predicate here: a user named ``ann`` would otherwise
    # match a manager named ``joann``.  Legacy rows may contain a display name
    # instead of a username, but it is safe to honor that alias only when the
    # active-user directory resolves it uniquely (the same rule used when
    # assigning customer managers).
    manager_tokens = {current_user.username}
    display_name = str(current_user.display_name or "").strip()
    if display_name:
        display_name_count = int(
            await db.scalar(
                select(func.count()).select_from(User).where(
                    User.is_active.is_(True), User.display_name == display_name
                )
            )
            or 0
        )
        if display_name_count == 1:
            manager_tokens.add(display_name)
    conditions = [BusinessRecord.module == "customer"]
    if scope in {"recycle", "department_recycle", "company_recycle"}:
        conditions.append(BusinessRecord.status == "已回收")
    elif scope == "public":
        if current_user.role not in {"admin", "manager", "user"}:
            raise HTTPException(status_code=403, detail="当前角色不能查看公海客户")
        conditions.append(BusinessRecord.status == "公海")
    elif scope == "shared":
        if current_user.role not in {"admin", "manager", "user"}:
            raise HTTPException(status_code=403, detail="当前角色不能查看共享客户")
        conditions.append(BusinessRecord.status.not_in(["已回收", "公海"]))
    elif scope == "recent_contact":
        # The original page is a projection of otherwise-visible active
        # customers, not a second customer owner register.  A non-empty real
        # contact timestamp is mandatory; recycled rows remain isolated in
        # their dedicated recycle-bin pages.
        conditions.append(BusinessRecord.status.not_in(["已回收", "公海"]))
    elif scope == "recent_update":
        # Original evidence shows this is an actor projection, not an all-firm
        # ``updated_at`` feed: rows last changed by other users on the same day
        # are absent.  Recycled rows remain eligible, while public-pool rows are
        # isolated on their dedicated page.
        if current_user.role not in {"admin", "manager", "user"}:
            raise HTTPException(status_code=403, detail="当前角色不能查看最近更新的客户")
        conditions.append(BusinessRecord.status != "公海")
    elif scope == "company":
        # Recycled (deleted) and public-pool customers have dedicated lists.
        conditions.append(BusinessRecord.status.not_in(["已回收", "公海"]))
    else:
        conditions.append(BusinessRecord.status.not_in(["已回收", "公海"]))
    if scope in {"department", "department_recycle"}:
        if current_user.role not in {"admin", "manager"}:
            raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以查看部门客户")
    elif scope in {"company", "company_recycle"} and current_user.role != "admin":
        detail = "只有系统管理员可以查看公司回收站" if scope == "company_recycle" else "只有系统管理员可以查看公司客户"
        raise HTTPException(status_code=403, detail=detail)
    normalized_name = customer_name.strip()
    if normalized_name:
        like = f"%{normalized_name}%"
        conditions.append(or_(BusinessRecord.serial_no.ilike(like), BusinessRecord.title.ilike(like)))
    conditions.append(
        func.coalesce(BusinessRecord.data["customer_type"].as_string(), "客户") == customer_type
    )
    normalized_manager = manager.strip()
    manager_search_tokens = {normalized_manager} if normalized_manager else set()
    if normalized_manager:
        # The original selector displays a person's name, while current rows
        # persist usernames.  Resolve an exact active display name only when it
        # identifies one account; duplicate display names must never broaden a
        # customer search to several unrelated managers.  Keep the literal
        # token as well for usernames and safely migrated legacy rows.
        display_name_usernames = list(
            (await db.scalars(
                select(User.username).where(
                    User.is_active.is_(True), User.display_name == normalized_manager
                )
            )).all()
        )
        if len(display_name_usernames) == 1:
            manager_search_tokens.add(display_name_usernames[0])
    candidate_rows = list(
        (await db.scalars(
        select(BusinessRecord)
        .where(*conditions)
        .order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc())
        )).all()
    )

    def exact_managers(item: BusinessRecord) -> set[str]:
        raw_managers = (item.data or {}).get("customer_managers", [])
        if not isinstance(raw_managers, list):
            return set()
        return {str(value).strip() for value in raw_managers if str(value).strip()}

    def customer_participants(item: BusinessRecord) -> set[str]:
        data = item.data or {}
        source = str(data.get("customer_source") or data.get("source_person") or "").strip()
        return {str(item.owner or "").strip(), *exact_managers(item), source} - {""}

    department_users = (await db.scalars(
        select(User).where(User.is_active.is_(True), User.department == current_user.department)
    )).all()
    department_tokens = {
        value
        for user in department_users
        for value in (str(user.username or "").strip(), str(user.display_name or "").strip())
        if value
    }

    # “我的客户” means that the current user is either a customer manager or
    # the source person; this applies to administrators too.
    if scope in {"mine", "recycle"}:
        candidate_rows = [
            item
            for item in candidate_rows
            if bool(customer_participants(item) & manager_tokens)
        ]
    # A department list is a projection of the personnel relationships shown
    # in the screenshot, not merely the department stamped on the record.
    if scope in {"department", "department_recycle"}:
        candidate_rows = [
            item for item in candidate_rows
            if bool(customer_participants(item) & department_tokens)
        ]
    if scope == "shared":
        # “我的共享客户” contains only active customer rows with an explicit
        # recipient relationship.  Admin keeps full-firm audit visibility but
        # the semantic scope still excludes customers that were never shared.
        if current_user.role == "admin":
            candidate_rows = [
                item
                for item in candidate_rows
                if bool({str(value).strip() for value in (item.data or {}).get("shared_with", []) if str(value).strip()})
            ]
        else:
            candidate_rows = [
                item
                for item in candidate_rows
                if bool(
                    {
                        str(value).strip()
                        for value in (item.data or {}).get("shared_with", [])
                        if str(value).strip()
                    }
                    & manager_tokens
                )
            ]
    if scope in {"recent_contact", "recent_update"}:
        if current_user.role != "admin":
            visible_ids = await _visible_record_ids(identity, db)
            candidate_rows = [item for item in candidate_rows if item.id in visible_ids]
    if scope == "recent_contact":
        candidate_rows = [
            item for item in candidate_rows
            if _parse_customer_contact_at((item.data or {}).get("last_contact_at")) is not None
        ]
    if scope == "recent_update":
        latest_modifier_by_record: dict[int, str] = {}
        candidate_ids = [item.id for item in candidate_rows]
        if candidate_ids:
            modification_events = (await db.scalars(
                select(WorkflowEvent).where(
                    WorkflowEvent.record_id.in_(candidate_ids),
                    WorkflowEvent.action.in_(CUSTOMER_MODIFICATION_ACTIONS),
                ).order_by(WorkflowEvent.created_at.desc(), WorkflowEvent.id.desc())
            )).all()
            for event in modification_events:
                latest_modifier_by_record.setdefault(event.record_id, event.operator)
        candidate_rows = [
            item for item in candidate_rows
            if str(
                latest_modifier_by_record.get(item.id)
                or (item.data or {}).get("last_modified_by")
                or ""
            ).strip() == identity["username"]
        ]
    if normalized_manager:
        candidate_rows = [
            item
            for item in candidate_rows
            if str(item.owner or "").strip() in manager_search_tokens
            or bool(exact_managers(item) & manager_search_tokens)
        ]

    if scope == "recent_contact":
        candidate_rows.sort(
            key=lambda item: (
                _parse_customer_contact_at((item.data or {}).get("last_contact_at")) or datetime.min,
                item.id,
            ),
            reverse=True,
        )
    if scope == "recent_update":
        candidate_rows.sort(
            key=lambda item: (
                _parse_customer_contact_at(item.updated_at) or datetime.min,
                item.id,
            ),
            reverse=True,
        )

    total = len(candidate_rows)
    page_items = candidate_rows[(page - 1) * page_size : page * page_size]
    allowed_fields = await _allowed_field_keys(identity, db)
    # Contract/case totals are relationship projections, not editable customer
    # attributes. Historical rows may still contain denormalized zeroes, so
    # recompute the visible page from authoritative related records every time.
    related_records = list((await db.scalars(
        select(BusinessRecord).where(
            BusinessRecord.module.in_(["contract", "case"]),
        )
    )).all())
    customers_by_id = {item.id: item for item in page_items}
    customers_by_no = {str(item.serial_no or "").strip(): item for item in page_items if str(item.serial_no or "").strip()}
    customers_by_name = {_normalize_customer_name(item.title): item for item in page_items}
    relationship_counts = {
        item.id: {"contract_count": 0, "civil_case_count": 0}
        for item in page_items
    }
    for related in related_records:
        related_data = related.data or {}
        linked_customer = None
        try:
            linked_customer = customers_by_id.get(
                int(related_data.get("customer_id") or related_data.get("customer_record_id") or 0)
            )
        except (TypeError, ValueError):
            linked_customer = None
        if linked_customer is None:
            customer_no = str(related_data.get("customer_no") or "").strip()
            if customer_no:
                linked_customer = customers_by_no.get(customer_no)
        if linked_customer is None and related.customer:
            linked_customer = customers_by_name.get(_normalize_customer_name(related.customer))
        if linked_customer is None:
            continue
        if related.module == "contract":
            if related.status in {"已归档", "Archived", "archived"}:
                continue
            relationship_counts[linked_customer.id]["contract_count"] += 1
        elif _is_civil_case_type(related_data.get("case_type")):
            relationship_counts[linked_customer.id]["civil_case_count"] += 1
    response_items = []
    for item in page_items:
        row = _record_dict(item, allowed_fields)
        row["data"] = {
            **(row.get("data") or {}),
            **relationship_counts[item.id],
        }
        response_items.append(row)
    legacy_summary_fields = [
        "agency_fee_due",
        "official_fee_unreceived",
        "total_paid_case_office_fee_amount",
        "total_cashed_case_office_fee_amount",
        "total_un_cashed_case_office_fee_amount",
        "total_deficit_case_office_fee_amount",
        "total_case_non_office_fee_amount",
        "total_cashed_case_non_office_fee_amount",
        "total_un_cashed_case_non_office_fee_amount",
        "total_case_commission_fee_amount",
        "total_cashed_case_commission_fee_amount",
        "total_paid_case_commission_fee_amount",
        "total_un_paid_case_commission_fee_amount",
        "total_invoiced_amount",
        "total_invoice_over_amount",
        "total_un_invoiced_amount",
    ]

    def legacy_summary_value(item: BusinessRecord, key: str) -> float:
        try:
            return float((item.data or {}).get(key) or 0)
        except (TypeError, ValueError):
            return 0

    summary = {
        key: round(sum(legacy_summary_value(item, key) for item in candidate_rows), 2)
        for key in legacy_summary_fields
    }
    return {
        "items": response_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "summary": summary,
    }
