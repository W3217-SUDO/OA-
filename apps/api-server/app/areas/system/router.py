"""系统管理路由编排。"""
from app.core.constants import (
    DEFAULT_ROLE_PERMISSIONS,
    DEFAULT_SYSTEM_MENUS, FIELD_KEYS, MENU_KEYS, MENU_PARENT_BY_KEY, ROLE_DATA_SCOPES, SYSTEM_ACTION_BY_CODE,
    SYSTEM_ACTION_DEFINITIONS, SYSTEM_CACHE_META, SYSTEM_CACHE_REGISTRY, SYSTEM_MENU_ROUTE_KEYS, SYSTEM_PARAMETER_CACHE,
    SYSTEM_PARAMETER_CATEGORIES, _LEGACY_CASE_TASK_HISTORY_ENTITIES, logger,
)
from app.core.dependencies import (
    AsyncSession, BusinessRecord, CUSTOM_SKILL_FILE_LIMIT, CUSTOM_SKILL_LIMIT,
    Depends, DingTalkError,
    DocumentTemplate, File, FileAttachment, HTTPException, IprCaseWarning, JobRole, LegacyCaseTaskHistory, LegacyHistoricalAttachment, Notification, OAuth2PasswordRequestForm,
    Query, Response, RolePermission, SystemConfig, SystemMenu, SystemParameter, UploadFile, User,
    WorkflowEvent, current_identity, custom_skill_public, date,
    datetime, dingtalk_client, func, get_db,
    hash_password, httpx, json, normalize_custom_skill,
    or_, parse_uploaded_skill, password_needs_rehash, select, settings,
    status, timedelta, uuid4, verify_password,
)
from app.models_shared import (
    CacheBatchClearInput, CurrentUserUpdate,
    DifyRequest, DingTalkBindInput, DingTalkBindingInput, DingTalkLoginInput, RolePermissionUpdate,
    SecurityPolicyUpdate, SystemConfigUpdate, SystemMenuInput, SystemMenuUpdate, SystemMenuVisibilityBatchInput, SystemParameterInput,
    SystemParameterRelationReplaceInput, SystemParameterUpdate, SystemUserInput, SystemUserPasswordResetInput, SystemUserUpdate,
    TemplateInput, TemplateUpdate, UserAgentSkillInput, UserAgentSkillUpdate, UserMessageInput,
    UserPermissionOverrideUpdate,
)
from fastapi import APIRouter, Request

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
    role_ids = list(identity.get("_actual_role_ids") or [identity.get("_actual_role") or user.role])
    return {
        **_system_user_dict(user),
        **(await _user_permission_payload(user, db)),
        "role": "admin",
        "role_ids": ["admin", *role_ids] if "admin" not in role_ids else role_ids,
        "actual_role": role_ids[0],
        "actual_role_ids": role_ids,
        "action_keys": ["*"],
        "field_keys": list(FIELD_KEYS),
        "data_scope": "全所数据",
    }


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
    role_ids = list(identity.get("_actual_role_ids") or [identity.get("_actual_role") or user.role])
    return {
        **_system_user_dict(user),
        **(await _user_permission_payload(user, db)),
        "role": "admin",
        "role_ids": ["admin", *role_ids] if "admin" not in role_ids else role_ids,
        "actual_role": role_ids[0],
        "actual_role_ids": role_ids,
        "action_keys": ["*"],
        "field_keys": list(FIELD_KEYS),
        "data_scope": "全所数据",
    }


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
async def list_system_parameter_categories(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _permission_payload_for_identity, _system_parameter_menu_granted,
    )
    permission = await _permission_payload_for_identity(identity, db)
    menu_keys = set(permission.get("menu_keys") or [])
    items = [
        {"key": key, "name": name}
        for key, name in SYSTEM_PARAMETER_CATEGORIES.items()
        if _system_parameter_menu_granted(key, menu_keys)
    ]
    if not items:
        raise HTTPException(status_code=403, detail="当前账号没有系统参数菜单权限")
    return {"items": items}


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
async def list_system_parameter_options(category: str, include_inactive: bool = False, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Expose active, form-safe parameter choices to authenticated users."""
    from app.core.cases import (
        _case_file_type_tree,
    )
    from app.core.finance import (
        _fee_type_catalog, _fee_type_catalog_aliases,
    )
    if category not in {"notary_office", "fee_type", "case_file_type"}:
        raise HTTPException(status_code=422, detail="当前参数分类不提供业务选项")
    if category == "fee_type":
        items = (await db.scalars(select(SystemParameter).where(
            SystemParameter.category == category,
        ).order_by(SystemParameter.sort_order, SystemParameter.id))).all()
        alias_ids = _fee_type_catalog_aliases(list(items))
        items_by_id = {item.id: item for item in items}
        aliases = {
            str(alias_id): {"id": target_id, "code": items_by_id[alias_id].code}
            for alias_id, target_id in alias_ids.items() if alias_id in items_by_id
        }
        catalog = _fee_type_catalog(list(items), include_inactive=include_inactive)
        for row in catalog:
            row["alias_ids"] = [alias_id for alias_id, target_id in alias_ids.items() if target_id == row["id"]]
        return {"items": catalog, "aliases": aliases}
    items = (await db.scalars(select(SystemParameter).where(
        SystemParameter.category == category,
        SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.sort_order, SystemParameter.id))).all()
    if category == "case_file_type":
        return {"items": _case_file_type_tree(list(items))}
    return {"items": [{"id": item.id, "code": item.code, "name": item.name} for item in items]}


@router.get(f"{settings.api_prefix}/system/parameters")
async def list_system_parameters(category: str = "", keyword: str = "", page: int | None = Query(None, ge=1), page_size: int | None = Query(None, ge=1, le=200), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _permission_payload_for_identity, _system_parameter_menu_granted,
    )
    from app.core.system import (
        _system_parameter_dict,
    )
    if category and category not in SYSTEM_PARAMETER_CATEGORIES: raise HTTPException(status_code=422, detail="参数分类无效")
    permission = await _permission_payload_for_identity(identity, db)
    menu_keys = set(permission.get("menu_keys") or [])
    visible_categories = {
        key: name for key, name in SYSTEM_PARAMETER_CATEGORIES.items()
        if _system_parameter_menu_granted(key, menu_keys)
    }
    if category and category not in visible_categories:
        raise HTTPException(status_code=403, detail="当前账号没有访问该系统参数菜单的权限")
    if not category and not visible_categories:
        raise HTTPException(status_code=403, detail="当前账号没有系统参数菜单权限")
    requested_categories = {category: visible_categories[category]} if category else visible_categories
    cache_key = category or "__all__"
    if not keyword.strip() and cache_key in SYSTEM_PARAMETER_CACHE:
        result = SYSTEM_PARAMETER_CACHE[cache_key]
        if not category:
            result = [item for item in result if item.get("category") in requested_categories]
        if page is None and page_size is None:
            return {"items": result, "categories": requested_categories, "cached": True}
        current_page, current_size = page or 1, page_size or 15
        total = len(result)
        start = (current_page - 1) * current_size
        return {"items": result[start:start + current_size], "total": total, "page": current_page, "page_size": current_size, "categories": requested_categories, "cached": True}
    statement = select(SystemParameter)
    if category: statement = statement.where(SystemParameter.category == category)
    else: statement = statement.where(SystemParameter.category.in_(requested_categories))
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
        return {"items": result, "categories": requested_categories, "cached": False}
    current_page, current_size = page or 1, page_size or 15
    total = len(result)
    start = (current_page - 1) * current_size
    return {"items": result[start:start + current_size], "total": total, "page": current_page, "page_size": current_size, "categories": requested_categories, "cached": False}


@router.get(f"{settings.api_prefix}/system/parameter-relations/{{kind}}")
async def list_system_parameter_relations(kind: str, source_id: int | None = Query(None), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    # Relation editors are part of the source parameter page. The source menu
    # grant covers both loading and saving the relation.
    from app.core.permissions import (
        _require_system_parameter_menu,
    )
    from app.core.system import (
        _system_parameter_dict, _system_parameter_relation_config,
    )
    model, source_field, target_field, source_category, target_category = _system_parameter_relation_config(kind)
    await _require_system_parameter_menu(source_category, identity, db)
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
        _require_system_parameter_menu,
    )
    from app.core.system import (
        _system_audit, _system_parameter_relation_config,
    )
    model, source_field, target_field, source_category, target_category = _system_parameter_relation_config(kind)
    await _require_system_parameter_menu(source_category, identity, db, action="修改")
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
        _require_system_parameter_menu,
    )
    from app.core.system import (
        _clear_parameter_cache, _system_audit, _system_parameter_dict, _validate_parameter_parent, _validate_parameter_references,
    )
    if body.category not in SYSTEM_PARAMETER_CATEGORIES: raise HTTPException(status_code=422, detail="参数分类无效")
    await _require_system_parameter_menu(body.category, identity, db, action="新增")
    code, name = body.code.strip(), body.name.strip()
    if body.category == "payment_type":
        candidates = list((await db.scalars(select(SystemParameter).where(SystemParameter.category == body.category))).all())
        next_payee = str((body.extra or {}).get("payee") or "").strip().casefold()
        duplicate = next((item for item in candidates if item.code == code or (next_payee and str((item.extra or {}).get("payee") or "").strip().casefold() == next_payee)), None)
    else:
        duplicate = await db.scalar(select(SystemParameter).where(SystemParameter.category == body.category, or_(SystemParameter.code == code, SystemParameter.name == name)))
    if duplicate: raise HTTPException(status_code=409, detail="同一分类下参数代码或名称已存在")
    if body.category == "fee_type":
        legacy_match = await db.scalar(select(SystemParameter.id).where(
            SystemParameter.category == "fee_type",
            SystemParameter.extra["legacy_id"].as_string() == code,
        ))
        if legacy_match:
            raise HTTPException(status_code=409, detail="费用类型编号已存在")
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
        _require_system_parameter_menu,
    )
    from app.core.system import (
        _clear_parameter_cache, _system_audit, _system_parameter_dict, _validate_parameter_parent, _validate_parameter_references,
    )
    item = await db.get(SystemParameter, parameter_id)
    if not item: raise HTTPException(status_code=404, detail="系统参数不存在")
    await _require_system_parameter_menu(item.category, identity, db, action="修改")
    code = body.code.strip() if body.code is not None else item.code
    name = body.name.strip() if body.name is not None else item.name
    next_extra = body.extra if body.extra is not None else (item.extra or {})
    if item.category == "fee_type" and (item.extra or {}).get("legacy_id") is not None:
        if code != item.code:
            raise HTTPException(status_code=422, detail="旧费用类型编号不可修改")
        if int(item.extra["legacy_id"]) < 0 and body.is_active is True:
            raise HTTPException(status_code=422, detail="旧系统选择占位项不能启用为费用")
    if item.category == "payment_type":
        candidates = list((await db.scalars(select(SystemParameter).where(SystemParameter.category == item.category, SystemParameter.id != item.id))).all())
        next_payee = str(next_extra.get("payee") or "").strip().casefold()
        duplicate = next((candidate for candidate in candidates if candidate.code == code or (next_payee and str((candidate.extra or {}).get("payee") or "").strip().casefold() == next_payee)), None)
    elif item.category == "fee_type" and name == item.name:
        # Legacy fee names may repeat across groups. Updating other fields must
        # not reject an unchanged historical name.
        duplicate = await db.scalar(select(SystemParameter).where(SystemParameter.category == item.category, SystemParameter.id != item.id, SystemParameter.code == code))
    else:
        duplicate = await db.scalar(select(SystemParameter).where(SystemParameter.category == item.category, SystemParameter.id != item.id, or_(SystemParameter.code == code, SystemParameter.name == name)))
    if duplicate: raise HTTPException(status_code=409, detail="同一分类下参数代码、名称或收款单位已存在")
    await _validate_parameter_parent(item.category, code, next_extra, db, current_id=item.id)
    if item.category == "fee_type":
        normalized = await _normalized_fee_type_extra(code, next_extra, db)
        # Identity and provenance are server-owned; the maintenance form only
        # submits parent_code. Keep the legacy link on every edit.
        next_extra = {**(item.extra or {}), **normalized}
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
        _require_system_parameter_menu,
    )
    from app.core.system import (
        _clear_parameter_cache, _parameter_reference_examples, _system_audit,
    )
    item = await db.get(SystemParameter, parameter_id)
    if not item: raise HTTPException(status_code=404, detail="系统参数不存在")
    await _require_system_parameter_menu(item.category, identity, db, action="删除")
    references = await _parameter_reference_examples(item, db)
    if references:
        raise HTTPException(status_code=409, detail=f"参数“{item.name}”已被业务记录引用（{ '、'.join(references) }），不能删除；请停用以保留历史数据")
    category = item.category
    await _system_audit(db, identity, "删除系统参数", f"系统参数:{category}/{item.code}", {"id": item.id, "category": category, "code": item.code})
    await db.delete(item); await db.commit(); _clear_parameter_cache(category, identity["username"])
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/system/configs")
async def list_system_configs(keyword: str = "", page: int | None = Query(None, ge=1), page_size: int | None = Query(None, ge=1, le=200), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.conflict_review import CONFIG_KEY, auto_review_status
    from app.core.permissions import (
        _require_admin,
    )
    _require_admin(identity)
    items = (await db.scalars(select(SystemConfig).order_by(SystemConfig.id))).all()
    result = [{"key": item.key, "label": item.label, "group": item.group, "value": item.value or {}, "description": item.description, "updated_by": item.updated_by, "updated_at": item.updated_at, **(auto_review_status(item.value) if item.key == CONFIG_KEY else {})} for item in items]
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
    from app.core.conflict_review import CONFIG_KEY, auto_review_status, can_manage_auto_review
    from app.core.permissions import (
        _require_admin,
    )
    from app.core.system import (
        _system_audit, _validate_system_config,
    )
    _require_admin(identity)
    if config_key == CONFIG_KEY and not can_manage_auto_review(identity):
        raise HTTPException(status_code=403, detail="仅实际管理员或获系统配置授权的人员可以管理自动利益冲突审查")
    item = await db.scalar(select(SystemConfig).where(SystemConfig.key == config_key))
    if not item: raise HTTPException(status_code=404, detail="系统配置不存在")
    value = _validate_system_config(config_key, body.value)
    if config_key == "investigation_assignment" and value["supervisor_username"]:
        supervisor = await db.scalar(select(User).where(User.username == value["supervisor_username"], User.is_active.is_(True)))
        if not supervisor:
            raise HTTPException(status_code=422, detail="调查任务分配人必须是启用的系统人员")
    previous_value = dict(item.value or {})
    item.value = value; item.updated_by = identity["username"]
    audit_detail = {"key": item.key}
    if config_key == CONFIG_KEY:
        audit_detail.update({"previous_enabled": previous_value.get("enabled") is True, "enabled": value["enabled"]})
    await _system_audit(db, identity, "更新系统配置", f"系统配置:{item.key}", audit_detail)
    await db.commit(); await db.refresh(item)
    return {"key": item.key, "label": item.label, "group": item.group, "value": item.value, "description": item.description, "updated_by": item.updated_by, "updated_at": item.updated_at, **(auto_review_status(item.value) if item.key == CONFIG_KEY else {})}


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


@router.put(f"{settings.api_prefix}/system/menus/visibility")
async def update_system_menu_visibility(body: SystemMenuVisibilityBatchInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import _require_admin
    from app.core.system import _system_audit, _system_menu_dict
    _require_admin(identity)
    items = list((await db.scalars(select(SystemMenu).order_by(SystemMenu.sort_order, SystemMenu.id))).all())
    system_items = [item for item in items if item.key in SYSTEM_MENU_ROUTE_KEYS]
    by_key = {item.key: item for item in system_items}
    requested = {str(key).strip() for key in body.visible_keys if str(key).strip()}
    unknown = requested - set(by_key)
    if unknown:
        raise HTTPException(status_code=422, detail="包含不存在的菜单：" + "、".join(sorted(unknown)))
    protected = {"dashboard", "system", "system-management"}
    requested.update(protected & set(by_key))
    for key in list(requested):
        parent_key = by_key[key].parent_key
        while parent_key and parent_key in by_key:
            requested.add(parent_key)
            parent_key = by_key[parent_key].parent_key
    for item in system_items:
        is_visible = item.key in requested
        if item.is_visible != is_visible:
            item.is_visible = is_visible
            item.updated_by = identity["username"]
    await _system_audit(db, identity, "批量配置菜单显示", "系统菜单", {"visible_keys": sorted(requested)})
    refreshed = list((await db.scalars(
        select(SystemMenu).order_by(SystemMenu.sort_order, SystemMenu.id).execution_options(populate_existing=True)
    )).all())
    result = {"items": [_system_menu_dict(item) for item in refreshed], "visible_keys": sorted(requested)}
    await db.commit()
    return result


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


@router.get(f"{settings.api_prefix}/dashboard", name="dashboard")
async def dashboard_http(
    request: Request,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
    section: str | None = Query(default=None, pattern="^(metrics|todos|cases)$"),
):
    from app.core.dashboard_request import run_dashboard_read

    return await run_dashboard_read(request, dashboard(identity, db, section))


async def dashboard(
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
    section: str | None = Query(default=None, pattern="^(metrics|todos|cases)$"),
):
    from app.core.dashboard_metrics import dashboard_metrics
    from app.core.dashboard_todos import dashboard_todos
    from app.core.dashboard_cases import dashboard_cases

    loaders = {"metrics": dashboard_metrics, "todos": dashboard_todos, "cases": dashboard_cases}
    if section is not None:
        return await loaders[section](identity, db)
    # 保留全量接口供原有调用方使用，各分区请求独立持有数据库会话。
    result = {"source": "realtime"}
    for name in ("todos", "metrics", "cases"):
        result.update(await loaders[name](identity, db))
    return result


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
        _notification_dict,
    )
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
        if source_type not in {"task", "finance", "contract", "case", "feedback", "ipr_warning", "message"}: raise HTTPException(status_code=422, detail="消息来源无效")
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
    source_ids = {item.source_id for item in items if item.source_type in {"task", "case", "feedback"} and item.source_id}
    source_records = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module.in_(("task", "case", "bug_feedback")), BusinessRecord.id.in_(source_ids),
    ))).all() if source_ids else []
    records_by_id = {record.id: record for record in source_records}
    users_by_username = await _user_display_map(
        {value for item in items for value in (item.sender, item.recipient)}
        | {record.owner for record in source_records if record.module == "task"}, db,
    )
    return {"items": [_notification_dict(x, users_by_username, records_by_id) for x in items], "unread": unread, "total": total, "page": page, "page_size": page_size}


@router.get(f"{settings.api_prefix}/users/directory")
async def user_directory(
    purpose: str = "",
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.contracts import (
        _is_contract_approver,
    )
    from app.core.documents import _user_has_seal_action
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
    if directory_purpose in {"contract_approver", "seal_approver"}:
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
        *([] if directory_purpose in {"contract_approver", "seal_approver"} else [BusinessRecord.status.not_in({"离职", "停用"})]),
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
            "can_approve_seal": await _user_has_seal_action(item, "approve", db),
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
    source_record = await db.get(BusinessRecord, item.source_id) if item.source_type in {"task", "case"} and item.source_id else None
    users_by_username = await _user_display_map({item.sender, item.recipient, source_record.owner if source_record else ""}, db)
    return _notification_dict(item, users_by_username, {source_record.id: source_record} if source_record else {})


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


from app.areas.system.attachments import (
    router as attachments_router,
    list_attachments as list_attachments,
    get_attachment as get_attachment,
    upload_attachment as upload_attachment,
    download_attachment as download_attachment,
    preview_attachment as preview_attachment,
    create_office_preview_link as create_office_preview_link,
    stream_office_preview_attachment as stream_office_preview_attachment,
    get_pdf_preview_metadata as get_pdf_preview_metadata,
    render_pdf_preview_page as render_pdf_preview_page,
    delete_attachment as delete_attachment,
)
router.include_router(attachments_router)










from app.areas.system.agent_documents import (
    router as agent_documents_router,
    list_agent_documents as list_agent_documents,
    create_agent_document as create_agent_document,
    retry_agent_document as retry_agent_document,
    update_agent_document as update_agent_document,
    confirm_agent_document as confirm_agent_document,
    download_agent_document as download_agent_document,
    writeback_agent_document as writeback_agent_document,
    delete_agent_document as delete_agent_document,
)
router.include_router(agent_documents_router)




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
