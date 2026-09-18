"""案件费用维护的账务限制，金额取已授权费用的真实关联投影。"""
from fastapi import HTTPException


async def require_unsettled_fee(fee, identity, db):
    from app.core.finance import _invoice_case_fee_rows
    rows = await _invoice_case_fee_rows(identity, db, scope="company", ids={fee.id},
        scope_authorized_fee_ids={fee.id}, include_all_fee_types=True, force_amount_projection=True)
    if len(rows) != 1:
        raise HTTPException(409, "无法核实费用账务状态，不能修改或删除")
    projected = rows[0]["data"]
    data = fee.data or {}
    restrictions = (
        (("cashed_amount", "received_amount"), "请先撤销到账分配"),
        (("invoice_amount", "invoiced_amount"), "请先作废关联发票"),
        (("paid_amount",), "请先取消付款"),
    )
    for fields, message in restrictions:
        if any(abs(float(source.get(field) or 0)) > 0 for field in fields for source in (projected, data)):
            raise HTTPException(409, message)
