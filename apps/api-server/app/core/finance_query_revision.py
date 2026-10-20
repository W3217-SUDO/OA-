"""财务查询缓存的数据修订：覆盖除少数高频非财务表之外的全部表。

控制台修订（``dashboard_revision``）只覆盖控制台依赖的表。财务查询还会读取旧系统导入、
应收计划、对账批次、旧案件日志等表，且经共享函数间接读取的表难以逐一列举。这里给当前
库中除排除名单外的每张表安装同一套修订触发器（同一张修订日志表、同一个触发函数），
财务查询缓存以修订日志的数量与总和判定数据是否变化。

读取修订时同时实时核对覆盖完整：任何一张非排除表缺少有效触发器（例如此后新建的表），
即视为无法判定，返回 None，调用方直接实时计算，不使用缓存。
"""
import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.dashboard_revision import (
    REVISION_TABLE, ROW_TRIGGER, TOUCH_FUNCTION, TRUNCATE_TRIGGER, quoted_identifier,
)
from app.core.request_metrics import measure_phase


logger = logging.getLogger(__name__)
MIGRATION_REVISION = "finance_query_revision_tables_v1"

# 后台循环或智能体持续写入、且财务查询不读取的表；修订日志及迁移登记表本身也不纳入。
EXCLUDED_TABLES = frozenset({
    REVISION_TABLE, "schema_migrations",
    "notification_sync_schedules", "ipr_case_reminder_types",
    "notifications", "notification_deliveries",
    "checkpoints", "checkpoint_blobs", "checkpoint_writes", "checkpoint_migrations",
})
_EXCLUDED_SQL = ", ".join("'" + name.replace("'", "''") + "'" for name in sorted(EXCLUDED_TABLES))

_COVERAGE_SQL = f"""
    NOT EXISTS (
        SELECT 1 FROM pg_class AS relation
        WHERE relation.relnamespace = (SELECT relnamespace FROM pg_class WHERE oid = to_regclass('{REVISION_TABLE}'))
            AND relation.relkind IN ('r', 'p')
            AND relation.relname NOT IN ({_EXCLUDED_SQL})
            AND NOT (
                EXISTS (
                    SELECT 1 FROM pg_trigger AS trigger JOIN pg_proc AS procedure ON procedure.oid = trigger.tgfoid
                    WHERE trigger.tgrelid = relation.oid AND trigger.tgname = '{ROW_TRIGGER}'
                        AND trigger.tgtype = 29 AND trigger.tgenabled = 'A' AND NOT trigger.tgisinternal
                        AND trigger.tgqual IS NULL AND procedure.proname = '{TOUCH_FUNCTION}'
                ) AND EXISTS (
                    SELECT 1 FROM pg_trigger AS trigger JOIN pg_proc AS procedure ON procedure.oid = trigger.tgfoid
                    WHERE trigger.tgrelid = relation.oid AND trigger.tgname = '{TRUNCATE_TRIGGER}'
                        AND trigger.tgtype = 32 AND trigger.tgenabled = 'A' AND NOT trigger.tgisinternal
                        AND procedure.proname = '{TOUCH_FUNCTION}'
                )
            )
    )
"""


def upgrade_finance_query_revision(connection):
    """给尚未安装修订触发器的非排除表安装触发器；已安装的表不改动，不更新任何业务行。"""
    if connection.dialect.name != "postgresql":
        return
    if not connection.scalar(text(f"SELECT to_regclass('{REVISION_TABLE}') IS NOT NULL")):
        raise RuntimeError("控制台事务修订表缺失，不能安装财务查询修订触发器")
    connection.execute(text("SET LOCAL lock_timeout = '5s'"))
    schema = connection.scalar(text(f"SELECT relnamespace::regnamespace::text FROM pg_class WHERE oid = to_regclass('{REVISION_TABLE}')"))
    function = f"{quoted_identifier(schema.strip(chr(34)))}.{quoted_identifier(TOUCH_FUNCTION)}"
    tables = connection.execute(text(f"""
        SELECT relation.relname FROM pg_class AS relation
        WHERE relation.relnamespace = (SELECT relnamespace FROM pg_class WHERE oid = to_regclass('{REVISION_TABLE}'))
            AND relation.relkind IN ('r', 'p') AND relation.relname NOT IN ({_EXCLUDED_SQL})
        ORDER BY relation.relname
    """)).scalars().all()
    for name in tables:
        target = quoted_identifier(name)
        existing = set(connection.execute(text(
            "SELECT tgname FROM pg_trigger WHERE tgrelid = CAST(:target AS regclass) AND NOT tgisinternal"
        ), {"target": target}).scalars().all())
        if ROW_TRIGGER not in existing:
            connection.execute(text(f"""
                CREATE TRIGGER {ROW_TRIGGER} AFTER INSERT OR UPDATE OR DELETE ON {target}
                FOR EACH ROW EXECUTE FUNCTION {function}()
            """))
            connection.execute(text(f"ALTER TABLE {target} ENABLE ALWAYS TRIGGER {ROW_TRIGGER}"))
        if TRUNCATE_TRIGGER not in existing:
            connection.execute(text(f"""
                CREATE TRIGGER {TRUNCATE_TRIGGER} AFTER TRUNCATE ON {target}
                FOR EACH STATEMENT EXECUTE FUNCTION {function}()
            """))
            connection.execute(text(f"ALTER TABLE {target} ENABLE ALWAYS TRIGGER {TRUNCATE_TRIGGER}"))
    if not connection.scalar(text(f"SELECT {_COVERAGE_SQL}")):
        raise RuntimeError("财务查询修订触发器安装后覆盖仍不完整")


async def finance_revision_snapshot(db, phase="query.cache.finance_revision"):
    """返回与控制台修订相同格式的令牌；覆盖不完整或会话不满足只读条件时返回 None。"""
    if db.get_bind().dialect.name != "postgresql" or db.new or db.dirty or db.deleted:
        return None
    try:
        with measure_phase(phase), db.no_autoflush:
            row = (await db.execute(text(f"""
                SELECT count(*)::text AS revision_count, COALESCE(sum(txid), 0)::text AS revision_sum,
                    pg_current_xact_id_if_assigned()::text AS own_xid,
                    current_setting('transaction_isolation') AS isolation,
                    ({_COVERAGE_SQL}) AS covered
                FROM {REVISION_TABLE}
            """))).one()
    except SQLAlchemyError as exc:
        logger.error("财务查询修订读取失败：%s", type(exc).__name__)
        return None
    if not row.covered:
        logger.warning("财务查询修订触发器覆盖不完整，本次查询不使用缓存")
        return None
    if row.own_xid is not None or row.isolation != "read committed" or db.new or db.dirty or db.deleted:
        return None
    if not (row.revision_count.isdigit() and row.revision_sum.isdigit()):
        return None
    return f"{row.revision_count}:{row.revision_sum}:"
