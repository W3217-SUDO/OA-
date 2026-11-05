"""501618（高勤兰 11-05）：知识产权中心 › 案件文件 补齐旧系统的收据、发票导入。

旧系统这几项把收据、发票挂到“案件费用”上；老案件的费用还没迁成新系统的案件费用（等技术部定迁移），
迁移完成前先挂成案件文档：收据用“官费收据”、发票用“发票”文档类型，案件页“发票文件”页签能看到；
文件名里的费用号写进说明，迁移后可按费用号补关联。

- 收据自定义文件导入：文件名 A(系统案号)F(费用号)，例 A21800025F21002.jpg；可单个文件，也可 zip 打包。
- 发票文件导入（案件 / 合同）：文件名是系统开出的发票号，例 888888.jpg；按发票号找到开票记录。
两项都先预览（confirm=false，不写任何东西），确认时重新上传同一文件（confirm=true）才写入，只导入预览里没有错误的行。
"""

from __future__ import annotations

import io
import re
import zipfile
from datetime import date
from pathlib import Path, PurePosixPath
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.constants import UPLOAD_ROOT
from app.database import get_db
from app.models import BusinessRecord, FileAttachment, WorkflowEvent
from app.security import current_identity

router = APIRouter(prefix="/ipr/fee-file-import", tags=["ipr-fee-file-import"])

RECEIPT_CATEGORY = "官费收据"
RECEIPT_TYPE_CODE = "IPR-RECEIPT"
INVOICE_CATEGORY = "发票"
INVOICE_TYPE_CODE = "IPR-INVOICE"
ALLOWED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".ofd"}
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_ENTRIES = 300
RECEIPT_NAME = re.compile(r"A(\d{1,16})F(\d{1,16})", re.IGNORECASE)


def _entry_name(info: zipfile.ZipInfo) -> str:
    name = info.filename
    if not info.flag_bits & 0x800:
        # 没有 UTF-8 标记的 zip（Windows 中文系统打包）按 GBK 还原文件名。
        try:
            name = name.encode("cp437").decode("gbk")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return PurePosixPath(name).name


def expand_upload(filename: str, content: bytes) -> list[tuple[str, bytes]]:
    """上传的文件或 zip 包里的文件，按 (文件名, 内容) 列出；目录、隐藏文件跳过。"""
    name = Path(filename or "").name
    if Path(name).suffix.lower() != ".zip":
        return [(name, content)]
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=422, detail="zip 文件损坏或不是 zip 格式") from exc
    files: list[tuple[str, bytes]] = []
    total = 0
    for info in archive.infolist():
        entry = _entry_name(info)
        if info.is_dir() or not entry or entry.startswith((".", "__MACOSX")) or "__MACOSX" in info.filename:
            continue
        if len(files) >= MAX_ENTRIES:
            raise HTTPException(status_code=422, detail=f"zip 里最多 {MAX_ENTRIES} 个文件，请拆分后上传")
        if info.file_size > MAX_FILE_BYTES:
            files.append((entry, b""))
            continue
        total += info.file_size
        if total > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="zip 解压后超过 100MB，请拆分后上传")
        files.append((entry, archive.read(info)))
    if not files:
        raise HTTPException(status_code=422, detail="zip 里没有可导入的文件")
    return files


def _file_errors(name: str, content: bytes) -> list[str]:
    if Path(name).suffix.lower() not in ALLOWED_SUFFIXES:
        return ["只能导入 PDF、图片或 OFD 文件"]
    if not content:
        return ["文件为空或超过 20MB"]
    return []


async def _read_upload(file: UploadFile) -> bytes:
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=422, detail="请选择要导入的文件")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="上传文件不能超过 100MB，请拆分后上传")
    return content


async def _require_import(identity: dict, db: AsyncSession) -> None:
    from app.core.permissions import _require_record_module_menu, _require_role_action
    await _require_role_action(identity, db, "ipr.case.file.manage")
    await _require_record_module_menu("ipr_case", identity, db, action="导入")


async def _visible_ipr_cases_by_number(identity: dict, db: AsyncSession) -> dict[str, list[BusinessRecord]]:
    """可见知识产权案件按系统案号（旧系统数字案号）建索引，一次查完，zip 里多个文件共用。"""
    from app.core.legacy_sync import _legacy_case_number_values
    from app.core.permissions import _record_scope_conditions
    rows = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "ipr_case", BusinessRecord.deleted_at.is_(None), *(await _record_scope_conditions(identity, db)),
    ))).all())
    index: dict[str, list[BusinessRecord]] = {}
    for row in rows:
        for value in _legacy_case_number_values(row):
            index.setdefault(value, []).append(row)
    return index


