"""回款及结算共用的财务主体边界，不推测历史归属。"""

from typing import Literal

from fastapi import Depends, HTTPException, Query, Request
from sqlalchemy import Integer, String, and_, case, cast, exists, false, func, inspect, literal, or_, select, union_all
from sqlalchemy.orm import aliased, with_expression

from app.database import get_db
from app.models import BusinessRecord, IncomingPayment, LegacyFinanceRecord
from app.security import current_identity
from app.core.incoming_legacy_amounts import ASSIGNED_FIELDS, LEGACY_ASSIGNED_AMOUNTS, legacy_assigned_amounts


FinanceScope = Literal["firm", "platform", "unclassified"]
# 501099（陶国南 11-02 定方案二）：财务数据按业务类型分诉讼/非诉（知识产权），和律所/平台两个中心交叉。
# 不传或“全部”不筛；知识产权中心下的“非诉财务中心”固定传“非诉”。记录上没写业务类型的都是诉讼。
BusinessTypeParam = Literal["诉讼", "非诉", "全部"]
BUSINESS_TYPES = ("诉讼", "非诉")
NONLITIGATION = "非诉"
NONLITIGATION_MENU_ROOT = "ipr-finance"
NONLITIGATION_VIEWER_MENUS = frozenset({"finance-receipts-manage", "platform-finance-overview-manage"})
RECORD_CENTER_VALUES = {
    "finance_scope": {"firm": "firm", "platform": "platform"},
    "accounting_center": {"财务中心": "firm", "律所财务中心": "firm", "平台财务中心": "platform"},
    "contract_body": {"律所": "firm", "平台": "platform"},
    "expense_scope": {"律所": "firm", "平台": "platform"},
}
# 律所/平台按老系统原样区分（陶威 2026-10-30）：迁移数据各表看自己的 GroupId（10=律所、20=平台、0=两边都不显示），
# 请款单看所属合同的 GroupId；本系统新建的记录仍看 finance_scope/accounting_center/contract_body/expense_scope。
LEGACY_GROUP_CENTERS = {"10": "firm", "20": "platform", "0": None}

# 旧导入未保存源库命名空间；新导入必须按真实头外键读取，不能跨库按裸主键拼接。
from app.data_models.finance import LegacyArPaymentField as _F
_LEGACY_PAYMENT_ID = _F.payment_id
# 关联键：有真实头外键时按 ID，否则按回款编号。两种前缀互不相等，等值关联与
# “ID 相等 或（双方都无 ID 且编号相等）”完全等价，但可以使用哈希连接。
_UNQUALIFIED_MATCH_KEY = literal("rcpt:HZ-RCPT-") + _LEGACY_PAYMENT_ID
_LEGACY_UNQUALIFIED_SOURCE = select(
    cast(literal(None), Integer).label("record_id"),
    func.max(_F.record_id).label("source_header_id"),
    _LEGACY_PAYMENT_ID.label("payment_id"),
    func.max(_F.group_id).label("group_id"),
    func.max(_F.payment_method).label("payment_method"),
    func.max(_F.settlement_status).label("settlement_status"),
    _UNQUALIFIED_MATCH_KEY.label("match_key"),
).where(
    _F.is_active.is_(True),
    _F.source_database.is_(None),
    ~_F.legacy_id.contains(":"),
).group_by(_LEGACY_PAYMENT_ID).having(
    func.count() == 1,
)
_LEGACY_LINKED_SOURCE = select(
    _F.record_id.label("record_id"),
    _F.record_id.label("source_header_id"),
    _F.payment_id.label("payment_id"),
    _F.group_id.label("group_id"),
    _F.payment_method.label("payment_method"),
    _F.settlement_status.label("settlement_status"),
    (literal("id:") + cast(_F.record_id, String)).label("match_key"),
).where(
    _F.is_active.is_(True),
)
# 物化成 CTE：每条查询只算一次旧来源（约 6,500 行）。原先是子查询，到账单估计行数偏少时规划器选嵌套循环，
# 对每张到账单都重算一遍分组聚合（9 张到账单就算 9 遍），工作台“待分配回款”计数负载高时要 7 秒（陶威 11-01）。
LEGACY_INCOMING_SOURCE = union_all(
    _LEGACY_UNQUALIFIED_SOURCE, _LEGACY_LINKED_SOURCE,
).cte("incoming_legacy_source").prefix_with("MATERIALIZED", dialect="postgresql")

