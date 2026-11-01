"""员工业绩统计中心（BUG 500799，思法汇成 11-01 18:35 确认口径）。

当年四类数（另加报表大屏搬来的“新建案件数”，BUG 500801），按案源人 / 调查员 / 开庭律师 / 律师助理分别统计，一个案件同角色几个人各算一次：
- 代理费到账：与报表大屏员工业绩排行（BUG 500798）同一口径，按到账日期；
- 在办案件：当前没结束的案件，不按年份（结束的判断与报表大屏相同，另不算已过期）；
- 开庭数：案件上一审、二审、再审、执行开庭日期落在当年的，每个日期算一次；
- 结案归档：归档审核通过日期在当年的案件，含亏损归档（另列“其中亏损归档”）。
- 新建案件：当年新建的案件数，与报表大屏员工业绩排行（BUG 500798）相同，按建案日期。
测试客户（名称含“测试”/test）的案件不算。
"""
from datetime import date

from app.core.agency_fee_ranking import (
    _is_test_customer, agency_fee_totals, assistant_people, hearing_people, investigator_people, source_people,
)

STAFF_ROLES = {
    "source": ("案源人", source_people, "by_source_person"),
    "investigator": ("调查员", investigator_people, "by_investigator"),
    "hearing": ("开庭律师", hearing_people, "by_hearing_lawyer"),
    "assistant": ("律师助理", assistant_people, "by_assistant"),
}
HEARING_DATE_KEYS = ("first_court_hearing_date", "second_court_hearing_date", "retrial_court_hearing_date", "execution_court_hearing_date")
# 正在走归档审核的案件不算在办（待思法汇成确认 A）。
ARCHIVING_STATUSES = frozenset({"归档审核", "亏损内审", "亏损审核", "归档拒绝", "亏损拒绝"})
NOT_ACTIVE_STATUSES = frozenset({"已过期"})


def _in_year(value, year: int) -> bool:
    text = str(value or "").strip()[:10]
    return len(text) == 10 and text[:4] == str(year)


def case_figures(case, year: int) -> dict:
    from app.core.cases import _large_screen_case_is_closed
    from app.core.formatters import _case_filing_date
    data = case.data or {}
    status = str(case.status or "").strip()
    active = not _large_screen_case_is_closed(case) and status not in NOT_ACTIVE_STATUSES and status not in ARCHIVING_STATUSES
    archived_on = data.get("archive_reviewed_at") or data.get("archived_at")
    archived = status in {"已归档", "亏损归档"} and _in_year(archived_on, year)
    filed = _case_filing_date(case)
    return {
        "new_cases": int(bool(filed) and filed.year == year),
        "active_cases": int(active),
        "hearings": sum(1 for key in HEARING_DATE_KEYS if _in_year(data.get(key), year)),
        "archived_cases": int(archived),
        "loss_archived_cases": int(archived and status == "亏损归档"),
    }


async def staff_performance(db, scope: list, cases: list, *, year: int, today: date, role: str, name: str = "", amount_visible: bool) -> dict:
    from app.core.cases import _large_screen_case_is_excluded
    label, people_of, fee_key = STAFF_ROLES[role]
    fees = None
    if amount_visible:
        fee_to = min(date(year, 12, 31), today)
        extra = {"by_investigator": investigator_people, "by_assistant": assistant_people}
        fees = await agency_fee_totals(db, scope, date(year, 1, 1), fee_to, extra_roles=extra) if fee_to >= date(year, 1, 1) else {"total": 0.0}
    keys = ("new_cases", "active_cases", "hearings", "archived_cases", "loss_archived_cases")
    totals = {key: 0 for key in keys}
    by_person: dict[str, dict] = {}
    for case in cases:
        if _large_screen_case_is_excluded(case) or _is_test_customer(str(case.customer or "")):
            continue
        figures = case_figures(case, year)
        for key in keys:
            totals[key] += figures[key]
        if not any(figures.values()):
            continue
        for person in people_of(case):
            row = by_person.setdefault(person, {key: 0 for key in keys})
            for key in keys:
                row[key] += figures[key]
    person_fees = (fees or {}).get(fee_key, {})
    for person in person_fees:
        by_person.setdefault(person, {key: 0 for key in keys})
    keyword = name.strip()
    rows = [
        {"person": person, **values, "agency_fee": round(person_fees.get(person, 0.0), 2) if fees is not None else None}
        for person, values in by_person.items() if not keyword or keyword in person
    ]
    rows.sort(key=lambda row: (-(row["agency_fee"] or 0), -row["active_cases"], -row["hearings"], row["person"]))
    return {
        "year": year, "role": role, "role_label": label, "amount_visible": amount_visible,
        "totals": {**totals, "agency_fee": fees["total"] if fees is not None else None},
        "rows": rows,
        "roles": [{"value": key, "label": value[0]} for key, value in STAFF_ROLES.items()],
        "definition": (
            "代理费到账：到账单分配到代理费的金额（按到账日期），不含公司之间转款、代收代付、测试客户和退款，与报表大屏员工业绩排行口径相同；"
            "在办案件：当前没结束的案件，不按年份；开庭数：一审、二审、再审、执行开庭日期落在当年的，每个日期算一次；"
            "结案归档：归档审核通过日期在当年的案件，含亏损归档；新建案件：当年新建的案件数，与报表大屏员工业绩排行相同。一个案件同角色有几个人，每人各算一次。"
        ),
    }
