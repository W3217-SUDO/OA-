"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.constants import (
    UPLOAD_ROOT,
)
from app.core.dependencies import (
    AsyncSession, BusinessRecord, FileAttachment, HTTPException, InvestigationClueLink,
    InvestigationEvidence, InvestigationEvidenceFile, InvestigationTaskLink, Path, SystemConfig,
    UploadFile, User, Warehouse, WarehouseEvidenceLocation, WarehouseStorageLocation,
    WorkflowEvent, and_, date, datetime, func,
    or_, re, select, timezone, uuid4,
)
from app.models_shared import (
    ClueCollectionInput, EvidenceRegistrationItem, NotaryCertificateInput, WarehouseEvidenceCheckInInput, WarehouseEvidenceInput,
    WarehouseEvidenceRecheckInInput,
)


def _investigation_authorization_expired(record: BusinessRecord, *, today: date | None = None) -> bool:
    """Return whether an investigation's authorization ended before today."""
    from app.core.formatters import (
        _investigation_task_date,
    )
    data = record.data or {}
    authorized_to = _investigation_task_date(data.get("authorized_to") or data.get("end_date"))
    return bool(authorized_to and authorized_to < (today or date.today()))


async def _resolve_investigation_task_root(source: BusinessRecord, identity: dict, db: AsyncSession) -> BusinessRecord:
    from app.core.permissions import (
        _record_scope_conditions,
    )
    if source.module == "investigation":
        return source
    candidate_ids: list[int] = []
    source_data = source.data or {}
    for key in ("investigation_record_id", "investigation_id"):
        try:
            candidate_id = int(source_data.get(key) or 0)
        except (TypeError, ValueError):
            candidate_id = 0
        if candidate_id > 0:
            candidate_ids.append(candidate_id)
    try:
        task_id = int(source_data.get("source_task_id") or 0)
    except (TypeError, ValueError):
        task_id = 0
    visited: set[int] = set()
    while task_id and task_id not in visited:
        visited.add(task_id)
        task = await db.get(BusinessRecord, task_id)
        if not task or task.module not in {"task", "investigation"}:
            break
        if task.module == "investigation":
            candidate_ids.insert(0, task.id)
            break
        task_data = task.data or {}
        for key in ("investigation_record_id", "investigation_id"):
            try:
                candidate_id = int(task_data.get(key) or 0)
            except (TypeError, ValueError):
                candidate_id = 0
            if candidate_id > 0:
                candidate_ids.append(candidate_id)
        try:
            task_id = int(task_data.get("parent_task_id") or 0)
        except (TypeError, ValueError):
            task_id = 0
    scope = await _record_scope_conditions(identity, db)
    for candidate_id in candidate_ids:
        root = await db.scalar(select(BusinessRecord).where(BusinessRecord.id == candidate_id, BusinessRecord.module == "investigation", *scope))
        if root:
            return root
    return source


async def _configured_investigation_supervisor(db: AsyncSession) -> User:
    config = await db.scalar(select(SystemConfig).where(SystemConfig.key == "investigation_assignment"))
    configured_username = str((config.value or {}).get("supervisor_username") or "").strip() if config else ""
    if not configured_username:
        raise HTTPException(status_code=409, detail="请先由管理员在系统配置中设置调查任务分配人")
    supervisor = await db.scalar(select(User).where(User.username == configured_username, User.is_active.is_(True)))
    if not supervisor:
        raise HTTPException(status_code=409, detail="已配置的调查任务分配人不存在或已停用，请重新设置")
    return supervisor


async def _sync_investigation_materials(record: BusinessRecord, db: AsyncSession) -> list[str]:
    categories = sorted(set((await db.scalars(select(FileAttachment.category).where(FileAttachment.record_id == record.id))).all()))
    record.data = {**(record.data or {}), "material_categories": categories, "material_count": int(await db.scalar(select(func.count()).select_from(FileAttachment).where(FileAttachment.record_id == record.id)) or 0)}
    return categories


