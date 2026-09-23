"""调查线索审批的疑似重复线索与案件检索。"""
import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BusinessRecord


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


async def clue_conflicts(clue: BusinessRecord, db: AsyncSession) -> dict[str, list[str]]:
    """沿用旧系统的同权利人、店铺及调查主体匹配边界。"""
    data = clue.data or {}
    holder = _name(data.get("rights_holder") or clue.customer)
    if not holder:
        return {"clues": [], "cases": []}
    legacy = _legacy_data(data)
    shop_name = _name(data.get("shop_name") or data.get("store_name") or legacy.get("StoreName") or clue.title)
    shop_id = _name(data.get("shop_id") or data.get("store_id") or legacy.get("StoreId"))
    indictees = _clue_parties(data, "indictees", "indictee", "Indictee")
    producers = _clue_parties(data, "producers", "producer", "Producer")
    records = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module.in_(["clue", "case"]),
        BusinessRecord.status.not_in(["已删除", "已回收", "已合并"]),
    ))).all()
    clue_nos: list[str] = []
    case_nos: list[str] = []
    for item in records:
        if item.id == clue.id or _name((item.data or {}).get("rights_holder") or item.customer) != holder:
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
            legacy_appellees = _name(_legacy_data(other).get("AppelleeNames"))
            raw_defendants = other.get("defendants")
            if legacy_appellees:
                defendants = {legacy_appellees}
            elif isinstance(raw_defendants, list):
                defendants = {
                    _name(value.get("name") if isinstance(value, dict) else value)
                    for value in raw_defendants
                }
            else:
                defendants = set()
            if not defendants - {""}:
                defendants = {_name(value) for value in re.split(
                    r"[,，;；、|]+", str(other.get("opponent") or other.get("defendant") or ""),
                )}
            if _contains_any(indictees | producers, defendants - {""}):
                case_nos.append(item.serial_no)
    return {"clues": sorted(set(clue_nos)), "cases": sorted(set(case_nos))}
