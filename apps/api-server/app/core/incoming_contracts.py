"""合同下的回款关联只读查询，不由共享合同猜测回款主体。"""

from sqlalchemy import JSON, String, and_, case, cast, column, func, literal, or_, select

from app.models import IncomingPayment


def contract_incoming_condition(contract, db):
    dialect = db.get_bind().dialect.name
    allocations = IncomingPayment.allocations
    if dialect == "postgresql":
        safe_array = case((func.json_typeof(allocations) == "array", allocations),
                          else_=literal([], type_=JSON))
        entries = func.json_array_elements(safe_array).table_valued(column("value", JSON))
    elif dialect == "sqlite":
        entries = func.json_each(allocations).table_valued(column("value", JSON))
    else:
        raise RuntimeError(f"合同回款查询不支持数据库方言：{dialect}")
    data = entries.c.value
    linked_id = func.coalesce(data["contract_id"].as_string(), data["contract_record_id"].as_string(), "")
    linked_no = func.coalesce(data["contract_no"].as_string(), "")
    has_id = cast(linked_id, String).not_in(("", "0"))
    has_no = linked_no != ""
    allocation_match = select(literal(1)).select_from(entries).where(
        or_(has_id, has_no),
        or_(~has_id, cast(linked_id, String) == str(contract.id)),
        or_(~has_no, linked_no == contract.serial_no),
    ).exists()
    if dialect == "sqlite":
        allocation_match = and_(func.json_type(allocations) == "array", allocation_match)
    root_id = IncomingPayment.contract_record_id
    root_no = func.coalesce(IncomingPayment.contract_no, "")
    root_match = and_(
        or_(root_id == contract.id, root_no == contract.serial_no),
        or_(root_id.is_(None), root_id == contract.id),
        or_(root_no == "", root_no == contract.serial_no),
    )
    return or_(root_match, allocation_match)
