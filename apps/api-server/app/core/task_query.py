"""普通任务列表的跨数据库查询条件及筛选关联轻投影。"""

from types import SimpleNamespace
from collections.abc import AsyncIterator

from sqlalchemy import Float, Integer, and_, case, cast, false, func, literal_column, or_, select

from app.core.constants import CASE_DEFENDANT_FIELDS, CASE_PLAINTIFF_FIELDS
from app.models import BusinessRecord, VipTask


PYTHON_WHITESPACE = "".join(map(chr, (
    *range(9, 14), *range(28, 33), 133, 160, 5760,
    *range(8192, 8203), 8232, 8233, 8239, 8287, 12288,
)))


def vip_collaborator_conditions(dialect: str, username: str):
    """数组字符串成员走 SQL；历史异形 JSON 由轻投影保留 Python 成员语义。"""
    if dialect == "postgresql":
        kind = func.json_typeof(VipTask.collaborators)
        array_value = case(
            (kind == "array", VipTask.collaborators),
            else_=literal_column("'[]'::json"),
        )
        values = func.json_array_elements(array_value).table_valued("value")
        text_values = func.json_array_elements_text(array_value).table_valued("value")
        non_string = select(1).select_from(values).where(func.json_typeof(values.c.value) != "string").exists()
        member = select(1).select_from(text_values).where(text_values.c.value == username).exists()
    elif dialect == "sqlite":
        kind = func.json_type(VipTask.collaborators)
        values = func.json_each(VipTask.collaborators).table_valued("value", "type")
        non_string = select(1).select_from(values).where(values.c.type != "text").exists()
        member = select(1).select_from(values).where(values.c.type == "text", values.c.value == username).exists()
    else:
        raise RuntimeError(f"不支持的 VIP 任务查询数据库方言：{dialect}")
    legacy_shape = or_(kind != "array", non_string)
    return member, legacy_shape


def _task_json_values(dialect: str):
    if dialect == "postgresql":
        def json_type(key: str):
            return func.coalesce(func.json_typeof(BusinessRecord.data[key]), "")

        string_type = "string"
        numeric_types = ("number",)
        true_type = "boolean"
    elif dialect == "sqlite":
        def json_type(key: str):
            return func.coalesce(func.json_type(BusinessRecord.data, f"$.{key}"), "")

        string_type = "text"
        numeric_types = ("integer", "real")
        true_type = "true"
    else:
        raise RuntimeError(f"不支持的任务列表数据库方言：{dialect}")

    def json_text(key: str):
        return func.coalesce(BusinessRecord.data[key].as_string(), "")

    def truthy(key: str):
        kind = json_type(key)
        value = json_text(key)
        return case(
            (kind == string_type, value != ""),
            (kind.in_(numeric_types), cast(value, Float) != 0),
            (kind == true_type, value.in_(("true", "1")) if dialect == "postgresql" else true_type == "true"),
            (kind == "array", value != "[]"),
            (kind == "object", value != "{}"),
            else_=false(),
        )

    return json_text, truthy


def task_not_investigation_condition(dialect: str):
    """与 _is_investigation_task 的历史 JSON 真值和 strip 规则保持一致。"""
    json_text, truthy = _task_json_values(dialect)

    def stripped(key: str):
        return truthy(key) & (func.trim(json_text(key), PYTHON_WHITESPACE) != "")

    business_type = case(
        (truthy("task_business_type"), json_text("task_business_type")),
        else_=json_text("business_type"),
    )
    is_investigation = or_(
        truthy("investigation_record_id"),
        stripped("investigation_no"),
        func.trim(json_text("investigation_module"), PYTHON_WHITESPACE) == "investigation",
        func.trim(json_text("source"), PYTHON_WHITESPACE).in_(("调查任务", "调查子任务")),
        func.trim(business_type, PYTHON_WHITESPACE).in_(("调查任务", "调查子任务")),
    )
    return ~is_investigation


