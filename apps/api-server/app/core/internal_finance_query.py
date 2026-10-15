"""内部财务队列的实体选择、授权投影和分页；不修改历史生命周期。"""

from datetime import date
from dataclasses import asdict, dataclass

from fastapi import HTTPException
from sqlalchemy import String, case, cast, func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models import BusinessRecord, LegacyCase, LegacyFinanceAllocation, LegacyFinanceAudit, LegacyFinanceRecord, WorkflowEvent
from app.core.finance_person_projection import apply_finance_person_displays


@dataclass
class InternalApplicationFilters:
    applicant: str = ""
    application_no: str = ""
    application_from: date | None = None
    application_to: date | None = None
    audit_from: date | None = None
    audit_to: date | None = None
    request_status: str = ""

    def values(self) -> dict:
        for name in ("application", "audit"):
            start, end = getattr(self, f"{name}_from"), getattr(self, f"{name}_to")
            if start and end and start > end:
                raise HTTPException(422, "查询开始日期不能晚于结束日期")
        return asdict(self)


def legacy_archive_application_ids(candidate_ids=None):
    """还原旧4010主单、当前审核轮次、案件阶段和回款全结算谓词。"""
    header = aliased(LegacyFinanceRecord)
    source_fee = aliased(LegacyFinanceRecord)
    case_fee = aliased(LegacyFinanceRecord)
    receipts = aliased(LegacyFinanceRecord)
    objects = aliased(LegacyFinanceAllocation)
    receipt_objects = aliased(LegacyFinanceAllocation)
    audit = aliased(LegacyFinanceAudit)
    case_fee_id = cast(case_fee.source_payload["CaseFeeId"].as_string(), String)
    case_fee_source_database = func.coalesce(
        cast(case_fee.source_payload["_source_database"].as_string(), String), ""
    )
    settled_fees = (
        select(case_fee_id, case_fee_source_database).select_from(receipt_objects)
        .join(receipts, receipts.id == receipt_objects.legacy_finance_record_id)
        .join(case_fee, case_fee_id == receipt_objects.legacy_case_fee_id)
        .where(receipt_objects.source_table == "FAM_AR_Payment_Object",
               receipts.source_table == "FAM_AR_Payment",
               case_fee.source_table == "FAM_AR_CaseFee",
               case_fee.source_payload["_source_database"].as_string().is_not_distinct_from(
                   header.source_payload["_source_database"].as_string()),
               receipts.source_payload["_source_database"].as_string().is_not_distinct_from(
                   case_fee.source_payload["_source_database"].as_string()))
        .group_by(case_fee_id, case_fee_source_database)
        .having(func.count() == func.sum(case(
            (cast(receipts.source_payload["SettlementStatus"].as_string(), String) == "25", 1), else_=0,
        )))
    )
    source_fee_case_fee_id = cast(source_fee.source_payload["CaseFeeId"].as_string(), String)
    source_fee_database = func.coalesce(
        cast(source_fee.source_payload["_source_database"].as_string(), String), ""
    )
    conditions = [
        header.source_table == "FAM_InternalFee_Payment", header.is_active.is_(True),
        header.status_code.in_(("1", "2")),
    ]
    if candidate_ids is not None:
        conditions.append(header.legacy_id.in_(candidate_ids))
    return (
        select(header.legacy_id).distinct()
        .join(objects, objects.legacy_finance_record_id == header.id)
        .join(source_fee, source_fee.source_payload["InternalFeeId"].as_string() == objects.source_payload["InternalFeeId"].as_string())
        .join(LegacyCase, LegacyCase.CaseId == source_fee.source_payload["CaseId"].as_integer())
        .join(audit, audit.legacy_finance_record_id == header.id)
        .where(
            *conditions,
            # 迁移批次的 kind 命名不同；业务实体以实际来源表和主单外键确定。
            objects.source_table == "FAM_InternalFee_Payment_Object",
            source_fee.source_table == "FAM_InternalFee",
            audit.source_table == "FAM_InternalFee_Payment_Audit",
            source_fee.source_payload["_source_database"].as_string().is_not_distinct_from(
                header.source_payload["_source_database"].as_string()),
            audit.audit_status_code == "2",
            audit.audit_flow_id == header.source_payload["AuditFlowId"].as_string(),
            audit.audit_flow_node_id == header.source_payload["AuditFlowNodeId"].as_string(),
            audit.audit_round_id == header.source_payload["AuditRoundId"].as_string(),
            LegacyCase.CasePhaseId.not_in((106012, 206012, 306012, 406012, 506012)),
            tuple_(source_fee_case_fee_id, source_fee_database).in_(settled_fees),
        )
    )


