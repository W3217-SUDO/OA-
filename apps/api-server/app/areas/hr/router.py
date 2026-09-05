"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.constants import (
    FIELD_KEYS, HR_SUBRECORD_KINDS, JOB_ROLE_ACTION_KEY_GRANTS, ROLE_DATA_SCOPES, SYSTEM_ADMIN_JOB_PERMISSIONS,
    SYSTEM_MENU_ROUTE_KEYS, WORKFLOW_TRANSITIONS,
)
from app.core.dependencies import (
    AsyncSession, BusinessRecord, Department, Depends, HTTPException,
    HrSubrecord, JSONResponse, JobRole, Query, Response,
    SystemMenu, User, WorkflowEvent, current_identity, date,
    datetime, delete, func, get_db, hash_password,
    or_, re, select, settings, status,
    update, uuid4,
)
from app.models_shared import (
    DepartmentInput, DepartmentUpdate, HrEmployeeBatchDeleteInput, HrEmployeeContractApprovalStatusInput, HrEmployeeCreateInput,
    HrEmployeeLoginStatusInput, HrEmployeeUpdateInput, HrPerformanceInput, HrSubrecordInput, HrSubrecordUpdate,
    HrTransitionInput, JobRoleInput, JobRolePermissionUpdate, JobRoleUpdate,
)
from fastapi import APIRouter

router = APIRouter()


@router.get(f"{settings.api_prefix}/hr/employees")
async def list_hr_employees(
    company: str = "", department: str = "", username: str = "", name: str = "", mobile: str = "", enabled: str = "",
    page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=100),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """Return the HR list with authoritative filtering and pagination.

    The old page exposes the employee list as a paged query.  Keep the
    account-only rows visible for administrators, but apply the same filters
    and page window before returning data so the browser cannot silently lose
    employees after the first 100 records.
    """
    from app.core.formatters import (
        _person_display_name,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _record_dict,
    )
    scope = await _record_scope_conditions(identity, db)
    employees = list((await db.scalars(
        select(BusinessRecord).where(BusinessRecord.module == "hr", *scope).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc())
    )).all())
    users_by_name: dict[str, User] = {}
    if identity.get("role") == "admin":
        users = list((await db.scalars(select(User).order_by(User.id))).all())
        users_by_name = {str(user.username).strip().lower(): user for user in users}
    rows: list[dict] = []
    linked_names: set[str] = set()
    for employee in employees:
        row = _record_dict(employee)
        data = dict(row.get("data") or {})
        key = str(data.get("username") or row.get("owner") or "").strip().lower()
        account = users_by_name.get(key)
        if account:
            profile = account.profile or {}
            row["department"] = account.department or row.get("department", "")
            row["data"] = {**data, **profile, "username": account.username, "role": account.role, "is_active": account.is_active, "system_user_id": account.id}
            linked_names.add(key)
        # Employee records are authoritative, but older records may leave the
        # title empty after the name was maintained on the linked user account.
        person_name, person_name_missing = _person_display_name(row.get("title", ""), key)
        if person_name_missing and account:
            person_name, person_name_missing = _person_display_name(account.display_name, key)
        row["person_display_name"] = person_name
        row["display_name_missing"] = person_name_missing
        if person_name_missing:
            row["title"] = person_name
        rows.append(row)
    if identity.get("role") == "admin":
        for user in users_by_name.values():
            key = str(user.username).strip().lower()
            if key in linked_names:
                continue
            profile = user.profile or {}
            person_name, person_name_missing = _person_display_name(user.display_name, user.username)
            rows.append({
                "id": -int(user.id), "serial_no": profile.get("employee_no") or f"SYS-{int(user.id):04d}",
                "title": person_name, "person_display_name": person_name, "display_name_missing": person_name_missing, "customer": profile.get("company") or "上海申浩律师事务所",
                "status": "在职" if user.is_active else "停用", "owner": user.username,
                "department": user.department or "", "description": "系统账号（尚未建立独立人事档案）", "created_at": user.created_at,
                "data": {**profile, "username": user.username, "role": user.role, "is_active": user.is_active, "system_user_id": user.id, "position": profile.get("position") or "系统管理员"},
            })
    def contains(value: object, needle: str) -> bool:
        return not needle or needle.casefold() in str(value or "").casefold()
    def visible(row: dict) -> bool:
        data = row.get("data") or {}
        active = data.get("is_active") is not False
        return (
            contains(row.get("customer"), company) and contains(row.get("department"), department)
            and contains(data.get("username") or row.get("owner"), username) and contains(row.get("title"), name)
            and contains(data.get("mobile") or data.get("phone"), mobile)
            and (not enabled or ("是" if active else "否") == enabled)
        )
    rows = [row for row in rows if visible(row)]
    total = len(rows)
    start = (page - 1) * page_size
    return {"items": rows[start:start + page_size], "total": total, "page": page, "page_size": page_size}


