"""报表大屏经营总数据（BUG 500801，思法汇成 11-01 18:54 确认）。

1. 全年新增案件数，按月；
2. 新增调查线索，按调查员、按品牌各一张图，两条线：提交数（不含草稿）和审核通过数；
3. 全年开庭数量，按月，口径同员工业绩统计中心：一审/二审/再审/执行开庭日期落在当年的，每个日期算一次，含已排期；
4. 任务按月两条线：发出的任务数和完成数。
"""
from datetime import datetime

from sqlalchemy import select

from app.core.constants import CASE_EVENT_TIME_ZONE
from app.core.person_names import person_name
from app.models import BusinessRecord

RANKING_LIMIT = 10
CLUE_DRAFT_STATUS = "草稿"
# 线索审核通过后的状态：待取证、待客户审核、已取证、已转案件。
CLUE_APPROVED_STATUSES = frozenset({"待取证", "待客户审核", "已取证", "已转案件"})
# 发出的任务不算取消和撤回的（10 月底批量生成后又取消的自动任务不计）。
TASK_NOT_ISSUED_STATUSES = frozenset({"已取消", "已撤回"})
TASK_DONE_STATUSES = frozenset({"已完成", "已验收"})
TASK_DONE_DATE_KEYS = ("finished_at", "auto_confirmed_at", "completion_auto_confirm_at", "auto_completed_at")


def _months() -> list[int]:
    return list(range(1, 13))


def _local_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.astimezone(CASE_EVENT_TIME_ZONE).date() if value.tzinfo else value.date()
    text = str(value).strip()[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _is_test_customer(title) -> bool:
    text = str(title or "")
    return "测试" in text or "test" in text.lower()


def case_month_counts(cases, year: int) -> list[dict]:
    from app.core.formatters import _case_filing_date
    counts = {month: 0 for month in _months()}
    for case in cases:
        filed = _case_filing_date(case)
        if filed and filed.year == year:
            counts[filed.month] += 1
    return [{"month": month, "value": counts[month]} for month in _months()]


def hearing_month_counts(cases, year: int) -> list[dict]:
    from app.core.staff_performance import HEARING_DATE_KEYS
    counts = {month: 0 for month in _months()}
    for case in cases:
        if _is_test_customer(case.customer):
            continue
        data = case.data or {}
        for key in HEARING_DATE_KEYS:
            day = _local_date(data.get(key))
            if day and day.year == year:
                counts[day.month] += 1
    return [{"month": month, "value": counts[month]} for month in _months()]


async def clue_rankings(db, scope: list, year: int) -> dict:
    clues = (await db.execute(select(
        BusinessRecord.owner, BusinessRecord.status, BusinessRecord.customer, BusinessRecord.created_at, BusinessRecord.data,
    ).where(BusinessRecord.module == "clue", *scope))).all()
    customer_ids = set()
    for clue in clues:
        try:
            customer_ids.add(int((clue.data or {}).get("customer_record_id") or (clue.data or {}).get("customer_id") or 0))
        except (TypeError, ValueError):
            continue
    customer_ids.discard(0)
    short_names = {}
    if customer_ids:
        for customer_id, data in (await db.execute(select(BusinessRecord.id, BusinessRecord.data).where(
            BusinessRecord.module == "customer", BusinessRecord.id.in_(customer_ids),
        ))).all():
            name = str((data or {}).get("customer_short_name") or (data or {}).get("short_name") or "").strip()
            if name:
                short_names[customer_id] = name
    by_investigator: dict[str, list[int]] = {}
    by_brand: dict[str, list[int]] = {}
    for clue in clues:
        created = _local_date(clue.created_at)
        if not created or created.year != year or clue.status == CLUE_DRAFT_STATUS or _is_test_customer(clue.customer):
            continue
        approved = int(clue.status in CLUE_APPROVED_STATUSES)
        data = clue.data or {}
        try:
            customer_id = int(data.get("customer_record_id") or data.get("customer_id") or 0)
        except (TypeError, ValueError):
            customer_id = 0
        investigator = person_name(clue.owner) or "未填调查员"
        brand = short_names.get(customer_id) or str(clue.customer or "").strip() or "未填客户"
        for bucket, key in ((by_investigator, investigator), (by_brand, brand)):
            values = bucket.setdefault(key, [0, 0])
            values[0] += 1
            values[1] += approved

    def ranking(bucket):
        rows = sorted(bucket.items(), key=lambda item: (-item[1][0], -item[1][1], item[0]))[:RANKING_LIMIT]
        return [{"name": name, "submitted": submitted, "approved": approved} for name, (submitted, approved) in rows]

    total_submitted = sum(values[0] for values in by_investigator.values())
    total_approved = sum(values[1] for values in by_investigator.values())
    return {"by_investigator": ranking(by_investigator), "by_brand": ranking(by_brand),
            "submitted": total_submitted, "approved": total_approved}


async def task_month_counts(db, scope: list, year: int) -> list[dict]:
    tasks = (await db.execute(select(BusinessRecord.status, BusinessRecord.created_at, BusinessRecord.data).where(
        BusinessRecord.module == "task", *scope,
    ))).all()
    issued = {month: 0 for month in _months()}
    done = {month: 0 for month in _months()}
    for task in tasks:
        data = task.data or {}
        legacy = data.get("legacy_record") if isinstance(data.get("legacy_record"), dict) else {}
        if task.status not in TASK_NOT_ISSUED_STATUSES:
            created = _local_date(legacy.get("CreateTime")) or _local_date(task.created_at)
            if created and created.year == year:
                issued[created.month] += 1
        if task.status in TASK_DONE_STATUSES:
            finished = next((day for day in (_local_date(data.get(key)) for key in TASK_DONE_DATE_KEYS) if day), None)
            finished = finished or _local_date(legacy.get("TaskFinishedTime"))
            if finished and finished.year == year:
                done[finished.month] += 1
    return [{"month": month, "issued": issued[month], "done": done[month]} for month in _months()]


async def large_screen_overview(db, scope: list, cases, year: int) -> dict:
    return {
        "year": year,
        "case_trend": case_month_counts(cases, year),
        "hearing_trend": hearing_month_counts(cases, year),
        "clues": await clue_rankings(db, scope, year),
        "task_trend": await task_month_counts(db, scope, year),
    }
