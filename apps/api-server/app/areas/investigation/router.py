"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.constants import (
    INVESTIGATION_CREATE_STATUS_BY_MODULE, INVESTIGATION_EDIT_DATA_FIELDS, INVESTIGATION_MATERIAL_CATEGORIES, INVESTIGATION_RECORD_MODULES, UPLOAD_ROOT,
)
from app.core.dependencies import (
    AsyncSession, BusinessRecord, Depends, File, FileAttachment,
    Form, HTTPException, InvestigationClueLink, InvestigationEvidence, Path,
    Query, Response, SystemConfig, UploadFile, User,
    WorkflowEvent, csv, current_identity, date, datetime,
    delete, get_db, io, select, settings,
    status, timedelta, uuid4,
)
from app.models_shared import (
    BatchClueCaseInput, ClueBatchCollectionInput, ClueBatchSubmitInput, ClueCaseContractResolveInput, ClueCollectionInput,
    ClueReviewInput, ClueSourceContractBindingInput, ClueTurnOnAuditInput, EvidenceCreateInput, EvidenceUpdateInput,
    InvestigationAssignmentInput, InvestigationBatchDeleteInput, InvestigationFeeInput, InvestigationPartyInput, InvestigationTaskInput,
    RecordInput, RecordUpdate, TaskActionInput,
)
from fastapi import APIRouter
import json

_AUTHORIZATION_CITIES = {item["province"]: item["cities"] for item in json.loads(
    (Path(__file__).parents[2] / "core" / "investigation_regions.json").read_text(encoding="utf-8")
)}

router = APIRouter()


@router.get(f"{settings.api_prefix}/investigations/assignment-supervisor")
async def investigation_assignment_supervisor(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.investigation import (
        _configured_investigation_supervisor,
    )
    supervisor = await _configured_investigation_supervisor(db)
    return {"username": supervisor.username, "display_name": supervisor.display_name, "department": supervisor.department}


@router.get(f"{settings.api_prefix}/investigations/clues/export")
async def export_investigation_clues(ids: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _scoped_export_records,
    )
    from app.core.system import (
        _csv_response,
    )
    records = await _scoped_export_records("clue", ids, identity, db)
    rows = []
    for item in records:
        data = item.data or {}
        rows.append([item.serial_no, item.title, item.customer, item.status, item.owner, data.get("platform", ""), data.get("product", ""), data.get("region") or data.get("address", ""), data.get("collected_at", ""), data.get("notary_institution", ""), data.get("converted_case_no", ""), item.description])
    return _csv_response(f"调查线索-{date.today()}.csv", ["线索编号", "店铺/事项", "权利人", "状态", "调查员", "调查平台", "侵权产品", "调查区域/地址", "取证日期", "公证机构", "关联案号", "说明"], rows)


@router.get(f"{settings.api_prefix}/investigations/clues/handover-export")
async def export_investigation_handover(ids: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _scoped_export_records,
    )
    from app.core.system import (
        _csv_response,
    )
    records = await _scoped_export_records("clue", ids, identity, db)
    rows = []
    for item in records:
        data = item.data or {}
        rows.append([item.serial_no, data.get("converted_case_no", ""), item.customer, item.title, data.get("product", ""), item.owner, data.get("collected_at", ""), data.get("certificate_no", ""), data.get("warehouse", ""), data.get("handoff_recipient", ""), item.status, item.description])
    return _csv_response(f"调查线索交接清单-{date.today()}.csv", ["线索编号", "案件编号", "权利人", "店铺/事项", "侵权产品", "调查员", "取证日期", "公证书号", "仓库位置", "交接接收人", "当前状态", "交接说明"], rows)


@router.get(f"{settings.api_prefix}/investigations/action-capabilities")
async def investigation_action_capabilities(
    record_ids: str = Query(default="", max_length=1200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """Return the current user's real investigation actions for visible records.

    The investigation workbench must not infer approval authority from a display
    role.  In particular, clue review is a job-role permission, customer review
    belongs to the relevant customer manager, and certificate registration also
    requires authority over the notary record itself.
    """
    from app.core.permissions import (
        _record_scope_conditions, _user_has_job_permission,
    )
    try:
        requested_ids = list(dict.fromkeys(int(value) for value in record_ids.split(",") if value.strip()))
    except ValueError:
        raise HTTPException(status_code=422, detail="记录编号格式无效")
    if not requested_ids:
        return {"items": {}}
    if len(requested_ids) > 100:
        raise HTTPException(status_code=422, detail="一次最多查询 100 条调查记录的操作权限")
    records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(requested_ids),
        BusinessRecord.module.in_({"clue", "notary"}),
        *(await _record_scope_conditions(identity, db)),
    ))).all())
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    can_review_clue = bool(user and await _user_has_job_permission(user, "线索审批", db))
    can_review_notary = bool(user and await _user_has_job_permission(user, "公证审核", db))
    can_register_certificate = bool(user and await _user_has_job_permission(user, "公证书号码登记", db))
    customer_names = {record.customer.strip() for record in records if record.module == "clue" and record.customer.strip()}
    customer_managers: dict[str, set[str]] = {}
    if customer_names:
        customers = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "customer", BusinessRecord.title.in_(customer_names),
        ))).all())
        customer_managers = {
            customer.title.strip(): set((customer.data or {}).get("customer_managers") or [customer.owner])
            for customer in customers
        }
    items: dict[str, dict[str, bool]] = {}
    for record in records:
        can_manage_record = (
            identity.get("role") == "admin"
            or record.owner == identity["username"]
            or (identity.get("role") == "manager" and user and record.department == user.department)
        )
        items[str(record.id)] = {
            "review_clue": record.module == "clue" and can_review_clue,
            "review_customer_clue": record.module == "clue" and (
                identity.get("role") == "admin"
                or identity["username"] in customer_managers.get(record.customer.strip(), set())
            ),
            "review_notary": record.module == "notary" and can_review_notary,
            "register_notary_certificate": record.module == "notary" and can_register_certificate and can_manage_record,
        }
    return {"items": items}


@router.get(f"{settings.api_prefix}/investigations/clues/import-template")
async def clue_import_template(_: dict = Depends(current_identity)):
    content = "\ufeff线索标题,调查任务编号,父调查编号,客户编号,客户,调查平台,侵权产品,负责人,对方主体,来源链接,说明\r\n线上店铺销售疑似侵权产品,RW2026070001,RW2026070000,KH2026070001,示例客户,淘宝,示例商品,管理者,示例店铺,https://example.com,优先使用唯一业务编号自动关联"
    return Response(content=content.encode("utf-8"), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="clue-import-template.csv"'})


@router.post(f"{settings.api_prefix}/investigations/records", status_code=status.HTTP_201_CREATED)
async def create_investigation_record(body: RecordInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.contracts import (
        _contract_allows_downstream_creation, _contract_person_values,
    )
    from app.core.investigation import (
        _configured_investigation_supervisor, _next_investigation_clue_serial,
    )
    from app.core.legacy_sync import (
        _sync_legacy_projection,
    )
    from app.core.permissions import (
        _ensure_record_visible, _require_investigation_clue_write_permission, _user_has_job_permission,
    )
    from app.core.system import (
        _record_dict,
    )
    if body.module not in INVESTIGATION_RECORD_MODULES:
        raise HTTPException(status_code=422, detail="调查中心记录类型无效")
    if body.module in {"notary", "evidence"}:
        raise HTTPException(status_code=422, detail="公证和证据必须从线索专用办理入口创建")
    payload = body.model_dump()
    if body.module == "clue":
        payload["serial_no"] = await _next_investigation_clue_serial(db)
    if await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == payload["serial_no"])):
        raise HTTPException(status_code=409, detail="业务编号已存在")
    payload["status"] = INVESTIGATION_CREATE_STATUS_BY_MODULE[body.module]
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if not user:
        raise HTTPException(status_code=401, detail="当前用户不存在")
    if body.module == "investigation" and identity.get("role") != "admin" and not await _user_has_job_permission(user, "调查任务发布", db):
        raise HTTPException(status_code=403, detail="当前岗位没有发布调查任务权限")
    if body.module == "investigation":
        investigation_data = dict(payload.get("data") or {})
        try:
            contract_id = int(investigation_data.get("contract_record_id") or investigation_data.get("contract_id") or 0)
        except (TypeError, ValueError):
            contract_id = 0
        if not contract_id:
            raise HTTPException(status_code=422, detail="父调查任务必须从合同创建并绑定有效合同")
        contract = await _ensure_record_visible(contract_id, identity, db)
        if not _contract_allows_downstream_creation(contract):
            raise HTTPException(status_code=409, detail="草稿合同不能创建调查任务")
        supervisor = await _configured_investigation_supervisor(db)
        requested_owner = str(payload.get("owner") or "").strip()
        if requested_owner and requested_owner != supervisor.username:
            raise HTTPException(status_code=422, detail="父调查任务必须分配给系统配置的调查主管")
        if payload.get("customer") and str(payload["customer"]).strip() != contract.customer.strip():
            raise HTTPException(status_code=422, detail="调查任务客户必须与关联合同客户一致")
        payload["owner"] = supervisor.username
        payload["customer"] = contract.customer
        payload["department"] = supervisor.department
        payload["data"] = {
            **investigation_data,
            "contract_id": contract.id,
            "contract_record_id": contract.id,
            "contract_no": contract.serial_no,
            "publisher": identity["username"],
            "assigner": identity["username"],
            "source_owner": investigation_data.get("source_owner") or (contract.data or {}).get("source_person") or contract.owner,
        }
    if body.module == "clue":
        await _require_investigation_clue_write_permission(user, db)
        source_task_id = int((payload.get("data") or {}).get("source_task_id") or 0)
        if not source_task_id:
            raise HTTPException(status_code=422, detail="创建线索必须关联已接收的调查任务")
        source_task = await _ensure_record_visible(source_task_id, identity, db)
        if source_task.module not in {"task", "investigation"}:
            raise HTTPException(status_code=404, detail="调查线索来源任务不存在")
        if source_task.module == "task" and not (source_task.data or {}).get("investigation_record_id"):
            raise HTTPException(status_code=422, detail="线索来源必须是调查中心任务")
        if identity.get("role") != "admin" and source_task.owner != identity["username"]:
            raise HTTPException(status_code=403, detail="只能在本人负责的调查任务下创建线索")
        payload["owner"] = source_task.owner
        payload["customer"] = source_task.customer
        payload["department"] = source_task.department
        source_data = source_task.data or {}
        payload["data"] = {**(payload.get("data") or {}), "source_task_id": source_task.id, "source_task_no": source_task.serial_no, "investigation_record_id": source_data.get("investigation_record_id") or (source_task.id if source_task.module == "investigation" else None), "investigation_no": source_data.get("investigation_no") or (source_task.serial_no if source_task.module == "investigation" else ""), "customer_review": bool(source_data.get("customer_review")), "customer_managers": list(source_data.get("customer_managers") or _contract_person_values(source_data.get("customer_manager"))), "customer_manager": source_data.get("customer_manager") or "、".join(list(source_data.get("customer_managers") or [])), "publisher": identity["username"]}
    if identity.get("role") != "admin" and body.module != "investigation":
        payload["department"] = user.department
        if identity.get("role") == "user":
            payload["owner"] = user.username
    record = BusinessRecord(**payload)
    db.add(record)
    await db.flush()
    db.add(WorkflowEvent(record_id=record.id, action="创建调查中心记录", to_status=record.status, operator=identity["username"], comment=f"类型：{body.module}"))
    await _sync_legacy_projection(record, identity, db)
    await db.commit()
    await db.refresh(record)
    return _record_dict(record)