@router.post(f"{settings.api_prefix}/hr/employees", status_code=status.HTTP_201_CREATED)
async def create_hr_employee(body: HrEmployeeCreateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _identity_role_ids, _job_role_for_name, _require_hr_employee_action, _require_unique_hr_display_name, _system_user_role_ids,
    )
    from app.core.system import (
        _record_dict, _security_policy, _system_user_dict,
    )
    await _require_hr_employee_action(identity, db, "hr.employee.create", "新建")
    account_type = (body.account_type or body.data.get("account_type") or "员工账号").strip()
    if account_type not in {"员工账号", "客户账号", "外部合作账号"}:
        raise HTTPException(status_code=422, detail="账号类型无效")
    if "admin" not in _identity_role_ids(identity) and body.role != "user":
        raise HTTPException(status_code=403, detail="非系统管理员不能创建高权限系统账号")
    username = body.username.strip().lower()
    employee_no = body.employee_no.strip()
    display_name = await _require_unique_hr_display_name(body.display_name, db, linked_username=username)
    if await db.scalar(select(BusinessRecord.id).where(BusinessRecord.module == "hr", BusinessRecord.serial_no == employee_no)):
        raise HTTPException(status_code=409, detail="员工编号已存在")
    department = await db.scalar(select(Department).where(Department.name == body.department, Department.is_active.is_(True)))
    if not department:
        raise HTTPException(status_code=422, detail="所选部门不存在或已停用")
    position = await db.scalar(select(JobRole).where(JobRole.name == body.position, JobRole.is_active.is_(True)))
    if not position:
        raise HTTPException(status_code=422, detail="所选职务不存在或已停用")
    staff_role = str(body.data.get("staff_role") or body.position).strip()
    assigned_role: JobRole | None = None
    if account_type == "员工账号":
        assigned_role = await _job_role_for_name(staff_role, db)
        if not assigned_role:
            raise HTTPException(status_code=422, detail="所选人员角色不存在或已停用")
        if "admin" not in _identity_role_ids(identity) and assigned_role.code == "SYSTEM-ADMIN":
            raise HTTPException(status_code=403, detail="非系统管理员不能绑定系统管理员岗位")
        staff_role = assigned_role.name
    profile = {
        **body.data,
        "account_type": account_type,
        "employee_no": employee_no,
        "company": body.company.strip(),
        "position": body.position.strip(),
        "staff_role": staff_role,
        "permission_role": staff_role if account_type == "员工账号" else "",
        "permission_role_code": assigned_role.code if assigned_role else "",
    }
    user: User | None = None
    login_backed_account = account_type in {"员工账号", "客户账号"}
    if login_backed_account:
        if not username:
            raise HTTPException(status_code=422, detail="登录账号必须填写登录用户名")
        if username == "admin":
            raise HTTPException(status_code=409, detail="不能通过员工档案创建或覆盖管理员账号")
        if not re.fullmatch(r"[a-z0-9._-]{2,64}", username):
            raise HTTPException(status_code=422, detail="登录账号只能包含小写字母、数字、点、下划线或短横线")
        existing_employee = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.module == "hr", or_(BusinessRecord.owner == username, BusinessRecord.data["username"].as_string() == username)))
        if existing_employee:
            raise HTTPException(status_code=409, detail="该登录账号已关联其他员工档案")
        user = await db.scalar(select(User).where(User.username == username))
        if user:
            if "admin" in _system_user_role_ids(user):
                raise HTTPException(status_code=409, detail="不能通过员工档案覆盖管理员账号")
            if account_type != "客户账号":
                raise HTTPException(status_code=409, detail="登录账号已存在")
            # Legacy customer logins can outlive their customer-account HR row.
            # Re-adopt that login instead of forcing users to create another account.
            user.display_name = display_name
            user.department = body.department.strip()
            user.role = "user"
            user.role_ids = ["user"]
            user.profile = {**(user.profile or {}), **profile}
            user.is_active = body.is_active
        else:
            policy = await _security_policy(db)
            if len(body.password) < policy.min_password_length:
                raise HTTPException(status_code=422, detail=f"登录账号密码至少需要 {policy.min_password_length} 位")
            user = User(
                username=username, display_name=display_name, department=body.department.strip(),
                # Job position controls business capability. Customer accounts also
                # need a real low-privilege User so they can be bound and activated.
                role="user", role_ids=["user"], profile=profile, password_hash=hash_password(body.password),
                is_active=body.is_active, password_changed_at=None, must_change_password=True,
            )
    employee = BusinessRecord(
        module="hr", serial_no=employee_no, title=display_name, customer=body.company.strip(),
        status="在职" if body.is_active else "停用", owner=username if user else identity["username"], department=body.department.strip(), description="",
        data={**profile, "username": username if user else "", "role": user.role if user else "", "is_active": body.is_active},
    )
    db.add(employee)
    if user and not user.id:
        db.add(user)
    try:
        await db.flush()
        db.add(WorkflowEvent(record_id=employee.id, action="新建员工", from_status="", to_status=employee.status, operator=identity["username"], comment=f"账号类型：{account_type}；{'登录账号：' + username if user else '不创建系统登录账号'}；职务：{body.position}"))
        await db.commit()
        if user:
            await db.refresh(user)
        await db.refresh(employee)
    except Exception:
        await db.rollback()
        raise
    return {"employee": _record_dict(employee), "user": _system_user_dict(user) if user else None}


