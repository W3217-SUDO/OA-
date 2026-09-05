"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.storage import _xls_preview_sheets
from app.core.constants import (
    AI_SPACE_CATEGORY, ARCHIVE_REQUIRED_CATEGORIES, ATTACHMENT_TEXT_PREVIEW_MAX_CHARS, CASE_FORMAL_DOCUMENT_FOLDERS, DEFAULT_ROLE_PERMISSIONS,
    DEFAULT_SYSTEM_MENUS, FIELD_KEYS, FINANCE_DEFAULT_VOUCHER_CATEGORY, INVESTIGATION_MATERIAL_CATEGORIES, JAR_FEE_MODULE,
    MENU_KEYS, MENU_PARENT_BY_KEY, PDF_PREVIEW_MAX_DIMENSION, PDF_PREVIEW_MAX_PIXELS, PDF_PREVIEW_MAX_WIDTH,
    PDF_PREVIEW_MIN_WIDTH, ROLE_DATA_SCOPES, SEAL_APPLICATION_FILE_CATEGORY, SEAL_STAMPED_FILE_CATEGORY, SYSTEM_ACTION_BY_CODE,
    SYSTEM_ACTION_DEFINITIONS, SYSTEM_CACHE_META, SYSTEM_CACHE_REGISTRY, SYSTEM_MENU_ROUTE_KEYS, SYSTEM_PARAMETER_CACHE,
    SYSTEM_PARAMETER_CATEGORIES, UPLOAD_ROOT, _LEGACY_CASE_TASK_HISTORY_ENTITIES, logger,
)
from app.core.dependencies import (
    AgentDocument, AsyncSession, BusinessRecord, CUSTOM_SKILL_FILE_LIMIT, CUSTOM_SKILL_LIMIT,
    CaseAssistedFee, CaseTypeFileTypeRelation, ContractApprovalStep, Depends, DingTalkError,
    Document, DocumentTemplate, File, FileAttachment, FileResponse,
    FinanceTransaction, Form, HTTPException, HearingSchedule, IprCaseFileCustomImportBatch,
    IprCaseFileCustomImportCandidate, IprCaseWarning, IprOfficialImportBatch, IprOfficialImportCandidate, JSONResponse,
    JobRole, LegacyCaseTaskHistory, LegacyHistoricalAttachment, Notification, OAuth2PasswordRequestForm,
    Path, Query, Response, RolePermission, StreamingResponse,
    SystemConfig, SystemMenu, SystemParameter, UploadFile, User,
    WorkflowEvent, and_, current_identity, custom_skill_public, date,
    datetime, delete, dingtalk_client, func, get_db,
    hash_password, httpx, io, json, normalize_custom_skill,
    or_, parse_uploaded_skill, password_needs_rehash, select, settings,
    status, timedelta, timezone, uuid4, verify_password,
)
from app.models_shared import (
    AgentDocumentConfirmInput, AgentDocumentInput, AgentDocumentUpdate, CacheBatchClearInput, CurrentUserUpdate,
    DifyRequest, DingTalkBindInput, DingTalkBindingInput, DingTalkLoginInput, RolePermissionUpdate,
    SecurityPolicyUpdate, SystemConfigUpdate, SystemMenuInput, SystemMenuUpdate, SystemParameterInput,
    SystemParameterRelationReplaceInput, SystemParameterUpdate, SystemUserInput, SystemUserPasswordResetInput, SystemUserUpdate,
    TemplateInput, TemplateUpdate, UserAgentSkillInput, UserAgentSkillUpdate, UserMessageInput,
    UserPermissionOverrideUpdate,
)
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post(f"{settings.api_prefix}/auth/login")
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    from app.core.system import (
        _login_response, _security_policy,
    )
    user = await db.scalar(select(User).where(User.username == form.username))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="账号或密码错误")
    policy = await _security_policy(db)
    # PostgreSQL returns TIMESTAMP WITH TIME ZONE values as aware datetimes,
    # while SQLite returns the same model field as a naive datetime.
    # Match the persisted value's timezone before comparing so both local
    # development and Docker/PostgreSQL enforce login locks identically.
    now = datetime.now(user.locked_until.tzinfo) if user.locked_until and user.locked_until.tzinfo else datetime.now()
    if user.locked_until and user.locked_until > now:
        raise HTTPException(status_code=423, detail=f"登录失败次数过多，账号锁定至 {user.locked_until.strftime('%Y-%m-%d %H:%M:%S')}")
    if not verify_password(form.password, user.password_hash):
        user.failed_login_attempts = int(user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= policy.max_failed_attempts:
            user.locked_until = now + timedelta(minutes=policy.lock_minutes)
        await db.commit()
        if user.locked_until: raise HTTPException(status_code=423, detail=f"登录失败次数过多，账号已锁定 {policy.lock_minutes} 分钟")
        raise HTTPException(status_code=401, detail=f"账号或密码错误，还可尝试 {policy.max_failed_attempts - user.failed_login_attempts} 次")
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(form.password)
        user.password_changed_at = now
    user.failed_login_attempts = 0; user.locked_until = None; user.last_login_at = now
    await db.commit()
    return await _login_response(user, db)


@router.get(f"{settings.api_prefix}/auth/dingtalk/config")
async def dingtalk_login_config():
    return {
        "enabled": dingtalk_client.configured,
        "corp_id": settings.dingtalk_corp_id if dingtalk_client.configured else "",
        "agent_id": settings.dingtalk_agent_id if dingtalk_client.configured else "",
    }


@router.post(f"{settings.api_prefix}/auth/dingtalk/login")
async def dingtalk_login(body: DingTalkLoginInput, db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _dingtalk_allowed_display_names,
    )
    from app.core.permissions import (
        _require_dingtalk_access,
    )
    from app.core.system import (
        _login_response,
    )
    if not dingtalk_client.configured:
        raise HTTPException(status_code=503, detail="钉钉免登尚未配置")
    try:
        ding_user = await dingtalk_client.user_by_auth_code(body.auth_code.strip())
    except (DingTalkError, httpx.HTTPError) as exc:
        logger.warning("DingTalk login failed: %s", exc)
        raise HTTPException(status_code=502, detail="钉钉身份校验失败，请稍后重试") from exc
    users = (await db.scalars(select(User).where(User.is_active.is_(True)))).all()
    matched = [user for user in users if str((user.profile or {}).get("dingtalk_user_id") or "").strip() == ding_user["user_id"]]
    if not matched and ding_user.get("mobile"):
        matched = [user for user in users if str((user.profile or {}).get("mobile") or "").strip() == ding_user["mobile"]]
        if len(matched) == 1:
            matched[0].profile = {**(matched[0].profile or {}), "dingtalk_user_id": ding_user["user_id"]}
    ding_name = str(ding_user.get("name") or "").strip()
    if not matched and ding_name in _dingtalk_allowed_display_names():
        matched = [user for user in users if str(user.display_name or "").strip() == ding_name]
        if len(matched) == 1:
            matched[0].profile = {**(matched[0].profile or {}), "dingtalk_user_id": ding_user["user_id"]}
    if len(matched) != 1:
        raise HTTPException(status_code=403, detail="钉钉账号尚未绑定系统员工，请联系管理员在员工账号中绑定")
    user = matched[0]
    _require_dingtalk_access(user)
    user.last_login_at = datetime.now()
    await db.commit()
    return await _login_response(user, db, require_password_change=False)


@router.post(f"{settings.api_prefix}/auth/dingtalk/bind")
async def bind_dingtalk_login(body: DingTalkBindInput, db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_unique_dingtalk_user_id, _require_dingtalk_access,
    )
    from app.core.system import (
        _login_response,
    )
    if not dingtalk_client.configured:
        raise HTTPException(status_code=503, detail="钉钉免登尚未配置")
    try:
        ding_user = await dingtalk_client.user_by_auth_code(body.auth_code.strip())
    except (DingTalkError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=502, detail="钉钉身份校验失败，请从工作台重新打开系统") from exc
    user = await db.scalar(select(User).where(User.username == body.username.strip().lower(), User.is_active.is_(True)))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="OA 账号或密码错误")
    _require_dingtalk_access(user)
    profile = {**(user.profile or {}), "dingtalk_user_id": ding_user["user_id"]}
    await _ensure_unique_dingtalk_user_id(profile, db, user.id, user.display_name)
    user.profile = profile
    user.last_login_at = datetime.now()
    await db.commit()
    return await _login_response(user, db)


@router.get(f"{settings.api_prefix}/auth/me")
async def current_user_profile(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _user_permission_payload,
    )
    from app.core.system import (
        _system_user_dict,
    )
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="当前用户不存在")
    return {**_system_user_dict(user), **(await _user_permission_payload(user, db))}


@router.patch(f"{settings.api_prefix}/auth/me")
async def update_current_user_profile(body: CurrentUserUpdate, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _user_permission_payload,
    )
    from app.core.system import (
        _security_policy, _system_user_dict,
    )
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="当前用户不存在")
    if body.display_name is not None:
        user.display_name = body.display_name.strip()
    profile_changes = {
        key: value.strip() if isinstance(value, str) else value
        for key, value in {
            "email": body.email,
            "office_phone": body.office_phone,
            "mobile": body.mobile,
            "menu_auto_collapse": body.menu_auto_collapse,
        }.items()
        if value is not None
    }
    if profile_changes:
        user.profile = {**(user.profile or {}), **profile_changes}
    if body.new_password is not None:
        if not body.current_password or not verify_password(body.current_password, user.password_hash):
            raise HTTPException(status_code=400, detail="当前密码不正确")
        if body.new_password == body.current_password:
            raise HTTPException(status_code=400, detail="新密码不能与当前密码相同")
        policy = await _security_policy(db)
        if len(body.new_password) < policy.min_password_length: raise HTTPException(status_code=422, detail=f"新密码至少需要 {policy.min_password_length} 位")
        user.password_hash = hash_password(body.new_password)
        user.password_changed_at = datetime.now(); user.failed_login_attempts = 0; user.locked_until = None; user.must_change_password = False
    await db.commit()
    await db.refresh(user)
    return {**_system_user_dict(user), **(await _user_permission_payload(user, db))}


@router.get(f"{settings.api_prefix}/system/users")
async def list_system_users(keyword: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _system_user_dict,
    )
    _require_admin(identity)
    statement = select(User)
    if keyword.strip():
        like = f"%{keyword.strip()}%"
        statement = statement.where(or_(User.username.ilike(like), User.display_name.ilike(like)))
    users = (await db.scalars(statement.order_by(User.id))).all()
    return {"items": [_system_user_dict(user) for user in users], "total": len(users)}


@router.patch(f"{settings.api_prefix}/system/users/{{user_id}}/dingtalk")
async def bind_system_user_dingtalk(user_id: int, body: DingTalkBindingInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin, _require_dingtalk_access,
    )
    from app.core.system import (
        _system_user_dict,
    )
    _require_admin(identity)
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="系统用户不存在")
    ding_user_id = body.user_id.strip()
    if ding_user_id:
        _require_dingtalk_access(user)
        users = (await db.scalars(select(User).where(User.id != user_id))).all()
        if any(str((item.profile or {}).get("dingtalk_user_id") or "").strip() == ding_user_id for item in users):
            raise HTTPException(status_code=409, detail="该钉钉账号已绑定其他系统用户")
    profile = dict(user.profile or {})
    if ding_user_id:
        profile["dingtalk_user_id"] = ding_user_id
    else:
        profile.pop("dingtalk_user_id", None)
    user.profile = profile
    await db.commit(); await db.refresh(user)
    return _system_user_dict(user)


@router.get(f"{settings.api_prefix}/people/options")
async def list_active_people_options(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Expose only active personnel names for authenticated internal selectors."""
    users = list((await db.scalars(select(User).where(User.is_active.is_(True)).order_by(User.display_name, User.username))).all())
    employees = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "hr", BusinessRecord.status.not_in({"离职", "停用"}),
    ))).all())
    employee_names = {
        str((employee.data or {}).get("username") or employee.owner or "").strip().lower(): str(employee.title or "").strip()
        for employee in employees
        if str((employee.data or {}).get("username") or employee.owner or "").strip()
    }
    items = []
    for user in users:
        name = employee_names.get(user.username.strip().lower()) or str(user.display_name or "").strip()
        if name:
            system_display_name = str(user.display_name or "").strip()
            items.append({
                "value": name,
                "label": name,
                "username": user.username,
                "search_text": " ".join(
                    value for value in (name, system_display_name, user.username) if value
                ),
            })
    return {"items": items}


@router.post(f"{settings.api_prefix}/system/users", status_code=status.HTTP_201_CREATED)
async def create_system_user(body: SystemUserInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_unique_dingtalk_user_id, _normalize_system_user_role_ids, _require_admin,
    )
    from app.core.system import (
        _security_policy, _system_user_dict, _system_user_manager_profile,
    )
    _require_admin(identity)
    role_ids = _normalize_system_user_role_ids(body.role_ids, body.role)
    username = body.username.strip().lower()
    if await db.scalar(select(User).where(User.username == username)):
        raise HTTPException(status_code=409, detail="登录账号已存在")
    policy = await _security_policy(db)
    if len(body.password) < policy.min_password_length: raise HTTPException(status_code=422, detail=f"密码至少需要 {policy.min_password_length} 位")
    profile = {**body.profile, "access_level": body.access_level.strip(), "lead_rate": body.lead_rate.strip(), "copy_rate": body.copy_rate.strip(), **(await _system_user_manager_profile(body.manager_id, db))}
    await _ensure_unique_dingtalk_user_id(profile, db, display_name=body.display_name)
    user = User(
        username=username,
        display_name=body.display_name.strip(),
        department=body.department.strip(),
        role=role_ids[0],
        role_ids=role_ids,
        profile=profile,
        password_hash=hash_password(body.password),
        is_active=body.is_active,
        password_changed_at=None,
        must_change_password=True,
    )
    db.add(user)
    await db.commit(); await db.refresh(user)
    return _system_user_dict(user)


@router.patch(f"{settings.api_prefix}/system/users/{{user_id}}")
async def update_system_user(user_id: int, body: SystemUserUpdate, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_system_user_lifecycle_safe, _ensure_unique_dingtalk_user_id, _normalize_system_user_role_ids, _require_admin, _require_unique_hr_display_name,
        _system_user_role_ids,
    )
    from app.core.system import (
        _rename_system_username, _security_policy, _system_user_dict, _system_user_manager_profile,
    )
    _require_admin(identity)
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if body.username is not None:
        await _rename_system_username(user, body.username, identity, db)
    if body.role is not None or body.role_ids is not None:
        role_ids = _normalize_system_user_role_ids(body.role_ids, body.role, fallback_role=_system_user_role_ids(user)[0])
        if user.username == identity["username"] and "admin" not in role_ids:
            raise HTTPException(status_code=409, detail="不能取消当前登录账号的管理员角色")
        user.role = role_ids[0]
        user.role_ids = role_ids
    if body.is_active is not None:
        if user.username == identity["username"] and not body.is_active:
            raise HTTPException(status_code=409, detail="不能停用当前登录账号")
        if not body.is_active and user.is_active:
            await _ensure_system_user_lifecycle_safe(user, db, action="停用")
        user.is_active = body.is_active
    if body.display_name is not None:
        user.display_name = await _require_unique_hr_display_name(
            body.display_name,
            db,
            linked_username=user.username,
        )
    if body.department is not None:
        user.department = body.department.strip()
    if body.password is not None:
        policy = await _security_policy(db)
        if len(body.password) < policy.min_password_length: raise HTTPException(status_code=422, detail=f"密码至少需要 {policy.min_password_length} 位")
        user.password_hash = hash_password(body.password)
        user.password_changed_at = None; user.must_change_password = True; user.failed_login_attempts = 0; user.locked_until = None
    profile = dict(user.profile or {})
    if "manager_id" in body.model_fields_set:
        profile.update(await _system_user_manager_profile(body.manager_id or None, db))
    for key in ("access_level", "lead_rate", "copy_rate"):
        if key in body.model_fields_set:
            value = getattr(body, key)
            profile[key] = (value or "").strip()
    if body.profile is not None:
        profile = {**profile, **body.profile}
    await _ensure_unique_dingtalk_user_id(profile, db, user.id, user.display_name)
    user.profile = profile
    await db.commit(); await db.refresh(user)
    return _system_user_dict(user)


@router.get(f"{settings.api_prefix}/system/users/{{user_id}}/permissions")
async def get_system_user_permissions(user_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin, _user_permission_overrides, _user_permission_payload,
    )
    _require_admin(identity)
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"user_id": user.id, "username": user.username, "overrides": _user_permission_overrides(user), "effective": await _user_permission_payload(user, db)}


@router.patch(f"{settings.api_prefix}/system/users/{{user_id}}/permissions")
async def update_system_user_permissions(user_id: int, body: UserPermissionOverrideUpdate, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin, _system_user_role_ids, _user_permission_overrides, _user_permission_payload,
    )
    from app.core.system import (
        _system_audit,
    )
    _require_admin(identity)
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if "admin" in _system_user_role_ids(user):
        raise HTTPException(status_code=422, detail="系统管理员保持完整权限，不能设置用户级权限覆盖")
    profile = dict(user.profile or {})
    if body.clear:
        profile.pop("permission_overrides", None)
    else:
        overrides: dict[str, object] = {}
        if body.menu_keys is not None:
            menu_keys = list(dict.fromkeys(body.menu_keys))
            legacy_keys = set((await db.scalars(select(SystemMenu.key).where(~SystemMenu.key.in_(SYSTEM_MENU_ROUTE_KEYS)))).all())
            all_menu_keys = set(MENU_KEYS) | legacy_keys
            invalid = sorted(set(menu_keys) - all_menu_keys)
            if invalid:
                raise HTTPException(status_code=422, detail=f"无效菜单权限：{', '.join(invalid)}")
            if "user-center" not in menu_keys:
                raise HTTPException(status_code=422, detail="用户中心为基础权限，不能移除")
            overrides["menu_keys"] = menu_keys
        if body.field_keys is not None:
            field_keys = list(dict.fromkeys(body.field_keys))
            invalid_fields = sorted(set(field_keys) - set(FIELD_KEYS))
            if invalid_fields:
                raise HTTPException(status_code=422, detail=f"无效字段权限：{', '.join(invalid_fields)}")
            overrides["field_keys"] = field_keys
        if body.data_scope is not None:
            data_scope = body.data_scope.strip()
            if data_scope not in ROLE_DATA_SCOPES:
                raise HTTPException(status_code=422, detail="数据范围无效")
            overrides["data_scope"] = data_scope
        profile["permission_overrides"] = overrides
    user.profile = profile
    await _system_audit(db, identity, "更新用户权限覆盖", f"用户:{user.username}", {"user_id": user.id, "overrides": _user_permission_overrides(user)})
    await db.commit(); await db.refresh(user)
    return {"user_id": user.id, "username": user.username, "overrides": _user_permission_overrides(user), "effective": await _user_permission_payload(user, db)}


@router.delete(f"{settings.api_prefix}/system/users/{{user_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_system_user(user_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_system_user_lifecycle_safe, _require_admin, _system_user_role_ids,
    )
    _require_admin(identity)
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.username == identity["username"]:
        raise HTTPException(status_code=409, detail="不能删除当前登录账号")
    if "admin" in _system_user_role_ids(user):
        raise HTTPException(status_code=409, detail="不能删除系统管理员账号")
    await _ensure_system_user_lifecycle_safe(user, db, action="删除")
    await db.delete(user); await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(f"{settings.api_prefix}/system/users/{{user_id}}/reset-password")
async def reset_system_user_password(user_id: int, body: SystemUserPasswordResetInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Reset a password as a distinct security action, not a profile edit.

    The recipient must change this administrator-issued password before using
    business APIs.  A reset also removes any stale login lock, which is the
    practical equivalent of the old system's separate "reset password" action.
    """
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _security_policy, _system_user_dict,
    )
    _require_admin(identity)
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.username == identity["username"]:
        raise HTTPException(status_code=409, detail="不能重置当前登录账号的密码，请使用个人资料中的修改密码功能")
    policy = await _security_policy(db)
    if len(body.new_password) < policy.min_password_length:
        raise HTTPException(status_code=422, detail=f"新密码至少需要 {policy.min_password_length} 位")
    if verify_password(body.new_password, user.password_hash):
        raise HTTPException(status_code=400, detail="新密码不能与当前密码相同")
    user.password_hash = hash_password(body.new_password)
    user.password_changed_at = None
    user.must_change_password = True
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.commit(); await db.refresh(user)
    return _system_user_dict(user)


