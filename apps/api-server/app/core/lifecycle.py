"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from datetime import datetime
from sqlalchemy import func, or_
from app.core.constants import CASE_CREATE_PERMISSION_KEYS, case_agent_runtime, logger
from app.core.dependencies import (
    AsyncSession, BusinessRecord, FastAPI, JSONResponse, RequestValidationError,
    SessionLocal, WorkflowEvent, ZoneInfo, asynccontextmanager, asyncio, ctypes,
    engine, gc, json, select, settings, suppress, sys, text, timezone,
)
from app.core.schema_alignment import (
    align_core_legacy_schema,
    align_integration_legacy_schema,
)
from app.core.startup_data import initialize_startup_data
from app.core.startup_migrations import migrate_startup_schema


def _upgrade_schema(connection) -> None:
    """按既有顺序升级结构并执行原有一次性数据迁移。"""
    from app.core.permissions import (
        _stored_menu_permission_keys,
    )
    align_core_legacy_schema(connection)
    contract_status_migrated = connection.execute(text(
        "SELECT key FROM schema_migrations WHERE key = 'contract_approved_status_v1'"
    )).first()
    if not contract_status_migrated:
        connection.execute(text(
            "UPDATE business_records SET status = '审批通过' "
            "WHERE module = 'contract' AND status IN ('已通过', '履行中')"
        ))
        connection.execute(text(
            'UPDATE "FCM_Contract" SET "ContractStatus" = 20 WHERE "ContractStatus" = 70'
        ))
        connection.execute(text("INSERT INTO schema_migrations (key) VALUES ('contract_approved_status_v1')"))
    conflict_capability_migrated = connection.execute(text(
        "SELECT key FROM schema_migrations WHERE key = 'customer_conflict_leaf_v1'"
    )).first()
    if not conflict_capability_migrated:
        role_rows = connection.execute(text("SELECT role, menu_keys FROM role_permissions")).mappings().all()
        for role_row in role_rows:
            raw_keys = role_row["menu_keys"]
            keys = list(raw_keys if isinstance(raw_keys, list) else json.loads(raw_keys or "[]"))
            if role_row["role"] != "auditor" and "customer" in keys and "customer-conflict" not in keys:
                encoded_keys = json.dumps([*keys, "customer-conflict"], ensure_ascii=False).replace("'", "''")
                role = str(role_row["role"]).replace("'", "''")
                connection.execute(text(f"UPDATE role_permissions SET menu_keys = '{encoded_keys}' WHERE role = '{role}'"))
        connection.execute(text("INSERT INTO schema_migrations (key) VALUES ('customer_conflict_leaf_v1')"))
    case_create_capabilities_migrated = connection.execute(text(
        "SELECT key FROM schema_migrations WHERE key = 'case_create_leaf_capabilities_v1'"
    )).first()
    if not case_create_capabilities_migrated:
        role_rows = connection.execute(text("SELECT role, menu_keys FROM role_permissions")).mappings().all()
        for role_row in role_rows:
            raw_keys = role_row["menu_keys"]
            keys = list(raw_keys if isinstance(raw_keys, list) else json.loads(raw_keys or "[]"))
            if role_row["role"] != "auditor" and "case" in keys:
                migrated_keys = [*keys, *(key for key in CASE_CREATE_PERMISSION_KEYS if key not in keys)]
                encoded_keys = json.dumps(migrated_keys, ensure_ascii=False).replace("'", "''")
                role = str(role_row["role"]).replace("'", "''")
                connection.execute(text(f"UPDATE role_permissions SET menu_keys = '{encoded_keys}' WHERE role = '{role}'"))
        connection.execute(text("INSERT INTO schema_migrations (key) VALUES ('case_create_leaf_capabilities_v1')"))
    agent_center_menu_migrated = connection.execute(text(
        "SELECT key FROM schema_migrations WHERE key = 'agent_center_menu_v1'"
    )).first()
    if not agent_center_menu_migrated:
        role_rows = connection.execute(text("SELECT role, menu_keys FROM role_permissions")).mappings().all()
        for role_row in role_rows:
            raw_keys = role_row["menu_keys"]
            keys = list(raw_keys if isinstance(raw_keys, list) else json.loads(raw_keys or "[]"))
            if "case" in keys and "agent-center" not in keys:
                encoded_keys = json.dumps([*keys, "agent-center"], ensure_ascii=False).replace("'", "''")
                role = str(role_row["role"]).replace("'", "''")
                connection.execute(text(f"UPDATE role_permissions SET menu_keys = '{encoded_keys}' WHERE role = '{role}'"))
        connection.execute(text("INSERT INTO schema_migrations (key) VALUES ('agent_center_menu_v1')"))
    leaf_menu_permissions_migrated = connection.execute(text(
        "SELECT key FROM schema_migrations WHERE key = 'role_menu_leaf_permissions_v1'"
    )).first()
    if not leaf_menu_permissions_migrated:
        role_rows = connection.execute(text("SELECT role, menu_keys FROM role_permissions")).mappings().all()
        for role_row in role_rows:
            if role_row["role"] == "admin":
                continue
            raw_keys = role_row["menu_keys"]
            keys = list(raw_keys if isinstance(raw_keys, list) else json.loads(raw_keys or "[]"))
            migrated_keys = _stored_menu_permission_keys(keys)
            encoded_keys = json.dumps(migrated_keys, ensure_ascii=False).replace("'", "''")
            role = str(role_row["role"]).replace("'", "''")
            connection.execute(text(f"UPDATE role_permissions SET menu_keys = '{encoded_keys}' WHERE role = '{role}'"))
        connection.execute(text("INSERT INTO schema_migrations (key) VALUES ('role_menu_leaf_permissions_v1')"))
    ordinary_user_seal_menu_migrated = connection.execute(text(
        "SELECT key FROM schema_migrations WHERE key = 'ordinary_user_seal_my_menu_v1'"
    )).first()
    if not ordinary_user_seal_menu_migrated:
        role_row = connection.execute(text("SELECT menu_keys FROM role_permissions WHERE role = 'user'")).mappings().first()
        if role_row:
            raw_keys = role_row["menu_keys"]
            keys = list(raw_keys if isinstance(raw_keys, list) else json.loads(raw_keys or "[]"))
            seal_my_keys = _stored_menu_permission_keys(["seal-my"])
            migrated_keys = [*keys, *(key for key in seal_my_keys if key not in keys)]
            encoded_keys = json.dumps(migrated_keys, ensure_ascii=False).replace("'", "''")
            connection.execute(text(f"UPDATE role_permissions SET menu_keys = '{encoded_keys}' WHERE role = 'user'"))
        connection.execute(text("INSERT INTO schema_migrations (key) VALUES ('ordinary_user_seal_my_menu_v1')"))
    assistant_seal_scope_migrated = connection.execute(text(
        "SELECT key FROM schema_migrations WHERE key = 'assistant_seal_my_scope_v1'"
    )).first()
    if not assistant_seal_scope_migrated:
        role_row = connection.execute(text("SELECT permissions FROM job_roles WHERE code = 'ASSISTANT'")).mappings().first()
        if role_row:
            raw_permissions = role_row["permissions"]
            permissions = list(raw_permissions if isinstance(raw_permissions, list) else json.loads(raw_permissions or "[]"))
            retained = [
                value for value in permissions
                if not str(value).startswith("seal") and str(value) != "用印审批"
            ]
            seal_my_keys = _stored_menu_permission_keys(["seal-my"])
            migrated_permissions = [*retained, *(key for key in seal_my_keys if key not in retained)]
            encoded_permissions = json.dumps(migrated_permissions, ensure_ascii=False).replace("'", "''")
            connection.execute(text(f"UPDATE job_roles SET permissions = '{encoded_permissions}' WHERE code = 'ASSISTANT'"))
        connection.execute(text("INSERT INTO schema_migrations (key) VALUES ('assistant_seal_my_scope_v1')"))
    assistant_configured_seal_permissions_restored = connection.execute(text(
        "SELECT key FROM schema_migrations WHERE key = 'assistant_configured_seal_permissions_restore_v1'"
    )).first()
    if not assistant_configured_seal_permissions_restored:
        role_row = connection.execute(text("SELECT permissions FROM job_roles WHERE code = 'ASSISTANT'")).mappings().first()
        if role_row:
            raw_permissions = role_row["permissions"]
            permissions = list(raw_permissions if isinstance(raw_permissions, list) else json.loads(raw_permissions or "[]"))
            configured_seal_permissions = [
                "seal", "seal-my", "seal-audit", "seal-admin",
                "seal-my-pending", "seal-my-stamping", "seal-my-used", "seal-my-refused", "seal-my-withdrawn",
                "seal-audit-pending", "seal-audit-stamping", "seal-audit-refused",
                "seal-admin-pending", "seal-admin-used", "seal-admin-query", "用印审批",
            ]
            restored_permissions = [*permissions, *(value for value in configured_seal_permissions if value not in permissions)]
            encoded_permissions = json.dumps(restored_permissions, ensure_ascii=False).replace("'", "''")
            connection.execute(text(f"UPDATE job_roles SET permissions = '{encoded_permissions}' WHERE code = 'ASSISTANT'"))
        connection.execute(text("INSERT INTO schema_migrations (key) VALUES ('assistant_configured_seal_permissions_restore_v1')"))
    # Remove the short-lived internal marker used by an earlier development
    # build; internal migrations must never appear in editable system config.
    connection.execute(text("DELETE FROM system_configs WHERE key = 'permission_capability_migrations'"))
    align_integration_legacy_schema(connection)


