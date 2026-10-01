"""按独立业务职责组织的路由，注册顺序与端点行为保持稳定。"""
from app.core.constants import (
    FINANCE_TRANSACTION_TYPES,
    UPLOAD_ROOT,
)
from app.core.dependencies import (
    AsyncSession,
    BusinessRecord,
    Depends,
    FileAttachment,
    FinanceTransaction,
    HTTPException,
    Path,
    Query,
    ReconciliationBatch,
    Response,
    WorkflowEvent,
    and_,
    current_identity,
    date,
    func,
    get_db,
    or_,
    select,
    settings,
    status,
)
from app.models_shared import (
    FinanceActionInput,
    FinanceTransactionInput,
    ReconciliationInput,
)
from fastapi import APIRouter

router = APIRouter()

@router.get(f"{settings.api_prefix}/finance/transactions")
async def list_finance_transactions(
    page: int = Query(1, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    finance_record_id: int | None = Query(None, ge=1),
    transaction_type: str = "",
    keyword: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _finance_transaction_dict,
    )
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _visible_record_ids,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    conditions = []
    if finance_record_id is not None:
        conditions.append(FinanceTransaction.finance_record_id == finance_record_id)
    if transaction_type.strip():
        conditions.append(FinanceTransaction.transaction_type == transaction_type.strip())
    if keyword.strip():
        like = f"%{keyword.strip()}%"
        conditions.append(or_(
            FinanceTransaction.voucher_no.ilike(like),
            FinanceTransaction.counterparty.ilike(like),
            FinanceTransaction.remark.ilike(like),
        ))
    if date_from:
        conditions.append(FinanceTransaction.transaction_date >= date_from)
    if date_to:
        conditions.append(FinanceTransaction.transaction_date <= date_to)
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="流水开始日期不能晚于结束日期")
    if identity.get("role") != "admin":
        visible_record_ids = await _visible_record_ids(identity, db)
        conditions.append(or_(
            and_(FinanceTransaction.finance_record_id.is_not(None), FinanceTransaction.finance_record_id.in_(visible_record_ids)),
            and_(FinanceTransaction.finance_record_id.is_(None), FinanceTransaction.operator == identity["username"]),
        ))
    total = await db.scalar(select(func.count()).select_from(FinanceTransaction).where(*conditions)) or 0
    query = select(FinanceTransaction).where(*conditions).order_by(
        FinanceTransaction.transaction_date.desc(), FinanceTransaction.id.desc()
    )
    if page_size is not None:
        query = query.offset((page - 1) * page_size).limit(page_size)
    items = (await db.scalars(query)).all()
    ids = {item.finance_record_id for item in items if item.finance_record_id}
    records = {item.id: item for item in (await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(ids)))).all()} if ids else {}
    transaction_ids = {item.id for item in items}
    voucher_rows = (await db.scalars(select(FileAttachment).where(FileAttachment.finance_transaction_id.in_(transaction_ids)).order_by(FileAttachment.created_at.desc()))).all() if transaction_ids else []
    vouchers: dict[int, list[FileAttachment]] = {}
    for voucher in voucher_rows:
        vouchers.setdefault(int(voucher.finance_transaction_id or 0), []).append(voucher)
    show_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    users_by_username = await _user_display_map({item.operator for item in items}, db)
    return {
        "items": [_finance_transaction_dict(item, records.get(item.finance_record_id), vouchers.get(item.id, []), show_amount=show_amount, users_by_username=users_by_username) for item in items],
        "total": int(total),
        "page": page,
        "page_size": page_size if page_size is not None else len(items),
    }


@router.post(f"{settings.api_prefix}/finance/transactions", status_code=status.HTTP_201_CREATED)
async def create_finance_transaction(body: FinanceTransactionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _finance_transaction_dict,
    )
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    if body.transaction_type not in FINANCE_TRANSACTION_TYPES: raise HTTPException(status_code=422, detail="流水类型无效")
    if body.transaction_type == "回款": raise HTTPException(status_code=409, detail="银行回款必须先进入回款管理，完成客户认领和应收分配")
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有登记财务流水的权限")
    if not body.finance_record_id:
        raise HTTPException(status_code=409, detail="付款、开票和退款流水必须关联费用记录并通过专用财务流程办理")
    record = await _ensure_record_module(body.finance_record_id, "finance", identity, db)
    if body.transaction_type != "付款":
        raise HTTPException(status_code=409, detail="开票和退款流水必须由发票或退费专用流程生成")
    from app.core.case_fee_payments import direct_fee_payment_amounts, lock_case_fee_rows
    from app.core.invoice_sources import is_external_case_fee
    if is_external_case_fee(record):
        record = (await lock_case_fee_rows([record.id], db))[0]
        payable = (await direct_fee_payment_amounts([record], db))[record.id]
        if body.amount > payable + .001:
            raise HTTPException(409, "付款金额不能超过直接申请的未付金额")
    if record.status not in {"已审批", "部分付款"}: raise HTTPException(status_code=409, detail="费用审批通过后才能付款")
    paid = await db.scalar(select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(FinanceTransaction.finance_record_id == record.id, FinanceTransaction.transaction_type == "付款"))
    if float(paid or 0) + body.amount > float((record.data or {}).get("amount", 0)) + 0.001: raise HTTPException(status_code=409, detail="付款金额不能超过费用金额")
    item = FinanceTransaction(**body.model_dump(), operator=identity["username"]); db.add(item); await db.flush()
    if record:
        previous = record.status
        if body.transaction_type == "付款":
            paid_total = float(paid or 0) + body.amount
            record.status = "已付款" if paid_total + 0.001 >= float((record.data or {}).get("amount", 0)) else "部分付款"
            record.data = {**(record.data or {}), "payment_status": "已付款" if record.status == "已付款" else "待付款"}
        db.add(WorkflowEvent(record_id=record.id, action=f"登记{body.transaction_type}", from_status=previous, to_status=record.status, operator=identity["username"], comment=f"{body.amount:.2f} 元；{body.remark}"))
    await db.commit(); await db.refresh(item)
    return _finance_transaction_dict(item, record, users_by_username=await _user_display_map({item.operator}, db))


