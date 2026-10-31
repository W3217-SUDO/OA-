"""客户“官费未到金额”“代理费待收金额”，按旧系统视图 V_CRM_Customer_Fee 的算法现算（2026-10-31 对齐）。

旧算法：客户的有效合同（按合同编号关联）下的有效费用，
- 官费未到 = 官方费用实际付出（已付款的请款单明细）- 已到账（回款分配），逐笔相减，负数抵扣；
- 代理费待收 = 代理费（11020010/20/30/40）金额 - 已到账。
新系统对应：请款单 = contract_payment 的 lines（已付款、已核销），另加费用直接付款流水；到账 = 回款 incoming_payments 的分配明细。
"""
from collections import defaultdict
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, inspect, or_, select, text

from app.core.json_relation_query import scalar_in_values
from app.models import BusinessRecord, FinanceTransaction, IncomingPayment, LegacyCustomerHistoryEvent

PAID_PAYMENT_STATUSES = ("已付款", "已核销")
OFFICIAL_FEE_TYPE = "官方费用"
AGENCY_FEE_TYPE = "代理费"
# 旧系统代理费待收只算这四类；新系统新建的代理费没有旧类型编号，按代理费计。
AGENCY_FEE_CODES = {"11020010", "11020020", "11020030", "11020040"}
FEE_KEYS = ("fee_record_id", "finance_record_id", "fee_id", "case_fee_id")


def _amount(value) -> Decimal:
    try:
        return Decimal(str(value)) if value not in (None, "") else Decimal(0)
    except (InvalidOperation, ValueError):
        return Decimal(0)


def _fee_id(item: dict) -> int | None:
    for key in FEE_KEYS:
        value = str(item.get(key) or "").strip()
        if value.isdigit():
            return int(value)
    return None


async def _paid_by_fee(fee_ids: set[int], db) -> dict[int, Decimal]:
    paid: dict[int, Decimal] = defaultdict(Decimal)
    if db.get_bind().dialect.name == "postgresql":
        rows = await db.execute(text("""
            SELECT fid::bigint, sum(amt::numeric) FROM (
              SELECT coalesce(nullif(l->>'fee_record_id', ''), nullif(l->>'case_fee_id', '')) AS fid, l->>'amount' AS amt
              FROM business_records p
              CROSS JOIN LATERAL json_array_elements(
                CASE WHEN json_typeof(p.data->'lines') = 'array' THEN p.data->'lines' ELSE '[]'::json END) l
              WHERE p.module = 'contract_payment' AND p.status = ANY(:statuses) AND p.deleted_at IS NULL
            ) x
            WHERE fid ~ '^[0-9]{1,18}$' AND amt ~ '^-?[0-9]+(\\.[0-9]+)?$' AND fid::bigint = ANY(:ids)
            GROUP BY 1
        """), {"statuses": list(PAID_PAYMENT_STATUSES), "ids": list(fee_ids)})
        for fee_id, total in rows.all():
            paid[int(fee_id)] += _amount(total)
    else:
        for (data,) in (await db.execute(select(BusinessRecord.data).where(
            BusinessRecord.module == "contract_payment", BusinessRecord.status.in_(PAID_PAYMENT_STATUSES),
        ))).all():
            for line in (data or {}).get("lines") or []:
                if isinstance(line, dict) and (fee_id := _fee_id(line)) in fee_ids:
                    paid[fee_id] += _amount(line.get("amount"))
    # 新系统对费用的直接付款记在付款流水上。
    for fee_id, total in (await db.execute(select(
        FinanceTransaction.finance_record_id, FinanceTransaction.amount,
    ).where(scalar_in_values(FinanceTransaction.finance_record_id, fee_ids),
            FinanceTransaction.transaction_type == "付款"))).all():
        paid[int(fee_id)] += _amount(total)
    return paid


async def _cashed_by_fee(fee_ids: set[int], db) -> dict[int, Decimal]:
    cashed: dict[int, Decimal] = defaultdict(Decimal)
    if db.get_bind().dialect.name == "postgresql":
        rows = await db.execute(text("""
            SELECT fid::bigint, sum(amt::numeric) FROM (
              SELECT coalesce(nullif(s->>'fee_record_id', ''), nullif(s->>'finance_record_id', ''),
                              nullif(s->>'fee_id', ''), nullif(s->>'case_fee_id', '')) AS fid, s->>'amount' AS amt
              FROM incoming_payments ip
              CROSS JOIN LATERAL json_array_elements(
                CASE WHEN json_typeof(ip.allocations) = 'array' THEN ip.allocations ELSE '[]'::json END) a
              CROSS JOIN LATERAL json_array_elements(
                CASE WHEN json_typeof(a->'settlement_items') = 'array' AND json_array_length(a->'settlement_items') > 0
                     THEN a->'settlement_items' ELSE json_build_array(a) END) s
              WHERE ip.deleted_at IS NULL
            ) x
            WHERE fid ~ '^[0-9]{1,18}$' AND amt ~ '^-?[0-9]+(\\.[0-9]+)?$' AND fid::bigint = ANY(:ids)
            GROUP BY 1
        """), {"ids": list(fee_ids)})
        for fee_id, total in rows.all():
            cashed[int(fee_id)] += _amount(total)
        return cashed
    for (allocations,) in (await db.execute(select(IncomingPayment.allocations))).all():
        for allocation in allocations or []:
            if not isinstance(allocation, dict):
                continue
            items = allocation.get("settlement_items")
            for item in items if isinstance(items, list) and items else [allocation]:
                if isinstance(item, dict) and (fee_id := _fee_id(item)) in fee_ids:
                    cashed[fee_id] += _amount(item.get("amount"))
    return cashed


