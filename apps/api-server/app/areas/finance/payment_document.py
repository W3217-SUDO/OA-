"""Read-only payment documents with authoritative case and contract context."""
from fastapi import HTTPException
from app.core.dependencies import BusinessRecord, select
from app.core.permissions import _record_dict_for_identity, _record_scope_conditions


async def payment_document(row, identity, db):
    scope = await _record_scope_conditions(identity, db)

    async def related(module, record_id=None, number=None):
        if not record_id and not number:
            return None
        return await db.scalar(select(BusinessRecord).where(
            BusinessRecord.module == module,
            BusinessRecord.id == int(record_id) if record_id else BusinessRecord.serial_no == str(number),
            *scope))

    result = await _record_dict_for_identity(row, identity, db)
    data = dict(result.get('data') or {})
    requests = [row]
    if row.module == 'finance_package':
        requests = []
        for record_id in data.get('fee_ids', []):
            request = await db.scalar(select(BusinessRecord).where(BusinessRecord.id == int(record_id), *scope))
            if not request or request.module not in {'finance', 'contract_payment'}:
                raise HTTPException(status_code=404, detail='付款包明细不存在或无权访问')
            requests.append(request)
    groups = []
    for request in requests:
        request_view = await _record_dict_for_identity(request, identity, db)
        request_data = dict(request_view.get('data') or {})
        contract = await related('contract', request_data.get('contract_id'), request_data.get('contract_no'))
        contract_view = await _record_dict_for_identity(contract, identity, db) if contract else {}
        contract_data = contract_view.get('data') or {}
        group = {**request_data, 'request_no': request.serial_no,
                 'contract_no': contract.serial_no if contract else request_data.get('contract_no'),
                 'contract_name': contract.title if contract else request_data.get('contract_name'),
                 'customer': request_view.get('customer'), 'applicant': request_data.get('applicant_display_name') or request_data.get('applicant') or request_view.get('owner'),
                 'payer': request_data.get('payer_name') or request_data.get('payer') or contract_data.get('payer_name'),
                 'application_date': request_data.get('application_date') or request_view.get('created_at')}
        lines = request_data.get('lines') or request_data.get('items') or [request_data]
        items = []
        for index, line in enumerate(lines):
            fee_id = line.get('case_fee_id') or line.get('fee_record_id')
            fee = await related('finance', fee_id) if fee_id else None
            fee_view = await _record_dict_for_identity(fee, identity, db) if fee else {}
            fee_data = fee_view.get('data') or {}
            item = {**request_data, **fee_data, **line}
            case = await related('case', item.get('case_id') or item.get('case_record_id'), item.get('case_no'))
            case_view = await _record_dict_for_identity(case, identity, db) if case else {}
            case_data = case_view.get('data') or {}
            item.update(id=f'{request.id}:{index}', request_no=request.serial_no,
                        case_no=case.serial_no if case else item.get('case_no'),
                        case_name=case.title if case else item.get('case_name'),
                        case_type=case_data.get('case_type') or case_data.get('case_kind') or item.get('case_type'),
                        plaintiff=case_data.get('plaintiff') or case_view.get('customer') or item.get('plaintiff'),
                        defendant=case_data.get('defendant') or case_data.get('opponent') or item.get('defendant'),
                        contract_no=group['contract_no'], contract_name=group['contract_name'],
                        fee_amount=fee_data.get('amount', item.get('amount')),
                        current_payment=line.get('requested_amount', line.get('payment_amount', line.get('amount', request_data.get('amount')))),
                        fee_remark=fee_view.get('description') or fee_data.get('remark') or item.get('fee_remark'),
                        payment_remark=line.get('remark') or request_view.get('description'),
                        applicant=group['applicant'], payer=group['payer'])
            for field in ('case_source', 'source_person', 'customer_manager'):
                group[field] = group.get(field) or case_data.get(field) or contract_data.get(field)
            items.append(item)
        group['items'] = items
        groups.append(group)
    if groups:
        data = {**groups[0], **data}
    data['document_groups'] = groups
    data['items'] = [item for group in groups for item in group['items']]
    result['data'] = data
    return result
