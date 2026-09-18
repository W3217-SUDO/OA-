"""案件合并的关系迁移；保留主案字段和来源快照。"""
from copy import deepcopy
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import or_, select
from app.models import BusinessRecord, CaseAssistedFee, CaseEvent, ContractObject, FileAttachment, HearingSchedule, IncomingPayment, WorkflowEvent
from app.core.case_relations import case_clues


async def merge_case_relations(source, target, db):
    snapshots = list((target.data or {}).get("merged_sources") or [])
    if any(item["id"] == source.id for item in snapshots):
        return
    snapshots.append({"id": source.id, "serial_no": source.serial_no, "title": source.title,
                      "customer": source.customer, "status": source.status, "owner": source.owner,
                      "description": source.description, "data": deepcopy(source.data or {}),
                      "merged_at": datetime.now().isoformat(timespec="seconds")})
    clues = {item.id: item for item in [*await case_clues(target, db), *await case_clues(source, db)]}
    target.data = {**(target.data or {}), "merged_sources": snapshots,
                   "investigation_clue_ids": list(clues),
                   "investigation_clue_nos": [item.serial_no for item in clues.values()]}
    for clue in clues.values():
        clue.data = {**(clue.data or {}), "case_id": target.id, "case_no": target.serial_no,
                     "converted_case_id": target.id, "converted_case_no": target.serial_no}
    rows = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module.in_(["task", "case_reminder", "case_log", "refund", "invoice", "contract_payment", "finance_settlement", "finance_archive_settlement", "finance_package"]),
    ))).all()
    for row in rows:
        data = dict(row.data or {})
        linked = any(str(data.get(key) or "") == str(source.id) for key in ("case_id", "case_record_id"))
        linked = linked or data.get("case_no") == source.serial_no or source.id in (data.get("case_ids") or []) or source.serial_no in (data.get("case_nos") or [])
        if not linked:
            continue
        for key in ("case_id", "case_record_id"):
            if str(data.get(key) or "") == str(source.id):
                data[key] = target.id
        if data.get("case_no") == source.serial_no:
            data.update(case_no=target.serial_no, case_id=target.id, case_record_id=target.id)
        if isinstance(data.get("case_ids"), list):
            data["case_ids"] = list(dict.fromkeys(target.id if value == source.id else value for value in data["case_ids"]))
        if isinstance(data.get("case_nos"), list):
            data["case_nos"] = list(dict.fromkeys(target.serial_no if value == source.serial_no else value for value in data["case_nos"]))
        data.update(merged_from_case_id=source.id, merged_from_case_no=source.serial_no)
        row.data = data
    receipts = (await db.scalars(select(IncomingPayment))).all()
    for receipt in receipts:
        changed = False
        allocations = deepcopy(receipt.allocations or [])
        for allocation in allocations:
            if allocation.get("case_no") == source.serial_no or allocation.get("case_id") == source.id:
                allocation.update(case_no=target.serial_no, case_id=target.id)
                changed = True
        if receipt.case_no == source.serial_no:
            receipt.case_no = target.serial_no
        if changed:
            receipt.allocations = allocations
    for model in (CaseEvent, HearingSchedule, ContractObject):
        for item in (await db.scalars(select(model).where(model.case_record_id == source.id))).all():
            item.case_record_id = target.id
    events = (await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == source.id))).all()
    for event in events:
        db.add(WorkflowEvent(record_id=target.id, action=event.action, from_status=event.from_status,
                             to_status=event.to_status, operator=event.operator, created_at=event.created_at,
                             comment=f"来源案件 {source.serial_no}：{event.comment}"))


async def finance_rows_for_merge(source, db):
    """历史导入 ID 可能属于其他模块，使用明确的案件号关联查找。"""
    return list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance",
        or_(BusinessRecord.data["case_no"].as_string() == source.serial_no,
            BusinessRecord.data["case_id"].as_integer() == source.id,
            BusinessRecord.data["case_record_id"].as_integer() == source.id),
    ))).all())


async def move_case_finance_files(source, target, identity, db):
    fees = await finance_rows_for_merge(source, db)
    for fee in fees:
        data = fee.data or {}
        for key in ("case_id", "case_record_id"):
            linked = await db.get(BusinessRecord, int(data[key])) if data.get(key) else None
            if linked and linked.module == "case" and linked.id != source.id:
                raise HTTPException(409, "费用案件ID与案号指向不同有效案件，不能合并")
        fee.data = {**(fee.data or {}), "case_id": target.id, "case_record_id": target.id,
                    "case_no": target.serial_no, "merged_from_case_id": source.id,
                    "merged_from_case_no": source.serial_no, "merged_at": datetime.now().isoformat(timespec="seconds")}
        db.add(WorkflowEvent(record_id=fee.id, action="案件合并迁移费用", from_status=fee.status,
            to_status=fee.status, operator=identity["username"], comment=f"{source.serial_no} → {target.serial_no}"))
    assisted = (await db.scalars(select(CaseAssistedFee).where(CaseAssistedFee.case_record_id == source.id))).all()
    for fee in assisted:
        fee.case_record_id = target.id
    files = (await db.scalars(select(FileAttachment).where(FileAttachment.record_id == source.id))).all()
    for file in files:
        file.record_id = target.id
        file.remark = f"{file.remark}｜案件合并迁移：{source.serial_no}→{target.serial_no}".strip("｜")
    return len(fees), len(assisted), len(files)
