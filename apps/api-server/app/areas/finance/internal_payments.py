"""内部结算与付款申请接口。"""
from fastapi import APIRouter
from app.core.dependencies import AsyncSession, BusinessRecord, Depends, HTTPException, Query, Response, User, WorkflowEvent, current_identity, date, datetime, delete, func, get_db, quote, select, settings, status
from app.models_shared import FinancePaymentPackageCreateInput, FinancePaymentPackagePreviewInput, FinancePaymentPackageUpdateInput, FinancePaymentPackageWriteoffInput, FinanceSettlementMarkInput

router = APIRouter()


@router.get(f"{settings.api_prefix}/finance/settlements/pending")
async def list_pending_finance_settlements(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.internal_requests import pending_case_fee_settlements

    rows = await pending_case_fee_settlements(identity, db)
    return {"items": rows, "total": len(rows)}

@router.post(f"{settings.api_prefix}/finance/settlements/mark-commission-paid")
async def mark_finance_settlements_commission_paid(body: FinanceSettlementMarkInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _record_scope_conditions,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有标识提成发放权限")
    fee_ids = list(dict.fromkeys(body.fee_ids))
    fees = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(fee_ids),
        BusinessRecord.module == "finance",
        *(await _record_scope_conditions(identity, db)),
    ).with_for_update())).all()
    if len(fees) != len(fee_ids):
        raise HTTPException(status_code=404, detail="部分案件费用不存在或无权访问")
    invalid = [item.serial_no for item in fees if
               (item.data or {}).get("fee_type") != "代理费"
               or (item.data or {}).get("refund_fee")
               or (item.data or {}).get("commission_paid")]
    if invalid:
        raise HTTPException(status_code=409, detail="仅可标识尚未发放提成的律师代理费：" + "、".join(invalid))
    linked = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance",
        BusinessRecord.status.not_in(("已删除", "已撤回", "已驳回", "已拒绝", "已作废")),
        BusinessRecord.data["fee_type"].as_string() == "内部费用",
        BusinessRecord.data["source_fee_id"].as_integer().in_(fee_ids),
    ).with_for_update())).all()
    linked_by_source = {fee_id: [] for fee_id in fee_ids}
    for commission in linked:
        if (commission.data or {}).get("commission_type"):
            linked_by_source[int((commission.data or {})["source_fee_id"])].append(commission)
    missing = [item.serial_no for item in fees if not linked_by_source[item.id]]
    if missing:
        raise HTTPException(409, "来源费用没有可标识的提成：" + "、".join(missing))
    if any((item.data or {}).get("commission_paid") for group in linked_by_source.values() for item in group):
        raise HTTPException(409, "关联提成已有部分发放标识，请核对后处理")
    marked_at = datetime.now().isoformat(timespec="seconds")
    for item in [*fees, *(commission for group in linked_by_source.values() for commission in group)]:
        item.data = {
            **(item.data or {}),
            "commission_paid": True,
            "commission_paid_by": identity["username"],
            "commission_paid_at": marked_at,
            "commission_paid_comment": body.comment.strip(),
        }
        db.add(WorkflowEvent(record_id=item.id, action="标识提成已发", from_status=item.status, to_status=item.status, operator=identity["username"], comment=body.comment.strip()))
    await db.commit()
    return {"marked": len(fees), "fee_ids": fee_ids, "marked_at": marked_at}

@router.get(f"{settings.api_prefix}/finance/fees/refund-review-candidates")
async def list_internal_refund_review_candidates(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.internal_requests import internal_review_rows

    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(403, "当前角色没有内部提成退费审批权限")
    rows = await internal_review_rows(identity, db, "refund")
    return {"items": rows, "total": len(rows)}

@router.get(f"{settings.api_prefix}/finance/payment-packages/{{package_no}}/print-word")
async def export_payment_package_word(
    package_no: str,
    scope: str = Query("internal_fee"),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _payment_package_for_word,
    )
    from app.core.storage import (
        _payment_package_docx_bytes,
    )
    package, fees, normalized_scope = await _payment_package_for_word(package_no, scope, identity, db)
    filename, content = _payment_package_docx_bytes(package, fees, scope=normalized_scope)
    disposition = f"attachment; filename=payment-package.docx; filename*=UTF-8''{quote(filename)}"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": disposition},
    )

