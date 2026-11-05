"""501614（fwl 11-05）：新建、编辑专利非诉案件草稿按旧系统“案件新建”弹窗的字段。

字段都写进旧系统迁来案件已有的键（含别名和姓名键），旧案件打开就能看到原值；
代理人、撰稿人、案源人、案件管理人的键名和分支3“我的案件”（501613）按角色分组用的一致。
"""
from __future__ import annotations

import re
from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

FLAG_KEYS = ("has_priority", "has_foreign", "has_relief", "has_advanced", "has_request_view", "has_private_inventor", "has_iu")
# 费用减缓比例：旧系统（沪知）存 1.00=无减缓、0.85=减缓85%、0.70=减缓70%；恒达迁来的 0.00 也按无减缓显示。
COST_SLOW_RATES = {"1.00": "无减缓", "0.85": "减缓85%", "0.70": "减缓70%"}
CARD_NO = re.compile(r"^[0-9A-Za-z]+$")


async def _display_names(db: AsyncSession, usernames: set[str]) -> dict[str, str]:
    from app.models import User
    names = {name for name in usernames if name}
    if not names:
        return {}
    rows = (await db.scalars(select(User).where(User.username.in_(names)))).all()
    return {row.username: row.display_name for row in rows}


async def apply_patent_form(data: dict, values: dict, db: AsyncSession) -> None:
    """values 只含本次提交的项；写入主键和旧系统别名键，人员同时写账号和姓名。"""
    people = {key: str(values[key] or "").strip() for key in ("agent", "writer", "case_source", "case_manager") if key in values}
    names = await _display_names(db, set(people.values()))
    if "agent" in people:
        account = people["agent"]
        data.update(agent=account, agent_username=account, procurator=account, procurator_name=names.get(account, account))
    if "writer" in people:
        account = people["writer"]
        data.update(writer=account, writer_username=account, copywriter=account, copywriter_name=names.get(account, account))
    if "case_source" in people:
        account = people["case_source"]
        data.update(case_source=account, case_source_username=account, case_origin_people=account,
                    case_origin_people_name=names.get(account, account))
    if "case_manager" in people:
        account = people["case_manager"]
        data.update(case_manager=account, case_manager_username=account, business_owner=account, case_officer=account,
                    case_officer_name=names.get(account, account))
    if "card_no" in values:
        card_no = str(values["card_no"] or "").strip()
        if card_no and not CARD_NO.fullmatch(card_no):
            raise HTTPException(status_code=422, detail="证件号码不允许有空格及特殊字符")
        data["card_no"] = card_no
    if "inventor" in values:
        data["inventor"] = data["case_inventor"] = str(values["inventor"] or "").strip()
    if "applicant" in values:
        applicant = str(values["applicant"] or "").strip()
        data["applicant"] = data["applicant_name"] = applicant
    for key, aliases in (("authorization_date", ()), ("source_date", ("case_origin_date",))):
        if key in values:
            value = values[key]
            text = value.isoformat() if isinstance(value, date) else str(value or "")
            data[key] = text
            for alias in aliases:
                data[alias] = text
    if "ref_case_no" in values:
        data["ref_case_no"] = str(values["ref_case_no"] or "").strip()
    if "first_annual_year" in values:
        year = values["first_annual_year"]
        data["first_annual_year"] = year
        if year:
            data["annual_fee_year"] = year
    if "cost_slow_rate" in values:
        rate = str(values["cost_slow_rate"] or "").strip()
        if rate and rate not in COST_SLOW_RATES:
            raise HTTPException(status_code=422, detail="费用减缓比例只能选无减缓、减缓85%或减缓70%")
        data["cost_slow_rate"] = rate or "1.00"
        data["rate"] = float(data["cost_slow_rate"])
    for key in FLAG_KEYS:
        if key in values and values[key] is not None:
            data[key] = "T" if values[key] else "F"
