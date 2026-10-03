"""按 JSON 标量预筛选关联候选，避免大批编号生成巨型正则。"""
import json

from sqlalchemy import Boolean, String, false, literal
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import FunctionElement


class _JsonScalarOverlap(FunctionElement):
    type = Boolean()
    inherit_cache = True


@compiles(_JsonScalarOverlap, "postgresql")
def _postgresql_scalar_overlap(element, compiler, **kwargs):
    payload, candidates = (compiler.process(clause, **kwargs) for clause in element.clauses)
    return (
        "EXISTS (SELECT 1 FROM jsonb_path_query("
        f"CAST({payload} AS JSONB), "
        "'strict $.** ? (@.type() == \"number\" || @.type() == \"string\")'"
        ") AS relation_value(value) "
        "WHERE relation_value.value #>> '{}' IN ("
        f"SELECT jsonb_array_elements_text(CAST({candidates} AS JSONB))))"
    )


@compiles(_JsonScalarOverlap, "sqlite")
def _sqlite_scalar_overlap(element, compiler, **kwargs):
    payload, candidates = (compiler.process(clause, **kwargs) for clause in element.clauses)
    return (
        f"EXISTS (SELECT 1 FROM json_tree({payload}) AS relation_value "
        "WHERE relation_value.type IN ('text', 'integer', 'real') "
        "AND CAST(relation_value.atom AS TEXT) IN ("
        f"SELECT CAST(value AS TEXT) FROM json_each({candidates})))"
    )


def json_scalar_overlap(column, values):
    """只预筛选候选，调用方仍按业务关联键精确判断归属。"""
    candidates = sorted({str(value) for value in values})
    if not candidates:
        return false()
    # 候选集使用一个 JSON 参数，参数数量及查询结构不随编号数量膨胀。
    encoded = json.dumps(candidates, ensure_ascii=False, separators=(",", ":"))
    return _JsonScalarOverlap(column, literal(encoded, type_=String))
