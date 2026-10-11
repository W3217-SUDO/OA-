"""控制台事务修订集合：只由真实依赖表的已提交写入推进。"""
import logging

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.request_metrics import measure_phase


logger = logging.getLogger(__name__)
REVISION_TABLE = "dashboard_change_revisions"
MIGRATION_REVISION = "dashboard_transaction_revisions_v1"
DEPENDENCY_TABLES = (
    "business_records", "business_record_read_models", "users", "job_roles",
    "role_permissions", "workflow_events", "contract_objects", "contract_approval_steps",
    "file_attachments", "incoming_payments", "finance_transactions", "hearing_schedules",
    "departments", "system_parameters",
)
ROW_TRIGGER = "oa_dashboard_revision_row"
TRUNCATE_TRIGGER = "oa_dashboard_revision_truncate"
TOUCH_FUNCTION = "oa_dashboard_revision_touch"
OWN_TRIGGER = "oa_dashboard_revision_own_txid"
OWN_FUNCTION = "oa_dashboard_revision_check_txid"
IMMUTABLE_TRIGGER = "oa_dashboard_revision_append_only"
IMMUTABLE_FUNCTION = "oa_dashboard_revision_reject_changes"
FUNCTION_BODIES = {
    TOUCH_FUNCTION: """
        BEGIN
            INSERT INTO {table} (txid) VALUES (pg_current_xact_id()::text::bigint)
            ON CONFLICT (txid) DO NOTHING;
            RETURN NULL;
        END;
    """,
    OWN_FUNCTION: """
        BEGIN
            IF NEW.txid <> pg_current_xact_id()::text::bigint THEN
                RAISE EXCEPTION 'dashboard revision must belong to the current transaction';
            END IF;
            RETURN NEW;
        END;
    """,
    IMMUTABLE_FUNCTION: """
        BEGIN
            RAISE EXCEPTION 'dashboard revision log is append only';
        END;
    """,
}


def quoted_identifier(name):
    return '"' + name.replace('"', '""') + '"'


def function_body(name, schema):
    return FUNCTION_BODIES[name].format(table=f"{quoted_identifier(schema)}.{quoted_identifier(REVISION_TABLE)}")


def _sql_literal(value):
    return "'" + value.replace("'", "''") + "'"


