"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.constants import (
    AGENT_ACTION_CAPABILITY, CASE_CREATABLE_TYPES, CIVIL_CASE_TYPES, CONTRACT_APPROVAL_ACTION_CODE, DEFAULT_MENU_LABEL_BY_KEY,
    DEFAULT_ROLE_PERMISSIONS, EXPENSE_SUBTYPE_FEE_TYPE, FIELD_KEYS, JAR_FEE_TRANSITIONS, JOB_ACTION_MENU_GRANTS,
    JOB_ROLE_ACTION_KEY_GRANTS, JOB_ROLE_LABEL_MENU_GRANTS, MENU_CHILDREN_BY_KEY, MENU_KEYS, ROLE_DATA_SCOPES,
    SYSTEM_ACTION_DEFINITIONS, SYSTEM_MENU_ROUTE_KEYS, SYSTEM_USER_ROLE_CODES,
)
from app.core.dependencies import (
    AgentDocument, AsyncSession, BusinessRecord, ContractApprovalStep, ContractObject,
    ContractPaymentLine, FileAttachment, GENERAL_SKILL, HTTPException, HrSubrecord,
    IprCaseFileCustomImportBatch, IprOfficialImportBatch, JobRole, LegacyCaseTaskHistory, RolePermission,
    SKILLS_BY_ID, SQLAlchemyError, SystemMenu, SystemParameter, User,
    WorkflowEvent, and_, custom_skill_agent, custom_skill_public, date,
    func, or_, public_skill_catalog, secrets, select,
    text, timedelta, user_role_ids,
)
from app.models_shared import (
    FinanceFeeInput,
)


def _expand_menu_permission_keys(menu_keys: list[str]) -> list[str]:
    """Return effective grants while preserving legacy parent-menu grants.

    Role settings created before leaf-level permissions stored only a top-level
    key such as ``case``.  A parent key therefore still grants every descendant;
    a role configured with only a leaf receives that leaf and its actual route
    only.  The result is ordered for stable API responses and tests.
    """
    granted = {key for key in menu_keys if key in SYSTEM_MENU_ROUTE_KEYS}
    pending = list(granted)
    while pending:
        current = pending.pop()
        for child_key in MENU_CHILDREN_BY_KEY.get(current, []):
            if child_key not in granted:
                granted.add(child_key)
                pending.append(child_key)
    return [key for key in MENU_KEYS if key in granted]


def _stored_menu_permission_keys(menu_keys: list[str]) -> list[str]:
    """Convert legacy parent grants to independently revocable leaf grants."""
    effective_keys = _expand_menu_permission_keys(menu_keys)
    result = [key for key in effective_keys if not MENU_CHILDREN_BY_KEY.get(key)]
    # User center is mandatory and also has child routes.  Keep its explicit
    # key so the existing base-permission validation remains meaningful.
    if "user-center" in effective_keys:
        result.append("user-center")
    return list(dict.fromkeys(result))


def _effective_job_role_action_keys(role: JobRole) -> list[str]:
    """Resolve a role's action nodes without treating menus as write grants."""
    result: list[str] = []
    for raw_value in role.permissions or []:
        value = str(raw_value or "").strip()
        candidates = (
            (value.removeprefix("action:"),)
            if value.startswith("action:")
            else JOB_ROLE_ACTION_KEY_GRANTS.get(value, ())
        )
        for candidate in candidates:
            if candidate and candidate not in result:
                result.append(candidate)
    return result


def _job_role_menu_permission_keys(permissions: list[str]) -> list[str]:
    """Resolve explicit menu keys and narrow legacy approval-action grants."""
    result: list[str] = []
    for value in permissions:
        key = str(value or "").strip()
        candidates = (key,) if key in SYSTEM_MENU_ROUTE_KEYS else JOB_ACTION_MENU_GRANTS.get(key, ())
        for candidate in candidates:
            if candidate not in result:
                result.append(candidate)
    return result


def _effective_job_role_menu_keys(role: JobRole) -> list[str]:
    """Resolve one HR role's checked tree nodes to real navigation grants."""
    result: list[str] = []
    for raw_value in role.permissions or []:
        value = str(raw_value or "").strip()
        candidates = (value,) if value in SYSTEM_MENU_ROUTE_KEYS else JOB_ROLE_LABEL_MENU_GRANTS.get(value, ())
        for candidate in candidates:
            if candidate not in result:
                result.append(candidate)
    return _expand_menu_permission_keys(result)


def _split_role_permission_keys(menu_keys: list[str] | None) -> tuple[list[str], list[str]]:
    menus: list[str] = []
    actions: list[str] = []
    for key in menu_keys or []:
        value = str(key)
        if value.startswith("@action:"):
            actions.append(value.removeprefix("@action:"))
        else:
            menus.append(value)
    return list(dict.fromkeys(menus)), list(dict.fromkeys(actions))


async def _system_permission_tree(db: AsyncSession, permission: RolePermission | None) -> list[dict]:
    from app.core.constants import (
        _system_action_definitions,
    )
    menu_keys, action_keys = _split_role_permission_keys(permission.menu_keys if permission else [])
    rows = list((await db.scalars(select(SystemMenu).order_by(SystemMenu.sort_order, SystemMenu.id))).all())
    by_key = {item.key: item for item in rows}
    action_definitions = _system_action_definitions(set(by_key))
    action_by_menu: dict[str, list[dict]] = {}
    for definition in action_definitions:
        action_by_menu.setdefault(definition["menu_key"], []).append(definition)
    children_by_parent: dict[str, list[SystemMenu]] = {}
    for item in rows:
        children_by_parent.setdefault(item.parent_key or "", []).append(item)

    def build(item: SystemMenu) -> dict:
        children = [build(child) for child in children_by_parent.get(item.key, [])]
        for definition in action_by_menu.get(item.key, []):
            children.append({
                "node_type": "A", "node_original_id": f"action:{definition['code']}",
                "node_id": f"action:{definition['code']}",
                "node_code": definition["code"], "text": definition["label"], "title": definition["label"],
                "state": {"checked": definition["code"] in action_keys}, "children": [],
            })
        label = str(item.label or "").strip()
        if not label or label in {"---", "—", "-"}:
            label = DEFAULT_MENU_LABEL_BY_KEY.get(item.key, "未命名菜单")
        return {
            "node_type": "M", "node_original_id": item.id, "node_id": str(item.id),
            "node_code": item.key, "text": label, "title": label,
            "state": {"checked": item.key in menu_keys}, "children": children,
        }

    # Include configured menu rows and synthetic action roots even when an isolated
    # database has not seeded every default menu.
    roots = [build(item) for item in children_by_parent.get("", [])]
    known = {node["node_code"] for node in roots}
    for definition in action_definitions:
        if definition["menu_key"] not in by_key and definition["menu_key"] not in known:
            roots.append({
                "node_type": "M", "node_original_id": f"menu:{definition['menu_key']}",
                "node_id": f"menu:{definition['menu_key']}",
                "node_code": definition["menu_key"], "text": definition["menu_key"], "title": definition["menu_key"],
                "state": {"checked": definition["menu_key"] in menu_keys},
                "children": [{
                    "node_type": "A", "node_original_id": f"action:{definition['code']}",
                    "node_id": f"action:{definition['code']}",
                    "node_code": definition["code"], "text": definition["label"], "title": definition["label"],
                    "state": {"checked": definition["code"] in action_keys}, "children": [],
                }],
            })
    return roots


def _normalize_system_user_role_ids(
    role_ids: list[str] | None,
    role: str | None,
    *,
    fallback_role: str = "user",
) -> list[str]:
    legacy_role = str(role or "").strip()
    if legacy_role and legacy_role not in SYSTEM_USER_ROLE_CODES:
        raise HTTPException(status_code=422, detail="角色值无效")
    requested = role_ids if role_ids is not None else ([legacy_role] if legacy_role else [fallback_role])
    normalized = [str(value or "").strip() for value in requested]
    if not normalized or any(not value for value in normalized):
        raise HTTPException(status_code=422, detail="至少需要保留一个角色")
    invalid = sorted(set(normalized) - SYSTEM_USER_ROLE_CODES)
    if invalid:
        raise HTTPException(status_code=422, detail=f"角色值无效：{', '.join(invalid)}")
    if len(set(normalized)) != len(normalized):
        raise HTTPException(status_code=422, detail="角色不能重复")
    if role_ids is not None and legacy_role and legacy_role not in normalized:
        raise HTTPException(status_code=422, detail="主角色必须包含在角色列表中")
    primary = "admin" if "admin" in normalized else (legacy_role or normalized[0])
    return [primary, *(value for value in normalized if value != primary)]


def _system_user_role_ids(user: User) -> list[str]:
    role_ids = [role for role in user_role_ids(user) if role in SYSTEM_USER_ROLE_CODES]
    if not role_ids:
        return ["user"]
    if "admin" in role_ids:
        return ["admin", *(role for role in role_ids if role != "admin")]
    return role_ids


def _identity_role_ids(identity: dict) -> list[str]:
    role_ids = [str(role).strip() for role in identity.get("role_ids", []) if str(role).strip() in SYSTEM_USER_ROLE_CODES]
    role = str(identity.get("role") or "user").strip()
    if role in SYSTEM_USER_ROLE_CODES and role not in role_ids:
        role_ids.insert(0, role)
    if "admin" in role_ids:
        return ["admin", *(value for value in role_ids if value != "admin")]
    return list(dict.fromkeys(role_ids)) or ["user"]


async def _permission_payload(role: str, db: AsyncSession) -> dict:
    permission = await db.scalar(select(RolePermission).where(RolePermission.role == role))
    config = DEFAULT_ROLE_PERMISSIONS.get(role, DEFAULT_ROLE_PERMISSIONS["user"])
    if role == "admin":
        return {
            "menu_keys": list(MENU_KEYS),
            "action_keys": ["*"],
            "data_scope": config["data_scope"],
            "field_keys": list(FIELD_KEYS),
        }
    menu_keys, action_keys = _split_role_permission_keys(permission.menu_keys if permission else config["menu_keys"])
    return {
        "menu_keys": _expand_menu_permission_keys(menu_keys),
        "action_keys": action_keys,
        "data_scope": permission.data_scope if permission else config["data_scope"],
        "field_keys": list(permission.field_keys if permission else config["field_keys"]),
    }


