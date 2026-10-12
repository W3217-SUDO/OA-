"""同业务事务维护费用关联事实，不在写入时计算金额或正规化旧值。"""
import re

from sqlalchemy import text

from app.core.constants import _OFFICIAL_RECEIVABLE_FEE_WORDS
from app.core.dashboard_finance_read_model import LINK_FIELDS, RAW_FIELDS, TABLE_NAME, TYPE_FIELDS
from app.core.dashboard_revision import (
    REVISION_TABLE, ROW_TRIGGER, TOUCH_FUNCTION, TRUNCATE_TRIGGER, quoted_identifier,
)


MIGRATION_REVISION = "dashboard_finance_relations_v1"
SYNC_FUNCTION = "oa_dashboard_finance_sync"
SYNC_TRIGGER = "oa_dashboard_finance_sync_row"
CLEAR_FUNCTION = "oa_dashboard_finance_clear"
CLEAR_TRIGGER = "oa_dashboard_finance_clear_all"
FUNCTION_NAMES = (SYNC_FUNCTION, CLEAR_FUNCTION)
VALUE_FIELDS = (*RAW_FIELDS, "links", "is_candidate", "data_is_object")


def _literal(value):
    return "'" + value.replace("'", "''") + "'"


def projection_values(source):
    """持久化原 JSON 值；未知类型只扩大候选，不在写入链引入转换错误。"""
    data = f"{source}.data"
    pattern = _literal("|".join(re.escape(word) for word in _OFFICIAL_RECEIVABLE_FEE_WORDS))
    candidate = [f"json_typeof({data}) IS DISTINCT FROM 'object'",
                 f"({data}->>'contract_object_id') IS NOT NULL", f"{source}.title ~ {pattern}"]
    for name in TYPE_FIELDS:
        candidate.extend((f"json_typeof({data}->{_literal(name)}) NOT IN ('string', 'null')",
                          f"({data}->>{_literal(name)}) ~ {pattern}"))
    return [*(f"{data}->{_literal(name)}" for name in RAW_FIELDS),
            "json_build_array(" + ",".join(f"{data}->{_literal(name)}" for name in LINK_FIELDS) + ")",
            "COALESCE((" + " OR ".join(candidate) + "), false)",
            f"COALESCE(json_typeof({data}) = 'object', false)"]


def function_bodies(schema):
    table = f"{quoted_identifier(schema)}.{quoted_identifier(TABLE_NAME)}"
    columns = ", ".join(quoted_identifier(name) for name in VALUE_FIELDS)
    updates = ", ".join(f"{quoted_identifier(name)} = EXCLUDED.{quoted_identifier(name)}" for name in VALUE_FIELDS)
    return {
        SYNC_FUNCTION: f"""
        BEGIN
            IF TG_OP = 'DELETE' THEN
                DELETE FROM {table} WHERE record_id = OLD.id;
            ELSIF NEW.module IS DISTINCT FROM 'finance' THEN
                DELETE FROM {table} WHERE record_id = NEW.id;
            ELSE
                INSERT INTO {table} (record_id, {columns})
                VALUES (NEW.id, {', '.join(projection_values('NEW'))})
                ON CONFLICT (record_id) DO UPDATE SET {updates};
            END IF;
            RETURN NULL;
        END;
        """,
        CLEAR_FUNCTION: f"""
        BEGIN
            DELETE FROM {table};
            RETURN NULL;
        END;
        """,
    }


