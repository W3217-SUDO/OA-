"""只读业务投影：在 SQL 层选择所需字段，不加载完整历史快照。"""
from types import SimpleNamespace

from sqlalchemy import JSON, Text, column, func, select, true

from app.models import BusinessRecord
from app.core.record_read_model import record_read_models, uses_record_read_model


def _postgresql_record_projection(data_fields, legacy_fields, text_fields=(), *, source=None):
    fields = [column(key, JSON) for key in data_fields]
    fields.extend(column(key, Text) for key in text_fields)
    if legacy_fields and "legacy_record" not in data_fields:
        fields.append(column("legacy_record", JSON))
    # 同一行只解压、解析一次原始 JSON，历史字段从已提取的对象读取。
    return func.json_to_record(BusinessRecord.data if source is None else source).table_valued(
        *fields,
    ).render_derived(with_types=True).lateral()


async def read_record_projections(db, conditions, data_fields, *, legacy_fields=(), text_fields=(), annotations=None,
                                  where_data=None):
    columns = ("id", "module", "serial_no", "title", "customer", "status", "owner",
               "department", "description", "created_at", "updated_at")
    data_fields = tuple(dict.fromkeys(data_fields))
    legacy_fields = tuple(dict.fromkeys(legacy_fields))
    text_fields = tuple(dict.fromkeys(text_fields))
    if set(text_fields) & (set(data_fields) | ({"legacy_record"} if legacy_fields else set())):
        raise ValueError("JSON 与文本投影字段不能重名")
    read_model = uses_record_read_model(db, (*data_fields, *text_fields), legacy_fields)
    source = record_read_models.c.data if read_model else BusinessRecord.data
    projection = _postgresql_record_projection(data_fields, legacy_fields, text_fields, source=source) if (
        data_fields and db.get_bind().dialect.name == "postgresql"
        and (not read_model or where_data is not None or annotations is not None)
    ) else None
    if read_model:
        # 查询表已是精简 JSON，直接读取，避免重新组装所有空字段和文本权限字段。
        data_columns = (source,)
    elif projection is not None:
        # 一条记录只解码一次 JSON，保留嵌套空值，不对业务对象递归删键。
        data_columns = (func.row_to_json(projection.table_valued(), type_=JSON),)
    else:
        data_columns = tuple(BusinessRecord.data[key] for key in data_fields)
    legacy_data = projection.c.legacy_record if projection is not None and legacy_fields else source["legacy_record"]
    extra = await annotations({
        key: projection.c[key] if projection is not None else BusinessRecord.data[key].as_string()
        for key in text_fields
    }) if annotations is not None else {}
    if set(extra) & {*columns, "data"}:
        raise ValueError("查询标记不能覆盖业务记录字段")
    query = select(
        *(getattr(BusinessRecord, key) for key in columns),
        *data_columns,
        *(legacy_data[key] for key in legacy_fields),
        *(value.label(key) for key, value in extra.items()),
    ).select_from(BusinessRecord)
    if read_model:
        query = query.join(record_read_models, record_read_models.c.record_id == BusinessRecord.id)
    if projection is not None:
        query = query.join(projection, true())
    if where_data is not None:
        # 空路径保留原 JSON 取键的文本、数字及空值语义，筛选不再重读整份历史 JSON。
        query = query.where(*where_data({
            key: projection.c[key][()] if projection is not None else BusinessRecord.data[key]
            for key in data_fields
        }))
    query = query.where(*conditions).execution_options(yield_per=256)
    result = await db.stream(query)
    records = []
    try:
        # 按既有有界批量消费游标，避免每一行都切换异步调度上下文。
        async for batch in result.partitions():
            for values in batch:
                data_end = len(columns) + len(data_columns)
                projected = values[len(columns)] if read_model or projection is not None else dict(
                    zip(data_fields, values[len(columns):data_end]),
                )
                data = {key: projected[key] for key in data_fields if projected.get(key) is not None}
                legacy_end = data_end + len(legacy_fields)
                legacy = {key: value for key, value in zip(legacy_fields, values[data_end:legacy_end])
                          if value is not None}
                if legacy:
                    data["legacy_record"] = legacy
                # 不加入 ORM 会话，避免轻量读取覆盖完整业务数据。
                records.append(SimpleNamespace(**dict(zip(columns, values[:len(columns)])), data=data,
                                               **dict(zip(extra, values[legacy_end:]))))
    finally:
        await result.close()
    return records
