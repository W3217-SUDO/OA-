"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from datetime import datetime
from app.core.constants import (
    CASE_CREATE_PERMISSION_KEYS, DEFAULT_DEPARTMENTS, DEFAULT_JOB_ROLES, DEFAULT_ROLE_PERMISSIONS, DEFAULT_SYSTEM_CONFIGS,
    DEFAULT_SYSTEM_MENUS, DEFAULT_SYSTEM_PARAMETERS, FIELD_KEYS, LEGACY_ADMIN_MENU_KEYS, LEGACY_FINANCE_MENU_KEYS,
    LEGACY_INVESTIGATION_MENU_KEYS, LEGACY_TASK_MENU_KEYS, MENU_KEYS, ORIGINAL_ADMIN_MENU_KEYS, ORIGINAL_FINANCE_MENU_KEYS,
    ORIGINAL_INVESTIGATION_MENU_KEYS, REQUIRED_SEAL_ASSETS, ROLE_DATA_SCOPES, SYSTEM_ADMIN_JOB_PERMISSIONS, case_agent_runtime,
    logger,
)
from app.core.dependencies import (
    AsyncSession, Base, BusinessRecord, ContractApprovalStep, Department,
    DocumentTemplate, FastAPI, HearingSchedule, JSONResponse, JobRole,
    LegacyCaseTaskHistory, LegacyCaseTaskHistoryFile, LegacyCaseTaskHistoryMessage, LegacyCaseTaskHistoryNode, LegacyCaseTaskHistoryNodeParticipant,
    LegacyCaseTaskHistoryNotification, LegacyCaseTaskHistoryReadReceipt, ReceivablePlan, RequestValidationError, RolePermission,
    SealAsset, SecurityPolicy, SessionLocal, SystemConfig, SystemMenu,
    SystemParameter, User, WorkflowEvent, ZoneInfo, align_legacy_column_types,
    align_legacy_constraints, align_legacy_indexes, asynccontextmanager, asyncio, create_full_legacy_schema,
    ctypes, date, delete, engine, ensure_legacy_indexes,
    func, gc, hash_password, inspect, json,
    select, settings, suppress, sys, text,
    timezone,
)