async def _backfill_clue_generated_case_register_dates(db: AsyncSession) -> int:
    """Fill only missing filing dates on historical clue-generated cases.

    The conversion event is the authoritative business timestamp.  The case
    creation timestamp is used only for legacy rows whose matching event was
    lost; both are converted to the Shanghai business date.
    """
    missing_register_date = func.trim(func.coalesce(
        BusinessRecord.data["case_register_date"].as_string(), "",
    )) == ""
    missing_filing_date = func.trim(func.coalesce(
        BusinessRecord.data["filing_date"].as_string(), "",
    )) == ""
    business_tz = ZoneInfo("Asia/Shanghai")
    last_id = 0
    updated = 0
    while True:
        # 先在数据库筛掉日期完整的案件，再按主键分批，避免整案 JSON 常驻内存。
        cases = (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "case",
            BusinessRecord.id > last_id,
            or_(missing_register_date, missing_filing_date),
        ).order_by(BusinessRecord.id).limit(400))).all()
        if not cases:
            break
        last_id = cases[-1].id
        candidates = [item for item in cases if bool((item.data or {}).get("batch_converted"))]
        if not candidates:
            continue
        events = (await db.scalars(select(WorkflowEvent).where(
            WorkflowEvent.record_id.in_([item.id for item in candidates]),
            WorkflowEvent.action == "线索生成案件",
        ).order_by(WorkflowEvent.created_at.asc(), WorkflowEvent.id.asc()))).all()
        generated_at_by_case: dict[int, datetime] = {}
        for event in events:
            generated_at_by_case.setdefault(event.record_id, event.created_at)
        for item in candidates:
            data = dict(item.data or {})
            case_register_date = str(data.get("case_register_date") or "").strip()
            filing_date = str(data.get("filing_date") or "").strip()
            resolved_date = case_register_date or filing_date
            if not resolved_date:
                generated_at = generated_at_by_case.get(item.id) or item.created_at
                if generated_at.tzinfo is None:
                    generated_at = generated_at.replace(tzinfo=timezone.utc)
                resolved_date = str(generated_at.astimezone(business_tz).date())
            if not case_register_date:
                data["case_register_date"] = resolved_date
            if not filing_date:
                data["filing_date"] = resolved_date
            item.data = data
        updated += len(candidates)
        await db.flush()
    return updated


