"""案件费用票据的真实来源投影与专用附件操作。"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import (BusinessRecord, FileAttachment, FinanceTransaction, User, WorkflowEvent,
                        LegacyCaseAttachmentRelation, InvestigationEvidenceFile,
                        IprCaseAssistedFee, IprCaseFileCustomImportCandidate, LegacyFinanceFile)
from app.security import current_identity
from app.core.cases import _case_action_granted
from app.core.documents import _word_editor_now, _word_editor_utc
from app.core.finance import _invoice_linked_fee_ids
from app.core.investigation_access import _actual_identity
from app.core.invoice_permissions import invoice_permissions
from app.core.json_relation_query import json_scalar_overlap
from app.core.permissions import (_configured_user_job_role_name, _job_role_for_name,
                                  _ensure_case_read_module, _ensure_record_visible, _permission_payload_for_identity)
from app.areas.legal.case_fee_file_deletions import fee_file_was_deleted

router = APIRouter()


def _id(value) -> int:
    return int(value) if str(value or "").isdigit() else 0


def _day(value) -> str:
    return str(value or "")[:10]


async def case_fee_file_rows(fees: list[BusinessRecord], db: AsyncSession) -> dict[int, list[dict]]:
    """按费用集合读取附件，不把付款凭证重新解释成真实发票。"""
    result = {fee.id: [] for fee in fees}
    if not fees:
        return result
    fee_map = {fee.id: fee for fee in fees}
    direct_records: dict[int, set[int]] = {}
    for fee in fees:
        for key in ("invoice_record_id", "writeoff_voucher_record_id"):
            record_id = _id((fee.data or {}).get(key))
            if record_id:
                direct_records.setdefault(record_id, set()).add(fee.id)
    related = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module.in_(["invoice", "finance_fee_inform"]),
        or_(BusinessRecord.id.in_(direct_records), json_scalar_overlap(BusinessRecord.data, fee_map)),
    ))).all()
    parents = {}
    parent_fees = {}
    for record in related:
        data = record.data or {}
        linked = (_invoice_linked_fee_ids(data) | direct_records.get(record.id, set())) if record.module == "invoice" else {_id(data.get("source_fee_id"))}
        linked &= fee_map.keys()
        if linked:
            parents[record.id] = record
            parent_fees[record.id] = linked
    transactions = {item.id: item for item in (await db.scalars(select(FinanceTransaction).where(
        FinanceTransaction.finance_record_id.in_(fee_map),
    ))).all()}
    attachments = (await db.scalars(select(FileAttachment).where(or_(
        FileAttachment.record_id.in_([*fee_map, *parents]),
        FileAttachment.finance_transaction_id.in_(transactions),
    )).order_by(FileAttachment.id))).all()
    for attachment in attachments:
        parent = parents.get(attachment.record_id)
        transaction = transactions.get(attachment.finance_transaction_id)
        targets = set()
        kind, source, bill_no, bill_date = "receipt", "案件票据", "", _day(attachment.document_date)
        invoice_id = attachment.invoice_record_id
        if transaction and attachment.record_id in (None, transaction.finance_record_id):
            targets = {transaction.finance_record_id}
            kind, source = "payment", "缴费凭证"
            bill_no, bill_date = transaction.voucher_no, _day(transaction.transaction_date)
        elif attachment.record_id in fee_map and attachment.category in {"案件票据文件", "案件发票文件"}:
            targets = {attachment.record_id}
            if attachment.category == "案件发票文件":
                kind, source = "invoice", "发票文件"
                invoice = parents.get(attachment.invoice_record_id)
                if invoice and invoice.module == "invoice":
                    invoice_data = invoice.data or {}
                    bill_no = invoice_data.get("invoice_no") or ""
                    bill_date = _day(invoice_data.get("invoice_date") or bill_date)
                    if invoice_data.get("purpose") == "付款凭证":
                        kind, source, invoice_id = "payment", "缴费凭证", None
                        bill_no = invoice_data.get("writeoff_voucher_no") or bill_no
                        bill_date = _day(invoice_data.get("paid_date") or invoice_data.get("payment_date") or bill_date)
        elif parent and parent.module == "invoice" and attachment.category in {"付款凭证", "案件发票文件"}:
            targets = parent_fees[parent.id]
            payment = (parent.data or {}).get("purpose") == "付款凭证" or attachment.category == "付款凭证"
            kind, source = ("payment", "缴费凭证") if payment else ("invoice", "发票文件")
            invoice_id = None if payment else parent.id
            data = parent.data or {}
            bill_no = (data.get("writeoff_voucher_no") or data.get("invoice_no") or "") if payment else (data.get("invoice_no") or "")
            bill_date = _day(data.get("paid_date") or data.get("payment_date") or data.get("invoice_date")) if payment else _day(data.get("invoice_date"))
        elif parent and parent.module == "finance_fee_inform" and _id((parent.data or {}).get("receipt_attachment_id")) == attachment.id:
            targets = parent_fees[parent.id]
            source = "费用通知票据"
            bill_no, bill_date = (parent.data or {}).get("bill_no") or "", _day((parent.data or {}).get("bill_date"))
        for fee_id in sorted(targets):
            fee_data = fee_map[fee_id].data or {}
            legacy_key = attachment.remark.removeprefix("原始发票文件 ").strip() if attachment.remark.startswith("原始发票文件 ") else ""
            if fee_file_was_deleted(fee_data, attachment_id=attachment.id, legacy_file_key=legacy_key):
                continue
            metadata = next((item for item in (fee_data.get("receipt_files") or []) if isinstance(item, dict) and _id(item.get("attachment_id")) == attachment.id), {})
            result[fee_id].append({
                "attachment_id": attachment.id, "kind": kind, "source": source,
                "bill_no": str(metadata.get("bill_no") or bill_no or ""),
                "bill_date": _day(metadata.get("bill_date") or bill_date),
                "original_name": attachment.original_name, "remark": attachment.remark,
                "invoice_record_id": invoice_id,
            })
    return result


async def _fee_context(case_id: int, fee_id: int, identity: dict, db: AsyncSession, *, lock=False):
    actual = await _actual_identity(identity, db)
    case = await _ensure_case_read_module(case_id, actual, db)
    query = select(BusinessRecord).where(BusinessRecord.id == fee_id, BusinessRecord.module == "finance", BusinessRecord.status != "已删除")
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    fee = await db.scalar(query)
    if not fee:
        raise HTTPException(404, "案件费用不存在")
    data = fee.data or {}
    ids = {_id(data.get(key)) for key in ("case_id", "case_record_id", "converted_case_id")} - {0}
    numbers = {str(data.get(key) or "") for key in ("case_no", "converted_case_no")} - {""}
    if (ids and case.id not in ids) or (not ids and case.serial_no not in numbers):
        raise HTTPException(404, "费用不属于当前案件")
    return actual, fee


async def _can_delete(fee: BusinessRecord, actual: dict, db: AsyncSession) -> bool:
    if "admin" in actual.get("role_ids", []):
        return True
    permission = await _permission_payload_for_identity(actual, db)
    actions = set(permission.get("action_keys") or [])
    data = fee.data or {}
    platform = data.get("expense_scope") == "平台" or data.get("finance_scope") == "platform" or data.get("accounting_center") == "平台财务中心" or data.get("contract_body") == "平台"
    prefix = "platform-finance-" if platform else "finance-"
    if not any(key.startswith(prefix) for key in permission.get("menu_keys", [])):
        return False
    has_fee_delete = "*" in actions or "case.fee.delete" in actions
    user = await db.scalar(select(User).where(User.username == actual["username"], User.is_active.is_(True)))
    role_name = _configured_user_job_role_name(user) if user else ""
    job = await _job_role_for_name(role_name, db) if role_name else None
    # 沿用实际岗位中的财务处理授权，不能用姓名、部门或页面临时管理员身份授权。
    has_finance_job_action = bool(job and {"收付款", "付款录入", "开票录入", "财务审批"}.intersection(job.permissions or []))
    finance = await invoice_permissions({key: value for key, value in actual.items() if key != "_invoice_permissions"}, db)
    if not has_fee_delete and not has_finance_job_action and not finance["platform" if platform else "firm"]["issue"]:
        return False
    try:
        await _ensure_record_visible(fee.id, actual, db)
    except HTTPException as error:
        if error.status_code not in (403, 404):
            raise
        return False
    return True


async def visible_case_fee_file_rows(fees: list[BusinessRecord], identity: dict, db: AsyncSession) -> dict[int, list[dict]]:
    actual = await _actual_identity(identity, db)
    if await _case_action_granted(actual, db, "case.fee.receipt.view"):
        visible = fees
    else:
        visible = [fee for fee in fees if await _can_delete(fee, actual, db)]
    return await case_fee_file_rows(visible, db)


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/fees/{{fee_id}}/files")
async def list_case_fee_files(case_id: int, fee_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    actual, fee = await _fee_context(case_id, fee_id, identity, db)
    can_delete = await _can_delete(fee, actual, db)
    if not can_delete and not await _case_action_granted(actual, db, "case.fee.receipt.view"):
        raise HTTPException(403, "当前账号没有查看案件费用票据的权限")
    rows = (await case_fee_file_rows([fee], db))[fee.id]
    return {"items": rows, "can_delete": can_delete}


def _references_attachment(data: dict, attachment_id: int) -> bool:
    return (_id(data.get("receipt_attachment_id")) == attachment_id
            or attachment_id in {_id(value) for value in (data.get("receipt_attachment_history_ids") or [])}
            or any(isinstance(item, dict) and _id(item.get("attachment_id")) == attachment_id for item in (data.get("receipt_files") or [])))


@router.delete(f"{settings.api_prefix}/cases/{{case_id}}/fees/{{fee_id}}/files/{{attachment_id}}")
async def delete_case_fee_file(case_id: int, fee_id: int, attachment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    actual, fee = await _fee_context(case_id, fee_id, identity, db, lock=True)
    if not await _can_delete(fee, actual, db):
        raise HTTPException(403, "当前账号没有该财务范围的案件费用删除权限")
    attachment = await db.scalar(select(FileAttachment).where(FileAttachment.id == attachment_id).with_for_update().execution_options(populate_existing=True))
    if not attachment:
        raise HTTPException(404, "票据附件不存在")
    rows = (await case_fee_file_rows([fee], db))[fee.id]
    if not any(row["attachment_id"] == attachment_id for row in rows):
        raise HTTPException(404, "票据附件不属于当前案件费用")
    expires = _word_editor_utc(attachment.word_editor_lock_expires_at)
    if attachment.is_locked or (attachment.word_editor_lock_token and expires and expires > _word_editor_now()):
        raise HTTPException(409, "附件已锁定或正在编辑，请结束编辑后重试")
    for model, field in ((LegacyCaseAttachmentRelation, LegacyCaseAttachmentRelation.attachment_id),
                         (InvestigationEvidenceFile, InvestigationEvidenceFile.attachment_id),
                         (IprCaseAssistedFee, IprCaseAssistedFee.receipt_attachment_id),
                         (IprCaseFileCustomImportCandidate, IprCaseFileCustomImportCandidate.attachment_id)):
        if await db.scalar(select(model.id).where(field == attachment_id).limit(1)):
            raise HTTPException(409, "该附件仍有关联业务材料引用，不能从费用入口删除")
    owner = await db.scalar(select(BusinessRecord).where(BusinessRecord.id == attachment.record_id).with_for_update().execution_options(populate_existing=True)) if attachment.record_id else fee
    if owner and owner.module == "invoice":
        other_fees = _invoice_linked_fee_ids(owner.data or {}) - {fee.id}
        references = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "finance", BusinessRecord.id != fee.id, or_(
            json_scalar_overlap(BusinessRecord.data["invoice_record_id"], [owner.id]),
            json_scalar_overlap(BusinessRecord.data["writeoff_voucher_record_id"], [owner.id]),
        )))).all()
        other_fees.update(item.id for item in references if any(_id((item.data or {}).get(key)) == owner.id for key in ("invoice_record_id", "writeoff_voucher_record_id")))
        if other_fees:
            raise HTTPException(409, "该票据同时关联其他费用，不能从单笔费用删除共享附件")
    references = (await db.scalars(select(BusinessRecord).where(
        or_(json_scalar_overlap(BusinessRecord.data["receipt_files"], [attachment_id]),
            json_scalar_overlap(BusinessRecord.data["receipt_attachment_id"], [attachment_id]),
            json_scalar_overlap(BusinessRecord.data["receipt_attachment_history_ids"], [attachment_id])),
    ).order_by(BusinessRecord.id).with_for_update().execution_options(populate_existing=True))).all()
    related = [item for item in references if _references_attachment(item.data or {}, attachment_id)]
    if any(item.id not in {fee.id, owner.id if owner else None} for item in related):
        raise HTTPException(409, "该附件仍被其他业务引用，不能删除")
    for item in related:
        data = dict(item.data or {})
        if isinstance(data.get("receipt_files"), list):
            data["receipt_files"] = [value for value in data["receipt_files"] if not isinstance(value, dict) or _id(value.get("attachment_id")) != attachment_id]
        if _id(data.get("receipt_attachment_id")) == attachment_id:
            data["receipt_attachment_id"] = None
        if isinstance(data.get("receipt_attachment_history_ids"), list):
            data["receipt_attachment_history_ids"] = [value for value in data["receipt_attachment_history_ids"] if _id(value) != attachment_id]
        item.data = data
    legacy_key = ""
    if attachment.remark.startswith("原始发票文件 "):
        legacy_key = attachment.remark.removeprefix("原始发票文件 ").strip()
        if not await db.scalar(select(LegacyFinanceFile.id).where(LegacyFinanceFile.legacy_key == legacy_key)):
            raise HTTPException(409, "原始发票文件账本关联不完整，不能删除")
    deleted = (fee.data or {}).get("deleted_case_fee_files", [])
    if not isinstance(deleted, list):
        raise HTTPException(409, "费用附件删除记录格式异常，不能删除")
    fee.data = {**(fee.data or {}), "deleted_case_fee_files": [*deleted, {
        "attachment_id": attachment.id, "stored_name": attachment.stored_name,
        "legacy_file_key": legacy_key, "deleted_by": actual["username"],
        "deleted_at": datetime.now(timezone.utc).isoformat(),
    }]}
    audit_ids = {fee.id, owner.id if owner else fee.id}
    for record_id in sorted(audit_ids):
        db.add(WorkflowEvent(record_id=record_id, action="删除费用票据附件", operator=actual["username"],
            comment=f"附件ID：{attachment.id}；文件：{attachment.original_name}；仅删除业务附件及关联，保留存储原件"))
    # 不调用存储删除；同路径附件和历史 OSS 原件保留，业务元数据与审计原子提交。
    try:
        await db.delete(attachment)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return {"deleted": attachment_id}
