"""费用收付款的关联读取；明细和金额统计共用同一归属与舍入规则。"""
from sqlalchemy import or_, select

from app.models import BusinessRecord, FinanceTransaction, IncomingPayment
from app.core.json_relation_query import json_scalar_overlap
from app.core.query_batches import _scalars_in_batches


def _case_fee_link_maps(fees: list[BusinessRecord]) -> tuple[set[int], dict[int, int]]:
    fee_ids = {item.id for item in fees}
    legacy_candidates: dict[int, set[int]] = {}
    for item in fees:
        data = item.data or {}
        for key in ("legacy_case_fee_id", "legacy_fee_id"):
            try:
                legacy_id = int(data.get(key) or 0)
            except (TypeError, ValueError):
                legacy_id = 0
            if legacy_id:
                legacy_candidates.setdefault(legacy_id, set()).add(item.id)
    return fee_ids, {
        legacy_id: next(iter(candidate_ids))
        for legacy_id, candidate_ids in legacy_candidates.items()
        if len(candidate_ids) == 1
    }


def _resolve_case_fee_link_id(link: dict, fee_ids: set[int], legacy_fee_ids: dict[int, int]) -> int:
    for key in ("fee_record_id", "fee_id"):
        try:
            linked_id = int(link.get(key) or 0)
        except (AttributeError, TypeError, ValueError):
            linked_id = 0
        if linked_id in fee_ids:
            return linked_id
        if linked_id in legacy_fee_ids:
            return legacy_fee_ids[linked_id]
    for key in ("legacy_case_fee_id", "legacy_fee_id"):
        try:
            legacy_id = int(link.get(key) or 0)
        except (AttributeError, TypeError, ValueError):
            legacy_id = 0
        if legacy_id in legacy_fee_ids:
            return legacy_fee_ids[legacy_id]
    return 0


async def read_fee_payments(fee_ids, db):
    transactions = await _scalars_in_batches(
        db, fee_ids, lambda batch: select(FinanceTransaction).where(
            FinanceTransaction.finance_record_id.in_(batch),
            FinanceTransaction.transaction_type == "付款",
        ),
    )
    transactions.sort(key=lambda item: (item.transaction_date, item.id), reverse=True)
    payments_by_fee = {}
    for transaction in transactions:
        if transaction.finance_record_id:
            payments_by_fee.setdefault(transaction.finance_record_id, []).append(transaction)
    return payments_by_fee


def fee_paid_amount(data, payments):
    # 保留原明细按日期倒序逐笔求和、分别舍入后取大值的金额口径。
    transaction_paid = round(sum(float(tx.amount or 0) for tx in payments), 2)
    return max(transaction_paid, round(float(data.get("paid_amount") or 0), 2))


async def read_fee_receipts(fees, fees_by_case, unambiguous_case_nos, db, *, filter_related):
    fee_ids, legacy_fee_ids = _case_fee_link_maps(fees)
    fees_by_id = {item.id: item for item in fees}
    case_nos = {str((item.data or {}).get("case_no") or "") for item in fees if (item.data or {}).get("case_no")}
    conditions = []
    if filter_related:
        conditions.append(or_(
            json_scalar_overlap(IncomingPayment.allocations, fee_ids | set(legacy_fee_ids)),
            json_scalar_overlap(IncomingPayment.allocations, case_nos),
        ))
    incoming = list((await db.scalars(select(IncomingPayment).where(*conditions).order_by(
        IncomingPayment.received_date.desc(), IncomingPayment.id.desc(),
    ))).all())
    receipts_by_fee = {}
    for payment in incoming:
        for allocation in payment.allocations or []:
            if not isinstance(allocation, dict):
                continue
            allocation_case_no = str(allocation.get("case_no") or "").strip()
            linked_nested = False
            for settlement_item in allocation.get("settlement_items") or []:
                if not isinstance(settlement_item, dict):
                    continue
                nested_fee_id = _resolve_case_fee_link_id(settlement_item, fee_ids, legacy_fee_ids)
                linked_fee = fees_by_id.get(nested_fee_id)
                linked_case_no = str(((linked_fee.data or {}) if linked_fee else {}).get("case_no") or "").strip()
                if nested_fee_id in fee_ids and (not allocation_case_no or allocation_case_no == linked_case_no):
                    nested_amount = float(settlement_item.get("amount") or settlement_item.get("settlement_amount") or 0)
                    receipts_by_fee.setdefault(nested_fee_id, []).append((payment, nested_amount))
                    linked_nested = True
            if linked_nested:
                continue
            fee_id = _resolve_case_fee_link_id(allocation, fee_ids, legacy_fee_ids)
            if not fee_id:
                try:
                    fee_id = int(allocation.get("finance_record_id") or 0)
                except (AttributeError, TypeError, ValueError):
                    pass
            if fee_id not in fee_ids:
                legacy_case_no = str(allocation.get("case_no") or "")
                candidates = fees_by_case.get(legacy_case_no, []) if legacy_case_no in unambiguous_case_nos else []
                if len(candidates) == 1:
                    fee_id = candidates[0].id
            linked_fee = fees_by_id.get(fee_id)
            linked_case_no = str(((linked_fee.data or {}) if linked_fee else {}).get("case_no") or "").strip()
            if fee_id in fee_ids and (not allocation_case_no or allocation_case_no == linked_case_no):
                receipts_by_fee.setdefault(fee_id, []).append((payment, float(allocation.get("amount") or 0)))
    return receipts_by_fee
