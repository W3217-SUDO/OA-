"""模板导出专用投影：复用既有数据权限和费用关联，补齐原件列。"""

from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import or_, select

from app.models import BusinessRecord, IncomingPayment, User


def joined(values):
    return ",".join(dict.fromkeys(str(value) for value in values if value is not None and value != ""))


def case_court_export_fields(data):
    """各审级先读当前保存字段，再读同级旧字段；拼接保留审级顺序并去重。"""
    numbers = joined((
        data.get("first_court_case_no") or data.get("first_instance_case_no") or data.get("court_case_no"),
        data.get("second_court_case_no") or data.get("second_instance_case_no"),
        data.get("execution_court_case_no") or data.get("execution_instance_case_no") or data.get("execution_case_no"),
        data.get("retrial_court_case_no") or data.get("last_instance_case_no") or data.get("retrial_case_no"),
    ))
    courts = joined((
        data.get("first_court_name") or data.get("first_instance_court"),
        data.get("second_court_name") or data.get("second_instance_court"),
        data.get("execution_court_name") or data.get("execution_instance_court"),
        data.get("retrial_court_name") or data.get("last_instance_court"),
    ))
    return numbers, courts


async def linked_cases(rows, identity, db):
    from app.core.permissions import _record_scope_conditions
    from app.core.query_batches import _scalars_in_batches
    ids = {int((row.get("data") or {}).get("case_id") or 0) for row in rows} - {0}
    numbers = {str((row.get("data") or {}).get("case_no") or "") for row in rows} - {""}
    scope = await _record_scope_conditions(identity, db)
    cases = []
    for column, values in ((BusinessRecord.id, ids), (BusinessRecord.serial_no, numbers)):
        cases.extend(await _scalars_in_batches(db, values, lambda batch: select(BusinessRecord).where(
            BusinessRecord.module.in_(("case", "ipr_case")), column.in_(batch), *scope)))
    return {case.id: case for case in cases}, {case.serial_no: case for case in cases}


async def fee_export_values(rows, identity, db, internal=False):
    from app.core.finance import _settlement_customer_manager_resolver
    from app.core.permissions import _record_scope_conditions
    from app.core.query_batches import _scalars_in_batches
    from app.core.system import _allowed_field_keys
    by_id, by_number = await linked_cases(rows, identity, db)
    scope = await _record_scope_conditions(identity, db)
    sources = {source.id: source for source in await _scalars_in_batches(db, {row["id"] for row in rows},
        lambda batch: select(BusinessRecord).where(BusinessRecord.id.in_(batch), BusinessRecord.module == "finance", *scope))}
    show_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    resolve_manager = await _settlement_customer_manager_resolver(db)
    names = dict((await db.execute(select(User.username, User.display_name))).all())

    def person(value):
        if isinstance(value, list):
            return joined(person(part) for part in value)
        text = str(value or "")
        return joined(names.get(part, part) or part for part in text.replace("、", ",").split(","))

    values = []
    for index, row in enumerate(rows, 1):
        data = row.get("data") or {}
        source = sources.get(row["id"])
        if not source:
            raise HTTPException(409, "费用原始记录不存在或无权导出")
        if show_amount and (source.data or {}).get("amount") is None:
            raise HTTPException(409, f"费用 {source.serial_no} 的金额未映射完整")
        data["amount"] = (source.data or {}).get("amount") if show_amount else None
        case = by_id.get(int(data.get("case_id") or 0)) or by_number.get(str(data.get("case_no") or ""))
        if not case:
            raise HTTPException(409, f"费用 {row.get('serial_no')} 的案件不存在或无权导出")
        case_data = case.data or {}
        if internal:
            # 原服务的“发票”列明确写空；公证书号读取案件，内部费用类型以用户原件补齐。
            values.append([index, data.get("case_no"), case.customer, data.get("case_name"),
                person(data.get("handling_lawyer")), person(data.get("lawyer_assistant")),
                person(data.get("investigator")), person(data.get("payee")), data.get("payment_status"),
                data.get("amount"), case_data.get("notary_nos") or case_data.get("notary_no") or case_data.get("certificate_no"),
                "", data.get("internal_fee_type")])
            continue
        case_numbers, case_courts = case_court_export_fields(case_data)
        requested, refunded = data.get("refund_requested_amount"), data.get("refunded_amount")
        refund = None if requested is None or refunded is None else f"{Decimal(str(requested)):.2f}/{Decimal(str(refunded)):.2f}"
        values.append([index, data.get("case_no"), case.customer, data.get("case_stage"),
            person(data.get("applicant") or data.get("submitted_by")),
            person(case_data.get("source_person") or case_data.get("business_owner") or case_data.get("case_source")),
            person(case_data.get("customer_manager") or case_data.get("customer_managers")) or resolve_manager(case_data, case.customer), person(data.get("hearing_lawyer")),
            person(case_data.get("handling_lawyers") or case_data.get("handling_lawyer") or case_data.get("case_lawyer")),
            person(data.get("assistant")), person(data.get("investigator")), data.get("fee_type"),
            data.get("amount"), data.get("invoice_date"), data.get("invoice_amount"), data.get("invoice_no"),
            refund, data.get("cashed_date"), data.get("cashed_amount"), data.get("received_payer_name"),
            data.get("paid_date"), data.get("paid_amount"), data.get("paid_organization"),
            data.get("payment_status"), data.get("contract_no"),
            case_numbers or data.get("court_case_no"), case_courts or data.get("court_name")])
    return values