INCOMING_CENTER = func.coalesce(IncomingPayment.finance_scope, case(
    (LEGACY_INCOMING_SOURCE.c.group_id == "10", "firm"),
    (LEGACY_INCOMING_SOURCE.c.group_id == "20", "platform"),
))


def _incoming_source_relation():
    # 原条件：hz 且（双方 ID 非空且相等，或双方 ID 均为空且回款编号 = "HZ-RCPT-" + PaymentId）。
    # 写成单一组合键的等值比较后语义不变；原 OR 条件只能嵌套循环逐对比较（约 2000 万对）。
    payment_key = case(
        (IncomingPayment.legacy_finance_record_id.is_not(None),
         literal("id:") + cast(IncomingPayment.legacy_finance_record_id, String)),
        else_=literal("rcpt:") + IncomingPayment.receipt_no,
    )
    return and_(
        IncomingPayment.source_kind == "hz_crm_20260930",
        payment_key == LEGACY_INCOMING_SOURCE.c.match_key,
    )


def reopened_legacy_settlement():
    """历史结算在新系统回滚（承接的申请已撤回）后按原系统回到待提交，重新进入待结算。"""
    return exists(select(BusinessRecord.id).where(
        BusinessRecord.module == "finance_settlement", BusinessRecord.status == "已撤回",
        BusinessRecord.data["legacy_projection_id"].as_string().is_not(None),
        BusinessRecord.data["receipt_id"].as_integer() == IncomingPayment.id,
    ))


def incoming_settlement_candidates(identity, *, receipt_ids=None):
    # 先保留原来源唯一性判定，再筛候选；不能先筛状态而把重复旧头变成唯一。
    statement = select(
        IncomingPayment.id.label("receipt_id"), LEGACY_INCOMING_SOURCE.c.source_header_id,
    ).join(LEGACY_INCOMING_SOURCE, _incoming_source_relation()).where(
        or_(LEGACY_INCOMING_SOURCE.c.settlement_status == "5", reopened_legacy_settlement()),
        *incoming_center_conditions(identity),
    )
    if receipt_ids is not None:
        statement = statement.where(IncomingPayment.id.in_(receipt_ids))
    return statement.cte("settlement_incoming_candidates").prefix_with("MATERIALIZED", dialect="postgresql")


def incoming_source_statement(*, include_amounts=True, legacy_header_ids=None):
    statement = select(IncomingPayment).outerjoin(LEGACY_INCOMING_SOURCE, _incoming_source_relation()).options(
        with_expression(IncomingPayment.resolved_finance_scope, INCOMING_CENTER),
        with_expression(IncomingPayment.legacy_payment_method, LEGACY_INCOMING_SOURCE.c.payment_method),
        with_expression(IncomingPayment.legacy_settlement_status, LEGACY_INCOMING_SOURCE.c.settlement_status),
    )
    if not include_amounts:
        return statement
    amounts = (LEGACY_ASSIGNED_AMOUNTS if legacy_header_ids is None else
               legacy_assigned_amounts(header_ids=legacy_header_ids))
    return statement.outerjoin(amounts,
        amounts.c.header_id == LEGACY_INCOMING_SOURCE.c.source_header_id).options(
        *(with_expression(getattr(IncomingPayment, "legacy_" + field), amounts.c[field])
          for field in ASSIGNED_FIELDS),
        with_expression(IncomingPayment.legacy_baseline_allocations, amounts.c.baseline_allocations),
        with_expression(IncomingPayment.legacy_baseline_applied_amount, amounts.c.baseline_applied_amount),
    )