@router.get(f"{settings.api_prefix}/finance/payment-packages")
async def list_internal_payment_packages(
    page: int = Query(1, ge=1),
    page_size: int | None = Query(None, ge=1, le=200),
    status_filter: str = Query("", alias="status"),
    page_id: str = Query("", alias="page_id"),
    package_no: str = Query(""),
    payee: str = Query(""),
    payment_date_from: date | None = Query(None),
    payment_date_to: date | None = Query(None),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _record_dict_for_identity, _record_scope_conditions,
    )
    legacy_status_by_page_id = {
        "5001003006": "待核销",
        "50001003006": "待核销",
    }
    effective_page_id = page_id.strip() if isinstance(page_id, str) else ""
    effective_status = status_filter.strip() or legacy_status_by_page_id.get(effective_page_id, "")
    conditions = [
        BusinessRecord.module == "finance_package",
        *(await _record_scope_conditions(identity, db)),
    ]
    if effective_status:
        conditions.append(BusinessRecord.status == effective_status)
    if package_no.strip():
        conditions.append(BusinessRecord.serial_no.ilike(f"%{package_no.strip()}%"))
    if payee.strip():
        conditions.append(BusinessRecord.data["payee"].as_string().ilike(f"%{payee.strip()}%"))
    if payment_date_from:
        conditions.append(BusinessRecord.data["payment_date"].as_string() >= str(payment_date_from))
    if payment_date_to:
        conditions.append(BusinessRecord.data["payment_date"].as_string() <= str(payment_date_to))
    total = await db.scalar(select(func.count()).select_from(BusinessRecord).where(*conditions)) or 0
    query = select(BusinessRecord).where(*conditions).order_by(
        BusinessRecord.created_at.desc(), BusinessRecord.id.desc()
    )
    if page_size is not None:
        query = query.offset((page - 1) * page_size).limit(page_size)
    items = (await db.scalars(query)).all()
    return {
        "items": [await _record_dict_for_identity(item, identity, db) for item in items],
        "total": int(total),
        "page": page,
        "page_size": page_size if page_size is not None else len(items),
    }

@router.get(f"{settings.api_prefix}/finance/payment-packages/candidates")
async def list_internal_payment_package_candidates(
    package_id: int | None = Query(None),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _record_dict_for_identity, _record_scope_conditions,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有打包付款权限")
    conditions = [BusinessRecord.module == "finance", *(await _record_scope_conditions(identity, db))]
    rows = (await db.scalars(select(BusinessRecord).where(*conditions).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()))).all()
    items = [
        row for row in rows
        if (row.data or {}).get("fee_type") == "内部费用"
        and (row.status == "已审批" or (package_id is not None and row.status == "待核销" and int((row.data or {}).get("payment_package_id") or 0) == package_id))
    ]
    return {"items": [await _record_dict_for_identity(item, identity, db) for item in items], "total": len(items)}

@router.post(f"{settings.api_prefix}/finance/payment-packages/preview")
async def preview_internal_payment_package(body: FinancePaymentPackagePreviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _new_internal_payment_package_no, _prepare_internal_payment_package,
    )
    _fees, details, payee, total_amount = await _prepare_internal_payment_package(body.fee_ids, identity, db)
    return {
        "package_no": _new_internal_payment_package_no(),
        "print_date": str(date.today()),
        "payee": payee,
        "total_amount": total_amount,
        "items": details,
    }

