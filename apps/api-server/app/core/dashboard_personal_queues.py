"""控制台个人提醒队列，不依赖公司案件或财务菜单权限。"""
from sqlalchemy import or_, select
from app.models import BusinessRecord
from app.core.permissions import _case_mine_scope_condition
from app.core.cases import _matches_dashboard_case_queue, _is_pending_execution_case
from app.core.finance import _invoice_case_fee_rows
from app.core.finance_batch_parity import official_refund_progress


async def personal_queues(identity, db):
    cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case", await _case_mine_scope_condition(identity, db),
        BusinessRecord.status.notin_(["已合并", "已删除", "已回收"]),
    ))).all())
    by_id = {case.id: case for case in cases}
    by_no = {case.serial_no: case for case in cases}
    fees = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance", BusinessRecord.status != "已删除",
        or_(BusinessRecord.data["case_id"].as_integer().in_(by_id),
            BusinessRecord.data["case_no"].as_string().in_(by_no)),
    ))).all()) if cases else []
    fee_ids = {fee.id for fee in fees}
    projected = await _invoice_case_fee_rows(identity, db, scope="company", ids=fee_ids,
        scope_authorized_fee_ids=fee_ids, force_amount_projection=True) if fee_ids else []
    queues = {key: {} for key in ("official-fee-unpaid", "refund-pending", "evidence-supplement",
        "opinion-supplement", "appeal-pending", "execution-pending", "urgent-cases", "official-fee-unreceived")}

    def add(key, case, amount=0):
        row = queues[key].setdefault(case.id, {"id": case.id, "serial_no": case.serial_no,
            "title": case.title, "status": case.status, "amount": 0})
        row["amount"] = round(row["amount"] + amount, 2)

    for case in cases:
        for key, queue in (("evidence-supplement", "supplement_evidence"), ("opinion-supplement", "supplement_opinion"), ("urgent-cases", "urgent")):
            if _matches_dashboard_case_queue(case, queue):
                add(key, case)
        if case.status.strip() in {"一审等待上诉", "待上诉"}:
            add("appeal-pending", case)
        if _is_pending_execution_case(case):
            add("execution-pending", case)
    for fee in projected:
        data = fee["data"]
        case = by_id.get(data.get("case_id")) or by_no.get(data.get("case_no"))
        if case is None:
            continue
        requested = float(data.get("refund_requested_amount") or data.get("refund_amount") or 0)
        refunded = official_refund_progress(data, requested, float(data.get("refunded_amount") or 0))
        if requested > refunded and not data.get("refund_not_required") and data.get("refund_status") != "R100":
            add("refund-pending", case, requested - refunded)
        if data.get("base_fee_type") == "官方费用":
            amount = float(data.get("amount") or 0)
            paid = float(data.get("paid_amount") or 0)
            received = float(data.get("cashed_amount") or data.get("received_amount") or 0)
            if amount > paid and data.get("payment_status") not in {"已驳回", "已作废"}:
                add("official-fee-unpaid", case, amount - paid)
            if amount > received:
                add("official-fee-unreceived", case, amount - received)
    return {key: list(rows.values()) for key, rows in queues.items()}
