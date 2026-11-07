"""控制台业务入口的数据边界；不授予额外写权限。"""
from dataclasses import dataclass
from datetime import datetime
from itertools import chain
from typing import NamedTuple
import re

from fastapi import HTTPException
from sqlalchemy import and_, false, literal_column, or_, select
from app.models import BusinessRecord, ContractObject, Department, User
from app.core.record_projection_query import read_record_projections
from app.core.finance_summary_query import FEE_SUMMARY_FIELDS
from app.core.json_relation_query import scalar_in_values
from app.core.request_metrics import measure_phase
from app.core.dashboard_finance_read_model import read_dashboard_finance_fee_pool
from app.core.fee_receipt_pool import FeeReceiptPool
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


class DashboardFeeProjection(NamedTuple):
    """控制台费用的只读元数据；字段和值与通用投影保持一致。"""

    id: int
    module: str
    serial_no: str
    title: str
    customer: str
    status: str
    owner: str
    department: str
    description: str
    created_at: datetime
    updated_at: datetime
    data: dict


class DashboardFinanceCaseProjection(NamedTuple):
    """财务三卡只消费案件编号、名称、状态和合同关系。"""

    id: int
    module: str
    serial_no: str
    title: str
    status: str
    data: dict


class DashboardFinanceFeeProjection(NamedTuple):
    """财务三卡费用保留原状态、类型回退、更新时间排序及完整摘要。"""

    id: int
    module: str
    serial_no: str
    title: str
    status: str
    updated_at: datetime
    data: dict


@dataclass
class DashboardScopeData:
    """仅供本次请求复用的授权范围和轻量数据，不跨账号或请求缓存。"""

    identity: dict
    cases: list
    fees: list
    contracts: list
    all_cases: bool
    personal_case_ids: set[int] | None = None
    finance_pool: FeeReceiptPool | None = None


async def company_hearing_conditions(identity, db, *, company: bool = False):
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
    conditions = [BusinessRecord.module == 'case', BusinessRecord.status.notin_(['已合并', '已删除', '已回收'])]
    # 开庭排期分“个人 / 全所”两个页签（陶国南 11-01 定）：默认“个人”= 我的案件（本人办理的案件和本人作为
    # 客户管理人/协作人的客户的案件），管理员也一样；所有人都能切到“全所”看全公司。
    if company:
        return conditions
    from app.core.permissions import _coordinated_case_condition
    return [*conditions, or_(
        await _case_mine_scope_condition(identity, db),
        _coordinated_case_condition(user.username, db.get_bind().dialect.name),
    )]


async def dashboard_company_account(user, db) -> bool:
    """工作台数字按全公司算的管理员类账号（陶国南 11-01 定）：系统角色 admin，或岗位“财务审核管理”。

    被驳回数不受影响，仍只算本人（见 dashboard_todos.REJECTED_COUNT_SCOPE）。
    """
    role = await _job_role_for_name(_configured_user_job_role_name(user), db)
    return "admin" in _system_user_role_ids(user) or bool(role and role.name == "财务审核管理")


async def dashboard_identity(identity, db, *, personal_cases=False):
    scope = await load_dashboard_scope(identity, db, personal_cases=personal_cases)
    return scope.identity


