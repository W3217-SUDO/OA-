"""法院退费与律所代理费退款费用在同一事务中保存。"""
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select
from app.models import BusinessRecord, SystemParameter, WorkflowEvent


async def create_agency_refund_fee(refund, source, identity, db):
    fee_type = await db.scalar(select(SystemParameter).where(
        SystemParameter.category == "fee_type", SystemParameter.code == "AGENCY-REFUND",
        SystemParameter.is_active.is_(True)))
    if not fee_type:
        raise HTTPException(422, "律师代理费（退费）费用类型未启用，请先维护费用类型")
    original = source.data or {}
    data = {key: original[key] for key in ("case_id", "case_record_id", "case_no", "contract_id", "contract_record_id", "contract_no") if key in original}
    data.update(fee_type="代理费", fee_type_id=fee_type.id, expense_subtype=fee_type.name,
        expense_scope="律所", amount=refund.data["amount"], source_fee_id=source.id,
        refund_record_id=refund.id, handler=identity["username"], refund_fee=True)
    fee = BusinessRecord(module="finance", serial_no=f"FYTF{datetime.now():%Y%m%d%H%M%S%f}",
        title=fee_type.name, customer=source.customer, status="草稿", owner=identity["username"],
        department=source.department, description=refund.description, data=data)
    db.add(fee)
    await db.flush()
    refund.data = {**refund.data, "refund_fee_id": fee.id}
    db.add(WorkflowEvent(record_id=fee.id, action="代理费法院退费生成费用", to_status=fee.status,
        operator=identity["username"], comment=f"来源费用：{source.serial_no}；退款申请：{refund.serial_no}"))
    return fee


async def update_agency_refund_fee_amount(refund, amount, db):
    fee_id = (refund.data or {}).get("refund_fee_id")
    if not fee_id:
        return
    fee = await db.scalar(select(BusinessRecord).where(BusinessRecord.id == fee_id).with_for_update())
    if not fee or fee.module != "finance" or (fee.data or {}).get("refund_record_id") != refund.id:
        raise HTTPException(409, "关联的代理费退费记录不存在或关联不一致")
    data = dict(fee.data or {})
    if fee.status != "草稿" or float(data.get("payment_requested_amount") or 0) or float(data.get("paid_amount") or 0):
        raise HTTPException(409, "关联代理费退费已进入付款流程，不能修改退款金额")
    fee.data = {**data, "amount": round(amount, 2)}
