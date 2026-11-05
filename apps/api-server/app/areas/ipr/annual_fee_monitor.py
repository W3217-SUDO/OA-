"""BUG20261030004：知识产权中心“专利年费”菜单，照老系统 年费清单 / 年费监控。

在监控中的专利：案件上点过“加入/放弃年费监控”的以此为准；迁移的老案件没点过的，按老系统案件阶段“年费监控”算。
应缴日按申请日周年日算，第 N 年年费在第 N 年开始（申请日 + N-1 年）前缴纳，逾期 6 个月内可补缴。
高勤兰 10-30 199162：已缴不手动登记，照老系统存储过程 P_IPR_Case_EventGenerate 的口径：
这一年度有年费请款（CaseFeeTypeId 11020/21020/31020，IsActived='T'，Amount>0），且请款挂了有效的
FAM_Invoice_File（按 CaseFeeGuid 关联，发票或官费收据都算），或请款 CaseFeeStatus=101（不再催缴），即为已缴。
付款金额/付款状态不参与。应缴日 = 申请日 + (年度-1) 年 - 1 天。案件阶段 32、99 和人工屏蔽（IPR_Case_Event_NotIn，
EventTypeId=4）不进年费监控。老系统费用表迁移后放在 legacy_ipr_sh / legacy_ipr_hd（按案件 data.legacy_source），
迁移前没有这些表，全部显示“未通知”、按未缴算。2017 年以前的 IPR_Case_FeeItem 旧费用模块不再用。
280146（高勤兰 11-02 举例 SHPD1711392 等，tgn 11-04 21:50 确认）：沪知老知识产权系统迁移来的专利，老系统 2018 年 12 月后不再更新，
阶段一直停在“年费监控”；没有任何后续记录（OA 里没有年费记录、没有在 HD 系统继续办理、也没有同一专利的其他案件）的视为已失效，
不进年费监控和年费清单。只改这里的筛选，不改案件数据；案件上手动点过“加入年费监控”的照常监控。
280146（高勤兰 11-05 举例 HDPU1600401、HDPU1600400）：照老系统，最后一个年度缴完后，在专利权到期日前一天（申请日 + 保护期 - 1 天）
再列一行“专利权到期”：阶段不是失效的才列，年度、年费为 0，“本案通/回/付”显示“专利权到期”；导出 Excel/Word 照列，
Word 里这一行滞纳金、手续费按 0 算。
"""
from calendar import monthrange
from urllib.parse import quote

from fastapi import APIRouter

from app.core.constants import UPLOAD_ROOT, WORD_DOCUMENT_CONTENT_TYPE
from app.core.dependencies import (
    AsyncSession, BusinessRecord, Depends, Document, File, FileAttachment, Form, HTTPException, Path, Query, Response,
    UploadFile, WorkflowEvent, and_, current_identity, date, func, get_db, io, json, or_, select, settings, text, uuid4,
)

router = APIRouter()

# 国家知识产权局专利年费标准（元/年，不含费减）：(截至第几年, 金额)
_FEE_TABLE = {
    "发明": [(3, 900), (6, 1200), (9, 2000), (12, 4000), (15, 6000), (20, 8000)],
    "实用新型": [(3, 600), (5, 900), (8, 1200), (10, 2000)],
    "外观设计": [(3, 600), (5, 900), (8, 1200), (10, 2000), (15, 3000)],
}
_QUARTER_NAMES = {1: "一", 2: "二", 3: "三", 4: "四"}
_ANNUAL_FEE_TYPE_IDS = [11020, 21020, 31020]
_LATE_FEE_TYPE_IDS = [11021, 21021, 31021]
_NO_MONITOR_PHASE_IDS = {"32", "99"}
_LEGACY_SCHEMAS = {"ipr_sh": "legacy_ipr_sh", "ipr_hd": "legacy_ipr_hd"}
_GRANTED_PHASES = {"年费监控", "授权", "发证", "滞纳金阶段"}
_UPLOAD_SUFFIXES = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".png", ".jpg", ".jpeg", ".zip", ".rar"}
_HANDLING_FEE = 100  # 老系统模板：年费手续费 100 元/项
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


