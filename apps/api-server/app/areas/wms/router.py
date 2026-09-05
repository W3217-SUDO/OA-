"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.dependencies import (
    AsyncSession, BusinessRecord, Depends, File, FileAttachment,
    HTTPException, Query, UploadFile, User, Warehouse,
    WarehouseEvidenceLocation, WarehouseStorageLocation, WorkflowEvent, csv, current_identity,
    date, func, get_db, io, or_,
    select, settings, status,
)
from app.models_shared import (
    EvidenceBatchRegistrationInput, EvidenceRegistrationItem, WarehouseBorrowInput, WarehouseEvidenceCheckInInput, WarehouseEvidenceCheckOutInput,
    WarehouseEvidenceDestroyInput, WarehouseEvidenceInput, WarehouseEvidenceRecheckInInput, WarehouseGoodsListInput, WarehouseReturnConfirmInput,
    WarehouseReturnInput, WarehouseScrapInput,
)
from fastapi import APIRouter

router = APIRouter()


@router.post(f"{settings.api_prefix}/evidence/register", status_code=status.HTTP_201_CREATED)
async def register_evidence(body: EvidenceRegistrationItem, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.investigation import (
        _build_evidence_record,
    )
    from app.core.system import (
        _record_dict,
    )
    record = await _build_evidence_record(body, identity, db)
    await db.commit(); await db.refresh(record); return _record_dict(record)


@router.post(f"{settings.api_prefix}/evidence/batch-register", status_code=status.HTTP_201_CREATED)
async def batch_register_evidence(body: EvidenceBatchRegistrationInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.investigation import (
        _build_evidence_record,
    )
    created_ids: list[int] = []; errors: list[dict] = []
    for index, entry in enumerate(body.items, start=1):
        try:
            record = await _build_evidence_record(entry, identity, db)
            await db.commit(); await db.refresh(record)
            created_ids.append(record.id)
        except HTTPException as exc:
            await db.rollback()
            errors.append({"index": index, "error": exc.detail})
    return {"created": len(created_ids), "created_ids": created_ids, "failed": len(errors), "errors": errors}


@router.get(f"{settings.api_prefix}/evidence")
async def list_evidence_records(keyword: str = "", page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _record_dict,
    )
    conditions = [BusinessRecord.module == "evidence", *(await _record_scope_conditions(identity, db))]
    if keyword.strip():
        term = f"%{keyword.strip()}%"
        conditions.append(or_(BusinessRecord.title.ilike(term), BusinessRecord.serial_no.ilike(term), BusinessRecord.customer.ilike(term), BusinessRecord.description.ilike(term)))
    total = int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(*conditions)) or 0)
    items = (await db.scalars(select(BusinessRecord).where(*conditions).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    return {"items": [_record_dict(item) for item in items], "total": total, "page": page, "page_size": page_size}


@router.get(f"{settings.api_prefix}/evidence/{{evidence_id}}/files")
async def list_evidence_files(evidence_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    from app.core.system import (
        _record_dict,
    )
    item = await _ensure_record_module(evidence_id, "evidence", identity, db)
    attachments = (await db.scalars(select(FileAttachment).where(FileAttachment.record_id == item.id).order_by(FileAttachment.created_at.desc(), FileAttachment.id.desc()))).all()
    return {"record": _record_dict(item), "items": [_attachment_dict(attachment, item) for attachment in attachments], "total": len(attachments)}


@router.post(f"{settings.api_prefix}/evidence/import", status_code=status.HTTP_201_CREATED)
async def import_evidence_records(file: UploadFile = File(...), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.investigation import (
        _build_evidence_record,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="仅支持 UTF-8 CSV 文件")
    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="导入文件不能超过 5MB")
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="CSV 必须使用 UTF-8 编码") from exc
    clues = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "clue", *(await _record_scope_conditions(identity, db))))).all()
    clue_by_no = {item.serial_no.strip().casefold(): item for item in clues}
    created = 0; errors: list[dict] = []
    for row_no, row in enumerate(csv.DictReader(io.StringIO(content)), 2):
        try:
            title = (row.get("证据标题") or row.get("title") or "").strip()
            clue_no = (row.get("关联线索编号") or row.get("clue_no") or "").strip()
            if not title:
                raise ValueError("证据标题为必填项")
            clue = clue_by_no.get(clue_no.casefold()) if clue_no else None
            if clue_no and not clue:
                raise ValueError("关联线索编号未找到或无权访问")
            entry = EvidenceRegistrationItem(
                title=title,
                owner=(row.get("负责人") or row.get("owner") or "").strip(),
                source=(row.get("材料来源") or row.get("source") or "调查取证").strip(),
                description=(row.get("说明") or row.get("description") or "").strip(),
                clue_id=clue.id if clue else None,
                notarization_no=(row.get("公证编号") or row.get("notarization_no") or "").strip(),
                invoice_no=(row.get("发票号") or row.get("invoice_no") or "").strip(),
                storage_location=(row.get("存放位置") or row.get("storage_location") or "").strip(),
                storage_state=(row.get("存放状态") or row.get("storage_state") or "待整理").strip(),
            )
            record = await _build_evidence_record(entry, identity, db)
            created += 1
        except (HTTPException, ValueError) as exc:
            await db.rollback()
            errors.append({"row": row_no, "error": str(exc) or "证据登记失败"})
    await db.commit()
    return {"created": created, "failed": len(errors), "errors": errors}


