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


async def clue_conflicts(clue: BusinessRecord, db: AsyncSession) -> dict[str, list[str]]:
    """沿用旧系统的同权利人、店铺及调查主体匹配边界。"""
    data = clue.data or {}
    holder = _name(data.get("rights_holder") or clue.customer)
    if not holder:
        return {"clues": [], "cases": []}
    shop_name = _name(data.get("shop_name") or clue.title)
    shop_id = _name(data.get("shop_id"))
    indictees = _party_names(data, "indictees", "indictee")
    producers = _party_names(data, "producers", "producer")
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
            same_shop = bool(shop_name and shop_name == _name(other.get("shop_name") or item.title))
            same_shop_id = bool(shop_id and shop_id == _name(other.get("shop_id")))
            same_indictee = bool(indictees & _party_names(other, "indictees", "indictee"))
            same_producer = bool(producers & _party_names(other, "producers", "producer"))
            if same_shop or same_shop_id or same_indictee or same_producer:
                clue_nos.append(item.serial_no)
        else:
            raw_defendants = other.get("defendants")
            defendants = {_name(value) for value in raw_defendants if isinstance(value, str)} if isinstance(raw_defendants, list) else set()
            if not defendants:
                legacy = other.get("legacy_record") if isinstance(other.get("legacy_record"), dict) else {}
                defendants = {_name(value) for value in re.split(
                    r"[,，;；、|]+", str(other.get("opponent") or other.get("defendant") or legacy.get("AppelleeNames") or ""),
                )}
            if (indictees | producers) & (defendants - {""}):
                case_nos.append(item.serial_no)
    return {"clues": sorted(set(clue_nos)), "cases": sorted(set(case_nos))}
