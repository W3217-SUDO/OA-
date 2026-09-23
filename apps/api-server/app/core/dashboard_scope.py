"""控制台业务入口的数据边界；不授予额外写权限。"""
from fastapi import HTTPException
from sqlalchemy import false, or_, select
from app.models import BusinessRecord, ContractObject, Department, User
from app.core.permissions import (
    _case_mine_scope_condition, _configured_user_job_role_name,
    _job_role_for_name, _system_user_role_ids,
)

CASE_QUEUES = {
    "evidence-supplement": "supplement_evidence",
    "opinion-supplement": "supplement_opinion",
    "appeal-pending": "pending_appeal",
    "execution-pending": "pending_execution",
    "urgent-cases": "urgent",
}
QUEUE_KEYS = {*CASE_QUEUES, "official-fee-unpaid", "refund-pending", "official-fee-unreceived"}


async def company_hearing_conditions(identity, db):
    user = await db.scalar(select(User).where(User.username == identity['username'], User.is_active.is_(True)))
    if user is None:
        raise HTTPException(401, '当前用户不存在或已停用')
    departments = list((await db.scalars(select(Department))).all())
    blocked = {item.id for item in departments if ''.join(item.name.split()) in {'合作律师部', '外部合作调查取证部'}}
    while True:
        expanded = blocked | {item.id for item in departments if item.parent_department_id in blocked}
        if expanded == blocked:
            break
        blocked = expanded
    excluded = {item.name for item in departments if item.id in blocked}
    if not user.department or user.department in excluded or ''.join(user.department.split()) in {'合作律师部', '外部合作调查取证部'}:
        return [false()]
    return [BusinessRecord.module == 'case', BusinessRecord.status.notin_(['已合并', '已删除', '已回收'])]


async def dashboard_identity(identity, db):
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if user is None or not user.is_active:
        raise HTTPException(401, "当前用户不存在或已停用")
    roles = _system_user_role_ids(user)
    role = await _job_role_for_name(_configured_user_job_role_name(user), db)
    all_cases = "admin" in roles or bool(role and role.name == "财务审核管理")
    conditions = [BusinessRecord.module == "case", BusinessRecord.status.notin_(["已合并", "已删除", "已回收"])]
    if not all_cases:
        owned_contracts = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "contract", BusinessRecord.owner == user.username,
            BusinessRecord.status.notin_(["已回收", "已删除"]),
        ))).all())
        owned_ids = {item.id for item in owned_contracts}
        owned_nos = {item.serial_no for item in owned_contracts}
        linked_cases = select(ContractObject.case_record_id).where(ContractObject.contract_record_id.in_(owned_ids))
        conditions.append(or_(
            await _case_mine_scope_condition(identity, db),
            BusinessRecord.id.in_(linked_cases),
            BusinessRecord.data['contract_id'].as_integer().in_(owned_ids),
            BusinessRecord.data['contract_record_id'].as_integer().in_(owned_ids),
            BusinessRecord.data['contract_no'].as_string().in_(owned_nos),
        ))
    cases = list((await db.scalars(select(BusinessRecord).where(*conditions))).all())
    case_ids = {item.id for item in cases}
    case_nos = {item.serial_no for item in cases}
    fees = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance", BusinessRecord.status != "已删除",
        or_(BusinessRecord.data["case_id"].as_integer().in_(case_ids),
            BusinessRecord.data["case_record_id"].as_integer().in_(case_ids),
            BusinessRecord.data["case_no"].as_string().in_(case_nos)),
    ))).all()) if case_ids else []
    contract_ids = set((await db.scalars(select(ContractObject.contract_record_id).where(
        ContractObject.case_record_id.in_(case_ids),
    ))).all()) if case_ids else set()
    contract_nos = set()
    for item in [*cases, *fees]:
        data = item.data or {}
        for key in ("contract_id", "contract_record_id"):
            value = str(data.get(key) or "")
            if value.isdigit():
                contract_ids.add(int(value))
        if data.get("contract_no"):
            contract_nos.add(str(data["contract_no"]))
    contracts = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "contract",
        or_(BusinessRecord.id.in_(contract_ids), BusinessRecord.serial_no.in_(contract_nos)),
    ))).all()) if contract_ids or contract_nos else []
    return {
        **identity, "role": roles[0], "role_ids": roles, "_page_menu_capability": False,
        "_dashboard_case_ids": case_ids,
        "_dashboard_fee_ids": {item.id for item in fees},
        "_dashboard_record_ids": {item.id for item in [*cases, *fees, *contracts]},
    }


async def dashboard_request_identity(queue, expected, identity, db):
    if not queue:
        return identity
    if queue not in expected:
        raise HTTPException(422, "控制台业务入口无效")
    scoped_identity = await dashboard_identity(identity, db)
    if queue == "urgent-cases":
        cases = await dashboard_urgent_cases(identity, db, scoped_identity["_dashboard_case_ids"])
        case_ids = {case.id for case in cases}
        scoped_identity["_dashboard_case_ids"] = case_ids
        scoped_identity["_dashboard_record_ids"] = case_ids
    return scoped_identity


async def dashboard_urgent_cases(identity, db, personal_case_ids):
    """紧急案件沿用公司案件菜单权限，否则只取本人可见案件。"""
    from app.core.permissions import _can_search_all_cases_from_global_search

    conditions = [
        BusinessRecord.module == "case",
        BusinessRecord.status.notin_(["已合并", "已删除", "已回收"]),
    ]
    if not await _can_search_all_cases_from_global_search(identity, db):
        conditions.append(BusinessRecord.id.in_(personal_case_ids))
    return list((await db.scalars(select(BusinessRecord).where(*conditions))).all())


async def dashboard_receivables(identity, db):
    from app.core.projections import _receivable_detail_projection
    rows = await _receivable_detail_projection(identity, db)
    return [row for row in rows if row["fee_category"] == "official" and row["remaining_amount"] > 0]


async def dashboard_fee_cases(rows, identity, db):
    """返回当前费用页的真实关联案件，供原有批量操作使用。"""
    from app.core.system import _record_dict, _allowed_field_keys
    case_ids = {row["data"].get("case_id") for row in rows} & identity["_dashboard_case_ids"]
    cases = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(case_ids)))).all()) if case_ids else []
    fields = await _allowed_field_keys(identity, db)
    return {"cases": [_record_dict(case, fields) for case in cases]}
