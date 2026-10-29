"""内部请款分类、审核和整单操作。"""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BusinessRecord, FinanceTransaction, WorkflowEvent
from app.core.constants import INTERNAL_REVIEW_APPROVE_ACTION, INTERNAL_REVIEW_REJECT_ACTION
from app.core.finance_batch_parity import group_commission_applications, is_explicit_internal_commission, is_internal_fee


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
        and is_explicit_internal_commission(item.data or {})
        and _is_refund_commission({"data": item.data or {}}, sources)
    }


def _application_key(item: BusinessRecord) -> tuple:
    data = item.data or {}
    imported_id = data.get("internal_application_id")
    if data.get("legacy_kind") == "internal_payment_line" and imported_id:
        return ("imported", int(imported_id))
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
    imported_ids = {int((item.data or {}).get("internal_application_id")) for item in anchors
                    if (item.data or {}).get("legacy_kind") == "internal_payment_line"
                    and (item.data or {}).get("internal_application_id")}
    numbers = {str((item.data or {}).get("payment_application_no") or "").strip()
               for item in anchors if str((item.data or {}).get("payment_application_no") or "").strip()
               and not (item.data or {}).get("internal_application_id")}
    match_conditions = []
    if numbers:
        match_conditions.append(BusinessRecord.data["payment_application_no"].as_string().in_(numbers))
    if imported_ids:
        match_conditions.append(BusinessRecord.data["internal_application_id"].as_integer().in_(imported_ids))
    statement = select(BusinessRecord).where(
        BusinessRecord.module == "finance", or_(*match_conditions),
    ).order_by(BusinessRecord.id)
    if lock:
        statement = statement.with_for_update()
    candidates = list((await db.scalars(statement)).all()) if match_conditions else []
    by_number: dict[tuple, list[BusinessRecord]] = {}
    for item in candidates:
        by_number.setdefault(_application_key(item), []).append(item)
    result: dict[int, BusinessRecord] = {}
    for anchor in anchors:
        key = _application_key(anchor)
        if key[0] == "single":
            result[anchor.id] = anchor
            continue
        same_number = by_number.get(key, [])
        if not same_number or (
            key[0] not in {"imported", "single"}
            and any(_application_key(item) != key for item in candidates
                    if str((item.data or {}).get("payment_application_no") or "").strip() == key[0])
        ):
            raise HTTPException(409, "请款单关联数据不一致，不能部分操作")
        for item in same_number:
            result[item.id] = item
    return list(result.values())


