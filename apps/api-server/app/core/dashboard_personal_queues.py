"""控制台统计复用各业务页面的筛选和金额投影。"""
from sqlalchemy import select
from app.models import BusinessRecord
from app.core.cases import _matches_dashboard_case_queue
from app.core.finance import _fee_query_rows, _refund_case_fee_rows
from app.core.dashboard_scope import CASE_QUEUES, QUEUE_KEYS, dashboard_identity, dashboard_receivables


async def personal_queues(identity, db):
    identity = await dashboard_identity(identity, db)
    cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(identity["_dashboard_case_ids"]),
    ))).all())
    by_id = {case.id: case for case in cases}
    by_no = {case.serial_no: case for case in cases}
    queues = {key: {} for key in QUEUE_KEYS}

    def add(key, case, amount=0):
        row = queues[key].setdefault(case.id, {"id": case.id, "serial_no": case.serial_no,
            "title": case.title, "status": case.status, "amount": 0})
        row["amount"] = round(row["amount"] + amount, 2)

    for case in cases:
        for key, queue in CASE_QUEUES.items():
            if _matches_dashboard_case_queue(case, queue):
                add(key, case)
    for key, rows in (
        ("official-fee-unpaid", await _fee_query_rows(identity, db, unpaid_official=True)),
        ("refund-pending", await _refund_case_fee_rows(identity, db)),
    ):
        for row in rows:
            data = row["data"]
            case = by_id.get(data.get("case_id")) or by_no.get(data.get("case_no"))
            if case:
                add(key, case)
    for row in await dashboard_receivables(identity, db):
        case = by_id.get(row.get("case_record_id"))
        if case:
            add("official-fee-unreceived", case, row["remaining_amount"])
    return {key: list(rows.values()) for key, rows in queues.items()}