def legacy_header_ids_for(*payment_conditions):
    """符合条件的回款所对应的旧系统回款头，用于把旧金额聚合限定到实际读取的行。"""
    return incoming_source_statement(include_amounts=False).with_only_columns(
        LEGACY_INCOMING_SOURCE.c.source_header_id,
    ).where(
        *payment_conditions,
        IncomingPayment.source_kind == "hz_crm_20260930",
        LEGACY_INCOMING_SOURCE.c.source_header_id.is_not(None),
    ).distinct()


def incoming_source_for(db, *payment_conditions):
    """与 incoming_source_statement().where(*payment_conditions) 返回相同的行和字段。

    旧金额按回款头分组聚合，只聚合结果行自身的回款头不会改变任何一行的金额；
    原写法每次都聚合全部回款头，查一笔回款也要扫描整个历史分配账本。
    SQLite 测试库保持原写法。
    """
    if db.get_bind().dialect.name != "postgresql":
        return incoming_source_statement().where(*payment_conditions)
    return incoming_source_statement(
        legacy_header_ids=legacy_header_ids_for(*payment_conditions),
    ).where(*payment_conditions)


def payment_center(payment):
    return payment.finance_scope or payment.resolved_finance_scope


async def refresh_incoming_payment(payment, db):
    return (await refresh_incoming_payments([payment], db))[0]


async def refresh_incoming_payments(payments, db):
    payment_ids = [inspect(payment).identity[0] for payment in payments]
    refreshed = list((await db.scalars(incoming_source_for(
        db, IncomingPayment.id.in_(payment_ids),
    ).execution_options(populate_existing=True))).all())
    by_id = {payment.id: payment for payment in refreshed}
    if set(by_id) != set(payment_ids):
        raise HTTPException(409, "回款已变更或删除，请重新查询")
    return [by_id[payment_id] for payment_id in payment_ids]


async def finance_center_identity(
    request: Request,
    finance_scope: FinanceScope = Query(...),
    business_type: BusinessTypeParam | None = Query(None),
    identity: dict = Depends(current_identity),
    db=Depends(get_db),
):
    if finance_scope == "unclassified" and request.method != "GET":
        raise HTTPException(409, "历史回款中心尚未确认，只允许查询，不能办理财务动作")
    if finance_scope == "unclassified" and identity.get("role") != "admin":
        raise HTTPException(403, "只有管理员可以查询待确认中心的历史回款")
    from app.core.permissions import _permission_payload_for_identity

    permission = await _permission_payload_for_identity(identity, db)
    menus = set(permission.get("menu_keys") or [])
    prefixes = ("finance", "platform-finance") if finance_scope == "unclassified" else (
        "platform-finance" if finance_scope == "platform" else "finance",
    )

    def granted(*roots):
        return any(key == root or key.startswith(root + "-") for root in roots for key in menus)

    business = business_type if business_type in BUSINESS_TYPES else None
    # 页面访问会把有菜单的账号临时当管理员（current_identity），这里按账号真实角色和菜单判断。
    actual_roles = set(identity.get("_actual_role_ids") or [identity.get("_actual_role") or identity.get("role")])
    if "admin" not in actual_roles and not granted("finance", "platform-finance"):
        # 只有非诉财务中心菜单的账号：只能在律所中心看、办非诉。
        if not (finance_scope == "firm" and business == NONLITIGATION and granted(NONLITIGATION_MENU_ROOT)):
            raise HTTPException(403, "当前账号没有该财务中心权限")
    elif identity.get("role") != "admin" and not granted(*prefixes):
        raise HTTPException(403, "当前账号没有该财务中心权限")
    # 诉讼人员不看非诉：能看非诉的是管理员、审批人员、有回款管理页的财务，以及有非诉财务中心菜单的人。
    if not (actual_roles & {"admin", "auditor"} or granted(NONLITIGATION_MENU_ROOT)
            or menus & NONLITIGATION_VIEWER_MENUS):
        business = "诉讼"
    return {**identity, "_finance_scope": finance_scope, "_business_type": business}


