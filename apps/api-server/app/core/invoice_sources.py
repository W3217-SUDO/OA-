"""发票申请使用费用自身的合同与板块，历史来源关系单独解析。"""
from fastapi import HTTPException
from sqlalchemy import String, cast, or_, select

from app.models import BusinessRecord
from app.core.finance_batch_parity import is_internal_fee


def is_external_case_fee(fee: BusinessRecord) -> bool:
    data = fee.data or {}
    return (fee.module == "finance" and not is_internal_fee(data)
            and str(data.get("expense_scope") or "律所").strip() in {"律所", "平台"}
            and str(data.get("legacy_kind") or "") != "ap_payment")


async def invoice_source_fees(invoice: BusinessRecord, identity: dict, db, *, positive_only=False) -> list[BusinessRecord]:
    from app.core.finance import _invoice_linked_fee_ids
    from app.core.permissions import _ensure_record_visible

    data = invoice.data or {}
    ids = _invoice_linked_fee_ids(data)
    if positive_only and ids and data.get("case_fee_allocations"):
        ids &= {int(item["fee_id"]) for item in data["case_fee_allocations"] if float(item.get("amount") or 0) > 0}
    if not ids:
        objects = data.get("legacy_objects") or []
        source = str(data.get("legacy_source") or "").strip()
        for item in objects:
            if not isinstance(item, dict) or item.get("IsActived") == "F":
                continue
            if float(item.get("InvoicedAmount") or 0) <= 0:
                continue
            legacy_id = str(item.get("CaseFeeId") or "").strip()
            case_no = str(item.get("CaseNo") or "").strip()
            if not legacy_id:
                raise HTTPException(409, "历史发票的费用来源资料不完整")
            candidates = list((await db.scalars(select(BusinessRecord).where(
                BusinessRecord.module == "finance",
                or_(cast(BusinessRecord.data["legacy_case_fee_id"].as_string(), String) == legacy_id,
                    cast(BusinessRecord.data["legacy_fee_id"].as_string(), String) == legacy_id),
            ))).all())
            if source:
                candidates = [fee for fee in candidates if str((fee.data or {}).get("legacy_source") or "") == source]
            # 费用 ID 在来源库内稳定；合并案件只改变案号，不能推翻已有来源关系。
            if len(candidates) > 1 and case_no:
                candidates = [fee for fee in candidates if case_no in {
                    str((fee.data or {}).get("case_no") or ""),
                    str((fee.data or {}).get("merged_from_case_no") or ""),
                }]
            if len(candidates) != 1:
                raise HTTPException(409, f"历史发票费用 {legacy_id} 未找到唯一关联，请先补全来源关系")
            ids.add(candidates[0].id)
    if not ids:
        raise HTTPException(409, "发票申请未关联案件费用，不能继续办理")
    fees = []
    for fee_id in sorted(ids):
        fee = await _ensure_record_visible(fee_id, identity, db)
        if fee.module != "finance":
            raise HTTPException(409, "发票关联记录不是案件费用")
        fees.append(fee)
    return fees


async def validate_invoice_fee_policy(fees: list[BusinessRecord], db) -> None:
    from app.core.formatters import _normalize_external_contract_numbers

    missing = []
    for fee in fees:
        if not is_external_case_fee(fee):
            raise HTTPException(409, "开票申请只能选择律所费用或平台费用，不能选择内部费用")
        data = fee.data or {}
        contract_id = data.get("contract_id") or data.get("contract_record_id")
        contract_no = str(data.get("contract_no") or "").strip()
        if contract_id:
            contract = await db.get(BusinessRecord, int(contract_id))
            if not contract or contract.module != "contract" or (contract_no and contract.serial_no != contract_no):
                raise HTTPException(409, f"费用 {fee.serial_no} 的合同关联无效")
        elif contract_no:
            contract = await db.scalar(select(BusinessRecord).where(
                BusinessRecord.module == "contract", BusinessRecord.serial_no == contract_no,
            ))
            if not contract:
                raise HTTPException(409, f"费用 {fee.serial_no} 的关联合同不存在")
        else:
            raise HTTPException(409, f"费用 {fee.serial_no} 未关联合同")
        raw = dict(contract.data or {})
        if "external_contract_numbers" not in raw and "external_contract_no" not in raw:
            raw["external_contract_no"] = raw.get("ref_contract_no") or ""
        numbers = _normalize_external_contract_numbers(raw)["external_contract_numbers"]
        if contract.serial_no.upper().startswith("SH") and not numbers:
            missing.append(contract.serial_no)
    if missing:
        raise HTTPException(409, "申请开票前请补充外部合同号：" + "、".join(dict.fromkeys(missing)))
