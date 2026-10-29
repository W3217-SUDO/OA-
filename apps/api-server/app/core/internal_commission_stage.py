"""内部提成三个列表（待结算/待归档/待审核）共用的回款、结算、归档事实。

BUG20261029002：待结算=已到账+已分配+未结算；待归档=已结算+案件未归档；
待审核=已结算+案件已归档。只决定列表显示，不改记录状态。
"""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BusinessRecord, IncomingPayment, LegacyFinanceAllocation, LegacyFinanceRecord

ARCHIVED_CASE_STATUSES = {"已归档", "亏损归档"}


def _truthy(value) -> bool:
    return str(value).lower() in {"true", "1"}


async def allocated_fee_ids(db: AsyncSession, fee_ids: set[int]) -> set[int]:
    """回款分配（部分分配/已分配）里出现过的案件费用。"""
    if not fee_ids:
        return set()
    from app.core.json_relation_query import json_text_precheck

    precheck = None if 0 in fee_ids else json_text_precheck(IncomingPayment.allocations, fee_ids)
    payments = (await db.scalars(select(IncomingPayment).where(
        IncomingPayment.status.in_({"部分分配", "已分配"}), *([] if precheck is None else [precheck]),
    ))).all()
    result: set[int] = set()
    for payment in payments:
        for allocation in payment.allocations or []:
            if not isinstance(allocation, dict):
                continue
            for candidate in [allocation, *(allocation.get("settlement_items") or [])]:
                if not isinstance(candidate, dict):
                    continue
                try:
                    fee_id = int(candidate.get("fee_record_id") or candidate.get("fee_id") or 0)
                except (TypeError, ValueError):
                    continue
                if fee_id in fee_ids:
                    result.add(fee_id)
    return result


async def archived_case_ids(db: AsyncSession, case_ids: set[int]) -> set[int]:
    case_ids = {item for item in case_ids if item}
    if not case_ids:
        return set()
    return set((await db.scalars(select(BusinessRecord.id).where(
        BusinessRecord.module == "case", BusinessRecord.id.in_(case_ids),
        BusinessRecord.status.in_(ARCHIVED_CASE_STATUSES),
    ))).all())


async def legacy_line_settled_ids(db: AsyncSession, lines: list[tuple[int, dict]]) -> set[int]:
    """旧系统导入的请款明细是否已结算：来源案件费用的回款全部结算（旧系统 SettlementStatus=25），
    或新系统已标识提成发放。没有回款的算未到账，不算已结算。"""
    if not lines:
        return set()
    internal_fee_ids = {str(data.get("legacy_internal_fee_id") or "") for _, data in lines} - {""}
    internal_fees = {item.legacy_id: item for item in (await db.scalars(select(LegacyFinanceRecord).where(
        LegacyFinanceRecord.source_table == "FAM_InternalFee", LegacyFinanceRecord.legacy_id.in_(internal_fee_ids),
    ))).all()} if internal_fee_ids else {}
    case_fee_by_line = {
        line_id: str((internal_fees[str(data.get("legacy_internal_fee_id") or "")].source_payload or {}).get("CaseFeeId") or "")
        for line_id, data in lines if str(data.get("legacy_internal_fee_id") or "") in internal_fees
    }
    case_fee_ids = set(case_fee_by_line.values()) - {""}
    objects = (await db.scalars(select(LegacyFinanceAllocation).where(
        LegacyFinanceAllocation.source_table == "FAM_AR_Payment_Object",
        LegacyFinanceAllocation.legacy_case_fee_id.in_(case_fee_ids),
    ))).all() if case_fee_ids else []
    receipts = {item.id: item for item in (await db.scalars(select(LegacyFinanceRecord).where(
        LegacyFinanceRecord.id.in_({item.legacy_finance_record_id for item in objects}),
        LegacyFinanceRecord.source_table == "FAM_AR_Payment",
    ))).all()} if objects else {}
    receipt_statuses: dict[str, list[str]] = defaultdict(list)
    for item in objects:
        receipt = receipts.get(item.legacy_finance_record_id)
        if receipt:
            receipt_statuses[item.legacy_case_fee_id].append(str((receipt.source_payload or {}).get("SettlementStatus") or ""))
    source_fee_ids = {int(data.get("source_fee_id")) for _, data in lines if str(data.get("source_fee_id") or "").isdigit()}
    marked_sources = {item.id for item in (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance", BusinessRecord.id.in_(source_fee_ids),
    ))).all() if _truthy((item.data or {}).get("commission_paid"))
        or str((item.data or {}).get("settlement_status") or "") == "25"} if source_fee_ids else set()
    settled = set()
    for line_id, data in lines:
        statuses = receipt_statuses.get(case_fee_by_line.get(line_id, ""), [])
        if (statuses and all(value == "25" for value in statuses)) or (
            str(data.get("source_fee_id") or "").isdigit() and int(data["source_fee_id"]) in marked_sources
        ):
            settled.add(line_id)
    return settled