async def _next_investigation_clue_serial(
    db: AsyncSession,
    created_at: datetime | None = None,
    prefix: str = "M",
) -> str:
    """Generate the legacy nine-character clue number: M/P + YYMM + sequence."""
    period = (created_at or datetime.now()).strftime("%y%m")
    normalized_prefix = prefix.upper() if prefix.upper() in {"M", "P"} else "M"
    pattern = re.compile(rf"^[MP]{period}(\d{{4}})$")
    serials = (
        await db.scalars(
            select(BusinessRecord.serial_no).where(
                BusinessRecord.module == "clue",
                BusinessRecord.serial_no.like(f"_{period}____"),
            )
        )
    ).all()
    sequence = max(
        (int(match.group(1)) for value in serials if (match := pattern.fullmatch(str(value or "")))),
        default=0,
    ) + 1
    if sequence > 9999:
        raise HTTPException(status_code=409, detail="本月调查线索编号已用尽")
    return f"{normalized_prefix}{period}{sequence:04d}"


async def _import_notary_named_file(file: UploadFile, match_field: str, reference_no: str, category: str, identity: dict, db: AsyncSession):
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    filename = Path(file.filename or "").name
    if Path(filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=422, detail="仅支持 PDF 文件")
    lookup = reference_no.strip().casefold()
    if not lookup:
        label = "公证书号" if match_field == "certificate_no" else "发票号"
        raise HTTPException(status_code=422, detail=f"请填写{label}")
    records = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "notary", *(await _record_scope_conditions(identity, db))))).all()
    matches = [item for item in records if str((item.data or {}).get(match_field, "")).strip().casefold() == lookup]
    if not matches:
        label = "公证书号" if match_field == "certificate_no" else "发票号"
        raise HTTPException(status_code=422, detail=f"{label} {reference_no.strip()} 未匹配到任何公证记录")
    if len(matches) > 1:
        raise HTTPException(status_code=409, detail=f"{label}匹配到多条公证记录，请先清理重复编号")
    record = matches[0]
    duplicate = await db.scalar(select(FileAttachment).where(FileAttachment.record_id == record.id, FileAttachment.category == category, FileAttachment.original_name == filename))
    if duplicate:
        raise HTTPException(status_code=409, detail="该文件已经导入，请勿重复上传")
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="单个文件不能超过 20MB")
    stored_name = f"{uuid4().hex}.pdf"; target = UPLOAD_ROOT / stored_name; target.write_bytes(content)
    item = FileAttachment(record_id=record.id, category=category, original_name=filename, stored_name=stored_name, content_type=file.content_type or "application/pdf", size=len(content), path=str(target), uploader=identity["username"], remark=f"按{match_field}显式编号匹配导入")
    db.add(item); db.add(WorkflowEvent(record_id=record.id, action=f"导入{category}", from_status=record.status, to_status=record.status, operator=identity["username"], comment=filename))
    await db.commit(); await db.refresh(item)
    return {"created": 1, "failed": 0, "errors": [], "record_id": record.id, "record_no": record.serial_no, "attachment": _attachment_dict(item, record)}


def _validate_clue_submission(clue: BusinessRecord) -> None:
    if clue.status not in {"草稿", "已驳回"}:
        raise HTTPException(status_code=409, detail=f"线索 {clue.serial_no} 不是草稿或已驳回状态")
    data = clue.data or {}
    missing = [name for name, value in {
        "客户": clue.customer, "调查平台": data.get("platform"), "侵权产品": data.get("product"),
    }.items() if not value]
    if missing:
        raise HTTPException(status_code=422, detail=f"线索 {clue.serial_no} 缺少：" + "、".join(missing))


def _apply_clue_submission(clue: BusinessRecord, identity: dict, comment: str, db: AsyncSession) -> None:
    previous = clue.status
    clue.status = "待审批"
    clue.data = {
        **(clue.data or {}), "submitted_at": datetime.now().isoformat(timespec="seconds"),
        "submitted_by": identity["username"], "review_comment": "",
    }
    db.add(WorkflowEvent(
        record_id=clue.id, action="提交线索审批", from_status=previous,
        to_status=clue.status, operator=identity["username"], comment=comment,
    ))