async def _permission_payload_for_roles(role_ids: list[str], db: AsyncSession) -> dict:
    if "admin" in role_ids:
        return await _permission_payload("admin", db)
    payloads = [await _permission_payload(role, db) for role in role_ids]
    menu_keys = list(dict.fromkeys(key for payload in payloads for key in payload["menu_keys"]))
    action_keys = list(dict.fromkeys(key for payload in payloads for key in payload["action_keys"]))
    field_keys = list(dict.fromkeys(key for payload in payloads for key in payload["field_keys"]))
    # A multi-role account may accumulate menus/actions, but its data range must
    # be deterministic and least-privileged.  Using the first stored role made
    # visibility depend on role_ids ordering (and let role reordering expose
    # data).  The scopes form the legacy range ladder below.
    scope_rank = {
        "本人及共享数据": 0,
        "授权审批数据": 1,
        "本部门数据": 2,
        "全所数据": 3,
    }
    data_scope = min(
        (payload["data_scope"] for payload in payloads),
        key=lambda value: scope_rank.get(value, -1),
    )
    return {
        "menu_keys": _expand_menu_permission_keys(menu_keys),
        "action_keys": action_keys,
        # Multiple roles may broaden operations, but never data visibility.
        "data_scope": data_scope,
        "field_keys": field_keys,
    }


async def _require_record_module_menu(module: str, identity: dict, db: AsyncSession, *, action: str) -> None:
    """Prevent generic write/export endpoints from bypassing menu authorization."""
    from app.core.system import (
        _record_module_menu_allowed,
    )
    permission = await _permission_payload_for_identity(identity, db)
    if not _record_module_menu_allowed(module, identity, permission):
        raise HTTPException(status_code=403, detail=f"当前角色没有{action}该业务模块的菜单权限")
    action_key = {
        ("customer", "新建"): "record.customer.create",
        ("customer", "编辑"): "record.customer.update",
    }.get((module, action))
    if action_key and "*" not in permission.get("action_keys", []) and action_key not in permission.get("action_keys", []):
        raise HTTPException(status_code=403, detail=f"当前角色没有{action}该业务模块的动作权限")


async def _require_contract_action(identity: dict, db: AsyncSession, action_key: str, action: str) -> None:
    """Allow visible contract workbenches while preserving workflow/data guards."""
    await _require_record_module_menu("contract", identity, db, action=action)


async def _require_hr_employee_action(identity: dict, db: AsyncSession, action_key: str, action: str) -> None:
    """Guard HR employee create/update without expanding other HR endpoints."""
    from app.core.system import (
        _menu_root,
    )
    if "admin" in _identity_role_ids(identity):
        return
    permission = await _permission_payload_for_identity(identity, db)
    if "hr" not in {_menu_root(key) for key in permission["menu_keys"]}:
        raise HTTPException(status_code=403, detail="当前角色没有人事中心菜单权限")
    if action_key not in permission.get("action_keys", []):
        raise HTTPException(status_code=403, detail=f"当前角色没有{action}员工档案的动作权限")


def _user_permission_overrides(user: User) -> dict:
    """Return validated per-user permission overrides stored on the account profile."""
    overrides = (user.profile or {}).get("permission_overrides")
    if not isinstance(overrides, dict):
        return {}
    return {key: overrides[key] for key in ("menu_keys", "field_keys", "data_scope") if key in overrides and overrides[key] not in (None, "")}


def _configured_user_job_role_name(user: User) -> str:
    """Resolve only an explicitly assigned personnel role.

    A display position is descriptive employee data, not an authorization
    grant. This prevents stale values such as ``系统管理员`` from escalating a
    normal account when its role assignment is missing or deleted.
    """
    profile = user.profile or {}
    permission_role_code = str(profile.get("permission_role_code") or "").strip()
    if permission_role_code:
        return permission_role_code
    permission_role = str(profile.get("permission_role") or "").strip()
    if permission_role:
        return permission_role
    staff_role = str(profile.get("staff_role") or "").strip()
    if staff_role:
        return staff_role
    # Older employee records used the position field for business-role
    # assignment. It remains a compatibility fallback only when it is not a
    # system-administrator label; that label must never escalate a user role.
    position = str(profile.get("position") or "").strip()
    return position


async def _job_role_for_name(name: str, db: AsyncSession) -> JobRole | None:
    value = str(name or "").strip()
    if not value:
        return None
    return await db.scalar(select(JobRole).where(
        JobRole.is_active.is_(True),
        or_(JobRole.code == value, JobRole.name == value),
    ))


def _denied_job_role_payload(payload: dict) -> dict:
    """Fail closed for an invalid explicit personnel-role binding."""
    return {**payload, "menu_keys": [], "action_keys": [], "field_keys": []}


def _apply_job_role_policy(payload: dict, job_role: JobRole) -> dict:
    """Overlay one explicitly bound personnel role onto a system-role fallback."""
    if job_role.code == "SYSTEM-ADMIN":
        # A profile must never turn a non-admin system account into an admin.
        return _denied_job_role_payload(payload)
    result = dict(payload)
    result["menu_keys"] = _effective_job_role_menu_keys(job_role)
    result["action_keys"] = _effective_job_role_action_keys(job_role)
    if job_role.field_keys_configured:
        result["field_keys"] = list(dict.fromkeys(job_role.field_keys or []))
    if job_role.data_scope in ROLE_DATA_SCOPES:
        result["data_scope"] = job_role.data_scope
    return result


async def _permission_payload_for_identity(identity: dict, db: AsyncSession) -> dict:
    """Resolve system-role grants plus the explicitly assigned HR role."""
    user = await db.scalar(select(User).where(User.username == identity.get("username", "")))
    if user:
        return await _user_permission_payload(user, db)
    role_ids = _identity_role_ids(identity)
    payload = await _permission_payload_for_roles(role_ids, db)
    if "admin" in role_ids:
        return payload
    explicit_role_name = str(identity.get("permission_role") or identity.get("staff_role") or "").strip()
    if explicit_role_name:
        if explicit_role_name in {"系统管理员", "管理员"}:
            return _denied_job_role_payload(payload)
        job_role = await _job_role_for_name(explicit_role_name, db)
        if not job_role:
            return _denied_job_role_payload(payload)
        payload = _apply_job_role_policy(payload, job_role)
    return payload


async def _user_permission_payload(user: User, db: AsyncSession) -> dict:
    """Resolve navigation and field grants from the assigned HR role.

    A concrete personnel role is the authoritative menu tree for that account;
    the legacy system applies the selected role's checked nodes at login and
    at every protected backend operation. Base system-role grants remain the
    fallback for accounts without an assigned personnel role.
    """
    from app.core.contracts import (
        _is_contract_approver,
    )
    role_ids = _system_user_role_ids(user)
    permission = await _permission_payload_for_roles(role_ids, db)
    explicit_role_name = _configured_user_job_role_name(user)
    job_role = await _job_role_for_name(explicit_role_name, db) if explicit_role_name else None
    if explicit_role_name and "admin" not in role_ids:
        if explicit_role_name in {"系统管理员", "管理员"}:
            return _denied_job_role_payload(permission)
        if not job_role:
            return _denied_job_role_payload(permission)
        permission = _apply_job_role_policy(permission, job_role)
    overrides = _user_permission_overrides(user)
    if overrides.get("menu_keys") is not None:
        permission["menu_keys"] = _expand_menu_permission_keys(overrides["menu_keys"])
    if overrides.get("field_keys") is not None:
        permission["field_keys"] = list(overrides["field_keys"])
    if overrides.get("data_scope") is not None:
        permission["data_scope"] = overrides["data_scope"]
    can_approve_contract = await _is_contract_approver(user, db)
    menu_keys = list(permission["menu_keys"])
    if can_approve_contract and "contract-audit" not in menu_keys:
        menu_keys.append("contract-audit")
    return {
        **permission,
        "menu_keys": _expand_menu_permission_keys(menu_keys),
        "action_keys": list(dict.fromkeys(permission.get("action_keys", []))),
        "can_approve_contract": can_approve_contract,
    }


