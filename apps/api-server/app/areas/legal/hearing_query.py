"""排期从权限范围内案件法院资料和独立排期记录统一查询，不回填业务表。"""

from fastapi import HTTPException
from sqlalchemy import String, case as sql_case, cast, func, literal, or_, select, union_all
from sqlalchemy.dialects.postgresql import JSONB

from app.core.formatters import _case_hearing_datetime
from app.models import BusinessRecord, FileAttachment, HearingSchedule, SystemParameter, User, WorkflowEvent


async def query_company_hearings(identity, db, *, page, page_size, filters, hearing_from, hearing_to, source_from, source_to, export_case_ids=False, scope="company"):
    from app.core.contracts import _contract_customer_record_dicts
    from app.core.permissions import _record_scope_conditions
    from app.core.system import _allowed_field_keys

    for start, end in ((hearing_from, hearing_to), (source_from, source_to)):
        if start and end and start > end:
            raise HTTPException(422, "开始日期不能晚于结束日期")

    aliases = {}
    person_filters = {key: filters.get(key, "").strip() for key in (
        "hearing_lawyer", "handling_lawyer", "assistant", "investigator",
    ) if filters.get(key, "").strip()}
    if person_filters:
        people = (await db.execute(select(User.username, User.display_name).where(or_(
            *(column.icontains(value, autoescape=True) for value in person_filters.values()
              for column in (User.username, User.display_name)),
        )))).all()
        for key, value in person_filters.items():
            aliases[key] = {value}
            for username, name in people:
                if any(value.casefold() in str(part or "").casefold() for part in (username, name)):
                    aliases[key].update(str(part).strip() for part in (username, name) if part)
    if filters.get("court", "").strip():
        value = filters["court"].strip()
        courts = (await db.execute(select(SystemParameter.code, SystemParameter.name).where(
            SystemParameter.category == "court",
            or_(SystemParameter.code.icontains(value, autoescape=True), SystemParameter.name.icontains(value, autoescape=True)),
        ))).all()
        aliases["court"] = {value, *(part for row in courts for part in row if part)}

    def matches(column, key):
        return or_(*(column.icontains(value, autoescape=True)
                     for value in aliases.get(key, {filters.get(key, "").strip()})))

    data = BusinessRecord.data

    def field(*keys):
        return func.coalesce(*(func.nullif(data[key].as_string(), "") for key in keys), "")

    def array_matches(key, filter_key):
        dialect = db.get_bind().dialect.name
        if dialect == "postgresql":
            value = cast(data[key], JSONB)
            safe_array = sql_case((func.jsonb_typeof(value) == "array", value), else_=literal([], type_=JSONB))
            values = func.jsonb_array_elements_text(safe_array).table_valued("value")
        elif dialect == "sqlite":
            values = func.json_each(data, f"$.{key}").table_valued("value")
        else:
            raise RuntimeError(f"开庭排期查询不支持数据库方言：{dialect}")
        return select(1).select_from(values).where(matches(cast(values.c.value, String), filter_key)).exists()

    conditions = [BusinessRecord.module == "case", BusinessRecord.status != "已合并"]
    # 与普通案件列表共用范围规则，不能将公司排期全量交给前端筛选。
    if scope == "department":
        from app.core.case_department_scope import department_case_condition
        conditions.append(await department_case_condition(identity, db))
    else:
        conditions.extend(await _record_scope_conditions(identity, db))
        if scope == "mine":
            from app.core.permissions import _case_mine_scope_condition
            conditions.append(await _case_mine_scope_condition(identity, db))
    columns = {
        "serial_no": BusinessRecord.serial_no, "customer": BusinessRecord.customer,
        "plaintiff": field("plaintiff"), "defendant": field("opponent", "defendant"),
        "third_party": field("third_party", "third_parties"), "notary_no": field("notary_no", "notary_nos"),
        "handling_lawyer": field("handling_lawyers", "handling_lawyer_usernames", "handling_lawyer"),
        "assistant": field("assistant", "assistant_username"),
        "investigator": field("investigator", "investigator_username"), "case_type": field("case_type"),
    }
    array_fields = {
        "plaintiff": ("plaintiffs",), "defendant": ("defendants",), "third_party": ("third_parties",),
        "notary_no": ("notary_nos",), "handling_lawyer": ("handling_lawyers", "handling_lawyer_usernames"),
        "assistant": ("assistants", "assistant_usernames"),
    }
    for key, column in columns.items():
        value = filters.get(key, "").strip()
        if value:
            if key == "case_type" and value in {"民事争议", "民事案件"}:
                conditions.append(column.in_(("民事争议", "民事案件")))
            else:
                conditions.append(or_(matches(column, key), *(array_matches(name, key) for name in array_fields.get(key, ()))))
    keyword = filters.get("keyword", "").strip()
    if keyword:
        conditions.append(or_(*(column.icontains(keyword, autoescape=True) for column in (
            BusinessRecord.serial_no, BusinessRecord.title, BusinessRecord.customer,
            field("court_case_no"), field("first_court_case_no"), field("second_court_case_no"),
            field("execution_court_case_no"), field("retrial_court_case_no"),
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
            field("hearing_lawyer", "hearing_lawyer_username").label("hearing_lawyer"),
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
        schedule_conditions.append(matches(schedules.c.court, "court"))
    if filters.get("hearing_lawyer", "").strip():
        schedule_conditions.append(matches(schedules.c.hearing_lawyer, "hearing_lawyer"))
    total = int(await db.scalar(select(func.count()).select_from(schedules).where(*schedule_conditions)) or 0)
    ordered_query = select(schedules).where(*schedule_conditions).order_by(
        schedules.c.day, schedules.c.time, schedules.c.case_id, schedules.c.slot,
    )
    # 导出只需要权限内的排期关联和顺序，避免逐页重复统计及完整案件投影。
    rows = (await db.execute(ordered_query if export_case_ids else ordered_query.offset((page - 1) * page_size).limit(page_size))).mappings().all()
    if export_case_ids:
        current_total = int(await db.scalar(select(func.count()).select_from(schedules).where(*schedule_conditions)) or 0)
        if current_total != total or len(rows) != total or len({(row["case_id"], row["slot"]) for row in rows}) != len(rows):
            raise HTTPException(409, "排期查询结果已变化，请刷新后重新导出")
        for row in rows:
            if _case_hearing_datetime(row["day"]) is None:
                raise HTTPException(422, f'案件 {row["case_id"]} 的开庭日期格式无效，请修正法院或排期资料')
        return list(dict.fromkeys(row["case_id"] for row in rows))
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
