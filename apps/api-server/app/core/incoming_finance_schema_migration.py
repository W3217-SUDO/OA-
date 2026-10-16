"""双财务中心回款字段的独立增量结构，不执行历史数据修正。"""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection


MIGRATION_REVISION = "incoming_finance_centers_v1"


def _source_foreign_keys(connection):
    if connection.dialect.name == "sqlite":
        # SQLite 的内联 REFERENCES 删除规则须从结构元数据直接读取。
        return [{"referred_table": row["table"], "referred_columns": [row["to"]],
                 "options": {"ondelete": row["on_delete"]}}
                for row in connection.execute(text("PRAGMA foreign_key_list(incoming_payments)")).mappings()
                if row["from"] == "legacy_finance_record_id"]
    return [item for item in inspect(connection).get_foreign_keys("incoming_payments")
            if item["constrained_columns"] == ["legacy_finance_record_id"]]


def upgrade_incoming_finance_schema(connection: Connection) -> None:
    columns = {item["name"]: item for item in inspect(connection).get_columns("incoming_payments")}
    for name, definition in (
        ("finance_scope", "VARCHAR(16)"),
        ("legacy_finance_record_id", "INTEGER REFERENCES legacy_finance_records(id) ON DELETE RESTRICT"),
        ("payment_method", "VARCHAR(100) NOT NULL DEFAULT ''"),
        ("local_allocation_summary", "JSON"),
    ):
        if name not in columns:
            connection.execute(text(f"ALTER TABLE incoming_payments ADD COLUMN {name} {definition}"))
    references = _source_foreign_keys(connection)
    if not references:
        if connection.dialect.name != "postgresql":
            raise RuntimeError("回款来源外键缺失，请核对既有结构，不能静默忽略")
        connection.execute(text("ALTER TABLE incoming_payments ADD CONSTRAINT fk_incoming_payment_legacy_source "
                                "FOREIGN KEY (legacy_finance_record_id) REFERENCES legacy_finance_records(id) ON DELETE RESTRICT"))
    elif (len(references) != 1 or references[0]["referred_table"] != "legacy_finance_records"
          or references[0]["referred_columns"] != ["id"]
          or references[0].get("options", {}).get("ondelete", "").upper() != "RESTRICT"):
        raise RuntimeError("回款来源外键定义不一致，请核对既有结构")
    if "payment_method" in columns and columns["payment_method"].get("default") is None:
        if connection.dialect.name == "postgresql":
            connection.execute(text("ALTER TABLE incoming_payments ALTER COLUMN payment_method SET DEFAULT ''"))
    for name in ("finance_scope", "legacy_finance_record_id"):
        connection.execute(text(f"CREATE INDEX IF NOT EXISTS ix_incoming_payments_{name} ON incoming_payments ({name})"))
