"""通用业务记录 CSV 导入。"""
from dataclasses import dataclass

from fastapi import APIRouter
from app.core.constants import RECORD_IMPORT_COLUMNS, RECORD_IMPORT_SAMPLES
from app.core.dependencies import AsyncSession, BusinessRecord, Depends, File, HTTPException, Query, Response, SealAsset, UploadFile, User, WorkflowEvent, csv, current_identity, date, datetime, get_db, io, or_, re, select, settings

router = APIRouter()


@dataclass(frozen=True)
class _ImportReference:
    id: int
    module: str
    serial_no: str
    title: str
    customer: str
    data: dict


async def _load_import_references(
    db: AsyncSession, scope: list, tokens_by_module: dict[str, set[str]],
) -> dict[str, list[_ImportReference]]:
    references: dict[str, dict[int, _ImportReference]] = {
        name: {} for name in tokens_by_module
    }
    for name, tokens in tokens_by_module.items():
        ordered_tokens = sorted(tokens)
        for offset in range(0, len(ordered_tokens), 200):
            chunk = ordered_tokens[offset:offset + 200]
            rows = (await db.execute(select(
                BusinessRecord.id, BusinessRecord.module, BusinessRecord.serial_no,
                BusinessRecord.title, BusinessRecord.customer, BusinessRecord.data,
            ).where(
                BusinessRecord.module == name,
                or_(BusinessRecord.serial_no.in_(chunk), BusinessRecord.title.in_(chunk)),
                *scope,
            ))).all()
            for row in rows:
                reference = _ImportReference(*row)
                references[name][reference.id] = reference
    return {name: list(items.values()) for name, items in references.items()}