@router.get(f"{settings.api_prefix}/warehouse/catalog")
async def warehouse_catalog(
    include_inactive: bool = True,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _require_record_module_menu,
    )
    await _require_record_module_menu("warehouse", identity, db, action="查看")
    warehouse_statement = select(Warehouse)
    location_statement = select(WarehouseStorageLocation)
    if not include_inactive:
        warehouse_statement = warehouse_statement.where(Warehouse.is_active.is_(True))
        location_statement = location_statement.where(WarehouseStorageLocation.is_active.is_(True))
    warehouses = list((await db.scalars(warehouse_statement.order_by(Warehouse.sort_order, Warehouse.warehouse_no, Warehouse.id))).all())
    locations = list((await db.scalars(location_statement.order_by(WarehouseStorageLocation.sort_order, WarehouseStorageLocation.storage_location_no, WarehouseStorageLocation.id))).all())
    counts = dict((await db.execute(
        select(WarehouseEvidenceLocation.storage_location_id, func.count(WarehouseEvidenceLocation.id))
        .group_by(WarehouseEvidenceLocation.storage_location_id)
    )).all())
    locations_by_warehouse: dict[int, list[dict[str, object]]] = {}
    for location in locations:
        locations_by_warehouse.setdefault(location.warehouse_id, []).append({
            "id": location.id,
            "storage_location_no": location.storage_location_no,
            "name": location.name,
            "address": location.address,
            "is_active": location.is_active,
            "sort_order": location.sort_order,
            "goods_count": int(counts.get(location.id, 0)),
        })
    return {
        "items": [
            {
                "id": warehouse.id,
                "warehouse_no": warehouse.warehouse_no,
                "name": warehouse.name,
                "address": warehouse.address,
                "is_active": warehouse.is_active,
                "sort_order": warehouse.sort_order,
                "goods_count": sum(int(location["goods_count"]) for location in locations_by_warehouse.get(warehouse.id, [])),
                "locations": locations_by_warehouse.get(warehouse.id, []),
            }
            for warehouse in warehouses
        ],
        "total": len(warehouses),
        "location_total": len(locations),
    }