async def load_dashboard_scope(identity, db, *, personal_cases=False, include_summaries=False, include_finance=True,
                               finance_metrics=False, light_records=False):
    """light_records：仍按摘要读合同，但案件和费用只读关联字段（集合不变），给只要记录范围的入口用（未到官费，11-07）。"""
    if finance_metrics and (not include_summaries or not include_finance):
        raise ValueError("财务指标读取必须包含费用摘要")
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if user is None or not user.is_active:
        raise HTTPException(401, "当前用户不存在或已停用")
    roles = _system_user_role_ids(user)
    all_cases = await dashboard_company_account(user, db)
    conditions = [BusinessRecord.module == "case", BusinessRecord.status.notin_(["已合并", "已删除", "已回收"])]
    if personal_cases:
        conditions.append(await _case_mine_scope_condition(identity, db))
    elif not all_cases:
        # 本人名下合同的案件也算进本人工作台（陶国南 11-01 定，旧系统不算）。
        owned_contracts = (await db.execute(select(BusinessRecord.id, BusinessRecord.serial_no).where(
            BusinessRecord.module == "contract", BusinessRecord.owner == user.username,
            BusinessRecord.status.notin_(["已回收", "已删除"]),
        ))).all()
        owned_ids = {item.id for item in owned_contracts}
        owned_nos = {item.serial_no for item in owned_contracts}
        linked_cases = select(ContractObject.case_record_id).where(
            scalar_in_values(ContractObject.contract_record_id, owned_ids),
        )
        own_condition = or_(
            await _case_mine_scope_condition(identity, db),
            BusinessRecord.id.in_(linked_cases),
            scalar_in_values(BusinessRecord.data['contract_id'].as_integer(), owned_ids),
            scalar_in_values(BusinessRecord.data['contract_record_id'].as_integer(), owned_ids),
            scalar_in_values(BusinessRecord.data['contract_no'].as_string(), owned_nos),
        )
        # 旧系统工作台按“我的案件”（PageId 100110110）统计，含本人作为客户管理人/协作人的客户的案件（1.2.80 已对齐）。
        from app.core.permissions import _coordinated_case_condition
        conditions.append(or_(own_condition, _coordinated_case_condition(user.username, db.get_bind().dialect.name)))
    relation_fields = ("contract_id", "contract_record_id", "contract_no")
    case_fields = (*relation_fields, "case_type", "case_phase_name", "case_phase", "case_stage", "business_stage")
    async def personal_annotation(data):
        return {"dashboard_personal": await _case_mine_scope_condition(identity, db, projected_data=data)}

    with measure_phase("dashboard.scope.cases"):
        # 财务统计不消费案件阶段或个人标记，退款范围仍由原权限 SQL 单独确认。
        case_summaries = include_summaries and not finance_metrics and not light_records
        cases = await read_record_projections(
            db, conditions, case_fields if case_summaries else relation_fields,
            legacy_fields=("CasePhaseName",) if case_summaries else (),
            text_fields=CASE_MINE_TEXT_FIELDS if case_summaries else (),
            annotations=personal_annotation if case_summaries else None,
            record_factory=DashboardFinanceCaseProjection if finance_metrics else None,
            metadata_fields=("id", "module", "serial_no", "title", "status") if finance_metrics else None,
            select_data_fields=finance_metrics,
        )
    case_ids = {item.id for item in cases}
    case_nos = {item.serial_no for item in cases}
    personal_ids = {case.id for case in cases if case.dashboard_personal} if case_summaries else None
    if not include_finance:
        # 案件指标沿用同一授权范围，独立返回时不等待费用和合同内容读取。
        scoped_identity = {
            **identity, "role": roles[0], "role_ids": roles, "_page_menu_capability": False,
            "_dashboard_case_ids": case_ids, "_dashboard_fee_ids": set(),
            "_dashboard_record_ids": case_ids,
        }
        return DashboardScopeData(scoped_identity, cases, [], [], all_cases and not personal_cases, personal_ids)
    def related_fee(data):
        return [or_(scalar_in_values(data["case_id"].as_integer(), case_ids),
                    scalar_in_values(data["case_record_id"].as_integer(), case_ids),
                    scalar_in_values(data["case_no"].as_string(), case_nos))]

    finance_pool = None
    with measure_phase("dashboard.scope.fees"):
        fee_conditions = [
            BusinessRecord.module == "finance", BusinessRecord.status != "已删除",
        ]
        if finance_metrics and db.get_bind().dialect.name == "postgresql":
            binding_rows, fees = await read_dashboard_finance_fee_pool(
                db, fee_conditions, where_data=related_fee,
            ) if case_ids else ([], [])
            finance_pool = FeeReceiptPool.from_rows(binding_rows)
        else:
            fees = await read_record_projections(
                db, fee_conditions,
                FEE_SUMMARY_FIELDS if include_summaries and not light_records
                else (*relation_fields, "case_id", "case_record_id", "case_no"),
                where_data=related_fee,
                filter_fields=("case_id", "case_record_id", "case_no") if finance_metrics else None,
                record_factory=(DashboardFinanceFeeProjection if finance_metrics else
                                DashboardFeeProjection if include_summaries and not light_records else None),
                metadata_fields=("id", "module", "serial_no", "title", "status", "updated_at")
                if finance_metrics else None,
            ) if case_ids else []
    contract_ids = set((await db.scalars(select(ContractObject.contract_record_id).where(
        scalar_in_values(ContractObject.case_record_id, case_ids),
    ))).all()) if case_ids else set()
    contract_nos = set()
    # 合同范围消费全量关系池，不能仅从金额候选费用推断合同集合。
    contract_links = (row.links[3:6] for row in finance_pool.rows) if finance_pool is not None else ()
    record_links = (tuple((item.data or {}).get(key) for key in relation_fields)
                    for item in chain(cases, () if finance_pool is not None else fees))
    for first_id, second_id, number in chain(record_links, contract_links):
        for raw_id in (first_id, second_id):
            value = str(raw_id or "")
            if value.isdigit():
                contract_ids.add(int(value))
        if number:
            contract_nos.add(str(number))
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
    fee_ids = finance_pool.all_record_ids if finance_pool is not None else {item.id for item in fees}
    scoped_identity = {
        **identity, "role": roles[0], "role_ids": roles, "_page_menu_capability": False,
        "_dashboard_case_ids": case_ids,
        "_dashboard_fee_ids": fee_ids,
        "_dashboard_record_ids": case_ids | fee_ids | visible_contract_ids,
    }
    return DashboardScopeData(scoped_identity, cases, fees, contracts, all_cases and not personal_cases,
                              personal_ids, finance_pool)