def filter_internal_rows(rows: list[dict], **filters) -> list[dict]:
    """作用于完整授权结果，分页和汇总必须在此之后执行。"""
    text_fields = {
        "case_no": "case_no", "handling_lawyer": "handling_lawyer",
        "assistant": "lawyer_assistant", "source_person": "case_source",
        "customer_manager": "customer_manager", "investigator": "investigator", "payee": "payee",
        "applicant": "applicant", "hearing_lawyer": "hearing_lawyer", "court_case_no": "court_case_no",
        "certificate_no": "certificate_no",
    }
    result = []
    stages = set(filter(None, (value.strip() for value in filters.get("case_stages", "").split(","))))
    types = set(filter(None, (value.strip() for value in filters.get("fee_types", "").split(","))))
    for row in rows:
        data = row.get("data") or {}
        children = [(item.get("data") or {}) for item in data.get("application_items") or []]
        if filters.get("request_status") and row.get("status") != filters["request_status"].strip():
            continue
        if any(str(filters.get(key) or "").strip().casefold() not in
               " ".join(f"{item.get(field) or ''} {item.get(field + '_display_name') or ''}"
                        for item in ([data, *children] if key == "payee" else [data])).casefold()
               for key, field in text_fields.items()):
            continue
        if str(filters.get("customer") or "").strip().casefold() not in str(row.get("customer") or "").casefold():
            continue
        if stages and str(data.get("case_stage") or "") not in stages:
            continue
        if types and not any(str(item.get("internal_fee_type") or "") in types for item in [data, *children]):
            continue
        number = str(data.get("payment_application_no") or data.get("application_no") or row.get("serial_no") or "")
        if str(filters.get("application_no") or "").strip().casefold() not in number.casefold():
            continue
        if filters.get("payment_status") and data.get("payment_status") != filters["payment_status"]:
            continue
        if filters.get("paid_from") or filters.get("paid_to"):
            raw = str(data.get("paid_date") or data.get("payment_date") or "")[:10]
            if not raw:
                continue
            paid = date.fromisoformat(raw)
            if filters.get("paid_from") and paid < filters["paid_from"]:
                continue
            if filters.get("paid_to") and paid > filters["paid_to"]:
                continue
        excluded = False
        for prefix, field in (("application", "application_date"), ("audit", "reviewed_at")):
            start, end = filters.get(f"{prefix}_from"), filters.get(f"{prefix}_to")
            if not start and not end:
                continue
            raw = str(data.get(field) or "")[:10]
            if not raw:
                excluded = True
                break
            value = date.fromisoformat(raw)
            if (start and value < start) or (end and value > end):
                excluded = True
                break
        if not excluded:
            result.append(row)
    return result


