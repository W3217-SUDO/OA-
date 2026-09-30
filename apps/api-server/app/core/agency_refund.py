"""法院退费与律所代理费退款费用在同一事务中保存。"""
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select
from app.models import BusinessRecord, FinanceTransaction, SystemParameter, WorkflowEvent


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


async def reset_case_court_refunds(source, identity, db):
    """仅在未发生真实收付时归零法院退费，并逻辑删除对应派生费用。"""
    if float((source.data or {}).get("refunded_amount") or 0) > 0:
        raise HTTPException(409, "法院退费已有到账金额，不能归零")
    refunds = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "refund",
        BusinessRecord.data["fee_record_id"].as_integer() == source.id,
        BusinessRecord.status.not_in({"已驳回", "已作废"}),
    ).order_by(BusinessRecord.id).with_for_update())).all())
    linked_fees = []
    linked_commissions = []
    for refund in refunds:
        if refund.status != "草稿":
            raise HTTPException(409, "退款申请已进入审批或到账流程，请先撤回后再归零")
        fee_id = (refund.data or {}).get("refund_fee_id")
        if not fee_id:
            continue
        fee = await db.scalar(select(BusinessRecord).where(BusinessRecord.id == fee_id).with_for_update())
        if not fee or fee.module != "finance" or (fee.data or {}).get("refund_record_id") != refund.id:
            raise HTTPException(409, "关联代理费退费记录不存在或关联不一致")
        data = fee.data or {}
        if fee.status not in {"草稿", "待审批", "已审批", "待付款", "已撤回"}:
            raise HTTPException(409, "关联代理费退费已进入付款或结算流程，不能归零")
        if data.get("payment_package_id") or data.get("payment_package_no") or float(data.get("paid_amount") or 0):
            raise HTTPException(409, "关联代理费退费已进入付款包或付款流程，不能归零")
        active_children = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "finance",
            BusinessRecord.data["source_fee_id"].as_integer() == fee.id,
            BusinessRecord.status.not_in({"已删除", "已作废", "已撤回"}),
        ).with_for_update())).all())
        for child in active_children:
            child_data = child.data or {}
            if child.status not in {"草稿", "待结算", "待审批", "已退回", "已驳回"}:
                raise HTTPException(409, "关联代理费退费的提成已进入结算或付款流程，不能归零")
            if child_data.get("payment_package_id") or child_data.get("payment_package_no") or float(child_data.get("paid_amount") or 0):
                raise HTTPException(409, "关联代理费退费的提成已有付款，不能归零")
            linked_commissions.append(child)
        linked_fees.append(fee)
    linked_ids = [item.id for item in (*refunds, *linked_fees, *linked_commissions)]
    if linked_ids and await db.scalar(select(FinanceTransaction.id).where(FinanceTransaction.finance_record_id.in_(linked_ids))):
        raise HTTPException(409, "关联退费或代理费退费已有财务流水，不能归零")
    from app.core.case_fee_payments import release_direct_fee_request
    from app.core.constants import INVOICE_RELEASED_STATUSES
    from app.core.finance import _invoice_json_fee_condition, _invoice_linked_fee_ids
    derivative_ids = {item.id for item in linked_fees}
    contract_payments = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "contract_payment",
        BusinessRecord.status.not_in({"已撤回", "已驳回", "已拒绝", "已作废", "已删除"}),
        _invoice_json_fee_condition(BusinessRecord.data, derivative_ids),
    ).with_for_update())).all()
    for payment in contract_payments:
        for line in (payment.data or {}).get("lines") or []:
            if (isinstance(line, dict) and str(line.get("case_fee_id") or "").isdigit()
                    and int(line["case_fee_id"]) in derivative_ids):
                raise HTTPException(409, "关联代理费退费已有合同付款申请，不能归零")
    invoices = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "invoice",
        BusinessRecord.status.not_in(INVOICE_RELEASED_STATUSES),
        _invoice_json_fee_condition(BusinessRecord.data, derivative_ids),
    ).with_for_update())).all()
    for invoice in invoices:
        data = invoice.data or {}
        allocation_ids = {int(row.get("fee_id")) for row in (data.get("case_fee_allocations") or [])
                          if isinstance(row, dict) and str(row.get("fee_id") or "").isdigit()}
        if derivative_ids & (_invoice_linked_fee_ids(data) | allocation_ids):
            raise HTTPException(409, "关联代理费退费已有开票申请，不能归零")
    changed_at = datetime.now().isoformat(timespec="seconds")
    for commission in linked_commissions:
        previous = commission.status
        commission.status = "已删除"
        commission.data = {**(commission.data or {}), "payment_requested_amount": 0,
            "payment_status": "已撤回", "refund_reset_by": identity["username"], "refund_reset_at": changed_at}
        db.add(WorkflowEvent(record_id=commission.id, action="法院退费归零撤销提成", from_status=previous,
            to_status=commission.status, operator=identity["username"], comment=f"来源费用：{source.serial_no}"))
    for fee in linked_fees:
        if fee.status != "草稿":
            await release_direct_fee_request(fee, db)
        previous = fee.status
        fee.status = "已删除"
        fee.data = {**(fee.data or {}), "payment_status": "已撤回", "refund_reset_by": identity["username"], "refund_reset_at": changed_at}
        db.add(WorkflowEvent(record_id=fee.id, action="法院退费归零撤销派生费用", from_status=previous,
            to_status=fee.status, operator=identity["username"], comment=f"来源费用：{source.serial_no}"))
    for refund in refunds:
        previous = refund.status
        refund.status = "已作废"
        refund.data = {**(refund.data or {}), "refund_reset_by": identity["username"], "refund_reset_at": changed_at}
        db.add(WorkflowEvent(record_id=refund.id, action="法院退费金额归零", from_status=previous,
            to_status=refund.status, operator=identity["username"], comment=f"来源费用：{source.serial_no}"))
    source.data = {**(source.data or {}), "refund_requested_amount": 0, "refund_amount": 0,
        "refund_reset_by": identity["username"], "refund_reset_at": changed_at}
    db.add(WorkflowEvent(record_id=source.id, action="法院退费金额归零", from_status=source.status,
        to_status=source.status, operator=identity["username"], comment=f"撤销未结算退费 {len(refunds)} 条"))
    return len(refunds)