@router.patch(f"{settings.api_prefix}/investigations/records/{{record_id}}")
async def update_investigation_record(record_id: int, body: RecordUpdate, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.legacy_sync import (
        _sync_legacy_projection,
    )
    from app.core.permissions import (
        _ensure_record_visible, _require_investigation_clue_write_permission, _require_record_owner_or_manager, _require_task_owner_or_initiator, _user_has_job_permission,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    record = await _ensure_record_visible(record_id, identity, db)
    if record.module not in {*INVESTIGATION_RECORD_MODULES, "task"}:
        raise HTTPException(status_code=404, detail="调查中心记录不存在")
    if record.module == "task":
        _require_task_owner_or_initiator(record, identity, action="修改调查任务")
    elif record.module == "clue" and record.status in {"待审批", "待客户审核", "待取证", "已取证"}:
        reviewer = await db.scalar(select(User).where(User.username == identity["username"]))
        if identity.get("role") != "admin" and (not reviewer or not await _user_has_job_permission(reviewer, "线索审批", db)):
            await _require_record_owner_or_manager(record, identity, db)
    else:
        await _require_record_owner_or_manager(record, identity, db)
    changes = body.model_dump(exclude_unset=True)
    clue_editable_statuses = {"草稿", "已驳回", "待审批", "待客户审核", "待取证", "已取证"}
    if record.module == "clue" and record.status not in clue_editable_statuses:
        raise HTTPException(status_code=409, detail="当前线索状态不允许修改")
    requested_status = changes.get("status")
    reflow_clue = record.module == "clue" and requested_status == "待审批" and record.status != "待审批"
    if reflow_clue:
        editor = await db.scalar(select(User).where(User.username == identity["username"]))
        if not editor:
            raise HTTPException(status_code=401, detail="当前用户不存在")
        await _require_investigation_clue_write_permission(editor, db)
    if requested_status and requested_status != record.status and not reflow_clue:
        raise HTTPException(status_code=409, detail="调查中心状态必须通过专用审批或办理入口变更")
    if changes.get("owner") and changes["owner"] != record.owner:
        raise HTTPException(status_code=409, detail="调查员/负责人必须通过分配调查员入口修改")
    old_status = record.status
    for field in ("title", "customer", "description"):
        if field in changes and changes[field] is not None:
            setattr(record, field, changes[field])
    if "data" in changes and changes["data"] is not None:
        incoming_data = dict(changes["data"] or {})
        editable_data = {key: incoming_data[key] for key in INVESTIGATION_EDIT_DATA_FIELDS if key in incoming_data}
        if record.module == "investigation" and set(incoming_data) & {"authorization_scope", "authorization_regions", "authorized_from", "authorized_to", "contract_id", "customer_review"} and "authorization_scope_type" not in incoming_data:
            raise HTTPException(status_code=422, detail="请通过基本信息修改表单完整提交授权信息")
        if record.module == "investigation" and "authorization_scope_type" in incoming_data:
            scope_type = incoming_data.get("authorization_scope_type")
            if scope_type not in {"N", "R"}:
                raise HTTPException(status_code=422, detail="授权范围只能为全国或区域")
            right_types = {"商标": 110010, "专利": 110020, "著作权": 110030, "不正当竞争": 110040}
            right_type = incoming_data.get("right_type")
            if right_type not in right_types:
                raise HTTPException(status_code=422, detail="请选择有效的权利类型")
            if not isinstance(incoming_data.get("customer_review"), bool):
                raise HTTPException(status_code=422, detail="请选择线索是否客户审核")
            try:
                start = date.fromisoformat(str(incoming_data.get("authorized_from") or ""))
                end = date.fromisoformat(str(incoming_data.get("authorized_to") or ""))
                contract_id = int(incoming_data.get("contract_id") or 0)
            except (TypeError, ValueError):
                raise HTTPException(status_code=422, detail="合同及授权起止日期为必填项")
            if end <= start:
                raise HTTPException(status_code=422, detail="授权结束日期必须晚于开始日期")
            contract = await _ensure_record_visible(contract_id, identity, db)
            if contract.module != "contract" or contract.customer != record.customer:
                raise HTTPException(status_code=422, detail="请选择当前权利人的合同")
            if contract.status in {"已删除", "已取消", "已作废"}:
                raise HTTPException(status_code=422, detail="该合同已失效，请重新选择")
            regions = incoming_data.get("authorization_regions") or []
            if not isinstance(regions, list) or len(regions) > 500 or any(
                not isinstance(path, list) or not 1 <= len(path) <= 2
                or any(not isinstance(part, str) or not part.strip() or len(part) > 60 for part in path)
                for path in regions
            ):
                raise HTTPException(status_code=422, detail="授权区域格式无效，请重新选择省市")
            if scope_type == "R" and not regions:
                raise HTTPException(status_code=422, detail="请选择授权区域")
            if any(path[0] not in _AUTHORIZATION_CITIES or (len(path) == 2 and path[1] not in _AUTHORIZATION_CITIES[path[0]]) for path in regions):
                raise HTTPException(status_code=422, detail="授权省市不存在或不属于同一区域")
            regions = regions if scope_type == "R" else []
            provinces = list(dict.fromkeys(path[0].strip() for path in regions))
            cities = list(dict.fromkeys(city for path in regions for city in (_AUTHORIZATION_CITIES[path[0]] if len(path) == 1 else [path[1]])))
            scope = "全国" if scope_type == "N" else "、".join(" ".join(path) for path in regions)
            editable_data.update({
                "authorization_scope_type": scope_type, "authorization_regions": regions,
                "authorization_scope": scope, "region": "全国" if scope_type == "N" else "区域",
                "province": ",".join(provinces), "city": ",".join(cities), "district": "",
                "authorized_from": str(start), "authorized_to": str(end),
                "customer_review": incoming_data["customer_review"], "case_type_id": right_types[right_type],
                "contract_id": contract.id, "contract_record_id": contract.id,
                "contract_no": contract.serial_no, "contract_name": contract.title,
            })
        record.data = {**(record.data or {}), **editable_data}
    if reflow_clue:
        record.status = "待审批"
        record.data = {
            **(record.data or {}),
            "reviewer": "", "reviewed_at": "", "review_comment": "",
            "customer_reviewer": "", "customer_reviewed_at": "", "customer_review_comment": "",
            "rejection_reason": "", "resubmitted_at": datetime.now().isoformat(timespec="seconds"),
            "resubmitted_by": identity["username"],
        }
    db.add(WorkflowEvent(record_id=record.id, action="修改并重新提交线索审批" if reflow_clue else "修改调查中心资料", from_status=old_status, to_status=record.status, operator=identity["username"], comment="通过调查中心专用入口修改基础资料"))
    await _sync_legacy_projection(record, identity, db)
    await db.commit()
    await db.refresh(record)
    return _record_dict(record, await _allowed_field_keys(identity, db))


@router.post(f"{settings.api_prefix}/investigations/clues/import")
async def import_investigation_clues(file: UploadFile = File(...), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.investigation import (
        _next_investigation_clue_serial,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _import_relation_data, _unique_import_record, _validate_import_relation_consistency,
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
    reader = csv.DictReader(io.StringIO(content))
    existing_rows = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "clue"))).all()
    existing = {(x.title.strip().casefold(), x.customer.strip().casefold(), str((x.data or {}).get("product", "")).strip().casefold()) for x in existing_rows}
    scope = await _record_scope_conditions(identity, db)
    scoped_records = list((await db.scalars(select(BusinessRecord).where(*scope))).all())
    customers = [item for item in scoped_records if item.module == "customer"]
    investigations = [item for item in scoped_records if item.module == "investigation"]
    tasks = [item for item in scoped_records if item.module == "task"]
    seen: set[tuple[str, str, str]] = set(); created = 0; errors: list[dict] = []
    for row_no, row in enumerate(reader, 2):
        title = (row.get("线索标题") or row.get("title") or "").strip()
        customer_value = (row.get("客户编号") or row.get("customer_no") or row.get("客户") or row.get("customer") or "").strip()
        platform = (row.get("调查平台") or row.get("platform") or "").strip()
        product = (row.get("侵权产品") or row.get("product") or "").strip()
        owner = (row.get("负责人") or row.get("owner") or identity["username"]).strip()
        if not title or not product:
            errors.append({"row": row_no, "error": "线索标题、侵权产品为必填项"}); continue
        if any(separator in product for separator in ["；", ";", "、", "\n"]):
            errors.append({"row": row_no, "error": "每行只能填写一种侵权产品，请拆分为多行"}); continue
        try:
            task = _unique_import_record(tasks, (row.get("调查任务编号") or row.get("task_no") or "").strip(), "关联调查任务")
            investigation = _unique_import_record(investigations, (row.get("父调查编号") or row.get("调查编号") or row.get("investigation_no") or "").strip(), "关联父调查")
            customer_record = _unique_import_record(customers, customer_value, "关联客户")
            relations = {name: item for name, item in (("task", task), ("investigation", investigation), ("customer", customer_record)) if item}
            if not relations:
                raise ValueError("必须提供调查任务编号、父调查编号或客户编号/名称以建立真实关联")
            _validate_import_relation_consistency(relations)
            relation_data = _import_relation_data(task=task, investigation=investigation, customer=customer_record)
            inherited_customer_id = relation_data.get("customer_record_id") or relation_data.get("customer_id")
            if inherited_customer_id:
                inherited_customer = next((item for item in customers if item.id == int(inherited_customer_id)), None)
                if inherited_customer:
                    if customer_record and customer_record.id != inherited_customer.id:
                        raise ValueError(f"关联关系冲突：所选任务/调查不属于客户 {customer_record.serial_no}")
                    customer_record = inherited_customer
                    relation_data.update(_import_relation_data(customer=inherited_customer))
            customer = customer_record.title if customer_record else str(relation_data.get("customer_title") or "").strip()
            if not customer:
                raise ValueError("关联任务/调查未绑定客户，请先修复父级关系")
        except ValueError as exc:
            errors.append({"row": row_no, "error": str(exc)}); continue
        key = (title.casefold(), customer.casefold(), product.casefold())
        if key in existing or key in seen:
            errors.append({"row": row_no, "error": "相同客户、标题和侵权产品的线索重复"}); continue
        serial_no = await _next_investigation_clue_serial(db)
        item = BusinessRecord(
            module="clue", serial_no=serial_no, title=title, customer=customer,
            status="草稿", owner=owner or identity["username"], department="上海分所",
            description=(row.get("说明") or row.get("description") or "").strip(),
            data={**relation_data, "source_task_id": task.id if task else relation_data.get("task_record_id"), "source_task_no": task.serial_no if task else relation_data.get("task_no", ""), "platform": platform, "product": product, "opponent": (row.get("对方主体") or row.get("opponent") or "").strip(), "source_url": (row.get("来源链接") or row.get("source_url") or "").strip(), "publisher": identity["username"], "imported_by": identity["username"], "imported_at": datetime.now().isoformat(timespec="seconds")},
        )
        db.add(item); await db.flush()
        db.add(WorkflowEvent(record_id=item.id, action="批量导入线索", to_status="草稿", operator=identity["username"], comment=f"CSV 第 {row_no} 行"))
        seen.add(key); created += 1
    await db.commit()
    return {"created": created, "failed": len(errors), "errors": errors}


@router.get(f"{settings.api_prefix}/investigations/notaries/import-template")
async def notary_import_template(_: dict = Depends(current_identity)):
    content = "\ufeff来源线索编号,公证标题,负责人,审核截止日,公证书编号,签发日期,存放位置,实物已收,说明\r\nXS2026070015,线上侵权产品公证审核,管理者,2026-08-15,(2026)沪证字001号,2026-08-10,上海档案室A-01,是,来源线索必须已经存在"
    return Response(content=content.encode("utf-8"), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="notary-import-template.csv"'})


@router.post(f"{settings.api_prefix}/investigations/notaries/import", status_code=status.HTTP_201_CREATED)
async def import_investigation_notaries(file: UploadFile = File(...), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _import_relation_data,
    )
    if not (file.filename or "").lower().endswith(".csv"): raise HTTPException(status_code=422, detail="仅支持 UTF-8 CSV 文件")
    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024: raise HTTPException(status_code=413, detail="导入文件不能超过 5MB")
    try: content = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc: raise HTTPException(status_code=422, detail="CSV 必须使用 UTF-8 编码") from exc
    clues = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "clue", *(await _record_scope_conditions(identity, db))))).all()
    clue_by_no = {item.serial_no.strip().casefold(): item for item in clues}
    existing_clue_ids = set((await db.scalars(select(BusinessRecord.data["clue_id"].as_integer()).where(BusinessRecord.module == "notary"))).all())
    existing_certificate_nos = {str(value).strip().casefold() for value in (await db.scalars(select(BusinessRecord.data["certificate_no"].as_string()).where(BusinessRecord.module == "notary"))).all() if value}
    seen: set[int] = set(); created_ids: list[int] = []; errors: list[dict] = []
    for row_no, row in enumerate(csv.DictReader(io.StringIO(content)), 2):
        clue_no = (row.get("来源线索编号") or row.get("clue_no") or "").strip()
        clue = clue_by_no.get(clue_no.casefold())
        if not clue: errors.append({"row": row_no, "error": "来源线索编号不存在"}); continue
        if clue.status not in {"已取证", "待公证", "已转案件"}: errors.append({"row": row_no, "error": "来源线索完成取证登记后才能导入公证信息"}); continue
        if clue.id in existing_clue_ids or clue.id in seen or (clue.data or {}).get("notary_record_id"):
            errors.append({"row": row_no, "error": "该线索已经存在公证记录"}); continue
        raw_due = (row.get("审核截止日") or row.get("review_due_date") or "").strip()
        try: due = date.fromisoformat(raw_due) if raw_due else date.today() + timedelta(days=30)
        except ValueError: errors.append({"row": row_no, "error": "审核截止日格式应为 YYYY-MM-DD"}); continue
        if due < date.today(): errors.append({"row": row_no, "error": "审核截止日不能早于今天"}); continue
        certificate_no = (row.get("公证书编号") or row.get("certificate_no") or "").strip(); raw_issued = (row.get("签发日期") or row.get("issued_date") or "").strip()
        if certificate_no and certificate_no.casefold() in existing_certificate_nos: errors.append({"row": row_no, "error": "公证书编号已经登记"}); continue
        try: issued_date = str(date.fromisoformat(raw_issued)) if raw_issued else ""
        except ValueError: errors.append({"row": row_no, "error": "签发日期格式应为 YYYY-MM-DD"}); continue
        clue_data = dict(clue.data or {}); serial_no = f"GZ{datetime.now():%Y%m%d%H%M%S}{row_no:04d}{uuid4().hex[:4].upper()}"
        relation_data = _import_relation_data(clue=clue)
        item = BusinessRecord(module="notary", serial_no=serial_no, title=(row.get("公证标题") or row.get("title") or f"{clue.title}—公证审核").strip(), customer=clue.customer, status="等待材料", owner=(row.get("负责人") or row.get("owner") or clue.owner).strip(), department=clue.department, description=(row.get("说明") or row.get("description") or "批量导入公证记录").strip(), data={**relation_data, "clue_id": clue.id, "clue_no": clue.serial_no, "platform": clue_data.get("platform", ""), "product": clue_data.get("product", ""), "case_id": clue_data.get("converted_case_id") or relation_data.get("case_record_id"), "case_no": clue_data.get("converted_case_no", "") or relation_data.get("case_no", ""), "review_due_date": str(due), "certificate_no": certificate_no, "certificate_issued_date": issued_date, "certificate_storage_location": (row.get("存放位置") or row.get("storage_location") or "").strip(), "physical_received": (row.get("实物已收") or row.get("physical_received") or "").strip().casefold() in {"是", "true", "1", "yes"}, "imported_at": datetime.now().isoformat(timespec="seconds")})
        db.add(item); await db.flush(); previous = clue.status; clue.status = "已转案件" if clue_data.get("converted_case_id") else "待公证"; clue.data = {**clue_data, "notary": "等待公证书扫描件", "notary_record_id": item.id}
        db.add_all([WorkflowEvent(record_id=clue.id, action="批量导入公证信息", from_status=previous, to_status=clue.status, operator=identity["username"], comment=f"CSV 第 {row_no} 行，生成 {serial_no}"), WorkflowEvent(record_id=item.id, action="批量导入公证", to_status="等待材料", operator=identity["username"], comment=f"来源线索 {clue.serial_no}；等待公证书扫描件")])
        seen.add(clue.id); created_ids.append(item.id)
        if certificate_no: existing_certificate_nos.add(certificate_no.casefold())
    await db.commit()
    return {"created": len(created_ids), "created_ids": created_ids, "failed": len(errors), "errors": errors}


