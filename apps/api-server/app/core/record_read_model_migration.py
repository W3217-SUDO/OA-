"""精简查询表与同步触发器同事务安装，不更新原业务数据。"""
from sqlalchemy import text

from app.core.record_read_model import READ_MODEL_FIELDS, record_read_models


def upgrade_record_read_model(connection):
    record_read_models.create(connection, checkfirst=True)
    if connection.dialect.name != "postgresql":
        return
    ready = connection.scalar(text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgrelid = 'business_records'::regclass
                AND tgname = 'business_record_read_model_sync' AND NOT tgisinternal
        )
    """))
    if not ready:
        raise RuntimeError("查询表缺少事务同步触发器，禁止登记升级成功")


def initialize_record_read_model_schema(connection):
    if connection.dialect.name != "postgresql":
        return
    connection.execute(text("SET LOCAL lock_timeout = '5s'"))
    connection.execute(text("SET LOCAL statement_timeout = '60s'"))
    keys = ", ".join("'" + key + "'" for key in sorted(READ_MODEL_FIELDS))
    connection.execute(text(f"""
        CREATE FUNCTION oa_record_read_data(source JSON) RETURNS JSON
        LANGUAGE SQL IMMUTABLE PARALLEL SAFE AS $body$
            SELECT CASE WHEN json_typeof(source) = 'object' THEN (
                SELECT COALESCE(json_object_agg(entry.key, entry.value), '{{}}'::json)
                FROM (
                    SELECT key, value FROM json_each(source)
                    WHERE key IN ({keys})
                    UNION ALL
                    SELECT 'legacy_record', json_build_object('CasePhaseName', value -> 'CasePhaseName')
                    FROM json_each(source) WHERE key = 'legacy_record'
                ) AS entry
            ) ELSE source END
        $body$
    """))
    connection.execute(text("""
        CREATE FUNCTION oa_sync_record_read_model() RETURNS trigger
        LANGUAGE plpgsql AS $body$
        BEGIN
            IF TG_OP = 'UPDATE' AND NEW.data::text IS NOT DISTINCT FROM OLD.data::text THEN
                RETURN NEW;
            END IF;
            INSERT INTO business_record_read_models(record_id, data)
            VALUES (NEW.id, oa_record_read_data(NEW.data))
            ON CONFLICT (record_id) DO UPDATE SET data = EXCLUDED.data;
            RETURN NEW;
        END
        $body$
    """))
    connection.execute(text("""
        CREATE TRIGGER business_record_read_model_sync
        AFTER INSERT OR UPDATE OF data ON business_records
        FOR EACH ROW EXECUTE FUNCTION oa_sync_record_read_model()
    """))
    connection.execute(text("""
        INSERT INTO business_record_read_models(record_id, data)
        SELECT id, oa_record_read_data(data) FROM business_records
    """))
    missing = connection.scalar(text("""
        SELECT count(*) FROM business_records AS source
        LEFT JOIN business_record_read_models AS projected ON projected.record_id = source.id
        WHERE projected.record_id IS NULL
    """))
    if missing:
        raise RuntimeError(f"查询数据初始化不完整，缺少 {missing} 条")
    # 导入库的行数统计也必须更新，避免查询表关联沿用导入前的错误估算。
    connection.execute(text("ANALYZE business_records"))
    connection.execute(text("ANALYZE business_record_read_models"))