@router.patch(f"{settings.api_prefix}/hr/employees/{{employee_id}}")
async def update_hr_employee(employee_id: int, body: HrEmployeeUpdateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _identity_role_ids, _job_role_for_name, _require_hr_employee_action, _require_hr_employee_target_access, _require_unique_hr_display_name,
        _system_user_role_ids,
    )
    from app.core.system import (
        _record_dict, _rename_system_username, _system_user_dict,
    )
    await _require_hr_employee_action(identity, db, "hr.employee.update", "修改")
    employee = await db.get(BusinessRecord, employee_id)
    if not employee or employee.module != "hr": raise HTTPException(status_code=404, detail="员工档案不存在")
    await _require_hr_employee_target_access(employee, identity, db)
    if body.role not in {"admin", "manager", "auditor", "user"}: raise HTTPException(status_code=422, detail="角色值无效")
    if body.left_at and body.left_at < body.joined_at: raise HTTPException(status_code=422, detail="离职日期不能早于入职日期")
    department = await db.scalar(select(Department).where(Department.name == body.department, Department.is_active.is_(True)))
    if not department: raise HTTPException(status_code=422, detail="所选部门不存在或已停用")
    current_position = str((employee.data or {}).get("position") or "").strip()
    if body.position != current_position:
        position = await db.scalar(select(JobRole).where(JobRole.name == body.position, JobRole.is_active.is_(True)))
        if not position:
            raise HTTPException(status_code=422, detail="所选职务不存在或已停用")
    account_type = str(body.data.get("account_type") or (employee.data or {}).get("account_type") or "员工账号").strip()
    if account_type not in {"员工账号", "客户账号", "外部合作账号"}:
        raise HTTPException(status_code=422, detail="账号类型无效")
    if "admin" not in _identity_role_ids(identity) and body.role != "user":
        raise HTTPException(status_code=403, detail="非系统管理员不能调整系统账号角色")
    effective_role = body.role if account_type == "员工账号" else "user"
    requested_staff_role = str(body.data.get("permission_role_code") or body.data.get("staff_role") or body.data.get("permission_role") or "").strip()
    current_staff_role = str((employee.data or {}).get("permission_role_code") or (employee.data or {}).get("staff_role") or (employee.data or {}).get("permission_role") or "").strip()
    if "admin" not in _identity_role_ids(identity) and requested_staff_role and requested_staff_role != current_staff_role:
        raise HTTPException(status_code=403, detail="非系统管理员不能调整员工的权限角色")
    staff_role: str | None = requested_staff_role or None
    assigned_role: JobRole | None = None
    if account_type == "员工账号":
        if requested_staff_role:
            assigned_role = await _job_role_for_name(requested_staff_role, db)
            if not assigned_role:
                raise HTTPException(status_code=422, detail="所选人员角色不存在或已停用")
            if "admin" not in _identity_role_ids(identity) and assigned_role.code == "SYSTEM-ADMIN":
                raise HTTPException(status_code=403, detail="非系统管理员不能绑定系统管理员岗位")
            staff_role = assigned_role.name
    elif account_type == "客户账号":
        staff_role = "客户联系人"
    role_binding = ({"staff_role": staff_role, "permission_role": staff_role, "permission_role_code": assigned_role.code if assigned_role else ""} if staff_role is not None else {})
    if account_type != "员工账号":
        role_binding["permission_role"] = ""
        role_binding["permission_role_code"] = ""
    stored_username = str((employee.data or {}).get("username") or "").strip().lower()
    requested_username = body.username.strip().lower()
    username = stored_username or (str(employee.owner or "").strip().lower() if account_type == "员工账号" else "")
    display_name = await _require_unique_hr_display_name(body.display_name, db, employee_id=employee.id, linked_username=username)
    user = await db.scalar(select(User).where(User.username == username)) if username else None
    if account_type == "客户账号" and not stored_username:
        if requested_username == "admin" or not re.fullmatch(r"[a-z0-9._-]{2,64}", requested_username):
            raise HTTPException(status_code=422, detail="客户账号用户名只能包含小写字母、数字、点、下划线或短横线")
        if await db.scalar(select(User.id).where(User.username == requested_username)):
            raise HTTPException(status_code=409, detail="客户账号用户名已被其他系统用户占用")
        username = requested_username
        user = User(
            username=username, display_name=display_name, department=body.department.strip(),
            role="user", role_ids=["user"], profile={}, password_hash=hash_password(uuid4().hex),
            is_active=body.is_active, password_changed_at=None, must_change_password=True,
        )
        db.add(user)
        await db.flush()
        employee.owner = username
    if account_type in {"员工账号", "客户账号"} and not user: raise HTTPException(status_code=409, detail="登录账号关联的系统用户不存在，不能只修改一侧资料")
    if user and user.username == "admin":
        raise HTTPException(status_code=409, detail="管理员账号不能通过员工档案修改、停用或改名")
    if account_type == "外部合作账号" and user:
        raise HTTPException(status_code=409, detail="请先在人事中心员工管理中解除登录账号关联，再变更为非员工账号")
    if not user:
        previous_status = employee.status
        profile = {**(employee.data or {}), **body.data, **role_binding, "account_type": account_type, "employee_no": employee.serial_no, "company": employee.customer, "position": body.position, "email": body.email.strip(), "mobile": body.mobile.strip(), "office_phone": body.office_phone.strip(), "joined_at": str(body.joined_at), "left_at": str(body.left_at) if body.left_at else ""}
        employee.title = display_name; employee.department = body.department.strip(); employee.data = profile
        db.add(WorkflowEvent(record_id=employee.id, action="修改员工资料", from_status=previous_status, to_status=employee.status, operator=identity["username"], comment=f"账号类型：{account_type}；未关联系统登录账号"))
        await db.commit(); await db.refresh(employee)
        return {"employee": _record_dict(employee), "user": None}
    username = await _rename_system_username(user, body.username, identity, db)
    if user.username == identity["username"] and not body.is_active: raise HTTPException(status_code=409, detail="不能停用当前登录账号")
    if user.username == identity["username"] and effective_role != "admin": raise HTTPException(status_code=409, detail="不能取消当前登录账号的管理员角色")
    # Login availability is independent from employment status: an active
    # employee may temporarily have login disabled without being offboarded.
    # Formal resignation/HR suspension still goes through the dedicated
    # transition endpoint, which also disables the linked account.
    previous_status = employee.status
    profile = {**(user.profile or {}), **body.data, **role_binding, "account_type": account_type, "employee_no": employee.serial_no, "company": employee.customer, "position": body.position, "email": body.email.strip(), "mobile": body.mobile.strip(), "office_phone": body.office_phone.strip(), "joined_at": str(body.joined_at), "left_at": str(body.left_at) if body.left_at else ""}
    existing_role_ids = _system_user_role_ids(user)
    preserved_secondary_roles = [role for role in existing_role_ids[1:] if role != effective_role]
    next_role_ids = [effective_role, *preserved_secondary_roles] if account_type == "员工账号" else ["user"]
    user.display_name = display_name; user.department = body.department.strip(); user.role = next_role_ids[0]; user.role_ids = next_role_ids; user.is_active = body.is_active; user.profile = profile
    contract_approval_enabled = bool(profile.get("contract_approval_enabled"))
    employee.title = display_name; employee.department = body.department.strip(); employee.data = {**(employee.data or {}), **profile, "contract_approval_enabled": contract_approval_enabled, "username": username, "role": effective_role, "is_active": body.is_active}
    db.add(WorkflowEvent(record_id=employee.id, action="修改员工资料", from_status=previous_status, to_status=employee.status, operator=identity["username"], comment=f"部门：{employee.department}；职务：{body.position}；账号：{'启用' if body.is_active else '停用'}"))
    await db.commit(); await db.refresh(employee); await db.refresh(user)
    return {"employee": _record_dict(employee), "user": _system_user_dict(user)}


@router.patch(f"{settings.api_prefix}/hr/employees/{{employee_id}}/login-status")
async def update_hr_employee_login_status(employee_id: int, body: HrEmployeeLoginStatusInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _record_dict, _system_user_dict,
    )
    _require_admin(identity)
    employee = await db.get(BusinessRecord, employee_id)
    if not employee or employee.module != "hr":
        raise HTTPException(status_code=404, detail="员工档案不存在")
    data = dict(employee.data or {})
    account_type = str(data.get("account_type") or "员工账号").strip()
    if account_type not in {"员工账号", "客户账号"}:
        raise HTTPException(status_code=409, detail="该员工档案未关联系统登录账号")
    username = str(data.get("username") or employee.owner).strip().lower()
    user = await db.scalar(select(User).where(User.username == username))
    if not user:
        raise HTTPException(status_code=409, detail="员工账号关联的登录用户不存在")
    if user.username == "admin":
        raise HTTPException(status_code=409, detail="管理员账号不能通过员工档案停用")
    if user.username == identity["username"] and not body.is_active:
        raise HTTPException(status_code=409, detail="不能停用当前登录账号")
    previous_active = user.is_active
    user.is_active = body.is_active
    data.update({"username": user.username, "role": user.role, "is_active": body.is_active, "system_user_id": user.id})
    employee.data = data
    db.add(WorkflowEvent(
        record_id=employee.id, action="切换登录账号状态",
        from_status="启用" if previous_active else "停用",
        to_status="启用" if body.is_active else "停用",
        operator=identity["username"],
        comment="登录账号：{}；{}".format(user.username, "启用" if body.is_active else "停用"),
    ))
    await db.commit(); await db.refresh(employee); await db.refresh(user)
    return {"employee": _record_dict(employee), "user": _system_user_dict(user)}