def finance_integrity_sql():
    """缓存命中前也检查同步链，不能只凭业务修订前进就信任失同步的关系池。"""
    expected = [("record_id", "integer", True), *((name, "json", False) for name in RAW_FIELDS),
                ("links", "json", True), ("is_candidate", "boolean", True), ("data_is_object", "boolean", True)]
    attributes = ",".join(f"({_literal(name)},{_literal(kind)},{str(required).lower()})"
                          for name, kind, required in expected)
    checks = []
    for trigger, kind, function in ((SYNC_TRIGGER, 29, SYNC_FUNCTION), (CLEAR_TRIGGER, 32, CLEAR_FUNCTION)):
        body = function_bodies("__OA_SCHEMA__")[function].replace("%", "%%").replace("__OA_SCHEMA__", "%1$s")
        checks.append(f"""EXISTS (
            SELECT 1 FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE t.tgrelid = 'business_records'::regclass AND t.tgname = {_literal(trigger)}
              AND t.tgtype = {kind} AND t.tgenabled = 'A' AND NOT t.tgisinternal
              AND t.tgqual IS NULL AND t.tgattr = ''::int2vector AND t.tgnargs = 0
              AND NOT t.tgdeferrable AND NOT t.tginitdeferred
              AND p.proname = {_literal(function)} AND n.nspname = current_schema() AND p.pronargs = 0
              AND p.prorettype = 'trigger'::regtype AND NOT p.prosecdef
              AND p.proconfig = ARRAY['search_path=pg_catalog']
              AND p.prosrc = format({_literal(body)}, replace(current_schema(), '"', '""')))
        """)
    return f"""
        EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.oid = to_regclass('{TABLE_NAME}') AND n.nspname = current_schema()
              AND c.relkind = 'r' AND c.relpersistence = 'p')
        AND NOT EXISTS (SELECT 1 FROM (VALUES {attributes}) expected(name, kind, required)
            WHERE NOT EXISTS (SELECT 1 FROM pg_attribute a
                WHERE a.attrelid = to_regclass('{TABLE_NAME}') AND a.attname = expected.name
                  AND format_type(a.atttypid, a.atttypmod) = expected.kind
                  AND a.attnotnull = expected.required AND NOT a.attisdropped))
        AND {' AND '.join(checks)}
    """


def validate_dashboard_finance_read_model(connection):
    if connection.dialect.name != "postgresql":
        return
    schema = connection.scalar(text("SELECT current_schema()"))
    table = f"{quoted_identifier(schema)}.{quoted_identifier(TABLE_NAME)}"
    table_oid = connection.scalar(text("SELECT to_regclass(:name)::oid"), {"name": table})
    if table_oid is None:
        raise RuntimeError("控制台费用关系读模型缺失，禁止启动")
    columns = dict(connection.execute(text("""
        SELECT attname, format_type(atttypid, atttypmod) FROM pg_attribute
        WHERE attrelid = :table_oid AND attnum > 0 AND NOT attisdropped
    """), {"table_oid": table_oid}).all())
    expected = {"record_id": "integer", **{name: "json" for name in (*RAW_FIELDS, "links")},
                "is_candidate": "boolean", "data_is_object": "boolean"}
    if columns != expected:
        raise RuntimeError("控制台费用关系列定义不一致，禁止启动")
    if not connection.scalar(text(f"SELECT {finance_integrity_sql()}")):
        raise RuntimeError("控制台费用关系结构或同步触发器不完整，禁止启动")
    if not connection.scalar(text("""
        SELECT EXISTS (SELECT 1 FROM pg_constraint AS c
            JOIN pg_attribute AS a ON a.attrelid = c.conrelid AND a.attname = 'record_id'
            WHERE c.conrelid = :table_oid AND c.contype = 'p' AND c.convalidated
              AND NOT c.condeferrable AND c.conkey = ARRAY[a.attnum]::smallint[])
        AND EXISTS (SELECT 1 FROM pg_constraint AS c
            JOIN pg_attribute AS a ON a.attrelid = c.conrelid AND a.attname = 'record_id'
            JOIN pg_attribute AS b ON b.attrelid = c.confrelid AND b.attname = 'id'
            WHERE c.conrelid = :table_oid AND c.confrelid = 'business_records'::regclass
              AND c.contype = 'f' AND c.convalidated AND NOT c.condeferrable AND c.confdeltype = 'c'
              AND c.conkey = ARRAY[a.attnum]::smallint[] AND c.confkey = ARRAY[b.attnum]::smallint[])
    """), {"table_oid": table_oid}):
        raise RuntimeError("控制台费用关系主外键不完整，禁止启动")
