"""只读业务投影：在 SQL 层选择所需字段，不加载完整历史快照。"""
from types import SimpleNamespace

from sqlalchemy import select

from app.models import BusinessRecord


async def read_record_projections(db, conditions, data_fields, *, legacy_fields=()):
    columns = ("id", "module", "serial_no", "title", "customer", "status", "owner",
               "department", "description", "created_at", "updated_at")
    data_fields = tuple(dict.fromkeys(data_fields))
    legacy_fields = tuple(dict.fromkeys(legacy_fields))
    query = select(
        *(getattr(BusinessRecord, key) for key in columns),
        *(BusinessRecord.data[key] for key in data_fields),
        *(BusinessRecord.data["legacy_record"][key] for key in legacy_fields),
    ).where(*conditions).execution_options(yield_per=256)
    result = await db.stream(query)
    records = []
    try:
        async for values in result:
            data_end = len(columns) + len(data_fields)
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
