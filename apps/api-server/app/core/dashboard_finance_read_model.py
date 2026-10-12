"""控制台专用费用关系池：全量保留绑定，只有候选费用读取金额摘要。"""
from datetime import datetime
from typing import NamedTuple

from fastapi import HTTPException
from sqlalchemy import Boolean, Column, Integer, JSON, MetaData, Table, and_, or_, select

from app.core.finance_summary_query import FEE_SUMMARY_FIELDS
from app.core.json_relation_query import scalar_in_values
from app.core.record_projection_query import read_record_projections
from app.models import BusinessRecord


TABLE_NAME = "dashboard_finance_relations"
LINK_FIELDS = (
    "case_id", "case_record_id", "case_no", "contract_id", "contract_record_id",
    "contract_no", "legacy_case_fee_id", "legacy_fee_id",
)
TYPE_FIELDS = ("fee_type", "fee_type_name", "case_fee_type_name", "expense_subtype")
RAW_FIELDS = (*LINK_FIELDS, *TYPE_FIELDS, "contract_object_id")
finance_relations = Table(
    TABLE_NAME, MetaData(), Column("record_id", Integer, primary_key=True),
    *(Column(name, JSON) for name in RAW_FIELDS), Column("links", JSON, nullable=False),
    Column("is_candidate", Boolean, nullable=False), Column("data_is_object", Boolean, nullable=False),
)


class FinanceBindingRow(NamedTuple):
    id: int
    status: str | None
    links: list
    is_candidate: bool


class FinanceMetricFee(NamedTuple):
    id: int
    module: str
    serial_no: str
    title: str
    status: str | None
    updated_at: datetime
    data: dict


async def read_dashboard_finance_fee_pool(db, conditions, *, where_data=None):
    """只供 PG 财务三卡使用；普通详情及其他数据库继续原读取器。"""
    if db.get_bind().dialect.name != "postgresql":
        raise ValueError("费用关系读模型仅适用于 PostgreSQL")
    relation = finance_relations.c
    records = BusinessRecord.__table__
    query = select(
        records.c.id, records.c.status, relation.links, relation.is_candidate,
        relation.data_is_object, relation.record_id,
    ).select_from(records).outerjoin(
        finance_relations, relation.record_id == records.c.id,
    ).where(*conditions)
    if where_data is not None:
        # 保留原 JSON 标量转换；补读条件还会读取四个费用类型和对象编号。
        filters = where_data({name: relation[name][()] for name in RAW_FIELDS})
        query = query.where(or_(
            relation.record_id.is_(None), relation.data_is_object.is_(False),
            and_(*filters),
        ))
    # Core 流仍使用当前会话事务，显式保留原 ORM 查询的自动刷新语义。
    if db.autoflush:
        await db.flush()
    connection = await db.connection()
    result = await connection.stream(query.execution_options(yield_per=1024))
    rows, invalid_ids = [], set()
    try:
        async for batch in result.partitions():
            for fee_id, status, links, is_candidate, data_is_object, record_id in batch:
                if record_id is None:
                    raise HTTPException(503, "控制台费用关系读模型不完整")
                if not data_is_object:
                    invalid_ids.add(fee_id)
                rows.append(FinanceBindingRow(fee_id, status, links, is_candidate))
    finally:
        await result.close()

    # 非对象数据仍经原读取器判断，不能把原来的类型错误变成空字典。
    invalid_fees = []
    if invalid_ids:
        invalid_fees = await read_record_projections(
            db, [*conditions, scalar_in_values(BusinessRecord.id, invalid_ids)], FEE_SUMMARY_FIELDS,
            where_data=where_data, record_factory=FinanceMetricFee,
            metadata_fields=("id", "module", "serial_no", "title", "status", "updated_at"),
        )
        visible_invalid = {fee.id for fee in invalid_fees}
        rows = [row for row in rows if row.id not in invalid_ids or row.id in visible_invalid]
    candidate_ids = {row.id for row in rows if row.is_candidate and row.id not in invalid_ids}
    fees = await read_record_projections(
        db, [scalar_in_values(BusinessRecord.id, candidate_ids)], FEE_SUMMARY_FIELDS,
        record_factory=FinanceMetricFee,
        metadata_fields=("id", "module", "serial_no", "title", "status", "updated_at"),
    ) if candidate_ids else []
    by_id = {fee.id: fee for fee in [*fees, *invalid_fees]}
    if set(by_id) != candidate_ids | {fee.id for fee in invalid_fees}:
        raise HTTPException(503, "控制台费用金额读模型不完整")
    return rows, [by_id[row.id] for row in rows if row.id in by_id]