def _normalized_application_no(data: dict) -> str:
    return str(data.get("application_no") or "").replace(" ", "")


async def _lapsed_legacy_case_ids(records: list, db: AsyncSession) -> set[int]:
    """沪知老系统迁移来、之后没有任何后续记录的专利（视为已失效）。"""
    from app.models import IprCaseAnnualFee
    candidates = [record for record in records
                  if str((record.data or {}).get("migration_source") or "").startswith("hz_crm")
                  and str((record.data or {}).get("annual_fee_monitoring")).lower() != "true"]
    if not candidates:
        return set()
    ids = [record.id for record in candidates]
    numbers = sorted({number for record in candidates if (number := _normalized_application_no(record.data or {}))})
    followed: set[str] = set()
    if numbers:
        # 同一专利在 OA 里还有别的案件（含恒达系统迁来的）。
        number_expr = func.replace(func.coalesce(BusinessRecord.data["application_no"].as_string(), ""), " ", "")
        for offset in range(0, len(numbers), 500):
            batch = numbers[offset:offset + 500]
            followed.update(number for number, count in (await db.execute(
                select(number_expr, func.count()).where(BusinessRecord.module == "ipr_case", BusinessRecord.deleted_at.is_(None),
                                                        number_expr.in_(batch)).group_by(number_expr))).all() if count > 1)
            # 在恒达（HD）老系统里继续办理。
            if db.get_bind().dialect.name == "postgresql" and await db.scalar(text("SELECT to_regclass('legacy_ipr_hd.\"IPR_Case\"') IS NOT NULL")):
                followed.update(row[0] for row in (await db.execute(text(
                    'SELECT DISTINCT replace("CaseRequestNo", \' \', \'\') FROM legacy_ipr_hd."IPR_Case" '
                    'WHERE replace("CaseRequestNo", \' \', \'\') = ANY(:numbers)'), {"numbers": batch})).all())
    # OA 里有年费记录（年费提醒或年费请款）。
    with_fees = set((await db.scalars(select(IprCaseAnnualFee.case_record_id).where(IprCaseAnnualFee.case_record_id.in_(ids)))).all())
    with_fees.update(int(value) for value in (await db.scalars(select(BusinessRecord.data["case_id"].as_string()).where(
        BusinessRecord.module == "finance", BusinessRecord.status != "已删除",
        BusinessRecord.data["case_id"].as_string().in_([str(value) for value in ids]),
        BusinessRecord.data["fee_type_name"].as_string().like("%年费%")))).all() if str(value or "").isdigit())
    return {record.id for record in candidates
            if record.id not in with_fees and _normalized_application_no(record.data or {}) not in followed}


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


def _legacy_source(data: dict) -> str:
    return str(data.get("legacy_source") or "ipr_sh")


