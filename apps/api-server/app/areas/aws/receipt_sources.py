"""按上传来源列出官文收文与案件内收文。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import current_identity, get_db, settings
from app.core.permissions import _permission_payload_for_identity, _require_record_module_menu
from app.core.query_batches import _scalars_in_batches
from app.core.storage import _attachment_dict
from app.core.system import _record_dict
from app.models import BusinessRecord, FileAttachment


router = APIRouter()

RECEIPT_KEYWORDS = ("缴费单", "判决书", "通知书", "传票", "告知书")
RECEIPT_MENU = {
    "official": "documents-official",
    "mine": "documents-my",
    "company": "documents-company",
}


def _is_actual_admin(identity: dict) -> bool:
    roles = identity.get("_actual_role_ids") or identity.get("role_ids") or [identity.get("role")]
    return "admin" in roles


async def is_official_receipt(record: BusinessRecord, db: AsyncSession) -> bool:
    if record.module != "document" or (record.data or {}).get("direction") != "收文":
        return False
    attachment_id = (record.data or {}).get("attachment_id")
    if not str(attachment_id or "").isdigit():
        return False
    attachment = await db.get(FileAttachment, int(attachment_id))
    if not attachment or attachment.category != "官方收文" or not attachment.record_id:
        return False
    case = await db.get(BusinessRecord, attachment.record_id)
    if not case or case.module != "case":
        return False
    return True


async def _require_receipt_menu(scope: str, identity: dict, db: AsyncSession) -> None:
    await _require_record_module_menu("document", identity, db, action="查看")
    if _is_actual_admin(identity):
        return
    permission = await _permission_payload_for_identity(identity, db)
    if RECEIPT_MENU[scope] not in set(permission.get("menu_keys") or []):
        raise HTTPException(status_code=403, detail="当前账号没有该收文窗口的查看权限")


async def can_read_receipt_attachment(attachment: FileAttachment, identity: dict, db: AsyncSession) -> bool:
    if not attachment.record_id:
        return False
    if _is_actual_admin(identity):
        return True
    permission = await _permission_payload_for_identity(identity, db)
    keys = set(permission.get("menu_keys") or [])
    if attachment.category == "官方收文":
        documents = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "document"))).all()
        linked = next((record for record in documents if
            (record.data or {}).get("direction") == "收文"
            and str((record.data or {}).get("attachment_id") or "") == str(attachment.id)
        ), None)
        if linked and await is_official_receipt(linked, db):
            return bool(keys & {"documents-official", "documents-company"})
    if not any(keyword in attachment.original_name for keyword in RECEIPT_KEYWORDS):
        return False
    if "documents-company" not in keys and not ("documents-my" in keys and attachment.uploader == identity["username"]):
        return False
    record = await db.get(BusinessRecord, attachment.record_id)
    return bool(record and record.module == "case")


def _case_attachment_row(attachment: FileAttachment, case: BusinessRecord) -> dict:
    case_data = case.data or {}
    created_at = attachment.created_at.isoformat() if attachment.created_at else ""
    return {
        "id": -attachment.id,
        "serial_no": case.serial_no,
        "title": attachment.original_name,
        "customer": case.customer,
        "status": "已签收",
        "owner": attachment.uploader,
        "description": attachment.remark,
        "data": {
            "receipt_source": "case_attachment",
            "attachment_id": attachment.id,
            "case_id": case.id,
            "case_no": case.serial_no,
            "plaintiff": case_data.get("plaintiff") or case.customer,
            "defendant": case_data.get("opponent") or "",
            "court_no": case_data.get("court_case_no") or case_data.get("first_court_case_no") or "",
            "court_name": case_data.get("court") or case_data.get("first_court_name") or "",
            "document_date": created_at[:10],
            "uploaded_at": created_at[:10],
            "uploader": attachment.uploader,
            "import_status": "已导入",
            "business_process_status": "未处理",
            "hearing_lawyer": case_data.get("hearing_lawyer") or "",
            "assistant": case_data.get("assistant") or "",
            "case_manager": case_data.get("case_manager") or "",
            "handling_lawyer": case_data.get("handling_lawyer") or "",
        },
    }


@router.get(f"{settings.api_prefix}/documents/receipts")
async def list_receipts(
    scope: str = Query(..., pattern="^(official|mine|company)$"),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    await _require_receipt_menu(scope, identity, db)
    official_records = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "document"))).all()
    eligible_records = [
        record for record in official_records
        if (record.data or {}).get("direction") == "收文"
        and str((record.data or {}).get("attachment_id") or "").isdigit()
        and int((record.data or {}).get("attachment_id") or 0) > 0
    ]
    official_candidates = {
        int((record.data or {}).get("attachment_id")): record
        for record in eligible_records
    }
    official_attachments = {
        item.id: item for item in await _scalars_in_batches(
            db, official_candidates,
            lambda batch: select(FileAttachment).where(FileAttachment.id.in_(batch)),
        )
    }
    official_case_ids = {attachment.record_id for attachment in official_attachments.values() if attachment.record_id}
    official_cases = {
        case.id: case for case in await _scalars_in_batches(
            db, official_case_ids,
            lambda batch: select(BusinessRecord).where(BusinessRecord.id.in_(batch), BusinessRecord.module == "case"),
        )
    }
    official_ids = {
        attachment_id for attachment_id, attachment in official_attachments.items()
        if attachment.category == "官方收文"
        and attachment.record_id in official_cases
    }
    rows: list[dict] = []
    files: dict[int, dict] = {}
    if scope in {"official", "company"}:
        for attachment_id in official_ids:
            record = official_candidates[attachment_id]
            attachment = official_attachments[attachment_id]
            row = _record_dict(record)
            row["data"] = {**row["data"], "receipt_source": "official_upload"}
            rows.append(row)
            files[attachment_id] = _attachment_dict(attachment)

    if scope in {"mine", "company"}:
        keyword_filter = or_(*(FileAttachment.original_name.contains(word) for word in RECEIPT_KEYWORDS))
        case_files = (await db.execute(
            select(FileAttachment, BusinessRecord)
            .join(BusinessRecord, FileAttachment.record_id == BusinessRecord.id)
            .where(BusinessRecord.module == "case", keyword_filter)
        )).all()
        for attachment, case in case_files:
            if attachment.id in official_ids:
                continue
            if scope == "mine" and attachment.uploader != identity["username"]:
                continue
            rows.append(_case_attachment_row(attachment, case))
            files[attachment.id] = _attachment_dict(attachment, case)

    rows.sort(key=lambda row: (str((row.get("data") or {}).get("uploaded_at") or ""), abs(row["id"])), reverse=True)
    return {"items": rows, "attachments": list(files.values()), "total": len(rows)}
