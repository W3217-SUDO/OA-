"""案件费用“移到其他案子”（10.22 第8行）。

用户确认的规则（全部按定位文档建议）：
- 目标案件手动输入案件编号；同一客户优先按客户记录 ID，其次客户编号，都缺失时才按客户名称；
- 合同编号保留原值；已有后续单据（申请付款、开票、回款、付款、费用通知、提成、退费）的费用不允许迁移；
- 原案或目标案处于归档中、已归档或已合并时不允许；只限律所费用、平台费用；
- 原案、目标案各记一条系统日志，费用本身也记一条；不要求填写原因。
"""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select

from app.models import BusinessRecord, WorkflowEvent

MOVE_BLOCKED_CASE_STATUSES = {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档", "已合并"}
MOVABLE_FEE_SCOPES = {"律所", "平台"}
INACTIVE_DOWNSTREAM_STATUSES = {"已删除", "已作废", "已撤回", "已驳回", "已取消"}


def _text(value) -> str:
    return str(value or "").strip()


def _fee_scope(fee: BusinessRecord) -> str:
    return _text((fee.data or {}).get("expense_scope")) or "律所"


def same_customer(source: BusinessRecord, target: BusinessRecord) -> bool:
    """客户记录 ID → 客户编号 → 客户名称，取两案都有的最精确口径比较。"""
    source_data, target_data = source.data or {}, target.data or {}
    for keys in (("customer_record_id", "customer_id"), ("customer_no",)):
        left = next((_text(source_data.get(key)) for key in keys if _text(source_data.get(key))), "")
        right = next((_text(target_data.get(key)) for key in keys if _text(target_data.get(key))), "")
        if left and right:
            return left == right
    return bool(_text(source.customer)) and _text(source.customer) == _text(target.customer)


def _amount(value) -> float:
    try:
        return abs(float(value or 0))
    except (TypeError, ValueError):
        return 0.0


async def downstream_blockers(fee: BusinessRecord, source: BusinessRecord, identity: dict, db) -> list[str]:
    """列出挡住迁移的后续单据；为空才允许迁移。"""
    from app.core.case_merge import _case_record_link_condition
    from app.core.finance import _invoice_case_fee_rows

    data = fee.data or {}
    projected = {}
    rows = await _invoice_case_fee_rows(identity, db, scope="company", ids={fee.id},
        scope_authorized_fee_ids={fee.id}, include_all_fee_types=True, force_amount_projection=True)
    if len(rows) == 1:
        projected = rows[0].get("data") or {}
    sources = (projected, data)
    reasons: list[str] = []
    for fields, label in (
        (("payment_requested_amount",), "已申请付款"),
        (("invoice_amount", "invoiced_amount"), "已开票"),
        (("cashed_amount", "received_amount"), "已回款"),
        (("paid_amount",), "已付款"),
        (("refund_requested_amount", "refunded_amount"), "已办理退费"),
    ):
        if any(_amount(item.get(field)) > 0 for field in fields for item in sources):
            reasons.append(label)
    if _text(data.get("payment_application_no")) and "已申请付款" not in reasons:
        reasons.append("已申请付款")

    async def active(rows):
        return [row for row in rows if _text(row.status) not in INACTIVE_DOWNSTREAM_STATUSES]

    notices = await active((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance_fee_inform",
    ))).all())
    if any(int((row.data or {}).get("source_fee_id") or 0) == fee.id
           or fee.id in [int(item) for item in ((row.data or {}).get("linked_fee_ids") or []) if str(item).isdigit()]
           for row in notices):
        reasons.append("已发费用通知")
    commissions = await active((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance",
        BusinessRecord.data["source_fee_id"].as_integer() == fee.id,
    ))).all())
    if commissions:
        reasons.append("已生成提成")
    linked = await active((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module.in_(["refund", "invoice", "contract_payment"]),
        _case_record_link_condition(source, db),
    ))).all())
    for row in linked:
        row_data = row.data or {}
        if row.module == "refund" and int(row_data.get("fee_record_id") or 0) == fee.id and "已办理退费" not in reasons:
            reasons.append("已办理退费")
        if row.module == "invoice" and fee.id in [int(item) for item in (row_data.get("case_fee_ids") or []) if str(item).isdigit()] and "已开票" not in reasons:
            reasons.append("已开票")
        if row.module == "contract_payment" and any(int(line.get("case_fee_id") or 0) == fee.id for line in (row_data.get("lines") or []) if isinstance(line, dict)) and "已申请付款" not in reasons:
            reasons.append("已申请付款")
    return reasons


