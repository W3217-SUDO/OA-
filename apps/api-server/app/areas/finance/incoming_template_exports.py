"""到账费用模板的独立导出路由，保留回款筛选与权限范围。"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import BusinessRecord, IncomingPayment, User
from app.security import current_identity

router = APIRouter()


@router.get(f"{settings.api_prefix}/finance/incoming-payments/query/export")
async def export_incoming_fee_query(
    ids: str = "", filters: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from decimal import Decimal
    from urllib.parse import quote
    from sqlalchemy import String, cast
    from app.areas.finance.incoming_query import parse_incoming_filters, read_incoming_query
    from app.areas.finance.excel_templates import render_rows
    from app.areas.finance.export_projection import fee_export_values, joined
    from app.core.finance import _invoice_case_fee_rows, _visible_incoming_payment_statement
    from app.core.fee_cash_query import _case_fee_link_maps, _resolve_case_fee_link_id, read_fee_receipts
    from app.core.finance_read_scope import unambiguous_fee_case_nos
    from app.core.permissions import _record_scope_conditions
    from app.core.query_batches import _scalars_in_batches
    from app.core.system import _export_ids, _allowed_field_keys

    query = parse_incoming_filters("finance-receipts-query", filters)
    selected_ids = set(_export_ids(ids)) if ids.strip() else None
    statement = await _visible_incoming_payment_statement(identity, db)
    if selected_ids is not None:
        statement = statement.where(IncomingPayment.id.in_(selected_ids))
    show_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    users = {user.username.lower(): user for user in (await db.scalars(select(User).where(User.is_active.is_(True)))).all()}
    # 与页面复用同一回款全集筛选；不携带显示分页，也不扩大到全部案件费用。
    result = await read_incoming_query(statement, "", "finance-receipts-query", query, None, None, show_amount, users, db)
    payments = result["items"]
    if selected_ids is not None and {payment.id for payment in payments} != selected_ids:
        raise HTTPException(409, "部分所选回款不符合当前筛选或无权导出")
    if not payments:
        raise HTTPException(422, "当前条件没有可导出的回款")
    allocations = [part for payment in payments for part in payment.allocations or []]
    links = [nested for part in allocations for nested in (part.get("settlement_items") or [part])]
    source_ids = {int(part[key]) for part in links
        for key in ("fee_record_id", "fee_id", "legacy_case_fee_id", "legacy_fee_id", "finance_record_id") if str(part.get(key) or "").isdigit()}
    case_nos = {str(part.get("case_no") or "").strip() for part in allocations} - {""}
    scope = await _record_scope_conditions(identity, db)
    candidates = await _scalars_in_batches(db, source_ids, lambda batch: select(BusinessRecord).where(
        BusinessRecord.module == "finance", BusinessRecord.id.in_(batch), *scope))
    candidates.extend(await _scalars_in_batches(db, source_ids, lambda batch: select(BusinessRecord).where(
        BusinessRecord.module == "finance", or_(
            cast(BusinessRecord.data["legacy_case_fee_id"].as_string(), String).in_([str(value) for value in batch]),
            cast(BusinessRecord.data["legacy_fee_id"].as_string(), String).in_([str(value) for value in batch])), *scope)))
    candidates.extend(await _scalars_in_batches(db, case_nos, lambda batch: select(BusinessRecord).where(
        BusinessRecord.module == "finance", BusinessRecord.data["case_no"].as_string().in_(batch), *scope)))
    candidates = list({fee.id: fee for fee in candidates}.values())
    fees_by_case = {}
    for fee in candidates:
        fees_by_case.setdefault(str((fee.data or {}).get("case_no") or ""), []).append(fee)
    unambiguous = await unambiguous_fee_case_nos(case_nos, db)
    native_ids, legacy_ids = _case_fee_link_maps(candidates)
    candidates_by_id = {fee.id: fee for fee in candidates}
    for allocation in allocations:
        case_no = str(allocation.get("case_no") or "").strip()
        for link in allocation.get("settlement_items") or [allocation]:
            if link.get("amount") is None and link.get("settlement_amount") is None:
                raise HTTPException(409, "回款分配金额未映射完整，不能生成到账模板")
            fee_id = _resolve_case_fee_link_id(link, native_ids, legacy_ids)
            if not fee_id:
                fee_id = int(link.get("finance_record_id") or 0)
            explicit = any(link.get(key) for key in ("fee_record_id", "fee_id", "legacy_case_fee_id", "legacy_fee_id", "finance_record_id"))
            if not explicit and case_no in unambiguous and len(fees_by_case.get(case_no, [])) == 1:
                fee_id = fees_by_case[case_no][0].id
            fee = candidates_by_id.get(fee_id)
            if not fee or (case_no and str((fee.data or {}).get("case_no") or "").strip() != case_no):
                raise HTTPException(409, "回款分配未找到唯一可见案件费用，不能生成到账模板")
    receipts = await read_fee_receipts(candidates, fees_by_case, unambiguous,
        db, filter_related=True, incoming=payments)
    mapped_payment_ids = {payment.id for parts in receipts.values() for payment, _amount in parts}
    if any(payment.allocations and payment.id not in mapped_payment_ids for payment in payments):
        raise HTTPException(409, "回款分配未找到唯一可见案件费用，不能生成到账模板")
    fee_ids = set(receipts)
    if not fee_ids:
        raise HTTPException(422, "当前回款尚无案件费用分配，不能生成到账费用模板")
    rows = await _invoice_case_fee_rows(identity, db, scope="company", ids=fee_ids, include_all_fee_types=True)
    if {row["id"] for row in rows} != fee_ids:
        raise HTTPException(409, "部分回款关联费用不存在或无权导出")
    for row in rows:
        scoped_receipts = receipts[row["id"]]
        data = row["data"]
        data["cashed_amount"] = float(sum((Decimal(str(amount)) for _payment, amount in scoped_receipts), Decimal(0))) if show_amount else None
        data["cashed_date"] = str(scoped_receipts[0][0].received_date)
        data["received_payer_name"] = joined(payment.payer_name for payment, _amount in scoped_receipts)
    values = await fee_export_values(rows, identity, db)
    filename = f"到账查询-{date.today()}.xls"
    return Response(content=render_rows("F27", values), media_type="application/vnd.ms-excel",
        headers={"Content-Disposition": f"attachment; filename=incoming-fees.xls; filename*=UTF-8''{quote(filename)}"})
