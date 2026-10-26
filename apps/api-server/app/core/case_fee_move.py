"""案件费用“移到其他案子”（10.22 第8行，10.26 第11行调整）。

10.26 第11行用户要求只保留两条限制：
- 目标案件必须与当前案件属于同一客户（客户记录 ID → 客户编号 → 客户名称，取两案都有的最精确口径）；
- 一次只迁移一条费用（接口按单条费用操作）。
除此之外不再设其他限制：已有申请付款/开票/回款/退费等后续单据、案件归档或合并状态、费用提交人、
目标案件是否在当前账号可见范围内，都不再拦截。后续单据按费用 ID 关联，随费用一起出现在目标案件。
合同编号保留原值；原案、目标案、费用各记一条系统日志。
"""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select

from app.models import BusinessRecord, WorkflowEvent

MOVABLE_FEE_SCOPES = {"律所", "平台"}


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


async def move_case_fee(fee_id: int, target_case_no: str, identity: dict, db) -> BusinessRecord:
    from app.core.cases import _case_action_granted
    from app.core.permissions import _ensure_record_module

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
    if not (await _case_action_granted(identity, db, "case.fee.move")
            or await _case_action_granted(identity, db, "case.fee.update")):
        raise HTTPException(status_code=403, detail="当前账号没有“移到其他案件”权限")
    target_no = _text(target_case_no)
    if target_no == source.serial_no:
        raise HTTPException(status_code=422, detail="目标案件不能与当前案件相同")
    target = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == "case", BusinessRecord.serial_no == target_no,
        BusinessRecord.status != "已删除",
    ))
    if not target:
        raise HTTPException(status_code=404, detail="未找到目标案件，请核对案件编号")
    for record in sorted((source, target, fee), key=lambda item: item.id):
        await db.refresh(record, with_for_update=True)
    if not same_customer(source, target):
        raise HTTPException(status_code=422, detail="目标案件与当前案件不属于同一客户，不允许迁移")
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