@router.get(f"{settings.api_prefix}/records/import-template")
async def records_import_template(module: str = Query(min_length=1, max_length=32), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_record_module_menu,
    )
    await _require_record_module_menu(module, identity, db, action="下载导入模板")
    if module == "case": raise HTTPException(status_code=409, detail="案件必须使用分阶段专用入口创建，不能使用通用导入模板")
    columns = RECORD_IMPORT_COLUMNS.get(module)
    if not columns: raise HTTPException(status_code=422, detail="该业务模块不支持批量导入")
    output = io.StringIO(); writer = csv.writer(output); writer.writerow(columns); writer.writerow(RECORD_IMPORT_SAMPLES[module])
    return Response(content=("\ufeff" + output.getvalue()).encode("utf-8"), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{module}-import-template.csv"'})

@router.post(f"{settings.api_prefix}/records/import")
async def import_business_records(module: str = Query(min_length=1, max_length=32), file: UploadFile = File(...), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _csv_date,
    )
    from app.core.permissions import (
        _record_scope_conditions, _require_record_module_menu,
    )
    from app.core.system import (
        _csv_value, _import_relation_data, _unique_import_record, _validate_import_relation_consistency,
    )
    from app.core.tasks import (
        _active_task_username, _validate_task_deadline,
    )
    if module == "conflict_review":
        raise HTTPException(status_code=409, detail="利益冲突审查必须使用专用入口办理")
    await _require_record_module_menu(module, identity, db, action="批量导入")
    if module not in RECORD_IMPORT_COLUMNS: raise HTTPException(status_code=422, detail="该业务模块不支持批量导入")
    if module == "case": raise HTTPException(status_code=409, detail="案件必须使用分阶段专用入口创建，不能通过通用导入绕过")
    if module in {"hr", "warehouse"} and identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="当前角色不能批量导入该模块")
    if not (file.filename or "").lower().endswith(".csv"): raise HTTPException(status_code=422, detail="仅支持 UTF-8 CSV 文件")
    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024: raise HTTPException(status_code=413, detail="导入文件不能超过 5MB")
    try: csv_text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc: raise HTTPException(status_code=422, detail="CSV 必须使用 UTF-8 编码") from exc
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames: raise HTTPException(status_code=422, detail="CSV 缺少表头")
    rows = list(reader)
    serials = {_csv_value(row, "业务编号", "员工编号", "物品编号", "申请编号", "serial_no") for row in rows}
    serials.discard("")
    existing = set((await db.scalars(select(BusinessRecord.serial_no).where(BusinessRecord.serial_no.in_(serials)))).all()) if serials else set()
    seen: set[str] = set(); errors: list[dict] = []; created_items: list[dict] = []
    scope = await _record_scope_conditions(identity, db)
    reference_columns = {
        "contract": ("关联合同号", "contract_no"),
        "case": ("关联案号", "case_no"),
        "investigation": ("调查编号", "investigation_no"),
        "task": ("调查任务编号", "task_no"),
        "clue": ("线索编号", "clue_no"),
        "evidence": ("取证编号", "evidence_no"),
    }
    tokens_by_module = {name: set() for name in ("customer", *reference_columns)}
    for row in rows:
        customer_token = _csv_value(row, "客户/主体", "customer")
        if customer_token and module not in {"hr", "warehouse"}:
            tokens_by_module["customer"].add(customer_token)
        customer_reference = _csv_value(row, "客户编号", "customer_no", default=customer_token if module not in {"hr", "warehouse"} else "")
        if customer_reference:
            tokens_by_module["customer"].add(customer_reference)
        for name, columns in reference_columns.items():
            token = _csv_value(row, *columns)
            if token:
                tokens_by_module[name].add(token)
    records_by_module = await _load_import_references(db, scope, tokens_by_module)
    if module in {"task", "document", "finance"}:
        derived_customers = {item.customer for item in records_by_module["case"] if item.customer}
        derived_customers -= tokens_by_module["customer"]
        if derived_customers:
            extra = await _load_import_references(db, scope, {"customer": derived_customers})
            by_id = {item.id: item for item in records_by_module["customer"]}
            by_id.update({item.id: item for item in extra["customer"]})
            records_by_module["customer"] = list(by_id.values())
    seal_codes = {_csv_value(row, "印章编号", "seal_code") for row in rows} if module == "seal" else set()
    seal_codes.discard("")
    seal_assets = {item.code: item for item in (await db.scalars(select(SealAsset).where(SealAsset.status == "可用", SealAsset.code.in_(seal_codes)))).all()} if seal_codes else {}
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    for row_no, row in enumerate(rows, 2):
        try:
            serial = _csv_value(row, "业务编号", "员工编号", "物品编号", "申请编号", "serial_no")
            title = _csv_value(row, "标题", "合同名称", "案件名称", "任务内容", "文件名称", "费用名称", "姓名", "物品名称", "申请标题", "title")
            if not serial or not title: raise ValueError("业务编号和名称不能为空")
            if serial in existing or serial in seen: raise ValueError(f"业务编号已存在：{serial}")
            owner = _csv_value(row, "负责人", "经办人", "owner", default=identity["username"])
            department = _csv_value(row, "部门", "department", default=(user.department if user else "上海分所"))
            if identity.get("role") != "admin":
                department = user.department if user else department
                if identity.get("role") == "user": owner = identity["username"]
            customer = _csv_value(row, "客户/主体", "customer")
            description = _csv_value(row, "说明", "description")
            data: dict = {"imported_at": datetime.now().isoformat(timespec="seconds"), "import_row": row_no}
            status_value = "草稿"
            if module == "contract":
                amount = float(_csv_value(row, "合同金额", "amount")); signed_at = _csv_date(_csv_value(row, "签订日期", "signed_at"), "签订日期")
                if amount < 0 or not customer: raise ValueError("客户不能为空，合同金额不能为负数")
                customer_record = _unique_import_record(records_by_module["customer"], customer, "关联客户")
                customer = customer_record.title
                data.update(_import_relation_data(customer=customer_record))
                data.update({"type": _csv_value(row, "合同类型", "type", default="专项服务"), "amount": f"{amount:.2f}", "signed_at": signed_at, "external_contract_no": _csv_value(row, "外部合同号", "external_contract_no")})
            elif module == "task":
                deadline = _csv_date(_csv_value(row, "截止日期", "deadline"), "截止日期")
                priority = _csv_value(row, "优先级", "priority", default="普通")
                if priority not in {"普通", "重要", "紧急"}: raise ValueError("任务优先级无效")
                try:
                    _validate_task_deadline(date.fromisoformat(deadline))
                    owner = await _active_task_username(owner, db, field_name="负责人")
                    collaborators = []
                    for value in [name.strip() for name in re.split(r"[、,，;；]", _csv_value(row, "协作人", "collaborators")) if name.strip()]:
                        collaborator = await _active_task_username(value, db, field_name="协作人")
                        if collaborator != owner and collaborator not in collaborators:
                            collaborators.append(collaborator)
                except HTTPException as exc:
                    raise ValueError(str(exc.detail)) from exc
                case_record = _unique_import_record(records_by_module["case"], _csv_value(row, "关联案号", "case_no"), "关联案件")
                if case_record:
                    customer = case_record.customer
                status_value = "待接收"; data.update(_import_relation_data(case=case_record)); data.update({"deadline": deadline, "priority": priority, "source": _csv_value(row, "来源", "source", default="日常任务"), "initiator": identity["username"], "collaborators": collaborators})
            elif module == "document":
                direction = _csv_value(row, "收发类型", "direction"); case_no = _csv_value(row, "关联案号", "case_no")
                if direction not in {"收文", "发文"}: raise ValueError("收发类型必须为收文或发文")
                case_record = _unique_import_record(records_by_module["case"], case_no, "关联案件")
                if case_record:
                    customer = case_record.customer
                status_value = "待登记"; data.update(_import_relation_data(case=case_record)); data.update({"direction": direction, "document_date": _csv_date(_csv_value(row, "文件日期", "document_date"), "文件日期"), "sender": _csv_value(row, "来文/送达单位", "sender")})
            elif module == "finance":
                amount = float(_csv_value(row, "金额", "amount")); case_no = _csv_value(row, "关联案号", "case_no")
                if amount <= 0: raise ValueError("费用金额必须大于 0")
                case_record = _unique_import_record(records_by_module["case"], case_no, "关联案件")
                if case_record:
                    customer = case_record.customer
                data.update(_import_relation_data(case=case_record)); data.update({"fee_type": _csv_value(row, "费用类型", "fee_type", default="官方费用"), "amount": f"{amount:.2f}", "handler": _csv_value(row, "经办人", "handler", default=owner)})
            elif module == "hr":
                position = _csv_value(row, "岗位", "position"); joined_at = _csv_date(_csv_value(row, "入职日期", "joined_at"), "入职日期")
                if not position: raise ValueError("岗位不能为空")
                requested_status = _csv_value(row, "状态", "status", default="试用"); status_value = "在职" if requested_status == "在职" else "试用"
                data.update({"position": position, "phone": _csv_value(row, "联系电话", "phone"), "joined_at": joined_at, "employment_type": _csv_value(row, "用工类型", "employment_type", default="全职"), "id_no": _csv_value(row, "证件号码", "id_no"), "email": _csv_value(row, "邮箱", "email")})
            elif module == "warehouse":
                quantity = int(_csv_value(row, "数量", "quantity")); category = _csv_value(row, "物品类别", "category"); location = _csv_value(row, "存放位置", "location")
                if quantity < 1 or not category or not location: raise ValueError("物品类别、数量和存放位置不能为空")
                customer = _csv_value(row, "供应商", "vendor"); status_value = "在库"; data.update({"category": category, "quantity": quantity, "unit": _csv_value(row, "单位", "unit", default="件"), "location": location, "vendor": customer, "borrower": "", "due_date": "", "borrow_purpose": ""})
            elif module == "seal":
                asset_code = _csv_value(row, "印章编号", "seal_code"); asset = seal_assets.get(asset_code); copies = int(_csv_value(row, "份数", "copies"))
                if not asset: raise ValueError("印章编号不存在或印章不可用")
                if copies < 1: raise ValueError("用印份数必须大于 0")
                data.update({"seal_asset_id": asset.id, "seal_name": asset.name, "seal_type": asset.seal_type, "copies": copies, "purpose": _csv_value(row, "用途", "purpose"), "use_date": _csv_date(_csv_value(row, "计划日期", "use_date"), "计划日期"), "delivery_method": _csv_value(row, "办理方式", "delivery_method", default="现场用印"), "document_names": _csv_value(row, "文件名称", "document_names")})
            relation_inputs = {
                "customer": _csv_value(row, "客户编号", "customer_no", default=customer if module not in {"warehouse", "hr"} else ""),
                "contract": _csv_value(row, "关联合同号", "contract_no"),
                "case": _csv_value(row, "关联案号", "case_no"),
                "investigation": _csv_value(row, "调查编号", "investigation_no"),
                "task": _csv_value(row, "调查任务编号", "task_no"),
                "clue": _csv_value(row, "线索编号", "clue_no"),
                "evidence": _csv_value(row, "取证编号", "evidence_no"),
            }
            resolved_relations = {
                name: _unique_import_record(records_by_module[name], value, f"关联{name}")
                for name, value in relation_inputs.items()
                if value
            }
            _validate_import_relation_consistency(resolved_relations)
            data.update(_import_relation_data(**resolved_relations))
            if customer_record := resolved_relations.get("customer"):
                customer = customer_record.title
            item = BusinessRecord(module=module, serial_no=serial, title=title, customer=customer, status=status_value, owner=owner, department=department, description=description, data=data)
            db.add(item); await db.flush(); db.add(WorkflowEvent(record_id=item.id, action="批量导入", to_status=item.status, operator=identity["username"], comment=f"CSV 第 {row_no} 行"))
            seen.add(serial); created_items.append({"id": item.id, "serial_no": serial, "title": title})
        except (ValueError, TypeError) as exc:
            errors.append({"row": row_no, "error": str(exc) or "字段格式错误", "value": _csv_value(row, "业务编号", "员工编号", "物品编号", "申请编号", "serial_no")})
    await db.commit()
    return {"module": module, "created": len(created_items), "failed": len(errors), "items": created_items, "errors": errors}
