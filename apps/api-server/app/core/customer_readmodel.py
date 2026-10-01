"""客户列表的汇总和关系投影，不加载无关业务完整载荷。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cases import _is_civil_case_type
from app.core.formatters import _normalize_customer_name
from app.models import BusinessRecord, User


async def customer_summary(db: AsyncSession, conditions: list, fields: list[str]) -> dict[str, float]:
    totals = dict.fromkeys(fields, 0.0)
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


async def customer_relationship_counts(db: AsyncSession, page_items: list) -> dict[int, dict[str, int]]:
    by_id = {item.id: item for item in page_items}
    by_no = {str(item.serial_no or "").strip(): item for item in page_items if str(item.serial_no or "").strip()}
    by_name = {_normalize_customer_name(item.title): item for item in page_items}
    counts = {item.id: {"contract_count": 0, "civil_case_count": 0} for item in page_items}
    fields = ("customer_id", "customer_record_id", "customer_no", "case_type")
    statement = select(
        BusinessRecord.module, BusinessRecord.status, BusinessRecord.customer,
        *(BusinessRecord.data[key] for key in fields),
    ).where(BusinessRecord.module.in_(["contract", "case"])).execution_options(yield_per=400)
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
