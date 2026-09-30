"""空合同删除前核对真实业务依赖，仅清理其从属且从未提交的用印草稿。"""
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import String, cast, delete, or_, select
from app.models import (BusinessRecord, ContractObject, FileAttachment, LegacyOfficialDocument,
                        LegacyOfficialDocumentAudit, LegacyOfficialDocumentFile, IncomingPayment, OfficialOutgoingDocument, WorkflowEvent)


def _links_contract(data, contract):
    if not isinstance(data, dict):
        return False
    if any(str(data.get(key) or "") == str(contract.id) for key in ("contract_id", "contract_record_id")):
        return True
    if str(data.get("contract_no") or "").strip() == contract.serial_no:
        return True
    if any(str(value) == str(contract.id) for key in ("contract_ids", "contract_record_ids") for value in (data.get(key) or [])):
        return True
    if contract.serial_no in (data.get("contract_nos") or []):
        return True
    return any(_links_contract(item, contract) for key in ("contract_allocations", "allocations", "lines", "items")
               for item in (data.get(key) or []) if isinstance(item, dict))


async def contract_dependent_drafts(contract, db):
    if await db.scalar(select(ContractObject.id).where(ContractObject.contract_record_id == contract.id).limit(1)):
        raise HTTPException(409, "合同已关联案件或费用对象，不能删除")
    if await db.scalar(select(OfficialOutgoingDocument.id).where(
        OfficialOutgoingDocument.source_type == "contract", OfficialOutgoingDocument.source_record_id == contract.id,
    ).limit(1)):
        raise HTTPException(409, "合同已关联正式发文，不能删除")
    receipts = (await db.scalars(select(IncomingPayment).where(or_(
        cast(IncomingPayment.allocations, String).contains(contract.serial_no),
        cast(IncomingPayment.allocations, String).contains(str(contract.id)),
    )))).all()
    if any(_links_contract({"allocations": item.allocations}, contract) for item in receipts):
        raise HTTPException(409, "合同已关联到账分配，不能删除")
    rows = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id != contract.id,
        or_(cast(BusinessRecord.data, String).contains(contract.serial_no),
            cast(BusinessRecord.data, String).contains(str(contract.id))),
    ))).all())
    data = contract.data or {}
    seal_ids = {str(value) for value in (data.get("seal_application_ids") or [])}
    seal_ids.add(str(data.get("seal_application_id") or ""))
    drafts = []
    for row in rows:
        if not _links_contract(row.data or {}, contract):
            continue
        detail = row.data or {}
        disposable = (row.module == "seal" and row.status == "草稿" and data.get("sync_seal")
                      and str(row.id) in seal_ids and detail.get("use_type") == "合同用印"
                      and not any(detail.get(key) for key in ("case_record_id", "case_no", "submitted_at", "stamped_at",
                                                             "stamp_attachment_id", "legacy_official_document_audit_round")))
        if disposable:
            events = list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == row.id))).all())
            disposable = bool(events) and all(event.action == "创建合同用印申请" and event.to_status == "草稿" for event in events)
        if disposable:
            legacy = await db.scalar(select(LegacyOfficialDocument).where(LegacyOfficialDocument.OfficialDocumentNo == row.serial_no))
            if legacy:
                disposable = not (legacy.PrintStatus or legacy.AuditStatus or await db.scalar(
                    select(LegacyOfficialDocumentAudit.AuditId).where(
                        LegacyOfficialDocumentAudit.OfficialDocumentId == legacy.OfficialDocumentId).limit(1)))
        if not disposable:
            raise HTTPException(409, f"合同已关联业务 {row.serial_no}，不能删除")
        drafts.append(row)
    return drafts


async def delete_dependent_draft(draft, identity, db):
    # 保留兼容投影的失效标识，避免物理删除新记录后旧查询仍将其列为有效用印。
    legacy = await db.scalar(select(LegacyOfficialDocument).where(LegacyOfficialDocument.OfficialDocumentNo == draft.serial_no))
    if legacy:
        legacy.IsActived = "N"
        legacy.ChangeUser = identity["username"][:20]
        legacy.ChangeTime = datetime.now()
        files = (await db.scalars(select(LegacyOfficialDocumentFile).where(
            LegacyOfficialDocumentFile.OfficialDocumentGuid == legacy.OfficialDocumentGuid))).all()
        for item in files:
            item.IsActived = "N"
            item.ChangeUser = identity["username"][:20]
            item.ChangeTime = datetime.now()
    files = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id == draft.id))).all())
    for item in files:
        await db.delete(item)
    await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == draft.id))
    await db.delete(draft)
    return files
