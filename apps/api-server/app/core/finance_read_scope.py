"""控制台一次计算内复用收款来源；离开请求即释放，不缓存业务结果。"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from types import SimpleNamespace

from sqlalchemy import func, select

from app.models import BusinessRecord, IncomingPayment
from app.core.record_read_model import record_json_source


@dataclass
class _FinanceReadScope:
    db: object
    incoming: list | None = None
    case_fee_counts: dict | None = None


_current_scope = ContextVar("finance_read_scope", default=None)


@contextmanager
def finance_read_scope(db):
    token = _current_scope.set(_FinanceReadScope(db))
    try:
        yield
    finally:
        _current_scope.reset(token)


async def scoped_incoming_payments(db):
    scope = _current_scope.get()
    if scope is None or scope.db is not db:
        return None
    if scope.incoming is None:
        # 只取关联计算和明细使用的字段，归属仍由调用方的授权费用集合逐笔判断。
        rows = await db.execute(select(
            IncomingPayment.id, IncomingPayment.received_date,
            IncomingPayment.payer_name, IncomingPayment.allocations,
        ).order_by(IncomingPayment.received_date.desc(), IncomingPayment.id.desc()))
        scope.incoming = [SimpleNamespace(**row._mapping) for row in rows]
    return scope.incoming


async def unambiguous_fee_case_nos(case_nos, db):
    if not case_nos:
        return set()
    scope = _current_scope.get()
    number = record_json_source(db, ("case_no",))["case_no"].as_string()
    query = select(number, func.count(BusinessRecord.id)).where(
        BusinessRecord.module == "finance",
    ).group_by(number)
    if scope is not None and scope.db is db:
        if scope.case_fee_counts is None:
            scope.case_fee_counts = dict((await db.execute(query)).all())
        counts = scope.case_fee_counts
        return {number for number in case_nos if counts.get(number) == 1}
    rows = (await db.execute(query.where(number.in_(case_nos)))).all()
    return {number for number, count in rows if count == 1}