async def dashboard_request_identity(queue, expected, identity, db):
    if not queue:
        return identity
    if queue not in expected:
        raise HTTPException(422, "控制台业务入口无效")
    # 点进去的列表就是工作台数字算出来的那批记录：优先取算数字时记下的成员，没有再按同一算法现算。
    from app.core.dashboard_queue_members import CASE_GROUP, FINANCE_GROUP, recall
    group = CASE_GROUP if queue in CASE_QUEUES else FINANCE_GROUP
    members = await recall(db, identity["username"], group, queue)
    if members is None:
        from app.core.dashboard_personal_queues import personal_case_queues, personal_finance_queues
        queues = await (personal_case_queues(identity, db) if group == CASE_GROUP
                        else personal_finance_queues(identity, db))
        rows = queues.get(queue, [])
        members = {"case_ids": [int(row["id"]) for row in rows],
                   "fee_ids": [int(row["fee_id"]) for row in rows if row.get("fee_id") is not None]}
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if user is None or not user.is_active:
        raise HTTPException(401, "当前用户不存在或已停用")
    roles = _system_user_role_ids(user)
    case_ids = set(members["case_ids"])
    fee_ids = set(members["fee_ids"])
    return {**identity, "role": roles[0], "role_ids": roles, "_page_menu_capability": False,
            "_dashboard_case_ids": case_ids, "_dashboard_fee_ids": fee_ids,
            "_dashboard_record_ids": case_ids | fee_ids, "_dashboard_queue_exact": True}


def _possible_refund_fee(fee, case_ids, case_nos):
    """已读字段只缩小候选编号，最终权限与类型转换仍交给原 SQL 确认。"""
    data = fee.data or {}
    return _possible_refund_links((data.get("case_id"), data.get("case_record_id"), data.get("case_no")),
                                  case_ids, case_nos)


def _possible_refund_links(links, case_ids, case_nos):
    number = links[2]
    if isinstance(number, str):
        if number in case_nos:
            return True
    elif number is not None:
        return True
    for value in links[:2]:
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


async def _sees_company_refunds(identity, db) -> bool:
    """旧系统有“公司案件/民事争议”（权限码 1001103010）的人，待退费看本公司全部。"""
    from app.core.permissions import _permission_payload_for_identity
    menus = set((await _permission_payload_for_identity(identity, db)).get("menu_keys") or [])
    return "case-company-civil" in menus


def _refund_candidate_conditions(db):
    """待退费候选费用：登记了退费进度，或是律师代理费(退费)（11020061）。
    PostgreSQL 上写成与部分索引一致的字面表达式并带 IS NOT NULL；三个条件分开查（各自走一个部分索引），
    合在一个 OR 里规划器只会扫 module 索引再逐条解析八万条费用 JSON（陶威 11-01：待缴官费慢）。"""
    data = BusinessRecord.data
    if db.get_bind().dialect.name != "postgresql":
        return [or_(data["refund_status"].as_string().notin_(["", "0"]),
                    data["legacy_record"]["RefundStatus"].as_string().notin_(["", "0"]),
                    data["case_fee_type_id"].as_string() == "11020061")]
    refund_status = literal_column("(business_records.data ->> 'refund_status')")
    legacy_status = literal_column("((business_records.data -> 'legacy_record') ->> 'RefundStatus')")
    fee_type_id = literal_column("(business_records.data ->> 'case_fee_type_id')")

    def not_blank_or_zero(value):
        # 与 NOT IN ('', '0') 等价（非空值）：大于 '0'，或介于 '' 与 '0' 之间；写成范围才能走 btree 索引。
        return and_(value.is_not(None), or_(value > "0", and_(value > "", value < "0")))

    return [
        not_blank_or_zero(refund_status),
        not_blank_or_zero(legacy_status),
        and_(fee_type_id.is_not(None), fee_type_id == "11020061"),
    ]