@router.post(f"{settings.api_prefix}/system/users/{{user_id}}/unlock")
async def unlock_system_user(user_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _system_user_dict,
    )
    _require_admin(identity)
    user = await db.get(User, user_id)
    if not user: raise HTTPException(status_code=404, detail="用户不存在")
    user.failed_login_attempts = 0; user.locked_until = None
    await db.commit(); await db.refresh(user); return _system_user_dict(user)


@router.get(f"{settings.api_prefix}/system/security-policy")
async def get_security_policy(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _security_policy, _security_policy_dict,
    )
    _require_admin(identity); return _security_policy_dict(await _security_policy(db))


@router.patch(f"{settings.api_prefix}/system/security-policy")
async def update_security_policy(body: SecurityPolicyUpdate, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _security_policy, _security_policy_dict,
    )
    _require_admin(identity); policy = await _security_policy(db)
    for key, value in body.model_dump().items(): setattr(policy, key, value)
    policy.updated_by = identity["username"]
    await db.commit(); await db.refresh(policy); return _security_policy_dict(policy)


@router.get(f"{settings.api_prefix}/system/parameter-categories")
async def list_system_parameter_categories(identity: dict = Depends(current_identity)):
    from app.core.permissions import (
        _require_admin,
    )
    _require_admin(identity)
    return {"items": [{"key": key, "name": name} for key, name in SYSTEM_PARAMETER_CATEGORIES.items()]}


@router.get(f"{settings.api_prefix}/system/parameters/cause/autocomplete")
async def autocomplete_system_causes(keyword: str = "", limit: int = Query(20, ge=1, le=50), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Return cause nodes for case forms without exposing unrelated parameters."""
    statement = select(SystemParameter).where(SystemParameter.category == "cause", SystemParameter.is_active.is_(True))
    if keyword.strip():
        term = f"%{keyword.strip()}%"
        statement = statement.where(or_(SystemParameter.code.ilike(term), SystemParameter.name.ilike(term)))
    items = (await db.scalars(statement.order_by(SystemParameter.sort_order, SystemParameter.id).limit(limit))).all()
    return {"items": [{"id": item.id, "code": item.code, "name": item.name} for item in items]}


@router.get(f"{settings.api_prefix}/system/parameters/options")
async def list_system_parameter_options(category: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Expose active, form-safe parameter choices to authenticated users."""
    from app.core.cases import (
        _case_file_type_tree,
    )
    from app.core.finance import (
        _fee_type_catalog,
    )
    if category not in {"notary_office", "fee_type", "case_file_type"}:
        raise HTTPException(status_code=422, detail="当前参数分类不提供业务选项")
    items = (await db.scalars(select(SystemParameter).where(
        SystemParameter.category == category,
        SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.sort_order, SystemParameter.id))).all()
    if category == "fee_type":
        return {"items": _fee_type_catalog(list(items))}
    if category == "case_file_type":
        return {"items": _case_file_type_tree(list(items))}
    return {"items": [{"id": item.id, "code": item.code, "name": item.name} for item in items]}


@router.get(f"{settings.api_prefix}/system/parameters")
async def list_system_parameters(category: str = "", keyword: str = "", page: int | None = Query(None, ge=1), page_size: int | None = Query(None, ge=1, le=200), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _system_parameter_dict,
    )
    _require_admin(identity)
    if category and category not in SYSTEM_PARAMETER_CATEGORIES: raise HTTPException(status_code=422, detail="参数分类无效")
    cache_key = category or "__all__"
    if not keyword.strip() and cache_key in SYSTEM_PARAMETER_CACHE:
        result = SYSTEM_PARAMETER_CACHE[cache_key]
        if page is None and page_size is None:
            return {"items": result, "categories": SYSTEM_PARAMETER_CATEGORIES, "cached": True}
        current_page, current_size = page or 1, page_size or 15
        total = len(result)
        start = (current_page - 1) * current_size
        return {"items": result[start:start + current_size], "total": total, "page": current_page, "page_size": current_size, "categories": SYSTEM_PARAMETER_CATEGORIES, "cached": True}
    statement = select(SystemParameter)
    if category: statement = statement.where(SystemParameter.category == category)
    if keyword.strip():
        term = f"%{keyword.strip()}%"
        keyword_fields = [SystemParameter.code.ilike(term), SystemParameter.name.ilike(term)]
        if category == "payment_type":
            keyword_fields.extend([
                SystemParameter.extra["nature"].as_string().ilike(term),
                SystemParameter.extra["payee"].as_string().ilike(term),
                SystemParameter.extra["account_bank"].as_string().ilike(term),
                SystemParameter.extra["account"].as_string().ilike(term),
            ])
        statement = statement.where(or_(*keyword_fields))
    items = (await db.scalars(statement.order_by(SystemParameter.sort_order, SystemParameter.id))).all()
    result = [_system_parameter_dict(item) for item in items]
    if not keyword.strip(): SYSTEM_PARAMETER_CACHE[cache_key] = result
    if page is None and page_size is None:
        return {"items": result, "categories": SYSTEM_PARAMETER_CATEGORIES, "cached": False}
    current_page, current_size = page or 1, page_size or 15
    total = len(result)
    start = (current_page - 1) * current_size
    return {"items": result[start:start + current_size], "total": total, "page": current_page, "page_size": current_size, "categories": SYSTEM_PARAMETER_CATEGORIES, "cached": False}


@router.get(f"{settings.api_prefix}/system/parameter-relations/{{kind}}")
async def list_system_parameter_relations(kind: str, source_id: int | None = Query(None), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    # These relations are runtime business rules used by ordinary case forms.
    # Authentication is sufficient for read access; mutation remains admin-only.
    from app.core.system import (
        _system_parameter_dict, _system_parameter_relation_config,
    )
    model, source_field, target_field, source_category, target_category = _system_parameter_relation_config(kind)
    sources = list((await db.scalars(select(SystemParameter).where(
        SystemParameter.category == source_category,
    ).order_by(SystemParameter.sort_order, SystemParameter.id))).all())
    targets = list((await db.scalars(select(SystemParameter).where(
        SystemParameter.category == target_category,
    ).order_by(SystemParameter.sort_order, SystemParameter.id))).all())
    rows = list((await db.scalars(select(model).order_by(getattr(model, source_field), getattr(model, target_field)))).all())
    relations: dict[str, list[int]] = {}
    for row in rows:
        relations.setdefault(str(getattr(row, source_field)), []).append(int(getattr(row, target_field)))
    return {
        "kind": kind,
        "source_category": source_category,
        "target_category": target_category,
        "sources": [_system_parameter_dict(item) for item in sources],
        "targets": [_system_parameter_dict(item) for item in targets],
        "relations": relations,
        "source_id": source_id,
        "target_ids": relations.get(str(source_id), []) if source_id is not None else None,
    }


@router.put(f"{settings.api_prefix}/system/parameter-relations/{{kind}}")
async def replace_system_parameter_relations(kind: str, body: SystemParameterRelationReplaceInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _system_audit, _system_parameter_relation_config,
    )
    _require_admin(identity)
    model, source_field, target_field, source_category, target_category = _system_parameter_relation_config(kind)
    target_ids = list(dict.fromkeys(body.target_ids))
    source = await db.scalar(select(SystemParameter).where(
        SystemParameter.id == body.source_id,
        SystemParameter.category == source_category,
    ))
    if not source:
        raise HTTPException(status_code=422, detail="关联源参数不存在或分类不匹配")
    targets = list((await db.scalars(select(SystemParameter).where(
        SystemParameter.id.in_(target_ids),
        SystemParameter.category == target_category,
    ))).all()) if target_ids else []
    if len(targets) != len(target_ids):
        raise HTTPException(status_code=422, detail="关联目标参数不存在或分类不匹配")
    current_rows = list((await db.scalars(
        select(model).where(getattr(model, source_field) == source.id).with_for_update()
    )).all())
    before = sorted(int(getattr(row, target_field)) for row in current_rows)
    for row in current_rows:
        await db.delete(row)
    for target_id in target_ids:
        db.add(model(**{
            source_field: source.id,
            target_field: target_id,
            "created_by": identity["username"],
            "updated_by": identity["username"],
        }))
    await _system_audit(db, identity, "更新系统参数关联", f"{kind}:{source.code}", {
        "source_id": source.id, "before": before, "after": sorted(target_ids),
    })
    await db.commit()
    return {"kind": kind, "source_id": source.id, "target_ids": target_ids, "updated": True}


@router.post(f"{settings.api_prefix}/system/parameters", status_code=status.HTTP_201_CREATED)
async def create_system_parameter(body: SystemParameterInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _normalized_fee_type_extra,
    )
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _clear_parameter_cache, _system_audit, _system_parameter_dict, _validate_parameter_parent, _validate_parameter_references,
    )
    _require_admin(identity)
    if body.category not in SYSTEM_PARAMETER_CATEGORIES: raise HTTPException(status_code=422, detail="参数分类无效")
    code, name = body.code.strip(), body.name.strip()
    if body.category == "payment_type":
        candidates = list((await db.scalars(select(SystemParameter).where(SystemParameter.category == body.category))).all())
        next_payee = str((body.extra or {}).get("payee") or "").strip().casefold()
        duplicate = next((item for item in candidates if item.code == code or (next_payee and str((item.extra or {}).get("payee") or "").strip().casefold() == next_payee)), None)
    else:
        duplicate = await db.scalar(select(SystemParameter).where(SystemParameter.category == body.category, or_(SystemParameter.code == code, SystemParameter.name == name)))
    if duplicate: raise HTTPException(status_code=409, detail="同一分类下参数代码或名称已存在")
    next_extra = body.extra
    await _validate_parameter_parent(body.category, code, next_extra, db)
    if body.category == "fee_type":
        next_extra = await _normalized_fee_type_extra(code, next_extra, db)
    await _validate_parameter_references(body.category, next_extra, db)
    item = SystemParameter(**body.model_dump(exclude={"code", "name", "extra"}), code=code, name=name, extra=next_extra, created_by=identity["username"], updated_by=identity["username"])
    db.add(item); await db.flush()
    await _system_audit(db, identity, "创建系统参数", f"系统参数:{item.category}/{item.code}", {"id": item.id, "category": item.category, "code": item.code})
    await db.commit(); await db.refresh(item); _clear_parameter_cache(body.category, identity["username"])
    return _system_parameter_dict(item)


@router.patch(f"{settings.api_prefix}/system/parameters/{{parameter_id}}")
async def update_system_parameter(parameter_id: int, body: SystemParameterUpdate, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _normalized_fee_type_extra,
    )
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _clear_parameter_cache, _system_audit, _system_parameter_dict, _validate_parameter_parent, _validate_parameter_references,
    )
    _require_admin(identity)
    item = await db.get(SystemParameter, parameter_id)
    if not item: raise HTTPException(status_code=404, detail="系统参数不存在")
    code = body.code.strip() if body.code is not None else item.code
    name = body.name.strip() if body.name is not None else item.name
    next_extra = body.extra if body.extra is not None else (item.extra or {})
    if item.category == "payment_type":
        candidates = list((await db.scalars(select(SystemParameter).where(SystemParameter.category == item.category, SystemParameter.id != item.id))).all())
        next_payee = str(next_extra.get("payee") or "").strip().casefold()
        duplicate = next((candidate for candidate in candidates if candidate.code == code or (next_payee and str((candidate.extra or {}).get("payee") or "").strip().casefold() == next_payee)), None)
    else:
        duplicate = await db.scalar(select(SystemParameter).where(SystemParameter.category == item.category, SystemParameter.id != item.id, or_(SystemParameter.code == code, SystemParameter.name == name)))
    if duplicate: raise HTTPException(status_code=409, detail="同一分类下参数代码、名称或收款单位已存在")
    await _validate_parameter_parent(item.category, code, next_extra, db, current_id=item.id)
    if item.category == "fee_type":
        next_extra = await _normalized_fee_type_extra(code, next_extra, db)
        active_children = list((await db.scalars(select(SystemParameter).where(
            SystemParameter.category == "fee_type",
            SystemParameter.extra["parent_code"].as_string() == item.code,
            SystemParameter.is_active.is_(True),
        ))).all())
        if body.is_active is False and active_children:
            raise HTTPException(status_code=409, detail="费用类型存在可用的下级类型，不能直接停用")
    await _validate_parameter_references(item.category, next_extra, db)
    previous_code = item.code
    for key, value in body.model_dump(exclude_unset=True, exclude={"extra"}).items(): setattr(item, key, value.strip() if key in {"code", "name"} else value)
    item.extra = next_extra
    if item.category == "fee_type" and previous_code != code:
        children = list((await db.scalars(select(SystemParameter).where(
            SystemParameter.category == "fee_type",
            SystemParameter.extra["parent_code"].as_string() == previous_code,
        ))).all())
        for child in children:
            child.extra = {**(child.extra or {}), "parent_code": code}
            child.updated_by = identity["username"]
    item.updated_by = identity["username"]
    await _system_audit(db, identity, "更新系统参数", f"系统参数:{item.category}/{item.code}", {"id": item.id, "category": item.category, "code": item.code})
    await db.commit(); await db.refresh(item); _clear_parameter_cache(item.category, identity["username"])
    return _system_parameter_dict(item)


