"""回款与结算共用的持久化操作。调用方管理提交与回滚。"""

from app.core.dependencies import (
    AsyncSession, BusinessRecord, FinanceTransaction, IncomingPayment, ReceivablePlan, select,
)


_INACTIVE_SETTLEMENT_STATUSES = {"已拒绝", "已驳回", "已退回", "已撤回", "已作废"}


async def _active_settlements_by_receipt(
    db: AsyncSession,
    receipt_ids: set[int],
    *,
    exclude_application_ids: set[int] | None = None,
) -> dict[int, BusinessRecord]:
    if not receipt_ids:
        return {}
    records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance_settlement",
        BusinessRecord.status.not_in(_INACTIVE_SETTLEMENT_STATUSES),
    ))).all())
    excluded = exclude_application_ids or set()
    result: dict[int, BusinessRecord] = {}
    for record in records:
        if record.id in excluded:
            continue
        receipt_id = int((record.data or {}).get("receipt_id") or 0)
        if receipt_id in receipt_ids:
            result.setdefault(receipt_id, record)
    return result


async def _revert_incoming_allocation(allocation: dict, db: AsyncSession, *, payment_id: int) -> None:
    from app.core.finance import (
        _round_fee_amount,
    )

    amount = _round_fee_amount(float(allocation.get("amount") or 0))
    plan = await db.get(ReceivablePlan, int(allocation.get("receivable_plan_id") or 0))
    if plan:
        plan.received_amount = max(_round_fee_amount(plan.received_amount - amount), 0)
        plan.status = "待收款" if plan.received_amount <= 0 else "部分收款"
    fee = await db.get(BusinessRecord, int(allocation.get("fee_record_id") or 0))
    if fee and fee.module == "finance":
        fee_data = dict(fee.data or {})
        if allocation.get("is_refund") is True:
            fee_data["refunded_amount"] = max(_round_fee_amount(float(fee_data.get("refunded_amount") or 0) - amount), 0)
        current_received = float(fee_data.get("received_amount") or fee_data.get("cashed_amount") or 0)
        remaining_received = max(_round_fee_amount(current_received - amount), 0)
        fee_data["received_amount"] = remaining_received
        if "cashed_amount" in fee_data:
            fee_data["cashed_amount"] = remaining_received
        if remaining_received <= 0.001:
            for key in ("received_at", "cashed_date", "incoming_payment_id", "receipt_no"):
                fee_data.pop(key, None)
        elif int(fee_data.get("incoming_payment_id") or 0) == payment_id:
            remaining_receipts = list((await db.scalars(select(IncomingPayment).where(
                IncomingPayment.id != payment_id,
            ).order_by(IncomingPayment.received_date.desc(), IncomingPayment.id.desc()))).all())
            latest = next((receipt for receipt in remaining_receipts if any(
                int(row.get("fee_record_id") or 0) == fee.id for row in (receipt.allocations or [])
            )), None)
            if latest:
                fee_data["incoming_payment_id"] = latest.id
                fee_data["receipt_no"] = latest.receipt_no
                fee_data["received_at"] = latest.received_date.isoformat()
                fee_data["cashed_date"] = latest.received_date.isoformat()
            else:
                for key in ("received_at", "cashed_date", "incoming_payment_id", "receipt_no"):
                    fee_data.pop(key, None)
        fee.data = fee_data
    tx = await db.get(FinanceTransaction, int(allocation.get("transaction_id") or 0))
    if tx:
        await db.delete(tx)


def _settlement_financial_snapshot(data: dict) -> dict:
    from app.core.finance import (
        _round_fee_amount,
    )

    amount_keys = (
        "receipt_amount", "allocated_amount", "remaining_amount", "assigned_official_fee",
        "assigned_agency_fee", "assigned_other_fee", "agency_settlement_amount", "archive_fee",
        "actual_settlement_amount",
    )
    return {
        **{key: _round_fee_amount(float(data.get(key) or 0)) for key in amount_keys},
        "allocation_details": data.get("allocation_details") or [],
    }
