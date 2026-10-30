"""BUG20261030004：知识产权中心“专利年费”菜单，照老系统 年费清单 / 年费监控。

在监控中的专利：案件上点过“加入/放弃年费监控”的以此为准；迁移的老案件没点过的，按老系统案件阶段“年费监控”算。
应缴日按申请日周年日算，第 N 年年费在第 N 年开始（申请日 + N-1 年）前缴纳，逾期 6 个月内可补缴。
缴费记录写在 ipr_case_annual_fees（fee_year 为应缴日所在公历年），已缴的不再进年费监控。
"""
from calendar import monthrange

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.dependencies import (
    AsyncSession, BusinessRecord, Decimal, Depends, HTTPException, IprCaseAnnualFee, Query, WorkflowEvent,
    and_, current_identity, date, get_db, or_, select, settings,
)

router = APIRouter()

# 国家知识产权局专利年费标准（元/年，不含费减）：(截至第几年, 金额)
_FEE_TABLE = {
    "发明": [(3, 900), (6, 1200), (9, 2000), (12, 4000), (15, 6000), (20, 8000)],
    "实用新型": [(3, 600), (5, 900), (8, 1200), (10, 2000)],
    "外观设计": [(3, 600), (5, 900), (8, 1200), (10, 2000), (15, 3000)],
}
_QUARTER_NAMES = {1: "一", 2: "二", 3: "三", 4: "四"}
_PAID = "已缴"


class IprAnnualFeePaidInput(BaseModel):
    case_id: int = Field(ge=1)
    fee_year: int = Field(ge=2000, le=2100)
    paid_date: date | None = None
    notes: str = Field(default="", max_length=500)


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year, month = value.year + month_index // 12, month_index % 12 + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def _parse_date(raw) -> date | None:
    try:
        return date.fromisoformat(str(raw or "")[:10])
    except ValueError:
        return None


def _patent_kind(case_type: str) -> str:
    for kind in ("发明", "实用新型", "外观设计"):
        if kind in (case_type or ""):
            return kind
    return ""


def _term_years(kind: str, application_date: date) -> int:
    if kind == "发明":
        return 20
    if kind == "外观设计" and application_date >= date(2021, 6, 1):
        return 15
    return 10


def _standard_fee(kind: str, year_no: int) -> int:
    for last_year, amount in _FEE_TABLE.get(kind, []):
        if year_no <= last_year:
            return amount
    return 0


def _first_paid_year_no(data: dict, application_date: date) -> int:
    """授权时随登记费缴纳的那一年；之后的年度才进年费监控。"""
    try:
        first = int(str(data.get("first_annual_year") or "").strip())
        if first >= 1:
            return first
    except ValueError:
        pass
    granted = _parse_date(data.get("authorization_date"))
    if granted and granted >= application_date:
        year_no = granted.year - application_date.year + 1
        if (granted.month, granted.day) < (application_date.month, application_date.day):
            year_no -= 1
        return max(year_no, 1)
    return 1


def _monitoring_condition():
    flag = BusinessRecord.data["annual_fee_monitoring"].as_string()
    return or_(
        flag == "true",
        and_(flag.is_(None), BusinessRecord.data["case_phase"].as_string() == "年费监控"),
    )


def _views(today: date) -> list[dict]:
    quarter = (today.month - 1) // 3 + 1
    items = [{"key": f"year-{today.year}", "group": "年费清单", "label": f"{today.year}年费",
              "start": date(today.year, 1, 1), "end": date(today.year, 12, 31), "unpaid_only": False}]
    for offset in (-1, 0, 1, 2):
        index = today.year * 4 + quarter - 1 + offset
        year, q = index // 4, index % 4 + 1
        start = date(year, (q - 1) * 3 + 1, 1)
        items.append({"key": f"quarter-{year}-{q}", "group": "年费清单", "label": f"{year % 100:02d}{_QUARTER_NAMES[q]}季度",
                      "start": start, "end": _add_months(start, 3) - date.resolution,"unpaid_only": False})
    items.append({"key": "within-6", "group": "年费监控", "label": "6月内年费",
                  "start": today, "end": _add_months(today, 6) - date.resolution, "unpaid_only": True})
    for months in range(1, 7):
        items.append({"key": f"overdue-{months}", "group": "年费监控", "label": f"逾期{months}月",
                      "start": _add_months(today, -months), "end": _add_months(today, -(months - 1)) - date.resolution, "unpaid_only": True})
    return items