@router.delete(f"{settings.api_prefix}/system/parameters/{{parameter_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_system_parameter(parameter_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _clear_parameter_cache, _parameter_reference_examples, _system_audit,
    )
    _require_admin(identity)
    item = await db.get(SystemParameter, parameter_id)
    if not item: raise HTTPException(status_code=404, detail="系统参数不存在")
    references = await _parameter_reference_examples(item, db)
    if references:
        raise HTTPException(status_code=409, detail=f"参数“{item.name}”已被业务记录引用（{ '、'.join(references) }），不能删除；请停用以保留历史数据")
    category = item.category
    await _system_audit(db, identity, "删除系统参数", f"系统参数:{category}/{item.code}", {"id": item.id, "category": category, "code": item.code})
    await db.delete(item); await db.commit(); _clear_parameter_cache(category, identity["username"])
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/system/configs")
async def list_system_configs(keyword: str = "", page: int | None = Query(None, ge=1), page_size: int | None = Query(None, ge=1, le=200), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin,
    )
    _require_admin(identity)
    items = (await db.scalars(select(SystemConfig).order_by(SystemConfig.id))).all()
    result = [{"key": item.key, "label": item.label, "group": item.group, "value": item.value or {}, "description": item.description, "updated_by": item.updated_by, "updated_at": item.updated_at} for item in items]
    supervisor_options = [
        {"username": user.username, "display_name": user.display_name}
        for user in (await db.scalars(select(User).where(User.is_active.is_(True)).order_by(User.display_name, User.username))).all()
    ]
    if keyword.strip():
        needle = keyword.strip().lower()
        result = [item for item in result if needle in " ".join([item["key"], item["label"], item["group"], item["description"], json.dumps(item["value"], ensure_ascii=False)]).lower()]
    if page is None and page_size is None:
        return {"items": result, "investigation_supervisor_options": supervisor_options}
    current_page, current_size = page or 1, page_size or 15
    total = len(result); start = (current_page - 1) * current_size
    return {"items": result[start:start + current_size], "total": total, "page": current_page, "page_size": current_size, "investigation_supervisor_options": supervisor_options}


@router.patch(f"{settings.api_prefix}/system/configs/{{config_key}}")
async def update_system_config(config_key: str, body: SystemConfigUpdate, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _system_audit, _validate_system_config,
    )
    _require_admin(identity)
    item = await db.scalar(select(SystemConfig).where(SystemConfig.key == config_key))
    if not item: raise HTTPException(status_code=404, detail="系统配置不存在")
    value = _validate_system_config(config_key, body.value)
    if config_key == "investigation_assignment":
        supervisor = await db.scalar(select(User).where(User.username == value["supervisor_username"], User.is_active.is_(True)))
        if not supervisor:
            raise HTTPException(status_code=422, detail="调查任务分配人必须是启用的系统人员")
    item.value = value; item.updated_by = identity["username"]
    await _system_audit(db, identity, "更新系统配置", f"系统配置:{item.key}", {"key": item.key})
    await db.commit(); await db.refresh(item)
    return {"key": item.key, "label": item.label, "group": item.group, "value": item.value, "description": item.description, "updated_by": item.updated_by, "updated_at": item.updated_at}


@router.get(f"{settings.api_prefix}/system/cache")
@router.get(f"{settings.api_prefix}/system/caches", include_in_schema=False)
async def list_system_caches(keyword: str = "", page: int | None = Query(None, ge=1), page_size: int | None = Query(None, ge=1, le=200), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _system_cache_list_payload,
    )
    _require_admin(identity)
    return await _system_cache_list_payload(keyword, page, page_size, db)


@router.post(f"{settings.api_prefix}/system/caches/clear")
async def clear_system_caches(body: CacheBatchClearInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _clear_all_system_parameter_cache, _clear_registered_cache, _registered_cache_is_clearable, _system_audit, _system_cache_entry_count,
    )
    _require_admin(identity)
    requested_keys = list(dict.fromkeys(body.cache_keys))
    keys = requested_keys if requested_keys else [key for key, definition in SYSTEM_CACHE_REGISTRY.items() if _registered_cache_is_clearable(definition)]
    unknown = [key for key in keys if key not in SYSTEM_CACHE_REGISTRY]
    if unknown:
        raise HTTPException(status_code=404, detail=f"缓存不存在: {unknown[0]}")
    unavailable = [key for key in keys if not _registered_cache_is_clearable(SYSTEM_CACHE_REGISTRY[key])]
    if unavailable:
        raise HTTPException(status_code=409, detail=f"缓存未启用，不能清理: {unavailable[0]}")
    if not requested_keys:
        _clear_all_system_parameter_cache(identity["username"])
    elif "system-parameters" in keys:
        _clear_all_system_parameter_cache(identity["username"])
    else:
        for key in keys:
            _clear_registered_cache(key, identity["username"])
    await _system_audit(db, identity, "清理系统缓存", "系统缓存:批量", {"cache_keys": keys, "clear_all": not requested_keys})
    await db.commit()
    return {"cleared": keys, "items": [{"key": key, "entry_count": await _system_cache_entry_count(key, SYSTEM_CACHE_REGISTRY[key], db), **SYSTEM_CACHE_META[key]} for key in keys]}


@router.post(f"{settings.api_prefix}/system/cache/clear-all")
async def clear_all_system_caches(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _clear_all_system_parameter_cache, _system_audit,
    )
    _require_admin(identity)
    # Clear every populated category, including categories without a legacy row.
    # This is deliberately limited to this API process's dictionary cache.
    cleared_buckets = _clear_all_system_parameter_cache(identity["username"])
    await _system_audit(db, identity, "清理系统缓存", "系统缓存:全部", {"cache_keys": cleared_buckets, "clear_all": True, "scope": "in_process_memory"})
    await db.commit()
    return {"cleared": cleared_buckets, "clear_all": True}


@router.post(f"{settings.api_prefix}/system/cache/{{cache_key}}/clear")
@router.post(f"{settings.api_prefix}/system/caches/{{cache_key}}/clear", include_in_schema=False)
async def clear_system_cache(cache_key: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _clear_registered_cache, _system_audit, _system_cache_entry_count,
    )
    _require_admin(identity)
    if cache_key not in SYSTEM_CACHE_REGISTRY: raise HTTPException(status_code=404, detail="缓存不存在")
    _clear_registered_cache(cache_key, identity["username"])
    await _system_audit(db, identity, "清理系统缓存", f"系统缓存:{cache_key}", {"cache_key": cache_key})
    await db.commit()
    definition = SYSTEM_CACHE_REGISTRY[cache_key]
    return {"key": cache_key, "cleared": True, "entry_count": await _system_cache_entry_count(cache_key, definition, db), **SYSTEM_CACHE_META[cache_key]}


@router.get(f"{settings.api_prefix}/system/menus/navigation")
async def navigation_menus(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _identity_role_ids, _permission_payload_for_identity, _user_permission_payload,
    )
    from app.core.system import (
        _system_menu_dict,
    )
    items = [
        item for item in (await db.scalars(
            select(SystemMenu).where(SystemMenu.is_active.is_(True), SystemMenu.is_visible.is_(True)).order_by(SystemMenu.sort_order, SystemMenu.id)
        )).all()
        if item.key in SYSTEM_MENU_ROUTE_KEYS or item.key.startswith("legacy-menu-")
    ]
    if "admin" in _identity_role_ids(identity):
        visible_keys = {item.key for item in items}
    else:
        user = await db.scalar(select(User).where(User.username == identity["username"]))
        permission = await _user_permission_payload(user, db) if user else await _permission_payload_for_identity(identity, db)
        visible_keys = {"dashboard", *permission["menu_keys"]}
        # Parent containers must remain visible for an authorized child, but
        # they are not themselves added as route grants.
        for key in list(visible_keys):
            parent_key = MENU_PARENT_BY_KEY.get(key, "")
            while parent_key:
                visible_keys.add(parent_key)
                parent_key = MENU_PARENT_BY_KEY.get(parent_key, "")
    return {"items": [_system_menu_dict(item) for item in items if item.key in visible_keys]}


@router.get(f"{settings.api_prefix}/system/menus")
async def list_system_menus(keyword: str = "", page: int | None = Query(None, ge=1), page_size: int | None = Query(None, ge=1, le=200), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _system_menu_dict,
    )
    _require_admin(identity)
    items = (await db.scalars(select(SystemMenu).order_by(SystemMenu.sort_order, SystemMenu.id))).all()
    result = [_system_menu_dict(item) for item in items]
    if keyword.strip():
        needle = keyword.strip().lower()
        result = [item for item in result if needle in " ".join(str(item.get(key) or "") for key in ("key", "parent_key", "label", "description")).lower()]
    if page is None and page_size is None:
        return {"items": result, "total": len(result)}
    current_page, current_size = page or 1, page_size or 15
    total = len(result); start = (current_page - 1) * current_size
    return {"items": result[start:start + current_size], "total": total, "page": current_page, "page_size": current_size}


@router.post(f"{settings.api_prefix}/system/menus", status_code=status.HTTP_201_CREATED)
async def create_system_menu(body: SystemMenuInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _system_audit, _system_menu_dict,
    )
    _require_admin(identity)
    requested_key = (body.key or "").strip()
    menu_key = requested_key or f"legacy-menu-{uuid4().hex[:12]}"
    parent_key = body.parent_key.strip()
    if requested_key and menu_key not in SYSTEM_MENU_ROUTE_KEYS:
        raise HTTPException(status_code=422, detail="菜单标识不是已实现的系统路由，不能创建菜单入口")
    if await db.scalar(select(SystemMenu.id).where(SystemMenu.key == menu_key)):
        raise HTTPException(status_code=409, detail="菜单标识已经存在")
    if parent_key and not await db.scalar(select(SystemMenu.id).where(SystemMenu.key == parent_key)):
        raise HTTPException(status_code=422, detail="父级菜单不存在")
    item = SystemMenu(
        key=menu_key,
        parent_key=parent_key,
        label=body.label.strip(),
        icon=body.icon.strip(),
        sort_order=body.sort_order,
        is_visible=body.is_visible,
        is_active=body.is_active,
        updated_by=identity["username"],
    )
    if hasattr(item, "description"):
        item.description = body.description.strip()
    db.add(item)
    await db.flush()
    await _system_audit(db, identity, "创建系统菜单", f"系统菜单:{item.key}", {"id": item.id, "key": item.key})
    await db.commit()
    await db.refresh(item)
    return _system_menu_dict(item)


@router.patch(f"{settings.api_prefix}/system/menus/{{menu_id}}")
async def update_system_menu(menu_id: int, body: SystemMenuUpdate, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _system_audit, _system_menu_dict,
    )
    _require_admin(identity)
    item = await db.get(SystemMenu, menu_id)
    if not item: raise HTTPException(status_code=404, detail="菜单不存在")
    changes = body.model_dump(exclude_none=True)
    if item.key in {"dashboard", "system", "system-management"} and (changes.get("is_active") is False or changes.get("is_visible") is False):
        raise HTTPException(status_code=422, detail="控制台和系统管理入口不能隐藏或停用")
    for key, value in changes.items():
        setattr(item, key, value.strip() if isinstance(value, str) else value)
    item.updated_by = identity["username"]
    await _system_audit(db, identity, "更新系统菜单", f"系统菜单:{item.key}", {"id": item.id, "key": item.key})
    await db.commit(); await db.refresh(item)
    return _system_menu_dict(item)


@router.delete(f"{settings.api_prefix}/system/menus/{{menu_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_system_menu(menu_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _system_audit,
    )
    _require_admin(identity)
    item = await db.get(SystemMenu, menu_id)
    if not item:
        raise HTTPException(status_code=404, detail="菜单不存在")
    if item.key in {key for key, *_ in DEFAULT_SYSTEM_MENUS}:
        raise HTTPException(status_code=422, detail="系统预置菜单不能删除")
    if await db.scalar(select(SystemMenu.id).where(SystemMenu.parent_key == item.key)):
        raise HTTPException(status_code=409, detail="请先删除该菜单的子菜单")
    await _system_audit(db, identity, "删除系统菜单", f"系统菜单:{item.key}", {"id": item.id, "key": item.key})
    await db.delete(item)
    await db.commit()


@router.post(f"{settings.api_prefix}/system/menus/reset")
async def reset_system_menus(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _system_audit, _system_menu_dict,
    )
    _require_admin(identity)
    defaults = {key: (parent_key, label, icon, sort_order) for key, parent_key, label, icon, sort_order in DEFAULT_SYSTEM_MENUS}
    items = (await db.scalars(select(SystemMenu))).all()
    by_key = {item.key: item for item in items}
    for item in items:
        if item.key not in defaults:
            item.is_visible = False; item.is_active = False; item.updated_by = identity["username"]
    for key, (parent_key, label, icon, sort_order) in defaults.items():
        item = by_key.get(key)
        if not item:
            db.add(SystemMenu(key=key, parent_key=parent_key, label=label, icon=icon, sort_order=sort_order, updated_by=identity["username"]))
            continue
        item.parent_key = parent_key; item.label = label; item.icon = icon; item.sort_order = sort_order
        item.is_visible = True; item.is_active = True; item.updated_by = identity["username"]
    await _system_audit(db, identity, "重置系统菜单", "系统菜单:重置", {"count": len(defaults)})
    await db.commit()
    refreshed = (await db.scalars(select(SystemMenu).order_by(SystemMenu.sort_order, SystemMenu.id))).all()
    return {"items": [_system_menu_dict(item) for item in refreshed], "total": len(refreshed)}


