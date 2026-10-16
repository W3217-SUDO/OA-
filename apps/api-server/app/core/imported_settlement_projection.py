"""旧结算只读投影：同源主键、主体、权限及筛选先在数据库中确定。"""

from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import Numeric, String, and_, case, cast, exists, func, literal, or_, select
from sqlalchemy.orm import aliased

from app.core.finance_centers import LEGACY_INCOMING_SOURCE
from app.models import BusinessRecord, IncomingPayment, LegacyFinanceAllocation, LegacyFinanceRecord
from app.core.incoming_legacy_amounts import (
    attach_source_fee_type, legacy_assigned_amounts,
    source_allocation_relation, source_fee_kind,
)


NORMAL_STATES = {"10": "待审批", "20": "待付款", "25": "已付款", "30": "已拒绝"}
ARCHIVED_PHASES = ("106012", "206012", "306012", "406012", "506012", "106018")
NORMAL_AMOUNTS = ("receipt_amount", "allocated_amount", "remaining_amount", "assigned_official_fee",
                  "assigned_agency_fee", "assigned_other_fee", "agency_settlement_amount", "archive_fee", "actual_settlement_amount")
ARCHIVE_AMOUNTS = ("receipt_amount", "archive_fee_amount")


def _text(payload, key):
    return cast(payload[key].as_string(), String)


def _money(payload, key):
    return cast(func.nullif(_text(payload, key), ""), Numeric(20, 2))


def _complete_sum(value):
    return case((func.count() == func.count(value), func.sum(value)))


