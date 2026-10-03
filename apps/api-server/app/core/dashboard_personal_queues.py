"""控制台统计复用各业务页面的筛选和金额投影。"""
from app.models import BusinessRecord
from app.core.cases import _matches_dashboard_case_queue, _urgent_case_ids
from app.core.finance import _refund_case_fee_rows
from app.core.dashboard_finance import dashboard_unpaid_fee_rows
from app.core.request_metrics import measure_phase
from app.core.dashboard_scope import CASE_QUEUES, QUEUE_KEYS, dashboard_identity, dashboard_queue_cases, dashboard_receivables, dashboard_urgent_cases, personal_refund_identity


async def personal_queues(identity, db):
    with measure_phase("dashboard.scope"):
        identity = await dashboard_identity(identity, db)
        refund_identity = await personal_refund_identity(identity, db)
        cases = await dashboard_queue_cases(db, [
            BusinessRecord.id.in_(identity["_dashboard_case_ids"]),
        ])
    by_id = {case.id: case for case in cases}
    by_no = {case.serial_no: case for case in cases}
    queues = {key: {} for key in QUEUE_KEYS}

    def add(key, case, amount=0, fee_id=None):
        queue_id = (case.id, fee_id) if fee_id is not None else case.id
        row = queues[key].setdefault(queue_id, {"id": case.id, "serial_no": case.serial_no,
            "title": case.title, "status": case.status, "amount": 0})
        row["amount"] = round(row["amount"] + amount, 2)
        if fee_id is not None:
            row["fee_id"] = fee_id

    with measure_phase("dashboard.urgent"):
        urgent_cases = await dashboard_urgent_cases(identity, db, identity["_dashboard_case_ids"])
        urgent_case_ids = await _urgent_case_ids(urgent_cases, db, identity["username"])
    for case in urgent_cases:
        if case.id in urgent_case_ids:
            add("urgent-cases", case)
    for case in cases:
        for key, queue in CASE_QUEUES.items():
            if queue != "urgent" and _matches_dashboard_case_queue(case, queue):
                add(key, case)
    for key in ("official-fee-unpaid", "refund-pending"):
        with measure_phase(f"dashboard.{key}"):
            if key == "official-fee-unpaid":
                rows = await dashboard_unpaid_fee_rows(identity, db, by_id, by_no)
            else:
                rows = await _refund_case_fee_rows(refund_identity, db)
        for row in rows:
            data = row["data"]
            case = by_id.get(data.get("case_id")) or by_no.get(data.get("case_no"))
            if case:
                add(key, case, fee_id=row["id"] if key == "refund-pending" else None)
        del rows
    with measure_phase("dashboard.receivables"):
        receivables = await dashboard_receivables(identity, db)
    for row in receivables:
        case = by_id.get(row.get("case_record_id"))
        if case:
            add("official-fee-unreceived", case, row["remaining_amount"])
    return {key: list(rows.values()) for key, rows in queues.items()}
