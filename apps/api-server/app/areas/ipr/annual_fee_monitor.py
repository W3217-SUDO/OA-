"""BUG20261030004：知识产权中心“专利年费”菜单，照老系统 年费清单 / 年费监控。

在监控中的专利：案件上点过“加入/放弃年费监控”的以此为准；迁移的老案件没点过的，按老系统案件阶段“年费监控”算。
应缴日按申请日周年日算，第 N 年年费在第 N 年开始（申请日 + N-1 年）前缴纳，逾期 6 个月内可补缴。
高勤兰 10-30 199162：已缴不手动登记，按老系统看这一年度的年费官费有没有上传缴费凭证（官费收据）；
老系统年费记录在 IPR_Case_FeeItem（FeeTypeId=3，Yearly=第几年度，Amount/ActualAmount/BillAmount=通/回/付）。
"""
from calendar import monthrange
from urllib.parse import quote

from docx.enum.section import WD_ORIENT
from fastapi import APIRouter

from app.core.constants import WORD_DOCUMENT_CONTENT_TYPE
from app.core.dependencies import (
    AsyncSession, BusinessRecord, Depends, Document, HTTPException, Query, Response,
    and_, current_identity, date, get_db, io, or_, select, settings, text,
)

router = APIRouter()

# 国家知识产权局专利年费标准（元/年，不含费减）：(截至第几年, 金额)
_FEE_TABLE = {
    "发明": [(3, 900), (6, 1200), (9, 2000), (12, 4000), (15, 6000), (20, 8000)],
    "实用新型": [(3, 600), (5, 900), (8, 1200), (10, 2000)],
    "外观设计": [(3, 600), (5, 900), (8, 1200), (10, 2000), (15, 3000)],
}
_QUARTER_NAMES = {1: "一", 2: "二", 3: "三", 4: "四"}
_LEGACY_ANNUAL_FEE_TYPE_ID = 3
# 列表上方的筛选，照老系统：参数名 -> 行里比对的字段。
_FILTER_FIELDS = {
    "applicant": ("applicant",), "customer": ("customer",), "case_source": ("case_source",),
    "case_type": ("case_type",), "writer": ("writer",), "case_no": ("serial_no", "application_no"),
    "case_phase": ("case_phase",), "procurator": ("procurator",),
}


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


def _relief_rate(data: dict) -> float:
    """案件上的费减比例：0.85 即费减 85%；1.00 是迁移数据里“无费减”的写法。"""
    try:
        rate = float(str(data.get("cost_slow_rate") or "0").strip())
    except ValueError:
        return 0.0
    return rate if 0 < rate < 1 else 0.0


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


async def _legacy_annual_fee_items(serial_nos: list[str], db: AsyncSession) -> dict[tuple[str, int], dict]:
    """老系统年费记录：同一案件同一年度取一条，有官费收据的优先。"""
    found: dict[tuple[str, int], dict] = {}
    for offset in range(0, len(serial_nos), 500):
        rows = (await db.execute(text(
            'SELECT "CaseNo", "Yearly", "Amount", "ActualAmount", "BillAmount", "BillNo", "BillFileName" '
            'FROM "IPR_Case_FeeItem" WHERE "FeeTypeId" = :fee_type AND coalesce("IsActive", \'T\') = \'T\' '
            'AND "Yearly" IS NOT NULL AND "CaseNo" = ANY(:case_nos)'
        ), {"fee_type": _LEGACY_ANNUAL_FEE_TYPE_ID, "case_nos": serial_nos[offset:offset + 500]})).all()
        for case_no, yearly, amount, actual, bill_amount, bill_no, bill_file in rows:
            paid = bool((bill_no or "").strip() or (bill_file or "").strip())
            key = (str(case_no), int(yearly))
            if key in found and found[key]["paid"] and not paid:
                continue
            found[key] = {
                "paid": paid, "inform_amount": float(amount or 0),
                "gained_amount": float(actual or 0), "bill_amount": float(bill_amount or 0),
            }
    return found


