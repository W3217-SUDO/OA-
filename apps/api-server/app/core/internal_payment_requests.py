"""案件内部费用的显式请款登记，与生成提成及出纳付款分离。"""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BusinessRecord, FinanceTransaction, WorkflowEvent
from app.core.finance_batch_parity import is_internal_fee


async def submitted_internal_fee_ids(items: list[BusinessRecord], db: AsyncSession) -> set[int]:
    """历史创建提成自带单号不等于提交，实际审批、付款和申请事件仍保留。"""
    ids = {item.id for item in items}
    payment_actions = {"提交内部费用付款申请", "提交费用付款申请", "内部请款单撤回", "内部请款单回滚", "付款包核销"}
    review_actions = {"提交费用审批", "费用审批通过", "费用审批驳回", "内部提成退费审批通过", "内部提成退费审批驳回"}
    events = (await db.execute(select(WorkflowEvent.record_id, WorkflowEvent.action).where(
        WorkflowEvent.record_id.in_(ids), WorkflowEvent.action.in_(payment_actions | review_actions),
    ))).all() if ids else []
    by_id = {item.id: item for item in items}
    submitted = set()
    for record_id, action in events:
        data = by_id[record_id].data or {}
        # 普通费用审批不是付款申请；历史提成已存在整单身份且人工审批的，保留原单。
        if action in payment_actions or (data.get("commission_created_at") and (
            data.get("payment_application_no") or data.get("applicant")
        )):
            submitted.add(record_id)
    for item in items:
        data = item.data or {}
        if (data.get("internal_payment_submitted_at") or data.get("internal_application_id")
                or data.get("legacy_kind") == "internal_payment_line"
                or data.get("payment_package_id") or data.get("writeoff_status") == "已核销"
                or float(data.get("paid_amount") or 0) > 0
                or (not data.get("commission_created_at") and (
                    data.get("payment_application_no") or data.get("applicant") or data.get("payment_applied_at")))):
            submitted.add(item.id)
    return submitted


async def prepare_internal_payment_requests(fee_ids: list[int], identity: dict, db: AsyncSession, *, lock: bool) -> tuple[list[BusinessRecord], set[int]]:
    from app.core.permissions import _record_scope_conditions, _require_record_owner_or_manager
    from app.areas.finance.fee_action_guards import _require_linked_case_fee_action

    if not fee_ids or len(set(fee_ids)) != len(fee_ids):
        raise HTTPException(422, "请选择不重复的内部费用")
    statement = select(BusinessRecord).where(
        BusinessRecord.module == "finance", BusinessRecord.id.in_(fee_ids),
        *(await _record_scope_conditions(identity, db)),
    ).order_by(BusinessRecord.id)
    if lock:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    rows = list((await db.scalars(statement)).all())
    if len(rows) != len(fee_ids):
        raise HTTPException(404, "部分费用不存在或无权访问")
    if any(not is_internal_fee(item.data or {}) for item in rows):
        raise HTTPException(422, "仅可选择内部费用")
    cases = {(item.data or {}).get("case_id") or (item.data or {}).get("case_record_id") or (item.data or {}).get("case_no") for item in rows}
    if len(cases) != 1 or not next(iter(cases)):
        raise HTTPException(409, "请选择同一案件的内部费用")
    for item in rows:
        if (item.data or {}).get("commission_created_by") != identity["username"]:
            await _require_record_owner_or_manager(item, identity, db)
        await _require_linked_case_fee_action(item, "case.fee.payment", identity, db)
    if lock:
        from app.core.case_fee_payments import lock_case_fee_rows
        rows = await lock_case_fee_rows(fee_ids, db)
    return rows, await submitted_internal_fee_ids(rows, db)


async def register_internal_payment_requests(lines: list, comment: str, identity: dict, db: AsyncSession) -> dict:
    """先校验全部明细，再一次提交；未结算、未归档仍由原生命周期决定状态。"""
    from app.core.finance import _new_internal_payment_package_no, _round_fee_amount, _sync_case_commission_lifecycle

    rows, submitted = await prepare_internal_payment_requests([line.fee_id for line in lines], identity, db, lock=True)
    if submitted:
        raise HTTPException(409, "所选费用已有请款申请，请查看原请款单")
    paid_ids = set((await db.scalars(select(FinanceTransaction.finance_record_id).where(
        FinanceTransaction.finance_record_id.in_([item.id for item in rows]),
        FinanceTransaction.transaction_type == "付款",
    ))).all())
    by_id = {line.fee_id: line for line in lines}
    allowed = {"草稿", "已退回", "待到账", "待分配", "待结算", "待归档", "待审批", "已审批"}
    for item in rows:
        data, line = item.data or {}, by_id[item.id]
        if item.status not in allowed or item.id in paid_ids or float(data.get("paid_amount") or 0) > 0 or data.get("writeoff_status") == "已核销":
            raise HTTPException(409, f"费用 {item.serial_no} 当前不能申请付款")
        if not line.payment_payee.strip() or not line.payment_account.strip():
            raise HTTPException(422, "请输入每笔内部费用的收款人和付款账号")
        total = _round_fee_amount(float(data.get("amount") or 0))
        if total <= 0 or abs(_round_fee_amount(line.amount) - total) > .001:
            raise HTTPException(409, f"费用 {item.serial_no} 申请金额必须等于当前费用金额")
    # 来源事实同步不能把尚未归档的普通提成直接送进审核队列。
    lifecycle = await _sync_case_commission_lifecycle(rows, db, operator=identity["username"])
    now = datetime.now().isoformat(timespec="seconds")
    numbers = {}
    for item in rows:
        data, line = item.data or {}, by_id[item.id]
        key = (data.get("source_fee_id"), bool(data.get("is_refund")), data.get("commission_lifecycle", ""))
        if key not in numbers:
            numbers[key] = _new_internal_payment_package_no()
        number = numbers[key]
        previous = item.status
        target = lifecycle.get(item.id, "待审批")
        item.status = target
        item.data = {
            **data, "payment_application_no": number, "applicant": identity["username"],
            "application_date": now[:10], "payment_requested_amount": _round_fee_amount(line.amount),
            "internal_payment_submitted_at": now, "internal_payment_submitted": True, "payment_applied_at": now,
            "payment_applied_by": identity["username"], "payment_status": target,
            "payment_payee": line.payment_payee.strip(), "payment_account": line.payment_account.strip(),
            "payment_remark": line.payment_remark.strip(),
        }
        db.add(WorkflowEvent(record_id=item.id, action="提交内部费用付款申请", from_status=previous,
                             to_status=target, operator=identity["username"], comment=line.payment_remark.strip() or comment.strip()))
    await db.commit()
    return {"application_no": next(iter(numbers.values())), "application_numbers": list(numbers.values()), "fee_ids": [item.id for item in rows], "submitted": len(rows)}
