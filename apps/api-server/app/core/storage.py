"""Extracted implementation; see scripts/rebuild_area_split.py and reference/."""
import xlrd
from app.core.constants import (
    AI_SPACE_CATEGORY, ATTACHMENT_TEXT_PREVIEW_MAX_CHARS, CASE_EVENT_TIME_ZONE, CONTRACT_PERSON_NAME_PLACEHOLDER, LEGACY_UPLOAD_ROOTS,
    PDF_PREVIEW_MAX_FILE_BYTES, PDF_PREVIEW_MAX_PAGES, UPLOAD_ROOT, XLSX_PREVIEW_MAX_COLUMNS, XLSX_PREVIEW_MAX_ROWS_PER_SHEET,
    XLSX_PREVIEW_MAX_SHEETS,
)
from app.core.dependencies import (
    AsyncSession, BusinessRecord, CommunicationLog, Document, FileAttachment,
    HTTPException, Path, datetime, io, load_workbook,
    pdfium, select, settings, timezone, uuid4,
)
from app.models_shared import (
    SealApplicationInput,
)


def _attachment_storage_path(item: FileAttachment) -> Path | None:
    """Resolve files whose database path may still use a legacy container root."""
    upload_root = UPLOAD_ROOT.resolve()
    trusted_roots = [upload_root, *(root.expanduser().resolve() for root in LEGACY_UPLOAD_ROOTS)]
    candidates = [(Path(item.path), upload_root)]
    for root in trusted_roots:
        if item.stored_name:
            candidates.append((root / Path(item.stored_name).name, root))
        if item.path:
            candidates.append((root / Path(item.path).name, root))
    for candidate, trusted_root in candidates:
        try:
            resolved = candidate.expanduser().resolve()
        except (OSError, RuntimeError):
            continue
        if resolved.is_file() and trusted_root in resolved.parents:
            return resolved
    return None


def _attachment_dict(
    item: FileAttachment,
    record: BusinessRecord | None = None,
    uploader_names: dict[str, str] | None = None,
) -> dict:
    from app.core.crm import (
        _customer_guid,
    )
    uploader_display_name = (uploader_names or {}).get(str(item.uploader or "").lower(), "") or CONTRACT_PERSON_NAME_PLACEHOLDER
    return {
        "id": item.id, "record_id": item.record_id, "communication_log_id": item.communication_log_id, "finance_transaction_id": item.finance_transaction_id,
        "customer_guid": _customer_guid(record) if record and record.module == "customer" else "",
        "record_no": record.serial_no if record else "",
        "record_title": record.title if record else "", "category": item.category, "file_type_code": item.file_type_code,
        "original_name": item.original_name, "content_type": item.content_type,
        "size": item.size, "uploader": item.uploader, "uploader_display_name": uploader_display_name, "remark": item.remark,
        "document_date": item.document_date, "is_license": bool(item.is_license), "requires_transmission": item.requires_transmission, "is_transmitted": item.is_transmitted,
        "transmitted_at": item.transmitted_at, "transmitted_by": item.transmitted_by,
        "is_locked": bool(item.is_locked), "locked_at": item.locked_at, "locked_by": item.locked_by,
        "created_at": item.created_at, "download_url": f"{settings.api_prefix}/attachments/{item.id}/download",
    }


async def _communication_attachment_context(communication_id: int, identity: dict, db: AsyncSession) -> tuple[CommunicationLog, BusinessRecord]:
    from app.core.crm import (
        _customer_or_404,
    )
    from app.core.permissions import (
        _require_record_owner_or_manager,
    )
    item = await db.get(CommunicationLog, communication_id)
    if not item or (identity.get("role") != "admin" and item.operator != identity["username"]):
        raise HTTPException(status_code=404, detail="沟通记录不存在")
    customer = await _customer_or_404(item.customer_record_id, identity, db)
    await _require_record_owner_or_manager(customer, identity, db)
    return item, customer