async def _monitored_fee_rows(identity: dict, db: AsyncSession, start: date, end: date) -> list[dict]:
    from app.core.ipr import _ipr_case_list_conditions
    conditions = await _ipr_case_list_conditions(identity, db, case_kind="专利")
    records = list((await db.scalars(select(BusinessRecord).where(*conditions, _monitoring_condition()))).all())
    legacy = await _legacy_annual_fee_items([item.serial_no for item in records], db) if records else {}
    rows = []
    for record in records:
        data = dict(record.data or {})
        application_date = _parse_date(data.get("application_date"))
        kind = _patent_kind(str(data.get("case_type") or ""))
        if not application_date or not kind:
            continue
        term, first_paid = _term_years(kind, application_date), _first_paid_year_no(data, application_date)
        relief = _relief_rate(data)
        for year in range(start.year, end.year + 1):
            year_no = year - application_date.year + 1
            if year_no <= first_paid or year_no > term:
                continue
            due = _add_months(application_date, 12 * (year_no - 1))
            if not start <= due <= end:
                continue
            fee = legacy.get((record.serial_no, year_no)) or {}
            rows.append({
                "case_id": record.id, "serial_no": record.serial_no,
                "case_name": data.get("case_name") or record.title or "", "case_type": data.get("case_type") or "",
                "case_phase": data.get("case_phase") or "",
                "customer": record.customer or "", "applicant": data.get("applicant_name") or data.get("applicant") or record.customer or "",
                "application_no": data.get("application_no") or "", "application_date": application_date,
                "procurator": data.get("procurator_name") or data.get("procurator") or "",
                "case_source": data.get("case_origin_people_name") or "",
                "writer": data.get("copywriter_name") or data.get("writer") or "",
                "fee_year": year, "year_no": year_no, "due_date": due,
                "period_end": _add_months(due, 12) - date.resolution,
                "annual_fee": round(_standard_fee(kind, year_no) * (1 - relief)), "relief_rate": round(relief * 100),
                "inform_amount": fee.get("inform_amount", 0), "gained_amount": fee.get("gained_amount", 0),
                "bill_amount": fee.get("bill_amount", 0), "paid": bool(fee.get("paid")),
            })
    rows.sort(key=lambda item: (item["due_date"], item["serial_no"]))
    return rows


def _filter_rows(rows: list[dict], filters: dict[str, str], date_from: date | None, date_to: date | None) -> list[dict]:
    for name, value in filters.items():
        word = (value or "").strip()
        if word:
            rows = [row for row in rows if any(word in str(row[field]) for field in _FILTER_FIELDS[name])]
    if date_from:
        rows = [row for row in rows if row["application_date"] >= date_from]
    if date_to:
        rows = [row for row in rows if row["application_date"] <= date_to]
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
        count = sum(1 for row in rows if view["start"] <= row["due_date"] <= view["end"] and not (view["unpaid_only"] and row["paid"]))
        items.append({"key": view["key"], "group": view["group"], "label": view["label"], "count": count})
    return {"items": items}


class _ListQuery:
    """列表、导出共用的查询条件：左侧项目 + 上方筛选；导出时 keys 为勾选的“案件id-年份”。"""

    def __init__(
        self,
        view: str = Query(min_length=1, max_length=32),
        applicant: str = Query(default="", max_length=100), customer: str = Query(default="", max_length=100),
        case_source: str = Query(default="", max_length=100), case_type: str = Query(default="", max_length=100),
        writer: str = Query(default="", max_length=100), case_no: str = Query(default="", max_length=100),
        case_phase: str = Query(default="", max_length=100), procurator: str = Query(default="", max_length=100),
        date_from: date | None = None, date_to: date | None = None,
        keys: str = Query(default="", max_length=20000),
    ):
        self.view, self.date_from, self.date_to = view, date_from, date_to
        self.filters = {
            "applicant": applicant, "customer": customer, "case_source": case_source, "case_type": case_type,
            "writer": writer, "case_no": case_no, "case_phase": case_phase, "procurator": procurator,
        }
        self.keys = {item.strip() for item in keys.split(",") if item.strip()}


