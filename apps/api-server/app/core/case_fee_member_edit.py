"""501384（fwl 11-04）：案件费用新建后还没产生任何数据时，本案人员都能修改、删除；
一旦有了提交审批、申请付款、退费、回款、开票、结算或核销、付款，就只有分配了“修改/删除案件费用”权限的角色能改删（原规则）。
本案人员和“案件任务只能发给本案人员”同一口径（case_task_members.case_member_usernames）。
"""
from app.core.dependencies import AsyncSession, BusinessRecord

# 新建后没动过的状态：新系统新建是“草稿”，旧系统导入的是“已记录”；其他状态（待审批、已通知、已付款…）都算已经办过。
UNTOUCHED_STATUSES = frozenset({"草稿", "已记录"})
ACTIVITY_AMOUNTS = (
    "payment_requested_amount", "applied_amount", "paid_amount", "cashed_amount", "received_amount",
    "invoice_amount", "invoiced_amount", "refund_requested_amount", "refunded_amount", "refund_amount",
    "settled_amount", "settlement_amount", "writeoff_amount",
)
ACTIVITY_MARKS = (
    "payment_application_no", "invoice_no", "invoice_record_id", "receipt_attachment_id", "bill_no",
    "settlement_no", "settlement_id", "settled_at", "writeoff_at", "written_off_at", "submitted_for_approval_at",
)
MEMBER_EDIT_DENIED = "这笔费用已经有审批、付款、退费、回款、开票或结算记录，只有分配了修改/删除案件费用权限的角色才能修改或删除"


def _amount(value) -> float:
    try:
        return abs(float(value or 0))
    except (TypeError, ValueError):
        return 0.0


def fee_has_activity(item: BusinessRecord, projected: dict | None = None) -> bool:
    """费用是否已经产生了数据（状态不再是新建，或付款、退费、回款、开票、结算、核销有任何一项）。"""
    if item.status not in UNTOUCHED_STATUSES:
        return True
    for source in (item.data or {}, projected or {}):
        if any(_amount(source.get(key)) > 0 for key in ACTIVITY_AMOUNTS):
            return True
        if any(str(source.get(key) or "").strip() not in ("", "0", "/", "—") for key in ACTIVITY_MARKS):
            return True
        if source.get("receipt_files") or source.get("bill_files") or source.get("invoices"):
            return True
    return False


async def member_may_change_untouched_fee(item: BusinessRecord, case_record: BusinessRecord | None, identity: dict, db: AsyncSession) -> bool:
    """本案人员改删还没产生数据的案件费用（内部结算费用仍按“内部结算”权限，不在此列）。"""
    from app.core.case_task_members import case_member_usernames
    from app.core.finance_batch_parity import is_internal_fee
    if not case_record or case_record.module != "case" or is_internal_fee(item.data or {}):
        return False
    username = str(identity.get("username") or "").strip().lower()
    if not username or username not in case_member_usernames(case_record):
        return False
    if fee_has_activity(item):
        return False
    from app.core.finance import _invoice_case_fee_rows
    rows = await _invoice_case_fee_rows(identity, db, scope="company", ids={item.id}, scope_authorized_fee_ids={item.id},
                                        include_all_fee_types=True, force_amount_projection=True)
    return len(rows) == 1 and not fee_has_activity(item, rows[0].get("data") or {})
