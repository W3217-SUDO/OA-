"""内部请款分类、审核和整单操作。"""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BusinessRecord, FinanceTransaction, WorkflowEvent
from app.core.finance_batch_parity import group_commission_applications, is_internal_fee


def external_finance_condition():
    """普通付款列表在分页前排除内部费用。"""
    data = BusinessRecord.data
    return ~or_(
        func.coalesce(data["expense_scope"].as_string(), "") == "内部",
        func.coalesce(data["fee_type"].as_string(), "").in_(("内部费用", "内部提成", "INTERNAL")),
        func.coalesce(data["commission_lifecycle"].as_string(), "") != "",
    )


def _is_refund_commission(row: dict, sources: dict[int, BusinessRecord]) -> bool:
    data = row.get("data") or {}
    source_id = data.get("source_fee_id")
    source = sources.get(int(source_id)) if str(source_id or "").isdigit() else None
    source_data = (source.data or {}) if source else {}
    return bool(
        data.get("is_refund")
        or float(data.get("amount") or 0) < 0
        or (source_data.get("refund_fee") is True
            and source_data.get("fee_type") == "代理费")
    )


async def refund_commission_ids(items: list[BusinessRecord], db: AsyncSession) -> set[int]:
    source_ids = {
        int((item.data or {}).get("source_fee_id"))
        for item in items
        if str((item.data or {}).get("source_fee_id") or "").isdigit()
    }
    sources = {
        item.id: item for item in (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "finance", BusinessRecord.id.in_(source_ids),
        ))).all()
    } if source_ids else {}
    return {
        item.id for item in items
        if is_internal_fee(item.data or {})
        and str((item.data or {}).get("commission_type") or "").strip()
        and _is_refund_commission({"data": item.data or {}}, sources)
    }


def _application_key(item: BusinessRecord) -> tuple:
    data = item.data or {}
    number = str(data.get("payment_application_no") or "").strip()
    if not number:
        return ("single", item.id)
    return (
        number, str(data.get("case_no") or ""),
        str(data.get("source_fee_id") or ""), str(data.get("applicant") or ""),
    )


async def _application_members(
    anchors: list[BusinessRecord], db: AsyncSession, *, lock: bool,
) -> list[BusinessRecord]:
    numbers = {str((item.data or {}).get("payment_application_no") or "").strip()
               for item in anchors if str((item.data or {}).get("payment_application_no") or "").strip()}
    statement = select(BusinessRecord).where(
        BusinessRecord.module == "finance",
        BusinessRecord.data["payment_application_no"].as_string().in_(numbers),
    ).order_by(BusinessRecord.id)
    if lock:
        statement = statement.with_for_update()
    candidates = list((await db.scalars(statement)).all()) if numbers else []
    by_number: dict[str, list[BusinessRecord]] = {}
    for item in candidates:
        by_number.setdefault(_application_key(item)[0], []).append(item)
    result: dict[int, BusinessRecord] = {}
    for anchor in anchors:
        key = _application_key(anchor)
        if key[0] == "single":
            result[anchor.id] = anchor
            continue
        same_number = by_number.get(key[0], [])
        if not same_number or any(_application_key(item) != key for item in same_number):
            raise HTTPException(409, "请款单关联数据不一致，不能部分操作")
        for item in same_number:
            result[item.id] = item
    return list(result.values())


