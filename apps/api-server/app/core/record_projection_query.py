"""只读业务投影：在 SQL 层选择所需字段，不加载完整历史快照。"""
import json
from types import SimpleNamespace

from sqlalchemy import JSON, String, literal, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import FunctionElement

from app.models import BusinessRecord


class _RecordProjectionData(FunctionElement):
    type = JSON()
    inherit_cache = True


@compiles(_RecordProjectionData, "postgresql")
def _postgresql_projection_data(element, compiler, **kwargs):
    payload, keys = (compiler.process(clause, **kwargs) for clause in element.clauses)
    # 一次解析 JSON 后挑选字段，避免逐字段重复解析同一大块历史数据。
    return (
        "(SELECT COALESCE(jsonb_object_agg(projection_entry.key, projection_entry.value), '{}'::jsonb) "
        f"FROM jsonb_each(CAST({payload} AS JSONB)) AS projection_entry(key, value) "
        "WHERE projection_entry.key IN ("
        f"SELECT jsonb_array_elements_text(CAST({keys} AS JSONB))))"
    )


async def read_record_projections(db, conditions, data_fields, *, legacy_fields=()):
    columns = ("id", "module", "serial_no", "title", "customer", "status", "owner",
               "department", "description", "created_at", "updated_at")
    data_fields = tuple(dict.fromkeys(data_fields))
    legacy_fields = tuple(dict.fromkeys(legacy_fields))
    grouped_data = db.get_bind().dialect.name == "postgresql"
    data_columns = (_RecordProjectionData(
        BusinessRecord.data, literal(json.dumps(data_fields), type_=String),
    ),) if grouped_data else tuple(BusinessRecord.data[key] for key in data_fields)
    query = select(
        *(getattr(BusinessRecord, key) for key in columns),
        *data_columns,
        *(BusinessRecord.data["legacy_record"][key] for key in legacy_fields),
    ).where(*conditions).execution_options(yield_per=256)
    result = await db.stream(query)
    records = []
    try:
        async for values in result:
            data_end = len(columns) + len(data_columns)
            if grouped_data:
                data = {key: value for key, value in (values[len(columns)] or {}).items() if value is not None}
            else:
                data = {key: value for key, value in zip(data_fields, values[len(columns):data_end])
                        if value is not None}
            legacy = {key: value for key, value in zip(legacy_fields, values[data_end:])
                      if value is not None}
            if legacy:
                data["legacy_record"] = legacy
            # 不加入 ORM 会话，避免轻量读取覆盖完整业务数据。
            records.append(SimpleNamespace(**dict(zip(columns, values[:len(columns)])), data=data))
    finally:
        await result.close()
    return records
