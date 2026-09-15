"""Ordinary payment submission and voucher writeoff as one audited workflow."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from app.core.dependencies import (AsyncSession, BusinessRecord, FileAttachment, FinanceTransaction,
    WorkflowEvent, current_identity, get_db, select, settings, date, datetime, Path, uuid4)
from app.core.constants import UPLOAD_ROOT
from app.core.permissions import _ensure_record_visible, _record_dict_for_identity, _require_contract_action
from app.core.finance_batch_parity import is_internal_fee

router = APIRouter()

class PaymentBatchInput(BaseModel):
    record_ids: list[int] = Field(min_length=1, max_length=100)


@router.post(f'{settings.api_prefix}/finance/payment-workflow/submit-batch')
async def submit_payment_batch(body: PaymentBatchInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    rows = [await payment_record(record_id, identity, db) for record_id in sorted(set(body.record_ids))]
    if any(row.status not in {'已审批', '待付款'} or (row.data or {}).get('writeoff_status') in {'待核销', '已核销'} for row in rows):
        raise HTTPException(409, '只能合并待付款申请')
    payees = {str((row.data or {}).get('payee') or row.customer).strip() for row in rows}
    banks = {(str((row.data or {}).get('account_bank') or (row.data or {}).get('bank_name') or ''), str((row.data or {}).get('account') or (row.data or {}).get('bank_account') or '')) for row in rows}
    if len(payees) != 1 or len(banks) != 1:
        raise HTTPException(422, '只能合并相同收款单位与银行账号的付款申请')
    for row in rows:
        if row.module == 'contract_payment':
            from app.core.contract_payment_lifecycle import ensure_unsettled
            await _require_contract_action(identity, db, 'contract.payment.pay', '办理付款')
            await ensure_unsettled(row, db)
    details = [{**(row.data or {}), 'id': row.id, 'request_no': row.serial_no} for row in rows]
    total = round(sum(float((row.data or {}).get('amount') or 0) for row in rows), 2)
    number = f'P{datetime.now():%y%m%d}-{uuid4().hex[:8]}'
    package = BusinessRecord(module='finance_package', serial_no=number, title='付款申请单', customer=rows[0].customer,
        owner=identity['username'], department=rows[0].department, status='待核销',
        data={**(rows[0].data or {}), 'fee_ids':[row.id for row in rows], 'items':details, 'amount':total,
              'total_amount':total, 'fee_type':'普通付款包', 'payment_status':'待核销', 'payment_package_no':number})
    db.add(package); await db.flush()
    for row in rows:
        previous=row.status; row.status='待核销'
        row.data={**(row.data or {}),'payment_status':'待核销','writeoff_status':'待核销','payment_package_id':package.id,'payment_package_no':number}
        db.add(WorkflowEvent(record_id=row.id,action='合并提交付款单',from_status=previous,to_status='待核销',operator=identity['username'],comment=number))
    await db.commit(); await db.refresh(package)
    return await _record_dict_for_identity(package,identity,db)


async def payment_record(record_id, identity, db, allow_package=False):
    row = await _ensure_record_visible(record_id, identity, db)
    if not (allow_package and row.module == 'finance_package') and (row.module not in {'finance', 'contract_payment'} or is_internal_fee(row.data or {})):
        raise HTTPException(422, '请选择普通费用或合同付款申请')
    if identity.get('role') not in {'admin', 'manager', 'auditor'}:
        raise HTTPException(403, '当前角色没有付款办理权限')
    if row.module == 'contract_payment':
        from app.core.contract_payment_lifecycle import locked_payment
        row, _ = await locked_payment(record_id, identity, db)
    else:
        await db.refresh(row, with_for_update=True)
    return row


@router.post(f'{settings.api_prefix}/finance/payment-workflow/{{record_id}}/submit')
async def submit_payment(record_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    row = await payment_record(record_id, identity, db)
    data = dict(row.data or {})
    if row.module == 'contract_payment':
        from app.core.contract_payment_lifecycle import ensure_unsettled
        await _require_contract_action(identity, db, 'contract.payment.pay', '办理付款')
        await ensure_unsettled(row, db)
    if row.status not in {'已审批', '待付款'} or data.get('writeoff_status') in {'待核销', '已核销'}:
        raise HTTPException(409, '仅待付款申请可以提交')
    previous = row.status
    row.status = '待核销'
    row.data = {**data, 'payment_status': '待核销', 'writeoff_status': '待核销',
                'payment_package_no': f'P{datetime.now():%y%m%d}-{uuid4().hex[:8]}',
                'payment_submitted_at': datetime.now().isoformat(), 'payment_submitted_by': identity['username']}
    db.add(WorkflowEvent(record_id=row.id, action='提交付款单', from_status=previous, to_status=row.status,
                         operator=identity['username'], comment='付款申请单提交至待核销'))
    await db.commit()
    await db.refresh(row)
    return await _record_dict_for_identity(row, identity, db)


@router.post(f'{settings.api_prefix}/finance/payment-workflow/{{record_id}}/writeoff')
async def writeoff_payment(record_id: int, paid_date: date = Form(...), amount: float = Form(...),
    payment_method: str = Form(...), invoice_no: str = Form(...), remark: str = Form(''),
    files: list[UploadFile] = File(...), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    row = await payment_record(record_id, identity, db, allow_package=True)
    data = dict(row.data or {})
    if row.module == 'contract_payment':
        await _require_contract_action(identity, db, 'contract.payment.writeoff', '核销付款')
    if row.status != '待核销' or data.get('writeoff_status') == '已核销':
        raise HTTPException(409, '仅待核销付款申请可以核销')
    if not invoice_no.strip() or payment_method not in {'自动扣款', '银行卡', '现金'}:
        raise HTTPException(422, '请填写付款方式和付款单据号')
    from math import isfinite
    if not isfinite(amount) or amount <= 0 or abs(round(amount, 2) - round(float(data.get('amount') or 0), 2)) > .001:
        raise HTTPException(409, '确认付款金额必须等于申请金额')
    if not files or len(files) > 10:
        raise HTTPException(422, '请上传1至10个付款凭证')
    contents = []
    for upload in files:
        content = await upload.read(20 * 1024 * 1024 + 1)
        if not content or len(content) > 20 * 1024 * 1024:
            raise HTTPException(422, '付款凭证不能为空且每个不能超过20MB')
        contents.append((upload, content))
    linked_fees = [row] if row.module == 'finance' else []
    if row.module == 'finance_package':
        for fee_id in data.get('fee_ids', []):
            fee = await _ensure_record_visible(int(fee_id), identity, db)
            if fee.module not in {'finance', 'contract_payment'} or fee.status != '待核销' or int((fee.data or {}).get('payment_package_id') or 0) != row.id:
                raise HTTPException(409, '付款包费用关联不一致')
            if fee.module == 'contract_payment':
                await _require_contract_action(identity, db, 'contract.payment.writeoff', '核销付款')
            linked_fees.append(fee)
    if row.module == 'finance_package' and not linked_fees:
        raise HTTPException(409, '付款包费用为空')
    invoice_targets = list(linked_fees)
    for payment in linked_fees if row.module == 'finance_package' else []:
        if payment.module == 'contract_payment':
            for line in (payment.data or {}).get('lines', []):
                fee_id = int(line.get('case_fee_id') or 0)
                if fee_id:
                    fee = await _ensure_record_visible(fee_id, identity, db)
                    if fee.module != 'finance':
                        raise HTTPException(409, '合同付款费用关联无效')
                    invoice_targets.append(fee)
    if row.module == 'contract_payment':
        # The authoritative request snapshot carries the source case fee IDs.
        ids = {int(line.get('case_fee_id') or line.get('fee_record_id') or 0) for line in data.get('lines', [])}
        ids.discard(0)
        for fee_id in ids:
            fee = await _ensure_record_visible(fee_id, identity, db)
            if fee.module != 'finance':
                raise HTTPException(409, '合同付款费用关联无效')
            linked_fees.append(fee)
    invoice = BusinessRecord(module='invoice', serial_no=f'FP{uuid4().hex}', title=f'付款凭证 {invoice_no.strip()}',
        customer=row.customer, owner=row.owner, department=row.department, status='已开票',
        data={'invoice_no': invoice_no.strip(), 'amount': amount, 'case_no': data.get('case_no', ''),
              'finance_record_id': row.id, 'invoice_date': str(paid_date), 'purpose': '付款凭证'})
    db.add(invoice)
    await db.flush()
    paths = []
    try:
        folder = Path(UPLOAD_ROOT) / 'payment-vouchers'
        folder.mkdir(parents=True, exist_ok=True)
        for upload, content in contents:
            name = Path(upload.filename or 'voucher').name
            stored = uuid4().hex + Path(name).suffix
            path = folder / stored
            paths.append(path)
            path.write_bytes(content)
            db.add(FileAttachment(record_id=invoice.id, category='付款凭证', original_name=name, stored_name=stored,
                content_type=upload.content_type or 'application/octet-stream', size=len(content), path=str(path),
                uploader=identity['username'], remark=f'付款单 {row.serial_no}'))
        row.status = '已付款'
        row.data = {**data, 'payment_status': '已付款', 'writeoff_status': '已核销', 'paid_amount': amount,
                    'payment_date': str(paid_date), 'paid_date': str(paid_date), 'payment_method': payment_method,
                    'invoice_no': invoice_no.strip(), 'writeoff_voucher_no': invoice_no.strip(),
                    'invoice_record_id': invoice.id, 'written_off_at': datetime.now().isoformat(),
                    'written_off_by': identity['username']}
        for fee in linked_fees:
            fee.data = {**(fee.data or {}), 'invoice_no': invoice_no.strip(), 'invoice_record_id': invoice.id}
            if row.module == 'finance_package':
                fee.status = '已付款'
                fee.data = {**fee.data, 'payment_status': '已付款', 'writeoff_status': '已核销',
                            'paid_amount': fee.data.get('actual_commission', fee.data.get('amount', 0)),
                            'paid_date': str(paid_date), 'payment_date': str(paid_date),
                            'writeoff_voucher_no': invoice_no.strip()}
                db.add(WorkflowEvent(record_id=fee.id, action='付款包核销', from_status='待核销', to_status='已付款', operator=identity['username'], comment=row.serial_no))
        for target in invoice_targets:
            target.data = {**(target.data or {}), 'invoice_no':invoice_no.strip(), 'invoice_record_id':invoice.id}
        for target in linked_fees if row.module == 'finance_package' else [row]:
            tx_amount = float((target.data or {}).get('paid_amount') or (target.data or {}).get('amount') or 0) if row.module == 'finance_package' else amount
            db.add(FinanceTransaction(finance_record_id=target.id, transaction_type='合同付款' if target.module == 'contract_payment' else '付款',
                amount=tx_amount, transaction_date=paid_date, voucher_no=invoice_no.strip(), counterparty=str(data.get('payee') or row.customer),
                operator=identity['username'], remark=remark))
        db.add(WorkflowEvent(record_id=row.id, action='付款核销', from_status='待核销', to_status='已付款', operator=identity['username'], comment=remark))
        await db.commit()
    except Exception:
        await db.rollback()
        for path in paths:
            path.unlink(missing_ok=True)
        raise
    await db.refresh(row)
    return await _record_dict_for_identity(row, identity, db)