@router.post(f"{settings.api_prefix}/finance/payment-packages", status_code=status.HTTP_201_CREATED)
async def create_internal_payment_package(body: FinancePaymentPackageCreateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _prepare_internal_payment_package, _round_fee_amount,
    )
    from app.core.permissions import (
        _record_dict_for_identity,
    )
    fees, details, payee, total_amount = await _prepare_internal_payment_package(body.fee_ids, identity, db)
    if await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == body.package_no)):
        raise HTTPException(status_code=409, detail="付款包号码已经存在")
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    paid_at = datetime.now().isoformat(timespec="seconds")
    payment_date = str(date.today())
    package = BusinessRecord(
        module="finance_package",
        serial_no=body.package_no,
        title=f"{payee}提成付款申请单",
        customer="",
        status="待核销",
        owner=identity["username"],
        department=user.department if user else "上海分所",
        description=body.comment.strip(),
        data={
            "fee_ids": [item.id for item in fees],
            "payee": payee,
            "amount": total_amount,
            "total_amount": total_amount,
            "payment_date": payment_date,
            "payment_status": "待核销",
            "fee_type": "内部提成",
            "items": details,
            "submitted_at": paid_at,
            "submitted_by": identity["username"],
            "comment": body.comment.strip(),
        },
    )
    db.add(package)
    await db.flush()
    db.add(WorkflowEvent(record_id=package.id, action="创建付款包", from_status="", to_status="待核销", operator=identity["username"], comment=body.comment.strip() or "同一收款人提成打包付款"))
    for fee in fees:
        previous = fee.status
        fee_amount = _round_fee_amount(float((fee.data or {}).get("actual_commission") if (fee.data or {}).get("actual_commission") is not None else (fee.data or {}).get("amount") or 0))
        fee.status = "待核销"
        fee.data = {
            **(fee.data or {}),
            "payment_status": "待核销",
            "payment_requested_amount": fee_amount,
            "paid_amount": 0,
            "payment_package_id": package.id,
            "payment_package_no": package.serial_no,
            "payment_applied_at": paid_at,
            "payment_applied_by": identity["username"],
        }
        db.add(WorkflowEvent(record_id=fee.id, action="申请打包付款", from_status=previous, to_status="待核销", operator=identity["username"], comment=f"付款包 {package.serial_no}；{body.comment.strip()}"))
    await db.commit()
    await db.refresh(package)
    return await _record_dict_for_identity(package, identity, db)