def upgrade_dashboard_finance_read_model(connection):
    if connection.dialect.name != "postgresql":
        return
    connection.execute(text("SET LOCAL lock_timeout = '5s'"))
    connection.execute(text("SET LOCAL statement_timeout = '60s'"))
    # 先锁业务表再建投影，阻止回填与业务写交错；不更新任何业务行。
    connection.execute(text("LOCK TABLE business_records IN SHARE ROW EXCLUSIVE MODE"))
    schema = connection.scalar(text("SELECT current_schema()"))
    qualify = lambda name: f"{quoted_identifier(schema)}.{quoted_identifier(name)}"
    table = qualify(TABLE_NAME)
    if connection.scalar(text("SELECT to_regclass(:name) IS NOT NULL"), {"name": table}):
        validate_dashboard_finance_read_model(connection)
        return
    raw_columns = ", ".join(f"{quoted_identifier(name)} JSON" for name in RAW_FIELDS)
    connection.execute(text(f"""
        CREATE TABLE {table} (
            record_id INTEGER PRIMARY KEY REFERENCES {qualify('business_records')}(id) ON DELETE CASCADE,
            {raw_columns}, links JSON NOT NULL, is_candidate BOOLEAN NOT NULL, data_is_object BOOLEAN NOT NULL)
    """))
    for name, body in function_bodies(schema).items():
        connection.execute(text(f"""CREATE FUNCTION {qualify(name)}() RETURNS trigger
            LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog AS $body${body}$body$"""))
    for name, event, level, function in (
        (SYNC_TRIGGER, "INSERT OR UPDATE OR DELETE", "ROW", SYNC_FUNCTION),
        (CLEAR_TRIGGER, "TRUNCATE", "STATEMENT", CLEAR_FUNCTION),
    ):
        connection.execute(text(f"CREATE TRIGGER {name} AFTER {event} ON {qualify('business_records')} "
                                f"FOR EACH {level} EXECUTE FUNCTION {qualify(function)}()"))
        connection.execute(text(f"ALTER TABLE {qualify('business_records')} ENABLE ALWAYS TRIGGER {name}"))
    columns = ", ".join(quoted_identifier(name) for name in VALUE_FIELDS)
    connection.execute(text(f"INSERT INTO {table} (record_id, {columns}) "
                            f"SELECT source.id, {', '.join(projection_values('source'))} "
                            f"FROM {qualify('business_records')} source WHERE source.module = 'finance'"))
    # 用 JSON 文本逐值核对，不能转 JSONB 丢失大数、重复键或原始表示。
    comparisons = []
    for name, value in zip(VALUE_FIELDS, projection_values('source')):
        suffix = "" if name in ("is_candidate", "data_is_object") else "::text"
        comparisons.append(f"relation.{quoted_identifier(name)}{suffix} IS DISTINCT FROM ({value}){suffix}")
    mismatch = connection.scalar(text(f"""
        SELECT EXISTS (SELECT 1 FROM {qualify('business_records')} source
        FULL JOIN {table} relation ON relation.record_id = source.id
        WHERE (source.module = 'finance' AND (relation.record_id IS NULL OR {' OR '.join(comparisons)}))
           OR (relation.record_id IS NOT NULL AND source.module IS DISTINCT FROM 'finance'))
    """))
    if mismatch:
        raise RuntimeError("控制台费用关系回填校验失败")
    connection.execute(text(f"CREATE INDEX ix_dashboard_finance_candidate ON {table} (is_candidate, record_id)"))
    # 已有修订日志的库需要立即覆盖新投影；新库由后续修订迁移统一安装。
    if connection.scalar(text("SELECT to_regclass(:name) IS NOT NULL"), {"name": qualify(REVISION_TABLE)}):
        for trigger, event, level in ((ROW_TRIGGER, "INSERT OR UPDATE OR DELETE", "ROW"),
                                      (TRUNCATE_TRIGGER, "TRUNCATE", "STATEMENT")):
            connection.execute(text(f"CREATE TRIGGER {trigger} AFTER {event} ON {table} "
                                    f"FOR EACH {level} EXECUTE FUNCTION {qualify(TOUCH_FUNCTION)}()"))
            connection.execute(text(f"ALTER TABLE {table} ENABLE ALWAYS TRIGGER {trigger}"))
    connection.execute(text(f"ANALYZE {table}"))
    validate_dashboard_finance_read_model(connection)