async def _register_clue_collection(clue_id: int, body: ClueCollectionInput, identity: dict, db: AsyncSession) -> BusinessRecord:
    from app.core.formatters import (
        _warehouse_location_display,
    )
    from app.core.legacy_sync import (
        _sync_legacy_investigation_clue_evidence, _sync_legacy_projection,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    clue = await _ensure_record_module(clue_id, "clue", identity, db); await _require_record_owner_or_manager(clue, identity, db)
    if clue.status != "待取证": raise HTTPException(status_code=409, detail="只有审批通过的待取证线索可以登记取证")
    if body.collected_at > date.today(): raise HTTPException(status_code=422, detail="取证日期不能晚于今天")
    evidence_file_ids = list(dict.fromkeys(body.evidence_file_ids))
    if evidence_file_ids:
        files = {item.id: item for item in (await db.scalars(select(FileAttachment).where(FileAttachment.id.in_(evidence_file_ids)))).all()}
        for file_id in evidence_file_ids:
            item = files.get(file_id)
            if not item or item.record_id != clue.id:
                raise HTTPException(status_code=422, detail=f"取证文件 {file_id} 不属于当前线索")
    if not body.storage_location_id:
        raise HTTPException(status_code=422, detail="请选择仓库库位")
    warehouse, location = await _resolve_warehouse_location(body, db)
    storage_location = _warehouse_location_display(warehouse, location)
    evidence_status = body.evidence_status.strip() or "未入库"
    if evidence_status not in {"未入库", "已入库", "已出库", "已重新入库", "已销毁"}:
        raise HTTPException(status_code=422, detail="证物状态无效")
    clue.status = "已取证"; clue.data = {
        **(clue.data or {}), "collected_at": str(body.collected_at),
        "notary_institution": body.notary_institution.strip(),
        "notarization_no": body.notarization_no.strip(), "certificate_no": body.notarization_no.strip(),
        "invoice_no": body.invoice_no.strip(), "storage_location": storage_location,
        **_warehouse_location_data(warehouse, location),
        "evidence_status": evidence_status, "collection_file_ids": evidence_file_ids,
        "collected_by": identity["username"], "collection_registered_at": datetime.now().isoformat(timespec="seconds"),
    }
    collection_evidence = await _create_collection_evidence_record(clue, identity, db)
    await _set_warehouse_evidence_location(
        collection_evidence.id, warehouse, location, identity["username"], db
    )
    clue.data = {**(clue.data or {}), "collection_evidence_record_id": collection_evidence.id}
    db.add(WorkflowEvent(record_id=clue.id, action="登记线索取证", from_status="待取证", to_status="已取证", operator=identity["username"], comment=f"取证日期 {body.collected_at}；取证机构 {body.notary_institution.strip()}；公证书号 {body.notarization_no.strip() or '未登记'}；发票号码 {body.invoice_no.strip() or '未登记'}；证物状态 {evidence_status}；取证文件 {len(evidence_file_ids)} 个。{body.comment}"))
    await _sync_legacy_projection(clue, identity, db)
    await _sync_legacy_investigation_clue_evidence(clue, identity, db, evidence_file_ids)
    return clue


async def _build_evidence_record(item: EvidenceRegistrationItem, identity: dict, db: AsyncSession) -> BusinessRecord:
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _import_relation_data,
    )
    clue = None
    if item.clue_id:
        clue = await _ensure_record_module(item.clue_id, "clue", identity, db)
    evidence_file_ids = list(dict.fromkeys(item.evidence_file_ids))
    if evidence_file_ids:
        files = {attachment.id: attachment for attachment in (await db.scalars(select(FileAttachment).where(FileAttachment.id.in_(evidence_file_ids)))).all()}
        for file_id in evidence_file_ids:
            attachment = files.get(file_id)
            if not attachment:
                raise HTTPException(status_code=404, detail=f"证据文件 {file_id} 不存在")
            if clue and attachment.record_id != clue.id:
                raise HTTPException(status_code=422, detail=f"证据文件 {file_id} 不属于关联线索")
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    owner = item.owner.strip() or identity["username"]
    if identity.get("role") == "user":
        owner = identity["username"]
    serial_no = f"ZJ{datetime.now():%Y%m%d%H%M%S%f}{uuid4().hex[:4].upper()}"
    record = BusinessRecord(
        module="evidence", serial_no=serial_no, title=item.title.strip(),
        customer=clue.customer if clue else "", status="待整理", owner=owner,
        department=user.department if user else (clue.department if clue else "上海分所"),
        description=item.description,
        data={
            **(_import_relation_data(clue=clue) if clue else {}),
            "source": item.source, "clue_id": clue.id if clue else None,
            "clue_no": clue.serial_no if clue else "",
            "notarization_no": item.notarization_no.strip(),
            "invoice_no": item.invoice_no.strip(),
            "storage_location": item.storage_location.strip(),
            "storage_state": item.storage_state.strip() or "待整理",
            "evidence_file_ids": evidence_file_ids,
        },
    )
    db.add(record); await db.flush()
    await _sync_investigation_relation_links(record, db)
    db.add(WorkflowEvent(record_id=record.id, action="登记证据", to_status="待整理", operator=identity["username"], comment=f"来源线索 {clue.serial_no}" if clue else "独立登记"))
    if clue:
        evidence_ids = list((clue.data or {}).get("evidence_ids", [])); evidence_ids.append(record.id)
        clue.data = {**(clue.data or {}), "evidence_ids": list(dict.fromkeys(evidence_ids)), "evidence_count": len(set(evidence_ids))}
        db.add(WorkflowEvent(record_id=clue.id, action="建立证据目录", from_status=clue.status, to_status=clue.status, operator=identity["username"], comment=f"生成 {serial_no}"))
    return record


