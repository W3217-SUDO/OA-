"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.models_shared import ContractPaymentLineInput
from app.core.constants import (
    CONTRACT_APPROVED_STATUS, CONTRACT_PERSON_NAME_PLACEHOLDER, UPLOAD_ROOT, _contract_serial_lock, logger,
)
from app.core.dependencies import (
    AsyncSession, BusinessRecord, ContractApprovalStep, ContractEvent, ContractObject,
    ContractObjectLog, ContractPaymentLine, Depends, FileAttachment, FinanceTransaction,
    HTTPException, IncomingPayment, JSONResponse, Path, Query,
    ReceivablePlan, Response, SealAsset, User, WorkflowEvent,
    and_, current_identity, date, datetime, delete,
    false, func, get_db, json, or_,
    select, settings, status, timezone, uuid4,
)
from app.models_shared import (
    ContractApprovalInput, ContractApproverSettingsInput, ContractArchiveClosureInput, ContractAttachmentBatchDeleteInput, ContractChangeInput,
    ContractChangeReviewInput, ContractDraftInput, ContractEventInput, ContractInvestigationInput, ContractObjectInput,
    ContractPaymentApplicationInput, ContractPaymentPayInput, ContractPaymentReviewInput, ContractPaymentWriteoffInput, ContractSealApplicationInput,
    ContractSubmitInput, ContractWholeDeleteInput, FinancePaymentTypeCreateInput,
)
from fastapi import APIRouter

router = APIRouter()


@router.get(f"{settings.api_prefix}/contracts/approver-settings")
async def contract_approver_settings(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.contracts import (
        _valid_contract_person_name,
    )
    from app.core.permissions import (
        _require_admin,
    )
    _require_admin(identity)
    employees = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "hr",
    ).order_by(BusinessRecord.title, BusinessRecord.id))).all())
    usernames = list(dict.fromkeys(
        str((item.data or {}).get("username") or item.owner or "").strip().lower()
        for item in employees
        if str((item.data or {}).get("username") or item.owner or "").strip()
    ))
    users = list((await db.scalars(select(User).where(User.username.in_(usernames), User.is_active.is_(True)))).all()) if usernames else []
    by_username = {item.username: item for item in users}
    items = []
    seen_usernames: set[str] = set()
    for employee in employees:
        username = str((employee.data or {}).get("username") or employee.owner or "").strip().lower()
        user = by_username.get(username)
        if not user or username in seen_usernames:
            continue
        seen_usernames.add(username)
        display_name = _valid_contract_person_name(user.display_name, username)
        items.append({
            "username": username,
            "display_name": display_name or CONTRACT_PERSON_NAME_PLACEHOLDER,
            "display_name_valid": bool(display_name),
            "department": user.department or employee.department,
            "position": str((user.profile or {}).get("position") or (employee.data or {}).get("position") or ""),
            "selected": bool((user.profile or {}).get("contract_approval_enabled")),
        })
    return {"items": items}


@router.put(f"{settings.api_prefix}/contracts/approver-settings")
async def save_contract_approver_settings(body: ContractApproverSettingsInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.contracts import (
        _valid_contract_person_name,
    )
    from app.core.permissions import (
        _require_admin,
    )
    _require_admin(identity)
    requested = set(dict.fromkeys(value.strip().lower() for value in body.usernames if value.strip()))
    employees = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "hr",
    ))).all())
    eligible = {
        str((item.data or {}).get("username") or item.owner or "").strip().lower()
        for item in employees
        if str((item.data or {}).get("username") or item.owner or "").strip()
    }
    invalid = sorted(requested - eligible)
    if invalid:
        raise HTTPException(status_code=422, detail=f"所选人员没有关联员工档案：{', '.join(invalid)}")
    users = list((await db.scalars(select(User).where(User.username.in_(eligible)))).all()) if eligible else []
    active_usernames = {item.username for item in users if item.is_active}
    invalid = sorted(requested - active_usernames)
    if invalid:
        raise HTTPException(status_code=422, detail=f"所选人员账号不存在或已停用：{', '.join(invalid)}")
    users_by_username = {item.username: item for item in users}
    invalid_names = sorted(username for username in requested if not _valid_contract_person_name(users_by_username[username].display_name, username))
    if invalid_names:
        raise HTTPException(status_code=422, detail="所选员工缺少有效姓名，请先在人事中心维护姓名并取消其合同审批资格")
    for user in users:
        user.profile = {**(user.profile or {}), "contract_approval_enabled": user.username in requested}
    await db.commit()
    return {"usernames": sorted(requested), "count": len(requested)}


@router.get(f"{settings.api_prefix}/contracts/{{contract_id}}/export")
async def export_contract_detail_excel(
    contract_id: int,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Export exactly one visible contract as a SpreadsheetML workbook."""
    from app.core.permissions import (
        _record_scope_conditions, _require_record_module_menu,
    )
    from app.core.system import (
        _allowed_field_keys, _excel_response, _record_dict,
    )
    await _require_record_module_menu("contract", identity, db, action="导出")
    contract = await db.scalar(
        select(BusinessRecord).where(
            BusinessRecord.id == contract_id,
            BusinessRecord.module == "contract",
            *(await _record_scope_conditions(identity, db)),
        )
    )
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在或当前账号无权导出")

    visible = _record_dict(contract, await _allowed_field_keys(identity, db))
    headers = ["业务编号", "标题", "客户/主体", "状态", "负责人", "部门", "说明", "扩展数据", "创建时间", "更新时间"]
    row = [
        visible["serial_no"], visible["title"], visible["customer"], visible["status"],
        visible["owner"], visible["department"], visible["description"],
        json.dumps(visible.get("data") or {}, ensure_ascii=False), visible["created_at"], visible["updated_at"],
    ]
    filename = f'{contract.serial_no or contract.id}-合同详情.xls'
    return _excel_response(filename, headers, [row])


@router.post(f"{settings.api_prefix}/contracts", status_code=status.HTTP_201_CREATED)
async def create_contract_draft(body: ContractDraftInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.contracts import (
        _contract_customer_source_person, _next_contract_serial_no, _resolve_contract_customer,
    )
    from app.core.formatters import (
        _normalize_external_contract_numbers,
    )
    from app.core.legacy_sync import (
        _sync_legacy_projection,
    )
    from app.core.permissions import (
        _record_dict_for_identity, _require_contract_action,
    )
    await _require_contract_action(identity, db, "contract.application.create", "新建")
    data = _normalize_external_contract_numbers(dict(body.data or {}))
    if body.staff_id:
        staff = await db.get(BusinessRecord, body.staff_id)
        if not staff or staff.module != "hr" or staff.status in ("离职", "停用"):
            raise HTTPException(status_code=422, detail="员工档案不存在或已停用")
        staff_data = staff.data or {}
        data = {**data, "staff_id": staff.id, "staff_no": staff.serial_no, "staff_name": staff.title, "staff_username": str(staff_data.get("username") or staff.owner or "")}
    customer = await _resolve_contract_customer(body.customer, data, identity, db)
    customer_data = customer.data or {}
    duplicate_title = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.module == "contract", BusinessRecord.title == body.title.strip(), BusinessRecord.status.not_in({"已删除", "已归档"})))
    if duplicate_title:
        raise HTTPException(status_code=409, detail="合同名称已存在，不能新建同名合同")
    # GUID is a server-owned identity; never accept a client-supplied value.
    data = {
        **data,
        "contract_guid": str(uuid4()),
        "customer_id": customer.id,
        "customer_no": customer.serial_no,
        "customer_manager": "、".join(customer_data.get("customer_managers") or [customer.owner]),
        "source_person": _contract_customer_source_person(customer),
    }
    if float(data.get("amount") or 0) < 0:
        raise HTTPException(status_code=422, detail="合同金额不能小于零")
    owner = body.owner.strip()
    department = body.department.strip()
    if identity.get("role") != "admin":
        current_user = await db.scalar(select(User).where(User.username == identity["username"]));
        if not current_user: raise HTTPException(status_code=401, detail="当前用户不存在")
        department = current_user.department
        if identity.get("role") == "user": owner = identity["username"]
    async with _contract_serial_lock:
        serial_no = await _next_contract_serial_no(db)
        item = BusinessRecord(module="contract", serial_no=serial_no, title=body.title.strip(), customer=customer.title, status="草稿", owner=owner, department=department, description=body.description.strip(), data=data)
        db.add(item); await db.flush()
        db.add(WorkflowEvent(record_id=item.id, action="创建合同草稿", to_status="草稿", operator=identity["username"], comment="通过合同专用入口创建"))
        await _sync_legacy_projection(item, identity, db)
        await db.commit(); await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)


@router.patch(f"{settings.api_prefix}/contracts/{{contract_id}}")
async def update_contract_draft(contract_id: int, body: ContractDraftInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.contracts import (
        _contract_customer_source_person, _resolve_contract_customer,
    )
    from app.core.formatters import (
        _normalize_external_contract_numbers,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _require_record_owner_or_manager,
    )
    item = await _ensure_record_module(contract_id, "contract", identity, db)
    await _require_record_owner_or_manager(item, identity, db)
    if item.status not in {"草稿", "已拒绝"}:
        raise HTTPException(status_code=409, detail="合同提交审批后不能直接编辑，请使用合同变更流程")
    duplicate = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == body.serial_no.strip(), BusinessRecord.id != item.id))
    if duplicate: raise HTTPException(status_code=409, detail="合同编号已存在")
    duplicate_title = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.module == "contract", BusinessRecord.title == body.title.strip(), BusinessRecord.id != item.id, BusinessRecord.status.not_in({"已删除", "已归档"})))
    if duplicate_title:
        raise HTTPException(status_code=409, detail="合同名称已存在，不能保存同名合同")
    data = _normalize_external_contract_numbers(dict(body.data or {}))
    customer = await _resolve_contract_customer(body.customer, data, identity, db)
    customer_data = customer.data or {}
    # Updates preserve the persisted GUID even when a malicious replacement is sent.
    data = {
        **data,
        "contract_guid": str((item.data or {}).get("contract_guid") or uuid4()),
        "customer_id": customer.id,
        "customer_no": customer.serial_no,
        "customer_manager": "、".join(customer_data.get("customer_managers") or [customer.owner]),
        "source_person": _contract_customer_source_person(customer),
    }
    if float(data.get("amount") or 0) < 0: raise HTTPException(status_code=422, detail="合同金额不能小于零")
    owner = body.owner.strip(); department = body.department.strip()
    if identity.get("role") != "admin":
        current_user = await db.scalar(select(User).where(User.username == identity["username"]));
        if not current_user: raise HTTPException(status_code=401, detail="当前用户不存在")
        department = current_user.department
        if identity.get("role") == "user": owner = identity["username"]
    item.serial_no = body.serial_no.strip(); item.title = body.title.strip(); item.customer = customer.title
    item.owner = owner; item.department = department; item.description = body.description.strip(); item.data = data
    db.add(WorkflowEvent(record_id=item.id, action="修改合同草稿", from_status=item.status, to_status=item.status, operator=identity["username"], comment="通过合同专用入口修改"))
    await db.commit(); await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)


@router.delete(f"{settings.api_prefix}/contracts/{{contract_id}}/draft", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_contract_draft(contract_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Withdraw an unsubmitted contract draft through its business-specific flow.

    This deliberately does not reuse the generic record delete endpoint.  A draft
    can be withdrawn only before it has approval, receivables, incoming payments,
    or downstream records; otherwise the related workflow is the source of truth.
    """
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    contract = await _ensure_record_module(contract_id, "contract", identity, db)
    await _require_record_owner_or_manager(contract, identity, db)
    if contract.status != "草稿":
        raise HTTPException(status_code=409, detail="仅草稿合同可以撤销；已提交或已处理合同请按对应业务流程办理")
    approval_count = int(await db.scalar(select(func.count()).select_from(ContractApprovalStep).where(ContractApprovalStep.contract_record_id == contract.id)) or 0)
    receivable_count = int(await db.scalar(select(func.count()).select_from(ReceivablePlan).where(ReceivablePlan.contract_record_id == contract.id)) or 0)
    incoming_payment_count = int(await db.scalar(select(func.count()).select_from(IncomingPayment).where(IncomingPayment.contract_record_id == contract.id)) or 0)
    related_record = await db.scalar(select(BusinessRecord.serial_no).where(
        BusinessRecord.id != contract.id,
        or_(
            BusinessRecord.data["contract_record_id"].as_integer() == contract.id,
            BusinessRecord.data["contract_id"].as_integer() == contract.id,
        ),
    ).limit(1))
    if approval_count or receivable_count or incoming_payment_count or related_record:
        raise HTTPException(
            status_code=409,
            detail="合同已有审批、收款或下游案件/用印/财务关联，不能撤销草稿；请按对应业务流程处理",
        )
    attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id == contract.id))).all())
    attachment_paths = [Path(item.path) for item in attachments]
    for attachment in attachments:
        await db.delete(attachment)
    await db.execute(delete(ContractEvent).where(ContractEvent.contract_record_id == contract.id))
    await db.execute(delete(ContractApprovalStep).where(ContractApprovalStep.contract_record_id == contract.id))


