"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.constants import (
    CASE_EXECUTION_STATUSES, CASE_PARTY_SEPARATOR, CONTRACT_APPROVED_STATUS, DEFAULT_MENU_LABEL_BY_KEY, FIELD_KEYS,
    FIELD_PERMISSION_DATA_KEYS, HR_SUBRECORD_KINDS, IPR_CASE_KINDS, MENU_PARENT_BY_KEY, PARAMETER_REFERENCE_FIELDS,
    RECORD_MODULE_MENU_ROOTS, RECORD_PERSON_FIELDS_BY_MODULE, RECORD_PERSON_LIST_FIELDS_BY_MODULE, SYSTEM_CACHE_META, SYSTEM_CACHE_REGISTRY,
    SYSTEM_MENU_ROUTE_KEYS, SYSTEM_PARAMETER_CACHE, SYSTEM_PARAMETER_CATEGORIES, SYSTEM_PARAMETER_RELATION_CONFIG,
)
from app.core.dependencies import (
    AgentDocument, AsyncSession, BaseModel, BusinessRecord, CaseFileTypeFeeTypeRelation,
    CaseTypeCasePhaseRelation, CaseTypeFileTypeRelation, CommunicationLog, ContractApprovalStep, Department,
    FileAttachment, FinanceTransaction, HTTPException, HearingSchedule, HrSubrecord,
    IncomingPayment, JobRole, Notification, OfficialOutgoingDocument, ReconciliationBatch,
    Response, SealAsset, SecurityPolicy, SessionLocal, String,
    SystemConfig, SystemMenu, SystemParameter, User, VipTask,
    VipTaskMessage, VipTaskNode, WorkflowEvent, asyncio, create_token,
    csv, date, datetime, func, hashlib,
    io, json, math, or_, quote,
    re, select, settings, update, uuid4,
    xml_escape,
)
from app.models_shared import (
    HrEmployeeBatchDeleteInput,
)


def _record_dict(record: BusinessRecord, allowed_fields: set[str] | None = None) -> dict:
    from app.core.crm import (
        _customer_contact_dict, _customer_guid,
    )
    data = dict(record.data or {})
    if record.module == "customer":
        data["contacts"] = [_customer_contact_dict(item) for item in list(data.get("contacts") or [])]
    if allowed_fields is not None:
        for permission, keys in FIELD_PERMISSION_DATA_KEYS.items():
            if permission not in allowed_fields:
                for key in keys: data.pop(key, None)
    result = {
        "id": record.id, "module": record.module, "serial_no": record.serial_no,
        "title": record.title, "customer": record.customer, "status": record.status,
        "owner": record.owner, "department": record.department,
        "description": record.description, "data": data,
        "created_at": record.created_at, "updated_at": record.updated_at,
    }
    if record.module == "ipr_case":
        result.update({
            "case_phase": data.get("case_phase", ""),
            "acceptance_date": data.get("accepted_at") or data.get("acceptance_date") or data.get("register_date") or "",
            "case_source": data.get("case_source") or data.get("case_origin_people_name") or data.get("origin_people_name") or "",
            "source_date": data.get("case_origin_date") or data.get("origin_date") or data.get("source_date") or "",
            "agent": data.get("agent") or data.get("procurator_name") or "",
            "writer": data.get("copywriter_name") or data.get("writer") or "",
            "handler": data.get("case_officer_name") or data.get("case_manager") or record.owner,
            "submitter": data.get("case_submitter_name") or data.get("submitter_name") or data.get("submitter") or "",
            "submit_date": data.get("case_submit_date") or data.get("submit_date") or "",
            "inventor": data.get("case_inventor") or data.get("inventor") or "",
            "deadline": data.get("deadline", ""),
            "contract_no": data.get("contract_no", ""),
            "contract_record_id": data.get("contract_record_id"),
        })
    if record.module == "customer":
        result["customer_guid"] = _customer_guid(record)
    return result


def _positive_record_id(value: object) -> int:
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed > 0 else 0


def _record_person_usernames(record: BusinessRecord) -> set[str]:
    from app.core.contracts import (
        _contract_person_values,
    )
    data = record.data or {}
    usernames = {str(record.owner or "").strip()}
    for key in RECORD_PERSON_FIELDS_BY_MODULE.get(record.module, ()):
        value = str(data.get(key) or "").strip()
        if value:
            if record.module == "case" and key == "assistant_username":
                usernames.update(_contract_person_values(value))
            else:
                usernames.add(value)
    for key in RECORD_PERSON_LIST_FIELDS_BY_MODULE.get(record.module, ()):
        usernames.update(_contract_person_values(data.get(key)))
    if record.module == "case":
        hearing_username = str(data.get("hearing_lawyer_username") or "").strip()
        if hearing_username:
            usernames.add(hearing_username)
    # `Legal_Case_Participant` is a real case membership relation from the
    # legacy database.  It is separate from the case's role fields and must
    # participate in both display-name resolution and case visibility.
    if record.module == "case":
        for participant in data.get("legacy_participants") or []:
            if isinstance(participant, dict):
                username = str(participant.get("staff_name") or "").strip()
                if username:
                    usernames.add(username)
    return {value for value in usernames if value}


def _explicit_vip_value(value: object) -> bool:
    """Recognize only an explicit VIP marker, never a general key-customer label."""
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().casefold() in {"1", "true", "yes", "是", "vip"}
    return isinstance(value, (int, float)) and value == 1


def _seed_business_records() -> list[BusinessRecord]:
    rows = [
        ("customer", "KH20260714001", "光明乳业股份有限公司", "光明乳业股份有限公司", "正常", "朱菁芸", {"contact": "法务部", "phone": "021-12345678", "level": "重点客户"}),
        ("customer", "KH20260714002", "萨普托乳业（中国）有限公司", "萨普托乳业（中国）有限公司", "跟进中", "朱淑旖", {"contact": "品牌保护部", "phone": "021-87654321", "level": "重点客户"}),
        ("contract", "HT2026070018", "知识产权维权专项法律服务合同", "迈大食品（上海）有限公司", "审批中", "陈名涛", {"amount": "280000.00", "signed_at": "2026-07-08", "type": "专项服务"}),
        ("contract", "HT2026060097", "常年法律顾问合同", "上海天路人造草坪有限公司", CONTRACT_APPROVED_STATUS, "陶勇刚", {"amount": "120000.00", "signed_at": "2026-06-20", "type": "法律顾问"}),
        ("case", "SH191000382B", "光明乳业商标侵权纠纷", "光明乳业股份有限公司", "文书准备", "陈名涛", {"court": "上海市宝山区人民法院", "case_type": "民事案件", "opponent": "安徽鑫牛食品有限公司"}),
        ("case", "SHMS2600387", "龙角散商标侵权纠纷", "株式会社龙角散", "一审立案受理", "陶勇刚", {"court": "杭州市余杭区人民法院", "case_type": "民事案件", "opponent": "杭州取道贸易有限公司"}),
        ("task", "RW20260714001", "准备开庭代理词及证据目录", "上海天路人造草坪有限公司", "处理中", "陶勇刚", {"deadline": "2026-07-15", "priority": "紧急", "source": "案件任务"}),
        ("task", "RW20260714002", "审核合同付款节点", "迈大食品（上海）有限公司", "待处理", "朱淑旖", {"deadline": "2026-07-17", "priority": "普通", "source": "合同任务"}),
        ("clue", "XS2026070015", "线上店铺销售疑似侵权产品", "北京汇源食品饮料有限公司", "待审批", "卢愿", {"platform": "淘宝", "product": "果汁饮料", "notary": "待申请"}),
        ("seal", "YY2026070042", "民事起诉状用印申请", "株式会社龙角散", "待审批", "陶勇刚", {"seal_type": "公章", "copies": 3, "purpose": "法院立案"}),
        ("finance", "FY2026070093", "上海市宝山区人民法院诉讼费", "光明乳业股份有限公司", "待审批", "陈名涛", {"amount": "3500.00", "fee_type": "官方费用", "case_no": "SH191000382B"}),
        ("document", "SW2026070031", "上海市徐汇区人民法院开庭传票", "上海益民食品一厂有限公司", "已签收", "江彤", {"direction": "收文", "received_at": "2026-07-14", "case_no": "SHMS2200026"}),
    ]
    return [BusinessRecord(module=m, serial_no=no, title=title, customer=customer, status=st, owner=owner, data=data) for m, no, title, customer, st, owner, data in rows]


async def _system_audit(db: AsyncSession, identity: dict, action: str, target: str, detail: dict | None = None) -> None:
    """Write system-center audit rows in the caller's transaction."""
    record = BusinessRecord(
        module="system_audit",
        serial_no=f"SYS-AUDIT-{uuid4().hex}",
        title=target,
        status="已完成",
        owner=str(identity.get("username") or "system"),
        department="系统",
        data=detail or {},
    )
    db.add(record)
    await db.flush()
    db.add(WorkflowEvent(
        record_id=record.id,
        action=action,
        from_status="",
        to_status="已完成",
        operator=str(identity.get("username") or "system"),
        comment=json.dumps(detail or {}, ensure_ascii=False, separators=(",", ":")),
    ))