@router.get(f"{settings.api_prefix}/finance/payment-packages/{{package_id}}")
async def get_internal_payment_package(package_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    package = await _ensure_record_module(package_id, "finance_package", identity, db)
    return await _record_dict_for_identity(package, identity, db)

@router.put(f"{settings.api_prefix}/finance/payment-packages/{{package_id}}")
async def update_internal_payment_package(package_id: int, body: FinancePaymentPackageUpdateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _prepare_internal_payment_package, _round_fee_amount,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有编辑付款包权限")
    package = await _ensure_record_module(package_id, "finance_package", identity, db)
    if package.status != "待核销":
        raise HTTPException(status_code=409, detail="仅待核销付款包可以编辑费用构成")
    previous_data = package.data or {}
    raw_previous_ids = list(previous_data.get("fee_ids", []))
    if not raw_previous_ids or any(not str(item_id).strip().isdigit() for item_id in raw_previous_ids):
        raise HTTPException(status_code=409, detail="付款包原费用关联无效，不能编辑")
    previous_ids = [int(item_id) for item_id in raw_previous_ids]
    fees, details, payee, total_amount = await _prepare_internal_payment_package(
        body.fee_ids, identity, db, editable_package_id=package.id,
    )
    next_ids = [item.id for item in fees]
    current_fees = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(previous_ids), BusinessRecord.module == "finance"
    ))).all() if previous_ids else []
    if len({item.id for item in current_fees}) != len(set(previous_ids)):
        raise HTTPException(status_code=409, detail="付款包原费用关联不完整，不能编辑")
    inconsistent = [
        item.serial_no for item in current_fees
        if item.status != "待核销"
        or int((item.data or {}).get("payment_package_id") or 0) != package.id
        or str((item.data or {}).get("payment_package_no") or "").strip() != package.serial_no
    ]
    if inconsistent:
        raise HTTPException(status_code=409, detail="付款包原费用关联不一致：" + "、".join(inconsistent))
    payment_keys = {
        "payment_status", "payment_date", "payment_package_id", "payment_package_no",
        "payment_requested_amount", "paid_amount", "payment_applied_at", "payment_applied_by",
        "paid_at", "paid_by", "writeoff_status", "writeoff_voucher_no", "payment_method",
        "written_off_at", "written_off_by",
    }
    removed = [item for item in current_fees if item.id not in next_ids]
    for fee in removed:
        data = fee.data or {}
        if int(data.get("payment_package_id") or 0) != package.id:
            raise HTTPException(status_code=409, detail=f"费用 {fee.serial_no} 的付款包关联不一致")
        fee.status = "已审批"
        fee.data = {key: value for key, value in data.items() if key not in payment_keys}
        db.add(WorkflowEvent(record_id=fee.id, action="编辑付款包移除费用", from_status="待核销", to_status="已审批", operator=identity["username"], comment=package.serial_no))
    now = datetime.now().isoformat(timespec="seconds")
    for fee in fees:
        data = fee.data or {}
        if fee.id not in previous_ids and data.get("payment_package_id"):
            raise HTTPException(status_code=409, detail=f"费用 {fee.serial_no} 已关联其他付款包")
        previous_status = fee.status
        amount = _round_fee_amount(float(data.get("actual_commission") if data.get("actual_commission") is not None else data.get("amount") or 0))
        fee.status = "待核销"
        fee.data = {**data, "payment_status": "待核销", "payment_requested_amount": amount, "paid_amount": 0,
                    "payment_package_id": package.id, "payment_package_no": package.serial_no,
                    "payment_applied_at": now, "payment_applied_by": identity["username"]}
        if fee.id not in previous_ids:
            db.add(WorkflowEvent(record_id=fee.id, action="编辑付款包加入费用", from_status=previous_status, to_status="待核销", operator=identity["username"], comment=package.serial_no))
    comment = body.comment.strip()
    package.title = f"{payee}提成付款申请单"
    package.description = comment
    package.data = {**previous_data, "fee_ids": next_ids, "payee": payee, "amount": total_amount,
                    "total_amount": total_amount, "items": details, "comment": comment,
                    "updated_at": now, "updated_by": identity["username"]}
    db.add(WorkflowEvent(record_id=package.id, action="编辑付款包", from_status="待核销", to_status="待核销", operator=identity["username"], comment=comment or "更新费用构成"))
    await db.commit()
    await db.refresh(package)
    return await _record_dict_for_identity(package, identity, db)

