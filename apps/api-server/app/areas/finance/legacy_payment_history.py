"""按旧请款状态读取历史付款申请，供财务各入口只读展示。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import BigInteger, cast, func, or_, select

from app.core.dependencies import (
    AsyncSession,
    LegacyFinanceAllocation,
    LegacyFinanceAudit,
    LegacyFinanceRecord,
    current_identity,
    get_db,
    settings,
)
from app.core.legacy_sync import (
    _legacy_finance_audit_table_exists,
    _legacy_finance_scope_conditions,
)
from app.core.system import _allowed_field_keys


router = APIRouter()

# 源状态由旧 FAM_AP_Payment.PaymentStatus 确定，不使用新系统审批状态推测。
PAYMENT_STATUS_LABELS = {
    "0": "创建待提交",
    "1": "待审批",
    "2": "审批中",
    "3": "待付款",
    "4": "已驳回",
    "5": "已作废",
    "6": "待核销",
    "7": "已付款",
}

VIEW_STATUS_CODES = {
    "audit": ("1", "2"),
    "waiting": ("3",),
    "print": ("3",),
    "package": ("6", "7"),
    "writeoff": ("6",),
}


def _payment_status_label(item: LegacyFinanceRecord) -> str:
    label = (item.status_label or "").strip()
    if label and not label.startswith("旧状态码 ") and not label.startswith("legacy_status_"):
        return label
    return PAYMENT_STATUS_LABELS.get(item.status_code, label)


def _payment_history_row(
    item: LegacyFinanceRecord,
    *,
    case_numbers: list[str],
    show_amount: bool,
) -> dict:
    source = item.source_payload or {}
    return {
        "id": item.id,
        "source_table": item.source_table,
        "legacy_id": item.legacy_id,
        "status_code": item.status_code,
        "status_label": _payment_status_label(item),
        "primary_amount": round(float(item.primary_amount or 0), 2) if show_amount else None,
        "legacy_contract_no": item.legacy_contract_no,
        "legacy_case_no": item.legacy_case_no,
        "legacy_customer_no": item.legacy_customer_no,
        "application_no": source.get("ApplicationNo") or "",
        "application_date": source.get("ApplicationDate") or None,
        "applicant": source.get("Applicant") or "",
        "deadline": source.get("DeadLine") or None,
        "payment_date": source.get("PaymentDate") or None,
        "package_no": source.get("PackageNo") or "",
        "payer_name": source.get("PayerName") or "",
        "payment_type_id": source.get("PaymentTypeId"),
        "case_numbers": case_numbers,
        "read_only": True,
    }


@router.get(f"{settings.api_prefix}/finance/legacy-payment-history")
async def list_legacy_payment_history(
    view: str = Query(..., pattern="^(mine|audit|waiting|print|package|writeoff|query)$"),
    keyword: str = "",
    status_code: str = Query("", pattern="^(|[0-7])$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """保留旧表的状态和数据范围，将历史请款投影到原业务入口。"""
    if status_code and view not in {"mine", "query"}:
        raise HTTPException(status_code=422, detail="当前历史请款入口不支持自选状态")

    scope = [
        *(await _legacy_finance_scope_conditions(identity, db)),
        LegacyFinanceRecord.record_kind == "ap_payment",
        LegacyFinanceRecord.source_table == "FAM_AP_Payment",
        LegacyFinanceRecord.is_active.is_(True),
    ]
    count_rows = (await db.execute(
        select(LegacyFinanceRecord.status_code, func.count())
        .where(*scope)
        .group_by(LegacyFinanceRecord.status_code)
    )).all()
    status_counts = {code: 0 for code in PAYMENT_STATUS_LABELS}
    status_counts.update({str(code): int(count) for code, count in count_rows})

    conditions = list(scope)
    if view == "mine":
        conditions.append(LegacyFinanceRecord.source_payload["Applicant"].as_string() == identity["username"])
    elif view == "audit":
        if not await _legacy_finance_audit_table_exists(db):
            raise HTTPException(status_code=503, detail="历史请款审批记录尚未导入")
        conditions.extend([
            LegacyFinanceRecord.status_code.in_(VIEW_STATUS_CODES["audit"]),
            LegacyFinanceRecord.id.in_(
                select(LegacyFinanceAudit.legacy_finance_record_id).where(
                    LegacyFinanceAudit.source_table == "FAM_AP_Payment_Audit",
                    LegacyFinanceAudit.audit_status_code == "2",
                    LegacyFinanceAudit.auditor == identity["username"],
                )
            ),
        ])
    elif view in VIEW_STATUS_CODES:
        conditions.append(LegacyFinanceRecord.status_code.in_(VIEW_STATUS_CODES[view]))

    if status_code:
        conditions.append(LegacyFinanceRecord.status_code == status_code)
    if keyword.strip():
        needle = f"%{keyword.strip()}%"
        conditions.append(or_(
            LegacyFinanceRecord.legacy_id.ilike(needle),
            LegacyFinanceRecord.legacy_contract_no.ilike(needle),
            LegacyFinanceRecord.legacy_case_no.ilike(needle),
            LegacyFinanceRecord.legacy_customer_no.ilike(needle),
            LegacyFinanceRecord.source_payload["ApplicationNo"].as_string().ilike(needle),
            LegacyFinanceRecord.source_payload["PayerName"].as_string().ilike(needle),
            LegacyFinanceRecord.id.in_(
                select(LegacyFinanceAllocation.legacy_finance_record_id).where(
                    LegacyFinanceAllocation.legacy_case_no.ilike(needle),
                    LegacyFinanceAllocation.legacy_finance_record_id.is_not(None),
                )
            ),
        ))

    total = int(await db.scalar(
        select(func.count()).select_from(LegacyFinanceRecord).where(*conditions)
    ) or 0)
    rows = list((await db.scalars(
        select(LegacyFinanceRecord)
        .where(*conditions)
        .order_by(
            func.coalesce(LegacyFinanceRecord.source_payload["ApplicationDate"].as_string(), "").desc(),
            func.coalesce(cast(LegacyFinanceRecord.source_payload["PaymentId"].as_string(), BigInteger), 0).desc(),
            LegacyFinanceRecord.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).all())

    case_numbers_by_record = {item.id: set() for item in rows}
    if rows:
        allocation_rows = (await db.execute(
            select(
                LegacyFinanceAllocation.legacy_finance_record_id,
                LegacyFinanceAllocation.legacy_case_no,
            ).where(
                LegacyFinanceAllocation.legacy_finance_record_id.in_(list(case_numbers_by_record)),
                LegacyFinanceAllocation.is_active.is_(True),
            )
        )).all()
        for record_id, case_no in allocation_rows:
            if case_no:
                case_numbers_by_record[record_id].add(case_no)
    for item in rows:
        if item.legacy_case_no:
            case_numbers_by_record[item.id].add(item.legacy_case_no)

    show_amount = "finance.amount" in await _allowed_field_keys(identity, db)
    return {
        "items": [
            _payment_history_row(
                item,
                case_numbers=sorted(case_numbers_by_record[item.id]),
                show_amount=show_amount,
            )
            for item in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "amount_visible": show_amount,
        "status_counts": status_counts,
        "read_only": True,
    }