async def _monitored_fee_rows(identity: dict, db: AsyncSession, start: date, end: date) -> list[dict]:
    from app.core.ipr import _ipr_case_list_conditions
    conditions = await _ipr_case_list_conditions(identity, db, case_kind="专利")
    records = list((await db.scalars(select(BusinessRecord).where(*conditions, _monitoring_condition()))).all())
    paid = {}
    if records:
        for row in (await db.scalars(select(IprCaseAnnualFee).where(
            IprCaseAnnualFee.case_record_id.in_([item.id for item in records]),
            IprCaseAnnualFee.fee_year.between(start.year, end.year),
        ))).all():
            paid[(row.case_record_id, row.fee_year)] = row
    rows = []
    for record in records:
        data = dict(record.data or {})
        application_date = _parse_date(data.get("application_date"))
        kind = _patent_kind(str(data.get("case_type") or ""))
        if not application_date or not kind:
            continue
        term, first_paid = _term_years(kind, application_date), _first_paid_year_no(data, application_date)
        for year in range(start.year, end.year + 1):
            year_no = year - application_date.year + 1
            if year_no <= first_paid or year_no > term:
                continue
            due = _add_months(application_date, 12 * (year_no - 1))
            if not start <= due <= end:
                continue
            fee = paid.get((record.id, year))
            rows.append({
                "case_id": record.id, "serial_no": record.serial_no,
                "case_name": data.get("case_name") or record.title or "", "case_type": data.get("case_type") or "",
                "customer": record.customer or "", "applicant": data.get("applicant_name") or data.get("applicant") or "",
                "application_no": data.get("application_no") or "", "application_date": application_date,
                "procurator": data.get("procurator_name") or data.get("procurator") or "",
                "fee_year": year, "year_no": year_no, "fee_name": f"第{year_no}年年费",
                "standard_amount": _standard_fee(kind, year_no), "due_date": due,
                "late_deadline": _add_months(due, 6),
                "status": fee.status if fee else "待缴", "paid_date": fee.paid_date if fee else None,
                "annual_fee_id": fee.id if fee else None,
            })
    rows.sort(key=lambda item: (item["due_date"], item["serial_no"]))
    return rows