def _menu_root(menu_key: str) -> str:
    """Return the configured top-level menu for a grantable menu key."""
    current = menu_key
    seen: set[str] = set()
    while MENU_PARENT_BY_KEY.get(current) and current not in seen:
        seen.add(current)
        current = MENU_PARENT_BY_KEY[current]
    return current


def _record_module_menu_roots(module: str) -> tuple[str, ...]:
    """Map generic-record modules to their owning business menu families.

    This is deliberately used only for direct generic operations.  Cross-module
    selectors retain their narrow, scoped lookup paths instead of receiving a
    broad record-list grant merely because a form needs to reference a customer
    or case.
    """
    roots = RECORD_MODULE_MENU_ROOTS.get(module)
    if not roots:
        raise HTTPException(status_code=422, detail="该业务模块不支持通用操作")
    return roots


def _record_module_menu_allowed(module: str, identity: dict, permission: dict) -> bool:
    """Return whether a module is readable from the caller's effective menu tree."""
    from app.core.permissions import (
        _identity_role_ids,
    )
    if "admin" in _identity_role_ids(identity):
        return True
    roots = RECORD_MODULE_MENU_ROOTS.get(module)
    if not roots:
        return False
    granted_roots = {_menu_root(key) for key in permission.get("menu_keys", [])}
    return bool(set(roots).intersection(granted_roots))


async def _allowed_field_keys(identity: dict, db: AsyncSession) -> set[str]:
    from app.core.permissions import (
        _identity_role_ids, _permission_payload_for_identity, _user_permission_overrides,
    )
    role_ids = _identity_role_ids(identity)
    if "admin" in role_ids:
        return set(FIELD_KEYS)
    permission = await _permission_payload_for_identity(identity, db)
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if user:
        overrides = _user_permission_overrides(user)
        if overrides.get("field_keys") is not None:
            return set(overrides["field_keys"])
    return set(permission["field_keys"])


def _is_smoke_test_username(username: object) -> bool:
    """Only hide explicitly generated smoke accounts; recorded English names stay valid."""
    return str(username or "").strip().casefold().startswith("smoke_")


async def _active_employee_usernames(db: AsyncSession) -> set[str]:
    """Return active staff login identities backed by an active HR record."""
    employees = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "hr",
        BusinessRecord.status.not_in({"离职", "停用"}),
    ))).all()
    return {
        username
        for item in employees
        for username in [str((item.data or {}).get("username") or item.owner or "").strip().lower()]
        if username
        and str((item.data or {}).get("account_type") or "员工账号").strip() == "员工账号"
        and not _is_smoke_test_username(username)
    }


async def _security_policy(db: AsyncSession) -> SecurityPolicy:
    policy = await db.get(SecurityPolicy, 1)
    if not policy:
        policy = SecurityPolicy(id=1, min_password_length=8, max_failed_attempts=5, lock_minutes=30, token_minutes=settings.access_token_minutes, updated_by="system")
        db.add(policy); await db.flush()
    return policy


def _security_policy_dict(policy: SecurityPolicy) -> dict:
    return {"min_password_length": policy.min_password_length, "max_failed_attempts": policy.max_failed_attempts, "lock_minutes": policy.lock_minutes, "token_minutes": policy.token_minutes, "updated_by": policy.updated_by, "updated_at": policy.updated_at}


async def _login_response(user: User, db: AsyncSession, *, require_password_change: bool | None = None) -> dict:
    from app.core.permissions import (
        _system_user_role_ids, _user_permission_payload,
    )
    policy = await _security_policy(db)
    permission = await _user_permission_payload(user, db)
    role_ids = _system_user_role_ids(user)
    must_change = user.must_change_password if require_password_change is None else require_password_change
    return {
        "access_token": create_token(user.username, role_ids[0], policy.token_minutes),
        "token_type": "bearer",
        "expires_in": policy.token_minutes * 60,
        "must_change_password": must_change,
        "user": {
            "username": user.username,
            "display_name": user.display_name,
            "department": user.department,
            "role": role_ids[0],
            "role_ids": role_ids,
            "must_change_password": must_change,
            **permission,
        },
    }


def _system_user_dict(user: User) -> dict:
    from app.core.formatters import (
        _person_display_name,
    )
    from app.core.permissions import (
        _system_user_role_ids,
    )
    profile = user.profile or {}
    role_ids = _system_user_role_ids(user)
    person_name, person_name_missing = _person_display_name(user.display_name, user.username)
    manager_name, manager_name_missing = _person_display_name(profile.get("manager_name", ""), "")
    return {"id": user.id, "username": user.username, "display_name": user.display_name, "person_display_name": person_name, "display_name_missing": person_name_missing, "department": user.department, "role": role_ids[0], "role_ids": role_ids, "is_active": user.is_active, "must_change_password": user.must_change_password, "profile": profile, "contract_approval_enabled": bool(profile.get("contract_approval_enabled")), "dingtalk_user_id": profile.get("dingtalk_user_id", ""), "dingtalk_bound": bool(profile.get("dingtalk_user_id")), "email": profile.get("email", ""), "office_phone": profile.get("office_phone", ""), "mobile": profile.get("mobile", ""), "menu_auto_collapse": profile.get("menu_auto_collapse", "no"), "manager_id": profile.get("manager_id"), "manager_name": profile.get("manager_name", ""), "manager_person_display_name": manager_name if profile.get("manager_id") else "", "manager_name_missing": manager_name_missing if profile.get("manager_id") else False, "access_level": profile.get("access_level", ""), "lead_rate": profile.get("lead_rate", ""), "copy_rate": profile.get("copy_rate", ""), "failed_login_attempts": user.failed_login_attempts or 0, "locked_until": user.locked_until, "last_login_at": user.last_login_at, "password_changed_at": user.password_changed_at, "created_at": user.created_at}


async def _system_user_manager_profile(manager_id: int | None, db: AsyncSession) -> dict:
    if not manager_id:
        return {"manager_id": None, "manager_name": ""}
    manager = await db.get(User, manager_id)
    if not manager or not manager.is_active:
        raise HTTPException(status_code=422, detail="上级领导不存在或已停用")
    return {"manager_id": manager.id, "manager_name": manager.display_name}


def _replace_username_value(value: object, old_username: str, new_username: str) -> object:
    """Replace exact username tokens in JSON data without touching free text."""
    if isinstance(value, str):
        return new_username if value == old_username else value
    if isinstance(value, list):
        return [_replace_username_value(item, old_username, new_username) for item in value]
    if isinstance(value, dict):
        return {key: _replace_username_value(item, old_username, new_username) for key, item in value.items()}
    return value


async def _rename_system_username(user: User, requested_username: str, identity: dict, db: AsyncSession) -> str:
    new_username = requested_username.strip().lower()
    old_username = user.username
    if not re.fullmatch(r"[a-z0-9._-]{2,64}", new_username):
        raise HTTPException(status_code=422, detail="登录账号只能包含小写字母、数字、点、下划线或短横线")
    if new_username == old_username:
        return old_username
    if old_username == identity["username"]:
        raise HTTPException(status_code=409, detail="不能在当前登录会话中修改自己的登录账号，请由其他管理员操作")
    if await db.scalar(select(User.id).where(User.username == new_username, User.id != user.id)):
        raise HTTPException(status_code=409, detail="登录账号已存在")

    scalar_references = (
        (Department, Department.manager), (Department, Department.created_by), (Department, Department.updated_by),
        (JobRole, JobRole.created_by), (JobRole, JobRole.updated_by),
        (SecurityPolicy, SecurityPolicy.updated_by), (SystemParameter, SystemParameter.created_by),
        (SystemParameter, SystemParameter.updated_by), (SystemConfig, SystemConfig.updated_by),
        (SystemMenu, SystemMenu.updated_by), (BusinessRecord, BusinessRecord.owner),
        (WorkflowEvent, WorkflowEvent.operator), (HrSubrecord, HrSubrecord.created_by),
        (HrSubrecord, HrSubrecord.updated_by), (HearingSchedule, HearingSchedule.hearing_lawyer),
        (FileAttachment, FileAttachment.uploader), (FinanceTransaction, FinanceTransaction.operator),
        (ReconciliationBatch, ReconciliationBatch.operator), (IncomingPayment, IncomingPayment.claimant),
        (IncomingPayment, IncomingPayment.operator), (ContractApprovalStep, ContractApprovalStep.approver),
        (Notification, Notification.sender), (Notification, Notification.recipient),
        (CommunicationLog, CommunicationLog.operator), (AgentDocument, AgentDocument.creator),
        (AgentDocument, AgentDocument.confirmed_by), (SealAsset, SealAsset.custodian),
    )
    for model, field in scalar_references:
        await db.execute(update(model).where(field == old_username).values({field.key: new_username}))

    for record in (await db.scalars(select(BusinessRecord))).all():
        replaced = _replace_username_value(record.data or {}, old_username, new_username)
        if replaced != (record.data or {}):
            record.data = replaced
    for payment in (await db.scalars(select(IncomingPayment))).all():
        replaced = _replace_username_value(payment.allocations or [], old_username, new_username)
        if replaced != (payment.allocations or []):
            payment.allocations = replaced
    for config in (await db.scalars(select(SystemConfig))).all():
        replaced = _replace_username_value(config.value or {}, old_username, new_username)
        if replaced != (config.value or {}):
            config.value = replaced
    user.profile = _replace_username_value(user.profile or {}, old_username, new_username)
    user.username = new_username
    return new_username