def integrity_sql():
    """逐表核对触发器事件、时机、函数、启用状态及无条件执行。"""
    dependencies = ",".join(f"('{name}')" for name in DEPENDENCY_TABLES)
    touch_body = _sql_literal(FUNCTION_BODIES[TOUCH_FUNCTION].format(table=f'"%s"."{REVISION_TABLE}"'))
    own_body = _sql_literal(FUNCTION_BODIES[OWN_FUNCTION])
    immutable_body = _sql_literal(FUNCTION_BODIES[IMMUTABLE_FUNCTION])
    return f"""
        EXISTS (
            SELECT 1 FROM pg_class AS control
            JOIN pg_attribute AS attribute ON attribute.attrelid = control.oid
            JOIN pg_constraint AS primary_key ON primary_key.conrelid = control.oid
            WHERE control.oid = to_regclass('{REVISION_TABLE}')
                AND control.relkind = 'r' AND control.relpersistence = 'p'
                AND attribute.attname = 'txid' AND attribute.atttypid = 'bigint'::regtype
                AND attribute.attnotnull AND NOT attribute.attisdropped
                AND primary_key.contype = 'p' AND primary_key.convalidated
                AND NOT primary_key.condeferrable
                AND primary_key.conkey = ARRAY[attribute.attnum]::smallint[]
        ) AND NOT EXISTS (
            SELECT 1 FROM (VALUES {dependencies}) AS dependency(name)
            CROSS JOIN (VALUES ('{ROW_TRIGGER}', 29), ('{TRUNCATE_TRIGGER}', 32)) AS expected(name, kind)
            WHERE NOT EXISTS (
                SELECT 1 FROM pg_trigger AS trigger
                JOIN pg_proc AS procedure ON procedure.oid = trigger.tgfoid
                WHERE trigger.tgrelid = to_regclass(dependency.name)
                    AND trigger.tgname = expected.name AND trigger.tgtype = expected.kind
                    AND procedure.proname = '{TOUCH_FUNCTION}'
                    AND procedure.pronamespace = (
                        SELECT relnamespace FROM pg_class WHERE oid = to_regclass('{REVISION_TABLE}')
                    )
                    AND procedure.pronargs = 0 AND procedure.prorettype = 'trigger'::regtype
                    AND procedure.prosecdef AND procedure.proconfig = ARRAY['search_path=pg_catalog']
                    AND procedure.prosrc = format({touch_body}, replace((
                        SELECT nspname FROM pg_namespace WHERE oid = procedure.pronamespace
                    ), '"', '""'))
                    AND trigger.tgenabled = 'A' AND NOT trigger.tgisinternal
                    AND trigger.tgnargs = 0 AND trigger.tgattr = ''::int2vector
                    AND trigger.tgqual IS NULL AND NOT trigger.tgdeferrable
                    AND NOT trigger.tginitdeferred
            )
        ) AND NOT EXISTS (
            SELECT 1 FROM (VALUES
                ('{OWN_TRIGGER}', 7, '{OWN_FUNCTION}', {own_body}),
                ('{IMMUTABLE_TRIGGER}', 58, '{IMMUTABLE_FUNCTION}', {immutable_body})
            ) AS expected(name, kind, function_name, body)
            WHERE NOT EXISTS (
                SELECT 1 FROM pg_trigger AS trigger
                JOIN pg_proc AS procedure ON procedure.oid = trigger.tgfoid
                WHERE trigger.tgrelid = to_regclass('{REVISION_TABLE}')
                    AND trigger.tgname = expected.name AND trigger.tgtype = expected.kind
                    AND procedure.proname = expected.function_name
                    AND procedure.pronamespace = (
                        SELECT relnamespace FROM pg_class WHERE oid = to_regclass('{REVISION_TABLE}')
                    )
                    AND procedure.pronargs = 0 AND procedure.prorettype = 'trigger'::regtype
                    AND NOT procedure.prosecdef AND procedure.proconfig = ARRAY['search_path=pg_catalog']
                    AND procedure.prosrc = expected.body
                    AND trigger.tgenabled = 'A' AND NOT trigger.tgisinternal
                    AND trigger.tgnargs = 0 AND trigger.tgattr = ''::int2vector
                    AND trigger.tgqual IS NULL AND NOT trigger.tgdeferrable
                    AND NOT trigger.tginitdeferred
            )
        )
    """


def revision_query():
    # 集合只增不减；count 检测乱序提交，sum 使用 PG numeric，不能改为 MAX 或序列。
    return text(f"""
        SELECT count(*)::text AS revision_count, COALESCE(sum(txid), 0)::text AS revision_sum,
            pg_current_snapshot()::text AS pg_snapshot,
            pg_current_xact_id_if_assigned()::text AS own_xid,
            current_setting('transaction_isolation') AS isolation,
            ({integrity_sql()}) AS ready
        FROM {REVISION_TABLE}
    """)


async def dashboard_snapshot(db, phase="dashboard.cache.revision"):
    """保持无写会话和实时读取护栏，仅用业务修订集合判定缓存新鲜度。"""
    if db.get_bind().dialect.name != "postgresql" or db.new or db.dirty or db.deleted:
        return None
    try:
        with measure_phase(phase), db.no_autoflush:
            row = (await db.execute(revision_query())).one()
    except SQLAlchemyError as exc:
        logger.error("控制台事务修订读取失败：%s", type(exc).__name__)
        raise HTTPException(503, "控制台事务修订结构不可用，请核查启动迁移") from exc
    if not row.ready:
        raise HTTPException(503, "控制台事务修订触发器不完整或已停用")
    if row.own_xid is not None or row.isolation != "read committed" or db.new or db.dirty or db.deleted:
        return None
    if (not isinstance(row.pg_snapshot, str) or not row.pg_snapshot
            or not isinstance(row.revision_count, str) or not row.revision_count.isascii()
            or not row.revision_count.isdigit() or not isinstance(row.revision_sum, str)
            or not row.revision_sum.isascii() or not row.revision_sum.isdigit()):
        raise HTTPException(503, "控制台事务修订类型无效")
    # 沿用存储层的数字集合令牌格式；不是将 PG xmax 或快照范围当作业务版本。
    return f"{row.revision_count}:{row.revision_sum}:"