@router.post(f"{settings.api_prefix}/contracts/delete")
async def delete_contract_records(body: ContractWholeDeleteInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.contracts import (
        _delete_contract_records,
    )
    return await _delete_contract_records(body, identity, db)


@router.post(f"{settings.api_prefix}/contracts/company/delete")
async def delete_company_contract_records(body: ContractWholeDeleteInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.contracts import (
        _delete_contract_records,
    )
    return await _delete_contract_records(body, identity, db, allow_company_contract=True)


    await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == contract.id))
    await db.delete(contract)
    await db.commit()
    for path in attachment_paths:
        if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
            path.unlink()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/contracts/{{contract_id}}/approvals")
async def contract_approvals(contract_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_contract_approval_access, _record_dict_for_identity,
    )
    from app.core.system import (
        _approval_step_dict,
    )
    contract = await _ensure_contract_approval_access(contract_id, identity, db)
    steps = (await db.scalars(select(ContractApprovalStep).where(ContractApprovalStep.contract_record_id == contract_id).order_by(ContractApprovalStep.step_order))).all()
    approver_usernames = list(dict.fromkeys(step.approver.lower() for step in steps if step.approver))
    users = list((await db.scalars(select(User).where(User.username.in_(approver_usernames)))).all()) if approver_usernames else []
    names_by_username = {user.username.lower(): user.display_name for user in users}
    items = [_approval_step_dict(step, names_by_username) for step in steps]
    current_step = next((item for item in items if item["status"] == "待审批"), None)
    return {"contract": await _record_dict_for_identity(contract, identity, db), "items": items, "current_step": current_step}