@router.post(f"{settings.api_prefix}/finance/payment-packages/{{package_id}}/writeoff")
async def writeoff_internal_payment_package(package_id: int, body: FinancePaymentPackageWriteoffInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _round_fee_amount,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有付款核销权限")
    package = await _ensure_record_module(package_id, "finance_package", identity, db)
    if package.status != "待核销":
        raise HTTPException(status_code=409, detail="仅待核销付款包可以核销")
    if body.payment_method not in {"自动扣款", "银行卡", "现金"}:
        raise HTTPException(status_code=422, detail="付款方式无效")
    if not body.invoice_no.strip():
        raise HTTPException(status_code=422, detail="请输入付款单据号.")
    package_data = package.data or {}
    expected_amount = _round_fee_amount(float(package_data.get("total_amount") or package_data.get("amount") or 0))
    confirmed_amount = _round_fee_amount(body.amount)
    if abs(confirmed_amount - expected_amount) > 0.001:
        raise HTTPException(status_code=409, detail=f"确认付款金额必须等于付款包金额 {expected_amount:.2f}")
    written_off_at = datetime.now().isoformat(timespec="seconds")
    package.status = "已付款"
    package.data = {
        **package_data,
        "payment_status": "已付款",
        "paid_date": str(body.paid_date),
        "payment_method": body.payment_method,
        "invoice_no": body.invoice_no.strip(),
        "remark": body.remark.strip(),
        "writeoff_status": "已核销",
        "written_off_at": written_off_at,
        "written_off_by": identity["username"],
    }
    fee_ids = [int(item_id) for item_id in package_data.get("fee_ids", [])]
    fees = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(fee_ids), BusinessRecord.module == "finance"
    ))).all() if fee_ids else []
    if len(fees) != len(set(fee_ids)):
        raise HTTPException(status_code=409, detail="付款包关联的费用记录不完整")
    for fee in fees:
        data = fee.data or {}
        if int(data.get("payment_package_id") or 0) != package.id:
            raise HTTPException(status_code=409, detail=f"费用 {fee.serial_no} 的付款包关联不一致")
        previous = fee.status
        fee_amount = _round_fee_amount(float(data.get("actual_commission") if data.get("actual_commission") is not None else data.get("amount") or 0))
        fee.status = "已付款"
        fee.data = {
            **data,
            "payment_status": "已付款",
            "payment_date": str(body.paid_date),
            "paid_amount": fee_amount,
            "paid_at": written_off_at,
            "paid_by": identity["username"],
            "writeoff_status": "已核销",
            "writeoff_voucher_no": body.invoice_no.strip(),
            "payment_method": body.payment_method,
            "written_off_at": written_off_at,
            "written_off_by": identity["username"],
        }
        db.add(WorkflowEvent(record_id=fee.id, action="付款包核销", from_status=previous, to_status="已付款", operator=identity["username"], comment=f"付款包 {package.serial_no}；单据号 {body.invoice_no.strip()}；{body.remark.strip()}"))
    db.add(WorkflowEvent(record_id=package.id, action="付款核销", from_status="待核销", to_status="已付款", operator=identity["username"], comment=f"{body.payment_method}；单据号 {body.invoice_no.strip()}；{body.remark.strip()}"))
    await db.commit()
    await db.refresh(package)
    return await _record_dict_for_identity(package, identity, db)

@router.delete(f"{settings.api_prefix}/finance/payment-packages/{{package_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_internal_payment_package(package_id: int, reverse_paid: bool = Query(False), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    if identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可以撤销付款包")
    package = await _ensure_record_module(package_id, "finance_package", identity, db)
    if package.status == "已付款" and not reverse_paid:
        raise HTTPException(status_code=409, detail="已核销付款包必须显式冲正后才能撤销")
    if package.status not in {"待核销", "已付款"}:
        raise HTTPException(status_code=409, detail="当前付款包状态不能撤销")
    package_data = package.data or {}
    raw_fee_ids = list(package_data.get("fee_ids", []))
    if not raw_fee_ids or any(not str(item_id).strip().isdigit() for item_id in raw_fee_ids):
        raise HTTPException(status_code=409, detail="付款包费用关联无效，不能撤销")
    fee_ids = [int(item_id) for item_id in raw_fee_ids]
    fees = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(fee_ids), BusinessRecord.module == "finance"
    ))).all() if fee_ids else []
    if len({item.id for item in fees}) != len(set(fee_ids)):
        raise HTTPException(status_code=409, detail="付款包关联费用不完整，不能撤销")
    payment_keys = {
        "payment_status", "payment_date", "payment_package_id",
        "payment_package_no", "payment_requested_amount", "paid_amount",
        "payment_applied_at", "payment_applied_by", "paid_at", "paid_by", "writeoff_status",
        "writeoff_voucher_no", "payment_method", "written_off_at",
        "written_off_by",
    }
    for fee in fees:
        data = fee.data or {}
        if (
            int(data.get("payment_package_id") or 0) != package.id
            or str(data.get("payment_package_no") or "").strip() != package.serial_no
        ):
            raise HTTPException(status_code=409, detail=f"费用 {fee.serial_no} 的付款包关联不一致")
        previous = fee.status
        fee.status = "已审批"
        fee.data = {key: value for key, value in data.items() if key not in payment_keys}
        action = "冲正已核销付款包" if package.status == "已付款" else "撤销打包付款"
        db.add(WorkflowEvent(record_id=fee.id, action=action, from_status=previous, to_status="已审批", operator=identity["username"], comment=f"撤销付款包 {package.serial_no}"))
    await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == package.id))
    await db.delete(package)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
