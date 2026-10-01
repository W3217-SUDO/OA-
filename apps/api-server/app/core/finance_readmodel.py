"""财务概览的只读聚合；不载入完整业务记录或交易实体。"""

from collections import defaultdict

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import FINANCE_FEE_TYPES
from app.core.finance import _visible_incoming_payment_statement
from app.core.permissions import _record_scope_conditions
from app.core.system import _allowed_field_keys
from app.models import BusinessRecord, FinanceTransaction, IncomingPayment


async def read_finance_summary(identity: dict, db: AsyncSession) -> dict:
    """保留原有范围和金额语义，计数下推，历史JSON金额分批读取。"""
    conditions = [
        BusinessRecord.module.in_(["finance", "invoice", "refund"]),
        *(await _record_scope_conditions(identity, db)),
    ]
    counts = defaultdict(int)
    totals = defaultdict(int)
    for module, record_status, count in (await db.execute(
        select(BusinessRecord.module, BusinessRecord.status, func.count())
        .where(*conditions).group_by(BusinessRecord.module, BusinessRecord.status)
    )).all():
        counts[module, record_status] = int(count)
        totals[module] += int(count)

    # 历史金额可能是数字或数字字符串；SQLite强制转换会吞掉非法值，
    # 因此只投影金额及JSON类型，仍按原实现float转换，并区分缺键与显式null。
    dialect = db.get_bind().dialect.name
    if dialect == "sqlite":
        amount_kind = func.json_type(BusinessRecord.data, "$.amount")
    elif dialect == "postgresql":
        amount_kind = func.json_typeof(BusinessRecord.data["amount"])
    else:
        raise ValueError(f"财务概览不支持数据库类型：{dialect}")
    amounts = {fee_type: 0 for fee_type in FINANCE_FEE_TYPES}
    amount_rows = await db.stream(
        select(BusinessRecord.data["fee_type"].as_string(),
               BusinessRecord.data["amount"], amount_kind)
        .where(*conditions, BusinessRecord.module == "finance",
               BusinessRecord.data["fee_type"].as_string().in_(FINANCE_FEE_TYPES))
        .order_by(BusinessRecord.id).execution_options(yield_per=400)
    )
    try:
        async for batch in amount_rows.partitions(400):
            for fee_type, amount, kind in batch:
                amounts[fee_type] += float(0 if kind is None else amount)
    finally:
        await amount_rows.close()

    transactions = select(FinanceTransaction.transaction_type,
                          func.sum(FinanceTransaction.amount))
    if identity.get("role") != "admin":
        visible_ids = select(BusinessRecord.id).where(*conditions)
        transactions = transactions.where(or_(
            FinanceTransaction.finance_record_id.in_(visible_ids),
            or_(FinanceTransaction.finance_record_id.is_(None),
                FinanceTransaction.finance_record_id == 0)
            & (FinanceTransaction.operator == identity["username"]),
        ))
    transaction_amounts = dict((await db.execute(
        transactions.group_by(FinanceTransaction.transaction_type)
    )).all())
    incoming = await _visible_incoming_payment_statement(identity, db)
    incoming_counts = dict((await db.execute(
        incoming.with_only_columns(IncomingPayment.status, func.count(),
                                   maintain_column_froms=True)
        .order_by(None).group_by(IncomingPayment.status)
    )).all())
    can_view_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    return {
        "fees": totals["finance"], "draft": counts["finance", "草稿"],
        "pending": counts["finance", "待审批"],
        "approved": counts["finance", "已审批"] + counts["finance", "部分付款"],
        "paid": counts["finance", "已付款"],
        "invoice_applications": totals["invoice"],
        "invoice_pending": counts["invoice", "待审批"],
        "refund_applications": totals["refund"],
        "refund_pending": counts["refund", "待审批"],
        "amount_visible": can_view_amount,
        "total_fee_amount": sum(amounts.values()) if can_view_amount else None,
        "amounts_by_type": amounts if can_view_amount else {},
        "paid_amount": transaction_amounts.get("付款", 0) if can_view_amount else None,
        "invoice_amount": transaction_amounts.get("开票", 0) if can_view_amount else None,
        "refund_amount": transaction_amounts.get("退费", 0) if can_view_amount else None,
        "incoming_payments": sum(incoming_counts.values()),
        "incoming_unclaimed": incoming_counts.get("待认领", 0),
        "incoming_unallocated": incoming_counts.get("待分配", 0) + incoming_counts.get("部分分配", 0),
    }