def _upgrade_schema(connection) -> None:
    """为已有本地数据库补充 create_all 不会自动增加的兼容字段。"""
    from app.core.permissions import (
        _stored_menu_permission_keys,
    )
    columns = {item["name"] for item in inspect(connection).get_columns("file_attachments")}
    ipr_case_customer_columns = {item["name"] for item in inspect(connection).get_columns("ipr_case_customers")}
    if "sorting_index" not in ipr_case_customer_columns:
        connection.execute(text("ALTER TABLE ipr_case_customers ADD COLUMN sorting_index INTEGER"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS ix_ipr_case_customers_sorting_index ON ipr_case_customers (sorting_index)"))
    if "finance_transaction_id" not in columns:
        connection.execute(text("ALTER TABLE file_attachments ADD COLUMN finance_transaction_id INTEGER"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_file_attachments_finance_transaction_id ON file_attachments (finance_transaction_id)"))
    if "law_firm_id" not in columns:
        connection.execute(text("ALTER TABLE file_attachments ADD COLUMN law_firm_id INTEGER"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_file_attachments_law_firm_id ON file_attachments (law_firm_id)"))
    if "document_date" not in columns:
        connection.execute(text("ALTER TABLE file_attachments ADD COLUMN document_date DATE"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_file_attachments_document_date ON file_attachments (document_date)"))
    if "is_license" not in columns:
        connection.execute(text("ALTER TABLE file_attachments ADD COLUMN is_license BOOLEAN NOT NULL DEFAULT FALSE"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_file_attachments_is_license ON file_attachments (is_license)"))
    if "file_type_code" not in columns:
        connection.execute(text("ALTER TABLE file_attachments ADD COLUMN file_type_code VARCHAR(64) NOT NULL DEFAULT ''"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_file_attachments_file_type_code ON file_attachments (file_type_code)"))
    if "requires_transmission" not in columns:
        connection.execute(text("ALTER TABLE file_attachments ADD COLUMN requires_transmission BOOLEAN NOT NULL DEFAULT FALSE"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_file_attachments_requires_transmission ON file_attachments (requires_transmission)"))
    if "is_transmitted" not in columns:
        connection.execute(text("ALTER TABLE file_attachments ADD COLUMN is_transmitted BOOLEAN NOT NULL DEFAULT FALSE"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_file_attachments_is_transmitted ON file_attachments (is_transmitted)"))
    if "transmitted_at" not in columns:
        connection.execute(text("ALTER TABLE file_attachments ADD COLUMN transmitted_at TIMESTAMP WITH TIME ZONE"))
    if "transmitted_by" not in columns:
        connection.execute(text("ALTER TABLE file_attachments ADD COLUMN transmitted_by VARCHAR(64) NOT NULL DEFAULT ''"))
    if "is_locked" not in columns:
        connection.execute(text("ALTER TABLE file_attachments ADD COLUMN is_locked BOOLEAN NOT NULL DEFAULT FALSE"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_file_attachments_is_locked ON file_attachments (is_locked)"))
    if "locked_at" not in columns:
        connection.execute(text("ALTER TABLE file_attachments ADD COLUMN locked_at TIMESTAMP WITH TIME ZONE"))
    if "locked_by" not in columns:
        connection.execute(text("ALTER TABLE file_attachments ADD COLUMN locked_by VARCHAR(64) NOT NULL DEFAULT ''"))
    if "word_editor_lock_token" not in columns:
        connection.execute(text("ALTER TABLE file_attachments ADD COLUMN word_editor_lock_token VARCHAR(96) NOT NULL DEFAULT ''"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_file_attachments_word_editor_lock_token ON file_attachments (word_editor_lock_token)"))
    if "word_editor_lock_expires_at" not in columns:
        connection.execute(text("ALTER TABLE file_attachments ADD COLUMN word_editor_lock_expires_at TIMESTAMP WITH TIME ZONE"))
    if "word_editor_locked_by" not in columns:
        connection.execute(text("ALTER TABLE file_attachments ADD COLUMN word_editor_locked_by VARCHAR(64) NOT NULL DEFAULT ''"))
    if "communication_log_id" not in columns:
        connection.execute(text("ALTER TABLE file_attachments ADD COLUMN communication_log_id INTEGER REFERENCES communication_logs(id) ON DELETE CASCADE"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_file_attachments_communication_log_id ON file_attachments (communication_log_id)"))
    custom_import_batch_columns = {item["name"] for item in inspect(connection).get_columns("ipr_case_file_custom_import_batches")}
    if "is_test" not in custom_import_batch_columns:
        connection.execute(text("ALTER TABLE ipr_case_file_custom_import_batches ADD COLUMN is_test BOOLEAN NOT NULL DEFAULT FALSE"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_ipr_case_file_custom_import_batches_is_test ON ipr_case_file_custom_import_batches (is_test)"))
    department_columns = {item["name"] for item in inspect(connection).get_columns("departments")}
    if "overdue_deduction" not in department_columns:
        connection.execute(text("ALTER TABLE departments ADD COLUMN overdue_deduction BOOLEAN NOT NULL DEFAULT FALSE"))
    if "parent_department_id" not in department_columns:
        connection.execute(text("ALTER TABLE departments ADD COLUMN parent_department_id INTEGER"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_departments_parent_department_id ON departments (parent_department_id)"))
    law_firm_columns = {item["name"] for item in inspect(connection).get_columns("law_firms")}
    for column, definition in {
        "firm_type": "VARCHAR(64) NOT NULL DEFAULT ''",
        "firm_level": "VARCHAR(32) NOT NULL DEFAULT ''",
    }.items():
        if column not in law_firm_columns:
            connection.execute(text(f"ALTER TABLE law_firms ADD COLUMN {column} {definition}"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS ix_law_firms_firm_type ON law_firms (firm_type)"))
    user_columns = {item["name"] for item in inspect(connection).get_columns("users")}
    if "department" not in user_columns:
        connection.execute(text("ALTER TABLE users ADD COLUMN department VARCHAR(64) NOT NULL DEFAULT '上海分所'"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_users_department ON users (department)"))
    for column, definition in {
        "profile": "JSON NOT NULL DEFAULT '{}'",
        "role_ids": "JSON NOT NULL DEFAULT '[]'",
        "failed_login_attempts": "INTEGER NOT NULL DEFAULT 0",
        "locked_until": "DATETIME",
        "last_login_at": "DATETIME",
        "password_changed_at": "DATETIME",
        "must_change_password": "BOOLEAN NOT NULL DEFAULT FALSE",
    }.items():
        if column not in user_columns: connection.execute(text(f"ALTER TABLE users ADD COLUMN {column} {definition}"))
    menu_columns = {item["name"] for item in inspect(connection).get_columns("system_menus")}
    if "description" not in menu_columns:
        connection.execute(text("ALTER TABLE system_menus ADD COLUMN description VARCHAR(255) NOT NULL DEFAULT ''"))
    role_columns = {item["name"] for item in inspect(connection).get_columns("role_permissions")}
    if "field_keys" not in role_columns:
        default_fields = json.dumps(FIELD_KEYS, ensure_ascii=False)
        connection.execute(text(f"ALTER TABLE role_permissions ADD COLUMN field_keys JSON NOT NULL DEFAULT '{default_fields}'"))
        for role, config in DEFAULT_ROLE_PERMISSIONS.items():
            fields = json.dumps(config["field_keys"], ensure_ascii=False).replace("'", "''")
            connection.execute(text(f"UPDATE role_permissions SET field_keys = '{fields}' WHERE role = '{role}'"))
    job_role_columns = {item["name"] for item in inspect(connection).get_columns("job_roles")}
    if "field_keys" not in job_role_columns:
        connection.execute(text("ALTER TABLE job_roles ADD COLUMN field_keys JSON NOT NULL DEFAULT '[]'"))
        admin_fields = json.dumps(FIELD_KEYS, ensure_ascii=False).replace("'", "''")
        connection.execute(text(f"UPDATE job_roles SET field_keys = '{admin_fields}' WHERE code = 'SYSTEM-ADMIN'"))
    if "field_keys_configured" not in job_role_columns:
        connection.execute(text("ALTER TABLE job_roles ADD COLUMN field_keys_configured BOOLEAN NOT NULL DEFAULT FALSE"))
        connection.execute(text("UPDATE job_roles SET field_keys_configured = TRUE WHERE code = 'SYSTEM-ADMIN'"))
    if "data_scope" not in job_role_columns:
        connection.execute(text("ALTER TABLE job_roles ADD COLUMN data_scope VARCHAR(64)"))
    connection.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (key VARCHAR(128) PRIMARY KEY)"))
    ipr_fee_audit_columns = {
        item["name"]: item for item in inspect(connection).get_columns("ipr_fee_audit_logs")
    }
    case_record_column = ipr_fee_audit_columns.get("case_record_id")
    if case_record_column and not case_record_column.get("nullable", True):
        if connection.dialect.name == "sqlite":
            connection.execute(text("""
                CREATE TABLE ipr_fee_audit_logs_nullable_case (
                    id INTEGER NOT NULL PRIMARY KEY,
                    case_record_id INTEGER REFERENCES business_records(id) ON DELETE CASCADE,
                    header_id INTEGER REFERENCES ipr_fee_headers(id) ON DELETE SET NULL,
                    item_id INTEGER REFERENCES ipr_fee_items(id) ON DELETE SET NULL,
                    action VARCHAR(64) NOT NULL,
                    operator VARCHAR(64) NOT NULL,
                    detail JSON NOT NULL DEFAULT '{}',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            connection.execute(text("""
                INSERT INTO ipr_fee_audit_logs_nullable_case
                    (id, case_record_id, header_id, item_id, action, operator, detail, created_at)
                SELECT id, case_record_id, header_id, item_id, action, operator,
                       COALESCE(detail, '{}'), created_at
                FROM ipr_fee_audit_logs
            """))
            connection.execute(text("DROP TABLE ipr_fee_audit_logs"))
            connection.execute(text("ALTER TABLE ipr_fee_audit_logs_nullable_case RENAME TO ipr_fee_audit_logs"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_ipr_fee_audit_logs_case_record_id ON ipr_fee_audit_logs (case_record_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_ipr_fee_audit_logs_header_id ON ipr_fee_audit_logs (header_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_ipr_fee_audit_logs_item_id ON ipr_fee_audit_logs (item_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_ipr_fee_audit_logs_action ON ipr_fee_audit_logs (action)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_ipr_fee_audit_logs_operator ON ipr_fee_audit_logs (operator)"))
        else:
            connection.execute(text("ALTER TABLE ipr_fee_audit_logs ALTER COLUMN case_record_id DROP NOT NULL"))
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
    timestamp_type = "TIMESTAMP WITH TIME ZONE" if connection.dialect.name == "postgresql" else "DATETIME"
    notification_columns = {item["name"] for item in inspect(connection).get_columns("notifications")}
    for column, definition in {
        "sender": "VARCHAR(64) NOT NULL DEFAULT 'system'",
        "notification_type": "VARCHAR(32) NOT NULL DEFAULT '系统通知'",
        "recipient_deleted": "BOOLEAN NOT NULL DEFAULT 0",
        "sender_deleted": "BOOLEAN NOT NULL DEFAULT 0",
        "dingtalk_status": "VARCHAR(16) NOT NULL DEFAULT 'skipped'",
        "dingtalk_attempts": "INTEGER NOT NULL DEFAULT 0",
        "dingtalk_sent_at": timestamp_type,
        "dingtalk_error": "VARCHAR(500) NOT NULL DEFAULT ''",
    }.items():
        if column not in notification_columns: connection.execute(text(f"ALTER TABLE notifications ADD COLUMN {column} {definition}"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS ix_notifications_sender ON notifications (sender)"))
    incoming_columns = {item["name"] for item in inspect(connection).get_columns("incoming_payments")}
    for column, definition in {
        "contract_record_id": "INTEGER",
        "contract_no": "VARCHAR(64) NOT NULL DEFAULT ''",
        "case_no": "VARCHAR(64) NOT NULL DEFAULT ''",
        "bank_source": "VARCHAR(64) NOT NULL DEFAULT ''",
    }.items():
        if column not in incoming_columns:
            connection.execute(text(f"ALTER TABLE incoming_payments ADD COLUMN {column} {definition}"))
    incoming_bank_reference = next(
        (item for item in inspect(connection).get_columns("incoming_payments") if item["name"] == "bank_reference"),
        None,
    )
    if (
        connection.dialect.name == "postgresql"
        and incoming_bank_reference
        and not incoming_bank_reference.get("nullable", True)
    ):
        connection.execute(text("ALTER TABLE incoming_payments ALTER COLUMN bank_reference DROP NOT NULL"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS ix_incoming_payments_contract_record_id ON incoming_payments (contract_record_id)"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS ix_incoming_payments_contract_no ON incoming_payments (contract_no)"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS ix_incoming_payments_case_no ON incoming_payments (case_no)"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS ix_incoming_payments_bank_source ON incoming_payments (bank_source)"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS ix_notifications_notification_type ON notifications (notification_type)"))
    agent_document_columns = {item["name"] for item in inspect(connection).get_columns("agent_documents")}
    for column, definition in {
        "content_version": "INTEGER NOT NULL DEFAULT 1",
        "confirmed_by": "VARCHAR(64) NOT NULL DEFAULT ''",
        "confirmed_at": timestamp_type,
        "confirmed_content_hash": "VARCHAR(64) NOT NULL DEFAULT ''",
    }.items():
        if column not in agent_document_columns:
            connection.execute(text(f"ALTER TABLE agent_documents ADD COLUMN {column} {definition}"))
    reminder_type_columns = {item["name"] for item in inspect(connection).get_columns("ipr_case_reminder_types")}
    for column, definition in {
        "legacy_reminder_type_id": "INTEGER",
        "legacy_query_object": "TEXT NOT NULL DEFAULT ''",
        "owner": "VARCHAR(64) NOT NULL DEFAULT 'system'",
    }.items():
        if column not in reminder_type_columns:
            connection.execute(text(f"ALTER TABLE ipr_case_reminder_types ADD COLUMN {column} {definition}"))
    connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_ipr_case_reminder_types_legacy_id ON ipr_case_reminder_types (legacy_reminder_type_id)"))
    connection.execute(text("CREATE INDEX IF NOT EXISTS ix_ipr_case_reminder_types_owner ON ipr_case_reminder_types (owner)"))
    for model in (
        LegacyCaseTaskHistory,
        LegacyCaseTaskHistoryNode,
        LegacyCaseTaskHistoryNodeParticipant,
        LegacyCaseTaskHistoryMessage,
        LegacyCaseTaskHistoryNotification,
        LegacyCaseTaskHistoryReadReceipt,
        LegacyCaseTaskHistoryFile,
    ):
        model.__table__.create(connection, checkfirst=True)


async def _backfill_clue_generated_case_register_dates(db: AsyncSession) -> int:
    """Fill only missing filing dates on historical clue-generated cases.

    The conversion event is the authoritative business timestamp.  The case
    creation timestamp is used only for legacy rows whose matching event was
    lost; both are converted to the Shanghai business date.
    """
    cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case",
    ))).all())
    candidates = []
    for item in cases:
        data = item.data or {}
        if not bool(data.get("batch_converted")):
            continue
        case_register_date = str(data.get("case_register_date") or "").strip()
        filing_date = str(data.get("filing_date") or "").strip()
        if not case_register_date or not filing_date:
            candidates.append(item)
    if not candidates:
        return 0
    events = list((await db.scalars(select(WorkflowEvent).where(
        WorkflowEvent.record_id.in_([item.id for item in candidates]),
        WorkflowEvent.action == "线索生成案件",
    ).order_by(WorkflowEvent.created_at.asc(), WorkflowEvent.id.asc()))).all())
    generated_at_by_case: dict[int, datetime] = {}
    for event in events:
        generated_at_by_case.setdefault(event.record_id, event.created_at)
    business_tz = ZoneInfo("Asia/Shanghai")
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
    return len(candidates)


@asynccontextmanager
async def lifespan(_: FastAPI):
    from app.core.ipr import (
        _seed_legacy_ipr_reminder_types,
    )
    from app.core.legacy_sync import (
        _sync_legacy_case,
    )
    from app.core.permissions import (
        _stored_menu_permission_keys,
    )
    from app.core.system import (
        _business_rule_loop, _seed_business_records,
    )
    from app.core.tasks import (
        _dingtalk_notification_loop,
    )
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
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.run_sync(create_full_legacy_schema)
        await connection.run_sync(align_legacy_column_types)
        await connection.run_sync(align_legacy_constraints)
        await connection.run_sync(ensure_legacy_indexes)
        await connection.run_sync(align_legacy_indexes)
        await connection.run_sync(_upgrade_schema)
    async with SessionLocal() as db:
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
        record_count = await db.scalar(select(func.count()).select_from(BusinessRecord))
        if settings.seed_demo_data and not record_count:
            db.add_all(_seed_business_records())
            await db.flush()
        # SQLite 默认不强制外键，主动清理孤立流程记录，并为初始化数据补一条留痕。
        await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id.not_in(select(BusinessRecord.id))))
        records = (await db.scalars(select(BusinessRecord))).all()
        original_customer = next(
            (record for record in records if record.module == "customer" and record.serial_no == "SHKH1810649"),
            None,
        )
        if settings.seed_demo_data and original_customer is None:
            original_customer = BusinessRecord(
                module="customer", serial_no="SHKH1810649", title="test", customer="test",
                status="正常", owner="admin", department="上海分所",
                data={
                    "source_person": "管理者", "customer_managers": ["管理者"],
                    "customer_type": "客户", "invoice_address": "test",
                    "customer_source": "管理者", "is_shared": "否",
                    "level": "立案客户", "is_assisted": "否",
                    "file_date": "2018-07-29", "last_contact_at": "2018-07-29",
                    "last_modified_date": "2018-07-29", "contact_count": 0,
                    "contract_count": 3, "civil_case_count": 2,
                    "agency_fee_due": 0, "official_fee_unreceived": -4000,
                },
            )
            db.add(original_customer)
            await db.flush()
            records.append(original_customer)
        elif settings.seed_demo_data and original_customer.title == "test" and (original_customer.data or {}).get("source_person") == "管理者":
            # Keep the historical read-only reference fixture complete across upgrades.
            # This branch is restricted to the app-owned demo row and never overwrites
            # non-empty values, so user-created customer data remains untouched.
            fixture_defaults = {
                "customer_type": "客户", "invoice_address": "test",
                "customer_source": "管理者", "is_shared": "否",
                "level": "立案客户", "is_assisted": "否",
            }
            fixture_data = dict(original_customer.data or {})
            for key, value in fixture_defaults.items():
                if not fixture_data.get(key):
                    fixture_data[key] = value
            original_customer.data = fixture_data
        original_contracts = [
            ("SHHT2610035", "test_合同", "审批中", {"contract_body": "律所"}),
            ("SHHT2510026", "test_合同", "审批中", {
                "contract_body": "律所", "official_paid": 0, "official_received": 4000,
                "official_unreceived": -4000, "official_loss": 0, "agency_total": 6000,
                "agency_received": 6000, "agency_due": 0, "other_total": 0,
                "other_paid": 0, "other_due": 0, "invoice_opened": 0,
                "invoice_should": 6000, "invoice_excess": 0,
            }),
            ("SHHT1810328", "test_合同", "已归档", {"contract_body": "律所"}),
        ]
        if not settings.seed_demo_data:
            original_contracts = []
        existing_contract_nos = {record.serial_no for record in records if record.module == "contract"}
        for serial_no, title, contract_status, data in original_contracts:
            if serial_no in existing_contract_nos:
                continue
            original_contract = BusinessRecord(
                module="contract", serial_no=serial_no, title=title, customer="test",
                status=contract_status, owner="admin", department="上海分所",
                data={
                    "type": "争议解决合同", "fee_type": "固定收费", "signed_at": "",
                    "source_person": "管理者", "amount": data.get("agency_total", 0),
                    "official_paid": 0, "official_received": 0, "official_unreceived": 0,
                    "official_loss": 0, "agency_total": 0, "agency_received": 0,
                    "agency_due": 0, "other_total": 0, "other_paid": 0,
                    "other_due": 0, "invoice_opened": 0, "invoice_should": 0,
                    "invoice_excess": 0, **data,
                },
            )
            db.add(original_contract)
            await db.flush()
            records.append(original_contract)
        original_cases = [
            ("SHMS2300502", "一审待客户回款", "上海台享餐饮管理有限公司", "长寿区娅娅小吃店", "重庆市自由贸易试验区人民法院", "（2023）渝0192民初10300号", "外部合作律师", "外部合作律师", "2023-12-29", 928, "结算规档任务", "本案SHMS2300502已到账超过30日,请尽快提交结算并归档.", "外部合作律师", "2025-09-26"),
            ("SHMS2400031", "一审判决结案", "中饮巴比食品股份有限公司", "高新区芭比特包包子铺", "成都高新技术产业开发区人民法院", "(2024)川0191民初18219号", "System", "刘波", "2026-02-12", 152, "结算规档任务", "本案SHMS2400031已到账超过30日,请尽快提交结算并归档.", "刘波", "2026-03-25"),
            ("SHMS2400065", "一审判决结案", "中饮巴比食品股份有限公司", "璧山区段世华面馆", "重庆市自由贸易试验区人民法院", "(2024)渝0192民初10299号", "System", "刘波", "2026-02-12", 152, "结算规档任务", "本案SHMS2400065已到账超过30日,请尽快提交结算并归档.", "刘波", "2026-03-25"),
            ("SHMS2500709A", "已归档", "上海天路人造草坪有限公司", "常州莱因人造草坪科技有限公司", "江苏省苏州市中级人民法院", "（2025）苏05民初1478号", "陶勇刚", "陶勇刚", "2026-07-08", 6, "结算归档一审和解结案", "结算归档", "陶亮", "2026-05-23"),
            ("SHMS2400317", "等待公证书", "珠海双喜电器股份有限公司", "义乌市热康日用品厂", "", "", "System", "", "2024-05-19", 786, "案件审核", "品管回复停止取证", "System", "2026-07-15"),
            ("SH171000067", "一审待客户回款", "珠海格力电器股份有限公司", "常州市天宁区天宁正和电子经营部", "常州市天宁区人民法院", "（2018）苏0402民初4642号", "崔铧尹", "李晓岩,朱莹", "2023-03-15", 1217, "案件跟进回款", "这几个格力案件，现在什么情况？", "陶国南", "2026-07-16"),
            ("SH171000093", "一审待客户回款", "珠海格力电器股份有限公司", "常州市钱达电器经营部", "常州市天宁区人民法院", "（2018）苏0402民初4643号", "崔铧尹", "李晓岩,朱莹", "2023-02-13", 1247, "案件跟进回款", "这几个格力案件，现在什么情况？", "陶国南", "2026-07-16"),
            ("SHMS2500647", "文书准备", "九牧王股份有限公司", "亳州市谯城区衣家园服装批发店（个体工商户）", "利辛县人民法院", "", "李佳妮", "张美莹", "2026-01-07", 188, "案件审核", "", "李佳妮", "2026-07-16"),
            ("SH191000297", "执行终本", "中粮集团有限公司", "上海联华快客便利有限公司习勤店,蓬莱华夏葡园酒业有限公司,上海联华快客便利有限公司", "上海市徐汇区人民法院", "（2024）沪0104执7123号、（2025）沪0104执异495号", "陶勇刚", "李佳妮", "2025-11-24", 232, "终本案件，先到账的先结算发提成，后面还要继续追讨", "", "审核管理（赵媛）", "2026-07-16"),
            ("SHMS2500149", "文书准备", "广东三雄极光照明股份有限公司", "王勇,上海寻梦信息技术有限公司", "上海市长宁区人民法院", "", "王晓英", "郝蕴", "2025-08-13", 335, "文书审核", "已修改上传系统，是否可以盖章", "郝蕴", "2026-07-16"),
        ]
        if not settings.seed_demo_data:
            original_cases = []
        existing_case_nos = {record.serial_no for record in records if record.module == "case"}
        for case_item in original_cases:
            serial_no, case_status, plaintiff, defendant, court, court_case_no, lawyer, assistant, changed_at, days, task_name, task_content, task_handler, task_time = case_item
            if serial_no in existing_case_nos:
                continue
            original_case = BusinessRecord(
                module="case", serial_no=serial_no, title=f"{plaintiff}诉{defendant}", customer=plaintiff,
                status=case_status, owner="admin", department="上海分所",
                data={"case_type": "民事案件", "plaintiff": plaintiff, "opponent": defendant,
                      "court": court, "court_case_no": court_case_no, "hearing_lawyer": lawyer,
                      "handling_lawyers": [lawyer] if lawyer else [], "assistant": assistant,
                      "phase_changed_at": changed_at, "phase_days": days, "task_name": task_name,
                      "task_content": task_content, "task_handler": task_handler, "task_time": task_time},
            )
            db.add(original_case); await db.flush(); records.append(original_case)
        event_record_ids = set((await db.scalars(select(WorkflowEvent.record_id).distinct())).all())
        for record in records:
            if settings.seed_demo_data and record.id not in event_record_ids:
                db.add(WorkflowEvent(record_id=record.id, action="系统初始化", to_status=record.status, operator="system", comment="初始化示例业务数据"))
        if settings.seed_demo_data and not await db.scalar(select(func.count()).select_from(ReceivablePlan)):
            contracts = {record.serial_no: record for record in records if record.module == "contract"}
            if contracts.get("HT2026070018"):
                db.add_all([
                    ReceivablePlan(contract_record_id=contracts["HT2026070018"].id, phase="合同签订首付款", due_date=date(2026, 7, 20), amount=140000, received_amount=0, status="待收款", payer=contracts["HT2026070018"].customer),
                    ReceivablePlan(contract_record_id=contracts["HT2026070018"].id, phase="项目办结尾款", due_date=date(2026, 12, 20), amount=140000, received_amount=0, status="待收款", payer=contracts["HT2026070018"].customer),
                ])
            if contracts.get("HT2026060097"):
                db.add(ReceivablePlan(contract_record_id=contracts["HT2026060097"].id, phase="年度顾问费", due_date=date(2026, 6, 30), amount=120000, received_amount=80000, status="部分收款", payer=contracts["HT2026060097"].customer))
        if settings.seed_demo_data and not await db.scalar(select(func.count()).select_from(HearingSchedule)):
            cases = {record.serial_no: record for record in records if record.module == "case"}
            if cases.get("SH191000382B"):
                db.add(HearingSchedule(case_record_id=cases["SH191000382B"].id, hearing_date=date(2026, 7, 15), hearing_time="09:00", court="上海市宝山区人民法院", courtroom="第六法庭", hearing_type="一审开庭", hearing_lawyer="陈名涛"))
            if cases.get("SHMS2600387"):
                db.add(HearingSchedule(case_record_id=cases["SHMS2600387"].id, hearing_date=date(2026, 7, 20), hearing_time="14:00", court="杭州市余杭区人民法院", courtroom="第二法庭", hearing_type="证据交换", hearing_lawyer="陶勇刚"))
        if settings.seed_demo_data and not await db.scalar(select(func.count()).select_from(DocumentTemplate)):
            db.add_all([
                DocumentTemplate(name="民事起诉状", category="诉讼文书", version="2026.1", description="知识产权民事案件起诉状标准模板", fields=["原告", "被告", "诉讼请求", "事实与理由"]),
                DocumentTemplate(name="律师函", category="非诉文书", version="2026.1", description="侵权告知及停止侵权律师函", fields=["委托人", "收函人", "事实", "法律意见"]),
                DocumentTemplate(name="案件归档目录", category="归档文书", version="2026.1", description="案件归档材料目录标准模板", fields=["案号", "客户", "材料清单", "归档日期"]),
            ])
        await db.flush()
        assets_by_type = {item.seal_type: item for item in (await db.scalars(select(SealAsset))).all()}
        for record in records:
            if record.module == "seal" and not (record.data or {}).get("seal_asset_id"):
                asset = assets_by_type.get((record.data or {}).get("seal_type")) or assets_by_type.get("公章")
                if asset:
                    record.data = {**(record.data or {}), "seal_asset_id": asset.id, "seal_name": asset.name}
        approval_contracts = [record for record in records if settings.seed_demo_data and record.module == "contract" and record.status == "审批中"]
        for contract in approval_contracts:
            if not await db.scalar(select(func.count()).select_from(ContractApprovalStep).where(ContractApprovalStep.contract_record_id == contract.id)):
                db.add(ContractApprovalStep(contract_record_id=contract.id, step_order=1, approver="admin", status="待审批", comment="历史合同补充默认审批节点"))
        # v1.0.234: earlier builds incorrectly sent deficit archives directly to
        # the normal final-review queue. Restore the legacy first-stage queue.
        deficit_archives = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "case",
            BusinessRecord.status == "待归档审核",
        ))).all())
        for record in deficit_archives:
            data = dict(record.data or {})
            if data.get("archive_type") != "deficit" or data.get("archive_internal_reviewed_at"):
                continue
            record.status = "亏损内审"
            record.data = {
                **data,
                "case_phase": "亏损内审",
                "case_phase_id": 106016,
                "archive_status": "待内部审核",
                "archive_status_code": 7,
            }
            await _sync_legacy_case(record, {"username": "system"}, db)
        await _backfill_clue_generated_case_register_dates(db)
        await db.commit()
        # The lifespan generator remains suspended for the entire process lifetime.
        # Drop the startup-only ORM snapshot before yielding so migrated record JSON
        # does not remain resident until the service stops.
        records.clear()
    gc.collect()
    if sys.platform.startswith("linux"):
        try:
            ctypes.CDLL(None).malloc_trim(0)
        except (AttributeError, OSError):
            logger.warning("Unable to return released startup heap pages to the operating system")
    await case_agent_runtime.start()
    rule_task = asyncio.create_task(_business_rule_loop())
    dingtalk_task = asyncio.create_task(_dingtalk_notification_loop())
    try:
        yield
    finally:
        rule_task.cancel()
        dingtalk_task.cancel()
        with suppress(asyncio.CancelledError):
            await rule_task
        with suppress(asyncio.CancelledError):
            await dingtalk_task
        await case_agent_runtime.stop()


async def request_validation_error_handler(_, exc: RequestValidationError):
    details = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", []) if part != "body")
        details.append(f"{location}：{error.get('msg', '参数格式错误')}" if location else error.get("msg", "参数格式错误"))
    logger.warning("Request validation failed: %s", "；".join(details))
    return JSONResponse(status_code=422, content={"detail": "；".join(details)})