async def _record_dict_for_identity(record: BusinessRecord, identity: dict, db: AsyncSession) -> dict:
    from app.core.contracts import (
        _contract_customer_record_dict,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    return await _contract_customer_record_dict(
        record,
        await _allowed_field_keys(identity, db),
        db,
        identity=identity,
    )


def _case_personal_scope_condition(username: str):
    exact_username_token = f'"{username}"'
    return or_(
        BusinessRecord.owner == username,
        BusinessRecord.data["case_team_usernames"].as_string().contains(exact_username_token),
        BusinessRecord.data["legacy_participants"].as_string().contains(
            f'"staff_name":"{username}"'
        ),
    )


async def _case_mine_scope_condition(identity: dict, db: AsyncSession):
    """Limit the Mine list to concrete case participation, even for admins."""
    username = str(identity["username"]).strip()
    exact_username_token = f'"{username}"'
    data = BusinessRecord.data
    conditions = [
        and_(
            BusinessRecord.owner == username,
            func.coalesce(data["source_person_username"].as_string(), "") == "",
            func.coalesce(data["source_person"].as_string(), "") == "",
            func.coalesce(data["business_owner"].as_string(), "") == "",
            func.coalesce(data["assistant_username"].as_string(), "") == "",
            func.coalesce(data["investigator"].as_string(), "") == "",
            func.coalesce(data["court_lawyer_username"].as_string(), "") == "",
            func.coalesce(data["case_team_usernames"].as_string(), "").in_({"", "[]"}),
            func.coalesce(data["handling_lawyer_usernames"].as_string(), "").in_({"", "[]"}),
            func.coalesce(data["legacy_participants"].as_string(), "").in_({"", "[]"}),
        ),
        data["case_team_usernames"].as_string().contains(exact_username_token),
        data["handling_lawyer_usernames"].as_string().contains(exact_username_token),
        data["legacy_participants"].as_string().contains(f'"staff_name":"{username}"'),
        func.lower(func.coalesce(data["source_person_username"].as_string(), "")) == username.lower(),
        func.lower(func.coalesce(data["source_person"].as_string(), "")) == username.lower(),
        func.lower(func.coalesce(data["business_owner"].as_string(), "")) == username.lower(),
        func.lower(func.coalesce(data["assistant_username"].as_string(), "")) == username.lower(),
        func.lower(func.coalesce(data["investigator"].as_string(), "")) == username.lower(),
        func.lower(func.coalesce(data["court_lawyer_username"].as_string(), "")) == username.lower(),
        select(FileAttachment.id).where(
            FileAttachment.record_id == BusinessRecord.id,
            func.lower(FileAttachment.uploader) == username.lower(),
        ).exists(),
    ]

    return or_(*conditions)


async def _record_scope_conditions(identity: dict, db: AsyncSession) -> list:
    if identity.get("role") == "admin":
        return []
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if not user:
        raise HTTPException(status_code=401, detail="当前用户不存在")
    scope = (await _user_permission_payload(user, db))["data_scope"]
    if scope == "全所数据":
        return []
    public_customer = and_(BusinessRecord.module == "customer", BusinessRecord.status == "公海")
    # JSON arrays are serialized with quoted string members.  Matching the
    # quoted username keeps ``ann`` from gaining access to rows assigned or
    # shared to ``joann`` while remaining portable across SQLite and
    # PostgreSQL.
    exact_username_token = f'"{user.username}"'
    managed_customer = and_(BusinessRecord.module == "customer", BusinessRecord.data["customer_managers"].as_string().contains(exact_username_token))
    shared_to_text = BusinessRecord.data["shared_to"].as_string()
    shared_with_text = BusinessRecord.data["shared_with"].as_string()
    shared_customer = and_(BusinessRecord.module == "customer", shared_with_text.contains(exact_username_token))
    exact_shared_to = shared_to_text.contains(exact_username_token)
    # A case team member must be able to find the assigned case even if their
    # ordinary role has only "own data" scope.  This is deliberately limited to
    # case records and stable username projections; it does not widen financial,
    # archive or team-management authority.
    personal_case = and_(BusinessRecord.module == "case", _case_personal_scope_condition(user.username))
    published_investigation = and_(
        BusinessRecord.module == "investigation",
        func.lower(BusinessRecord.data["publisher"].as_string()) == user.username.lower(),
    )
    initiated_task = and_(
        BusinessRecord.module == "task",
        func.lower(func.coalesce(BusinessRecord.data["initiator"].as_string(), "")) == user.username.lower(),
    )
    assigned_clue_review = and_(
        BusinessRecord.module == "clue",
        func.lower(func.coalesce(BusinessRecord.data["reviewer"].as_string(), "")) == user.username.lower(),
    )
    pending_contract_approval = and_(
        BusinessRecord.module == "contract",
        BusinessRecord.status == "审批中",
        select(ContractApprovalStep.id).where(
            ContractApprovalStep.contract_record_id == BusinessRecord.id,
            ContractApprovalStep.approver == user.username,
            ContractApprovalStep.status == "待审批",
        ).exists(),
    )
    if scope == "本部门数据":
        return [or_(BusinessRecord.department == user.department, public_customer, managed_customer, shared_customer, exact_shared_to, personal_case, published_investigation, initiated_task, assigned_clue_review, pending_contract_approval)]
    if scope == "授权审批数据":
        # Approval range is not a blanket view of every pending record.  A
        # contract becomes visible here only for its current pending approver;
        # other modules retain their own owner/share/participant projections
        # until they expose an equally concrete candidate relation.
        return [or_(BusinessRecord.owner == user.username, public_customer, managed_customer, shared_customer, exact_shared_to, personal_case, published_investigation, initiated_task, assigned_clue_review, pending_contract_approval)]
    return [or_(BusinessRecord.owner == user.username, public_customer, managed_customer, shared_customer, exact_shared_to, personal_case, published_investigation, initiated_task, assigned_clue_review, pending_contract_approval)]


async def _visible_legacy_ipr_case_ids(identity: dict, db: AsyncSession) -> set[int]:
    """Expose materialized IPR history only through current IPR menu and scope."""
    await _require_record_module_menu("ipr_case", identity, db, action="查看")
    if "admin" in _identity_role_ids(identity):
        return set()
    rows = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "ipr_case", *(await _record_scope_conditions(identity, db)),
    ))).all())
    legacy_ids: set[int] = set()
    for row in rows:
        raw_id = (row.data or {}).get("legacy_ipr_case_id", (row.data or {}).get("legacy_case_id"))
        try:
            if raw_id not in (None, ""):
                legacy_ids.add(int(raw_id))
        except (TypeError, ValueError):
            continue
    return legacy_ids


async def _visible_legacy_ls_case_ids(identity: dict, db: AsyncSession) -> set[int]:
    """Expose LS history only through an explicit current-case legacy identity."""

    await _require_record_module_menu("case", identity, db, action="查看")
    if "admin" in _identity_role_ids(identity):
        return set()
    rows = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case", *(await _record_scope_conditions(identity, db)),
    ))).all())
    visible: set[int] = set()
    for row in rows:
        value = (row.data or {}).get("legacy_ls_case_id")
        try:
            if value not in (None, ""):
                visible.add(int(value))
        except (TypeError, ValueError):
            continue
    # New carrier rows retain their own mapping column rather than requiring a
    # second write into BusinessRecord.data.  The relation remains exact by
    # current record primary key and stays fail-closed when the carrier is not
    # present in a database yet.
    record_ids = [int(row.id) for row in rows]
    if record_ids:
        bind_names = {f"record_id_{index}": record_id for index, record_id in enumerate(record_ids)}
        try:
            result = await db.execute(text(
                "SELECT legacy_case_id FROM legacy_ls_cases WHERE current_case_record_id IN ("
                + ",".join(f":{name}" for name in bind_names) + ")"
            ), bind_names)
            visible.update(int(value) for value in result.scalars().all())
        except SQLAlchemyError:
            # An unmigrated application database has no LS carrier table.  Do
            # not broaden visibility or make ordinary case pages unavailable.
            pass
    return visible


async def _visible_legacy_contract_history_parent_keys(identity: dict, db: AsyncSession) -> set[str]:
    """Restrict historical contract parents to current visible customer/contract/case scope."""
    if "admin" in _identity_role_ids(identity):
        return set()
    records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module.in_(("customer", "contract", "case")),
        *(await _record_scope_conditions(identity, db)),
    ))).all())
    aliases: set[tuple[str, str]] = set()
    for record in records:
        data = record.data or {}
        if record.module == "contract":
            value = str(record.serial_no or data.get("contract_no") or "").strip().upper()
            if value:
                aliases.add(("contract_no", value))
        elif record.module == "customer":
            value = str(record.serial_no or data.get("customer_no") or "").strip().upper()
            if value:
                aliases.add(("customer_no", value))
        else:
            contract_no = str(data.get("contract_no") or "").strip().upper()
            customer_no = str(data.get("customer_no") or "").strip().upper()
            if contract_no:
                aliases.add(("contract_no", contract_no))
            if customer_no:
                aliases.add(("customer_no", customer_no))
    if not aliases:
        return set()
    clauses = []
    parameters: dict[str, str] = {}
    for index, (kind, value) in enumerate(sorted(aliases)):
        clauses.append(f"(alias_kind=:legacy_alias_kind_{index} AND alias_value=:legacy_alias_value_{index})")
        parameters[f"legacy_alias_kind_{index}"] = kind
        parameters[f"legacy_alias_value_{index}"] = value
    try:
        result = await db.execute(text(
            "SELECT DISTINCT history_parent_key FROM legacy_contract_parent_aliases "
            "WHERE source_system='GDCRM' AND (" + " OR ".join(clauses) + ")"
        ), parameters)
    except SQLAlchemyError:
        return set()
    return {str(row[0]) for row in result.all()}


async def _ensure_record_visible(record_id: int, identity: dict, db: AsyncSession) -> BusinessRecord:
    conditions = [BusinessRecord.id == record_id, *(await _record_scope_conditions(identity, db))]
    record = await db.scalar(select(BusinessRecord).where(*conditions))
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在或无权访问")
    return record


async def _ensure_attachment_record_visible(record_id: int, identity: dict, db: AsyncSession) -> BusinessRecord:
    """Resolve attachment parent visibility without losing task-participant access.

    Task collaborators and initiators deliberately have a narrower record scope than
    ordinary owners, but they are still first-class participants for task feedback.
    Attachments must therefore use the task participation rule before the generic
    business-record scope rule.
    """
    from app.core.tasks import (
        _is_task_participant,
    )
    record = await db.get(BusinessRecord, record_id)
    if record and record.module == "task":
        if not _is_task_participant(record, identity):
            raise HTTPException(status_code=403, detail="只有任务参与人可以访问任务反馈附件")
        return record
    return await _ensure_record_visible(record_id, identity, db)


async def _require_hr_attachment_write_access(record: BusinessRecord, category: str, identity: dict, db: AsyncSession) -> None:
    if record.module != "hr":
        return
    if category not in {"员工档案", "员工头像"}:
        raise HTTPException(status_code=422, detail="员工附件类型必须为员工档案或员工头像")
    if category == "员工头像":
        await _require_hr_employee_action(identity, db, "hr.employee.update", "修改")
        await _require_hr_employee_target_access(record, identity, db)
        return
    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="仅系统管理员或部门负责人可以维护员工档案")
    await _ensure_record_module(record.id, "hr", identity, db)


async def _ensure_record_module(record_id: int, module: str, identity: dict, db: AsyncSession) -> BusinessRecord:
    record = await _ensure_record_visible(record_id, identity, db)
    if record.module != module:
        raise HTTPException(status_code=404, detail="业务记录不存在")
    return record


async def _require_record_owner_or_manager(record: BusinessRecord, identity: dict, db: AsyncSession) -> None:
    if record.module == "customer" and record.status == "公海" and identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="公海客户必须先领取后才能修改")
    if identity.get("role") == "admin" or record.owner == identity["username"] or (
        record.module == "customer" and identity["username"] in (record.data or {}).get("customer_managers", [])
    ):
        return
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if identity.get("role") == "manager" and user and record.department == user.department:
        return
    raise HTTPException(status_code=403, detail="只有负责人、部门负责人或系统管理员可以执行此操作")


