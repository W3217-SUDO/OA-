"""按业务职责组织的 API 路由，保留原有端点行为与注册顺序。"""

from app.core.dependencies import (
    AsyncSession, BusinessRecord, Depends, File, FinanceTransaction, Form, HTTPException,
    IncomingPayment, Query, ReceivablePlan, Response, UploadFile, User, WorkflowEvent,
    current_identity, date, datetime, func, get_db, or_, select, settings, status,
)
from app.core.incoming_allocation_records import AllocationCancelInput
from app.models_shared import (
    IncomingPaymentAllocateInput, IncomingPaymentAllocationItem, IncomingPaymentClaimInput,
    IncomingPaymentInput, IncomingPaymentRefundClaimInput, IncomingPaymentRevokeInput,
    IncomingPaymentUpdateInput,
)
from fastapi import APIRouter
from app.core.incoming_settlement import (_active_settlements_by_receipt, _revert_incoming_allocation)

router = APIRouter()


@router.get(f"{settings.api_prefix}/finance/incoming-payments")
async def list_incoming_payments(payment_status: str = "", keyword: str = "", bank_source: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.contracts import (
        _contract_person_values,
    )
    from app.core.finance import (
        _incoming_payment_dict, _visible_incoming_payment_statement,
    )
    from app.core.formatters import (
        _person_reference_display,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    if bank_source:
        aliases = {
            "icbc": ("工行", "工商银行"),
            "citic": ("中信",),
            "boc": ("中行", "中国银行"),
            "cmb": ("招商", "招行"),
        }
        bank_code = bank_source.strip().lower()
        if bank_code not in aliases:
            raise HTTPException(422, "银行筛选条件无效")
    statement = await _visible_incoming_payment_statement(identity, db)
    if bank_source:
        statement = statement.where(or_(
            func.lower(func.trim(IncomingPayment.bank_source)) == bank_code,
            *(IncomingPayment.bank_source.contains(name) for name in aliases[bank_code]),
        ))
    if payment_status:
        statement = statement.where(IncomingPayment.status == payment_status)
    items = (await db.scalars(statement.order_by(IncomingPayment.received_date.desc(), IncomingPayment.id.desc()))).all()
    if keyword:
        key = keyword.casefold(); items = [item for item in items if key in f"{item.receipt_no} {item.payer_name} {item.bank_reference} {item.claimed_customer}".casefold()]
    can_view_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    users = list((await db.scalars(select(User).where(User.is_active.is_(True)))).all())
    users_by_username = {user.username.lower(): user for user in users}
    claimed_names = {item.claimed_customer.strip() for item in items if item.claimed_customer.strip()}
    customer_rows = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "customer", BusinessRecord.title.in_(claimed_names),
    ))).all()) if claimed_names else []
    customers_by_title = {row.title.strip(): row for row in customer_rows}
    rows = []
    for item in items:
        payload = _incoming_payment_dict(item, show_amount=can_view_amount, users_by_username=users_by_username)
        customer = customers_by_title.get(item.claimed_customer.strip())
        if customer:
            manager_values = _contract_person_values((customer.data or {}).get("customer_managers") or [customer.owner])
            payload["customer_manager"] = "、".join(manager_values)
            payload["customer_manager_display_name"] = "、".join(
                _person_reference_display(value, users_by_username)[0] for value in manager_values
            )
        else:
            payload["customer_manager"] = ""
            payload["customer_manager_display_name"] = ""
        rows.append(payload)
    return {"items": rows, "total": len(items), "summary": {"total": len(items), "unclaimed": sum(1 for item in items if item.status == "待认领"), "unallocated": sum(1 for item in items if item.status in {"待分配", "部分分配"}), "completed": sum(1 for item in items if item.status == "已分配"), "amount": sum(item.amount for item in items) if can_view_amount else None, "remaining": sum(max(item.amount - item.allocated_amount, 0) for item in items) if can_view_amount else None}}


