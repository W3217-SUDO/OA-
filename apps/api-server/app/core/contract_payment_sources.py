"""合同请款承接已合并来源费用，费用原合同仍用于追溯。"""
from sqlalchemy import or_, select

from app.models import BusinessRecord


def _record_id(value):
    try:
        return int(value) if value else 0
    except (ValueError, TypeError):
        return 0


async def merged_contract_fees(contract, db):
    """普通未合并的一案多合同不扩围；合并链四个方向必须一致。"""
    from app.core.finance import _fee_matches_contract, _is_contract_payment_case_fee
    parents = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case", BusinessRecord.status != "已合并",
        or_(BusinessRecord.data["contract_id"].as_integer() == contract.id,
            BusinessRecord.data["contract_record_id"].as_integer() == contract.id,
            BusinessRecord.data["contract_no"].as_string() == contract.serial_no),
    ))).all())
    parents = {item.id: item for item in parents if _fee_matches_contract(item, contract) and (item.data or {}).get("merged_sources")}
    if not parents:
        return []
    source_ids = {_record_id(entry.get("id")) for item in parents.values()
                  for entry in item.data["merged_sources"] if isinstance(entry, dict)} - {0}
    sources = {item.id: item for item in (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case", BusinessRecord.id.in_(source_ids),
    ))).all()}
    fees = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance",
        or_(BusinessRecord.data["case_id"].as_integer().in_(parents),
            BusinessRecord.data["case_record_id"].as_integer().in_(parents)),
    ))).all()
    result = []
    for fee in fees:
        data = fee.data or {}
        parent = parents.get(_record_id(data.get("case_id") or data.get("case_record_id")))
        source = sources.get(_record_id(data.get("merged_from_case_id")))
        if not parent or not source or not _is_contract_payment_case_fee(fee):
            continue
        parent_data, source_data = parent.data or {}, source.data or {}
        if (source.status != "已合并" or source.customer != parent.customer or fee.customer != parent.customer
                or _record_id(source_data.get("merged_into_case_id")) != parent.id
                or source_data.get("merged_into_case_no") != parent.serial_no
                or data.get("merged_from_case_no") != source.serial_no
                or data.get("case_no") != parent.serial_no
                or any(data.get(key) and _record_id(data[key]) != parent.id for key in ("case_id", "case_record_id"))):
            continue
        if any(isinstance(entry, dict) and _record_id(entry.get("id")) == source.id
               and entry.get("serial_no") == source.serial_no for entry in parent_data["merged_sources"]):
            result.append(fee)
    return result
