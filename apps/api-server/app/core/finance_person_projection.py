"""财务只读人员名称投影，不改动身份键和外部收付款单位。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BusinessRecord, User
from app.core.constants import CONTRACT_PERSON_NAME_PLACEHOLDER, PERSON_NAME_PLACEHOLDER
from app.core.formatters import _person_reference_display, _user_display_map


PERSON_FIELDS = (
    "applicant", "paid_by", "payment_operator", "submitted_by", "handler",
    "handling_lawyer", "lawyer_assistant", "case_source", "investigator",
    "customer_manager", "quality_manager",
)
PAYMENT_FIELDS = ("payee", "payment_target", "payer")


def _payment_user_id(value: object) -> int | None:
    # 仅解析显式用户主键，不把旧支付对象编号或银行账号猜作新用户 ID。
    if type(value) is int or isinstance(value, str) and value.strip().isascii() and value.strip().isdigit():
        number = int(value)
        if 0 < number <= 2147483647:
            return number
    return None


def _payloads(rows: list[dict]):
    for row in rows:
        if isinstance(row.get("data"), dict):
            row["data"] = dict(row["data"])
        data = row.get("data") if isinstance(row.get("data"), dict) else row
        yield data
        for key in ("application_items", "commission_details", "details", "items"):
            children = data.get(key)
            if isinstance(children, list):
                data[key] = [dict(child) if isinstance(child, dict) else child for child in children]
                yield from _payloads([child for child in data[key] if isinstance(child, dict)])


async def apply_finance_person_displays(rows: list[dict], db: AsyncSession) -> list[dict]:
    """只在授权后的返回值补显示字段；离职员工仍通过账号精确解析。"""
    payloads = list(_payloads(rows))
    fields = PERSON_FIELDS + PAYMENT_FIELDS
    usernames = {
        str(data[key]).strip() for data in payloads for key in fields
        if isinstance(data.get(key), str) and data[key].strip()
    }
    usernames.update(
        data[f"{key}_username"].strip() for data in payloads for key in PAYMENT_FIELDS
        if isinstance(data.get(f"{key}_username"), str) and data[f"{key}_username"].strip()
    )
    users = await _user_display_map(usernames, db)
    user_ids = {_payment_user_id(data.get(f"{key}_user_id")) for data in payloads for key in PAYMENT_FIELDS}
    user_ids.discard(None)
    users_by_id = {user.id: user for user in (await db.scalars(
        select(User).where(User.id.in_(user_ids))
    )).all()} if user_ids else {}
    for data in payloads:
        for key in fields:
            username = data.get(f"{key}_username") if key in PAYMENT_FIELDS else None
            username = username.strip() if isinstance(username, str) else ""
            user_id = data.get(f"{key}_user_id") if key in PAYMENT_FIELDS else None
            has_user_id = user_id is not None and user_id != ""
            if key not in data and not username and not has_user_id:
                continue
            if not isinstance(data.get(key), (str, int, type(None))):
                continue
            explicit = str(data.get(f"{key}_display_name") or "").strip()
            if (not data.get(f"{key}_display_name_missing")
                    and explicit not in {PERSON_NAME_PLACEHOLDER, CONTRACT_PERSON_NAME_PLACEHOLDER}
                    and any("\u3400" <= char <= "\u9fff" for char in explicit)):
                continue
            raw = str(data.get(key) or "").strip()
            if username:
                label, missing = _person_reference_display(username, users)
            elif has_user_id:
                user = users_by_id.get(_payment_user_id(user_id))
                label, missing = _person_reference_display(
                    user.username if user else str(user_id), {user.username.lower(): user} if user else {},
                )
            # 收付款单位允许自由文本，只有精确命中账号才转成人员名称。
            elif raw.lower() not in users and (key in PAYMENT_FIELDS or any("\u4e00" <= char <= "\u9fff" for char in raw)):
                label, missing = raw, False
            else:
                label, missing = _person_reference_display(raw, users)
            data[f"{key}_display_name"] = label
            data[f"{key}_display_name_missing"] = missing
    return rows


async def finance_print_records(records: list[BusinessRecord], db: AsyncSession) -> list[BusinessRecord]:
    """打印器使用独立的展示副本，不改 ORM 对象或审批使用的原账号。"""
    rows = [{"data": {**(record.data or {}), "applicant": (record.data or {}).get("applicant") or record.owner,
                       "submitted_by": (record.data or {}).get("submitted_by") or record.owner}}
            for record in records]
    await apply_finance_person_displays(rows, db)
    for data in _payloads(rows):
        for key in PERSON_FIELDS + PAYMENT_FIELDS:
            if data.get(f"{key}_display_name"):
                data[key] = data[f"{key}_display_name"]
    return [BusinessRecord(id=record.id, module=record.module, serial_no=record.serial_no,
                           title=record.title, customer=record.customer, status=record.status,
                           owner=record.owner, department=record.department, description=record.description,
                           data=row["data"])
            for record, row in zip(records, rows)]