@router.get(f"{settings.api_prefix}/warehouse/evidence")
async def list_warehouse_evidence(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=15, ge=1, le=200),
    warehouse_id: int | None = Query(default=None, gt=0),
    storage_location_id: int | None = Query(default=None, gt=0),
    keyword: str = "",
    rights_holder: str = "",
    evidence_status: str = "",
    case_no: str = "",
    shop_name: str = "",
    investigator: str = "",
    notary_no: str = "",
    evidence_date_from: str = "",
    evidence_date_to: str = "",
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.investigation import (
        _warehouse_evidence_dict, _warehouse_evidence_location_statement,
    )
    from app.core.permissions import (
        _record_scope_conditions, _require_record_module_menu,
    )
    await _require_record_module_menu("warehouse", identity, db, action="查看")
    conditions = list(await _record_scope_conditions(identity, db))
    if warehouse_id:
        conditions.append(WarehouseEvidenceLocation.warehouse_id == warehouse_id)
    if storage_location_id:
        conditions.append(WarehouseEvidenceLocation.storage_location_id == storage_location_id)
    if keyword.strip():
        term = f"%{keyword.strip()}%"
        conditions.append(or_(
            BusinessRecord.serial_no.ilike(term),
            BusinessRecord.title.ilike(term),
            BusinessRecord.customer.ilike(term),
            BusinessRecord.data["legacy_evidence_no"].as_string().ilike(term),
            BusinessRecord.data["clue_no"].as_string().ilike(term),
            BusinessRecord.data["case_no"].as_string().ilike(term),
        ))
    def data_like(key: str, value: str):
        return BusinessRecord.data[key].as_string().ilike(f"%{value.strip()}%") if value.strip() else None

    filter_conditions = [
        data_like("rights_holder", rights_holder),
        data_like("evidence_status", evidence_status),
        data_like("case_no", case_no),
        data_like("shop_name", shop_name),
        data_like("investigator", investigator),
    ]
    conditions.extend(condition for condition in filter_conditions if condition is not None)
    if notary_no.strip():
        term = f"%{notary_no.strip()}%"
        conditions.append(or_(
            BusinessRecord.data["notary_no"].as_string().ilike(term),
            BusinessRecord.data["notary_nos"].as_string().ilike(term),
            BusinessRecord.data["certificate_no"].as_string().ilike(term),
            BusinessRecord.data["notarization_no"].as_string().ilike(term),
        ))
    if evidence_date_from.strip():
        conditions.append(BusinessRecord.data["evidence_date"].as_string() >= evidence_date_from.strip())
    if evidence_date_to.strip():
        conditions.append(BusinessRecord.data["evidence_date"].as_string() <= evidence_date_to.strip())
    statement = _warehouse_evidence_location_statement(conditions)
    total = int(await db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = (await db.execute(statement.order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    return {
        "items": [_warehouse_evidence_dict(*row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post(f"{settings.api_prefix}/warehouse/evidence", status_code=status.HTTP_201_CREATED)
async def create_warehouse_evidence(body: WarehouseEvidenceInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.investigation import (
        _resolve_warehouse_location, _set_warehouse_evidence_location, _warehouse_location_data,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以登记证物")
    if await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == body.serial_no.strip())):
        raise HTTPException(status_code=409, detail="线索编号已存在")
    department = "上海分所"
    if identity.get("role") != "admin":
        user = await db.scalar(select(User).where(User.username == identity["username"]))
        if not user:
            raise HTTPException(status_code=401, detail="当前用户不存在")
        department = user.department
    warehouse, location = await _resolve_warehouse_location(body, db)
    evidence_data = body.model_dump(mode="json", exclude={"serial_no", "description", "warehouse_id", "storage_location_id", "warehouse", "location"})
    evidence_data.update(_warehouse_location_data(warehouse, location))
    evidence_data.update({
        "category": "证物",
        "quantity": 1,
        "unit": "件",
        "evidence_status": "未入库",
        "registered_at": str(date.today()),
        "registered_by": identity["username"],
    })
    item = BusinessRecord(
        module="warehouse",
        serial_no=body.serial_no.strip(),
        title=body.shop_name.strip(),
        customer=body.rights_holder.strip(),
        status="在库",
        owner=body.investigator.strip(),
        department=department,
        description=body.description.strip(),
        data=evidence_data,
    )
    db.add(item)
    await db.flush()
    await _set_warehouse_evidence_location(item.id, warehouse, location, identity["username"], db)
    db.add(WorkflowEvent(record_id=item.id, action="证物登记", to_status="未入库", operator=identity["username"], comment=body.description.strip()))
    await db.commit()
    await db.refresh(item)
    return _record_dict(item, await _allowed_field_keys(identity, db))


@router.patch(f"{settings.api_prefix}/warehouse/evidence/{{item_id}}")
async def update_warehouse_evidence(item_id: int, body: WarehouseEvidenceInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.investigation import (
        _resolve_warehouse_location, _set_warehouse_evidence_location, _warehouse_evidence_status, _warehouse_location_data,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以修改证物资料")
    item = await _ensure_record_module(item_id, "warehouse", identity, db)
    evidence_status = _warehouse_evidence_status(item)
    if evidence_status in {"已出库", "已销毁"}:
        raise HTTPException(status_code=409, detail="已出库或已销毁的证物不能修改资料")
    duplicate = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == body.serial_no.strip(), BusinessRecord.id != item.id))
    if duplicate:
        raise HTTPException(status_code=409, detail="线索编号已存在")
    warehouse, location = await _resolve_warehouse_location(body, db)
    process_fields = {
        key: value for key, value in (item.data or {}).items()
        if key in {
            "category", "quantity", "unit", "evidence_status", "registered_at", "registered_by",
            "checked_in_at", "checked_in_by", "checked_out_at", "checked_out_by", "recipient",
            "checkout_purpose", "rechecked_in_at", "rechecked_in_by", "return_condition",
            "destroyed_at", "destroyed_by", "destroy_reason",
        }
    }
    evidence_data = body.model_dump(mode="json", exclude={"serial_no", "description", "warehouse_id", "storage_location_id", "warehouse", "location"})
    evidence_data.update(_warehouse_location_data(warehouse, location))
    evidence_data.update(process_fields)
    item.serial_no = body.serial_no.strip()
    item.title = body.shop_name.strip()
    item.customer = body.rights_holder.strip()
    item.owner = body.investigator.strip()
    item.description = body.description.strip()
    item.data = evidence_data
    await _set_warehouse_evidence_location(item.id, warehouse, location, identity["username"], db)
    db.add(WorkflowEvent(record_id=item.id, action="修改证物资料", from_status=evidence_status, to_status=evidence_status, operator=identity["username"], comment=body.description.strip()))
    await db.commit()
    await db.refresh(item)
    return _record_dict(item, await _allowed_field_keys(identity, db))


@router.post(f"{settings.api_prefix}/warehouse/evidence/{{item_id}}/check-in")
async def check_in_warehouse_evidence(item_id: int, body: WarehouseEvidenceCheckInInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.investigation import (
        _resolve_warehouse_location, _set_warehouse_evidence_location, _warehouse_evidence_status, _warehouse_location_data,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以办理证物入库")
    item = await _ensure_record_module(item_id, "warehouse", identity, db)
    previous = _warehouse_evidence_status(item)
    if previous != "未入库":
        raise HTTPException(status_code=409, detail="只有未入库证物可以办理首次入库")
    warehouse, location = await _resolve_warehouse_location(body, db)
    item.status = "在库"
    item.data = {**(item.data or {}), **_warehouse_location_data(warehouse, location), "evidence_status": "已入库", "checked_in_at": str(date.today()), "checked_in_by": identity["username"]}
    await _set_warehouse_evidence_location(item.id, warehouse, location, identity["username"], db)
    db.add(WorkflowEvent(record_id=item.id, action="证物入库", from_status=previous, to_status="已入库", operator=identity["username"], comment=body.comment.strip()))
    await db.commit()
    await db.refresh(item)
    return _record_dict(item, await _allowed_field_keys(identity, db))


@router.post(f"{settings.api_prefix}/warehouse/evidence/{{item_id}}/check-out")
async def check_out_warehouse_evidence(item_id: int, body: WarehouseEvidenceCheckOutInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.investigation import (
        _warehouse_evidence_status,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以办理证物出库")
    item = await _ensure_record_module(item_id, "warehouse", identity, db)
    previous = _warehouse_evidence_status(item)
    if previous not in {"已入库", "已重新入库"}:
        raise HTTPException(status_code=409, detail="只有在库证物可以办理出库")
    item.status = "借出"
    item.data = {**(item.data or {}), "evidence_status": "已出库", "checked_out_at": str(date.today()), "checked_out_by": identity["username"], "recipient": body.recipient.strip(), "checkout_purpose": body.purpose.strip()}
    db.add(WorkflowEvent(record_id=item.id, action="证物出库", from_status=previous, to_status="已出库", operator=identity["username"], comment=f"领取人：{body.recipient.strip()}；用途：{body.purpose.strip()}。{body.comment.strip()}"))
    await db.commit()
    await db.refresh(item)
    return _record_dict(item, await _allowed_field_keys(identity, db))


@router.post(f"{settings.api_prefix}/warehouse/evidence/{{item_id}}/recheck-in")
async def recheck_in_warehouse_evidence(item_id: int, body: WarehouseEvidenceRecheckInInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.investigation import (
        _resolve_warehouse_location, _set_warehouse_evidence_location, _warehouse_evidence_status, _warehouse_location_data,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以办理证物重新入库")
    item = await _ensure_record_module(item_id, "warehouse", identity, db)
    previous = _warehouse_evidence_status(item)
    if previous != "已出库":
        raise HTTPException(status_code=409, detail="只有已出库证物可以办理重新入库")
    warehouse, location = await _resolve_warehouse_location(body, db)
    previous_data = item.data or {}
    item.status = "在库"
    item.data = {**previous_data, **_warehouse_location_data(warehouse, location), "evidence_status": "已重新入库", "rechecked_in_at": str(date.today()), "rechecked_in_by": identity["username"], "return_condition": body.condition.strip(), "last_recipient": previous_data.get("recipient", ""), "recipient": "", "checkout_purpose": ""}
    await _set_warehouse_evidence_location(item.id, warehouse, location, identity["username"], db)
    db.add(WorkflowEvent(record_id=item.id, action="证物重新入库", from_status=previous, to_status="已重新入库", operator=identity["username"], comment=f"物品状况：{body.condition.strip()}。{body.comment.strip()}"))
    await db.commit()
    await db.refresh(item)
    return _record_dict(item, await _allowed_field_keys(identity, db))


@router.post(f"{settings.api_prefix}/warehouse/evidence/{{item_id}}/destroy")
async def destroy_warehouse_evidence(item_id: int, body: WarehouseEvidenceDestroyInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.investigation import (
        _warehouse_evidence_status,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    if identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以销毁证物")
    item = await _ensure_record_module(item_id, "warehouse", identity, db)
    previous = _warehouse_evidence_status(item)
    if previous not in {"已入库", "已重新入库"}:
        raise HTTPException(status_code=409, detail="只有在库证物可以办理销毁")
    item.status = "报废"
    item.data = {**(item.data or {}), "evidence_status": "已销毁", "destroyed_at": str(date.today()), "destroyed_by": identity["username"], "destroy_reason": body.reason.strip()}
    db.add(WorkflowEvent(record_id=item.id, action="证物销毁", from_status=previous, to_status="已销毁", operator=identity["username"], comment=body.reason.strip()))
    await db.commit()
    await db.refresh(item)
    return _record_dict(item, await _allowed_field_keys(identity, db))


@router.post(f"{settings.api_prefix}/warehouse/{{item_id}}/borrow")
async def borrow_warehouse_item(item_id: int, body: WarehouseBorrowInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _record_dict,
    )
    if identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以办理借出")
    item = await _ensure_record_module(item_id, "warehouse", identity, db)
    if (item.data or {}).get("evidence_status"): raise HTTPException(status_code=409, detail="证物必须使用证物出库入口办理")
    if item.status != "在库": raise HTTPException(status_code=409, detail="只有在库物品可以借出")
    if body.due_date < date.today(): raise HTTPException(status_code=422, detail="预计归还日期不能早于今天")
    data = dict(item.data or {}); data.update({"borrower": body.borrower.strip(), "due_date": str(body.due_date), "borrow_purpose": body.purpose.strip(), "borrowed_at": str(date.today()), "borrowed_by": identity["username"], "return_requested_at": ""})
    item.status = "借出"; item.data = data
    db.add(WorkflowEvent(record_id=item.id, action="物品借出", from_status="在库", to_status="借出", operator=identity["username"], comment=f"借用人：{body.borrower}；预计归还：{body.due_date}。{body.comment}"))
    await db.commit(); await db.refresh(item); return _record_dict(item)


@router.post(f"{settings.api_prefix}/warehouse/{{item_id}}/return")
async def return_warehouse_item(item_id: int, body: WarehouseReturnInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _record_dict,
    )
    item = await _ensure_record_module(item_id, "warehouse", identity, db)
    if (item.data or {}).get("evidence_status"): raise HTTPException(status_code=409, detail="证物必须使用证物重新入库入口办理")
    data = dict(item.data or {})
    if item.status != "借出": raise HTTPException(status_code=409, detail="只有已借出物品可以发起归还")
    if identity.get("role") not in {"admin", "manager"} and data.get("borrower") not in {identity["username"], identity.get("display_name", "")}: raise HTTPException(status_code=403, detail="只有借用人或管理人员可以发起归还")
    item.status = "归还中"; item.data = {**data, "return_requested_at": str(date.today()), "return_requested_by": identity["username"]}
    db.add(WorkflowEvent(record_id=item.id, action="发起归还", from_status="借出", to_status="归还中", operator=identity["username"], comment=body.comment))
    await db.commit(); await db.refresh(item); return _record_dict(item)


@router.post(f"{settings.api_prefix}/warehouse/{{item_id}}/return-confirm")
async def confirm_warehouse_return(item_id: int, body: WarehouseReturnConfirmInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _record_dict,
    )
    if identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以验收归还")
    item = await _ensure_record_module(item_id, "warehouse", identity, db)
    if (item.data or {}).get("evidence_status"): raise HTTPException(status_code=409, detail="证物必须使用证物重新入库入口办理")
    if item.status != "归还中": raise HTTPException(status_code=409, detail="只有归还中的物品可以验收入库")
    previous_data = dict(item.data or {}); last_borrower = str(previous_data.get("borrower") or "")
    data = {**previous_data, "last_borrower": last_borrower, "last_due_date": previous_data.get("due_date", ""), "returned_at": str(date.today()), "return_condition": body.condition.strip(), "returned_by": identity["username"], "borrower": "", "due_date": "", "borrow_purpose": "", "return_requested_at": ""}
    if body.location.strip(): data["location"] = body.location.strip()
    item.status = "在库"; item.data = data
    db.add(WorkflowEvent(record_id=item.id, action="归还验收入库", from_status="归还中", to_status="在库", operator=identity["username"], comment=f"原借用人：{last_borrower}；物品状况：{body.condition}。{body.comment}"))
    await db.commit(); await db.refresh(item); return _record_dict(item)


@router.post(f"{settings.api_prefix}/warehouse/{{item_id}}/scrap")
async def scrap_warehouse_item(item_id: int, body: WarehouseScrapInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _record_dict,
    )
    if identity.get("role") != "admin": raise HTTPException(status_code=403, detail="仅管理员可以报废物品")
    item = await _ensure_record_module(item_id, "warehouse", identity, db)
    if (item.data or {}).get("evidence_status"): raise HTTPException(status_code=409, detail="证物必须使用证物销毁入口办理")
    if item.status != "在库": raise HTTPException(status_code=409, detail="只有在库物品可以报废")
    item.status = "报废"; item.data = {**(item.data or {}), "scrapped_at": str(date.today()), "scrap_reason": body.reason.strip(), "scrapped_by": identity["username"]}
    db.add(WorkflowEvent(record_id=item.id, action="物品报废", from_status="在库", to_status="报废", operator=identity["username"], comment=body.reason))
    await db.commit(); await db.refresh(item); return _record_dict(item)


@router.post(f"{settings.api_prefix}/WMS/Warehouse/GoodsList")
async def warehouse_goods_list(body: WarehouseGoodsListInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Legacy server-side pagination contract used by the old WMS GoodsList page."""
    from app.core.investigation import (
        _warehouse_evidence_location_statement, _warehouse_goods_legacy_row,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    condition = body.SearchCondition
    page_no = condition.PageNo or 1
    page_size = condition.PageSize or 15
    filters = list(await _record_scope_conditions(identity, db))
    def like_filter(column: object, value: str):
        return column.ilike(f"%{value.strip()}%") if value.strip() else None
    serial_value = condition.SerialNo or condition.EvidenceNo
    filters.extend(filter(None, [
        like_filter(BusinessRecord.title, condition.Name),
        like_filter(BusinessRecord.data["clue_no"].as_string(), condition.ClueNo),
        like_filter(BusinessRecord.data["case_no"].as_string(), condition.CaseNo),
    ]))
    if serial_value.strip():
        term = f"%{serial_value.strip()}%"
        filters.append(or_(BusinessRecord.serial_no.ilike(term), BusinessRecord.data["legacy_evidence_no"].as_string().ilike(term)))
    if condition.WareHouseNo.strip():
        filters.append(Warehouse.warehouse_no == condition.WareHouseNo.strip())
    if condition.DepositAddress.strip():
        term = f"%{condition.DepositAddress.strip()}%"
        filters.append(or_(WarehouseStorageLocation.name.ilike(term), WarehouseStorageLocation.address.ilike(term)))
    statement = _warehouse_evidence_location_statement(filters)
    total = int(await db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = (await db.execute(statement.order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()).offset((page_no - 1) * page_size).limit(page_size))).all()
    return {"GoodsList": [_warehouse_goods_legacy_row(*row) for row in rows], "PageNo": page_no, "PageSize": page_size, "TotalItemCount": total}


@router.post(f"{settings.api_prefix}/WMS/WarehouseStorageLocation/GetStorageLocationGoodsCountList")
async def warehouse_storage_location_goods_count_list(
    _: WarehouseGoodsListInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Legacy WMS tree contract backed by structured warehouse master data."""
    from app.core.permissions import (
        _record_scope_conditions, _require_record_module_menu,
    )
    await _require_record_module_menu("warehouse", identity, db, action="查看")
    scope = list(await _record_scope_conditions(identity, db))
    count_rows = (await db.execute(
        select(
            WarehouseEvidenceLocation.storage_location_id,
            func.count(WarehouseEvidenceLocation.id),
        )
        .select_from(WarehouseEvidenceLocation)
        .join(BusinessRecord, BusinessRecord.id == WarehouseEvidenceLocation.record_id)
        .where(BusinessRecord.module == "warehouse", *scope)
        .group_by(WarehouseEvidenceLocation.storage_location_id)
    )).all()
    counts = dict(count_rows)
    warehouses = list((await db.scalars(select(Warehouse).order_by(Warehouse.sort_order, Warehouse.warehouse_no, Warehouse.id))).all())
    locations = list((await db.scalars(select(WarehouseStorageLocation).order_by(WarehouseStorageLocation.sort_order, WarehouseStorageLocation.storage_location_no, WarehouseStorageLocation.id))).all())
    by_warehouse: dict[int, list[WarehouseStorageLocation]] = {}
    for location in locations:
        by_warehouse.setdefault(location.warehouse_id, []).append(location)
    payload = []
    for warehouse in warehouses:
        locations_payload = [{
            "StorageLocationId": location.id,
            "StorageLocationNo": location.storage_location_no,
            "StorageLocationName": location.name,
            "GoodsCounts": int(counts.get(location.id, 0)),
            "IsActived": "T" if location.is_active else "F",
        } for location in by_warehouse.get(warehouse.id, [])]
        payload.append({
            "WarehouseId": warehouse.id,
            "WarehouseNo": warehouse.warehouse_no,
            "WarehouseName": warehouse.name,
            "GoodsCounts": sum(int(location["GoodsCounts"]) for location in locations_payload),
            "Locations": locations_payload,
            "IsActived": "T" if warehouse.is_active else "F",
        })
    return {"WarehouseLocationGoods": payload}