async def invoice_export_values(rows, identity, db):
    from sqlalchemy import String, cast
    from app.core.finance import _invoice_fee_details, _invoice_linked_fee_ids, _visible_incoming_payment_statement, _settlement_fee_kind, _incoming_payment_legacy_summary
    from app.core.formatters import _case_fee_display_type
    from app.core.permissions import _record_scope_conditions
    from app.core.query_batches import _scalars_in_batches
    from app.core.system import _allowed_field_keys
    from app.core.fee_cash_query import read_fee_receipts

    scope = await _record_scope_conditions(identity, db)
    records = {item.id: item for item in await _scalars_in_batches(db, {row["id"] for row in rows},
        lambda batch: select(BusinessRecord).where(BusinessRecord.id.in_(batch), BusinessRecord.module == "invoice", *scope))}
    show_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    ids = set().union(*(_invoice_linked_fee_ids(item.data or {}) for item in records.values())) if records else set()
    legacy_ids = {str(part.get("CaseFeeId")) for item in records.values() for part in (item.data or {}).get("legacy_objects") or []
                  if part.get("IsActived") != "F" and part.get("CaseFeeId")}
    fees = {fee.id: fee for fee in await _scalars_in_batches(db, ids,
        lambda batch: select(BusinessRecord).where(BusinessRecord.id.in_(batch), BusinessRecord.module == "finance", *scope))}
    historical = await _scalars_in_batches(db, legacy_ids, lambda batch: select(BusinessRecord).where(
        BusinessRecord.module == "finance", or_(cast(BusinessRecord.data["legacy_case_fee_id"].as_string(), String).in_(batch),
            cast(BusinessRecord.data["legacy_fee_id"].as_string(), String).in_(batch)), *scope))
    fees.update({fee.id: fee for fee in historical})
    projected = {fee["id"]: fee for fee in await _invoice_fee_details(identity, db, ids=set(fees))} if fees else {}
    fees_by_case = {}
    for fee in fees.values():
        fees_by_case.setdefault(str((fee.data or {}).get("case_no") or ""), []).append(fee)
    receipt_links = await read_fee_receipts(list(fees.values()), fees_by_case,
        {number for number, linked in fees_by_case.items() if number and len(linked) == 1}, db, filter_related=True)
    payment_ids = {payment.id for links in receipt_links.values() for payment, _amount in links}
    statement = await _visible_incoming_payment_statement(identity, db)
    visible_payments = {payment.id: payment for payment in await _scalars_in_batches(db, payment_ids,
        lambda batch: statement.where(IncomingPayment.id.in_(batch)))}
    payments_by_fee = {fee_id: {payment.id: visible_payments[payment.id] for payment, _amount in links if payment.id in visible_payments}
        for fee_id, links in receipt_links.items()}
    values = []
    for index, row in enumerate(rows, 1):
        record = records[row["id"]]
        raw = record.data or {}
        data = row["data"]
        fee_ids = _invoice_linked_fee_ids(raw)
        allocations = {int(part["fee_id"]): part.get("amount") for part in raw.get("case_fee_allocations") or []}
        if not fee_ids:
            for part in raw.get("legacy_objects") or []:
                if part.get("IsActived") == "F":
                    continue
                source_id = str(part.get("CaseFeeId") or "")
                candidates = [fee for fee in historical if source_id == str((fee.data or {}).get("legacy_case_fee_id") or (fee.data or {}).get("legacy_fee_id") or "")]
                source = str(raw.get("legacy_source") or "")
                if source:
                    candidates = [fee for fee in candidates if str((fee.data or {}).get("legacy_source") or "") == source]
                if len(candidates) != 1:
                    raise HTTPException(409, f"发票 {record.serial_no} 的历史费用未找到唯一可见来源")
                fee_ids.add(candidates[0].id)
                allocations[candidates[0].id] = part.get("InvoicedAmount")
        if not fee_ids or not fee_ids.issubset(projected):
            raise HTTPException(409, f"发票 {record.serial_no} 的费用来源未映射完整或无权导出")
        if len(fee_ids) == 1 and not allocations:
            allocations[next(iter(fee_ids))] = raw.get("amount")
        objects = [projected[fee_id]["data"] for fee_id in sorted(fee_ids)]
        if any(item.get("contract_missing_or_forbidden") for item in objects):
            raise HTTPException(409, f"发票 {record.serial_no} 的关联合同不存在或无权导出")
        official, non_official = Decimal(0), Decimal(0)
        for fee_id in fee_ids:
            amount = allocations.get(fee_id)
            if amount is None:
                raise HTTPException(409, f"发票 {record.serial_no} 缺少费用开票金额")
            if show_amount:
                kind = _settlement_fee_kind(_case_fee_display_type(fees[fee_id]))
                if kind == "official":
                    official += Decimal(str(amount))
                elif kind in {"agency", "other"}:
                    # 原开票代理费列实际读取 CaseNonOfficeFeeAmount，即非官费开票金额。
                    non_official += Decimal(str(amount))
        receipts = {payment_id: payment for fee_id in fee_ids for payment_id, payment in payments_by_fee.get(fee_id, {}).items()}
        services = raw.get("service_items") or []
        values.append([index, record.serial_no, data.get("invoice_no"),
            str(data.get("application_date") or "")[:10], data.get("invoice_date"), record.customer,
            joined(item.get("contract_no") for item in objects), joined(item.get("external_contract_no") for item in objects),
            joined(item.get("case_no") for item in objects), joined(item.get("fee_type") for item in objects),
            data.get("amount"), float(official) if show_amount else None, float(non_official) if show_amount else None,
            data.get("extra_amount"), joined(item.get("service_name") or item.get("name") for item in services) or data.get("invoice_content"),
            data.get("invoice_title"), data.get("taxpayer_id"), data.get("invoice_address"), data.get("invoice_phone"),
            data.get("bank_name"), data.get("bank_account"), data.get("remark"),
            joined(str(payment.received_date) for payment in receipts.values()), sum(float(payment.amount) for payment in receipts.values()) if show_amount else None,
            joined(payment.payer_name for payment in receipts.values()), joined(_incoming_payment_legacy_summary(payment)["payment_method"] for payment in receipts.values()),
            data.get("recipient"), record.status])
    return values


