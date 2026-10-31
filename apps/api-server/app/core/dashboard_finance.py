"""控制台费用统计只计算筛选所需值，复用明细的付款和状态规则。"""
from sqlalchemy import select

from app.models import BusinessRecord
from app.core.fee_cash_query import fee_paid_amount, read_fee_payments, read_fee_receipts
from app.core.finance import (
    _case_commission_lifecycle_statuses, _finance_fee_payment_status, _matches_unpaid_official_fee,
    _refund_case_fee_status,
)
from app.core.fee_refund_query import read_fee_refunds
from app.core.finance_read_scope import unambiguous_fee_case_nos
from app.core.formatters import _case_fee_display_type
from app.core.json_relation_query import scalar_in_values
from app.core.legacy_sync import _legacy_case_fee_projection
from app.core.record_projection_query import read_record_projections


LEGACY_UNPAID_OFFICIAL_FEE_CODES = {"11010020", "11010030", "11010040", "11010140", "11010090"}


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
            "case_fee_type_id", "inform_date",
        ))
    # 类型条件与最终筛选一致，非官费不读取付款流水或计算提成生命周期。
    candidates = []
    for fee in fees:
        data = fee.data or {}
        display_type = _case_fee_display_type(fee)
        if (str(data.get("fee_type") or "") == "官方费用"
                or "官费" in display_type or "诉讼费" in display_type
                or display_type in {"保全费", "执行费"}):
            candidates.append((fee, display_type))
    # 类型筛选不依赖顺序，保留候选的原排序，避免对无关费用排序。
    candidates.sort(key=lambda item: (item[0].updated_at, item[0].id), reverse=True)
    fees = [fee for fee, _ in candidates]
    lifecycle = await _case_commission_lifecycle_statuses(fees, db)
    candidates = [(fee, display_type, _finance_fee_payment_status(fee, lifecycle.get(fee.id)))
                  for fee, display_type in candidates]
    candidates = [item for item in candidates if item[2] not in {"已付款", "已驳回", "已作废"}]
    fees = [fee for fee, _, _ in candidates]
    payments = await read_fee_payments({fee.id for fee in fees}, db)
    rows = []
    for fee, display_type, payment_status in candidates:
        data = fee.data or {}
        values = {
            "base_fee_type": str(data.get("fee_type") or ""),
            "fee_type": display_type,
            "amount": data.get("amount"),
            "paid_amount": fee_paid_amount(data, payments.get(fee.id, [])),
            "payment_status": payment_status,
        }
        code = str(data.get("case_fee_type_id") or "").strip()
        if code:
            # 旧系统待缴官费（PageId 5001010002）：这五类官费、2018-04-25 以后通知、还没请款、金额大于已付。
            if (code not in LEGACY_UNPAID_OFFICIAL_FEE_CODES
                    or str(data.get("inform_date") or "")[:10] <= "2018-04-25"
                    or str(data.get("payment_status") or "").strip()
                    or float(data.get("amount") or 0) <= float(data.get("paid_amount") or 0)):
                continue
        elif not _matches_unpaid_official_fee(values):
            continue
        case = cases_by_id.get(int(data.get("case_id") or 0)) or cases_by_no.get(str(data.get("case_no") or ""))
        rows.append({"id": fee.id, "data": {
            "case_id": case.id if case else data.get("case_id"),
            "case_no": case.serial_no if case else data.get("case_no", ""),
        }})
    return rows


LEGACY_PENDING_REFUND_STATUSES = {"R10", "R20", "R30", "R35", "R40", "R50"}


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
    rows = []
    for fee in fees:
        data = fee.data or {}
        raw_data = _legacy_case_fee_projection(data)
        # 旧系统待退费（CaseFeeSearchDao，HasRefundFee）：费用金额 > 0，且
        # (a) 已登记退费进度（10/20/30/35/40/50）、申请退费金额 > 0 且大于已退金额；或
        # (b) 律师代理费(退费)（11020061）金额大于已到账。按费用笔数计。
        if float(data.get("amount") or 0) <= 0:
            continue
        legacy = data.get("legacy_record") if isinstance(data.get("legacy_record"), dict) else {}
        status, _ = _refund_case_fee_status(raw_data)
        # 新系统的退费申请是单独的退费记录，费用上不一定写进度；有退费记录也算已登记。
        has_status = str(data.get("refund_status") or legacy.get("RefundStatus") or "").strip() != "" or bool(refunds.get(fee.id))
        # 旧系统直接比较费用上的申请退费金额和已退金额，不把法院退回的到账算成已退。
        fee_refunds = refunds.get(fee.id, [])
        raw_requested = max(float(data.get("refund_requested_amount") or data.get("refund_amount") or legacy.get("RefundAmount") or 0),
                            sum(float((item.data or {}).get("amount") or 0) for item in fee_refunds
                                if item.status not in {"已驳回", "已作废"}))
        raw_refunded = max(float(data.get("refunded_amount") or legacy.get("RefundedAmount") or 0),
                           sum(float((item.data or {}).get("amount") or 0) for item in fee_refunds if item.status == "已退款"))
        pending_refund = (has_status and status in LEGACY_PENDING_REFUND_STATUSES
                          and raw_requested > 0 and raw_requested > raw_refunded)
        fee_code = str(data.get("case_fee_type_id") or legacy.get("CaseFeeTypeId") or "").strip()
        cashed = max(round(sum(amount for _, amount in receipts.get(fee.id, [])), 2),
                     float(data.get("cashed_amount") or 0))
        uncashed_refund_fee = fee_code == "11020061" and float(data.get("amount") or 0) > cashed
        if not (pending_refund or uncashed_refund_fee):
            continue
        case = linked_cases[fee.id]
        rows.append({"id": fee.id, "data": {
            "case_id": case.id if case else data.get("case_id"),
            "case_no": case.serial_no if case else data.get("case_no", ""),
        }})
    return rows
