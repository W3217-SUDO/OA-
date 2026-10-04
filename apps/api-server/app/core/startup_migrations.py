"""串行执行应用启动所需的结构迁移。"""

import hashlib
from collections.abc import Callable

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app.database import Base
from app.core.notification_schema_migration import upgrade_notification_delivery_schema
from app.core.record_read_model_migration import upgrade_record_read_model
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
NOTIFICATION_DELIVERY_REVISION = "notification_delivery_outbox_v1"
RECORD_READ_MODEL_REVISION = "business_record_read_model_v1"


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


def _apply_record_read_model(connection: Connection, _upgrade_schema: Callable[[Connection], None]) -> None:
    upgrade_record_read_model(connection)


def _run_versioned_schema_migrations(
    connection: Connection,
    upgrade_schema: Callable[[Connection], None],
) -> None:
    """每个结构版本仅在首次升级时执行，版本登记与变更同事务。"""
    connection.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (key VARCHAR(128) PRIMARY KEY)"))
    revisions = (
        (SCHEMA_BOOTSTRAP_REVISION, _apply_schema_bootstrap),
        (NOTIFICATION_DELIVERY_REVISION, _apply_notification_delivery),
        (RECORD_READ_MODEL_REVISION, _apply_record_read_model),
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