async def _require_contract_investigation_create_access(
    contract: BusinessRecord, identity: dict, db: AsyncSession,
) -> None:
    """Recognize the contract's legacy business owner as its investigation publisher."""
    from app.core.contracts import (
        _contract_person_values,
    )
    if identity.get("role") == "admin":
        return
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if not user:
        raise HTTPException(status_code=401, detail="当前用户不存在")
    actor_tokens = {
        str(user.username or "").strip().casefold(),
        str(user.display_name or "").strip().casefold(),
    } - {""}
    data = contract.data or {}
    responsible_tokens = {
        str(value or "").strip().casefold()
        for key in (
            "source_person", "source_person_username", "business_owner",
            "business_owner_username", "source_owner",
        )
        for value in _contract_person_values(data.get(key))
        if str(value or "").strip()
    }
    responsible_tokens.add(str(contract.owner or "").strip().casefold())
    if actor_tokens & responsible_tokens:
        return
    if identity.get("role") == "manager" and contract.department == user.department:
        return
    raise HTTPException(status_code=403, detail="只有负责人、部门负责人或系统管理员可以执行此操作")


async def _require_contract_attachment_write_access(record: BusinessRecord, identity: dict, db: AsyncSession) -> None:
    """Protect generic attachment writes for contract records.

    Contract detail UI disables attachment writes while approval is in progress or
    after archiving; enforce the same rule server-side so the generic attachment
    endpoints cannot be used to bypass that guard.
    """
    await _require_record_owner_or_manager(record, identity, db)
    if record.status in {"审批中", "已归档"}:
        raise HTTPException(status_code=409, detail="审批中或已归档合同不能上传或删除附件")


def _require_task_owner_or_initiator(task: BusinessRecord, identity: dict, *, action: str) -> None:
    """Protect task writes from department-manager privilege escalation.

    Department scope grants read access to task lists, not authority to impersonate
    the current owner.  A manager who is neither owner nor initiator must not first
    replace the owner through a generic/batch endpoint and then perform lifecycle
    actions as that new owner.  System administrators deliberately retain the
    documented all-firm override.
    """
    username = identity["username"]
    data = task.data or {}
    if identity.get("role") == "admin" or task.owner == username or data.get("initiator") == username:
        return
    raise HTTPException(status_code=403, detail=f"只有任务负责人、发起人或系统管理员可以{action}")


async def _visible_record_ids(identity: dict, db: AsyncSession) -> set[int]:
    conditions = await _record_scope_conditions(identity, db)
    return set((await db.scalars(select(BusinessRecord.id).where(*conditions))).all())


async def _filter_visible_attachments(items: list[FileAttachment], identity: dict, db: AsyncSession) -> list[FileAttachment]:
    if identity.get("role") == "admin":
        return items
    record_ids = await _visible_record_ids(identity, db)
    return [item for item in items if (item.record_id and item.record_id in record_ids) or (not item.record_id and item.uploader == identity["username"])]


def _require_dingtalk_access(user: User) -> None:
    from app.core.formatters import (
        _dingtalk_allowed_display_names,
    )
    allowed_names = _dingtalk_allowed_display_names()
    if allowed_names and str(user.display_name or "").strip() not in allowed_names:
        raise HTTPException(status_code=403, detail="当前员工未开通钉钉登录，请联系管理员")


def _require_admin(identity: dict) -> None:
    if "admin" not in _identity_role_ids(identity):
        raise HTTPException(status_code=403, detail="仅系统管理员可以执行此操作")


async def _ensure_unique_dingtalk_user_id(profile: dict, db: AsyncSession, exclude_user_id: int | None = None, display_name: str = "") -> None:
    from app.core.formatters import (
        _dingtalk_allowed_display_names,
    )
    ding_user_id = str(profile.get("dingtalk_user_id") or "").strip()
    if not ding_user_id:
        return
    allowed_names = _dingtalk_allowed_display_names()
    if allowed_names and str(display_name or "").strip() not in allowed_names:
        raise HTTPException(status_code=403, detail="当前员工未开通钉钉登录，请联系管理员")
    users = (await db.scalars(select(User))).all()
    if any(user.id != exclude_user_id and str((user.profile or {}).get("dingtalk_user_id") or "").strip() == ding_user_id for user in users):
        raise HTTPException(status_code=409, detail="该钉钉账号已绑定其他系统用户")


async def _ensure_system_user_lifecycle_safe(user: User, db: AsyncSession, *, action: str) -> None:
    """Keep account administration from orphaning HR records or approval nodes."""
    pending_contract = await db.scalar(
        select(BusinessRecord.serial_no)
        .join(ContractApprovalStep, ContractApprovalStep.contract_record_id == BusinessRecord.id)
        .where(
            BusinessRecord.module == "contract",
            BusinessRecord.status == "审批中",
            ContractApprovalStep.status == "待审批",
            ContractApprovalStep.approver == user.username,
        )
        .order_by(BusinessRecord.id)
        .limit(1)
    )
    if pending_contract:
        raise HTTPException(status_code=409, detail=f"账号正在审批合同 {pending_contract}，请先完成、改派或撤回该合同审批后再{action}")
    employee_no = await db.scalar(
        select(BusinessRecord.serial_no)
        .where(
            BusinessRecord.module == "hr",
            or_(BusinessRecord.owner == user.username, BusinessRecord.data["username"].as_string() == user.username),
        )
        .order_by(BusinessRecord.id)
        .limit(1)
    )
    if employee_no:
        raise HTTPException(status_code=409, detail=f"账号已关联员工档案 {employee_no}，请通过人事办理状态同步账号，不能直接{action}")


def _role_permission_dict(item: RolePermission) -> dict:
    menu_keys, action_keys = _split_role_permission_keys(item.menu_keys)
    if item.role == "admin":
        config = DEFAULT_ROLE_PERMISSIONS["admin"]
        return {"role": item.role, "display_name": config["display_name"], "data_scope": config["data_scope"], "menu_keys": list(MENU_KEYS), "action_keys": [item["code"] for item in SYSTEM_ACTION_DEFINITIONS], "field_keys": list(FIELD_KEYS), "updated_at": item.updated_at}
    return {"role": item.role, "display_name": item.display_name, "data_scope": item.data_scope, "menu_keys": menu_keys, "action_keys": action_keys, "field_keys": item.field_keys, "updated_at": item.updated_at}


async def _scoped_export_records(module: str, ids: str, identity: dict, db: AsyncSession) -> list[BusinessRecord]:
    from app.core.system import (
        _export_ids,
    )
    conditions = [BusinessRecord.module == module, *(await _record_scope_conditions(identity, db))]
    selected_ids = _export_ids(ids)
    if selected_ids:
        conditions.append(BusinessRecord.id.in_(selected_ids))
    return list((await db.scalars(select(BusinessRecord).where(*conditions).order_by(BusinessRecord.created_at, BusinessRecord.id))).all())


async def _ensure_unique_customer_name(title: str, db: AsyncSession, *, exclude_id: int | None = None) -> None:
    from app.core.formatters import (
        _normalize_customer_name,
    )
    normalized = _normalize_customer_name(title)
    if not normalized:
        raise HTTPException(status_code=422, detail="客户名称不能为空")
    rows = (await db.execute(
        select(BusinessRecord.id, BusinessRecord.title).where(BusinessRecord.module == "customer")
    )).all()
    if any(item_id != exclude_id and _normalize_customer_name(existing_title) == normalized for item_id, existing_title in rows):
        raise HTTPException(status_code=409, detail="客户名称已存在，不能创建或改为同名客户")


async def _require_customer_conflict_permission(identity: dict, db: AsyncSession) -> None:
    if identity.get("role") == "admin":
        return
    permission = await _permission_payload_for_identity(identity, db)
    if "customer-conflict" not in set(permission.get("menu_keys", [])):
        raise HTTPException(status_code=403, detail="当前角色没有客户利益检索权限")


async def _user_has_job_permission(user: User, permission_name: str, db: AsyncSession) -> bool:
    """Resolve business action permission from the employee's configured job role."""
    if user.role == "admin":
        return True
    job_role_name = _configured_user_job_role_name(user)
    if not job_role_name:
        return False
    job_role = await db.scalar(select(JobRole).where(JobRole.name == job_role_name, JobRole.is_active.is_(True)))
    if not job_role or job_role.code == "SYSTEM-ADMIN":
        return False
    permissions = set(job_role.permissions or []) if job_role else set()
    # 旧的人事岗位“调查专员”已经使用“调查取证”描述其工作范围；
    # 调查线索提交和现场材料扫描是该范围内不可拆分的专用动作。
    implied_permissions = {
        "调查取证": {"线索提交", "扫描上传"},
    }
    return permission_name in permissions or permission_name in set().union(*(implied_permissions.get(item, set()) for item in permissions))


async def _user_can_write_investigation_clue(user: User, db: AsyncSession) -> bool:
    """Resolve clue writes from the account's effective menu or business action grants.

    The investigation workbench already hides the clue entry unless the account
    receives the relevant menu.  Requiring a separately configured job title
    after the account has reached that entry makes the same authorization model
    disagree with itself.  Keep the check narrow to the clue menu family, while
    retaining the legacy explicit business-action grant for configured roles.
    """
    if user.role == "admin":
        return True
    permission = await _user_permission_payload(user, db)
    menu_keys = set(permission.get("menu_keys") or [])
    has_clue_menu = bool(menu_keys.intersection({
        "investigation-task-sub-mine", "clue-my-draft",
    }))
    has_submit_action = await _user_has_job_permission(user, "线索提交", db)
    return has_clue_menu or has_submit_action


async def _require_investigation_clue_write_permission(user: User, db: AsyncSession) -> None:
    if not await _user_can_write_investigation_clue(user, db):
        raise HTTPException(status_code=403, detail="当前账号没有创建或提交调查线索权限")


async def _can_act_on_contract_approval_step(
    step: ContractApprovalStep,
    identity: dict,
    action_key: str,
    db: AsyncSession,
) -> bool:
    # System administrators retain the established explicit delegation escape
    # hatch.  Every non-admin must be the current selected candidate; merely
    # holding the same job action never substitutes for another approver.
    if identity.get("role") == "admin":
        return action_key == CONTRACT_APPROVAL_ACTION_CODE
    if step.approver != identity.get("username"):
        return False
    # Candidate maintenance is strict (active HR record + enabled flag +
    # action).  Existing legacy steps may predate the HR flag, so execution
    # preserves an already assigned current node when it still has the explicit
    # approval action.  It must never become a substitute for another node.
    permission = await _permission_payload_for_identity(identity, db)
    action_keys = set(permission.get("action_keys") or [])
    return "*" in action_keys or CONTRACT_APPROVAL_ACTION_CODE in action_keys