@router.delete(f"{settings.api_prefix}/finance/transactions/{{transaction_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_finance_transaction(transaction_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    if identity["role"] != "admin": raise HTTPException(status_code=403, detail="仅管理员可删除")
    item = await db.get(FinanceTransaction, transaction_id)
    if not item: raise HTTPException(status_code=404, detail="财务流水不存在")
    record = await db.get(BusinessRecord, item.finance_record_id) if item.finance_record_id else None
    attachments = (await db.scalars(select(FileAttachment).where(FileAttachment.finance_transaction_id == item.id))).all()
    paths = [Path(x.path) for x in attachments]
    for attachment in attachments:
        await db.delete(attachment)
    await db.delete(item); await db.flush()
    if record and item.transaction_type == "付款":
        paid = float(await db.scalar(select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(FinanceTransaction.finance_record_id == record.id, FinanceTransaction.transaction_type == "付款")) or 0)
        fee_amount = float((record.data or {}).get("amount", 0))
        record.status = "已审批" if paid <= 0 else ("已付款" if paid + 0.001 >= fee_amount else "部分付款")
        record.data = {**(record.data or {}), "payment_status": "待付款" if record.status in {"已审批", "部分付款"} else "已付款"}
    await db.commit()
    for path in paths:
        if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
            path.unlink()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/finance/reconciliations")
async def list_reconciliations(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _reconciliation_dict,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    items = (await db.scalars(select(ReconciliationBatch).order_by(ReconciliationBatch.date_to.desc(), ReconciliationBatch.id.desc()))).all()
    if identity.get("role") not in {"admin", "auditor"}: items = [item for item in items if item.operator == identity["username"]]
    show_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    return {"items": [_reconciliation_dict(item, show_amount=show_amount) for item in items], "total": len(items)}


@router.post(f"{settings.api_prefix}/finance/reconciliations", status_code=status.HTTP_201_CREATED)
async def create_reconciliation(body: ReconciliationInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _reconciliation_dict,
    )
    from app.core.permissions import (
        _visible_record_ids,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}: raise HTTPException(status_code=403, detail="当前角色没有对账权限")
    if body.period_type not in {"周对账", "月对账"}: raise HTTPException(status_code=422, detail="对账周期无效")
    if body.date_from > body.date_to: raise HTTPException(status_code=422, detail="开始日期不能晚于结束日期")
    duplicate = await db.scalar(select(ReconciliationBatch.id).where(ReconciliationBatch.period_type == body.period_type, ReconciliationBatch.date_from == body.date_from, ReconciliationBatch.date_to == body.date_to))
    if duplicate: raise HTTPException(status_code=409, detail="该周期已经生成对账单")
    txs = (await db.scalars(select(FinanceTransaction).where(FinanceTransaction.transaction_date >= body.date_from, FinanceTransaction.transaction_date <= body.date_to))).all()
    if identity.get("role") != "admin":
        visible_record_ids = await _visible_record_ids(identity, db)
        txs = [item for item in txs if (item.finance_record_id and item.finance_record_id in visible_record_ids) or (not item.finance_record_id and item.operator == identity["username"])]
    item = ReconciliationBatch(**body.model_dump(), transaction_count=len(txs), total_amount=sum(tx.amount for tx in txs), status="待确认", operator=identity["username"])
    db.add(item); await db.commit(); await db.refresh(item); return _reconciliation_dict(item, show_amount="finance.amount" in await _allowed_field_keys(identity, db))


@router.post(f"{settings.api_prefix}/finance/reconciliations/{{batch_id}}/confirm")
async def confirm_reconciliation(batch_id: int, body: FinanceActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _reconciliation_dict,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}: raise HTTPException(status_code=403, detail="当前角色没有对账权限")
    item = await db.get(ReconciliationBatch, batch_id)
    if not item: raise HTTPException(status_code=404, detail="对账单不存在")
    if item.status == "已确认": raise HTTPException(status_code=409, detail="对账单已经确认")
    item.status = "已确认"; item.operator = identity["username"]; item.remark = body.comment or item.remark
    await db.commit(); await db.refresh(item); return _reconciliation_dict(item, show_amount="finance.amount" in await _allowed_field_keys(identity, db))


@router.delete(f"{settings.api_prefix}/finance/reconciliations/{{batch_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reconciliation(batch_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    if identity["role"] != "admin": raise HTTPException(status_code=403, detail="仅管理员可删除")
    item = await db.get(ReconciliationBatch, batch_id)
    if not item: raise HTTPException(status_code=404, detail="对账单不存在")
    await db.delete(item); await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
