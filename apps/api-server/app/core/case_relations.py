"""案件与来源线索的关联、选择资格和详情投影。"""
from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BusinessRecord


def case_clue_ids(case: BusinessRecord) -> set[int]:
    data = case.data or {}
    values = data.get("investigation_clue_ids") or []
    if not isinstance(values, list):
        values = [values]
    return {int(value) for value in [*values, data.get("investigation_clue_id"), data.get("clue_record_id"), data.get("clue_id")]
            if str(value or "").isdigit() and int(value) > 0}


async def case_clues(case: BusinessRecord, db: AsyncSession) -> list[BusinessRecord]:
    ids = case_clue_ids(case)
    data = case.data or {}
    numbers = data.get("investigation_clue_nos") or []
    if isinstance(numbers, str):
        numbers = [numbers]
    numbers = [*numbers, data.get("clue_no"), data.get("source_clue_no")]
    condition = BusinessRecord.id.in_(ids) if ids else BusinessRecord.serial_no.in_([n for n in numbers if n])
    if not ids and not any(numbers):
        condition = or_(BusinessRecord.data["case_id"].as_integer() == case.id,
                        BusinessRecord.data["converted_case_id"].as_integer() == case.id,
                        BusinessRecord.data["converted_case_no"].as_string() == case.serial_no)
    return list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "clue", condition,
    ).order_by(BusinessRecord.id))).all())


async def validate_case_clues(case: BusinessRecord, clues: list[BusinessRecord], customer: str, db: AsyncSession) -> None:
    """锁定线索后校验，保留本案原有关联，阻止新增占用其他案件的线索。"""
    existing = case_clue_ids(case)
    for clue in clues:
        if clue.id in existing:
            continue
        await db.refresh(clue, with_for_update=True)
        data = clue.data or {}
        if clue.status != "已取证" or clue.customer.strip() != customer.strip():
            raise HTTPException(409, "只能绑定同一客户已取证且尚未生成案件的线索")
        if any(data.get(key) for key in ("case_id", "case_record_id", "case_no", "converted_case_id", "converted_case_no")):
            raise HTTPException(409, "所选线索已经关联案件，请重新选择")
        other_cases = (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "case", BusinessRecord.id != case.id,
            BusinessRecord.status != "已合并",
        ))).all()
        if any(clue.id in case_clue_ids(other) for other in other_cases):
            raise HTTPException(409, "所选线索已经关联案件，请重新选择")


def clue_header_values(clues: list[BusinessRecord]) -> dict:
    certificates: list[str] = []
    locations: list[str] = []
    for clue in clues:
        data = clue.data or {}
        certificate = str(data.get("certificate_no") or data.get("notarization_no") or data.get("notary_no") or "").strip()
        location = str(data.get("storage_location") or data.get("warehouse_location") or data.get("warehouse") or "").strip()
        if certificate and certificate not in certificates:
            certificates.append(certificate)
        if location and location not in locations:
            locations.append(location)
    return {"notary_no": "、".join(certificates), "warehouse_location": "、".join(locations)}


async def case_source_projection(case: BusinessRecord, identity: dict, db: AsyncSession) -> dict:
    """读取来源投影，不覆盖案件人工维护的数据，也不在读取时写数据库。"""
    from app.core.contracts import _resolve_clue_source_contract
    clues = await case_clues(case, db)
    data = dict(case.data or {})
    derived = clue_header_values(clues)
    if not any(data.get(key) for key in ("notarial_no", "notary_no", "certificate_no", "notary_nos")):
        data["notary_no"] = derived["notary_no"]
    if not any(data.get(key) for key in ("warehouse", "warehouse_location", "storage_location", "location", "deposit_address", "warehouse_locations")):
        data["warehouse_location"] = derived["warehouse_location"]
    if not data.get("contract_no"):
        contracts = {}
        for clue in clues:
            contract, _ = await _resolve_clue_source_contract(clue, identity, db)
            if contract:
                contracts[contract.id] = contract
        if len(contracts) == 1:
            contract = next(iter(contracts.values()))
            data.update(contract_id=contract.id, contract_record_id=contract.id, contract_no=contract.serial_no)
    header_keys = {"contract_id", "contract_record_id", "contract_no", "notarial_no", "notary_no", "certificate_no", "notary_nos",
                   "warehouse", "warehouse_location", "storage_location", "location", "deposit_address", "warehouse_locations"}
    return {key: value for key, value in data.items() if key in header_keys}