async def internal_review_rows(identity: dict, db: AsyncSession, kind: str) -> list[dict]:
    """按申请单展示互斥的内部审批队列。"""
    from app.core.finance import _internal_fee_rows

    rows = await _internal_fee_rows(
        identity, db, scope="company", case_no="", handling_lawyer="",
        assistant="", source_person="", customer="", customer_manager="",
        investigator="", payment_status="", paid_from=None, paid_to=None,
        payee="", case_stages="", fee_types="",
    )
    source_ids = {
        int((row.get("data") or {}).get("source_fee_id"))
        for row in rows
        if str((row.get("data") or {}).get("source_fee_id") or "").isdigit()
    }
    sources = {
        item.id: item for item in (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "finance", BusinessRecord.id.in_(source_ids),
        ))).all()
    } if source_ids else {}
    selected = []
    for row in rows:
        data = row.get("data") or {}
        commission = bool(str(data.get("commission_type") or "").strip())
        refund = commission and _is_refund_commission(row, sources)
        if kind == "refund" and refund and row["status"] in {"待结算", "待归档", "待审批"}:
            selected.append({**row, "status": "待审批", "data": {**data, "is_refund": True}})
        elif row["status"] == "待审批" and (
            (kind == "commission" and commission and not refund)
            or (kind == "other" and not commission)
        ):
            selected.append(row)
    if not selected:
        return []
    anchors = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_([row["id"] for row in selected]),
        BusinessRecord.module == "finance",
    ))).all())
    members = await _application_members(anchors, db, lock=False)
    projected = {row["id"]: row for row in rows}
    missing = [item for item in members if item.id not in projected]
    if missing:
        from app.core.finance import _internal_fee_row, _case_commission_lifecycle_statuses
        from app.core.system import _allowed_field_keys

        case_ids = {int((item.data or {}).get("case_id")) for item in missing
                    if str((item.data or {}).get("case_id") or "").isdigit()}
        cases = {item.id: item for item in (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "case", BusinessRecord.id.in_(case_ids),
        ))).all()} if case_ids else {}
        paid = (await db.execute(select(
            FinanceTransaction.finance_record_id, func.sum(FinanceTransaction.amount),
        ).where(
            FinanceTransaction.finance_record_id.in_([item.id for item in missing]),
            FinanceTransaction.transaction_type == "付款",
        ).group_by(FinanceTransaction.finance_record_id))).all()
        paid_by_id = {item_id: float(amount or 0) for item_id, amount in paid}
        statuses = await _case_commission_lifecycle_statuses(missing, db)
        allowed_fields = await _allowed_field_keys(identity, db)
        for item in missing:
            case = cases.get(int((item.data or {}).get("case_id") or 0))
            projected[item.id] = _internal_fee_row(
                item, case, paid_by_id.get(item.id, 0), allowed_fields, statuses.get(item.id),
            )
    full = [projected[item.id] for item in members]
    refund_ids = await refund_commission_ids(members, db)
    for row in full:
        if row["id"] in refund_ids and row["status"] in {"待结算", "待归档", "待审批"}:
            row["status"] = "待审批"
            row["data"] = {**(row.get("data") or {}), "is_refund": True}
    return group_commission_applications(full)


async def review_internal_applications(
    fee_ids: list[int], kind: str, approved: bool, comment: str,
    identity: dict, db: AsyncSession,
) -> dict:
    """审批完整请款单，阻止跨类别或缺项的部分审批。"""
    from app.core.finance import _review_finance_fee_records
    from app.core.permissions import _record_scope_conditions

    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(403, "当前角色没有内部请款审批权限")
    unique_ids = list(dict.fromkeys(fee_ids))
    anchors = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(unique_ids), BusinessRecord.module == "finance",
        *(await _record_scope_conditions(identity, db)),
    ).with_for_update())).all())
    if len(anchors) != len(unique_ids):
        raise HTTPException(404, "部分请款单不存在或无权访问")
    members = await _application_members(anchors, db, lock=True)
    refund_ids = await refund_commission_ids(members, db)
    for item in members:
        data = item.data or {}
        commission = bool(str(data.get("commission_type") or "").strip())
        member_kind = "refund" if item.id in refund_ids else "commission" if commission else "other"
        if not is_internal_fee(data) or member_kind != kind:
            raise HTTPException(409, "请款单含其他审批类别，不能部分审批")
        allowed = {"待审批", "待结算", "待归档"} if kind == "refund" else {"待审批"}
        if item.status not in allowed:
            raise HTTPException(409, "请款单含非待审批费用，不能部分审批")
    await _review_finance_fee_records(members, approved, comment, identity, db)
    await db.commit()
    return {"reviewed": len(members), "fee_ids": [item.id for item in members],
            "status": "已审批" if approved else "已驳回"}