@router.get(f"{settings.api_prefix}/system/role-permissions")
async def list_role_permissions(
    keyword: str = "", page: int | None = Query(None, ge=1), page_size: int | None = Query(None, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _require_admin, _role_permission_dict, _system_permission_tree,
    )
    _require_admin(identity)
    all_items = list((await db.scalars(select(RolePermission).order_by(RolePermission.id))).all())
    items = all_items
    if keyword.strip():
        needle = keyword.strip().casefold()
        items = [item for item in items if needle in " ".join((item.role, item.display_name, item.data_scope)).casefold()]
    response_items = [_role_permission_dict(item) for item in items]
    response = {"items": response_items}
    if page is not None or page_size is not None or keyword.strip():
        current_page, current_size = page or 1, page_size or 15
        total = len(items)
        start = (current_page - 1) * current_size
        response.update({
            "items": response_items[start:start + current_size], "total": total,
            "page": current_page, "page_size": current_size,
            "pages": (total + current_size - 1) // current_size if total else 0,
        })
    legacy_keys = list((await db.scalars(select(SystemMenu.key).where(~SystemMenu.key.in_(SYSTEM_MENU_ROUTE_KEYS)))).all())
    tree_permission = next((item for item in all_items if item.role == identity.get("role")), all_items[0] if all_items else None)
    response.update({"available_menu_keys": [*MENU_KEYS, *legacy_keys], "available_field_keys": FIELD_KEYS, "permission_tree": await _system_permission_tree(db, tree_permission)})
    return response


@router.patch(f"{settings.api_prefix}/system/role-permissions/{{role}}")
async def update_role_permission(role: str, body: RolePermissionUpdate, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _require_admin, _role_permission_dict, _split_role_permission_keys,
    )
    from app.core.system import (
        _system_audit,
    )
    _require_admin(identity)
    if role not in DEFAULT_ROLE_PERMISSIONS:
        raise HTTPException(status_code=404, detail="角色不存在")
    data_scope = body.data_scope.strip()
    if data_scope not in ROLE_DATA_SCOPES:
        raise HTTPException(status_code=422, detail="数据范围无效")
    legacy_keys = set((await db.scalars(select(SystemMenu.key).where(~SystemMenu.key.in_(SYSTEM_MENU_ROUTE_KEYS)))).all())
    all_menu_keys = set(MENU_KEYS) | legacy_keys
    invalid = sorted(set(body.menu_keys) - all_menu_keys)
    if invalid:
        raise HTTPException(status_code=422, detail=f"无效菜单权限：{', '.join(invalid)}")
    menu_keys = list(dict.fromkeys(body.menu_keys))
    item = await db.scalar(select(RolePermission).where(RolePermission.role == role))
    _, existing_actions = _split_role_permission_keys(item.menu_keys if item else [])
    action_keys = list(dict.fromkeys(body.action_keys if body.action_keys is not None else (existing_actions or ([item["code"] for item in SYSTEM_ACTION_DEFINITIONS] if role == "admin" else []))))
    invalid_actions = sorted(set(action_keys) - set(SYSTEM_ACTION_BY_CODE))
    if invalid_actions:
        raise HTTPException(status_code=422, detail=f"无效动作权限：{', '.join(invalid_actions)}")
    if "user-center" not in menu_keys:
        raise HTTPException(status_code=422, detail="用户中心为基础权限，不能移除")
    if role == "admin" and set(menu_keys) != all_menu_keys:
        raise HTTPException(status_code=422, detail="系统管理员必须保留全部菜单权限")
    if role == "admin" and data_scope != DEFAULT_ROLE_PERMISSIONS["admin"]["data_scope"]:
        raise HTTPException(status_code=422, detail="系统管理员必须保留全所数据权限")
    invalid_fields = sorted(set(body.field_keys) - set(FIELD_KEYS))
    if invalid_fields: raise HTTPException(status_code=422, detail=f"无效字段权限：{', '.join(invalid_fields)}")
    field_keys = list(dict.fromkeys(body.field_keys))
    if role == "admin" and set(field_keys) != set(FIELD_KEYS): raise HTTPException(status_code=422, detail="系统管理员必须保留全部字段权限")
    if role == "admin" and body.action_keys is not None and set(action_keys) != set(SYSTEM_ACTION_BY_CODE):
        raise HTTPException(status_code=422, detail="系统管理员必须保留全部动作权限")
    stored_menu_keys = menu_keys + [f"@action:{key}" for key in action_keys]
    if not item:
        config = DEFAULT_ROLE_PERMISSIONS[role]
        item = RolePermission(role=role, display_name=config["display_name"], data_scope=data_scope, menu_keys=stored_menu_keys, field_keys=field_keys)
        db.add(item)
    else:
        item.data_scope = data_scope
        item.menu_keys = stored_menu_keys
        item.field_keys = field_keys
    await _system_audit(db, identity, "更新角色权限", f"角色权限:{role}", {"role": role, "menu_keys": menu_keys, "action_keys": action_keys})
    await db.commit(); await db.refresh(item)
    return _role_permission_dict(item)


@router.get(f"{settings.api_prefix}/dashboard")
async def dashboard(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    # Keep dashboard task counts on the same lifecycle snapshot as /tasks.
    # Otherwise an auto-completed handoff can remain in the dashboard after it
    # has already disappeared from the user's accepted-task queue.
    from app.core.cases import (
        _case_action_granted, _dashboard_case_hearing, _dashboard_latest_case_row, _is_pending_execution_case, _matches_dashboard_case_queue,
    )
    from app.core.contracts import (
        _contract_person_values,
    )
    from app.core.crm import (
        _dashboard_customer_for_case,
    )
    from app.core.documents import (
        _seal_authorization_context,
    )
    from app.core.finance import (
        _fee_query_rows, _refund_case_fee_rows,
    )
    from app.core.formatters import (
        _dashboard_case_date, _normalized_customer_name, _user_display_map,
    )
    from app.core.investigation import (
        _is_investigation_task,
    )
    from app.core.permissions import (
        _case_personal_scope_condition, _record_scope_conditions,
    )
    from app.core.projections import (
        _receivable_detail_projection,
    )
    from app.core.system import (
        _record_person_usernames,
    )
    from app.core.tasks import (
        _apply_task_auto_completion, _apply_task_overdue_performance, _task_dict,
    )
    await _apply_task_auto_completion(db)
    await _apply_task_overdue_performance(db)
    scope = await _record_scope_conditions(identity, db)
    dashboard_modules = {"case", "task", "finance", "refund", "contract", "clue", "seal"}
    records = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module.in_(dashboard_modules), *scope,
    ))).all()
    by_module = {module: [item for item in records if item.module == module] for module in {"case", "task", "finance", "refund", "contract", "clue", "seal"}}
    cases, tasks = by_module["case"], by_module["task"]
    finances = by_module["finance"] + by_module["refund"]
    username = identity["username"]
    pending_statuses = {"待审批", "审批中", "待审核"}
    def count(rows, statuses, owner_only=False, predicate=None):
        return sum(item.status in statuses and (not owner_only or item.owner == username) and (predicate is None or predicate(item.data or {})) for item in rows)
    def fee_match(word): return lambda data: word in str(data.get("fee_type") or data.get("expense_scope") or "")
    official = lambda data: any(word in str(data.get("fee_type") or data.get("expense_scope") or "") for word in ("官方", "官费", "律所"))
    def amount(value: object) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
    unpaid_official = await _fee_query_rows(
        identity, db, scope="mine", unpaid_official=True,
    )
    receivable_details = await _receivable_detail_projection(identity, db, list(records))
    personal_official_receivables = [
        item for item in receivable_details
        if item["fee_category"] == "official" and item["owner"] == username
    ]
    unpaid_amount = sum(item["remaining_amount"] for item in personal_official_receivables)
    pending_refunds = await _refund_case_fee_rows(identity, db)
    def case_signal(item: BusinessRecord, *words: str) -> bool:
        data = item.data or {}
        values = [
            item.status, data.get("case_phase"), data.get("execution_status"),
            data.get("required_action"), data.get("review_action"), data.get("supplement_type"),
        ]
        return any(word in str(value or "") for word in words for value in values)
    supplement_evidence = [item for item in cases if _matches_dashboard_case_queue(item, "supplement_evidence")]
    supplement_opinion = [item for item in cases if _matches_dashboard_case_queue(item, "supplement_opinion")]
    personal_cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case",
        _case_personal_scope_condition(username),
    ))).all())
    appeal_phases = {"一审等待上诉", "待上诉"}
    pending_appeal = [
        item for item in personal_cases
        if str(item.status or "").strip() in appeal_phases
    ]
    pending_execution = [item for item in cases if _is_pending_execution_case(item)]
    urgent_cases = [item for item in cases if _matches_dashboard_case_queue(item, "urgent")]
    metrics = [
        {
            "key": "official-fee-unpaid", "label": "待缴官费",
            "value": f"{len(unpaid_official)}件", "tone": "amber",
            "route": "finance-fee-query",
            "query": {"scope": "mine", "unpaid_official": True},
        },
        {"key": "refund-pending", "label": "待退费", "value": f"{len(pending_refunds)}件", "tone": "cyan", "route": "finance-refund"},
        {"key": "evidence-supplement", "label": "补充证据", "value": f"{len(supplement_evidence)}件", "tone": "green", "route": "case-company-supplement-evidence"},
        {"key": "opinion-supplement", "label": "补充意见", "value": f"{len(supplement_opinion)}件", "tone": "blue", "route": "case-company-supplement-opinion"},
        {"key": "appeal-pending", "label": "待上诉", "value": f"{len(pending_appeal)}件", "tone": "red", "route": "case-mine-appeal"},
        {"key": "execution-pending", "label": "待执行", "value": f"{len(pending_execution)}件", "tone": "purple", "route": "case-company-execution"},
        {"key": "urgent-cases", "label": "紧急案件", "value": f"{len(urgent_cases)}件", "tone": "orange", "route": "case-company-urgent"},
        {
            "key": "official-fee-unreceived", "label": "未到官费金额",
            "value": f"{unpaid_amount:.2f}元", "tone": "navy",
            "route": "contract-receivable-detail",
            "detail_context": {
                "contract_no": "", "return_view": "contract-receivable-mine",
                "amount_filter": "official-unreceived", "owner": username,
            },
        },
    ]
    todo_specs = [
        ("待处理任务", tasks, {"待接收", "待处理", "处理中"}, None, "待审批官方费用", finances, pending_statuses, official),
        ("待审批线索", by_module["clue"], pending_statuses, None, "待审批内部费用", finances, pending_statuses, fee_match("内部")),
        ("待审批合同", by_module["contract"], pending_statuses, None, "待审批结算费用", finances, pending_statuses, fee_match("结算")),
        ("待审批用印", by_module["seal"], pending_statuses, None, "待审批归档费用", finances, pending_statuses, fee_match("归档")),
        ("待审核归档", cases, {"待归档审核", "亏损内审", "亏损审核"}, None, "待审核预损费用", finances, pending_statuses, fee_match("预损")),
    ]
    todos = [[left, count(left_rows, left_states, True, left_pred), count(left_rows, left_states, False, left_pred), right, count(right_rows, right_states, True, right_pred), count(right_rows, right_states, False, right_pred)] for left, left_rows, left_states, left_pred, right, right_rows, right_states, right_pred in todo_specs]

    # The legacy dashboard's blue number is the signed-in user's actionable
    # queue; the orange number is that user's rejected/returned queue.  Neither
    # number is a company-wide total, even for administrators.
    personal_tasks = [
        item for item in tasks
        if not _is_investigation_task(item)
        and (
            item.owner == username
            or str((item.data or {}).get("initiator") or "").strip() == username
        )
    ]
    def task_is_effectively_pending(item: BusinessRecord) -> bool:
        # The task centre presents an overdue task in the processing tab even
        # when the stored workflow state is still 待接收/待处理.
        if _task_dict(item)["status"] not in {"待接收", "待处理"}:
            return False
        data = item.data or {}
        if item.status != "待接收" or data.get("handoff_restarted"):
            return True
        auto_complete_at = str(data.get("handoff_auto_complete_at") or "").strip()
        if not auto_complete_at:
            return True
        try:
            return date.fromisoformat(auto_complete_at) > date.today()
        except ValueError:
            return True
    personal_todo_counts = {
        "待处理任务": (
            sum(item.owner == username and task_is_effectively_pending(item) for item in personal_tasks),
            sum(
                str((item.data or {}).get("initiator") or "").strip() == username
                and item.status == "已拒绝"
                for item in personal_tasks
            ),
        ),
        "待审批合同": (0, 0),
        "待审批线索": (
            sum(item.status == "待审批" for item in by_module["clue"]),
            sum(item.status in {"已驳回", "已拒绝"} for item in by_module["clue"]),
        ),
        "待审批用印": (0, 0),
        "待审核归档": (0, 0),
    }
    pending_contract_ids = set((await db.scalars(select(ContractApprovalStep.contract_record_id).where(
        ContractApprovalStep.approver == username,
        ContractApprovalStep.status == "待审批",
    ))).all())
    personal_todo_counts["待审批合同"] = (
        int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
            BusinessRecord.module == "contract",
            BusinessRecord.id.in_(pending_contract_ids),
            BusinessRecord.status.in_(pending_statuses),
        )) or 0) if pending_contract_ids else 0,
        int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
            BusinessRecord.module == "contract",
            BusinessRecord.owner == username,
            BusinessRecord.status.in_({"已拒绝", "已驳回"}),
        )) or 0),
    )

    seal_context = await _seal_authorization_context(identity, db)
    seal_approver = func.trim(func.coalesce(BusinessRecord.data["approver"].as_string(), ""))
    personal_todo_counts["待审批用印"] = (
        int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
            BusinessRecord.module == "seal",
            BusinessRecord.status == "待审批",
            or_(seal_approver == "", seal_approver == username),
        )) or 0) if seal_context["approve"] or seal_context["reject"] else 0,
        int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
            BusinessRecord.module == "seal",
            BusinessRecord.owner == username,
            BusinessRecord.status == "已拒绝",
        )) or 0),
    )

    archive_action_allowed = await _case_action_granted(identity, db, "case.archive.review")
    archive_scope = await _record_scope_conditions(identity, db)
    archive_submitter = func.trim(func.coalesce(BusinessRecord.data["archive_submitter"].as_string(), ""))
    archive_reviewer = func.trim(func.coalesce(BusinessRecord.data["archive_reviewer"].as_string(), ""))
    archive_internal_reviewer = func.trim(func.coalesce(BusinessRecord.data["archive_internal_reviewer"].as_string(), ""))
    archive_assigned_to_user = or_(
        archive_reviewer == username,
        archive_internal_reviewer == username,
        and_(archive_reviewer == "", archive_internal_reviewer == "", BusinessRecord.owner == username),
    )
    personal_todo_counts["待审核归档"] = (
        int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
            BusinessRecord.module == "case",
            BusinessRecord.status.in_({"待归档审核", "亏损内审", "亏损审核"}),
            archive_assigned_to_user,
            archive_submitter != username,
            *archive_scope,
        )) or 0) if archive_action_allowed else 0,
        int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
            BusinessRecord.module == "case",
            archive_submitter == username,
            or_(
                BusinessRecord.status == "亏损归档拒绝",
                func.trim(func.coalesce(BusinessRecord.data["archive_reject_reason"].as_string(), "")) != "",
            ),
            *archive_scope,
        )) or 0),
    )
    for todo in todos:
        if todo[0] in personal_todo_counts:
            todo[1], todo[2] = personal_todo_counts[todo[0]]
    current_month = date.today().replace(day=1); month_keys = []
    for offset in range(9, -1, -1):
        year, month = current_month.year, current_month.month - offset
        while month <= 0: year -= 1; month += 12
        month_keys.append(f"{year:04d}-{month:02d}")
    case_trend = [{"date": key, "value": sum(item.created_at.strftime("%Y-%m") == key for item in cases)} for key in month_keys]
    stage_groups = [("立案待分配", lambda s: s in {"新案待分配", "立案待分配"}, "#f7474c"), ("文书准备", lambda s: "文书准备" in s, "#46b8b8"), ("一审", lambda s: "一审" in s, "#ffb45a"), ("二审", lambda s: "二审" in s, "#7f70b3"), ("再审", lambda s: "再审" in s, "#98a5b7"), ("执行", lambda s: "执行" in s, "#303030")]
    stage_counts = {label: 0 for label, _, _ in stage_groups}; other_count = 0
    for item in cases:
        matched = next((label for label, match, _ in stage_groups if match(item.status)), None)
        if matched: stage_counts[matched] += 1
        else: other_count += 1
    civil_distribution = [{"label": label, "value": stage_counts[label], "color": color} for label, _, color in stage_groups]
    if other_count: civil_distribution.append({"label": "其他", "value": other_count, "color": "#c5cbd3"})
    case_map = {item.id: item for item in cases}; visible_case_ids = set(case_map)
    today = date.today()
    cutoff = today + timedelta(days=100)
    projected_hearings = {
        item.id: projected
        for item in cases
        if (projected := _dashboard_case_hearing(item, today, cutoff)) is not None
    }
    hearing_rows = (await db.scalars(select(HearingSchedule).where(
        HearingSchedule.case_record_id.in_(visible_case_ids),
        HearingSchedule.hearing_date >= today,
        HearingSchedule.hearing_date <= cutoff,
    ).order_by(HearingSchedule.hearing_date, HearingSchedule.hearing_time))).all() if visible_case_ids else []
    hearings = list(projected_hearings.values())
    for item in hearing_rows:
        if item.case_record_id in projected_hearings:
            continue
        case = case_map[item.case_record_id]; data = case.data or {}
        hearings.append({"case_record_id": case.id, "weekday": "星期" + "一二三四五六日"[item.hearing_date.weekday()], "date": str(item.hearing_date), "time": item.hearing_time, "court": item.court, "case_no": case.serial_no, "client": case.customer, "lawyer": item.hearing_lawyer or data.get("hearing_lawyer", ""), "agent": ",".join(data.get("handling_lawyers", [])), "assistant": data.get("assistant", ""), "hearing_type": item.hearing_type, "courtroom": item.courtroom})
    hearings.sort(key=lambda item: (item["date"], item["time"], item["case_no"]))
    hearings = hearings[:13]
    latest_case_records = sorted(cases, key=lambda value: (_dashboard_case_date(value), value.id), reverse=True)[:13]
    customer_ids: set[int] = set()
    customer_nos: set[str] = set()
    customer_names: set[str] = set()
    person_usernames: set[str] = set()
    for item in latest_case_records:
        data = item.data or {}
        try:
            customer_id = int(data.get("customer_record_id") or data.get("customer_id") or 0)
        except (TypeError, ValueError):
            customer_id = 0
        if customer_id:
            customer_ids.add(customer_id)
        if customer_no := str(data.get("customer_no") or "").strip():
            customer_nos.add(customer_no)
        if item.customer:
            customer_names.add(_normalized_customer_name(item.customer))
        person_usernames.update(_record_person_usernames(item))
        for person_key in (
            "customer_manager", "customer_managers", "customer_manager_username", "customer_manager_usernames",
            "hearing_lawyer", "hearing_lawyers",
            "hearing_lawyer_username", "hearing_lawyer_usernames", "handling_lawyers",
            "handling_lawyer_usernames", "assistant", "assistants", "assistant_username",
            "assistant_usernames",
        ):
            person_usernames.update(_contract_person_values(data.get(person_key)))
    customer_conditions = []
    if customer_ids:
        customer_conditions.append(BusinessRecord.id.in_(customer_ids))
    if customer_nos:
        customer_conditions.append(BusinessRecord.serial_no.in_(customer_nos))
    if customer_names:
        customer_conditions.append(BusinessRecord.title.in_({item.customer for item in latest_case_records if item.customer}))
    related_customers = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "customer", or_(*customer_conditions),
    ))).all()) if customer_conditions else []
    customers_by_id = {item.id: item for item in related_customers}
    customers_by_no: dict[str, list[BusinessRecord]] = {}
    customers_by_name: dict[str, list[BusinessRecord]] = {}
    for item in related_customers:
        customers_by_no.setdefault(str(item.serial_no or "").strip(), []).append(item)
        customers_by_name.setdefault(_normalized_customer_name(item.title), []).append(item)
    for customer in related_customers:
        person_usernames.add(customer.owner)
        person_usernames.update(_contract_person_values((customer.data or {}).get("customer_managers")))
    users_by_username = await _user_display_map(person_usernames, db)
    latest_cases = [
        _dashboard_latest_case_row(
            item,
            _dashboard_customer_for_case(item, customers_by_id, customers_by_no, customers_by_name),
            users_by_username,
        )
        for item in latest_case_records
    ]
    return {"metrics": metrics, "todos": todos, "case_trend": case_trend, "civil_distribution": civil_distribution, "hearings": hearings, "latest_cases": latest_cases, "source": "realtime"}


