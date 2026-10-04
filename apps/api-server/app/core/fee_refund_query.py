"""退款归属和进度计算，供费用明细与控制台共用。"""
from sqlalchemy import or_, select

from app.models import BusinessRecord
from app.core.finance_batch_parity import official_refund_progress
from app.core.json_relation_query import json_scalar_overlap
from app.core.record_projection_query import read_record_projections


async def read_fee_refunds(fees, db, *, scope_conditions=(), ids=None, summary_only=False):
    fee_ids = {fee.id for fee in fees}
    conditions = [BusinessRecord.module == "refund", *scope_conditions]
    if ids is not None:
        case_nos = {str((fee.data or {}).get("case_no") or "") for fee in fees if (fee.data or {}).get("case_no")}
        conditions.append(or_(
            json_scalar_overlap(BusinessRecord.data, {int(fee_id) for fee_id in ids}),
            BusinessRecord.data["case_no"].as_string().in_(case_nos),
            BusinessRecord.data["original_payment_no"].as_string().in_(
                {str((fee.data or {}).get("document_no") or "") for fee in fees} - {""}),
        ))
    if summary_only:
        refunds = await read_record_projections(db, conditions, (
            "fee_record_id", "original_payment_no", "case_no", "amount",
        ))
        refunds.sort(key=lambda item: (item.updated_at, item.id), reverse=True)
    else:
        refunds = list((await db.scalars(select(BusinessRecord).where(*conditions).order_by(
            BusinessRecord.updated_at.desc(), BusinessRecord.id.desc(),
        ))).all())
    by_id = {fee.id: fee for fee in fees}
    by_document_no = {}
    official_by_case = {}
    for fee in fees:
        data = fee.data or {}
        if str(data.get("fee_type") or "") == "官方费用":
            official_by_case.setdefault(str(data.get("case_no") or ""), []).append(fee)
        document_no = str(data.get("document_no") or "").strip()
        if document_no:
            by_document_no[document_no] = fee
    result = {}
    for refund in refunds:
        data = refund.data or {}
        try:
            fee_id = int(data.get("fee_record_id") or 0)
        except (TypeError, ValueError):
            fee_id = 0
        fee = by_id.get(fee_id) if fee_id in fee_ids else None
        if fee is None:
            fee = by_document_no.get(str(data.get("original_payment_no") or "").strip())
        if fee is None:
            candidates = official_by_case.get(str(data.get("case_no") or ""), [])
            if len(candidates) == 1:
                fee = candidates[0]
        if fee:
            result.setdefault(fee.id, []).append(refund)
    return result


def fee_refund_progress(data, refunds, receipts):
    requested = round(sum(float((refund.data or {}).get("amount") or 0)
                          for refund in refunds if refund.status not in {"已驳回", "已作废"}), 2)
    refunded = round(sum(float((refund.data or {}).get("amount") or 0)
                         for refund in refunds if refund.status == "已退款"), 2)
    if not refunds:
        requested = float(data.get("refund_requested_amount") or data.get("refund_amount") or 0)
    refunded = official_refund_progress(
        data, requested, max(refunded, float(data.get("refunded_amount") or 0)),
        round(sum(amount for _, amount in receipts), 2) if receipts
        else data.get("received_amount", data.get("cashed_amount", 0)),
    )
    return requested, refunded


def legacy_refund_progress(raw_data, projected_data):
    requested = max(float(projected_data.get("refund_requested_amount") or 0),
                    float(raw_data.get("refund_requested_amount") or raw_data.get("refund_amount") or 0))
    refunded = max(float(projected_data.get("refunded_amount") or 0), float(raw_data.get("refunded_amount") or 0))
    return requested, official_refund_progress(raw_data, requested, refunded)