async def _source_query(identity, db, mode, statuses, filters):
    from app.core.finance import _visible_incoming_payment_statement

    visible = await _visible_incoming_payment_statement(identity, db, include_amounts=False)
    receipts = visible.with_only_columns(IncomingPayment.id.label("receipt_id"), IncomingPayment.receipt_no,
        LEGACY_INCOMING_SOURCE.c.source_header_id,
        func.nullif(cast(IncomingPayment.local_allocation_summary, String), "null").is_not(None).label(
            "has_local_allocation_activity")).subquery("visible_legacy_receipts")
    # 普通历史结算金额只会被当前可见回款头使用。将旧金额聚合限制到该集合，
    # 保留原有明细、基线和金额完整性计算，避免每次刷新扫描全部旧回款头。
    visible_legacy_amounts = legacy_assigned_amounts(header_ids=select(
        receipts.c.source_header_id,
    ).where(receipts.c.source_header_id.is_not(None)).distinct())
    head = LegacyFinanceRecord
    line = LegacyFinanceAllocation
    original_fee = aliased(LegacyFinanceRecord)
    linked_case = aliased(BusinessRecord)
    linked_customer = aliased(BusinessRecord)
    source = head.source_payload
    obj = line.source_payload
    fee_id = case((_text(source, "_source_database").is_not(None),
                   _text(source, "_source_database") + literal(":") + line.legacy_case_fee_id),
                  else_=line.legacy_case_fee_id)
    # 从可见回款头集合起步，先缩小历史来源范围，再联接明细和案件；旧写法
    # 以全部历史明细为 FROM 起点，容易在大库上形成全表 JSON 关联。
    line_from = select(line.id).select_from(receipts).join(
        head, and_(head.id == receipts.c.source_header_id,
                   head.source_table == "FAM_AR_Payment", head.is_active.is_(True))).join(
        line, and_(line.legacy_finance_record_id == head.id,
                   line.source_table == "FAM_AR_Payment_Object", line.is_active.is_(True))).outerjoin(
        original_fee, and_(original_fee.source_table == "FAM_AR_CaseFee", original_fee.is_active.is_(True),
            original_fee.legacy_id == fee_id,
            _text(original_fee.source_payload, "CaseFeeId") == line.legacy_case_fee_id,
            _text(original_fee.source_payload, "_source_database").is_not_distinct_from(_text(source, "_source_database")))).outerjoin(
        linked_case, and_(linked_case.id == line.case_record_id, linked_case.module == "case"))
    line_from, type_id, fee_name = attach_source_fee_type(line_from, original_fee, head)
    relation = and_(line.source_table == "FAM_AR_Payment_Object", line.is_active.is_(True),
        source_allocation_relation(line, head))
    bad = await db.scalar(select(line.id).join(head, head.id == line.legacy_finance_record_id).join(
        receipts, receipts.c.source_header_id == head.id).where(line.source_table == "FAM_AR_Payment_Object",
        line.is_active.is_(True), relation.is_not(True)).limit(1))
    if bad is not None:
        raise HTTPException(409, "历史结算明细的原主键、源库或父关联不一致，请先核对来源")
    fee_kind = source_fee_kind(type_id, line, original_fee)
    amount = _money(obj, "CashedAmount")
    line_columns = {
        "line_id": line.id, "header_id": head.id, "receipt_id": receipts.c.receipt_id,
        "receipt_no": receipts.c.receipt_no, "case_id": line.case_record_id, "case_no": line.legacy_case_no,
        "contract_no": original_fee.legacy_contract_no, "customer": linked_case.customer,
        "case_stage": linked_case.data["case_stage"].as_string(),
        "case_type": linked_case.data["case_type"].as_string(),
        "assistant": linked_case.data["assistant"].as_string(),
        "hearing_lawyer": linked_case.data["hearing_lawyer"].as_string(),
        "customer_manager": linked_case.data["customer_manager"].as_string(),
        "source_person": linked_case.data["source_person"].as_string(),
        "fee_type": fee_name, "kind": fee_kind,
        "current_amount": amount, "fee_allocated_amount": amount,
        "fee_total_amount": _money(original_fee.source_payload, "Amount"),
        "settlement_amount": _money(obj, "SettlementAmount"), "archive_fee": _money(obj, "ArchiveAmount"),
        "source_status": _text(obj, "ArchiveAmountSettlementStatus"),
        "header_legacy_id": head.legacy_id, "line_legacy_id": line.legacy_key,
        "source_object": obj, "source_header": source,
    }
    details = line_from.with_only_columns(*(value.label(key) for key, value in line_columns.items())).where(relation)
    modern = exists(select(BusinessRecord.id).where(BusinessRecord.module == "finance_settlement",
        BusinessRecord.status != "已删除", BusinessRecord.data["receipt_id"].as_integer() == receipts.c.receipt_id))
    common = {"header_id": head.id, "receipt_id": receipts.c.receipt_id, "receipt_no": receipts.c.receipt_no,
        "has_local_allocation_activity": receipts.c.has_local_allocation_activity,
        "header_legacy_id": head.legacy_id,
        "finance_scope": case((_text(source, "GroupId") == "10", "firm"), (_text(source, "GroupId") == "20", "platform")),
        "source_header": source, "payment_method": source["PaymentModeName"].as_string(),
        "payer_name": source["PayerName"].as_string(), "received_date": source["CashedDate"].as_string(),
        "applied_by": source["SettlementToAuditBusinessOwnerName"].as_string(),
        "applied_at": source["SettlementToAuditDate"].as_string(),
        "reviewer": source["SettlementAuditorName"].as_string(),
        "reviewed_at": source["SettlementAuditDate"].as_string(),
        "paid_at": source["SettlementPaidDate"].as_string(),
        "settlement_paid_at": source["SettlementPaidDate"].as_string()}
    if mode == "normal":
        join_text = lambda value: (func.string_agg(func.distinct(cast(value, String)), literal("、"))
                                  if db.get_bind().dialect.name == "postgresql" else func.group_concat(func.distinct(cast(value, String))))
        related = {key: join_text(value).label(key) for key, value in line_columns.items()
                   if key in {"case_no", "case_type", "case_stage", "assistant", "hearing_lawyer", "customer_manager", "source_person", "customer"}}
        sums = details.with_only_columns(head.id.label("header_id"), *related.values()).group_by(head.id).subquery("legacy_settlement_relations")
        common.update({key: _money(source, field) for key, field in (
            ("receipt_amount", "CashedAmount"), ("allocated_amount", "AppliedAmount"),
            ("agency_settlement_amount", "CaseNonOfficeFeeSettlementAmount"), ("archive_fee", "CaseFeeArchiveAmount"),
            ("actual_settlement_amount", "CaseFeeSettlementAmount"),
        )})
        common.update({key: visible_legacy_amounts.c[key] for key in (
            "assigned_official_fee", "assigned_agency_fee", "assigned_other_fee")})
        balance = _money(source, "CashedAmount") - _money(source, "AppliedAmount")
        common["remaining_amount"] = case((balance.is_(None), None), (balance > 0, balance), else_=0)
        common.update({key: sums.c[key] for key in related})
        common["customer"] = func.coalesce(linked_customer.title, sums.c.customer)
        common.update({"projection_key": literal("legacy-normal:") + cast(head.id, String),
            "source_status": _text(source, "SettlementStatus"),
            "status": case(*(( _text(source, "SettlementStatus") == key, value) for key, value in NORMAL_STATES.items())),
            "line_id": literal(None), "source_object": literal(None)})
        query = select(*(value.label(key) for key, value in common.items())).select_from(head).join(
            receipts, receipts.c.source_header_id == head.id).outerjoin(sums, sums.c.header_id == head.id).outerjoin(
            visible_legacy_amounts, visible_legacy_amounts.c.header_id == head.id).where(
                ~modern, _text(source, "SettlementStatus").in_([key for key, value in NORMAL_STATES.items() if value in statuses]))
        query = query.outerjoin(linked_customer, and_(linked_customer.id == head.customer_record_id, linked_customer.module == "customer"))
    else:
        raw_phase = _text(linked_case.data["legacy_record"], "CasePhaseId")
        stored_phase = _text(linked_case.data, "case_phase_id")
        phase = case((and_(raw_phase.is_not(None), stored_phase.is_not(None), raw_phase != stored_phase), None),
                     else_=func.coalesce(raw_phase, stored_phase))
        common.update(line_columns)
        common.update({"applied_at": obj["ArchiveAmountSettlementToAuditDate"].as_string(),
            "applied_by": obj["ArchiveAmountSettlementToAuditBusinessOwnerName"].as_string(),
            "reviewed_at": obj["ArchiveAmountSettlementAuditDate"].as_string(),
            "reviewer": obj["ArchiveAmountSettlementAuditorName"].as_string(),
            "paid_at": obj["ArchiveAmountSettlementPaidDate"].as_string(),
            "archive_date": linked_case.data["legacy_record"]["AuditedTime"].as_string()})
        common.update({"projection_key": literal("legacy-archive:") + cast(line.id, String),
            "status": literal({"pending": "待归档", "payment": "待支付", "paid": "已支付", "rejected": "已拒绝"}[mode]),
            "receipt_amount": amount, "archive_fee_amount": _money(obj, "ArchiveAmount"), "phase": phase})
        query = line_from.with_only_columns(*(value.label(key) for key, value in common.items())).where(
            relation, ~modern, _text(obj, "IsActived") == "T",
            _text(original_fee.source_payload, "IsActived") == "T", original_fee.is_active.is_(True))
        archive_state = _text(obj, "ArchiveAmountSettlementStatus")
        if mode == "pending":
            query = query.where(or_(phase.notin_(ARCHIVED_PHASES), phase.is_(None)), _text(source, "SettlementStatus").in_(("20", "25")))
        elif mode == "payment":
            query = query.where(or_(phase.in_(ARCHIVED_PHASES), phase.is_(None)), _text(source, "SettlementStatus") == "25",
                                or_(archive_state == "20", archive_state.is_(None)))
        else:
            query = query.where(archive_state == ("30" if mode == "paid" else "40"))
    fields = query.subquery("legacy_settlement_fields")
    query = select(fields)
    text_filters = {"customer": "customer", "case_no": "case_no", "payer": "payer_name", "payment_method": "payment_method",
        "applied_by": "applied_by", "submitted_by": "applied_by", "reviewer": "reviewer", "case_type": "case_type",
        "case_stage": "case_stage", "hearing_lawyer": "hearing_lawyer", "assistant": "assistant",
        "customer_manager": "customer_manager", "source_person": "source_person"}
    for name, field in text_filters.items():
        value = filters.get(name)
        if isinstance(value, str) and value.strip():
            if field not in fields.c:
                if name == "case_no" and mode == "normal":
                    continue
                query = query.where(literal(False))
            else:
                query = query.where(cast(fields.c[field], String).icontains(value.strip(), autoescape=True))
    unknown_dates = []
    for prefix, field in (("received", "received_date"), ("applied", "applied_at"), ("reviewed", "reviewed_at"),
                          ("paid", "paid_at"), ("settled", "settlement_paid_at"), ("submitted", "applied_at"),
                          ("payment", "paid_at"), ("archive", "archive_date")):
        for suffix, operator in (("from", "ge"), ("to", "le")):
            value = filters.get(prefix + "_" + suffix)
            if isinstance(value, date):
                if field not in fields.c:
                    query = query.where(literal(False))
                    continue
                missing = or_(fields.c[field].is_(None), cast(fields.c[field], String) == "")
                unknown_dates.append(missing)
                comparison = getattr(func.substr(fields.c[field], 1, 10), "__" + operator + "__")(value.isoformat())
                query = query.where(or_(missing, comparison))
    query = query.add_columns((or_(*unknown_dates) if unknown_dates else literal(False)).label("date_unknown"))
    return query, details