async def pending_case_fee_settlements(identity: dict, db: AsyncSession) -> list[dict]:
    """按案件费用及实际到账展示待发放提成。"""
    from app.core.finance import _invoice_case_fee_rows
    from app.core.permissions import _record_scope_conditions

    scope = await _record_scope_conditions(identity, db)
    commissions = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance", BusinessRecord.status != "已删除",
        BusinessRecord.data["fee_type"].as_string() == "内部费用",
        BusinessRecord.data["source_fee_id"].as_integer() > 0,
        *scope,
    ))).all()
    source_ids = {
        int((item.data or {}).get("source_fee_id"))
        for item in commissions
        if (item.data or {}).get("commission_type")
        and not (item.data or {}).get("commission_paid")
        and item.status not in {"已撤回", "已驳回", "已拒绝", "已作废"}
    }
    if not source_ids:
        return []
    rows = await _invoice_case_fee_rows(identity, db, scope="company", ids=source_ids)
    rows = [row for row in rows if
            (row.get("data") or {}).get("base_fee_type") == "代理费"
            and not (row.get("data") or {}).get("refund_fee")
            and not (row.get("data") or {}).get("commission_paid")]
    case_ids = {
        int((row.get("data") or {}).get("case_id"))
        for row in rows if str((row.get("data") or {}).get("case_id") or "").isdigit()
    }
    cases = {
        item.id: item for item in (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "case", BusinessRecord.id.in_(case_ids), *scope,
        ))).all()
    } if case_ids else {}
    for row in rows:
        data = row["data"]
        case = cases.get(int(data.get("case_id") or 0))
        case_data = (case.data or {}) if case else {}
        row["data"] = {
            **data,
            "case_source": data.get("case_source") or case_data.get("case_source") or case_data.get("business_owner") or "",
            "quality_manager": data.get("quality_manager") or case_data.get("quality_manager") or case_data.get("quality_control") or "",
            "settlement_status": data.get("settlement_status") or data.get("payment_status") or "",
        }
    return rows


async def change_internal_application(
    fee_id: int, action: str, comment: str, identity: dict, db: AsyncSession,
) -> dict:
    """在同一事务中撤回或回滚请款单的全部费用。"""
    from app.core.permissions import _ensure_record_module

    first = await _ensure_record_module(fee_id, "finance", identity, db)
    initial = first.data or {}
    if not is_internal_fee(initial):
        raise HTTPException(422, "只有内部费用请款单可执行该操作")
    application_no = str(initial.get("payment_application_no") or "").strip()
    candidates = await _application_members([first], db, lock=True)
    if not candidates or first.id not in {item.id for item in candidates}:
        raise HTTPException(404, "请款单不存在")
    applicant = str(initial.get("applicant") or "").strip()
    if not applicant or applicant != str(identity.get("username") or "").strip():
        raise HTTPException(403, "只有请款申请人可以撤回或回滚")
    if not comment.strip():
        raise HTTPException(422, "请输入操作原因")
    allowed = (
        {"草稿", "待结算", "待归档", "待审批"}
        if action == "withdraw" else
        {"待结算", "待归档", "待审批", "已审批", "待付款"}
    )
    invalid = [item.serial_no for item in candidates if item.status not in allowed or not is_internal_fee(item.data or {})]
    if invalid:
        raise HTTPException(409, "请款单包含不可操作的费用：" + "、".join(invalid))
    ids = [item.id for item in candidates]
    paid_ids = set((await db.scalars(select(FinanceTransaction.finance_record_id).where(
        FinanceTransaction.finance_record_id.in_(ids), FinanceTransaction.transaction_type == "付款",
    ))).all())
    if paid_ids or any(
        float((item.data or {}).get("paid_amount") or 0) > 0
        or str((item.data or {}).get("writeoff_status") or "") == "已核销"
        for item in candidates
    ):
        raise HTTPException(409, "请款单已有付款或核销记录，不能撤回或回滚")
    target = "已撤回" if action == "withdraw" else "草稿"
    changed_at = datetime.now().isoformat(timespec="seconds")
    for item in candidates:
        previous = item.status
        item.status = target
        item.data = {
            **(item.data or {}), "payment_status": target,
            ("cancel_reason" if action == "withdraw" else "rollback_comment"): comment.strip(),
            ("canceled_by" if action == "withdraw" else "rolled_back_by"): identity["username"],
            ("canceled_at" if action == "withdraw" else "rolled_back_at"): changed_at,
        }
        db.add(WorkflowEvent(
            record_id=item.id, action="内部请款单撤回" if action == "withdraw" else "内部请款单回滚",
            from_status=previous, to_status=target, operator=identity["username"],
            comment=comment.strip(),
        ))
    await db.commit()
    return {"application_no": application_no or first.serial_no, "fee_ids": ids, "status": target}