async def _apply_notary_auto_conversion(db: AsyncSession) -> bool:
    """公证审核超过 30 日仍未处理时，自动进入“新案待分配”。"""
    from app.core.formatters import (
        _convert_notary_to_case,
    )
    notaries = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "notary", BusinessRecord.status == "待审核",
    ))).all()
    changed = False
    for notary in notaries:
        raw_due = (notary.data or {}).get("review_due_date")
        try:
            overdue = bool(raw_due) and date.fromisoformat(str(raw_due)) < date.today()
        except ValueError:
            overdue = False
        if not overdue:
            continue
        clue_id = int((notary.data or {}).get("clue_id", 0))
        clue = await db.get(BusinessRecord, clue_id)
        if not clue:
            continue
        await _convert_notary_to_case(
            notary, clue, db, operator="system", automatic=True,
            comment="公证书审核已超过 30 日，系统自动将案件进入“新案待分配”",
        )
        changed = True
    if changed:
        await db.commit()
    return changed


def _is_investigation_task(task: BusinessRecord) -> bool:
    """Keep investigation child tasks out of the general task centre.

    Investigation child tasks share the ``task`` module with ordinary and case
    tasks.  Legacy rows do not consistently carry a case number, so case linkage
    must never be used as a proxy for task-centre eligibility.  The investigation
    relation/source fields are the stable discriminator across old and new rows.
    """
    data = task.data or {}
    source = str(data.get("source") or "").strip()
    business_type = str(data.get("task_business_type") or data.get("business_type") or "").strip()
    return bool(
        data.get("investigation_record_id")
        or str(data.get("investigation_no") or "").strip()
        or str(data.get("investigation_module") or "").strip() == "investigation"
        or source in {"调查任务", "调查子任务"}
        or business_type in {"调查任务", "调查子任务"}
    )


