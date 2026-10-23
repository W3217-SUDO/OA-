"""退款归属和进度计算，供费用明细与控制台共用。"""
from sqlalchemy import or_, select

from app.models import BusinessRecord
from app.core.finance_batch_parity import official_refund_progress
from app.core.json_relation_query import json_scalar_overlap, scalar_in_values
from app.core.record_projection_query import read_record_projections


async def read_fee_refunds(fees, db, *, scope_conditions=(), ids=None, summary_only=False):
    fee_ids = {fee.id for fee in fees}
    conditions = [BusinessRecord.module == "refund", *scope_conditions]
    if ids is not None:
        case_nos = {str((fee.data or {}).get("case_no") or "") for fee in fees if (fee.data or {}).get("case_no")}
        conditions.append(or_(
            json_scalar_overlap(BusinessRecord.data, {int(fee_id) for fee_id in ids}),
            scalar_in_values(BusinessRecord.data["case_no"].as_string(), case_nos),
            scalar_in_values(BusinessRecord.data["original_payment_no"].as_string(),
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
    inactive = await inactive_agency_refund_ids(refunds, db)
    refunds = [refund for refund in refunds if refund.id not in inactive]
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


# 10.23 第3行：律师代理费（退费）已删除、已撤回或已作废时，生成它的退费单不再计入待退费和案件“退费”列。
INACTIVE_AGENCY_REFUND_STATUSES = {"已删除", "已撤回", "已作废"}


async def inactive_agency_refund_ids(refunds, db):
    """返回对应律师代理费（退费）已失效的退费单 id；没有律师代理费（退费）的退费单（旧系统）不受影响。"""
    refund_ids = {int(item.id) for item in refunds}
    if not refund_ids:
        return set()
    agency_fees = (await db.execute(
        select(BusinessRecord.status, BusinessRecord.deleted_at, BusinessRecord.data).where(
            BusinessRecord.module == "finance",
            BusinessRecord.data["refund_record_id"].as_integer().in_(refund_ids),
        ).execution_options(include_deleted=True)
    )).all()
    inactive: set[int] = set()
    for status, deleted_at, data in agency_fees:
        if not (data or {}).get("refund_fee"):
            continue
        if deleted_at is not None or str(status or "") in INACTIVE_AGENCY_REFUND_STATUSES:
            inactive.add(int((data or {}).get("refund_record_id") or 0))
    return inactive


async def void_refund_for_agency_fee(fee, operator, db, reason):
    """律师代理费（退费）删除或撤回时，把它对应的草稿退费单标为已作废（逻辑作废，不删除）。"""
    from app.models import WorkflowEvent
    data = fee.data or {}
    if not data.get("refund_fee") or not str(data.get("refund_record_id") or "").isdigit():
        return None
    refund = await db.get(BusinessRecord, int(data["refund_record_id"]))
    if not refund or refund.module != "refund" or refund.status != "草稿":
        return None
    previous = refund.status
    refund.status = "已作废"
    refund.data = {**(refund.data or {}), "voided_reason": reason, "voided_by": operator, "voided_with_fee_id": fee.id}
    db.add(WorkflowEvent(record_id=refund.id, action="退费单随律师代理费（退费）作废", from_status=previous,
                         to_status="已作废", operator=operator, comment=f"{reason}：{fee.serial_no}"))
    return refund


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
