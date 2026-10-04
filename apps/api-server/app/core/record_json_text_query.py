"""集中提取查询所需的 JSON 文本字段，保留原取键和空值语义。"""
from sqlalchemy import JSON, Text, case, cast, column, func, literal, select

from app.models import BusinessRecord
from app.core.record_read_model import record_json_source


def record_json_text_projection(db, keys):
    keys = tuple(dict.fromkeys(keys))
    if not keys:
        raise ValueError("JSON 文本投影至少需要一个字段")
    if db.get_bind().dialect.name != "postgresql":
        return None, {key: BusinessRecord.data[key].as_string() for key in keys}
    # JSON 取键对非对象返回 NULL；空对象让行投影保持相同结果。
    source = record_json_source(db, keys)
    payload = case(
        (func.json_typeof(source) == "object", source),
        else_=cast(literal("{}"), JSON),
    )
    projection = func.json_to_record(payload).table_valued(
        *(column(key, Text) for key in keys),
    ).render_derived(with_types=True)
    return projection, {key: projection.c[key] for key in keys}


def projected_record_condition(projection, condition):
    if projection is None:
        return condition
    return select(condition).select_from(projection).correlate(BusinessRecord).scalar_subquery()
