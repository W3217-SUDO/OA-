"""只对已获授权的接口结果做组合筛选、投影、分组和统计。"""

from decimal import Decimal, InvalidOperation
import json
import operator

from fastapi import HTTPException

from .source import field_value


def scalar(value):
    if isinstance(value, (dict, list)):
        raise HTTPException(422, "筛选、分组及排序字段必须是标量，请指定具体子字段")
    return value


def available_fields(rows):
    result = set()

    def visit(item, prefix="", depth=0):
        if depth > 6:
            return
        for key, value in item.items():
            path = prefix + str(key)
            if isinstance(value, dict):
                visit(value, path + ".", depth + 1)
            elif not isinstance(value, list):
                result.add(path)
    for row in rows:
        visit(row)
    return result


def matches(row, condition):
    value, target = scalar(field_value(row, condition.field)), condition.value
    if condition.op in {"is_null", "not_null"}:
        return (value is None) == (condition.op == "is_null")
    if condition.op in {"in", "not_in"}:
        if not isinstance(target, list) or len(target) > 100 or any(isinstance(x, (dict, list)) for x in target):
            raise HTTPException(422, "集合筛选值必须是不超过100项的标量数组")
        return (value in target) == (condition.op == "in")
    scalar(target)
    if condition.op in {"contains", "starts_with"}:
        if not isinstance(target, str):
            raise HTTPException(422, "文字筛选值必须是字符串")
        return isinstance(value, str) and (target.casefold() in value.casefold() if condition.op == "contains"
                                          else value.casefold().startswith(target.casefold()))
    if condition.op in {"eq", "ne"}:
        return (value == target) == (condition.op == "eq")
    if value is None or target is None:
        return False
    if isinstance(value, bool) or isinstance(target, bool) or (
        not (isinstance(value, (int, float)) and isinstance(target, (int, float))) and type(value) is not type(target)
    ):
        raise HTTPException(422, "比较字段和值类型不一致；日期请使用原接口格式")
    return {"gt": operator.gt, "gte": operator.ge, "lt": operator.lt, "lte": operator.le}[condition.op](value, target)


def metric_value(rows, metric):
    values = [scalar(field_value(row, metric.field)) for row in rows] if metric.field else rows
    values = [value for value in values if value is not None]
    if metric.op == "count":
        return len(values)
    if not values:
        return None
    try:
        if any(isinstance(value, bool) for value in values):
            raise InvalidOperation
        numbers = [Decimal(str(value)) for value in values]
        if any(not value.is_finite() for value in numbers):
            raise InvalidOperation
    except InvalidOperation as exc:
        raise HTTPException(422, "数值统计字段含非数值，未跳过或按零处理") from exc
    value = {"sum": lambda: sum(numbers), "avg": lambda: sum(numbers) / len(numbers),
             "min": lambda: min(numbers), "max": lambda: max(numbers)}[metric.op]()
    return str(value)


def transform(rows, body):
    available = available_fields(rows)
    requested = [*body.fields, *body.group_by, *[x.field for x in body.where], *[x.field for x in body.metrics if x.field]]
    if rows and set(requested) - available:
        raise HTTPException(422, "查询字段不存在于当前账号可见结果：" + "、".join(sorted(set(requested) - available)))
    selected = [row for row in rows if not body.where or (all if body.match == "all" else any)(matches(row, x) for x in body.where)]
    filtered = len(selected)
    if body.group_by or body.metrics:
        groups = {}
        for row in selected:
            values = {field: scalar(field_value(row, field)) for field in body.group_by}
            key = json.dumps(values, sort_keys=True, ensure_ascii=False)
            groups.setdefault(key, (values, []))[1].append(row)
        if not body.group_by and not selected:
            groups["{}"] = ({}, [])
        selected = [{**values, **{metric.name: metric_value(members, metric) for metric in body.metrics}}
                    for values, members in groups.values()]
        sort_fields = {*body.group_by, *[metric.name for metric in body.metrics]}
    else:
        sort_fields = available
    for order in reversed(body.order_by):
        if rows and order.field not in sort_fields:
            raise HTTPException(422, "排序字段必须是当前可见明细字段或统计结果字段")
        numeric = any(x.name == order.field and x.op != "count" for x in body.metrics)

        def key(row):
            value = row.get(order.field) if body.metrics or body.group_by else field_value(row, order.field)
            scalar(value)
            if numeric and value is not None:
                value = Decimal(value)
            # 异类字段保持确定顺序；数值相互比较，不以文字顺序排列金额。
            kind = "number" if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool) else type(value).__name__
            return value is None, kind, value
        selected.sort(key=key, reverse=order.direction == "desc")
    total = len(selected)
    selected = selected[body.offset:body.offset + body.limit]
    if body.fields:
        selected = [{name: field_value(row, name) for name in body.fields} for row in selected]
    return {"items": selected, "total": total, "filtered_source_rows": filtered,
            "offset": body.offset, "limit": body.limit, "available_fields": sorted(available)}
