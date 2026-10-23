"""客户列表的汇总和关系投影，不加载无关业务完整载荷。"""

import re
import unicodedata
from functools import lru_cache

from sqlalchemy import cast, func, literal, literal_column, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cases import _is_civil_case_type
from app.core.formatters import _normalize_customer_name
from app.models import BusinessRecord, User


CUSTOMER_TYPE_INDEX = "ix_business_records_module_customer_type"


def customer_type_expression(dialect_name: str):
    """客户类型（未填按“客户”）。PostgreSQL 上键名和默认值写成字面量，才能命中同表达式的索引。"""
    if dialect_name == "postgresql":
        return func.coalesce(BusinessRecord.data[literal_column("'customer_type'")].as_string(), literal_column("'客户'"))
    return func.coalesce(BusinessRecord.data["customer_type"].as_string(), "客户")


CUSTOMER_GUID_INDEX = "ix_business_records_module_customer_guid"


def customer_guid_expression(dialect_name: str):
    """存储的客户 GUID。PostgreSQL 上键名写成字面量，才能命中同表达式的索引。"""
    if dialect_name == "postgresql":
        return BusinessRecord.data[literal_column("'customer_guid'")].as_string()
    return BusinessRecord.data["customer_guid"].as_string()


def create_customer_list_indexes(connection) -> None:
    """客户列表按“模块 + 客户类型”过滤、客户详情按 GUID 查找，建索引后不必逐行解析全部客户的 JSON。"""
    if connection.dialect.name != "postgresql":
        return
    from sqlalchemy import text
    connection.execute(text(
        f"CREATE INDEX IF NOT EXISTS {CUSTOMER_TYPE_INDEX} ON business_records "
        "(module, (COALESCE(CAST(data ->> 'customer_type' AS VARCHAR), '客户')))"
    ))
    connection.execute(text(
        f"CREATE INDEX IF NOT EXISTS {CUSTOMER_GUID_INDEX} ON business_records "
        "(module, (CAST(data ->> 'customer_guid' AS VARCHAR)))"
    ))


async def customer_summary(db: AsyncSession, conditions: list, fields: list[str]) -> dict[str, float]:
    totals = dict.fromkeys(fields, 0.0)
    if db.get_bind().dialect.name == "postgresql":
        # 每个客户的 data 只解析一次，再取各汇总字段；取出的值与逐字段读取相同。
        source = select(
            BusinessRecord.updated_at, BusinessRecord.id, cast(BusinessRecord.data, JSONB).label("doc"),
        ).where(*conditions).offset(0).subquery()
        statement = select(*(source.c.doc[key] for key in fields)).order_by(
            source.c.updated_at.desc(), source.c.id.desc(),
        ).execution_options(yield_per=400)
    else:
        statement = select(*(BusinessRecord.data[key] for key in fields)).where(*conditions).order_by(
            BusinessRecord.updated_at.desc(), BusinessRecord.id.desc(),
        ).execution_options(yield_per=400)
    rows = await db.stream(statement)
    try:
        async for row in rows:
            for key, value in zip(fields, row):
                try:
                    totals[key] += float(value or 0)
                except (TypeError, ValueError):
                    # 历史非金额字段按原列表规则不参与金额汇总。
                    continue
    finally:
        await rows.close()
    return {key: round(value, 2) for key, value in totals.items()}


# Python 的 str.strip() 会去掉这些 ASCII 空白；其余（含 Unicode 空白）都按“有风险字符”整行保留。
_ASCII_STRIP = " \t\n\r\x0b\x0c\x1c\x1d\x1e\x1f"
_SAFE_SERIAL = re.compile(r"[A-Za-z0-9_\-]+")


@lru_cache(maxsize=1)
def _risky_text_pattern() -> str:
    """不在“可安全比较”字符集里的字符：Unicode 空白、带大小写、NFKC 会改写的字符、非 BMP 字符等。

    只由可打印 ASCII 和 NFKC 不变、无大小写、非空白的 BMP 字符组成的名称，
    数据库里的 lower(btrim(名称)) 与 Python 的 NFKC+casefold 归一化结果完全一致；
    含其他字符的行一律交给 Python 逐条判断，保证结果不变。
    """
    ranges: list[tuple[int, int]] = []
    start = None
    for code in range(0x80, 0x10000):
        char = chr(code)
        safe = not 0xD800 <= code <= 0xDFFF and not char.isspace() and unicodedata.normalize("NFKC", char) == char \
            and char.lower() == char and char.upper() == char and char.casefold() == char
        if safe and start is None:
            start = code
        elif not safe and start is not None:
            ranges.append((start, code - 1))
            start = None
    if start is not None:
        ranges.append((start, 0xFFFF))
    body = "".join(f"\\u{a:04x}" if a == b else f"\\u{a:04x}-\\u{b:04x}" for a, b in ranges)
    return f"[^\\x20-\\x7e{body}]"