@router.get(f"{settings.api_prefix}/search")
async def global_search(q: str = Query(min_length=2, max_length=100), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _filter_visible_attachments, _permission_payload_for_identity, _record_scope_conditions,
    )
    from app.core.system import (
        _record_module_menu_allowed,
    )
    keyword = q.strip(); like = f"%{keyword}%"
    permission = await _permission_payload_for_identity(identity, db)
    records = (await db.scalars(select(BusinessRecord).where(or_(BusinessRecord.serial_no.ilike(like), BusinessRecord.title.ilike(like), BusinessRecord.customer.ilike(like), BusinessRecord.owner.ilike(like), BusinessRecord.description.ilike(like)), *(await _record_scope_conditions(identity, db))).order_by(BusinessRecord.updated_at.desc()).limit(50))).all()
    records = [record for record in records if _record_module_menu_allowed(record.module, identity, permission)]
    document_menu_keys = set(permission.get("menu_keys") or [])
    can_search_attachments = "documents-files" in document_menu_keys
    can_search_templates = "documents-template" in document_menu_keys
    attachments = (await db.scalars(select(FileAttachment).where(or_(FileAttachment.original_name.ilike(like), FileAttachment.remark.ilike(like))).order_by(FileAttachment.created_at.desc()).limit(20))).all() if can_search_attachments else []
    attachments = await _filter_visible_attachments(attachments, identity, db) if attachments else []
    templates = (await db.scalars(select(DocumentTemplate).where(or_(DocumentTemplate.name.ilike(like), DocumentTemplate.description.ilike(like))).order_by(DocumentTemplate.updated_at.desc()).limit(20))).all() if can_search_templates else []
    route_map = {"customer": "customer-company", "contract": "contract-mine", "case": "case-company", "task": "task-company", "clue": "clue", "notary": "notary", "evidence": "evidence", "seal": "seal-my", "finance": "finance-fee-query", "finance_package": "finance-fee-query", "finance_settlement": "finance-fee-query", "finance_archive_settlement": "finance-fee-query", "invoice": "finance-invoice-mine", "refund": "finance-refund", "sms": "case-company", "document": "documents-register", "hr": "hr-all", "warehouse": "warehouse", "report": "reports"}
    items = [{"type": "record", "id": x.id, "module": x.module, "route": route_map.get(x.module, "dashboard"), "serial_no": x.serial_no, "title": x.title, "subtitle": x.customer or x.description, "status": x.status, "updated_at": x.updated_at, "related_id": (x.data or {}).get("case_id") if x.module == "sms" else None, "related_serial_no": (x.data or {}).get("case_no", "") if x.module == "sms" else ""} for x in records]
    items.extend({"type": "attachment", "id": x.id, "module": "attachment", "route": "documents-files", "serial_no": "附件", "title": x.original_name, "subtitle": f"{x.category}｜{x.remark}", "status": "", "updated_at": x.created_at} for x in attachments)
    items.extend({"type": "template", "id": x.id, "module": "template", "route": "documents-template", "serial_no": "模板", "title": x.name, "subtitle": f"{x.category}｜{x.description}", "status": "启用" if x.is_active else "停用", "updated_at": x.updated_at} for x in templates)
    return {"query": keyword, "items": items, "total": len(items)}