@router.post(f"{settings.api_prefix}/contracts/{{contract_id}}/submit")
async def submit_contract(contract_id: int, body: ContractSubmitInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.contracts import (
        _is_contract_approver,
    )
    from app.core.legacy_sync import (
        _legacy_contract_business_failure_response,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _require_contract_action, _require_record_owner_or_manager,
    )
    try:
        contract = await _ensure_record_module(contract_id, "contract", identity, db)
        await _require_contract_action(identity, db, "contract.application.submit", "提交审批")
        await _require_record_owner_or_manager(contract, identity, db)
        if contract.status not in {"草稿", "已拒绝"}: raise HTTPException(status_code=409, detail="只有草稿或已拒绝合同可以重新提交")
        attachment_count = int(await db.scalar(select(func.count()).select_from(FileAttachment).where(
            FileAttachment.record_id == contract.id, FileAttachment.category == "合同附件",
        )) or 0)
        if attachment_count < 1:
            raise HTTPException(status_code=422, detail="请先上传至少一份合同附件后再提交审批")
        approvers = [x.strip() for x in body.approvers if x.strip()]
        if len(approvers) != 1: raise HTTPException(status_code=422, detail="合同审批只能选择一名合同审批流程人员")
        approver_user = await db.scalar(select(User).where(User.username == approvers[0], User.is_active.is_(True)))
        if not approver_user: raise HTTPException(status_code=422, detail="审批人不存在或已停用")
        if not await _is_contract_approver(approver_user, db):
            raise HTTPException(status_code=422, detail="所选人员不在合同审批流程人员名单中")
        await db.execute(delete(ContractApprovalStep).where(ContractApprovalStep.contract_record_id == contract_id))
        for index, approver in enumerate(approvers, 1):
            db.add(ContractApprovalStep(contract_record_id=contract_id, step_order=index, approver=approver, status="待审批" if index == 1 else "等待中"))
        old = contract.status
        contract.status = "审批中"
        contract.data = {
            **(contract.data or {}),
            "approval_count": len(approvers),
            "submitted_at": datetime.now().isoformat(timespec="seconds"),
            "submitted_by": identity["username"],
            "submit_comment": body.comment.strip(),
            "current_approver": approvers[0],
            "sync_seal": body.sync_seal,
        }
        db.add(WorkflowEvent(record_id=contract.id, action="提交合同审批", from_status=old, to_status="审批中", operator=identity["username"], comment=body.comment or f"审批人：{approvers[0]}")); await db.commit(); await db.refresh(contract)
        return await _record_dict_for_identity(contract, identity, db)
    except HTTPException as exc:
        return _legacy_contract_business_failure_response(exc)


@router.post(f"{settings.api_prefix}/contracts/{{contract_id}}/approve")
async def approve_contract(contract_id: int, body: ContractApprovalInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.legacy_sync import (
        _legacy_contract_business_failure_response, _sync_legacy_contract_audit, _sync_legacy_official_audit,
    )
    from app.core.permissions import (
        _can_act_on_contract_approval_step, _ensure_contract_approval_access, _record_dict_for_identity,
    )
    try:
        contract = await _ensure_contract_approval_access(contract_id, identity, db)
        if contract.status != "审批中": raise HTTPException(status_code=409, detail="合同当前不在审批中")
        if not body.approved and not body.comment.strip(): raise HTTPException(status_code=422, detail="拒绝时必须填写审批意见")
        steps = (await db.scalars(select(ContractApprovalStep).where(ContractApprovalStep.contract_record_id == contract_id).order_by(ContractApprovalStep.step_order))).all()
        current = next((x for x in steps if x.status == "待审批"), None)
        if not current: raise HTTPException(status_code=409, detail="合同没有待处理的审批节点")
        can_act = await _can_act_on_contract_approval_step(current, identity, body.action_key, db)
        explicit_delegate = current.approver != identity["username"] and can_act
        if not can_act:
            raise HTTPException(status_code=403, detail=f"当前节点应由 {current.approver} 审批")
        current.comment = body.comment.strip(); current.acted_at = datetime.now(); old = contract.status
        if not body.approved:
            current.status = "已拒绝"; contract.status = "已拒绝"
            contract.data = {**(contract.data or {}), "current_approver": ""}
            for step in steps:
                if step.status == "等待中": step.status = "已取消"
            action = "合同审批拒绝"
        else:
            current.status = "已通过"; next_step = next((x for x in steps if x.status == "等待中"), None)
            if next_step:
                next_step.status = "待审批"; action = "合同节点通过"
                contract.data = {**(contract.data or {}), "current_approver": next_step.approver}
            else:
                contract.status = CONTRACT_APPROVED_STATUS; action = "合同审批完成"
                contract.data = {**(contract.data or {}), "current_approver": ""}
                seal_application_id = int((contract.data or {}).get("seal_application_id") or 0)
                if seal_application_id and (contract.data or {}).get("sync_seal"):
                    seal_application = await db.get(BusinessRecord, seal_application_id)
                    if seal_application and seal_application.module == "seal" and seal_application.status == "草稿":
                        seal_application.status = "待审批"
                        contract.data = {**(contract.data or {}), "sync_seal_submitted_at": datetime.now().isoformat(timespec="seconds"), "sync_seal_file_required": False}
                        db.add(WorkflowEvent(record_id=seal_application.id, action="合同通过后自动提交同步用印", from_status="草稿", to_status="待审批", operator=identity["username"], comment=f"来源合同 {contract.serial_no} 已审批通过"))
                        await _sync_legacy_official_audit(seal_application, identity, db, 10, f"来源合同 {contract.serial_no} 已审批通过")
        await _sync_legacy_contract_audit(contract, identity, db, 20 if body.approved else 30, body.comment)
        approval_actor = f"授权代办 {current.approver}" if explicit_delegate else current.approver
        db.add(WorkflowEvent(record_id=contract.id, action=action, from_status=old, to_status=contract.status, operator=identity["username"], comment=f"第{current.step_order}级 {approval_actor}：{body.comment}")); await db.commit(); await db.refresh(contract)
        return await _record_dict_for_identity(contract, identity, db)
    except HTTPException as exc:
        return _legacy_contract_business_failure_response(exc)


@router.post(f"{settings.api_prefix}/contracts/{{contract_id}}/seal-application", status_code=status.HTTP_201_CREATED)
async def create_contract_seal_application(contract_id: int, body: ContractSealApplicationInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.contracts import (
        _single_linked_case_for_contract,
    )
    from app.core.documents import (
        _next_seal_application_serial, _seal_record_dict, _user_has_seal_action,
    )
    from app.core.legacy_sync import (
        _sync_legacy_official_audit, _sync_legacy_official_document,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager, _require_seal_base_action,
    )
    from app.core.storage import (
        _copy_seal_source_attachments,
    )
    contract = await _ensure_record_module(contract_id, "contract", identity, db)
    await _require_record_owner_or_manager(contract, identity, db)
    await _require_seal_base_action(identity, db, "apply")
    sync_seal_requested = bool((contract.data or {}).get("sync_seal"))
    sync_seal_draft = contract.status == "审批中" and sync_seal_requested
    # Contract approval and seal approval are distinct channels.  An explicitly
    # submitted sync-seal request must enter the seal approver's queue at once;
    # only an explicit save-without-submit remains a draft.
    direct_submission = contract.status in {CONTRACT_APPROVED_STATUS, "已完成"} and body.submit
    submitted = direct_submission or (sync_seal_draft and body.submit)
    if contract.status == "审批中" and not sync_seal_draft:
        raise HTTPException(status_code=409, detail="当前合同状态不支持提交用印审批")
    if body.submit and not (sync_seal_draft or direct_submission):
        raise HTTPException(status_code=409, detail="当前合同状态不支持提交用印审批")
    if contract.status in {"\u8349\u7a3f", "\u5df2\u62d2\u7edd"}:
        raise HTTPException(status_code=409, detail="合同提交审批后才能配置同步用印")
    approver = await db.scalar(select(User).where(User.username == body.approver.strip(), User.is_active.is_(True)))
    if not approver:
        raise HTTPException(status_code=422, detail="用印审批人不存在或已停用")
    if not await _user_has_seal_action(approver, "approve", db):
        raise HTTPException(status_code=422, detail="所选人员没有用印审批动作权限")
    existing_id = int((contract.data or {}).get("seal_application_id") or 0)
    if existing_id:
        existing = await db.get(BusinessRecord, existing_id)
        if existing:
            raise HTTPException(status_code=409, detail=f"合同已生成用印申请 {existing.serial_no}")
    asset = await db.get(SealAsset, body.seal_asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="印章不存在")
    if asset.status != "可用":
        raise HTTPException(status_code=409, detail=f"印章当前状态为“{asset.status}”，不能申请")
    explicit_source_attachment_ids = list(dict.fromkeys(int(item_id) for item_id in body.source_attachment_ids if int(item_id) > 0))
    source_attachment_ids = list(explicit_source_attachment_ids)
    if not source_attachment_ids:
        source_attachment_ids = list((await db.scalars(select(FileAttachment.id).where(
            FileAttachment.record_id == contract.id,
        ).order_by(FileAttachment.created_at, FileAttachment.id))).all())
    source_files = list((await db.scalars(select(FileAttachment).where(
        FileAttachment.id.in_(source_attachment_ids),
        FileAttachment.record_id == contract.id,
    ))).all()) if source_attachment_ids else []
    if explicit_source_attachment_ids and len(source_files) != len(source_attachment_ids):
        raise HTTPException(status_code=422, detail="选中的来源文件必须全部归属于当前合同")
    if not source_files:
        raise HTTPException(status_code=409, detail="当前合同没有可复制的有效附件，不能发起同步用印")
    if len(source_files) != len(source_attachment_ids):
        raise HTTPException(status_code=422, detail="当前合同附件无法完整复制")
    linked_case = await _single_linked_case_for_contract(contract, identity, db)
    serial = await _next_seal_application_serial(db)
    seal_status = "待审批" if submitted else "草稿"
    seal = BusinessRecord(
        module="seal",
        serial_no=serial,
        title=f"{contract.title}合同用印",
        customer=contract.customer,
        status=seal_status,
        owner=identity["username"],
        department=contract.department,
        description=body.description,
        data={
            "case_record_id": linked_case.id if linked_case else None,
            "case_no": linked_case.serial_no if linked_case else "",
            "contract_record_id": contract.id,
            "contract_no": contract.serial_no,
            "use_type": "合同用印",
            "seal_asset_id": asset.id,
            "seal_type": asset.seal_type,
            "seal_name": asset.name,
            "copies": body.copies,
            "purpose": body.purpose,
            "use_date": str(body.use_date),
            "delivery_method": body.delivery_method,
            "document_names": body.document_names,
            "approver": approver.username,
            "source_attachment_ids": source_attachment_ids,
        },
    )
    copied_targets: list[Path] = []
    try:
        db.add(seal)
        await db.flush()
        copied_targets = await _copy_seal_source_attachments(seal, source_attachment_ids, identity, db)
        contract.data = {
            **(contract.data or {}),
            "seal_application_id": seal.id,
            "seal_application_no": seal.serial_no,
            "seal_requested_at": datetime.now().isoformat(timespec="seconds"),
            "sync_seal": sync_seal_requested,
            **({"sync_seal_submitted_at": datetime.now().isoformat(timespec="seconds"), "sync_seal_file_required": False} if submitted and sync_seal_requested else {}),
        }
        db.add_all([
            WorkflowEvent(record_id=seal.id, action="创建合同用印申请并提交审批" if submitted else "创建合同用印申请", to_status=seal_status, operator=identity["username"], comment=f"来源合同 {contract.serial_no}｜{asset.name}｜{body.copies}份"),
            WorkflowEvent(record_id=contract.id, action="配置同步用印" if contract.status == "审批中" else "发起合同用印", from_status=contract.status, to_status=contract.status, operator=identity["username"], comment=f"生成用印申请 {seal.serial_no}" + ("并提交审批" if submitted else "，保存为草稿")),
        ])
        if submitted:
            await _sync_legacy_official_audit(seal, identity, db, 10, "合同用印申请已提交审批")
        else:
            await _sync_legacy_official_document(seal, identity, db)
        await db.commit()
        await db.refresh(seal)
    except Exception:
        await db.rollback()
        for target in copied_targets:
            target.unlink(missing_ok=True)
        raise
    return await _seal_record_dict(seal, db, identity=identity)


@router.post(f"{settings.api_prefix}/contracts/{{contract_id}}/investigation", status_code=status.HTTP_201_CREATED)
async def create_contract_investigation(contract_id: int, body: ContractInvestigationInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.contracts import (
        _contract_allows_downstream_creation, _contract_customer_manager_values, _contract_investigation_source_data,
    )
    from app.core.crm import (
        _customer_reference_from_maps,
    )
    from app.core.investigation import (
        _configured_investigation_supervisor,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_contract_investigation_create_access,
    )
    from app.core.projections import (
        _contract_customer_projection_context,
    )
    from app.core.system import (
        _record_dict,
    )
    contract = await _ensure_record_module(contract_id, "contract", identity, db)
    await _require_contract_investigation_create_access(contract, identity, db)
    if not _contract_allows_downstream_creation(contract):
        raise HTTPException(status_code=409, detail="草稿合同不能新建调查任务")
    if body.authorized_to < body.authorized_from:
        raise HTTPException(status_code=422, detail="授权结束日期不能早于开始日期")
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    supervisor = await _configured_investigation_supervisor(db)
    requested_owner = body.owner.strip()
    if requested_owner and requested_owner != supervisor.username:
        raise HTTPException(status_code=422, detail="调查任务必须分配给系统配置的调查主管")
    owner = supervisor.username
    duplicate = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == "investigation",
        BusinessRecord.data["contract_id"].as_integer() == contract.id,
        BusinessRecord.title == body.title.strip(),
        BusinessRecord.status.not_in({"已取消", "已完成"}),
    ))
    if duplicate:
        raise HTTPException(status_code=409, detail=f"该合同已有同名调查任务 {duplicate.serial_no}")
    contract_context = await _contract_customer_projection_context([contract], db)
    customer, _ = _customer_reference_from_maps(
        contract.customer,
        contract.data or {},
        contract_context["customers_by_id"],
        contract_context["customers_by_no"],
        contract_context["customers_by_name"],
    )
    source_data = _contract_investigation_source_data(contract, customer)
    serial = f"DC{datetime.now():%Y%m%d%H%M%S}{uuid4().hex[:4].upper()}"
    investigation = BusinessRecord(
        module="investigation",
        serial_no=serial,
        title=body.title.strip(),
        customer=contract.customer,
        status="进行中" if owner else "待分配",
        owner=owner,
        department=user.department if user else contract.department,
        description=body.description,
        data={
            **source_data,
            "authorized_from": str(body.authorized_from),
            "authorized_to": str(body.authorized_to),
            "region": body.region.strip(),
            "authorization_scope": body.authorization_scope.strip(),
            "right_type": body.right_type.strip(),
            "customer_review": body.customer_review,
            "publisher": identity["username"],
            "assigner": identity["username"] if owner else "",
            "source_owner": (contract.data or {}).get("source_person") or contract.owner,
            "customer_managers": _contract_customer_manager_values(contract, customer),
            "customer_manager": "、".join(_contract_customer_manager_values(contract, customer)),
        },
    )
    db.add(investigation)
    await db.flush()
    attachment_ids = list(dict.fromkeys(int(item) for item in body.attachment_ids if int(item) > 0))
    if attachment_ids:
        attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.id.in_(attachment_ids)))).all())
        if len(attachments) != len(attachment_ids) or any(item.record_id not in {None, contract.id} and item.uploader != identity["username"] for item in attachments):
            raise HTTPException(status_code=422, detail="调查任务附件不存在或无权使用")
        for attachment in attachments:
            attachment.record_id = investigation.id
    linked_ids = list((contract.data or {}).get("investigation_ids", [])); linked_ids.append(investigation.id)
    contract.data = {**(contract.data or {}), "investigation_ids": list(dict.fromkeys(linked_ids)), "last_investigation_no": serial}
    db.add_all([
        WorkflowEvent(record_id=investigation.id, action="从合同创建调查任务", to_status=investigation.status, operator=identity["username"], comment=f"来源合同 {contract.serial_no}"),
        WorkflowEvent(record_id=contract.id, action="新建调查任务", from_status=contract.status, to_status=contract.status, operator=identity["username"], comment=f"生成调查任务 {serial}"),
    ])
    await db.commit(); await db.refresh(investigation)
    return _record_dict(investigation)


