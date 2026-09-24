"""案件费用票据列表与批量上传。"""

from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import UPLOAD_ROOT
from app.core.cases import _case_action_granted
from app.core.dependencies import current_identity, get_db, settings
from app.core.finance import _fee_query_rows
from app.core.permissions import _permission_payload_for_identity, _record_scope_conditions, _require_case_action, _require_record_module_menu
from app.models import BusinessRecord, FileAttachment, WorkflowEvent


router = APIRouter()


def _actual_identity(identity: dict) -> dict:
    return {
        **identity,
        "role": identity.get("_actual_role") or identity["role"],
        "role_ids": identity.get("_actual_role_ids") or identity.get("role_ids") or [identity["role"]],
        "_page_menu_capability": False,
    }


async def _visible_receipt_fee_ids(identity: dict, db: AsyncSession) -> set[int]:
    await _require_record_module_menu("case", identity, db, action="查看")
    actual_identity = _actual_identity(identity)
    actual_roles = set(actual_identity["role_ids"])
    permission = await _permission_payload_for_identity(actual_identity, db)
    menu_keys = set(permission.get("menu_keys") or [])
    if "admin" not in actual_roles and "case-files-receipt" not in menu_keys:
        raise HTTPException(status_code=403, detail="当前账号没有案件票据文件菜单权限")
    case_scope = [] if "admin" in actual_roles or "case-company" in menu_keys else await _record_scope_conditions(actual_identity, db)
    cases = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case", *case_scope,
    ))).all()
    case_ids = {case.id for case in cases}
    case_nos = {case.serial_no for case in cases}
    if not case_ids:
        return set()
    fees = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "finance"))).all()
    return {
        fee.id for fee in fees
        if (fee.data or {}).get("case_id") in case_ids or (fee.data or {}).get("case_no") in case_nos
    }


def _matches(row: dict, key: str, value: str) -> bool:
    if not value.strip():
        return True
    data = row.get("data") or {}
    actual = data.get(key, "")
    if key == "status":
        actual = data.get("case_stage") or row.get("status", "")
    elif key == "fee_group":
        actual = data.get("base_fee_type") or data.get("fee_type", "")
    elif key == "receipt_status":
        actual = "已上传" if data.get("receipt_files") else "未上传"
    return value.strip().casefold() in str(actual or "").casefold()


@router.get(f"{settings.api_prefix}/finance/receipt-files/fees")
async def list_receipt_fees(
    serial_no: str = "", customer: str = "", contract_no: str = "",
    fee_group: str = "", case_type: str = "", status: str = "",
    fee_type: str = "", receipt_status: str = "", notary_no: str = "", package_no: str = "",
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    authorized_ids = await _visible_receipt_fee_ids(identity, db)
    rows = await _fee_query_rows(identity, db, scope="company", case_no=serial_no, customer=customer, notary_no=notary_no, scope_authorized_fee_ids=authorized_ids)
    filters = {
        "contract_no": contract_no, "fee_group": fee_group, "case_type": case_type,
        "status": status, "fee_type": fee_type, "receipt_status": receipt_status,
        "package_no": package_no,
    }
    rows = [row for row in rows if all(_matches(row, key, value) for key, value in filters.items())]
    for row in rows:
        data = row.get("data") or {}
        row["data"] = {**data, "receipt_status": "已上传" if data.get("receipt_files") else "未上传"}
    start = (page - 1) * page_size
    can_upload = await _case_action_granted(_actual_identity(identity), db, "case.fee.receipt.upload")
    return {"items": rows[start:start + page_size], "total": len(rows), "page": page, "page_size": page_size, "can_upload": can_upload}


@router.post(f"{settings.api_prefix}/finance/receipt-files/batch", status_code=status.HTTP_201_CREATED)
async def upload_receipt_files(
    fee_ids: str = Form(...), bill_no: str = Form(...), bill_date: date = Form(...),
    file: UploadFile = File(...), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    await _require_case_action(_actual_identity(identity), db, "case.fee.receipt.upload")
    try:
        selected_ids = list(dict.fromkeys(int(value.strip()) for value in fee_ids.split(",")))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="费用记录编号无效") from exc
    if not selected_ids or len(selected_ids) > 200 or any(value <= 0 for value in selected_ids):
        raise HTTPException(status_code=422, detail="请选择 1 至 200 条费用记录")
    if not bill_no.strip() or len(bill_no.strip()) > 100:
        raise HTTPException(status_code=422, detail="票据编号须为 1 至 100 个字符")
    filename = Path(file.filename or "").name
    if not filename:
        raise HTTPException(status_code=422, detail="票据文件名不能为空")
    suffix = Path(filename).suffix.lower()
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="票据文件不能为空")
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="票据文件不能超过 20MB")
    authorized_ids = await _visible_receipt_fee_ids(identity, db)
    visible_rows = await _fee_query_rows(identity, db, scope="company", ids=set(selected_ids), scope_authorized_fee_ids=authorized_ids)
    if {row["id"] for row in visible_rows} != set(selected_ids):
        raise HTTPException(status_code=403, detail="所选费用不存在或当前账号无权操作")
    fees = (await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(selected_ids), BusinessRecord.module == "finance"))).all()
    fee_by_id = {fee.id: fee for fee in fees}
    if len(fee_by_id) != len(selected_ids):
        raise HTTPException(status_code=404, detail="所选费用记录不存在")
    for fee in fees:
        case_id = int((fee.data or {}).get("case_id") or 0)
        if case_id:
            case = await db.get(BusinessRecord, case_id)
            if not case or case.module != "case":
                raise HTTPException(status_code=409, detail="案件费用关联的案件不存在")
    customers = {
        str((fee.data or {}).get("customer_id") or (fee.data or {}).get("customer_no") or fee.customer).strip()
        for fee in fees
    }
    if len(customers) != 1:
        raise HTTPException(status_code=422, detail="批量上传的费用必须属于同一客户")
    targets: list[Path] = []
    result: list[dict] = []
    try:
        for fee_id in selected_ids:
            fee = fee_by_id[fee_id]
            target = UPLOAD_ROOT / f"{uuid4().hex}{suffix}"
            target.write_bytes(content)
            targets.append(target)
            attachment = FileAttachment(
                record_id=fee.id, category="案件票据文件", original_name=filename,
                stored_name=target.name, content_type=file.content_type or "application/octet-stream",
                size=len(content), path=str(target), uploader=identity["username"],
                document_date=bill_date, remark=f"票据编号：{bill_no.strip()}",
            )
            db.add(attachment)
            await db.flush()
            metadata = {
                "attachment_id": attachment.id, "bill_no": bill_no.strip(),
                "bill_date": str(bill_date), "bill_amount": (fee.data or {}).get("amount"),
                "original_name": filename,
                "uploaded_by": identity["username"], "uploaded_at": datetime.now().isoformat(timespec="seconds"),
            }
            fee.data = {**(fee.data or {}), "receipt_files": [*(fee.data or {}).get("receipt_files", []), metadata]}
            db.add(WorkflowEvent(
                record_id=fee.id, action="批量上传案件票据文件", from_status=fee.status,
                to_status=fee.status, operator=identity["username"], comment=f"票据 {bill_no.strip()}｜附件 {attachment.id}",
            ))
            result.append({"fee_id": fee.id, **metadata})
        await db.commit()
    except Exception:
        await db.rollback()
        for target in targets:
            target.unlink(missing_ok=True)
        raise
    return {"uploaded": len(result), "items": result}