def _warehouse_evidence_status(item: BusinessRecord) -> str:
    data = item.data or {}
    explicit = str(data.get("evidence_status") or "").strip()
    if explicit:
        return explicit
    return {"在库": "已入库", "借出": "已出库", "归还中": "已出库", "报废": "已销毁"}.get(item.status, "未入库")


async def _resolve_warehouse_location(
    body: WarehouseEvidenceInput | WarehouseEvidenceCheckInInput | WarehouseEvidenceRecheckInInput | ClueCollectionInput | NotaryCertificateInput,
    db: AsyncSession,
) -> tuple[Warehouse, WarehouseStorageLocation]:
    """Resolve one active location from catalog master data, never free text."""
    location: WarehouseStorageLocation | None = None
    if body.storage_location_id:
        location = await db.get(WarehouseStorageLocation, body.storage_location_id)
    else:
        warehouse_name = body.warehouse.strip()
        location_name = body.location.strip()
        if warehouse_name and location_name:
            location = await db.scalar(
                select(WarehouseStorageLocation)
                .join(Warehouse, Warehouse.id == WarehouseStorageLocation.warehouse_id)
                .where(Warehouse.name == warehouse_name, WarehouseStorageLocation.name == location_name)
                .order_by(WarehouseStorageLocation.id)
            )
    if not location:
        raise HTTPException(status_code=422, detail="请从仓库库位主数据选择有效库位")
    warehouse = await db.get(Warehouse, location.warehouse_id)
    if not warehouse or not warehouse.is_active or not location.is_active:
        raise HTTPException(status_code=422, detail="所选仓库或库位已停用")
    if body.warehouse_id and body.warehouse_id != warehouse.id:
        raise HTTPException(status_code=422, detail="仓库与库位不属于同一层级")
    return warehouse, location


def _warehouse_location_data(warehouse: Warehouse, location: WarehouseStorageLocation) -> dict[str, object]:
    return {
        "warehouse_id": warehouse.id,
        "warehouse_no": warehouse.warehouse_no,
        "warehouse": warehouse.name,
        "storage_location_id": location.id,
        "storage_location_no": location.storage_location_no,
        "location": location.name,
    }


async def _set_warehouse_evidence_location(
    record_id: int,
    warehouse: Warehouse,
    location: WarehouseStorageLocation,
    username: str,
    db: AsyncSession,
) -> WarehouseEvidenceLocation:
    binding = await db.scalar(select(WarehouseEvidenceLocation).where(WarehouseEvidenceLocation.record_id == record_id))
    if not binding:
        binding = WarehouseEvidenceLocation(
            record_id=record_id,
            warehouse_id=warehouse.id,
            storage_location_id=location.id,
            assigned_by=username,
        )
        db.add(binding)
        return binding
    binding.warehouse_id = warehouse.id
    binding.storage_location_id = location.id
    binding.assigned_by = username
    binding.assigned_at = datetime.now(timezone.utc)
    return binding