async def internal_review_rows(identity: dict, db: AsyncSession, kind: str) -> list[dict]:
    """按申请单展示互斥的内部审批队列。"""
    from app.core.finance import _internal_fee_rows

    rows = await _internal_fee_rows(
        identity, db, scope="review", case_no="", handling_lawyer="",
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
        commission = is_explicit_internal_commission(data)
        refund = commission and _is_refund_commission(row, sources)
        # 退费提成未归档时在“内部提成-待归档”，案件归档后才进入本队列。
        # commission_all：工作台“待审内部提成费用”，合并内部提成-待审核和内部提成(退费)-待审核两个队列。
        if kind in {"refund", "commission_all"} and refund and row["status"] == "待审批":
            selected.append({**row, "data": {**data, "is_refund": True}})
        elif row["status"] == "待审批" and (
            (kind in {"commission", "commission_all"} and commission and not refund)
            or (kind == "other" and not commission)
        ):
            selected.append(row)
    # BUG20261029002：旧系统导入的待审批请款明细（LIP-）也要案件已归档才进待审核，
    # 内部提成还要已结算；退费提成按 10.22 规则只看归档。
    legacy = {row["id"]: row for row in selected if (row.get("data") or {}).get("legacy_kind") == "internal_payment_line"}
    if legacy:
        from app.core.internal_commission_stage import archived_case_ids, legacy_line_settled_ids

        records = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(legacy)))).all())
        archived = await archived_case_ids(db, {int((item.data or {}).get("case_id") or 0) for item in records
                                                if str((item.data or {}).get("case_id") or "").isdigit()})
        settled = await legacy_line_settled_ids(db, [(item.id, item.data or {}) for item in records])
        keep = {item.id for item in records
                if str((item.data or {}).get("case_id") or "").isdigit() and int((item.data or {})["case_id"]) in archived
                and (item.id in settled or (legacy[item.id].get("data") or {}).get("is_refund"))}
        selected = [row for row in selected if row["id"] not in legacy or row["id"] in keep]
    if not selected:
        return []
    anchors = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_([row["id"] for row in selected]),
        BusinessRecord.module == "finance",
    ))).all())
    members = await _application_members(anchors, db, lock=False)
    from app.core.permissions import _record_scope_conditions
    scope_conditions = await _record_scope_conditions(identity, db)
    visible_ids = set((await db.scalars(select(BusinessRecord.id).where(
        BusinessRecord.id.in_([item.id for item in members]), *scope_conditions,
    ))).all())
    members = [item for item in members if item.id in visible_ids]
    projected = {row["id"]: row for row in rows}
    missing = [item for item in members if item.id not in projected]
    if missing:
        from app.core.finance import _internal_fee_row, _case_commission_lifecycle_statuses
        from app.core.system import _allowed_field_keys

        case_ids = {int((item.data or {}).get("case_id")) for item in missing
                    if str((item.data or {}).get("case_id") or "").isdigit()}
        cases = {item.id: item for item in (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "case", BusinessRecord.id.in_(case_ids), *scope_conditions,
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
        if row["id"] in refund_ids:
            row["data"] = {**(row.get("data") or {}), "is_refund": True}
    from app.core.finance_person_projection import apply_finance_person_displays
    grouped = group_commission_applications(full)
    def application_order(row):
        data = row.get("data") or {}
        return (str(data.get("internal_payment_submitted_at") or data.get("payment_applied_at")
                    or data.get("application_date") or row.get("created_at") or ""), row["id"])
    grouped.sort(key=application_order, reverse=True)
    return await apply_finance_person_displays(grouped, db)


async def review_internal_applications(
    fee_ids: list[int], kind: str, approved: bool, comment: str,
    identity: dict, db: AsyncSession,
) -> dict:
    """审批完整请款单，阻止跨类别或缺项的部分审批。"""
    from app.core.finance import _case_commission_lifecycle_statuses, _review_finance_fee_records
    from app.core.permissions import _record_scope_conditions

    from app.core.permissions import _permission_payload_for_identity
    permission = await _permission_payload_for_identity(identity, db)
    required_action = INTERNAL_REVIEW_APPROVE_ACTION if approved else INTERNAL_REVIEW_REJECT_ACTION
    action_keys = set(permission.get("action_keys") or [])
    if "*" not in action_keys and required_action not in action_keys:
        raise HTTPException(403, "当前角色没有内部费用审批动作权限")
    if not approved and not comment.strip():
        raise HTTPException(422, "拒绝审批必须填写理由")
    unique_ids = list(dict.fromkeys(fee_ids))
    anchors = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(unique_ids), BusinessRecord.module == "finance",
        *(await _record_scope_conditions(identity, db)),
    ).with_for_update())).all())
    if len(anchors) != len(unique_ids):
        raise HTTPException(404, "部分请款单不存在或无权访问")
    members = await _application_members(anchors, db, lock=True)
    refund_ids = await refund_commission_ids(members, db)
    lifecycle_statuses = await _case_commission_lifecycle_statuses(members, db)
    for item in members:
        data = item.data or {}
        if data.get("internal_payment_submitted") is False:
            raise HTTPException(409, "费用尚未提交付款申请，不能直接审批")
        commission = is_explicit_internal_commission(data)
        member_kind = "refund" if item.id in refund_ids else "commission" if commission else "other"
        if not is_internal_fee(data) or member_kind != kind:
            raise HTTPException(409, "请款单含其他审批类别，不能部分审批")
        effective_status = lifecycle_statuses.get(item.id, item.status)
        if effective_status != "待审批":
            raise HTTPException(409, "请款单含非待审批费用，不能部分审批")
    await _review_finance_fee_records(members, approved, comment, identity, db)
    await db.commit()
    return {"reviewed": len(members), "fee_ids": [item.id for item in members],
            "status": "已审批" if approved else "已驳回"}