@router.post(f"{settings.api_prefix}/investigations/notaries/storage/import", status_code=status.HTTP_201_CREATED)
async def import_notary_storage(file: UploadFile = File(...), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Update warehouse/certificate/invoice/case fields on existing notary records from UTF-8 CSV."""
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _import_relation_data, _unique_import_record,
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
    records = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "notary", *(await _record_scope_conditions(identity, db))))).all()
    cases = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "case", *(await _record_scope_conditions(identity, db))))).all()
    by_clue = {str((item.data or {}).get("clue_no", "")).strip().casefold(): item for item in records if (item.data or {}).get("clue_no")}
    by_certificate = {str((item.data or {}).get("certificate_no", "")).strip().casefold(): item for item in records if (item.data or {}).get("certificate_no")}
    updated = 0; errors: list[dict] = []; seen: set[int] = set(); imported_rows: list[dict] = []
    for row_no, row in enumerate(csv.DictReader(io.StringIO(content)), 2):
        clue_no = (row.get("线索号") or row.get("线索编号") or row.get("clue_no") or "").strip()
        certificate_no = (row.get("公证书号") or row.get("certificate_no") or "").strip()
        item = by_clue.get(clue_no.casefold()) if clue_no else None
        if item is None and certificate_no:
            item = by_certificate.get(certificate_no.casefold())
        if item is None:
            errors.append({"row": row_no, "error": "未找到对应公证记录（请提供有效线索号或公证书号）"}); continue
        if item.id in seen:
            errors.append({"row": row_no, "error": "同一公证记录在文件中重复"}); continue
        data = dict(item.data or {})
        try:
            case_record = _unique_import_record(cases, (row.get("案号") or row.get("案件编号") or row.get("case_no") or "").strip(), "关联案件")
            if case_record:
                existing_case_id = data.get("case_record_id") or data.get("case_id")
                existing_case_no = str(data.get("case_no") or "").strip()
                if existing_case_id and int(existing_case_id) != case_record.id:
                    raise ValueError(f"关联关系冲突：公证记录不属于案件 {case_record.serial_no}")
                if existing_case_no and existing_case_no != case_record.serial_no:
                    raise ValueError(f"关联关系冲突：公证记录不属于案件 {case_record.serial_no}")
                data.update(_import_relation_data(case=case_record))
        except ValueError as exc:
            errors.append({"row": row_no, "error": str(exc)}); continue
        values = {
            "certificate_no": certificate_no,
            "warehouse": (row.get("仓库") or row.get("仓库位置") or row.get("warehouse") or "").strip(),
            "invoice_no": (row.get("发票号") or row.get("invoice_no") or "").strip(),
            "case_no": case_record.serial_no if case_record else "",
            "investigator": (row.get("调查员") or row.get("investigator") or "").strip(),
            "investigated_at": (row.get("调查时间") or row.get("investigated_at") or "").strip(),
            "infringement_method": (row.get("侵权方式") or row.get("infringement_method") or "").strip(),
            "shop_name": (row.get("店铺名称") or row.get("shop_name") or "").strip(),
            "address": (row.get("调查地址") or row.get("address") or "").strip(),
        }
        item.data = {**data, **{key: value for key, value in values.items() if value}}
        db.add(WorkflowEvent(record_id=item.id, action="导入公证仓库信息", from_status=item.status, to_status=item.status, operator=identity["username"], comment=f"CSV 第 {row_no} 行"))
        imported_rows.append({
            "id": item.id,
            "线索号": clue_no or str(data.get("clue_no", "")),
            "调查员": values["investigator"] or item.owner,
            "调查时间": values["investigated_at"] or str(data.get("investigated_at", "")),
            "侵权方式": values["infringement_method"] or str(data.get("infringement_method", "")),
            "店铺名称": values["shop_name"] or str(data.get("shop_name", "")),
            "调查地址": values["address"] or str(data.get("address", "")),
            "公证书号": values["certificate_no"] or str(data.get("certificate_no", "")),
            "仓库": values["warehouse"] or str(data.get("warehouse", "")),
            "发票号": values["invoice_no"] or str(data.get("invoice_no", "")),
            "案号": values["case_no"] or str(data.get("case_no", "")),
        })
        seen.add(item.id); updated += 1
    await db.commit()
    return {"created": updated, "updated": updated, "updated_ids": sorted(seen), "items": imported_rows, "failed": len(errors), "errors": errors}


@router.post(f"{settings.api_prefix}/investigations/notaries/files/import", status_code=status.HTTP_201_CREATED)
async def import_notary_certificate_file(file: UploadFile = File(...), certificate_no: str = Form(...), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.investigation import (
        _import_notary_named_file,
    )
    return await _import_notary_named_file(file, "certificate_no", certificate_no, "公证书扫描件", identity, db)


@router.post(f"{settings.api_prefix}/investigations/notaries/invoices/import", status_code=status.HTTP_201_CREATED)
async def import_notary_invoice_file(file: UploadFile = File(...), invoice_no: str = Form(...), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.investigation import (
        _import_notary_named_file,
    )
    return await _import_notary_named_file(file, "invoice_no", invoice_no, "公证发票", identity, db)


@router.get(f"{settings.api_prefix}/investigations/notaries/files")
async def list_notary_files(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Return one query row per imported certificate or invoice attachment."""
    from app.core.permissions import (
        _record_scope_conditions,
    )
    rows = (await db.execute(
        select(FileAttachment, BusinessRecord)
        .join(BusinessRecord, FileAttachment.record_id == BusinessRecord.id)
        .where(
            BusinessRecord.module == "notary",
            FileAttachment.category.in_({"公证书扫描件", "公证发票"}),
            *(await _record_scope_conditions(identity, db)),
        )
        .order_by(FileAttachment.created_at.desc(), FileAttachment.id.desc())
    )).all()
    items = []
    for attachment, record in rows:
        data = record.data or {}
        items.append({
            "id": attachment.id,
            "module": "notary_file",
            "serial_no": record.serial_no,
            "title": attachment.original_name,
            "customer": record.customer,
            "status": record.status,
            "owner": attachment.uploader or record.owner,
            "description": attachment.remark,
            "created_at": attachment.created_at.isoformat() if attachment.created_at else "",
            "updated_at": attachment.created_at.isoformat() if attachment.created_at else "",
            "data": {
                "attachment_id": attachment.id,
                "attachment_category": attachment.category,
                "invoice_no": data.get("invoice_no") or "",
                "certificate_no": data.get("certificate_no") or "",
                "collected_at": data.get("collected_at") or "",
                "notary_institution": data.get("notary_institution") or "",
                "clue_no": data.get("clue_no") or "",
                "case_no": data.get("case_no") or "",
                "document_type": attachment.category,
                "shop_name": data.get("shop_name") or record.title,
                "handler": attachment.uploader or record.owner,
                "imported_at": attachment.created_at.isoformat() if attachment.created_at else "",
            },
        })
    return {"items": items, "total": len(items)}


@router.post(f"{settings.api_prefix}/investigations/clues/{{clue_id}}/submit")
async def submit_investigation_clue(clue_id: int, body: TaskActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.investigation import (
        _apply_clue_submission, _validate_clue_submission,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_investigation_clue_write_permission, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _record_dict,
    )
    clue = await _ensure_record_module(clue_id, "clue", identity, db); await _require_record_owner_or_manager(clue, identity, db)
    submitter = await db.scalar(select(User).where(User.username == identity["username"]))
    if not submitter:
        raise HTTPException(status_code=401, detail="当前用户不存在")
    await _require_investigation_clue_write_permission(submitter, db)
    _validate_clue_submission(clue)
    _apply_clue_submission(clue, identity, body.comment, db)
    await db.commit(); await db.refresh(clue); return _record_dict(clue)


@router.post(f"{settings.api_prefix}/investigations/clues/batch-submit")
async def batch_submit_investigation_clues(body: ClueBatchSubmitInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.investigation import (
        _apply_clue_submission, _validate_clue_submission,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_investigation_clue_write_permission, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _record_dict,
    )
    clue_ids = list(dict.fromkeys(body.clue_ids))
    submitter = await db.scalar(select(User).where(User.username == identity["username"]))
    if not submitter:
        raise HTTPException(status_code=401, detail="当前用户不存在")
    await _require_investigation_clue_write_permission(submitter, db)
    clues: list[BusinessRecord] = []
    for clue_id in clue_ids:
        clue = await _ensure_record_module(clue_id, "clue", identity, db)
        await _require_record_owner_or_manager(clue, identity, db)
        _validate_clue_submission(clue)
        clues.append(clue)
    for clue in clues:
        _apply_clue_submission(clue, identity, body.comment, db)
    await db.commit()
    for clue in clues:
        await db.refresh(clue)
    return {"updated": len(clues), "items": [_record_dict(clue) for clue in clues]}


@router.get(f"{settings.api_prefix}/investigations/clues/{{clue_id}}/reviewer-candidates")
async def list_investigation_clue_reviewer_candidates(clue_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _person_display_name,
    )
    from app.core.permissions import (
        _ensure_record_module, _user_has_job_permission,
    )
    await _ensure_record_module(clue_id, "clue", identity, db)
    users = list((await db.scalars(select(User).where(User.is_active.is_(True)).order_by(User.display_name, User.username))).all())
    candidates = []
    for user in users:
        if await _user_has_job_permission(user, "线索审批", db):
            candidates.append({"username": user.username, "display_name": _person_display_name(user.display_name, user.username)[0], "department": user.department})
    return {"items": candidates, "total": len(candidates)}


@router.post(f"{settings.api_prefix}/investigations/clues/{{clue_id}}/turn-on-audit")
async def turn_on_investigation_clue_audit(clue_id: int, body: ClueTurnOnAuditInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _user_has_job_permission,
    )
    from app.core.system import (
        _record_dict,
    )
    clue = await _ensure_record_module(clue_id, "clue", identity, db)
    if clue.status != "待审批":
        raise HTTPException(status_code=409, detail="只有待审批线索可以转交审核人")
    actor = await db.scalar(select(User).where(User.username == identity["username"], User.is_active.is_(True)))
    if not actor or not await _user_has_job_permission(actor, "线索审批", db):
        raise HTTPException(status_code=403, detail="当前账号没有线索审批岗位权限")
    current_reviewer = str((clue.data or {}).get("reviewer") or "").strip()
    if current_reviewer and current_reviewer != identity["username"] and identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="只有当前审核人可以转交该线索")
    reviewer = await db.scalar(select(User).where(User.username == body.reviewer.strip(), User.is_active.is_(True)))
    if not reviewer or not await _user_has_job_permission(reviewer, "线索审批", db):
        raise HTTPException(status_code=422, detail="目标审核人不存在、已停用或没有线索审批岗位权限")
    if reviewer.username == current_reviewer:
        raise HTTPException(status_code=409, detail="目标审核人与当前审核人相同")
    transferred_at = datetime.now().isoformat(timespec="seconds")
    clue.data = {
        **(clue.data or {}), "previous_reviewer": current_reviewer,
        "reviewer": reviewer.username, "turn_on_auditor": reviewer.username,
        "turn_on_audit_time": transferred_at,
    }
    db.add(WorkflowEvent(
        record_id=clue.id, action="转交线索审核人", from_status=clue.status,
        to_status=clue.status, operator=identity["username"],
        comment=f"{current_reviewer or '未指定'} -> {reviewer.username}；{body.comment}",
    ))
    await db.commit(); await db.refresh(clue)
    return _record_dict(clue)


@router.post(f"{settings.api_prefix}/investigations/clues/{{clue_id}}/review")
async def review_investigation_clue(clue_id: int, body: ClueReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _record_scope_conditions, _user_has_job_permission,
    )
    from app.core.system import (
        _record_dict,
    )
    reviewer = await db.scalar(select(User).where(User.username == identity["username"]))
    if not reviewer or not await _user_has_job_permission(reviewer, "线索审批", db):
        raise HTTPException(status_code=403, detail="当前账号没有线索审批岗位权限")
    clue = await _ensure_record_module(clue_id, "clue", identity, db)
    if clue.status != "待审批": raise HTTPException(status_code=409, detail="只有待审批线索可以审核")
    assigned_reviewer = str((clue.data or {}).get("reviewer") or "").strip()
    if assigned_reviewer and assigned_reviewer != identity["username"] and identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="该线索已分配给其他审核人")
    next_status = "待客户审核" if body.approved and bool((clue.data or {}).get("customer_review")) else "待取证" if body.approved else "已驳回"
    merge_into_case_no = body.merge_into_case_no.strip()
    merge_case = None
    if merge_into_case_no:
        merge_case = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "case", BusinessRecord.serial_no == merge_into_case_no, *(await _record_scope_conditions(identity, db))))
        if not merge_case:
            raise HTTPException(status_code=422, detail="并入案号未找到或无权访问")
    clue.status = next_status
    clue.data = {**(clue.data or {}), "reviewer": identity["username"], "reviewed_at": datetime.now().isoformat(timespec="seconds"), "review_comment": body.comment, "rejection_reason": "" if body.approved else body.comment,
                 "suspected_conflict_clue_nos": list(dict.fromkeys(body.suspected_conflict_clue_nos)),
                 "suspected_conflict_case_nos": list(dict.fromkeys(body.suspected_conflict_case_nos)),
                 "supplement_evidence": body.supplement_evidence.strip(),
                 "merge_into_case_no": merge_into_case_no, "merge_into_case_id": merge_case.id if merge_case else None}
    db.add(WorkflowEvent(record_id=clue.id, action="线索内部审批通过，待客户审核" if next_status == "待客户审核" else "线索审批通过" if body.approved else "线索审批驳回", from_status="待审批", to_status=clue.status, operator=identity["username"], comment=body.comment))
    await db.commit(); await db.refresh(clue); return _record_dict(clue)