async def optional_finance_center_identity(
    request: Request,
    finance_scope: FinanceScope | None = Query(None),
    business_type: BusinessTypeParam | None = Query(None),
    identity: dict = Depends(current_identity),
    db=Depends(get_db),
):
    if finance_scope is None and business_type is None:
        # 只有非诉财务中心菜单的账号不带中心也只能看、办非诉（页面访问会把它临时当管理员）。
        if not await _nonlitigation_only(identity, db):
            return identity
        business_type = NONLITIGATION
    return await finance_center_identity(request, finance_scope or "firm", business_type, identity, db)


async def _nonlitigation_only(identity, db) -> bool:
    if "admin" in set(identity.get("_actual_role_ids") or [identity.get("_actual_role") or identity.get("role")]):
        return False
    from app.core.permissions import _permission_payload_for_identity
    menus = set((await _permission_payload_for_identity(identity, db)).get("menu_keys") or [])
    granted = lambda root: any(key == root or key.startswith(root + "-") for key in menus)
    return granted(NONLITIGATION_MENU_ROOT) and not granted("finance") and not granted("platform-finance")


def legacy_center_conditions(identity):
    scope = identity.get("_finance_scope")
    if not scope:
        return []
    group = cast(LegacyFinanceRecord.source_payload["GroupId"].as_string(), String)
    center = case((group == "10", "firm"), (group == "20", "platform"))
    conditions = [center.is_(None) if scope == "unclassified" else center == scope]
    if identity.get("_business_type") == NONLITIGATION:
        # 沪知老财务表都是诉讼；恒达知识产权老数据另行接入时再在这里认来源。
        conditions.append(false())
    return conditions


def validate_legacy_receipt_allocations(header, allocations):
    if header.source_table != "FAM_AR_Payment":
        return
    source = header.source_payload or {}
    payment_id = source.get("PaymentId")
    for allocation in allocations:
        payload = allocation.source_payload or {}
        if (allocation.source_table != "FAM_AR_Payment_Object"
                or allocation.legacy_finance_record_id != header.id
                or allocation.parent_source_table != header.source_table
                or allocation.parent_legacy_id != header.legacy_id
                or payload.get("_source_database") != source.get("_source_database")
                or payment_id is None or str(payload.get("PaymentId")) != str(payment_id)):
            raise HTTPException(409, "历史结算明细的源库、原主键或父关联不一致，不能混合显示")


def incoming_business_type(payment) -> str:
    return payment.business_type or "诉讼"


def incoming_business_conditions(identity):
    business = identity.get("_business_type")
    if business not in BUSINESS_TYPES:
        return []
    return [func.coalesce(IncomingPayment.business_type, "诉讼") == business]


def incoming_center_conditions(identity):
    scope = identity.get("_finance_scope")
    if not scope:
        return []
    return [INCOMING_CENTER.is_(None) if scope == "unclassified" else INCOMING_CENTER == scope,
            *incoming_business_conditions(identity)]


def require_incoming_center(payment, identity):
    scope = identity.get("_finance_scope")
    if payment is not None and scope and (payment_center(payment) or "unclassified") != scope:
        raise HTTPException(409, "回款不属于当前财务中心，或历史归属尚未确认")
    business = identity.get("_business_type")
    if payment is not None and business in BUSINESS_TYPES and incoming_business_type(payment) != business:
        raise HTTPException(409, f"回款不属于当前业务类型（{business}）")


def record_business_type(record) -> str:
    return str((record.data or {}).get("business_type") or "诉讼")


def record_business_conditions(identity, *, allow_shared_contract=True):
    business = identity.get("_business_type")
    if business not in BUSINESS_TYPES:
        return []
    condition = func.coalesce(BusinessRecord.data["business_type"].as_string(), "诉讼") == business
    # 合同诉讼、非诉共用，不按业务类型挡。
    return [or_(condition, BusinessRecord.module == "contract") if allow_shared_contract else condition]