@router.get(f"{settings.api_prefix}/notifications")
async def list_notifications(
    unread_only: bool = False, sent_only: bool = False, read_status: str = "", sender: str = "",
    keyword: str = "", notification_type: str = "", source_type: str = "", level: str = "",
    reminder_only: bool = False, date_from: date | None = None, date_to: date | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.tasks import (
        _notification_dict, _sync_notifications,
    )
    await _sync_notifications(identity, db)
    if date_from and date_to and date_from > date_to: raise HTTPException(status_code=422, detail="开始日期不能晚于结束日期")
    conditions = [Notification.sender == identity["username"], Notification.sender_deleted.is_(False)] if sent_only else [Notification.recipient == identity["username"], Notification.recipient_deleted.is_(False)]
    if unread_only or read_status == "未读": conditions.append(Notification.is_read.is_(False))
    elif read_status == "已读": conditions.append(Notification.is_read.is_(True))
    elif read_status not in {"", "全部"}: raise HTTPException(status_code=422, detail="消息状态无效")
    if sender.strip(): conditions.append(Notification.sender.ilike(f"%{sender.strip()}%"))
    if keyword.strip():
        term = f"%{keyword.strip()}%"; conditions.append(or_(Notification.title.ilike(term), Notification.content.ilike(term)))
    if notification_type:
        if notification_type not in {"系统通知", "用户通知"}: raise HTTPException(status_code=422, detail="消息类型无效")
        conditions.append(Notification.notification_type == notification_type)
    if source_type:
        if source_type not in {"task", "finance", "contract", "case", "ipr_warning", "message"}: raise HTTPException(status_code=422, detail="消息来源无效")
        conditions.append(Notification.source_type == source_type)
    if level:
        if level not in {"info", "warning", "error"}: raise HTTPException(status_code=422, detail="提醒级别无效")
        conditions.append(Notification.level == level)
    if reminder_only:
        conditions.extend([
            Notification.source_type == "task",
            Notification.source_key.like("task-%"),
            ~Notification.source_key.like("task-message-%"),
            ~Notification.source_key.like("task-history-%"),
        ])
    if date_from: conditions.append(Notification.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to: conditions.append(Notification.created_at <= datetime.combine(date_to, datetime.max.time()))
    total = int(await db.scalar(select(func.count()).select_from(Notification).where(*conditions)) or 0)
    items = (await db.scalars(select(Notification).where(*conditions).order_by(Notification.created_at.desc(), Notification.id.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    unread = int(await db.scalar(select(func.count()).select_from(Notification).where(Notification.recipient == identity["username"], Notification.recipient_deleted.is_(False), Notification.is_read.is_(False))) or 0)
    users_by_username = await _user_display_map({value for item in items for value in (item.sender, item.recipient)}, db)
    return {"items": [_notification_dict(x, users_by_username) for x in items], "unread": unread, "total": total, "page": page, "page_size": page_size}


@router.get(f"{settings.api_prefix}/users/directory")
async def user_directory(
    purpose: str = "",
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.contracts import (
        _is_contract_approver,
    )
    from app.core.crm import (
        _active_customer_usernames,
    )
    from app.core.permissions import (
        _configured_user_job_role_name,
    )
    from app.core.system import (
        _active_employee_usernames, _is_smoke_test_username,
    )
    directory_purpose = purpose.strip().lower()
    if directory_purpose == "contract_approver":
        approver_employees = (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "hr",
        ))).all()
        eligible_usernames = {
            str((item.data or {}).get("username") or item.owner or "").strip().lower()
            for item in approver_employees
            if str((item.data or {}).get("username") or item.owner or "").strip()
        }
    else:
        eligible_usernames = (
            await _active_customer_usernames(db)
            if directory_purpose == "customer_contact"
            else await _active_employee_usernames(db)
        )
    if directory_purpose == "customer_manager":
        # Keep active legacy/system accounts in the response so an existing
        # customer source or manager can still render its display name.  The
        # eligibility flag below continues to prevent accounts without an
        # active employee record from being newly selected.
        candidates = (await db.scalars(select(User).where(
            User.is_active.is_(True),
        ).order_by(User.display_name, User.username))).all()
        items = [
            item for item in candidates
            if not _is_smoke_test_username(item.username)
            and str((item.profile or {}).get("account_type") or "").strip() != "客户账号"
        ]
    else:
        items = (await db.scalars(select(User).where(
            User.is_active.is_(True), User.username.in_(eligible_usernames),
        ).order_by(User.display_name, User.username))).all() if eligible_usernames else []
    employee_display_names: dict[str, str] = {}
    active_employees = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "hr",
        *([] if directory_purpose == "contract_approver" else [BusinessRecord.status.not_in({"离职", "停用"})]),
    ))).all()
    for employee in active_employees:
        username = str((employee.data or {}).get("username") or employee.owner or "").strip().lower()
        display_name = str(employee.title or "").strip()
        if username and display_name:
            employee_display_names.setdefault(username, display_name)
    job_roles = (await db.scalars(select(JobRole).where(JobRole.is_active.is_(True)))).all()
    roles_by_name = {item.name: item for item in job_roles}
    payload = []
    for item in items:
        position = _configured_user_job_role_name(item)
        account_type = str((item.profile or {}).get("account_type") or "员工账号").strip()
        job_role = roles_by_name.get(position)
        job_permissions = list(job_role.permissions or []) if job_role else []
        display_name = employee_display_names.get(item.username.lower()) or item.display_name
        payload.append({
            "username": item.username,
            "display_name": display_name,
            "department": item.department,
            "is_active": item.is_active,
            "role": item.role,
            "position": position,
            "staff_role": str((item.profile or {}).get("staff_role") or ""),
            "account_type": account_type,
            "job_permissions": job_permissions,
            "can_approve_contract": await _is_contract_approver(item, db),
            "eligible_customer_person": item.username.lower() in eligible_usernames if directory_purpose in {"customer_manager", "customer_contact"} else None,
        })
    return {"items": payload}


@router.post(f"{settings.api_prefix}/notifications/send", status_code=status.HTTP_201_CREATED)
async def send_user_message(body: UserMessageInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.tasks import (
        _notification_dict,
    )
    recipients = list(dict.fromkeys(value.strip() for value in body.recipients if value.strip()))
    active_users = set((await db.scalars(select(User.username).where(User.username.in_(recipients), User.is_active.is_(True)))).all())
    missing = sorted(set(recipients) - active_users)
    if missing: raise HTTPException(status_code=422, detail=f"接收人不存在或已停用：{', '.join(missing)}")
    batch = uuid4().hex
    items = []
    for recipient in recipients:
        item = Notification(source_key=f"user-message-{batch}-{recipient}", source_type="message", sender=identity["username"], recipient=recipient, notification_type="用户通知", title=body.title.strip(), content=body.content.strip(), level="info")
        db.add(item); items.append(item)
    await db.commit()
    for item in items: await db.refresh(item)
    users_by_username = await _user_display_map({value for item in items for value in (item.sender, item.recipient)}, db)
    return {"items": [_notification_dict(item, users_by_username) for item in items], "sent": len(items)}


@router.post(f"{settings.api_prefix}/notifications/{{notification_id}}/read")
async def read_notification(notification_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.tasks import (
        _notification_dict,
    )
    item = await db.get(Notification, notification_id)
    if not item or item.recipient != identity["username"] or item.recipient_deleted: raise HTTPException(status_code=404, detail="消息不存在")
    item.is_read = True; item.read_at = datetime.now()
    if item.source_type == "ipr_warning":
        warning = await db.scalar(select(IprCaseWarning).where(IprCaseWarning.notification_id == item.id, IprCaseWarning.recipient == identity["username"]))
        if warning and warning.status == "未读": warning.status = "已读"; warning.read_at = item.read_at
    await db.commit(); await db.refresh(item)
    users_by_username = await _user_display_map({item.sender, item.recipient}, db)
    return _notification_dict(item, users_by_username)


@router.post(f"{settings.api_prefix}/notifications/read-all")
async def read_all_notifications(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    items = (await db.scalars(select(Notification).where(Notification.recipient == identity["username"], Notification.recipient_deleted.is_(False), Notification.is_read.is_(False)))).all()
    now = datetime.now()
    for item in items:
        item.is_read = True; item.read_at = now
        if item.source_type == "ipr_warning":
            warning = await db.scalar(select(IprCaseWarning).where(IprCaseWarning.notification_id == item.id, IprCaseWarning.recipient == identity["username"]))
            if warning and warning.status == "未读": warning.status = "已读"; warning.read_at = now
    await db.commit(); return {"updated": len(items)}


@router.delete(f"{settings.api_prefix}/notifications/{{notification_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(notification_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    item = await db.get(Notification, notification_id)
    if not item: raise HTTPException(status_code=404, detail="消息不存在")
    changed = False
    if item.recipient == identity["username"] and not item.recipient_deleted: item.recipient_deleted = True; changed = True
    if item.sender == identity["username"] and not item.sender_deleted: item.sender_deleted = True; changed = True
    if not changed: raise HTTPException(status_code=404, detail="消息不存在")
    if item.recipient_deleted and item.sender_deleted: await db.delete(item)
    await db.commit(); return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/audit/events")
async def list_audit_events(module: str = "", keyword: str = "", page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _person_reference_display, _user_display_map,
    )
    if identity.get("role") != "admin": raise HTTPException(status_code=403, detail="仅管理员可以查看全所操作日志")
    conditions = []
    if module: conditions.append(BusinessRecord.module == module)
    if keyword.strip():
        like = f"%{keyword.strip()}%"
        conditions.append(or_(BusinessRecord.serial_no.ilike(like), BusinessRecord.title.ilike(like), WorkflowEvent.action.ilike(like), WorkflowEvent.operator.ilike(like), WorkflowEvent.comment.ilike(like)))
    base = select(WorkflowEvent, BusinessRecord).join(BusinessRecord, BusinessRecord.id == WorkflowEvent.record_id).where(*conditions)
    total = int(await db.scalar(select(func.count()).select_from(WorkflowEvent).join(BusinessRecord, BusinessRecord.id == WorkflowEvent.record_id).where(*conditions)) or 0)
    result = (await db.execute(base.order_by(WorkflowEvent.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    users_by_username = await _user_display_map({event.operator for event, _record in result}, db)
    return {
        "items": [{"id": event.id, "record_id": record.id, "module": record.module, "serial_no": record.serial_no, "title": record.title, "action": event.action, "from_status": event.from_status, "to_status": event.to_status, "operator": event.operator, "operator_display_name": _person_reference_display(event.operator, users_by_username)[0], "comment": event.comment, "created_at": event.created_at} for event, record in result],
        "total": total, "page": page, "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
    }


@router.get(f"{settings.api_prefix}/legacy-case-task-history/graph/{{legacy_task_guid}}")
async def list_legacy_case_task_history_graph(
    legacy_task_guid: str,
    entity: str = Query("nodes", pattern="^(nodes|participants|messages|notifications|read-receipts|files)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.legacy_sync import (
        _legacy_case_task_history_dict, _legacy_case_task_history_item_dict,
    )
    from app.core.permissions import (
        _ensure_legacy_case_task_history_visible,
    )
    history = await db.scalar(select(LegacyCaseTaskHistory).where(LegacyCaseTaskHistory.legacy_task_guid == legacy_task_guid))
    if history:
        await _ensure_legacy_case_task_history_visible(history, identity, db)
    elif identity.get("role") != "admin":
        raise HTTPException(status_code=404, detail="历史任务不存在或当前账号无权查看")
    model, scope_column, order_column = _LEGACY_CASE_TASK_HISTORY_ENTITIES[entity]
    if entity == "read-receipts":
        if not history:
            return {"legacy_task_guid": legacy_task_guid, "root": None, "entity": entity, "items": [], "total": 0, "page": page, "page_size": page_size, "pages": 0}
        condition = model.legacy_task_id == history.legacy_task_id
    else:
        condition = scope_column == legacy_task_guid
    total = int(await db.scalar(select(func.count()).select_from(model).where(condition)) or 0)
    records = list((await db.scalars(
        select(model).where(condition).order_by(order_column.asc(), model.id.asc()).offset((page - 1) * page_size).limit(page_size)
    )).all())
    return {
        "legacy_task_guid": legacy_task_guid, "root": _legacy_case_task_history_dict(history) if history else None,
        "entity": entity, "items": [_legacy_case_task_history_item_dict(item, entity) for item in records],
        "total": total, "page": page, "page_size": page_size, "pages": (total + page_size - 1) // page_size if total else 0,
        "read_only": True,
    }


@router.get(f"{settings.api_prefix}/legacy-case-task-history/{{legacy_task_guid}}")
async def get_legacy_case_task_history(
    legacy_task_guid: str,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.legacy_sync import (
        _legacy_case_task_history_dict,
    )
    from app.core.permissions import (
        _ensure_legacy_case_task_history_visible,
    )
    history = await db.scalar(select(LegacyCaseTaskHistory).where(LegacyCaseTaskHistory.legacy_task_guid == legacy_task_guid))
    if not history:
        raise HTTPException(status_code=404, detail="历史任务不存在")
    await _ensure_legacy_case_task_history_visible(history, identity, db)
    counts = {}
    for entity, (model, scope_column, _) in _LEGACY_CASE_TASK_HISTORY_ENTITIES.items():
        condition = model.legacy_task_id == history.legacy_task_id if entity == "read-receipts" else scope_column == history.legacy_task_guid
        counts[entity] = int(await db.scalar(select(func.count()).select_from(model).where(condition)) or 0)
    return {"item": _legacy_case_task_history_dict(history), "graph_counts": counts, "read_only": True}


@router.get(f"{settings.api_prefix}/legacy-history/attachments")
async def list_legacy_historical_attachments(
    source_system: str = "",
    legacy_entity_type: str = "",
    legacy_parent_no: str = "",
    legacy_parent_guid: str = "",
    recovery_status: str = "",
    include_inactive: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Read-only ledger for legacy blobs whose physical source is unavailable."""
    from app.core.legacy_sync import (
        _legacy_historical_attachment_dict,
    )
    from app.core.permissions import (
        _require_legacy_attachment_history_access,
    )
    await _require_legacy_attachment_history_access(identity, db)
    conditions = []
    if source_system.strip():
        conditions.append(LegacyHistoricalAttachment.source_system == source_system.strip())
    if legacy_entity_type.strip():
        conditions.append(LegacyHistoricalAttachment.legacy_entity_type == legacy_entity_type.strip())
    if legacy_parent_no.strip():
        conditions.append(LegacyHistoricalAttachment.legacy_parent_no == legacy_parent_no.strip())
    if legacy_parent_guid.strip():
        conditions.append(LegacyHistoricalAttachment.legacy_parent_guid == legacy_parent_guid.strip())
    if recovery_status.strip():
        conditions.append(LegacyHistoricalAttachment.source_recovery_status == recovery_status.strip())
    if not include_inactive:
        conditions.append(LegacyHistoricalAttachment.legacy_is_active.is_(True))
    total = int(await db.scalar(select(func.count()).select_from(LegacyHistoricalAttachment).where(*conditions)) or 0)
    rows = list((await db.scalars(
        select(LegacyHistoricalAttachment).where(*conditions).order_by(
            LegacyHistoricalAttachment.source_observed_at.desc(),
            LegacyHistoricalAttachment.id.desc(),
        ).offset((page - 1) * page_size).limit(page_size)
    )).all())
    return {
        "items": [_legacy_historical_attachment_dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "read_only": True,
        "physical_files_recoverable": False,
    }


@router.get(f"{settings.api_prefix}/legacy-history/attachments/{{attachment_id}}")
async def get_legacy_historical_attachment(
    attachment_id: int,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.legacy_sync import (
        _legacy_historical_attachment_dict,
    )
    from app.core.permissions import (
        _require_legacy_attachment_history_access,
    )
    await _require_legacy_attachment_history_access(identity, db)
    item = await db.get(LegacyHistoricalAttachment, attachment_id)
    if not item:
        raise HTTPException(status_code=404, detail="历史附件元数据不存在")
    return _legacy_historical_attachment_dict(item, include_payload=True)


@router.get(f"{settings.api_prefix}/agent/skills")
async def list_user_agent_skills(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _agent_skill_catalog_for_identity,
    )
    return {"items": await _agent_skill_catalog_for_identity(identity, db)}


@router.post(f"{settings.api_prefix}/agent/skills")
async def create_user_agent_skill(body: UserAgentSkillInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _save_user_agent_skills, _user_agent_skill_store,
    )
    _, skills = await _user_agent_skill_store(identity["username"], db)
    if len(skills) >= CUSTOM_SKILL_LIMIT:
        raise HTTPException(status_code=409, detail=f"每个账号最多保存 {CUSTOM_SKILL_LIMIT} 个自定义技能")
    try:
        record = normalize_custom_skill(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"技能字段格式不正确：{exc}") from exc
    skills.append(record)
    await _save_user_agent_skills(identity["username"], skills, identity, db)
    return custom_skill_public(record)


@router.post(f"{settings.api_prefix}/agent/skills/upload")
async def upload_user_agent_skill(file: UploadFile = File(...), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _save_user_agent_skills, _user_agent_skill_store,
    )
    _, skills = await _user_agent_skill_store(identity["username"], db)
    if len(skills) >= CUSTOM_SKILL_LIMIT:
        raise HTTPException(status_code=409, detail=f"每个账号最多保存 {CUSTOM_SKILL_LIMIT} 个自定义技能")
    content = await file.read(CUSTOM_SKILL_FILE_LIMIT + 1)
    try:
        record = parse_uploaded_skill(file.filename or "", content)
    except ValueError as exc:
        errors = {
            "file_too_large": "技能文件不能超过 2MB",
            "file_type": "仅支持 JSON、Markdown、Word（.docx）技能文件",
            "encoding": "技能文件必须使用 UTF-8 编码",
            "json": "JSON 技能文件格式不正确",
            "word": "Word 技能文件损坏或无法识别",
        }
        raise HTTPException(status_code=422, detail=errors.get(str(exc), f"技能字段格式不正确：{exc}")) from exc
    skills.append(record)
    await _save_user_agent_skills(identity["username"], skills, identity, db)
    return custom_skill_public(record)


@router.patch(f"{settings.api_prefix}/agent/skills/{{skill_id}}")
async def update_user_agent_skill(skill_id: str, body: UserAgentSkillUpdate, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _save_user_agent_skills, _user_agent_skill_store,
    )
    _, skills = await _user_agent_skill_store(identity["username"], db)
    index = next((index for index, item in enumerate(skills) if item.get("id") == skill_id), -1)
    if index < 0:
        raise HTTPException(status_code=404, detail="自定义技能不存在")
    merged = {**skills[index], **body.model_dump(exclude_unset=True)}
    try:
        skills[index] = normalize_custom_skill(merged, skill_id=skill_id, source=str(skills[index].get("source") or "user-custom"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"技能字段格式不正确：{exc}") from exc
    await _save_user_agent_skills(identity["username"], skills, identity, db)
    return custom_skill_public(skills[index])


@router.delete(f"{settings.api_prefix}/agent/skills/{{skill_id}}")
async def delete_user_agent_skill(skill_id: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _save_user_agent_skills, _user_agent_skill_store,
    )
    _, skills = await _user_agent_skill_store(identity["username"], db)
    retained = [item for item in skills if item.get("id") != skill_id]
    if len(retained) == len(skills):
        raise HTTPException(status_code=404, detail="自定义技能不存在")
    await _save_user_agent_skills(identity["username"], retained, identity, db)
    return {"deleted": True, "skill_id": skill_id}


@router.get(f"{settings.api_prefix}/templates")
async def list_templates(category: str = "", _: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _template_dict,
    )
    query = select(DocumentTemplate).order_by(DocumentTemplate.category, DocumentTemplate.name)
    if category:
        query = query.where(DocumentTemplate.category == category)
    items = (await db.scalars(query)).all()
    return {"items": [_template_dict(item) for item in items], "total": len(items)}


@router.get(f"{settings.api_prefix}/templates/{{template_id}}")
async def get_template(template_id: int, _: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _template_dict,
    )
    item = await db.get(DocumentTemplate, template_id)
    if not item:
        raise HTTPException(status_code=404, detail="模板不存在")
    return _template_dict(item)


@router.post(f"{settings.api_prefix}/templates", status_code=status.HTTP_201_CREATED)
async def create_template(body: TemplateInput, _: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _template_dict,
    )
    if await db.scalar(select(DocumentTemplate.id).where(DocumentTemplate.name == body.name)):
        raise HTTPException(status_code=409, detail="模板名称已存在")
    item = DocumentTemplate(**body.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _template_dict(item)


@router.patch(f"{settings.api_prefix}/templates/{{template_id}}")
async def update_template(template_id: int, body: TemplateUpdate, _: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _template_dict,
    )
    item = await db.get(DocumentTemplate, template_id)
    if not item:
        raise HTTPException(status_code=404, detail="模板不存在")
    changes = body.model_dump(exclude_unset=True)
    if not changes: return _template_dict(item)
    if "name" in changes:
        changes["name"] = str(changes["name"] or "").strip()
        if not changes["name"]: raise HTTPException(status_code=422, detail="模板名称不能为空")
        duplicate = await db.scalar(select(DocumentTemplate.id).where(DocumentTemplate.name == changes["name"], DocumentTemplate.id != template_id))
        if duplicate: raise HTTPException(status_code=409, detail="模板名称已存在")
    for key, value in changes.items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return _template_dict(item)


@router.delete(f"{settings.api_prefix}/templates/{{template_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(template_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    if identity["role"] != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可删除模板")
    item = await db.get(DocumentTemplate, template_id)
    if not item:
        raise HTTPException(status_code=404, detail="模板不存在")
    await db.delete(item)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/attachments")
async def list_attachments(
    record_id: int | None = None,
    finance_transaction_id: int | None = None,
    category: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.formatters import (
        _person_display_name, _user_display_map,
    )
    from app.core.permissions import (
        _ensure_attachment_record_visible, _filter_visible_attachments,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    record = None
    if record_id is not None:
        record = await _ensure_attachment_record_visible(record_id, identity, db)
        if record.module == JAR_FEE_MODULE:
            raise HTTPException(status_code=409, detail="JAR交案费文件必须使用交案费专用文件接口")
    conditions = []
    if record_id is not None:
        conditions.append(FileAttachment.record_id == record_id)
    if finance_transaction_id is not None:
        conditions.append(FileAttachment.finance_transaction_id == finance_transaction_id)
    if category:
        conditions.append(FileAttachment.category == category)
    items = (await db.scalars(select(FileAttachment).where(*conditions).order_by(FileAttachment.created_at.desc(), FileAttachment.id.desc()))).all()
    if not (record and record.module == "task"):
        items = await _filter_visible_attachments(items, identity, db)
    total = len(items)
    items = items[(page - 1) * page_size:(page - 1) * page_size + page_size]
    record_ids = {item.record_id for item in items if item.record_id}
    records = {record.id: record for record in (await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(record_ids)))).all()} if record_ids else {}
    uploader_usernames = {item.uploader for item in items if item.uploader}
    uploader_users = await _user_display_map(uploader_usernames, db)
    uploader_names = {username: _person_display_name(user.display_name, user.username)[0] for username, user in uploader_users.items()}
    return {
        "items": [_attachment_dict(item, records.get(item.record_id), uploader_names) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
        "required_archive_categories": sorted(ARCHIVE_REQUIRED_CATEGORIES),
    }


@router.get(f"{settings.api_prefix}/attachments/{{attachment_id}}")
async def get_attachment(attachment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _person_display_name, _user_display_map,
    )
    from app.core.permissions import (
        _ensure_attachment_record_visible,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    item = await db.get(FileAttachment, attachment_id)
    if not item:
        raise HTTPException(status_code=404, detail="附件不存在")
    record = None
    if item.record_id:
        record = await _ensure_attachment_record_visible(item.record_id, identity, db)
    elif identity.get("role") != "admin" and item.uploader != identity["username"]:
        raise HTTPException(status_code=404, detail="附件不存在或无权访问")
    uploader_users = await _user_display_map({item.uploader}, db)
    uploader_names = {username: _person_display_name(user.display_name, user.username)[0] for username, user in uploader_users.items()}
    return _attachment_dict(item, record, uploader_names)


@router.post(f"{settings.api_prefix}/attachments", status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    file: UploadFile = File(...), record_id: int | None = Form(None),
    finance_transaction_id: int | None = Form(None),
    source_case_id: int | None = Form(None),
    customer_guid: str | None = Form(None), is_license: bool | None = Form(None), document_date: date | None = Form(None),
    category: str = Form("普通附件"), remark: str = Form(""),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.cases import (
        _case_type_parameter_for_value,
    )
    from app.core.crm import (
        _customer_guid,
    )
    from app.core.documents import (
        _case_custom_document_folders, _sync_case_document_readiness, _sync_seal_document_names,
    )
    from app.core.investigation import (
        _sync_investigation_materials,
    )
    from app.core.permissions import (
        _ensure_attachment_record_visible, _ensure_record_module, _ensure_record_visible, _require_case_attachment_upload_access, _require_case_related_attachment_target,
        _require_contract_attachment_write_access, _require_hr_attachment_write_access, _require_record_owner_or_manager, _user_has_job_permission,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    from app.core.tasks import (
        _add_task_message_notifications, _is_task_participant,
    )
    record = None
    source_case = None
    transaction = None
    resolved_case_file_type = None
    customer_metadata_provided = customer_guid is not None or is_license is not None
    if source_case_id is not None and record_id is None:
        raise HTTPException(status_code=422, detail="案件关联文档必须指定客户或合同记录")
    if customer_metadata_provided and record_id is None:
        raise HTTPException(status_code=422, detail="客户专属附件字段只能用于客户记录")
    if finance_transaction_id is not None:
        transaction = await db.get(FinanceTransaction, finance_transaction_id)
        if not transaction:
            raise HTTPException(status_code=404, detail="关联财务流水不存在")
        if record_id is not None and record_id != transaction.finance_record_id:
            raise HTTPException(status_code=409, detail="附件关联费用与财务流水不一致")
        record_id = transaction.finance_record_id
        await _ensure_record_visible(record_id, identity, db)
        expected_category = FINANCE_DEFAULT_VOUCHER_CATEGORY[transaction.transaction_type]
        if category == "普通附件":
            category = expected_category
    if record_id is not None:
        record = await _ensure_attachment_record_visible(record_id, identity, db)
        if record.module == JAR_FEE_MODULE:
            raise HTTPException(status_code=409, detail="JAR交案费文件必须使用交案费专用文件接口")
        if source_case_id is not None:
            source_case = await _ensure_record_module(source_case_id, "case", identity, db)
            await _require_case_attachment_upload_access(source_case, identity, db)
            await _require_case_related_attachment_target(source_case, record)
            expected_related_category = "合同文档" if record.module == "contract" else "客户文档"
            if category != expected_related_category:
                raise HTTPException(status_code=422, detail=f"案件关联文档类型必须为{expected_related_category}")
        if customer_metadata_provided:
            if record.module != "customer":
                raise HTTPException(status_code=422, detail="客户专属附件字段只能用于客户记录")
            normalized_customer_guid = str(customer_guid or "").strip()
            if not normalized_customer_guid:
                raise HTTPException(status_code=422, detail="客户 Guid 不能为空")
            stored_customer_guid = (record.data or {}).get("customer_guid")
            if "customer_guid" in (record.data or {}) and not str(stored_customer_guid or "").strip():
                raise HTTPException(status_code=422, detail="客户记录 customer_guid 不能为空")
            if normalized_customer_guid != _customer_guid(record):
                raise HTTPException(status_code=409, detail="附件 customer_guid 与客户记录不一致")
        if record.module == "hr" and category != "员工头像":
            category = "员工档案"
        await _require_hr_attachment_write_access(record, category, identity, db)
        if record.module == "ipr_case":
            raise HTTPException(status_code=409, detail="知识产权案件文档请使用案件详情中的专用文档入口上传")
        if record.module == "contract" and not source_case:
            await _require_contract_attachment_write_access(record, identity, db)
        if record.module == "case":
            await _require_case_attachment_upload_access(record, identity, db)
            if category not in {
                "普通附件",
                AI_SPACE_CATEGORY,
                *CASE_FORMAL_DOCUMENT_FOLDERS,
                *_case_custom_document_folders(record),
            }:
                file_types = list((await db.scalars(select(SystemParameter).where(
                    SystemParameter.category == "case_file_type",
                    SystemParameter.name == category,
                    SystemParameter.is_active.is_(True),
                ).order_by(SystemParameter.id))).all())
                if not file_types:
                    raise HTTPException(status_code=422, detail="案件文件类型不存在或已停用")
                case_type = await _case_type_parameter_for_value(str((record.data or {}).get("case_type") or ""), db)
                if case_type:
                    configured_count = int(await db.scalar(select(func.count()).select_from(CaseTypeFileTypeRelation).where(
                        CaseTypeFileTypeRelation.case_type_id == case_type.id,
                    )) or 0)
                    allowed_ids = set((await db.scalars(select(CaseTypeFileTypeRelation.file_type_id).where(
                        CaseTypeFileTypeRelation.case_type_id == case_type.id,
                    ))).all()) if configured_count else set()
                    resolved_case_file_type = next((item for item in file_types if item.id in allowed_ids), None) if configured_count else file_types[0]
                    if configured_count and not resolved_case_file_type:
                        raise HTTPException(status_code=422, detail="该案件类型不允许使用所选文件类型")
                else:
                    resolved_case_file_type = file_types[0]
        if record.module == "task":
            if not _is_task_participant(record, identity):
                raise HTTPException(status_code=403, detail="只有任务参与人可以上传任务反馈附件")
            if category not in {"任务反馈附件", "任务资料附件"}:
                category = "任务资料附件"
        if record.module == "customer" and not source_case:
            await _require_record_owner_or_manager(record, identity, db)
        if record.module == "seal":
            await _require_record_owner_or_manager(record, identity, db)
            if record.status not in {"草稿", "待用印"}:
                raise HTTPException(status_code=409, detail="仅草稿或待用印用印申请可以上传用印文件")
            if record.status == "待用印":
                if identity.get("role") not in {"admin", "manager"}:
                    raise HTTPException(status_code=403, detail="只有用印管理员可以上传盖章文件")
                category = SEAL_STAMPED_FILE_CATEGORY
            else:
                category = SEAL_APPLICATION_FILE_CATEGORY
        if record.module == "official_outgoing":
            await _require_record_owner_or_manager(record, identity, db)
            if record.status not in {"草稿", "已拒绝", "已撤回"}:
                raise HTTPException(status_code=409, detail="仅草稿、已拒绝或已撤回正式发文可以上传或替换发文文件")
            if category != "正式发文附件":
                category = "正式发文附件"
        if record.module in INVESTIGATION_MATERIAL_CATEGORIES:
            await _require_record_owner_or_manager(record, identity, db)
            if category == "公证书扫描件":
                operator = await db.scalar(select(User).where(User.username == identity["username"]))
                if not operator or not await _user_has_job_permission(operator, "扫描上传", db):
                    raise HTTPException(status_code=403, detail="当前账号没有公证书扫描上传岗位权限")
    suffix = Path(file.filename or "").suffix.lower()
    # 旧普通案件文件库不按扩展名拒收：案件资料常含法院专用格式、加密包和
    # 其他业务文件。文件仍受大小、案件权限和受控下载约束；知识产权
    # 案件继续走自己的专用格式校验接口。
    allowed = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".png", ".jpg", ".jpeg", ".zip", ".rar"}
    is_employee_avatar = bool(record and record.module == "hr" and category == "员工头像")
    if not is_employee_avatar and (not record or record.module != "case") and suffix not in allowed:
        raise HTTPException(status_code=422, detail="不支持的文件格式")
    content = await file.read()
    if is_employee_avatar:
        if suffix not in {".png", ".jpg", ".jpeg", ".gif", ".webp"} or not str(file.content_type or "").lower().startswith("image/"):
            raise HTTPException(status_code=422, detail="头像仅支持 PNG、JPG、GIF 或 WebP 图片")
        if not content:
            raise HTTPException(status_code=422, detail="头像图片不能为空")
        image_signature_valid = (
            (suffix == ".png" and content.startswith(b"\x89PNG\r\n\x1a\n"))
            or (suffix in {".jpg", ".jpeg"} and content.startswith(b"\xff\xd8\xff"))
            or (suffix == ".gif" and content[:6] in {b"GIF87a", b"GIF89a"})
            or (suffix == ".webp" and content.startswith(b"RIFF") and content[8:12] == b"WEBP")
        )
        if not image_signature_valid:
            raise HTTPException(status_code=422, detail="头像文件内容不是有效图片")
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="头像图片不能超过 5MB")
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="单个文件不能超过 20MB")
    try:
        stored_name = f"{uuid4().hex}{suffix}"
        target = UPLOAD_ROOT / stored_name
        target.write_bytes(content)
        item = FileAttachment(record_id=record_id, finance_transaction_id=finance_transaction_id, category=category, file_type_code=resolved_case_file_type.code if resolved_case_file_type else "", original_name=Path(file.filename or stored_name).name, stored_name=stored_name, content_type=file.content_type or "application/octet-stream", size=len(content), path=str(target), uploader=identity["username"], remark=remark, is_license=bool(is_license), document_date=document_date)
        db.add(item)
        await db.flush()
        if record and record.module == "hr" and category == "员工头像":
            record.data = {**(record.data or {}), "avatar_attachment_id": item.id}
            linked_username = str((record.data or {}).get("username") or record.owner or "").strip().lower()
            linked_user = await db.scalar(select(User).where(User.username == linked_username)) if linked_username else None
            if linked_user:
                linked_user.profile = {**(linked_user.profile or {}), "avatar_attachment_id": item.id}
            db.add(WorkflowEvent(record_id=record.id, action="更新员工头像", from_status=record.status, to_status=record.status, operator=identity["username"], comment=item.original_name))
        if source_case:
            db.add(WorkflowEvent(record_id=source_case.id, action="上传案件关联文档", from_status=source_case.status, to_status=source_case.status, operator=identity["username"], comment=f"{category}：{item.original_name}"))
        elif record and record.module == "case":
            await _sync_case_document_readiness(record, db)
            db.add(WorkflowEvent(record_id=record.id, action="上传归档材料", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{category}：{item.original_name}"))
        elif record and record.module in INVESTIGATION_MATERIAL_CATEGORIES:
            material_categories = await _sync_investigation_materials(record, db)
            db.add(WorkflowEvent(record_id=record.id, action="上传调查材料", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{category}：{item.original_name}"))
            if record.module == "notary" and category == "公证书扫描件" and record.status in {"等待材料", "审核驳回"}:
                previous_notary_status = record.status; record.status = "待审核"; record.data = {**(record.data or {}), "review_due_date": str(date.today() + timedelta(days=30)), "scan_uploaded_at": datetime.now().isoformat(timespec="seconds"), "scan_uploaded_by": identity["username"]}
                clue = await db.get(BusinessRecord, int((record.data or {}).get("clue_id") or 0)); case_record = await db.get(BusinessRecord, int(((record.data or {}).get("case_id") or ((clue.data or {}).get("converted_case_id") if clue else 0)) or 0))
                if case_record and case_record.status == "等待公证书":
                    case_record.status = "等待审核公证书"; db.add(WorkflowEvent(record_id=case_record.id, action="公证书扫描件已上传", from_status="等待公证书", to_status="等待审核公证书", operator=identity["username"], comment=f"公证记录 {record.serial_no}"))
                db.add(WorkflowEvent(record_id=record.id, action="提交公证书审核", from_status=previous_notary_status, to_status="待审核", operator=identity["username"], comment=f"扫描件 {item.original_name}；审核期限 30 日"))
        elif record and record.module == "customer":
            db.add(WorkflowEvent(record_id=record.id, action="上传客户文档", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{category}：{item.original_name}"))
        elif record and record.module == "seal":
            if category == SEAL_APPLICATION_FILE_CATEGORY:
                await _sync_seal_document_names(record, db)
            action = "上传盖章文件" if category == SEAL_STAMPED_FILE_CATEGORY else "上传用印文件"
            db.add(WorkflowEvent(record_id=record.id, action=action, from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{category}：{item.original_name}"))
        elif record and record.module == "official_outgoing":
            db.add(WorkflowEvent(record_id=record.id, action="上传正式发文附件", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{category}：{item.original_name}"))
        elif record and record.module == "task":
            await _add_task_message_notifications(
                record,
                WorkflowEvent(
                    record_id=record.id, action=f"上传{category}",
                    from_status=record.status, to_status=record.status,
                    operator=identity["username"], comment=f"{category}：{item.original_name}",
                ),
                db,
                content=f"已上传{category}：{item.original_name}",
            )
        elif record and transaction:
            db.add(WorkflowEvent(record_id=record.id, action="上传财务凭证", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{transaction.transaction_type}流水 #{transaction.id}｜{category}：{item.original_name}"))
        await db.commit()
    except Exception:
        await db.rollback()
        target.unlink(missing_ok=True)
        raise
    await db.refresh(item)
    return _attachment_dict(item, record)


@router.get(f"{settings.api_prefix}/attachments/{{attachment_id}}/download")
async def download_attachment(attachment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_attachment_record_visible,
    )
    from app.core.storage import (
        _attachment_storage_path,
    )
    item = await db.get(FileAttachment, attachment_id)
    if not item:
        raise HTTPException(status_code=404, detail="附件不存在")
    if item.record_id:
        record = await _ensure_attachment_record_visible(item.record_id, identity, db)
        if record.module == JAR_FEE_MODULE:
            raise HTTPException(status_code=409, detail="JAR交案费文件必须使用交案费专用下载接口")
    elif identity.get("role") != "admin" and item.uploader != identity["username"]:
        raise HTTPException(status_code=404, detail="附件不存在或无权访问")
    path = _attachment_storage_path(item)
    if path is None:
        raise HTTPException(status_code=404, detail="附件文件不存在")
    return FileResponse(path, media_type=item.content_type, filename=item.original_name)


@router.get(f"{settings.api_prefix}/attachments/{{attachment_id}}/preview")
async def preview_attachment(attachment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Return safe, authenticated metadata/content for the in-app attachment preview."""
    from app.core.permissions import (
            _ensure_attachment_record_visible,
        )
    from app.core.storage import (
            _attachment_storage_path, _xlsx_preview_text,
        )
    item = await db.get(FileAttachment, attachment_id)
    if not item:
        raise HTTPException(status_code=404, detail="附件不存在")
    if item.record_id:
        await _ensure_attachment_record_visible(item.record_id, identity, db)
    elif identity.get("role") != "admin" and item.uploader != identity["username"]:
        raise HTTPException(status_code=404, detail="附件不存在或无权访问")

    path = _attachment_storage_path(item)
    if path is None:
        raise HTTPException(status_code=404, detail="附件文件不存在")

    suffix = Path(item.original_name).suffix.lower()
    content_type = str(item.content_type or "").lower()
    base = {"original_name": item.original_name, "content_type": content_type}
    if suffix == ".docx" and path.stat().st_size == 0:
        return {**base, "kind": "unsupported", "detail": "DOCX 文件为空，无法在线查看，请重新上传有效文件"}
    if content_type.startswith("image/") or suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}:
        return {**base, "kind": "image"}
    if content_type == "application/pdf" or suffix == ".pdf":
        return {**base, "kind": "pdf"}
    if suffix == ".docx":
        try:
            document = Document(path)
            parts = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
            for index, table in enumerate(document.tables, start=1):
                rows = [" | ".join(cell.text.strip() for cell in row.cells) for row in table.rows]
                if rows:
                    parts.append(f"表格 {index}：\n" + "\n".join(rows))
            preview_text = "\n\n".join(parts) or "（该 DOCX 文档没有可提取的文字内容）"
        except Exception as exc:
            raise HTTPException(status_code=422, detail="DOCX 文件无法在线读取") from exc
        if len(preview_text) > ATTACHMENT_TEXT_PREVIEW_MAX_CHARS:
            preview_text = f"{preview_text[:ATTACHMENT_TEXT_PREVIEW_MAX_CHARS]}\n\n[文档内容过长，在线预览仅显示前 200000 个字符]"
        return {**base, "kind": "docx", "text": preview_text}
    if suffix == ".xlsx":
        if path.stat().st_size == 0:
            return {**base, "kind": "unsupported", "detail": "XLSX 文件为空，无法在线查看，请重新上传有效文件"}
        try:
            preview_text = _xlsx_preview_text(path)
        except Exception as exc:
            raise HTTPException(status_code=422, detail="XLSX 文件无法在线读取") from exc
        return {**base, "kind": "xlsx", "text": preview_text}
    if suffix == ".xls":
        if path.stat().st_size == 0:
            return {**base, "kind": "unsupported", "detail": "XLS 文件为空，无法在线查看，请重新上传有效文件"}
        try:
            sheets, truncated = _xls_preview_sheets(path)
        except Exception as exc:
            raise HTTPException(status_code=422, detail="XLS 文件无法在线读取") from exc
        return {**base, "kind": "workbook", "sheets": sheets, "truncated": truncated}
    if suffix in {".txt", ".md", ".csv", ".json", ".xml", ".log", ".yaml", ".yml", ".html", ".htm"}:
        try:
            preview_text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise HTTPException(status_code=422, detail="文本文件无法在线读取") from exc
        if len(preview_text) > ATTACHMENT_TEXT_PREVIEW_MAX_CHARS:
            preview_text = f"{preview_text[:ATTACHMENT_TEXT_PREVIEW_MAX_CHARS]}\n\n[文件内容过长，在线预览仅显示前 200000 个字符]"
        return {**base, "kind": "text", "text": preview_text}
    return {**base, "kind": "unsupported", "detail": "当前文件格式暂不支持在线预览，请下载后查看"}


@router.get(f"{settings.api_prefix}/attachments/{{attachment_id}}/pdf-preview")
async def get_pdf_preview_metadata(
    attachment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """Return authenticated PDF page metadata; image bytes stay on the page endpoint."""
    from app.core.storage import (
        _authorized_pdf_preview_attachment, _open_preview_pdf, _pdf_preview_response_headers,
    )
    item, path = await _authorized_pdf_preview_attachment(attachment_id, identity, db)
    document = _open_preview_pdf(path)
    try:
        page_count = len(document)
    finally:
        document.close()
    page_url_template = (
        f"{settings.api_prefix}/attachments/{item.id}/pdf-preview/pages/{{page}}.png"
        "?width={width}"
    )
    return JSONResponse(
        content={
            "kind": "pdf_pages",
            "original_name": item.original_name,
            "content_type": "application/pdf",
            "page_count": page_count,
            "min_width": PDF_PREVIEW_MIN_WIDTH,
            "max_width": PDF_PREVIEW_MAX_WIDTH,
            "max_dimension": PDF_PREVIEW_MAX_DIMENSION,
            "max_pixels": PDF_PREVIEW_MAX_PIXELS,
            "page_url_template": page_url_template,
        },
        headers=_pdf_preview_response_headers(),
    )


@router.get(f"{settings.api_prefix}/attachments/{{attachment_id}}/pdf-preview/pages/{{page_number}}.png")
async def render_pdf_preview_page(
    attachment_id: int,
    page_number: int,
    width: int = Query(1440, ge=PDF_PREVIEW_MIN_WIDTH, le=PDF_PREVIEW_MAX_WIDTH),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Render one authorized PDF page as a bounded PNG for browser-safe previewing."""
    from app.core.storage import (
        _authorized_pdf_preview_attachment, _open_preview_pdf, _pdf_preview_response_headers,
    )
    _item, path = await _authorized_pdf_preview_attachment(attachment_id, identity, db)
    document = _open_preview_pdf(path)
    page = None
    try:
        page_count = len(document)
        if page_number < 1 or page_number > page_count:
            raise HTTPException(status_code=404, detail="PDF 页码不存在")
        page = document[page_number - 1]
        page_width, page_height = page.get_size()
        if page_width <= 0 or page_height <= 0:
            raise HTTPException(status_code=422, detail="PDF 页面尺寸无效")
        max_scale_for_pixels = (PDF_PREVIEW_MAX_PIXELS / (page_width * page_height)) ** 0.5
        max_scale_for_dimension = PDF_PREVIEW_MAX_DIMENSION / max(page_width, page_height)
        requested_scale = width / page_width
        scale = min(requested_scale, max_scale_for_pixels, max_scale_for_dimension)
        if scale <= 0:
            raise HTTPException(status_code=422, detail="PDF 页面无法渲染")
        bitmap = page.render(scale=scale)
        try:
            image = bitmap.to_pil().convert("RGB")
            output = io.BytesIO()
            image.save(output, format="PNG", optimize=True)
        finally:
            close_bitmap = getattr(bitmap, "close", None)
            if callable(close_bitmap):
                close_bitmap()
        payload = output.getvalue()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail="PDF 页面无法渲染") from exc
    finally:
        if page is not None:
            page.close()
        document.close()
    headers = _pdf_preview_response_headers()
    headers["Content-Disposition"] = f'inline; filename="attachment-{attachment_id}-page-{page_number}.png"'
    return Response(content=payload, media_type="image/png", headers=headers)


@router.delete(f"{settings.api_prefix}/attachments/{{attachment_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(attachment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _sync_case_document_readiness, _sync_seal_document_names,
    )
    from app.core.investigation import (
        _sync_investigation_materials,
    )
    from app.core.permissions import (
        _ensure_attachment_record_visible, _ensure_case_word_editor_not_locked, _ensure_record_module, _require_case_detail_write_access, _require_contract_attachment_write_access,
        _require_hr_attachment_write_access, _require_record_owner_or_manager,
    )
    from app.core.tasks import (
        _add_task_message_notifications,
    )
    item = await db.get(FileAttachment, attachment_id)
    if not item:
        raise HTTPException(status_code=404, detail="附件不存在")
    # 联系人照片的附件 ID 保存在客户 contacts JSON 中。若允许通用附件接口删除，
    # 会留下指向已删除文件的引用；必须从联系人维护入口替换或随联系人删除。
    if item.category == "客户联系人照片":
        raise HTTPException(status_code=409, detail="联系人照片请在客户联系人中维护")
    record = await db.get(BusinessRecord, item.record_id) if item.record_id else None
    if record and record.module == "hr" and item.category == "员工头像" and int((record.data or {}).get("avatar_attachment_id") or 0) == item.id:
        raise HTTPException(status_code=409, detail="当前员工头像不能通过附件接口删除，请上传新头像替换")
    if record and record.module == JAR_FEE_MODULE:
        raise HTTPException(status_code=409, detail="JAR fee files must use the dedicated finance endpoint")
    if record and record.module == "ipr_case":
        raise HTTPException(status_code=409, detail="知识产权案件文档请使用案件详情中的专用文档入口删除")
    may_manage_customer_document = False
    may_manage_case_document = False
    may_manage_task_attachment = False
    may_manage_seal_attachment = False
    may_manage_official_outgoing_attachment = False
    if record and record.module == "contract":
        await _require_contract_attachment_write_access(record, identity, db)
    if record and record.module == "task":
        record = await _ensure_attachment_record_visible(record.id, identity, db)
        if item.category not in {"任务反馈附件", "任务资料附件"}:
            raise HTTPException(status_code=422, detail="任务附件类型无效")
        if identity.get("role") != "admin" and item.uploader != identity["username"]:
            raise HTTPException(status_code=403, detail="任务参与人只能删除自己上传的任务附件")
        may_manage_task_attachment = True
    if record and record.module == "case":
        record = await _ensure_record_module(record.id, "case", identity, db)
        await _require_case_detail_write_access(record, identity, db)
        _ensure_case_word_editor_not_locked(item)
        may_manage_case_document = True
    if record and record.module == "customer":
        record = await _ensure_record_module(record.id, "customer", identity, db)
        await _require_record_owner_or_manager(record, identity, db)
        may_manage_customer_document = True
    if record and record.module == "seal":
        record = await _ensure_record_module(record.id, "seal", identity, db)
        await _require_record_owner_or_manager(record, identity, db)
        may_delete_application_file = record.status == "草稿" and item.category == SEAL_APPLICATION_FILE_CATEGORY
        may_delete_stamped_file = (
            record.status == "待用印"
            and item.category == SEAL_STAMPED_FILE_CATEGORY
            and identity.get("role") in {"admin", "manager"}
        )
        if not (may_delete_application_file or may_delete_stamped_file):
            raise HTTPException(status_code=409, detail="当前状态不允许删除该用印附件")
        if item.category not in {SEAL_APPLICATION_FILE_CATEGORY, SEAL_STAMPED_FILE_CATEGORY}:
            raise HTTPException(status_code=422, detail="用印申请附件类型无效")
        may_manage_seal_attachment = True
    if record and record.module == "official_outgoing":
        record = await _ensure_record_module(record.id, "official_outgoing", identity, db)
        await _require_record_owner_or_manager(record, identity, db)
        if record.status not in {"草稿", "已拒绝", "已撤回"}:
            raise HTTPException(status_code=409, detail="仅草稿、已拒绝或已撤回正式发文可以删除发文文件")
        if item.category != "正式发文附件":
            raise HTTPException(status_code=422, detail="已提交正式发文的盖章文件不能通过普通附件删除")
        may_manage_official_outgoing_attachment = True
    may_manage_hr_document = False
    if record and record.module == "hr":
        await _require_hr_attachment_write_access(record, item.category, identity, db)
        may_manage_hr_document = True
    if identity["role"] != "admin" and not may_manage_hr_document and not may_manage_customer_document and not may_manage_case_document and not may_manage_task_attachment and not may_manage_seal_attachment and not may_manage_official_outgoing_attachment:
        raise HTTPException(status_code=403, detail="仅管理员可删除附件；客户负责人可删除客户文档，部门负责人可删除员工档案")
    path = Path(item.path)
    await db.delete(item)
    await db.flush()
    if record and record.module == "case":
        await _sync_case_document_readiness(record, db)
        db.add(WorkflowEvent(record_id=record.id, action="删除归档材料", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{item.category}：{item.original_name}"))
    elif record and record.module in INVESTIGATION_MATERIAL_CATEGORIES:
        material_categories = await _sync_investigation_materials(record, db)
        db.add(WorkflowEvent(record_id=record.id, action="删除调查材料", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{item.category}：{item.original_name}"))
        if record.module == "notary" and item.category == "公证书扫描件" and "公证书扫描件" not in material_categories and record.status == "待审核":
            record.status = "等待材料"; record.data = {**(record.data or {}), "review_due_date": "", "scan_uploaded_at": ""}
            clue = await db.get(BusinessRecord, int((record.data or {}).get("clue_id") or 0)); case_record = await db.get(BusinessRecord, int(((record.data or {}).get("case_id") or ((clue.data or {}).get("converted_case_id") if clue else 0)) or 0))
            if case_record and case_record.status == "等待审核公证书":
                case_record.status = "等待公证书"; db.add(WorkflowEvent(record_id=case_record.id, action="撤回公证书审核", from_status="等待审核公证书", to_status="等待公证书", operator=identity["username"], comment="公证书扫描件已删除"))
            db.add(WorkflowEvent(record_id=record.id, action="撤回公证书审核", from_status="待审核", to_status="等待材料", operator=identity["username"], comment="公证书扫描件已删除"))
    elif record and record.module == "customer":
        db.add(WorkflowEvent(record_id=record.id, action="删除客户文档", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{item.category}：{item.original_name}"))
    elif record and record.module == "seal":
        if item.category == SEAL_APPLICATION_FILE_CATEGORY:
            await _sync_seal_document_names(record, db)
        action = "删除盖章文件" if item.category == SEAL_STAMPED_FILE_CATEGORY else "删除用印文件"
        db.add(WorkflowEvent(record_id=record.id, action=action, from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{item.category}：{item.original_name}"))
    elif record and record.module == "official_outgoing":
        db.add(WorkflowEvent(record_id=record.id, action="删除正式发文附件", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{item.category}：{item.original_name}"))
    elif record and record.module == "task":
        await _add_task_message_notifications(
            record,
            WorkflowEvent(record_id=record.id, action=f"删除{item.category}", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{item.category}：{item.original_name}"),
            db,
            content=f"已删除{item.category}：{item.original_name}",
        )
    elif record and item.finance_transaction_id:
        db.add(WorkflowEvent(record_id=record.id, action="删除财务凭证", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"流水 #{item.finance_transaction_id}｜{item.category}：{item.original_name}"))
    await db.commit()
    if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
        path.unlink()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(f"{settings.api_prefix}/testing/ipr-case-file-custom-import-batches/{{batch_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_ipr_case_file_custom_import_batch(batch_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Precise cleanup for test batches only; never exposed through the production workflow."""
    if identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可以清理测试导入批次")
    batch = await db.get(IprCaseFileCustomImportBatch, batch_id)
    if not batch or not batch.is_test:
        raise HTTPException(status_code=404, detail="测试自定义导入批次不存在")
    candidates = list((await db.scalars(select(IprCaseFileCustomImportCandidate).where(IprCaseFileCustomImportCandidate.batch_id == batch.id))).all())
    attachment_ids = [row.attachment_id for row in candidates if row.attachment_id]
    attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.id.in_(attachment_ids)))).all()) if attachment_ids else []
    for attachment in attachments:
        path = Path(attachment.path)
        if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
            path.unlink(missing_ok=True)
        await db.delete(attachment)
    source_path = Path(batch.source_path)
    if source_path.is_file() and UPLOAD_ROOT.resolve() in source_path.resolve().parents:
        source_path.unlink(missing_ok=True)
    await db.delete(batch); await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    f"{settings.api_prefix}/testing/ipr-official-import-batches/{{batch_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
async def delete_smoke_ipr_official_import_batch(
    batch_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """Remove one explicitly marked local smoke import batch and its generated records.

    Candidate imports intentionally create no formal record until confirmation.  The
    smoke suite does confirm candidates to prove that boundary, so it needs a
    narrowly scoped cleanup path that also removes the retained source CSV.  This
    endpoint is unavailable in production and accepts only a file name from the
    suite's fixed ``smoke-`` namespace; it cannot delete normal import batches.
    """
    if settings.app_env.strip().lower() in {"production", "prod"}:
        raise HTTPException(status_code=404, detail="接口不存在")
    if identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可以清理本地冒烟导入批次")
    batch = await db.get(IprOfficialImportBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="官文导入批次不存在")
    if not (batch.source_filename.lower().startswith("smoke-") or batch.source_filename.lower().startswith(".tmp-codex-")):
        raise HTTPException(status_code=403, detail="只能清理带明确 SMOKE 或 CODEX 文件名标识的本地导入批次")
    source_path = Path(batch.source_path)
    candidates = list((await db.scalars(
        select(IprOfficialImportCandidate).where(IprOfficialImportCandidate.batch_id == batch.id)
    )).all())
    record_ids = [candidate.official_record_id for candidate in candidates if candidate.official_record_id]
    if record_ids:
        attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id.in_(record_ids)))).all())
        attachment_paths = [Path(item.path) for item in attachments]
        for attachment in attachments:
            await db.delete(attachment)
        await db.execute(delete(FinanceTransaction).where(FinanceTransaction.finance_record_id.in_(record_ids)))
        await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id.in_(record_ids)))
        await db.execute(delete(BusinessRecord).where(BusinessRecord.id.in_(record_ids), BusinessRecord.module == "ipr_official_file"))
    else:
        attachment_paths = []
    await db.execute(delete(IprOfficialImportCandidate).where(IprOfficialImportCandidate.batch_id == batch.id))
    await db.delete(batch)
    await db.commit()
    for path in [source_path, *attachment_paths]:
        if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
            path.unlink()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    f"{settings.api_prefix}/testing/cases/{{case_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
async def delete_smoke_case(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Non-production cleanup for records created by the end-to-end smoke suite only."""
    from app.core.cases import (
        _delete_case_events_for_case_cleanup,
    )
    from app.core.tasks import (
        _delete_task_notifications,
    )
    if settings.app_env.strip().lower() in {"production", "prod"}:
        raise HTTPException(status_code=404, detail="接口不存在")
    if identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可清理本地冒烟案件")
    record = await db.get(BusinessRecord, case_id)
    if not record:
        raise HTTPException(status_code=404, detail="案件不存在")
    if record.module != "case":
        raise HTTPException(status_code=422, detail="该测试清理入口仅支持案件")
    if not (record.serial_no.startswith("SMOKE-") or record.title.startswith("SMOKE")):
        raise HTTPException(status_code=403, detail="只能清理本地冒烟测试案件")
    attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id == case_id))).all())
    attachment_paths = [Path(item.path) for item in attachments]
    for attachment in attachments:
        await db.delete(attachment)
    related_tasks = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "task", BusinessRecord.data["case_id"].as_integer() == case_id))).all())
    for task in related_tasks:
        await _delete_task_notifications(task.id, db)
        await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == task.id))
        await db.delete(task)
    await db.execute(delete(CaseAssistedFee).where(CaseAssistedFee.case_record_id == case_id))
    await db.execute(delete(HearingSchedule).where(HearingSchedule.case_record_id == case_id))
    await db.execute(delete(FinanceTransaction).where(FinanceTransaction.finance_record_id == case_id))
    await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == case_id))
    await _delete_case_events_for_case_cleanup(case_id, db)
    await db.delete(record)
    await db.commit()
    for path in attachment_paths:
        if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
            path.unlink()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    f"{settings.api_prefix}/testing/records/{{record_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
async def delete_smoke_record(record_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Non-production cleanup that cannot be used for ordinary or historical records."""
    from app.core.cases import (
        _delete_case_events_for_case_cleanup,
    )
    from app.core.tasks import (
        _delete_task_notifications,
    )
    if settings.app_env.strip().lower() in {"production", "prod"}:
        raise HTTPException(status_code=404, detail="接口不存在")
    if identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可清理本地冒烟记录")
    record = await db.get(BusinessRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    explicit_test_marker = (
        record.serial_no.startswith("SMOKE-")
        or "SMOKE" in record.title.upper()
        or "冒烟" in record.title
        # UI-driven cross-role acceptance records use this exact, deliberately
        # narrow marker.  It keeps cleanup available for terminal task flows
        # which have no business-page delete action, without admitting normal
        # records that merely contain a generic "验收" label.
        or "UI任务流转验收-" in record.title
        # Contact-edit page evidence uses this equally narrow, fixed UI marker.
        or "UI临时联系人验收-" in record.title
        # Employee-account lifecycle page evidence has no normal physical-delete
        # action: the account must first be offboarded through HR, then this
        # exact local-only marker permits precise acceptance cleanup.
        or "页面验收临时员工" in record.title
        or "SMOKE" in (record.customer or "").upper()
        or "冒烟" in (record.customer or "")
        or record.owner.lower().startswith("smoke_")
        or "smoke_" in json.dumps(record.data or {}, ensure_ascii=False).lower()
        or record.title.startswith("CODEX-")
    )
    if not explicit_test_marker:
        raise HTTPException(status_code=403, detail="只能清理带明确测试标识的本地冒烟记录")
    attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id == record_id))).all())
    attachment_paths = [Path(item.path) for item in attachments]
    for attachment in attachments:
        await db.delete(attachment)
    if record.module == "case":
        related_tasks = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "task", BusinessRecord.data["case_id"].as_integer() == record.id))).all())
        for task in related_tasks:
            await _delete_task_notifications(task.id, db)
            await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == task.id))
            await db.delete(task)
        await db.execute(delete(CaseAssistedFee).where(CaseAssistedFee.case_record_id == record.id))
        await _delete_case_events_for_case_cleanup(record.id, db)
        await db.execute(delete(FinanceTransaction).where(FinanceTransaction.finance_record_id == record_id))
    await db.execute(delete(ContractApprovalStep).where(ContractApprovalStep.contract_record_id == record_id))
    await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == record_id))
    if record.module == "task":
        await _delete_task_notifications(record_id, db)
    await db.delete(record)
    await db.commit()
    for path in attachment_paths:
        if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
            path.unlink()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
    db.add(item); await db.flush(); await _run_document_agent(item); await _sync_agent_document_to_case_ai_space(item, record, db); await db.commit(); await db.refresh(item)
    if record: db.add(WorkflowEvent(record_id=record.id, action="创建智能文档", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{item.job_no}｜{template.name}")); await db.commit()
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
    content = _docx_bytes(item.title, item.content)
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
    content = _docx_bytes(item.title, item.content); stored_name = f"{uuid4().hex}.docx"; path = UPLOAD_ROOT / stored_name; path.write_bytes(content)
    attachment = FileAttachment(record_id=record.id, category="智能生成文书", original_name=f"{item.title}.docx", stored_name=stored_name, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", size=len(content), path=str(path), uploader=identity["username"], remark=f"Dify任务 {item.job_no}")
    db.add(attachment); db.add(WorkflowEvent(record_id=record.id, action="智能文档回写", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{item.job_no}｜{item.title}")); await db.commit(); await db.refresh(attachment)
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


@router.delete(f"{settings.api_prefix}/testing/agent-documents/{{document_id}}", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
async def delete_smoke_agent_document(document_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Remove explicit smoke-only AI jobs when normal audit retention blocks deletion."""
    if settings.app_env.strip().lower() in {"production", "prod"}:
        raise HTTPException(status_code=404, detail="接口不存在")
    if identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可清理本地冒烟智能文档")
    item = await db.get(AgentDocument, document_id)
    if not item:
        raise HTTPException(status_code=404, detail="智能文档任务不存在")
    if "SMOKE" not in item.title.upper() and "冒烟" not in item.title:
        raise HTTPException(status_code=403, detail="只能清理带明确测试标识的本地智能文档")
    await db.delete(item)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(f"{settings.api_prefix}/agent/chat")
async def agent_chat(body: DifyRequest, identity: dict = Depends(current_identity)):
    if not settings.dify_base_url or not settings.dify_api_key:
        raise HTTPException(status_code=503, detail="Dify 尚未配置")
    payload = {"inputs": {"operator": identity["username"]}, "query": body.query, "response_mode": "blocking", "user": identity["username"]}
    if body.conversation_id:
        payload["conversation_id"] = body.conversation_id
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(f"{settings.dify_base_url.rstrip('/')}/v1/chat-messages", headers={"Authorization": f"Bearer {settings.dify_api_key}"}, json=payload)
    if response.is_error:
        raise HTTPException(status_code=502, detail="Dify 调用失败")
    return response.json()