def _system_parameter_dict(item: SystemParameter) -> dict:
    return {
        "id": item.id, "category": item.category, "category_name": SYSTEM_PARAMETER_CATEGORIES.get(item.category, item.category),
        "code": item.code, "name": item.name, "extra": item.extra or {}, "sort_order": item.sort_order,
        "is_active": item.is_active, "created_by": item.created_by, "updated_by": item.updated_by,
        "created_at": item.created_at, "updated_at": item.updated_at,
    }


def _clear_parameter_cache(category: str | None = None, operator: str = "system") -> None:
    if category:
        SYSTEM_PARAMETER_CACHE.pop(category, None)
        SYSTEM_PARAMETER_CACHE.pop("__all__", None)
    else:
        SYSTEM_PARAMETER_CACHE.clear()
    SYSTEM_CACHE_META["system-parameters"] = {"last_cleared_at": datetime.now().isoformat(), "last_cleared_by": operator}


def _system_parameter_relation_config(kind: str):
    config = SYSTEM_PARAMETER_RELATION_CONFIG.get(kind)
    if config is None:
        raise HTTPException(status_code=404, detail="参数关联类型不存在")
    return config


async def _validate_parameter_references(category: str, extra: dict, db: AsyncSession) -> None:
    """Keep dependent master data from becoming orphaned through the generic parameter API."""
    if category == "ipr_case_file_type":
        case_kinds = (extra or {}).get("case_kinds") or []
        if not isinstance(case_kinds, list) or any(value not in IPR_CASE_KINDS for value in case_kinds):
            raise HTTPException(status_code=422, detail="知识产权案件文件类型的适用案件类型必须是专利或商标")
        for key in {"is_official", "requires_transmission", "allow_repeat"}:
            if key in (extra or {}) and not isinstance(extra[key], bool):
                raise HTTPException(status_code=422, detail=f"知识产权案件文件类型的 {key} 必须为布尔值")
        for key in {"hedging_file_type_codes", "hedging_fee_type_codes"}:
            value = (extra or {}).get(key) or []
            if not isinstance(value, list) or any(not isinstance(code, str) or not code.strip() for code in value):
                raise HTTPException(status_code=422, detail=f"知识产权案件文件类型的 {key} 必须为代码数组")
        return
    if category == "payment_type":
        required = {"nature": "付款性质", "payee": "收款单位", "account_bank": "开户行", "account": "账号信息"}
        missing = [label for key, label in required.items() if not str((extra or {}).get(key) or "").strip()]
        if missing:
            raise HTTPException(status_code=422, detail="付款单位必须填写：" + "、".join(missing))
        return
    if category != "court_officer":
        return
    court_code = str((extra or {}).get("court_code") or "").strip()
    role = str((extra or {}).get("role") or "").strip()
    if not court_code or not role:
        raise HTTPException(status_code=422, detail="法院工作人员必须填写法院代码和职务")
    court = await db.scalar(select(SystemParameter).where(
        SystemParameter.category == "court", SystemParameter.code == court_code, SystemParameter.is_active.is_(True)
    ))
    if not court:
        raise HTTPException(status_code=422, detail="关联法院不存在或已停用")


async def _validate_parameter_parent(category: str, code: str, extra: dict, db: AsyncSession, current_id: int | None = None) -> None:
    """Validate hierarchical parameter links without allowing orphan or cyclic trees."""
    if category not in {"fee_type", "case_phase", "cause", "case_file_type"}:
        return
    parent_code = str((extra or {}).get("parent_code") or "").strip()
    if not parent_code:
        return
    if parent_code == code:
        raise HTTPException(status_code=422, detail="父级参数不能引用自身")
    parent = await db.scalar(select(SystemParameter).where(
        SystemParameter.category == category,
        SystemParameter.code == parent_code,
        SystemParameter.is_active.is_(True),
    ))
    if not parent or (current_id is not None and parent.id == current_id):
        raise HTTPException(status_code=422, detail="父级参数不存在")
    seen = {code}
    cursor = parent
    while cursor:
        if cursor.code in seen:
            raise HTTPException(status_code=422, detail="参数父级关系存在循环引用")
        seen.add(cursor.code)
        next_code = str((cursor.extra or {}).get("parent_code") or "").strip()
        if not next_code:
            break
        cursor = await db.scalar(select(SystemParameter).where(
            SystemParameter.category == category,
            SystemParameter.code == next_code,
            SystemParameter.is_active.is_(True),
        ))
        if cursor is None:
            raise HTTPException(status_code=422, detail="父级参数不存在")


async def _parameter_reference_examples(item: SystemParameter, db: AsyncSession) -> list[str]:
    """Return a small, exact sample of business references before parameter deletion.

    Parameters remain historical master data.  Deleting one that is already in a
    customer, case or attachment would make existing records impossible to
    interpret, so the generic maintenance endpoint must reject it instead.
    """
    relation_checks = (
        (CaseTypeFileTypeRelation, CaseTypeFileTypeRelation.case_type_id, "案件类型-文件类型关联"),
        (CaseTypeFileTypeRelation, CaseTypeFileTypeRelation.file_type_id, "案件类型-文件类型关联"),
        (CaseFileTypeFeeTypeRelation, CaseFileTypeFeeTypeRelation.file_type_id, "文件类型-费用类型关联"),
        (CaseFileTypeFeeTypeRelation, CaseFileTypeFeeTypeRelation.fee_type_id, "文件类型-费用类型关联"),
        (CaseTypeCasePhaseRelation, CaseTypeCasePhaseRelation.case_type_id, "案件类型-案件阶段关联"),
        (CaseTypeCasePhaseRelation, CaseTypeCasePhaseRelation.case_phase_id, "案件类型-案件阶段关联"),
    )
    for model, field, label in relation_checks:
        if await db.scalar(select(model.id).where(field == item.id).limit(1)):
            return [label]
    if item.category == "fee_type":
        children = list((await db.scalars(select(SystemParameter).where(
            SystemParameter.category == "fee_type",
            SystemParameter.extra["parent_code"].as_string() == item.code,
        ).limit(3))).all())
        if children:
            return [f"下级费用类型：{child.name}" for child in children]
        records = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "finance",
            or_(
                BusinessRecord.data["fee_type_id"].as_integer() == item.id,
                BusinessRecord.data["fee_type_code"].as_string() == item.code,
                BusinessRecord.data["expense_subtype"].as_string() == item.name,
            ),
        ).limit(3))).all())
        if records:
            return [record.serial_no for record in records]
    if item.category == "case_file_type":
        attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.category == item.name).limit(3))).all())
        return [f"附件#{attachment.id}" for attachment in attachments]
    if item.category == "case_phase":
        records = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "case", BusinessRecord.status == item.name).limit(3))).all())
        return [record.serial_no for record in records]
    fields_by_module = PARAMETER_REFERENCE_FIELDS.get(item.category, {})
    examples: list[str] = []
    for module, fields in fields_by_module.items():
        records = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == module))).all())
        for record in records:
            data = record.data or {}
            if any(str(data.get(field) or "").strip() == item.name for field in fields):
                examples.append(record.serial_no)
                if len(examples) >= 3:
                    return examples
    return examples


