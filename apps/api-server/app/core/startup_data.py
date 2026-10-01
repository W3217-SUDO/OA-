"""启动时补齐基础资料并执行现有历史业务回填。"""

from collections.abc import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.core.constants import (
    DEFAULT_DEPARTMENTS, DEFAULT_JOB_ROLES, DEFAULT_ROLE_PERMISSIONS,
    DEFAULT_SYSTEM_CONFIGS, DEFAULT_SYSTEM_MENUS, DEFAULT_SYSTEM_PARAMETERS,
    FIELD_KEYS, LEGACY_ADMIN_MENU_KEYS, LEGACY_FINANCE_MENU_KEYS,
    LEGACY_INVESTIGATION_MENU_KEYS, LEGACY_TASK_MENU_KEYS, MENU_KEYS,
    ORIGINAL_ADMIN_MENU_KEYS, ORIGINAL_FINANCE_MENU_KEYS,
    ORIGINAL_INVESTIGATION_MENU_KEYS, REQUIRED_SEAL_ASSETS, ROLE_DATA_SCOPES,
    SYSTEM_ACTION_DEFINITIONS, SYSTEM_ADMIN_JOB_PERMISSIONS,
)
from app.core.startup_backfills import run_historical_backfills
from app.core.startup_migrations import lock_startup_transaction
from app.models import (
    BusinessRecord, Department, JobRole, RolePermission, SealAsset,
    SecurityPolicy, SystemConfig, SystemMenu, SystemParameter, User,
)
from app.security import hash_password