@router.patch(f"{settings.api_prefix}/hr/employees/{{employee_id}}/contract-approval-status")
async def update_hr_employee_contract_approval_status(employee_id: int, body: HrEmployeeContractApprovalStatusInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.contracts import (
        _is_contract_approver,
    )
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _record_dict, _system_user_dict,
    )
    _require_admin(identity)
    employee = await db.get(BusinessRecord, employee_id)
    if not employee or employee.module != "hr":
        raise HTTPException(status_code=404, detail="员工档案不存在")
    data = dict(employee.data or {})
    username = str(data.get("username") or employee.owner).strip().lower()
    user = await db.scalar(select(User).where(User.username == username))
    if not user:
        raise HTTPException(status_code=409, detail="员工账号关联的登录用户不存在")
    previous_enabled = bool((user.profile or {}).get("contract_approval_enabled"))
    user.profile = {**(user.profile or {}), "contract_approval_enabled": body.contract_approval_enabled}
    data.update({
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
        "system_user_id": user.id,
        "contract_approval_enabled": body.contract_approval_enabled,
    })
    employee.data = data
    db.add(WorkflowEvent(
        record_id=employee.id, action="切换合同审批资格",
        from_status="已配置" if previous_enabled else "未配置",
        to_status="已配置" if body.contract_approval_enabled else "未配置",
        operator=identity["username"],
        comment="合同审批流程人员：{}；{}".format(user.username, "是" if body.contract_approval_enabled else "否"),
    ))
    await db.commit(); await db.refresh(employee); await db.refresh(user)
    return {
        "employee": _record_dict(employee),
        "user": _system_user_dict(user),
        "can_approve_contract": await _is_contract_approver(user, db),
    }


@router.get(f"{settings.api_prefix}/hr/employees/{{employee_id}}/deletion-impact")
async def get_hr_employee_deletion_impact(employee_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _hr_duplicate_identity_canonical, _hr_duplicate_identity_group, _require_admin,
    )
    from app.core.system import (
        _collect_hr_employee_deletion_blockers,
    )
    _require_admin(identity)
    employee = await db.get(BusinessRecord, employee_id)
    if not employee or employee.module != "hr":
        raise HTTPException(status_code=404, detail="员工档案不存在")
    blockers, _ = await _collect_hr_employee_deletion_blockers(employee, identity, db)
    duplicate_group = await _hr_duplicate_identity_group(employee, db)
    canonical = await _hr_duplicate_identity_canonical(duplicate_group, db)
    duplicate_cleanup = len(duplicate_group) > 1 and canonical.id != employee.id
    return {
        "deletable": not blockers,
        "blockers": blockers,
        "duplicate_cleanup": duplicate_cleanup,
        "canonical_employee_id": canonical.id if duplicate_cleanup else None,
    }


@router.post(f"{settings.api_prefix}/hr/employees/batch-deletion-impact")
async def get_hr_employee_batch_deletion_impact(body: HrEmployeeBatchDeleteInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _load_hr_batch_deletion_impact,
    )
    _require_admin(identity)
    _, blockers = await _load_hr_batch_deletion_impact(body, identity, db)
    return {"deletable": not blockers, "blockers": blockers}


@router.api_route(f"{settings.api_prefix}/hr/employees/batch", methods=["DELETE"])
async def delete_hr_employees_batch(body: HrEmployeeBatchDeleteInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _load_hr_batch_deletion_impact,
    )
    _require_admin(identity)
    employees, blockers = await _load_hr_batch_deletion_impact(body, identity, db)
    if blockers:
        await db.rollback()
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"deletable": False, "blockers": blockers})
    for employee, user in employees:
        await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == employee.id))
        await db.delete(employee)
        if user:
            await db.delete(user)
    await db.commit()
    return {"deleted_ids": [employee.id for employee, _ in employees]}


@router.delete(f"{settings.api_prefix}/hr/employees/{{employee_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hr_employee(employee_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Old Staff/Delete parity: delete only an unreferenced employee and linked login atomically."""
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _collect_hr_employee_deletion_blockers,
    )
    _require_admin(identity)
    employee = await db.get(BusinessRecord, employee_id)
    if not employee or employee.module != "hr":
        raise HTTPException(status_code=404, detail="员工档案不存在")
    blockers, user = await _collect_hr_employee_deletion_blockers(employee, identity, db)
    if blockers:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"deletable": False, "blockers": blockers})
    await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == employee.id))
    await db.delete(employee)
    if user:
        await db.delete(user)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/hr/departments")