def settlement_center_conditions(identity):
    scope = identity.get("_finance_scope")
    if not scope:
        return []
    # 原主单主体和回款主体都保留；无新回款键的旧申请不能从未分类视图消失。
    receipts = incoming_source_statement(include_amounts=False).with_only_columns(
        IncomingPayment.id, INCOMING_CENTER.label("finance_scope"),
    ).cte("settlement_receipt_centers")
    own = record_center_presence()
    present = {center: or_(own[center], BusinessRecord.data["receipt_id"].as_integer().in_(
        select(receipts.c.id).where(receipts.c.finance_scope == center),
    )).is_(True) for center in ("firm", "platform")}
    expression = case(
        (and_(present["firm"], ~present["platform"]), "firm"),
        (and_(present["platform"], ~present["firm"]), "platform"),
    )
    return [expression.is_(None) if scope == "unclassified" else expression == scope,
            *record_business_conditions(identity, allow_shared_contract=False)]


async def unclassified_incoming_count(identity, db):
    from app.core.finance import _visible_incoming_payment_statement

    visible = await _visible_incoming_payment_statement({**identity, "_finance_scope": "unclassified"}, db, include_amounts=False)
    return int(await db.scalar(select(func.count()).select_from(visible.subquery())))


async def legacy_incoming_status_counts(identity, db):
    from app.core.finance import _visible_incoming_payment_statement

    visible = await _visible_incoming_payment_statement(identity, db, include_amounts=False)
    status = LEGACY_INCOMING_SOURCE.c.settlement_status
    rows = (await db.execute(visible.with_only_columns(status, func.count()).where(
        IncomingPayment.source_kind == "hz_crm_20260930",
    ).group_by(status))).all()
    return {
        "legacy_source_statuses": [{"source_status": value, "count": int(count)} for value, count in rows],
        "unmapped_legacy_status_total": sum(int(count) for value, count in rows
                                           if value not in {"5", "10", "20", "25", "30"}),
    }


async def resolved_record_center_values(record, db):
    if db is None or record.module != "finance":
        return record_center_values(record)
    present = record_center_presence()
    row = (await db.execute(select(present["firm"], present["platform"]).where(
        BusinessRecord.id == record.id,
    ))).one()
    return {center for center, exists in zip(("firm", "platform"), row) if exists}


async def require_source_center(record, db=None):
    values = await resolved_record_center_values(record, db)
    center = next(iter(values)) if len(values) == 1 else None
    if center is None:
        raise HTTPException(409, "来源费用的财务中心尚未确认或存在冲突，不能登记到账；请先核对来源费用主体")
    return center


def record_center_values(record):
    data = record.data or {}
    group = str(data.get("group_id") if data.get("group_id") is not None else "").strip()
    if group in LEGACY_GROUP_CENTERS:
        return {LEGACY_GROUP_CENTERS[group]} - {None}
    values = set()
    for key, mapping in RECORD_CENTER_VALUES.items():
        value = data.get(key)
        if isinstance(value, str) and value in mapping:
            values.add(mapping[value])
    legacy = data.get("legacy_record")
    if isinstance(legacy, dict):
        group = str(legacy.get("GroupId"))
        if group in {"10", "20"}:
            values.add("firm" if group == "10" else "platform")
    return values


async def require_record_center(record, identity, db=None, *, allow_shared_contract=True):
    scope = identity.get("_finance_scope")
    values = await resolved_record_center_values(record, db)
    # 历史共享合同可以没有主体元信息；费用和回款仍必须明确同中心。
    if allow_shared_contract and record.module == "contract" and not values:
        return
    if scope and values != {scope}:
        raise HTTPException(409, "关联费用或合同的财务主体不一致或尚未确认")
    business = identity.get("_business_type")
    if business in BUSINESS_TYPES and record.module != "contract" and record_business_type(record) != business:
        raise HTTPException(409, f"关联费用不属于当前业务类型（{business}）")