async def _ensure_contract_approval_access(contract_id: int, identity: dict, db: AsyncSession) -> BusinessRecord:
    contract = await db.get(BusinessRecord, contract_id)
    if not contract or contract.module != "contract":
        raise HTTPException(status_code=404, detail="合同不存在")
    assigned = await db.scalar(select(ContractApprovalStep.id).where(
        ContractApprovalStep.contract_record_id == contract_id,
        ContractApprovalStep.approver == identity["username"],
    ))
    if assigned or identity.get("role") == "admin":
        return contract
    return await _ensure_record_module(contract_id, "contract", identity, db)


def _require_internal_fee_payload(body: FinanceFeeInput) -> None:
    """Keep the internal-fee workbench from creating another fee category."""
    if body.fee_type != "内部费用" or body.expense_scope != "内部":
        raise HTTPException(status_code=422, detail="内部费用必须使用“内部”归属和“内部费用”类型")


async def _require_jar_fee_access(identity: dict, db: AsyncSession, *, write: bool = False) -> None:
    if identity.get("role") == "admin":
        return
    permission = await _permission_payload_for_identity(identity, db)
    menu_keys = set(permission.get("menu_keys") or [])
    if "finance-jar" not in menu_keys:
        raise HTTPException(status_code=403, detail="当前账号没有JAR交案费管理权限")
    if write and identity.get("role") not in {"manager", "user"}:
        raise HTTPException(status_code=403, detail="当前账号没有维护交案费权限")


async def _jar_fee_capabilities(item: BusinessRecord, identity: dict, db: AsyncSession) -> dict:
    try:
        await _require_jar_fee_access(identity, db, write=True)
        await _require_record_owner_or_manager(item, identity, db)
        can_manage = True
    except HTTPException:
        can_manage = False
    editable = can_manage and item.status == "待确认"
    return {
        "can_update": editable, "can_delete": editable, "can_manage_files": editable,
        "can_manage_status": can_manage and bool(JAR_FEE_TRANSITIONS.get(item.status, set())),
        "allowed_statuses": sorted(JAR_FEE_TRANSITIONS.get(item.status, set())) if can_manage else [],
    }


async def _ensure_contract_by_guid(contract_guid: str, identity: dict, db: AsyncSession) -> BusinessRecord:
    guid = str(contract_guid or "").strip()
    if not guid:
        raise HTTPException(status_code=404, detail="合同不存在")
    contract = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == "contract",
        BusinessRecord.data["contract_guid"].as_string() == guid,
        *(await _record_scope_conditions(identity, db)),
    ))
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    return contract


async def _ensure_contract_object_not_reserved(item: ContractObject, db: AsyncSession) -> None:
    """Do not let a pending/paid payment line be detached from its subject."""
    active_payment = await db.scalar(
        select(BusinessRecord.id)
        .join(ContractPaymentLine, ContractPaymentLine.payment_record_id == BusinessRecord.id)
        .where(
            ContractPaymentLine.contract_object_id == item.id,
            BusinessRecord.module == "contract_payment",
            BusinessRecord.status.in_(["待审批", "待付款", "已付款", "已核销"]),
        )
        .limit(1)
    )
    if active_payment:
        raise HTTPException(status_code=409, detail="该合同标的已有待审批、待付款或已付款申请，不能修改或删除")


async def _require_company_task_read_scope(identity: dict, db: AsyncSession, relation: str) -> None:
    """Authorize company task views from configured menu and data-range grants."""
    permission = await _permission_payload_for_identity(identity, db)
    required_menu = {
        "initiated": "task-company-created",
        "owned": "task-company-accepted",
        "collaborating": "task-company-collaborating",
    }.get(relation, "task-company")
    if required_menu not in set(permission.get("menu_keys") or []):
        raise HTTPException(status_code=403, detail="当前角色没有查看公司任务的菜单权限")
    if str(permission.get("data_scope") or "") != "全所数据":
        raise HTTPException(status_code=403, detail="当前角色没有查看公司任务的全所数据权限")


async def _ensure_legacy_case_task_history_visible(
    history: LegacyCaseTaskHistory,
    identity: dict,
    db: AsyncSession,
) -> None:
    """Do not infer a viewer for a legacy graph with no verified current case."""
    if identity.get("role") == "admin":
        return
    if history.case_record_id:
        await _ensure_record_module(history.case_record_id, "case", identity, db)
        return
    raise HTTPException(status_code=404, detail="历史任务尚未建立可验证的案件映射")


def _validate_finance_fee_scope_subtype(expense_scope: str | None, expense_subtype: str | None, fee_type: str) -> None:
    if expense_subtype and EXPENSE_SUBTYPE_FEE_TYPE.get(expense_subtype) != fee_type:
        raise HTTPException(status_code=422, detail="费用子类型与费用类型不一致")
    if expense_scope == "平台" and fee_type == "代理费" and expense_subtype != "平台代理费":
        raise HTTPException(status_code=422, detail="平台费用的代理费类型只能是平台代理费")
    if expense_scope != "平台" and expense_subtype == "平台代理费":
        raise HTTPException(status_code=422, detail="平台代理费只能归属于平台费用")


async def _refund_identity_department(identity: dict, db: AsyncSession) -> str:
    department = str(identity.get("department") or "").strip()
    if not department:
        user = await db.scalar(select(User).where(User.username == identity["username"]))
        department = str(user.department or "").strip() if user else ""
    if not department:
        raise HTTPException(status_code=401, detail="当前用户所属单位不存在")
    return department


async def _ensure_refund_company_record(
    refund_id: int,
    identity: dict,
    db: AsyncSession,
) -> BusinessRecord:
    item = await _ensure_record_module(refund_id, "refund", identity, db)
    if str(item.department or "").strip() != await _refund_identity_department(identity, db):
        raise HTTPException(status_code=404, detail="退款记录不存在")
    return item


async def _require_legacy_attachment_history_access(identity: dict, db: AsyncSession) -> None:
    """Historical source paths can contain sensitive legacy topology.

    There is no safe record-level scope for unattached/ambiguous rows, so this
    ledger is deliberately limited to the two audit roles until a complete
    identity and parent migration has been accepted.
    """
    if identity.get("role") not in {"admin", "auditor"}:
        raise HTTPException(status_code=403, detail="仅系统管理员或审计角色可以查看历史附件元数据")


def _settlement_application_scope(identity: dict) -> list:
    if identity.get("role") in {"admin", "auditor"}:
        return []
    if identity.get("role") == "manager":
        return [BusinessRecord.department == str(identity.get("department") or "")]
    return [BusinessRecord.owner == identity["username"]]


async def _case_event_access(case_id: int, identity: dict, db: AsyncSession, *, write: bool) -> tuple[BusinessRecord, str | None]:
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    return case_record, (await _require_case_event_write_access(case_record, identity, db) if write else None)


async def _ensure_case_fixed_tasks(case_record: BusinessRecord, db: AsyncSession, *, operator: str) -> list[BusinessRecord]:
    """Create the mandatory standard task set once for each case."""
    from app.core.tasks import (
        _add_task_message_notifications, _next_manual_task_serial,
    )
    existing = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "task",
        BusinessRecord.data["case_id"].as_integer() == case_record.id,
        BusinessRecord.data["task_type"].as_string() == "固定任务",
    ))).all())
    existing_keys = {str((item.data or {}).get("fixed_task_key") or "") for item in existing}
    specs = [
        ("filing-registration", "立案登记", 7, "完成法院立案信息登记并上传受理材料"),
        ("service-tracking", "送达跟踪", 14, "跟踪法院送达情况并记录送达结果"),
    ]
    created: list[BusinessRecord] = []
    for key, title, days, description in specs:
        if key in existing_keys:
            continue
        task = BusinessRecord(
            module="task", serial_no=await _next_manual_task_serial(db),
            title=f"{title}—{case_record.serial_no}", customer=case_record.customer, status="待接收",
            owner=case_record.owner, department=case_record.department, description=description,
            data={
                "deadline": str(date.today() + timedelta(days=days)), "priority": "普通", "source": "案件任务",
                "creation_mode": "自动", "task_type": "固定任务", "fixed_task_key": key, "initiator": operator,
                "collaborators": [], "case_no": case_record.serial_no, "case_id": case_record.id,
                "case_stage": "立案", "system_created_by": operator,
            },
        )
        db.add(task); await db.flush()
        await _add_task_message_notifications(task, WorkflowEvent(record_id=task.id, action="生成案件固定任务", to_status="待接收", operator=operator, comment=f"案件 {case_record.serial_no} 创建时自动生成"), db, content="案件固定任务已生成.")
        created.append(task)
    if created:
        case_record.data = {**(case_record.data or {}), "fixed_tasks_generated": True, "fixed_task_ids": [*list((case_record.data or {}).get("fixed_task_ids", [])), *[item.id for item in created]]}
    return [*existing, *created]


async def _ensure_case_assisted_fee_write(
    case_id: int, identity: dict, db: AsyncSession,
) -> BusinessRecord:
    """Keep assisted-fee lifecycle writes inside the ordinary case-detail gate."""
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_action(identity, db, "case.assisted_fee.manage")
    await _require_case_detail_write_access(case_record, identity, db)
    return case_record


def _require_case_creation_completed(case_record: BusinessRecord, *, require_approval: bool = True) -> None:
    """Require completed creation data and, when needed, a passed creation approval."""
    creation_step = str((case_record.data or {}).get("case_creation_step") or "")
    if creation_step and creation_step != "completed":
        raise HTTPException(status_code=409, detail="请先完成案件新建三步信息")
    approval_status = str((case_record.data or {}).get("case_creation_approval_status") or "")
    if require_approval and approval_status and approval_status not in {"已通过", "自动通过"}:
        raise HTTPException(status_code=409, detail="案件创建尚未通过案件主管审批")


async def _require_case_detail_write_access(case_record: BusinessRecord, identity: dict, db: AsyncSession) -> None:
    """Apply one non-bypassable gate to every mutable case-detail feature."""
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
        raise HTTPException(status_code=409, detail="案件已进入归档流程，不能新增、删除或修改案件详情资料")


async def _require_case_document_write_access(case_record: BusinessRecord, identity: dict, db: AsyncSession) -> None:
    """Authorize legacy document generation independently of the creation wizard."""
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档", "已合并"}:
        raise HTTPException(status_code=409, detail="归档中、已归档或已合并案件不能生成办理文书")


