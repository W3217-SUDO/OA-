"""应收模板按真实费用记录和收款分配生成有符号明细。"""
from collections import defaultdict
from sqlalchemy import or_, select

from app.models import BusinessRecord, ContractObject
from app.core.constants import _INVALID_RECEIVABLE_FEE_STATUSES
from app.core.finance import _fee_matches_contract_object, _receivable_fee_category, _receivable_relation_id
from app.core.finance_summary_query import receivable_payment_projection
from app.core.formatters import _case_fee_display_type
from app.core.json_relation_query import scalar_in_values
from app.core.invoice_sources import is_external_case_fee
from app.core.permissions import _record_scope_conditions


async def receivable_export_rows(contracts, identity, db, *, case_ids=None):
    """费用只出现一次；未生成费用的合同标的保留为独立应收义务。"""
    by_contract_id = {row["id"]: row for row in contracts}
    by_contract_no = {row["serial_no"]: row for row in contracts}
    if not contracts:
        return []
    object_case_ids = select(ContractObject.case_record_id).where(
        scalar_in_values(ContractObject.contract_record_id, by_contract_id))
    cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case", *(await _record_scope_conditions(identity, db)),
        or_(BusinessRecord.id.in_(object_case_ids),
            scalar_in_values(BusinessRecord.data["contract_id"].as_integer(), by_contract_id),
            scalar_in_values(BusinessRecord.data["contract_record_id"].as_integer(), by_contract_id),
            scalar_in_values(BusinessRecord.data["contract_no"].as_string(), by_contract_no)),
    ))).all())
    if case_ids is not None:
        cases = [case for case in cases if case.id in case_ids]
    by_case_id = {case.id: case for case in cases}
    by_case_no = {case.serial_no: case for case in cases}
    objects = list((await db.scalars(select(ContractObject).where(
        scalar_in_values(ContractObject.contract_record_id, by_contract_id),
        scalar_in_values(ContractObject.case_record_id, by_case_id),
    ))).all()) if cases else []
    by_object_id = {item.id: item for item in objects}
    objects_by_relation = defaultdict(list)
    for item in objects:
        objects_by_relation[(item.contract_record_id, item.case_record_id)].append(item)
    fees = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance",
        BusinessRecord.status.not_in({"已删除", "已撤回", *_INVALID_RECEIVABLE_FEE_STATUSES}),
        or_(scalar_in_values(BusinessRecord.data["contract_id"].as_integer(), by_contract_id),
            scalar_in_values(BusinessRecord.data["contract_record_id"].as_integer(), by_contract_id),
            scalar_in_values(BusinessRecord.data["contract_no"].as_string(), by_contract_no),
            scalar_in_values(BusinessRecord.data["contract_object_id"].as_integer(), by_object_id)),
    ).order_by(BusinessRecord.id))).all())
    fees = [fee for fee in fees if is_external_case_fee(fee)]
    cash = await receivable_payment_projection(fees, identity, db)
    rows = []
    matched_objects = set()

    def row(contract, case, fee_type, amount, received, paid, source_id):
        data, case_data = contract["data"], case.data or {}
        phase = case_data.get("case_stage") or case_data.get("business_stage") or case.status
        return {"id": source_id, "contract_record_id": contract["id"], "contract_no": contract["serial_no"],
                "contract_title": contract["title"],
                "owner": contract["owner"], "contract_body": data.get("contract_body") or "律所",
                "contract_date": data.get("signed_at") or "", "customer": contract["customer"],
                "source_person": data.get("source_person") or contract["owner"],
                "case_record_id": case.id, "case_no": case.serial_no,
                "case_type": case_data.get("case_type") or "", "fee_type": fee_type,
                "fee_category": _receivable_fee_category(fee_type),
                "phase": phase, "case_stage": phase, "due_date": "", "status": case.status,
                "payer": contract["customer"], "remark": "",
                "amount": amount, "paid_amount": paid, "received_amount": received,
                "remaining_amount": round(amount - received, 2) if amount is not None else None}

    for fee in fees:
        data = fee.data or {}
        case = by_case_id.get(_receivable_relation_id(data, "case_record_id", "case_id")) or by_case_no.get(str(data.get("case_no") or ""))
        item = by_object_id.get(int(data.get("contract_object_id") or 0))
        if item is not None:
            case = by_case_id[item.case_record_id]
            contract = by_contract_id[item.contract_record_id]
        else:
            contract = by_contract_id.get(_receivable_relation_id(data, "contract_record_id", "contract_id")) or by_contract_no.get(str(data.get("contract_no") or ""))
        if case is None or contract is None:
            continue
        if item is not None:
            matched_objects.add(item.id)
        for candidate in objects_by_relation[(contract["id"], case.id)]:
            if _fee_matches_contract_object(fee, candidate, case):
                matched_objects.add(candidate.id)
        amount = float(data["amount"]) if data.get("amount") is not None else None
        if amount == 0 and cash[fee.id]["cashed_amount"] == 0:
            continue
        projected = row(contract, case, _case_fee_display_type(fee), amount, cash[fee.id]["cashed_amount"],
                        cash[fee.id]["paid_amount"], f"fee:{fee.id}")
        projected.update({"source_type": "case_fee", "fee_record_id": fee.id,
                          "contract_object_id": int(data["contract_object_id"]) if data.get("contract_object_id") else None,
                          "due_date": str(data.get("deadline") or ""), "status": fee.status,
                          "remark": fee.description, "updated_at": fee.updated_at})
        rows.append(projected)
    for item in objects:
        if item.id in matched_objects or item.amount == 0:
            continue
        amount = float(item.amount) if item.amount is not None else None
        projected = row(by_contract_id[item.contract_record_id], by_case_id[item.case_record_id], item.fee_type,
                        amount, 0.0, 0.0, f"object:{item.id}")
        projected.update({"source_type": "contract_object", "fee_record_id": None,
                          "contract_object_id": item.id, "remark": item.remark, "updated_at": item.updated_at})
        rows.append(projected)
    totals = {}
    for item in rows:
        amounts = totals.setdefault(item["contract_record_id"], {
            "official_paid": 0.0, "official_received": 0.0, "official_unreceived": 0.0, "official_loss": 0.0,
            "agency_total": 0.0, "agency_received": 0.0, "agency_due": 0.0,
        })
        keys = {"official_paid": "paid_amount", "official_received": "received_amount", "official_unreceived": "remaining_amount"} if item["fee_category"] == "official" else {"agency_total": "amount", "agency_received": "received_amount", "agency_due": "remaining_amount"}
        if item["fee_category"] == "official" and "亏损" in item["phase"]:
            keys["official_loss"] = "remaining_amount"
        for target, source in keys.items():
            amounts[target] = None if amounts[target] is None or item[source] is None else round(amounts[target] + item[source], 2)
    for item in rows:
        item["contract_totals"] = totals[item["contract_record_id"]]
    return sorted(rows, key=lambda item: (item["contract_no"], item["case_no"], item["id"]))