def _payment_package_docx_bytes(
    package: BusinessRecord,
    fees: list[BusinessRecord],
    *,
    scope: str,
) -> tuple[str, bytes]:
    from app.core.finance import (
        _round_fee_amount,
    )
    package_data = package.data or {}
    details = list(package_data.get("items") or [])
    fee_by_id = {item.id: item for item in fees}
    total_amount = _round_fee_amount(
        float(package_data.get("total_amount") or package_data.get("amount") or 0)
    )
    title = "提成付款申请单" if scope == "internal_fee" else "付款申请单"
    document = Document()
    document.add_heading(title, level=0)
    meta_rows = [
        ("打包流水号", package.serial_no),
        ("打印日期", f"{datetime.now():%Y-%m-%d}"),
        ("付款状态", package.status),
        ("收款单位", package_data.get("payee") or ""),
        ("付款总金额", f"{total_amount:.2f}"),
        ("属性", package_data.get("fee_type") or package_data.get("attribute") or ""),
        ("付款日期", package_data.get("paid_date") or package_data.get("payment_date") or ""),
        ("付款方式", package_data.get("payment_method") or ""),
        ("付款单据号", package_data.get("invoice_no") or package_data.get("writeoff_voucher_no") or ""),
        ("制单人", package_data.get("submitted_by") or package.owner or ""),
        ("备注", package_data.get("remark") or package_data.get("comment") or package.description or ""),
    ]
    meta_table = document.add_table(rows=0, cols=2)
    meta_table.style = "Table Grid"
    for label, value in meta_rows:
        cells = meta_table.add_row().cells
        cells[0].text = str(label)
        cells[1].text = str(value or "—")

    document.add_paragraph("")
    item_table = document.add_table(rows=1, cols=8)
    item_table.style = "Table Grid"
    headers = ["请款单号", "合同编号", "合同名称", "案号", "付款金额", "费用类型", "申请人", "交款人"]
    for index, header in enumerate(headers):
        item_table.rows[0].cells[index].text = header
    if details:
        source_rows = details
    else:
        source_rows = [
            {
                "fee_id": item.id,
                "request_no": item.serial_no,
                "case_no": (item.data or {}).get("case_no", ""),
                "case_name": (item.data or {}).get("case_name") or item.title,
                "amount": (item.data or {}).get("actual_commission")
                if (item.data or {}).get("actual_commission") is not None
                else (item.data or {}).get("amount") or 0,
                "commission_type": (item.data or {}).get("commission_type")
                or (item.data or {}).get("fee_type")
                or item.title,
                "payee": (item.data or {}).get("payee") or (item.data or {}).get("applicant") or item.owner,
                "remark": (item.data or {}).get("remark") or item.description or "",
            }
            for item in fees
        ]
    for row in source_rows:
        fee = fee_by_id.get(int(row.get("fee_id") or 0))
        fee_data = (fee.data or {}) if fee else {}
        cells = item_table.add_row().cells
        values = [
            row.get("request_no") or (fee.serial_no if fee else ""),
            fee_data.get("contract_no") or row.get("contract_no") or "",
            fee_data.get("contract_title") or row.get("contract_title") or "",
            row.get("case_no") or fee_data.get("case_no") or "",
            f"{_round_fee_amount(float(row.get('amount') or 0)):.2f}",
            row.get("commission_type") or fee_data.get("fee_type") or "",
            (fee_data.get("applicant") or fee.owner) if fee else "",
            row.get("payee") or package_data.get("payee") or "",
        ]
        for index, value in enumerate(values):
            cells[index].text = str(value or "—")
    document.add_paragraph("")
    document.add_paragraph("客户管理人签字：")
    document.add_paragraph("审批人签字：")
    document.add_paragraph("出纳签字：")
    output = io.BytesIO()
    document.save(output)
    filename = f"{package.serial_no}-{title}-{datetime.now():%Y%m%d%H%M%S}.docx"
    return filename, output.getvalue()