@router.post(f"{settings.api_prefix}/investigations/clues/{{clue_id}}/customer-review")
async def customer_review_investigation_clue(clue_id: int, body: ClueReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _record_dict,
    )
    clue = await _ensure_record_module(clue_id, "clue", identity, db)
    if clue.status != "待客户审核":
        raise HTTPException(status_code=409, detail="只有待客户审核线索可以确认客户审核结果")
    if identity.get("role") != "admin":
        customer = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "customer", BusinessRecord.title == clue.customer))
        customer_managers = set((customer.data or {}).get("customer_managers") or ([customer.owner] if customer else []))
        if identity["username"] not in customer_managers:
            raise HTTPException(status_code=403, detail="仅该客户的客户管理人可以代录客户审核结果")
    clue.status = "待取证" if body.approved else "已驳回"
    clue.data = {**(clue.data or {}), "customer_reviewer": identity["username"], "customer_reviewed_at": datetime.now().isoformat(timespec="seconds"), "customer_review_comment": body.comment, "rejection_reason": "" if body.approved else body.comment}
    db.add(WorkflowEvent(record_id=clue.id, action="客户审核通过" if body.approved else "客户审核驳回", from_status="待客户审核", to_status=clue.status, operator=identity["username"], comment=body.comment))
    await db.commit(); await db.refresh(clue); return _record_dict(clue)


