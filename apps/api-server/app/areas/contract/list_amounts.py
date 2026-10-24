"""合同列表的 13 个金额，按旧系统合同查询口径从案件费用、收付款和发票实时汇总。

旧系统 ContractBasicInfo 的列：官费（CaseOfficeFee）支付/到账/未到/亏损，代理费（CaseNonOfficeFee）
总额/到账/待收，其他金额（CaseCommissionFee，费用大类 1103“其他费用”）总额/已支付/待支付，
发票已开/应开（未开）/高开。合同本身不存这些数，列表每次按当页合同计算。
"""
from sqlalchemy import select

from app.areas.contract.receivable_export_rows import receivable_export_rows
from app.core.finance import _receivable_fee_category
from app.models import BusinessRecord

CONTRACT_AMOUNT_KEYS = (
    "official_paid", "official_received", "official_unreceived", "official_loss",
    "agency_total", "agency_received", "agency_due",
    "other_total", "other_paid", "other_due",
    "invoice_opened", "invoice_should", "invoice_excess",
)
_VALID_INVOICE_STATUSES = ("已开票", "已付款")


def _fee_class(raw_type: str, type_code: str, display_type: str) -> str:
    if raw_type == "官方费用" or _receivable_fee_category(display_type) == "official":
        return "official"
    if raw_type == "其他费用" or type_code.startswith("1103") or display_type.startswith("其他"):
        return "other"
    return "agency"


def _number(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


async def contract_list_amounts(contracts: list[dict], identity: dict, db) -> dict[int, dict[str, float]]:
    totals = {row["id"]: dict.fromkeys(CONTRACT_AMOUNT_KEYS, 0.0) for row in contracts}
    if not totals:
        return {}
    rows = await receivable_export_rows(contracts, identity, db, fees_by_case=True)
    fee_ids = {row["fee_record_id"] for row in rows if row.get("fee_record_id")}
    fee_types = {
        fee_id: (str(raw or ""), str(code or "")) for fee_id, raw, code in (await db.execute(select(
            BusinessRecord.id, BusinessRecord.data["fee_type"].as_string(), BusinessRecord.data["fee_type_code"].as_string(),
        ).where(BusinessRecord.id.in_(fee_ids)))).all()
    } if fee_ids else {}
    fee_contract: dict[int, int] = {}
    billable = dict.fromkeys(totals, 0.0)
    for row in rows:
        amounts = totals[row["contract_record_id"]]
        raw, code = fee_types.get(row.get("fee_record_id"), ("", ""))
        kind = _fee_class(raw, code, str(row.get("fee_type") or ""))
        amount, paid = _number(row["amount"]), _number(row["paid_amount"])
        received, remaining = _number(row["received_amount"]), _number(row["remaining_amount"])
        if kind == "official":
            amounts["official_paid"] += paid
            amounts["official_received"] += received
            amounts["official_unreceived"] += remaining
            if "亏损" in str(row.get("phase") or ""):
                amounts["official_loss"] += remaining
        elif kind == "agency":
            amounts["agency_total"] += amount
            amounts["agency_received"] += received
            amounts["agency_due"] += remaining
        else:
            amounts["other_total"] += amount
            amounts["other_paid"] += paid
            amounts["other_due"] += amount - paid
        billable[row["contract_record_id"]] += amount
        if row.get("fee_record_id"):
            fee_contract[row["fee_record_id"]] = row["contract_record_id"]

    # 发票按开票分配到的案件费用归到合同；一张发票跨合同时，票面和高开按分配金额比例拆分。
    invoiced_against_fees = dict.fromkeys(totals, 0.0)
    if fee_contract:
        invoices = (await db.execute(select(
            BusinessRecord.data["case_fee_allocations"], BusinessRecord.data["invoice_amount"].as_string(),
            BusinessRecord.data["invoice_over_amount"].as_string(),
        ).where(BusinessRecord.module == "invoice", BusinessRecord.status.in_(_VALID_INVOICE_STATUSES)))).all()
        for allocations, face, over in invoices:
            shares: dict[int, float] = {}
            for item in allocations or []:
                if not isinstance(item, dict):
                    continue
                try:
                    contract_id = fee_contract.get(int(item.get("fee_id") or 0))
                except (TypeError, ValueError):
                    continue
                if contract_id is not None:
                    shares[contract_id] = shares.get(contract_id, 0.0) + _number(item.get("amount"))
            if not shares:
                continue
            allocated = sum(_number(item.get("amount")) for item in allocations if isinstance(item, dict)) or 1.0
            face_amount = _number(face) or allocated
            for contract_id, share in shares.items():
                ratio = share / allocated
                totals[contract_id]["invoice_opened"] += face_amount * ratio
                totals[contract_id]["invoice_excess"] += _number(over) * ratio
                invoiced_against_fees[contract_id] += share
    for contract_id, amounts in totals.items():
        amounts["invoice_should"] = max(billable[contract_id] - invoiced_against_fees[contract_id], 0.0)
        for key, value in amounts.items():
            amounts[key] = round(value, 2)
    return totals


async def attach_contract_list_amounts(items: list[dict], identity: dict, db, allowed_fields: set[str]) -> list[dict]:
    """把金额写进列表行的 data；无合同金额字段权限时给 None，前端显示“—”。"""
    if not items:
        return items
    amounts = await contract_list_amounts(items, identity, db) if "contract.amount" in allowed_fields else {}
    for item in items:
        values = amounts.get(item["id"])
        item["data"] = {**(item.get("data") or {}), **(values or dict.fromkeys(CONTRACT_AMOUNT_KEYS))}
    return items