async def list_departments(
    keyword: str = "", active_only: bool = False,
    page: int | None = Query(default=None, ge=1), page_size: int | None = Query(default=None, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.system import (
        _department_dict, _organization_page,
    )
    statement = select(Department)
    if keyword.strip():
        term = f"%{keyword.strip()}%"; statement = statement.where(or_(Department.code.ilike(term), Department.name.ilike(term), Department.manager.ilike(term)))
    if active_only: statement = statement.where(Department.is_active.is_(True))
    items = (await db.scalars(statement.order_by(Department.sort_order, Department.id))).all()
    parent_ids = {item.parent_department_id for item in items if item.parent_department_id}
    parents = (await db.scalars(select(Department).where(Department.id.in_(parent_ids)))).all() if parent_ids else []
    names_by_id = {item.id: item.name for item in parents}
    page_items, effective_page, effective_page_size, total = _organization_page(items, page, page_size)
    display_users = await _user_display_map({value for item in page_items for value in (item.manager, item.created_by, item.updated_by)}, db)
    return {
        "items": [_department_dict(item, names_by_id.get(item.parent_department_id or 0, ""), display_users) for item in page_items],
        "total": total, "page": effective_page, "page_size": effective_page_size,
    }


@router.post(f"{settings.api_prefix}/hr/departments", status_code=status.HTTP_201_CREATED)
async def create_department(body: DepartmentInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _department_dict, _record_organization_audit,
    )
    _require_admin(identity); code, name = body.code.strip().upper(), body.name.strip()
    if await db.scalar(select(Department.id).where(or_(Department.code == code, Department.name == name))): raise HTTPException(status_code=409, detail="部门代码或名称已存在")
    parent = None
    if body.parent_department_id:
        parent = await db.get(Department, body.parent_department_id)
        if not parent or not parent.is_active: raise HTTPException(status_code=422, detail="上级部门不存在或已停用")
    item = Department(**body.model_dump(exclude={"code", "name", "manager"}), code=code, name=name, manager=body.manager.strip(), created_by=identity["username"], updated_by=identity["username"])
    db.add(item); await db.flush()
    await _record_organization_audit(db, identity, "创建部门", f"部门:{item.code}", {"department_id": item.id, "code": item.code, "name": item.name})
    await db.commit(); await db.refresh(item)
    display_users = await _user_display_map({item.manager, item.created_by, item.updated_by}, db)
    return _department_dict(item, parent.name if parent else "", display_users)


@router.patch(f"{settings.api_prefix}/hr/departments/{{department_id}}")
async def update_department(department_id: int, body: DepartmentUpdate, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _department_dict, _record_organization_audit,
    )
    _require_admin(identity); item = await db.get(Department, department_id)
    if not item: raise HTTPException(status_code=404, detail="部门不存在")
    old_name = item.name; code = body.code.strip().upper() if body.code is not None else item.code; name = body.name.strip() if body.name is not None else item.name
    if await db.scalar(select(Department.id).where(Department.id != item.id, or_(Department.code == code, Department.name == name))): raise HTTPException(status_code=409, detail="部门代码或名称已存在")
    if "parent_department_id" in body.model_fields_set and body.parent_department_id is not None:
        if body.parent_department_id == item.id: raise HTTPException(status_code=422, detail="上级部门不能是本部门")
        parent = await db.get(Department, body.parent_department_id)
        if not parent or not parent.is_active: raise HTTPException(status_code=422, detail="上级部门不存在或已停用")
        ancestor = parent
        while ancestor.parent_department_id:
            if ancestor.parent_department_id == item.id: raise HTTPException(status_code=422, detail="上级部门不能是本部门的下级部门")
            ancestor = await db.get(Department, ancestor.parent_department_id)
            if not ancestor: break
    changes = body.model_dump(exclude_unset=True, exclude_none=True)
    if "parent_department_id" in body.model_fields_set:
        changes["parent_department_id"] = body.parent_department_id
    for key, value in changes.items(): setattr(item, key, value.strip().upper() if key == "code" else value.strip() if key in {"name", "manager"} else value)
    item.updated_by = identity["username"]
    if item.name != old_name:
        await db.execute(update(User).where(User.department == old_name).values(department=item.name))
        await db.execute(update(BusinessRecord).where(BusinessRecord.department == old_name).values(department=item.name))
    await _record_organization_audit(db, identity, "修改部门", f"部门:{item.code}", {"department_id": item.id, "code": item.code, "name": item.name})
    await db.commit(); await db.refresh(item)
    parent = await db.get(Department, item.parent_department_id) if item.parent_department_id else None
    display_users = await _user_display_map({item.manager, item.created_by, item.updated_by}, db)
    return _department_dict(item, parent.name if parent else "", display_users)


@router.delete(f"{settings.api_prefix}/hr/departments/{{department_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(department_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _record_organization_audit,
    )
    _require_admin(identity); item = await db.get(Department, department_id)
    if not item: raise HTTPException(status_code=404, detail="部门不存在")
    users = await db.scalar(select(func.count()).select_from(User).where(User.department == item.name))
    records = await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.department == item.name))
    child_count = await db.scalar(select(func.count()).select_from(Department).where(Department.parent_department_id == item.id))
    if (users or 0) + (records or 0) > 0: raise HTTPException(status_code=409, detail=f"部门仍被 {users or 0} 个账号和 {records or 0} 条业务记录使用，请先停用或迁移")
    if child_count: raise HTTPException(status_code=409, detail=f"部门仍有 {child_count} 个下级部门，请先调整其上级部门")
    await _record_organization_audit(db, identity, "删除部门", f"部门:{item.code}", {"department_id": item.id, "code": item.code, "name": item.name})
    await db.delete(item); await db.commit(); return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/hr/job-roles")