@router.get(f"{settings.api_prefix}/finance/customer-options")
async def list_finance_customer_options(
    keyword: str = Query("", max_length=255),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Search active system customers for receipt registration, never litigants."""
    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以登记银行到账")
    conditions = [
        BusinessRecord.module == "customer",
        BusinessRecord.status.not_in(["已回收"]),
        func.coalesce(BusinessRecord.data["customer_type"].as_string(), "客户") == "客户",
    ]
    normalized_keyword = keyword.strip()
    if normalized_keyword:
        like = f"%{normalized_keyword}%"
        conditions.append(or_(BusinessRecord.title.ilike(like), BusinessRecord.serial_no.ilike(like)))
    rows = list((await db.scalars(
        select(BusinessRecord).where(*conditions).order_by(BusinessRecord.title, BusinessRecord.id).limit(50)
    )).all())
    return {
        "items": [
            {"id": row.id, "title": row.title, "serial_no": row.serial_no}
            for row in rows
        ]
    }


@router.post(f"{settings.api_prefix}/finance/incoming-payments", status_code=status.HTTP_201_CREATED)
async def create_incoming_payment(body: IncomingPaymentInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _incoming_payment_dict, _round_fee_amount,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    if identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以登记银行到账")
    bank_reference = body.bank_reference.strip()
    if bank_reference and await db.scalar(select(IncomingPayment.id).where(IncomingPayment.bank_reference == bank_reference)): raise HTTPException(status_code=409, detail="银行流水号已经登记")
    contract_no = body.contract_no.strip()
    case_no = body.case_no.strip()
    customer = body.customer.strip()
    contract = None
    if contract_no:
        contract = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "contract", BusinessRecord.serial_no == contract_no))
        if not contract: raise HTTPException(status_code=422, detail="关联合同不存在")
        if customer and contract.customer != customer: raise HTTPException(status_code=422, detail="关联合同与所选客户不一致")
        customer = customer or contract.customer
    case_record = None
    if case_no:
        case_record = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "case", BusinessRecord.serial_no == case_no, *(await _record_scope_conditions(identity, db))))
        if not case_record: raise HTTPException(status_code=422, detail="关联案件不存在或无权查看")
        linked_contract_id = int((case_record.data or {}).get("contract_id") or 0)
        if contract:
            if linked_contract_id and linked_contract_id != contract.id:
                raise HTTPException(status_code=422, detail="关联案件不属于所选合同")
        elif linked_contract_id:
            contract = await db.get(BusinessRecord, linked_contract_id)
            if not contract or contract.module != "contract":
                raise HTTPException(status_code=422, detail="关联案件的合同不存在")
            contract_no = contract.serial_no
        customer = customer or case_record.customer
    item = IncomingPayment(source_kind="manual", receipt_no=f"HK{datetime.now():%Y%m%d%H%M%S%f}", received_date=body.received_date, amount=_round_fee_amount(body.amount), payer_name=body.payer_name.strip(), bank_reference=bank_reference or None, status="待认领", contract_record_id=contract.id if contract else None, contract_no=contract.serial_no if contract else "", case_no=case_no, bank_source=body.bank_source.strip(), operator=identity["username"], remark=body.remark)
    db.add(item); await db.flush()
    if body.claim:
        if not customer: raise HTTPException(status_code=422, detail="自动认领需要填写客户名称")
        claimed = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "customer", BusinessRecord.title == customer, *(await _record_scope_conditions(identity, db))))
        if not claimed: raise HTTPException(status_code=404, detail="客户不存在或无权认领")
        item.claimed_customer = claimed.title; item.claimant = identity["username"]; item.status = "待分配"
        item.remark = "；".join(part for part in [item.remark, "回款登记时自动认领"] if part)
        db.add(WorkflowEvent(record_id=claimed.id, action="认领银行到账", from_status=claimed.status, to_status=claimed.status, operator=identity["username"], comment=f"{item.receipt_no}｜{item.payer_name}｜{item.amount:.2f} 元。回款登记时自动认领"))
    await db.commit(); await db.refresh(item); return _incoming_payment_dict(item)


@router.post(f"{settings.api_prefix}/finance/incoming-payments/import")
async def import_incoming_payments(file: UploadFile | None = File(None), bank_source: str = Form(""), confirmed_rows: str = Form(""), confirmation_token: str = Form(""), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.bank_statement_import import read_statement, cell_text, parse_received_date, parse_amount
    from app.core.bank_document_recognition import requires_recognition, recognize_document, sign_preview, verify_preview
    import json
    from app.core.permissions import _permission_payload_for_identity
    bank_source = bank_source.strip().lower()
    bank_names = {"icbc": "工行", "citic": "中信", "boc": "中行", "cmb": "招商"}
    if bank_source and bank_source not in bank_names:
        raise HTTPException(422, "请选择工行、中信、中行或招商回款入口上传")
    permission = await _permission_payload_for_identity(identity, db)
    menus = set(permission.get("menu_keys", []))
    if identity.get("role") not in {"admin", "manager"} and not (bank_source and (
        f"finance-receipts-{bank_source}" in menus or f"platform-finance-overview-{bank_source}" in menus
    )):
        raise HTTPException(status_code=403, detail="当前账号没有该银行回款上传权限")
    preview = False
    recognized = False
    try:
        if confirmation_token:
            if len(confirmed_rows) > 2 * 1024 * 1024:
                raise ValueError('确认内容过大，请重新识别')
            statement_rows = json.loads(confirmed_rows)
            if not isinstance(statement_rows, list) or len(statement_rows) > 1000 or not verify_preview(confirmation_token, statement_rows, identity['username'], bank_source):
                raise ValueError('识别结果已过期或被更改，请重新上传识别')
            recognized = True
        else:
            if file is None:
                raise ValueError('请选择需要识别的银行流水文件')
            raw = await file.read(100 * 1024 * 1024 + 1)
            if len(raw) > 100 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="银行流水文件不能超过100MB，请拆分后上传")
            if requires_recognition(file.filename or ''):
                statement_rows = await recognize_document(raw, file.filename or '', bank_source)
                statement_rows = [[sheet, number, {key: cell_text(value) for key, value in row.items()}] for sheet, number, row in statement_rows]
                preview = recognized = True
            else:
                from starlette.concurrency import run_in_threadpool
                statement_rows = await run_in_threadpool(read_statement, raw, file.filename or "", bank_source)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(422, "文件无法识别，请确认格式真实、文件未加密且未损坏") from exc
    existing = set((await db.scalars(select(IncomingPayment.bank_reference))).all())
    existing_receipts = set((await db.scalars(select(IncomingPayment.receipt_no))).all()) if bank_source == 'icbc' else set()
    created = 0
    skipped = 0
    errors: list[dict] = []
    preview_items: list[dict] = []
    for sheet_name, row_no, row in statement_rows:
        try:
            if cell_text(row.get("direction")).upper() in {"借", "借方", "付", "付款", "支出", "转出", "D", "DEBIT"}:
                skipped += 1
                continue
            if recognized and row.get('direction') == '未知':
                raise ValueError('无法确认收付方向，请核对原文件后使用明确的收入流水明细')
            payer = cell_text(row.get("payer_name"))
            bank_reference = cell_text(row.get("bank_reference"))
            import_identity = cell_text(row.get('_import_identity')) if bank_source == 'icbc' else ''
            if import_identity:
                import re
                if not re.fullmatch(r'HKICBC[0-9a-f]{48}', import_identity):
                    raise ValueError('工行导入标识无效，请重新上传')
            received_text = row.get("received_date")
            amount_text = row.get("amount")
            if not payer or not (bank_reference or import_identity) or not received_text or not amount_text:
                raise ValueError("缺少对方户名、银行流水号、到账日期或到账金额")
            if len(payer) > 255 or len(bank_reference) > 128:
                raise ValueError("对方户名或银行流水号过长，请检查表头与数据列")
            if bank_reference and bank_reference in existing:
                raise ValueError("银行流水号已经登记")
            if import_identity and import_identity in existing_receipts:
                raise ValueError('这笔工行流水已经导入，请勿重复上传')
            received_date = parse_received_date(received_text)
            amount = parse_amount(amount_text)
            if amount <= 0:
                raise ValueError("到账金额必须大于 0")
            item_values = dict(
                source_kind="bank_import",
                receipt_no=import_identity or f"HK{datetime.now():%Y%m%d%H%M%S%f}{row_no}",
                received_date=received_date,
                amount=amount,
                payer_name=payer,
                bank_reference=bank_reference or None,
                status="待认领",
                bank_source=bank_names.get(bank_source, ""),
                operator=identity["username"],
                remark=cell_text(row.get("remark")),
            )
            if preview:
                preview_items.append({'source': sheet_name, 'row': row_no, 'payer_name': payer, 'bank_reference': bank_reference,
                    'received_date': str(received_date), 'amount': amount, 'remark': item_values['remark']})
            else:
                db.add(IncomingPayment(**item_values))
            existing.add(bank_reference)
            if import_identity:
                existing_receipts.add(import_identity)
            created += 1
        except (ValueError, TypeError) as exc:
            errors.append({"sheet": sheet_name, "row": row_no, "error": str(exc) or "字段格式错误"})
    if preview:
        return {'requires_confirmation': True, 'items': preview_items, 'rows': statement_rows,
            'confirmation_token': sign_preview(statement_rows, identity['username'], bank_source),
            'created': 0, 'valid_count': created, 'errors': errors, 'skipped': skipped}
    if created:
        await db.commit()
    return {"created": created, "errors": errors, "skipped": skipped}


@router.get(f"{settings.api_prefix}/finance/incoming-payments/export")
async def export_incoming_payments(payment_status: str = "", keyword: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import _visible_incoming_payment_statement
    from app.core.system import (
        _allowed_field_keys, _excel_response,
    )
    statement = await _visible_incoming_payment_statement(identity, db)
    if payment_status:
        statement = statement.where(IncomingPayment.status == payment_status)
    items = (await db.scalars(statement.order_by(IncomingPayment.received_date.desc(), IncomingPayment.id.desc()))).all()
    if keyword:
        key = keyword.casefold(); items = [item for item in items if key in f"{item.receipt_no} {item.payer_name} {item.bank_reference} {item.claimed_customer}".casefold()]
    can_view_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    headers = ["回款流水号", "到账日期", "回款单位", "银行流水号", "客户", "合同编号", "案件编号", "银行来源", "金额", "已分配金额", "剩余金额", "状态", "领取人", "登记人", "备注"]
    rows = []
    for item in items:
        amount = float(item.amount); allocated = float(item.allocated_amount or 0)
        rows.append([
            item.receipt_no, str(item.received_date), item.payer_name, item.bank_reference,
            item.claimed_customer, item.contract_no, item.case_no, item.bank_source,
            f"{amount:.2f}" if can_view_amount else "", f"{allocated:.2f}" if can_view_amount else "",
            f"{max(amount - allocated, 0):.2f}" if can_view_amount else "", item.status,
            item.claimant, item.operator, item.remark,
        ])
    return _excel_response(f"银行到账-{date.today()}.xls", headers, rows)


@router.get(f"{settings.api_prefix}/finance/incoming-payments/{{payment_id}}")
async def get_incoming_payment(payment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _general_settlement_rows, _incoming_payment_dict,
    )
    from app.core.formatters import (
        _user_display_map,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    item = await db.get(IncomingPayment, payment_id)
    if not item: raise HTTPException(status_code=404, detail="银行到账记录不存在")
    if identity.get("role") not in {"admin", "auditor"}:
        visible_customer_titles = set((await db.scalars(select(BusinessRecord.title).where(BusinessRecord.module == "customer", *(await _record_scope_conditions(identity, db))))).all())
        if item.operator != identity["username"] and item.claimant != identity["username"] and item.claimed_customer not in visible_customer_titles:
            raise HTTPException(status_code=404, detail="银行到账记录不存在")
    show_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    users_by_username = await _user_display_map({item.claimant, item.operator}, db)
    result = _incoming_payment_dict(item, show_amount=show_amount, users_by_username=users_by_username)
    settlement_rows = await _general_settlement_rows(
        identity,
        db,
        receipt_ids={payment_id},
        include_active_receipts=True,
    )
    if settlement_rows:
        settlement_data = settlement_rows[0]["data"]
        result.update({
            "payment_method": settlement_data.get("payment_method") or result.get("payment_method"),
            "assigned_official_fee": settlement_data.get("assigned_official_fee"),
            "assigned_agency_fee": settlement_data.get("assigned_agency_fee"),
            "assigned_other_fee": settlement_data.get("assigned_other_fee"),
            "allocation_details": settlement_data.get("allocation_details") or [],
        })
    else:
        result["allocation_details"] = []
    return result


@router.get(f"{settings.api_prefix}/finance/incoming-payments/{{payment_id}}/view-assigned")
async def view_assigned_incoming_payment(payment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _incoming_payment_dict,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    item = await db.get(IncomingPayment, payment_id)
    if not item: raise HTTPException(status_code=404, detail="银行到账记录不存在")
    if identity.get("role") not in {"admin", "auditor"}:
        visible_customer_titles = set((await db.scalars(select(BusinessRecord.title).where(BusinessRecord.module == "customer", *(await _record_scope_conditions(identity, db))))).all())
        if item.operator != identity["username"] and item.claimant != identity["username"] and item.claimed_customer not in visible_customer_titles:
            raise HTTPException(status_code=404, detail="银行到账记录不存在")
    rows = []
    for allocation in item.allocations or []:
        plan = await db.get(ReceivablePlan, int(allocation.get("receivable_plan_id") or 0))
        contract = await db.get(BusinessRecord, int(allocation.get("contract_id") or 0))
        case_record = await db.get(BusinessRecord, int(allocation.get("case_id") or 0))
        rows.append({
            **allocation,
            "plan": {"id": plan.id, "phase": plan.phase, "amount": plan.amount, "received_amount": plan.received_amount, "status": plan.status} if plan else None,
            "contract": {"id": contract.id, "serial_no": contract.serial_no, "title": contract.title} if contract else None,
            "case": {"id": case_record.id, "serial_no": case_record.serial_no, "title": case_record.title} if case_record else None,
        })
    return {"items": rows, "total": len(rows), "payment": _incoming_payment_dict(item, show_amount="finance.amount" in await _allowed_field_keys(identity, db))}


@router.post(f"{settings.api_prefix}/finance/incoming-payments/{{payment_id}}/claim")
async def claim_incoming_payment(payment_id: int, body: IncomingPaymentClaimInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _incoming_payment_dict,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    item = await db.get(IncomingPayment, payment_id)
    if not item: raise HTTPException(status_code=404, detail="银行到账记录不存在")
    if item.status not in {"待认领", "待分配"} or item.allocated_amount > 0: raise HTTPException(status_code=409, detail="已发生分配的到账不能重新认领")
    customer = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "customer", BusinessRecord.title == body.customer.strip(), *(await _record_scope_conditions(identity, db))))
    if not customer: raise HTTPException(status_code=404, detail="客户不存在或无权认领")
    item.claimed_customer = customer.title; item.claimant = identity["username"]; item.status = "待分配"; item.remark = "；".join(part for part in [item.remark, body.comment] if part)
    db.add(WorkflowEvent(record_id=customer.id, action="认领银行到账", from_status=customer.status, to_status=customer.status, operator=identity["username"], comment=f"{item.receipt_no}｜{item.payer_name}｜{item.amount:.2f} 元。{body.comment}"))
    await db.commit(); await db.refresh(item); return _incoming_payment_dict(item, show_amount="finance.amount" in await _allowed_field_keys(identity, db))


@router.get(f"{settings.api_prefix}/finance/incoming-payments/{{payment_id}}/allocation-candidates")
async def incoming_payment_allocation_candidates(payment_id: int, case_fees_only: bool = False, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import _case_fee_display_type
    from app.core.crm import (
        _case_is_for_allocation_customer,
    )
    from app.core.finance import (
        _round_fee_amount,
    )
    from app.core.formatters import (
        _record_belongs_to_customer,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    item = await db.get(IncomingPayment, payment_id)
    if not item:
        raise HTTPException(status_code=404, detail="银行到账记录不存在")
    if item.status not in {"待分配", "部分分配"} or not item.claimed_customer:
        raise HTTPException(status_code=409, detail="到账认领到客户后才能查看可分配案件费用")

    claimed_customer_record = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == "customer",
        BusinessRecord.title == item.claimed_customer,
        *(await _record_scope_conditions(identity, db)),
    ))
    customer_links = [BusinessRecord.customer == item.claimed_customer]
    if claimed_customer_record is not None:
        customer_links.extend([
            BusinessRecord.data["customer_id"].as_integer() == claimed_customer_record.id,
            BusinessRecord.data["customer_record_id"].as_integer() == claimed_customer_record.id,
        ])
        if str(claimed_customer_record.serial_no or "").strip():
            customer_links.append(BusinessRecord.data["customer_no"].as_string() == claimed_customer_record.serial_no)
    contracts = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "contract",
        or_(*customer_links),
        *(await _record_scope_conditions(identity, db)),
    ))).all())
    contracts_by_id = {contract.id: contract for contract in contracts}
    contract_ids = set(contracts_by_id)
    plans = list((await db.scalars(select(ReceivablePlan).where(
        ReceivablePlan.contract_record_id.in_(contract_ids),
    ).order_by(ReceivablePlan.due_date.asc(), ReceivablePlan.id.asc()))).all()) if contract_ids else []
    plans = [plan for plan in plans if _round_fee_amount(plan.amount - plan.received_amount) > 0]

    cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case",
        or_(*customer_links),
        *(await _record_scope_conditions(identity, db)),
    ).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()))).all())
    cases_by_contract: dict[int, list[BusinessRecord]] = {}
    case_count_by_contract: dict[int, int] = {}
    contract_no_to_id = {contract.serial_no: contract.id for contract in contracts}
    for case_record in cases:
        if not _record_belongs_to_customer(case_record, claimed_customer_record, item.claimed_customer):
            continue
        case_data = case_record.data or {}
        contract_id = int(case_data.get("contract_id") or case_data.get("contract_record_id") or 0)
        if not contract_id:
            contract_id = contract_no_to_id.get(str(case_data.get("contract_no") or "").strip(), 0)
        if contract_id in contracts_by_id:
            case_count_by_contract[contract_id] = case_count_by_contract.get(contract_id, 0) + 1
            if _case_is_for_allocation_customer(case_record, claimed_customer_record, item.claimed_customer):
                cases_by_contract.setdefault(contract_id, []).append(case_record)

    rows = []
    for plan in plans:
        if case_fees_only:
            continue
        contract = contracts_by_id[plan.contract_record_id]
        remaining = _round_fee_amount(plan.amount - plan.received_amount)
        linked_cases = cases_by_contract.get(contract.id)
        if not linked_cases and case_count_by_contract.get(contract.id):
            continue
        linked_cases = linked_cases or [None]
        for case_record in linked_cases:
            case_data = case_record.data or {} if case_record else {}
            submitted_at = (
                case_data.get("case_register_date")
                or case_data.get("submission_date")
                or case_data.get("filing_date")
                or (case_record.created_at.isoformat() if case_record and case_record.created_at else "")
            )
            rows.append({
                "key": f"{plan.id}:{case_record.id if case_record else 0}",
                "receivable_plan_id": plan.id,
                "contract_id": contract.id,
                "contract_no": contract.serial_no,
                "case_id": case_record.id if case_record else None,
                "case_no": case_record.serial_no if case_record else "",
                "case_title": case_record.title if case_record else contract.title,
                "plaintiff": str(case_data.get("plaintiff") or case_data.get("appellant_names") or contract.customer),
                "defendant": str(case_data.get("defendant") or case_data.get("appellee_names") or case_data.get("opponent") or ""),
                "case_stage": str(case_data.get("case_stage") or case_data.get("business_stage") or (case_record.status if case_record else "合同应收")),
                "submission_date": str(submitted_at)[:10],
                "fee_type": plan.phase,
                "total_amount": _round_fee_amount(plan.amount),
                "received_amount": _round_fee_amount(plan.received_amount),
                "remaining_amount": remaining,
            })
    # Some legacy case fees were created without a receivable-plan row.  They
    # are still payable case expenses and must appear in the same allocation
    # dialog, but only when their contract and case belong to the claimed
    # customer.
    plan_ids = {plan.id for plan in plans}
    fees = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance",
        or_(*customer_links),
        *(await _record_scope_conditions(identity, db)),
    ).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()))).all())
    for fee_record in fees:
        fee_data = fee_record.data or {}
        from app.core.finance_batch_parity import is_internal_fee
        if is_internal_fee(fee_data):
            continue
        if case_fees_only and fee_data.get("expense_scope") not in {"律所", "平台"}:
            continue
        fee_contract_id = int(fee_data.get("contract_id") or fee_data.get("contract_record_id") or 0)
        fee_contract_no = str(fee_data.get("contract_no") or "").strip()
        fee_case_id = int(fee_data.get("case_id") or fee_data.get("case_record_id") or 0)
        fee_case_no = str(fee_data.get("case_no") or "").strip()
        fee_cases = [case for case in cases if case.id == fee_case_id or (fee_case_no and case.serial_no == fee_case_no)]
        if case_fees_only and not (fee_case_id or fee_case_no):
            continue
        if fee_case_id or fee_case_no:
            fee_cases = [case for case in fee_cases if _case_is_for_allocation_customer(case, claimed_customer_record, item.claimed_customer)]
            if not fee_cases:
                continue
        contract = contracts_by_id.get(fee_contract_id)
        if contract is None and fee_contract_no:
            contract = next((item for item in contracts if item.serial_no == fee_contract_no), None)
        has_explicit_contract = bool(fee_contract_id or fee_contract_no)
        if contract is None and not has_explicit_contract and fee_cases:
            case_data = fee_cases[0].data or {}
            case_contract_id = int(case_data.get("contract_id") or case_data.get("contract_record_id") or 0)
            case_contract_no = str(case_data.get("contract_no") or "").strip()
            contract = contracts_by_id.get(case_contract_id)
            if contract is None and case_contract_no:
                contract = next((item for item in contracts if item.serial_no == case_contract_no), None)
        if contract is None or not _record_belongs_to_customer(fee_record, claimed_customer_record, item.claimed_customer):
            continue
        from app.core.finance_batch_parity import official_refund_progress
        refund_requested = float(fee_data.get("refund_amount") or fee_data.get("refund_requested_amount") or 0)
        refund_received = official_refund_progress(fee_data, refund_requested, float(fee_data.get("refunded_amount") or 0))
        refund_remaining = _round_fee_amount(max(0, refund_requested - refund_received))
        if "法院" in item.payer_name and refund_remaining > 0 and str(fee_data.get("fee_type")) in {"官方费用", "官费"}:
            rows.append({"key": f"refund:{fee_record.id}", "is_refund": True, "fee_record_id": fee_record.id,
                         "receivable_plan_id": None, "contract_id": contract.id, "contract_no": contract.serial_no,
                         "case_no": fee_case_no, "case_title": fee_record.title, "case_stage": fee_data.get("case_stage", ""),
                         "fee_type": "法院退费", "total_amount": float(fee_data.get("refund_amount") or fee_data.get("refund_requested_amount") or 0),
                         "received_amount": refund_received, "remaining_amount": refund_remaining})
        if not case_fees_only and fee_data.get("receivable_plan_id") and int(fee_data["receivable_plan_id"]) in plan_ids:
            continue
        total_amount = _round_fee_amount(float(fee_data.get("amount") or 0))
        received_amount = _round_fee_amount(float(fee_data.get("received_amount") or fee_data.get("cashed_amount") or 0))
        remaining = _round_fee_amount(total_amount - received_amount)
        if remaining <= 0:
            continue
        for case_record in (fee_cases or [None]):
            case_data = case_record.data or {} if case_record else {}
            rows.append({
                "key": f"fee:{fee_record.id}:{case_record.id if case_record else 0}",
                "receivable_plan_id": None,
                "fee_record_id": fee_record.id,
                "contract_id": contract.id,
                "contract_no": contract.serial_no,
                "case_id": case_record.id if case_record else None,
                "case_no": case_record.serial_no if case_record else fee_case_no,
                "case_title": case_record.title if case_record else fee_record.title,
                "plaintiff": str(case_data.get("plaintiff") or case_data.get("appellant_names") or contract.customer),
                "defendant": str(case_data.get("defendant") or case_data.get("appellee_names") or case_data.get("opponent") or ""),
                "case_stage": str(case_data.get("case_stage") or case_data.get("business_stage") or (case_record.status if case_record else "案件费用")),
                "submission_date": str(case_data.get("case_register_date") or case_data.get("submission_date") or "")[:10],
                "fee_type": _case_fee_display_type(fee_record),
                "total_amount": total_amount,
                "received_amount": received_amount,
                "remaining_amount": remaining,
            })
    return {
        "items": rows,
        "total": len(rows),
        "customer": item.claimed_customer,
        "remaining_amount": _round_fee_amount(item.amount - item.allocated_amount),
    }




@router.post(f"{settings.api_prefix}/finance/incoming-payments/{{payment_id}}/allocate")
async def allocate_incoming_payment(payment_id: int, body: IncomingPaymentAllocateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _case_is_for_allocation_customer,
    )
    from app.core.finance import (
        _incoming_payment_dict, _round_fee_amount, _settlement_amounts_for_fee,
    )
    from app.core.formatters import (
        _case_fee_display_type, _record_belongs_to_customer,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    item = await db.get(IncomingPayment, payment_id)
    if not item: raise HTTPException(status_code=404, detail="银行到账记录不存在")
    if item.status not in {"待分配", "部分分配"} or not item.claimed_customer: raise HTTPException(status_code=409, detail="到账认领到客户后才能分配")
    claimed_customer_record = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == "customer",
        BusinessRecord.title == item.claimed_customer,
        *(await _record_scope_conditions(identity, db)),
    ))
    total = _round_fee_amount(sum(entry.amount for entry in body.allocations)); remaining_payment = _round_fee_amount(item.amount - item.allocated_amount)
    if total > remaining_payment + 0.001: raise HTTPException(status_code=409, detail=f"分配金额超过到账未分配余额 {remaining_payment:.2f} 元")
    if any(entry.is_refund for entry in body.allocations):
        from app.core.finance_batch_parity import allocate_court_refund
        return await allocate_court_refund(item, body, claimed_customer_record, identity, db)
    prepared: list[tuple[IncomingPaymentAllocationItem, ReceivablePlan, BusinessRecord, BusinessRecord | None, BusinessRecord | None, list[dict]]] = []
    plan_totals: dict[int, float] = {}
    fee_totals: dict[int, float] = {}
    for entry in body.allocations:
        if entry.settlement_items:
            classified_total = _round_fee_amount(sum(item.amount for item in entry.settlement_items))
            if abs(classified_total - _round_fee_amount(entry.amount)) > 0.001:
                raise HTTPException(status_code=422, detail="结算费用明细金额之和必须等于本次分配金额")
        plan = await db.get(ReceivablePlan, entry.receivable_plan_id) if entry.receivable_plan_id else None
        fee_record = await _ensure_record_module(entry.fee_record_id, "finance", identity, db) if entry.fee_record_id else None
        from app.core.finance_batch_parity import is_internal_fee
        if body.case_fees_only:
            if not fee_record or (fee_record.data or {}).get("expense_scope") not in {"律所", "平台"}:
                raise HTTPException(422, "只能分配案件中的律所或平台费用")
            fd = fee_record.data or {}
            linked = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "case",
                BusinessRecord.id == int(fd.get("case_id") or fd.get("case_record_id") or 0) if fd.get("case_id") or fd.get("case_record_id") else BusinessRecord.serial_no == str(fd.get("case_no") or ""),
                *(await _record_scope_conditions(identity, db))))
            if not linked or not _case_is_for_allocation_customer(linked, claimed_customer_record, item.claimed_customer):
                raise HTTPException(422, "费用未关联当前客户的有效案件")
        if fee_record and is_internal_fee(fee_record.data or {}):
            raise HTTPException(status_code=422, detail="内部费用不能分配回款")
        if not plan and not fee_record:
            raise HTTPException(status_code=422, detail="分配项目必须关联应收计划或案件费用")
        if plan:
            contract = await _ensure_record_module(plan.contract_record_id, "contract", identity, db)
            phase = plan.phase
            remaining_plan = _round_fee_amount(plan.amount - plan.received_amount)
            plan_totals[plan.id] = _round_fee_amount(plan_totals.get(plan.id, 0) + entry.amount)
            if plan_totals[plan.id] > remaining_plan + 0.001: raise HTTPException(status_code=409, detail=f"{contract.serial_no}｜{phase} 分配金额合计超过未收 {remaining_plan:.2f} 元")
        else:
            fee_data = fee_record.data or {}
            contract_id = int(fee_data.get("contract_id") or fee_data.get("contract_record_id") or 0)
            contract_no = str(fee_data.get("contract_no") or "").strip()
            contract = await db.get(BusinessRecord, contract_id) if contract_id else None
            if not contract and contract_no:
                contract = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "contract", BusinessRecord.serial_no == contract_no))
            has_explicit_contract = bool(contract_id or contract_no)
            if not contract and not has_explicit_contract:
                fee_case_id = int(fee_data.get("case_id") or fee_data.get("case_record_id") or 0)
                fee_case_no = str(fee_data.get("case_no") or "").strip()
                linked_case = await db.get(BusinessRecord, fee_case_id) if fee_case_id else None
                if not linked_case and fee_case_no:
                    linked_case = await db.scalar(select(BusinessRecord).where(
                        BusinessRecord.module == "case",
                        BusinessRecord.serial_no == fee_case_no,
                        *(await _record_scope_conditions(identity, db)),
                    ))
                if linked_case and linked_case.module == "case":
                    linked_case_data = linked_case.data or {}
                    linked_contract_id = int(linked_case_data.get("contract_id") or linked_case_data.get("contract_record_id") or 0)
                    linked_contract_no = str(linked_case_data.get("contract_no") or "").strip()
                    contract = await db.get(BusinessRecord, linked_contract_id) if linked_contract_id else None
                    if not contract and linked_contract_no:
                        contract = await db.scalar(select(BusinessRecord).where(
                            BusinessRecord.module == "contract",
                            BusinessRecord.serial_no == linked_contract_no,
                        ))
            if not contract or contract.module != "contract":
                raise HTTPException(status_code=409, detail=f"费用 {fee_record.serial_no} 未关联有效合同")
            phase = str(fee_data.get("fee_type") or fee_record.title or "案件费用")
            fee_total = _round_fee_amount(float(fee_data.get("amount") or 0))
            fee_received = _round_fee_amount(float(fee_data.get("received_amount") or fee_data.get("cashed_amount") or 0))
            remaining_plan = _round_fee_amount(fee_total - fee_received)
            fee_totals[fee_record.id] = _round_fee_amount(fee_totals.get(fee_record.id, 0) + entry.amount)
            if fee_totals[fee_record.id] > remaining_plan + 0.001: raise HTTPException(status_code=409, detail=f"{fee_record.serial_no} 分配金额合计超过未收 {remaining_plan:.2f} 元")
            plan = ReceivablePlan(contract_record_id=contract.id, phase=phase, due_date=item.received_date, amount=fee_total, received_amount=fee_received, status="部分收款" if fee_received else "待收款", payer=item.claimed_customer, remark=f"案件费用 {fee_record.serial_no}")
            db.add(plan); await db.flush()
        if not _record_belongs_to_customer(contract, claimed_customer_record, item.claimed_customer): raise HTTPException(status_code=409, detail=f"应收项目 {phase} 的客户与到账认领客户不一致")
        case_record = None
        if entry.case_no.strip():
            case_record = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "case", BusinessRecord.serial_no == entry.case_no.strip(), *(await _record_scope_conditions(identity, db))))
            case_data = case_record.data or {} if case_record else {}
            linked_contract_id = int(case_data.get("contract_id") or case_data.get("contract_record_id") or 0)
            linked_contract_no = str(case_data.get("contract_no") or "").strip()
            case_contract_matches = linked_contract_id == contract.id or (
                not linked_contract_id and linked_contract_no == contract.serial_no
            )
            fee_data = fee_record.data or {} if fee_record else {}
            fee_case_id = int(fee_data.get("case_id") or fee_data.get("case_record_id") or 0)
            fee_case_no = str(fee_data.get("case_no") or "").strip()
            fee_contract_id = int(fee_data.get("contract_id") or fee_data.get("contract_record_id") or 0)
            fee_contract_no = str(fee_data.get("contract_no") or "").strip()
            fee_relation_matches = bool(
                case_record
                and (fee_case_id == case_record.id or (not fee_case_id and fee_case_no == case_record.serial_no))
                and (fee_contract_id == contract.id or (not fee_contract_id and fee_contract_no == contract.serial_no))
            )
            if not case_record or not (case_contract_matches or fee_relation_matches):
                raise HTTPException(status_code=409, detail=f"案件 {entry.case_no} 与当前应收项目的合同缺少有效关联")
            if not _record_belongs_to_customer(case_record, claimed_customer_record, item.claimed_customer):
                raise HTTPException(status_code=409, detail=f"案件 {entry.case_no} 的客户与到账认领客户不一致")
            if not _case_is_for_allocation_customer(case_record, claimed_customer_record, item.claimed_customer):
                raise HTTPException(status_code=409, detail=f"案件 {entry.case_no} 的诉讼当事人与到账认领客户不一致")
        canonical_settlement_items: list[dict] = []
        for settlement in entry.settlement_items:
            settlement_fee = fee_record
            if settlement.fee_record_id is None:
                settlement_fee = fee_record
            else:
                settlement_fee = await _ensure_record_module(settlement.fee_record_id, "finance", identity, db)
                fee_data = settlement_fee.data or {}
                if not _record_belongs_to_customer(settlement_fee, claimed_customer_record, item.claimed_customer):
                    raise HTTPException(status_code=409, detail=f"费用 {settlement_fee.serial_no} 的客户与到账认领客户不一致")
                if case_record and int(fee_data.get("case_id") or 0) not in {0, case_record.id} and str(fee_data.get("case_no") or "") != case_record.serial_no:
                    raise HTTPException(status_code=409, detail=f"费用 {settlement_fee.serial_no} 不属于案件 {case_record.serial_no}")
            fee_type = _case_fee_display_type(settlement_fee) if settlement_fee else settlement.fee_type
            settlement_amount, archive_fee = _settlement_amounts_for_fee(
                settlement_fee, fee_type, _round_fee_amount(settlement.amount), case_record,
            )
            canonical_settlement_items.append({
                "fee_record_id": settlement_fee.id if settlement_fee else None,
                "fee_type": fee_type,
                "amount": _round_fee_amount(settlement.amount),
                "settlement_amount": settlement_amount,
                "archive_fee": archive_fee,
            })
        prepared.append((entry, plan, contract, case_record, fee_record, canonical_settlement_items))
    allocation_rows = list(item.allocations or [])
    for entry, plan, contract, case_record, fee_record, canonical_settlement_items in prepared:
        amount = _round_fee_amount(entry.amount); plan.received_amount = _round_fee_amount(plan.received_amount + amount); plan.status = "已收款" if plan.received_amount + 0.001 >= plan.amount else "部分收款"
        if fee_record:
            fee_data = dict(fee_record.data or {})
            fee_data["received_amount"] = _round_fee_amount(float(fee_data.get("received_amount") or fee_data.get("cashed_amount") or 0) + amount)
            fee_data["received_at"] = item.received_date.isoformat()
            fee_data["cashed_date"] = item.received_date.isoformat()
            fee_data["incoming_payment_id"] = item.id
            fee_data["receipt_no"] = item.receipt_no
            fee_record.data = fee_data
        tx = FinanceTransaction(finance_record_id=contract.id, transaction_type="回款", amount=amount, transaction_date=item.received_date, voucher_no=item.bank_reference, counterparty=item.payer_name, operator=identity["username"], remark=f"银行到账 {item.receipt_no} 分配至 {contract.serial_no}｜{plan.phase}" + (f"｜案件 {case_record.serial_no}" if case_record else ""))
        db.add(tx); await db.flush(); row = {"receivable_plan_id": plan.id, "fee_record_id": fee_record.id if fee_record else None, "contract_id": contract.id, "contract_no": contract.serial_no, "phase": plan.phase, "case_id": case_record.id if case_record else None, "case_no": case_record.serial_no if case_record else "", "amount": amount, "payment_method": entry.payment_method.strip(), "settlement_items": canonical_settlement_items, "transaction_id": tx.id, "allocated_by": identity["username"], "allocated_at": datetime.now().isoformat(timespec="seconds")}; allocation_rows.append(row)
        db.add(WorkflowEvent(record_id=contract.id, action="分配银行回款", from_status=contract.status, to_status=contract.status, operator=identity["username"], comment=f"{item.receipt_no}｜{plan.phase}｜{amount:.2f} 元。{body.comment}"))
    item.allocated_amount = _round_fee_amount(item.allocated_amount + total); item.allocations = allocation_rows; item.status = "已分配" if item.allocated_amount + 0.001 >= item.amount else "部分分配"
    await db.commit(); await db.refresh(item); return _incoming_payment_dict(item, show_amount="finance.amount" in await _allowed_field_keys(identity, db))


@router.delete(f"{settings.api_prefix}/finance/incoming-payments/{{payment_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_incoming_payment(payment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    if identity.get("role") != "admin": raise HTTPException(status_code=403, detail="仅管理员可删除银行到账")
    item = await db.get(IncomingPayment, payment_id)
    if not item: raise HTTPException(status_code=404, detail="银行到账记录不存在")
    active_settlement = (await _active_settlements_by_receipt(db, {item.id})).get(item.id)
    if active_settlement:
        raise HTTPException(status_code=409, detail=f"到账已关联{active_settlement.status}结算 {active_settlement.serial_no}，不能删除")
    for allocation in item.allocations or []:
        await _revert_incoming_allocation(allocation, db, payment_id=item.id)
    await db.delete(item); await db.commit(); return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(f"{settings.api_prefix}/finance/incoming-payments/{{payment_id}}")
async def update_incoming_payment(payment_id: int, body: IncomingPaymentUpdateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _incoming_payment_dict, _round_fee_amount,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    if identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以编辑银行到账")
    item = await db.scalar(select(IncomingPayment).where(IncomingPayment.id == payment_id).with_for_update())
    if not item: raise HTTPException(status_code=404, detail="银行到账记录不存在")
    if identity.get("role") != "admin" and item.operator != identity["username"] and item.claimant != identity["username"]:
        visible_customer = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.module == "customer", BusinessRecord.title == item.claimed_customer, *(await _record_scope_conditions(identity, db))))
        if not visible_customer:
            raise HTTPException(status_code=403, detail="无权编辑该回款")
    if "finance.amount" not in await _allowed_field_keys(identity, db):
        raise HTTPException(status_code=403, detail="当前账号没有回款金额权限")
    if item.source_kind != "manual":
        raise HTTPException(status_code=403, detail="仅手动新增的回款可以编辑，导入或来源未确认的记录不可编辑")
    allocated = max(float(item.allocated_amount or 0), sum(float(row.get("amount") or 0) for row in (item.allocations or []) if isinstance(row, dict)))
    if _round_fee_amount(body.amount) < _round_fee_amount(allocated):
        raise HTTPException(status_code=422, detail="回款金额不能小于已分配金额")
    if allocated and (body.contract_no.strip() != (item.contract_no or "") or body.case_no.strip() != (item.case_no or "") or body.customer.strip() != (item.claimed_customer or "")):
        raise HTTPException(status_code=409, detail="已分配回款不能更换客户、合同或案件")
    bank_reference = body.bank_reference.strip()
    if bank_reference and await db.scalar(select(IncomingPayment.id).where(IncomingPayment.bank_reference == bank_reference, IncomingPayment.id != payment_id)): raise HTTPException(status_code=409, detail="银行流水号已经登记")
    contract_no = body.contract_no.strip(); case_no = body.case_no.strip(); customer = body.customer.strip(); contract = None
    if contract_no:
        contract = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "contract", BusinessRecord.serial_no == contract_no))
        if not contract: raise HTTPException(status_code=422, detail="关联合同不存在")
        if customer and contract.customer != customer: raise HTTPException(status_code=422, detail="关联合同与所选客户不一致")
        customer = customer or contract.customer
    if case_no:
        case_record = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "case", BusinessRecord.serial_no == case_no, *(await _record_scope_conditions(identity, db))))
        if not case_record: raise HTTPException(status_code=422, detail="关联案件不存在或无权查看")
        linked_contract_id = int((case_record.data or {}).get("contract_id") or 0)
        if contract:
            if linked_contract_id and linked_contract_id != contract.id:
                raise HTTPException(status_code=422, detail="关联案件不属于所选合同")
        elif linked_contract_id:
            contract = await db.get(BusinessRecord, linked_contract_id)
            if not contract or contract.module != "contract":
                raise HTTPException(status_code=422, detail="关联案件的合同不存在")
            contract_no = contract.serial_no
        customer = customer or case_record.customer
    item.received_date = body.received_date; item.amount = _round_fee_amount(body.amount); item.payer_name = body.payer_name.strip(); item.bank_reference = bank_reference or None; item.contract_record_id = contract.id if contract else None; item.contract_no = contract.serial_no if contract else ""; item.case_no = case_no; item.bank_source = body.bank_source.strip(); item.remark = body.remark
    if not allocated:
        item.claimed_customer = customer
        item.claimant = (item.claimant or identity["username"]) if customer else ""
    item.status = ("已分配" if allocated >= item.amount else "部分分配") if allocated else ("待分配" if item.claimed_customer else "待认领")
    await db.commit(); await db.refresh(item); return _incoming_payment_dict(item, show_amount="finance.amount" in await _allowed_field_keys(identity, db))


@router.get(f"{settings.api_prefix}/finance/incoming-payments/{{payment_id}}/refund-candidates")
async def incoming_payment_refund_candidates(payment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _round_fee_amount,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    item = await db.get(IncomingPayment, payment_id)
    if not item: raise HTTPException(status_code=404, detail="银行到账记录不存在")
    if item.allocations or item.allocated_amount > 0: raise HTTPException(status_code=409, detail="已发生分配的到账不能领取退费")
    if "法院" not in item.payer_name: raise HTTPException(status_code=422, detail="只有法院退款到账可以匹配官方费用")
    remaining = _round_fee_amount(item.amount - item.allocated_amount)
    fees = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "finance", *(await _record_scope_conditions(identity, db))))).all()
    candidates = []
    for fee in fees:
        data = fee.data or {}
        if str(data.get("fee_type") or "") != "官方费用": continue
        if fee.status not in {"已付款", "部分付款"}: continue
        court = str(data.get("court") or "").strip()
        if court and court not in item.payer_name and item.payer_name not in court: continue
        amount = _round_fee_amount(float(data.get("amount") or 0))
        candidates.append({"fee_record_id": fee.id, "serial_no": fee.serial_no, "title": fee.title, "case_no": data.get("case_no", ""), "court": court or item.payer_name, "amount": amount, "match_amount": _round_fee_amount(min(amount, remaining))})
    return {"items": candidates, "total": len(candidates), "remaining_amount": remaining}


@router.post(f"{settings.api_prefix}/finance/incoming-payments/{{payment_id}}/refund-claim")
async def refund_claim_incoming_payment(payment_id: int, body: IncomingPaymentRefundClaimInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _incoming_payment_dict,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    item = await db.get(IncomingPayment, payment_id)
    if not item: raise HTTPException(status_code=404, detail="银行到账记录不存在")
    if item.status not in {"待认领", "待分配"} or item.allocated_amount > 0: raise HTTPException(status_code=409, detail="已发生分配的到账不能重新认领")
    if "法院" not in item.payer_name: raise HTTPException(status_code=422, detail="只有法院退款到账可以领取退费")
    customer = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "customer", BusinessRecord.title == body.customer.strip(), *(await _record_scope_conditions(identity, db))))
    if not customer: raise HTTPException(status_code=404, detail="客户不存在或无权认领")
    fee_record = None
    if body.fee_record_id:
        fee_record = await _ensure_record_module(body.fee_record_id, "finance", identity, db)
        if str((fee_record.data or {}).get("fee_type") or "") != "官方费用": raise HTTPException(status_code=422, detail="匹配的退费记录不是官方费用")
    item.claimed_customer = customer.title; item.claimant = identity["username"]; item.status = "待分配"; item.remark = "；".join(part for part in [item.remark, body.comment] if part)
    db.add(WorkflowEvent(record_id=customer.id, action="认领退费到账", from_status=customer.status, to_status=customer.status, operator=identity["username"], comment=f"{item.receipt_no}｜{item.payer_name}｜{item.amount:.2f} 元。{body.comment}"))
    if fee_record:
        db.add(WorkflowEvent(record_id=fee_record.id, action="匹配退费到账", from_status=fee_record.status, to_status=fee_record.status, operator=identity["username"], comment=f"{item.receipt_no} 匹配 {fee_record.serial_no}"))
    await db.commit(); await db.refresh(item); return _incoming_payment_dict(item, show_amount="finance.amount" in await _allowed_field_keys(identity, db))


@router.post(f"{settings.api_prefix}/finance/incoming-payments/revoke-allocations")
async def revoke_incoming_payment_allocations(body: IncomingPaymentRevokeInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _incoming_payment_dict,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    if identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以批量撤销分配")
    payment_ids = list(dict.fromkeys(body.payment_ids))
    items = list((await db.scalars(select(IncomingPayment).where(IncomingPayment.id.in_(payment_ids)))).all())
    if len(items) != len(payment_ids): raise HTTPException(status_code=404, detail="部分银行到账记录不存在")
    active_settlements = await _active_settlements_by_receipt(db, set(payment_ids))
    if active_settlements:
        blocked = [f"{item.receipt_no}（{active_settlements[item.id].status}）" for item in items if item.id in active_settlements]
        raise HTTPException(status_code=409, detail="以下到账已有有效结算，不能撤销分配：" + "、".join(blocked))
    revoked = 0
    for item in items:
        if not (item.allocations or item.allocated_amount > 0):
            continue
        for allocation in item.allocations or []:
            plan = await db.get(ReceivablePlan, int(allocation.get("receivable_plan_id") or 0)); amount = float(allocation.get("amount") or 0)
            contract = await db.get(BusinessRecord, int(allocation.get("contract_id") or 0))
            if contract:
                db.add(WorkflowEvent(record_id=contract.id, action="撤销银行回款分配", from_status=contract.status, to_status=contract.status, operator=identity["username"], comment=f"{item.receipt_no}｜{plan.phase if plan else ''}｜{amount:.2f} 元。{body.comment}"))
            await _revert_incoming_allocation(allocation, db, payment_id=item.id)
        item.allocations = []; item.allocated_amount = 0; item.status = "待分配"
        revoked += 1
    await db.commit()
    for item in items:
        await db.refresh(item)
    return {"revoked": revoked, "items": [_incoming_payment_dict(item, show_amount="finance.amount" in await _allowed_field_keys(identity, db)) for item in items]}


@router.get(f"{settings.api_prefix}/finance/incoming-payments/{{payment_id}}/allocation-records")
async def get_allocation_records(payment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.incoming_allocation_records import allocation_records
    return await allocation_records(payment_id, identity, db)


@router.post(f"{settings.api_prefix}/finance/incoming-payments/{{payment_id}}/allocation-records/cancel")
async def cancel_selected_allocations(payment_id: int, body: AllocationCancelInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.incoming_allocation_records import cancel_allocation_records
    return await cancel_allocation_records(payment_id, body, identity, db)