def _validate_system_config(key: str, value: dict) -> dict:
    if key == "customer_share_policy":
        required = {"all_days", "filed_days", "premium_days", "standard_days", "basic_days", "shared_days"}
        if set(value) != required or any(isinstance(value[name], bool) or not isinstance(value[name], int) or not 1 <= value[name] <= 3650 for name in required):
            raise HTTPException(status_code=422, detail="客户共享天数必须完整填写，范围为 1 至 3650 天")
    elif key == "company_profile":
        required = {"name", "code", "short_code", "address", "phone", "fax", "email", "postal_code", "bank_name", "bank_account", "bank_address"}
        if set(value) != required or any(not isinstance(value[name], str) for name in required) or not all(str(value[name]).strip() for name in {"name", "code", "short_code"}):
            raise HTTPException(status_code=422, detail="公司名称、代码和字母短写代码必填，且公司资料字段必须完整")
        value = {name: str(value[name]).strip() for name in required}
    elif key == "application_settings":
        required = {"system_name", "default_department", "page_size", "attachment_limit_mb", "maintenance_mode"}
        if set(value) != required or not isinstance(value["maintenance_mode"], bool) or not isinstance(value["page_size"], int) or not 10 <= value["page_size"] <= 200 or not isinstance(value["attachment_limit_mb"], int) or not 1 <= value["attachment_limit_mb"] <= 100:
            raise HTTPException(status_code=422, detail="系统配置字段或数值范围无效")
        if not str(value["system_name"]).strip() or not str(value["default_department"]).strip(): raise HTTPException(status_code=422, detail="系统名称和默认部门必填")
    elif key == "investigation_assignment":
        if set(value) != {"supervisor_username"} or not isinstance(value["supervisor_username"], str):
            raise HTTPException(status_code=422, detail="调查任务分配人配置无效")
        value = {"supervisor_username": value["supervisor_username"].strip()}
    else:
        raise HTTPException(status_code=404, detail="系统配置不存在")
    return value


async def _system_cache_entry_count(cache_key: str, definition: dict, db: AsyncSession) -> int:
    category = definition.get("category")
    if category:
        if category == "__all__":
            return sum(len(items) for items in SYSTEM_PARAMETER_CACHE.values())
        return len(SYSTEM_PARAMETER_CACHE.get(category, []))
    return 0


def _registered_cache_is_clearable(definition: dict) -> bool:
    """Only expose a clear operation for a cache this process actually owns."""
    return bool(definition.get("category"))


def _clear_registered_cache(cache_key: str, operator: str) -> None:
    definition = SYSTEM_CACHE_REGISTRY[cache_key]
    category = definition.get("category")
    if not category:
        raise HTTPException(status_code=409, detail="该项目当前为直接 SQL 查询，未启用可清理缓存")
    _clear_parameter_cache(None if category == "__all__" else category, operator)
    SYSTEM_CACHE_META[cache_key] = {"last_cleared_at": datetime.now().isoformat(), "last_cleared_by": operator}


def _clear_all_system_parameter_cache(operator: str) -> list[str]:
    """Clear every populated dictionary bucket and update all cache metadata."""
    cleared_buckets = list(SYSTEM_PARAMETER_CACHE)
    _clear_parameter_cache(None, operator)
    cleared_at = datetime.now().isoformat()
    for key, definition in SYSTEM_CACHE_REGISTRY.items():
        if _registered_cache_is_clearable(definition):
            SYSTEM_CACHE_META[key] = {"last_cleared_at": cleared_at, "last_cleared_by": operator}
    return cleared_buckets


async def _system_cache_list_payload(keyword: str, page: int | None, page_size: int | None, db: AsyncSession) -> dict:
    """Build cache facts from the in-process cache only; never inspect Redis queues or credentials."""
    # system-parameters is an internal aggregate alias; the eight visible rows
    # keep the legacy CacheList names while showing whether each is cache-backed.
    keys = [key for key in SYSTEM_CACHE_REGISTRY if key != "system-parameters"]
    rows = []
    for key in keys:
        definition = SYSTEM_CACHE_REGISTRY[key]
        clearable = _registered_cache_is_clearable(definition)
        bucket_count = (
            len(SYSTEM_PARAMETER_CACHE)
            if definition.get("category") == "__all__"
            else int(definition.get("category") in SYSTEM_PARAMETER_CACHE)
        ) if clearable else 0
        rows.append({
            "key": key,
            "name": definition["name"],
            "description": definition["description"],
            "storage": "进程内存" if clearable else "直接 SQL 查询",
            "clearable": clearable,
            "entry_count": await _system_cache_entry_count(key, definition, db),
            "bucket_count": bucket_count,
            **SYSTEM_CACHE_META[key],
        })
    if keyword.strip():
        needle = keyword.strip().lower()
        rows = [row for row in rows if needle in f"{row['key']} {row['name']} {row['description']}".lower()]
    current_page, current_size = page or 1, page_size or 15
    total = len(rows)
    start = (current_page - 1) * current_size
    memory_rows = [row for row in rows if row["clearable"]]
    return {
        "items": rows[start:start + current_size],
        "total": total,
        "page": current_page,
        "page_size": current_size,
        "pages": (total + current_size - 1) // current_size,
        "summary": {
            "cache_entries": sum(len(items) for items in SYSTEM_PARAMETER_CACHE.values()),
            "cache_buckets": len(SYSTEM_PARAMETER_CACHE),
            "clearable_caches": len(memory_rows),
            "scope": "当前 API 进程内存；多进程部署需分别清理各进程缓存。",
        },
    }


def _system_menu_dict(item: SystemMenu) -> dict:
    label = str(item.label or "").strip()
    if not label or label in {"---", "—", "-"}:
        label = DEFAULT_MENU_LABEL_BY_KEY.get(item.key, "未命名菜单")
    return {
        "id": item.id, "key": item.key, "parent_key": item.parent_key,
        "label": label, "description": getattr(item, "description", ""), "icon": item.icon, "sort_order": item.sort_order,
        "is_visible": item.is_visible, "is_active": item.is_active,
        "is_system": item.key in SYSTEM_MENU_ROUTE_KEYS,
        "updated_by": item.updated_by, "updated_at": item.updated_at,
    }


def _dashboard_people(
    users_by_username: dict[str, User],
    *candidate_groups: object,
) -> str:
    from app.core.contracts import (
        _contract_person_values, _valid_contract_chinese_person_name,
    )
    for candidate in candidate_groups:
        values = _contract_person_values(candidate)
        if not values:
            continue
        labels: list[str] = []
        for value in values:
            if value.lower() == "system":
                continue
            else:
                user = users_by_username.get(value.lower())
                label = (
                    _valid_contract_chinese_person_name(user.display_name)
                    if user
                    else _valid_contract_chinese_person_name(value)
                )
            if label and label not in labels:
                labels.append(label)
        if labels:
            return "、".join(labels)
    return ""


def _communication_dict(item: CommunicationLog, users_by_username: dict[str, User] | None = None) -> dict:
    from app.core.formatters import (
        _person_reference_display,
    )
    return {"id": item.id, "customer_record_id": item.customer_record_id, "customer_name": item.customer_name, "contact": item.contact, "phone": item.phone, "content": item.content, "occurred_at": item.occurred_at, "operator": item.operator, "operator_display_name": _person_reference_display(item.operator, users_by_username or {})[0], "created_at": item.created_at, "updated_at": item.updated_at}