@router.post(f"{settings.api_prefix}/investigations/clues/batch-collect")
async def register_clue_collection_batch(body: ClueBatchCollectionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.investigation import (
        _register_clue_collection,
    )
    clue_ids = list(dict.fromkeys(body.clue_ids))
    if len(clue_ids) < 2:
        raise HTTPException(status_code=422, detail="批量取证至少需要选择两条线索")
    if body.evidence_file_ids:
        raise HTTPException(status_code=422, detail="批量取证不支持共用附件，请在单个取证中分别上传")
    collected = []
    try:
        for clue_id in clue_ids:
            collected.append(await _register_clue_collection(clue_id, body, identity, db))
    except Exception:
        await db.rollback()
        raise
    await db.commit()
    return {"collected": len(collected), "clue_ids": [clue.id for clue in collected]}


@router.post(f"{settings.api_prefix}/investigations/clues/{{clue_id}}/collect")
async def register_clue_collection(clue_id: int, body: ClueCollectionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.investigation import (
        _register_clue_collection,
    )
    from app.core.system import (
        _record_dict,
    )
    clue = await _register_clue_collection(clue_id, body, identity, db)
    await db.commit(); await db.refresh(clue); return _record_dict(clue)


@router.post(f"{settings.api_prefix}/investigations/clues/{{clue_id}}/evidence", status_code=status.HTTP_201_CREATED)
async def create_evidence_from_clue(clue_id: int, body: EvidenceCreateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.investigation import (
        _sync_investigation_relation_links,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _record_dict,
    )
    clue = await _ensure_record_module(clue_id, "clue", identity, db); await _require_record_owner_or_manager(clue, identity, db)
    if clue.status in {"草稿", "待审批", "已驳回"}: raise HTTPException(status_code=409, detail="线索审批通过后才能建立证据目录")
    user = await db.scalar(select(User).where(User.username == identity["username"])); owner = body.owner.strip() or identity["username"]
    if identity.get("role") == "user": owner = identity["username"]
    serial_no = f"ZJ{datetime.now():%Y%m%d%H%M%S%f}"; item = BusinessRecord(module="evidence", serial_no=serial_no, title=body.title.strip(), customer=clue.customer, status="待整理", owner=owner, department=user.department if user else clue.department, description=body.description, data={"source": body.source, "clue_id": clue.id, "clue_no": clue.serial_no, "platform": (clue.data or {}).get("platform", ""), "product": (clue.data or {}).get("product", ""), "notarization_no": body.notarization_no.strip(), "invoice_no": body.invoice_no.strip(), "storage_location": body.storage_location.strip(), "storage_state": body.storage_state.strip() or "待整理", "evidence_file_ids": list(dict.fromkeys(body.evidence_file_ids))})
    db.add(item); await db.flush()
    await _sync_investigation_relation_links(item, db)
    evidence_ids = list((clue.data or {}).get("evidence_ids", [])); evidence_ids.append(item.id); clue.data = {**(clue.data or {}), "evidence_ids": list(dict.fromkeys(evidence_ids)), "evidence_count": len(set(evidence_ids))}
    db.add_all([WorkflowEvent(record_id=clue.id, action="建立证据目录", from_status=clue.status, to_status=clue.status, operator=identity["username"], comment=f"生成 {serial_no}"), WorkflowEvent(record_id=item.id, action="从线索建立证据", to_status="待整理", operator=identity["username"], comment=f"来源线索 {clue.serial_no}")])
    await db.commit(); await db.refresh(item); return _record_dict(item)


@router.post(f"{settings.api_prefix}/investigations/evidence/{{evidence_id}}/organize")
async def organize_evidence(evidence_id: int, body: TaskActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.investigation import (
        _sync_investigation_relation_links,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _record_dict,
    )
    item = await _ensure_record_module(evidence_id, "evidence", identity, db); await _require_record_owner_or_manager(item, identity, db)
    if item.status != "待整理": raise HTTPException(status_code=409, detail="只有待整理证据可以完成整理")
    item.status = "已整理"; item.data = {**(item.data or {}), "organized_at": datetime.now().isoformat(timespec="seconds"), "organized_by": identity["username"]}
    db.add(WorkflowEvent(record_id=item.id, action="完成证据整理", from_status="待整理", to_status=item.status, operator=identity["username"], comment=body.comment)); await _sync_investigation_relation_links(item, db); await db.commit(); await db.refresh(item); return _record_dict(item)


@router.post(f"{settings.api_prefix}/investigations/evidence/{{evidence_id}}/file")
async def file_evidence(evidence_id: int, body: TaskActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.investigation import (
        _sync_investigation_relation_links,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _record_dict,
    )
    item = await _ensure_record_module(evidence_id, "evidence", identity, db); await _require_record_owner_or_manager(item, identity, db)
    if item.status != "已整理": raise HTTPException(status_code=409, detail="证据整理完成后才能入卷")
    categories = set((await db.scalars(select(FileAttachment.category).where(FileAttachment.record_id == item.id))).all())
    if "证据目录" not in categories or not categories.intersection({"证据原件", "证据扫描件"}): raise HTTPException(status_code=422, detail="入卷前必须上传证据目录及证据原件或扫描件")
    item.status = "已入卷"; item.data = {**(item.data or {}), "filed_at": datetime.now().isoformat(timespec="seconds"), "filed_by": identity["username"], "file_categories": sorted(categories)}
    db.add(WorkflowEvent(record_id=item.id, action="证据入卷", from_status="已整理", to_status=item.status, operator=identity["username"], comment=body.comment)); await _sync_investigation_relation_links(item, db); await db.commit(); await db.refresh(item); return _record_dict(item)


@router.put(f"{settings.api_prefix}/investigations/evidence/{{evidence_id}}")
async def update_evidence_record(evidence_id: int, body: EvidenceUpdateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.investigation import (
        _sync_investigation_relation_links,
    )
    from app.core.legacy_sync import (
        _sync_legacy_investigation_clue_evidence, _sync_legacy_projection,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _optional_record_id, _record_dict,
    )
    item = await _ensure_record_module(evidence_id, "evidence", identity, db)
    await _require_record_owner_or_manager(item, identity, db)
    data = dict(item.data or {})
    values = body.model_dump(exclude_none=True)
    for key in ("title", "description"):
        if key in values:
            setattr(item, key, str(values[key]).strip())
    if "owner" in values:
        item.owner = str(values["owner"]).strip() or item.owner
    for key in ("source", "notarization_no", "invoice_no", "storage_location", "storage_state", "notary_institution"):
        if key in values:
            data[key] = str(values[key]).strip()
    if "collected_at" in values:
        data["collected_at"] = str(values["collected_at"])
    if "certificate_no" in values:
        data["notarization_no"] = str(values["certificate_no"]).strip()
    if "evidence_status" in values:
        evidence_status = str(values["evidence_status"]).strip()
        if evidence_status not in {"未入库", "已入库", "已出库", "已重新入库", "已销毁"}:
            raise HTTPException(status_code=422, detail="证物状态无效")
        data["storage_state"] = evidence_status
    item.data = data
    db.add(WorkflowEvent(record_id=item.id, action="修改证据信息", from_status=item.status, to_status=item.status, operator=identity["username"], comment="、".join(values)))
    await _sync_investigation_relation_links(item, db)
    clue_id = _optional_record_id(data.get("clue_id") or data.get("clue_record_id"))
    clue = await db.get(BusinessRecord, clue_id) if clue_id else None
    if clue and clue.module == "clue":
        clue_data = dict(clue.data or {})
        if _optional_record_id(clue_data.get("collection_evidence_record_id")) == item.id:
            clue.data = {
                **clue_data,
                "collected_at": data.get("collected_at") or clue_data.get("collected_at") or "",
                "notary_institution": data.get("notary_institution") or "",
                "notarization_no": data.get("notarization_no") or "",
                "certificate_no": data.get("notarization_no") or "",
                "invoice_no": data.get("invoice_no") or "",
                "storage_location": data.get("storage_location") or "",
                "evidence_status": data.get("storage_state") or "未入库",
            }
            await _sync_legacy_projection(clue, identity, db)
            await _sync_legacy_investigation_clue_evidence(
                clue, identity, db, list(dict.fromkeys(clue_data.get("collection_file_ids") or [])),
            )
    await db.commit(); await db.refresh(item); return _record_dict(item)


@router.get(f"{settings.api_prefix}/investigations/clues/{{clue_id}}/workspace")
async def get_investigation_clue_workspace(clue_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _record_scope_conditions,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    from app.core.system import (
        _optional_record_id, _record_dict,
    )
    clue = await _ensure_record_module(clue_id, "clue", identity, db)
    visible_evidence = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "evidence", *(await _record_scope_conditions(identity, db)),
    ).order_by(BusinessRecord.created_at.asc(), BusinessRecord.id.asc()))).all())
    clue_data = clue.data or {}
    linked_ids = {
        record_id for value in (
            list(clue_data.get("evidence_ids") or [])
            + [clue_data.get("collection_evidence_record_id")]
        ) if (record_id := _optional_record_id(value))
    }
    evidence = [
        item for item in visible_evidence
        if item.id in linked_ids
        or _optional_record_id((item.data or {}).get("clue_id") or (item.data or {}).get("clue_record_id")) == clue.id
        or str((item.data or {}).get("clue_no") or "").strip() == clue.serial_no
    ]
    record_ids = [clue.id, *[item.id for item in evidence]]
    attachments = list((await db.scalars(select(FileAttachment).where(
        FileAttachment.record_id.in_(record_ids),
    ).order_by(FileAttachment.created_at.asc(), FileAttachment.id.asc()))).all())
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    def can_manage(item: BusinessRecord) -> bool:
        return bool(
            identity.get("role") == "admin"
            or item.owner == identity["username"]
            or (identity.get("role") == "manager" and user and item.department == user.department)
        )
    return {
        "clue": _record_dict(clue),
        "clue_files": [_attachment_dict(item, clue) for item in attachments if item.record_id == clue.id],
        "evidence": [
            {
                **_record_dict(item),
                "files": [_attachment_dict(file, item) for file in attachments if file.record_id == item.id],
                "can_edit": can_manage(item),
                "can_delete": can_manage(item) and item.status != "已入卷",
            }
            for item in evidence
        ],
    }


@router.delete(f"{settings.api_prefix}/investigations/evidence/{{evidence_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_investigation_evidence(evidence_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _optional_record_id,
    )
    item = await _ensure_record_module(evidence_id, "evidence", identity, db)
    await _require_record_owner_or_manager(item, identity, db)
    if item.status == "已入卷":
        raise HTTPException(status_code=409, detail="已入卷证据不能删除")
    data = item.data or {}
    clue_id = _optional_record_id(data.get("clue_id") or data.get("clue_record_id"))
    clue = await db.get(BusinessRecord, clue_id) if clue_id else None
    attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id == item.id))).all())
    paths = [Path(attachment.path) for attachment in attachments]
    for attachment in attachments:
        await db.delete(attachment)
    canonical = await db.scalar(select(InvestigationEvidence).where(InvestigationEvidence.record_id == item.id))
    if canonical:
        await db.delete(canonical)
    await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == item.id))
    if clue and clue.module == "clue":
        clue_data = dict(clue.data or {})
        clue_data["evidence_ids"] = [
            record_id
            for value in clue_data.get("evidence_ids") or []
            if (record_id := _optional_record_id(value)) and record_id != item.id
        ]
        clue_data["evidence_count"] = len(clue_data["evidence_ids"])
        if _optional_record_id(clue_data.get("collection_evidence_record_id")) == item.id:
            clue_data.pop("collection_evidence_record_id", None)
        clue.data = clue_data
        db.add(WorkflowEvent(record_id=clue.id, action="删除取证信息", from_status=clue.status, to_status=clue.status, operator=identity["username"], comment=f"删除证据记录 {item.serial_no}"))
    await db.delete(item)
    await db.commit()
    for path in paths:
        if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
            path.unlink()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/investigations/{{record_id}}/parties")
async def list_investigation_parties(record_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_visible,
    )
    from app.core.system import (
        _record_dict,
    )
    record = await _ensure_record_visible(record_id, identity, db)
    if record.module not in INVESTIGATION_RECORD_MODULES:
        raise HTTPException(status_code=404, detail="调查业务记录不存在")
    data = record.data or {}
    return {"record": _record_dict(record), "producers": data.get("producers", []), "indictees": data.get("indictees", [])}


@router.post(f"{settings.api_prefix}/investigations/{{record_id}}/parties")
async def update_investigation_parties(record_id: int, body: InvestigationPartyInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_visible, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _record_dict,
    )
    record = await _ensure_record_visible(record_id, identity, db)
    if record.module not in INVESTIGATION_RECORD_MODULES:
        raise HTTPException(status_code=404, detail="调查业务记录不存在")
    await _require_record_owner_or_manager(record, identity, db)
    data = dict(record.data or {})
    data["producers"] = body.producers
    data["indictees"] = body.indictees
    if body.producers and isinstance(body.producers[0], dict):
        data["producer"] = str(body.producers[0].get("name") or body.producers[0].get("producer") or "")
    if body.indictees and isinstance(body.indictees[0], dict):
        data["indictee"] = str(body.indictees[0].get("name") or body.indictees[0].get("indictee") or "")
    record.data = data
    db.add(WorkflowEvent(record_id=record.id, action="更新调查主体", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"生产商 {len(body.producers)} 条；被调查主体 {len(body.indictees)} 条"))
    await db.commit(); await db.refresh(record)
    return {"record": _record_dict(record), "producers": body.producers, "indictees": body.indictees}


