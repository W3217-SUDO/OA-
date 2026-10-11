"""维护导入内部请款明细与原费用之间的已付金额关联。"""

from datetime import date

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BusinessRecord, FinanceTransaction


async def adjust_imported_internal_paid(
    line: BusinessRecord,
    amount: float,
    db: AsyncSession,
    *,
    transaction_date: date | None = None,
    operator: str = "",
    voucher_no: str = "",
) -> None:
    data = line.data or {}
    if data.get("legacy_kind") != "internal_payment_line":
        return
    source_id = data.get("internal_fee_record_id")
    if not source_id:
        raise HTTPException(409, f"请款明细 {line.serial_no} 缺少原费用关联")
    source = await db.get(BusinessRecord, int(source_id), with_for_update=True)
    if not source or source.module != "finance" or (source.data or {}).get("legacy_kind") != "internal_fee_source":
        raise HTTPException(409, f"请款明细 {line.serial_no} 的原费用关联无效")
    if (source.data or {}).get("case_id") != data.get("case_id"):
        raise HTTPException(409, f"请款明细 {line.serial_no} 与原费用不属于同一案件")
    current_paid = float((source.data or {}).get("paid_amount") or 0)
    source.data = {**(source.data or {}), "paid_amount": round(current_paid + amount, 2)}
    if transaction_date is not None:
        db.add(FinanceTransaction(
            finance_record_id=source.id,
            transaction_type="付款",
            amount=round(amount, 2),
            transaction_date=transaction_date,
            voucher_no=voucher_no[:64],
            counterparty=str(data.get("payee") or ""),
            operator=operator,
            remark=f"内部请款明细 {line.serial_no}" + ("；付款冲正" if amount < 0 else ""),
        ))
