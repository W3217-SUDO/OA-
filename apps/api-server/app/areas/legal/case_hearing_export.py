"""公司排期导出复用当前查询，保留权限并按关联案件去重。"""

from fastapi import HTTPException
from sqlalchemy import select

from app.areas.legal.hearing_query import query_company_hearings
from app.models import BusinessRecord


async def export_company_hearing_cases(identity, db, **query):
    from app.areas.legal.router import _ordinary_cases_excel_response
    from app.core.query_batches import _scalars_in_batches

    ids = await query_company_hearings(identity, db, **query, export_case_ids=True)
    if not ids:
        raise HTTPException(422, "当前排期查询没有可导出的案件")
    records = await _scalars_in_batches(db, ids, lambda batch: select(BusinessRecord).where(
        BusinessRecord.module == "case", BusinessRecord.id.in_(batch),
    ))
    by_id = {record.id: record for record in records}
    if set(by_id) != set(ids):
        raise HTTPException(409, "排期关联案件已变化，请刷新后重新导出")
    return await _ordinary_cases_excel_response([by_id[case_id] for case_id in ids], identity, db)
