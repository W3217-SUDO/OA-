"""财务费用流程接口。"""
from fastapi import APIRouter
from app.core.constants import FINANCE_PAYMENT_CANCELABLE_STATUSES, FINANCE_PAYMENT_ROLLBACKABLE_STATUSES, REFUND_CASE_FEE_STATUSES
from app.core.dependencies import AsyncSession, BusinessRecord, Depends, FinanceTransaction, HTTPException, WorkflowEvent, current_identity, datetime, func, get_db, select, settings, status
from app.models_shared import FinanceActionInput, FinanceFeeBatchReviewInput, FinanceFeeReviewInput, FinancePaymentCancelInput, FinancePaymentRollbackInput, FinancePaymentTypeCreateInput, FinanceWriteoffInput
from app.areas.finance.fee_action_guards import _is_internal_application as _is_internal_application, _require_non_internal_application_action as _require_non_internal_application_action, _require_linked_case_fee_action as _require_linked_case_fee_action

router = APIRouter()


@router.get(f"{settings.api_prefix}/finance/fees/{{fee_id}}/readiness")
async def finance_fee_readiness(fee_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _finance_fee_readiness,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    item = await _ensure_record_module(fee_id, "finance", identity, db)
    return await _finance_fee_readiness(item, identity, db)

@router.post(f"{settings.api_prefix}/finance/fees/{{fee_id}}/cancel")
async def cancel_finance_payment(
    fee_id: int,
    body: FinancePaymentCancelInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _require_record_owner_or_manager,
    )
    item = await _ensure_record_module(fee_id, "finance", identity, db)
    _require_non_internal_application_action(item)
    await _require_record_owner_or_manager(item, identity, db)
    await _require_linked_case_fee_action(item, "case.fee.payment", identity, db)
    from app.core.case_fee_payments import lock_case_fee_rows, release_direct_fee_request
    from app.core.invoice_sources import is_external_case_fee
    if is_external_case_fee(item):
        item = (await lock_case_fee_rows([item.id], db))[0]
    if item.status not in FINANCE_PAYMENT_CANCELABLE_STATUSES:
        raise HTTPException(status_code=409, detail="当前付款申请状态不能撤回")
    reason = body.reason.strip()
    if not reason:
        raise HTTPException(status_code=422, detail="请输入撤回原因")
    previous = item.status
    changed_at = datetime.now().isoformat(timespec="seconds")
    if is_external_case_fee(item):
        await release_direct_fee_request(item, db)
    item.status = "已撤回"
    item.data = {
        **(item.data or {}),
        "cancel_reason": reason,
        "canceled_by": identity["username"],
        "canceled_at": changed_at,
    }
    db.add(WorkflowEvent(
        record_id=item.id,
        action="付款申请撤回",
        from_status=previous,
        to_status=item.status,
        operator=identity["username"],
        comment=reason,
    ))
    await db.commit()
    await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)

@router.post(f"{settings.api_prefix}/finance/fees/{{fee_id}}/rollback")
async def rollback_finance_payment(
    fee_id: int,
    body: FinancePaymentRollbackInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有付款回滚权限")
    item = await _ensure_record_module(fee_id, "finance", identity, db)
    _require_non_internal_application_action(item)
    await _require_linked_case_fee_action(item, "case.fee.payment", identity, db)
    from app.core.case_fee_payments import lock_case_fee_rows, release_direct_fee_request
    from app.core.invoice_sources import is_external_case_fee
    if is_external_case_fee(item):
        item = (await lock_case_fee_rows([item.id], db))[0]
    if item.status not in FINANCE_PAYMENT_ROLLBACKABLE_STATUSES:
        raise HTTPException(status_code=409, detail="当前付款申请状态不能回滚")
    previous = item.status
    changed_at = datetime.now().isoformat(timespec="seconds")
    comment = body.comment.strip()
    if is_external_case_fee(item):
        await release_direct_fee_request(item, db)
    item.status = "草稿"
    item.data = {
        **(item.data or {}),
        "rollback_comment": comment,
        "rolled_back_by": identity["username"],
        "rolled_back_at": changed_at,
    }
    db.add(WorkflowEvent(
        record_id=item.id,
        action="付款申请回滚",
        from_status=previous,
        to_status=item.status,
        operator=identity["username"],
        comment=comment,
    ))
    await db.commit()
    await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)