async def _list_rows(query: _ListQuery, identity: dict, db: AsyncSession) -> tuple[dict, list[dict]]:
    from app.core.permissions import _require_record_module_menu
    await _require_record_module_menu("ipr_case", identity, db, action="查看")
    selected = next((item for item in _views(date.today()) if item["key"] == query.view), None)
    if not selected:
        raise HTTPException(status_code=422, detail="年费清单/监控项目无效，请刷新页面")
    rows = await _monitored_fee_rows(identity, db, selected["start"], selected["end"])
    if selected["unpaid_only"]:
        rows = [row for row in rows if not row["paid"]]
    rows = _filter_rows(rows, query.filters, query.date_from, query.date_to)
    if query.keys:
        rows = [row for row in rows if f"{row['case_id']}-{row['fee_year']}" in query.keys]
    return selected, rows


_EXPORT_HEADERS = ["申请人", "专利名称", "案件类型", "案件编号", "申请号", "申请日", "年度", "年费", "费减", "案源人", "本案通/回/付"]


def _export_values(row: dict) -> list[str]:
    amounts = "/".join(str(round(row[key] or 0)) for key in ("inform_amount", "gained_amount", "bill_amount"))
    return [
        row["applicant"], row["case_name"], row["case_type"], row["serial_no"], row["application_no"], str(row["application_date"]),
        f"第{row['year_no']}年度：{row['due_date']}至{row['period_end']}", str(row["annual_fee"]), f"{row['relief_rate']}%",
        row["case_source"], amounts,
    ]


@router.get(f"{settings.api_prefix}/ipr/annual-fee-monitor/items")
async def list_ipr_annual_fee_monitor_items(query: _ListQuery = Depends(), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    selected, rows = await _list_rows(query, identity, db)
    return {"items": rows, "total": len(rows), "label": selected["label"], "group": selected["group"]}


@router.get(f"{settings.api_prefix}/ipr/annual-fee-monitor/export/excel")
async def export_ipr_annual_fee_monitor_excel(query: _ListQuery = Depends(), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """生成年费清单(Excel)：勾选了导出勾选的，没勾导出当前列表全部。"""
    from app.core.system import _excel_response
    selected, rows = await _list_rows(query, identity, db)
    return _excel_response(f"年费清单-{selected['label']}-{date.today()}.xls", _EXPORT_HEADERS, [_export_values(row) for row in rows])


@router.get(f"{settings.api_prefix}/ipr/annual-fee-monitor/export/word")
async def export_ipr_annual_fee_monitor_word(query: _ListQuery = Depends(), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """生成年费清单(Word)：表格同 Excel。"""
    selected, rows = await _list_rows(query, identity, db)
    document = Document()
    section = document.sections[0]
    section.orientation, section.page_width, section.page_height = WD_ORIENT.LANDSCAPE, section.page_height, section.page_width
    document.add_heading(f"专利年费清单（{selected['label']}）", level=1)
    document.add_paragraph(f"生成日期：{date.today()}　共 {len(rows)} 件")
    table = document.add_table(rows=1, cols=len(_EXPORT_HEADERS))
    table.style = "Table Grid"
    for cell, header in zip(table.rows[0].cells, _EXPORT_HEADERS):
        cell.text = header
    for row in rows:
        for cell, value in zip(table.add_row().cells, _export_values(row)):
            cell.text = value
    buffer = io.BytesIO()
    document.save(buffer)
    filename = f"年费清单-{selected['label']}-{date.today()}.docx"
    return Response(
        content=buffer.getvalue(), media_type=WORD_DOCUMENT_CONTENT_TYPE,
        headers={"Content-Disposition": f"attachment; filename=annual-fees.docx; filename*=UTF-8''{quote(filename)}"},
    )
