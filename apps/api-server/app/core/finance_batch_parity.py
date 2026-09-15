"""Shared classifications and application projection for the 9.15 batch."""
from collections import OrderedDict


def is_internal_fee(data: dict) -> bool:
    return (str(data.get('expense_scope') or '') == '内部'
            or str(data.get('fee_type') or '') in {'内部费用', '内部提成', 'INTERNAL'}
            or bool(data.get('commission_lifecycle')))


def group_commission_applications(rows: list[dict]) -> list[dict]:
    groups = OrderedDict()
    for row in rows:
        data = row.get('data') or {}
        number = str(data.get('payment_application_no') or '').strip()
        key = (number, data.get('case_no'), data.get('source_fee_id'), data.get('applicant')) if number else ('single', row['id'])
        groups.setdefault(key, []).append(row)
    result = []
    for items in groups.values():
        first = items[0]
        data = first.get('data') or {}
        if not data.get('payment_application_no'):
            result.append(first)
            continue
        states = list(dict.fromkeys(item['status'] for item in items))
        amount = None if any(item['data'].get('amount') is None for item in items) else round(sum(float(item['data']['amount']) for item in items), 2)
        result.append({**first, 'serial_no': data['payment_application_no'],
                       'status': states[0] if len(states) == 1 else '部分处理',
                       'data': {**data, 'amount': amount, 'application_items': items,
                                'payment_status': states[0] if len(states) == 1 else '部分处理',
                                'fee_type': '内部费用', 'commission_type': '提成申请汇总'}})
    return result


async def allocate_court_refund(payment, body, customer, identity, db):
    from app.core.dependencies import HTTPException, FinanceTransaction, WorkflowEvent, datetime
    from app.core.permissions import _ensure_record_module
    from app.core.formatters import _record_belongs_to_customer
    from app.core.finance import _round_fee_amount, _incoming_payment_dict
    from app.core.system import _allowed_field_keys
    if not all(entry.is_refund for entry in body.allocations):
        raise HTTPException(422, "法院退费与普通回款请分别分配")
    if "法院" not in payment.payer_name:
        raise HTTPException(422, "只有法院退费到账可以分配退费")
    totals, fees = {}, {}
    for entry in body.allocations:
        if not entry.fee_record_id or entry.receivable_plan_id:
            raise HTTPException(422, "法院退费必须关联案件官费")
        fee = await _ensure_record_module(entry.fee_record_id, 'finance', identity, db)
        data = fee.data or {}
        if body.case_fees_only and data.get('expense_scope') not in {'律所', '平台'}:
            raise HTTPException(422, "法院退费必须关联律所或平台案件官费")
        if is_internal_fee(data) or data.get('fee_type') not in {'官方费用', '官费'}:
            raise HTTPException(422, "法院退费必须关联案件官费")
        if not _record_belongs_to_customer(fee, customer, payment.claimed_customer):
            raise HTTPException(409, "退费费用不属于当前认领客户")
        if not data.get('case_id') and not data.get('case_no'):
            raise HTTPException(422, "退费费用未关联案件")
        if entry.case_no and entry.case_no != data.get('case_no'):
            raise HTTPException(409, "退费案件关联不一致")
        totals[fee.id] = _round_fee_amount(totals.get(fee.id, 0) + entry.amount)
        remaining = _round_fee_amount(float(data.get('refund_amount') or data.get('refund_requested_amount') or 0) - float(data.get('refunded_amount') or 0))
        if totals[fee.id] > remaining + .001:
            raise HTTPException(409, "分配金额超过剩余未退金额")
        fees[fee.id] = fee
    allocations = list(payment.allocations or [])
    for fee_id, amount in totals.items():
        fee = fees[fee_id]
        data = dict(fee.data or {})
        data.update(refunded_amount=_round_fee_amount(float(data.get('refunded_amount') or 0) + amount),
                    received_amount=_round_fee_amount(float(data.get('received_amount') or data.get('cashed_amount') or 0) + amount),
                    received_at=str(payment.received_date), cashed_date=str(payment.received_date),
                    incoming_payment_id=payment.id, receipt_no=payment.receipt_no)
        fee.data = data
        tx = FinanceTransaction(finance_record_id=fee.id, transaction_type='法院退费', amount=amount,
                                transaction_date=payment.received_date, voucher_no=payment.bank_reference,
                                counterparty=payment.payer_name, operator=identity['username'], remark=body.comment)
        db.add(tx)
        await db.flush()
        allocations.append(dict(is_refund=True, fee_record_id=fee.id, case_no=data.get('case_no', ''),
                                amount=amount, transaction_id=tx.id, allocated_by=identity['username'],
                                allocated_at=datetime.now().isoformat()))
        db.add(WorkflowEvent(record_id=fee.id, action='分配法院退费', from_status=fee.status, to_status=fee.status,
                             operator=identity['username'], comment=f'{payment.receipt_no}｜{amount:.2f}'))
    payment.allocations = allocations
    payment.allocated_amount = _round_fee_amount(payment.allocated_amount + sum(totals.values()))
    payment.status = '已分配' if payment.allocated_amount + .001 >= payment.amount else '部分分配'
    await db.commit()
    await db.refresh(payment)
    return _incoming_payment_dict(payment, show_amount='finance.amount' in await _allowed_field_keys(identity, db))
