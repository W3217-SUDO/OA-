"""对齐既有数据库结构，保留启动时补齐缺失结构的能力。"""

import json

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

from app.core.constants import DEFAULT_ROLE_PERMISSIONS, FIELD_KEYS
from app.models import (
    LegacyCaseTaskHistory,
    LegacyCaseTaskHistoryFile,
    LegacyCaseTaskHistoryMessage,
    LegacyCaseTaskHistoryNode,
    LegacyCaseTaskHistoryNodeParticipant,
    LegacyCaseTaskHistoryNotification,
    LegacyCaseTaskHistoryReadReceipt,
)


def align_core_legacy_schema(connection: Connection) -> None:
    """补齐早期核心表的字段、索引和约束。"""
    columns = {item["name"] for item in inspect(connection).get_columns("file_attachments")}
    if "invoice_record_id" not in columns:
        connection.execute(text("ALTER TABLE file_attachments ADD COLUMN invoice_record_id INTEGER REFERENCES business_records(id) ON DELETE SET NULL"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_file_attachments_invoice_record_id ON file_attachments (invoice_record_id)"))
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


def align_integration_legacy_schema(connection: Connection) -> None:
    """补齐通知、收款及代理文档等后续集成字段。"""
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
    if "source_kind" not in incoming_columns:
        connection.execute(text("ALTER TABLE incoming_payments ADD COLUMN source_kind VARCHAR(24) NOT NULL DEFAULT 'unknown'"))
        from app.core.incoming_payment_sources import backfill_incoming_sources
        backfill_incoming_sources(connection)
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
