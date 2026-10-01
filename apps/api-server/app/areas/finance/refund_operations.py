"""按独立业务职责组织的路由，注册顺序与端点行为保持稳定。"""
from app.areas.finance.fee_action_guards import (
    _require_linked_case_fee_action,
)
from app.core.constants import (
    REFUND_PAGE_SIZES,
)
from app.core.dependencies import (
    AsyncSession,
    BusinessRecord,
    Depends,
    FinanceTransaction,
    HTTPException,
    Query,
    User,
    WorkflowEvent,
    current_identity,
    datetime,
    get_db,
    select,
    settings,
    status,
)
from app.models_shared import (
    FinanceActionInput,
    FinanceReviewInput,
    LitigationRefundInput,
    RefundAmountUpdateInput,
    RefundBatchStatusInput,
    RefundCompleteInput,
)
from fastapi import APIRouter

router = APIRouter()

@router.get(f"{settings.api_prefix}/finance/refunds/query")
async def query_refund_applications(
    status_filter: str = Query("", alias="status"), group: str = "", scope: str = Query("company", pattern="^(mine|company)$"),
    page: int = Query(1, ge=1), page_size: int = Query(15, ge=10, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _refund_query_rows,
    )
    if page_size not in REFUND_PAGE_SIZES:
        raise HTTPException(status_code=422, detail="退款列表页长必须为 10、15、20、50、100 或 200")
    rows = await _refund_query_rows(identity, db, status_filter=status_filter, group=group, scope=scope)
    start = (page - 1) * page_size
    total = len(rows)
    return {"items": rows[start:start + page_size], "total": total, "page": page, "page_size": page_size, "pages": (total + page_size - 1) // page_size if total else 0}


@router.get(f"{settings.api_prefix}/finance/refunds/export")
async def export_refund_applications(
    status_filter: str = Query("", alias="status"), group: str = "", scope: str = Query("company", pattern="^(mine|company)$"),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _refund_export_request,
    )
    return await _refund_export_request(ids="", selected_only=False, status_filter=status_filter, group=group, scope=scope, identity=identity, db=db)


@router.get(f"{settings.api_prefix}/finance/refunds/export-selected")
async def export_selected_refund_applications(
    ids: str = "", status_filter: str = Query("", alias="status"), group: str = "", scope: str = Query("company", pattern="^(mine|company)$"),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _refund_export_request,
    )
    return await _refund_export_request(ids=ids, selected_only=True, status_filter=status_filter, group=group, scope=scope, identity=identity, db=db)


@router.patch(f"{settings.api_prefix}/finance/refunds/{{refund_id}}/amount")
async def update_refund_amount(refund_id: int, body: RefundAmountUpdateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _round_fee_amount,
    )
    from app.core.permissions import (
        _ensure_record_visible, _ensure_refund_company_record, _record_dict_for_identity, _require_record_owner_or_manager,
    )
    item = await _ensure_refund_company_record(refund_id, identity, db)
    await _require_record_owner_or_manager(item, identity, db)
    if item.status not in {"草稿", "已驳回"}:
        raise HTTPException(status_code=409, detail="当前退款状态不能修改金额")
    data = dict(item.data or {})
    fee_id = int(data.get("fee_record_id") or 0)
    if fee_id:
        fee = await _ensure_record_visible(fee_id, identity, db)
        if fee.module != "finance":
            raise HTTPException(status_code=404, detail="关联费用不存在")
        original_amount = float((fee.data or {}).get("amount") or 0)
        if body.amount > original_amount:
            raise HTTPException(status_code=422, detail="退款金额不能超过原费用金额")
    if data.get("refund_fee_id"):
        from app.core.agency_refund import update_agency_refund_fee_amount
        other_refunds = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "refund", BusinessRecord.id != item.id,
            BusinessRecord.data["fee_record_id"].as_integer() == fee_id,
            BusinessRecord.status.not_in({"已驳回", "已作废"}),
        ))).all())
        if _round_fee_amount(body.amount + sum(float((row.data or {}).get("amount") or 0) for row in other_refunds)) > original_amount:
            raise HTTPException(422, "累计退款金额不能超过原费用金额")
        await update_agency_refund_fee_amount(item, body.amount, db)
    old_amount = float(data.get("amount") or 0)
    item.data = {**data, "amount": _round_fee_amount(body.amount), "amount_updated_by": identity["username"], "amount_updated_at": datetime.now().isoformat(timespec="seconds")}
    db.add(WorkflowEvent(record_id=item.id, action="修改退款金额", from_status=item.status, to_status=item.status, operator=identity["username"], comment=f"{old_amount:.2f} → {body.amount:.2f}；{body.comment}"))
    await db.commit(); await db.refresh(item)
    return await _record_dict_for_identity(item, identity, db)