@router.get(f"{settings.api_prefix}/finance/fees/{{fee_id}}/payment-types")
async def list_finance_fee_payment_types(
    fee_id: int,
    keyword: str = "",
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _active_payment_type_rows, _finance_payment_type_for_fee,
    )
    await _finance_payment_type_for_fee(fee_id, identity, db)
    return {"items": await _active_payment_type_rows(db, keyword)}

@router.post(f"{settings.api_prefix}/finance/fees/{{fee_id}}/payment-types", status_code=status.HTTP_201_CREATED)
async def create_finance_fee_payment_type(
    fee_id: int,
    body: FinancePaymentTypeCreateInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _create_payment_type, _finance_payment_type_dict, _finance_payment_type_for_fee,
    )
    fee = await _finance_payment_type_for_fee(fee_id, identity, db)
    item = await _create_payment_type(body, identity, db, {"fee_id": fee.id, "fee_no": fee.serial_no})
    return _finance_payment_type_dict(item)

@router.post(f"{settings.api_prefix}/finance/fees/{{fee_id}}/submit")
async def submit_finance_fee(fee_id: int, body: FinanceActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _active_contract_payment_fee_reservations, _active_payment_type, _finance_fee_readiness, _finance_payment_type_dict, _round_fee_amount,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _require_record_owner_or_manager,
    )
    item = await _ensure_record_module(fee_id, "finance", identity, db)
    if _is_internal_application(item):
        if body.amount is not None:
            raise HTTPException(409, "内部请款单付款申请不能按单笔费用提交")
        from app.core.internal_requests import submit_internal_application

        return await submit_internal_application(fee_id, body.comment, identity, db)
    await _require_record_owner_or_manager(item, identity, db)
    is_payment_request = body.amount is not None
    if is_payment_request:
        from app.core.case_fee_payments import lock_case_fee_rows
        item = (await lock_case_fee_rows([item.id], db))[0]
    await _require_linked_case_fee_action(
        item, "case.fee.payment" if is_payment_request else "case.fee.update", identity, db,
    )
    allowed_statuses = {"草稿", "已退回", "已审批", "部分付款"} if is_payment_request else {"草稿", "已退回"}
    from app.core.invoice_sources import is_external_case_fee
    if is_payment_request and is_external_case_fee(item):
        allowed_statuses |= {"已驳回", "已撤回"}
    if item.status not in allowed_statuses:
        raise HTTPException(status_code=409, detail="当前状态不能申请付款" if is_payment_request else "当前状态不能提交审批")
    data = item.data or {}
    if not is_payment_request:
        commission_missing = []
        if data.get("fee_type") == "代理费" and data.get("commission_mode") == "automatic":
            commission_missing = [
                str(message).strip()
                for message in (data.get("commission_missing_messages") or [])
                if str(message).strip()
            ]
        if commission_missing:
            raise HTTPException(
                status_code=422,
                detail="自动提成缺少人员或有效提成方案：" + "、".join(commission_missing),
            )
        missing = []
        if not data.get("handler"): missing.append("经办人员")
        if not data.get("case_no"): missing.append("关联案号")
        if data.get("fee_type") == "官方费用":
            if not data.get("court"): missing.append("缴费法院/机构")
            if not data.get("document_no"): missing.append("缴费通知文号")
        if missing: raise HTTPException(status_code=422, detail="缺少费用审批要素：" + "、".join(missing))
        if data.get("fee_type") == "官方费用":
            readiness = await _finance_fee_readiness(item, identity, db)
            if not readiness["ready"]: raise HTTPException(status_code=422, detail="案件付款三要素不完整：" + "；".join(readiness["missing"]))
    if body.amount is not None:
        payment_type = None
        if data.get("expense_scope") != "内部" and data.get("fee_type") != "内部费用":
            if not body.payment_type_id and data.get("fee_type") != "官方费用":
                raise HTTPException(status_code=422, detail="请选择系统付款单位")
            payment_type = await _active_payment_type(body.payment_type_id, db) if body.payment_type_id else None
            payment_type_data = _finance_payment_type_dict(payment_type) if payment_type else {}
            payee = payment_type_data.get("payee", "")
            account = payment_type_data.get("account", "")
        else:
            account = body.payment_account.strip()
            if not account:
                raise HTTPException(status_code=422, detail="请输入付款账号")
            payee = body.payment_payee.strip()
            if not payee:
                raise HTTPException(status_code=422, detail="请输入收款单位")
        payment_remark = body.payment_remark.strip()
        requested = _round_fee_amount(body.amount)
        paid = _round_fee_amount(float(await db.scalar(select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(
            FinanceTransaction.finance_record_id == item.id,
            FinanceTransaction.transaction_type == "付款",
        )) or 0))
        previous_requested = _round_fee_amount(float(data.get("payment_requested_amount") or 0))
        contract_reserved = (await _active_contract_payment_fee_reservations({item.id}, db)).get(item.id, 0)
        # 已付与直接申请是同一申请生命周期，不能相加重复扣减。
        remaining = _round_fee_amount(abs(float(data.get("amount") or 0)) - max(paid, float(data.get("paid_amount") or 0), previous_requested) - contract_reserved)
        if requested > remaining + 0.001:
            raise HTTPException(status_code=409, detail=f"申请付款金额不能超过未付款金额 {remaining:.2f}")
        applied_at = datetime.now().isoformat(timespec="seconds")
        previous = item.status
        item.status = "待审批"
        item.data = {
            **data,
            "payment_requested_amount": _round_fee_amount(max(previous_requested, paid, float(data.get("paid_amount") or 0)) + requested),
            **({"payment_request_amount": requested, "writeoff_status": "", "payment_package_id": None,
                "payment_package_no": "", "payment_package_amount": None} if payment_type or data.get("fee_type") == "官方费用" else {}),
            "payment_account": account,
            "payment_payee": payee,
            "payment_type_id": payment_type.id if payment_type else None,
            "payment_type_code": payment_type.code if payment_type else "",
            "payment_type_name": payment_type.name if payment_type else "",
            "payment_nature": str((payment_type.extra or {}).get("nature") or payment_type.name or "") if payment_type else "",
            "payment_account_bank": str((payment_type.extra or {}).get("account_bank") or (payment_type.extra or {}).get("bank") or "") if payment_type else "",
            "payment_remark": payment_remark,
            "payee": payee,
            "payment_applied_at": applied_at,
            "payment_applied_by": identity["username"],
            "payment_status": "待审批",
        }
        db.add(WorkflowEvent(record_id=item.id, action="提交费用付款申请", from_status=previous, to_status="待审批", operator=identity["username"], comment=payment_remark or body.comment.strip() or f"申请付款 {requested:.2f} 元"))
        await db.commit(); await db.refresh(item)
        return await _record_dict_for_identity(item, identity, db)
    previous = item.status; item.status = "待审批"
    db.add(WorkflowEvent(record_id=item.id, action="提交费用审批", from_status=previous, to_status="待审批", operator=identity["username"], comment=body.comment))
    await db.commit(); await db.refresh(item); return await _record_dict_for_identity(item, identity, db)