def task_canonical_deadline(dialect: str):
    """只为严格 ISO 日期提供 SQL 排序；其它历史日期交由 Python 原解析器处理。"""
    json_text, truthy = _task_json_values(dialect)
    raw = case(
        (truthy("deadline"), json_text("deadline")),
        (truthy("task_end_time"), json_text("task_end_time")),
        else_=json_text("TaskEndTime"),
    )
    if dialect == "postgresql":
        shape = raw.op("~")(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    else:
        shape = raw.op("GLOB")("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]")
    year = case((shape, cast(func.substr(raw, 1, 4), Integer)), else_=0)
    month = case((shape, cast(func.substr(raw, 6, 2), Integer)), else_=0)
    day = case((shape, cast(func.substr(raw, 9, 2), Integer)), else_=0)
    leap_year = and_(year % 4 == 0, or_(year % 100 != 0, year % 400 == 0))
    month_days = case(
        (month.in_((1, 3, 5, 7, 8, 10, 12)), 31),
        (month.in_((4, 6, 9, 11)), 30),
        (month == 2, case((leap_year, 29), else_=28)),
        else_=0,
    )
    canonical = and_(shape, year.between(1, 9999), month.between(1, 12), day.between(1, month_days))
    return raw, canonical


async def task_employee_names(db) -> dict[str, str]:
    """只读员工展示字段，保留原有同账号后出现的名称覆盖顺序。"""
    rows = (await db.execute(select(
        BusinessRecord.owner, BusinessRecord.title, BusinessRecord.data["username"],
    ).where(
        BusinessRecord.module == "hr", BusinessRecord.status.not_in({"离职", "停用"}),
    ))).all()
    names = {}
    for owner, title, username in rows:
        key = str(username or owner or "").strip().lower()
        if key:
            names[key] = str(title or "").strip()
    return names


async def enrich_task_filter_rows(rows: list[dict], db, *, employee_names: dict[str, str] | None, need_cases: bool) -> None:
    """只计算搜索需要的人员和案件字段，不构造完整任务响应。"""
    if not rows:
        return
    if employee_names is not None:
        from app.core.formatters import _person_reference_display, _user_display_map

        usernames = {row["owner"] for row in rows}
        usernames.update(row["initiator"] for row in rows if "initiator" in row["_data"])
        users = await _user_display_map(usernames, db)
        for row in rows:
            owner_name = _person_reference_display(row["owner"], users)[0]
            row["owner_display_name"] = employee_names.get(str(row["owner"] or "").strip().lower()) or owner_name
            if "initiator" in row["_data"]:
                row["initiator_display_name"] = _person_reference_display(row["initiator"], users)[0]
    if not need_cases:
        return

    from app.core.cases import _case_party_values

    case_ids: set[int] = set()
    case_nos: set[str] = set()
    for row in rows:
        data = row["_data"]
        raw_ids = data.get("case_ids") if isinstance(data.get("case_ids"), list) else []
        for raw_id in [data.get("case_record_id") or data.get("case_id"), *raw_ids]:
            try:
                if raw_id:
                    case_ids.add(int(raw_id))
            except (TypeError, ValueError):
                pass
        raw_nos = data.get("case_nos") if isinstance(data.get("case_nos"), list) else []
        for raw_no in [data.get("case_no"), *raw_nos]:
            case_no = str(raw_no or "").strip()
            if case_no:
                case_nos.add(case_no)
    conditions = []
    if case_ids:
        conditions.append(BusinessRecord.id.in_(case_ids))
    if case_nos:
        conditions.append(BusinessRecord.serial_no.in_(case_nos))
    case_data_fields = tuple(dict.fromkeys((*CASE_PLAINTIFF_FIELDS, *CASE_DEFENDANT_FIELDS)))
    cases = []
    if conditions:
        values = (await db.execute(select(
            BusinessRecord.id, BusinessRecord.serial_no, BusinessRecord.customer,
            *(BusinessRecord.data[key] for key in case_data_fields),
        ).where(BusinessRecord.module.in_({"case", "ipr_case"}), or_(*conditions)))).all()
        cases = [SimpleNamespace(
            id=value[0], serial_no=value[1], customer=value[2],
            data={key: item for key, item in zip(case_data_fields, value[3:]) if item is not None},
        ) for value in values]
    by_id = {item.id: item for item in cases}
    by_no = {item.serial_no: item for item in cases}
    for row in rows:
        data = row["_data"]
        linked = []
        raw_ids = data.get("case_ids") if isinstance(data.get("case_ids"), list) else []
        for raw_id in [data.get("case_record_id") or data.get("case_id"), *raw_ids]:
            try:
                item = by_id.get(int(raw_id)) if raw_id else None
            except (TypeError, ValueError):
                item = None
            if item and item not in linked:
                linked.append(item)
        raw_nos = data.get("case_nos") if isinstance(data.get("case_nos"), list) else []
        for raw_no in [data.get("case_no"), *raw_nos]:
            item = by_no.get(str(raw_no or "").strip())
            if item and item not in linked:
                linked.append(item)
        if linked:
            first = linked[0]
            row["case_no"] = first.serial_no
            row["plaintiff"] = "、".join(_case_party_values(first.data, CASE_PLAINTIFF_FIELDS)) or row["plaintiff"] or first.customer
            row["defendant"] = "、".join(_case_party_values(first.data, CASE_DEFENDANT_FIELDS)) or row["defendant"]
        row["case_nos"] = [item.serial_no for item in linked]


async def stream_task_rows(
    db, conditions: list, columns: tuple[str, ...], data_fields: tuple[str, ...],
    presence_fields: tuple[str, ...], *, after_id: int = 0, limit: int | None = None,
) -> AsyncIterator[SimpleNamespace]:
    """分批读取指定轻字段，并保留 JSON 显式 null 与缺键的差异。"""
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        presence = [func.json_typeof(BusinessRecord.data[key]) for key in presence_fields]
    elif dialect == "sqlite":
        presence = [func.json_type(BusinessRecord.data, f"$.{key}") for key in presence_fields]
    else:
        raise RuntimeError(f"不支持的任务列表数据库方言：{dialect}")
    query = select(
        *(getattr(BusinessRecord, key) for key in columns),
        *(BusinessRecord.data[key] for key in data_fields),
        *presence,
    ).where(*conditions, BusinessRecord.id > after_id).order_by(BusinessRecord.id)
    if limit is not None:
        query = query.limit(limit)
    query = query.execution_options(yield_per=256)
    result = await db.stream(query)
    try:
        async for values in result:
            data_end = len(columns) + len(data_fields)
            present = {key for key, kind in zip(presence_fields, values[data_end:]) if kind is not None}
            data = {
                key: value for key, value in zip(data_fields, values[len(columns):data_end])
                if value is not None or key in present
            }
            yield SimpleNamespace(**dict(zip(columns, values[:len(columns)])), data=data)
    finally:
        await result.close()


def task_scope_visible(task, scope: str, relation: str, username: str, department_usernames: set[str]) -> bool:
    """保留现有任务页面的人员关系二次校验。"""
    data = task.data or {}
    if scope in {"mine", "default"}:
        if not (task.owner == username or data.get("initiator") == username or username in data.get("collaborators", [])):
            return False
        if relation == "initiated":
            return data.get("initiator") == username
        if relation == "owned":
            return task.owner == username
        if relation == "collaborating":
            return username in data.get("collaborators", [])
    elif scope == "department":
        if relation == "owned":
            return task.owner in department_usernames
        if relation == "collaborating":
            return bool(department_usernames.intersection(data.get("collaborators", [])))
        return data.get("initiator") in department_usernames
    elif relation == "collaborating":
        return bool(data.get("collaborators", []))
    return True


def task_filter_row(task, relation: str) -> dict:
    """只生成筛选、排序和动态统计字段。"""
    from app.core.tasks import _task_creation_mode, _task_schedule_state

    data = task.data or {}
    deadline, days_remaining, effective_status, reminder_due, _ = _task_schedule_state(task)
    source = data.get("source", "日常任务")
    if relation == "initiated" and task.status in {"待接收", "待处理"} and source == "案件任务":
        effective_status = "进行中"
    return {
        "id": task.id, "serial_no": task.serial_no, "title": task.title,
        "customer": task.customer, "description": task.description,
        "owner": task.owner, "created_at": task.created_at, "updated_at": task.updated_at,
        "status": effective_status, "deadline": deadline, "days_remaining": days_remaining,
        "reminder_due": reminder_due, "source": source,
        "priority": data.get("priority", "普通"),
        "creation_mode": _task_creation_mode(data),
        "initiator": data.get("initiator", ""),
        "case_no": str(data.get("case_no") or "").strip(), "case_nos": [],
        "plaintiff": data.get("plaintiff", ""), "defendant": data.get("defendant", ""),
        "_data": data,
    }


def add_task_summary(summary: dict[str, int], row: dict) -> None:
    """累加原任务列表在文本筛选之前展示的动态汇总。"""
    status = row["status"]
    summary["total"] += 1
    if status in {"待接收", "待处理"}:
        summary["pending"] += 1
    if status in {"处理中", "进行中"}:
        summary["processing"] += 1
    if status == "已完成":
        summary["awaiting_confirmation"] += 1
    if row["days_remaining"] in {0, 1} and status not in {"已完成", "已撤回"}:
        summary["due_soon"] += 1
    if status == "已逾期":
        summary["overdue"] += 1
    if row["reminder_due"]:
        summary["reminders"] += 1
