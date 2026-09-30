"""按已开票申请的发票号导入文件，并为申请中的每笔费用保存独立副本。"""
import mimetypes
from pathlib import Path, PurePosixPath
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

from fastapi import HTTPException
from sqlalchemy import select, update

from app.models import BusinessRecord, FileAttachment, User, WorkflowEvent
from app.security import user_role_ids
from app.core.constants import UPLOAD_ROOT
from app.core.invoice_sources import invoice_source_fees

CATEGORY = "案件发票文件"
MAX_BYTES = 20 * 1024 * 1024
FILE_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".ofd", ".xlsx", ".xls", ".csv"}


async def require_invoice_file_access(identity, db):
    from app.core.permissions import _user_permission_payload
    user = await db.scalar(select(User).where(User.username == identity["username"], User.is_active.is_(True)))
    if not user:
        raise HTTPException(401, "当前用户不存在或已停用")
    menus = (await _user_permission_payload(user, db)).get("menu_keys") or []
    if "admin" not in user_role_ids(user) and "case-files-invoice" not in menus:
        raise HTTPException(403, "当前账号没有案件发票文件权限")


def _invoice_file_entries(attachment):
    from app.core.storage import _attachment_storage_path
    path = _attachment_storage_path(attachment)
    if path is None:
        raise HTTPException(409, "上传文件不存在，请重新上传")
    if Path(attachment.original_name).suffix.lower() != ".zip":
        if path.stat().st_size > MAX_BYTES:
            raise HTTPException(413, "单个文件不能超过 20MB")
        return path, [(attachment.original_name, path.read_bytes())]
    try:
        with ZipFile(path) as archive:
            members = [item for item in archive.infolist() if not item.is_dir()]
            if not members or len(members) > 100 or sum(item.file_size for item in members) > MAX_BYTES:
                raise HTTPException(422, "压缩包须包含 1–100 个文件，解压总量不能超过 20MB")
            entries = []
            for member in members:
                name = PurePosixPath(member.filename.replace("\\", "/"))
                if name.is_absolute() or ".." in name.parts or member.flag_bits & 1:
                    raise HTTPException(422, "压缩包包含不安全路径或加密文件")
                entries.append((name.name, archive.read(member)))
            return path, entries
    except (BadZipFile, RuntimeError) as exc:
        raise HTTPException(422, "压缩包无法读取，请检查文件格式") from exc


async def import_invoice_files(identity, db):
    from app.core.permissions import _record_scope_conditions
    await require_invoice_file_access(identity, db)
    # 更新锁在 SQLite 和 PostgreSQL 均串行化同一批待导入附件，重试不会再次复制。
    await db.execute(update(FileAttachment).where(
        FileAttachment.category == CATEGORY, FileAttachment.uploader == identity["username"],
        FileAttachment.record_id.is_(None),
    ).values(remark=FileAttachment.remark))
    pending = list((await db.scalars(select(FileAttachment).where(
        FileAttachment.category == CATEGORY, FileAttachment.uploader == identity["username"],
        FileAttachment.record_id.is_(None),
    ).order_by(FileAttachment.id).execution_options(populate_existing=True))).all())
    invoices = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "invoice", BusinessRecord.status == "已开票",
        *(await _record_scope_conditions(identity, db)),
    ))).all())
    by_number = {}
    for invoice in invoices:
        number = str((invoice.data or {}).get("invoice_no") or "").strip()
        if number:
            by_number.setdefault(number, []).append(invoice)
    results, created_paths, obsolete_paths = [], [], []
    try:
        for attachment in pending:
            try:
                source_path, entries = _invoice_file_entries(attachment)
                plans = []
                seen = set()
                for name, content in entries:
                    number = Path(name).stem.strip()
                    if Path(name).suffix.lower() not in FILE_SUFFIXES:
                        raise HTTPException(422, f"{name}：不支持的发票文件格式")
                    if number in seen:
                        raise HTTPException(409, f"压缩包中发票号 {number} 重复")
                    seen.add(number)
                    matches = by_number.get(number, [])
                    if len(matches) != 1:
                        raise HTTPException(409, f"{name}：未找到唯一可见的已开票申请，请核对文件名与发票号")
                    invoice = matches[0]
                    fees = await invoice_source_fees(invoice, identity, db, positive_only=True)
                    plans.extend((name, content, invoice, fee) for fee in fees)
            except HTTPException as exc:
                attachment.remark = f"导入失败：{exc.detail}"
                results.append({"id": attachment.id, "matched": False, "message": str(exc.detail)})
                continue
            # 全部成员与费用先验证，再在同一事务中创建独立文件与关系。
            for index, (name, content, invoice, fee) in enumerate(plans):
                target = UPLOAD_ROOT / f"{uuid4().hex}{Path(name).suffix.lower()}"
                created_paths.append(target)
                target.write_bytes(content)
                item = attachment if index == 0 else FileAttachment(uploader=attachment.uploader, created_at=attachment.created_at)
                item.record_id = fee.id
                item.invoice_record_id = invoice.id
                item.category = CATEGORY
                item.original_name = name
                item.stored_name = target.name
                item.path = str(target)
                item.content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
                item.size = len(content)
                item.remark = f"按发票号 {invoice.data['invoice_no']} 导入费用 {fee.serial_no}"
                db.add(item)
                db.add(WorkflowEvent(record_id=fee.id, action="导入案件发票文件", from_status=fee.status,
                                     to_status=fee.status, operator=identity["username"], comment=f"{name}｜申请 {invoice.serial_no}"))
            obsolete_paths.append(source_path)
            results.append({"id": attachment.id, "matched": True, "fee_files": len(plans)})
        await db.commit()
    except Exception:
        await db.rollback()
        for path in created_paths:
            path.unlink(missing_ok=True)
        raise
    for path in obsolete_paths:
        path.unlink(missing_ok=True)
    matched = sum(bool(item["matched"]) for item in results)
    return {"processed": len(results), "matched": matched, "unmatched": len(results) - matched, "items": results}


