"""逻辑删除升级：业务表补 deleted_at/deleted_by 列；唯一约束/唯一索引换成只对未删除行生效的部分唯一索引。幂等。"""

from sqlalchemy import inspect, text

MIGRATION_REVISION = "soft_delete_v1"


def _partial(index: dict) -> bool:
    options = index.get("dialect_options") or {}
    return options.get("postgresql_where") is not None or options.get("sqlite_where") is not None  # SQLite 返回的是 SQL 表达式，不能直接转布尔


def upgrade_soft_delete(connection) -> None:
    from app.core import soft_delete

    quote = connection.dialect.identifier_preparer.quote
    postgres = connection.dialect.name == "postgresql"
    inspector = inspect(connection)
    for name in soft_delete.soft_tables():
        if not inspector.has_table(name):
            continue
        existing = {column["name"] for column in inspector.get_columns(name)}
        if "deleted_at" not in existing:
            connection.execute(text(f"ALTER TABLE {quote(name)} ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE NULL"))
        if "deleted_by" not in existing:
            connection.execute(text(f"ALTER TABLE {quote(name)} ADD COLUMN deleted_by VARCHAR(64) NULL"))

    for name in soft_delete.soft_tables():
        if inspector.has_table(name):
            connection.execute(text(
                f"CREATE INDEX IF NOT EXISTS {quote(f'ix_{name}_deleted_at')} ON {quote(name)} (deleted_at) WHERE deleted_at IS NOT NULL"))
    inspector = inspect(connection)
    specs: dict[str, list[tuple[str, tuple[str, ...]]]] = {}
    for table, index_name, columns in soft_delete.partial_unique_index_specs():
        specs.setdefault(table, []).append((index_name, tuple(columns)))
    inspector = inspect(connection)  # 重新读取，拿到刚加的列
    for table, wanted in specs.items():
        if not inspector.has_table(table):
            continue
        constraints = inspector.get_unique_constraints(table)
        indexes = inspector.get_indexes(table)
        for index_name, columns in wanted:
            if any(ix["name"] == index_name and _partial(ix) for ix in indexes):
                continue
            if postgres:
                # 原来的全表唯一约束/唯一索引（同一组列）先删掉，再建部分唯一索引。
                for constraint in constraints:
                    if tuple(constraint["column_names"]) == columns:
                        connection.execute(text(f"ALTER TABLE {quote(table)} DROP CONSTRAINT {quote(constraint['name'])}"))
                for ix in indexes:
                    if ix.get("unique") and tuple(ix["column_names"]) == columns and not _partial(ix) and not ix.get("duplicates_constraint"):
                        connection.execute(text(f"DROP INDEX {quote(ix['name'])}"))
                connection.execute(text(
                    f"CREATE UNIQUE INDEX IF NOT EXISTS {quote(index_name)} ON {quote(table)} ({', '.join(quote(c) for c in columns)}) "
                    "WHERE deleted_at IS NULL"))
            # SQLite 只用于测试/开发，库是 create_all 新建的；已存在的旧库不改约束。
