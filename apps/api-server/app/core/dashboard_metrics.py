"""控制台个人统计和明细使用同一队列口径。"""
from app.core.dashboard_personal_queues import personal_queues


async def dashboard_metrics(identity, db):
    queues = await personal_queues(identity, db)
    definitions = [
        ("official-fee-unpaid", "待缴官费", "amber"),
        ("refund-pending", "待退费", "cyan"),
        ("evidence-supplement", "补充证据", "green"),
        ("opinion-supplement", "补充意见", "blue"),
        ("appeal-pending", "待上诉", "red"),
        ("execution-pending", "待执行", "purple"),
        ("urgent-cases", "紧急案件", "orange"),
        ("official-fee-unreceived", "未到官费金额", "navy"),
    ]
    return {"metrics": [{"key": key, "label": label, "tone": tone,
        "value": f"{sum(item['amount'] for item in queues[key]):.2f}元" if key == "official-fee-unreceived" else f"{len(queues[key])}件",
        "route": f"dashboard-queue-{key}"}
        for key, label, tone in definitions]}