async def _staff_roi_report(
    identity: dict,
    db: AsyncSession,
    start_date: date | None = None,
    end_date: date | None = None,
    department_id: int | None = None,
) -> dict:
    """Report settled staff performance and paid commission cost without duplicating a source fee.

    A bank receipt allocated to an agency-fee record is split only among that
    fee's generated commission records, in proportion to their actual
    commission amounts.  Cost is a commission record's posted ``付款`` ledger
    amount, never an HR salary or commission-setting estimate.
    """
    from app.core.finance import (
        _round_fee_amount,
    )
    from app.core.formatters import (
        _staff_roi_date_matches,
    )
    from app.core.permissions import (
        _record_scope_conditions, _require_record_module_menu,
    )
    await _require_record_module_menu("report", identity, db, action="查看")
    if "finance.amount" not in await _allowed_field_keys(identity, db):
        raise HTTPException(status_code=403, detail="当前角色没有查看员工业绩ROI金额的字段权限")
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="开始日期不能晚于结束日期")

    selected_department = None
    if department_id:
        selected_department = await db.get(Department, department_id)
        if not selected_department or not selected_department.is_active:
            raise HTTPException(status_code=422, detail="部门不存在或已停用")

    scope = await _record_scope_conditions(identity, db)
    visible_fees = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance", *scope,
    ))).all())
    visible_by_id = {item.id: item for item in visible_fees}
    def source_fee_id_for(item: BusinessRecord) -> int | None:
        try:
            value = int((item.data or {}).get("source_fee_id") or 0)
        except (TypeError, ValueError):
            return None
        return value if value > 0 else None

    visible_commission_rows = [
        item for item in visible_fees
        if str((item.data or {}).get("expense_scope") or "").strip() == "内部"
        and source_fee_id_for(item)
        and str((item.data or {}).get("payee") or item.owner or "").strip()
    ]
    visible_source_fee_ids = {
        source_fee_id_for(item)
        for item in visible_commission_rows
        if source_fee_id_for(item) in visible_by_id
    }
    # The source fee is scope-checked above.  Load every generated commission
    # for that already-visible source only to establish its denominator; rows
    # outside the caller's finance scope are never returned or used for costs.
    all_commission_rows = [
        item for item in (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "finance"))).all()
        if str((item.data or {}).get("expense_scope") or "").strip() == "内部"
        and source_fee_id_for(item) in visible_source_fee_ids
        and str((item.data or {}).get("payee") or item.owner or "").strip()
    ]
    visible_commission_rows = [item for item in visible_commission_rows if source_fee_id_for(item) in visible_source_fee_ids]

    employee_usernames = {
        str((item.data or {}).get("payee") or item.owner or "").strip()
        for item in visible_commission_rows
    }
    users = list((await db.scalars(select(User).where(User.username.in_(employee_usernames)))).all()) if employee_usernames else []
    users_by_username = {user.username: user for user in users}
    allowed_usernames = {
        username for username, user in users_by_username.items()
        if not selected_department or user.department == selected_department.name
    }

    rows: dict[str, dict[str, object]] = {}
    def bucket(username: str) -> dict[str, object]:
        user = users_by_username[username]
        return rows.setdefault(username, {
            "employee": user.display_name or username,
            "employee_username": username,
            "department": user.department,
            "performance": 0.0,
            "cost": 0.0,
        })

    commission_by_source: dict[int, list[BusinessRecord]] = {}
    for commission in all_commission_rows:
        username = str((commission.data or {}).get("payee") or commission.owner or "").strip()
        commission_by_source.setdefault(source_fee_id_for(commission), []).append(commission)

    # Income comes only from allocated, settled incoming payments.  A receipt
    # may contain unrelated allocations, so use its exact fee_record_id link.
    incoming = list((await db.scalars(select(IncomingPayment).where(
        IncomingPayment.status.in_({"部分分配", "已分配"}),
    ))).all())
    for receipt in incoming:
        if not _staff_roi_date_matches(receipt.received_date, start_date, end_date):
            continue
        for allocation in receipt.allocations or []:
            try:
                source_fee_id = int(allocation.get("fee_record_id") or 0)
                received_amount = _round_fee_amount(float(allocation.get("amount") or 0))
            except (TypeError, ValueError):
                continue
            commissions = commission_by_source.get(source_fee_id, [])
            if received_amount <= 0 or not commissions:
                continue
            total_weight = sum(max(float((item.data or {}).get("amount") or 0), 0) for item in commissions)
            if total_weight <= 0:
                continue
            for commission in commissions:
                username = str((commission.data or {}).get("payee") or commission.owner).strip()
                weight = max(float((commission.data or {}).get("amount") or 0), 0)
                if username in allowed_usernames:
                    bucket(username)["performance"] = float(bucket(username)["performance"]) + received_amount * weight / total_weight

    commission_ids = [item.id for item in visible_commission_rows if str((item.data or {}).get("payee") or item.owner or "").strip() in allowed_usernames]
    payments = list((await db.scalars(select(FinanceTransaction).where(
        FinanceTransaction.finance_record_id.in_(commission_ids),
        FinanceTransaction.transaction_type == "付款",
    ))).all()) if commission_ids else []
    for payment in payments:
        if not _staff_roi_date_matches(payment.transaction_date, start_date, end_date):
            continue
        commission = visible_by_id.get(payment.finance_record_id)
        if not commission:
            continue
        username = str((commission.data or {}).get("payee") or commission.owner or "").strip()
        if username in allowed_usernames:
            bucket(username)["cost"] = float(bucket(username)["cost"]) + float(payment.amount or 0)

    items = []
    for item in rows.values():
        performance = _round_fee_amount(float(item["performance"]))
        cost = _round_fee_amount(float(item["cost"]))
        items.append({
            **item,
            "performance": performance,
            "cost": cost,
            "roi": round(performance / cost * 100, 2) if cost > 0 else None,
        })
    items.sort(key=lambda item: (-float(item["performance"]), str(item["employee"])))
    return {
        "items": items,
        "total": len(items),
        "filter_options": {
            "departments": [{"id": item.id, "name": item.name} for item in (await db.scalars(select(Department).where(Department.is_active.is_(True)).order_by(Department.sort_order, Department.id))).all()],
        },
        "definition": {
            "performance": "已分配银行回款按该代理费生成的员工提成金额比例分摊",
            "cost": "员工提成记录已登记的付款流水，不含提成方案或基本工资估算",
            "roi": "业绩÷成本×100%；成本为零时不计算",
        },
        "source": "settled_cash_flow",
    }


def _large_screen_month_keys(today: date) -> list[str]:
    keys: list[str] = []
    for offset in range(11, -1, -1):
        year = today.year
        month = today.month - offset
        while month <= 0:
            month += 12
            year -= 1
        keys.append(f"{year:04d}-{month:02d}")
    return keys


async def _report_analytics(view: str, identity: dict, db: AsyncSession, customer: str = "", court_lawyer: str = "", handling_lawyer: str = "", assistant: str = "", investigator: str = "", court: str = "", source_from: date | None = None, source_to: date | None = None, hearing_from: date | None = None, hearing_to: date | None = None, group_mode: str = "") -> dict:
    from app.core.permissions import (
        _record_scope_conditions,
    )
    if view not in {"brand", "lawyer", "refund", "execution-1", "execution-2", "execution-3"}: raise HTTPException(status_code=422, detail="不支持的统计视图")
    if source_from and source_to and source_from > source_to: raise HTTPException(status_code=422, detail="案源开始日期不能晚于结束日期")
    if hearing_from and hearing_to and hearing_from > hearing_to: raise HTTPException(status_code=422, detail="开庭开始日期不能晚于结束日期")
    if group_mode and group_mode not in {"按律师分组统计", "按文书分组统计"}: raise HTTPException(status_code=422, detail="不支持的分组模式")
    scope = await _record_scope_conditions(identity, db)
    cases = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "case", *scope))).all()
    customers_selected = {value.strip() for value in customer.split(",") if value.strip()}
    court_lawyers_selected = {value.strip() for value in court_lawyer.split(",") if value.strip()}
    def matches(item: BusinessRecord) -> bool:
        data = item.data or {}; handlers = data.get("handling_lawyers", [])
        return (not customers_selected or any(value in item.customer for value in customers_selected)) and (not court_lawyers_selected or data.get("hearing_lawyer") in court_lawyers_selected) and (not handling_lawyer or handling_lawyer in handlers) and (not assistant or assistant in str(data.get("assistant", ""))) and (not investigator or investigator in str(data.get("investigator", "")))
    cases = [item for item in cases if matches(item) and (not source_from or item.created_at.date() >= source_from) and (not source_to or item.created_at.date() <= source_to)]
    if court or hearing_from or hearing_to:
        case_ids = {item.id for item in cases}
        conditions = [HearingSchedule.case_record_id.in_(case_ids)]
        if court: conditions.append(HearingSchedule.court.ilike(f"%{court}%"))
        if hearing_from: conditions.append(HearingSchedule.hearing_date >= hearing_from)
        if hearing_to: conditions.append(HearingSchedule.hearing_date <= hearing_to)
        heard_case_ids = set((await db.scalars(select(HearingSchedule.case_record_id).where(*conditions))).all()) if case_ids else set()
        cases = [item for item in cases if item.id in heard_case_ids]
    case_by_no = {item.serial_no: item for item in cases}
    customers = sorted({item.customer for item in cases if item.customer}); lawyers = sorted({str((item.data or {}).get("hearing_lawyer")) for item in cases if (item.data or {}).get("hearing_lawyer")})
    if view in {"refund", "execution-1", "execution-2", "execution-3"}:
        if view == "refund":
            refunds = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "refund", *scope))).all()
            refunds = [item for item in refunds if not customers_selected or any(value in item.customer for value in customers_selected)]
            specs = [("准备资料进度案件数量", {"草稿", "准备资料", "待提交"}), ("客户盖章进度案件数量", {"客户盖章"}), ("提交法院进度案件数量", {"提交法院", "已提交法院"}), ("等待客户回款进度案件数量", {"等待客户回款", "待回款"})]
            charts = [{"title": title, "unit": "个/案", "items": [{"name": "案件数", "value": sum(item.status in statuses for item in refunds)}]} for title, statuses in specs]
        else:
            execution_statuses = list(CASE_EXECUTION_STATUSES)
            charts = [{"title": f"{status}案件数量", "unit": "个/案", "items": [{"name": "案件数", "value": sum(status in item.status for item in cases)}]} for status in execution_statuses]
        return {"view": view, "charts": charts, "filter_options": {"customers": customers, "lawyers": lawyers}, "source": "realtime"}
    can_view_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    finances = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "finance", *scope))).all() if can_view_amount else []
    from app.core.roi import operating_charts
    charts, warnings = await operating_charts(cases, finances, view, group_mode, db) if can_view_amount else ([], [])
    return {"view": view, "charts": charts, "warnings": warnings, "filter_options": {"customers": customers, "lawyers": lawyers}, "source": "realtime"}


def _export_ids(value: str) -> list[int]:
    if not value.strip():
        return []
    try:
        return list(dict.fromkeys(int(item) for item in value.split(",") if item.strip()))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="导出记录编号格式错误") from exc


