"""控制台费用统计只计算筛选所需值，复用明细的付款和状态规则。"""
from sqlalchemy import select

from app.models import BusinessRecord
from app.core.fee_cash_query import fee_paid_amount, read_fee_payments, read_fee_receipts
from app.core.finance import (
    _case_commission_lifecycle_statuses, _finance_fee_payment_status, _matches_unpaid_official_fee,
    _refund_case_fee_status,
)
from app.core.fee_refund_query import fee_refund_progress, legacy_refund_progress, read_fee_refunds
from app.core.finance_read_scope import unambiguous_fee_case_nos
from app.core.formatters import _case_fee_display_type
from app.core.json_relation_query import scalar_in_values
from app.core.legacy_sync import _legacy_case_fee_projection
from app.core.record_projection_query import read_record_projections
from app.core.system import _allowed_field_keys


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


async def dashboard_refund_fee_rows(identity, db, cases):
    """仅计算退款队列条件，不为计数构造发票、付款日期和费用展示明细。"""
    fee_ids = identity["_dashboard_fee_ids"]
    if not fee_ids:
        return []
    fees = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance", BusinessRecord.status != "已删除",
        scalar_in_values(BusinessRecord.id, fee_ids),
    ).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all())
    cases = [case for case in cases if case.id in identity["_dashboard_case_ids"]]
    by_id = {case.id: case for case in cases}
    by_no = {case.serial_no: case for case in cases}
    linked_cases = {}
    fees_by_case = {}
    case_nos = set()
    for fee in fees:
        data = fee.data or {}
        case = by_id.get(int(data.get("case_id") or 0)) or by_no.get(str(data.get("case_no") or ""))
        linked_cases[fee.id] = case
        number = case.serial_no if case else str(data.get("case_no") or "")
        if number:
            fees_by_case.setdefault(number, []).append(fee)
        if data.get("case_no"):
            case_nos.add(str(data["case_no"]))
    unique_nos = await unambiguous_fee_case_nos(case_nos, db) if case_nos else set(fees_by_case)
    receipts = await read_fee_receipts(fees, fees_by_case, unique_nos, db, filter_related=True)
    refunds = await read_fee_refunds(fees, db, ids=fee_ids, summary_only=True)
    show_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    rows = []
    for fee in fees:
        data = fee.data or {}
        requested, refunded = fee_refund_progress(data, refunds.get(fee.id, []), receipts.get(fee.id, []))
        raw_data = _legacy_case_fee_projection(data)
        requested, refunded = legacy_refund_progress(raw_data, {
            "refund_requested_amount": requested if show_amount else None,
            "refunded_amount": refunded if show_amount else None,
        })
        status, _ = _refund_case_fee_status(raw_data)
        if requested <= refunded or status == "R100":
            continue
        case = linked_cases[fee.id]
        rows.append({"id": fee.id, "data": {
            "case_id": case.id if case else data.get("case_id"),
            "case_no": case.serial_no if case else data.get("case_no", ""),
        }})
    return rows
