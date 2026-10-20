"""按既有数据模型的默认值生成批量历史投影；缺少必填映射即阻断。"""

import sys
from pathlib import Path
from psycopg import sql

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api-server"))
from app.models import Base


def string(column):
    return f"COALESCE(s.\"{column}\"::text,'')"


def active(column="IsActived"):
    return f"UPPER(COALESCE(s.\"{column}\"::text,'')) IN ('Y','T','1','TRUE')"


def literal(value):
    if isinstance(value, (dict, list)):
        import json

        return sql.SQL("{}::json").format(sql.Literal(json.dumps(value, ensure_ascii=False)))
    return sql.Literal(value)


def project(db, target, source, mapping, conflict, joins="", where="", update=True):
    table = Base.metadata.tables[target]
    values = {key: sql.SQL(value) for key, value in mapping.items()}
    for column in table.columns:
        if column.name in values or column.primary_key or column.server_default is not None or column.nullable:
            continue
        if column.default is None:
            raise ValueError(f"{target}.{column.name} has no source mapping")
        default = column.default.arg
        if callable(default):
            default = default(None)
        values[column.name] = literal(default)
    statement = sql.SQL("INSERT INTO {} ({}) SELECT {} FROM {} s {} {} ON CONFLICT ({}) {}").format(
        sql.Identifier(target),
        sql.SQL(",").join(map(sql.Identifier, values)),
        sql.SQL(",").join(values.values()),
        sql.Identifier(source),
        sql.SQL(joins),
        sql.SQL("WHERE " + where) if where else sql.SQL(""),
        sql.SQL(",").join(map(sql.Identifier, conflict)),
        sql.SQL("DO UPDATE SET {}").format(
            sql.SQL(",").join(
                sql.SQL("{}=EXCLUDED.{}").format(sql.Identifier(k), sql.Identifier(k))
                for k in values
                if k not in conflict
            )
        )
        if update
        else sql.SQL("DO NOTHING"),
    )
    count = db.execute(statement).rowcount
    db.commit()
    print(f"{source} -> {target}: {count}", flush=True)
    return count


def record_views(db):
    db.execute(
        "CREATE TEMP VIEW hz_records AS SELECT * FROM business_records WHERE data->>'migration_source'='hz_crm_20260930'"
    )


def business_join(module, field, alias="r"):
    return f"LEFT JOIN hz_records {alias} ON {alias}.module='{module}' AND {alias}.serial_no=s.\"{field}\""


def user_join(field, alias="u"):
    return f'LEFT JOIN users {alias} ON {alias}.username=LOWER(s."{field}")'


def state(alias):
    return f"CASE WHEN {alias}.id IS NULL THEN 'source_parent_missing' ELSE 'mapped' END"