@router.post(f"{settings.api_prefix}/finance/refunds/status")
async def batch_refund_status(body: RefundBatchStatusInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_refund_company_record, _record_dict_for_identity, _require_record_owner_or_manager,
    )
    ids = list(dict.fromkeys(body.ids))
    if body.status not in {"待审批", "退款办理中", "已驳回"}:
        raise HTTPException(status_code=422, detail="退款批量状态无效")
    items = [await _ensure_refund_company_record(record_id, identity, db) for record_id in ids]
    if body.status in {"退款办理中", "已驳回"} and identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有退款审批权限")
    for item in items:
        await _require_record_owner_or_manager(item, identity, db) if body.status == "待审批" else None
        allowed = {"待审批": {"草稿", "已驳回"}, "退款办理中": {"待审批"}, "已驳回": {"待审批"}}[body.status]
        if item.status not in allowed:
            raise HTTPException(status_code=409, detail=f"退款 {item.serial_no} 当前状态不能变更为 {body.status}")
    for item in items:
        previous = item.status; item.status = body.status
        db.add(WorkflowEvent(record_id=item.id, action="批量退款状态变更", from_status=previous, to_status=item.status, operator=identity["username"], comment=body.comment))
    await db.commit()
    for item in items:
        await db.refresh(item)
    return {"items": [await _record_dict_for_identity(item, identity, db) for item in items], "status": body.status, "count": len(items)}


@router.post(f"{settings.api_prefix}/finance/fees/{{fee_id}}/court-refund/reset")
async def reset_finance_fee_court_refund(fee_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.agency_refund import reset_case_court_refunds
    from app.core.permissions import _ensure_record_module, _record_dict_for_identity

    source = await _ensure_record_module(fee_id, "finance", identity, db)
    await _require_linked_case_fee_action(source, "case.fee.refund", identity, db)
    data = source.data or {}
    agency_fee = data.get("fee_type") == "代理费" and data.get("expense_scope") == "律所" and not data.get("refund_fee")
    if data.get("fee_type") != "官方费用" and not agency_fee:
        raise HTTPException(422, "法院退费只能关联官费或律所代理费")
    await db.scalar(select(BusinessRecord.id).where(BusinessRecord.id == source.id).with_for_update())
    await reset_case_court_refunds(source, identity, db)
    await db.commit()
    await db.refresh(source)
    return await _record_dict_for_identity(source, identity, db)


@router.post(f"{settings.api_prefix}/finance/refunds", status_code=status.HTTP_201_CREATED)
async def create_litigation_refund(body: LitigationRefundInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _finance_linked_case, _round_fee_amount,
    )
    from app.core.permissions import (
        _ensure_record_visible, _record_dict_for_identity,
    )
    case_record = await _finance_linked_case(body.case_no, identity, db)
    if not case_record: raise HTTPException(status_code=422, detail="诉讼费退款必须关联案件")
    fee_record = None
    agency_refund = False
    if body.fee_record_id:
        fee_record = await _ensure_record_visible(body.fee_record_id, identity, db)
        await db.scalar(select(BusinessRecord.id).where(BusinessRecord.id == fee_record.id).with_for_update())
        source_data = fee_record.data or {}
        agency_refund = source_data.get("fee_type") == "代理费" and str(source_data.get("expense_scope") or "律所") == "律所" and not source_data.get("refund_fee")
        if fee_record.module != "finance" or (source_data.get("fee_type") != "官方费用" and not agency_refund):
            raise HTTPException(status_code=422, detail="法院退费只能关联官费或律所代理费")
        if body.request_key:
            existing = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "refund", BusinessRecord.owner == identity["username"], BusinessRecord.data["fee_record_id"].as_integer() == fee_record.id, BusinessRecord.data["request_key"].as_string() == body.request_key))
            if existing:
                return await _record_dict_for_identity(existing, identity, db)
        if str((fee_record.data or {}).get("case_no") or "") != case_record.serial_no:
            raise HTTPException(status_code=409, detail="退款费用与案件不一致")
        original_amount = _round_fee_amount(abs(float((fee_record.data or {}).get("amount") or 0)))
        linked_refunds = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "refund",
            BusinessRecord.data["fee_record_id"].as_integer() == fee_record.id,
            ~BusinessRecord.status.in_({"已驳回", "已作废"}),
        ))).all())
        already_requested = _round_fee_amount(sum(float((refund.data or {}).get("amount") or 0) for refund in linked_refunds))
        if _round_fee_amount(body.amount) + already_requested > original_amount:
            raise HTTPException(status_code=422, detail="退款金额不能超过原费用金额")
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if not user: raise HTTPException(status_code=401, detail="当前用户不存在")
    serial = f"TF{datetime.now():%Y%m%d%H%M%S%f}"; data = body.model_dump(mode="json"); data["amount"] = _round_fee_amount(body.amount); data["case_id"] = case_record.id; data["case_record_id"] = case_record.id; data["case_no"] = case_record.serial_no
    item = BusinessRecord(module="refund", serial_no=serial, title=f"{body.case_no}{'代理费法院退费' if agency_refund else '诉讼费退款'}", customer=body.customer.strip(), status="草稿", owner=identity["username"], department=user.department, description=body.remark, data=data)
    db.add(item); await db.flush(); db.add(WorkflowEvent(record_id=item.id, action="创建诉讼费退款申请", to_status=item.status, operator=identity["username"], comment=f"{body.court}：{data['amount']:.2f} 元"))
    # 律所官费和代理费法院退费均生成同额代理费退费，保留原费用类型和退费流程。
    if fee_record and str((fee_record.data or {}).get("expense_scope") or "律所") == "律所":
        from app.core.agency_refund import create_agency_refund_fee
        await create_agency_refund_fee(item, fee_record, identity, db)
    await db.commit(); await db.refresh(item); return await _record_dict_for_identity(item, identity, db)