async def list_job_roles(
    keyword: str = "", active_only: bool = False,
    page: int | None = Query(default=None, ge=1), page_size: int | None = Query(default=None, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _job_role_dict,
    )
    from app.core.system import (
        _organization_page,
    )
    statement = select(JobRole)
    if keyword.strip():
        term = f"%{keyword.strip()}%"; statement = statement.where(or_(JobRole.code.ilike(term), JobRole.name.ilike(term), JobRole.description.ilike(term)))
    if active_only: statement = statement.where(JobRole.is_active.is_(True))
    items = (await db.scalars(statement.order_by(JobRole.sort_order, JobRole.id))).all()
    page_items, effective_page, effective_page_size, total = _organization_page(items, page, page_size)
    display_users = await _user_display_map({value for item in page_items for value in (item.created_by, item.updated_by)}, db)
    return {
        "items": [_job_role_dict(item, display_users) for item in page_items],
        "total": total, "page": effective_page, "page_size": effective_page_size,
    }


@router.get(f"{settings.api_prefix}/hr/job-roles/{{role_id}}/permissions")
async def get_job_role_permissions(role_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _organization_permission_tree, _require_admin,
    )
    _require_admin(identity)
    role = await db.get(JobRole, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="岗位角色不存在")
    menus = (await db.scalars(select(SystemMenu).order_by(SystemMenu.sort_order, SystemMenu.id))).all()
    menu_keys = {menu.key for menu in menus} | set(SYSTEM_MENU_ROUTE_KEYS)
    role_rows = (await db.scalars(select(JobRole).order_by(JobRole.id))).all()
    actions = sorted(
        ({action.strip() for row in role_rows for action in (row.permissions or []) if action.strip()} | set(SYSTEM_ADMIN_JOB_PERMISSIONS))
        - menu_keys
    )
    permissions = list(dict.fromkeys(value.strip() for value in (role.permissions or []) if value.strip()))
    return {
        "role_id": role.id, "role_code": role.code, "permissions": permissions,
        "field_keys": list(dict.fromkeys(role.field_keys or [])),
        "field_keys_configured": role.field_keys_configured,
        "data_scope": role.data_scope,
        "available_data_scopes": sorted(ROLE_DATA_SCOPES),
        "available_field_keys": FIELD_KEYS,
        "tree": _organization_permission_tree(menus, actions, set(permissions)),
    }


@router.patch(f"{settings.api_prefix}/hr/job-roles/{{role_id}}/permissions")
async def update_job_role_permissions(
    role_id: int, body: JobRolePermissionUpdate,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _job_role_dict, _normalize_job_role_data_scope, _normalize_job_role_field_keys, _require_admin,
    )
    from app.core.system import (
        _record_organization_audit,
    )
    _require_admin(identity)
    role = await db.get(JobRole, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="岗位角色不存在")
    permissions = list(dict.fromkeys(value.strip() for value in body.permissions if value.strip()))
    field_keys = _normalize_job_role_field_keys(body.field_keys) if body.field_keys is not None else list(dict.fromkeys(role.field_keys or []))
    field_keys_configured = body.field_keys_configured if body.field_keys_configured is not None else role.field_keys_configured
    data_scope = _normalize_job_role_data_scope(body.data_scope) if "data_scope" in body.model_fields_set else role.data_scope
    if role.code == "SYSTEM-ADMIN":
        if set(permissions) != set(SYSTEM_ADMIN_JOB_PERMISSIONS) or set(field_keys) != set(FIELD_KEYS) or not field_keys_configured or data_scope not in {None, "全所数据"}:
            raise HTTPException(status_code=422, detail="系统管理员角色权限不可修改")
    else:
        role_rows = (await db.scalars(select(JobRole).order_by(JobRole.id))).all()
        configured_menu_keys = set((await db.scalars(select(SystemMenu.key))).all()) | set(SYSTEM_MENU_ROUTE_KEYS)
        allowed_actions = (
            {action.strip() for row in role_rows for action in (row.permissions or []) if action.strip()}
            | set(SYSTEM_ADMIN_JOB_PERMISSIONS)
        ) - configured_menu_keys
        allowed = configured_menu_keys | allowed_actions | {f"action:{key}" for values in JOB_ROLE_ACTION_KEY_GRANTS.values() for key in values}
        invalid = sorted(set(permissions) - allowed)
        if invalid:
            raise HTTPException(status_code=422, detail=f"无效菜单或业务动作权限：{', '.join(invalid)}")
    role.permissions = permissions
    role.field_keys = field_keys
    role.field_keys_configured = bool(field_keys_configured)
    role.data_scope = "全所数据" if role.code == "SYSTEM-ADMIN" else data_scope
    role.updated_by = identity["username"]
    await _record_organization_audit(db, identity, "修改岗位角色权限", f"岗位角色:{role.code}", {"role_id": role.id, "permissions": permissions})
    await db.commit(); await db.refresh(role)
    display_users = await _user_display_map({role.created_by, role.updated_by}, db)
    return _job_role_dict(role, display_users)


@router.post(f"{settings.api_prefix}/hr/job-roles", status_code=status.HTTP_201_CREATED)
async def create_job_role(body: JobRoleInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _job_role_dict, _normalize_job_role_data_scope, _normalize_job_role_field_keys, _require_admin,
    )
    from app.core.system import (
        _record_organization_audit,
    )
    _require_admin(identity); code, name = body.code.strip().upper(), body.name.strip()
    if await db.scalar(select(JobRole.id).where(or_(JobRole.code == code, JobRole.name == name))): raise HTTPException(status_code=409, detail="岗位角色代码或名称已存在")
    permissions = list(dict.fromkeys(value.strip() for value in body.permissions if value.strip()))
    field_keys = _normalize_job_role_field_keys(body.field_keys)
    data_scope = _normalize_job_role_data_scope(body.data_scope)
    item = JobRole(**body.model_dump(exclude={"code", "name", "permissions", "description", "field_keys", "field_keys_configured", "data_scope"}), code=code, name=name, permissions=permissions, field_keys=field_keys, field_keys_configured=bool(body.field_keys_configured or field_keys), data_scope=data_scope, description=body.description.strip(), created_by=identity["username"], updated_by=identity["username"])
    db.add(item); await db.flush()
    await _record_organization_audit(db, identity, "创建岗位角色", f"岗位角色:{item.code}", {"role_id": item.id, "code": item.code, "name": item.name})
    await db.commit(); await db.refresh(item)
    display_users = await _user_display_map({item.created_by, item.updated_by}, db)
    return _job_role_dict(item, display_users)


@router.patch(f"{settings.api_prefix}/hr/job-roles/{{role_id}}")
async def update_job_role(role_id: int, body: JobRoleUpdate, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _job_role_dict, _normalize_job_role_data_scope, _normalize_job_role_field_keys, _require_admin,
    )
    from app.core.system import (
        _record_organization_audit,
    )
    _require_admin(identity); item = await db.get(JobRole, role_id)
    if not item: raise HTTPException(status_code=404, detail="岗位角色不存在")
    if item.code == "SYSTEM-ADMIN":
        requested_permissions = body.permissions if body.permissions is not None else list(SYSTEM_ADMIN_JOB_PERMISSIONS)
        normalized_permissions = list(dict.fromkeys(entry.strip() for entry in requested_permissions if entry.strip()))
        requested_fields = body.field_keys if body.field_keys is not None else list(FIELD_KEYS)
        normalized_fields = _normalize_job_role_field_keys(requested_fields)
        if body.code not in {None, "SYSTEM-ADMIN"} or body.name not in {None, "系统管理员"} or set(normalized_permissions) != set(SYSTEM_ADMIN_JOB_PERMISSIONS) or set(normalized_fields) != set(FIELD_KEYS) or body.field_keys_configured is False or body.data_scope not in {None, "全所数据"} or body.is_active is False:
            raise HTTPException(status_code=422, detail="系统管理员岗位必须保持启用、名称不变并保留全部业务动作权限")
    old_name = item.name; code = body.code.strip().upper() if body.code is not None else item.code; name = body.name.strip() if body.name is not None else item.name
    if await db.scalar(select(JobRole.id).where(JobRole.id != item.id, or_(JobRole.code == code, JobRole.name == name))): raise HTTPException(status_code=409, detail="岗位角色代码或名称已存在")
    changes = body.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in changes.items():
        if key == "permissions": value = list(dict.fromkeys(entry.strip() for entry in value if entry.strip()))
        elif key == "field_keys":
            value = _normalize_job_role_field_keys(value)
            if "field_keys_configured" not in changes:
                item.field_keys_configured = True
        elif key == "data_scope": value = _normalize_job_role_data_scope(value)
        elif key == "code": value = value.strip().upper()
        elif key in {"name", "description"}: value = value.strip()
        setattr(item, key, value)
    if item.code == "SYSTEM-ADMIN":
        item.field_keys_configured = True
        item.data_scope = "全所数据"
    item.updated_by = identity["username"]
    if item.name != old_name:
        hr_records = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "hr"))).all()
        for record in hr_records:
            if (record.data or {}).get("position") == old_name: record.data = {**(record.data or {}), "position": item.name}
    await _record_organization_audit(db, identity, "修改岗位角色", f"岗位角色:{item.code}", {"role_id": item.id, "code": item.code, "name": item.name})
    await db.commit(); await db.refresh(item)
    display_users = await _user_display_map({item.created_by, item.updated_by}, db)
    return _job_role_dict(item, display_users)


