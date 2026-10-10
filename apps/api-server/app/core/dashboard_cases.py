"""控制台案件区块：统计在数据库完成，明细按显示范围读取。"""
from datetime import datetime, time, timezone
from sqlalchemy import String, cast
from app.core.dependencies import BusinessRecord, HearingSchedule, SystemParameter, select, func, or_, date, timedelta
from app.core.constants import _CASE_HEARING_LEVELS, CASE_EVENT_TIME_ZONE
from app.core.cases import _dashboard_case_hearing, _dashboard_latest_case_row
from app.core.contracts import _contract_person_values
from app.core.crm import _dashboard_customer_for_case
from app.core.formatters import _normalized_customer_name, _user_display_map
from app.core.system import _dashboard_people, _record_person_usernames
from app.core.dashboard import dashboard_scope
from app.core.record_json_text_query import projected_record_condition, record_json_text_projection
from app.core.record_projection_query import read_record_projections


async def dashboard_cases(identity, db):
    scope, modules = await dashboard_scope(identity, db)
    conditions = [BusinessRecord.module == "case", BusinessRecord.status != "已合并", BusinessRecord.module.in_(modules), *scope]
    today = datetime.now(timezone.utc).astimezone(CASE_EVENT_TIME_ZONE).date()
    current_month = today.replace(day=1)
    month_keys = []
    for offset in range(9, -1, -1):
        year, month = current_month.year, current_month.month - offset
        while month <= 0:
            year -= 1
            month += 12
        month_keys.append(f"{year:04d}-{month:02d}")
    # SQLite 保存无时区 UTC，PostgreSQL 保存 timestamptz；按既有业务时区归入自然月。
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        local_created_at = func.timezone(str(CASE_EVENT_TIME_ZONE), BusinessRecord.created_at)
    elif dialect == "sqlite":
        local_created_at = func.datetime(BusinessRecord.created_at, "+8 hours")
    else:
        raise ValueError(f"控制台月统计不支持数据库：{dialect}")
    month_column = func.substr(cast(local_created_at, String), 1, 7)
    first_month = datetime.combine(
        date.fromisoformat(month_keys[0] + "-01"), time.min, tzinfo=CASE_EVENT_TIME_ZONE,
    ).astimezone(timezone.utc)
    month_counts = dict((await db.execute(select(month_column, func.count()).where(
        *conditions, BusinessRecord.created_at >= first_month,
    ).group_by(month_column))).all())
    case_trend = [{"date": key, "value": month_counts.get(key, 0)} for key in month_keys]
    stage_groups = [("立案待分配", lambda s: s in {"新案待分配", "立案待分配"}, "#f7474c"),
                    ("文书准备", lambda s: "文书准备" in s, "#46b8b8"),
                    ("一审", lambda s: "一审" in s, "#ffb45a"),
                    ("二审", lambda s: "二审" in s, "#7f70b3"),
                    ("再审", lambda s: "再审" in s, "#98a5b7"),
                    ("执行", lambda s: "执行" in s, "#303030")]
    stage_counts = {label: 0 for label, _, _ in stage_groups}
    other_count = 0
    for status, total in (await db.execute(select(BusinessRecord.status, func.count()).where(
        *conditions,
    ).group_by(BusinessRecord.status))).all():
        matched = next((label for label, match, _ in stage_groups if match(status)), None)
        if matched:
            stage_counts[matched] += total
        else:
            other_count += total
    civil_distribution = [{"label": label, "value": stage_counts[label], "color": color}
                          for label, _, color in stage_groups]
    if other_count:
        civil_distribution.append({"label": "其他", "value": other_count, "color": "#c5cbd3"})
    # 当前发布规则按创建时间取最新案件，旧登记日期不再参与排序。
    latest_case_records = list((await db.scalars(select(BusinessRecord).where(
        *conditions,
    ).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()).limit(13))).all())
    cutoff = today + timedelta(days=100)
    scheduled_ids = select(HearingSchedule.case_record_id).where(
        HearingSchedule.hearing_date >= today, HearingSchedule.hearing_date <= cutoff,
    )
    hearing_keys = [f"{prefix}_court_hearing_date" for prefix, _ in _CASE_HEARING_LEVELS]
    hearing_keys.extend(("hearing_date", "next_hearing_date"))
    from app.core.dashboard_scope import company_hearing_conditions
    hearing_conditions = await company_hearing_conditions(identity, db)
    hearing_projection, hearing_data = record_json_text_projection(db, hearing_keys)
    hearing_fields = (*hearing_keys, "hearing_time", "next_hearing_time", "hearing_lawyer",
                      "handling_lawyers", "assistant", "court", "courtroom",
                      "first_instance_court", "second_instance_court",
                      *(f"{prefix}_court_{key}" for prefix, _ in _CASE_HEARING_LEVELS
                        for key in ("name", "courtroom")))
    # 开庭投影只依赖这些字段，历史快照不参与排期，不载入 ORM 会话。
    cases = await read_record_projections(db, [*hearing_conditions, or_(
        BusinessRecord.id.in_(scheduled_ids),
        projected_record_condition(hearing_projection, or_(
            *(func.coalesce(hearing_data[key], "") != "" for key in hearing_keys),
        )),
    )], hearing_fields)
    case_map = {item.id: item for item in cases}
    visible_case_ids = set(case_map)
    projected_hearings = {
        item.id: projected
        for item in cases
        if (projected := _dashboard_case_hearing(item, today, cutoff)) is not None
    }
    hearing_rows = (await db.scalars(select(HearingSchedule).where(
        HearingSchedule.case_record_id.in_(visible_case_ids),
        HearingSchedule.hearing_date >= today,
        HearingSchedule.hearing_date <= cutoff,
    ).order_by(HearingSchedule.hearing_date, HearingSchedule.hearing_time))).all() if visible_case_ids else []
    hearings = list(projected_hearings.values())
    for item in hearing_rows:
        if item.case_record_id in projected_hearings:
            continue
        case = case_map[item.case_record_id]; data = case.data or {}
        hearings.append({"case_record_id": case.id, "weekday": "星期" + "一二三四五六日"[item.hearing_date.weekday()], "date": str(item.hearing_date), "time": item.hearing_time, "court": item.court, "case_no": case.serial_no, "client": case.customer, "lawyer": item.hearing_lawyer or data.get("hearing_lawyer", ""), "agent": ",".join(data.get("handling_lawyers", [])), "assistant": data.get("assistant", ""), "hearing_type": item.hearing_type, "courtroom": item.courtroom})
    hearings.sort(key=lambda item: (item["date"], item["time"], item["case_no"]))
    hearings = hearings[:13]
    customer_ids: set[int] = set()
    customer_nos: set[str] = set()
    customer_names: set[str] = set()
    person_usernames: set[str] = set()
    for item in latest_case_records:
        data = item.data or {}
        try:
            customer_id = int(data.get("customer_record_id") or data.get("customer_id") or 0)
        except (TypeError, ValueError):
            customer_id = 0
        if customer_id:
            customer_ids.add(customer_id)
        if customer_no := str(data.get("customer_no") or "").strip():
            customer_nos.add(customer_no)
        if item.customer:
            customer_names.add(_normalized_customer_name(item.customer))
        person_usernames.update(_record_person_usernames(item))
        for person_key in (
            "customer_manager", "customer_managers", "customer_manager_username", "customer_manager_usernames",
            "hearing_lawyer", "hearing_lawyers",
            "hearing_lawyer_username", "hearing_lawyer_usernames", "handling_lawyers",
            "handling_lawyer_usernames", "assistant", "assistants", "assistant_username",
            "assistant_usernames",
        ):
            person_usernames.update(_contract_person_values(data.get(person_key)))
    for hearing in hearings:
        for person_key in ("lawyer", "agent", "assistant"):
            person_usernames.update(_contract_person_values(hearing.get(person_key)))
    customer_conditions = []
    if customer_ids:
        customer_conditions.append(BusinessRecord.id.in_(customer_ids))
    if customer_nos:
        customer_conditions.append(BusinessRecord.serial_no.in_(customer_nos))
    if customer_names:
        customer_conditions.append(BusinessRecord.title.in_({item.customer for item in latest_case_records if item.customer}))
    related_customers = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "customer", or_(*customer_conditions),
    ))).all()) if customer_conditions else []
    customers_by_id = {item.id: item for item in related_customers}
    customers_by_no: dict[str, list[BusinessRecord]] = {}
    customers_by_name: dict[str, list[BusinessRecord]] = {}
    for item in related_customers:
        customers_by_no.setdefault(str(item.serial_no or "").strip(), []).append(item)
        customers_by_name.setdefault(_normalized_customer_name(item.title), []).append(item)
    for customer in related_customers:
        person_usernames.add(customer.owner)
        person_usernames.update(_contract_person_values((customer.data or {}).get("customer_managers")))
    users_by_username = await _user_display_map(person_usernames, db)
    court_values = {
        str(hearing.get("court") or "").strip()
        for hearing in hearings
        if str(hearing.get("court") or "").strip()
    }
    court_rows = (await db.scalars(select(SystemParameter).where(
        SystemParameter.category == "court",
        SystemParameter.is_active.is_(True),
        SystemParameter.code.in_(court_values),
    ))).all() if court_values else []
    court_names_by_code = {str(item.code).strip().casefold(): str(item.name).strip() for item in court_rows}
    for hearing in hearings:
        raw_court = str(hearing.get("court") or "").strip()
        hearing["court"] = court_names_by_code.get(raw_court.casefold(), raw_court)
        for person_key in ("lawyer", "agent", "assistant"):
            hearing[person_key] = _dashboard_people(users_by_username, hearing.get(person_key))
    latest_cases = [
        _dashboard_latest_case_row(
            item,
            _dashboard_customer_for_case(item, customers_by_id, customers_by_no, customers_by_name),
            users_by_username,
        )
        for item in latest_case_records
    ]
    return {"case_trend": case_trend, "civil_distribution": civil_distribution, "hearings": hearings, "latest_cases": latest_cases}