async def enrich_internal_audit_dates(rows: list[dict], identity: dict, db: AsyncSession) -> None:
    """审核日期取当前旧审批轮次或明确审批事件，不以修改时间冒充。"""
    from app.core.permissions import _record_scope_conditions

    leaves = [item for row in rows for item in [row, *((row.get("data") or {}).get("application_items") or [])]]
    parent_ids = {int(item["data"]["internal_application_id"]) for item in leaves
                  if (item.get("data") or {}).get("internal_application_id")}
    parent_keys = dict((await db.execute(select(
        BusinessRecord.id, BusinessRecord.data["legacy_internal_payment_id"].as_string(),
    ).where(BusinessRecord.module == "finance_application", BusinessRecord.id.in_(parent_ids),
            *(await _record_scope_conditions(identity, db))))).all()) if parent_ids else {}
    keys = {str((item.get("data") or {}).get("legacy_internal_payment_id") or parent_keys.get(
        (item.get("data") or {}).get("internal_application_id")) or "") for item in leaves} - {""}
    dates = dict((await db.execute(select(LegacyFinanceRecord.legacy_id, func.max(LegacyFinanceAudit.audit_date))
        .join(LegacyFinanceAudit, LegacyFinanceAudit.legacy_finance_record_id == LegacyFinanceRecord.id)
        .where(LegacyFinanceRecord.source_table == "FAM_InternalFee_Payment", LegacyFinanceRecord.legacy_id.in_(keys),
               LegacyFinanceAudit.source_table == "FAM_InternalFee_Payment_Audit",
               LegacyFinanceAudit.audit_flow_id == LegacyFinanceRecord.source_payload["AuditFlowId"].as_string(),
               LegacyFinanceAudit.audit_flow_node_id == LegacyFinanceRecord.source_payload["AuditFlowNodeId"].as_string(),
               LegacyFinanceAudit.audit_round_id == LegacyFinanceRecord.source_payload["AuditRoundId"].as_string())
        .group_by(LegacyFinanceRecord.legacy_id))).all()) if keys else {}
    modern_ids = {item["id"] for item in leaves if not (item.get("data") or {}).get("legacy_kind")}
    events = dict((await db.execute(select(WorkflowEvent.record_id, func.max(WorkflowEvent.created_at)).where(
        WorkflowEvent.record_id.in_(modern_ids), WorkflowEvent.action.in_((
            "费用审批通过", "费用审批驳回", "内部提成退费审批通过", "内部提成退费审批驳回",
        )),
    ).group_by(WorkflowEvent.record_id))).all()) if modern_ids else {}
    for item in leaves:
        data = item.get("data") or {}
        key = str(data.get("legacy_internal_payment_id") or parent_keys.get(data.get("internal_application_id")) or "")
        value = dates.get(key) if key else events.get(item["id"])
        if not data.get("reviewed_at") and value:
            item["data"] = {**data, "reviewed_at": value.isoformat()}


def internal_page(rows: list[dict], page: int, page_size: int, *, amount_visible: bool) -> dict:
    start = (page - 1) * page_size
    totals = {"total_amount": None, "total_actual_commission": None, "total_cashed_amount": None}
    if amount_visible:
        data_rows = [row.get("data") or {} for row in rows]
        totals = {
            "total_amount": round(sum(float(data.get("amount") or 0) for data in data_rows), 2),
            "total_actual_commission": round(sum(float(
                data["actual_commission"] if data.get("actual_commission") is not None
                else data.get("amount") or 0
            ) for data in data_rows), 2),
            "total_cashed_amount": round(sum(float(data.get("cashed_amount") or 0) for data in data_rows), 2),
        }
    return {
        "items": rows[start:start + page_size], "total": len(rows),
        **totals, "amount_visible": amount_visible,
        "page": page, "page_size": page_size,
    }