async def archive_export_values(rows, identity, db):
    from app.core.finance import _invoice_case_fee_rows
    from app.core.permissions import _settlement_application_scope
    from app.core.query_batches import _scalars_in_batches
    application_ids = {int(row["data"].get("application_id") or row["data"].get("source_application_id") or 0) for row in rows} - {0}
    applications = await _scalars_in_batches(db, application_ids, lambda batch: select(BusinessRecord).where(
        BusinessRecord.module == "finance_settlement", BusinessRecord.id.in_(batch), *_settlement_application_scope(identity)))
    source_details = {f"{application.id}:{detail.get('detail_id') or index}": detail
        for application in applications for index, detail in enumerate((application.data or {}).get("allocation_details") or [], 1)}
    fee_ids = set()
    for row in rows:
        if row.get("read_only"):
            continue
        data = row["data"]
        detail = source_details.get(str(data.get("source_row_id") or row["id"]))
        if not detail or not detail.get("fee_id"):
            raise HTTPException(409, "归档费的原案件费用来源不完整或无权导出")
        data["fee_id"] = int(detail["fee_id"])
        fee_ids.add(data["fee_id"])
    fees = {fee["id"]: fee for fee in await _invoice_case_fee_rows(identity, db, scope="company", ids=fee_ids, include_all_fee_types=True)} if fee_ids else {}
    values = []
    for index, row in enumerate(rows, 1):
        data = row["data"]
        if row.get("read_only"):
            values.append([index, data.get("case_no"), row.get("customer"), data.get("case_stage"),
                data.get("assistant"), data.get("hearing_lawyer"), data.get("customer_manager"), data.get("fee_type"),
                data.get("payment_method"), data.get("payer_name"), data.get("receipt_amount"), data.get("received_date"),
                data.get("archive_fee_amount"), data.get("settlement_paid_at"), row.get("status"), data.get("archive_no")])
            continue
        fee = fees.get(data["fee_id"])
        if not fee:
            raise HTTPException(409, "归档费关联费用不存在或无权导出")
        values.append([index, data.get("case_no"), row.get("customer"), data.get("case_stage"),
            data.get("assistant"), data.get("hearing_lawyer"), data.get("customer_manager"), data.get("fee_type"),
            data.get("payment_method"), data.get("payer_name"), fee["data"].get("cashed_amount"), data.get("received_date"),
            data.get("archive_fee_amount"), str(data.get("settlement_paid_at") or "")[:10], row.get("status"), data.get("archive_no")])
    if rows:
        amounts = [row["data"].get("archive_fee_amount") for row in rows]
        total = None if any(amount is None for amount in amounts) else sum(Decimal(str(amount)) for amount in amounts)
        values.append([len(rows) + 1, "", "", "", "", "", "", "", "", "", "", "", float(total) if total is not None else None, "", "", ""])
    return values


