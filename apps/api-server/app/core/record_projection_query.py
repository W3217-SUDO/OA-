"""只读业务投影：在 SQL 层选择所需字段，不加载完整历史快照。"""
from types import SimpleNamespace

from sqlalchemy import JSON, column, func, select, true
from sqlalchemy.dialects.postgresql import JSONB

from app.models import BusinessRecord


def _postgresql_record_projection(data_fields, legacy_fields):
    fields = [column(key, JSONB) for key in data_fields]
    if legacy_fields and "legacy_record" not in data_fields:
        fields.append(column("legacy_record", JSON))
    # 同一行只解压、解析一次原始 JSON，历史字段从已提取的对象读取。
    return func.json_to_record(BusinessRecord.data).table_valued(
        *fields,
    ).render_derived(with_types=True).lateral()


async def read_record_projections(db, conditions, data_fields, *, legacy_fields=()):
    columns = ("id", "module", "serial_no", "title", "customer", "status", "owner",
               "department", "description", "created_at", "updated_at")
    data_fields = tuple(dict.fromkeys(data_fields))
    legacy_fields = tuple(dict.fromkeys(legacy_fields))
    projection = _postgresql_record_projection(data_fields, legacy_fields) if (
        data_fields and db.get_bind().dialect.name == "postgresql"
    ) else None
    data_columns = tuple(projection.c[key] if projection is not None else BusinessRecord.data[key]
                         for key in data_fields)
    legacy_data = projection.c.legacy_record if projection is not None and legacy_fields else BusinessRecord.data["legacy_record"]
    query = select(
        *(getattr(BusinessRecord, key) for key in columns),
        *data_columns,
        *(legacy_data[key] for key in legacy_fields),
    ).select_from(BusinessRecord)
    if projection is not None:
        query = query.join(projection, true())
    query = query.where(*conditions).execution_options(yield_per=256)
    result = await db.stream(query)
    records = []
    try:
        async for values in result:
            data_end = len(columns) + len(data_columns)
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
