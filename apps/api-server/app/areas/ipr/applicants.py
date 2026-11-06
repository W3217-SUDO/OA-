"""501187：非诉案件的申请人。输入时搜已有客户、当事人和申请人库；手填的新名称登记到非诉申请人库。"""
from __future__ import annotations

import re

from fastapi import APIRouter, Query
from sqlalchemy import delete, func, or_, select

from app.config import settings
from app.core.dependencies import AsyncSession, Depends, HTTPException, get_db
from app.core.formatters import _normalize_customer_name
from app.data_models.ipr_applicant import IprApplicant, IprApplicantCase
from app.data_models.parties import PartyRecord
from app.models import BusinessRecord
from app.security import current_identity

router = APIRouter()
LIBRARY_MENU = "party-ipr-applicants"
_SPLIT = re.compile(r"[,，、;；]")


def split_applicants(value: object) -> list[str]:
    names: dict[str, str] = {}
    for part in _SPLIT.split(str(value or "")):
        name = part.strip()
        key = _normalize_customer_name(name) if name else ""
        if key:
            names.setdefault(key, name)
    return list(names.values())


async def _known_elsewhere(db: AsyncSession, name: str, key: str) -> bool:
    """客户或当事人里已有同名：直接用已有的那条，不再登记。"""
    rows = await db.scalars(select(BusinessRecord.title).where(
        BusinessRecord.module == "customer", BusinessRecord.deleted_at.is_(None),
        BusinessRecord.status != "已回收", BusinessRecord.title.icontains(name[:60], autoescape=True)).limit(50))
    if any(_normalize_customer_name(title) == key for title in rows):
        return True
    parties = await db.scalars(select(PartyRecord.name).where(
        PartyRecord.status != "已回收", PartyRecord.name.icontains(name[:60], autoescape=True)).limit(50))
    return any(_normalize_customer_name(title) == key for title in parties)


async def sync_case_applicants(record: BusinessRecord, username: str, db: AsyncSession) -> None:
    """按案件当前的申请人刷新登记和关联。诉讼案件不进这个库。调用方负责提交事务。"""
    data = record.data or {}
    if record.module != "ipr_case" or data.get("case_category", "non_litigation") == "litigation":
        return
    linked: set[int] = set()
    for name in split_applicants(data.get("applicant_name") or data.get("applicant")):
        key = _normalize_customer_name(name)[:512]
        applicant = await db.scalar(select(IprApplicant).where(IprApplicant.normalized_name == key))
        if not applicant:
            if await _known_elsewhere(db, name, key):
                continue
            applicant = IprApplicant(applicant_no=f"TMP{record.id}-{len(linked)}", name=name, normalized_name=key, created_by=username)
            db.add(applicant)
            await db.flush()
            applicant.applicant_no = f"SQR{applicant.id:07d}"
        linked.add(applicant.id)
        exists = await db.scalar(select(IprApplicantCase.id).where(
            IprApplicantCase.applicant_id == applicant.id, IprApplicantCase.case_id == record.id))
        if not exists:
            db.add(IprApplicantCase(applicant_id=applicant.id, case_id=record.id, case_no=record.serial_no or ""))
    stale = delete(IprApplicantCase).where(IprApplicantCase.case_id == record.id)
    if linked:
        stale = stale.where(IprApplicantCase.applicant_id.not_in(linked))
    await db.execute(stale)


@router.get(f"{settings.api_prefix}/ipr/applicant-options")
async def ipr_applicant_options(
    keyword: str = Query("", max_length=100), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """边输边搜：已有客户、当事人、非诉申请人库。名称相同只出现一次。"""
    from app.core.permissions import _require_record_module_menu
    await _require_record_module_menu("ipr_case", identity, db, action="查看")
    term = keyword.strip()
    if not term:
        return {"items": []}
    customers = await db.scalars(select(BusinessRecord.title).where(
        BusinessRecord.module == "customer", BusinessRecord.deleted_at.is_(None), BusinessRecord.status != "已回收",
        func.coalesce(BusinessRecord.data["customer_type"].as_string(), "客户") == "客户",
        BusinessRecord.title.icontains(term, autoescape=True)).order_by(BusinessRecord.title).limit(20))
    parties = await db.scalars(select(PartyRecord.name).where(
        PartyRecord.status != "已回收", PartyRecord.name.icontains(term, autoescape=True)).order_by(PartyRecord.name).limit(20))
    applicants = await db.scalars(select(IprApplicant.name).where(
        IprApplicant.name.icontains(term, autoescape=True)).order_by(IprApplicant.name).limit(20))
    seen: set[str] = set()
    items = []
    for source, names in (("客户", customers), ("当事人", parties), ("申请人库", applicants)):
        for name in names:
            key = _normalize_customer_name(name)
            if key and key not in seen:
                seen.add(key)
                items.append({"value": name, "source": source})
    return {"items": items}


@router.get(f"{settings.api_prefix}/party-library/ipr-applicants")
async def list_ipr_applicants(
    keyword: str = Query("", max_length=200), case_no: str = Query("", max_length=64),
    page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    if "admin" not in (identity.get("_actual_role_ids") or []) and LIBRARY_MENU not in set(identity.get("menu_keys") or []):
        raise HTTPException(status_code=403, detail="当前账号未开通非诉申请人库权限")
    conditions = []
    if keyword.strip():
        conditions.append(or_(IprApplicant.name.icontains(keyword.strip(), autoescape=True),
                              IprApplicant.applicant_no.icontains(keyword.strip(), autoescape=True)))
    if case_no.strip():
        conditions.append(IprApplicant.id.in_(select(IprApplicantCase.applicant_id).where(
            IprApplicantCase.case_no.icontains(case_no.strip(), autoescape=True))))
    total = await db.scalar(select(func.count()).select_from(IprApplicant).where(*conditions))
    rows = (await db.scalars(select(IprApplicant).where(*conditions).order_by(IprApplicant.id.desc())
                             .offset((page - 1) * page_size).limit(page_size))).all()
    links: dict[int, list[dict]] = {}
    if rows:
        for link in (await db.scalars(select(IprApplicantCase).where(
                IprApplicantCase.applicant_id.in_([row.id for row in rows])).order_by(IprApplicantCase.id))).all():
            links.setdefault(link.applicant_id, []).append({"case_id": link.case_id, "case_no": link.case_no})
    return {"total": total or 0, "items": [{
        "id": row.id, "applicant_no": row.applicant_no, "name": row.name, "created_by": row.created_by,
        "created_at": row.created_at, "cases": links.get(row.id, []),
    } for row in rows]}