async def personal_refund_identity(scoped_identity, db, *, scope_data=None):
    """待退费范围：有公司民事案件菜单的看全公司，其他人看“我的案件”（含本人作为客户管理人/协作人的客户的案件）。
    返回的身份只含计入待退费的费用，控制台数字和点进去的列表一致。"""
    from app.core.dashboard_finance import dashboard_refund_fee_rows

    company = await _sees_company_refunds(scoped_identity, db)
    if company:
        cases = (await db.execute(select(BusinessRecord.id, BusinessRecord.serial_no).where(
            BusinessRecord.module == "case", BusinessRecord.status.notin_(["已合并", "已删除", "已回收"]),
        ))).all()
    else:
        # 旧系统本人条件只看案件角色和客户协作人，不含“本人名下合同的案件”；出庭律师不算（陶国南 11-02 选 c-A）。
        from app.core.permissions import _coordinated_case_condition
        cases = (await db.execute(select(BusinessRecord.id, BusinessRecord.serial_no).where(
            scalar_in_values(BusinessRecord.id, scoped_identity["_dashboard_case_ids"]),
            or_(await _case_mine_scope_condition(scoped_identity, db, court_lawyer=False),
                _coordinated_case_condition(scoped_identity["username"], db.get_bind().dialect.name)),
        ))).all()
    case_ids = {case.id for case in cases}
    case_nos = {case.serial_no for case in cases}
    if company:
        candidate_ids = set()
        for condition in _refund_candidate_conditions(db):
            candidate_ids |= set((await db.scalars(select(BusinessRecord.id).where(
                BusinessRecord.module == "finance", BusinessRecord.status != "已删除", condition,
            ))).all())
    else:
        candidate_ids = scoped_identity["_dashboard_fee_ids"]
    if scope_data is not None and not company:
        if scope_data.finance_pool is not None:
            candidate_ids = {row.id for row in scope_data.finance_pool.rows if row.id in candidate_ids
                             and _possible_refund_links(row.links, case_ids, case_nos)}
        else:
            candidate_ids = {fee.id for fee in scope_data.fees if fee.id in candidate_ids
                             and _possible_refund_fee(fee, case_ids, case_nos)}
    fee_ids = set((await db.scalars(select(BusinessRecord.id).where(
        scalar_in_values(BusinessRecord.id, candidate_ids),
        or_(scalar_in_values(BusinessRecord.data["case_id"].as_integer(), case_ids),
            scalar_in_values(BusinessRecord.data["case_record_id"].as_integer(), case_ids),
            scalar_in_values(BusinessRecord.data["case_no"].as_string(), case_nos)),
    ))).all()) if case_ids and candidate_ids else set()
    refund_identity = {**scoped_identity, "_dashboard_case_ids": case_ids, "_dashboard_fee_ids": fee_ids}
    rows = await dashboard_refund_fee_rows(refund_identity, db, cases) if fee_ids else []
    fee_ids = {row["id"] for row in rows}
    return {**refund_identity, "_dashboard_fee_ids": fee_ids, "_dashboard_record_ids": case_ids | fee_ids,
            "_dashboard_refund_rows": rows}


async def dashboard_urgent_cases(identity, db, personal_case_ids, *, scope_data=None):
    """紧急案件的案件范围和其他案件提醒一样：普通账号看“我的案件”（本人办理或本人作为客户管理人/协作人的客户的案件），
    管理员类账号看全公司（陶国南 11-01 定）。"""
    from app.core.permissions import _coordinated_case_condition

    if scope_data is not None:
        return scope_data.cases
    conditions = [
        BusinessRecord.module == "case",
        BusinessRecord.status.notin_(["已合并", "已删除", "已回收"]),
        or_(await _case_mine_scope_condition(identity, db),
            _coordinated_case_condition(identity["username"], db.get_bind().dialect.name)),
    ]
    return await dashboard_queue_cases(db, conditions)


async def dashboard_queue_cases(db, conditions):
    return await read_record_projections(
        db, conditions, ("case_type", "case_phase_name", "case_phase"),
        legacy_fields=("CasePhaseName",),
    )


async def dashboard_receivables(identity, db, *, records=None, summary_only=False, finance_metrics=False,
                                 receipt_pool=None):
    from app.core.projections import _receivable_detail_projection
    rows = await _receivable_detail_projection(
        identity, db, records=records, summary_only=summary_only, official_only=summary_only,
        dashboard_finance_only=finance_metrics,
        receipt_pool=receipt_pool,
    )
    return [row for row in rows if row["fee_category"] == "official" and row["remaining_amount"] > 0]


async def dashboard_fee_cases(rows, identity, db):
    """返回当前费用页的真实关联案件，供原有批量操作使用。"""
    from app.core.system import _record_dict, _allowed_field_keys
    case_ids = {row["data"].get("case_id") for row in rows} & identity["_dashboard_case_ids"]
    cases = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(case_ids)))).all()) if case_ids else []
    fields = await _allowed_field_keys(identity, db)
    return {"cases": [_record_dict(case, fields) for case in cases]}
