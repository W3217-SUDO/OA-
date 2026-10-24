"""按 JSON 标量预筛选关联候选，避免大批编号生成巨型正则。"""
import json
import re

from sqlalchemy import Boolean, Integer, String, Text, and_, cast, false, literal
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


# 文本预检只用于少量纯 ASCII 候选：这类值在 JSON 原文里不会被转义，标量等于候选时原文必然含该子串。
_TEXT_PRECHECK_CANDIDATE = re.compile(r"[0-9A-Za-z_-]+")
TEXT_PRECHECK_MAX_CANDIDATES = 200


def json_scalar_overlap(column, values):
    """只预筛选候选，调用方仍按业务关联键精确判断归属。"""
    candidates = sorted({str(value) for value in values})
    if not candidates:
        return false()
    # 候选集使用一个 JSON 参数，参数数量及查询结构不随编号数量膨胀。
    encoded = json.dumps(candidates, ensure_ascii=False, separators=(",", ":"))
    overlap = _JsonScalarOverlap(column, literal(encoded, type_=String))
    precheck = json_text_precheck(column, candidates)
    # 先在原文上做子串预检（必要条件），只对可能命中的行转 JSONB 逐值精确比较，结果不变。
    return overlap if precheck is None else and_(precheck, overlap)


def json_text_precheck(column, values):
    """原文子串预检（必要条件）：候选少且都是纯 ASCII 时返回条件，否则返回 None 表示不预检。"""
    candidates = sorted({str(value) for value in values})
    if (not candidates or len(candidates) > TEXT_PRECHECK_MAX_CANDIDATES
            or not all(_TEXT_PRECHECK_CANDIDATE.fullmatch(value) for value in candidates)):
        return None
    return _TextContains(cast(column, Text), literal("(" + "|".join(candidates) + ")", type_=String))


class _TextContains(FunctionElement):
    type = Boolean()
    inherit_cache = True


@compiles(_TextContains, "postgresql")
def _postgresql_text_contains(element, compiler, **kwargs):
    text_value, pattern = (compiler.process(clause, **kwargs) for clause in element.clauses)
    return f"({text_value} ~ {pattern})"


@compiles(_TextContains, "sqlite")
def _sqlite_text_contains(element, compiler, **kwargs):
    # SQLite 无正则运算符；预检只是必要条件，直接放行，由精确比较决定。
    return "1"


class _ScalarInValues(FunctionElement):
    type = Boolean()
    inherit_cache = True


@compiles(_ScalarInValues, "postgresql")
def _postgresql_scalar_in_values(element, compiler, **kwargs):
    column, candidates = (compiler.process(clause, **kwargs) for clause in element.clauses)
    value_type = compiler.dialect.type_compiler.process(list(element.clauses)[0].type)
    return (
        f"({column} IN (SELECT CAST(candidate.value AS {value_type}) "
        f"FROM jsonb_array_elements_text(CAST({candidates} AS JSONB)) AS candidate(value)))"
    )


@compiles(_ScalarInValues, "sqlite")
def _sqlite_scalar_in_values(element, compiler, **kwargs):
    column, candidates = (compiler.process(clause, **kwargs) for clause in element.clauses)
    return f"({column} IN (SELECT value FROM json_each({candidates})))"


def scalar_in_values(column, values):
    """用单个参数表示编号集合，避免按批次重复扫描未索引的关联列。"""
    if not isinstance(column.type, (Integer, String)):
        raise TypeError("集合关联仅支持整数或字符串列")
    candidates = sorted(set(values), key=lambda value: (value is None, str(value)))
    if not candidates:
        return false()
    encoded = json.dumps(candidates, ensure_ascii=False, separators=(",", ":"))
    return _ScalarInValues(column, literal(encoded, type_=String))