async def move_case_fee(fee_id: int, target_case_no: str, identity: dict, db) -> BusinessRecord:
    from app.core.cases import _case_action_granted
    from app.core.permissions import _ensure_record_module, _record_scope_conditions, _require_record_owner_or_manager

    fee = await _ensure_record_module(fee_id, "finance", identity, db)
    if fee.status == "已删除":
        raise HTTPException(status_code=404, detail="费用记录不存在")
    if _fee_scope(fee) not in MOVABLE_FEE_SCOPES:
        raise HTTPException(status_code=422, detail="只有律所费用和平台费用可以移到其他案子")
    data = dict(fee.data or {})
    source_id = int(data.get("case_record_id") or data.get("case_id") or 0)
    source = await db.get(BusinessRecord, source_id) if source_id else None
    if not source or source.module != "case":
        raise HTTPException(status_code=409, detail="该费用没有关联有效案件，不能移到其他案子")
    if _text(data.get("case_no")) and _text(data.get("case_no")) != source.serial_no:
        raise HTTPException(status_code=409, detail="费用的案件 ID 与案件编号指向不同案件，请先修正关联")
    await _ensure_record_module(source.id, "case", identity, db)
    await _require_record_owner_or_manager(fee, identity, db)
    if not await _case_action_granted(identity, db, "case.fee.move"):
        raise HTTPException(status_code=403, detail="当前账号没有“移到其他案件”权限")
    target_no = _text(target_case_no)
    if target_no == source.serial_no:
        raise HTTPException(status_code=422, detail="目标案件不能与当前案件相同")
    target = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == "case", BusinessRecord.serial_no == target_no,
        *(await _record_scope_conditions(identity, db)),
    ))
    if not target:
        raise HTTPException(status_code=404, detail="未找到目标案件，或当前账号无权查看")
    for record in sorted((source, target, fee), key=lambda item: item.id):
        await db.refresh(record, with_for_update=True)
    if source.status in MOVE_BLOCKED_CASE_STATUSES or target.status in MOVE_BLOCKED_CASE_STATUSES:
        raise HTTPException(status_code=409, detail="归档中、已归档或已合并的案件不能迁出或迁入费用")
    if not same_customer(source, target):
        raise HTTPException(status_code=422, detail="目标案件与当前案件不属于同一客户，不允许迁移")
    reasons = await downstream_blockers(fee, source, identity, db)
    if reasons:
        raise HTTPException(status_code=409, detail=f"该费用{'、'.join(reasons)}，不能移到其他案子")
    moved_at = datetime.now().isoformat(timespec="seconds")
    if str(data.get("converted_case_id") or "") == str(source.id):
        data["converted_case_id"] = target.id
    if _text(data.get("converted_case_no")) == source.serial_no:
        data["converted_case_no"] = target.serial_no
    # 合同字段保留原值（用户确认）；只改案件关联的 id 与案号两套字段。
    fee.data = {**data, "case_id": target.id, "case_record_id": target.id, "case_no": target.serial_no,
                "moved_from_case_id": source.id, "moved_from_case_no": source.serial_no,
                "moved_at": moved_at, "moved_by": identity["username"]}
    comment = f"费用 {fee.serial_no}（{fee.title}）由 {source.serial_no} 移到 {target.serial_no}"
    for record_id in (fee.id, source.id, target.id):
        record = fee if record_id == fee.id else source if record_id == source.id else target
        db.add(WorkflowEvent(record_id=record_id, action="案件费用移到其他案件", from_status=record.status,
                             to_status=record.status, operator=identity["username"], comment=comment))
    await db.commit()
    await db.refresh(fee)
    return fee
