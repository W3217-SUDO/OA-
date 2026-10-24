"""合同应收模板导出入口。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.security import current_identity
from app.areas.contract.receivable_export_rows import receivable_export_rows
from app.areas.contract.export_projection import contract_export_rows, render_contract_details, render_contract_list

router = APIRouter()


async def _detail_rows(identity, db, *, contracts=None, dashboard_queue=""):
    case_ids = None
    if dashboard_queue:
        if dashboard_queue != "official-fee-unreceived":
            raise HTTPException(422, "控制台业务入口无效")
        from app.core.dashboard_scope import load_dashboard_scope
        from app.core.contracts import _contract_customer_record_dicts
        from app.core.system import _allowed_field_keys
        dashboard = await load_dashboard_scope(identity, db, include_summaries=True)
        identity = dashboard.identity
        case_ids = {case.id for case in dashboard.cases}
        contracts = await _contract_customer_record_dicts(dashboard.contracts, await _allowed_field_keys(identity, db), db, identity)
    elif contracts is None:
        contracts = await contract_export_rows(identity, db, action="查看", scope="all")
    return await receivable_export_rows(contracts, identity, db, case_ids=case_ids), identity, contracts


@router.get(f"{settings.api_prefix}/contracts/receivables/detail")
async def list_contract_receivable_details(
    dashboard_queue: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.system import _allowed_field_keys
    items, scoped_identity, _ = await _detail_rows(identity, db, dashboard_queue=dashboard_queue)
    if dashboard_queue == "official-fee-unreceived":
        # 控制台数字口径 M2：从“未到官费金额”进入时只列官费且未到账>0 的行，合计与首页同一口径。
        items = [item for item in items if item["fee_category"] == "official" and (item["remaining_amount"] or 0) > 0]
    amount_visible = "contract.amount" in await _allowed_field_keys(scoped_identity, db)
    if not amount_visible:
        for item in items:
            for key in ("amount", "paid_amount", "received_amount", "remaining_amount"):
                item[key] = None
            item["contract_totals"] = dict.fromkeys(item["contract_totals"], None)
    official = [item["remaining_amount"] for item in items if item["fee_category"] == "official"]
    total = round(sum(official), 2) if amount_visible and all(amount is not None for amount in official) else None
    return {"items": items, "total": len(items), "official_unreceived": total, "amount_visible": amount_visible}


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
    from app.areas.contract.list_amounts import attach_contract_list_amounts
    from app.core.system import _allowed_field_keys
    items = await attach_contract_list_amounts(items, identity, db, await _allowed_field_keys(identity, db))
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
    contracts = None
    if detail and dashboard_queue:
        from app.core.permissions import _require_record_module_menu
        # 控制台合同集合沿用页面范围，导出仍校验原身份的合同菜单权限。
        await _require_record_module_menu("contract", identity, db, action="导出")
    else:
        contracts = await contract_export_rows(identity, db, scope=scope if not detail else "all",
            serial_no=contract_no, customer=customer, contract_body=contract_body, case_no=case_no if not detail else "",
            source_person=source_person, signed_at_start=signed_at_start, signed_at_end=signed_at_end)
    if not detail:
        return await render_contract_list(contracts, identity, db, summary=True)
    details, scoped_identity, contracts = await _detail_rows(identity, db, contracts=contracts, dashboard_queue=dashboard_queue)
    if dashboard_queue == "official-fee-unreceived":
        # 与控制台进入的明细页同一口径：只导出官费且未到账>0 的行。
        details = [row for row in details if row["fee_category"] == "official" and (row["remaining_amount"] or 0) > 0]
    def matches(row):
        if dashboard_queue:
            # 控制台沿用当前明细页面对投影字段的筛选，避免普通合同列表范围截断。
            for value, key in ((contract_no, "contract_no"), (customer, "customer"), (source_person, "source_person")):
                if value and value.casefold() not in row[key].casefold():
                    return False
            if contract_body and row["contract_body"] != contract_body:
                return False
            contract_date = row["contract_date"][:10]
            if signed_at_start and (not contract_date or contract_date < signed_at_start):
                return False
            if signed_at_end and (not contract_date or contract_date > signed_at_end):
                return False
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
    return await render_contract_details(contracts, [row for row in details if matches(row)], scoped_identity, db)