@router.post(f"{settings.api_prefix}/contracts/{{contract_id}}/archive")
async def archive_contract(contract_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _require_contract_action, _require_record_owner_or_manager,
    )
    contract = await _ensure_record_module(contract_id, "contract", identity, db)
    await _require_contract_action(identity, db, "contract.archive.close", "归档")
    await _require_record_owner_or_manager(contract, identity, db)
    if contract.status == "已归档":
        raise HTTPException(status_code=409, detail="合同已经归档")
    if contract.status not in {CONTRACT_APPROVED_STATUS, "已完成"}:
        raise HTTPException(status_code=409, detail="只有审批全部通过且处于履行或完成阶段的合同可以归档")
    pending_or_rejected = int(await db.scalar(select(func.count()).select_from(ContractApprovalStep).where(ContractApprovalStep.contract_record_id == contract.id, ContractApprovalStep.status != "已通过")) or 0)
    if pending_or_rejected:
        raise HTTPException(status_code=409, detail="合同仍有未通过的审批节点，不能归档")
    previous = contract.status
    contract.status = "已归档"
    contract.data = {**(contract.data or {}), "archived_at": datetime.now().isoformat(timespec="seconds")}
    db.add(WorkflowEvent(record_id=contract.id, action="合同归档", from_status=previous, to_status="已归档", operator=identity["username"], comment="合同列表批量操作归档"))
    await db.commit(); await db.refresh(contract)
    return await _record_dict_for_identity(contract, identity, db)


