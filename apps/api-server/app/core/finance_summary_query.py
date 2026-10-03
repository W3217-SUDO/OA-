"""金额统计使用的只读费用字段，不包含完整历史业务快照。"""
from app.core.record_projection_query import read_record_projections
from sqlalchemy import func, or_, select

from app.models import BusinessRecord
from app.core.fee_cash_query import fee_paid_amount, read_fee_payments, read_fee_receipts
from app.core.json_relation_query import scalar_in_values


FEE_SUMMARY_FIELDS = (
    "amount", "paid_amount", "cashed_amount", "received_amount",
    "refund_amount", "refund_requested_amount", "refunded_amount",
    "case_id", "case_record_id", "case_no", "case_title", "case_type", "case_stage",
    "contract_id", "contract_record_id", "contract_no", "contract_object_id",
    "fee_type", "fee_type_name", "case_fee_type_name", "expense_subtype",
    "fee_type_id", "fee_type_code", "legacy_fee_type_code", "expense_scope",
    "legacy_case_fee_id", "legacy_fee_id", "source_fee_id", "commission_type",
    "commission_lifecycle", "is_refund", "writeoff_status", "payment_status",
    "document_no", "paid_date", "payment_date", "cashed_date", "receipt_date",
    "paid_organization", "payee", "payer_name", "received_payer_name", "deadline",
    "assistant", "lawyer_assistant", "hearing_lawyer", "investigator",
    "court_case_no", "certificate_no", "notary_no", "court_name", "court",
    "plaintiff", "opponent", "applicant", "payment_applied_by", "commission_created_by", "handler",
)


async def read_fee_summaries(db, conditions):
    return await read_record_projections(db, conditions, FEE_SUMMARY_FIELDS)


async def receivable_payment_projection(finances, identity, db):
    """应收只计算收付款，复用已读取费用，不构造发票、退款和提成明细。"""
    from app.core.formatters import _case_fee_display_type
    from app.core.permissions import _record_scope_conditions

    fees = [item for item in finances if item.status != "已删除"]
    if not fees:
        return {}
    case_ids = {int((item.data or {}).get("case_id") or 0) for item in fees if (item.data or {}).get("case_id")}
    case_nos = {str((item.data or {}).get("case_no") or "") for item in fees if (item.data or {}).get("case_no")}
    conditions = await _record_scope_conditions(identity, db)
    cases = (await db.execute(select(BusinessRecord.id, BusinessRecord.serial_no).where(
        BusinessRecord.module.in_(("case", "ipr_case")),
        or_(scalar_in_values(BusinessRecord.id, case_ids), scalar_in_values(BusinessRecord.serial_no, case_nos)),
        *conditions,
    ))).all() if case_ids or case_nos else []
    by_id = {item.id: item for item in cases}
    by_no = {item.serial_no: item for item in cases}
    fees_by_case = {}
    for fee in fees:
        data = fee.data or {}
        case = by_id.get(int(data.get("case_id") or 0)) or by_no.get(str(data.get("case_no") or ""))
        linked_no = case.serial_no if case else str(data.get("case_no") or "")
        if linked_no:
            fees_by_case.setdefault(linked_no, []).append(fee)
    unambiguous_case_nos = set(fees_by_case)
    if case_nos:
        # 与明细一致：全库同案只有一笔费用，才允许没有费用编号的旧收款归属。
        case_no_column = BusinessRecord.data["case_no"].as_string()
        counts = (await db.execute(select(case_no_column, func.count(BusinessRecord.id)).where(
            BusinessRecord.module == "finance", case_no_column.in_(case_nos),
        ).group_by(case_no_column))).all()
        unambiguous_case_nos = {number for number, count in counts if count == 1}
    payments = await read_fee_payments({fee.id for fee in fees}, db)
    receipts = await read_fee_receipts(fees, fees_by_case, unambiguous_case_nos, db, filter_related=True)
    return {
        fee.id: {
            "fee_type": _case_fee_display_type(fee),
            "paid_amount": fee_paid_amount(fee.data or {}, payments.get(fee.id, [])),
            "cashed_amount": round(sum(amount for _, amount in receipts.get(fee.id, [])), 2),
        }
        for fee in fees
    }
