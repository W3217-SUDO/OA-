"""控制台业务入口的数据边界；不授予额外写权限。"""
from dataclasses import dataclass
import re

from fastapi import HTTPException
from sqlalchemy import false, or_, select
from app.models import BusinessRecord, ContractObject, Department, User
from app.core.record_projection_query import read_record_projections
from app.core.finance_summary_query import FEE_SUMMARY_FIELDS
from app.core.json_relation_query import scalar_in_values
from app.core.request_metrics import measure_phase
from app.core.permissions import (
    CASE_MINE_TEXT_FIELDS,
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


@dataclass
class DashboardScopeData:
    """仅供本次请求复用的授权范围和轻量数据，不跨账号或请求缓存。"""

    identity: dict
    cases: list
    fees: list
    contracts: list
    all_cases: bool
    personal_case_ids: set[int] | None = None


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


async def dashboard_identity(identity, db, *, personal_cases=False):
    scope = await load_dashboard_scope(identity, db, personal_cases=personal_cases)
    return scope.identity


async def load_dashboard_scope(identity, db, *, personal_cases=False, include_summaries=False):
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if user is None or not user.is_active:
        raise HTTPException(401, "当前用户不存在或已停用")
    roles = _system_user_role_ids(user)
    role = await _job_role_for_name(_configured_user_job_role_name(user), db)
    all_cases = "admin" in roles or bool(role and role.name == "财务审核管理")
    conditions = [BusinessRecord.module == "case", BusinessRecord.status.notin_(["已合并", "已删除", "已回收"])]
    if personal_cases:
        conditions.append(await _case_mine_scope_condition(identity, db))
    elif not all_cases:
        owned_contracts = (await db.execute(select(BusinessRecord.id, BusinessRecord.serial_no).where(
            BusinessRecord.module == "contract", BusinessRecord.owner == user.username,
            BusinessRecord.status.notin_(["已回收", "已删除"]),
        ))).all()
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
    relation_fields = ("contract_id", "contract_record_id", "contract_no")
    case_fields = (*relation_fields, "case_type", "case_phase_name", "case_phase", "case_stage", "business_stage")
    async def personal_annotation(data):
        return {"dashboard_personal": await _case_mine_scope_condition(identity, db, projected_data=data)}

    with measure_phase("dashboard.scope.cases"):
        cases = await read_record_projections(
            db, conditions, case_fields if include_summaries else relation_fields,
            legacy_fields=("CasePhaseName",) if include_summaries else (),
            text_fields=CASE_MINE_TEXT_FIELDS if include_summaries else (),
            annotations=personal_annotation if include_summaries else None,
        )
    case_ids = {item.id for item in cases}
    case_nos = {item.serial_no for item in cases}
    def related_fee(data):
        return [or_(scalar_in_values(data["case_id"].as_integer(), case_ids),
                    scalar_in_values(data["case_record_id"].as_integer(), case_ids),
                    scalar_in_values(data["case_no"].as_string(), case_nos))]

    with measure_phase("dashboard.scope.fees"):
        fees = await read_record_projections(db, [
            BusinessRecord.module == "finance", BusinessRecord.status != "已删除",
        ], FEE_SUMMARY_FIELDS if include_summaries else (*relation_fields, "case_id", "case_record_id", "case_no"),
            where_data=related_fee) if case_ids else []
    contract_ids = set((await db.scalars(select(ContractObject.contract_record_id).where(
        scalar_in_values(ContractObject.case_record_id, case_ids),
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
    contract_conditions = [
        BusinessRecord.module == "contract",
        or_(scalar_in_values(BusinessRecord.id, contract_ids), scalar_in_values(BusinessRecord.serial_no, contract_nos)),
    ]
    contracts = []
    if include_summaries:
        contracts = await read_record_projections(
            db, contract_conditions, ("contract_body", "signed_at", "source_person"),
        ) if contract_ids or contract_nos else []
        visible_contract_ids = {item.id for item in contracts}
    else:
        visible_contract_ids = set((await db.scalars(select(BusinessRecord.id).where(
            *contract_conditions,
        ))).all()) if contract_ids or contract_nos else set()
    scoped_identity = {
        **identity, "role": roles[0], "role_ids": roles, "_page_menu_capability": False,
        "_dashboard_case_ids": case_ids,
        "_dashboard_fee_ids": {item.id for item in fees},
        "_dashboard_record_ids": case_ids | {item.id for item in fees} | visible_contract_ids,
    }
    personal_ids = {case.id for case in cases if case.dashboard_personal} if include_summaries else None
    return DashboardScopeData(scoped_identity, cases, fees, contracts, all_cases and not personal_cases, personal_ids)


async def dashboard_request_identity(queue, expected, identity, db):
    if not queue:
        return identity
    if queue not in expected:
        raise HTTPException(422, "控制台业务入口无效")
    scoped_identity = await dashboard_identity(identity, db, personal_cases=queue == "refund-pending")
    if queue == "urgent-cases":
        cases = await dashboard_urgent_cases(identity, db, scoped_identity["_dashboard_case_ids"])
        case_ids = {case.id for case in cases}
        scoped_identity["_dashboard_case_ids"] = case_ids
        scoped_identity["_dashboard_record_ids"] = case_ids
    return scoped_identity


def _possible_refund_fee(fee, case_ids, case_nos):
    """已读字段只缩小候选编号，最终权限与类型转换仍交给原 SQL 确认。"""
    data = fee.data or {}
    number = data.get("case_no")
    if isinstance(number, str):
        if number in case_nos:
            return True
    elif number is not None:
        return True
    for key in ("case_id", "case_record_id"):
        value = data.get(key)
        if value is None:
            continue
        if type(value) is int:
            candidate = value
        elif isinstance(value, str) and re.fullmatch(r"[+-]?[0-9]+", value.strip()):
            candidate = int(value)
        else:
            return True
        if candidate in case_ids:
            return True
    return False


async def personal_refund_identity(scoped_identity, db, *, scope_data=None):
    """从已经加载的控制台范围收窄退款范围，不重复投影合同和费用详情。"""
    if scope_data is not None and scope_data.personal_case_ids is not None:
        cases = [case for case in scope_data.cases if case.id in scope_data.personal_case_ids]
    else:
        case_query = select(BusinessRecord.id, BusinessRecord.serial_no).where(
            BusinessRecord.id.in_(scoped_identity["_dashboard_case_ids"]),
            await _case_mine_scope_condition(scoped_identity, db),
        )
        cases = (await db.execute(case_query)).all()
    case_ids = {case.id for case in cases}
    case_nos = {case.serial_no for case in cases}
    candidate_ids = scoped_identity["_dashboard_fee_ids"]
    if scope_data is not None:
        candidate_ids = {fee.id for fee in scope_data.fees if fee.id in candidate_ids
                         and _possible_refund_fee(fee, case_ids, case_nos)}
    fee_ids = set((await db.scalars(select(BusinessRecord.id).where(
        BusinessRecord.id.in_(candidate_ids),
        or_(BusinessRecord.data["case_id"].as_integer().in_(case_ids),
            BusinessRecord.data["case_record_id"].as_integer().in_(case_ids),
            BusinessRecord.data["case_no"].as_string().in_(case_nos)),
    ))).all()) if case_ids and candidate_ids else set()
    return {**scoped_identity, "_dashboard_case_ids": case_ids,
            "_dashboard_fee_ids": fee_ids, "_dashboard_record_ids": case_ids | fee_ids}


async def dashboard_urgent_cases(identity, db, personal_case_ids, *, scope_data=None):
    """紧急案件沿用公司案件菜单权限，否则只取本人可见案件。"""
    from app.core.permissions import _can_search_all_cases_from_global_search

    conditions = [
        BusinessRecord.module == "case",
        BusinessRecord.status.notin_(["已合并", "已删除", "已回收"]),
    ]
    can_search_all = await _can_search_all_cases_from_global_search(identity, db)
    if scope_data is not None and (not can_search_all or scope_data.all_cases):
        return scope_data.cases
    if not can_search_all:
        conditions.append(BusinessRecord.id.in_(personal_case_ids))
    return await dashboard_queue_cases(db, conditions)


async def dashboard_queue_cases(db, conditions):
    return await read_record_projections(
        db, conditions, ("case_type", "case_phase_name", "case_phase"),
        legacy_fields=("CasePhaseName",),
    )


async def dashboard_receivables(identity, db, *, records=None):
    from app.core.projections import _receivable_detail_projection
    rows = await _receivable_detail_projection(identity, db, records=records)
    return [row for row in rows if row["fee_category"] == "official" and row["remaining_amount"] > 0]


async def dashboard_fee_cases(rows, identity, db):
    """返回当前费用页的真实关联案件，供原有批量操作使用。"""
    from app.core.system import _record_dict, _allowed_field_keys
    case_ids = {row["data"].get("case_id") for row in rows} & identity["_dashboard_case_ids"]
    cases = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(case_ids)))).all()) if case_ids else []
    fields = await _allowed_field_keys(identity, db)
    return {"cases": [_record_dict(case, fields) for case in cases]}
