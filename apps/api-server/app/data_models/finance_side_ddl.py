"""财务旁表的建表、触发器和回填语句（11-07 慢查询 A3），启动修订、建表钩子和一致性检查共用一份。

- legacy_ar_payment_fields：legacy_finance_records 里 FAM_AR_Payment 行的 source_payload 拆出的字段；
- incoming_allocation_items：incoming_payments.allocations 展开的（到账单、费用、金额）明细。

两张表只是派生数据，由来源表上的触发器维护，应用和同步程序都不直接写；原 JSON 不动。
"""
from sqlalchemy import text

LEGACY_COLUMNS = "record_id, legacy_id, is_active, payment_id, group_id, payment_method, settlement_status, source_database"
LEGACY_EXPECTED = """
    SELECT id AS record_id, legacy_id, is_active, source_payload->>'PaymentId' AS payment_id,
           source_payload->>'GroupId' AS group_id, source_payload->>'PaymentModeName' AS payment_method,
           source_payload->>'SettlementStatus' AS settlement_status, source_payload->>'_source_database' AS source_database
    FROM legacy_finance_records WHERE source_table = 'FAM_AR_Payment'
"""
_ALLOCATION_ROWS = r"""
    SELECT coalesce(nullif(s->>'fee_record_id', ''), nullif(s->>'finance_record_id', ''),
                    nullif(s->>'fee_id', ''), nullif(s->>'case_fee_id', '')) AS fid, s->>'amount' AS amt
    FROM json_array_elements(CASE WHEN json_typeof({allocations}) = 'array' THEN {allocations} ELSE '[]'::json END) a
    CROSS JOIN LATERAL json_array_elements(
        CASE WHEN json_typeof(a->'settlement_items') = 'array' AND json_array_length(a->'settlement_items') > 0
             THEN a->'settlement_items' ELSE json_build_array(a) END) s
"""
ALLOCATION_EXPECTED = f"""
    SELECT ip.id AS incoming_payment_id, x.fid::bigint AS fee_id, x.amt
    FROM incoming_payments ip CROSS JOIN LATERAL ({_ALLOCATION_ROWS.format(allocations="ip.allocations")}) x
    WHERE x.fid ~ '^[0-9]{{1,18}}$'
"""

POSTGRES_INSTALL = (
    """CREATE TABLE IF NOT EXISTS legacy_ar_payment_fields (
        record_id integer PRIMARY KEY, legacy_id varchar(128) NOT NULL DEFAULT '', is_active boolean NOT NULL DEFAULT true,
        payment_id varchar(128), group_id varchar(64), payment_method varchar(128), settlement_status varchar(64), source_database varchar(128))""",
    f"""CREATE OR REPLACE FUNCTION oa_legacy_ar_payment_fields_sync() RETURNS trigger LANGUAGE plpgsql AS $f$
    BEGIN
      IF TG_OP <> 'INSERT' THEN DELETE FROM legacy_ar_payment_fields WHERE record_id = OLD.id; END IF;
      IF TG_OP <> 'DELETE' AND NEW.source_table = 'FAM_AR_Payment' THEN
        INSERT INTO legacy_ar_payment_fields ({LEGACY_COLUMNS}) VALUES (NEW.id, NEW.legacy_id, NEW.is_active,
          NEW.source_payload->>'PaymentId', NEW.source_payload->>'GroupId', NEW.source_payload->>'PaymentModeName',
          NEW.source_payload->>'SettlementStatus', NEW.source_payload->>'_source_database');
      END IF;
      RETURN NULL;
    END $f$""",
    "DROP TRIGGER IF EXISTS oa_legacy_ar_payment_fields ON legacy_finance_records",
    """CREATE TRIGGER oa_legacy_ar_payment_fields AFTER INSERT OR UPDATE OF source_table, legacy_id, is_active, source_payload OR DELETE
       ON legacy_finance_records FOR EACH ROW EXECUTE FUNCTION oa_legacy_ar_payment_fields_sync()""",
    "CREATE TABLE IF NOT EXISTS incoming_allocation_items (id bigserial PRIMARY KEY, incoming_payment_id integer NOT NULL, fee_id bigint, amt text)",
    "CREATE INDEX IF NOT EXISTS ix_incoming_allocation_items_payment ON incoming_allocation_items (incoming_payment_id)",
    "CREATE INDEX IF NOT EXISTS ix_incoming_allocation_items_fee ON incoming_allocation_items (fee_id)",
    f"""CREATE OR REPLACE FUNCTION oa_incoming_allocation_items_sync() RETURNS trigger LANGUAGE plpgsql AS $f$
    BEGIN
      IF TG_OP <> 'INSERT' THEN DELETE FROM incoming_allocation_items WHERE incoming_payment_id = OLD.id; END IF;
      IF TG_OP <> 'DELETE' THEN
        INSERT INTO incoming_allocation_items (incoming_payment_id, fee_id, amt)
        SELECT NEW.id, x.fid::bigint, x.amt FROM ({_ALLOCATION_ROWS.format(allocations="NEW.allocations")}) x
        WHERE x.fid ~ '^[0-9]{{1,18}}$';
      END IF;
      RETURN NULL;
    END $f$""",
    "DROP TRIGGER IF EXISTS oa_incoming_allocation_items ON incoming_payments",
    """CREATE TRIGGER oa_incoming_allocation_items AFTER INSERT OR UPDATE OF allocations OR DELETE ON incoming_payments
       FOR EACH ROW EXECUTE FUNCTION oa_incoming_allocation_items_sync()""",
)
POSTGRES_BACKFILL = (
    "DELETE FROM legacy_ar_payment_fields",
    f"INSERT INTO legacy_ar_payment_fields ({LEGACY_COLUMNS}) {LEGACY_EXPECTED}",
    "DELETE FROM incoming_allocation_items",
    f"INSERT INTO incoming_allocation_items (incoming_payment_id, fee_id, amt) {ALLOCATION_EXPECTED}",
)