def _row(value, show_amount, archive):
    source = value["source_header"] or {}
    obj = value.get("source_object") or {}
    key = value["projection_key"]
    data = {name: (float(part) if isinstance(part, Decimal) else part) for name, part in value.items()
            if name not in {"source_header", "source_object", "projection_key", "date_unknown", "header_legacy_id", "line_legacy_id"}}
    if not show_amount:
        for name in set(NORMAL_AMOUNTS + ARCHIVE_AMOUNTS + ("current_amount", "settlement_amount", "fee_total_amount", "fee_allocated_amount")):
            if name in data:
                data[name] = None
    data.update({"amount_visible": show_amount, "case_nos": data.get("case_no"), "amount_basis": "legacy_snapshot"})
    return {"id": key, "projection_id": key, "source": "legacy", "read_only": True,
        "amount_basis": "legacy_snapshot", "source_label": "原始历史结算快照（只读，不代表现行分配）",
        "has_local_allocation_activity": bool(value.get("has_local_allocation_activity")),
        "legacy_record_id": value["header_id"], "legacy_allocation_id": value.get("line_id"),
        "source_status": value["source_status"], "serial_no": "", "title": "历史归档结算" if archive else "历史普通结算",
        "customer": value.get("customer") or "", "status": value["status"], "owner": value.get("applied_by") or "",
        "can_edit": False, "can_delete": False, "can_submit": False, "can_pay": False, "can_refund": False,
        "provenance": {"source_database": source.get("_source_database"), "source_table": "FAM_AR_Payment_Object" if archive else "FAM_AR_Payment",
            "legacy_id": value.get("line_legacy_id") if archive else value["header_legacy_id"],
            "PaymentId": source.get("PaymentId"), "SeqId": obj.get("SeqId")}, "data": data}


