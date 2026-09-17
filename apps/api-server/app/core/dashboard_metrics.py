"""控制台提醒及财务统计，保持费用投影的授权和金额口径。"""
from app.core.dependencies import BusinessRecord, select, func
from app.core.cases import _is_pending_execution_case, _matches_dashboard_case_queue
from app.core.finance import _fee_query_rows, _refund_case_fee_rows
from app.core.permissions import _case_personal_scope_condition
from app.core.projections import _receivable_detail_projection
from app.core.dashboard import dashboard_scope, dashboard_records


async def dashboard_metrics(identity, db):
    scope, allowed_dashboard_modules = await dashboard_scope(identity, db)
    records = await dashboard_records(db, scope, allowed_dashboard_modules & {"case", "contract", "finance"})
    cases = [item for item in records if item.module == "case"]
    username = identity["username"]
    unpaid_official = await _fee_query_rows(
        identity, db, scope="mine", unpaid_official=True,
    )
    receivable_details = await _receivable_detail_projection(identity, db, list(records))
    personal_official_receivables = [
        item for item in receivable_details
        if item["fee_category"] == "official" and item["owner"] == username
    ]
    unpaid_amount = sum(item["remaining_amount"] for item in personal_official_receivables)
    pending_refunds = await _refund_case_fee_rows(identity, db) if "finance" in allowed_dashboard_modules else []
    supplement_evidence = [item for item in cases if _matches_dashboard_case_queue(item, "supplement_evidence")]
    supplement_opinion = [item for item in cases if _matches_dashboard_case_queue(item, "supplement_opinion")]
    pending_appeal_count = int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
        BusinessRecord.module == "case", _case_personal_scope_condition(username),
        func.trim(BusinessRecord.status).in_({"一审等待上诉", "待上诉"}),
    )) or 0)
    pending_execution = [item for item in cases if _is_pending_execution_case(item)]
    urgent_cases = [item for item in cases if _matches_dashboard_case_queue(item, "urgent")]
    metrics = [
        {
            "key": "official-fee-unpaid", "label": "待缴官费",
            "value": f"{len(unpaid_official)}件", "tone": "amber",
            "route": "finance-fee-query",
            "query": {"scope": "mine", "unpaid_official": True},
        },
        {"key": "refund-pending", "label": "待退费", "value": f"{len(pending_refunds)}件", "tone": "cyan", "route": "finance-refund"},
        {"key": "evidence-supplement", "label": "补充证据", "value": f"{len(supplement_evidence)}件", "tone": "green", "route": "case-company-supplement-evidence"},
        {"key": "opinion-supplement", "label": "补充意见", "value": f"{len(supplement_opinion)}件", "tone": "blue", "route": "case-company-supplement-opinion"},
        {"key": "appeal-pending", "label": "待上诉", "value": f"{pending_appeal_count}件", "tone": "red", "route": "case-mine-appeal"},
        {"key": "execution-pending", "label": "待执行", "value": f"{len(pending_execution)}件", "tone": "purple", "route": "case-company-execution"},
        {"key": "urgent-cases", "label": "紧急案件", "value": f"{len(urgent_cases)}件", "tone": "orange", "route": "case-company-urgent"},
        {
            "key": "official-fee-unreceived", "label": "未到官费金额",
            "value": f"{unpaid_amount:.2f}元", "tone": "navy",
            "route": "contract-receivable-detail",
            "detail_context": {
                "contract_no": "", "return_view": "contract-receivable-mine",
                "amount_filter": "official-unreceived", "owner": username,
            },
        },
    ]
    return {"metrics": metrics}