async def _fee_type_names(codes: set[str], db: AsyncSession) -> dict[str, str]:
    """费用号对应的费用名称：两套旧知识产权系统的费用类型表（镜像在的才查）。"""
    names: dict[str, str] = {}
    if not codes:
        return names
    for schema in ("public", "legacy_ipr_hd"):
        exists = await db.scalar(text(f"SELECT to_regclass('{schema}.\"IPR_Case_FeeType\"') IS NOT NULL")) if db.get_bind().dialect.name == "postgresql" else False
        if not exists:
            continue
        rows = (await db.execute(text(
            f'SELECT CAST("FeeTypeCode" AS text), "FeeTypeName" FROM {schema}."IPR_Case_FeeType" WHERE CAST("FeeTypeCode" AS text) = ANY(:codes)'
        ), {"codes": sorted(codes)})).all()
        for code, name in rows:
            names.setdefault(str(code), str(name or ""))
    return names


def _store(content: bytes, original_name: str) -> tuple[str, Path]:
    suffix = Path(original_name).suffix.lower()
    stored_name = f"{uuid4().hex}{suffix}"
    target = UPLOAD_ROOT / stored_name
    target.write_bytes(content)
    return stored_name, target


@router.post("/receipts")
async def import_receipt_files(
    file: UploadFile = File(...), confirm: bool = Form(False), document_date: date | None = Form(None),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """收据自定义文件导入：A(系统案号)F(费用号)。预览不写入；确认时只导入没有错误的行。"""
    await _require_import(identity, db)
    from app.core.permissions import _ensure_ipr_case_file_write
    entries = expand_upload(file.filename or "", await _read_upload(file))
    index = await _visible_ipr_cases_by_number(identity, db)
    parsed = [(name, content, RECEIPT_NAME.fullmatch(Path(name).stem.strip())) for name, content in entries]
    fee_names = await _fee_type_names({match.group(2) for _name, _content, match in parsed if match}, db)
    rows: list[dict] = []
    targets: list[tuple[dict, bytes, BusinessRecord]] = []
    for name, content, match in parsed:
        errors = _file_errors(name, content)
        case_no = fee_code = ""
        record = None
        if not match:
            errors.append("文件名要按 A(系统案号)F(费用号) 命名，例如 A21800025F21002.jpg")
        else:
            case_no, fee_code = match.group(1), match.group(2)
            matched = index.get(case_no.lstrip("0") or "0", [])
            if not matched:
                errors.append("没有找到这个系统案号的知识产权案件（或没有查看权限）")
            elif len(matched) > 1:
                errors.append("这个系统案号对应多个案件，请改用案件页上传")
            else:
                record = matched[0]
                try:
                    await _ensure_ipr_case_file_write(record.id, identity, db)
                except HTTPException as exc:
                    errors.append(str(exc.detail))
        data = (record.data or {}) if record else {}
        row = {
            "file_name": name, "case_no": case_no, "fee_code": fee_code, "fee_type": fee_names.get(fee_code, ""),
            "case_id": record.id if record else None, "serial_no": record.serial_no if record else "",
            "case_kind": data.get("case_kind") or "", "case_type": data.get("case_type") or "",
            "application_no": data.get("application_no") or "", "errors": errors,
            "status": "可导入" if not errors else "；".join(errors),
        }
        rows.append(row)
        if not errors and record:
            targets.append((row, content, record))
    if not confirm:
        return {"items": rows, "total": len(rows), "importable": len(targets)}
    if not targets:
        raise HTTPException(status_code=422, detail="没有可导入的文件，请按预览里的提示修改后重新上传")
    written: list[Path] = []
    try:
        for row, content, record in targets:
            stored_name, path = _store(content, row["file_name"])
            written.append(path)
            fee_text = f"费用号 {row['fee_code']}" + (f"（{row['fee_type']}）" if row["fee_type"] else "")
            db.add(FileAttachment(
                record_id=record.id, category=RECEIPT_CATEGORY, file_type_code=RECEIPT_TYPE_CODE, original_name=row["file_name"],
                stored_name=stored_name, content_type="application/octet-stream", size=len(content), path=str(path),
                uploader=identity["username"], remark=f"收据自定义文件导入：{fee_text}", document_date=document_date or date.today(),
            ))
            db.add(WorkflowEvent(record_id=record.id, action="导入官费收据", from_status=record.status, to_status=record.status,
                                 operator=identity["username"], comment=f"{row['file_name']}｜{fee_text}"))
        await db.commit()
    except Exception:
        await db.rollback()
        for path in written:
            path.unlink(missing_ok=True)
        raise
    return {"items": rows, "total": len(rows), "created": len(targets)}


@router.post("/invoices")
async def import_invoice_files(
    file: UploadFile = File(...), scope: str = Form("case"), confirm: bool = Form(False), document_date: date | None = Form(None),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """发票文件导入：文件名是系统开出的发票号。scope=case 挂到发票关联的知识产权案件，scope=contract 挂到合同开票记录。"""
    await _require_import(identity, db)
    if scope not in {"case", "contract"}:
        raise HTTPException(status_code=422, detail="发票导入类型无效")
    from app.core.permissions import _ensure_ipr_case_file_write
    entries = expand_upload(file.filename or "", await _read_upload(file))
    numbers = {Path(name).stem.strip() for name, _content in entries}
    invoices: dict[str, list[BusinessRecord]] = {}
    if numbers:
        for row in (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "invoice", BusinessRecord.deleted_at.is_(None),
            BusinessRecord.data["invoice_no"].as_string().in_(sorted(numbers)),
        ))).all():
            invoices.setdefault(str((row.data or {}).get("invoice_no") or ""), []).append(row)
    case_ids = {int(value) for rows in invoices.values() for row in rows for value in ((row.data or {}).get("case_ids") or []) if str(value).isdigit()}
    cases = {row.id: row for row in (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(case_ids), BusinessRecord.module == "ipr_case", BusinessRecord.deleted_at.is_(None),
    ))).all()} if case_ids else {}
    rows: list[dict] = []
    targets: list[tuple[dict, bytes, BusinessRecord, list[BusinessRecord]]] = []
    for name, content in entries:
        number = Path(name).stem.strip()
        errors = _file_errors(name, content)
        matched = invoices.get(number, [])
        invoice = matched[0] if len(matched) == 1 else None
        linked: list[BusinessRecord] = []
        if not matched:
            errors.append("系统里没有这个发票号的开票记录")
        elif len(matched) > 1:
            errors.append("这个发票号对应多条开票记录，请到开票管理里上传")
        else:
            data = invoice.data or {}
            linked = [cases[int(value)] for value in (data.get("case_ids") or []) if str(value).isdigit() and int(value) in cases]
            if scope == "case":
                if not linked:
                    errors.append("这张发票没有关联知识产权案件，请用“发票文件导入（合同）”")
                for record in linked:
                    try:
                        await _ensure_ipr_case_file_write(record.id, identity, db)
                    except HTTPException as exc:
                        errors.append(f"{record.serial_no}：{exc.detail}")
            elif not (data.get("contract_no") or data.get("contract_record_id") or data.get("contract_id")):
                errors.append("这张发票没有关联合同，请用“发票文件导入（案件）”")
        data = (invoice.data or {}) if invoice else {}
        row = {
            "file_name": name, "invoice_no": number, "invoice_id": invoice.id if invoice else None,
            "invoice_serial_no": invoice.serial_no if invoice else "", "customer": (invoice.customer if invoice else "") or data.get("customer") or "",
            "contract_no": data.get("contract_no") or "", "amount": data.get("amount"), "invoice_date": str(data.get("invoice_date") or data.get("issued_date") or "")[:10],
            "status_text": invoice.status if invoice else "", "applicant": data.get("applicant") or data.get("requester") or "",
            "cases": [{"id": item.id, "serial_no": item.serial_no, "application_no": (item.data or {}).get("application_no") or "",
                       "case_type": (item.data or {}).get("case_type") or ""} for item in linked],
            "remark": data.get("remark") or "", "errors": errors, "status": "可导入" if not errors else "；".join(errors),
        }
        rows.append(row)
        if not errors and invoice:
            targets.append((row, content, invoice, linked if scope == "case" else []))
    if not confirm:
        return {"items": rows, "total": len(rows), "importable": len(targets)}
    if not targets:
        raise HTTPException(status_code=422, detail="没有可导入的文件，请按预览里的提示修改后重新上传")
    written: list[Path] = []
    try:
        for row, content, invoice, linked in targets:
            owners = linked or [invoice]
            for owner in owners:
                stored_name, path = _store(content, row["file_name"])
                written.append(path)
                is_case = owner.module == "ipr_case"
                db.add(FileAttachment(
                    record_id=owner.id, invoice_record_id=invoice.id, category=INVOICE_CATEGORY if is_case else "发票文件",
                    file_type_code=INVOICE_TYPE_CODE if is_case else "", original_name=row["file_name"], stored_name=stored_name,
                    content_type="application/octet-stream", size=len(content), path=str(path), uploader=identity["username"],
                    remark=f"发票文件导入：发票号 {row['invoice_no']}（{invoice.serial_no}）", document_date=document_date or date.today(),
                ))
                db.add(WorkflowEvent(record_id=owner.id, action="导入发票文件", from_status=owner.status, to_status=owner.status,
                                     operator=identity["username"], comment=f"{row['file_name']}｜发票号 {row['invoice_no']}"))
        await db.commit()
    except Exception:
        await db.rollback()
        for path in written:
            path.unlink(missing_ok=True)
        raise
    return {"items": rows, "total": len(rows), "created": len(targets)}


__all__ = ["router", "expand_upload", "settings"]