@router.post(f"{settings.api_prefix}/finance/fees/{{fee_id}}/mark-no-payment")
async def mark_finance_fee_no_payment(fee_id: int, body: FinanceActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _require_record_owner_or_manager,
    )
    item = await _ensure_record_module(fee_id, "finance", identity, db)
    await _require_record_owner_or_manager(item, identity, db)
    await _require_linked_case_fee_action(item, "case.fee.mark_unpaid", identity, db)
    if item.status not in {"草稿", "已退回"}:
        raise HTTPException(status_code=409, detail="仅草稿或已退回费用可以标记不缴费")
    previous = item.status
    changed_at = datetime.now().isoformat(timespec="seconds")
    item.status = "不缴费"
    item.data = {
        **(item.data or {}),
        "payment_status": "不缴费",
        "no_payment_comment": body.comment.strip(),
        "no_payment_by": identity["username"],
        "no_payment_at": changed_at,
    }
    db.add(WorkflowEvent(
        record_id=item.id,
        action="案件费用标记不缴费",
        from_status=previous,
        to_status="不缴费",
        operator=identity["username"],
        comment=body.comment.strip() or "案件费用标记不缴费",
    ))
    await db.commit()
    await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)

@router.post(f"{settings.api_prefix}/finance/fees/{{fee_id}}/mark-refund-not-required")
async def mark_finance_fee_refund_not_required(fee_id: int, body: FinanceActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _editable_refund_case_fees, _receivable_number, _refund_case_fee_status,
    )
    from app.core.permissions import (
        _permission_payload_for_identity, _record_dict_for_identity,
    )
    if identity.get("role") not in {"admin", "manager"}:
        permission = await _permission_payload_for_identity(identity, db)
        if "*" not in permission.get("action_keys", []) and "finance.refund.not_required" not in permission.get("action_keys", []):
            raise HTTPException(status_code=403, detail="当前角色没有标记不再办理退费的权限")
    item = (await _editable_refund_case_fees([fee_id], identity, db))[0]
    await _require_linked_case_fee_action(item, "case.fee.refund", identity, db)
    data = dict(item.data or {})
    previous_code, previous_label = _refund_case_fee_status(data)
    if previous_code == "R100":
        raise HTTPException(status_code=409, detail="该费用已标记为不再办理退费")
    legacy = data.get("legacy_record") if isinstance(data.get("legacy_record"), dict) else {}
    has_explicit_refund_status = any(
        value is not None and str(value).strip()
        for value in (data.get("refund_status"), data.get("refund_status_label"), legacy.get("RefundStatus"))
    )
    has_refund_amount = any(
        _receivable_number(data.get(field)) > 0
        for field in ("refund_requested_amount", "refund_amount", "refunded_amount")
    )
    if not has_explicit_refund_status and not has_refund_amount:
        raise HTTPException(status_code=409, detail="仅有退费记录的费用可以标记不再办理退费")
    changed_at = datetime.now().isoformat(timespec="seconds")
    comment = body.comment.strip()
    item.data = {
        **data,
        "refund_status": "R100",
        "refund_status_label": REFUND_CASE_FEE_STATUSES["R100"],
        "refund_status_started_at": changed_at,
        "refund_not_required": True,
        "refund_not_required_comment": comment,
        "refund_not_required_by": identity["username"],
        "refund_not_required_at": changed_at,
    }
    db.add(WorkflowEvent(
        record_id=item.id,
        action="标记不再办理退费",
        from_status=previous_label,
        to_status=REFUND_CASE_FEE_STATUSES["R100"],
        operator=identity["username"],
        comment=comment or "案件费用标记不再办理退费",
    ))
    await db.commit()
    await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)