def record_center_conditions(identity, *, allow_shared_contract=True):
    scope = identity.get("_finance_scope")
    if not scope:
        return []
    present = record_center_presence()
    expression = case(
        (and_(present["firm"], ~present["platform"]), "firm"),
        (and_(present["platform"], ~present["firm"]), "platform"),
    )
    business = record_business_conditions(identity, allow_shared_contract=allow_shared_contract)
    if scope == "unclassified":
        return [expression.is_(None), *business]
    if not allow_shared_contract:
        return [expression == scope, *business]
    return [or_(expression == scope, and_(
        BusinessRecord.module == "contract", ~present["firm"], ~present["platform"],
    )), *business]


def record_center_presence():
    source = aliased(LegacyFinanceRecord)
    data = BusinessRecord.data
    database = data["legacy_record"]["_source_database"].as_string()
    original_id = cast(data["legacy_record"]["CaseFeeId"].as_string(), String)
    qualified_id = database + literal(":") + original_id
    # 仅沿正式旧费用导入保存的主键及来源查头；不按合同、公司或费用名称推测。
    source_group = select(cast(source.source_payload["GroupId"].as_string(), String)).where(
        BusinessRecord.module == "finance",
        source.source_table == "FAM_AR_CaseFee",
        or_(and_(
            data["legacy_kind"].as_string() == "ar_case_fee",
            data["legacy_source"].as_string() == "hz_crm_20260930",
            data["source_table"].as_string() == "FAM_AR_CaseFee",
            or_(data["legacy_case_fee_id"].as_string().is_(None),
                data["case_fee_id"].as_string().is_(None),
                cast(data["legacy_case_fee_id"].as_string(), String) == cast(data["case_fee_id"].as_string(), String)),
            source.legacy_id == cast(func.coalesce(data["legacy_case_fee_id"].as_string(),
                                                 data["case_fee_id"].as_string()), String),
            source.source_payload["_source_database"].as_string().is_(None),
            ~source.legacy_id.contains(":"),
        ), and_(
            database.is_not(None), database != "",
            source.source_payload["_source_database"].as_string() == database,
            source.legacy_id == qualified_id,
            cast(data["legacy_case_fee_id"].as_string(), String).in_([original_id, qualified_id]),
        )),
        source.is_active.is_(True),
    ).correlate(BusinessRecord).scalar_subquery()
    # 迁移数据有 GroupId 就只按它（0 两边都不算），不再和导入时写的 expense_scope 等字段冲突（陶威 2026-10-30）。
    group = func.coalesce(BusinessRecord.data["group_id"].as_string(), "")
    has_group = group.in_(list(LEGACY_GROUP_CENTERS))
    return {
        center: or_(and_(has_group, group == ("10" if center == "firm" else "20")), and_(~has_group, or_(
            *(BusinessRecord.data[key].as_string().in_(
                [value for value, mapped in mapping.items() if mapped == center],
            ) for key, mapping in RECORD_CENTER_VALUES.items()),
            cast(BusinessRecord.data["legacy_record"]["GroupId"].as_string(), String) == (
                "10" if center == "firm" else "20"),
            source_group == ("10" if center == "firm" else "20"),
        ))).is_(True)
        for center in ("firm", "platform")
    }


_CENTER_FIELDS = ("group_id", "finance_scope", "accounting_center", "contract_body", "expense_scope",
                  "contract_record_id", "contract_id")


def _own_center(data: dict, module: str) -> tuple[bool, str | None]:
    """返回（是否已判定，中心）。迁移数据有 GroupId 就只看它。"""
    group = str(data.get("group_id") if data.get("group_id") is not None else "").strip()
    if group in LEGACY_GROUP_CENTERS:
        return True, LEGACY_GROUP_CENTERS[group]
    values = {mapping[value] for key, mapping in RECORD_CENTER_VALUES.items()
              if isinstance(value := data.get(key), str) and value in mapping}
    if len(values) == 1:
        return True, next(iter(values))
    return False, None