async def pending_case_fee_settlements(identity: dict, db: AsyncSession) -> list[dict]:
    """按案件费用及实际到账展示待发放提成。"""
    from app.core.finance import _invoice_case_fee_rows
    from app.core.legacy_case_fee_settlement import legacy_case_fee_settlement_sources
    from app.core.permissions import _record_scope_conditions

    scope = await _record_scope_conditions(identity, db)
    commissions = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance", BusinessRecord.status != "已删除",
        BusinessRecord.data["fee_type"].as_string() == "内部费用",
        BusinessRecord.data["source_fee_id"].as_integer() > 0,
        *scope,
    ))).all()
    # 原费用与其付款明细均可迁入，同一旧提成只计来源实体一次。
    valid_commissions = [item for item in commissions
                         if ((item.data or {}).get("commission_type")
                             or (item.data or {}).get("legacy_kind") == "internal_fee_source")
                         and not (item.data or {}).get("commission_paid")
                         and (item.data or {}).get("legacy_kind") != "internal_payment_line"
                         and item.status not in {"已撤回", "已驳回", "已拒绝", "已作废"}]
    commission_amounts = {}
    for item in valid_commissions:
        data = item.data or {}
        source_id = int(data["source_fee_id"])
        value = data.get("actual_commission") if data.get("actual_commission") is not None else data.get("amount")
        if value is None or (source_id in commission_amounts and commission_amounts[source_id] is None):
            commission_amounts[source_id] = None
        else:
            commission_amounts[source_id] = round(commission_amounts.get(source_id, 0) + float(value), 2)
    source_ids = set(commission_amounts)
    legacy_sources = await legacy_case_fee_settlement_sources(db)
    legacy_source_ids = {record_id for record_id, source in legacy_sources.items() if source["eligible"]}
    source_ids.update(legacy_source_ids)
    if not source_ids:
        return []
    from app.core.finance_centers import record_center_conditions
    from app.core.finance import _record_id_in
    # 上千个来源编号用单个参数传入，避免逐个绑定参数带来的解析和规划开销。
    source_ids = set((await db.scalars(select(BusinessRecord.id).where(
        _record_id_in(source_ids), *scope, *record_center_conditions(identity),
    ))).all())
    if not source_ids:
        return []
    rows = await _invoice_case_fee_rows(identity, db, scope="company", ids=source_ids)
    rows = [row for row in rows if
            (row.get("data") or {}).get("base_fee_type") == "代理费"
            and not (row.get("data") or {}).get("refund_fee")
            and not (row.get("data") or {}).get("commission_paid")]
    # BUG20261029002：待结算只放已到账、已分配的案件费用；旧系统导入的来源按旧到账结算资格判断。
    from app.core.internal_commission_stage import allocated_fee_ids
    modern_ids = {row["id"] for row in rows if not legacy_sources.get(row["id"], {}).get("eligible")}
    allocated = await allocated_fee_ids(db, modern_ids)
    rows = [row for row in rows if legacy_sources.get(row["id"], {}).get("eligible") or (
        row["id"] in allocated
        and float((row.get("data") or {}).get("received_amount") or (row.get("data") or {}).get("cashed_amount") or 0) > 0
    )]
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
        legacy_source = legacy_sources.get(row["id"])
        row["data"] = {
            **data,
            "amount": commission_amounts.get(row["id"]) if data.get("amount") is not None else None,
            "actual_commission": commission_amounts.get(row["id"]) if data.get("amount") is not None else None,
            "commission_amount_available": commission_amounts.get(row["id"]) is not None,
            "cashed_amount": max(float(data["cashed_amount"]), legacy_source["cashed_amount"])
            if legacy_source and data.get("cashed_amount") is not None else data.get("cashed_amount"),
            "case_source": data.get("case_source") or case_data.get("case_source") or case_data.get("business_owner") or "",
            "quality_manager": data.get("quality_manager") or case_data.get("quality_manager") or case_data.get("quality_control") or "",
            "settlement_status": data.get("settlement_status") or data.get("payment_status") or "",
        }
    from app.core.finance_person_projection import apply_finance_person_displays
    return await apply_finance_person_displays(rows, db)


async def change_internal_application(
    fee_id: int, action: str, comment: str, identity: dict, db: AsyncSession,
) -> dict:
    """在同一事务中撤回或回滚请款单的全部费用。"""
    first, candidates = await _locked_internal_application(fee_id, identity, db)
    initial = first.data or {}
    applicant = str(initial.get("applicant") or "").strip()
    if not applicant or applicant != str(identity.get("username") or "").strip():
        raise HTTPException(403, "只有请款申请人可以撤回或回滚")
    if not comment.strip():
        raise HTTPException(422, "请输入操作原因")
    allowed = (
        {"草稿", "待到账", "待分配", "待结算", "待归档", "待审批"}
        if action == "withdraw" else
        {"待到账", "待分配", "待结算", "待归档", "待审批", "已审批", "待付款"}
    )
    invalid = [item.serial_no for item in candidates if item.status not in allowed]
    if invalid:
        raise HTTPException(409, "请款单包含不可操作的费用：" + "、".join(invalid))
    await _ensure_internal_application_unpaid(candidates, db, "撤回或回滚")
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
    return {"application_no": str(initial.get("payment_application_no") or "").strip() or first.serial_no,
            "fee_ids": [item.id for item in candidates], "status": target}


