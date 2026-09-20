"""控制台案件区块：统计在数据库完成，明细按显示范围读取。"""
from types import SimpleNamespace
from sqlalchemy import String, cast
from app.core.dependencies import BusinessRecord, HearingSchedule, select, func, or_, date, timedelta
from app.core.constants import _CASE_HEARING_LEVELS
from app.core.cases import _dashboard_case_hearing, _dashboard_latest_case_row
from app.core.contracts import _contract_person_values
from app.core.crm import _dashboard_customer_for_case
from app.core.formatters import _dashboard_case_date, _normalized_customer_name, _user_display_map
from app.core.system import _record_person_usernames
from app.core.dashboard import dashboard_scope


async def dashboard_cases(identity, db):
    scope, modules = await dashboard_scope(identity, db)
    conditions = [BusinessRecord.module == "case", BusinessRecord.status != "已合并", BusinessRecord.module.in_(modules), *scope]
    current_month = date.today().replace(day=1)
    month_keys = []
    for offset in range(9, -1, -1):
        year, month = current_month.year, current_month.month - offset
        while month <= 0:
            year -= 1
            month += 12
        month_keys.append(f"{year:04d}-{month:02d}")
    month_column = func.substr(cast(BusinessRecord.created_at, String), 1, 7)
    month_counts = dict((await db.execute(select(month_column, func.count()).where(
        *conditions, BusinessRecord.created_at >= date.fromisoformat(month_keys[0] + "-01"),
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
    # 历史日期可能包含时区或无效文本，继续使用原解析器，避免 SQL 强制转换改变顺序。
    date_rows = (await db.execute(select(
        BusinessRecord.id, BusinessRecord.created_at,
        BusinessRecord.data["case_register_date"].as_string(),
        BusinessRecord.data["legacy_record"]["CaseRegisterDate"].as_string(),
    ).where(*conditions))).all()
    dated = [SimpleNamespace(id=row[0], created_at=row[1], data={
        "case_register_date": row[2], "legacy_record": {"CaseRegisterDate": row[3]},
    }) for row in date_rows]
    latest_ids = [item.id for item in sorted(dated, key=lambda item: (_dashboard_case_date(item), item.id), reverse=True)[:13]]
    latest_map = {item.id: item for item in (await db.scalars(select(BusinessRecord).where(
        *conditions, BusinessRecord.id.in_(latest_ids),
    ))).all()} if latest_ids else {}
    latest_case_records = [latest_map[item_id] for item_id in latest_ids]
    today = date.today()
    cutoff = today + timedelta(days=100)
    scheduled_ids = select(HearingSchedule.case_record_id).where(
        HearingSchedule.hearing_date >= today, HearingSchedule.hearing_date <= cutoff,
    )
    hearing_keys = [f"{prefix}_court_hearing_date" for prefix, _ in _CASE_HEARING_LEVELS]
    hearing_keys.extend(("hearing_date", "next_hearing_date"))
    from app.core.dashboard_scope import company_hearing_conditions
    hearing_conditions = await company_hearing_conditions(identity, db)
    cases = list((await db.scalars(select(BusinessRecord).where(*hearing_conditions, or_(
        BusinessRecord.id.in_(scheduled_ids),
        *(func.coalesce(BusinessRecord.data[key].as_string(), "") != "" for key in hearing_keys),
    )))).all())
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
    latest_cases = [
        _dashboard_latest_case_row(
            item,
            _dashboard_customer_for_case(item, customers_by_id, customers_by_no, customers_by_name),
            users_by_username,
        )
        for item in latest_case_records
    ]
    return {"case_trend": case_trend, "civil_distribution": civil_distribution, "hearings": hearings, "latest_cases": latest_cases}