def _csv_response(filename: str, headers: list[str], rows: list[list[object]]) -> Response:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    content = "\ufeff" + output.getvalue()
    disposition = f"attachment; filename=export.csv; filename*=UTF-8''{quote(filename)}"
    return Response(content=content.encode("utf-8"), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": disposition})


def _excel_response(filename: str, headers: list[str], rows: list[list[object]]) -> Response:
    """Return a real SpreadsheetML workbook instead of renaming CSV to Excel."""
    def cell(value: object) -> str:
        return f'<Cell><Data ss:Type="String">{xml_escape(str(value if value is not None else ""))}</Data></Cell>'

    table_rows = [f"<Row>{''.join(cell(header) for header in headers)}</Row>"]
    table_rows.extend(f"<Row>{''.join(cell(value) for value in row)}</Row>" for row in rows)
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" '
        'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">'
        f'<Worksheet ss:Name="导出数据"><Table>{"".join(table_rows)}</Table></Worksheet></Workbook>'
    )
    disposition = f"attachment; filename=export.xls; filename*=UTF-8''{quote(filename)}"
    return Response(content=content.encode("utf-8"), media_type="application/vnd.ms-excel", headers={"Content-Disposition": disposition})


def _csv_value(row: dict, *names: str, default: str = "") -> str:
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip(): return str(value).strip()
    return default


def _unique_import_record(records: list[BusinessRecord], value: str, label: str) -> BusinessRecord | None:
    token = value.strip()
    if not token:
        return None
    exact_serial = [item for item in records if item.serial_no == token]
    exact_title = [item for item in records if item.title == token]
    matches = exact_serial or exact_title
    if not matches:
        raise ValueError(f"{label}不存在或无权访问：{token}")
    if len(matches) != 1:
        raise ValueError(f"{label}存在多个同名记录，请使用唯一业务编号：{token}")
    return matches[0]


def _import_relation_data(
    *,
    customer: BusinessRecord | None = None,
    contract: BusinessRecord | None = None,
    case: BusinessRecord | None = None,
    investigation: BusinessRecord | None = None,
    task: BusinessRecord | None = None,
    clue: BusinessRecord | None = None,
    evidence: BusinessRecord | None = None,
) -> dict:
    result: dict = {}
    items = (
        ("customer", customer), ("contract", contract), ("case", case),
        ("investigation", investigation), ("task", task), ("clue", clue), ("evidence", evidence),
    )
    for name, item in items:
        if item:
            result[f"{name}_id"] = item.id
            result[f"{name}_record_id"] = item.id
            result[f"{name}_no"] = item.serial_no
            result[f"{name}_title"] = item.title
    # A directly selected child also carries its already-resolved parent chain.
    # This keeps downstream imports navigable even when the CSV only provides a
    # case, clue, task, or evidence number.
    for _, item in items:
        if not item:
            continue
        source = item.data or {}
        for name in ("customer", "contract", "case", "investigation", "task", "clue", "evidence"):
            for suffix in ("id", "record_id", "no", "title"):
                key = f"{name}_{suffix}"
                value = source.get(key)
                if value not in (None, ""):
                    result.setdefault(key, value)
    return result


def _validate_import_relation_consistency(relations: dict[str, BusinessRecord]) -> None:
    for child_name, child in relations.items():
        source = child.data or {}
        for parent_name, parent in relations.items():
            if child_name == parent_name:
                continue
            expected = source.get(f"{parent_name}_record_id") or source.get(f"{parent_name}_id")
            expected_no = str(source.get(f"{parent_name}_no") or "").strip()
            if expected and int(expected) != parent.id:
                raise ValueError(f"关联关系冲突：{child.serial_no} 不属于 {parent.serial_no}")
            if expected_no and expected_no != parent.serial_no:
                raise ValueError(f"关联关系冲突：{child.serial_no} 不属于 {parent.serial_no}")


def _conflict_entity_tokens(value: object) -> list[str]:
    """Expand stored party arrays and legacy comma-delimited party fields."""
    if isinstance(value, (list, tuple, set)):
        # An explicit array already defines entity boundaries.  Do not split an
        # English legal name such as ``Foo, Inc.`` inside one array element.
        return list(dict.fromkeys(str(item or "").strip() for item in value if str(item or "").strip()))
    tokens: list[str] = []
    for token in CASE_PARTY_SEPARATOR.split(str(value or "")):
        token = token.strip()
        if token and token not in tokens:
            tokens.append(token)
    return tokens


def _portal_code_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _approval_step_dict(step: ContractApprovalStep, names_by_username: dict[str, str] | None = None) -> dict:
    from app.core.formatters import (
        _contract_person_display_name,
    )
    return {
        "id": step.id,
        "contract_record_id": step.contract_record_id,
        "step_order": step.step_order,
        "approver": step.approver,
        "approver_display_name": _contract_person_display_name(step.approver, names_by_username),
        "status": step.status,
        "comment": step.comment,
        "acted_at": step.acted_at,
        "created_at": step.created_at,
    }


def _optional_record_id(value: object) -> int:
    try:
        record_id = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return record_id if record_id > 0 else 0


async def _business_rule_loop() -> None:
    """本地部署时持续执行不依赖用户打开页面的期限规则。"""
    from app.core.investigation import (
        _apply_notary_auto_conversion,
    )
    from app.core.tasks import (
        _apply_hearing_sms_reminders, _apply_task_auto_completion, _apply_task_overdue_performance,
    )
    while True:
        async with SessionLocal() as db:
            try:
                await _apply_notary_auto_conversion(db)
                await _apply_task_auto_completion(db)
                await _apply_task_overdue_performance(db)
                await _apply_hearing_sms_reminders(db)
            except Exception:
                await db.rollback()
        await asyncio.sleep(3600)


def _vip_node_member(node: VipTaskNode, identity: dict) -> bool:
    return identity.get("role") == "admin" or identity["username"] in {
        node.created_by, node.owner, *(str(value) for value in (node.participants or [])),
    }


def _vip_validate_schedule(start_at: datetime | None, deadline: date | None, end_at: datetime | None) -> None:
    if start_at and end_at and start_at >= end_at:
        raise HTTPException(status_code=422, detail="结束时间必须晚于开始时间")
    if deadline and end_at and deadline != end_at.date():
        raise HTTPException(status_code=422, detail="截止日期必须与结束时间日期一致")


def _vip_validate_node_transition(node: VipTaskNode, target: str, identity: dict) -> None:
    if target == node.status:
        return
    allowed = {
        "待处理": {"处理中", "已拒绝", "已暂停", "已取消"}, "处理中": {"已完成", "已暂停", "已取消"},
        "已暂停": {"待处理", "处理中", "已取消"}, "已完成": {"待处理", "已验收", "已拒绝"},
        "已拒绝": {"待处理"}, "已验收": set(), "已取消": set(),
    }
    if target not in allowed.get(node.status, set()):
        raise HTTPException(status_code=409, detail=f"VIP任务节点不能从{node.status}变更为{target}")
    if identity.get("role") != "admin" and identity["username"] not in {node.created_by, node.owner}:
        raise HTTPException(status_code=403, detail="只有VIP节点创建人或负责人可以变更状态")


async def _vip_active_usernames(values: list[str], db: AsyncSession, *, owner: str = "") -> list[str]:
    from app.core.tasks import (
        _active_task_username,
    )
    normalized: list[str] = []
    for raw in values:
        username = await _active_task_username(raw, db, field_name="VIP任务参与人")
        if username != owner and username not in normalized:
            normalized.append(username)
    return normalized


async def _vip_node_or_404(task: VipTask, node_id: int, identity: dict, db: AsyncSession, *, write: bool = False) -> VipTaskNode:
    node = await db.scalar(select(VipTaskNode).where(VipTaskNode.id == node_id, VipTaskNode.vip_task_id == task.id))
    if not node:
        raise HTTPException(status_code=404, detail="VIP任务节点不存在")
    if not _vip_node_member(node, identity):
        raise HTTPException(status_code=403, detail="无权访问该VIP任务节点")
    if write and identity.get("role") != "admin" and identity["username"] not in {node.created_by, node.owner}:
        raise HTTPException(status_code=403, detail="只有节点创建人或负责人可以修改节点")
    return node


def _vip_node_dict(node: VipTaskNode) -> dict:
    return {
        "id": node.id, "task_id": node.vip_task_id, "title": node.title, "status": node.status,
        "priority": node.priority, "owner": node.owner, "participants": node.participants or [],
        "description": node.description, "created_by": node.created_by, "start_at": node.start_at,
        "deadline": node.deadline, "end_at": node.end_at, "created_at": node.created_at, "updated_at": node.updated_at,
    }


def _vip_message_dict(message: VipTaskMessage) -> dict:
    return {
        "id": message.id, "task_id": message.vip_task_id, "node_id": message.vip_task_node_id,
        "sender": message.sender, "recipient": message.recipient, "content": message.content,
        "is_read": message.is_read, "read_at": message.read_at, "created_at": message.created_at,
    }