async def _locked_internal_application(
    fee_id: int, identity: dict, db: AsyncSession,
) -> tuple[BusinessRecord, list[BusinessRecord]]:
    from app.core.permissions import _ensure_record_module

    first = await _ensure_record_module(fee_id, "finance", identity, db)
    if not is_internal_fee(first.data or {}):
        raise HTTPException(422, "只有内部费用请款单可执行该操作")
    candidates = await _application_members([first], db, lock=True)
    if not candidates or first.id not in {item.id for item in candidates}:
        raise HTTPException(404, "请款单不存在")
    invalid = [item.serial_no for item in candidates if not is_internal_fee(item.data or {})]
    if invalid:
        raise HTTPException(409, "请款单包含非内部费用：" + "、".join(invalid))
    return first, candidates


async def _ensure_internal_application_unpaid(
    candidates: list[BusinessRecord], db: AsyncSession, action: str,
) -> None:
    ids = [item.id for item in candidates]
    paid_ids = set((await db.scalars(select(FinanceTransaction.finance_record_id).where(
        FinanceTransaction.finance_record_id.in_(ids), FinanceTransaction.transaction_type == "付款",
    ))).all())
    if paid_ids or any(
        float((item.data or {}).get("paid_amount") or 0) > 0
        or str((item.data or {}).get("writeoff_status") or "") == "已核销"
        for item in candidates
    ):
        raise HTTPException(409, f"请款单已有付款或核销记录，不能{action}")


async def submit_internal_application(
    fee_id: int, comment: str, identity: dict, db: AsyncSession,
) -> dict:
    """由申请人整单提交尚未审批的内部请款。"""
    first, candidates = await _locked_internal_application(fee_id, identity, db)
    if any((item.data or {}).get("internal_payment_submitted") is False for item in candidates):
        raise HTTPException(409, "请先从案件内部结算提交付款申请")
    applicant = str((first.data or {}).get("applicant") or "").strip()
    if not applicant or applicant != str(identity.get("username") or "").strip():
        raise HTTPException(403, "只有请款申请人可以提交审批")
    invalid = [item.serial_no for item in candidates if item.status not in {"草稿", "已退回"}]
    if invalid:
        raise HTTPException(409, "请款单包含不可提交的费用：" + "、".join(invalid))
    refund_ids = await refund_commission_ids(candidates, db)
    kinds = {"refund" if item.id in refund_ids else
             "commission" if is_explicit_internal_commission(item.data or {}) else "other"
             for item in candidates}
    if len(kinds) != 1:
        raise HTTPException(409, "请款单包含不同费用类别，不能混合提交")
    missing = [item.serial_no for item in candidates
               if not (item.data or {}).get("handler") or not (item.data or {}).get("case_no")]
    if missing:
        raise HTTPException(422, "缺少费用审批要素：" + "、".join(missing))
    await _ensure_internal_application_unpaid(candidates, db, "提交审批")
    for item in candidates:
        previous = item.status
        item.status = "待审批"
        item.data = {**(item.data or {}), "payment_status": "待审批"}
        db.add(WorkflowEvent(
            record_id=item.id, action="提交费用审批", from_status=previous,
            to_status="待审批", operator=identity["username"], comment=comment.strip(),
        ))
    await db.commit()
    return {"application_no": str((first.data or {}).get("payment_application_no") or "").strip() or first.serial_no,
            "fee_ids": [item.id for item in candidates], "status": "待审批"}


async def void_internal_application(
    fee_id: int, comment: str, identity: dict, db: AsyncSession,
) -> dict:
    """将已拒绝请款单的全部费用作废。"""
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(403, "当前角色没有请款单作废权限")
    first, candidates = await _locked_internal_application(fee_id, identity, db)
    invalid = [item.serial_no for item in candidates if item.status not in {"已拒绝", "已退回", "已驳回"}]
    if invalid:
        raise HTTPException(409, "请款单包含不可作废的费用：" + "、".join(invalid))
    await _ensure_internal_application_unpaid(candidates, db, "作废")
    changed_at = datetime.now().isoformat(timespec="seconds")
    for item in candidates:
        previous = item.status
        item.status = "已作废"
        item.data = {
            **(item.data or {}), "payment_status": "已作废",
            "void_comment": comment.strip(), "voided_by": identity["username"],
            "voided_at": changed_at,
        }
        db.add(WorkflowEvent(
            record_id=item.id, action="请款单作废", from_status=previous,
            to_status="已作废", operator=identity["username"],
            comment=comment.strip() or "已拒绝请款单作废",
        ))
    await db.commit()
    return {"application_no": str((first.data or {}).get("payment_application_no") or "").strip() or first.serial_no,
            "fee_ids": [item.id for item in candidates], "status": "已作废"}