@router.delete(f"{settings.api_prefix}/hr/job-roles/{{role_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job_role(role_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _record_organization_audit,
    )
    _require_admin(identity); item = await db.get(JobRole, role_id)
    if item and item.code == "SYSTEM-ADMIN":
        raise HTTPException(status_code=422, detail="系统管理员角色不能删除")
    if not item: raise HTTPException(status_code=404, detail="岗位角色不存在")
    hr_records = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "hr"))).all()
    used = sum(1 for record in hr_records if (record.data or {}).get("position") == item.name)
    if used: raise HTTPException(status_code=409, detail=f"岗位角色仍被 {used} 份员工档案使用，请先调整员工岗位")
    await _record_organization_audit(db, identity, "删除岗位角色", f"岗位角色:{item.code}", {"role_id": item.id, "code": item.code, "name": item.name})
    await db.delete(item); await db.commit(); return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/hr/performance")
async def list_hr_performance(employee_id: int | None = Query(None, gt=0), employee: str = "", department: str = "", start_date: date | None = None, end_date: date | None = None, page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=100), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.system import (
        _hr_performance_rows,
    )
    rows = await _hr_performance_rows(employee_id, employee.strip(), department.strip(), start_date, end_date, identity, db)
    return {"items": rows[(page - 1) * page_size:page * page_size], "total": len(rows), "page": page, "page_size": page_size}