@router.post(f"{settings.api_prefix}/investigations/{{record_id}}/assign")
async def assign_investigation_record(record_id: int, body: InvestigationAssignmentInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_visible, _require_record_owner_or_manager, _require_task_owner_or_initiator,
    )
    from app.core.system import (
        _record_dict,
    )
    from app.core.tasks import (
        _active_task_username, _add_task_message_notifications, _task_dict,
    )
    record = await _ensure_record_visible(record_id, identity, db)
    if record.module not in {"investigation", "clue", "task"}:
        raise HTTPException(status_code=422, detail="仅调查授权、调查线索或调查任务可以分配调查员")
    if record.module == "task":
        _require_task_owner_or_initiator(record, identity, action="修改任务负责人")
    else:
        await _require_record_owner_or_manager(record, identity, db)
    if record.module == "clue" and record.status in {"已转案件"}:
        raise HTTPException(status_code=409, detail="已转案件线索不能更换调查员")
    if record.module == "task" and record.status in {"已完成", "待确认", "已验收", "已拒绝", "已撤回", "已停止", "已取消"}:
        raise HTTPException(status_code=409, detail="已结束任务不能更换调查员")
    if record.module == "investigation" and record.status in {"已完成", "已取消"}:
        raise HTTPException(status_code=409, detail="已结束调查授权不能更换调查员")
    previous_owner = record.owner
    record.owner = await _active_task_username(body.investigator, db, field_name="调查员")
    record.data = {**(record.data or {}), "investigator": record.owner, "assigner": identity["username"], "assigned_at": datetime.now().isoformat(timespec="seconds"), "assigned_by": identity["username"]}
    if record.module == "investigation" and record.status == "待分配": record.status = "进行中"
    assignment_event = WorkflowEvent(record_id=record.id, action="分配调查员", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{previous_owner} → {record.owner}。{body.comment}")
    if record.module == "task":
        await _add_task_message_notifications(record, assignment_event, db, content="任务负责人已修改.")
    else:
        db.add(assignment_event)
    await db.commit(); await db.refresh(record)
    return _record_dict(record) if record.module != "task" else _task_dict(record)


@router.post(f"{settings.api_prefix}/investigations/clues/{{record_id}}/fee-application", status_code=status.HTTP_201_CREATED)
async def create_investigation_fee_application(record_id: int, body: InvestigationFeeInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _record_dict,
    )
    clue = await _ensure_record_module(record_id, "clue", identity, db); await _require_record_owner_or_manager(clue, identity, db)
    if clue.status not in {"已取证", "待公证", "已转案件"}:
        raise HTTPException(status_code=409, detail="线索完成取证后才能申请费用")
    if (clue.data or {}).get("fee_application_id"):
        raise HTTPException(status_code=409, detail="该线索已经提交过费用申请")
    serial_no = f"FY{datetime.now():%Y%m%d%H%M%S%f}"; fee = BusinessRecord(module="finance", serial_no=serial_no, title=f"调查费用—{clue.title}", customer=clue.customer, status="草稿", owner=identity["username"], department=clue.department, description=body.description, data={"fee_type": body.fee_type, "amount": body.amount, "clue_id": clue.id, "clue_no": clue.serial_no, "investigator": clue.owner, "source": "调查线索费用申请"})
    db.add(fee); await db.flush(); clue.data = {**(clue.data or {}), "fee_application_id": fee.id, "fee_no": serial_no, "fee_amount": body.amount, "fee_type": body.fee_type}
    db.add_all([WorkflowEvent(record_id=clue.id, action="申请调查费用", from_status=clue.status, to_status=clue.status, operator=identity["username"], comment=f"{serial_no}，{body.fee_type}，{body.amount:.2f}"), WorkflowEvent(record_id=fee.id, action="由调查线索生成费用申请", to_status="草稿", operator=identity["username"], comment=clue.serial_no)])
    await db.commit(); await db.refresh(fee); await db.refresh(clue)
    return {"fee": _record_dict(fee), "clue": _record_dict(clue)}


@router.post(f"{settings.api_prefix}/investigations/batch-delete")
async def batch_delete_investigation_records(body: InvestigationBatchDeleteInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _identity_role_ids, _record_scope_conditions,
    )
    from app.core.tasks import (
        _delete_task_notifications,
    )
    records = (await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(set(body.record_ids)), BusinessRecord.module.in_(["investigation", "clue", "task"]), *(await _record_scope_conditions(identity, db))))).all()
    found = {item.id: item for item in records}; errors: list[dict] = []; deleted = 0; paths: list[Path] = []
    role_ids = set(_identity_role_ids(identity))
    manager = bool(role_ids.intersection({"admin", "manager"}))
    for record_id in dict.fromkeys(body.record_ids):
        record = found.get(record_id)
        if not record:
            errors.append({"record_id": record_id, "error": "记录不存在或无权访问"}); continue
        if record.module == "investigation":
            publisher = str((record.data or {}).get("publisher") or "").strip().lower()
            legacy_owner_is_publisher = not publisher and str(record.owner or "").strip().lower() == identity["username"].lower()
            if "admin" not in role_ids and publisher != identity["username"].lower() and not legacy_owner_is_publisher:
                errors.append({"record_id": record_id, "record_no": record.serial_no, "error": "只能删除本人发布的调查任务"}); continue
        if record.module == "task" and "admin" not in role_ids and record.owner != identity["username"] and (record.data or {}).get("initiator") != identity["username"]:
            errors.append({"record_id": record_id, "record_no": record.serial_no, "error": "只能删除本人负责或发起的任务"}); continue
        if record.module not in {"task", "investigation"} and not manager and record.owner != identity["username"]:
            errors.append({"record_id": record_id, "record_no": record.serial_no, "error": "只能删除本人负责的记录"}); continue
        allowed = record.status in ({"草稿", "已驳回"} if record.module == "clue" else {"待接收", "未开始", "已驳回"} if record.module == "task" else {"待分配"})
        if not allowed:
            errors.append({"record_id": record_id, "record_no": record.serial_no, "error": f"当前状态“{record.status}”不允许删除"}); continue
        if record.module == "clue":
            related = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.module.in_(["notary", "case"]), BusinessRecord.data["clue_id"].as_integer() == record.id))
            if related:
                errors.append({"record_id": record_id, "record_no": record.serial_no, "error": "已关联公证或案件，不能删除"}); continue
        elif record.module == "task":
            child = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.module == "task", BusinessRecord.data["parent_task_id"].as_integer() == record.id))
            if child:
                errors.append({"record_id": record_id, "record_no": record.serial_no, "error": "任务存在子任务，不能删除"}); continue
            linked_clue = await db.scalar(
                select(InvestigationClueLink.clue_record_id).where(
                    InvestigationClueLink.task_record_id == record.id,
                )
            )
            if linked_clue:
                errors.append({"record_id": record_id, "record_no": record.serial_no, "error": "任务已有调查线索，不能删除"}); continue
        else:
            child = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.module == "task", BusinessRecord.data["investigation_record_id"].as_integer() == record.id))
            if child:
                errors.append({"record_id": record_id, "record_no": record.serial_no, "error": "调查任务存在子任务，不能删除"}); continue
        attachments = (await db.scalars(select(FileAttachment).where(FileAttachment.record_id == record.id))).all()
        for attachment in attachments:
            paths.append(Path(attachment.path)); await db.delete(attachment)
        if record.module == "task":
            await _delete_task_notifications(record.id, db)
        await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == record.id)); await db.delete(record); deleted += 1
    await db.commit()
    for path in paths:
        if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents: path.unlink(missing_ok=True)
    return {"deleted": deleted, "failed": len(errors), "errors": errors}


@router.get(f"{settings.api_prefix}/investigations/{{record_id}}/tasks")
async def list_investigation_tasks(record_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _task_display_dict,
    )
    from app.core.investigation import (
        _resolve_investigation_task_root,
    )
    from app.core.permissions import (
        _ensure_record_visible, _record_scope_conditions,
    )
    from app.core.system import (
        _record_dict,
    )
    source = await _ensure_record_visible(record_id, identity, db)
    if source.module not in INVESTIGATION_MATERIAL_CATEGORIES:
        raise HTTPException(status_code=404, detail="调查业务记录不存在")
    root = await _resolve_investigation_task_root(source, identity, db)
    root_data = root.data or {}
    can_view_all_children = (
        identity.get("role") == "admin"
        or root.owner == identity["username"]
        or str(root_data.get("publisher") or "").lower() == identity["username"].lower()
    )
    task_scope = [] if can_view_all_children else await _record_scope_conditions(identity, db)
    tasks = (
        await db.scalars(
            select(BusinessRecord)
            .where(
                BusinessRecord.module == "task",
                BusinessRecord.data["investigation_record_id"].as_integer() == root.id,
                *task_scope,
            )
            .order_by(BusinessRecord.created_at, BusinessRecord.id)
        )
    ).all()
    return {"record": _record_dict(root), "items": [await _task_display_dict(item, db) for item in tasks], "total": len(tasks)}


