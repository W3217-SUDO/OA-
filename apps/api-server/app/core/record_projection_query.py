"""只读业务投影：在 SQL 层选择所需字段，不加载完整历史快照。"""
from types import SimpleNamespace

from sqlalchemy import JSON, column, func, literal, select, type_coerce
from sqlalchemy.dialects.postgresql import JSONB

from app.models import BusinessRecord


def _postgresql_projection_data(data_fields):
    if not data_fields:
        return literal({}, type_=JSON)
    # 直接声明所需字段，避免逐条展开未使用的历史快照并进行哈希连接、聚合。
    # JSONB 字段保留原投影对选中值的类型转换；嵌套空值不能被递归删除。
    projection = func.json_to_record(BusinessRecord.data).table_valued(
        *(column(key, JSONB) for key in data_fields),
    ).render_derived(with_types=True)
    return select(type_coerce(func.row_to_json(projection.table_valued()), JSON)).select_from(
        projection,
    ).correlate(BusinessRecord).scalar_subquery()


async def read_record_projections(db, conditions, data_fields, *, legacy_fields=()):
    columns = ("id", "module", "serial_no", "title", "customer", "status", "owner",
               "department", "description", "created_at", "updated_at")
    data_fields = tuple(dict.fromkeys(data_fields))
    legacy_fields = tuple(dict.fromkeys(legacy_fields))
    grouped_data = db.get_bind().dialect.name == "postgresql"
    data_columns = (_postgresql_projection_data(data_fields),) if grouped_data else tuple(
        BusinessRecord.data[key] for key in data_fields
    )
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
