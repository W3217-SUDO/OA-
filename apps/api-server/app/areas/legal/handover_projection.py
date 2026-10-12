"""交接清单的费用与回款投影，按来源主键去重并保留财务可见范围。"""

from datetime import date
from decimal import Decimal

from sqlalchemy import or_, select

from app.models import BusinessRecord, IncomingPayment, LegacyFinanceAllocation, LegacyFinanceRecord
from app.core.json_relation_query import json_scalar_overlap, scalar_in_values


def _amount(value) -> Decimal | None:
    return None if value is None or value == "" else Decimal(str(value))


def _total(values: list[Decimal | None]) -> str:
    if not values or any(value is None for value in values):
        return ""
    return format(sum(values, Decimal(0)), ".2f")


def _payment_key(payment: IncomingPayment) -> tuple[str, str]:
    # 沪知迁移明确保存 HZ-RCPT-旧PaymentId；不按金额、日期或付款人猜匹配。
    if payment.source_kind == "hz_crm_20260930" and payment.receipt_no.startswith("HZ-RCPT-"):
        return "FAM_AR_Payment", payment.receipt_no.removeprefix("HZ-RCPT-")
    return "incoming_payments", str(payment.id)


def _fee_source_keys(fee: BusinessRecord) -> set[tuple[str, str]]:
    data = fee.data or {}
    legacy = data.get("legacy_record") if isinstance(data.get("legacy_record"), dict) else {}
    source = str(legacy.get("_source_database") or "")
    return {(source, str(value)) for value in [data.get("legacy_case_fee_id"), data.get("legacy_fee_id"), legacy.get("CaseFeeId")] if value is not None and value != ""}