@router.post(f"{settings.api_prefix}/investigations/{{record_id}}/close")
async def close_investigation(record_id: int, body: TaskActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    from app.core.storage import (
        _attachment_dict, _docx_bytes,
    )
    from app.core.system import (
        _record_dict,
    )
    investigation = await _ensure_record_module(record_id, "investigation", identity, db)
    await _require_record_owner_or_manager(investigation, identity, db)
    if investigation.status in {"已完成", "已取消"}: raise HTTPException(status_code=409, detail="调查任务已经结束")
    tasks = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "task", BusinessRecord.data["investigation_record_id"].as_integer() == investigation.id))).all())
    active_tasks = [item for item in tasks if item.status not in {"已完成", "已验收", "已拒绝", "已撤回", "已停止", "已取消"}]
    if active_tasks: raise HTTPException(status_code=409, detail=f"仍有 {len(active_tasks)} 个调查子任务未办结")
    task_ids = [item.id for item in tasks]
    clues = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "clue", BusinessRecord.data["source_task_id"].as_integer().in_(task_ids)))).all()) if task_ids else []
    active_clues = [item for item in clues if item.status not in {"已转案件", "已驳回"}]
    if active_clues: raise HTTPException(status_code=409, detail=f"仍有 {len(active_clues)} 条调查线索未转案或未驳回")
    previous = investigation.status; investigation.status = "已完成"
    report_content = "\n".join([
        f"调查任务：{investigation.serial_no}｜{investigation.title}", f"客户：{investigation.customer}",
        f"负责人：{investigation.owner}", f"调查子任务：{len(tasks)} 个", f"调查线索：{len(clues)} 条",
        f"已转案件线索：{sum(1 for item in clues if item.status == '已转案件')} 条", f"驳回线索：{sum(1 for item in clues if item.status == '已驳回')} 条",
        f"关闭说明：{body.comment.strip() or '全部调查事项已经办结'}",
    ])
    content = _docx_bytes(f"调查任务报告-{investigation.serial_no}", report_content)
    stored_name = f"{uuid4().hex}.docx"; path = UPLOAD_ROOT / stored_name; path.write_bytes(content)
    attachment = FileAttachment(record_id=investigation.id, category="调查任务报告", original_name=f"调查任务报告-{investigation.serial_no}.docx", stored_name=stored_name, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", size=len(content), path=str(path), uploader=identity["username"], remark="调查任务关闭时由系统生成")
    db.add(attachment); await db.flush()
    investigation.data = {**(investigation.data or {}), "closed_at": datetime.now().isoformat(timespec="seconds"), "closed_by": identity["username"], "close_comment": body.comment.strip(), "report_attachment_id": attachment.id}
    db.add(WorkflowEvent(record_id=investigation.id, action="关闭调查任务并生成报告", from_status=previous, to_status="已完成", operator=identity["username"], comment=body.comment))
    await db.commit(); await db.refresh(investigation); await db.refresh(attachment)
    return {"record": _record_dict(investigation), "report": _attachment_dict(attachment, investigation)}


@router.post(f"{settings.api_prefix}/investigations/{{record_id}}/tasks", status_code=status.HTTP_201_CREATED)
async def create_investigation_task(record_id: int, body: InvestigationTaskInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.contracts import (
        _contract_allows_downstream_creation,
    )
    from app.core.formatters import (
        _investigation_task_date, _task_display_dict,
    )
    from app.core.investigation import (
        _investigation_authorization_expired, _resolve_investigation_task_root,
    )
    from app.core.legacy_sync import (
        _sync_legacy_projection,
    )
    from app.core.permissions import (
        _ensure_record_module, _ensure_record_visible, _require_record_owner_or_manager,
    )
    from app.core.tasks import (
        _active_task_username, _add_task_message_notifications, _next_rw_task_serial_no, _validate_task_deadline,
    )
    source = await _ensure_record_visible(record_id, identity, db)
    if source.module not in INVESTIGATION_MATERIAL_CATEGORIES:
        raise HTTPException(status_code=404, detail="调查业务记录不存在")
    await _require_record_owner_or_manager(source, identity, db)
    _validate_task_deadline(body.deadline)
    source = await _resolve_investigation_task_root(source, identity, db)
    source_data = source.data or {}
    is_legacy_investigation = bool(
        source_data.get("migration_source")
        or source_data.get("legacy_investigation_id")
        or source_data.get("legacy_record")
    )
    if _investigation_authorization_expired(source):
        raise HTTPException(status_code=409, detail="该任务已过期，不允许新建子任务")
    parent = None
    if body.parent_task_id:
        parent = await _ensure_record_module(body.parent_task_id, "task", identity, db)
        if int((parent.data or {}).get("investigation_record_id") or 0) != source.id:
            raise HTTPException(status_code=409, detail="父任务不属于当前调查事项")
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    owner = body.owner.strip()
    can_delegate = identity.get("role") in {"admin", "manager"}
    if identity.get("role") == "user":
        assignment_config = await db.scalar(select(SystemConfig).where(SystemConfig.key == "investigation_assignment"))
        configured_username = str((assignment_config.value or {}).get("supervisor_username") or "").strip() if assignment_config else ""
        can_delegate = configured_username.lower() == identity["username"].lower()
    if identity.get("role") == "user" and not can_delegate:
        owner = identity["username"]
    owner = await _active_task_username(owner, db, field_name="负责人")
    attachment_ids = list(dict.fromkeys(body.attachment_ids))
    if attachment_ids:
        referenced = {item.id: item for item in (await db.scalars(select(FileAttachment).where(FileAttachment.id.in_(attachment_ids)))).all()}
        for attachment_id in attachment_ids:
            attachment = referenced.get(attachment_id)
            if not attachment or attachment.record_id != source.id:
                raise HTTPException(status_code=422, detail="所选附件不属于当前调查事项")
    parent_data = parent.data or {} if parent else {}
    stored_source_contract_id = source_data.get("contract_id") or source_data.get("contract_record_id") or parent_data.get("contract_id") or parent_data.get("contract_record_id")
    source_contract_no = str(source_data.get("contract_no") or parent_data.get("contract_no") or "").strip()
    source_contract = None
    if stored_source_contract_id:
        candidate = await db.get(BusinessRecord, int(stored_source_contract_id))
        if (
            candidate
            and candidate.module == "contract"
            and candidate.customer.strip() == source.customer.strip()
            and (not source_contract_no or candidate.serial_no == source_contract_no)
        ):
            source_contract = candidate
    if not source_contract and source_contract_no:
        source_contract = await db.scalar(select(BusinessRecord).where(
            BusinessRecord.module == "contract",
            BusinessRecord.serial_no == source_contract_no,
            BusinessRecord.customer == source.customer,
        ))
    source_contract_id = source_contract.id if source_contract else None
    requested_contract_id = body.contract_record_id
    if source_contract_id and requested_contract_id and int(source_contract_id) != requested_contract_id:
        raise HTTPException(status_code=409, detail="调查事项已绑定合同，不能在创建子任务时更换合同")
    if not source_contract_id and not requested_contract_id and not is_legacy_investigation:
        raise HTTPException(status_code=422, detail="创建调查任务前必须绑定同客户合同")
    if source_contract_id:
        contract = source_contract
    elif requested_contract_id:
        contract = await _ensure_record_visible(int(requested_contract_id), identity, db)
    else:
        contract = None
    if contract and not _contract_allows_downstream_creation(contract):
        raise HTTPException(status_code=409, detail="草稿合同不能创建调查子任务")
    if contract and source.customer.strip() != contract.customer.strip():
        raise HTTPException(status_code=422, detail="所选合同客户必须与调查事项客户一致")
    relation_needs_repair = bool(
        contract
        and (
            not source_contract_id
            or int(stored_source_contract_id or 0) != contract.id
            or source_data.get("contract_record_id") != contract.id
            or source_data.get("contract_no") != contract.serial_no
        )
    )
    if contract and (not source_contract_id or relation_needs_repair):
        source.data = {**source_data, "contract_id": contract.id, "contract_record_id": contract.id, "contract_no": contract.serial_no, "contract_name": contract.title}
        db.add(source)
        db.add(WorkflowEvent(record_id=source.id, action="修复调查事项合同关联" if stored_source_contract_id else "绑定调查事项合同", from_status=source.status, to_status=source.status, operator=identity["username"], comment=f"绑定客户 {contract.customer} / 合同 {contract.serial_no}"))
    start_date = body.start_date or _investigation_task_date(parent_data.get("start_date") or parent_data.get("authorized_from")) or _investigation_task_date(source_data.get("authorized_from"))
    end_date = body.end_date or body.deadline or _investigation_task_date(parent_data.get("end_date") or parent_data.get("deadline") or parent_data.get("authorized_to")) or _investigation_task_date(source_data.get("authorized_to"))
    authorized_from = _investigation_task_date(parent_data.get("authorized_from")) or _investigation_task_date(source_data.get("authorized_from")) or start_date
    authorized_to = _investigation_task_date(parent_data.get("authorized_to")) or _investigation_task_date(source_data.get("authorized_to")) or end_date
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="调查结束时间必须不早于开始时间")
    parent_or_source = parent_data or source_data
    requested_province = body.province.strip()
    requested_city = body.city.strip()
    requested_district = body.district.strip()
    requested_scope = body.authorization_scope.strip()
    province = requested_province or str(parent_or_source.get("province") or "").strip()
    city = requested_city or str(parent_or_source.get("city") or "").strip()
    district = requested_district or str(parent_or_source.get("district") or "").strip()
    # Authorization scope and investigation area are different fields.  When
    # the form carries a concrete province/city selection, keep that selection
    # as the task area even if the authorization scope is 全国; only fall back
    # to the scope label when no concrete area was supplied.
    if any((requested_province, requested_city, requested_district)):
        region = " ".join(part for part in (requested_province, requested_city, requested_district) if part)
    elif requested_scope:
        region = requested_scope
    else:
        region = str(parent_or_source.get("region") or parent_or_source.get("address") or "").strip()
        if not region:
            region = " ".join(part for part in (province, city, district) if part)
    task_data = {
        "deadline": str(end_date or body.deadline), "priority": body.priority, "source": "调查任务",
        "initiator": identity["username"], "collaborators": [], "case_no": "",
        "contract_id": contract.id if contract else None,
        "contract_record_id": contract.id if contract else None,
        "contract_no": contract.serial_no if contract else "",
        "contract_name": contract.title if contract else "",
        "authorization_scope": requested_scope or str(parent_or_source.get("authorization_scope") or ""),
        "authorization_scope_type": parent_or_source.get("authorization_scope_type", ""),
        "authorization_regions": parent_or_source.get("authorization_regions", []),
        "attachment_ids": attachment_ids,
        "investigation_record_id": source.id, "investigation_no": source.serial_no,
        "investigation_module": source.module,
        "customer_review": bool(source_data.get("customer_review")),
        "right_type": str(source_data.get("right_type") or ""),
        "region": region, "province": province, "city": city, "district": district,
        "start_date": str(start_date or ""), "end_date": str(end_date or ""),
        "authorized_from": str(authorized_from or ""), "authorized_to": str(authorized_to or ""),
        "source_owner": str(source_data.get("source_owner") or ""),
        "assigner": str(source_data.get("assigner") or source_data.get("assigned_by") or identity["username"]),
        "parent_task_id": parent.id if parent else None,
        "parent_task_no": parent.serial_no if parent else "",
    }
    serial_no = await _next_rw_task_serial_no(db)
    task = BusinessRecord(module="task", serial_no=serial_no, title=body.title.strip(), customer=source.customer, status="待接收", owner=owner, department=user.department if user else source.department, description=body.description, data=task_data)
    db.add(task); await db.flush()
    db.add(WorkflowEvent(record_id=source.id, action="创建调查任务", from_status=source.status, to_status=source.status, operator=identity["username"], comment=f"{serial_no}：{body.title}"))
    await _add_task_message_notifications(task, WorkflowEvent(record_id=task.id, action="创建调查任务", to_status="待接收", operator=identity["username"], comment=f"来源 {source.serial_no}" + (f"；父任务 {parent.serial_no}" if parent else "")), db, content="任务已分派")
    await _sync_legacy_projection(source, identity, db)
    await _sync_legacy_projection(task, identity, db)
    await db.commit(); await db.refresh(task); return await _task_display_dict(task, db)


@router.post(f"{settings.api_prefix}/investigations/clues/case-contracts")
async def resolve_clue_case_contracts(body: ClueCaseContractResolveInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.contracts import (
        _resolve_clue_source_contract,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    clues = {item.id: item for item in (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "clue", BusinessRecord.id.in_(set(body.clue_ids)), *(await _record_scope_conditions(identity, db))))).all()}
    items = []
    for clue_id in dict.fromkeys(body.clue_ids):
        clue = clues.get(clue_id)
        if not clue:
            items.append({"clue_id": clue_id, "error": "线索不存在"}); continue
        contract, error = await _resolve_clue_source_contract(clue, identity, db)
        items.append({"clue_id": clue.id, "clue_no": clue.serial_no, "clue_title": clue.title, "customer": clue.customer, "contract": {"id": contract.id, "serial_no": contract.serial_no, "title": contract.title, "customer": contract.customer, "status": contract.status} if contract else None, "error": error})
    return {"items": items}


@router.post(f"{settings.api_prefix}/investigations/clues/{{clue_id}}/bind-source-contract")
async def bind_clue_source_contract(clue_id: int, body: ClueSourceContractBindingInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """One-time repair for legacy tasks created without a contract binding.

    The selected contract binds to the *source task*, then every still-open clue
    from that task inherits the same customer and stable contract identifiers.
    It is deliberately not a contract picker on the case-generation command.
    """
    from app.core.contracts import (
        _contract_allows_downstream_creation, _resolve_clue_source_contract,
    )
    from app.core.permissions import (
        _ensure_record_module, _ensure_record_visible, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _record_dict,
    )
    clue = await _ensure_record_module(clue_id, "clue", identity, db)
    await _require_record_owner_or_manager(clue, identity, db)
    if clue.status == "已转案件" or (clue.data or {}).get("converted_case_id"):
        raise HTTPException(status_code=409, detail="已转案件的线索不能补绑来源任务合同")
    try:
        source_task_id = int((clue.data or {}).get("source_task_id") or 0)
    except (TypeError, ValueError):
        source_task_id = 0
    if not source_task_id:
        raise HTTPException(status_code=422, detail="线索缺少来源调查任务，无法补绑合同")
    source_task = await _ensure_record_visible(source_task_id, identity, db)
    if source_task.module not in {"task", "investigation"}:
        raise HTTPException(status_code=422, detail="线索来源不是可绑定合同的调查任务")
    existing_contract, _ = await _resolve_clue_source_contract(clue, identity, db)
    if existing_contract:
        raise HTTPException(status_code=409, detail=f"来源调查任务已绑定合同 {existing_contract.serial_no}")
    contract = await _ensure_record_visible(body.contract_record_id, identity, db)
    if not _contract_allows_downstream_creation(contract):
        raise HTTPException(status_code=409, detail="草稿合同不能创建调查子任务")
    contract_data = {"contract_id": contract.id, "contract_record_id": contract.id, "contract_no": contract.serial_no, "contract_name": contract.title}
    source_task.customer = contract.customer
    source_task.data = {**(source_task.data or {}), **contract_data}
    db.add(source_task)
    related_clues = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "clue", BusinessRecord.data["source_task_id"].as_integer() == source_task.id))).all())
    for related in related_clues:
        if related.status == "已转案件" or (related.data or {}).get("converted_case_id"):
            continue
        related.customer = contract.customer
        related.data = {**(related.data or {}), **contract_data}
        db.add(related)
    try:
        investigation_id = int((source_task.data or {}).get("investigation_record_id") or 0)
    except (TypeError, ValueError):
        investigation_id = 0
    if investigation_id:
        investigation = await db.get(BusinessRecord, investigation_id)
        if investigation and investigation.module == "investigation":
            investigation.customer = contract.customer
            investigation.data = {**(investigation.data or {}), **contract_data}
            db.add(investigation)
    db.add(WorkflowEvent(record_id=source_task.id, action="补绑来源任务合同", from_status=source_task.status, to_status=source_task.status, operator=identity["username"], comment=f"绑定客户 {contract.customer} / 合同 {contract.serial_no}；同步 {len(related_clues)} 条未转案线索"))
    await db.commit()
    await db.refresh(clue)
    return {"clue": _record_dict(clue), "contract": {"id": contract.id, "serial_no": contract.serial_no, "title": contract.title, "customer": contract.customer}}