async def customer_fee_balances(db, customers: list[BusinessRecord]) -> dict[int, dict[str, float]]:
    """返回 {客户 id: {"official_fee_unreceived": 官费未到, "agency_fee_due": 代理费待收}}。"""
    result = {item.id: {"official_fee_unreceived": 0.0, "agency_fee_due": 0.0} for item in customers}
    if not customers:
        return result
    by_id = {str(item.id): item.id for item in customers}
    by_no = {str(item.serial_no or "").strip(): item.id for item in customers if str(item.serial_no or "").strip()}
    data = BusinessRecord.data
    contracts = (await db.execute(select(
        BusinessRecord.serial_no, data["customer_record_id"].as_string(), data["customer_id"].as_string(),
        data["customer_no"].as_string(),
    ).where(BusinessRecord.module == "contract", or_(
        scalar_in_values(data["customer_record_id"].as_string(), set(by_id)),
        scalar_in_values(data["customer_id"].as_string(), set(by_id)),
        scalar_in_values(data["customer_no"].as_string(), set(by_no) or {""}),
    )))).all()
    customer_by_contract: dict[str, int] = {}
    for contract_no, record_id, customer_id, customer_no in contracts:
        owner = by_id.get(str(record_id or "")) or by_id.get(str(customer_id or "")) or by_no.get(str(customer_no or "").strip())
        if contract_no and owner is not None:
            customer_by_contract[str(contract_no).strip()] = owner
    if not customer_by_contract:
        return result
    fees = (await db.execute(select(
        BusinessRecord.id, data["contract_no"].as_string(), data["fee_type"].as_string(),
        data["case_fee_type_id"].as_string(), data["amount"].as_string(),
    ).where(
        BusinessRecord.module == "finance", BusinessRecord.status != "已删除",
        scalar_in_values(data["contract_no"].as_string(), set(customer_by_contract)),
        data["fee_type"].as_string().in_([OFFICIAL_FEE_TYPE, AGENCY_FEE_TYPE]),
    ))).all()
    fee_ids = {row[0] for row in fees}
    if not fee_ids:
        return result
    paid = await _paid_by_fee(fee_ids, db)
    cashed = await _cashed_by_fee(fee_ids, db)
    official: dict[int, Decimal] = defaultdict(Decimal)
    agency: dict[int, Decimal] = defaultdict(Decimal)
    for fee_id, contract_no, fee_type, code, amount in fees:
        customer_id = customer_by_contract.get(str(contract_no or "").strip())
        if customer_id is None:
            continue
        if fee_type == OFFICIAL_FEE_TYPE:
            official[customer_id] += paid.get(fee_id, Decimal(0)) - cashed.get(fee_id, Decimal(0))
        elif not code or str(code) in AGENCY_FEE_CODES:
            agency[customer_id] += _amount(amount) - cashed.get(fee_id, Decimal(0))
    for customer_id in result:
        result[customer_id] = {
            "official_fee_unreceived": float(round(official.get(customer_id, Decimal(0)), 2)),
            "agency_fee_due": float(round(agency.get(customer_id, Decimal(0)), 2)),
        }
    return result


_event_table_ready: dict[int, bool] = {}


async def legacy_customer_event_counts(db, customer_ids: list[int]) -> dict[int, int]:
    """旧系统联系次数 = CRM_Customer_Event 条数（不看是否有效、不分内容）；只建了部分表的测试库没有这张表。"""
    if not customer_ids:
        return {}
    key = id(db.get_bind())
    if key not in _event_table_ready:
        _event_table_ready[key] = await db.run_sync(
            lambda session: inspect(session.connection()).has_table(LegacyCustomerHistoryEvent.__tablename__))
    if not _event_table_ready[key]:
        return {}
    return dict((await db.execute(select(
        LegacyCustomerHistoryEvent.customer_record_id, func.count(),
    ).where(LegacyCustomerHistoryEvent.customer_record_id.in_(customer_ids))
      .group_by(LegacyCustomerHistoryEvent.customer_record_id))).all())


async def managed_customers_official_unreceived(db, username: str) -> float:
    """工作台“未到官费金额”：旧系统 GetTotalCaseFeeAmount，本人是客户负责人或在客户协作人里的全部客户（不看是否公海、是否删除）。"""
    import json
    token = json.dumps(username, ensure_ascii=False)
    data = BusinessRecord.data
    customers = (await db.execute(select(BusinessRecord.id, BusinessRecord.serial_no).where(
        BusinessRecord.module == "customer", or_(
            BusinessRecord.owner == username,
            data["customer_managers"].as_string().contains(token, autoescape=True),
            data["coordinators"].as_string().contains(token, autoescape=True),
        ),
    ))).all()
    balances = await customer_fee_balances(db, customers)
    return round(sum(item["official_fee_unreceived"] for item in balances.values()), 2)
