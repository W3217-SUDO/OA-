"""分配读模型的费用键和原始事件时间归一化，不修改持久化记录。"""

from datetime import datetime
import re

from fastapi import HTTPException


def _relation_id(value, label: str) -> int | None:
    if value in (None, "", 0, "0") and not isinstance(value, bool):
        return None
    text = str(value).strip()
    if isinstance(value, bool) or not re.fullmatch(r"[0-9]+", text) or int(text) <= 0:
        raise HTTPException(409, f"分配明细的{label}不是有效关联编号")
    return int(text)


def allocation_fee_id(allocation: dict) -> int | None:
    """四种费用关联键必须指向同一记录，不能按键优先级掩盖冲突。"""
    fee_ids = {
        value for key in ("fee_record_id", "fee_id", "case_fee_id", "finance_record_id")
        if (value := _relation_id(allocation.get(key), key)) is not None
    }
    if len(fee_ids) > 1:
        raise HTTPException(409, "分配明细的费用关联编号不一致")
    return next(iter(fee_ids)) if fee_ids else None


def normalize_incoming_allocation(allocation: dict, *, receipt_no: str) -> dict:
    """只接受一致的新费用键；旧时间必须具有同笔回款和分配行来源。"""
    result = dict(allocation)
    fee_id = allocation_fee_id(allocation)
    if fee_id is not None:
        result["fee_record_id"] = fee_id
    source = allocation.get("source_object")
    if isinstance(source, dict) and source:
        payment_id = _relation_id(source.get("PaymentId"), "旧回款")
        source_id = _relation_id(source.get("SeqId"), "旧分配行")
        legacy_receipt = re.fullmatch(r"HZ-RCPT-(\d+)", str(receipt_no))
        if legacy_receipt and payment_id and payment_id != int(legacy_receipt.group(1)):
            raise HTTPException(409, "分配明细的旧回款来源与当前回款不一致")
        if legacy_receipt and payment_id and source_id:
            result["allocation_source_id"] = source_id
            if not result.get("allocated_at") and source.get("CreateTime"):
                value = str(source["CreateTime"]).strip()
                try:
                    parsed = datetime.fromisoformat(value)
                except ValueError as exc:
                    raise HTTPException(409, "旧分配行时间格式无效") from exc
                if "T" not in value and " " not in value:
                    raise HTTPException(409, "旧分配行时间缺少时分秒")
                result["allocated_at"] = parsed.isoformat()
    if isinstance(allocation.get("settlement_items"), list):
        result["settlement_items"] = [
            normalize_incoming_allocation(item, receipt_no=receipt_no)
            for item in allocation["settlement_items"]
        ]
    return result


def normalize_settlement_allocation_times(data: dict, allocations: list[dict], *, receipt_no: str) -> dict:
    """旧申请快照只按分配来源或唯一费用关系补时间，歧义不按位置猜测。"""
    normalized = [normalize_incoming_allocation(item, receipt_no=receipt_no) for item in allocations]
    sources = []
    for item in normalized:
        children = item.get("settlement_items") or []
        sources.extend([
            {**child, "allocated_at": child.get("allocated_at") or item.get("allocated_at", ""),
             "allocation_source_id": child.get("allocation_source_id") or item.get("allocation_source_id")}
            for child in children
        ] if children else [item])
    details = []
    for original in data.get("allocation_details") or []:
        detail = dict(original)
        source_id = _relation_id(detail.get("allocation_source_id"), "分配来源")
        fee_id = _relation_id(detail.get("fee_id"), "费用")
        matches = [item for item in sources if (
            item.get("allocation_source_id") == source_id
            and (fee_id is None or item.get("fee_record_id") == fee_id) if source_id
            else fee_id is not None and item.get("fee_record_id") == fee_id
        )]
        if len(matches) == 1:
            match = matches[0]
            if not detail.get("allocated_at") and match.get("allocated_at"):
                detail["allocated_at"] = match["allocated_at"]
            if match.get("allocation_source_id"):
                detail["allocation_source_id"] = match["allocation_source_id"]
        details.append(detail)
    return {**data, "allocation_details": details}