async def _require_case_action(identity: dict, db: AsyncSession, action_code: str) -> None:
    from app.core.cases import (
        _case_action_granted,
    )
    if not await _case_action_granted(identity, db, action_code):
        raise HTTPException(status_code=403, detail="当前岗位没有执行该案件操作的权限")


async def _require_case_note_write_access(
    case_record: BusinessRecord,
    identity: dict,
    db: AsyncSession,
    action_code: str = "case.reminder.manage",
) -> None:
    """Allow case-team notes independently from the case-creation wizard state.

    Historical and duplicated cases can carry legacy ``case_creation_step``
    values even though they are already active records.  Reminders and logs
    belong to the case itself, so their write gate must not depend on that
    wizard-only marker.
    """
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档", "已合并"}:
        raise HTTPException(status_code=409, detail="归档中、已归档或已合并案件不能新增或删除案件提醒和日志")


async def _require_case_event_write_access(case_record: BusinessRecord, identity: dict, db: AsyncSession) -> str:
    """Restrict independently maintained case events to the actual case team.

    Record visibility alone deliberately is not enough: an all-office reader can
    see an event but cannot create or change a deadline-bearing case milestone.
    """
    from app.core.cases import (
        _case_team_role,
    )
    await _require_case_note_write_access(case_record, identity, db, "case.event.manage")
    team_role = await _case_team_role(case_record, identity, db)
    if team_role == "none":
        raise HTTPException(status_code=403, detail="只有案件负责人、案件团队成员、部门负责人或系统管理员可以维护案件事件")
    return team_role


async def _require_case_task_write_access(case_record: BusinessRecord, identity: dict, db: AsyncSession) -> None:
    """Allow responsible case members to publish tasks for every active case."""
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档", "已合并"}:
        raise HTTPException(status_code=409, detail="归档中、已归档或已合并案件不能发布案件任务")


async def _require_case_attachment_upload_access(case_record: BusinessRecord, identity: dict, db: AsyncSession) -> None:
    """Allow case materials before creation approval without widening other writes."""
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
        raise HTTPException(status_code=409, detail="案件已进入归档流程，不能上传案件文档")


async def _require_case_related_attachment_target(
    case_record: BusinessRecord,
    target_record: BusinessRecord,
) -> None:
    """Keep case-workbench writes limited to the case's own customer or contract."""
    from app.core.system import (
        _positive_record_id,
    )
    case_data = case_record.data or {}
    if target_record.module == "contract":
        linked_id = _positive_record_id(case_data.get("contract_record_id") or case_data.get("contract_id"))
        linked_by_legacy_no = not linked_id and str(case_data.get("contract_no") or "").strip() == target_record.serial_no
        if linked_id == target_record.id or linked_by_legacy_no:
            return
    elif target_record.module == "customer":
        linked_id = _positive_record_id(case_data.get("customer_record_id") or case_data.get("customer_id"))
        linked_by_legacy_name = not linked_id and str(case_record.customer or "").strip() == target_record.title
        if linked_id == target_record.id or linked_by_legacy_name:
            return
    raise HTTPException(status_code=409, detail="所选文档目录不属于当前案件关联的客户或合同")


async def _require_case_progress_write_access(case_record: BusinessRecord, identity: dict, db: AsyncSession) -> None:
    """Only a responsible/manager user or assigned handling lawyer may advance a case."""
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
        raise HTTPException(status_code=409, detail="案件已进入归档流程，不能维护进展或开庭排期")
    if case_record.status == "已合并":
        raise HTTPException(status_code=409, detail="已合并案件不能维护进展或开庭排期")


async def _require_case_court_info_write_access(case_record: BusinessRecord, identity: dict, db: AsyncSession) -> None:
    """Authorize the independent court-info dialog without workflow side effects."""
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档", "已合并"}:
        raise HTTPException(status_code=409, detail="归档中、已归档或已合并案件不能修改法院信息")


async def _require_case_phase_change_access(case_record: BusinessRecord, identity: dict, db: AsyncSession) -> None:
    """Keep phase maintenance independent from creation approval while preserving write guards."""
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
        raise HTTPException(status_code=409, detail="案件已进入归档流程，不能修改案件阶段")
    if case_record.status == "已合并":
        raise HTTPException(status_code=409, detail="已合并案件不能修改案件阶段")


async def _case_detail_action_capabilities(case_record: BusinessRecord, identity: dict, db: AsyncSession) -> dict:
    from app.core.cases import (
        _case_action_granted, _case_team_role,
    )
    role = await _case_team_role(case_record, identity, db)
    case_type = str((case_record.data or {}).get("case_type") or "").strip()
    immutable = case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档", "已合并"}
    active = not immutable
    can_create_same_type = active and (case_type in CASE_CREATABLE_TYPES or case_type in CIVIL_CASE_TYPES)
    can_assign_team = active
    can_edit_hearing_lawyer = active
    can_edit_basic = active
    can_edit_court_info = active
    can_close_case = active
    can_archive_case = case_record.status not in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档", "已合并"}
    base = {
        "can_write": False, "can_manage_assisted_fees": False, "can_generate_document": False, "can_upload_attachment": False,
        "can_delete_attachment": False, "can_create_reminder": False,
        "can_delete_reminder": False, "can_create_log": False,
        "can_update_progress": False, "can_change_phase": False, "can_manage_hearing": False,
        "can_create_case_task": False, "can_duplicate_case": can_create_same_type,
        "can_delete_case": identity.get("role") in {"admin", "manager"} and case_record.status not in {"已归档", "已合并"},
        "can_merge_case": active,
        "can_assign_team": can_assign_team, "can_edit_hearing_lawyer": can_edit_hearing_lawyer,
        "can_edit_basic": can_edit_basic, "can_edit_court_info": can_edit_court_info,
        "can_close_case": can_close_case, "can_archive": can_archive_case,
        # Capability endpoints are reached only after the case has passed the
        # caller's data-scope check. Match the legacy rule: anyone who can see
        # the case may add its fees; invisible cases remain inaccessible.
        "can_create_finance": True, "team_role": role, "reason": "",
    }
    try:
        await _require_case_attachment_upload_access(case_record, identity, db)
        base["can_upload_attachment"] = True
    except HTTPException as exc:
        base["reason"] = str(exc.detail)
    try:
        await _require_case_phase_change_access(case_record, identity, db)
        base["can_change_phase"] = True
    except HTTPException:
        pass
    try:
        await _require_case_note_write_access(case_record, identity, db, "case.reminder.manage")
        base["can_create_reminder"] = True
        base["can_delete_reminder"] = True
    except HTTPException:
        pass
    try:
        await _require_case_note_write_access(case_record, identity, db, "case.log.create")
        base["can_create_log"] = True
    except HTTPException:
        pass
    try:
        await _require_case_task_write_access(case_record, identity, db)
        base["can_create_case_task"] = True
    except HTTPException:
        pass
    try:
        await _require_case_document_write_access(case_record, identity, db)
        base["can_generate_document"] = True
    except HTTPException:
        pass
    try:
        await _require_case_detail_write_access(case_record, identity, db)
    except HTTPException as exc:
        return {**base, "reason": str(exc.detail)}
    can_progress = active
    can_manage_assisted_fees = await _case_action_granted(identity, db, "case.assisted_fee.manage")
    return {
        **base,
        "can_write": True,
        "can_manage_assisted_fees": can_manage_assisted_fees,
        "can_delete_attachment": base["can_upload_attachment"],
        "can_update_progress": can_progress, "can_manage_hearing": can_progress,
        "can_delete_case": identity.get("role") in {"admin", "manager"} and case_record.status not in {"已归档", "已合并"},
    }


async def _agent_skill_catalog_for_identity(identity: dict, db: AsyncSession) -> list[dict]:
    from app.core.documents import (
        _user_agent_skill_store,
    )
    _, custom_records = await _user_agent_skill_store(identity["username"], db)
    return [*public_skill_catalog(), *[custom_skill_public(item) for item in custom_records]]


async def _agent_skill_for_identity(skill_id: str, identity: dict, db: AsyncSession):
    from app.core.documents import (
        _user_agent_skill_store,
    )
    normalized = str(skill_id or GENERAL_SKILL.id).strip()
    if normalized in SKILLS_BY_ID:
        skill = SKILLS_BY_ID[normalized]
        if not skill.available:
            raise HTTPException(status_code=409, detail=skill.unavailable_reason or "该技能暂不可用")
        return skill
    _, custom_records = await _user_agent_skill_store(identity["username"], db)
    record = next((item for item in custom_records if item.get("id") == normalized), None)
    if not record:
        raise HTTPException(status_code=404, detail="技能不存在或不属于当前账号")
    skill = custom_skill_agent(record)
    if not skill.available:
        raise HTTPException(status_code=409, detail="该技能已停用")
    return skill


def _require_case_agent_action_access(action_type: str, capabilities: dict) -> None:
    capability = AGENT_ACTION_CAPABILITY.get(action_type)
    if not capability:
        raise HTTPException(status_code=422, detail="该智能体操作类型不在系统白名单中")
    if not capabilities.get(capability):
        raise HTTPException(status_code=403, detail="智能体不能超出当前账号原有业务权限执行该操作")


async def _ensure_case_document_folder_name_available(
    name: str, record: BusinessRecord, db: AsyncSession, *, ignored_name: str = "",
) -> None:
    from app.core.documents import (
        _case_custom_document_folders,
    )
    custom_names = {value for value in _case_custom_document_folders(record) if value != ignored_name}
    if name in custom_names:
        raise HTTPException(status_code=409, detail="当前案件已存在同名目录")
    system_name = await db.scalar(select(SystemParameter.id).where(
        SystemParameter.category == "case_file_type",
        SystemParameter.name == name,
        SystemParameter.is_active.is_(True),
    ))
    if system_name:
        raise HTTPException(status_code=409, detail="该名称已是系统案件文档目录")


async def _require_case_word_editor_lock(item: FileAttachment, token: str, db: AsyncSession) -> None:
    from app.core.documents import (
        _word_editor_lock_payload, _word_editor_now,
    )
    expires_at = item.word_editor_lock_expires_at
    if not item.word_editor_lock_token or not secrets.compare_digest(item.word_editor_lock_token, token):
        raise HTTPException(status_code=409, detail={"message": "Word 编辑锁已被其他会话占用", **_word_editor_lock_payload(item)})
    now = _word_editor_now()
    if not expires_at or expires_at <= now:
        raise HTTPException(status_code=409, detail={"message": "Word 编辑锁已过期，请重新打开文件", **_word_editor_lock_payload(item)})