async def enrich_settlement_exports(rows, identity, db, *, include_invoice_fields: bool):
    from app.core.contracts import _contract_person_values, _valid_contract_chinese_person_name
    from app.core.formatters import _person_reference_display, _user_display_map
    from app.core.incoming_allocation_projection import normalize_settlement_allocation_times
    from app.core.finance import _invoice_fee_details, _visible_incoming_payment_statement, _incoming_payment_legacy_summary
    from app.core.permissions import _record_scope_conditions
    from app.core.system import _allowed_field_keys

    modern_rows = [row for row in rows if not row.get("read_only")]
    if not modern_rows:
        return rows
    details = [detail for row in modern_rows for detail in row["data"].get("allocation_details") or []]
    by_id, by_number = await linked_cases([{"data": detail} for detail in details], identity, db)
    lawyer_references = {case.id: _contract_person_values(
        (case.data or {}).get("hearing_lawyer_username") or (case.data or {}).get("hearing_lawyer")
        or (case.data or {}).get("court_lawyer")
    ) for case in by_id.values()}
    users = await _user_display_map({value for values in lawyer_references.values() for value in values}, db)
    lawyer_names = {}
    for case_id, references in lawyer_references.items():
        names = []
        for reference in references:
            if reference.lower() in users:
                name, missing = _person_reference_display(reference, users)
            else:
                name = _valid_contract_chinese_person_name(reference)
                missing = not name
            if missing:
                raise HTTPException(409, "结算关联案件的开庭律师姓名不完整，请在员工管理中补全后导出")
            names.append(name)
        lawyer_names[case_id] = "、".join(dict.fromkeys(names))
    ids = {int(detail["fee_id"]) for detail in details if detail.get("fee_id")}
    fees = {fee["id"]: fee for fee in await _invoice_fee_details(identity, db, ids=ids)} if ids else {}
    invoices_by_case_id, invoices_by_case_no = {}, {}
    if include_invoice_fields:
        invoices = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "invoice",
            or_(BusinessRecord.data["purpose"].as_string().is_(None), BusinessRecord.data["purpose"].as_string() != "付款凭证"),
            *(await _record_scope_conditions(identity, db)), BusinessRecord.status.notin_(("已作废", "已撤回")),
        ))).all())
        for invoice in invoices:
            invoice_data = invoice.data or {}
            for case_id in set([invoice_data.get("case_id")] + list(invoice_data.get("case_ids") or [])) - {None, ""}:
                invoices_by_case_id.setdefault(int(case_id), {})[invoice.id] = invoice
            for case_no in set([invoice_data.get("case_no")] + list(invoice_data.get("case_nos") or [])) - {None, ""}:
                invoices_by_case_no.setdefault(str(case_no), {})[invoice.id] = invoice
    receipt_ids = {int(row["data"]["receipt_id"]) for row in modern_rows if row["data"].get("receipt_id")}
    payment_statement = await _visible_incoming_payment_statement(identity, db)
    payments = {payment.id: payment for payment in (await db.scalars(payment_statement.where(IncomingPayment.id.in_(receipt_ids)))).all()}
    show_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    for row in modern_rows:
        receipt_id = row["data"].get("receipt_id")
        if not receipt_id:
            raise HTTPException(409, "结算申请缺少原回款关系，不能把申请编号作为回款编号导出")
        payment = payments.get(int(receipt_id))
        if not payment:
            raise HTTPException(409, "结算关联回款不存在或无权导出")
        row["data"] = normalize_settlement_allocation_times(
            row["data"], payment.allocations or [], receipt_no=payment.receipt_no,
        )
        row["data"]["payment_method"] = _incoming_payment_legacy_summary(payment)["payment_method"]
        row["data"]["amount_visible"] = show_amount
        for detail in row["data"].get("allocation_details") or []:
            case = by_id.get(int(detail.get("case_id") or 0)) or by_number.get(str(detail.get("case_no") or ""))
            if not case:
                raise HTTPException(409, "结算关联案件不存在或无权导出")
            case_data = case.data or {}
            detail.update({"hearing_lawyer": lawyer_names[case.id],
                "source_person": case_data.get("source_person") or case_data.get("business_owner") or case_data.get("case_source"),
                "court_case_no": case_data.get("official_no") or case_data.get("court_case_no") or case_data.get("first_instance_case_no"),
                "file_no": case_data.get("file_no"), "archive_no": case_data.get("archive_no") or case_data.get("archived_file_no")})
            if not detail.get("fee_id"):
                raise HTTPException(409, "结算分配明细未关联原案件费用，不能生成案件费用模板")
            fee = fees.get(int(detail["fee_id"]))
            if not fee:
                raise HTTPException(409, "结算关联费用不存在或无权导出")
            if show_amount and fee["data"].get("amount") is None:
                raise HTTPException(409, "结算关联费用金额未映射完整")
            detail["fee_total_amount"] = fee["data"].get("amount")
            detail["fee_allocated_amount"] = fee["data"].get("cashed_amount")
            if include_invoice_fields:
                linked = list({**invoices_by_case_no.get(case.serial_no, {}), **invoices_by_case_id.get(case.id, {})}.values())
                detail["invoice_dates"] = joined((invoice.data or {}).get("invoice_date") for invoice in linked)
                detail["invoice_titles"] = joined((invoice.data or {}).get("invoice_title") for invoice in linked)
                detail["invoice_numbers"] = joined((invoice.data or {}).get("invoice_no") for invoice in linked)
                for target, source in (("invoice_amount", "amount"), ("invoice_extra_amount", "extra_amount")):
                    amounts = [(invoice.data or {}).get(source) for invoice in linked]
                    if show_amount and any(amount is None for amount in amounts):
                        raise HTTPException(409, "结算关联发票金额未映射完整")
                    detail[target] = sum(float(amount) for amount in amounts) if show_amount else None
    return rows
