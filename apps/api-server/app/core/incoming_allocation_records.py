"""回款分配明细读取与按选中项撤销。"""
import hashlib
import json
import math
from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from app.models import BusinessRecord, IncomingPayment, ReceivablePlan, WorkflowEvent


class AllocationCancelInput(BaseModel):
    revision: str
    indexes: list[int] = Field(min_length=1, max_length=100)
    comment: str = Field(default='', max_length=2000)


def allocation_revision(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


async def authorized_payment(payment_id, identity, db, *, lock=False):
    from app.core.permissions import _record_scope_conditions
    from app.core.system import _allowed_field_keys
    stmt = select(IncomingPayment).where(IncomingPayment.id == payment_id)
    payment = await db.scalar(stmt.with_for_update() if lock else stmt)
    if payment is None:
        raise HTTPException(404, '银行到账记录不存在')
    if identity.get('role') != 'admin' and identity['username'] not in {payment.operator, payment.claimant}:
        customer = await db.scalar(select(BusinessRecord.id).where(
            BusinessRecord.module == 'customer', BusinessRecord.title == payment.claimed_customer,
            *(await _record_scope_conditions(identity, db)),
        ))
        if not customer:
            raise HTTPException(403, '无权查看该回款分配记录')
    if 'finance.amount' not in await _allowed_field_keys(identity, db):
        raise HTTPException(403, '当前账号没有回款金额权限')
    return payment


async def allocation_records(payment_id, identity, db):
    from app.core.finance import _incoming_payment_dict
    from app.core.formatters import _case_fee_display_type, _user_display_map
    payment = await authorized_payment(payment_id, identity, db)
    records = []
    for index, allocation in enumerate(payment.allocations or []):
        fee = await db.get(BusinessRecord, int(allocation.get('fee_record_id') or 0))
        case = await db.get(BusinessRecord, int(allocation.get('case_id') or 0))
        case_data = (case.data or {}) if case else {}
        fee_data = (fee.data or {}) if fee else {}
        total = float(fee_data.get('amount') or 0) if fee else None
        received = float(fee_data.get('received_amount') or fee_data.get('cashed_amount') or 0) if fee else None
        records.append({**allocation, 'index': index,
            'fee_type': _case_fee_display_type(fee) if fee else allocation.get('phase', ''),
            'case_stage': case.status if case else '',
            'plaintiff': (case.data or {}).get('plaintiff', case.customer) if case else '',
            'defendant': case_data.get('defendant') or case_data.get('opponent', ''),
            'case_title': case.title if case else '', 'case_type': case_data.get('case_type', ''),
            'court_keywords': ' '.join(str(value) for key, value in case_data.items() if 'court' in key and isinstance(value, str)),
            'fee_amount': total, 'fee_received': received,
            'fee_remaining': round(max(total - received, 0), 2) if fee else None,
        })
    users = await _user_display_map({payment.claimant, payment.operator}, db)
    return {'payment': _incoming_payment_dict(payment, users_by_username=users), 'items': records,
            'revision': allocation_revision(payment.allocations or []),
            'can_cancel': identity.get('role') in {'admin', 'manager'}}


async def cancel_allocation_records(payment_id, body, identity, db):
    from app.areas.finance.router import _active_settlements_by_receipt, _revert_incoming_allocation
    from app.core.finance import _round_fee_amount
    if identity.get('role') not in {'admin', 'manager'}:
        raise HTTPException(403, '当前账号没有取消分配权限')
    payment = await authorized_payment(payment_id, identity, db, lock=True)
    rows = list(payment.allocations or [])
    if allocation_revision(rows) != body.revision:
        raise HTTPException(409, '分配记录已变更，请刷新后重新选择')
    indexes = set(body.indexes)
    if len(indexes) != len(body.indexes) or any(index < 0 or index >= len(rows) for index in indexes):
        raise HTTPException(422, '选择的分配记录无效')
    if await _active_settlements_by_receipt(db, {payment.id}):
        raise HTTPException(409, '该回款已有有效结算，不能取消分配')
    selected = [row for index, row in enumerate(rows) if index in indexes]
    remaining = [row for index, row in enumerate(rows) if index not in indexes]
    if any(not math.isfinite(float(row.get('amount') or 0)) or float(row.get('amount') or 0) <= 0 for row in selected):
        raise HTTPException(409, '分配金额无效，不能取消分配')
    for key in ('receivable_plan_id', 'fee_record_id'):
        totals = {}
        for row in selected:
            if row.get(key):
                totals[int(row[key])] = totals.get(int(row[key]), 0) + float(row['amount'])
        for record_id, amount in totals.items():
            record = await db.get(ReceivablePlan if key == 'receivable_plan_id' else BusinessRecord, record_id)
            if record is None:
                raise HTTPException(409, '分配关联记录缺失，不能取消分配')
            balance = record.received_amount if key == 'receivable_plan_id' else float((record.data or {}).get('received_amount') or (record.data or {}).get('cashed_amount') or 0)
            if balance + 0.001 < amount:
                raise HTTPException(409, '关联费用到账金额与分配记录不一致，不能取消分配')
    for row in selected:
        await _revert_incoming_allocation(row, db, payment_id=payment.id)
        contract = await db.get(BusinessRecord, int(row.get('contract_id') or 0))
        if contract:
            db.add(WorkflowEvent(record_id=contract.id, action='取消回款明细分配', from_status=contract.status,
                to_status=contract.status, operator=identity['username'],
                comment=f"{payment.receipt_no}｜费用{row.get('fee_record_id') or ''}｜{float(row['amount']):.2f}元。{body.comment}"))
    for row in remaining:
        fee = await db.get(BusinessRecord, int(row.get('fee_record_id') or 0))
        if fee and any(item.get('fee_record_id') == fee.id for item in selected):
            latest_id = int((fee.data or {}).get('incoming_payment_id') or 0)
            latest = await db.get(IncomingPayment, latest_id) if latest_id else None
            if latest and (latest.received_date, latest.id) > (payment.received_date, payment.id):
                continue
            fee.data = {**(fee.data or {}), 'incoming_payment_id': payment.id, 'receipt_no': payment.receipt_no,
                        'received_at': str(payment.received_date), 'cashed_date': str(payment.received_date)}
    payment.allocations = remaining
    payment.allocated_amount = _round_fee_amount(sum(float(row['amount']) for row in remaining))
    payment.status = '已分配' if payment.allocated_amount + 0.001 >= payment.amount else '部分分配' if remaining else '待分配'
    await db.commit()
    return await allocation_records(payment_id, identity, db)
