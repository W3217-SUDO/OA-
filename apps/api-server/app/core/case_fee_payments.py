"""案件费用请款的原始占额、合同申请及只读金额投影。"""
from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.exc import OperationalError

from app.models import BusinessRecord, FinanceTransaction


ACTIVE_CONTRACT_PAYMENT_STATUSES = {"待审批", "待付款", "待核销", "已付款", "已核销"}
PAYMENT_PROJECTION_KEYS = {
    "direct_payment_requested_amount", "contract_payment_requested_amount",
    "payment_requested_amount", "payment_remaining_amount",
    "payment_request_amount", "payment_package_amount",
}


async def lock_case_fee_rows(fee_ids, db):
    """两个申请入口都锁费用本身，跨合同也不能重复占用余额。"""
    ids = sorted(set(fee_ids))
    if not ids:
        return []
    try:
        for fee_id in ids:
            await db.execute(update(BusinessRecord).where(
                BusinessRecord.id == fee_id, BusinessRecord.module == "finance",
            ).values(id=BusinessRecord.id, updated_at=BusinessRecord.updated_at)
              .execution_options(synchronize_session=False))
    except OperationalError as exc:
        if "locked" in str(exc.orig).lower() or getattr(exc.orig, "sqlstate", None) in {"40001", "40P01"}:
            raise HTTPException(409, "该费用正在申请付款，请刷新后重试") from exc
        raise
    rows = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(ids), BusinessRecord.module == "finance",
    ).order_by(BusinessRecord.id).with_for_update().execution_options(populate_existing=True))).all())
    if len(rows) != len(ids):
        raise HTTPException(404, "申请付款的费用不存在")
    return rows


async def contract_fee_reservations(fee_ids, db, *, contract=None):
    """以稳定费用 ID 汇总已持久化申请，不依赖费用当前合同或字段回填。"""
    from app.core.finance import _fee_matches_contract, _round_fee_amount
    if not fee_ids:
        return {}
    payments = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "contract_payment",
        BusinessRecord.status.in_(ACTIVE_CONTRACT_PAYMENT_STATUSES),
    ))).all()
    amounts = {}
    for payment in payments:
        if contract and not _fee_matches_contract(payment, contract):
            continue
        for line in (payment.data or {}).get("lines", []):
            if not isinstance(line, dict):
                continue
            try:
                fee_id = int(line.get("case_fee_id") or 0)
            except (ValueError, TypeError):
                continue
            if fee_id in fee_ids:
                amounts[fee_id] = _round_fee_amount(amounts.get(fee_id, 0) + float(line.get("amount") or 0))
    return amounts


async def fee_payment_totals(records, db):
    """每批费用查询一次申请和一次流水，原始直接请款字段始终不改写。"""
    from app.core.finance import _round_fee_amount
    from app.core.invoice_sources import is_external_case_fee
    fees = [item for item in records if is_external_case_fee(item)]
    ids = {item.id for item in fees}
    if not ids:
        return {}
    contract_amounts = await contract_fee_reservations(ids, db)
    paid_amounts = await direct_fee_paid_amounts(fees, db)
    result = {}
    for fee in fees:
        data = fee.data or {}
        direct = _round_fee_amount(float(data.get("payment_requested_amount") or 0))
        paid = paid_amounts[fee.id]
        contract = contract_amounts.get(fee.id, 0)
        result[fee.id] = {
            "direct_payment_requested_amount": direct,
            "contract_payment_requested_amount": contract,
            "payment_requested_amount": _round_fee_amount(direct + contract),
            "payment_remaining_amount": max(_round_fee_amount(abs(float(data.get("amount") or 0)) - max(paid, direct) - contract), 0),
        }
    return result


async def direct_fee_paid_amounts(records, db):
    """统一读取真实付款流水及历史已付字段，不能只依赖某个写入口的字段。"""
    ids = {item.id for item in records}
    if not ids:
        return {}
    amounts = dict((await db.execute(select(
        FinanceTransaction.finance_record_id, func.sum(FinanceTransaction.amount),
    ).where(FinanceTransaction.finance_record_id.in_(ids), FinanceTransaction.transaction_type == "付款")
      .group_by(FinanceTransaction.finance_record_id))).all())
    return {item.id: max(float(amounts.get(item.id) or 0), float((item.data or {}).get("paid_amount") or 0)) for item in records}


async def release_direct_fee_request(item, db):
    """调用者持有费用锁；撤回、回滚或驳回只释放本轮未付款申请。"""
    from app.core.finance import _round_fee_amount
    data = item.data or {}
    if "payment_requested_amount" not in data:
        return
    paid = (await direct_fee_paid_amounts([item], db))[item.id]
    requested = float(data["payment_requested_amount"] or 0)
    current = float(data.get("payment_request_amount", requested) or 0)
    item.data = {**data, "payment_requested_amount": _round_fee_amount(max(paid, requested - current)), "payment_request_amount": 0}


async def direct_fee_payment_amounts(records, db):
    """外部费用仅支付直接申请的未付部分，合同申请使用独立付款单。"""
    from app.core.finance import _round_fee_amount
    from app.core.invoice_sources import is_external_case_fee
    fees = [item for item in records if is_external_case_fee(item)]
    totals = await fee_payment_totals(fees, db)
    paid_by_id = await direct_fee_paid_amounts(fees, db)
    result = {}
    for fee in fees:
        data = fee.data or {}
        # 原有整笔费用审批没有独立申请字段，仍按整笔批准金额支付。
        requested = float(data["payment_requested_amount"]) if "payment_requested_amount" in data else float(data.get("amount") or 0)
        paid = max(float(paid_by_id.get(fee.id) or 0), float(data.get("paid_amount") or 0))
        amount = _round_fee_amount(requested - paid)
        if amount <= 0 or requested + totals[fee.id]["contract_payment_requested_amount"] > float(data.get("amount") or 0) + .001:
            raise HTTPException(409, "直接付款申请与合同申请合计超过费用金额，或本申请已付清")
        result[fee.id] = amount
    return result


def apply_fee_payment_projection(payload, totals, allowed_fields):
    """只改响应副本；隐藏金额时连原始请求金额也不能泄漏。"""
    if payload["module"] != "finance":
        return payload
    data = payload["data"]
    if allowed_fields is not None and "finance.amount" not in allowed_fields:
        for key in PAYMENT_PROJECTION_KEYS:
            data.pop(key, None)
    elif payload["id"] in totals:
        data.update(totals[payload["id"]])
    return payload