@router.post(f"{settings.api_prefix}/finance/refunds/{{refund_id}}/submit")
async def submit_litigation_refund(refund_id: int, body: FinanceActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_refund_company_record, _record_dict_for_identity, _require_record_owner_or_manager,
    )
    item = await _ensure_refund_company_record(refund_id, identity, db); await _require_record_owner_or_manager(item, identity, db)
    if item.status not in {"草稿", "已驳回"}: raise HTTPException(status_code=409, detail="当前退款申请不能提交")
    data = item.data or {}; required = {"法院": data.get("court"), "原缴费票号": data.get("original_payment_no"), "申请人": data.get("applicant")}
    missing = [name for name, value in required.items() if not value]
    if missing: raise HTTPException(status_code=422, detail="退款申请缺少：" + "、".join(missing))
    previous = item.status; item.status = "待审批"; db.add(WorkflowEvent(record_id=item.id, action="提交诉讼费退款", from_status=previous, to_status=item.status, operator=identity["username"], comment=body.comment))
    await db.commit(); await db.refresh(item); return await _record_dict_for_identity(item, identity, db)


@router.post(f"{settings.api_prefix}/finance/refunds/{{refund_id}}/review")
async def review_litigation_refund(refund_id: int, body: FinanceReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_refund_company_record, _record_dict_for_identity,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}: raise HTTPException(status_code=403, detail="当前角色没有退款审批权限")
    item = await _ensure_refund_company_record(refund_id, identity, db)
    if item.status != "待审批": raise HTTPException(status_code=409, detail="只有待审批退款申请可以审核")
    item.status = "退款办理中" if body.approved else "已驳回"; item.data = {**(item.data or {}), "reviewer": identity["username"], "reviewed_at": datetime.now().isoformat(timespec="seconds"), "review_comment": body.comment}
    db.add(WorkflowEvent(record_id=item.id, action="退款审批通过" if body.approved else "退款审批驳回", from_status="待审批", to_status=item.status, operator=identity["username"], comment=body.comment))
    await db.commit(); await db.refresh(item); return await _record_dict_for_identity(item, identity, db)


@router.post(f"{settings.api_prefix}/finance/refunds/{{refund_id}}/complete")
async def complete_litigation_refund(refund_id: int, body: RefundCompleteInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_refund_company_record, _record_dict_for_identity,
    )
    if identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以登记退款到账")
    item = await _ensure_refund_company_record(refund_id, identity, db)
    if item.status != "退款办理中": raise HTTPException(status_code=409, detail="退款审批通过后才能登记到账")
    data = item.data or {}; tx = FinanceTransaction(finance_record_id=item.id, transaction_type="退费", amount=float(data.get("amount", 0)), transaction_date=body.actual_date, voucher_no=body.voucher_no.strip(), counterparty=str(data.get("court", item.customer)), operator=identity["username"], remark=f"诉讼费退款 {item.serial_no}；{body.comment}")
    db.add(tx); await db.flush(); item.status = "已退款"; item.data = {**data, "actual_date": str(body.actual_date), "refund_voucher_no": body.voucher_no.strip(), "refund_transaction_id": tx.id, "completed_by": identity["username"], "completed_at": datetime.now().isoformat(timespec="seconds")}
    db.add(WorkflowEvent(record_id=item.id, action="登记退款到账", from_status="退款办理中", to_status=item.status, operator=identity["username"], comment=f"凭证号：{body.voucher_no}。{body.comment}"))
    await db.commit(); await db.refresh(item); return await _record_dict_for_identity(item, identity, db)
