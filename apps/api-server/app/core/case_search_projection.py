"""案件筛选只读字段和分页回读，避免将未显示案件的历史快照载入内存。"""
from types import SimpleNamespace

from sqlalchemy import select

from app.models import BusinessRecord


CASE_SEARCH_FIELDS = (
    "case_type", "case_phase", "case_phase_name",
    "customer_id", "customer_record_id", "customer_no",
    "plaintiff", "plaintiffs", "defendant", "opponent", "defendants",
    "court", "court_name", "first_court_name",
    "prosecutor", "procuratorate", "first_procuratorate_name",
    "administrative_agency", "counsel_contact",
    "court_case_no", "first_court_case_no", "first_instance_no",
    "second_court_case_no", "second_instance_no", "execution_case_no", "retrial_case_no",
    "notary_no", "notary_nos", "certificate_no",
    "clue_no", "clue_nos", "investigation_clue", "investigation_clue_nos", "source_clue_no",
    "evidence_org", "evidence_organization",
    "hearing_lawyer", "hearing_lawyers", "court_lawyer",
    "investigator", "investigators", "investigation_user",
    "channel", "case_channel", "warehouse", "evidence_warehouse",
    "area", "case_area", "location", "case_location", "log_content",
    "source_date", "source_at", "hearing_date", "first_court_hearing_date",
    "second_court_hearing_date", "retrial_court_hearing_date",
    "counsel_type", "handling_lawyers", "assistant", "counsel_start", "counsel_end",
    "assisted_response_user", "response_user", "assisted_request_date", "request_date",
    "assisted_response_date", "response_date",
)


def matches_case_search_status(record, body):
    if body.case_statuses:
        allowed_statuses = {str(status or "").strip() for status in body.case_statuses if str(status or "").strip()}
        return str(record.status or "").strip() in allowed_statuses
    expected = (body.case_status or body.status).strip()
    return not expected or expected.casefold() in str(record.status or "").casefold()


# 只带这些条件的检索（打开列表、点阶段树、翻页、排序）只扫描一次范围条件、只读排序和计数所需的列；
# 其他任何条件都回到完整筛选，保持原有语义。
FAST_SEARCH_FIELDS = frozenset({
    "scope", "case_types", "case_type", "case_status", "case_statuses", "status",
    "sort_order", "page", "page_size",
})
SORT_ORDERS = {"updated_desc", "updated_asc", "created_desc", "created_asc", "status_asc", "case_no_asc", "case_no_desc"}


def fast_case_search_eligible(body) -> bool:
    return (
        body.scope in {"mine", "department", "company", "global"}
        and body.sort_order in SORT_ORDERS
        and set(body.model_dump(exclude_defaults=True)) <= FAST_SEARCH_FIELDS
    )


async def fast_case_search_page(body, scope_conditions, db):
    """返回 (阶段计数, 总数, 当前页完整记录)，与完整筛选路径的结果逐条一致。

    范围条件（尤其是部门范围）本身较重，只执行一次；类型、阶段筛选和排序沿用完整路径的 Python 规则，
    但只作用在几列轻量数据上，不再解析每个案件的全部业务字段。
    """
    from app.core.cases import sort_case_search_records

    requested_types = {str(item).strip() for item in body.case_types if str(item).strip()}
    if body.case_type.strip():
        requested_types.add(body.case_type.strip())
    rows = (await db.execute(select(
        BusinessRecord.id, BusinessRecord.status, BusinessRecord.serial_no,
        BusinessRecord.created_at, BusinessRecord.updated_at, BusinessRecord.data["case_type"],
    ).where(*scope_conditions))).all()
    candidates = []
    for row in rows:
        case_type = str(row[5] or "")
        if requested_types:
            if case_type not in requested_types:
                continue
        elif body.scope != "global" and case_type == "法律顾问":
            continue
        candidates.append(SimpleNamespace(id=row.id, status=row.status, serial_no=row.serial_no,
                                          created_at=row.created_at, updated_at=row.updated_at))
    phase_counts: dict[str, int] = {}
    for record in candidates:
        phase_counts[str(record.status or "")] = phase_counts.get(str(record.status or ""), 0) + 1
    matched = [record for record in candidates if matches_case_search_status(record, body)]
    sort_case_search_records(matched, body.sort_order)
    return phase_counts, len(matched), await read_case_search_page(matched, body.page, body.page_size, db)


async def read_case_search_page(records, page, page_size, db):
    start = (page - 1) * page_size
    selected = records[start:start + page_size]
    if not selected:
        return []
    rows = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case", BusinessRecord.id.in_([record.id for record in selected]),
    ))).all()
    by_id = {record.id: record for record in rows}
    # 按既有 Python 排序回填完整记录；并发删除的记录不能变成虚构的列表项。
    return [by_id[record.id] for record in selected if record.id in by_id]