@router.post(f"{settings.api_prefix}/finance/fees/{{fee_id}}/approve")
async def approve_finance_fee(fee_id: int, body: FinanceActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _review_finance_fee_records,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    item = await _ensure_record_module(fee_id, "finance", identity, db)
    _require_non_internal_application_action(item)
    await _review_finance_fee_records([item], True, body.comment, identity, db)
    await db.commit(); await db.refresh(item); return await _record_dict_for_identity(item, identity, db)

@router.post(f"{settings.api_prefix}/finance/fees/batch-review")
async def batch_review_finance_fees(body: FinanceFeeBatchReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _review_finance_fee_records,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    fee_ids = list(dict.fromkeys(body.fee_ids))
    items = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(fee_ids),
        BusinessRecord.module == "finance",
        *(await _record_scope_conditions(identity, db)),
    ))).all()
    if len(items) != len(fee_ids):
        raise HTTPException(status_code=404, detail="部分费用不存在或无权访问")
    for item in items:
        _require_non_internal_application_action(item)
    await _review_finance_fee_records(items, body.approved, body.comment, identity, db)
    await db.commit()
    return {"reviewed": len(items), "fee_ids": fee_ids, "status": "已审批" if body.approved else "已驳回"}

@router.post(f"{settings.api_prefix}/finance/fees/{{fee_id}}/review")
async def review_finance_fee(fee_id: int, body: FinanceFeeReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _review_finance_fee_records,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    item = await _ensure_record_module(fee_id, "finance", identity, db)
    _require_non_internal_application_action(item)
    await _review_finance_fee_records([item], body.approved, body.comment, identity, db)
    await db.commit(); await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)

