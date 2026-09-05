"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
from app.core.constants import (
    _INVALID_RECEIVABLE_FEE_STATUSES,
)
from app.core.dependencies import (
    AsyncSession, BusinessRecord, ContractApprovalStep, ContractObject, or_,
    select,
)


async def _contract_customer_projection_context(records: list[BusinessRecord], db: AsyncSession) -> dict:
    from app.core.formatters import (
        _normalized_customer_name,
    )
    from app.core.system import (
        _positive_record_id,
    )
    contracts = [record for record in records if record.module == "contract"]
    if not contracts:
        return {"customers_by_id": {}, "customers_by_no": {}, "customers_by_name": {}, "current_steps": {}}
    customer_ids = {_positive_record_id((record.data or {}).get("customer_id") or (record.data or {}).get("customer_record_id")) for record in contracts}
    customer_ids.discard(0)
    customer_nos = {str((record.data or {}).get("customer_no") or "").strip() for record in contracts}
    customer_nos.discard("")
    customer_names = {_normalized_customer_name(record.customer) for record in contracts}
    customer_names.discard("")
    legacy_customer_names = {
        _normalized_customer_name(record.customer)
        for record in contracts
        if not _positive_record_id((record.data or {}).get("customer_id") or (record.data or {}).get("customer_record_id"))
        and not str((record.data or {}).get("customer_no") or "").strip()
        and _normalized_customer_name(record.customer)
    }
    customer_conditions = [BusinessRecord.module == "customer", BusinessRecord.status.not_in({"已回收"})]
    lookup_conditions = []
    if customer_ids:
        lookup_conditions.append(BusinessRecord.id.in_(customer_ids))
    if customer_nos:
        lookup_conditions.append(BusinessRecord.serial_no.in_(customer_nos))
    if customer_names:
        lookup_conditions.append(BusinessRecord.title.in_([record.customer for record in contracts if _normalized_customer_name(record.customer) in customer_names]))
    customers = list((await db.scalars(select(BusinessRecord).where(*customer_conditions, or_(*lookup_conditions)))).all()) if lookup_conditions else []
    if legacy_customer_names:
        # Historical contracts may contain full-width characters or irregular
        # whitespace. SQL equality cannot reproduce the NFKC key, so fetch the
        # bounded customer directory once and resolve only unambiguous keys.
        legacy_candidates = list((await db.scalars(select(BusinessRecord).where(*customer_conditions))).all())
        seen_customer_ids = {customer.id for customer in customers}
        customers.extend(
            customer for customer in legacy_candidates
            if customer.id not in seen_customer_ids and _normalized_customer_name(customer.title) in legacy_customer_names
        )
    customers_by_id = {customer.id: customer for customer in customers}
    customers_by_no: dict[str, list[BusinessRecord]] = {}
    customers_by_name: dict[str, list[BusinessRecord]] = {}
    for customer in customers:
        customers_by_no.setdefault(str(customer.serial_no or "").strip(), []).append(customer)
        customers_by_name.setdefault(_normalized_customer_name(customer.title), []).append(customer)
    contract_ids = [contract.id for contract in contracts]
    steps = list((await db.scalars(select(ContractApprovalStep).where(
        ContractApprovalStep.contract_record_id.in_(contract_ids),
        ContractApprovalStep.status == "待审批",
    ).order_by(ContractApprovalStep.contract_record_id, ContractApprovalStep.step_order))).all())
    current_steps: dict[int, ContractApprovalStep] = {}
    for step in steps:
        current_steps.setdefault(step.contract_record_id, step)
    return {
        "customers_by_id": customers_by_id,
        "customers_by_no": customers_by_no,
        "customers_by_name": customers_by_name,
        "current_steps": current_steps,
    }


