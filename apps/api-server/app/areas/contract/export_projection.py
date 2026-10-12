"""合同导出沿用列表范围、客户投影和真实应收关联。"""
from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy import or_, select

from app.models import BusinessRecord
from app.core.json_relation_query import scalar_in_values
from app.core.constants import _INVALID_RECEIVABLE_FEE_STATUSES
from app.core.permissions import _require_record_module_menu
from app.core.system import _allowed_field_keys
from app.core.finance_summary_query import receivable_payment_projection
from app.areas.contract.export_workbooks import render_workbook


def contract_signed_date(data):
    """历史签订日期来源于审批日期字段，不使用记录创建时间。"""
    legacy = data.get("legacy_record") or {}
    return str(data.get("signed_at") or legacy.get("AuditDate") or "")[:10]


async def contract_export_rows(identity, db, **filters):
    from app.areas.legal.record_queries import list_records
    await _require_record_module_menu("contract", identity, db, action="导出")
    result = await list_records(
        module="contract", record_type=filters.pop("record_type", ""),
        scope=filters.pop("scope", "all"), customer_id=None,
        finance_view="", investigation_view="", archive_view="", page=1, page_size=65536,
        identity=identity, db=db, **filters,
    )
    if result["total"] > len(result["items"]):
        raise HTTPException(422, "导出行数超过 XLS 上限，请缩小查询范围")
    return result["items"]


async def contract_export_amounts(contracts, identity, db):
    """旧合同以关联案件费用为金额来源，标的用于尚未产生费用的新合同。"""
    contract_ids = {row["id"] for row in contracts}
    contract_nos = {row["serial_no"] for row in contracts}
    totals = {key: [0.0, 0.0, 0.0] for key in contract_ids}
    if not contract_ids:
        return totals
    fees = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance", BusinessRecord.status.not_in({"已删除", "已撤回", *_INVALID_RECEIVABLE_FEE_STATUSES}),
        or_(scalar_in_values(BusinessRecord.data["contract_id"].as_integer(), contract_ids),
            scalar_in_values(BusinessRecord.data["contract_record_id"].as_integer(), contract_ids),
            scalar_in_values(BusinessRecord.data["contract_no"].as_string(), contract_nos)),
    ))).all())
    cash = await receivable_payment_projection(fees, identity, db, receipts_only=True)
    by_no = {row["serial_no"]: row["id"] for row in contracts}
    fee_contracts = set()
    for fee in fees:
        data = fee.data or {}
        contract_id = int(data.get("contract_record_id") or data.get("contract_id") or by_no.get(data.get("contract_no")) or 0)
        if contract_id not in totals:
            raise HTTPException(409, f"费用 {fee.serial_no} 的合同关联不一致，请先核对合同编号与记录关联")
        fee_contracts.add(contract_id)
        legacy = data.get("legacy_record") or {}
        customer_pays = data.get("payment_by_customer", legacy.get("PaymentByCustomer", False))
        if str(customer_pays).strip().lower() not in {"true", "t", "1"}:
            if data.get("amount") is None:
                totals[contract_id][0] = None
            elif totals[contract_id][0] is not None:
                totals[contract_id][0] += float(data["amount"])
        # 与费用查询一致，以已关联收款分配的有符号金额为唯一回款来源。
        totals[contract_id][1] += cash[fee.id]["cashed_amount"]
    from app.models import ContractObject
    objects = (await db.execute(select(ContractObject.contract_record_id, ContractObject.amount).where(
        scalar_in_values(ContractObject.contract_record_id, contract_ids - fee_contracts),
    ))).all() if contract_ids - fee_contracts else []
    for item in objects:
        totals[item.contract_record_id][0] += float(item.amount or 0)
    for values in totals.values():
        values[0] = round(values[0], 2) if values[0] is not None else None
        values[1] = round(values[1], 2)
        values[2] = round(values[0] - values[1], 2) if values[0] is not None else None
    return totals


async def render_contract_list(contracts, identity, db, *, summary=False):
    totals = await contract_export_amounts(contracts, identity, db)
    allowed = await _allowed_field_keys(identity, db)
    rows = []
    for item in contracts:
        data = item["data"]
        amounts = totals[item["id"]] if "contract.amount" in allowed else [None] * 3
        rows.append([item["serial_no"], item["title"], item["status"], *amounts,
                     data.get("customer_manager_display_name") or data.get("customer_manager") or "",
                     contract_signed_date(data), data.get("customer_no") or "", item["customer"]])
    total = round(sum(value[2] for value in totals.values()), 2) if "contract.amount" in allowed and all(value[2] is not None for value in totals.values()) else None
    return render_workbook("contract-receivable-summary" if summary else "contract-list", rows,
                           summary=total if summary else None)


async def render_contract_details(contracts, details, identity, db):
    allowed = await _allowed_field_keys(identity, db)
    totals = await contract_export_amounts(contracts, identity, db)
    by_id = {row["id"]: row for row in contracts}
    grouped = defaultdict(list)
    for item in details:
        if item["contract_record_id"] in by_id:
            grouped[item["contract_record_id"]].append(item)
    case_ids = {item.get("case_record_id") for item in details if item.get("case_record_id")}
    titles = dict((await db.execute(select(BusinessRecord.id, BusinessRecord.title).where(
        scalar_in_values(BusinessRecord.id, case_ids), BusinessRecord.module == "case",
    ))).all()) if case_ids else {}
    rows, merges = [], []
    for contract_id, items in grouped.items():
        contract = by_id[contract_id]
        prefix = [contract["serial_no"], contract["title"], contract_signed_date(contract["data"]),
                  *(totals[contract_id] if "contract.amount" in allowed else [None] * 3)]
        start = len(rows)
        for item in items:
            amounts = [item["amount"], item["received_amount"], item["remaining_amount"]] if "contract.amount" in allowed else [None] * 3
            rows.append([*prefix, item["case_no"], item["case_type"], titles.get(item.get("case_record_id"), ""), item["fee_type"], *amounts])
        if len(items) > 1:
            merges.extend((start, len(rows) - 1, column) for column in range(6))
    total = round(sum(totals[key][2] for key in grouped), 2) if "contract.amount" in allowed and all(totals[key][2] is not None for key in grouped) else None
    return render_workbook("contract-receivable-detail", rows, summary=total, groups=merges)
