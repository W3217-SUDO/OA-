"""Dedicated IPR fee, bill, law-firm ownership and triple-rule APIs.

This router keeps fee, bill and rule state in dedicated IPR tables rather than
generic finance records or JSON fields. Historical bill files are retained as
metadata-only records and have no download route until independently recovered.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_db
from .models import (
    BusinessRecord,
    FileAttachment,
    IprCaseLawFirm,
    IprCaseTypeAssignment,
    IprCaseTypeFileFeeTypeRule,
    IprFeeAuditLog,
    IprFeeBill,
    IprFeeBillAttachmentMetadata,
    IprFeeHeader,
    IprFeeItem,
    LawFirm,
    SystemParameter,
    User,
    WorkflowEvent,
)
from .security import current_identity


router = APIRouter(prefix="/ipr", tags=["ipr-fee-file-parity"])
MANAGER_ROLES = {"admin", "manager"}
MUTABLE_CASE_STATUS = "在办"
UPLOAD_ROOT = (
    Path(settings.upload_root).expanduser().resolve()
    if settings.upload_root.strip()
    else (Path(__file__).resolve().parents[1] / "uploads").resolve()
)
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
ALLOWED_BILL_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx", ".xls", ".xlsx"}


class TripleRuleInput(BaseModel):
    case_type_id: int
    file_type_id: int
    fee_type_id: int


class CaseTypeAssignmentInput(BaseModel):
    case_type_id: int


class FeeHeaderInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    law_firm_id: int


class FeeItemInput(BaseModel):
    rule_id: int
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class FeeConfirmationInput(BaseModel):
    payment_bank: str = Field(min_length=1, max_length=128)
    actual_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    gained_date: date


class BillAttachmentMetadataInput(BaseModel):
    original_name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(default="application/octet-stream", max_length=128)
    size: int = Field(default=0, ge=0)
    source_locator: str = Field(default="", max_length=512)


class BillConfirmationInput(BaseModel):
    bill_no: str = Field(min_length=1, max_length=128)
    bill_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    bill_date: date
    attachment: BillAttachmentMetadataInput


async def _case(case_id: int, identity: dict, db: AsyncSession, *, write: bool) -> BusinessRecord:
    record = await db.get(BusinessRecord, case_id)
    if not record or record.module != "ipr_case":
        raise HTTPException(status_code=404, detail="知识产权案件不存在")
    if identity.get("role") not in MANAGER_ROLES and record.owner != identity["username"]:
        raise HTTPException(status_code=403, detail="无权访问该知识产权案件费用")
    if write and record.status != MUTABLE_CASE_STATUS:
        raise HTTPException(status_code=409, detail="仅在办知识产权案件可以变更费用")
    return record


async def _manager(identity: dict) -> None:
    if identity.get("role") not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="仅管理员或管理人员可以执行此费用操作")


async def _parameter(parameter_id: int, category: str, db: AsyncSession, label: str) -> SystemParameter:
    row = await db.get(SystemParameter, parameter_id)
    if not row or row.category != category or not row.is_active:
        raise HTTPException(status_code=422, detail=f"{label}必须是启用的 {category} 参数")
    return row


async def _audit(
    record: BusinessRecord, identity: dict, db: AsyncSession, action: str,
    *, header_id: int | None = None, item_id: int | None = None, detail: dict | None = None,
) -> None:
    detail = detail or {}
    db.add(IprFeeAuditLog(
        case_record_id=record.id, header_id=header_id, item_id=item_id,
        action=action, operator=identity["username"], detail=detail,
    ))
    db.add(WorkflowEvent(
        record_id=record.id, action=action, from_status=record.status,
        to_status=record.status, operator=identity["username"],
        comment=f"IPR费用#{header_id or '-'} 明细#{item_id or '-'}",
    ))


async def _header(case_id: int, header_id: int, identity: dict, db: AsyncSession, *, write: bool) -> tuple[BusinessRecord, IprFeeHeader]:
    record = await _case(case_id, identity, db, write=write)
    header = await db.scalar(select(IprFeeHeader).where(IprFeeHeader.id == header_id, IprFeeHeader.case_record_id == record.id))
    if not header:
        raise HTTPException(status_code=404, detail="知识产权费用头不存在")
    return record, header


async def _assigned_case_type_id(case_id: int, db: AsyncSession) -> int | None:
    assignment = await db.scalar(select(IprCaseTypeAssignment).where(IprCaseTypeAssignment.case_record_id == case_id))
    return assignment.case_type_id if assignment else None


async def _item(case_id: int, header_id: int, item_id: int, identity: dict, db: AsyncSession, *, write: bool) -> tuple[BusinessRecord, IprFeeHeader, IprFeeItem]:
    record, header = await _header(case_id, header_id, identity, db, write=write)
    item = await db.scalar(select(IprFeeItem).where(IprFeeItem.id == item_id, IprFeeItem.header_id == header.id))
    if not item:
        raise HTTPException(status_code=404, detail="知识产权费用明细不存在")
    return record, header, item


def _metadata_dict(metadata: IprFeeBillAttachmentMetadata | None) -> dict | None:
    if not metadata:
        return None
    return {
        "original_name": metadata.original_name,
        "content_type": metadata.content_type,
        "size": metadata.size,
        "recovery_state": metadata.recovery_state,
        "source_locator": metadata.source_locator,
        "downloadable": metadata.recovery_state == "available" and metadata.source_locator.startswith("attachment:"),
    }


async def _item_dict(item: IprFeeItem, db: AsyncSession) -> dict:
    bill = await db.scalar(select(IprFeeBill).where(IprFeeBill.fee_item_id == item.id))
    metadata = await db.scalar(select(IprFeeBillAttachmentMetadata).where(IprFeeBillAttachmentMetadata.bill_id == bill.id)) if bill else None
    usernames = {value for value in [item.created_by, item.confirmed_by, bill.confirmed_by if bill else ""] if value}
    users = list((await db.scalars(select(User).where(User.username.in_(usernames)))).all()) if usernames else []
    display_names = {row.username: row.display_name or row.username for row in users}
    return {
        "id": item.id, "header_id": item.header_id, "rule_id": item.rule_id,
        "amount": float(item.amount), "status": item.status, "payment_bank": item.payment_bank,
        "actual_amount": float(item.actual_amount) if item.actual_amount is not None else None,
        "gained_date": str(item.gained_date) if item.gained_date else None,
        "created_by": item.created_by,
        "created_by_display_name": display_names.get(item.created_by, item.created_by),
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "confirmed_by": item.confirmed_by,
        "confirmed_by_display_name": display_names.get(item.confirmed_by, item.confirmed_by),
        "confirmed_at": item.confirmed_at.isoformat() if item.confirmed_at else None,
        "bill": None if not bill else {
            "id": bill.id, "bill_no": bill.bill_no, "bill_amount": float(bill.bill_amount),
            "bill_date": str(bill.bill_date), "confirmed_by": bill.confirmed_by,
            "confirmed_by_display_name": display_names.get(bill.confirmed_by, bill.confirmed_by),
            "attachment": _metadata_dict(metadata),
        },
    }


async def _rule_dict(rule: IprCaseTypeFileFeeTypeRule, db: AsyncSession) -> dict:
    case_type = await db.get(SystemParameter, rule.case_type_id)
    file_type = await db.get(SystemParameter, rule.file_type_id)
    fee_type = await db.get(SystemParameter, rule.fee_type_id)
    return {
        "id": rule.id,
        "case_type_id": rule.case_type_id,
        "case_type_name": case_type.name if case_type else "",
        "file_type_id": rule.file_type_id,
        "file_type_name": file_type.name if file_type else "",
        "fee_type_id": rule.fee_type_id,
        "fee_type_name": fee_type.name if fee_type else "",
        "is_active": rule.is_active,
    }


@router.post("/fee-rules", status_code=status.HTTP_201_CREATED)
async def create_ipr_fee_rule(body: TripleRuleInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)) -> dict:
    await _manager(identity)
    await _parameter(body.case_type_id, "ipr_case_type", db, "案件类型")
    await _parameter(body.file_type_id, "ipr_case_file_type", db, "文件类型")
    await _parameter(body.fee_type_id, "ipr_fee_type", db, "费用类型")
    existing = await db.scalar(select(IprCaseTypeFileFeeTypeRule).where(
        IprCaseTypeFileFeeTypeRule.case_type_id == body.case_type_id,
        IprCaseTypeFileFeeTypeRule.file_type_id == body.file_type_id,
        IprCaseTypeFileFeeTypeRule.fee_type_id == body.fee_type_id,
    ))
    if existing:
        raise HTTPException(status_code=409, detail="知识产权案件类型-文件类型-费用类型规则已存在")
    row = IprCaseTypeFileFeeTypeRule(**body.model_dump(), created_by=identity["username"], updated_by=identity["username"])
    db.add(row); await db.flush()
    db.add(IprFeeAuditLog(
        action="创建知识产权三元规则", operator=identity["username"],
        detail={"rule_id": row.id, **body.model_dump()},
    ))
    await db.commit(); await db.refresh(row)
    return {"id": row.id, **body.model_dump(), "is_active": row.is_active}


@router.get("/fee-rules")
async def list_ipr_fee_rules(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)) -> dict:
    rows = list((await db.scalars(select(IprCaseTypeFileFeeTypeRule).order_by(IprCaseTypeFileFeeTypeRule.id))).all())
    return {"items": [await _rule_dict(row, db) for row in rows]}


@router.get("/cases/{case_id}/case-type")
async def get_ipr_case_type_assignment(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)) -> dict:
    record = await _case(case_id, identity, db, write=False)
    assignment = await db.scalar(select(IprCaseTypeAssignment).where(IprCaseTypeAssignment.case_record_id == record.id))
    case_type = await db.get(SystemParameter, assignment.case_type_id) if assignment else None
    return {
        "case_record_id": record.id,
        "case_type_id": assignment.case_type_id if assignment else None,
        "case_type_name": case_type.name if case_type else "",
        "assigned_by": assignment.assigned_by if assignment else "",
        "assigned_at": assignment.assigned_at.isoformat() if assignment else None,
    }


@router.put("/cases/{case_id}/case-type")
async def assign_ipr_case_type(case_id: int, body: CaseTypeAssignmentInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)) -> dict:
    await _manager(identity)
    record = await _case(case_id, identity, db, write=True)
    await _parameter(body.case_type_id, "ipr_case_type", db, "案件类型")
    assignment = await db.scalar(select(IprCaseTypeAssignment).where(IprCaseTypeAssignment.case_record_id == record.id))
    if assignment:
        assignment.case_type_id = body.case_type_id
        assignment.assigned_by = identity["username"]
        assignment.assigned_at = datetime.now()
        action = "更新知识产权案件类型"
    else:
        assignment = IprCaseTypeAssignment(case_record_id=record.id, case_type_id=body.case_type_id, assigned_by=identity["username"])
        db.add(assignment)
        action = "设置知识产权案件类型"
    await _audit(record, identity, db, action, detail={"case_type_id": body.case_type_id})
    await db.commit(); await db.refresh(assignment)
    return {"case_record_id": assignment.case_record_id, "case_type_id": assignment.case_type_id, "assigned_by": assignment.assigned_by, "assigned_at": assignment.assigned_at.isoformat()}


@router.post("/cases/{case_id}/fee-headers", status_code=status.HTTP_201_CREATED)
async def create_ipr_fee_header(case_id: int, body: FeeHeaderInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)) -> dict:
    record = await _case(case_id, identity, db, write=True)
    law_firm = await db.get(LawFirm, body.law_firm_id)
    linked = await db.scalar(select(IprCaseLawFirm.id).where(IprCaseLawFirm.case_record_id == record.id, IprCaseLawFirm.law_firm_id == body.law_firm_id))
    if not law_firm or not linked:
        raise HTTPException(status_code=422, detail="费用律所必须已关联至该知识产权案件")
    header = IprFeeHeader(case_record_id=record.id, law_firm_id=law_firm.id, title=body.title.strip(), created_by=identity["username"])
    db.add(header); await db.flush()
    await _audit(record, identity, db, "新建知识产权费用头", header_id=header.id, detail={"law_firm_id": law_firm.id, "title": header.title})
    await db.commit(); await db.refresh(header)
    return {"id": header.id, "case_record_id": header.case_record_id, "law_firm_id": header.law_firm_id, "title": header.title, "status": header.status}


@router.get("/cases/{case_id}/fee-headers")
async def list_ipr_fee_headers(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)) -> dict:
    record = await _case(case_id, identity, db, write=False)
    headers = list((await db.scalars(select(IprFeeHeader).where(IprFeeHeader.case_record_id == record.id).order_by(IprFeeHeader.id))).all())
    result = []
    for row in headers:
        law_firm = await db.get(LawFirm, row.law_firm_id)
        items = list((await db.scalars(select(IprFeeItem).where(IprFeeItem.header_id == row.id).order_by(IprFeeItem.id))).all())
        item_rows = []
        for item in items:
            payload = await _item_dict(item, db)
            rule = await db.get(IprCaseTypeFileFeeTypeRule, item.rule_id)
            payload["rule"] = await _rule_dict(rule, db) if rule else None
            item_rows.append(payload)
        result.append({
            "id": row.id,
            "law_firm_id": row.law_firm_id,
            "law_firm_code": law_firm.code if law_firm else "",
            "law_firm_name": law_firm.name if law_firm else "",
            "title": row.title,
            "status": row.status,
            "items": item_rows,
        })
    return {"items": result}


@router.post("/cases/{case_id}/fee-headers/{header_id}/items", status_code=status.HTTP_201_CREATED)
async def create_ipr_fee_item(case_id: int, header_id: int, body: FeeItemInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)) -> dict:
    record, header = await _header(case_id, header_id, identity, db, write=True)
    rule = await db.get(IprCaseTypeFileFeeTypeRule, body.rule_id)
    case_type_id = await _assigned_case_type_id(record.id, db)
    if not rule or not rule.is_active or case_type_id != rule.case_type_id:
        raise HTTPException(status_code=422, detail="费用明细必须匹配该案件的启用知识产权三元规则")
    item = IprFeeItem(header_id=header.id, rule_id=rule.id, amount=body.amount, created_by=identity["username"])
    db.add(item); await db.flush()
    await _audit(record, identity, db, "新建知识产权费用明细", header_id=header.id, item_id=item.id, detail={"rule_id": rule.id, "amount": str(item.amount)})
    await db.commit(); await db.refresh(item)
    return await _item_dict(item, db)


@router.post("/cases/{case_id}/fee-headers/{header_id}/items/{item_id}/confirm")
async def confirm_ipr_fee_item(case_id: int, header_id: int, item_id: int, body: FeeConfirmationInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)) -> dict:
    await _manager(identity)
    record, header, item = await _item(case_id, header_id, item_id, identity, db, write=True)
    if item.status != "待确认":
        raise HTTPException(status_code=409, detail="仅待确认知识产权费用明细可以确认")
    item.status = "已确认"; item.payment_bank = body.payment_bank.strip(); item.actual_amount = body.actual_amount
    item.gained_date = body.gained_date; item.confirmed_by = identity["username"]; item.confirmed_at = datetime.now()
    await _audit(record, identity, db, "确认知识产权费用", header_id=header.id, item_id=item.id, detail={"actual_amount": str(item.actual_amount), "gained_date": str(item.gained_date)})
    await db.commit(); await db.refresh(item)
    return await _item_dict(item, db)


@router.post("/cases/{case_id}/fee-headers/{header_id}/items/{item_id}/bill", status_code=status.HTTP_201_CREATED)
async def confirm_ipr_fee_bill(case_id: int, header_id: int, item_id: int, body: BillConfirmationInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)) -> dict:
    await _manager(identity)
    record, header, item = await _item(case_id, header_id, item_id, identity, db, write=True)
    if item.status != "已确认":
        raise HTTPException(status_code=409, detail="仅已确认知识产权费用明细可以确认票据")
    existing = await db.scalar(select(IprFeeBill.id).where(IprFeeBill.fee_item_id == item.id))
    if existing:
        raise HTTPException(status_code=409, detail="该知识产权费用明细已确认票据")
    bill = IprFeeBill(fee_item_id=item.id, bill_no=body.bill_no.strip(), bill_amount=body.bill_amount, bill_date=body.bill_date, confirmed_by=identity["username"])
    db.add(bill); await db.flush()
    metadata = IprFeeBillAttachmentMetadata(bill_id=bill.id, **body.attachment.model_dump(), recovery_state="unrecoverable")
    db.add(metadata); item.status = "已票据确认"
    await _audit(record, identity, db, "确认知识产权费用票据", header_id=header.id, item_id=item.id, detail={"bill_no": bill.bill_no, "attachment_recovery_state": metadata.recovery_state})
    await db.commit(); await db.refresh(item)
    return await _item_dict(item, db)


@router.post("/cases/{case_id}/fee-headers/{header_id}/items/{item_id}/bill/upload", status_code=status.HTTP_201_CREATED)
async def upload_ipr_fee_bill(
    case_id: int,
    header_id: int,
    item_id: int,
    bill_no: str = Form(...),
    bill_amount: Decimal = Form(...),
    bill_date: date = Form(...),
    file: UploadFile = File(...),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await _manager(identity)
    record, header, item = await _item(case_id, header_id, item_id, identity, db, write=True)
    if item.status != "已确认":
        raise HTTPException(status_code=409, detail="仅已确认知识产权费用明细可以上传票据")
    if await db.scalar(select(IprFeeBill.id).where(IprFeeBill.fee_item_id == item.id)):
        raise HTTPException(status_code=409, detail="该知识产权费用明细已确认票据")
    normalized_bill_no = bill_no.strip()
    if not normalized_bill_no or bill_amount <= 0:
        raise HTTPException(status_code=422, detail="票据编号和票据金额必须有效")
    original_name = Path(file.filename or "").name
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_BILL_SUFFIXES:
        raise HTTPException(status_code=422, detail="票据文件仅支持 PDF、图片和常用 Office 文档")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="票据文件不能为空")
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="票据文件不能超过 20MB")
    stored_name = f"ipr-fee-bill-{uuid4().hex}{suffix}"
    target = UPLOAD_ROOT / stored_name
    target.write_bytes(content)
    try:
        attachment = FileAttachment(
            record_id=record.id,
            category="知识产权费用票据",
            original_name=original_name,
            stored_name=stored_name,
            content_type=file.content_type or "application/octet-stream",
            size=len(content),
            path=str(target),
            uploader=identity["username"],
            remark=f"费用头#{header.id} 明细#{item.id} 票据",
            document_date=bill_date,
        )
        db.add(attachment)
        await db.flush()
        bill = IprFeeBill(
            fee_item_id=item.id,
            bill_no=normalized_bill_no,
            bill_amount=bill_amount,
            bill_date=bill_date,
            confirmed_by=identity["username"],
        )
        db.add(bill)
        await db.flush()
        db.add(IprFeeBillAttachmentMetadata(
            bill_id=bill.id,
            original_name=original_name,
            content_type=file.content_type or "application/octet-stream",
            size=len(content),
            source_locator=f"attachment:{attachment.id}",
            recovery_state="available",
        ))
        item.status = "已票据确认"
        await _audit(record, identity, db, "上传知识产权费用票据", header_id=header.id, item_id=item.id, detail={"bill_no": bill.bill_no, "attachment_id": attachment.id})
        await db.commit()
        await db.refresh(item)
    except Exception:
        await db.rollback()
        target.unlink(missing_ok=True)
        raise
    return await _item_dict(item, db)


@router.get("/cases/{case_id}/fee-headers/{header_id}/items/{item_id}/bill/attachment")
async def get_ipr_fee_bill_attachment(case_id: int, header_id: int, item_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)) -> dict:
    _, _, item = await _item(case_id, header_id, item_id, identity, db, write=False)
    bill = await db.scalar(select(IprFeeBill).where(IprFeeBill.fee_item_id == item.id))
    metadata = await db.scalar(select(IprFeeBillAttachmentMetadata).where(IprFeeBillAttachmentMetadata.bill_id == bill.id)) if bill else None
    if not metadata:
        raise HTTPException(status_code=404, detail="知识产权费用票据附件元数据不存在")
    if metadata.recovery_state != "available" or not metadata.source_locator.startswith("attachment:"):
        raise HTTPException(status_code=409, detail="该历史票据附件尚不可恢复，仅可查看隔离元数据")
    try:
        attachment_id = int(metadata.source_locator.split(":", 1)[1])
    except (TypeError, ValueError):
        raise HTTPException(status_code=409, detail="票据附件关联信息无效")
    attachment = await db.get(FileAttachment, attachment_id)
    if not attachment or attachment.record_id != case_id:
        raise HTTPException(status_code=404, detail="票据附件不存在")
    path = Path(attachment.path).resolve()
    if not path.is_file() or UPLOAD_ROOT not in path.parents:
        raise HTTPException(status_code=404, detail="票据附件文件不存在")
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.original_name)
