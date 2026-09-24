"""调查线索审批的疑似重复线索与案件检索。"""
import re
import unicodedata
from typing import TypedDict

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BusinessRecord


class ClueConflicts(TypedDict):
    clues: list[str]
    cases: list[str]
    case_search_available: bool


def _name(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).split()).casefold()


def _party_names(data: dict, plural: str, singular: str) -> set[str]:
    values = data.get(plural) if isinstance(data.get(plural), list) else []
    names = {
        _name(item.get("name") or item.get(singular)) if isinstance(item, dict) else _name(item)
        for item in values
    }
    if not names:
        names = {_name(value) for value in re.split(r"[,，;；、|]+", str(data.get(singular) or ""))}
    return names - {""}


def _legacy_data(data: dict) -> dict:
    legacy = data.get("legacy_record")
    return legacy if isinstance(legacy, dict) else {}


def _clue_parties(data: dict, plural: str, singular: str, legacy_key: str) -> set[str]:
    names = _party_names(data, plural, singular)
    if names:
        return names
    legacy_names = re.split(r"[,，;；、|]+", str(_legacy_data(data).get(legacy_key) or ""))
    return {_name(value) for value in legacy_names} - {""}


def _contains_any(source: set[str], targets: set[str]) -> bool:
    return any(name in target for name in source for target in targets)


def _holder_reference(record: BusinessRecord) -> tuple[str, str, str]:
    data = record.data or {}
    legacy = _legacy_data(data)
    holder_id = str(data.get("rights_holder_id") or data.get("customer_record_id") or data.get("customer_id") or "").strip()
    holder_no = str(data.get("rights_holder_no") or data.get("customer_no") or legacy.get("CustomerNo") or "").strip()
    holder_name = _name(data.get("rights_holder") or record.customer)
    return holder_id, holder_no, holder_name


def _case_defendants(data: dict) -> set[str]:
    if "defendants" in data:
        raw = data["defendants"]
        if isinstance(raw, list):
            return {_name(value.get("name") if isinstance(value, dict) else value) for value in raw} - {""}
        return {_name(value) for value in re.split(r"[,，;；、|]+", str(raw or ""))} - {""}
    if "opponent" in data or "defendant" in data:
        return {_name(value) for value in re.split(r"[,，;；、|]+", str(data.get("opponent") or data.get("defendant") or ""))} - {""}
    legacy = _legacy_data(data)
    return {_name(value) for value in re.split(r"[,，;；、|]+", str(legacy.get("AppelleeNames") or ""))} - {""}


async def clue_conflicts(clue: BusinessRecord, db: AsyncSession) -> ClueConflicts:
    """沿用旧系统的同权利人、店铺及调查主体匹配边界。"""
    data = clue.data or {}
    holder_id, holder_no, holder = _holder_reference(clue)
    if not (holder_id or holder_no or holder):
        return {"clues": [], "cases": [], "case_search_available": False}
    legacy = _legacy_data(data)
    shop_name = _name(data.get("shop_name") or data.get("store_name") or legacy.get("StoreName") or clue.title)
    shop_id = _name(data.get("shop_id") or data.get("store_id") or legacy.get("StoreId"))
    indictees = _clue_parties(data, "indictees", "indictee", "Indictee")
    producers = _clue_parties(data, "producers", "producer", "Producer")
    has_case_subject = bool(indictees or producers)
    holder_conditions = []
    if holder:
        holder_text = str(data.get("rights_holder") or clue.customer).strip()
        holder_conditions.extend((
            BusinessRecord.customer == holder_text,
            BusinessRecord.data["rights_holder"].as_string() == holder_text,
        ))
    if holder_id:
        holder_conditions.extend((
            BusinessRecord.data["customer_id"].as_string() == holder_id,
            BusinessRecord.data["customer_record_id"].as_string() == holder_id,
            BusinessRecord.data["rights_holder_id"].as_string() == holder_id,
        ))
        if holder_id.isdigit():
            holder_conditions.extend((
                BusinessRecord.data["customer_id"].as_integer() == int(holder_id),
                BusinessRecord.data["customer_record_id"].as_integer() == int(holder_id),
                BusinessRecord.data["rights_holder_id"].as_integer() == int(holder_id),
            ))
    if holder_no:
        holder_conditions.extend((
            BusinessRecord.data["customer_no"].as_string() == holder_no,
            BusinessRecord.data["rights_holder_no"].as_string() == holder_no,
            BusinessRecord.data["legacy_record"]["CustomerNo"].as_string() == holder_no,
        ))
    records = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module.in_(["clue", "case"] if has_case_subject else ["clue"]),
        BusinessRecord.status.not_in(["已删除", "已回收", "已合并"]),
        or_(*holder_conditions),
    ))).all()
    clue_nos: list[str] = []
    case_nos: list[str] = []
    for item in records:
        if item.id == clue.id:
            continue
        other_holder_id, other_holder_no, other_holder = _holder_reference(item)
        if holder_id and other_holder_id and holder_id != other_holder_id:
            continue
        if holder_no and other_holder_no and holder_no != other_holder_no:
            continue
        if not ((holder_id and other_holder_id) or (holder_no and other_holder_no)) and other_holder != holder:
            continue
        other = item.data or {}
        if item.module == "clue":
            other_legacy = _legacy_data(other)
            other_shop_name = _name(other.get("shop_name") or other.get("store_name") or other_legacy.get("StoreName") or item.title)
            other_shop_id = _name(other.get("shop_id") or other.get("store_id") or other_legacy.get("StoreId"))
            same_shop = bool(shop_name and shop_name in other_shop_name)
            same_shop_id = bool(shop_id and shop_id in other_shop_id)
            same_indictee = _contains_any(indictees, _clue_parties(other, "indictees", "indictee", "Indictee"))
            same_producer = _contains_any(producers, _clue_parties(other, "producers", "producer", "Producer"))
            if same_shop or same_shop_id or same_indictee or same_producer:
                clue_nos.append(item.serial_no)
        else:
            if _contains_any(indictees | producers, _case_defendants(other)):
                case_nos.append(item.serial_no)
    return {"clues": sorted(set(clue_nos)), "cases": sorted(set(case_nos)), "case_search_available": has_case_subject}
