"""启动时同事务安装追加式控制台修订日志，不更新任何已有业务行。"""
from sqlalchemy import text

from app.core.dashboard_revision import (
    DEPENDENCY_TABLES, IMMUTABLE_FUNCTION, IMMUTABLE_TRIGGER, OWN_FUNCTION, OWN_TRIGGER,
    REVISION_TABLE, ROW_TRIGGER, TOUCH_FUNCTION, TRUNCATE_TRIGGER, function_body,
    integrity_sql, quoted_identifier,
)


def validate_dashboard_revision(connection):
    if connection.dialect.name != "postgresql":
        return
    if not connection.scalar(text(f"SELECT to_regclass('{REVISION_TABLE}') IS NOT NULL")):
        raise RuntimeError("控制台事务修订表缺失，禁止启动")
    if not connection.scalar(text(f"SELECT {integrity_sql()}")):
        raise RuntimeError("控制台事务修订触发器不完整，禁止启动")


def upgrade_dashboard_revision(connection):
    if connection.dialect.name != "postgresql":
        return
    if connection.scalar(text(f"SELECT to_regclass('{REVISION_TABLE}') IS NOT NULL")):
        validate_dashboard_revision(connection)
        return
    connection.execute(text("SET LOCAL lock_timeout = '5s'"))
    connection.execute(text("SET LOCAL statement_timeout = '60s'"))
    schema = connection.scalar(text("SELECT current_schema()"))
    quote = quoted_identifier
    qualified = lambda name: f"{quote(schema)}.{quote(name)}"
    table = qualified(REVISION_TABLE)
    # 本轮不清理日志；后续维护必须更换缓存代际，不能删除旧修订制造 ABA。
    connection.execute(text(f"CREATE TABLE {table} (txid BIGINT PRIMARY KEY CHECK (txid > 0))"))
    for name in (TOUCH_FUNCTION, OWN_FUNCTION, IMMUTABLE_FUNCTION):
        security = "SECURITY DEFINER" if name == TOUCH_FUNCTION else "SECURITY INVOKER"
        connection.execute(text(f"""
            CREATE FUNCTION {qualified(name)}() RETURNS trigger
            LANGUAGE plpgsql {security} SET search_path = pg_catalog
            AS $body${function_body(name, schema)}$body$
        """))
    connection.execute(text(f"""
        CREATE TRIGGER {OWN_TRIGGER} BEFORE INSERT ON {table}
        FOR EACH ROW EXECUTE FUNCTION {qualified(OWN_FUNCTION)}()
    """))
    connection.execute(text(f"""
        CREATE TRIGGER {IMMUTABLE_TRIGGER} BEFORE UPDATE OR DELETE OR TRUNCATE ON {table}
        FOR EACH STATEMENT EXECUTE FUNCTION {qualified(IMMUTABLE_FUNCTION)}()
    """))
    for name in (OWN_TRIGGER, IMMUTABLE_TRIGGER):
        connection.execute(text(f"ALTER TABLE {table} ENABLE ALWAYS TRIGGER {name}"))
    for name in DEPENDENCY_TABLES:
        # 缺依赖表即让本次启动事务失败，不跳过安装或登记成功。
        target = quote(name)
        connection.execute(text(f"""
            CREATE TRIGGER {ROW_TRIGGER} AFTER INSERT OR UPDATE OR DELETE ON {target}
            FOR EACH ROW EXECUTE FUNCTION {qualified(TOUCH_FUNCTION)}()
        """))
        connection.execute(text(f"""
            CREATE TRIGGER {TRUNCATE_TRIGGER} AFTER TRUNCATE ON {target}
            FOR EACH STATEMENT EXECUTE FUNCTION {qualified(TOUCH_FUNCTION)}()
        """))
        for trigger in (ROW_TRIGGER, TRUNCATE_TRIGGER):
            connection.execute(text(f"ALTER TABLE {target} ENABLE ALWAYS TRIGGER {trigger}"))
    validate_dashboard_revision(connection)