def _ensure_case_word_editor_not_locked(item: FileAttachment) -> None:
    from app.core.documents import (
        _word_editor_now,
    )
    expires_at = item.word_editor_lock_expires_at
    now = _word_editor_now()
    if item.word_editor_lock_token and expires_at and expires_at > now:
        raise HTTPException(status_code=409, detail=f"文件 {item.original_name} 正在由 {item.word_editor_locked_by or '其他用户'} 在线编辑，不能修改或删除")


async def _require_seal_base_action(identity: dict, db: AsyncSession, action: str) -> dict:
    from app.core.documents import (
        _seal_authorization_context,
    )
    context = await _seal_authorization_context(identity, db)
    if not context.get(action):
        raise HTTPException(status_code=403, detail="当前账号没有对应的用印岗位动作权限")
    return context


async def _seal_application_capabilities(
    record: BusinessRecord,
    identity: dict,
    db: AsyncSession,
    authorization_context: dict | None = None,
) -> dict[str, bool]:
    from app.core.documents import (
        _seal_authorization_context,
    )
    context = authorization_context or await _seal_authorization_context(identity, db)
    selected_approver = str((record.data or {}).get("approver") or "").strip()
    assigned_to_actor = not selected_approver or selected_approver == identity.get("username")
    can_audit = bool(context["approve"] and assigned_to_actor)
    return {
        "apply": bool(context["apply"] and record.owner == identity.get("username") and record.status == "草稿"),
        "approve": bool(can_audit and record.status == "待审批"),
        "reject": bool(context["reject"] and assigned_to_actor and record.status == "待审批"),
        "stamp": bool(context["stamp"] and record.status == "待用印"),
        "archive": bool(context["archive"] and record.status == "已用印"),
        "manage_assets": bool(context["manage_assets"]),
    }


def _job_role_dict(item: JobRole, users_by_username: dict[str, User] | None = None) -> dict:
    from app.core.formatters import (
        _person_reference_display,
    )
    users = users_by_username or {}
    created_name, created_missing = _person_reference_display(item.created_by, users)
    updated_name, updated_missing = _person_reference_display(item.updated_by, users)
    return {"id": item.id, "code": item.code, "name": item.name, "permissions": item.permissions or [], "field_keys": item.field_keys or [], "field_keys_configured": item.field_keys_configured, "data_scope": item.data_scope, "description": item.description, "sort_order": item.sort_order, "is_active": item.is_active, "created_by": item.created_by, "created_by_display_name": created_name, "created_by_display_name_missing": created_missing, "updated_by": item.updated_by, "updated_by_display_name": updated_name, "updated_by_display_name_missing": updated_missing, "created_at": item.created_at, "updated_at": item.updated_at}


def _normalize_job_role_field_keys(values: list[str]) -> list[str]:
    normalized = list(dict.fromkeys(str(value or "").strip() for value in values if str(value or "").strip()))
    invalid = sorted(set(normalized) - set(FIELD_KEYS))
    if invalid:
        raise HTTPException(status_code=422, detail=f"无效字段权限：{', '.join(invalid)}")
    return normalized


def _normalize_job_role_data_scope(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    if normalized not in ROLE_DATA_SCOPES:
        raise HTTPException(status_code=422, detail="无效数据范围")
    return normalized


def _hr_record_identity_tokens(record: BusinessRecord) -> set[str]:
    """Return stable identity keys used to detect migrated duplicate HR files."""
    from app.core.system import (
        _hr_record_linked_username,
    )
    data = record.data or {}
    legacy = data.get("legacy_hr_identity") if isinstance(data.get("legacy_hr_identity"), dict) else {}
    tokens: set[str] = set()
    username = _hr_record_linked_username(record)
    if username:
        tokens.add(f"username:{username}")
    system_user_id = data.get("system_user_id")
    if str(system_user_id or "").strip():
        tokens.add(f"system_user_id:{system_user_id}")
    legacy_staff_id = data.get("legacy_staff_id") or legacy.get("legacy_staff_id")
    if str(legacy_staff_id or "").strip():
        tokens.add(f"legacy_staff_id:{legacy_staff_id}")
    return tokens


async def _hr_duplicate_identity_group(employee: BusinessRecord, db: AsyncSession) -> list[BusinessRecord]:
    """Find the transitive HR-record group that resolves to the same identity."""
    records = list((await db.scalars(
        select(BusinessRecord).where(BusinessRecord.module == "hr").order_by(BusinessRecord.id)
    )).all())
    group: list[BusinessRecord] = [employee]
    group_ids = {employee.id}
    tokens = _hr_record_identity_tokens(employee)
    changed = True
    while changed:
        changed = False
        for record in records:
            if record.id in group_ids:
                continue
            record_tokens = _hr_record_identity_tokens(record)
            if tokens and tokens.intersection(record_tokens):
                group.append(record)
                group_ids.add(record.id)
                tokens.update(record_tokens)
                changed = True
    return group


async def _hr_duplicate_identity_canonical(group: list[BusinessRecord], db: AsyncSession) -> BusinessRecord:
    """Prefer the record already carrying employee-owned data, then the oldest file."""
    ranked: list[tuple[tuple[int, int, int], BusinessRecord]] = []
    for record in group:
        subrecords = int((await db.scalar(
            select(func.count()).select_from(HrSubrecord).where(HrSubrecord.employee_id == record.id)
        )) or 0)
        attachments = int((await db.scalar(
            select(func.count()).select_from(FileAttachment).where(FileAttachment.record_id == record.id)
        )) or 0)
        events = int((await db.scalar(
            select(func.count()).select_from(WorkflowEvent).where(WorkflowEvent.record_id == record.id)
        )) or 0)
        legacy = (record.data or {}).get("legacy_hr_identity")
        legacy_weight = len([value for value in legacy.values() if value is not None and value != ""]) if isinstance(legacy, dict) else 0
        ranked.append(((subrecords + attachments + events, legacy_weight, -int(record.id)), record))
    return max(ranked, key=lambda item: item[0])[1]


async def _require_unique_hr_display_name(display_name: str, db: AsyncSession, *, employee_id: int | None = None, linked_username: str = "") -> str:
    """Keep the personnel-facing Chinese name unique across HR files and login-only accounts."""
    from app.core.system import (
        _hr_record_linked_username,
    )
    normalized = display_name.strip()
    name_key = normalized.casefold()
    employee_statement = select(BusinessRecord).where(
        BusinessRecord.module == "hr",
        func.lower(func.trim(BusinessRecord.title)) == name_key,
    )
    if employee_id:
        employee_statement = employee_statement.where(BusinessRecord.id != employee_id)
    matching_employees = list((await db.scalars(employee_statement)).all())
    normalized_linked_username = linked_username.strip().lower()
    if any(
        not normalized_linked_username
        or _hr_record_linked_username(employee) != normalized_linked_username
        for employee in matching_employees
    ):
        raise HTTPException(status_code=409, detail="中文姓名已存在")
    user_statement = select(User.id).where(func.lower(func.trim(User.display_name)) == name_key)
    if linked_username:
        user_statement = user_statement.where(User.username != linked_username.strip().lower())
    if await db.scalar(user_statement.limit(1)):
        raise HTTPException(status_code=409, detail="中文姓名已存在")
    return normalized


async def _require_hr_employee_target_access(
    employee: BusinessRecord,
    identity: dict,
    db: AsyncSession,
) -> None:
    """Keep delegated HR editors inside their data scope and below administrators."""
    if "admin" in _identity_role_ids(identity):
        return
    actor = await db.scalar(select(User).where(User.username == identity["username"], User.is_active.is_(True)))
    if not actor:
        raise HTTPException(status_code=403, detail="当前账号不可修改员工档案")
    target_username = str((employee.data or {}).get("username") or employee.owner or "").strip()
    target_user = await db.scalar(select(User).where(User.username == target_username)) if target_username else None
    if target_user and "admin" in _system_user_role_ids(target_user):
        raise HTTPException(status_code=403, detail="非系统管理员不能修改管理员员工档案")
    if target_user:
        target_job_role = await _job_role_for_name(_configured_user_job_role_name(target_user), db)
        if target_job_role and target_job_role.code == "SYSTEM-ADMIN":
            raise HTTPException(status_code=403, detail="非系统管理员不能修改系统管理员岗位人员")
    permission = await _permission_payload_for_identity(identity, db)
    data_scope = str(permission.get("data_scope") or "")
    if data_scope == "全所数据":
        return
    if data_scope == "本部门数据" and employee.department == actor.department:
        return
    if target_username == actor.username or employee.owner == actor.username:
        return
    raise HTTPException(status_code=403, detail="当前角色的数据范围不包含该员工档案")


def _organization_permission_tree(menus: list[SystemMenu], actions: list[str], selected: set[str]) -> list[dict]:
    by_parent: dict[str, list[SystemMenu]] = {}
    for menu in menus:
        by_parent.setdefault(menu.parent_key or "", []).append(menu)

    def build(parent_key: str, trail: set[str]) -> list[dict]:
        nodes: list[dict] = []
        for menu in by_parent.get(parent_key, []):
            if menu.key in trail:
                continue
            children = build(menu.key, {*trail, menu.key})
            label = str(menu.label or "").strip()
            if not label or label in {"---", "—", "-"}:
                label = DEFAULT_MENU_LABEL_BY_KEY.get(menu.key, "未命名菜单")
            nodes.append({
                "key": f"menu:{menu.key}", "node_type": "M", "node_original_id": menu.id,
                "node_id": menu.id, "node_code": menu.key, "text": label, "title": label,
                "state": {"checked": menu.key in selected}, "children": children,
            })
        return nodes

    tree = build("", set())
    tree.append({
        "key": "actions", "node_type": "M", "node_original_id": 0,
        "node_id": 0, "node_code": "actions", "text": "业务动作", "title": "业务动作",
        "state": {"checked": False}, "children": [
            {
                "key": action, "node_type": "A", "node_original_id": action,
                "node_id": action, "node_code": action, "text": action, "title": action,
                "state": {"checked": action in selected}, "children": [],
            }
            for action in actions
        ],
    })
    return tree


async def _visible_ipr_cases(identity: dict, db: AsyncSession, extra_conditions: list | None = None) -> list[BusinessRecord]:
    conditions = [BusinessRecord.module == "ipr_case", *(await _record_scope_conditions(identity, db)), *(extra_conditions or [])]
    return list((await db.scalars(select(BusinessRecord).where(*conditions).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all())


def _require_ipr_reminder_type_manage(identity: dict) -> None:
    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="仅系统管理员或部门负责人可以维护案件提醒类型")


def _ipr_case_role_view_conditions(role_view: str, identity: dict) -> list:
    """Apply legacy IPR PageId role views using only the authenticated identity.

    The old CaseListController selected these filters from the menu PageId.  A
    client may select a view, but it never supplies the person being matched.
    Keeping this in the shared list-condition builder also prevents exports
    from bypassing an active identity view.
    """
    if not role_view:
        return []
    username = str(identity.get("username") or "").strip()
    display_name = str(identity.get("display_name") or "").strip()
    if not username:
        raise HTTPException(status_code=401, detail="当前用户不存在")

    def matches(keys: tuple[str, ...], values: tuple[str, ...]):
        return or_(*[
            BusinessRecord.data[key].as_string() == value
            for key in keys
            for value in values
        ])

    named_views = {
        "source_person": (
            ("case_origin_people_name", "case_source", "origin_people_name", "CaseOriginPeopleName"),
            "案源人",
        ),
        "procurator": (
            ("case_procurator_name", "procurator_name", "agent", "CaseProcuratorName", "ProcuratorName"),
            "代理人",
        ),
        "copywriter": (
            ("case_copywriter_name", "copywriter_name", "writer", "CaseCopywriterName", "CopywriterName"),
            "撰稿人",
        ),
        "business_owner": (
            ("business_owner_name", "business_owner", "BusinessOwnerName", "BusinessOwner"),
            "案件管理人",
        ),
    }
    if role_view in named_views:
        if not display_name:
            raise HTTPException(status_code=422, detail="当前账号未维护中文姓名，不能使用该案件视图")
        keys, label = named_views[role_view]
        return [matches(keys, (display_name,))]
    if role_view == "officer":
        # Legacy PageId 1001001004 matched both CaseOfficer and its display
        # name projection.  Current records also retain case_manager.
        return [matches(
            ("case_officer", "case_officer_name", "case_manager", "CaseOfficer", "CaseOfficerName"),
            tuple(value for value in (username, display_name) if value),
        )]
    raise HTTPException(status_code=422, detail="知识产权案件身份视图无效")


async def _ensure_ipr_litigation_case_write(case_id: int, identity: dict, db: AsyncSession) -> BusinessRecord:
    """Guard lawsuit-specific IPR state without weakening the existing IPR scope rules."""
    record = await _ensure_active_ipr_case_write(case_id, identity, db)
    if (record.data or {}).get("case_category", "non_litigation") != "litigation":
        raise HTTPException(status_code=422, detail="当前知识产权案件不是诉讼案件")
    return record


async def _ensure_active_ipr_case_write(case_id: int, identity: dict, db: AsyncSession) -> BusinessRecord:
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    await _require_record_owner_or_manager(record, identity, db)
    if record.status not in {"草稿", "已驳回", "在办"}:
        raise HTTPException(status_code=409, detail="当前案件状态不能维护客户或案件联系人")
    return record


async def _ensure_ipr_case_assisted_fee_write(
    case_id: int, identity: dict, db: AsyncSession,
) -> BusinessRecord:
    """Guard dedicated assistance workflow mutations from generic fee bypasses."""
    case_record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    await _require_record_owner_or_manager(case_record, identity, db)
    if case_record.status != "在办":
        raise HTTPException(status_code=409, detail="只有在办知识产权案件可以维护协助费")
    return case_record


async def _ipr_case_assisted_fee_capabilities(
    case_record: BusinessRecord, identity: dict, db: AsyncSession,
) -> dict[str, bool]:
    """Expose the same ownership rule enforced by assistance workflow writes."""
    if case_record.status != "在办":
        return {"can_manage": False}
    if identity.get("role") == "admin" or case_record.owner == identity["username"]:
        return {"can_manage": True}
    if identity.get("role") != "manager":
        return {"can_manage": False}
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    return {"can_manage": bool(user and user.department == case_record.department)}


async def _ensure_ipr_case_fee_write(case_id: int, identity: dict, db: AsyncSession) -> BusinessRecord:
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    await _require_record_owner_or_manager(record, identity, db)
    if record.status != "在办":
        raise HTTPException(status_code=409, detail="只有在办知识产权案件可以维护案件费用")
    return record


async def _ensure_active_ipr_case_write(case_id: int, identity: dict, db: AsyncSession) -> BusinessRecord:
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    await _require_record_owner_or_manager(record, identity, db)
    if record.status != "在办":
        raise HTTPException(status_code=409, detail="只有在办知识产权案件可以维护提醒")
    return record


async def _ipr_annual_fee_capabilities(case_record: BusinessRecord, identity: dict, db: AsyncSession) -> dict:
    if case_record.status != "在办":
        return {"can_manage": False}
    try:
        await _require_record_owner_or_manager(case_record, identity, db)
    except HTTPException:
        return {"can_manage": False}
    return {"can_manage": True}


async def _ensure_ipr_case_file_write(case_id: int, identity: dict, db: AsyncSession) -> BusinessRecord:
    """Dedicated guard for IPR case files; generic attachment routes must not bypass it."""
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    await _require_record_owner_or_manager(record, identity, db)
    if record.status != "在办":
        raise HTTPException(status_code=409, detail="仅在办知识产权案件可以维护案件文档")
    return record


async def _find_visible_ipr_case_by_legacy_no(parsed_case_no: str, identity: dict, db: AsyncSession) -> BusinessRecord | None:
    from app.core.legacy_sync import (
        _legacy_case_number_values,
    )
    rows = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "ipr_case", *(await _record_scope_conditions(identity, db)),
    ))).all())
    expected = parsed_case_no.lstrip("0") or "0"
    matched = [row for row in rows if expected in _legacy_case_number_values(row)]
    return matched[0] if len(matched) == 1 else None


