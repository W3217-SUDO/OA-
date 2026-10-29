"""控制台个人统计和明细使用同一队列口径。"""
from app.core.dashboard_personal_queues import personal_case_queues, personal_finance_queues, personal_queues
from app.core.dashboard_scope import CASE_QUEUES


METRIC_DEFINITIONS = (
    ("official-fee-unpaid", "待缴官费", "amber"),
    ("refund-pending", "待退费", "cyan"),
    ("evidence-supplement", "补充证据", "green"),
    ("opinion-supplement", "补充意见", "blue"),
    ("appeal-pending", "待上诉", "red"),
    ("execution-pending", "待执行", "purple"),
    ("urgent-cases", "紧急案件", "orange"),
    ("official-fee-unreceived", "未到官费金额", "navy"),
)


def _metrics_response(queues, definitions=METRIC_DEFINITIONS):
    return {"metrics": [{"key": key, "label": label, "tone": tone,
        "value": f"{sum(item['amount'] for item in queues[key]):.2f}元" if key == "official-fee-unreceived" else f"{len(queues[key])}件",
        "route": f"dashboard-queue-{key}"}
        for key, label, tone in definitions]}


async def _official_fee_audit_metric(response, identity, db):
    """BUG20261028003（范明明 2026-10-29）：能打开请款单审批的人，“待缴官费”= 请款单审批里待审批的官方费用，
    点进去也只看这些；其他人（律师）仍是本人案件未缴的官费。"""
    from app.core.dashboard_list_counts import payment_audit_official_total
    from app.core.permissions import _permission_payload_for_identity
    menus = set((await _permission_payload_for_identity(identity, db)).get("menu_keys") or [])
    if "finance-payment-audit" not in menus:
        return response
    for metric in response["metrics"]:
        if metric["key"] == "official-fee-unpaid":
            metric["value"] = f"{await payment_audit_official_total(identity, db)}件"
            metric["route"] = "dashboard-queue-official-fee-audit"
    return response


async def dashboard_metrics(identity, db):
    return await _official_fee_audit_metric(_metrics_response(await personal_queues(identity, db)), identity, db)


async def dashboard_finance_metrics(identity, db):
    """返回原八卡中的三张财务卡，其他指标由案件分区读取。"""
    definitions = [item for item in METRIC_DEFINITIONS if item[0] not in CASE_QUEUES]
    return await _official_fee_audit_metric(
        _metrics_response(await personal_finance_queues(identity, db), definitions), identity, db)


async def dashboard_case_metrics(identity, db):
    """先返回真实案件指标，不等待财务指标的全量计算。"""
    definitions = [item for item in METRIC_DEFINITIONS if item[0] in CASE_QUEUES]
    return _metrics_response(await personal_case_queues(identity, db), definitions)
