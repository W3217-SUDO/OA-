"""当事人独立表：建表、回填，并用触发器让它随客户记录同步。"""
from sqlalchemy import text

from app.data_models.parties import Party

MIGRATION_REVISION = "party_table_v1"

_COLUMNS = "id, serial_no, name, party_type, status, owner, department, description, data, created_at, updated_at"
_NOT_CUSTOMER = "COALESCE(NEW.data->>'customer_type', '客户') <> '客户'"


def upgrade_party_table(connection):
    Party.__table__.create(connection, checkfirst=True)
    if connection.dialect.name != "postgresql":
        return
    connection.execute(text(f"""
        CREATE OR REPLACE FUNCTION oa_sync_party() RETURNS trigger
        LANGUAGE plpgsql AS $body$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                DELETE FROM parties WHERE id = OLD.id;
                RETURN OLD;
            END IF;
            IF {_NOT_CUSTOMER} THEN
                INSERT INTO parties ({_COLUMNS})
                VALUES (NEW.id, NEW.serial_no, NEW.title, COALESCE(NEW.data->>'customer_type', ''), NEW.status,
                        NEW.owner, NEW.department, NEW.description, NEW.data, NEW.created_at, NEW.updated_at)
                ON CONFLICT (id) DO UPDATE SET
                    serial_no = EXCLUDED.serial_no, name = EXCLUDED.name, party_type = EXCLUDED.party_type,
                    status = EXCLUDED.status, owner = EXCLUDED.owner, department = EXCLUDED.department,
                    description = EXCLUDED.description, data = EXCLUDED.data,
                    created_at = EXCLUDED.created_at, updated_at = EXCLUDED.updated_at;
            ELSE
                DELETE FROM parties WHERE id = NEW.id;
            END IF;
            RETURN NEW;
        END
        $body$
    """))
    connection.execute(text("DROP TRIGGER IF EXISTS oa_party_sync ON business_records"))
    connection.execute(text("""
        CREATE TRIGGER oa_party_sync AFTER INSERT OR UPDATE ON business_records
        FOR EACH ROW WHEN (NEW.module = 'customer') EXECUTE FUNCTION oa_sync_party()
    """))
    connection.execute(text("DROP TRIGGER IF EXISTS oa_party_sync_delete ON business_records"))
    connection.execute(text("""
        CREATE TRIGGER oa_party_sync_delete AFTER DELETE ON business_records
        FOR EACH ROW WHEN (OLD.module = 'customer') EXECUTE FUNCTION oa_sync_party()
    """))
    connection.execute(text(f"""
        INSERT INTO parties ({_COLUMNS})
        SELECT id, serial_no, title, COALESCE(data->>'customer_type', ''), status, owner, department,
               description, data, created_at, updated_at
        FROM business_records
        WHERE module = 'customer' AND COALESCE(data->>'customer_type', '客户') <> '客户'
        ON CONFLICT (id) DO NOTHING
    """))
    # 迁移前后条数必须一致，否则回滚升级。
    expected = connection.scalar(text(
        "SELECT count(*) FROM business_records WHERE module = 'customer' "
        "AND COALESCE(data->>'customer_type', '客户') <> '客户'"))
    actual = connection.scalar(text("SELECT count(*) FROM parties"))
    if expected != actual:
        raise RuntimeError(f"当事人表回填条数不一致：源 {expected}，当事人表 {actual}")