async def handover_export_rows(records, projections: list[dict], identity: dict, db) -> list[list]:
    from app.core.fee_cash_query import _case_fee_link_maps, _resolve_case_fee_link_id
    from app.core.finance import _visible_incoming_payment_statement
    from app.core.legacy_sync import _legacy_finance_scope_conditions
    from app.core.permissions import _record_scope_conditions

    case_ids = [record.id for record in records]
    case_nos = [record.serial_no for record in records]
    scope = await _record_scope_conditions(identity, db)
    fees = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance", BusinessRecord.status != "已删除", *scope,
        or_(scalar_in_values(BusinessRecord.data["case_record_id"].as_integer(), case_ids), scalar_in_values(BusinessRecord.data["case_id"].as_integer(), case_ids), scalar_in_values(BusinessRecord.data["case_no"].as_string(), case_nos)),
    ))).all())
    lawyer_fees = []
    for fee in fees:
        data = fee.data or {}
        legacy = data.get("legacy_record") if isinstance(data.get("legacy_record"), dict) else {}
        code = str(data.get("fee_type_code") or legacy.get("CaseFeeTypeId") or "")
        if code == "11020010" or not code and str(data.get("fee_type_name") or data.get("fee_type") or "") in {"代理费", "律师代理费"}:
            lawyer_fees.append(fee)
    fee_ids, legacy_fee_ids = _case_fee_link_maps(lawyer_fees)
    receipts = {record.id: {} for record in records}
    amounts = {record.id: [] for record in records}
    ids_by_no = {record.serial_no: record.id for record in records}
    nos_by_id = {record.id: record.serial_no for record in records}
    fee_case_ids = {}
    modern_fee_keys = set()
    for fee in lawyer_fees:
        data = fee.data or {}
        case_id = int(data.get("case_record_id") or data.get("case_id") or ids_by_no.get(data.get("case_no"), 0))
        if case_id in amounts:
            fee_case_ids[fee.id] = case_id
            amounts[case_id].append(_amount(data.get("amount")))
            modern_fee_keys.update((case_id, *key) for key in _fee_source_keys(fee))

    visible_statement = await _visible_incoming_payment_statement(identity, db)
    payments = (await db.scalars(visible_statement.where(
        json_scalar_overlap(IncomingPayment.allocations, fee_ids | set(legacy_fee_ids)),
    ).order_by(IncomingPayment.received_date, IncomingPayment.id))).all()
    for payment in payments:
        matched = set()
        for allocation in payment.allocations or []:
            for part in allocation.get("settlement_items") or [allocation]:
                fee_id = _resolve_case_fee_link_id(part, fee_ids, legacy_fee_ids)
                if fee_id in fee_case_ids:
                    case_id = fee_case_ids[fee_id]
                    if allocation.get("case_no") and allocation["case_no"] != nos_by_id[case_id]:
                        continue
                    matched.add(case_id)
        for case_id in matched:
            receipts[case_id][_payment_key(payment)] = (payment.received_date.isoformat(), payment.bank_source, payment.payer_name, _amount(payment.amount))

    legacy_scope = await _legacy_finance_scope_conditions(identity, db)
    legacy_rows = (await db.execute(select(LegacyFinanceAllocation, LegacyFinanceRecord)
        .join(LegacyFinanceRecord, LegacyFinanceAllocation.legacy_finance_record_id == LegacyFinanceRecord.id)
        .where(LegacyFinanceAllocation.source_table == "FAM_AR_Payment_Object", scalar_in_values(LegacyFinanceAllocation.case_record_id, case_ids),
               LegacyFinanceAllocation.is_active.is_(True), LegacyFinanceRecord.source_table == "FAM_AR_Payment", LegacyFinanceRecord.record_kind == "ar_payment", LegacyFinanceRecord.is_active.is_(True), *legacy_scope)
        .order_by(LegacyFinanceRecord.id, LegacyFinanceAllocation.id))).all()
    legacy_fees = (await db.scalars(select(LegacyFinanceRecord).where(
        LegacyFinanceRecord.source_table == "FAM_AR_CaseFee", scalar_in_values(LegacyFinanceRecord.case_record_id, case_ids), LegacyFinanceRecord.is_active.is_(True), *legacy_scope,
    ))).all()
    lawyer_legacy = {}
    for fee in legacy_fees:
        payload = fee.source_payload or {}
        if str(payload.get("CaseFeeTypeId")) != "11020010":
            continue
        raw_id = str(payload.get("CaseFeeId") or fee.legacy_id)
        key = (fee.case_record_id, str(payload.get("_source_database") or ""), raw_id)
        lawyer_legacy[key] = fee
        if key not in modern_fee_keys:
            amounts[fee.case_record_id].append(_amount(payload.get("Amount")))

    source_receipts = {"HZ-RCPT-" + payment.legacy_id for _, payment in legacy_rows}
    counterparts = list((await db.scalars(select(IncomingPayment).where(
        IncomingPayment.source_kind == "hz_crm_20260930", scalar_in_values(IncomingPayment.receipt_no, source_receipts),
    ))).all())
    visible_counterparts = set((await db.scalars(visible_statement.with_only_columns(IncomingPayment.id).where(
        IncomingPayment.source_kind == "hz_crm_20260930", scalar_in_values(IncomingPayment.receipt_no, source_receipts),
    ))).all())
    counterparts_by_no = {payment.receipt_no: payment for payment in counterparts}
    for allocation, payment in legacy_rows:
        payload = allocation.source_payload or {}
        fee_key = (allocation.case_record_id, str(payload.get("_source_database") or ""), allocation.legacy_case_fee_id)
        if fee_key not in lawyer_legacy:
            continue
        counterpart = counterparts_by_no.get("HZ-RCPT-" + payment.legacy_id)
        if counterpart and counterpart.id not in visible_counterparts:
            continue
        source_key = ("FAM_AR_Payment", payment.legacy_id)
        if source_key in receipts[allocation.case_record_id]:
            continue
        header = payment.source_payload or {}
        receipts[allocation.case_record_id][source_key] = (str(header.get("CashedDate") or "")[:10], str(header.get("PaymentModeName") or ""), str(header.get("PayerName") or ""), _amount(header.get("CashedAmount")))
    result = []
    for index, (record, item) in enumerate(zip(records, projections, strict=True), 1):
        entries = list(receipts[record.id].values())
        result.append([
            index, item["contract_no"], item["case_no"], item["plaintiff"], item["defendant"], item["archive_no"] or item["stage"],
            item["cause"], item["assistant"], item["court_lawyer"], ",".join(row[0] for row in entries if row[0]),
            ",".join("中行" if "中行" in row[1] else row[1] for row in entries if row[1]), ",".join(row[2] for row in entries if row[2]),
            _total([row[3] for row in entries]), _total(amounts[record.id]), "", date.today().isoformat(),
        ])
    return result
