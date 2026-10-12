"""合同应收模板导出入口。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.security import current_identity
from app.areas.contract.receivable_export_rows import receivable_export_rows
from app.areas.contract.export_projection import contract_export_rows, render_contract_details, render_contract_list

router = APIRouter()


@router.get(f"{settings.api_prefix}/contracts/receivables/contracts")
async def list_receivable_contracts(
    scope: str = Query("company", pattern="^(all|mine|department|company)$"),
    contract_no: str = "", contract_body: str = "", customer: str = "", case_no: str = "",
    source_person: str = "", signed_at_start: str = "", signed_at_end: str = "",
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    items = await contract_export_rows(identity, db, action="查看", scope=scope, serial_no=contract_no,
        customer=customer, contract_body=contract_body, case_no=case_no, source_person=source_person,
        signed_at_start=signed_at_start, signed_at_end=signed_at_end)
    return {"items": items, "total": len(items)}


@router.get(f"{settings.api_prefix}/contracts/receivables/export-excel")
async def export_contract_receivables(
    detail: bool = False, scope: str = Query("company", pattern="^(mine|department|company)$"),
    contract_no: str = "", contract_body: str = "", customer: str = "", case_no: str = "",
    source_person: str = "", signed_at_start: str = "", signed_at_end: str = "",
    detail_contract_no: str = "", amount_filter: str = Query("", pattern="^(|official-unreceived|official-loss|agency-due)$"),
    dashboard_queue: str = "", owner: str = "",
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    contracts = await contract_export_rows(identity, db, scope=scope if not detail else "all",
        serial_no=contract_no, customer=customer, contract_body=contract_body, case_no=case_no if not detail else "",
        source_person=source_person, signed_at_start=signed_at_start, signed_at_end=signed_at_end)
    if not detail:
        return await render_contract_list(contracts, identity, db, summary=True)
    if dashboard_queue:
        if dashboard_queue != "official-fee-unreceived":
            raise HTTPException(422, "控制台业务入口无效")
        from app.core.dashboard_scope import load_dashboard_scope
        dashboard = await load_dashboard_scope(identity, db, include_summaries=True)
        case_ids = {case.id for case in dashboard.cases}
        details = await receivable_export_rows(contracts, dashboard.identity, db, case_ids=case_ids)
    else:
        details = await receivable_export_rows(contracts, identity, db)
    def matches(row):
        if detail_contract_no and row["contract_no"] != detail_contract_no:
            return False
        if owner and row["owner"] != owner:
            return False
        if case_no and case_no.casefold() not in row["case_no"].casefold():
            return False
        if amount_filter:
            official = row["fee_category"] == "official"
            if amount_filter == "official-loss":
                return official and "亏损" in row["phase"] and row["remaining_amount"] is not None and row["remaining_amount"] > 0
            return row["remaining_amount"] is not None and row["remaining_amount"] > 0 and (official if amount_filter == "official-unreceived" else not official)
        return True
    return await render_contract_details(contracts, [row for row in details if matches(row)], identity, db)
