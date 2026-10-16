"""本地分配动作的 HZ 分类快照，与现行分配版本绑定，不修改原始账本。"""

from copy import deepcopy
from collections import Counter
from decimal import Decimal, InvalidOperation

from sqlalchemy import and_, case, func, literal, or_, select
from sqlalchemy.orm import aliased

from app.core.incoming_allocation_projection import allocation_fee_id
from app.core.incoming_legacy_amounts import ASSIGNED_FIELDS, attach_source_fee_type, fee_kind_from_type_id, source_text
from app.core.constants import FEE_TYPE_ROOT_BASES
from app.core.fee_type_metadata import FEE_GROUP_BASES, fee_type_group
from app.models import BusinessRecord, LegacyFinanceRecord, SystemParameter


def proven_current_zero(payment):
    def known_zero(value):
        if value is None or isinstance(value, bool):
            return False
        try:
            amount = Decimal(str(value))
            return amount.is_finite() and amount == 0
        except (InvalidOperation, TypeError, ValueError):
            return False

    if not known_zero(payment.allocated_amount) or not isinstance(payment.allocations, list):
        return False
    for row in payment.allocations:
        if not isinstance(row, dict) or not known_zero(row.get("amount")):
            return False
        children = row.get("settlement_items")
        if children is not None and not isinstance(children, list):
            return False
        if any(not isinstance(child, dict) or not known_zero(child.get("amount")) for child in children or []):
            return False
    return True


def verified_legacy_baseline(payment):
    if payment.legacy_baseline_applied_amount is None or payment.legacy_baseline_allocations is None:
        return False
    try:
        if Decimal(str(payment.allocated_amount)) != Decimal(str(payment.legacy_baseline_applied_amount)):
            return False
        expected = Counter()
        for sequence, fee_id, amount, payment_id, valid, active, namespace in payment.legacy_baseline_allocations:
            if not valid or active != "T":
                return False
            expected[(str(sequence), str(fee_id), Decimal(str(amount)), str(payment_id), namespace)] += 1
        current = Counter()
        total = Decimal(0)
        for row in payment.allocations or []:
            source = row.get("source_object") or {}
            if row.get("settlement_items") or not source or source.get("IsActived") != "T":
                return False
            amount = Decimal(str(row["amount"]))
            if amount != Decimal(str(source.get("CashedAmount"))):
                return False
            current[(str(source.get("SeqId")), str(source.get("CaseFeeId")), amount, str(source.get("PaymentId")),
                     source.get("_source_database"))] += 1
            total += amount
        return total == Decimal(str(payment.allocated_amount)) and current == expected
    except (InvalidOperation, KeyError, TypeError, ValueError):
        return False


async def _modern_fee_classes(sources, db):
    modern = {key: row.fee_data for key, row in sources.items() if not any(
        (row.fee_data or {}).get(field) for field in ("legacy_case_fee_id", "legacy_kind", "legacy_source", "migration_source", "legacy_record"))}
    if not modern:
        return {}
    parameters = list((await db.scalars(select(SystemParameter).where(SystemParameter.category == "fee_type"))).all())
    by_id = {item.id: item for item in parameters}
    by_code = {}
    for item in parameters:
        by_code.setdefault(item.code, []).append(item)
    result = {}
    for fee_id, data in modern.items():
        identifier = data.get("fee_type_id")
        node = by_id.get(identifier) if isinstance(identifier, int) and not isinstance(identifier, bool) else None
        if node is None or (data.get("fee_type_code") and data["fee_type_code"] != node.code):
            continue
        seen = set()
        configured_group = ""
        while node.id not in seen:
            seen.add(node.id)
            configured_group = configured_group or fee_type_group(node)
            parent = str((node.extra or {}).get("parent_code") or "").strip()
            if not parent:
                extra = node.extra or {}
                base = FEE_GROUP_BASES.get(configured_group) if configured_group else extra.get("base_fee_type") or FEE_TYPE_ROOT_BASES.get(node.code)
                type_id = {"official": 1, "agency": 2, "other": 3, "internal": 4, "third-party": 5, "platform": 6}.get(configured_group)
                if not configured_group:
                    type_id = {"官方费用": 1, "代理费": 2, "其他费用": 3, "内部费用": 4}.get(base)
                if type_id is not None and data.get("fee_type") == base:
                    result[fee_id] = (type_id, identifier)
                break
            parents = by_code.get(parent, [])
            if len(parents) != 1:
                break
            node = parents[0]
    return result


def current_hz_summary(payment):
    from app.core.incoming_allocation_records import allocation_revision

    summary = payment.local_allocation_summary
    if summary is None:
        return None
    valid = (summary.get("version") == 1
             and summary.get("allocation_revision") == allocation_revision(payment.allocations or [])
             and summary.get("allocated_amount") == payment.allocated_amount)
    return {field: summary.get(field) if valid else None for field in ASSIGNED_FIELDS}


