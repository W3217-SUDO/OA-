"""控制台一次计算内复用收款来源；离开请求即释放，不缓存业务结果。"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from types import SimpleNamespace

from sqlalchemy import JSON, case, cast, column, func, literal, select, true
from sqlalchemy.dialects.postgresql import aggregate_order_by

from app.models import BusinessRecord, IncomingPayment
from app.core.record_read_model import record_read_models, uses_record_read_model


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
        allocations = IncomingPayment.allocations
        if db.get_bind().dialect.name == "postgresql":
            # 分配条目含大量历史字段；金额关联只需这些键，保持原分配顺序和嵌套条目。
            allocation_source = case(
                (func.json_typeof(allocations) == "null", cast(literal("[]"), JSON)),
                else_=allocations,
            )
            items = func.json_array_elements(allocation_source).table_valued(
                column("value", JSON), with_ordinality="position",
            ).render_derived().lateral()
            item_source = case(
                (func.json_typeof(items.c.value) == "object", items.c.value),
                else_=cast(literal("{}"), JSON),
            )
            item = func.json_to_record(item_source).table_valued(
                *(column(key, JSON) for key in (
                    "case_no", "fee_record_id", "fee_id", "legacy_case_fee_id", "legacy_fee_id",
                    "finance_record_id", "amount", "settlement_items",
                )),
            ).render_derived(with_types=True).lateral()
            allocations = select(func.json_agg(aggregate_order_by(
                func.row_to_json(item.table_valued(), type_=JSON), items.c.position,
            ), type_=JSON)).select_from(items).join(item, true()).where(
                func.json_typeof(items.c.value) == "object",
            ).correlate(IncomingPayment).scalar_subquery()
        rows = await db.execute(select(
            IncomingPayment.id, IncomingPayment.received_date,
            IncomingPayment.payer_name, allocations.label("allocations"),
        ).order_by(IncomingPayment.received_date.desc(), IncomingPayment.id.desc()))
        scope.incoming = [SimpleNamespace(**row._mapping) for row in rows]
    return scope.incoming


async def unambiguous_fee_case_nos(case_nos, db):
    if not case_nos:
        return set()
    scope = _current_scope.get()
    read_model = uses_record_read_model(db, ("case_no",))
    source = record_read_models.c.data if read_model else BusinessRecord.data
    number = source["case_no"].as_string()
    query = select(number, func.count(BusinessRecord.id)).select_from(BusinessRecord)
    if read_model:
        query = query.join(record_read_models, record_read_models.c.record_id == BusinessRecord.id)
    query = query.where(
        BusinessRecord.module == "finance",
    ).group_by(number)
    if scope is not None and scope.db is db:
        if scope.case_fee_counts is None:
            scope.case_fee_counts = dict((await db.execute(query)).all())
        counts = scope.case_fee_counts
        return {number for number in case_nos if counts.get(number) == 1}
    rows = (await db.execute(query.where(number.in_(case_nos)))).all()
    return {number for number, count in rows if count == 1}