@router.get(f"{settings.api_prefix}/contracts/archive-list")
async def list_contract_archive_records(
    contract_no: str = "", customer: str = "",
    archive_status: str = Query("", pattern="^(|归档中|已归档)$"),
    archive_date_from: date | None = None, archive_date_to: date | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.contracts import (
        _contract_archive_rows,
    )
    if archive_date_from and archive_date_to and archive_date_from > archive_date_to:
        raise HTTPException(status_code=422, detail="归档开始日期不能晚于结束日期")
    rows = await _contract_archive_rows(identity, db, contract_no=contract_no, customer=customer,
                                        archive_status=archive_status, archive_date_from=archive_date_from,
                                        archive_date_to=archive_date_to)
    total = len(rows)
    start = (page - 1) * page_size
    return {"items": rows[start:start + page_size], "total": total, "page": page, "page_size": page_size,
            "pages": (total + page_size - 1) // page_size if total else 0}


@router.get(f"{settings.api_prefix}/contracts/archive-list/export-excel")
async def export_contract_archive_records(
    contract_no: str = "", customer: str = "",
    archive_status: str = Query("", pattern="^(|归档中|已归档)$"),
    archive_date_from: date | None = None, archive_date_to: date | None = None,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.contracts import (
        _contract_archive_rows,
    )
    from app.core.system import (
        _excel_response,
    )
    if archive_date_from and archive_date_to and archive_date_from > archive_date_to:
        raise HTTPException(status_code=422, detail="归档开始日期不能晚于结束日期")
    items = await _contract_archive_rows(identity, db, contract_no=contract_no, customer=customer,
                                         archive_status=archive_status, archive_date_from=archive_date_from,
                                         archive_date_to=archive_date_to)
    headers = ["合同编号", "合同名称", "客户", "归档状态", "归档日期", "负责人", "部门"]
    rows = [[item.get("serial_no", ""), item.get("title", ""), item.get("customer", ""), item.get("archive_status", ""), item.get("archive_date", ""), item.get("owner", ""), item.get("department", "")] for item in items]
    return _excel_response(f"合同归档-{date.today()}.xls", headers, rows)


@router.get(f"{settings.api_prefix}/contracts/{{contract_id}}/events")
async def list_contract_events(
    contract_id: int, page: int | None = Query(None, ge=1), page_size: int | None = Query(None, ge=1, le=200), keyword: str = "",
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.contracts import (
        _contract_events_payload,
    )
    from app.core.permissions import (
        _ensure_record_visible,
    )
    contract = await _ensure_record_visible(contract_id, identity, db)
    if contract.module != "contract":
        raise HTTPException(status_code=404, detail="合同不存在")
    return await _contract_events_payload(contract, page=page, page_size=page_size, keyword=keyword, db=db)


@router.get(f"{settings.api_prefix}/contracts/guid/{{contract_guid}}/events")
async def list_contract_events_by_guid(
    contract_guid: str, page: int | None = Query(None, ge=1), page_size: int | None = Query(None, ge=1, le=200), keyword: str = "",
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.contracts import (
        _contract_events_payload,
    )
    from app.core.permissions import (
        _ensure_contract_by_guid,
    )
    contract = await _ensure_contract_by_guid(contract_guid, identity, db)
    return await _contract_events_payload(contract, page=page, page_size=page_size, keyword=keyword, db=db)


@router.post(f"{settings.api_prefix}/contracts/{{contract_id}}/events", status_code=status.HTTP_201_CREATED)
async def create_contract_event(contract_id: int, body: ContractEventInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.contracts import (
        _create_contract_event_for_record,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    contract = await _ensure_record_module(contract_id, "contract", identity, db)
    return await _create_contract_event_for_record(contract, body, identity, db)


@router.post(f"{settings.api_prefix}/contracts/guid/{{contract_guid}}/events", status_code=status.HTTP_201_CREATED)
async def create_contract_event_by_guid(contract_guid: str, body: ContractEventInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.contracts import (
        _create_contract_event_for_record,
    )
    from app.core.permissions import (
        _ensure_contract_by_guid,
    )
    contract = await _ensure_contract_by_guid(contract_guid, identity, db)
    return await _create_contract_event_for_record(contract, body, identity, db)


@router.get(f"{settings.api_prefix}/contracts/{{contract_id}}/objects")
async def list_contract_objects(contract_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.contracts import (
        _contract_object_payload,
    )
    from app.core.permissions import (
        _ensure_record_visible,
    )
    contract = await _ensure_record_visible(contract_id, identity, db)
    if contract.module != "contract":
        raise HTTPException(status_code=404, detail="合同不存在")
    objects = (await db.scalars(select(ContractObject).where(ContractObject.contract_record_id == contract.id).order_by(ContractObject.id))).all()
    return {"items": [await _contract_object_payload(item, identity, db) for item in objects], "total": len(objects)}


@router.get(f"{settings.api_prefix}/contracts/{{contract_id}}/object-cases")
async def list_contract_object_cases(contract_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Return every visible case eligible to become a subject line of this contract.

    This is deliberately not a paged generic-record lookup: a client with more
    than 100 cases must not silently lose valid subject candidates in the
    contract-object editor.
    """
    from app.core.permissions import (
        _ensure_record_visible, _record_scope_conditions,
    )
    contract = await _ensure_record_visible(contract_id, identity, db)
    if contract.module != "contract":
        raise HTTPException(status_code=404, detail="合同不存在")
    cases = (await db.scalars(
        select(BusinessRecord)
        .where(
            BusinessRecord.module == "case",
            BusinessRecord.customer == contract.customer,
            *(await _record_scope_conditions(identity, db)),
        )
        .order_by(BusinessRecord.serial_no, BusinessRecord.id)
    )).all()
    return {
        "items": [
            {
                "id": item.id,
                "serial_no": item.serial_no,
                "title": item.title,
                "customer": item.customer,
                "status": item.status,
                "case_type": (item.data or {}).get("case_type", ""),
            }
            for item in cases
        ],
        "total": len(cases),
    }


@router.post(f"{settings.api_prefix}/contracts/{{contract_id}}/objects", status_code=status.HTTP_201_CREATED)
async def create_contract_object(contract_id: int, body: ContractObjectInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.contracts import (
        _contract_object_payload, _contract_object_writable,
    )
    from app.core.permissions import (
        _ensure_record_module, _ensure_record_visible, _require_contract_action,
    )
    contract = await _ensure_record_module(contract_id, "contract", identity, db)
    await _require_contract_action(identity, db, "contract.application.update", "维护合同标的")
    await _contract_object_writable(contract, identity, db)
    case = await _ensure_record_visible(body.case_record_id, identity, db)
    if case.module != "case" or case.customer != contract.customer:
        raise HTTPException(status_code=422, detail="合同标的必须关联当前客户范围内的案件")
    duplicate = await db.scalar(select(ContractObject.id).where(ContractObject.contract_record_id == contract.id, ContractObject.case_record_id == case.id, ContractObject.fee_type == body.fee_type.strip()))
    if duplicate:
        raise HTTPException(status_code=409, detail="该案件和费用类型已存在合同标的")
    item = ContractObject(contract_record_id=contract.id, case_record_id=case.id, fee_type=body.fee_type.strip(), amount=body.amount, remark=body.remark.strip(), created_by=identity["username"], updated_by=identity["username"])
    db.add(item); await db.flush()
    snapshot = {"case_no": case.serial_no, "fee_type": item.fee_type, "amount": item.amount, "remark": item.remark}
    db.add(ContractObjectLog(contract_object_id=item.id, action="新增合同标的", before={}, after=snapshot, operator=identity["username"]))
    db.add(WorkflowEvent(record_id=contract.id, action="新增合同标的", from_status=contract.status, to_status=contract.status, operator=identity["username"], comment=f"{case.serial_no}｜{item.fee_type}｜{item.amount}"))
    await db.commit(); await db.refresh(item)
    return await _contract_object_payload(item, identity, db)


@router.patch(f"{settings.api_prefix}/contracts/{{contract_id}}/objects/{{object_id}}")
async def update_contract_object(contract_id: int, object_id: int, body: ContractObjectInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.contracts import (
        _contract_object_payload, _contract_object_writable,
    )
    from app.core.permissions import (
        _ensure_contract_object_not_reserved, _ensure_record_module, _ensure_record_visible, _require_contract_action,
    )
    contract = await _ensure_record_module(contract_id, "contract", identity, db)
    await _require_contract_action(identity, db, "contract.application.update", "维护合同标的")
    await _contract_object_writable(contract, identity, db)
    item = await db.scalar(select(ContractObject).where(ContractObject.id == object_id, ContractObject.contract_record_id == contract.id))
    if not item: raise HTTPException(status_code=404, detail="合同标的不存在")
    await _ensure_contract_object_not_reserved(item, db)
    case = await _ensure_record_visible(body.case_record_id, identity, db)
    if case.module != "case" or case.customer != contract.customer: raise HTTPException(status_code=422, detail="合同标的必须关联当前客户范围内的案件")
    duplicate = await db.scalar(select(ContractObject.id).where(ContractObject.contract_record_id == contract.id, ContractObject.case_record_id == case.id, ContractObject.fee_type == body.fee_type.strip(), ContractObject.id != item.id))
    if duplicate: raise HTTPException(status_code=409, detail="该案件和费用类型已存在合同标的")
    before = {"case_record_id": item.case_record_id, "fee_type": item.fee_type, "amount": item.amount, "remark": item.remark}
    item.case_record_id = case.id; item.fee_type = body.fee_type.strip(); item.amount = body.amount; item.remark = body.remark.strip(); item.updated_by = identity["username"]
    after = {"case_record_id": item.case_record_id, "fee_type": item.fee_type, "amount": item.amount, "remark": item.remark}
    db.add(ContractObjectLog(contract_object_id=item.id, action="修改合同标的", before=before, after=after, operator=identity["username"]))
    db.add(WorkflowEvent(record_id=contract.id, action="修改合同标的", from_status=contract.status, to_status=contract.status, operator=identity["username"], comment=f"标的#{item.id}"))
    await db.commit(); await db.refresh(item)
    return await _contract_object_payload(item, identity, db)


@router.delete(f"{settings.api_prefix}/contracts/{{contract_id}}/objects/{{object_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract_object(contract_id: int, object_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.contracts import (
        _contract_object_writable,
    )
    from app.core.permissions import (
        _ensure_contract_object_not_reserved, _ensure_record_module, _require_contract_action,
    )
    contract = await _ensure_record_module(contract_id, "contract", identity, db)
    await _require_contract_action(identity, db, "contract.application.update", "维护合同标的")
    await _contract_object_writable(contract, identity, db)
    item = await db.scalar(select(ContractObject).where(ContractObject.id == object_id, ContractObject.contract_record_id == contract.id))
    if not item: raise HTTPException(status_code=404, detail="合同标的不存在")
    await _ensure_contract_object_not_reserved(item, db)
    db.add(WorkflowEvent(record_id=contract.id, action="删除合同标的", from_status=contract.status, to_status=contract.status, operator=identity["username"], comment=f"标的#{item.id}｜{item.fee_type}｜{item.amount}"))
    await db.delete(item); await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/contracts/{{contract_id}}/archive-subjects")
async def contract_archive_subjects(contract_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_archive_checks,
    )
    from app.core.finance import (
        _fee_matches_contract_object, _invoice_case_fee_rows, _round_fee_amount,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_scope_conditions, _require_record_module_menu,
    )
    await _require_record_module_menu("contract", identity, db, action="查看")
    contract = await _ensure_record_module(contract_id, "contract", identity, db)
    objects = list((await db.scalars(
        select(ContractObject)
        .where(ContractObject.contract_record_id == contract.id)
        .order_by(ContractObject.case_record_id, ContractObject.id)
    )).all())
    case_ids = {item.case_record_id for item in objects}
    cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(case_ids), BusinessRecord.module == "case",
        *(await _record_scope_conditions(identity, db)),
    ))).all()) if case_ids else []
    cases_by_id = {item.id: item for item in cases}
    case_nos = {item.serial_no for item in cases}
    fees = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance",
        or_(
            BusinessRecord.data["case_id"].as_integer().in_(case_ids),
            BusinessRecord.data["case_no"].as_string().in_(case_nos),
        ) if case_ids else false(),
        *(await _record_scope_conditions(identity, db)),
    ))).all())
    fee_ids = {fee.id for fee in fees}
    finance_rows = await _invoice_case_fee_rows(
        identity, db, scope="company", ids=fee_ids, include_all_fee_types=True,
    ) if fee_ids else []
    finance_by_id = {int(row["id"]): row for row in finance_rows}
    items: list[dict] = []
    for item in objects:
        case = cases_by_id.get(item.case_record_id)
        if not case:
            continue
        linked_fees = [fee for fee in fees if _fee_matches_contract_object(fee, item, case)]
        checks = await _case_archive_checks(case, db)
        paid_amount = 0.0
        invoiced_amount = 0.0
        for fee in linked_fees:
            row_data = (finance_by_id.get(fee.id) or {}).get("data") or {}
            paid_amount += float(row_data.get("paid_amount") or 0)
            invoiced_amount += float(row_data.get("invoice_amount") or 0)
        items.append({
            "contract_object_id": item.id,
            "case_record_id": case.id,
            "case_no": case.serial_no,
            "case_title": case.title,
            "case_fee_ids": [fee.id for fee in linked_fees],
            "fee_type": item.fee_type,
            "contract_amount": _round_fee_amount(item.amount),
            "paid_amount": _round_fee_amount(paid_amount),
            "invoiced_amount": _round_fee_amount(invoiced_amount),
            "fee_archived": bool(linked_fees) and all(bool((fee.data or {}).get("fee_archived")) for fee in linked_fees),
            "materials_ready": all(checks.values()),
            "archive_checks": checks,
        })
    return {
        "contract": {
            "id": contract.id, "serial_no": contract.serial_no, "title": contract.title,
            "customer": contract.customer, "status": contract.status,
        },
        "items": items,
        "total": len(items),
    }


@router.post(f"{settings.api_prefix}/contracts/{{contract_id}}/archive-closure")
async def close_contract_archive_subjects(contract_id: int, body: ContractArchiveClosureInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _fee_matches_contract_object,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_scope_conditions, _require_contract_action, _require_record_owner_or_manager,
    )
    contract = await _ensure_record_module(contract_id, "contract", identity, db)
    await _require_contract_action(identity, db, "contract.archive.close", "归档")
    await _require_record_owner_or_manager(contract, identity, db)
    case_fee_ids = list(dict.fromkeys(body.case_fee_ids))
    objects = list((await db.scalars(
        select(ContractObject)
        .where(ContractObject.contract_record_id == contract.id)
        .with_for_update()
    )).all())
    if not objects:
        raise HTTPException(status_code=409, detail="合同没有可完结的案件费用标的")
    visible_scope = await _record_scope_conditions(identity, db)
    case_ids = {item.case_record_id for item in objects}
    cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_({item.case_record_id for item in objects}),
        BusinessRecord.module == "case",
        *visible_scope,
    ))).all())
    if len(cases) != len(case_ids):
        raise HTTPException(status_code=403, detail="当前账号无权操作合同关联案件")
    cases_by_id = {item.id: item for item in cases}
    fees = list((await db.scalars(
        select(BusinessRecord)
        .where(BusinessRecord.id.in_(case_fee_ids), BusinessRecord.module == "finance")
        .where(*visible_scope)
        .with_for_update()
    )).all())
    if len(fees) != len(case_fee_ids):
        raise HTTPException(status_code=422, detail="选择的案件费用不存在或已失效")
    object_by_fee: dict[int, ContractObject] = {}
    for fee in fees:
        matches = [
            item for item in objects
            if (case := cases_by_id.get(item.case_record_id)) is not None
            and _fee_matches_contract_object(fee, item, case)
        ]
        if len(matches) != 1:
            raise HTTPException(status_code=422, detail=f"案件费用#{fee.id}不属于当前合同的唯一标的")
        object_by_fee[fee.id] = matches[0]
    changed = 0
    now = datetime.now(timezone.utc).isoformat()
    for fee in fees:
        item = object_by_fee[fee.id]
        before_data = dict(fee.data or {})
        before_archived = bool(before_data.get("fee_archived"))
        fee.data = {
            **before_data,
            "fee_archived": body.fee_archived,
            "fee_archived_at": now if body.fee_archived else None,
            "fee_archived_by": identity["username"] if body.fee_archived else "",
            "fee_archive_comment": body.comment.strip(),
            "contract_object_id": item.id,
            "contract_id": contract.id,
            "contract_no": contract.serial_no,
        }
        if before_archived != body.fee_archived:
            changed += 1
        db.add(ContractObjectLog(
            contract_object_id=item.id,
            action="完结案件费用" if body.fee_archived else "取消案件费用完结",
            before={"case_fee_id": fee.id, "fee_archived": before_archived},
            after={"case_fee_id": fee.id, "fee_archived": body.fee_archived},
            operator=identity["username"],
        ))
        db.add(WorkflowEvent(
            record_id=fee.id,
            action="合同归档完结案件费用" if body.fee_archived else "合同归档取消费用完结",
            from_status=fee.status,
            to_status=fee.status,
            operator=identity["username"],
            comment=f"{contract.serial_no}｜标的#{item.id}｜{body.comment.strip()}",
        ))
    contract.data = {
        **(contract.data or {}),
        "archive_closure_updated_at": now,
        "archive_closure_updated_by": identity["username"],
    }
    db.add(WorkflowEvent(
        record_id=contract.id,
        action="更新合同归档费用完结状态",
        from_status=contract.status,
        to_status=contract.status,
        operator=identity["username"],
        comment=f"处理 {len(fees)} 条案件费用；变更 {changed} 条。{body.comment.strip()}",
    ))
    await db.commit()
    return {"updated": len(fees), "changed": changed, "fee_archived": body.fee_archived}


@router.get(f"{settings.api_prefix}/contracts/{{contract_id}}/payment-candidates")
async def contract_payment_candidates(contract_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _active_payment_type_rows, _contract_payment_candidate_rows,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    contract = await _ensure_record_module(contract_id, "contract", identity, db)
    payment_types = await _active_payment_type_rows(db)
    return {
        "contract": {"id": contract.id, "serial_no": contract.serial_no, "title": contract.title, "customer": contract.customer, "owner": contract.owner, "status": contract.status},
        "payment_types": [
            {
                **item,
                "value": item["id"],
                "label": "｜".join([item["payee"], item["account_bank"], item["account"]]),
            }
            for item in payment_types
        ],
        "items": await _contract_payment_candidate_rows(contract, identity, db),
    }


@router.post(f"{settings.api_prefix}/contracts/{{contract_id}}/payment-types", status_code=status.HTTP_201_CREATED)
async def create_contract_payment_type(contract_id: int, body: FinancePaymentTypeCreateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _create_payment_type, _finance_payment_type_dict,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_contract_action, _require_record_owner_or_manager,
    )
    contract = await _ensure_record_module(contract_id, "contract", identity, db)
    await _require_contract_action(identity, db, "contract.payment.create", "新增合同付款单位")
    await _require_record_owner_or_manager(contract, identity, db)
    item = await _create_payment_type(body, identity, db, {"contract_id": contract.id, "contract_no": contract.serial_no})
    return {**_finance_payment_type_dict(item), "value": item.id, "label": "｜".join([body.payee.strip(), body.account_bank.strip(), body.account.strip()])}


@router.get(f"{settings.api_prefix}/contracts/{{contract_id}}/payment-applications")
async def list_contract_payment_applications(contract_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _record_scope_conditions,
    )
    contract = await _ensure_record_module(contract_id, "contract", identity, db)
    items = (await db.scalars(select(BusinessRecord).where(
        or_(
            and_(
                BusinessRecord.module == "contract_payment",
                BusinessRecord.data["contract_id"].as_integer() == contract.id,
            ),
            and_(
                BusinessRecord.module == "finance",
                BusinessRecord.data["legacy_kind"].as_string() == "ap_payment",
                BusinessRecord.data["contract_id"].as_integer() == contract.id,
            ),
        ),
        *(await _record_scope_conditions(identity, db)),
    ).order_by(BusinessRecord.id.desc()))).all()
    result = []
    for item in items:
        lines = (await db.scalars(select(ContractPaymentLine).where(ContractPaymentLine.payment_record_id == item.id).order_by(ContractPaymentLine.id))).all()
        line_payload = [{"id": line.id, "contract_object_id": line.contract_object_id, "case_record_id": line.case_record_id, "fee_type": line.fee_type, "requested_amount": line.requested_amount} for line in lines]
        if not line_payload and (item.data or {}).get("legacy_kind") == "ap_payment":
            line_payload = [
                {
                    "legacy_case_fee_id": line.get("legacy_case_fee_id"),
                    "case_no": line.get("case_no", ""),
                    "fee_type": line.get("fee_type", ""),
                    "requested_amount": float(line.get("settlement_amount", 0) or 0),
                }
                for line in (item.data or {}).get("lines", [])
            ]
        result.append({**await _record_dict_for_identity(item, identity, db), "lines": line_payload})
    return {"items": result, "total": len(result)}


@router.post(f"{settings.api_prefix}/contracts/{{contract_id}}/payment-applications", status_code=status.HTTP_201_CREATED)
async def create_contract_payment_application(contract_id: int, body: ContractPaymentApplicationInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _active_payment_type, _contract_payment_candidate_rows, _finance_payment_type_dict, _round_fee_amount,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _require_contract_action, _require_record_owner_or_manager,
    )
    contract = await _ensure_record_module(contract_id, "contract", identity, db)
    await _require_contract_action(identity, db, "contract.payment.create", "发起付款申请")
    await _require_record_owner_or_manager(contract, identity, db)
    if contract.status in {"审批中", "已归档"}:
        raise HTTPException(status_code=409, detail="审批中或已归档合同不能发起合同付款")
    if contract.status not in {CONTRACT_APPROVED_STATUS, "已完成"}:
        raise HTTPException(status_code=409, detail="仅审批通过或已完成的合同可以发起合同付款")
    payment_type = await _active_payment_type(body.payment_type_id, db)
    payment_type_data = _finance_payment_type_dict(payment_type)
    line_inputs = list({line.contract_object_id: line for line in body.lines}.values())
    if len(line_inputs) != len(body.lines):
        raise HTTPException(status_code=422, detail="同一合同标的只能提交一次")
    candidates = {item["contract_object_id"]: item for item in await _contract_payment_candidate_rows(contract, identity, db)}
    invalid = [str(line.contract_object_id) for line in line_inputs if line.contract_object_id not in candidates]
    if invalid:
        raise HTTPException(status_code=404, detail="部分合同标的不存在或无权访问：" + "、".join(invalid))
    normalized_lines: list[tuple[ContractPaymentLineInput, dict]] = []
    for line in line_inputs:
        candidate = candidates[line.contract_object_id]
        amount = _round_fee_amount(line.amount)
        if amount <= 0 or amount > float(candidate["remaining_amount"]) + 0.0001:
            raise HTTPException(status_code=422, detail=f"案件 {candidate['case_no']} 的本次支付金额不能超过待付余额")
        normalized_lines.append((line, candidate))
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if not user: raise HTTPException(status_code=401, detail="当前用户不存在")
    total = _round_fee_amount(sum(_round_fee_amount(line.amount) for line, _ in normalized_lines))
    serial = f"CP{datetime.now():%Y%m%d%H%M%S%f}"
    snapshot = [{"contract_object_id": item["contract_object_id"], "case_id": item["case_record_id"], "case_no": item["case_no"], "fee_type": item["fee_type"], "amount": _round_fee_amount(line.amount)} for line, item in normalized_lines]
    payment = BusinessRecord(module="contract_payment", serial_no=serial, title=f"{contract.serial_no}合同付款申请", customer=contract.customer, status="待审批", owner=contract.owner, department=user.department, description=body.remark.strip(), data={"contract_id": contract.id, "contract_no": contract.serial_no, "payment_type_id": payment_type.id, "payment_type_code": payment_type.code, "payment_type": payment_type.name, "payment_nature": payment_type_data["nature"], "payee": payment_type_data["payee"], "account_bank": payment_type_data["account_bank"], "account": payment_type_data["account"], "application_date": body.application_date.isoformat(), "amount": total, "lines": snapshot, "applicant": identity["username"]})
    db.add(payment); await db.flush()
    for line, candidate in normalized_lines:
        db.add(ContractPaymentLine(payment_record_id=payment.id, contract_object_id=line.contract_object_id, case_record_id=candidate["case_record_id"], fee_type=candidate["fee_type"], requested_amount=_round_fee_amount(line.amount)))
    db.add(WorkflowEvent(record_id=payment.id, action="提交合同付款申请", to_status="待审批", operator=identity["username"], comment=f"{payment_type_data['payee']}｜{total:.2f} 元"))
    db.add(WorkflowEvent(record_id=contract.id, action="发起合同付款申请", from_status=contract.status, to_status=contract.status, operator=identity["username"], comment=f"{serial}｜{total:.2f} 元"))
    await db.commit(); await db.refresh(payment)
    return await _record_dict_for_identity(payment, identity, db)


@router.post(f"{settings.api_prefix}/contract-payment-applications/{{payment_id}}/review")
async def review_contract_payment_application(payment_id: int, body: ContractPaymentReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _require_contract_action,
    )
    await _require_contract_action(identity, db, "contract.payment.approve", "审批付款申请")
    payment = await _ensure_record_module(payment_id, "contract_payment", identity, db)
    if payment.status != "待审批": raise HTTPException(status_code=409, detail="仅待审批合同付款可以审核")
    target = "待付款" if body.approved else "已驳回"
    payment.status = target
    db.add(WorkflowEvent(record_id=payment.id, action="合同付款审批通过" if body.approved else "合同付款审批驳回", from_status="待审批", to_status=target, operator=identity["username"], comment=body.comment.strip()))
    await db.commit(); await db.refresh(payment); return await _record_dict_for_identity(payment, identity, db)


@router.post(f"{settings.api_prefix}/contract-payment-applications/{{payment_id}}/pay")
async def pay_contract_payment_application(payment_id: int, body: ContractPaymentPayInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _round_fee_amount,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _require_contract_action,
    )
    await _require_contract_action(identity, db, "contract.payment.pay", "办理付款")
    payment = await _ensure_record_module(payment_id, "contract_payment", identity, db)
    if payment.status != "待付款": raise HTTPException(status_code=409, detail="仅待付款合同付款申请可以标记付款")
    data = dict(payment.data or {}); total = _round_fee_amount(float(data.get("amount") or 0))
    db.add(FinanceTransaction(finance_record_id=payment.id, transaction_type="合同付款", amount=total, transaction_date=body.paid_date, voucher_no=body.voucher_no.strip(), counterparty=str(data.get("payee") or ""), operator=identity["username"], remark=body.comment.strip()))
    payment.status = "已付款"; payment.data = {**data, "paid_date": body.paid_date.isoformat(), "voucher_no": body.voucher_no.strip(), "paid_by": identity["username"]}
    db.add(WorkflowEvent(record_id=payment.id, action="合同付款完成", from_status="待付款", to_status="已付款", operator=identity["username"], comment=body.comment.strip()))
    await db.commit(); await db.refresh(payment); return await _record_dict_for_identity(payment, identity, db)


@router.post(f"{settings.api_prefix}/contract-payment-applications/{{payment_id}}/writeoff")
async def writeoff_contract_payment_application(payment_id: int, body: ContractPaymentWriteoffInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _require_contract_action,
    )
    await _require_contract_action(identity, db, "contract.payment.writeoff", "核销付款")
    payment = await _ensure_record_module(payment_id, "contract_payment", identity, db)
    data = dict(payment.data or {})
    if data.get("writeoff_status") == "已核销" or payment.status == "已核销":
        raise HTTPException(status_code=409, detail="合同付款已经核销")
    if payment.status != "已付款":
        raise HTTPException(status_code=409, detail="仅已付款合同付款申请可以核销")
    payment_total = float(await db.scalar(select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(
        FinanceTransaction.finance_record_id == payment.id,
        FinanceTransaction.transaction_type == "合同付款",
    )) or 0)
    amount = abs(float(data.get("amount") or 0))
    if payment_total + 0.001 < amount:
        raise HTTPException(status_code=409, detail="合同付款流水合计未达到申请金额，不能核销")
    payment.status = "已核销"
    payment.data = {
        **data,
        "writeoff_status": "已核销",
        "writeoff_date": body.writeoff_date.isoformat(),
        "writeoff_voucher_no": body.voucher_no.strip(),
        "writeoff_comment": body.comment.strip(),
        "written_off_by": identity["username"],
        "written_off_at": datetime.now().isoformat(timespec="seconds"),
    }
    db.add(WorkflowEvent(record_id=payment.id, action="合同付款核销", from_status="已付款", to_status="已核销", operator=identity["username"], comment=f"核销凭证：{body.voucher_no.strip()}；{body.comment.strip()}"))
    await db.commit(); await db.refresh(payment)
    return await _record_dict_for_identity(payment, identity, db)


@router.get(f"{settings.api_prefix}/contracts/{{contract_id}}/changes")
async def contract_changes(contract_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_visible,
    )
    contract = await _ensure_record_visible(contract_id, identity, db)
    if contract.module != "contract": raise HTTPException(status_code=404, detail="合同不存在")
    events = (await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == contract.id, WorkflowEvent.action.in_(["提交合同变更", "合同变更审批通过", "合同变更审批驳回"])).order_by(WorkflowEvent.created_at.desc(), WorkflowEvent.id.desc()))).all()
    items = []
    for event in events:
        try: detail = json.loads(event.comment or "{}")
        except json.JSONDecodeError: detail = {"reason": event.comment}
        items.append({"id": event.id, "operator": event.operator, "created_at": event.created_at, **detail})
    return {"items": items, "total": len(items)}


@router.post(f"{settings.api_prefix}/contracts/{{contract_id}}/changes", status_code=status.HTTP_201_CREATED)
async def change_contract(contract_id: int, body: ContractChangeInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _normalize_external_contract_numbers,
    )
    from app.core.permissions import (
        _ensure_record_visible, _record_dict_for_identity, _require_contract_action, _require_record_owner_or_manager,
    )
    contract = await _ensure_record_visible(contract_id, identity, db)
    if contract.module != "contract": raise HTTPException(status_code=404, detail="合同不存在")
    await _require_contract_action(identity, db, "contract.application.change", "发起变更")
    await _require_record_owner_or_manager(contract, identity, db)
    if contract.status != CONTRACT_APPROVED_STATUS: raise HTTPException(status_code=409, detail="只有审批通过的合同可以发起变更")
    data = dict(contract.data or {}); changes = []
    if (data.get("pending_change") or {}).get("status") == "待审批":
        raise HTTPException(status_code=409, detail="已有合同变更正在审批")
    requested_external_numbers = body.external_contract_numbers
    if requested_external_numbers is None and body.external_contract_no is not None:
        requested_external_numbers = [body.external_contract_no]
    normalized_external_numbers = None
    if requested_external_numbers is not None:
        normalized_external_numbers = _normalize_external_contract_numbers({"external_contract_numbers": requested_external_numbers})["external_contract_numbers"]
    candidates = {
        "contract_body": (data.get("contract_body", ""), body.contract_body),
        "contract_type": (data.get("type", ""), body.contract_type),
        "fee_type": (data.get("fee_type", ""), body.fee_type),
        "title": (contract.title, body.title),
        "amount": (data.get("amount"), body.amount),
        "description": (data.get("description", ""), body.description),
        "external_contract_numbers": (data.get("external_contract_numbers") or ([data.get("external_contract_no")] if data.get("external_contract_no") else []), normalized_external_numbers),
        "end_date": (data.get("end_date", ""), str(body.end_date) if body.end_date else None),
    }
    labels = {"contract_body": "合同主体", "contract_type": "合同类别", "fee_type": "收费模式", "title": "合同名称", "amount": "合同金额", "description": "备注", "external_contract_numbers": "外部合同号", "end_date": "合同期限"}
    for key, (before, after) in candidates.items():
        if after is not None and after != before:
            changes.append({"field": key, "label": labels[key], "before": before, "after": after})
    if not changes: raise HTTPException(status_code=422, detail="至少填写一项发生变化的合同内容")
    detail = {"status": "待审批", "change_type": body.change_type.strip(), "reason": body.reason.strip(), "changes": changes, "requested_by": identity["username"], "requested_at": datetime.now().isoformat(timespec="seconds")}
    contract.data = {**data, "pending_change": detail}
    db.add(WorkflowEvent(record_id=contract.id, action="提交合同变更", from_status=contract.status, to_status=contract.status, operator=identity["username"], comment=json.dumps(detail, ensure_ascii=False)))
    await db.commit(); await db.refresh(contract)
    return {"contract": await _record_dict_for_identity(contract, identity, db), **detail}


@router.post(f"{settings.api_prefix}/contracts/{{contract_id}}/changes/review")
async def review_contract_change(contract_id: int, body: ContractChangeReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _normalize_external_contract_numbers,
    )
    from app.core.permissions import (
        _ensure_record_visible, _record_dict_for_identity, _require_contract_action,
    )
    await _require_contract_action(identity, db, "contract.application.change.approve", "审批合同变更")
    contract = await _ensure_record_visible(contract_id, identity, db)
    if contract.module != "contract": raise HTTPException(status_code=404, detail="合同不存在")
    data = dict(contract.data or {}); pending = data.get("pending_change") or {}
    if pending.get("status") != "待审批": raise HTTPException(status_code=409, detail="该合同没有待审批的变更")
    if not body.approved and not body.comment.strip(): raise HTTPException(status_code=422, detail="驳回时必须填写原因")
    if body.approved:
        for change in pending.get("changes", []):
            key = change.get("field"); value = change.get("after")
            if key == "title": contract.title = str(value)
            elif key == "external_contract_numbers": data = _normalize_external_contract_numbers({**data, "external_contract_numbers": value})
            elif key == "contract_type": data["type"] = value
            elif key in {"amount", "end_date"}: data[key] = value
            elif key in {"contract_body", "fee_type", "description"}: data[key] = value
        data["last_changed_at"] = datetime.now().isoformat(timespec="seconds")
        data["change_count"] = int(data.get("change_count", 0)) + 1
    reviewed = {**pending, "status": "已通过" if body.approved else "已驳回", "reviewed_by": identity["username"], "reviewed_at": datetime.now().isoformat(timespec="seconds"), "review_comment": body.comment.strip()}
    contract.data = {**data, "pending_change": reviewed}
    action = "合同变更审批通过" if body.approved else "合同变更审批驳回"
    db.add(WorkflowEvent(record_id=contract.id, action=action, from_status=contract.status, to_status=contract.status, operator=identity["username"], comment=json.dumps(reviewed, ensure_ascii=False)))
    await db.commit(); await db.refresh(contract)
    return {"contract": await _record_dict_for_identity(contract, identity, db), **reviewed}


@router.post(f"{settings.api_prefix}/contracts/{{contract_id}}/attachments/delete")
async def batch_delete_contract_attachments(contract_id: int, body: ContractAttachmentBatchDeleteInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Legacy FCM-style batch delete for contract files with a 200 envelope."""
    from app.core.permissions import (
        _ensure_record_module, _require_contract_attachment_write_access,
    )
    ids = list(dict.fromkeys([int(item_id) for item_id in [*body.file_ids, *body.fileIds, *body.attachment_ids] if int(item_id) > 0]))
    staged: list[tuple[Path, Path]] = []
    try:
        if not ids:
            raise HTTPException(status_code=422, detail="请选择要删除的合同附件")
        contract = await _ensure_record_module(contract_id, "contract", identity, db)
        await _require_contract_attachment_write_access(contract, identity, db)
        attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.id.in_(ids)))).all())
        if len(attachments) != len(ids):
            raise HTTPException(status_code=422, detail="所选合同附件不存在或已删除")
        by_id = {item.id: item for item in attachments}
        ordered = [by_id[item_id] for item_id in ids]
        prepared: list[tuple[FileAttachment, Path]] = []
        for item in ordered:
            if not item.record_id == contract_id:
                raise HTTPException(status_code=422, detail="所选文件不属于当前合同")
            if item.category != "合同附件":
                raise HTTPException(status_code=422, detail="所选文件不是合同附件")
            await _require_contract_attachment_write_access(contract, identity, db)
            path = Path(item.path)
            if not path.is_file() or UPLOAD_ROOT.resolve() not in path.resolve().parents:
                raise HTTPException(status_code=422, detail=f"合同附件文件 {item.original_name} 不存在")
            prepared.append((item, path))
        for item, path in prepared:
            staged_path = path.with_name(f".contract-delete-{uuid4().hex}-{path.name}")
            path.replace(staged_path)
            staged.append((path, staged_path))
        for item, _ in prepared:
            await db.delete(item)
            db.add(WorkflowEvent(record_id=contract.id, action="批量删除合同附件", from_status=contract.status, to_status=contract.status, operator=identity["username"], comment=f"合同附件：{item.original_name}"))
        await db.commit()
    except HTTPException as exc:
        await db.rollback()
        for original, staged_path in reversed(staged):
            if staged_path.is_file():
                staged_path.replace(original)
        return JSONResponse(status_code=status.HTTP_200_OK, content={"IsSuccess": False, "Message": str(exc.detail), "fileIds": ids})
    except Exception:
        await db.rollback()
        for original, staged_path in reversed(staged):
            if staged_path.is_file():
                staged_path.replace(original)
        raise
    for _, staged_path in staged:
        try:
            staged_path.unlink(missing_ok=True)
        except OSError:
            logger.exception("无法清理已删除的合同附件临时文件: %s", staged_path)
    return {"IsSuccess": True, "Message": "删除成功！", "fileIds": ids, "deleted": len(prepared)}