def _case_event_storage_time(value: datetime) -> datetime:
    """Normalize incoming event instants for SQLite and PostgreSQL alike.

    Browser clients submit ISO timestamps with an offset.  A timestamp without
    one is deliberately interpreted as the firm's Shanghai local time, then
    stored as UTC.  SQLite drops timezone metadata for DateTime columns, so the
    companion display function treats its naive values as UTC rather than as the
    process-local timezone.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=CASE_EVENT_TIME_ZONE)
    return value.astimezone(timezone.utc)


async def _case_word_editor_attachment(
    case_id: int, attachment_id: int, identity: dict, db: AsyncSession,
) -> tuple[BusinessRecord, FileAttachment, Path]:
    from app.core.permissions import (
        _ensure_record_module, _require_case_detail_write_access,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_detail_write_access(case_record, identity, db)
    item = await db.get(FileAttachment, attachment_id)
    if not item or item.record_id != case_record.id or item.category == AI_SPACE_CATEGORY:
        raise HTTPException(status_code=404, detail="案件正式 Word 文件不存在")
    suffix = Path(item.original_name).suffix.lower()
    if suffix == ".doc":
        raise HTTPException(status_code=422, detail="旧版 .doc 文件不支持在线编辑，请转换为 .docx 后再编辑")
    if suffix != ".docx":
        raise HTTPException(status_code=422, detail="仅支持 .docx Word 文件在线编辑")
    path = _attachment_storage_path(item)
    if path is None:
        raise HTTPException(status_code=404, detail="案件 Word 文件不存在")
    return case_record, item, path


def _xlsx_preview_text(path: Path) -> str:
    workbook = load_workbook(path, read_only=True, data_only=True)
    parts: list[str] = []
    character_count = 0
    truncated = False
    try:
        worksheets = workbook.worksheets[:XLSX_PREVIEW_MAX_SHEETS]
        for worksheet in worksheets:
            sheet_lines = [f"工作表：{worksheet.title}"]
            max_row = min(worksheet.max_row or 1, XLSX_PREVIEW_MAX_ROWS_PER_SHEET)
            max_column = min(worksheet.max_column or 1, XLSX_PREVIEW_MAX_COLUMNS)
            for cells in worksheet.iter_rows(min_row=1, max_row=max_row, max_col=max_column):
                values = ["" if cell.value is None else str(cell.value) for cell in cells]
                while values and not values[-1]:
                    values.pop()
                line = "\t".join(values)
                if character_count + len(line) + 1 > ATTACHMENT_TEXT_PREVIEW_MAX_CHARS:
                    truncated = True
                    break
                sheet_lines.append(line)
                character_count += len(line) + 1
            parts.append("\n".join(sheet_lines).rstrip())
            if truncated:
                break
        if len(workbook.worksheets) > XLSX_PREVIEW_MAX_SHEETS:
            truncated = True
    finally:
        workbook.close()
    preview_text = "\n\n".join(part for part in parts if part).strip()
    if not preview_text:
        preview_text = "（该 XLSX 工作簿没有可显示的单元格内容）"
    if truncated:
        preview_text += "\n\n[工作簿内容过长，在线预览仅显示前部分内容]"
    return preview_text


async def _authorized_pdf_preview_attachment(
    attachment_id: int, identity: dict, db: AsyncSession,
) -> tuple[FileAttachment, Path]:
    """Resolve a previewable PDF through the same authorization path as downloads."""
    from app.core.permissions import (
        _ensure_attachment_record_visible,
    )
    item = await db.get(FileAttachment, attachment_id)
    if not item:
        raise HTTPException(status_code=404, detail="附件不存在")
    if item.record_id:
        await _ensure_attachment_record_visible(item.record_id, identity, db)
    elif identity.get("role") != "admin" and item.uploader != identity["username"]:
        raise HTTPException(status_code=404, detail="附件不存在或无权访问")

    suffix = Path(item.original_name).suffix.lower()
    content_type = str(item.content_type or "").lower()
    if suffix != ".pdf" and content_type != "application/pdf":
        raise HTTPException(status_code=422, detail="仅支持 PDF 文件在线逐页预览")
    path = _attachment_storage_path(item)
    if path is None:
        raise HTTPException(status_code=404, detail="附件文件不存在")
    if path.stat().st_size > PDF_PREVIEW_MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="PDF 文件过大，不能在线逐页预览，请下载后查看")
    return item, path


def _open_preview_pdf(path: Path) -> object:
    try:
        document = pdfium.PdfDocument(path)
        page_count = len(document)
        if page_count < 1:
            document.close()
            raise HTTPException(status_code=422, detail="PDF 文件没有可预览的页面")
        if page_count > PDF_PREVIEW_MAX_PAGES:
            document.close()
            raise HTTPException(status_code=413, detail=f"PDF 页数超过在线预览上限（{PDF_PREVIEW_MAX_PAGES} 页），请下载后查看")
        return document
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail="PDF 文件无法读取或已损坏") from exc


def _pdf_preview_response_headers() -> dict[str, str]:
    return {
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; sandbox",
    }


async def _copy_seal_source_attachments(
    target_record: BusinessRecord,
    source_attachment_ids: list[int],
    identity: dict,
    db: AsyncSession,
) -> list[Path]:
    """Copy contract/case source files into a draft seal application."""
    from app.core.documents import (
            _sync_seal_document_names,
        )
    from app.core.permissions import (
            _ensure_attachment_record_visible, _ensure_record_module,
        )
    ids = list(dict.fromkeys([int(item_id) for item_id in source_attachment_ids if int(item_id) > 0]))
    if not ids:
        return []
    source_items = list((await db.scalars(select(FileAttachment).where(FileAttachment.id.in_(ids)))).all())
    if len(source_items) != len(ids):
        raise HTTPException(status_code=404, detail="閫変腑鐨勬潵婧愭枃浠朵笉瀛樺湪")
    by_id = {item.id: item for item in source_items}
    created_targets: list[Path] = []
    category = "用印文件"
    try:
        for item_id in ids:
            source = by_id[item_id]
            if not source.record_id:
                raise HTTPException(status_code=422, detail="閫変腑鐨勬潵婧愭枃浠舵湭鍏宠仈涓氬姟璁板綍")
            source_record = await _ensure_attachment_record_visible(source.record_id, identity, db)
            if source_record.module == "contract":
                await _ensure_record_module(source_record.id, "contract", identity, db)
            elif source_record.module == "case":
                await _ensure_record_module(source_record.id, "case", identity, db)
            elif source_record.module == "customer":
                await _ensure_record_module(source_record.id, "customer", identity, db)
            else:
                raise HTTPException(status_code=422, detail="鐢ㄥ嵃鐢宠鍙兘浠庡悎鍚屾垨妗堜欢澶嶅埗鏉ユ簮鏂囦欢")
            source_path = _attachment_storage_path(source)
            if source_path is None:
                raise HTTPException(status_code=404, detail=f"鏉ユ簮鏂囦欢 {source.original_name} 涓嶅瓨鍦?")
            target = UPLOAD_ROOT / f"{uuid4().hex}{source_path.suffix.lower()}"
            target.write_bytes(source_path.read_bytes())
            created_targets.append(target)
            db.add(FileAttachment(
                record_id=target_record.id,
                category=category,
                original_name=source.original_name,
                stored_name=target.name,
                content_type=source.content_type or "application/octet-stream",
                size=target.stat().st_size,
                path=str(target),
                uploader=identity["username"],
                remark=f"copied from {source_record.serial_no}",
                document_date=source.document_date,
            ))
        await db.flush()
        await _sync_seal_document_names(target_record, db)
        return created_targets
    except Exception:
        await db.rollback()
        for target in created_targets:
            target.unlink(missing_ok=True)
        raise


async def _resolve_seal_source_attachment_ids(
    body: SealApplicationInput,
    case_no: str,
    contract_no: str,
    case_record_id: int | None,
    contract_record_id: int | None,
    customer_record_id: int | None,
    identity: dict,
    db: AsyncSession,
) -> list[int]:
    """Resolve real files from the selected contract/case and reject cross-record selections."""
    from app.core.permissions import (
            _record_scope_conditions,
        )
    explicit_ids = list(dict.fromkeys(
        int(item_id)
        for item_id in [*body.source_attachment_ids, *body.contract_file_ids, *body.case_file_ids]
        if int(item_id) > 0
    ))
    module = "case" if case_no else "contract" if contract_no else ""
    serial_no = case_no or contract_no
    if not module:
        if explicit_ids:
            raise HTTPException(status_code=422, detail="行政用印不能选择合同或案件来源文件")
        return []

    scope = await _record_scope_conditions(identity, db)
    source_record = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == module,
        BusinessRecord.serial_no == serial_no,
        *scope,
    ))
    if not source_record:
        raise HTTPException(status_code=422, detail="关联业务记录不存在或当前账号无权使用")

    allowed_record_ids = {
        record_id for record_id in (case_record_id, contract_record_id, customer_record_id) if record_id
    }
    if explicit_ids:
        selected = list((await db.scalars(
            select(FileAttachment).where(FileAttachment.id.in_(explicit_ids))
        )).all())
        if len(selected) != len(explicit_ids) or any(item.record_id not in allowed_record_ids for item in selected):
            raise HTTPException(status_code=422, detail="选择的来源文件不属于当前关联合同或案件")
        return explicit_ids

    return list((await db.scalars(
        select(FileAttachment.id)
        .where(FileAttachment.record_id == source_record.id)
        .order_by(FileAttachment.created_at, FileAttachment.id)
    )).all())


async def _ipr_case_file_attachment(case_record: BusinessRecord, attachment_id: int, identity: dict, db: AsyncSession) -> FileAttachment:
    attachment = await db.scalar(select(FileAttachment).where(FileAttachment.id == attachment_id, FileAttachment.record_id == case_record.id))
    if not attachment:
        raise HTTPException(status_code=404, detail="知识产权案件文档不存在或不属于当前案件")
    return attachment


def _docx_bytes(title: str, content: str) -> bytes:
    document = Document(); document.add_heading(title, level=0)
    for raw in content.splitlines():
        line = raw.strip()
        if not line: continue
        if line.startswith("### "): document.add_heading(line[4:], level=3)
        elif line.startswith("## "): document.add_heading(line[3:], level=2)
        elif line.startswith("# "): document.add_heading(line[2:], level=1)
        elif line.startswith(("- ", "* ")): document.add_paragraph(line[2:], style="List Bullet")
        else: document.add_paragraph(line)
    output = io.BytesIO(); document.save(output); return output.getvalue()


def _xls_preview_sheets(path: Path) -> tuple[list[dict], bool]:
    """Read a bounded legacy BIFF workbook for safe browser table rendering."""
    workbook = xlrd.open_workbook(path, on_demand=True)
    sheets: list[dict] = []
    truncated = workbook.nsheets > XLSX_PREVIEW_MAX_SHEETS
    try:
        for sheet in workbook.sheets()[:XLSX_PREVIEW_MAX_SHEETS]:
            row_count = min(sheet.nrows, XLSX_PREVIEW_MAX_ROWS_PER_SHEET)
            column_count = min(sheet.ncols, XLSX_PREVIEW_MAX_COLUMNS)
            if sheet.nrows > row_count or sheet.ncols > column_count:
                truncated = True
            rows: list[list[str]] = []
            for row_index in range(row_count):
                values: list[str] = []
                for column_index in range(column_count):
                    cell = sheet.cell(row_index, column_index)
                    if cell.ctype == xlrd.XL_CELL_DATE:
                        value = xlrd.xldate.xldate_as_datetime(cell.value, workbook.datemode).isoformat(sep=" ")
                    elif cell.ctype == xlrd.XL_CELL_BOOLEAN:
                        value = "TRUE" if cell.value else "FALSE"
                    elif cell.ctype == xlrd.XL_CELL_NUMBER and float(cell.value).is_integer():
                        value = str(int(cell.value))
                    elif cell.ctype in {xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK}:
                        value = ""
                    else:
                        value = str(cell.value)
                    values.append(value)
                while values and not values[-1]:
                    values.pop()
                rows.append(values)
            sheets.append({"name": sheet.name, "rows": rows})
    finally:
        workbook.release_resources()
    return sheets, truncated