async def _sync_case_notary_warehouse_evidence(
    case_record: BusinessRecord,
    locations: list[tuple[Warehouse, WarehouseStorageLocation]],
    notary_nos: str,
    username: str,
    db: AsyncSession,
) -> None:
    """Keep the case's physical notary evidence visible in the warehouse tree.

    Case details store the human-readable location summary, while warehouse
    counts and filtered rows are driven by ``warehouse_evidence_locations``.
    The two records therefore have to be updated in one transaction.
    """
    related = list((await db.scalars(
        select(BusinessRecord)
        .where(
            BusinessRecord.module == "warehouse",
            or_(
                BusinessRecord.data["case_record_id"].as_integer() == case_record.id,
                BusinessRecord.data["case_id"].as_integer() == case_record.id,
                BusinessRecord.data["case_no"].as_string() == case_record.serial_no,
            ),
        )
        .order_by(BusinessRecord.id)
    )).all())
    case_data = dict(case_record.data or {})
    for index, (warehouse, location) in enumerate(locations):
        if index < len(related):
            evidence = related[index]
        else:
            evidence = BusinessRecord(
                module="warehouse",
                serial_no=f"CKZ-{case_record.id}-{index + 1}",
                title=f"{case_record.title}—公证证物",
                customer=case_record.customer,
                status="在库",
                owner=str(case_data.get("investigator") or case_record.owner or username),
                department=case_record.department,
                description="由案件公证信息维护的实体证物",
            )
            db.add(evidence)
            await db.flush()
            related.append(evidence)
        evidence_data = dict(evidence.data or {})
        evidence.title = case_record.title or evidence.title
        evidence.customer = case_record.customer
        evidence.owner = str(case_data.get("investigator") or evidence.owner or case_record.owner or username)
        evidence.department = case_record.department
        evidence.status = "在库"
        evidence.data = {
            **evidence_data,
            "source": "案件公证信息",
            "case_record_id": case_record.id,
            "case_id": case_record.id,
            "case_no": case_record.serial_no,
            "notary_no": notary_nos,
            "shop_name": case_record.title,
            "rights_holder": case_record.customer,
            "investigator": str(case_data.get("investigator") or case_record.owner or username),
            "evidence_status": "已入库",
            "case_notary_evidence": True,
            **_warehouse_location_data(warehouse, location),
        }
        await _set_warehouse_evidence_location(evidence.id, warehouse, location, username, db)

    # A case can have more pre-existing warehouse rows than selected locations.
    # Move every related physical record into the currently selected locations so
    # the former location never keeps an obsolete count after a successful edit.
    for index, evidence in enumerate(related[len(locations):], start=len(locations)):
        warehouse, location = locations[index % len(locations)]
        evidence.data = {
            **dict(evidence.data or {}),
            "source": "案件公证信息",
            "case_record_id": case_record.id,
            "case_id": case_record.id,
            "case_no": case_record.serial_no,
            "notary_no": notary_nos,
            "evidence_status": "已入库",
            "case_notary_evidence": True,
            **_warehouse_location_data(warehouse, location),
        }
        await _set_warehouse_evidence_location(evidence.id, warehouse, location, username, db)


def _warehouse_evidence_location_statement(identity_conditions: list):
    return (
        select(BusinessRecord, WarehouseEvidenceLocation, Warehouse, WarehouseStorageLocation)
        .select_from(BusinessRecord)
        .outerjoin(WarehouseEvidenceLocation, WarehouseEvidenceLocation.record_id == BusinessRecord.id)
        .outerjoin(Warehouse, Warehouse.id == WarehouseEvidenceLocation.warehouse_id)
        .outerjoin(WarehouseStorageLocation, WarehouseStorageLocation.id == WarehouseEvidenceLocation.storage_location_id)
        # Evidence created by the investigation collection flow keeps its
        # canonical ``evidence`` module, but a warehouse binding makes it a
        # warehouse-visible record.  Restricting this query to ``warehouse``
        # hid those bound evidence records from the warehouse overview.
        .where(
            or_(
                BusinessRecord.module == "warehouse",
                and_(
                    BusinessRecord.module == "evidence",
                    WarehouseEvidenceLocation.id.is_not(None),
                ),
            ),
            *identity_conditions,
        )
    )