async def _commission_employee_index(db: AsyncSession) -> dict[str, BusinessRecord]:
    employees = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "hr"))).all())
    users = list((await db.scalars(select(User).where(User.is_active.is_(True)))).all())
    users_by_username = {user.username.lower(): user for user in users}
    index: dict[str, BusinessRecord] = {}
    for employee in employees:
        data = employee.data or {}
        if data.get("is_active") is False or employee.status in {"离职", "停用"}:
            continue
        username = str(data.get("username") or employee.owner or "").strip()
        user = users_by_username.get(username.lower()) if username else None
        for value in (username, employee.owner, employee.title, user.display_name if user else ""):
            key = str(value or "").strip().lower()
            if key:
                index.setdefault(key, employee)
    return index


async def _save_criminal_detail(record: BusinessRecord, payload: dict, action: str, comment: str, identity: dict, db: AsyncSession):
    from app.core.legacy_sync import (
        _sync_legacy_projection,
    )
    record.data = {**(record.data or {}), **payload}
    db.add(WorkflowEvent(record_id=record.id, action=action, from_status=record.status, to_status=record.status, operator=identity["username"], comment=comment.strip()))
    await _sync_legacy_projection(record, identity, db)
    await db.commit(); await db.refresh(record); return _record_dict(record)


def _criminal_maintenance_payload(body: BaseModel) -> dict:
    """Keep judicial booleans and dates typed when editing a completed case."""
    payload: dict[str, object] = {}
    for key, value in body.model_dump(exclude={"comment"}).items():
        if isinstance(value, date):
            payload[key] = str(value)
        elif isinstance(value, bool) or value is None:
            payload[key] = value
        else:
            payload[key] = str(value or "").strip()
    return payload


async def _official_outgoing_dict(item: OfficialOutgoingDocument, record: BusinessRecord, identity: dict, db: AsyncSession) -> dict:
    from app.core.formatters import (
        _person_display_name, _person_reference_display, _user_display_map,
    )
    from app.core.permissions import (
        _ensure_record_visible, _record_dict_for_identity,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    source = await _ensure_record_visible(item.source_record_id, identity, db) if item.source_record_id else None
    attachments = (await db.scalars(select(FileAttachment).where(FileAttachment.record_id == record.id).order_by(FileAttachment.id))).all()
    latest_audit = await db.scalar(select(WorkflowEvent).where(
        WorkflowEvent.record_id == record.id,
        WorkflowEvent.action.in_(("正式发文审批通过", "正式发文审批拒绝")),
    ).order_by(WorkflowEvent.id.desc()))
    display_users = await _user_display_map({*[attachment.uploader for attachment in attachments], latest_audit.operator if latest_audit else ""}, db)
    uploader_names = {username: _person_display_name(user.display_name, user.username)[0] for username, user in display_users.items()}
    return {
        **await _record_dict_for_identity(record, identity, db),
        "official_no": item.official_no,
        "need_audit": item.need_audit,
        "source_type": item.source_type,
        "source_record_id": item.source_record_id,
        "source_serial_no": source.serial_no if source else "",
        "source_file_ids": item.source_file_ids or [],
        "stamp_attachment_id": item.stamp_attachment_id,
        "attachments": [_attachment_dict(attachment, record, uploader_names) for attachment in attachments],
        "seal_asset_id": (record.data or {}).get("seal_asset_id"),
        "seal_type": (record.data or {}).get("seal_type", ""),
        "seal_name": (record.data or {}).get("seal_name", ""),
        "is_electronic_seal": bool((record.data or {}).get("is_electronic_seal")),
        "is_offline_print": bool((record.data or {}).get("is_offline_print", True)),
        "print_quantity": int((record.data or {}).get("print_quantity") or 1),
        "content": (record.data or {}).get("content", ""),
        "auditor": latest_audit.operator if latest_audit else "",
        "auditor_display_name": _person_reference_display(latest_audit.operator if latest_audit else "", display_users)[0],
        "audit_time": latest_audit.created_at.isoformat() if latest_audit else "",
        "audit_remark": latest_audit.comment if latest_audit else "",
    }


def _department_dict(item: Department, parent_name: str = "", users_by_username: dict[str, User] | None = None) -> dict:
    from app.core.formatters import (
        _person_reference_display,
    )
    users = users_by_username or {}
    manager_name, manager_missing = _person_reference_display(item.manager, users)
    created_name, created_missing = _person_reference_display(item.created_by, users)
    updated_name, updated_missing = _person_reference_display(item.updated_by, users)
    return {"id": item.id, "code": item.code, "name": item.name, "parent_department_id": item.parent_department_id, "parent_department_name": parent_name, "manager": item.manager, "manager_display_name": manager_name, "manager_display_name_missing": manager_missing, "overdue_deduction": item.overdue_deduction, "sort_order": item.sort_order, "is_active": item.is_active, "created_by": item.created_by, "created_by_display_name": created_name, "created_by_display_name_missing": created_missing, "updated_by": item.updated_by, "updated_by_display_name": updated_name, "updated_by_display_name_missing": updated_missing, "created_at": item.created_at, "updated_at": item.updated_at}


def _hr_record_linked_username(record: BusinessRecord) -> str:
    data = record.data or {}
    return str(data.get("username") or record.owner or "").strip().lower()


async def _collect_hr_employee_deletion_blockers(employee: BusinessRecord, identity: dict, db: AsyncSession) -> tuple[list[dict[str, object]], User | None]:
    """Return every conservative deletion blocker used by both HR preflight and delete."""
    from app.core.permissions import (
        _hr_duplicate_identity_canonical, _hr_duplicate_identity_group,
    )
    account_type = str((employee.data or {}).get("account_type") or "员工账号").strip()
    username = str((employee.data or {}).get("username") or "").strip().lower()
    # External HR profiles deliberately have no system login. Their owner is
    # the administrator who created the profile, not an account that belongs to
    # the profile, so it must not trigger admin protection or broad references.
    if account_type in {"员工账号", "客户账号"} and not username:
        username = str(employee.owner or "").strip().lower()
    blockers: list[dict[str, object]] = []
    user = await db.scalar(select(User).where(User.username == username)) if username else None
    duplicate_group = await _hr_duplicate_identity_group(employee, db)
    canonical = await _hr_duplicate_identity_canonical(duplicate_group, db)
    redundant_duplicate = len(duplicate_group) > 1 and canonical.id != employee.id
    if len(duplicate_group) > 1 and canonical.id == employee.id:
        blockers.append({
            "kind": "重复身份主档案",
            "count": len(duplicate_group) - 1,
            "records": [row.serial_no for row in duplicate_group if row.id != employee.id],
        })
    if not redundant_duplicate and (username == identity["username"].lower() or username == "admin" or (user and user.role == "admin")):
        blockers.append({"kind": "受保护登录账号", "count": 1, "records": [username or employee.serial_no]})
    subrecord_count = int((await db.scalar(select(func.count()).select_from(HrSubrecord).where(HrSubrecord.employee_id == employee.id))) or 0)
    if subrecord_count:
        rows = list((await db.scalars(select(HrSubrecord).where(HrSubrecord.employee_id == employee.id).order_by(HrSubrecord.id).limit(10))).all())
        blockers.append({"kind": "员工附属记录", "count": subrecord_count, "records": [f"{row.kind}#{row.id}" for row in rows]})
    attachment_count = int((await db.scalar(select(func.count()).select_from(FileAttachment).where(FileAttachment.record_id == employee.id))) or 0)
    if attachment_count:
        rows = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id == employee.id).order_by(FileAttachment.id).limit(10))).all())
        blockers.append({"kind": "员工档案文件", "count": attachment_count, "records": [row.original_name for row in rows]})
    reference_terms = [value for value in {username, employee.title.strip()} if value]
    reference_conditions = [BusinessRecord.owner == username] if username else []
    reference_conditions.extend(func.cast(BusinessRecord.data, String).ilike(f"%{value}%") for value in reference_terms)
    if reference_conditions and not redundant_duplicate:
        reference_filter = (
            BusinessRecord.id != employee.id,
            BusinessRecord.module.in_({"case", "task", "investigation", "contract", "seal", "finance"}),
            or_(*reference_conditions),
        )
        reference_count = int((await db.scalar(select(func.count()).select_from(BusinessRecord).where(*reference_filter))) or 0)
        if reference_count:
            rows = list((await db.scalars(select(BusinessRecord).where(*reference_filter).order_by(BusinessRecord.id).limit(10))).all())
            blockers.append({"kind": "可能业务关联", "count": reference_count, "records": [row.serial_no for row in rows]})
    # A redundant migrated file shares the surviving record's login. Deleting
    # that file must never remove the real account.
    return blockers, None if redundant_duplicate else user