def _relation_candidate_filter(page_items: list, doc, customer):
    """数据库侧只取“可能”关联到本页客户的合同/案件（超集），精确判断仍由下面的 Python 规则完成。

    无法安全缩小范围时返回 None，退回原来的全量扫描。
    """
    ids = sorted({int(item.id) for item in page_items})
    serials = sorted({str(item.serial_no or "").strip() for item in page_items} - {""})
    names = sorted({_normalize_customer_name(item.title) for item in page_items})
    if not ids or "" in names or any(not _SAFE_SERIAL.fullmatch(serial) for serial in serials):
        return None
    risky = literal(_risky_text_pattern())
    id_text = "|".join(str(value) for value in ids)
    id_pattern = literal(rf"^\s*[+]?0*({id_text})\s*$")
    plain_digits = literal(r"^\s*[+-]?[0-9]+\s*$")

    def id_may_match(key: str):
        value = doc[key].astext
        # 纯数字只在等于本页客户编号时保留；小数、布尔、全角数字等 Python int() 也可能接受的写法一律保留。
        return or_(value.op("~")(id_pattern), (value != "") & ~value.op("~")(plain_digits))

    customer_no = doc["customer_no"].astext
    name = func.coalesce(customer, "")
    conditions = [id_may_match("customer_id"), id_may_match("customer_record_id"),
                  customer_no.op("~")(literal(r"[^\x20-\x7e]")),
                  (name != "") & name.op("~")(risky),
                  func.lower(func.btrim(name, _ASCII_STRIP)).in_(names)]
    if serials:
        conditions.append(func.btrim(customer_no, _ASCII_STRIP).in_(serials))
    return or_(*conditions)


async def customer_relationship_counts(db: AsyncSession, page_items: list) -> dict[int, dict[str, int]]:
    by_id = {item.id: item for item in page_items}
    by_no = {str(item.serial_no or "").strip(): item for item in page_items if str(item.serial_no or "").strip()}
    by_name = {_normalize_customer_name(item.title): item for item in page_items}
    counts = {item.id: {"contract_count": 0, "civil_case_count": 0} for item in page_items}
    fields = ("customer_id", "customer_record_id", "customer_no", "case_type")
    statement = select(
        BusinessRecord.module, BusinessRecord.status, BusinessRecord.customer,
        *(BusinessRecord.data[key] for key in fields),
    ).where(BusinessRecord.module.in_(["contract", "case"]))
    if db.get_bind().dialect.name == "postgresql":
        # 每行的 data 只解析一次（OFFSET 0 阻止子查询被展开成多次解析），再在数据库侧挑出可能关联本页客户的行。
        source = select(
            BusinessRecord.module, BusinessRecord.status, BusinessRecord.customer,
            cast(BusinessRecord.data, JSONB).label("doc"),
        ).where(BusinessRecord.module.in_(["contract", "case"])).offset(0).subquery()
        candidate_filter = _relation_candidate_filter(page_items, source.c.doc, source.c.customer)
        if candidate_filter is not None:
            statement = select(
                source.c.module, source.c.status, source.c.customer, *(source.c.doc[key] for key in fields),
            ).where(candidate_filter)
    statement = statement.execution_options(yield_per=400)
    rows = await db.stream(statement)
    try:
        async for row in rows:
            module, status, name = row[:3]
            data = dict(zip(fields, row[3:]))
            try:
                linked = by_id.get(int(data.get("customer_id") or data.get("customer_record_id") or 0))
            except (TypeError, ValueError):
                linked = None
            if linked is None:
                linked = by_no.get(str(data.get("customer_no") or "").strip())
            if linked is None and name:
                linked = by_name.get(_normalize_customer_name(name))
            if linked is None:
                continue
            if module == "contract":
                if status not in {"已归档", "Archived", "archived"}:
                    counts[linked.id]["contract_count"] += 1
            elif _is_civil_case_type(data.get("case_type")):
                counts[linked.id]["civil_case_count"] += 1
    finally:
        await rows.close()
    return counts


async def customer_person_names(db: AsyncSession, page_items: list) -> dict[str, str]:
    needed = set()
    for item in page_items:
        data = item.data or {}
        managers = data.get("customer_managers") or ([item.owner] if item.owner else [])
        if not isinstance(managers, list):
            managers = [managers]
        source = data.get("customer_source") or data.get("source_person") or item.owner
        needed.update(str(value or "").strip().casefold() for value in [*managers, source])
        needed.add(str(item.owner or "").strip().casefold())
    needed.discard("")
    names: dict[str, str] = {}
    profile_fields = ("employee_id", "employee_no", "legacy_guid", "person_guid", "user_guid")
    rows = await db.stream(select(
        User.id, User.username, User.display_name, *(User.profile[key] for key in profile_fields),
    ).execution_options(yield_per=400))
    try:
        async for row in rows:
            display = str(row[2] or "").strip()
            if not display:
                continue
            profile = dict(zip(profile_fields, row[3:]))
            aliases = {
                str(row[1] or "").strip(), str(row[0]), display,
                str(profile.get("employee_id") or "").strip(), str(profile.get("employee_no") or "").strip(),
                str(profile.get("legacy_guid") or profile.get("person_guid") or profile.get("user_guid") or "").strip(),
            }
            names.update({alias.casefold(): display for alias in aliases if alias.casefold() in needed})
    finally:
        await rows.close()
    fields = ("display_name", "name", "username", "employee_id", "employee_no", "legacy_guid", "person_guid", "system_user_id")
    rows = await db.stream(select(
        BusinessRecord.id, BusinessRecord.serial_no, BusinessRecord.title, BusinessRecord.owner,
        *(BusinessRecord.data[key] for key in fields),
    ).where(BusinessRecord.module == "hr").execution_options(yield_per=400))
    try:
        async for row in rows:
            data = dict(zip(fields, row[4:]))
            display = str(row[2] or data.get("display_name") or data.get("name") or "").strip()
            if not display:
                continue
            aliases = {
                str(row[0]), str(row[1] or "").strip(), str(row[3] or "").strip(),
                *(str(data.get(key) or "").strip() for key in fields[2:]),
            }
            for alias in aliases:
                if alias.casefold() in needed:
                    names.setdefault(alias.casefold(), display)
    finally:
        await rows.close()
    return names