async def _receivable_detail_projection(
    identity: dict, db: AsyncSession, records: list[BusinessRecord] | None = None,
) -> list[dict]:
    """Project the legacy contract-object receivable detail from visible data."""
    from app.core.finance import (
        _fee_matches_contract_object, _invoice_case_fee_rows, _receivable_fee_category, _receivable_number, _receivable_relation_id,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.query_batches import _scalars_in_batches

    if records is None:
        records = list((await db.scalars(select(BusinessRecord).where(
            *(await _record_scope_conditions(identity, db)),
        ))).all())

    contracts = [item for item in records if item.module == "contract"]
    cases = [item for item in records if item.module == "case"]
    finances = [item for item in records if item.module == "finance"]
    contracts_by_id = {item.id: item for item in contracts}
    contracts_by_no = {item.serial_no: item for item in contracts if item.serial_no}
    cases_by_id = {item.id: item for item in cases}
    cases_by_no = {item.serial_no: item for item in cases if item.serial_no}

    objects = await _scalars_in_batches(
        db, contracts_by_id,
        lambda batch: select(ContractObject).where(
            ContractObject.contract_record_id.in_(batch),
        ),
    ) if contracts_by_id and cases_by_id else []
    objects = sorted(
        (item for item in objects if item.case_record_id in cases_by_id),
        key=lambda item: (item.contract_record_id, item.case_record_id, item.id),
    )

    # A case/contract owner is allowed to see the receivable even when the
    # linked finance record is operated by a cashier.  The ordinary record
    # scope filters that finance row out, so resolve only finance records that
    # are explicitly linked to the already-visible contract/case/object set.
    finances_by_id = {item.id: item for item in finances}
    contract_ids = set(contracts_by_id)
    case_ids = set(cases_by_id)
    object_ids = {item.id for item in objects}
    contract_nos = set(contracts_by_no)
    case_nos = set(cases_by_no)
    for key, values in (
        ("contract_object_id", object_ids),
        ("contract_id", contract_ids),
        ("contract_record_id", contract_ids),
        ("case_id", case_ids),
        ("case_record_id", case_ids),
    ):
        related_finances = await _scalars_in_batches(
            db, values,
            lambda batch: select(BusinessRecord).where(
                BusinessRecord.module == "finance",
                or_(BusinessRecord.data[key].as_integer().in_(batch),
                    BusinessRecord.data[key].as_string().in_([str(value) for value in batch])),
            ),
        )
        finances_by_id.update((item.id, item) for item in related_finances)
    for key, values in (("contract_no", contract_nos), ("case_no", case_nos)):
        related_finances = await _scalars_in_batches(
            db, values,
            lambda batch: select(BusinessRecord).where(
                BusinessRecord.module == "finance",
                BusinessRecord.data[key].as_string().in_(batch),
            ),
        )
        finances_by_id.update((item.id, item) for item in related_finances)
    finances = list(finances_by_id.values())

    finance_ids = {item.id for item in finances}
    finance_rows = await _invoice_case_fee_rows(
        identity, db, scope="company", ids=finance_ids, include_all_fee_types=True,
        scope_authorized_fee_ids=finance_ids,
        force_amount_projection=True,
    ) if finance_ids else []
    finance_data_by_id = {
        int(item["id"]): dict(item.get("data") or {}) for item in finance_rows
    }
    rows: list[dict] = []

    def relation(fee_data: dict) -> tuple[BusinessRecord | None, BusinessRecord | None]:
        case_record = cases_by_id.get(_receivable_relation_id(fee_data, "case_id", "case_record_id"))
        if case_record is None:
            case_record = cases_by_no.get(str(fee_data.get("case_no") or "").strip())
        contract = contracts_by_id.get(_receivable_relation_id(fee_data, "contract_id", "contract_record_id"))
        if contract is None:
            contract = contracts_by_no.get(str(fee_data.get("contract_no") or "").strip())
        if contract is None and case_record is not None:
            case_data = case_record.data or {}
            contract = contracts_by_id.get(_receivable_relation_id(case_data, "contract_id", "contract_record_id"))
            if contract is None:
                contract = contracts_by_no.get(str(case_data.get("contract_no") or "").strip())
        return contract, case_record

    matched_fee_ids: set[int] = set()
    for item in objects:
        contract = contracts_by_id[item.contract_record_id]
        case_record = cases_by_id[item.case_record_id]
        amount = _receivable_number(item.amount)
        if amount <= 0:
            continue
        linked_fees = [
            fee for fee in finances if _fee_matches_contract_object(fee, item, case_record)
        ]
        matched_fee_ids.update(fee.id for fee in linked_fees)
        paid = 0.0
        received = 0.0
        for fee in linked_fees:
            raw = fee.data or {}
            projected = finance_data_by_id.get(fee.id, {})
            paid += max(
                _receivable_number(projected.get("paid_amount")),
                _receivable_number(raw.get("paid_amount")),
            )
            received += max(
                _receivable_number(projected.get("cashed_amount")),
                _receivable_number(raw.get("cashed_amount")),
                _receivable_number(raw.get("received_amount")),
            )
        paid = min(_receivable_number(paid), amount)
        received = min(_receivable_number(received), amount)
        remaining = max(round(amount - received, 2), 0)
        case_data = case_record.data or {}
        contract_data = contract.data or {}
        rows.append({
            "id": f"object:{item.id}", "source_type": "contract_object",
            "contract_object_id": item.id, "fee_record_id": None,
            "contract_record_id": contract.id, "contract_no": contract.serial_no,
            "contract_title": contract.title,
            "contract_body": str(contract_data.get("contract_body") or "律所"),
            "contract_date": str(contract_data.get("signed_at") or "")[:10],
            "customer": contract.customer, "owner": contract.owner,
            "source_person": str(contract_data.get("source_person") or contract.owner),
            "case_record_id": case_record.id, "case_no": case_record.serial_no,
            "case_stage": str(case_data.get("case_stage") or case_data.get("business_stage") or case_record.status),
            "case_type": str(case_data.get("case_type") or ""),
            "phase": str(case_data.get("case_stage") or case_data.get("business_stage") or case_record.status),
            "fee_type": item.fee_type, "fee_category": _receivable_fee_category(item.fee_type),
            "due_date": "", "amount": amount, "paid_amount": paid,
            "received_amount": received, "remaining_amount": remaining,
            "status": case_record.status, "payer": contract.customer,
            "remark": item.remark, "updated_at": item.updated_at,
        })

    # Historical rows may predate contract-object migration. Keep only
    # unmatched, contract-resolvable fees so the contract-centric page remains
    # usable without duplicating modern object-backed rows.
    for fee in finances:
        if fee.id in matched_fee_ids:
            continue
        data = fee.data or {}
        if fee.status in _INVALID_RECEIVABLE_FEE_STATUSES:
            continue
        projected = finance_data_by_id.get(fee.id, {})
        fee_type = str(projected.get("fee_type") or data.get("fee_type") or fee.title or "案件费用").strip()
        fee_category = _receivable_fee_category(fee_type)
        contract, case_record = relation(data)
        if contract is None:
            continue
        amount = _receivable_number(data.get("amount"))
        paid = max(
            _receivable_number(projected.get("paid_amount")),
            _receivable_number(data.get("paid_amount")),
        )
        received = max(
            _receivable_number(projected.get("cashed_amount")),
            _receivable_number(data.get("cashed_amount")),
            _receivable_number(data.get("received_amount")),
        )
        paid = min(paid, amount)
        received = min(received, amount)
        remaining = max(round(amount - received, 2), 0)
        if amount <= 0:
            continue
        case_data = case_record.data or {} if case_record else {}
        contract_data = contract.data or {} if contract else {}
        rows.append({
            "id": f"fee:{fee.id}", "source_type": "case_fee",
            "contract_object_id": None, "fee_record_id": fee.id,
            "contract_record_id": contract.id,
            "contract_no": contract.serial_no,
            "contract_title": contract.title,
            "contract_body": str(contract_data.get("contract_body") or "律所"),
            "contract_date": str(contract_data.get("signed_at") or "")[:10],
            "customer": contract.customer,
            "owner": contract.owner,
            "source_person": str(contract_data.get("source_person") or contract.owner),
            "case_record_id": case_record.id if case_record else None,
            "case_no": case_record.serial_no if case_record else str(data.get("case_no") or ""),
            "case_stage": str(case_data.get("case_stage") or case_data.get("business_stage") or (case_record.status if case_record else "案件费用")),
            "case_type": str(case_data.get("case_type") or ""),
            "phase": str(case_data.get("case_stage") or case_data.get("business_stage") or (case_record.status if case_record else "案件费用")),
            "fee_type": fee_type, "fee_category": fee_category,
            "due_date": str(data.get("deadline") or ""), "amount": amount,
            "paid_amount": paid,
            "received_amount": received, "remaining_amount": remaining,
            "status": fee.status, "payer": fee.customer, "remark": fee.description,
            "updated_at": fee.updated_at,
        })

    aggregates: dict[int, dict[str, float]] = {}
    for row in rows:
        totals = aggregates.setdefault(row["contract_record_id"], {
            "official_paid": 0.0, "official_received": 0.0, "official_unreceived": 0.0,
            "official_loss": 0.0, "agency_total": 0.0, "agency_received": 0.0, "agency_due": 0.0,
        })
        if row["fee_category"] == "official":
            totals["official_paid"] += row["paid_amount"]
            totals["official_received"] += row["received_amount"]
            totals["official_unreceived"] += row["remaining_amount"]
            if "亏损" in row["phase"]:
                totals["official_loss"] += row["remaining_amount"]
        else:
            totals["agency_total"] += row["amount"]
            totals["agency_received"] += row["received_amount"]
            totals["agency_due"] += row["remaining_amount"]
    for row in rows:
        row["contract_totals"] = {key: round(value, 2) for key, value in aggregates[row["contract_record_id"]].items()}
    return sorted(rows, key=lambda row: (row["contract_no"] or "~", row["case_no"] or "~", str(row["id"])))