async def internal_application_queue(identity: dict, db: AsyncSession, scope: str, **filters) -> list[dict]:
    from app.core.finance import _internal_fee_row, _internal_fee_rows
    from app.core.permissions import _record_scope_conditions
    from app.core.system import _allowed_field_keys
    from app.core.finance_batch_parity import group_commission_applications

    access = await _record_scope_conditions(identity, db)
    rejected = ("已拒绝", "已驳回", "已退回")
    conditions = [BusinessRecord.module == "finance_application", *access,
                  BusinessRecord.data["legacy_kind"].as_string() == "internal_payment",
                  BusinessRecord.status != "已删除"]
    if scope == "refused":
        conditions.append(BusinessRecord.status.in_(rejected))
    else:
        # 归档页只处理仍处于当前请款生命周期的主单。历史已审批/已作废主单
        # 由旧财务查询保留在审计数据中，不应在每次刷新时重新扫描。
        conditions.append(BusinessRecord.status.in_(("待审批", "待归档")))
        # The legacy archive predicate is a multi-table correlated query.  On
        # a modern installation there are no legacy finance rows at all, so
        # running it on every refresh needlessly holds the shared-query lock
        # until the 30s timeout (the old page then shows “查询结果计算超时”).
        # Probe the narrow source-table index first and only build the full
        # legacy predicate when legacy payment headers actually exist.
        candidate_ids = select(BusinessRecord.data["legacy_internal_payment_id"].as_string()).where(
            *conditions,
        ).scalar_subquery()
        legacy_header_id = await db.scalar(select(LegacyFinanceRecord.id).where(
            LegacyFinanceRecord.source_table == "FAM_InternalFee_Payment",
            LegacyFinanceRecord.is_active.is_(True),
        ).limit(1))
        if legacy_header_id is None:
            conditions.append(BusinessRecord.id == -1)
        else:
            conditions.append(BusinessRecord.data["legacy_internal_payment_id"].as_string().in_(
                legacy_archive_application_ids(candidate_ids)
            ))
    parents = list((await db.scalars(select(BusinessRecord).where(*conditions).order_by(
        BusinessRecord.updated_at.desc(), BusinessRecord.id.desc(),
    ))).all())
    parent_ids = {item.id for item in parents}
    kind = BusinessRecord.data["legacy_kind"].as_string()
    modern_conditions = [BusinessRecord.module == "finance", *access,
                         or_(kind.is_(None), kind.not_in(("internal_payment_line", "internal_fee_source")))]
    modern_conditions.append(BusinessRecord.status.in_(rejected if scope == "refused" else
        ("待到账", "待分配", "待结算", "待归档", "待审批")))
    modern_ids = set((await db.scalars(select(BusinessRecord.id).where(*modern_conditions))).all())
    child_ids = set((await db.scalars(select(BusinessRecord.id).where(
        BusinessRecord.module == "finance", *access, BusinessRecord.status != "已删除",
        kind == "internal_payment_line", BusinessRecord.data["internal_application_id"].as_integer().in_(parent_ids),
    ))).all()) if parents else set()
    all_rows = await _internal_fee_rows(
        identity, db, scope="queue", ids=modern_ids | child_ids, case_no="", handling_lawyer="",
        assistant="", source_person="", customer="", customer_manager="", investigator="",
        payment_status="", paid_from=None, paid_to=None, payee="", case_stages="", fee_types="",
    )
    children: dict[int, list[dict]] = {}
    for row in all_rows:
        if row["id"] in child_ids:
            children.setdefault(int(row["data"]["internal_application_id"]), []).append(row)
    case_ids = {int((item.data or {}).get("case_id") or 0) for item in parents}
    cases = {item.id: item for item in (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case", BusinessRecord.id.in_(case_ids), *access,
    ))).all()} if case_ids else {}
    allowed = await _allowed_field_keys(identity, db)
    rows = []
    for item in parents:
        data = item.data or {}
        row = _internal_fee_row(item, cases.get(int(data.get("case_id") or 0)), 0, allowed)
        row["data"].update({
            "applicant": item.owner, "application_items": children.get(item.id, []),
            "payment_application_no": data.get("application_no") or item.serial_no,
            "queue_status": "已拒绝" if scope == "refused" else "待归档",
            "read_only": True, "query_entity": "internal_application",
        })
        rows.append(row)
    modern = [row for row in all_rows if row["id"] in modern_ids
              and (scope == "refused" or row["status"] == "待归档")]
    rows.extend(group_commission_applications(modern))
    rows.sort(key=lambda row: (str(row.get("updated_at") or ""), row["id"]), reverse=True)
    await apply_finance_person_displays(rows, db)
    if filters.get("audit_from") or filters.get("audit_to"):
        await enrich_internal_audit_dates(rows, identity, db)
    return filter_internal_rows(rows, **filters)