# SQLite（测试库）只用到 legacy_ar_payment_fields：费用到账汇总在 SQLite 上走 Python，不读 incoming_allocation_items。
_SQLITE_LEGACY_ROW = f"""INSERT OR REPLACE INTO legacy_ar_payment_fields ({LEGACY_COLUMNS})
    SELECT NEW.id, NEW.legacy_id, NEW.is_active, json_extract(NEW.source_payload, '$.PaymentId'),
        json_extract(NEW.source_payload, '$.GroupId'), json_extract(NEW.source_payload, '$.PaymentModeName'),
        json_extract(NEW.source_payload, '$.SettlementStatus'), json_extract(NEW.source_payload, '$._source_database')
    WHERE NEW.source_table = 'FAM_AR_Payment';"""
SQLITE_INSTALL = (
    f"CREATE TRIGGER IF NOT EXISTS oa_legacy_ar_payment_fields_ins AFTER INSERT ON legacy_finance_records BEGIN {_SQLITE_LEGACY_ROW} END",
    "CREATE TRIGGER IF NOT EXISTS oa_legacy_ar_payment_fields_upd AFTER UPDATE ON legacy_finance_records BEGIN "
    f"DELETE FROM legacy_ar_payment_fields WHERE record_id = OLD.id; {_SQLITE_LEGACY_ROW} END",
    "CREATE TRIGGER IF NOT EXISTS oa_legacy_ar_payment_fields_del AFTER DELETE ON legacy_finance_records BEGIN "
    "DELETE FROM legacy_ar_payment_fields WHERE record_id = OLD.id; END",
)


def install_after_create(target, connection, **kw) -> None:
    """建表钩子：来源表和旁表这次刚建好时装触发器（新库、测试库）。生产已有的库由启动修订安装并回填。"""
    created = {table.name for table in kw.get("tables") or ()}
    if "legacy_finance_records" not in created and "incoming_payments" not in created:
        return
    dialect = connection.dialect.name
    if dialect == "sqlite":
        if {"legacy_finance_records", "legacy_ar_payment_fields"} <= _existing_tables(connection, dialect):
            for statement in SQLITE_INSTALL:
                connection.execute(text(statement))
    elif dialect == "postgresql":
        if {"legacy_finance_records", "incoming_payments"} <= _existing_tables(connection, dialect):
            for statement in POSTGRES_INSTALL:
                connection.execute(text(statement))


def _existing_tables(connection, dialect: str) -> set[str]:
    from sqlalchemy import inspect
    return set(inspect(connection).get_table_names())