def _warehouse_evidence_dict(
    item: BusinessRecord,
    binding: WarehouseEvidenceLocation | None,
    warehouse: Warehouse | None,
    location: WarehouseStorageLocation | None,
) -> dict[str, object]:
    data = dict(item.data or {})
    canonical_notary_no = str(
        data.get("notary_no")
        or data.get("notary_nos")
        or data.get("certificate_no")
        or data.get("notarization_no")
        or ""
    ).strip()
    if canonical_notary_no:
        data["notary_no"] = canonical_notary_no
    if warehouse and location:
        data.update(_warehouse_location_data(warehouse, location))
    return {
        "id": item.id,
        "serial_no": item.serial_no,
        "title": item.title,
        "customer": item.customer,
        "status": item.status,
        "owner": item.owner,
        "department": item.department,
        "description": item.description,
        "data": data,
        "warehouse_binding_id": binding.id if binding else None,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _warehouse_goods_legacy_row(
    item: BusinessRecord,
    binding: WarehouseEvidenceLocation | None = None,
    warehouse: Warehouse | None = None,
    location: WarehouseStorageLocation | None = None,
) -> dict:
    data = dict(item.data or {})
    if warehouse and location:
        data.update(_warehouse_location_data(warehouse, location))
    return {
        "EvidenceNo": data.get("legacy_evidence_no") or item.serial_no,
        "StorageLocation": data.get("location", ""),
        "ClueNo": data.get("clue_no", ""),
        "NotarialNo": data.get("notary_no", ""),
        "CaseNo": data.get("case_no", ""),
        "StoreName": data.get("shop_name", item.title),
        "InvestigatorName": data.get("investigator", item.owner),
        "NotaryOrganization": data.get("notary_office", ""),
        "IndicterName": data.get("rights_holder", item.customer),
        "NotarialObtainDate": str(data.get("evidence_date") or ""),
        "GoodsStatusName": _warehouse_evidence_status(item),
        "id": item.id, "serial_no": item.serial_no, "title": item.title,
        "status": item.status, "warehouse": data.get("warehouse", ""),
        "warehouse_no": data.get("warehouse_no", ""), "location": data.get("location", ""),
        "storage_location_no": data.get("storage_location_no", ""), "notary_no": data.get("notary_no", ""),
        "case_no": data.get("case_no", ""), "investigator": data.get("investigator", item.owner),
        "notary_office": data.get("notary_office", ""), "evidence_date": data.get("evidence_date", ""),
    }


async def _sync_investigation_relation_links(record: BusinessRecord, db: AsyncSession) -> None:
    """Persist current investigation links outside the JSON compatibility projection.

    New workflows still expose the shared ``BusinessRecord`` contract, but the
    investigation tree itself is now stored with foreign keys.  Historical
    imports use the same tables and add a missing-parent reference only when
    the old source truly has no parent row.
    """
    from app.core.legacy_sync import (
        _legacy_case_datetime,
    )

    data = record.data or {}
    if record.module == "task":
        try:
            investigation_id = int(data.get("investigation_record_id") or data.get("investigation_id") or 0)
        except (TypeError, ValueError):
            investigation_id = 0
        investigation = await db.get(BusinessRecord, investigation_id) if investigation_id else None
        if not investigation or investigation.module != "investigation":
            return
        link = await db.scalar(select(InvestigationTaskLink).where(InvestigationTaskLink.task_record_id == record.id))
        if not link:
            link = InvestigationTaskLink(task_record_id=record.id)
            db.add(link)
        link.investigation_record_id = investigation.id
        link.missing_investigation_reference_id = None
        link.legacy_task_no = record.serial_no
        return

    if record.module == "clue":
        try:
            task_id = int(data.get("source_task_record_id") or data.get("source_task_id") or 0)
        except (TypeError, ValueError):
            task_id = 0
        try:
            investigation_id = int(data.get("investigation_record_id") or data.get("investigation_id") or 0)
        except (TypeError, ValueError):
            investigation_id = 0
        task = await db.get(BusinessRecord, task_id) if task_id else None
        if (not investigation_id) and task:
            try:
                investigation_id = int((task.data or {}).get("investigation_record_id") or 0)
            except (TypeError, ValueError):
                investigation_id = 0
        investigation = await db.get(BusinessRecord, investigation_id) if investigation_id else None
        if not task or task.module != "task" or not investigation or investigation.module != "investigation":
            return
        link = await db.scalar(select(InvestigationClueLink).where(InvestigationClueLink.clue_record_id == record.id))
        if not link:
            link = InvestigationClueLink(clue_record_id=record.id)
            db.add(link)
        link.task_record_id = task.id
        link.missing_task_reference_id = None
        link.investigation_record_id = investigation.id
        link.missing_investigation_reference_id = None
        link.legacy_clue_no = record.serial_no
        return

    if record.module == "evidence":
        try:
            clue_id = int(data.get("clue_record_id") or data.get("clue_id") or 0)
        except (TypeError, ValueError):
            clue_id = 0
        clue = await db.get(BusinessRecord, clue_id) if clue_id else None
        if not clue or clue.module != "clue":
            return
        evidence = await db.scalar(select(InvestigationEvidence).where(InvestigationEvidence.record_id == record.id))
        if not evidence:
            # The canonical table requires a real clue reference. Set it on
            # construction so the first flush cannot create a parentless row.
            evidence = InvestigationEvidence(record_id=record.id, clue_record_id=clue.id)
            db.add(evidence)
        evidence.clue_record_id = clue.id
        evidence.missing_clue_reference_id = None
        evidence.legacy_evidence_no = str(data.get("legacy_evidence_no") or record.serial_no)[:200]
        evidence.evidence_type = str(data.get("evidence_type") or "调查取证")[:32]
        evidence.evidence_date = _legacy_case_datetime(data.get("evidence_date") or data.get("collected_at"))
        evidence.status = record.status
        evidence.source_snapshot = {"source": data.get("source") or "调查取证", "clue_no": clue.serial_no}
        await db.flush()
        for attachment_id in dict.fromkeys(data.get("evidence_file_ids") or []):
            if not isinstance(attachment_id, int):
                continue
            attachment = await db.get(FileAttachment, attachment_id)
            if not attachment or attachment.record_id != clue.id:
                continue
            evidence_file = await db.scalar(select(InvestigationEvidenceFile).where(InvestigationEvidenceFile.attachment_id == attachment.id))
            if not evidence_file:
                evidence_file = InvestigationEvidenceFile(evidence_id=evidence.id, attachment_id=attachment.id)
                db.add(evidence_file)
            evidence_file.evidence_id = evidence.id
            evidence_file.file_name = attachment.original_name
            evidence_file.media_type = attachment.content_type
            evidence_file.source_path = attachment.path
            evidence_file.file_size = attachment.size
            evidence_file.source_available = bool(attachment.path)


async def _create_collection_evidence_record(
    clue: BusinessRecord,
    identity: dict,
    db: AsyncSession,
) -> BusinessRecord:
    """Create the canonical evidence record for a completed clue collection."""

    clue_data = clue.data or {}
    try:
        existing_id = int(clue_data.get("collection_evidence_record_id") or 0)
    except (TypeError, ValueError):
        existing_id = 0
    existing = await db.get(BusinessRecord, existing_id) if existing_id else None
    if existing and existing.module == "evidence":
        return existing
    serial_no = f"ZJ-{clue.serial_no}"
    duplicate = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == serial_no))
    if duplicate and duplicate.module == "evidence":
        return duplicate
    item = BusinessRecord(
        module="evidence",
        serial_no=serial_no,
        title=f"{clue.title}—取证材料",
        customer=clue.customer,
        status="已取证",
        owner=clue.owner,
        department=clue.department,
        description=clue.description,
        data={
            "source": "线索取证登记",
            "clue_id": clue.id,
            "clue_record_id": clue.id,
            "clue_no": clue.serial_no,
            "evidence_type": "调查取证",
            "collected_at": clue_data.get("collected_at") or "",
            "notary_institution": clue_data.get("notary_institution") or "",
            "notarization_no": clue_data.get("notarization_no") or "",
            "invoice_no": clue_data.get("invoice_no") or "",
            "storage_location": clue_data.get("storage_location") or "",
            "storage_state": clue_data.get("evidence_status") or "未入库",
            "evidence_file_ids": list(dict.fromkeys(clue_data.get("collection_file_ids") or [])),
        },
    )
    db.add(item)
    await db.flush()
    await _sync_investigation_relation_links(item, db)
    db.add(WorkflowEvent(
        record_id=item.id,
        action="登记线索取证证据",
        to_status="已取证",
        operator=identity["username"],
        comment=f"来源线索 {clue.serial_no}",
    ))
    return item