async def stamp_hz_allocation_summary(payment, db):
    if payment.source_kind != "hz_crm_20260930":
        return
    from app.core.incoming_allocation_records import allocation_revision

    rows = deepcopy(payment.allocations or [])
    parts = [part for row in rows for part in (row.get("settlement_items") or [row])]
    fee_ids = {allocation_fee_id(part) for part in parts} - {0, None}
    fee = aliased(BusinessRecord)
    original = aliased(LegacyFinanceRecord)
    namespace = source_text(fee.data["legacy_record"], "_source_database")
    stored_key = source_text(fee.data, "legacy_case_fee_id")
    fee_key = source_text(fee.data["legacy_record"], "CaseFeeId")
    old_hz = and_(namespace.is_(None), source_text(fee.data, "legacy_kind") == "ar_case_fee",
        source_text(fee.data, "source_table") == "FAM_AR_CaseFee",
        source_text(fee.data, "legacy_source") == "hz_crm_20260930",
        func.coalesce(source_text(fee.data, "migration_source"), "").in_(("", "hz_crm_20260930")))
    proven_source = or_(namespace.is_not(None), old_hz)
    legacy_id = case((namespace.is_not(None), namespace + literal(":") + fee_key), else_=fee_key)
    statement = select(fee.id.label("fee_id"), fee.data.label("fee_data"), original.source_payload.label("source"), original.is_active).select_from(fee).outerjoin(
        original, and_(original.source_table == "FAM_AR_CaseFee", original.legacy_id == legacy_id,
            proven_source,
            or_(stored_key == fee_key, stored_key == legacy_id),
            source_text(original.source_payload, "CaseFeeId") == fee_key,
            source_text(original.source_payload, "_source_database").is_not_distinct_from(namespace)))
    statement, type_id, _ = attach_source_fee_type(statement, original, original)
    kind = case((source_text(original.source_payload, "IsActived") == "F", "excluded"),
                (and_(source_text(original.source_payload, "IsActived") == "T", original.is_active.is_(True)),
                 fee_kind_from_type_id(type_id)))
    statement = statement.add_columns(type_id.label("type_id"), kind.label("kind")).where(
        fee.module == "finance", fee.id.in_(fee_ids))
    sources = {row.fee_id: row for row in (await db.execute(statement)).all()} if fee_ids else {}
    modern = await _modern_fee_classes(sources, db)
    totals = dict.fromkeys(ASSIGNED_FIELDS, Decimal(0))
    covered_amount = Decimal(0)
    for part in parts:
        evidence = sources.get(allocation_fee_id(part))
        source = evidence.source if evidence and evidence.source else {}
        category = evidence.kind if evidence else None
        modern_type, parameter_id = modern.get(allocation_fee_id(part), (None, None))
        if modern_type is not None:
            category = {1: "official", 2: "agency", 3: "other"}.get(modern_type, "excluded")
        original_object = part.get("source_object") or {}
        if original_object and (str(original_object.get("CaseFeeId")) != str(source.get("CaseFeeId"))
                                or original_object.get("_source_database") != source.get("_source_database")
                                or original_object.get("IsActived") != "T"):
            category = None
        raw_type = str(modern_type) if modern_type is not None else str(evidence.type_id) if evidence and evidence.type_id is not None else ""
        part.update(case_fee_type_id=source.get("CaseFeeTypeId"),
                    base_fee_type_id=int(raw_type) if raw_type.isascii() and raw_type.isdecimal() and int(raw_type) > 0 else None,
                    legacy_fee_is_active=evidence.is_active if evidence and source else None,
                    fee_type_parameter_id=parameter_id,
                    classification_source="system_parameter" if parameter_id is not None else "legacy" if source else None)
        try:
            amount = Decimal(str(part["amount"]))
            if not amount.is_finite() or amount < 0:
                amount = None
        except (KeyError, InvalidOperation, TypeError, ValueError):
            amount = None
        covered_amount = covered_amount + amount if covered_amount is not None and amount is not None else None
        for expected, field in zip(("official", "agency", "other"), ASSIGNED_FIELDS):
            if category is None or (category == expected and amount is None):
                totals[field] = None
            elif category == expected and totals[field] is not None:
                totals[field] += amount
    if covered_amount is None or covered_amount != Decimal(str(payment.allocated_amount)):
        totals = dict.fromkeys(ASSIGNED_FIELDS, None)
    payment.allocations = rows
    payment.local_allocation_summary = {
        "version": 1, "allocation_revision": allocation_revision(rows),
        "allocated_amount": payment.allocated_amount,
        **{field: float(amount.quantize(Decimal("0.01"))) if amount is not None else None for field, amount in totals.items()},
    }