async def _load_hr_batch_deletion_impact(body: HrEmployeeBatchDeleteInput, identity: dict, db: AsyncSession) -> tuple[list[tuple[BusinessRecord, User | None]], list[dict[str, object]]]:
    employee_ids = sorted(set(body.employee_ids))
    if any(employee_id <= 0 for employee_id in employee_ids):
        raise HTTPException(status_code=422, detail="员工标识无效")
    employees = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(employee_ids), BusinessRecord.module == "hr").with_for_update())).all())
    found_ids = {employee.id for employee in employees}
    missing = [employee_id for employee_id in employee_ids if employee_id not in found_ids]
    blockers: list[dict[str, object]] = [{"employee_id": employee_id, "employee_no": str(employee_id), "blockers": [{"kind": "员工档案不存在", "count": 1, "records": [str(employee_id)]}]} for employee_id in missing]
    loaded: list[tuple[BusinessRecord, User | None]] = []
    for employee in employees:
        employee_blockers, user = await _collect_hr_employee_deletion_blockers(employee, identity, db)
        loaded.append((employee, user))
        if employee_blockers:
            blockers.append({"employee_id": employee.id, "employee_no": employee.serial_no, "employee_name": employee.title, "blockers": employee_blockers})
    return loaded, blockers


async def _record_organization_audit(
    db: AsyncSession, identity: dict, action: str, target: str, detail: dict,
) -> None:
    """Persist organization mutations in the existing audit event stream."""
    audit = BusinessRecord(
        module="organization_audit",
        serial_no=f"ORG-AUDIT-{uuid4().hex}",
        title=target,
        status="已记录",
        owner=identity["username"],
        department=str(identity.get("department") or ""),
        data={"target": target, **detail},
    )
    db.add(audit)
    await db.flush()
    db.add(WorkflowEvent(
        record_id=audit.id,
        action=action,
        from_status="",
        to_status="已记录",
        operator=identity["username"],
        comment=json.dumps(detail, ensure_ascii=False, sort_keys=True),
    ))


def _organization_page(items: list, page: int | None, page_size: int | None) -> tuple[list, int, int, int]:
    """Keep legacy full-list callers working while exposing server paging."""
    total = len(items)
    if page is None and page_size is None:
        return items, 1, total or 15, total
    effective_page = page or 1
    effective_page_size = page_size or 15
    start = (effective_page - 1) * effective_page_size
    return items[start:start + effective_page_size], effective_page, effective_page_size, total


async def _audit_hr_performance(item: HrSubrecord, action: str, identity: dict, db: AsyncSession, before: dict | None = None) -> None:
    employee = await db.get(BusinessRecord, item.employee_id)
    db.add(WorkflowEvent(
        record_id=item.employee_id, action=action, from_status=employee.status, to_status=employee.status,
        operator=identity["username"],
        comment=json.dumps({"performance_id": item.id, "before": before, "after": None if action == "删除绩效方案" else item.data}, ensure_ascii=False),
    ))


async def _hr_performance_rows(employee_id: int | None, employee: str, department: str, start_date: date | None, end_date: date | None, identity: dict, db: AsyncSession) -> list[dict]:
    from app.core.formatters import (
        _person_display_name, _user_display_map,
    )
    from app.core.permissions import (
        _record_scope_conditions, _require_record_module_menu,
    )
    await _require_record_module_menu("hr", identity, db, action="查看")
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="筛选结束日期不能早于开始日期")
    conditions = [BusinessRecord.module == "hr", HrSubrecord.kind == "commission", *(await _record_scope_conditions(identity, db))]
    if employee_id is not None:
        conditions.append(BusinessRecord.id == employee_id)
    pairs = (await db.execute(select(HrSubrecord, BusinessRecord).join(BusinessRecord, BusinessRecord.id == HrSubrecord.employee_id).where(*conditions).order_by(HrSubrecord.created_at.desc(), HrSubrecord.id.desc()))).all()
    users = await _user_display_map({value for item, person in pairs for value in (item.created_by, item.updated_by, person.owner)}, db)
    rows = []
    for item, person in pairs:
        name, missing_name = _person_display_name(person.title, person.owner)
        account = users.get(str(person.owner).lower())
        if missing_name and account:
            name = _person_display_name(account.display_name, account.username)[0]
        if employee and employee.casefold() not in f"{name} {person.serial_no} {person.owner}".casefold():
            continue
        if department and department != (person.department or ""):
            continue
        data = item.data or {}
        if start_date or end_date:
            try:
                start = date.fromisoformat(str(data.get("start_date") or ""))
                end = date.fromisoformat(str(data["end_date"])) if data.get("end_date") else None
            except (ValueError, TypeError):
                continue
            if start_date and end and end < start_date or end_date and start > end_date:
                continue
        rows.append({**_hr_subrecord_dict(item, users), "employee_name": name, "employee_no": person.serial_no, "department": person.department})
    return rows


async def _get_hr_performance(performance_id: int, identity: dict, db: AsyncSession) -> HrSubrecord:
    from app.core.permissions import (
        _ensure_record_module, _require_record_module_menu,
    )
    await _require_record_module_menu("hr", identity, db, action="查看")
    item = await db.get(HrSubrecord, performance_id)
    if not item or item.kind != "commission":
        raise HTTPException(status_code=404, detail="绩效方案不存在")
    await _ensure_record_module(item.employee_id, "hr", identity, db)
    return item


def _hr_subrecord_dict(item: HrSubrecord, users_by_username: dict[str, User] | None = None) -> dict:
    from app.core.formatters import (
        _person_reference_display,
    )
    users = users_by_username or {}
    return {
        "id": item.id, "employee_id": item.employee_id, "kind": item.kind,
        "data": item.data or {}, "created_by": item.created_by,
        "created_by_display_name": _person_reference_display(item.created_by, users)[0],
        "updated_by": item.updated_by, "updated_by_display_name": _person_reference_display(item.updated_by, users)[0], "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _validate_hr_subrecord(kind: str, raw: dict) -> dict:
    if kind not in HR_SUBRECORD_KINDS:
        raise HTTPException(status_code=422, detail="不支持的员工附属记录类型")
    data = dict(raw or {})
    if kind == "leave":
        required = {"start_date": "请假开始", "end_date": "请假结束", "leave_type": "请假类型"}
        for key, label in required.items():
            if not str(data.get(key) or "").strip(): raise HTTPException(status_code=422, detail=f"请填写{label}")
        try: start, end = date.fromisoformat(str(data["start_date"])), date.fromisoformat(str(data["end_date"]))
        except ValueError as exc: raise HTTPException(status_code=422, detail="请假日期格式无效") from exc
        if end < start: raise HTTPException(status_code=422, detail="请假结束不能早于开始")
        hours = float(data.get("hours") or 0)
        if hours <= 0: raise HTTPException(status_code=422, detail="请假小时数必须大于 0")
        data.update({"start_date": str(start), "end_date": str(end), "hours": hours, "leave_type": str(data["leave_type"]).strip(), "remark": str(data.get("remark") or "").strip()})
    elif kind == "matter":
        content = str(data.get("content") or "").strip()
        if not content: raise HTTPException(status_code=422, detail="请填写事项内容")
        operation_date = str(data.get("operation_date") or date.today())
        try: date.fromisoformat(operation_date)
        except ValueError as exc: raise HTTPException(status_code=422, detail="事项日期格式无效") from exc
        data.update({"content": content, "operation_date": operation_date})
    else:
        start_date, end_date = str(data.get("start_date") or ""), str(data.get("end_date") or "")
        if not start_date: raise HTTPException(status_code=422, detail="请填写提成开始日期")
        if not end_date: raise HTTPException(status_code=422, detail="请填写提成结束日期")
        try:
            start = date.fromisoformat(start_date); end = date.fromisoformat(end_date) if end_date else None
        except ValueError as exc: raise HTTPException(status_code=422, detail="提成日期格式无效") from exc
        if end and end < start: raise HTTPException(status_code=422, detail="提成结束不能早于开始")
        numeric = [
            "base_salary",
            "hearing_rate", "hearing_fixed",
            "document_rate", "document_fixed",
            "source_rate", "source_fixed",
            "investigation_rate", "investigation_fixed",
            "quality_rate", "quality_fixed",
        ]
        for key in numeric:
            try:
                value = float(data.get(key) or 0)
            except (TypeError, ValueError, OverflowError) as exc:
                raise HTTPException(status_code=422, detail="提成或工资必须是有效数值") from exc
            if not math.isfinite(value) or value < 0:
                raise HTTPException(status_code=422, detail="提成或工资必须是有限非负数值")
            data[key] = value
        scheme_name = str(data.get("scheme_name") or "").strip()
        remark = str(data.get("remark") or "").strip()
        if len(scheme_name) > 128 or len(remark) > 2000:
            raise HTTPException(status_code=422, detail="方案名称不能超过128字，备注不能超过2000字")
        data.update({"start_date": str(start), "end_date": str(end) if end else "", "scheme_name": scheme_name, "remark": remark})
    return data
