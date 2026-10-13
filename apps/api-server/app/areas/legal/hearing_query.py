"""公司排期从案件法院资料和独立排期记录统一查询，不回填业务表。"""

from fastapi import HTTPException
from sqlalchemy import String, cast, func, literal, or_, select, union_all

from app.core.formatters import _case_hearing_datetime
from app.models import BusinessRecord, FileAttachment, HearingSchedule, WorkflowEvent


async def query_company_hearings(identity, db, *, page, page_size, filters, hearing_from, hearing_to, source_from, source_to):
    from app.core.contracts import _contract_customer_record_dicts
    from app.core.permissions import _record_scope_conditions
    from app.core.system import _allowed_field_keys

    for start, end in ((hearing_from, hearing_to), (source_from, source_to)):
        if start and end and start > end:
            raise HTTPException(422, "开始日期不能晚于结束日期")

    data = BusinessRecord.data

    def field(*keys):
        return func.coalesce(*(func.nullif(data[key].as_string(), "") for key in keys), "")

    conditions = [BusinessRecord.module == "case", BusinessRecord.status != "已合并", *(await _record_scope_conditions(identity, db))]
    columns = {
        "serial_no": BusinessRecord.serial_no, "customer": BusinessRecord.customer,
        "plaintiff": field("plaintiff"), "defendant": field("opponent", "defendant"),
        "third_party": field("third_party"), "notary_no": field("notary_no"),
        "handling_lawyer": cast(data["handling_lawyers"], String),
        "assistant": field("assistant"),
        "investigator": field("investigator"), "case_type": field("case_type"),
    }
    for key, column in columns.items():
        value = filters.get(key, "").strip()
        if value:
            conditions.append(column.icontains(value, autoescape=True))
    keyword = filters.get("keyword", "").strip()
    if keyword:
        conditions.append(or_(*(column.icontains(keyword, autoescape=True) for column in (
            BusinessRecord.serial_no, BusinessRecord.title, BusinessRecord.customer,
            field("court_case_no"), field("first_court_case_no"), field("second_court_case_no"),
        ))))
    for key, model, column in (("document_name", FileAttachment, FileAttachment.original_name), ("log_content", WorkflowEvent, WorkflowEvent.comment)):
        value = filters.get(key, "").strip()
        if value:
            conditions.append(select(model.id).where(model.record_id == BusinessRecord.id, column.icontains(value, autoescape=True)).exists())
    source_date = func.substr(field("case_register_date", "source_date", "source_at"), 1, 10)
    if source_from:
        conditions.append(source_date >= source_from.isoformat())
    if source_to:
        conditions.append(source_date <= source_to.isoformat())

    cases = select(BusinessRecord.id).where(*conditions).subquery()
    levels = (
        ("first", "一审开庭", field("first_court_hearing_date"), field("first_court_name", "first_instance_court", "court"), field("first_court_courtroom", "courtroom")),
        ("second", "二审开庭", field("second_court_hearing_date"), field("second_court_name", "second_instance_court"), field("second_court_courtroom")),
        ("execution", "执行开庭", field("execution_court_hearing_date"), field("execution_court_name"), field("execution_court_courtroom")),
        ("retrial", "再审开庭", field("retrial_court_hearing_date", "last_court_hearing_date"), field("retrial_court_name", "last_court_name"), field("retrial_court_courtroom", "last_court_courtroom")),
        ("hearing", "开庭", field("hearing_date"), field("court"), field("courtroom")),
        ("next", "开庭", field("next_hearing_date"), field("court"), field("courtroom")),
    )
    projections = []
    for slot, hearing_type, raw_date, court, courtroom in levels:
        day = func.substr(raw_date, 1, 10)
        time = func.substr(raw_date, 12, 5)
        if slot in {"hearing", "next"}:
            time = func.coalesce(func.nullif(time, ""), field("hearing_time" if slot == "hearing" else "next_hearing_time"))
        duplicate = select(HearingSchedule.id).where(
            HearingSchedule.case_record_id == BusinessRecord.id,
            cast(HearingSchedule.hearing_date, String) == day,
            or_(HearingSchedule.hearing_type == hearing_type, HearingSchedule.hearing_type == "开庭"),
            or_(time == "", func.substr(HearingSchedule.hearing_time, 1, 5) == time),
        ).exists()
        exclusions = []
        # 通用日期只是同一次法院排期的投影，不再次列出。
        if slot in {"hearing", "next"}:
            exclusions.extend(func.substr(value, 1, 10) != day for _, _, value, _, _ in levels[:4])
        if slot == "next":
            exclusions.append(func.substr(field("hearing_date"), 1, 10) != day)
        projections.append(select(
            BusinessRecord.id.label("case_id"), literal(slot).label("slot"),
            day.label("day"), time.label("time"), court.label("court"),
            courtroom.label("courtroom"), literal(hearing_type).label("hearing_type"),
            field("hearing_lawyer").label("hearing_lawyer"),
        ).where(BusinessRecord.id.in_(select(cases.c.id)), raw_date != "", ~duplicate, *exclusions))
    projections.append(select(
        HearingSchedule.case_record_id.label("case_id"),
        (literal("schedule:") + cast(HearingSchedule.id, String)).label("slot"),
        cast(HearingSchedule.hearing_date, String).label("day"),
        HearingSchedule.hearing_time.label("time"), HearingSchedule.court.label("court"),
        HearingSchedule.courtroom.label("courtroom"), HearingSchedule.hearing_type.label("hearing_type"),
        HearingSchedule.hearing_lawyer.label("hearing_lawyer"),
    ).where(HearingSchedule.case_record_id.in_(select(cases.c.id))))
    schedules = union_all(*projections).subquery()
    schedule_conditions = []
    if hearing_from:
        schedule_conditions.append(schedules.c.day >= hearing_from.isoformat())
    if hearing_to:
        schedule_conditions.append(schedules.c.day <= hearing_to.isoformat())
    if filters.get("court", "").strip():
        schedule_conditions.append(schedules.c.court.icontains(filters["court"].strip(), autoescape=True))
    if filters.get("hearing_lawyer", "").strip():
        schedule_conditions.append(schedules.c.hearing_lawyer.icontains(filters["hearing_lawyer"].strip(), autoescape=True))
    total = int(await db.scalar(select(func.count()).select_from(schedules).where(*schedule_conditions)) or 0)
    rows = (await db.execute(select(schedules).where(*schedule_conditions).order_by(
        schedules.c.day, schedules.c.time, schedules.c.case_id, schedules.c.slot,
    ).offset((page - 1) * page_size).limit(page_size))).mappings().all()
    ids = {row["case_id"] for row in rows}
    records = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(ids)))).all()) if ids else []
    visible = await _contract_customer_record_dicts(records, await _allowed_field_keys(identity, db), db, identity)
    by_id = {record["id"]: record for record in visible}
    items = []
    for row in rows:
        hearing_at = _case_hearing_datetime(row["day"])
        if hearing_at is None:
            raise HTTPException(422, f'案件 {row["case_id"]} 的开庭日期格式无效，请修正法院或排期资料')
        hearing_day = hearing_at.date()
        case = by_id[row["case_id"]]
        items.append({
            "id": f'{row["case_id"]}:{row["slot"]}', "case_record_id": row["case_id"], "case": case,
            "case_no": case["serial_no"], "customer": case["customer"],
            "weekday": "星期" + "一二三四五六日"[hearing_day.weekday()],
            "hearing_date": hearing_day.isoformat(), "hearing_time": row["time"],
            "court": row["court"], "courtroom": row["courtroom"], "hearing_type": row["hearing_type"],
            "hearing_lawyer": row["hearing_lawyer"],
        })
    return {"items": items, "total": total, "page": page, "page_size": page_size}