@router.get(f"{settings.api_prefix}/hr/performance/export")
async def export_hr_performance(employee_id: int | None = Query(None, gt=0), employee: str = "", department: str = "", start_date: date | None = None, end_date: date | None = None, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.system import (
        _csv_response, _hr_performance_rows,
    )
    rows = await _hr_performance_rows(employee_id, employee.strip(), department.strip(), start_date, end_date, identity, db)
    fields = [("scheme_name", "方案名称"), ("start_date", "开始日期"), ("end_date", "结束日期"), ("base_salary", "基本工资"), ("hearing_rate", "开庭提成"), ("hearing_fixed", "开庭固定"), ("document_rate", "文书提成"), ("document_fixed", "文书固定"), ("source_rate", "案源提成"), ("source_fixed", "案源固定"), ("investigation_rate", "调查提成"), ("investigation_fixed", "调查固定"), ("quality_rate", "品管提成"), ("quality_fixed", "品管固定"), ("remark", "备注")]
    return _csv_response(f"hr-performance-{date.today()}.csv", ["员工编号", "员工", "部门", *[label for _, label in fields]], [[row["employee_no"], row["employee_name"], row["department"], *[row["data"].get(key, "") for key, _ in fields]] for row in rows])


@router.get(f"{settings.api_prefix}/hr/performance/{{performance_id}}")
async def get_hr_performance(performance_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.system import (
        _get_hr_performance, _hr_performance_rows,
    )
    item = await _get_hr_performance(performance_id, identity, db)
    rows = await _hr_performance_rows(item.employee_id, "", "", None, None, identity, db)
    return next(row for row in rows if row["id"] == item.id)


@router.post(f"{settings.api_prefix}/hr/performance", status_code=status.HTTP_201_CREATED)
async def create_hr_performance(body: HrPerformanceInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    result = await create_hr_subrecord(body.employee_id, HrSubrecordInput(kind="commission", data=body.data), identity, db)
    return await get_hr_performance(result["id"], identity, db)


@router.patch(f"{settings.api_prefix}/hr/performance/{{performance_id}}")
async def update_hr_performance(performance_id: int, body: HrSubrecordUpdate, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.system import (
        _get_hr_performance,
    )
    item = await _get_hr_performance(performance_id, identity, db)
    await update_hr_subrecord(item.employee_id, item.id, body, identity, db)
    return await get_hr_performance(item.id, identity, db)


@router.delete(f"{settings.api_prefix}/hr/performance/{{performance_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hr_performance(performance_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.system import (
        _get_hr_performance,
    )
    item = await _get_hr_performance(performance_id, identity, db)
    return await delete_hr_subrecord(item.employee_id, item.id, identity, db)


@router.get(f"{settings.api_prefix}/hr/{{employee_id}}/subrecords")
async def list_hr_subrecords(employee_id: int, kind: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_record_module_menu,
    )
    from app.core.system import (
        _hr_subrecord_dict,
    )
    await _require_record_module_menu("hr", identity, db, action="查看")
    await _ensure_record_module(employee_id, "hr", identity, db)
    conditions = [HrSubrecord.employee_id == employee_id]
    if kind:
        if kind not in HR_SUBRECORD_KINDS: raise HTTPException(status_code=422, detail="不支持的员工附属记录类型")
        conditions.append(HrSubrecord.kind == kind)
    items = (await db.scalars(select(HrSubrecord).where(*conditions).order_by(HrSubrecord.created_at.desc(), HrSubrecord.id.desc()))).all()
    users_by_username = await _user_display_map({value for item in items for value in (item.created_by, item.updated_by)}, db)
    return {"items": [_hr_subrecord_dict(item, users_by_username) for item in items], "total": len(items)}


@router.get(f"{settings.api_prefix}/hr/{{employee_id}}/performance-for-case/{{case_id}}")
async def get_employee_performance_for_case(employee_id: int, case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Resolve the evidenced employee+case performance scheme by the case business date."""
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _hr_subrecord_dict,
    )
    await _ensure_record_module(employee_id, "hr", identity, db)
    case = await _ensure_record_module(case_id, "case", identity, db)
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色无权查看员工案件绩效")
    case_date = (case.created_at.date() if case.created_at else date.today())
    rows = (await db.scalars(select(HrSubrecord).where(HrSubrecord.employee_id == employee_id, HrSubrecord.kind == "commission").order_by(HrSubrecord.created_at.desc(), HrSubrecord.id.desc()))).all()
    matched: HrSubrecord | None = None
    for item in rows:
        data = item.data or {}
        try:
            start = date.fromisoformat(str(data.get("start_date") or "")); end = date.fromisoformat(str(data.get("end_date") or "")) if data.get("end_date") else None
        except ValueError:
            continue
        if start <= case_date and (end is None or case_date <= end):
            matched = item; break
    return {"employee_id": employee_id, "case_id": case.id, "case_no": case.serial_no, "case_date": str(case_date), "matched": bool(matched), "performance": _hr_subrecord_dict(matched) if matched else None}


@router.post(f"{settings.api_prefix}/hr/{{employee_id}}/subrecords", status_code=status.HTTP_201_CREATED)
async def create_hr_subrecord(employee_id: int, body: HrSubrecordInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _require_record_module_menu,
    )
    from app.core.system import (
        _audit_hr_performance, _hr_subrecord_dict, _validate_hr_subrecord,
    )
    if identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以维护员工记录")
    await _ensure_record_module(employee_id, "hr", identity, db)
    await _require_record_module_menu("hr", identity, db, action="维护")
    item = HrSubrecord(employee_id=employee_id, kind=body.kind, data=_validate_hr_subrecord(body.kind, body.data), created_by=identity["username"], updated_by=identity["username"])
    db.add(item)
    await db.flush()
    if item.kind == "commission":
        await _audit_hr_performance(item, "新增绩效方案", identity, db)
    await db.commit(); await db.refresh(item); return _hr_subrecord_dict(item)


@router.patch(f"{settings.api_prefix}/hr/{{employee_id}}/subrecords/{{subrecord_id}}")
async def update_hr_subrecord(employee_id: int, subrecord_id: int, body: HrSubrecordUpdate, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _require_record_module_menu,
    )
    from app.core.system import (
        _audit_hr_performance, _hr_subrecord_dict, _validate_hr_subrecord,
    )
    if identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以维护员工记录")
    await _ensure_record_module(employee_id, "hr", identity, db)
    item = await db.get(HrSubrecord, subrecord_id)
    if not item or item.employee_id != employee_id: raise HTTPException(status_code=404, detail="员工附属记录不存在")
    await _require_record_module_menu("hr", identity, db, action="维护")
    before = dict(item.data or {})
    item.data = _validate_hr_subrecord(item.kind, body.data); item.updated_by = identity["username"]
    if item.kind == "commission":
        await _audit_hr_performance(item, "修改绩效方案", identity, db, before)
    await db.commit(); await db.refresh(item); return _hr_subrecord_dict(item)


@router.delete(f"{settings.api_prefix}/hr/{{employee_id}}/subrecords/{{subrecord_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hr_subrecord(employee_id: int, subrecord_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _require_record_module_menu,
    )
    from app.core.system import (
        _audit_hr_performance,
    )
    if identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以维护员工记录")
    await _ensure_record_module(employee_id, "hr", identity, db)
    item = await db.get(HrSubrecord, subrecord_id)
    if not item or item.employee_id != employee_id: raise HTTPException(status_code=404, detail="员工附属记录不存在")
    await _require_record_module_menu("hr", identity, db, action="维护")
    if item.kind == "commission":
        await _audit_hr_performance(item, "删除绩效方案", identity, db, dict(item.data or {}))
    await db.delete(item); await db.commit(); return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(f"{settings.api_prefix}/hr/{{employee_id}}/transition")
async def transition_employee(employee_id: int, body: HrTransitionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    if identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以办理人事状态")
    item = await _ensure_record_module(employee_id, "hr", identity, db)
    allowed = WORKFLOW_TRANSITIONS["hr"].get(item.status, [])
    if body.to_status not in allowed: raise HTTPException(status_code=409, detail=f"不能从“{item.status}”办理到“{body.to_status}”")
    reason = body.reason.strip()
    if body.to_status in {"离职", "停用"} and len(reason) < 2: raise HTTPException(status_code=422, detail="离职或停用必须填写原因")
    if body.effective_date < date(2000, 1, 1): raise HTTPException(status_code=422, detail="办理日期无效")
    previous = item.status; data = dict(item.data or {})
    if body.to_status == "在职":
        if previous == "试用":
            data.update({"regularized_at": str(body.effective_date), "regularized_by": identity["username"]}); action = "试用转正"
        else:
            data.update({"reactivated_at": str(body.effective_date), "reactivated_by": identity["username"]}); action = "恢复在职"
    elif body.to_status == "离职":
        data.update({"offboard_date": str(body.effective_date), "offboard_reason": reason, "handover_to": body.handover_to.strip(), "offboard_by": identity["username"]}); action = "办理离职"
    else:
        data.update({"disabled_at": str(body.effective_date), "disabled_reason": reason, "disabled_by": identity["username"]}); action = "停用员工"
    # The dedicated HR lifecycle is the authoritative employment switch for a
    # linked employee login.  Every non-administrator employee account,
    # including manager and auditor accounts, must be synchronized.  The
    # separately protected administrator account is never altered here.
    linked_username = str(data.get("username") or item.owner or "").strip().lower()
    linked_user = await db.scalar(select(User).where(User.username == linked_username)) if linked_username else None
    if linked_user and linked_user.role != "admin":
        login_enabled = body.to_status == "在职"
        linked_user.is_active = login_enabled
        data["is_active"] = login_enabled
        data["login_account_synced_at"] = datetime.now().isoformat()
        data["login_account_sync"] = "已启用" if login_enabled else "已停用"
    item.status = body.to_status; item.data = data
    db.add(WorkflowEvent(record_id=item.id, action=action, from_status=previous, to_status=item.status, operator=identity["username"], comment=body.comment or reason))
    await db.commit(); await db.refresh(item); return _record_dict(item, await _allowed_field_keys(identity, db))