@asynccontextmanager
async def lifespan(_: FastAPI):
    from app.core.system import (
        _automatic_cache_cleanup_loop, _business_rule_loop,
    )
    from app.core.tasks import (
        _dingtalk_notification_loop,
    )
    from app.core.notification_scheduler import notification_scheduler_loop
    if settings.app_env.strip().lower() == "production":
        unsafe_secret = (
            len(settings.secret_key) < 64
            or "CHANGE_ME" in settings.secret_key.upper()
            or settings.secret_key == "replace-this-before-production"
        )
        unsafe_admin_password = (
            len(settings.initial_admin_password) < 12
            or "CHANGE_ME" in settings.initial_admin_password.upper()
            or settings.initial_admin_password == "20230616601"
            or settings.initial_admin_password.lower() in {"admin", "password", "12345678"}
        )
        if unsafe_secret:
            raise RuntimeError("生产环境 SECRET_KEY 不安全，必须使用至少 64 位随机值")
        if unsafe_admin_password:
            raise RuntimeError("生产环境 INITIAL_ADMIN_PASSWORD 不安全，必须使用至少 12 位强随机一次性密码")
    await migrate_startup_schema(engine, _upgrade_schema)
    await initialize_startup_data(SessionLocal, _backfill_clue_generated_case_register_dates)
    gc.collect()
    if sys.platform.startswith("linux"):
        try:
            ctypes.CDLL(None).malloc_trim(0)
        except (AttributeError, OSError):
            logger.warning("Unable to return released startup heap pages to the operating system")
    await case_agent_runtime.start()
    rule_task = asyncio.create_task(_business_rule_loop())
    cache_cleanup_task = asyncio.create_task(_automatic_cache_cleanup_loop())
    dingtalk_task = asyncio.create_task(_dingtalk_notification_loop())
    notification_task = asyncio.create_task(notification_scheduler_loop())
    try:
        yield
    finally:
        rule_task.cancel()
        cache_cleanup_task.cancel()
        dingtalk_task.cancel()
        notification_task.cancel()
        with suppress(asyncio.CancelledError):
            await rule_task
        with suppress(asyncio.CancelledError):
            await cache_cleanup_task
        with suppress(asyncio.CancelledError):
            await dingtalk_task
        with suppress(asyncio.CancelledError):
            await notification_task
        await case_agent_runtime.stop()


async def request_validation_error_handler(_, exc: RequestValidationError):
    details = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", []) if part != "body")
        details.append(f"{location}：{error.get('msg', '参数格式错误')}" if location else error.get("msg", "参数格式错误"))
    logger.warning("Request validation failed: %s", "；".join(details))
    return JSONResponse(status_code=422, content={"detail": "；".join(details)})