async def _ensure_ipr_custom_import_batch_visible(batch_id: int, identity: dict, db: AsyncSession) -> IprCaseFileCustomImportBatch:
    batch = await db.get(IprCaseFileCustomImportBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="案件自定义文件导入批次不存在")
    if identity.get("role") == "admin" or batch.created_by == identity["username"]:
        return batch
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if identity.get("role") == "manager" and user and user.department == batch.department:
        return batch
    raise HTTPException(status_code=404, detail="案件自定义文件导入批次不存在或当前账号无权查看")


async def _ensure_ipr_import_batch_visible(batch_id: int, identity: dict, db: AsyncSession) -> IprOfficialImportBatch:
    batch = await db.get(IprOfficialImportBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="官文导入批次不存在")
    if identity.get("role") == "admin" or batch.created_by == identity["username"]:
        return batch
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if identity.get("role") == "manager" and user and user.department == batch.department:
        return batch
    raise HTTPException(status_code=404, detail="官文导入批次不存在或当前账号无权查看")


async def _visible_ipr_import_batches(identity: dict, db: AsyncSession) -> list[IprOfficialImportBatch]:
    """Return import batches under the same creator/department scope as the batch workspace."""
    conditions = []
    if identity.get("role") != "admin":
        user = await db.scalar(select(User).where(User.username == identity["username"]))
        if identity.get("role") == "manager" and user:
            conditions.append(or_(IprOfficialImportBatch.created_by == identity["username"], IprOfficialImportBatch.department == user.department))
        else:
            conditions.append(IprOfficialImportBatch.created_by == identity["username"])
    return list((await db.scalars(select(IprOfficialImportBatch).where(*conditions).order_by(IprOfficialImportBatch.created_at.desc()))).all())


async def _ensure_agent_document_access(document_id: int, identity: dict, db: AsyncSession, *, write: bool = False) -> tuple[AgentDocument, BusinessRecord | None]:
    item = await db.get(AgentDocument, document_id)
    if not item:
        raise HTTPException(status_code=404, detail="智能文档任务不存在")
    linked_record = await db.get(BusinessRecord, item.record_id) if item.record_id else None
    if item.record_id:
        # A generated document contains a snapshot of the related business
        # record.  Its creator must never retain access after that record is
        # transferred, hidden, or otherwise revoked.  Current record scope is
        # therefore checked before creator status for every module.
        if not linked_record:
            raise HTTPException(status_code=404, detail="关联业务记录不存在或无权访问")
        record = await _ensure_record_visible(item.record_id, identity, db)
        # Customer documents may contain a complete historic customer snapshot.
        # A shared read-only recipient can view the customer record itself, but
        # must not gain access to the generated document or its prompt/content.
        if record.module == "customer":
            await _require_record_owner_or_manager(record, identity, db)
            return item, record
        if write:
            await _require_record_owner_or_manager(record, identity, db)
        return item, record
    if identity.get("role") == "admin" or item.creator == identity["username"]:
        return item, None
    raise HTTPException(status_code=404, detail="智能文档任务不存在或无权访问")


async def _agent_document_capabilities(item: AgentDocument, identity: dict, db: AsyncSession, record: BusinessRecord | None) -> dict:
    """Return UI capabilities after the same checks used by protected APIs."""
    is_creator_or_admin = identity.get("role") == "admin" or item.creator == identity["username"]
    can_write = is_creator_or_admin
    if record:
        try:
            await _require_record_owner_or_manager(record, identity, db)
        except HTTPException:
            can_write = False
        else:
            can_write = True
    can_writeback = bool(can_write and record and item.status == "已人工确认")
    if can_writeback and record and record.module == "case":
        try:
            await _require_case_detail_write_access(record, identity, db)
        except HTTPException:
            can_writeback = False
    has_written_attachment = False
    if record:
        has_written_attachment = bool(await db.scalar(select(FileAttachment.id).where(FileAttachment.record_id == record.id, FileAttachment.remark == f"Dify任务 {item.job_no}")))
    can_delete = bool(can_write and is_creator_or_admin and not item.confirmed_by and not item.confirmed_at and not has_written_attachment)
    # Exported DOCX is a formal work product. It must not escape the review
    # gate just because it has not yet been written back as a business file.
    can_download = bool(item.status == "已人工确认" and item.confirmed_by and item.confirmed_at)
    return {"can_download": can_download, "can_edit": can_write, "can_retry": can_write, "can_confirm": can_write, "can_writeback": can_writeback, "can_delete": can_delete}
