"""控制台费用统计只计算筛选所需值，复用明细的付款和状态规则。"""
from app.models import BusinessRecord
from app.core.fee_cash_query import fee_paid_amount, read_fee_payments
from app.core.finance import (
    _case_commission_lifecycle_statuses, _finance_fee_payment_status, _matches_unpaid_official_fee,
)
from app.core.formatters import _case_fee_display_type
from app.core.record_projection_query import read_record_projections


async def dashboard_unpaid_fee_rows(identity, db, cases_by_id, cases_by_no, *, fees=None):
    fee_ids = identity["_dashboard_fee_ids"]
    if not fee_ids:
        return []
    if fees is None:
        fees = await read_record_projections(db, [
            BusinessRecord.module == "finance", BusinessRecord.status != "已删除",
            BusinessRecord.id.in_(fee_ids),
        ], (
            "amount", "paid_amount", "case_id", "case_no", "fee_type", "fee_type_name",
            "case_fee_type_name", "expense_subtype", "writeoff_status", "payment_status",
            "source_fee_id", "commission_type", "commission_lifecycle", "is_refund", "expense_scope",
        ))
    fees = sorted(fees, key=lambda item: (item.updated_at, item.id), reverse=True)
    lifecycle = await _case_commission_lifecycle_statuses(fees, db)
    payments = await read_fee_payments({fee.id for fee in fees}, db)
    rows = []
    for fee in fees:
        data = fee.data or {}
        values = {
            "base_fee_type": str(data.get("fee_type") or ""),
            "fee_type": _case_fee_display_type(fee),
            "amount": data.get("amount"),
            "paid_amount": fee_paid_amount(data, payments.get(fee.id, [])),
            "payment_status": _finance_fee_payment_status(fee, lifecycle.get(fee.id)),
        }
        if not _matches_unpaid_official_fee(values):
            continue
        case = cases_by_id.get(int(data.get("case_id") or 0)) or cases_by_no.get(str(data.get("case_no") or ""))
        rows.append({"id": fee.id, "data": {
            "case_id": case.id if case else data.get("case_id"),
            "case_no": case.serial_no if case else data.get("case_no", ""),
        }})
    return rows