async def read_imported_settlement_page(modern_rows, identity, db, *, mode, statuses=(), filters=None, page=1, page_size=10, projection_ids=None):
    from app.core.system import _allowed_field_keys
    filters = filters or {}

    # 没有可见历史回款头时，后续历史明细、案件关联和状态汇总都不可能产生行。
    # 先做一次轻量存在性查询，避免空结果请求仍构造整套历史投影关联 SQL。
    if not modern_rows and projection_ids is None:
        from app.core.finance import _visible_incoming_payment_statement
        from app.core.finance_centers import LEGACY_INCOMING_SOURCE

        visible = await _visible_incoming_payment_statement(identity, db, include_amounts=False)
        visible_headers = visible.with_only_columns(
            LEGACY_INCOMING_SOURCE.c.source_header_id,
        ).where(LEGACY_INCOMING_SOURCE.c.source_header_id.is_not(None)).limit(1).subquery("visible_settlement_headers")
        if await db.scalar(select(func.count()).select_from(visible_headers)) == 0:
            amount_keys = NORMAL_AMOUNTS if mode == "normal" else ARCHIVE_AMOUNTS
            return {
                "items": [],
                "total": 0,
                "totals": {key: 0 if "finance.amount" in await _allowed_field_keys(identity, db) else None for key in amount_keys},
                "unknown_amount_counts": {key: 0 for key in amount_keys},
                "unknown_phase_total": 0,
                "unknown_eligibility_total": 0,
                "unknown_date_total": 0,
                "page": page,
                "page_size": page_size,
            }

    query, details = await _source_query(identity, db, mode, statuses, filters)
    if mode in {"pending", "payment", "paid", "rejected"}:
        # 归档投影的基础关联非常重，原实现会为未知状态、未知阶段、未知日期、
        # 总额和当前页重复执行同一 CTE。一次读取基础行后按同一条件顺序计算，
        # 保留原有未知计数、金额汇总和分页口径。
        raw_rows = [dict(value) for value in (await db.execute(query)).mappings()]
        date_fields = []
        for prefix, field in (("received", "received_date"), ("applied", "applied_at"),
                              ("reviewed", "reviewed_at"), ("paid", "paid_at"),
                              ("settled", "settlement_paid_at"), ("submitted", "applied_at"),
                              ("payment", "paid_at"), ("archive", "archive_date")):
            if any(isinstance(filters.get(prefix + suffix), date) for suffix in ("_from", "_to")):
                date_fields.append(field)
        for row in raw_rows:
            row["date_unknown"] = bool(date_fields) and any(
                row.get(field) is None or str(row.get(field) or "") == "" for field in date_fields
            )
        if projection_ids is not None:
            selected_ids = set(projection_ids)
            raw_rows = [row for row in raw_rows if row.get("projection_key") in selected_ids]
        unknown_eligibility_total = sum(
            1 for row in raw_rows
            if row.get("source_status") is None or row.get("archive_fee_amount") is None
        )
        eligible_rows = [
            row for row in raw_rows
            if row.get("source_status") is not None and row.get("archive_fee_amount") is not None
            and float(row.get("archive_fee_amount") or 0) > 0
        ]
        unknown_phase_total = sum(1 for row in eligible_rows if row.get("phase") is None) if mode in {"pending", "payment"} else 0
        phase_rows = (
            [row for row in eligible_rows if row.get("phase") is not None]
            if mode in {"pending", "payment"} else eligible_rows
        )
        unknown_date_total = sum(1 for row in phase_rows if row.get("date_unknown"))
        legacy_rows = [row for row in phase_rows if not row.get("date_unknown")]
        show_amount = "finance.amount" in await _allowed_field_keys(identity, db)
        amount_keys = ARCHIVE_AMOUNTS
        totals = {}
        unknown = {}
        for key in amount_keys:
            values = [row.get(key) for row in legacy_rows]
            unknown[key] = sum(value is None for value in values)
            totals[key] = None if not show_amount and legacy_rows else (
                None if any(value is None for value in values) else round(sum(float(value or 0) for value in values), 2)
            )
        start = (page - 1) * page_size
        selected = legacy_rows if projection_ids is not None else legacy_rows[start:start + page_size]
        legacy_result = [_row(row, show_amount, True) for row in selected]
        if projection_ids is not None and {row["id"] for row in legacy_result} != set(projection_ids):
            raise HTTPException(409, "部分历史结算不存在、状态已变化、已由现代记录承接或无权导出")
        rows = modern_rows + legacy_result
        rows.sort(key=lambda row: (str((row.get("data") or {}).get("received_date") or ""), str(row["id"])), reverse=True)
        for key in amount_keys:
            modern_values = [(item.get("data") or {}).get(key) for item in modern_rows]
            if any(value is None for value in modern_values):
                totals[key] = None
                unknown[key] += sum(value is None for value in modern_values)
            elif totals[key] is not None:
                totals[key] = round(float(totals[key] or 0) + sum(float(value or 0) for value in modern_values), 2)
        return {
            "items": rows if projection_ids is not None or not modern_rows else rows[start:start + page_size],
            "total": len(modern_rows) + len(legacy_rows),
            "totals": totals,
            "unknown_amount_counts": unknown,
            "unknown_phase_total": unknown_phase_total,
            "unknown_eligibility_total": unknown_eligibility_total,
            "unknown_date_total": unknown_date_total,
            "page": page,
            "page_size": page_size,
        }
    if db.get_bind().dialect.name == "postgresql":
        # 同一历史投影会被未知计数、总计和当前页查询重复引用；在 PostgreSQL
        # 上物化一次，避免每条统计语句重新展开相同的多表关联。SQLite 保持
        # 原 subquery 语法，确保现有测试数据库兼容。
        base = query.cte("filtered_legacy_settlements").prefix_with("MATERIALIZED")
    else:
        base = query.subquery("filtered_legacy_settlements")
    unknown_phase_total = 0
    unknown_eligibility_total = 0
    if mode != "normal":
        unknown_eligibility_total = int(await db.scalar(select(func.count()).select_from(base).where(or_(
            base.c.source_status.is_(None), base.c.archive_fee_amount.is_(None)))))
        base = select(base).where(base.c.source_status.is_not(None),
                                   base.c.archive_fee_amount > 0).subquery("eligible_archive_settlements")
    if mode in {"pending", "payment"}:
        unknown_phase_total = int(await db.scalar(select(func.count()).select_from(base).where(base.c.phase.is_(None))))
        base = select(base).where(base.c.phase.is_not(None)).subquery("known_phase_settlements")
    unknown_date_total = int(await db.scalar(select(func.count()).select_from(base).where(base.c.date_unknown.is_(True))))
    base = select(base).where(base.c.date_unknown.is_(False)).subquery("known_date_settlements")
    amount_keys = NORMAL_AMOUNTS if mode == "normal" else ARCHIVE_AMOUNTS
    show_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    if projection_ids is not None:
        query = select(base).where(base.c.projection_key.in_(projection_ids))
        base = query.subquery("selected_legacy_settlements")
    total, *sums = (await db.execute(select(func.count(), *(_complete_sum(base.c[key]) for key in amount_keys),
        *(func.count() - func.count(base.c[key]) for key in amount_keys)).select_from(base))).one()
    missing_counts = sums[len(amount_keys):]
    sums = sums[:len(amount_keys)]
    selected = select(base).order_by(base.c.received_date.desc(), base.c.projection_key.desc())
    start = (page - 1) * page_size
    if projection_ids is None:
        selected = selected.offset(start).limit(page_size) if not modern_rows else selected.limit(page * page_size)
    legacy_rows = [_row(dict(value), show_amount, mode != "normal") for value in (await db.execute(selected)).mappings()]
    if projection_ids is not None and {row["id"] for row in legacy_rows} != set(projection_ids):
        raise HTTPException(409, "部分历史结算不存在、状态已变化、已由现代记录承接或无权导出")
    if mode == "normal" and legacy_rows:
        header_ids = [row["legacy_record_id"] for row in legacy_rows]
        by_header = {}
        for value in (await db.execute(details.where(LegacyFinanceRecord.id.in_(header_ids)))).mappings():
            detail = {key: (float(part) if isinstance(part, Decimal) else part) for key, part in value.items() if key not in {"source_header", "source_object"}}
            if not show_amount:
                for key in ("current_amount", "fee_allocated_amount", "fee_total_amount", "settlement_amount", "archive_fee"):
                    detail[key] = None
            by_header.setdefault(value["header_id"], []).append(detail)
        for row in legacy_rows:
            row["data"]["allocation_details"] = by_header.get(row["legacy_record_id"], [])
    totals = {}
    unknown = {}
    for key, legacy_sum, missing_count in zip(amount_keys, sums, missing_counts):
        values = [row.get("data", {}).get(key) for row in modern_rows]
        incomplete = (total > 0 and legacy_sum is None) or any(value is None for value in values)
        unknown[key] = int(missing_count) + sum(value is None for value in values)
        totals[key] = None if incomplete or not show_amount else round(float(legacy_sum or 0) + sum(float(value) for value in values), 2)
    rows = modern_rows + legacy_rows
    rows.sort(key=lambda row: (str(row.get("data", {}).get("received_date") or ""), str(row["id"])), reverse=True)
    return {"items": rows if projection_ids is not None or not modern_rows else rows[start:start + page_size], "total": len(modern_rows) + total,
        "totals": totals, "unknown_amount_counts": unknown, "unknown_phase_total": unknown_phase_total,
        "unknown_eligibility_total": unknown_eligibility_total,
        "unknown_date_total": unknown_date_total,
        "page": page, "page_size": page_size}