async def invoice_file_rows(identity, db, page, page_size):
    from app.core.formatters import _person_display_name, _user_display_map
    from app.core.permissions import _filter_visible_attachments, _record_scope_conditions
    from app.core.storage import _attachment_dict
    from app.core.system import _allowed_field_keys, _record_dict
    await require_invoice_file_access(identity, db)
    items = list((await db.scalars(select(FileAttachment).where(FileAttachment.category == CATEGORY)
                                  .order_by(FileAttachment.created_at.desc(), FileAttachment.id.desc()))).all())
    items = await _filter_visible_attachments(items, identity, db)
    # 未匹配文件仅由上传人处理，不能因页面能力扩张而暴露其他人的待导入文件。
    items = [item for item in items if item.record_id or item.uploader == identity["username"]]
    total = len(items)
    items = items[(page - 1) * page_size:page * page_size]
    ids = {value for item in items for value in (item.record_id, item.invoice_record_id) if value}
    records = {record.id: record for record in (await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(ids)))).all()}
    case_nos = {str((record.data or {}).get("case_no") or "") for record in records.values() if record.module == "finance"} - {""}
    cases = {record.serial_no: record for record in (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case", BusinessRecord.serial_no.in_(case_nos), *(await _record_scope_conditions(identity, db)),
    ))).all()} if case_nos else {}
    usernames = {item.uploader for item in items} | {record.owner for record in records.values() if record.module == "invoice"}
    users = await _user_display_map(usernames, db)
    names = {username: _person_display_name(user.display_name, user.username)[0] for username, user in users.items()}
    fields = await _allowed_field_keys(identity, db)
    rows = []
    for item in items:
        fee, invoice = records.get(item.record_id), records.get(item.invoice_record_id)
        row = _attachment_dict(item, fee, names)
        linked = bool(fee and fee.module == "finance" and invoice and invoice.module == "invoice")
        row["match_status"] = "已关联费用" if linked else "历史文件未关联发票申请" if item.record_id else item.remark or "待导入"
        if linked:
            fee_data = _record_dict(fee, fields)["data"]
            invoice_data = _record_dict(invoice, fields)["data"]
            case = cases.get(str(fee_data.get("case_no") or ""))
            row.update(case_no=fee_data.get("case_no", ""), case_type=(case.data or {}).get("case_type", "") if case else "",
                       fee_type=fee_data.get("fee_type", ""), fee_amount=fee_data.get("amount"),
                       invoice_no=invoice_data.get("invoice_no", ""), invoice_amount=invoice_data.get("amount"),
                       invoice_date=invoice_data.get("invoice_date", ""), applicant=invoice.owner,
                       applicant_display_name=names.get(invoice.owner.lower(), ""))
        rows.append(row)
    return {"items": rows, "total": total, "page": page, "page_size": page_size,
            "pages": (total + page_size - 1) // page_size if total else 0}