@router.get(f"{settings.api_prefix}/ipr/annual-fee-monitor/summary")
async def ipr_annual_fee_monitor_summary(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """中间一栏：年费清单、年费监控各项及数量。"""
    from app.core.permissions import _require_record_module_menu
    await _require_record_module_menu("ipr_case", identity, db, action="查看")
    views = _views(date.today())
    rows = await _monitored_fee_rows(identity, db, min(item["start"] for item in views), max(item["end"] for item in views))
    items = []
    for view in views:
        count = sum(1 for row in rows if view["start"] <= row["due_date"] <= view["end"] and not (view["unpaid_only"] and row["status"] == _PAID))
        items.append({"key": view["key"], "group": view["group"], "label": view["label"], "count": count})
    return {"items": items}


@router.get(f"{settings.api_prefix}/ipr/annual-fee-monitor/items")
async def list_ipr_annual_fee_monitor_items(
    view: str = Query(min_length=1, max_length=32), keyword: str = Query(default="", max_length=100),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import _require_record_module_menu
    await _require_record_module_menu("ipr_case", identity, db, action="查看")
    selected = next((item for item in _views(date.today()) if item["key"] == view), None)
    if not selected:
        raise HTTPException(status_code=422, detail="年费清单/监控项目无效，请刷新页面")
    rows = await _monitored_fee_rows(identity, db, selected["start"], selected["end"])
    if selected["unpaid_only"]:
        rows = [row for row in rows if row["status"] != _PAID]
    word = keyword.strip()
    if word:
        rows = [row for row in rows if any(word in str(row[key]) for key in ("serial_no", "case_name", "customer", "applicant", "application_no"))]
    return {"items": rows, "total": len(rows), "label": selected["label"], "group": selected["group"]}


async def _annual_fee_case(case_id: int, fee_year: int, identity: dict, db: AsyncSession) -> tuple[BusinessRecord, dict]:
    from app.core.permissions import _ensure_record_module, _require_role_action
    await _require_role_action(identity, db, "ipr.case.reminder.manage")
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    rows = [row for row in await _monitored_fee_rows(identity, db, date(fee_year, 1, 1), date(fee_year, 12, 31)) if row["case_id"] == record.id]
    if not rows:
        raise HTTPException(status_code=404, detail="该案件这一年没有需要缴纳的年费，或已不在年费监控中")
    return record, rows[0]


@router.post(f"{settings.api_prefix}/ipr/annual-fee-monitor/paid")
async def mark_ipr_annual_fee_paid(body: IprAnnualFeePaidInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """登记已缴：写入案件年费记录，之后不再进年费监控。"""
    from app.core.finance import _sync_ipr_annual_fee_reminder
    record, item = await _annual_fee_case(body.case_id, body.fee_year, identity, db)
    paid_date = body.paid_date or date.today()
    row = await db.scalar(select(IprCaseAnnualFee).where(IprCaseAnnualFee.case_record_id == record.id, IprCaseAnnualFee.fee_year == body.fee_year))
    if row is None:
        row = IprCaseAnnualFee(
            case_record_id=record.id, fee_year=body.fee_year, fee_name=item["fee_name"],
            amount=Decimal(item["standard_amount"]), currency="CNY", due_date=item["due_date"], created_by=identity["username"],
        )
        db.add(row)
    row.status, row.paid_date, row.reminder_date = _PAID, paid_date, None
    if body.notes.strip():
        row.notes = body.notes.strip()
    await db.flush()
    await _sync_ipr_annual_fee_reminder(row, record, identity, db)
    db.add(WorkflowEvent(record_id=record.id, action="登记知识产权案件年费已缴", from_status=record.status, to_status=record.status,
                         operator=identity["username"], comment=f"{item['fee_name']}（应缴日 {item['due_date']}）；缴费日期：{paid_date}"))
    await db.commit()
    return {"case_id": record.id, "fee_year": body.fee_year, "status": row.status, "paid_date": row.paid_date}


@router.post(f"{settings.api_prefix}/ipr/annual-fee-monitor/unpaid")
async def undo_ipr_annual_fee_paid(body: IprAnnualFeePaidInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """撤销已缴：登记错了改回待缴，重新进年费监控。"""
    record, item = await _annual_fee_case(body.case_id, body.fee_year, identity, db)
    row = await db.scalar(select(IprCaseAnnualFee).where(IprCaseAnnualFee.case_record_id == record.id, IprCaseAnnualFee.fee_year == body.fee_year))
    if row is None or row.status != _PAID:
        raise HTTPException(status_code=409, detail="这一年的年费还没有登记已缴")
    row.status, row.paid_date = "待缴", None
    db.add(WorkflowEvent(record_id=record.id, action="撤销知识产权案件年费已缴", from_status=record.status, to_status=record.status,
                         operator=identity["username"], comment=f"{item['fee_name']}（应缴日 {item['due_date']}）"))
    await db.commit()
    return {"case_id": record.id, "fee_year": body.fee_year, "status": row.status}