async def finance_centers_for_ids(db, ids) -> dict[int, str | None]:
    """按记录编号批量算所属财务中心；只读必要字段，不取整条 data。"""
    ids = sorted({int(item) for item in ids if item is not None})
    if not ids:
        return {}
    fields = [BusinessRecord.data[key].as_string().label(key) for key in _CENTER_FIELDS]
    rows = []
    for offset in range(0, len(ids), 2000):
        rows.extend((await db.execute(select(BusinessRecord.id, BusinessRecord.module, *fields).where(
            BusinessRecord.id.in_(ids[offset:offset + 2000])))).all())
    result: dict[int, str | None] = {}
    pending_contracts: dict[int, int] = {}
    for row in rows:
        data = {key: getattr(row, key) for key in _CENTER_FIELDS}
        if row.module == "contract_payment" and not data.get("finance_scope"):
            contract = str(data.get("contract_record_id") or data.get("contract_id") or "")
            if contract.isdigit():
                pending_contracts[row.id] = int(contract)
                continue
        decided, center = _own_center(data, row.module)
        result[row.id] = center if decided else "firm"
    if pending_contracts:
        contract_centers = await finance_centers_for_ids(db, set(pending_contracts.values()))
        for record_id, contract_id in pending_contracts.items():
            result[record_id] = contract_centers.get(contract_id, "firm") if contract_id in contract_centers else "firm"
    return result


async def business_types_for_ids(db, ids) -> dict[int, str]:
    """按记录编号批量取业务类型（没写的都是诉讼）。"""
    ids = sorted({int(item) for item in ids if item is not None})
    result: dict[int, str] = {}
    for offset in range(0, len(ids), 2000):
        rows = (await db.execute(select(BusinessRecord.id, BusinessRecord.data["business_type"].as_string()).where(
            BusinessRecord.id.in_(ids[offset:offset + 2000])))).all()
        result.update({row[0]: row[1] or "诉讼" for row in rows})
    return result


async def filter_rows_by_center(rows, identity, db, *, id_of=lambda row: row.get("id")):
    """当前财务中心只留本中心的行（未传中心时原样返回）；带业务类型时只留该业务类型的行。"""
    scope = identity.get("_finance_scope")
    rows = list(rows)
    business = identity.get("_business_type")
    if business in BUSINESS_TYPES:
        types = await business_types_for_ids(db, [id_of(row) for row in rows if str(id_of(row) or "").isdigit()])
        # 没有记录编号的行（老系统直读）都是诉讼。
        rows = [row for row in rows if (types.get(int(id_of(row)), "诉讼") if str(id_of(row) or "").isdigit() else "诉讼") == business]
    if scope not in {"firm", "platform"}:
        return rows
    centers = await finance_centers_for_ids(db, [id_of(row) for row in rows if str(id_of(row) or "").isdigit()])
    return [row for row in rows if not str(id_of(row) or "").isdigit() or centers.get(int(id_of(row)), "firm") == scope]


async def has_nonlitigation_page(identity, db, *keys: str) -> bool:
    """501099“给页面＝功能全有”：当前是非诉业务，且账号真实菜单里有这些非诉财务中心页面之一。
    只有非诉菜单的账号写操作不会被页面访问临时提升，后端角色门槛要用它放行（只对非诉数据）。"""
    if identity.get("_business_type") != NONLITIGATION:
        return False
    from app.core.permissions import _permission_payload_for_identity
    menus = set((await _permission_payload_for_identity(identity, db)).get("menu_keys") or [])
    return any(key in menus for key in keys)


def nonlitigation_record_type(*records) -> str | None:
    """由来源记录（费用等）推出新记录的业务类型：来源全是非诉才记非诉，否则不写（=诉讼）。"""
    records = [record for record in records if record is not None]
    if records and all(record_business_type(record) == NONLITIGATION for record in records):
        return NONLITIGATION
    return None
