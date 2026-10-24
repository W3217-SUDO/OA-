"""串行执行应用启动所需的结构迁移。"""

import hashlib
from collections.abc import Callable

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app.database import Base
from app.core.notification_schema_migration import upgrade_notification_delivery_schema
from app.core.record_read_model_migration import upgrade_record_read_model
from app.core.schema_alignment import align_business_record_json_indexes
from app.core.soft_delete_migration import MIGRATION_REVISION as SOFT_DELETE_REVISION, upgrade_soft_delete
from app.core.incoming_finance_schema_migration import (
    MIGRATION_REVISION as INCOMING_FINANCE_REVISION, upgrade_incoming_finance_schema,
)
from app.core.dashboard_finance_read_model_migration import (
    MIGRATION_REVISION as DASHBOARD_FINANCE_REVISION,
    upgrade_dashboard_finance_read_model, validate_dashboard_finance_read_model,
)
from app.core.dashboard_revision import MIGRATION_REVISION as DASHBOARD_REVISION
from app.core.dashboard_revision_migration import upgrade_dashboard_revision, validate_dashboard_revision
from app.core.finance_query_revision import (
    MIGRATION_REVISION as FINANCE_QUERY_REVISION, REINSTALL_REVISION as FINANCE_QUERY_REINSTALL_REVISION,
    upgrade_finance_query_revision,
)
from app.core.hz_allocation_read_model_migration import (
    MIGRATION_REVISION as HZ_ALLOCATION_READ_MODEL_REVISION,
    upgrade_hz_allocation_read_model,
)
from app.core.party_library import (
    MIGRATION_REVISION as PARTY_LIBRARY_REVISION, PARTY_MASTER_REVISION, upgrade_party_library, upgrade_party_master,
)
from app.legacy_schema import (
    align_legacy_column_types,
    align_legacy_constraints,
    align_legacy_indexes,
    create_full_legacy_schema,
    ensure_legacy_indexes,
)


_STARTUP_LOCK_ID = int.from_bytes(
    hashlib.sha256(b"sunhold-oa:startup-migrations").digest()[:8],
    byteorder="big",
    signed=True,
)
SCHEMA_BOOTSTRAP_REVISION = "startup_schema_bootstrap_v1"
LEGACY_SETTLEMENT_INDEX_REVISION = "legacy_settlement_query_indexes_v1"
NOTIFICATION_DELIVERY_REVISION = "notification_delivery_outbox_v1"
RECORD_READ_MODEL_REVISION = "business_record_read_model_v1"
CASE_LINK_JSON_INDEX_REVISION = "business_record_case_link_json_indexes_v1"


def _apply_schema_bootstrap(connection: Connection, upgrade_schema: Callable[[Connection], None]) -> None:
    """保留旧版完整结构对齐的执行顺序。"""
    Base.metadata.create_all(connection)
    create_full_legacy_schema(connection)
    align_legacy_column_types(connection)
    align_legacy_constraints(connection)
    ensure_legacy_indexes(connection)
    align_legacy_indexes(connection)
    upgrade_schema(connection)


def _apply_notification_delivery(connection: Connection, _upgrade_schema: Callable[[Connection], None]) -> None:
    """已完成历史结构升级的数据库也独立补齐通知队列表。"""
    upgrade_notification_delivery_schema(connection)


def _apply_legacy_settlement_indexes(connection: Connection, _upgrade_schema: Callable[[Connection], None]) -> None:
    """为历史结算投影补齐固定父子联接索引。"""
    if connection.dialect.name != "postgresql":
        return
    connection.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_legacy_finance_allocations_parent_source_active "
        "ON legacy_finance_allocations (legacy_finance_record_id, source_table, is_active)"
    ))
    connection.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_legacy_finance_records_source_active_id "
        "ON legacy_finance_records (source_table, is_active, id)"
    ))
    connection.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_legacy_finance_records_payment_status_json "
        "ON legacy_finance_records (source_table, ((source_payload->>'SettlementStatus')))"
    ))
    connection.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_legacy_finance_allocations_archive_status_json "
        "ON legacy_finance_allocations (source_table, ((source_payload->>'ArchiveAmountSettlementStatus')), is_active)"
    ))
    connection.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_legacy_finance_allocations_active_json "
        "ON legacy_finance_allocations (source_table, ((source_payload->>'IsActived')), is_active)"
    ))


def _apply_case_link_json_indexes(connection: Connection, _upgrade_schema: Callable[[Connection], None]) -> None:
    """已完成历史结构升级的数据库也独立补齐案件关联 JSON 表达式索引。"""
    align_business_record_json_indexes(connection)


def _apply_record_read_model(connection: Connection, _upgrade_schema: Callable[[Connection], None]) -> None:
    upgrade_record_read_model(connection)


def _apply_dashboard_revision(connection: Connection, _upgrade_schema: Callable[[Connection], None]) -> None:
    upgrade_dashboard_revision(connection)


def _apply_finance_query_revision(connection: Connection, _upgrade_schema: Callable[[Connection], None]) -> None:
    upgrade_finance_query_revision(connection)


def _apply_dashboard_finance(connection: Connection, _upgrade_schema: Callable[[Connection], None]) -> None:
    upgrade_dashboard_finance_read_model(connection)


def _apply_incoming_finance(connection: Connection, _upgrade_schema: Callable[[Connection], None]) -> None:
    upgrade_incoming_finance_schema(connection)