async def initialize_startup_data(
    session_factory: async_sessionmaker[AsyncSession],
    backfill_clue_case_dates: Callable[[AsyncSession], Awaitable[int]],
) -> None:
    """在独立事务中补齐基础资料并执行尚未登记的历史修正。"""
    from app.core.ipr import _seed_legacy_ipr_reminder_types
    from app.core.permissions import _stored_menu_permission_keys

    async with session_factory() as db:
        await lock_startup_transaction(await db.connection())
        existing = await db.scalar(select(User).where(User.username == settings.initial_admin_username))
        if not existing:
            if not settings.initial_admin_password:
                raise RuntimeError("首次初始化必须通过 INITIAL_ADMIN_PASSWORD 配置一次性管理员密码")
            db.add(User(
                username=settings.initial_admin_username,
                display_name=settings.initial_admin_display_name,
                department=settings.initial_admin_department,
                role="admin",
                role_ids=["admin"],
                password_hash=hash_password(settings.initial_admin_password),
                must_change_password=True,
            ))
        if not await db.get(SecurityPolicy, 1):
            db.add(SecurityPolicy(id=1, min_password_length=8, max_failed_attempts=5, lock_minutes=30, token_minutes=settings.access_token_minutes, updated_by="system"))
        existing_roles = set((await db.scalars(select(RolePermission.role))).all())
        for role, config in DEFAULT_ROLE_PERMISSIONS.items():
            if role not in existing_roles:
                role_config = dict(config)
                if role != "admin":
                    role_config["menu_keys"] = _stored_menu_permission_keys(config["menu_keys"])
                db.add(RolePermission(role=role, **role_config))
        admin_permission = await db.scalar(select(RolePermission).where(RolePermission.role == "admin"))
        if admin_permission:
            admin_config = DEFAULT_ROLE_PERMISSIONS["admin"]
            admin_permission.display_name = admin_config["display_name"]
            admin_permission.data_scope = admin_config["data_scope"]
            admin_permission.menu_keys = list(MENU_KEYS)
            admin_permission.field_keys = list(FIELD_KEYS)
        # Versions before server-side validation could persist arbitrary data
        # scopes.  Repair those legacy values deterministically at startup so
        # they never continue through the implicit own/shared-data fallback.
        role_permissions = (await db.scalars(select(RolePermission))).all()
        for permission in role_permissions:
            if permission.data_scope not in ROLE_DATA_SCOPES:
                permission.data_scope = DEFAULT_ROLE_PERMISSIONS.get(
                    permission.role,
                    DEFAULT_ROLE_PERMISSIONS["user"],
                )["data_scope"]
            stored_keys = list(permission.menu_keys or [])
            if permission.role != "admin" and any(key == "case" or str(key).startswith("case-") for key in stored_keys):
                existing_actions = {str(key).removeprefix("@action:") for key in stored_keys if str(key).startswith("@action:")}
                if not any(code.startswith("case.") for code in existing_actions):
                    stored_keys.extend(
                        f"@action:{item['code']}" for item in SYSTEM_ACTION_DEFINITIONS
                        if item["code"].startswith("case.")
                    )
                    permission.menu_keys = list(dict.fromkeys(stored_keys))
        existing_parameters = set((await db.execute(select(SystemParameter.category, SystemParameter.code))).all())
        for index, (category, code, name, extra) in enumerate(DEFAULT_SYSTEM_PARAMETERS, start=1):
            if (category, code) not in existing_parameters:
                db.add(SystemParameter(category=category, code=code, name=name, extra=extra, sort_order=index, created_by="system", updated_by="system"))
        await db.flush()
        civil_phase_defaults = {
            code: (name, extra)
            for category, code, name, extra in DEFAULT_SYSTEM_PARAMETERS
            if category == "case_phase" and str(extra.get("case_type") or "").strip() == "民事争议"
        }
        civil_phases = (await db.scalars(select(SystemParameter).where(SystemParameter.category == "case_phase"))).all()
        for phase in civil_phases:
            expected = civil_phase_defaults.get(phase.code)
            configured_type = str((phase.extra or {}).get("case_type") or "").strip()
            if expected:
                name, extra = expected
                phase.name = name
                phase.extra = dict(extra)
                phase.sort_order = int(extra.get("sort_order") or 0)
                phase.is_active = True
                phase.updated_by = "system"
            elif configured_type in {"民事争议", "民事案件"} and phase.created_by == "system":
                phase.is_active = False
                phase.updated_by = "system"
        existing_configs = {item.key: item for item in (await db.scalars(select(SystemConfig))).all()}
        for key, config in DEFAULT_SYSTEM_CONFIGS.items():
            if key not in existing_configs:
                db.add(SystemConfig(key=key, **config, updated_by="system"))
            else:
                current_value = existing_configs[key].value or {}
                missing_defaults = {name: value for name, value in config["value"].items() if name not in current_value}
                if missing_defaults:
                    existing_configs[key].value = {**current_value, **missing_defaults}
        await _seed_legacy_ipr_reminder_types(db)
        existing_menus = {item.key: item for item in (await db.scalars(select(SystemMenu))).all()}
        for key, parent_key, label, icon, sort_order in DEFAULT_SYSTEM_MENUS:
            if key not in existing_menus:
                db.add(SystemMenu(key=key, parent_key=parent_key, label=label, icon=icon, sort_order=sort_order, updated_by="system"))
            elif key in ORIGINAL_FINANCE_MENU_KEYS or key in ORIGINAL_ADMIN_MENU_KEYS or key in ORIGINAL_INVESTIGATION_MENU_KEYS or (
                key.startswith("customer-") and existing_menus[key].updated_by == "system"
            ) or (
                key in {"documents-official", "documents-my", "documents-company"}
                and existing_menus[key].updated_by == "system"
            ):
                existing_menus[key].parent_key = parent_key
                existing_menus[key].label = label
                existing_menus[key].icon = icon
                existing_menus[key].sort_order = sort_order
                existing_menus[key].is_visible = True
                existing_menus[key].is_active = True
        for key in LEGACY_FINANCE_MENU_KEYS:
            if key in existing_menus:
                existing_menus[key].is_visible = False
                existing_menus[key].is_active = False
        for key in LEGACY_ADMIN_MENU_KEYS:
            if key in existing_menus:
                existing_menus[key].is_visible = False
                existing_menus[key].is_active = False
        for key in LEGACY_INVESTIGATION_MENU_KEYS:
            if key in existing_menus:
                existing_menus[key].is_visible = False
                existing_menus[key].is_active = False
        for key in LEGACY_TASK_MENU_KEYS:
            if key in existing_menus:
                existing_menus[key].is_visible = False
                existing_menus[key].is_active = False
        existing_department_codes = set((await db.scalars(select(Department.code))).all())
        for index, (code, name) in enumerate(DEFAULT_DEPARTMENTS, start=1):
            if code not in existing_department_codes: db.add(Department(code=code, name=name, sort_order=index, created_by="system", updated_by="system"))
        existing_job_role_codes = set((await db.scalars(select(JobRole.code))).all())
        existing_job_role_names = set((await db.scalars(select(JobRole.name))).all())
        for index, (code, name, permissions) in enumerate(DEFAULT_JOB_ROLES, start=1):
            if code not in existing_job_role_codes and name not in existing_job_role_names:
                db.add(JobRole(code=code, name=name, permissions=permissions, sort_order=index, created_by="system", updated_by="system"))
        system_admin_job_role = await db.scalar(select(JobRole).where(JobRole.code == "SYSTEM-ADMIN"))
        if system_admin_job_role:
            system_admin_job_role.name = "系统管理员"
            system_admin_job_role.permissions = list(SYSTEM_ADMIN_JOB_PERMISSIONS)
            system_admin_job_role.field_keys = list(FIELD_KEYS)
            system_admin_job_role.field_keys_configured = True
            system_admin_job_role.data_scope = "全所数据"
            system_admin_job_role.is_active = True
        # 七类印章是合同用印流程所需的基础资料，不属于演示数据。这里只补缺，
        # 不覆盖管理员已经维护的保管人、位置、状态、用印次数等真实台账字段。
        existing_seal_assets = (await db.scalars(select(SealAsset))).all()
        seal_assets_by_type = {item.seal_type: item for item in existing_seal_assets}
        seal_assets_by_code = {item.code: item for item in existing_seal_assets}
        legacy_default_types = {"合同专用章": "合同章", "律师事务所专用章": "所函专用章"}
        for code, seal_type, location in REQUIRED_SEAL_ASSETS:
            if seal_type in seal_assets_by_type:
                continue
            existing_asset = seal_assets_by_code.get(code)
            if (
                existing_asset
                and existing_asset.name.startswith("申浩律师事务所")
                and legacy_default_types.get(existing_asset.seal_type) == seal_type
            ):
                existing_asset.name = f"申浩律师事务所{seal_type}"
                existing_asset.seal_type = seal_type
                seal_assets_by_type[seal_type] = existing_asset
                continue
            if existing_asset:
                # 默认编号被真实台账占用时不覆盖用户数据，换一个系统补缺编号。
                code = f"{code.rsplit('-', 1)[0]}-SYS-001"
            asset = SealAsset(
                code=code,
                name=f"申浩律师事务所{seal_type}",
                seal_type=seal_type,
                custodian="admin",
                location=location,
                remark="系统基础印章资料；管理员可在用印中心维护保管信息",
            )
            db.add(asset)
            seal_assets_by_type[seal_type] = asset
        await db.flush()
        assets_by_type = {item.seal_type: item for item in (await db.scalars(select(SealAsset))).all()}
        seal_records = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "seal"))).all()
        for record in seal_records:
            if record.module == "seal" and not (record.data or {}).get("seal_asset_id"):
                asset = assets_by_type.get((record.data or {}).get("seal_type")) or assets_by_type.get("公章")
                if asset:
                    record.data = {**(record.data or {}), "seal_asset_id": asset.id, "seal_name": asset.name}
        await run_historical_backfills(db, backfill_clue_case_dates)
        await db.commit()
