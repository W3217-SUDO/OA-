"""案件筛选只读字段和分页回读，避免将未显示案件的历史快照载入内存。"""
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
