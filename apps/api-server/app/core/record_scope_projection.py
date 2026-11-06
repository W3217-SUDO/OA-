"""数据范围条件每行只解析一次 JSON。

data 是 json 列，每个 data ->> 'key' 都要重新解析整份 JSON；数据范围条件有二三十个这样的键，非全所账号查询时每行解析几十遍
（11-06 压测：这类查询占工作台重算的大部分 CPU）。这里把条件里取本表 JSON 文本的部分换成从同一行一次解析的结果读取，
比较逻辑一个字不改；别名表（如客户子查询）和嵌套路径保持原样。
"""
from sqlalchemy.sql import operators, visitors
from sqlalchemy.sql.elements import BinaryExpression, BindParameter
from sqlalchemy.sql.selectable import Alias
from sqlalchemy.sql.type_api import TypeEngine  # noqa: F401
from sqlalchemy import String, cast

from app.core.record_json_text_query import projected_record_condition, record_json_text_projection
from app.models import BusinessRecord


def _json_text_key(element):
    """本表 data ->> 'key' 返回 key，其余返回 None。"""
    if not isinstance(element, BinaryExpression) or element.operator is not operators.json_getitem_op:
        return None
    left, right = element.left, element.right
    table = getattr(left, "table", None)
    if getattr(left, "key", None) != "data" or isinstance(table, Alias) or getattr(table, "name", None) != BusinessRecord.__tablename__:
        return None
    if not isinstance(right, BindParameter) or not isinstance(right.value, str) or not isinstance(element.type, String):
        return None
    return right.value


def single_parse_condition(condition, db):
    keys = []

    def collect(element):
        key = _json_text_key(element)
        if key is not None:
            keys.append(key)

    visitors.traverse(condition, {}, {"binary": collect})
    if len(set(keys)) < 2:
        return condition
    projection, data = record_json_text_projection(db, keys)
    if projection is None:
        return condition

    def replace(element, **_kwargs):
        key = _json_text_key(element)
        return None if key is None else cast(data[key], String)

    return projected_record_condition(projection, visitors.replacement_traverse(condition, {}, replace))