def _apply_party_library(connection: Connection, _upgrade_schema: Callable[[Connection], None]) -> None:
    upgrade_party_library(connection)


def _apply_party_master(connection: Connection, _upgrade_schema: Callable[[Connection], None]) -> None:
    upgrade_party_master(connection)


def _apply_mcp_access_tokens(connection: Connection, _upgrade_schema: Callable[[Connection], None]) -> None:
    from app.data_models.mcp_tokens import McpAccessToken, McpCallLog
    McpAccessToken.__table__.create(connection, checkfirst=True)
    McpCallLog.__table__.create(connection, checkfirst=True)


def _apply_mcp_token_write(connection: Connection, _upgrade_schema: Callable[[Connection], None]) -> None:
    from sqlalchemy import inspect
    inspector = inspect(connection)
    for table, column in (("mcp_call_logs", "is_write"),):
        if column not in {item["name"] for item in inspector.get_columns(table)}:
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} INTEGER NOT NULL DEFAULT 0"))


def _apply_soft_delete(connection: Connection, _upgrade_schema: Callable[[Connection], None]) -> None:
    upgrade_soft_delete(connection)


def _apply_change_log(connection: Connection, _upgrade_schema: Callable[[Connection], None]) -> None:
    from app.data_models.change_logs import DataChangeLog
    DataChangeLog.__table__.create(connection, checkfirst=True)


def _apply_hz_allocation_read_model(connection: Connection, _upgrade_schema: Callable[[Connection], None]) -> None:
    upgrade_hz_allocation_read_model(connection)


def _apply_customer_list_indexes(connection: Connection, _upgrade_schema: Callable[[Connection], None]) -> None:
    from app.core.customer_readmodel import create_customer_list_indexes
    create_customer_list_indexes(connection)


def _run_versioned_schema_migrations(
    connection: Connection,
    upgrade_schema: Callable[[Connection], None],
) -> None:
    """每个结构版本仅在首次升级时执行，版本登记与变更同事务。"""
    connection.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (key VARCHAR(128) PRIMARY KEY)"))
    revisions = (
        (SCHEMA_BOOTSTRAP_REVISION, _apply_schema_bootstrap),
        (SOFT_DELETE_REVISION, _apply_soft_delete),  # 先于其他修订：后面的 ORM 读写会带上 deleted_at 列
        ("data_change_logs_v1", _apply_change_log),  # 变更留痕表要在任何 ORM 写入之前就有
        (LEGACY_SETTLEMENT_INDEX_REVISION, _apply_legacy_settlement_indexes),
        (INCOMING_FINANCE_REVISION, _apply_incoming_finance),
        (HZ_ALLOCATION_READ_MODEL_REVISION, _apply_hz_allocation_read_model),
        (NOTIFICATION_DELIVERY_REVISION, _apply_notification_delivery),
        (RECORD_READ_MODEL_REVISION, _apply_record_read_model),
        (DASHBOARD_FINANCE_REVISION, _apply_dashboard_finance),
        (DASHBOARD_REVISION, _apply_dashboard_revision),
        (FINANCE_QUERY_REVISION, _apply_finance_query_revision),
        (CASE_LINK_JSON_INDEX_REVISION, _apply_case_link_json_indexes),
        (PARTY_LIBRARY_REVISION, _apply_party_library),
        (PARTY_MASTER_REVISION, _apply_party_master),
        ("mcp_access_tokens_v1", _apply_mcp_access_tokens),
        ("mcp_access_tokens_write_v1", _apply_mcp_token_write),
        ("customer_list_indexes_v1", _apply_customer_list_indexes),
        # 放在所有建表修订之后：给此前新建的表补财务查询修订触发器，恢复财务查询缓存。
        (FINANCE_QUERY_REINSTALL_REVISION, _apply_finance_query_revision),
    )
    for revision, migration in revisions:
        if connection.execute(
            text("SELECT key FROM schema_migrations WHERE key = :key"),
            {"key": revision},
        ).first():
            continue
        migration(connection, upgrade_schema)
        connection.execute(
            text("INSERT INTO schema_migrations (key) VALUES (:key)"),
            {"key": revision},
        )
    validate_dashboard_finance_read_model(connection)
    validate_dashboard_revision(connection)


async def lock_startup_transaction(connection: AsyncConnection) -> None:
    """让不同进程的结构迁移和基础数据初始化依次执行。"""
    dialect_name = connection.dialect.name
    if dialect_name == "postgresql":
        await connection.execute(
            text("SELECT pg_advisory_xact_lock(:lock_id)"),
            {"lock_id": _STARTUP_LOCK_ID},
        )
    elif dialect_name == "sqlite":
        await connection.exec_driver_sql("PRAGMA busy_timeout = 60000")
        await connection.exec_driver_sql("BEGIN IMMEDIATE")
    else:
        raise RuntimeError(f"不支持的启动迁移数据库类型：{dialect_name}")


async def migrate_startup_schema(
    engine: AsyncEngine,
    upgrade_schema: Callable[[Connection], None],
) -> None:
    """仅在缺少版本登记时，按原有顺序执行结构升级。"""
    async with engine.begin() as connection:
        await lock_startup_transaction(connection)
        await connection.run_sync(_run_versioned_schema_migrations, upgrade_schema)