async def _legacy_annual_fees(case_ids_by_source: dict[str, list[int]], db: AsyncSession) -> tuple[dict, set]:
    """老系统年费/滞纳金请款，按 (来源, 老系统 CaseId, 年度) 汇总；另返回人工屏蔽年费提醒的 (来源, CaseId)。"""
    fees: dict[tuple[str, int, int], dict] = {}
    blocked: set[tuple[str, int]] = set()
    for source, case_ids in case_ids_by_source.items():
        schema = _LEGACY_SCHEMAS.get(source)
        if not schema or not case_ids or not await db.scalar(text(f"SELECT to_regclass('{schema}.\"FAM_AR_CaseFee\"') IS NOT NULL")):
            continue
        has_notin = await db.scalar(text(f"SELECT to_regclass('{schema}.\"IPR_Case_Event_NotIn\"') IS NOT NULL"))
        for offset in range(0, len(case_ids), 500):
            batch = case_ids[offset:offset + 500]
            rows = (await db.execute(text(
                f'SELECT f."CaseId", f."AnnualYear", f."CaseFeeTypeId", f."Amount", f."CashedAmount", f."PaidAmount", f."CaseFeeStatus", '
                f'EXISTS (SELECT 1 FROM {schema}."FAM_Invoice_File" i WHERE i."CaseFeeId" = CAST(f."CaseFeeGuid" AS text) AND i."IsActived" = \'T\') '
                f'FROM {schema}."FAM_AR_CaseFee" f WHERE f."IsActived" = \'T\' AND f."AnnualYear" IS NOT NULL '
                'AND f."CaseFeeTypeId" = ANY(:types) AND f."CaseId" = ANY(:case_ids)'
            ), {"types": _ANNUAL_FEE_TYPE_IDS + _LATE_FEE_TYPE_IDS, "case_ids": batch})).all()
            for case_id, year_no, fee_type, amount, cashed, paid_amount, fee_status, has_invoice in rows:
                item = fees.setdefault((source, int(case_id), int(year_no)), {
                    "informed": False, "paid": False, "inform_amount": 0.0, "gained_amount": 0.0, "bill_amount": 0.0, "late_fee": 0.0,
                })
                if int(fee_type) in _LATE_FEE_TYPE_IDS:
                    item["late_fee"] += float(amount or 0)
                    continue
                item["informed"] = True
                item["inform_amount"] += float(amount or 0)
                item["gained_amount"] += float(cashed or 0)
                item["bill_amount"] += float(paid_amount or 0)
                if float(amount or 0) > 0 and (has_invoice or str(fee_status or "") == "101"):
                    item["paid"] = True
            if has_notin:
                for (case_id,) in (await db.execute(text(
                    f'SELECT DISTINCT "CaseId" FROM {schema}."IPR_Case_Event_NotIn" WHERE "EventTypeId" = 4 AND "CaseId" = ANY(:case_ids)'
                ), {"case_ids": batch})).all():
                    blocked.add((source, int(case_id)))
    return fees, blocked


def _out_of_monitor(row: dict) -> bool:
    """年费监控（6月内、逾期）只列未缴且没被人工屏蔽的；年费清单照老系统不按已缴过滤。"""
    return row["paid"] or row["monitor_blocked"]


def _amounts_text(row: dict) -> str:
    if row.get("term_expired"):
        return "专利权到期"
    if not row["informed"]:
        return "未通知"
    return "/".join(str(round(row[key] or 0)) for key in ("inform_amount", "gained_amount", "bill_amount"))