@router.post(f"{settings.api_prefix}/finance/fees/{{fee_id}}/void")
async def void_rejected_finance_fee(fee_id: int, body: FinanceActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有请款单作废权限")
    item = await _ensure_record_module(fee_id, "finance", identity, db)
    data = item.data or {}
    if data.get("fee_type") != "内部费用":
        raise HTTPException(status_code=409, detail="该入口仅可作废内部费用请款单")
    if _is_internal_application(item):
        from app.core.internal_requests import void_internal_application

        return await void_internal_application(fee_id, body.comment, identity, db)
    if item.status not in {"已拒绝", "已退回", "已驳回"}:
        raise HTTPException(status_code=409, detail="仅已拒绝的内部费用请款单可以作废")
    previous = item.status
    voided_at = datetime.now().isoformat(timespec="seconds")
    item.status = "已作废"
    item.data = {
        **data,
        "payment_status": "已作废",
        "voided_by": identity["username"],
        "voided_at": voided_at,
        "void_comment": body.comment.strip(),
    }
    db.add(WorkflowEvent(
        record_id=item.id,
        action="请款单作废",
        from_status=previous,
        to_status="已作废",
        operator=identity["username"],
        comment=body.comment.strip() or "已拒绝请款单作废",
    ))
    await db.commit(); await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)

@router.post(f"{settings.api_prefix}/finance/fees/{{fee_id}}/writeoff")
async def writeoff_finance_fee(fee_id: int, body: FinanceWriteoffInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有付款核销权限")
    item = await _ensure_record_module(fee_id, "finance", identity, db)
    if item.status != "已付款":
        raise HTTPException(status_code=409, detail="费用全部付款后才能核销")
    data = item.data or {}
    if data.get("writeoff_status") == "已核销":
        raise HTTPException(status_code=409, detail="付款已经核销")
    payment_total = float(await db.scalar(select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(FinanceTransaction.finance_record_id == item.id, FinanceTransaction.transaction_type == "付款")) or 0)
    if payment_total + 0.001 < abs(float(data.get("amount", 0) or 0)):
        raise HTTPException(status_code=409, detail="付款流水合计未达到申请金额，不能核销")
    item.data = {
        **data,
        "payment_status": "已付款",
        "writeoff_status": "已核销",
        "writeoff_voucher_no": body.voucher_no.strip(),
        "writeoff_comment": body.comment.strip(),
        "written_off_by": identity["username"],
        "written_off_at": datetime.now().isoformat(timespec="seconds"),
    }
    db.add(WorkflowEvent(record_id=item.id, action="付款核销", from_status=item.status, to_status=item.status, operator=identity["username"], comment=f"核销凭证：{body.voucher_no.strip()}。{body.comment}"))
    await db.commit(); await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)
