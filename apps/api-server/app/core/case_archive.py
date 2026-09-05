"""Archive queue queries and batch request contracts."""
from datetime import date
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import and_, cast, func, or_, select, String

from app.models import BusinessRecord, HearingSchedule, User
from app.models_shared import ArchiveReviewInput


class ArchiveSearchInput(BaseModel):
    view: Literal["pending", "done", "refused"] = "pending"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=15, ge=1, le=100)
    serial_no: str = Field(default="", max_length=200)
    plaintiff: str = Field(default="", max_length=200)
    defendant: str = Field(default="", max_length=200)
    third_party: str = Field(default="", max_length=200)
    assistant: str = Field(default="", max_length=200)
    court: str = Field(default="", max_length=200)
    notary_no: str = Field(default="", max_length=200)
    hearing_lawyer: str = Field(default="", max_length=200)
    handling_lawyer: str = Field(default="", max_length=200)
    submitter: str = Field(default="", max_length=200)
    review_from: date | None = None
    review_to: date | None = None
    submit_from: date | None = None
    submit_to: date | None = None


class ArchiveBatchReviewItem(ArchiveReviewInput):
    case_id: int = Field(gt=0)


class ArchiveBatchReviewInput(BaseModel):
    items: list[ArchiveBatchReviewItem] = Field(min_length=1, max_length=100)


class ArchiveExportInput(ArchiveSearchInput):
    selected_ids: list[int] | None = Field(default=None, min_length=1, max_length=100)
    format: Literal["excel", "csv"] = "excel"


def _text(key):
    return func.coalesce(BusinessRecord.data[key].as_string(), "")


def _date_range(expression, start, end):
    # Stored timestamps may include time/offset; ISO date prefix is portable to
    # both PostgreSQL and SQLite and does not cast empty legacy strings to date.
    day = func.substr(expression, 1, 10)
    values = [day != ""]
    if start:
        values.append(day >= start.isoformat())
    if end:
        values.append(day <= end.isoformat())
    return and_(*values)


async def search_archive_cases(body, identity, db, *, export=False):
    from app.core.cases import _case_action_granted
    from app.core.contracts import _contract_customer_record_dicts
    from app.core.permissions import _record_scope_conditions, _require_record_module_menu
    from app.core.system import _allowed_field_keys

    await _require_record_module_menu("case", identity, db, action="查看归档案件")
    for start, end in ((body.review_from, body.review_to), (body.submit_from, body.submit_to)):
        if start and end and start > end:
            raise HTTPException(status_code=422, detail="开始日期不能晚于结束日期")
    conditions = [BusinessRecord.module == "case", *(await _record_scope_conditions(identity, db))]
    submitter = func.trim(_text("archive_submitter"))
    reviewer = func.trim(_text("archive_reviewer"))
    internal_reviewer = func.trim(_text("archive_internal_reviewer"))
    if body.view == "pending":
        if not await _case_action_granted(identity, db, "case.archive.review"):
            return [] if export else {"items": [], "total": 0, "page": body.page, "page_size": body.page_size}
        conditions.extend([
            BusinessRecord.status.in_(["待归档审核", "亏损内审", "亏损审核"]),
            or_(reviewer == identity["username"], internal_reviewer == identity["username"],
                and_(reviewer == "", internal_reviewer == "", BusinessRecord.owner == identity["username"])),
            submitter != identity["username"],
        ])
    elif body.view == "done":
        conditions.append(BusinessRecord.status.in_(["已归档", "亏损归档"]))
    else:
        conditions.extend([submitter == identity["username"], or_(
            BusinessRecord.status == "亏损归档拒绝", func.trim(_text("archive_reject_reason")) != "",
        )])

    fields = {
        "serial_no": [BusinessRecord.serial_no],
        "plaintiff": [_text("plaintiff"), _text("plaintiffs"), BusinessRecord.customer],
        "defendant": [_text("opponent"), _text("defendant"), _text("defendants")],
        "third_party": [_text("third_party"), _text("third_parties"), _text("victim"), _text("victims")],
        "court": [_text(key) for key in ("court", "first_court_name", "first_instance_court", "second_court_name", "second_instance_court", "execution_court_name", "retrial_court_name")],
        "notary_no": [_text("notary_no"), _text("certificate_no"), _text("notarization_no")],
        "assistant": [_text("assistant"), _text("assistants"), _text("case_assistant")],
        "hearing_lawyer": [_text("hearing_lawyer"), _text("hearing_lawyers")],
        "handling_lawyer": [_text("handling_lawyer"), _text("handling_lawyers")],
        "submitter": [func.coalesce(func.nullif(submitter, ""), BusinessRecord.owner)],
    }
    for key, expressions in fields.items():
        value = getattr(body, key).strip()
        if not value:
            continue
        needles = [value]
        if key in {"assistant", "hearing_lawyer", "handling_lawyer", "submitter"}:
            needles.extend((await db.scalars(select(User.username).where(User.display_name.icontains(value, autoescape=True)))).all())
        conditions.append(or_(*(expression.icontains(needle, autoescape=True) for expression in expressions for needle in needles)))
    if body.submit_from or body.submit_to:
        conditions.append(_date_range(_text("archive_submitted_at"), body.submit_from, body.submit_to))
    if body.review_from or body.review_to:
        if body.view == "pending":
            hearing_checks = [_date_range(_text(key), body.review_from, body.review_to) for key in (
                "hearing_date", "next_hearing_date", "first_court_hearing_date", "second_court_hearing_date", "retrial_court_hearing_date", "execution_court_hearing_date",
            )]
            hearing_checks.append(select(HearingSchedule.id).where(
                HearingSchedule.case_record_id == BusinessRecord.id,
                _date_range(cast(HearingSchedule.hearing_date, String), body.review_from, body.review_to),
            ).exists())
            conditions.append(or_(*hearing_checks))
        else:
            reviewed = func.coalesce(func.nullif(_text("archive_reviewed_at"), ""), _text("archived_at"))
            conditions.append(_date_range(reviewed, body.review_from, body.review_to))
    total = await db.scalar(select(func.count()).select_from(BusinessRecord).where(*conditions)) or 0
    sort_date = _text("archive_submitted_at") if body.view == "pending" else func.coalesce(func.nullif(_text("archive_reviewed_at"), ""), _text("archived_at"))
    if export and body.selected_ids is not None:
        conditions.append(BusinessRecord.id.in_(body.selected_ids))
    query = select(BusinessRecord).where(*conditions).order_by(sort_date.desc(), BusinessRecord.id.desc())
    if not export:
        query = query.offset((body.page - 1) * body.page_size).limit(body.page_size)
    records = list((await db.scalars(query)).all())
    if export:
        if body.selected_ids is not None and len(records) != len(set(body.selected_ids)):
            raise HTTPException(status_code=409, detail="选中案件已变化或不在当前筛选范围，请刷新后重试")
        return records
    items = await _contract_customer_record_dicts(records, await _allowed_field_keys(identity, db), db, identity)
    return {"items": items, "total": total, "page": body.page, "page_size": body.page_size}