@router.post(f"{settings.api_prefix}/investigations/clues/batch-cases", status_code=status.HTTP_201_CREATED)
async def batch_create_cases_from_clues(body: BatchClueCaseInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_team_payload, _next_case_serial, _resolve_active_case_people,
    )
    from app.core.contracts import (
        _contract_allows_downstream_creation, _resolve_clue_source_contract,
    )
    from app.core.crm import (
        _persist_case_litigant_customers,
    )
    from app.core.permissions import (
        _ensure_case_fixed_tasks, _record_scope_conditions,
    )
    clues = {item.id: item for item in (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "clue", BusinessRecord.id.in_(set(body.clue_ids)), *(await _record_scope_conditions(identity, db))))).all()}
    created_ids: list[int] = []; errors: list[dict] = []
    for clue_id in dict.fromkeys(body.clue_ids):
        clue = clues.get(clue_id)
        if not clue: errors.append({"clue_id": clue_id, "error": "线索不存在"}); continue
        clue_data = dict(clue.data or {})
        if clue_data.get("converted_case_id") or clue.status == "已转案件": errors.append({"clue_id": clue_id, "clue_no": clue.serial_no, "error": "线索已经转为案件"}); continue
        if clue.status not in {"已取证", "待公证"}: errors.append({"clue_id": clue_id, "clue_no": clue.serial_no, "error": "线索完成取证登记后才能转案件"}); continue
        contract, contract_error = await _resolve_clue_source_contract(clue, identity, db)
        if contract and not _contract_allows_downstream_creation(contract):
            errors.append({"clue_id": clue_id, "clue_no": clue.serial_no, "error": "来源任务关联合同状态不支持生成案件"}); continue
        contract_data = (contract.data or {}) if contract else {}
        case_customer = contract.customer if contract else clue.customer
        case_department = contract.department if contract else clue.department
        contract_reference = contract.serial_no if contract else "未关联合同"
        requested_handling_lawyer = body.handling_lawyer.strip()
        if requested_handling_lawyer:
            handling_lawyers, handling_usernames = await _resolve_active_case_people(
                [requested_handling_lawyer], db, field_name="经办律师",
            )
        else:
            handling_lawyers = list(dict.fromkeys(filter(None, clue_data.get("handling_lawyers") or [])))
            handling_usernames = list(dict.fromkeys(filter(None, clue_data.get("handling_lawyer_usernames") or [])))
        requested_assistant = body.assistant.strip()
        if requested_assistant:
            assistant_values, assistant_usernames = await _resolve_active_case_people(
                [requested_assistant], db, field_name="律师助理",
            )
            assistant = assistant_values[0]
            assistant_username = assistant_usernames[0]
        else:
            assistant = str(clue_data.get("assistant") or "").strip()
            assistant_username = str(clue_data.get("assistant_username") or "").strip()
        cause_or_charge = body.cause_or_charge.strip() or clue_data.get("cause_or_charge") or clue_data.get("cause", "")
        missing_case_fields = [
            label for label, value in (
                ("案由", cause_or_charge),
                ("经办律师", handling_lawyers),
                ("律师助理", assistant),
            ) if not value
        ]
        if missing_case_fields:
            errors.append({"clue_id": clue_id, "clue_no": clue.serial_no, "error": f"生成案件前请填写{'、'.join(missing_case_fields)}"})
            continue
        serial_no = await _next_case_serial(body.case_type, db)
        case_title = "".join(filter(None, [case_customer, cause_or_charge, clue.title]))
        case_register_date = str(date.today())
        case_data = _case_team_payload(
            {"contract_id": contract.id if contract else None, "contract_no": contract.serial_no if contract else "", "external_contract_no": contract_data.get("external_contract_no", ""), "external_contract_numbers": contract_data.get("external_contract_numbers", []), "contract_title": contract.title if contract else "", "clue_id": clue.id, "clue_record_id": clue.id, "investigation_clue_id": clue.id, "investigation_clue_ids": [clue.id], "clue_no": clue.serial_no, "investigation_clue": clue.serial_no, "investigation_clue_nos": [clue.serial_no], "notary_id": clue_data.get("notary_record_id"), "case_type": body.case_type, "court": body.court, "client_position": body.client_position.strip() or clue_data.get("client_position", "原告"), "cause_or_charge": cause_or_charge, "cause_of_action": cause_or_charge, "investigator": clue_data.get("investigator") or clue.owner, "opponent": clue_data.get("opponent", ""), "product": clue_data.get("product", ""), "case_register_date": case_register_date, "filing_date": case_register_date, "batch_converted": True, "case_creation_step": "completed", "case_creation_approval_status": "自动通过", "case_creation_approved_by": "system"},
            handling_lawyers,
            handling_usernames,
            assistant,
            assistant_username,
        )
        case_record = BusinessRecord(module="case", serial_no=serial_no, title=case_title or clue.title, customer=case_customer, status=body.case_phase.strip() or "等待公证书", owner=clue.owner, department=case_department, description=f"由已取证线索 {clue.serial_no} 自动转案", data=case_data)
        db.add(case_record); await db.flush()
        await _persist_case_litigant_customers(
            case_record,
            {"对方当事人": [str(clue_data.get("opponent") or "").strip()] if str(clue_data.get("opponent") or "").strip() else []},
            identity,
            db,
        )
        previous = clue.status; clue.status = "已转案件"; clue.data = {**clue_data, "converted_case_id": case_record.id, "converted_case_no": serial_no}
        notary = await db.get(BusinessRecord, int(clue_data.get("notary_record_id") or 0)) if clue_data.get("notary_record_id") else None
        if notary: notary.data = {**(notary.data or {}), "case_id": case_record.id, "case_no": serial_no}
        case_fields_comment = f"案由 {cause_or_charge or '未填写'} / 经办律师 {'、'.join(handling_lawyers) or '未填写'} / 律师助理 {assistant or '未填写'}"
        db.add_all([WorkflowEvent(record_id=clue.id, action="已取证线索生成案件", from_status=previous, to_status="已转案件", operator=identity["username"], comment=f"来源任务合同 {contract_reference}，生成案件 {serial_no}；{case_fields_comment}"), WorkflowEvent(record_id=case_record.id, action="线索生成案件", to_status=case_record.status, operator=identity["username"], comment=f"来源线索 {clue.serial_no} / 来源任务合同 {contract_reference}；{case_fields_comment}")])
        await _ensure_case_fixed_tasks(case_record, db, operator="system")
        created_ids.append(case_record.id)
    await db.commit()
    return {"created": len(created_ids), "created_ids": created_ids, "failed": len(errors), "errors": errors}


@router.get(f"{settings.api_prefix}/investigations/{{record_id}}/materials")
async def list_investigation_materials(record_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_visible,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    from app.core.system import (
        _record_dict,
    )
    record = await _ensure_record_visible(record_id, identity, db)
    if not record or record.module not in INVESTIGATION_MATERIAL_CATEGORIES:
        raise HTTPException(status_code=404, detail="调查、公证或证据记录不存在")
    items = (await db.scalars(select(FileAttachment).where(FileAttachment.record_id == record.id).order_by(FileAttachment.created_at.desc(), FileAttachment.id.desc()))).all()
    return {"record": _record_dict(record), "allowed_categories": INVESTIGATION_MATERIAL_CATEGORIES[record.module], "items": [_attachment_dict(x, record) for x in items], "total": len(items)}


@router.post(f"{settings.api_prefix}/investigations/{{clue_id}}/notary", status_code=status.HTTP_201_CREATED)
async def create_notary_from_clue(clue_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _record_dict,
    )
    clue = await _ensure_record_module(clue_id, "clue", identity, db)
    await _require_record_owner_or_manager(clue, identity, db)
    if clue.status not in {"已取证", "已转案件"}: raise HTTPException(status_code=409, detail="线索完成取证登记后才能建立公证记录")
    clue_data = clue.data or {}
    if clue_data.get("notary_record_id"):
        existing = await db.get(BusinessRecord, int(clue_data["notary_record_id"]))
        if existing:
            raise HTTPException(status_code=409, detail=f"该线索已生成公证记录 {existing.serial_no}")
    serial = f"GZ{datetime.now():%Y%m%d%H%M%S%f}"
    notary = BusinessRecord(
        module="notary", serial_no=serial, title=f"{clue.title}—公证审核",
        customer=clue.customer, status="等待材料", owner=clue.owner, department=clue.department,
        description="由调查线索自动生成",
        data={"clue_id": clue.id, "clue_no": clue.serial_no, "platform": clue_data.get("platform", ""), "product": clue_data.get("product", ""), "case_id": clue_data.get("converted_case_id"), "case_no": clue_data.get("converted_case_no", "")},
    )
    db.add(notary)
    await db.flush()
    previous_status = clue.status
    clue.status = "已转案件" if clue_data.get("converted_case_id") else "待公证"
    clue.data = {**clue_data, "notary": "等待公证书扫描件", "notary_record_id": notary.id}
    db.add_all([
        WorkflowEvent(record_id=clue.id, action="建立公证记录", from_status=previous_status, to_status=clue.status, operator=identity["username"], comment=f"生成公证记录 {serial}"),
        WorkflowEvent(record_id=notary.id, action="创建公证材料记录", to_status="等待材料", operator=identity["username"], comment=f"来源线索 {clue.serial_no}，等待上传公证书扫描件"),
    ])
    await db.commit()
    await db.refresh(notary)
    return _record_dict(notary)