async def _monitored_fee_rows(identity: dict, db: AsyncSession, start: date, end: date) -> list[dict]:
    from app.core.ipr import _ipr_case_list_conditions
    conditions = await _ipr_case_list_conditions(identity, db, case_kind="专利")
    records = list((await db.scalars(select(BusinessRecord).where(*conditions, _monitoring_condition()))).all())
    lapsed = await _lapsed_legacy_case_ids(records, db)
    records = [record for record in records if record.id not in lapsed]
    by_source: dict[str, list[int]] = {}
    for item in records:
        legacy_id = str((item.data or {}).get("legacy_ipr_case_id") or "")
        if legacy_id.isdigit():
            by_source.setdefault(_legacy_source(item.data or {}), []).append(int(legacy_id))
    legacy, blocked = await _legacy_annual_fees(by_source, db) if by_source else ({}, set())
    rows = []
    for record in records:
        data = dict(record.data or {})
        application_date = _parse_date(data.get("application_date"))
        kind = _patent_kind(str(data.get("case_type") or ""))
        if not application_date or not kind or str(data.get("case_phase_id") or "") in _NO_MONITOR_PHASE_IDS:
            continue
        source, legacy_id = _legacy_source(data), str(data.get("legacy_ipr_case_id") or "")
        legacy_key = int(legacy_id) if legacy_id.isdigit() else None
        term, first_paid = _term_years(kind, application_date), _first_paid_year_no(data, application_date)
        relief = _relief_rate(data)
        base = {
            "case_id": record.id, "serial_no": record.serial_no,
            "case_name": data.get("case_name") or record.title or "", "case_type": data.get("case_type") or "",
            "case_phase": data.get("case_phase") or "",
            "customer": record.customer or "", "customer_record_id": data.get("customer_record_id"),
            "granted": bool(_parse_date(data.get("authorization_date"))) or str(data.get("case_phase") or "") in _GRANTED_PHASES,
            "applicant": data.get("applicant_name") or data.get("applicant") or record.customer or "",
            "application_no": data.get("application_no") or "", "application_date": application_date,
            "procurator": data.get("procurator_name") or data.get("procurator") or "",
            "case_source": data.get("case_origin_people_name") or "",
            "writer": data.get("copywriter_name") or data.get("writer") or "",
            "relief_rate": round(relief * 100), "monitor_blocked": legacy_key is not None and (source, legacy_key) in blocked,
            "term_expired": False,
        }
        expiry_due = _add_months(application_date, 12 * term) - date.resolution
        if start <= expiry_due <= end and "失效" not in str(data.get("case_phase") or ""):
            rows.append({
                **base, "fee_year": expiry_due.year, "year_no": term + 1, "due_date": expiry_due,
                "period_start": expiry_due, "period_end": expiry_due, "annual_fee": 0, "informed": False,
                "inform_amount": 0, "gained_amount": 0, "bill_amount": 0, "late_fee_billed": 0, "paid": False,
                "term_expired": True,
            })
        for year_no in range(first_paid + 1, term + 1):
            period_start = _add_months(application_date, 12 * (year_no - 1))
            due = period_start - date.resolution
            if due > end:
                break
            if due < start:
                continue
            fee = legacy.get((source, legacy_key, year_no)) or {} if legacy_key is not None else {}
            rows.append({
                **base,
                "fee_year": due.year, "year_no": year_no, "due_date": due, "period_start": period_start,
                "period_end": _add_months(period_start, 12) - date.resolution,
                "annual_fee": round(_standard_fee(kind, year_no) * (1 - relief)),
                "informed": bool(fee.get("informed")),
                "inform_amount": fee.get("inform_amount", 0), "gained_amount": fee.get("gained_amount", 0),
                "bill_amount": fee.get("bill_amount", 0), "late_fee_billed": fee.get("late_fee", 0),
                "paid": bool(fee.get("paid")),
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
        count = sum(1 for row in rows if view["start"] <= row["due_date"] <= view["end"] and not (view["unpaid_only"] and _out_of_monitor(row)))
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
        rows = [row for row in rows if not _out_of_monitor(row)]
    rows = _filter_rows(rows, query.filters, query.date_from, query.date_to)
    if query.keys:
        rows = [row for row in rows if f"{row['case_id']}-{row['year_no']}" in query.keys]
    return selected, rows


_EXPORT_HEADERS = ["申请人", "专利名称", "案件类型", "案件编号", "申请号", "申请日", "年度", "年费", "费减", "案源人", "本案通/回/付"]


def _export_values(row: dict) -> list[str]:
    amounts = _amounts_text(row)
    return [
        row["applicant"], row["case_name"], row["case_type"], row["serial_no"], row["application_no"], str(row["application_date"]),
        "0" if row.get("term_expired") else f"第{row['year_no']}年度：{row['period_start']}至{row['period_end']}", str(row["annual_fee"]), f"{row['relief_rate']}%",
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


def _late_fee(row: dict, today: date) -> int:
    """滞纳金：逾期不满一个月不收，之后每满一个月加收当年全额年费的 5%（模板所引专利法实施细则规定）。"""
    if row.get("term_expired") or row["due_date"] >= today:
        return 0
    months = 0
    while months < 6 and _add_months(row["due_date"], months + 1) < today:
        months += 1
    return round(row["annual_fee"] * 0.05 * months)


def _handling_fee(row: dict) -> int:
    """专利权到期那一行不缴年费，手续费也按 0（280146）。"""
    return 0 if row.get("term_expired") else _HANDLING_FEE


def _fill_placeholders(paragraph, values: dict[str, str]) -> None:
    """先在单个 run 内替换保留格式；占位符被拆在多个 run 里时整段合并后替换。"""
    for run in paragraph.runs:
        for key, value in values.items():
            if key in run.text:
                run.text = run.text.replace(key, value)
    if "$" in paragraph.text and paragraph.runs:
        merged = paragraph.text
        for key, value in values.items():
            merged = merged.replace(key, value)
        if merged != paragraph.text:
            paragraph.runs[0].text = merged
            for run in paragraph.runs[1:]:
                run.text = ""


async def _customer_letter_fields(customer_record_id, fallback_name: str, db: AsyncSession) -> dict[str, str]:
    record = None
    try:
        record = await db.get(BusinessRecord, int(customer_record_id)) if customer_record_id else None
    except (TypeError, ValueError):
        record = None
    data = dict(record.data or {}) if record and record.module == "customer" else {}
    contacts = [item for item in data.get("contacts") or [] if isinstance(item, dict) and item.get("is_valid", True)]
    contact = next((item for item in contacts if item.get("is_primary")), contacts[0] if contacts else {})
    return {
        "$CUSTOMERNAME": (record.title if record and record.module == "customer" else "") or fallback_name,
        "$CONTRACTNAME": str(contact.get("name") or ""),
        "$ZIP": str(data.get("zip") or data.get("zip_code") or data.get("postal_code") or ""),
        "$ADDRESS": str(data.get("address") or data.get("registered_address") or ""),
        "$TEL": str(contact.get("office_phone") or contact.get("phone") or data.get("phone") or ""),
        "$FAX": str(data.get("fax") or ""),
    }


@router.get(f"{settings.api_prefix}/ipr/annual-fee-monitor/export/word")
async def export_ipr_annual_fee_monitor_word(query: _ListQuery = Depends(), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """生成年费清单(Word)：照老系统模板 3300034“通知交纳年费”，只含已授权专利，勾选的案件须是同一客户。"""
    from app.areas.ipr.annual_fee_notice_template import annual_fee_notice_template
    if not query.keys:
        raise HTTPException(status_code=422, detail="请先勾选要生成年费清单的案件")
    _, rows = await _list_rows(query, identity, db)
    if not rows:
        raise HTTPException(status_code=422, detail="勾选的案件不在当前列表中，请刷新后重新勾选")
    if any(not row["granted"] for row in rows):
        names = "、".join(row["serial_no"] for row in rows if not row["granted"])
        raise HTTPException(status_code=422, detail=f"只能对已授权专利生成年费清单：{names} 尚未授权")
    if len({(row["customer_record_id"], row["customer"]) for row in rows}) > 1:
        raise HTTPException(status_code=422, detail="勾选的案件须属于同一客户")
    today = date.today()
    # 老系统滞纳金是单独请款（11021/21021/31021），有就用请款金额，没有按规定估算。
    late_fees = [round(row["late_fee_billed"]) if row["late_fee_billed"] else _late_fee(row, today) for row in rows]
    annual_total = sum(row["annual_fee"] for row in rows) + sum(late_fees)
    handling_fees = [_handling_fee(row) for row in rows]
    handling_total = sum(handling_fees)
    values = await _customer_letter_fields(rows[0]["customer_record_id"], rows[0]["customer"], db)
    values.update({
        "$FWR": str(today), "$1": str(min(row["due_date"] for row in rows)),
        "$2": str(annual_total), "$3": str(handling_total), "$4": str(annual_total + handling_total),
    })
    document = Document(io.BytesIO(annual_fee_notice_template()))
    paragraphs = list(document.paragraphs)
    for table in document.tables:
        for cells in table.rows:
            for cell in cells.cells:
                paragraphs.extend(cell.paragraphs)
    # $1~$4 之外的占位符更长，先替换长的，避免 $1 误伤其它占位符。
    ordered = dict(sorted(values.items(), key=lambda item: -len(item[0])))
    for paragraph in paragraphs:
        if "$" in paragraph.text:
            _fill_placeholders(paragraph, ordered)
    fee_table = document.tables[-1]
    for index, (row, late, handling) in enumerate(zip(rows, late_fees, handling_fees), start=1):
        cells = fee_table.add_row().cells
        for cell, value in zip(cells, [
            str(index), row["serial_no"], row["case_name"], row["application_no"], str(row["application_date"]),
            "0" if row.get("term_expired") else f"第{row['year_no']}年度", str(row["annual_fee"]), str(late), str(handling),
        ]):
            cell.text = value
    buffer = io.BytesIO()
    document.save(buffer)
    filename = f"通知缴纳年费-{values['$CUSTOMERNAME'] or rows[0]['serial_no']}-{today}.docx"
    return Response(
        content=buffer.getvalue(), media_type=WORD_DOCUMENT_CONTENT_TYPE,
        headers={"Content-Disposition": f"attachment; filename=annual-fee-notice.docx; filename*=UTF-8''{quote(filename)}"},
    )


@router.post(f"{settings.api_prefix}/ipr/annual-fee-monitor/upload", status_code=201)
async def upload_ipr_annual_fee_monitor_file(
    file: UploadFile = File(...), case_ids: str = Form(...), category: str = Form(...), document_date: date = Form(...),
    remark: str = Form(""), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """上传文件：照老系统，勾选案件、选文件类型，同一个文件挂到每个勾选的案件。

    年费监控里的迁移案件状态是老系统阶段（如“年费监控”），不是“在办”，所以不走通用批量上传的在办限制，
    只要求案件在年费监控中、当前用户是案件负责人或管理者。对冲（把收据挂到年费请款上算已缴）待老系统费用迁入后接上。
    """
    from app.core.ipr import _active_ipr_case_file_type
    from app.core.permissions import _ensure_record_module, _require_record_owner_or_manager, _require_role_action
    from app.core.storage import _attachment_dict
    await _require_role_action(identity, db, "ipr.case.file.manage")
    try:
        target_ids = list(dict.fromkeys(int(value) for value in json.loads(case_ids)))
    except (TypeError, ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=422, detail="请勾选要上传文件的案件")
    if not target_ids or len(target_ids) > 200:
        raise HTTPException(status_code=422, detail="请勾选 1~200 个案件")
    normalized_category = category.strip()
    if not normalized_category or len(normalized_category) > 64 or len(remark.strip()) > 1000:
        raise HTTPException(status_code=422, detail="文件类型或说明不符合要求")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _UPLOAD_SUFFIXES:
        raise HTTPException(status_code=422, detail="不支持的文件格式")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="文件不能为空")
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="单个文件不能超过 20MB")
    monitored = set((await db.scalars(select(BusinessRecord.id).where(BusinessRecord.id.in_(target_ids), _monitoring_condition()))).all())
    records, file_types = [], {}
    for target_id in target_ids:
        record = await _ensure_record_module(target_id, "ipr_case", identity, db)
        if record.id not in monitored:
            raise HTTPException(status_code=409, detail=f"案件 {record.serial_no} 不在年费监控中；本次未上传任何文件")
        await _require_record_owner_or_manager(record, identity, db)
        file_types[record.id] = await _active_ipr_case_file_type(record, normalized_category, db)
        records.append(record)
    original_name = Path(file.filename or "document").name
    paths, attachments = [], []
    try:
        for record in records:
            file_type = file_types[record.id]
            target = UPLOAD_ROOT / f"{uuid4().hex}{suffix}"
            target.write_bytes(content)
            paths.append(target)
            attachment = FileAttachment(
                record_id=record.id, category=normalized_category, file_type_code=file_type.code, original_name=original_name,
                stored_name=target.name, content_type=file.content_type or "application/octet-stream", size=len(content), path=str(target),
                uploader=identity["username"], remark=remark.strip(), document_date=document_date,
                requires_transmission=bool((file_type.extra or {}).get("requires_transmission")),
            )
            attachments.append(attachment)
            db.add(attachment)
            db.add(WorkflowEvent(record_id=record.id, action="专利年费上传文件", from_status=record.status, to_status=record.status,
                                 operator=identity["username"], comment=f"{normalized_category}｜{original_name}｜文档日期 {document_date}"))
        await db.commit()
        for attachment in attachments:
            await db.refresh(attachment)
    except Exception:
        await db.rollback()
        for path in paths:
            path.unlink(missing_ok=True)
        raise
    by_id = {record.id: record for record in records}
    return {"created": len(attachments), "items": [_attachment_dict(item, by_id[item.record_id]) for item in attachments]}
