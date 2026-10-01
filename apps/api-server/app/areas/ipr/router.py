"""知识产权案件路由编排。"""
from typing import Literal
from app.models_shared import IprCaseBatchCreateRow
from app.core.constants import (
    IPR_CASE_CATEGORIES, IPR_CASE_DOCUMENT_TYPES, IPR_CASE_DRAFT_STATUSES,
    IPR_CASE_KINDS, UPLOAD_ROOT,
)
from app.core.dependencies import (
    AsyncSession, BusinessRecord, Depends,
    Document, File, FileAttachment, FinanceTransaction, Form,
    HTTPException, IprCaseBatch, IprCaseBatchItem, IprCaseCustomer, IprCaseCustomerContact, IprCaseLawFirm, IprCaseLog, IprCaseRebootLink, IprCaseReminderType, IprCaseWarning, IprCaseWarningRule, IprOfficialImportBatch,
    IprOfficialImportCandidate, LawFirm, Notification, Path, Query,
    Response, StreamingResponse, String, UploadFile,
    User, WorkflowEvent, csv, current_identity, date,
    datetime, delete, func, get_db, io,
    json, or_, quote, select,
    settings, status, uuid4, xml_escape, zipfile,
)
from app.models_shared import (
    IprCaseAnnualFeeMonitoringInput, IprCaseBatchCreateInput, IprCaseBatchMaintenanceInput, IprCaseCreateInput,
    IprCaseCrossModuleLinkInput, IprCaseCustomerContactReplaceInput, IprCaseCustomerReplaceInput, IprCaseLawFirmReplaceInput, IprCaseLifecycleInput,
    IprCaseLogInput, IprCaseMaintenanceInput, IprCaseRebootInput, IprCaseReminderTypeInput, IprCaseReminderTypeUpdateInput, IprCaseReviewInput, IprCaseUpdateInput,
    IprCaseWarningProcessInput, IprLitigationCourtInfoInput, IprLitigationCourtInput,
    IprLitigationPartyInput, IprOfficialCandidateConfirmInput, IprOfficialCandidateCorrectInput, IprOfficialCandidateMatchInput, IprOfficialFileActionInput,
    IprOfficialFileBatchActionInput, TaskInput,
)
from app.core.conflict_review import assess_conflict_review, get_conflict_review_gate, require_conflict_clear
from fastapi import APIRouter

router = APIRouter()


@router.get(f"{settings.api_prefix}/ipr/reminder-types")
async def list_ipr_reminder_types(
    include_inactive: bool = False,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Legacy CaseReminderList workbench with counts from the caller's IPR scope."""
    from app.core.ipr import (
        _ipr_cases_for_reminder_type, _ipr_reminder_type_dict,
    )
    from app.core.permissions import (
        _require_ipr_reminder_type_manage, _require_record_module_menu,
    )
    await _require_record_module_menu("ipr_case", identity, db, action="查看")
    if include_inactive:
        _require_ipr_reminder_type_manage(identity)
    statement = select(IprCaseReminderType)
    if not include_inactive:
        statement = statement.where(IprCaseReminderType.is_active.is_(True))
    types = list((await db.scalars(statement.order_by(IprCaseReminderType.sort_order, IprCaseReminderType.name, IprCaseReminderType.id))).all())
    items = []
    for item in types:
        _, matching_rows = await _ipr_cases_for_reminder_type(item.id, identity, db)
        items.append(_ipr_reminder_type_dict(item, len(matching_rows)))
    return {
        "items": items,
        "total": len(types),
    }


@router.post(f"{settings.api_prefix}/ipr/reminder-types", status_code=status.HTTP_201_CREATED)
async def create_ipr_reminder_type(
    body: IprCaseReminderTypeInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.ipr import (
        _ipr_reminder_type_dict, _ipr_reminder_type_query_object,
    )
    from app.core.permissions import (
        _require_ipr_reminder_type_manage,
    )
    _require_ipr_reminder_type_manage(identity)
    name = body.name.strip()
    if await db.scalar(select(IprCaseReminderType.id).where(IprCaseReminderType.name == name)):
        raise HTTPException(status_code=409, detail="案件提醒类型名称已存在")
    row = IprCaseReminderType(
        name=name,
        query_object=_ipr_reminder_type_query_object(body.query_object),
        is_default=body.is_default,
        is_active=body.is_active,
        sort_order=body.sort_order,
        created_by=identity["username"],
        updated_by=identity["username"],
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _ipr_reminder_type_dict(row)


@router.patch(f"{settings.api_prefix}/ipr/reminder-types/{{reminder_type_id}}")
async def update_ipr_reminder_type(
    reminder_type_id: int,
    body: IprCaseReminderTypeUpdateInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.ipr import (
        _ipr_reminder_type_dict, _ipr_reminder_type_query_object,
    )
    from app.core.permissions import (
        _require_ipr_reminder_type_manage,
    )
    _require_ipr_reminder_type_manage(identity)
    row = await db.get(IprCaseReminderType, reminder_type_id)
    if not row:
        raise HTTPException(status_code=404, detail="案件提醒类型不存在")
    if body.name is not None:
        name = body.name.strip()
        duplicate = await db.scalar(select(IprCaseReminderType.id).where(IprCaseReminderType.name == name, IprCaseReminderType.id != row.id))
        if duplicate:
            raise HTTPException(status_code=409, detail="案件提醒类型名称已存在")
        row.name = name
    if body.query_object is not None:
        row.query_object = _ipr_reminder_type_query_object(body.query_object)
    if body.is_default is not None:
        row.is_default = body.is_default
    if body.is_active is not None:
        row.is_active = body.is_active
    if body.sort_order is not None:
        row.sort_order = body.sort_order
    row.updated_by = identity["username"]
    await db.commit()
    await db.refresh(row)
    return _ipr_reminder_type_dict(row)


@router.delete(f"{settings.api_prefix}/ipr/reminder-types/{{reminder_type_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ipr_reminder_type(
    reminder_type_id: int,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _require_ipr_reminder_type_manage,
    )
    _require_ipr_reminder_type_manage(identity)
    row = await db.get(IprCaseReminderType, reminder_type_id)
    if not row:
        raise HTTPException(status_code=404, detail="案件提醒类型不存在")
    if row.is_default:
        raise HTTPException(status_code=409, detail="默认案件提醒类型不能删除，请先取消默认标记")
    await db.delete(row)
    await db.commit()


@router.get(f"{settings.api_prefix}/ipr/reminder-types/{{reminder_type_id}}/cases")
async def list_ipr_cases_by_reminder_type(
    reminder_type_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.ipr import (
        _ipr_cases_for_reminder_type, _ipr_reminder_type_dict,
    )
    from app.core.permissions import (
        _require_record_module_menu,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    await _require_record_module_menu("ipr_case", identity, db, action="查看")
    reminder_type, rows = await _ipr_cases_for_reminder_type(reminder_type_id, identity, db)
    total = len(rows)
    page_rows = rows[(page - 1) * page_size: page * page_size]
    return {
        "reminder_type": _ipr_reminder_type_dict(reminder_type, total),
        "items": [_record_dict(row, await _allowed_field_keys(identity, db)) for row in page_rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
    }


@router.get(f"{settings.api_prefix}/ipr/cases")
async def list_ipr_cases(
    case_kind: str = "", record_status: str = "", keyword: str = "", annual_fee_monitoring: bool | None = None,
    case_type: str = "", case_phase: str = "", reminder_type: str = "", case_category: str = "",
    reminder_type_id: int | None = Query(None, ge=1),
    date_from: date | None = None, date_to: date | None = None,
    search_by_month_day: bool = False, month_day: str = "", role_view: str = "",
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.ipr import (
        _ipr_case_list_conditions, _ipr_cases_for_reminder_type,
    )
    from app.core.permissions import (
        _require_record_module_menu,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    await _require_record_module_menu("ipr_case", identity, db, action="查看")
    conditions = await _ipr_case_list_conditions(
        identity, db, case_kind=case_kind, record_status=record_status, keyword=keyword,
        annual_fee_monitoring=annual_fee_monitoring, case_type=case_type, case_phase=case_phase,
        reminder_type=reminder_type, case_category=case_category, date_from=date_from, date_to=date_to,
        search_by_month_day=search_by_month_day, month_day=month_day, role_view=role_view,
    )
    if reminder_type_id is not None:
        _, matched_rows = await _ipr_cases_for_reminder_type(reminder_type_id, identity, db, conditions)
        total = len(matched_rows)
        rows = matched_rows[(page - 1) * page_size: page * page_size]
    else:
        total = int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(*conditions)) or 0)
        rows = (await db.scalars(select(BusinessRecord).where(*conditions).order_by(BusinessRecord.updated_at.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    return {
        "items": [_record_dict(row, await _allowed_field_keys(identity, db)) for row in rows],
        "total": total, "page": page, "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
    }


@router.get(f"{settings.api_prefix}/ipr/cases/export/excel")
async def export_ipr_cases_excel(
    case_kind: str = "", record_status: str = "", keyword: str = "", annual_fee_monitoring: bool | None = None,
    case_type: str = "", case_phase: str = "", reminder_type: str = "", case_category: str = "",
    reminder_type_id: int | None = Query(None, ge=1),
    date_from: date | None = None, date_to: date | None = None,
    search_by_month_day: bool = False, month_day: str = "", role_view: str = "",
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """Export the caller's visible IPR cases as a real SpreadsheetML workbook.

    The legacy patent/trademark lists expose an Excel export.  Keep the export
    scoped by the same record and menu rules as the visible list, rather than
    exporting all firm records from a generic reporting endpoint.
    """
    from app.core.ipr import (
        _ipr_case_export_headers, _ipr_case_export_values, _ipr_case_list_conditions, _ipr_cases_for_reminder_type,
    )
    from app.core.permissions import (
        _require_record_module_menu,
    )
    await _require_record_module_menu("ipr_case", identity, db, action="查看")
    conditions = await _ipr_case_list_conditions(
        identity, db, case_kind=case_kind, record_status=record_status, keyword=keyword,
        annual_fee_monitoring=annual_fee_monitoring, case_type=case_type, case_phase=case_phase,
        reminder_type=reminder_type, case_category=case_category, date_from=date_from, date_to=date_to,
        search_by_month_day=search_by_month_day, month_day=month_day, role_view=role_view,
    )
    if reminder_type_id is not None:
        _, rows = await _ipr_cases_for_reminder_type(reminder_type_id, identity, db, conditions)
    else:
        rows = (await db.scalars(select(BusinessRecord).where(*conditions).order_by(BusinessRecord.updated_at.desc()))).all()
    headers = _ipr_case_export_headers()
    number_indexes = {19, 21}
    def cell(value: object, *, number: bool = False) -> str:
        rendered = f"{float(value or 0):.2f}" if number else str(value or "")
        return f'<Cell><Data ss:Type="{"Number" if number else "String"}">{xml_escape(rendered)}</Data></Cell>'
    sheet_rows = ["<Row>" + "".join(cell(header) for header in headers) + "</Row>"]
    for row in rows:
        values = _ipr_case_export_values(row)
        sheet_rows.append("<Row>" + "".join(cell(value, number=index in number_indexes) for index, value in enumerate(values)) + "</Row>")
    sheet_name = f"{case_kind or '知识产权'}案件"
    workbook = '<?xml version="1.0" encoding="UTF-8"?><?mso-application progid="Excel.Sheet"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="' + sheet_name + '"><Table>' + "".join(sheet_rows) + "</Table></Worksheet></Workbook>"
    filename = f"{sheet_name}清单-{date.today()}.xls"
    return Response(
        content=workbook.encode("utf-8"), media_type="application/vnd.ms-excel",
        headers={"Content-Disposition": f"attachment; filename=ipr-cases.xls; filename*=UTF-8''{quote(filename)}"},
    )


@router.get(f"{settings.api_prefix}/ipr/cases/export/word")
async def export_ipr_cases_word(
    case_kind: str = "", record_status: str = "", keyword: str = "", annual_fee_monitoring: bool | None = None,
    case_type: str = "", case_phase: str = "", reminder_type: str = "", case_category: str = "",
    reminder_type_id: int | None = Query(None, ge=1),
    date_from: date | None = None, date_to: date | None = None,
    search_by_month_day: bool = False, month_day: str = "", role_view: str = "",
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """Export the caller's visible IPR cases as a real .docx with the legacy CaseListToWord columns."""
    from app.core.ipr import (
        _ipr_case_export_headers, _ipr_case_export_values, _ipr_case_list_conditions, _ipr_cases_for_reminder_type,
    )
    from app.core.permissions import (
        _require_record_module_menu,
    )
    await _require_record_module_menu("ipr_case", identity, db, action="查看")
    conditions = await _ipr_case_list_conditions(
        identity, db, case_kind=case_kind, record_status=record_status, keyword=keyword,
        annual_fee_monitoring=annual_fee_monitoring, case_type=case_type, case_phase=case_phase,
        reminder_type=reminder_type, case_category=case_category, date_from=date_from, date_to=date_to,
        search_by_month_day=search_by_month_day, month_day=month_day, role_view=role_view,
    )
    if reminder_type_id is not None:
        _, rows = await _ipr_cases_for_reminder_type(reminder_type_id, identity, db, conditions)
    else:
        rows = (await db.scalars(select(BusinessRecord).where(*conditions).order_by(BusinessRecord.updated_at.desc()))).all()
    headers = _ipr_case_export_headers()
    document = Document()
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for index, header in enumerate(headers):
        table.rows[0].cells[index].text = header
    for row in rows:
        cells = table.add_row().cells
        for index, value in enumerate(_ipr_case_export_values(row)):
            cells[index].text = str(value or "")
    buffer = io.BytesIO()
    document.save(buffer)
    filename = f"{case_kind or '知识产权'}案件清单-{date.today()}.docx"
    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=ipr-cases.docx; filename*=UTF-8''{quote(filename)}"},
    )


@router.get(f"{settings.api_prefix}/ipr/cases/{{case_id}}")
async def get_ipr_case(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _require_record_module_menu,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    await _require_record_module_menu("ipr_case", identity, db, action="查看")
    return _record_dict(await _ensure_record_module(case_id, "ipr_case", identity, db), await _allowed_field_keys(identity, db))


@router.get(f"{settings.api_prefix}/ipr/lawsuit/cases")
async def list_ipr_lawsuit_cases(
    case_kind: str = "", record_status: str = "", keyword: str = "", page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """A scoped litigation-only projection of the existing IPR case list."""
    return await list_ipr_cases(case_kind=case_kind, record_status=record_status, keyword=keyword, case_category="litigation", reminder_type_id=None, page=page, page_size=page_size, identity=identity, db=db)


@router.get(f"{settings.api_prefix}/ipr/lawsuit/cases/{{case_id}}/court-info")
async def get_ipr_litigation_court_info(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    data = record.data or {}
    if data.get("case_category", "non_litigation") != "litigation":
        raise HTTPException(status_code=422, detail="当前知识产权案件不是诉讼案件")
    return {key: data.get(key, "") for key in ("court_case_no", "court_name", "judge", "clerk", "plaintiff", "defendant", "third_parties")}


@router.put(f"{settings.api_prefix}/ipr/lawsuit/cases/{{case_id}}/court-info")
async def update_ipr_litigation_court_info(case_id: int, body: IprLitigationCourtInfoInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _save_ipr_litigation_data,
    )
    from app.core.permissions import (
        _ensure_ipr_litigation_case_write,
    )
    record = await _ensure_ipr_litigation_case_write(case_id, identity, db)
    data = dict(record.data or {})
    data.update({key: str(value).strip() for key, value in body.model_dump().items()})
    await _save_ipr_litigation_data(record, data, identity, db, "修改知识产权诉讼法院及当事人信息", data.get("court_case_no", ""))
    return {**await get_ipr_litigation_court_info(case_id, identity, db), "conflict_review": (record.data or {}).get("conflict_review")}


@router.get(f"{settings.api_prefix}/ipr/lawsuit/cases/{{case_id}}/courts")
async def list_ipr_litigation_courts(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _ipr_litigation_rows,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    if (record.data or {}).get("case_category", "non_litigation") != "litigation":
        raise HTTPException(status_code=422, detail="当前知识产权案件不是诉讼案件")
    rows = _ipr_litigation_rows(record.data or {}, "litigation_courts")
    return {"items": rows, "total": len(rows)}


@router.post(f"{settings.api_prefix}/ipr/lawsuit/cases/{{case_id}}/courts", status_code=status.HTTP_201_CREATED)
async def create_ipr_litigation_court(case_id: int, body: IprLitigationCourtInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _ipr_litigation_rows, _save_ipr_litigation_data,
    )
    from app.core.permissions import (
        _ensure_ipr_litigation_case_write,
    )
    record = await _ensure_ipr_litigation_case_write(case_id, identity, db)
    data = dict(record.data or {}); rows = _ipr_litigation_rows(data, "litigation_courts")
    item = {**body.model_dump(), "id": uuid4().hex, "filing_date": str(body.filing_date or ""), "hearing_date": str(body.hearing_date or ""), "created_by": identity["username"]}
    rows.append(item); data["litigation_courts"] = rows
    await _save_ipr_litigation_data(record, data, identity, db, "新增知识产权诉讼法院信息", item["court_name"])
    return {**item, "conflict_review": (record.data or {}).get("conflict_review")}


@router.put(f"{settings.api_prefix}/ipr/lawsuit/cases/{{case_id}}/courts/{{court_id}}")
async def update_ipr_litigation_court(case_id: int, court_id: str, body: IprLitigationCourtInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _ipr_litigation_rows, _save_ipr_litigation_data,
    )
    from app.core.permissions import (
        _ensure_ipr_litigation_case_write,
    )
    record = await _ensure_ipr_litigation_case_write(case_id, identity, db)
    data = dict(record.data or {}); rows = _ipr_litigation_rows(data, "litigation_courts")
    item = next((row for row in rows if row.get("id") == court_id), None)
    if not item: raise HTTPException(status_code=404, detail="诉讼法院信息不存在")
    item.update({**body.model_dump(), "id": court_id, "filing_date": str(body.filing_date or ""), "hearing_date": str(body.hearing_date or ""), "updated_by": identity["username"]})
    data["litigation_courts"] = rows
    await _save_ipr_litigation_data(record, data, identity, db, "修改知识产权诉讼法院信息", item["court_name"])
    return {**item, "conflict_review": (record.data or {}).get("conflict_review")}


@router.delete(f"{settings.api_prefix}/ipr/lawsuit/cases/{{case_id}}/courts/{{court_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ipr_litigation_court(case_id: int, court_id: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _ipr_litigation_rows, _save_ipr_litigation_data,
    )
    from app.core.permissions import (
        _ensure_ipr_litigation_case_write,
    )
    record = await _ensure_ipr_litigation_case_write(case_id, identity, db)
    data = dict(record.data or {}); rows = _ipr_litigation_rows(data, "litigation_courts")
    remaining = [row for row in rows if row.get("id") != court_id]
    if len(remaining) == len(rows): raise HTTPException(status_code=404, detail="诉讼法院信息不存在")
    data["litigation_courts"] = remaining
    await _save_ipr_litigation_data(record, data, identity, db, "删除知识产权诉讼法院信息")


@router.get(f"{settings.api_prefix}/ipr/lawsuit/cases/{{case_id}}/parties")
async def list_ipr_litigation_parties(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _ipr_litigation_rows,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    if (record.data or {}).get("case_category", "non_litigation") != "litigation": raise HTTPException(status_code=422, detail="当前知识产权案件不是诉讼案件")
    rows = _ipr_litigation_rows(record.data or {}, "litigation_parties")
    return {"items": rows, "total": len(rows)}


@router.post(f"{settings.api_prefix}/ipr/lawsuit/cases/{{case_id}}/parties", status_code=status.HTTP_201_CREATED)
async def create_ipr_litigation_party(case_id: int, body: IprLitigationPartyInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _ipr_litigation_rows, _save_ipr_litigation_data,
    )
    from app.core.permissions import (
        _ensure_ipr_litigation_case_write,
    )
    record = await _ensure_ipr_litigation_case_write(case_id, identity, db)
    data = dict(record.data or {}); rows = _ipr_litigation_rows(data, "litigation_parties")
    item = {**body.model_dump(), "id": uuid4().hex, "created_by": identity["username"]}; rows.append(item); data["litigation_parties"] = rows
    await _save_ipr_litigation_data(record, data, identity, db, "新增知识产权诉讼当事人", f"{item['party_type']}：{item['name']}")
    return {**item, "conflict_review": (record.data or {}).get("conflict_review")}


@router.put(f"{settings.api_prefix}/ipr/lawsuit/cases/{{case_id}}/parties/{{party_id}}")
async def update_ipr_litigation_party(case_id: int, party_id: str, body: IprLitigationPartyInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _ipr_litigation_rows, _save_ipr_litigation_data,
    )
    from app.core.permissions import (
        _ensure_ipr_litigation_case_write,
    )
    record = await _ensure_ipr_litigation_case_write(case_id, identity, db)
    data = dict(record.data or {}); rows = _ipr_litigation_rows(data, "litigation_parties"); item = next((row for row in rows if row.get("id") == party_id), None)
    if not item: raise HTTPException(status_code=404, detail="诉讼当事人不存在")
    item.update({**body.model_dump(), "id": party_id, "updated_by": identity["username"]}); data["litigation_parties"] = rows
    await _save_ipr_litigation_data(record, data, identity, db, "修改知识产权诉讼当事人", f"{item['party_type']}：{item['name']}")
    return {**item, "conflict_review": (record.data or {}).get("conflict_review")}


@router.delete(f"{settings.api_prefix}/ipr/lawsuit/cases/{{case_id}}/parties/{{party_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ipr_litigation_party(case_id: int, party_id: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _ipr_litigation_rows, _save_ipr_litigation_data,
    )
    from app.core.permissions import (
        _ensure_ipr_litigation_case_write,
    )
    record = await _ensure_ipr_litigation_case_write(case_id, identity, db)
    data = dict(record.data or {}); rows = _ipr_litigation_rows(data, "litigation_parties"); remaining = [row for row in rows if row.get("id") != party_id]
    if len(remaining) == len(rows): raise HTTPException(status_code=404, detail="诉讼当事人不存在")
    data["litigation_parties"] = remaining
    await _save_ipr_litigation_data(record, data, identity, db, "删除知识产权诉讼当事人")


@router.post(f"{settings.api_prefix}/ipr/cases", status_code=status.HTTP_201_CREATED)
async def create_ipr_case(body: IprCaseCreateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _next_ipr_case_serial,
    )
    from app.core.permissions import (
        _record_scope_conditions, _require_record_module_menu,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    await _require_record_module_menu("ipr_case", identity, db, action="新建")
    case_kind = body.case_kind.strip()
    if case_kind not in IPR_CASE_KINDS: raise HTTPException(status_code=422, detail="知识产权案件类型仅支持专利或商标")
    customer = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "customer", BusinessRecord.title == body.customer.strip(), *(await _record_scope_conditions(identity, db))))
    if not customer: raise HTTPException(status_code=422, detail="客户不存在或当前账号无权选择")
    serial_no = await _next_ipr_case_serial(case_kind, db)
    data = {
        "case_kind": case_kind, "case_category": body.case_category,
        "application_no": body.application_no.strip(), "application_type": body.application_type.strip(),
        "applicant": body.applicant.strip(), "case_manager": (body.case_manager or identity["username"]).strip(),
        "application_date": str(body.application_date) if body.application_date else "", "deadline": str(body.deadline) if body.deadline else "",
        "annual_fee_year": body.annual_fee_year, "annual_fee_monitoring": False, "rate": body.rate, "created_from": "ipr_case_center",
    }
    if body.case_category == "litigation":
        data.update({
            "court_case_no": body.court_case_no.strip(), "court_name": body.court_name.strip(),
            "judge": body.judge.strip(), "clerk": body.clerk.strip(),
            "plaintiff": body.plaintiff.strip(), "defendant": body.defendant.strip(),
            "third_parties": body.third_parties.strip(), "litigation_courts": [], "litigation_parties": [],
        })
    record = BusinessRecord(module="ipr_case", serial_no=serial_no, title=body.title.strip(), customer=customer.title, status="草稿", owner=identity["username"], department=customer.department, description=body.description.strip(), data=data)
    db.add(record); await db.flush()
    db.add(IprCaseCustomer(case_record_id=record.id, customer_record_id=customer.id, is_primary=True, created_by=identity["username"]))
    db.add(WorkflowEvent(record_id=record.id, action="新建知识产权案件草稿", to_status=record.status, operator=identity["username"], comment=f"{case_kind}{'诉讼' if body.case_category == 'litigation' else '非诉讼'}案件"))
    await assess_conflict_review(record, identity, db, trigger="case_save")
    await db.commit(); await db.refresh(record)
    return _record_dict(record, await _allowed_field_keys(identity, db))


@router.post(f"{settings.api_prefix}/ipr/cases/batch-create", status_code=status.HTTP_201_CREATED)
async def batch_create_ipr_cases(body: IprCaseBatchCreateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Create valid legacy MultiCreate rows in one transaction and report invalid rows.

    Invalid input rows deliberately never become business records.  When at least
    one row is valid, all valid rows, their customer relations, batch metadata and
    audit events commit together; a database error rolls that whole valid subset
    back.
    """
    from app.core.formatters import (
        _parse_ipr_batch_date,
    )
    from app.core.ipr import (
        _next_ipr_case_serial,
    )
    from app.core.permissions import (
        _record_scope_conditions, _require_record_module_menu,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )

    await _require_record_module_menu("ipr_case", identity, db, action="新建")
    case_kind = body.case_kind.strip()
    if case_kind not in IPR_CASE_KINDS:
        raise HTTPException(status_code=422, detail="知识产权案件类型仅支持专利或商标")
    customer = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == "customer",
        BusinessRecord.title == body.customer.strip(),
        *(await _record_scope_conditions(identity, db)),
    ))
    if not customer:
        raise HTTPException(status_code=422, detail="客户不存在或当前账号无权选择")

    valid_rows: list[tuple[int, IprCaseBatchCreateRow, date, date]] = []
    errors: list[dict] = []
    for row_no, row in enumerate(body.rows, start=1):
        row_errors: dict[str, str] = {}
        case_type = row.case_type.strip()
        case_phase = row.case_phase.strip()
        register_date, register_error = _parse_ipr_batch_date(row.case_register_date, "立案日期")
        deadline, deadline_error = _parse_ipr_batch_date(row.deadline, "处理期限")
        if not case_type:
            row_errors["case_type"] = "案件类型不能为空"
        if not case_phase:
            row_errors["case_phase"] = "案件阶段不能为空"
        if register_error:
            row_errors["case_register_date"] = register_error
        if deadline_error:
            row_errors["deadline"] = deadline_error
        if register_date and deadline and deadline < register_date:
            row_errors["deadline"] = "处理期限不能早于立案日期"
        if row_errors:
            errors.append({"row_no": row_no, "errors": row_errors, "message": "；".join(row_errors.values())})
            continue
        valid_rows.append((row_no, row, register_date, deadline))

    if not valid_rows:
        raise HTTPException(status_code=422, detail={"message": "没有可创建的有效案件行", "errors": errors})

    batch_no = f"IPR-BATCH-{datetime.now():%Y%m%d%H%M%S}-{uuid4().hex[:6].upper()}"
    batch = IprCaseBatch(
        batch_no=batch_no,
        customer_record_id=customer.id,
        case_kind=case_kind,
        total_count=len(body.rows),
        created_count=len(valid_rows),
        created_by=identity["username"],
        department=customer.department,
    )
    created: list[BusinessRecord] = []
    pending_reviews: list[dict] = []
    try:
        db.add(batch)
        await db.flush()
        for row_no, row, register_date, deadline in valid_rows:
            serial_no = await _next_ipr_case_serial(case_kind, db)
            title = row.title.strip() or f"{row.case_type.strip()}案件"
            row_data = {
                "case_kind": case_kind,
                "case_type": row.case_type.strip(),
                "case_phase": row.case_phase.strip(),
                "case_register_date": str(register_date),
                "application_date": str(register_date),
                "deadline": str(deadline),
                "application_no": row.application_no.strip(),
                "application_type": row.application_type.strip(),
                "applicant": row.applicant.strip(),
                "case_manager": identity["username"],
                "case_officer": identity["username"],
                "case_officer_name": identity.get("display_name") or identity["username"],
                "case_origin_people": identity["username"],
                "case_origin_people_name": identity.get("display_name") or identity["username"],
                "annual_fee_monitoring": False,
                "created_from": "ipr_batch_create",
                "batch_id": batch.id,
                "batch_no": batch_no,
                "batch_row_no": row_no,
            }
            record = BusinessRecord(
                module="ipr_case",
                serial_no=serial_no,
                title=title,
                customer=customer.title,
                status="草稿",
                owner=identity["username"],
                department=customer.department,
                description=row.description.strip(),
                data=row_data,
            )
            db.add(record)
            await db.flush()
            db.add(IprCaseCustomer(case_record_id=record.id, customer_record_id=customer.id, is_primary=True, created_by=identity["username"]))
            db.add(IprCaseBatchItem(
                batch_id=batch.id,
                row_no=row_no,
                case_record_id=record.id,
                input_data={
                    "case_type": row.case_type.strip(),
                    "case_phase": row.case_phase.strip(),
                    "case_register_date": str(register_date),
                    "deadline": str(deadline),
                    "title": row.title.strip(),
                },
            ))
            db.add(WorkflowEvent(
                record_id=record.id,
                action="批量创建知识产权案件",
                to_status=record.status,
                operator=identity["username"],
                comment=f"批次 {batch_no} 第 {row_no} 行",
            ))
            created.append(record)
        for record in created:
            summary = await assess_conflict_review(record, identity, db, trigger="case_save")
            if summary and summary["blocking"]:
                pending_reviews.append({"case_id": record.id, "case_no": record.serial_no, "conflict_review": summary})
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    allowed_fields = await _allowed_field_keys(identity, db)
    return {
        "batch_no": batch_no,
        "created_count": len(created),
        "invalid_count": len(errors),
        "created": [_record_dict(record, allowed_fields) for record in created],
        "errors": errors,
        "pending_reviews": pending_reviews,
    }


@router.get(f"{settings.api_prefix}/ipr/cases/{{case_id}}/reboot-preview")
async def preview_ipr_case_reboot(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _next_ipr_reboot_serial,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_record_module_menu, _require_record_owner_or_manager,
    )
    await _require_record_module_menu("ipr_case", identity, db, action="新建")
    source = await _ensure_record_module(case_id, "ipr_case", identity, db)
    await _require_record_owner_or_manager(source, identity, db)
    root_serial, next_serial_no = await _next_ipr_reboot_serial(source, db)
    return {
        "source_case_id": source.id,
        "source_case_no": source.serial_no,
        "source_title": source.title,
        "source_status": source.status,
        "reboot_root_serial": root_serial,
        "next_serial_no": next_serial_no,
    }


@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/reboot", status_code=status.HTTP_201_CREATED)
async def reboot_ipr_case(case_id: int, body: IprCaseRebootInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Create a separately-tracked resubmission without mutating the source case."""
    from app.core.ipr import (
        _next_ipr_reboot_serial,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_record_module_menu, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )

    await _require_record_module_menu("ipr_case", identity, db, action="新建")
    source = await _ensure_record_module(case_id, "ipr_case", identity, db)
    await _require_record_owner_or_manager(source, identity, db)
    if source.status not in {"草稿", "已驳回", "在办", "已结案"}:
        raise HTTPException(status_code=409, detail="当前知识产权案件状态不能重提")

    root_serial, reboot_serial_no = await _next_ipr_reboot_serial(source, db)
    source_data = dict(source.data or {})
    new_data = json.loads(json.dumps(source_data, ensure_ascii=False, default=str))
    for key in {"closed_at", "closed_by", "reopened_at", "reopened_by", "reboot_case_ids", "reboot_case_nos", "last_rebooted_at", "last_rebooted_by"}:
        new_data.pop(key, None)
    new_data.pop("conflict_review", None)
    new_data.update({
        "reboot_root_serial": root_serial,
        "reboot_source_case_id": source.id,
        "reboot_source_case_no": source.serial_no,
        "reboot_reason": body.reason.strip(),
        "rebooted_at": datetime.now().isoformat(timespec="seconds"),
        "rebooted_by": identity["username"],
        "created_from": "ipr_case_reboot",
    })
    reboot_case = BusinessRecord(
        module="ipr_case",
        serial_no=reboot_serial_no,
        title=source.title,
        customer=source.customer,
        status="草稿",
        owner=identity["username"],
        department=source.department,
        description=source.description,
        data=new_data,
    )
    try:
        db.add(reboot_case)
        await db.flush()
        source_customers = list((await db.scalars(select(IprCaseCustomer).where(IprCaseCustomer.case_record_id == source.id))).all())
        for relation in source_customers:
            db.add(IprCaseCustomer(
                case_record_id=reboot_case.id,
                customer_record_id=relation.customer_record_id,
                is_primary=relation.is_primary,
                created_by=identity["username"],
            ))
        source_law_firms = list((await db.scalars(select(IprCaseLawFirm).where(IprCaseLawFirm.case_record_id == source.id))).all())
        for relation in source_law_firms:
            db.add(IprCaseLawFirm(case_record_id=reboot_case.id, law_firm_id=relation.law_firm_id, created_by=identity["username"]))
        source_contacts = list((await db.scalars(select(IprCaseCustomerContact).where(IprCaseCustomerContact.case_record_id == source.id))).all())
        for relation in source_contacts:
            db.add(IprCaseCustomerContact(
                case_record_id=reboot_case.id,
                customer_record_id=relation.customer_record_id,
                contact_id=relation.contact_id,
                contact_role=relation.contact_role,
                created_by=identity["username"],
            ))
        source_data["reboot_case_ids"] = [*list(source_data.get("reboot_case_ids") or []), reboot_case.id]
        source_data["reboot_case_nos"] = [*list(source_data.get("reboot_case_nos") or []), reboot_case.serial_no]
        source_data["last_rebooted_at"] = datetime.now().isoformat(timespec="seconds")
        source_data["last_rebooted_by"] = identity["username"]
        source.data = source_data
        db.add(IprCaseRebootLink(
            source_case_id=source.id,
            reboot_case_id=reboot_case.id,
            reason=body.reason.strip(),
            created_by=identity["username"],
        ))
        db.add(WorkflowEvent(
            record_id=source.id,
            action="知识产权案件重提",
            from_status=source.status,
            to_status=source.status,
            operator=identity["username"],
            comment=f"生成重提案件 {reboot_case.serial_no}" + (f"；{body.reason.strip()}" if body.reason.strip() else ""),
        ))
        db.add(WorkflowEvent(
            record_id=reboot_case.id,
            action="重提知识产权案件创建",
            to_status=reboot_case.status,
            operator=identity["username"],
            comment=f"原案件 {source.serial_no}" + (f"；{body.reason.strip()}" if body.reason.strip() else ""),
        ))
        await assess_conflict_review(reboot_case, identity, db, trigger="case_save")
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    await db.refresh(reboot_case)
    return _record_dict(reboot_case, await _allowed_field_keys(identity, db))


@router.patch(f"{settings.api_prefix}/ipr/cases/{{case_id}}")
async def update_ipr_case(case_id: int, body: IprCaseUpdateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _ipr_litigation_rows,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    if (record.data or {}).get("legacy_ipr_case_id", (record.data or {}).get("legacy_case_id")) not in (None, ""):
        raise HTTPException(status_code=409, detail="Historical IPR cases are read-only")
    await _require_record_owner_or_manager(record, identity, db)
    if record.status not in {"草稿", "已驳回", "在办"}:
        raise HTTPException(status_code=409, detail="仅草稿、已驳回或在办的知识产权案件可以修改")
    before = record.status
    previous_phase = (record.data or {}).get("case_phase")
    data = dict(record.data or {})
    values = body.model_dump(exclude_unset=True)
    litigation_keys = {"court_case_no", "court_name", "judge", "clerk", "plaintiff", "defendant", "third_parties"}
    current_category = data.get("case_category", "non_litigation")
    next_category = values.pop("case_category", current_category)
    if next_category not in IPR_CASE_CATEGORIES:
        raise HTTPException(status_code=422, detail="知识产权案件诉讼类型无效")
    if litigation_keys.intersection(values) and next_category != "litigation":
        raise HTTPException(status_code=422, detail="诉讼专有字段只能用于诉讼知识产权案件")
    if current_category == "litigation" and next_category == "non_litigation":
        has_litigation_data = bool(_ipr_litigation_rows(data, "litigation_courts") or _ipr_litigation_rows(data, "litigation_parties") or any(str(data.get(key) or "").strip() for key in litigation_keys))
        has_litigation_fee = await db.scalar(select(BusinessRecord.id).where(
            BusinessRecord.module == "finance", BusinessRecord.data["case_id"].as_string() == str(record.id),
        ))
        if has_litigation_data or has_litigation_fee:
            raise HTTPException(status_code=409, detail="诉讼案件已有法院、当事人或费用记录，不能改为非诉讼案件")
    data["case_category"] = next_category
    for key in {"application_no", "application_type", "applicant", "case_manager", "case_phase", "case_source", "agent", "writer", "submitter", "inventor"}:
        if key in values:
            data[key] = str(values.pop(key) or "").strip()
    for key in {"application_date", "deadline", "acceptance_date", "source_date"}:
        if key in values:
            data[key] = str(values.pop(key) or "")
    for key in {"annual_fee_year", "rate"}:
        if key in values:
            data[key] = values.pop(key)
    for key in litigation_keys:
        if key in values:
            data[key] = str(values.pop(key) or "").strip()
    if "contract_record_id" in values:
        contract_id = values.pop("contract_record_id")
        if contract_id is not None:
            contract = await _ensure_record_module(contract_id, "contract", identity, db)
            data["contract_record_id"] = contract.id
            data["contract_no"] = contract.serial_no
        else:
            data.pop("contract_record_id", None)
            data.pop("contract_no", None)
    if "title" in values:
        record.title = str(values.pop("title")).strip()
    if "description" in values:
        record.description = str(values.pop("description") or "").strip()
    record.data = data
    await assess_conflict_review(record, identity, db, trigger="case_save")
    gate = await get_conflict_review_gate(record, db, action="修改知识产权案件阶段")
    if gate["blocking"] and "case_phase" in body.model_fields_set:
        restored_data = dict(record.data or {})
        if previous_phase is None:
            restored_data.pop("case_phase", None)
        else:
            restored_data["case_phase"] = previous_phase
        record.data = restored_data
    db.add(WorkflowEvent(record_id=record.id, action="修改知识产权案件基本信息", from_status=before, to_status=record.status, operator=identity["username"], comment="更新案件基本信息"))
    await db.commit(); await db.refresh(record)
    return _record_dict(record, await _allowed_field_keys(identity, db))


@router.put(f"{settings.api_prefix}/ipr/cases/{{case_id}}/links")
@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/links")
async def update_ipr_case_links(case_id: int, body: IprCaseCrossModuleLinkInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _ensure_record_visible, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    if (record.data or {}).get("legacy_ipr_case_id", (record.data or {}).get("legacy_case_id")) not in (None, ""):
        raise HTTPException(status_code=409, detail="Historical IPR cases are read-only")
    await _require_record_owner_or_manager(record, identity, db)
    if record.status not in {"草稿", "已驳回", "在办"}:
        raise HTTPException(status_code=409, detail="当前案件状态不能维护跨模块关联")
    data = dict(record.data or {})
    changed: list[str] = []
    if body.contract_record_id is not None:
        contract = await _ensure_record_module(body.contract_record_id, "contract", identity, db)
        data["contract_record_id"] = contract.id
        data["contract_no"] = contract.serial_no
        changed.append(f"合同：{contract.serial_no}")
    elif "contract_record_id" in body.model_fields_set:
        data.pop("contract_record_id", None)
        data.pop("contract_no", None)
        changed.append("合同：无")
    if body.payment_record_id is not None:
        payment = await _ensure_record_visible(body.payment_record_id, identity, db)
        if payment.module not in {"finance", "contract_payment", "payment"}:
            raise HTTPException(status_code=422, detail="关联记录不是付款或费用记录")
        data["payment_record_id"] = payment.id
        data["payment_no"] = payment.serial_no
        changed.append(f"付款：{payment.serial_no}")
    elif "payment_record_id" in body.model_fields_set:
        data.pop("payment_record_id", None)
        data.pop("payment_no", None)
        changed.append("付款：无")
    record.data = data
    db.add(WorkflowEvent(record_id=record.id, action="关联知识产权案件跨模块记录", from_status=record.status, to_status=record.status, operator=identity["username"], comment="；".join(changed) or "更新跨模块关联"))
    await assess_conflict_review(record, identity, db, trigger="case_save")
    await db.commit(); await db.refresh(record)
    return _record_dict(record, await _allowed_field_keys(identity, db))


@router.get(f"{settings.api_prefix}/ipr/cases/{{case_id}}/tasks")
async def list_ipr_case_tasks(
    case_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.formatters import (
        _task_display_dicts,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _record_dict,
    )
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    conditions = [
        BusinessRecord.module == "task",
        or_(
            BusinessRecord.data["case_record_id"].as_integer() == record.id,
            BusinessRecord.data["case_id"].as_integer() == record.id,
            BusinessRecord.data.cast(String).contains(f'"{record.serial_no}"'),
        ),
    ]
    if identity.get("role") != "admin":
        username_token = f'"{identity["username"]}"'
        conditions.append(or_(
            BusinessRecord.owner == identity["username"],
            BusinessRecord.data["initiator"].as_string() == identity["username"],
            BusinessRecord.data["collaborators"].as_string().contains(username_token),
        ))
    total = int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(*conditions)) or 0)
    rows = list((await db.scalars(
        select(BusinessRecord).where(*conditions)
        .order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).all())
    return {
        "case": _record_dict(record), "items": await _task_display_dicts(rows, db),
        "total": total, "page": page, "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
    }


@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/tasks", status_code=status.HTTP_201_CREATED)
async def create_ipr_case_task(
    case_id: int,
    body: TaskInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Create a real task bound to the IPR case selected by the route."""
    from app.core.task_commands import create_task_record
    from app.core.tasks import _task_dict
    if body.case_record_id is not None and body.case_record_id != case_id:
        raise HTTPException(status_code=422, detail="请求中的案件与当前知识产权案件不一致")
    normalized = body.model_copy(update={
        "source": "案件任务",
        "case_record_id": case_id,
        "case_module": "ipr_case",
        "case_no": "",
        "case_nos": [],
    })
    task = await create_task_record(normalized, identity, db)
    await db.commit()
    await db.refresh(task)
    return _task_dict(task)


@router.get(f"{settings.api_prefix}/ipr/cases/{{case_id}}/customers")
async def list_ipr_case_customers(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Legacy CaseCustomer list equivalent; includes an explicit primary-customer fallback for historical records."""
    from app.core.ipr import (
        _ipr_case_customer_dict, _ipr_case_customer_links,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_scope_conditions,
    )
    case_record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    links = await _ipr_case_customer_links(case_record, identity, db)
    customer_ids = [item.customer_record_id for item in links]
    customers = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(customer_ids), BusinessRecord.module == "customer", *(await _record_scope_conditions(identity, db)),
    ))).all()) if customer_ids else []
    by_id = {item.id: item for item in customers}
    items = [_ipr_case_customer_dict(link, by_id[link.customer_record_id]) for link in links if link.customer_record_id in by_id]
    return {"items": items, "total": len(items), "primary_customer_id": next((item["customer_id"] for item in items if item["is_primary"]), None)}


@router.get(f"{settings.api_prefix}/ipr/cases/{{case_id}}/customers/candidates")
async def list_ipr_case_customer_candidates(case_id: int, keyword: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Legacy CaseCustomerSelected equivalent: visible non-recycled customers and selected ids."""
    from app.core.ipr import (
        _ipr_case_customer_links,
    )
    from app.core.permissions import (
        _ensure_active_ipr_case_write, _record_scope_conditions,
    )
    case_record = await _ensure_active_ipr_case_write(case_id, identity, db)
    statement = select(BusinessRecord).where(
        BusinessRecord.module == "customer", BusinessRecord.status.not_in(["已回收"]), *(await _record_scope_conditions(identity, db)),
    ).order_by(BusinessRecord.title, BusinessRecord.id)
    if keyword.strip():
        like = f"%{keyword.strip()}%"
        statement = statement.where(or_(BusinessRecord.serial_no.ilike(like), BusinessRecord.title.ilike(like)))
    customers = list((await db.scalars(statement.limit(200))).all())
    links = await _ipr_case_customer_links(case_record, identity, db)
    selected_ids = [item.customer_record_id for item in links]
    primary_customer_id = next((item.customer_record_id for item in links if item.is_primary), None)
    return {"items": [{"id": item.id, "customer_no": item.serial_no, "name": item.title, "status": item.status, "selected": item.id in selected_ids} for item in customers], "selected_ids": selected_ids, "primary_customer_id": primary_customer_id}


@router.put(f"{settings.api_prefix}/ipr/cases/{{case_id}}/customers")
async def replace_ipr_case_customers(case_id: int, body: IprCaseCustomerReplaceInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Atomically replace an IPR case's customers and keep its shared primary customer field in sync."""
    from app.core.permissions import (
        _ensure_active_ipr_case_write, _record_scope_conditions,
    )
    case_record = await _ensure_active_ipr_case_write(case_id, identity, db)
    selected_ids = list(dict.fromkeys(body.customer_ids))
    if body.primary_customer_id not in selected_ids or any(item <= 0 for item in selected_ids):
        raise HTTPException(status_code=422, detail="请从已选客户中指定一个主客户")
    customers = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(selected_ids), BusinessRecord.module == "customer", BusinessRecord.status.not_in(["已回收"]), *(await _record_scope_conditions(identity, db)),
    ))).all())
    if len(customers) != len(selected_ids):
        raise HTTPException(status_code=422, detail="所选客户不存在、已回收或无权访问")
    by_id = {item.id: item for item in customers}
    existing = list((await db.scalars(select(IprCaseCustomer).where(IprCaseCustomer.case_record_id == case_record.id))).all())
    before_ids = {item.customer_record_id for item in existing}; after_ids = set(selected_ids)
    for item in existing:
        if item.customer_record_id not in after_ids:
            await db.delete(item)
    for customer_id in selected_ids:
        link = next((item for item in existing if item.customer_record_id == customer_id), None)
        if link:
            link.is_primary = customer_id == body.primary_customer_id
        else:
            db.add(IprCaseCustomer(case_record_id=case_record.id, customer_record_id=customer_id, is_primary=customer_id == body.primary_customer_id, created_by=identity["username"]))
    primary = by_id[body.primary_customer_id]
    case_record.customer = primary.title
    case_record.department = primary.department or case_record.department
    data = dict(case_record.data or {}); data["primary_customer_id"] = primary.id; case_record.data = data
    db.add(WorkflowEvent(record_id=case_record.id, action="维护知识产权案件客户", from_status=case_record.status, to_status=case_record.status, operator=identity["username"], comment=f"主客户：{primary.title}；客户数：{len(selected_ids)}；新增：{len(after_ids - before_ids)}；移除：{len(before_ids - after_ids)}"))
    await assess_conflict_review(case_record, identity, db, trigger="case_save")
    await db.commit()
    return {**await list_ipr_case_customers(case_id, identity, db), "conflict_review": (case_record.data or {}).get("conflict_review")}


@router.get(f"{settings.api_prefix}/ipr/cases/{{case_id}}/customers/{{customer_id}}/contact-candidates")
async def list_ipr_case_customer_contact_candidates(case_id: int, customer_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Legacy CaseCustomerContactsSelected equivalent with the two selectable contact roles."""
    from app.core.ipr import (
        _ipr_case_contact_candidates,
    )
    from app.core.permissions import (
        _ensure_active_ipr_case_write,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    case_record = await _ensure_active_ipr_case_write(case_id, identity, db)
    customer, contacts = await _ipr_case_contact_candidates(case_record, customer_id, identity, db)
    links = list((await db.scalars(select(IprCaseCustomerContact).where(
        IprCaseCustomerContact.case_record_id == case_record.id, IprCaseCustomerContact.customer_record_id == customer.id,
    ))).all())
    document_ids = {item.contact_id for item in links if item.contact_role == "document"}
    technology_ids = {item.contact_id for item in links if item.contact_role == "technology"}
    return {"customer": _record_dict(customer, await _allowed_field_keys(identity, db)), "items": contacts, "document_contact_ids": sorted(document_ids), "technology_contact_ids": sorted(technology_ids)}


@router.put(f"{settings.api_prefix}/ipr/cases/{{case_id}}/customer-contacts")
async def replace_ipr_case_customer_contacts(case_id: int, body: IprCaseCustomerContactReplaceInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Atomically save legacy document-contact and technology-contact selections for one linked customer."""
    from app.core.ipr import (
        _ipr_case_contact_candidates,
    )
    from app.core.permissions import (
        _ensure_active_ipr_case_write,
    )
    case_record = await _ensure_active_ipr_case_write(case_id, identity, db)
    customer, contacts = await _ipr_case_contact_candidates(case_record, body.customer_id, identity, db)
    valid_ids = {str(item["id"]) for item in contacts}
    document_ids = set(dict.fromkeys(item.strip() for item in body.document_contact_ids if item.strip()))
    technology_ids = set(dict.fromkeys(item.strip() for item in body.technology_contact_ids if item.strip()))
    if not document_ids.issubset(valid_ids) or not technology_ids.issubset(valid_ids):
        raise HTTPException(status_code=422, detail="所选联系人不存在、已失效或不属于该客户")
    existing = list((await db.scalars(select(IprCaseCustomerContact).where(
        IprCaseCustomerContact.case_record_id == case_record.id, IprCaseCustomerContact.customer_record_id == customer.id,
    ))).all())
    expected = {(contact_id, "document") for contact_id in document_ids} | {(contact_id, "technology") for contact_id in technology_ids}
    current = {(item.contact_id, item.contact_role) for item in existing}
    for item in existing:
        if (item.contact_id, item.contact_role) not in expected:
            await db.delete(item)
    for contact_id, role in expected - current:
        db.add(IprCaseCustomerContact(case_record_id=case_record.id, customer_record_id=customer.id, contact_id=contact_id, contact_role=role, created_by=identity["username"]))
    db.add(WorkflowEvent(record_id=case_record.id, action="维护知识产权案件联系人", from_status=case_record.status, to_status=case_record.status, operator=identity["username"], comment=f"客户：{customer.title}；文书联系人 {len(document_ids)} 人；技术联系人 {len(technology_ids)} 人"))
    await db.commit()
    return await list_ipr_case_customer_contact_candidates(case_id, customer.id, identity, db)


@router.get(f"{settings.api_prefix}/ipr/cases/{{case_id}}/customer-contacts")
async def list_ipr_case_customer_contacts(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """A read-only flattened case-contact view for the old CaseContactsList tab."""
    from app.core.crm import (
        _customer_contact_dict,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_scope_conditions,
    )
    case_record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    links = list((await db.scalars(select(IprCaseCustomerContact).where(IprCaseCustomerContact.case_record_id == case_record.id).order_by(IprCaseCustomerContact.customer_record_id, IprCaseCustomerContact.id))).all())
    customer_ids = list({item.customer_record_id for item in links})
    customers = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(customer_ids), *(await _record_scope_conditions(identity, db))))).all()) if customer_ids else []
    result: list[dict] = []
    for customer in customers:
        contacts = {str(item.get("id")): item for item in list((customer.data or {}).get("contacts", []))}
        for link in [item for item in links if item.customer_record_id == customer.id]:
            contact = contacts.get(link.contact_id)
            if contact:
                projected = _customer_contact_dict(contact)
                result.append({"id": link.id, "customer_id": customer.id, "customer_name": customer.title, "contact_id": link.contact_id, "contact_role": link.contact_role, "name": projected.get("name", ""), "phone": projected.get("phone", ""), "email": projected.get("email", ""), "position": projected.get("position", ""), "is_valid": bool(projected.get("is_valid", True)), "is_received_email": bool(projected.get("is_received_email", True)), "is_contacted": bool(projected.get("is_contacted", True)), "is_people_base": bool(projected.get("is_people_base", True))})
    return {"items": result, "total": len(result)}


@router.get(f"{settings.api_prefix}/ipr/cases/{{case_id}}/law-firms")
async def list_ipr_case_law_firms(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Return the legacy CaseLawFirmList equivalent for one visible IPR case."""
    from app.core.ipr import (
        _ipr_law_firm_dict,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    case_record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    links = list((await db.scalars(select(IprCaseLawFirm).where(IprCaseLawFirm.case_record_id == case_record.id).order_by(IprCaseLawFirm.id))).all())
    firm_ids = [item.law_firm_id for item in links]
    firms = list((await db.scalars(select(LawFirm).where(LawFirm.id.in_(firm_ids)))).all()) if firm_ids else []
    by_id = {item.id: item for item in firms}
    return {"items": [_ipr_law_firm_dict(item, by_id[item.law_firm_id]) for item in links if item.law_firm_id in by_id], "total": len(links)}


@router.get(f"{settings.api_prefix}/ipr/cases/{{case_id}}/law-firms/candidates")
async def list_ipr_case_law_firm_candidates(case_id: int, keyword: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Legacy CaseLawFirmListSelected equivalent: active master firms plus selected ids."""
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    case_record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    await _require_record_owner_or_manager(case_record, identity, db)
    statement = select(LawFirm).where(LawFirm.is_active.is_(True)).order_by(LawFirm.name, LawFirm.id)
    if keyword.strip():
        like = f"%{keyword.strip()}%"
        statement = statement.where(or_(LawFirm.code.ilike(like), LawFirm.name.ilike(like)))
    firms = list((await db.scalars(statement.limit(200))).all())
    selected_ids = list((await db.scalars(select(IprCaseLawFirm.law_firm_id).where(IprCaseLawFirm.case_record_id == case_record.id))).all())
    return {"items": [{"id": item.id, "code": item.code, "name": item.name, "phone": item.phone, "email": item.email, "selected": item.id in selected_ids} for item in firms], "selected_ids": selected_ids}


@router.put(f"{settings.api_prefix}/ipr/cases/{{case_id}}/law-firms")
async def replace_ipr_case_law_firms(case_id: int, body: IprCaseLawFirmReplaceInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Atomically replace collaboration-law-firm selections; it is never a generic record write."""
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    case_record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    await _require_record_owner_or_manager(case_record, identity, db)
    if case_record.status not in {"草稿", "已驳回", "在办"}:
        raise HTTPException(status_code=409, detail="当前案件状态不能维护协作律所")
    selected_ids = list(dict.fromkeys(body.law_firm_ids))
    if any(item <= 0 for item in selected_ids):
        raise HTTPException(status_code=422, detail="协作律所编号无效")
    firms = list((await db.scalars(select(LawFirm).where(LawFirm.id.in_(selected_ids), LawFirm.is_active.is_(True)))).all()) if selected_ids else []
    if len(firms) != len(selected_ids):
        raise HTTPException(status_code=422, detail="选择的协作律所不存在或已停用")
    existing = list((await db.scalars(select(IprCaseLawFirm).where(IprCaseLawFirm.case_record_id == case_record.id))).all())
    before_ids = {item.law_firm_id for item in existing}; after_ids = set(selected_ids)
    for item in existing:
        if item.law_firm_id not in after_ids:
            await db.delete(item)
    for firm_id in selected_ids:
        if firm_id not in before_ids:
            db.add(IprCaseLawFirm(case_record_id=case_record.id, law_firm_id=firm_id, created_by=identity["username"]))
    if before_ids != after_ids:
        firm_names = {item.id: item.name for item in firms}
        db.add(WorkflowEvent(record_id=case_record.id, action="维护知识产权案件协作律所", from_status=case_record.status, to_status=case_record.status, operator=identity["username"], comment=f"新增：{'、'.join(firm_names.get(item, str(item)) for item in sorted(after_ids - before_ids)) or '无'}；移除：{'、'.join(map(str, sorted(before_ids - after_ids))) or '无'}"))
    await db.commit()
    return await list_ipr_case_law_firms(case_id, identity, db)


@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/maintenance")
async def maintain_ipr_case(case_id: int, body: IprCaseMaintenanceInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Maintain active IPR deadline, annual-fee year and rate through a dedicated audited action."""
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    await _require_record_owner_or_manager(record, identity, db)
    if record.status != "在办":
        raise HTTPException(status_code=409, detail="只有在办知识产权案件可以维护期限、年费和费率")
    values = body.model_dump(exclude_unset=True, exclude={"comment"})
    if not values:
        raise HTTPException(status_code=422, detail="请至少填写一项期限、年费年度或费率")
    data = dict(record.data or {})
    changes: list[str] = []
    if "deadline" in values:
        new_value = str(values["deadline"] or "")
        changes.append(f"办理期限：{data.get('deadline') or '—'} → {new_value or '—'}")
        data["deadline"] = new_value
    if "annual_fee_year" in values:
        new_value = values["annual_fee_year"]
        changes.append(f"年费年度：{data.get('annual_fee_year') or '—'} → {new_value or '—'}")
        data["annual_fee_year"] = new_value
    if "rate" in values:
        new_value = values["rate"]
        changes.append(f"费率：{data.get('rate') if data.get('rate') is not None else '—'} → {new_value if new_value is not None else '—'}")
        data["rate"] = new_value
    record.data = data
    db.add(WorkflowEvent(
        record_id=record.id, action="维护知识产权案件期限年费费率", from_status=record.status,
        to_status=record.status, operator=identity["username"],
        comment="；".join(changes) + (f"；{body.comment.strip()}" if body.comment.strip() else ""),
    ))
    await assess_conflict_review(record, identity, db, trigger="case_save")
    await db.commit(); await db.refresh(record)
    return _record_dict(record, await _allowed_field_keys(identity, db))


@router.post(f"{settings.api_prefix}/ipr/cases/batch-maintenance")
async def batch_maintain_ipr_cases(body: IprCaseBatchMaintenanceInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Apply the visible legacy batch-edit fields only after every target passes the same write checks."""
    from app.core.permissions import (
        _record_scope_conditions, _require_record_owner_or_manager,
    )
    case_ids = list(dict.fromkeys(body.case_ids))
    values = body.model_dump(exclude={"case_ids", "comment"}, exclude_unset=True)
    if not values or all(value is None or value == "" for value in values.values()):
        raise HTTPException(status_code=422, detail="请至少填写经办人、办理期限、首年缴费年度或减缓比例之一")
    records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(case_ids), BusinessRecord.module == "ipr_case", *(await _record_scope_conditions(identity, db)),
    ).with_for_update())).all())
    if len(records) != len(case_ids):
        raise HTTPException(status_code=404, detail="存在知识产权案件不存在或无权访问")
    by_id = {item.id: item for item in records}
    ordered = [by_id[item] for item in case_ids]
    for record in ordered:
        await _require_record_owner_or_manager(record, identity, db)
        if record.status != "在办":
            raise HTTPException(status_code=409, detail=f"案件 {record.serial_no} 不在办理中，不能批量维护")
    manager = str(values.get("case_manager") or "").strip() if "case_manager" in values else None
    if manager:
        active_user = await db.scalar(select(User).where(User.username == manager, User.is_active.is_(True)))
        if not active_user:
            raise HTTPException(status_code=422, detail="案件经办人不存在或已停用")
    updated: list[dict] = []
    for record in ordered:
        data = dict(record.data or {})
        changes: list[str] = []
        if manager is not None and manager != data.get("case_manager", ""):
            changes.append(f"经办人：{data.get('case_manager') or '—'} → {manager or '—'}")
            data["case_manager"] = manager or ""
        if "deadline" in values:
            value = str(values["deadline"] or "")
            if value != str(data.get("deadline") or ""):
                changes.append(f"办理期限：{data.get('deadline') or '—'} → {value or '—'}")
                data["deadline"] = value
        if "annual_fee_year" in values and values["annual_fee_year"] != data.get("annual_fee_year"):
            changes.append(f"首年缴费年度：{data.get('annual_fee_year') or '—'} → {values['annual_fee_year'] or '—'}")
            data["annual_fee_year"] = values["annual_fee_year"]
        if "rate" in values and values["rate"] != data.get("rate"):
            changes.append(f"减缓比例：{data.get('rate') if data.get('rate') is not None else '—'} → {values['rate'] if values['rate'] is not None else '—'}")
            data["rate"] = values["rate"]
        if changes:
            record.data = data
            db.add(WorkflowEvent(record_id=record.id, action="批量维护知识产权案件", from_status=record.status, to_status=record.status, operator=identity["username"], comment="；".join(changes) + (f"；{body.comment.strip()}" if body.comment.strip() else "")))
            await assess_conflict_review(record, identity, db, trigger="case_save")
        updated.append({"id": record.id, "serial_no": record.serial_no, "changed": bool(changes), "conflict_review": (record.data or {}).get("conflict_review")})
    await db.commit()
    return {"updated": sum(1 for item in updated if item["changed"]), "items": updated}


@router.post(f"{settings.api_prefix}/ipr/cases/annual-fee-monitoring/add")
async def add_ipr_cases_to_annual_fee_monitoring(body: IprCaseAnnualFeeMonitoringInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _set_ipr_annual_fee_monitoring,
    )
    return await _set_ipr_annual_fee_monitoring(body, True, identity, db)


@router.post(f"{settings.api_prefix}/ipr/cases/annual-fee-monitoring/remove")
async def remove_ipr_cases_from_annual_fee_monitoring(body: IprCaseAnnualFeeMonitoringInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _set_ipr_annual_fee_monitoring,
    )
    return await _set_ipr_annual_fee_monitoring(body, False, identity, db)


@router.get(f"{settings.api_prefix}/ipr/cases/{{case_id}}/logs")
async def list_ipr_case_logs(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Return legacy business logs and a read-only operation log projection from audited workflow events."""
    from app.core.formatters import (
        _person_reference_display, _user_display_map,
    )
    from app.core.ipr import (
        _ipr_case_log_dict,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    business_logs = list((await db.scalars(select(IprCaseLog).where(IprCaseLog.case_record_id == record.id).order_by(IprCaseLog.created_at.desc(), IprCaseLog.id.desc()))).all())
    operations = list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == record.id).order_by(WorkflowEvent.created_at.desc(), WorkflowEvent.id.desc()))).all())
    users_by_username = await _user_display_map({*[item.created_by for item in business_logs], *[item.operator for item in operations]}, db)
    return {
        "business_logs": [_ipr_case_log_dict(item, users_by_username) for item in business_logs],
        "operation_logs": [{"id": item.id, "action": item.action, "operator": item.operator, "operator_display_name": _person_reference_display(item.operator, users_by_username)[0], "comment": item.comment, "from_status": item.from_status, "to_status": item.to_status, "created_at": item.created_at} for item in operations],
    }


@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/logs", status_code=status.HTTP_201_CREATED)
async def create_ipr_case_log(case_id: int, body: IprCaseLogInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Create a user-authored business log without weakening the immutable workflow audit trail."""
    from app.core.ipr import (
        _ipr_case_log_dict,
    )
    from app.core.permissions import (
        _ensure_active_ipr_case_write,
    )
    record = await _ensure_active_ipr_case_write(case_id, identity, db)
    item = IprCaseLog(case_record_id=record.id, content=body.content.strip(), created_by=identity["username"])
    db.add(item); await db.flush()
    db.add(WorkflowEvent(record_id=record.id, action="新增知识产权案件业务日志", from_status=record.status, to_status=record.status, operator=identity["username"], comment=item.content[:500]))
    await db.commit(); await db.refresh(item)
    return _ipr_case_log_dict(item)


@router.delete(f"{settings.api_prefix}/ipr/cases/{{case_id}}/logs/{{log_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ipr_case_log(case_id: int, log_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Only the note author, the case manager, or an administrator can remove an authored business note."""
    from app.core.permissions import (
        _ensure_active_ipr_case_write,
    )
    record = await _ensure_active_ipr_case_write(case_id, identity, db)
    item = await db.scalar(select(IprCaseLog).where(IprCaseLog.id == log_id, IprCaseLog.case_record_id == record.id))
    if not item:
        raise HTTPException(status_code=404, detail="案件业务日志不存在")
    if item.created_by != identity["username"] and identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="只有日志创建人或管理人员可以删除业务日志")
    content = item.content
    await db.delete(item)
    db.add(WorkflowEvent(record_id=record.id, action="删除知识产权案件业务日志", from_status=record.status, to_status=record.status, operator=identity["username"], comment=content[:500]))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


from app.areas.ipr.fees import (
    router as fees_router,
    list_ipr_case_assisted_fees as list_ipr_case_assisted_fees,
    create_ipr_case_assisted_fee as create_ipr_case_assisted_fee,
    update_ipr_case_assisted_fee as update_ipr_case_assisted_fee,
    confirm_ipr_case_assisted_fee as confirm_ipr_case_assisted_fee,
    transact_ipr_case_assisted_fee as transact_ipr_case_assisted_fee,
    delete_ipr_case_assisted_fee as delete_ipr_case_assisted_fee,
    list_ipr_case_fees as list_ipr_case_fees,
    create_ipr_case_fee as create_ipr_case_fee,
    create_ipr_case_fee_invoice as create_ipr_case_fee_invoice,
    list_ipr_case_fee_payment_types as list_ipr_case_fee_payment_types,
    create_ipr_case_fee_payment_type as create_ipr_case_fee_payment_type,
    create_ipr_case_fee_payment_application as create_ipr_case_fee_payment_application,
    create_ipr_case_fee_arrival as create_ipr_case_fee_arrival,
    unlock_ipr_case_fee as unlock_ipr_case_fee,
    delete_ipr_case_fee as delete_ipr_case_fee,
)
router.include_router(fees_router)


from app.areas.ipr.reminders import (
    router as reminders_router,
    list_ipr_reminder_event_types as list_ipr_reminder_event_types,
    list_ipr_case_reminders as list_ipr_case_reminders,
    create_ipr_case_reminder as create_ipr_case_reminder,
    update_ipr_case_reminder as update_ipr_case_reminder,
    delete_ipr_case_reminder as delete_ipr_case_reminder,
    get_ipr_case_reminder_suppressions as get_ipr_case_reminder_suppressions,
    replace_ipr_case_reminder_suppressions as replace_ipr_case_reminder_suppressions,
    list_ipr_case_annual_fees as list_ipr_case_annual_fees,
    create_ipr_case_annual_fee as create_ipr_case_annual_fee,
    update_ipr_case_annual_fee as update_ipr_case_annual_fee,
    delete_ipr_case_annual_fee as delete_ipr_case_annual_fee,
    list_ipr_warning_rules as list_ipr_warning_rules,
    create_ipr_warning_rule as create_ipr_warning_rule,
    update_ipr_warning_rule as update_ipr_warning_rule,
    delete_ipr_warning_rule as delete_ipr_warning_rule,
)
router.include_router(reminders_router)


@router.post(f"{settings.api_prefix}/ipr/warnings/generate")
async def generate_ipr_warnings(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _materialize_ipr_case_warnings,
    )
    created = await _materialize_ipr_case_warnings(identity, db)
    await db.commit()
    return {"created": created, "total": created}


@router.get(f"{settings.api_prefix}/ipr/warnings")
async def list_ipr_warnings(status_filter: str = Query("", alias="status"), case_kind: str = "", page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _ipr_warning_dict,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    scope = await _record_scope_conditions(identity, db)
    conditions = [BusinessRecord.module == "ipr_case", *scope]
    if identity.get("role") != "admin":
        conditions.append(IprCaseWarning.recipient == identity["username"])
    if status_filter:
        if status_filter not in {"未读", "已读", "已处理"}: raise HTTPException(status_code=422, detail="预警状态无效")
        conditions.append(IprCaseWarning.status == status_filter)
    if case_kind:
        if case_kind not in IPR_CASE_KINDS: raise HTTPException(status_code=422, detail="案件类型无效")
        conditions.append(BusinessRecord.data["case_kind"].as_string() == case_kind)
    statement = select(IprCaseWarning, IprCaseWarningRule, BusinessRecord).join(IprCaseWarningRule, IprCaseWarningRule.id == IprCaseWarning.rule_id).join(BusinessRecord, BusinessRecord.id == IprCaseWarning.case_record_id).where(*conditions)
    total = int(await db.scalar(select(func.count()).select_from(IprCaseWarning).join(BusinessRecord, BusinessRecord.id == IprCaseWarning.case_record_id).where(*conditions)) or 0)
    rows = (await db.execute(statement.order_by(IprCaseWarning.due_date, IprCaseWarning.id).offset((page - 1) * page_size).limit(page_size))).all()
    unread = int(await db.scalar(select(func.count()).select_from(IprCaseWarning).join(BusinessRecord, BusinessRecord.id == IprCaseWarning.case_record_id).where(*conditions, IprCaseWarning.status == "未读")) or 0)
    return {"items": [_ipr_warning_dict(warning, rule, case_record) for warning, rule, case_record in rows], "total": total, "unread": unread, "page": page, "page_size": page_size}


@router.post(f"{settings.api_prefix}/ipr/warnings/{{warning_id}}/read")
async def read_ipr_warning(warning_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _ipr_warning_for_recipient,
    )
    row = await _ipr_warning_for_recipient(warning_id, identity, db)
    if row.status == "未读": row.status = "已读"; row.read_at = datetime.now()
    if row.notification_id:
        notice = await db.get(Notification, row.notification_id)
        if notice and notice.recipient == row.recipient: notice.is_read = True; notice.read_at = row.read_at or datetime.now()
    await db.commit()
    return {"id": row.id, "status": row.status, "is_read": True, "read_at": row.read_at}


@router.post(f"{settings.api_prefix}/ipr/warnings/{{warning_id}}/process")
async def process_ipr_warning(warning_id: int, body: IprCaseWarningProcessInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _ipr_warning_for_recipient,
    )
    row = await _ipr_warning_for_recipient(warning_id, identity, db)
    if row.status == "已处理":
        return {"id": row.id, "status": row.status, "processed_at": row.processed_at, "processed_by": row.processed_by}
    now = datetime.now(); row.status = "已处理"; row.read_at = row.read_at or now; row.processed_at = now; row.processed_by = identity["username"]; row.process_comment = body.comment.strip()
    if row.notification_id:
        notice = await db.get(Notification, row.notification_id)
        if notice and notice.recipient == row.recipient: notice.is_read = True; notice.read_at = now
    db.add(WorkflowEvent(record_id=row.case_record_id, action="处理知识产权案件预警", operator=identity["username"], comment=row.process_comment or "已处理预警"))
    await db.commit()
    return {"id": row.id, "status": row.status, "processed_at": row.processed_at, "processed_by": row.processed_by}


from app.areas.ipr.case_files import (
    router as case_files_router,
    list_ipr_case_files as list_ipr_case_files,
    list_ipr_case_file_types as list_ipr_case_file_types,
    upload_ipr_case_file as upload_ipr_case_file,
    create_ipr_case_file_custom_import_batch as create_ipr_case_file_custom_import_batch,
    list_ipr_case_file_custom_import_batches as list_ipr_case_file_custom_import_batches,
    list_ipr_case_file_custom_import_candidates as list_ipr_case_file_custom_import_candidates,
    match_ipr_case_file_custom_import_candidate as match_ipr_case_file_custom_import_candidate,
    correct_ipr_case_file_custom_import_candidate as correct_ipr_case_file_custom_import_candidate,
    confirm_ipr_case_file_custom_import_candidates as confirm_ipr_case_file_custom_import_candidates,
    batch_upload_ipr_case_file as batch_upload_ipr_case_file,
    mark_ipr_case_file_transmitted as mark_ipr_case_file_transmitted,
    mark_ipr_case_files_transmitted as mark_ipr_case_files_transmitted,
    unlock_ipr_case_file as unlock_ipr_case_file,
    generate_ipr_case_application_file as generate_ipr_case_application_file,
    delete_ipr_case_file as delete_ipr_case_file,
)
router.include_router(case_files_router)


@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/submit")
async def submit_ipr_case(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    await _require_record_owner_or_manager(record, identity, db)
    if record.status not in IPR_CASE_DRAFT_STATUSES: raise HTTPException(status_code=409, detail="当前状态不能提交知识产权立案审核")
    data = record.data or {}
    if not str(data.get("application_no") or "").strip(): raise HTTPException(status_code=422, detail="提交立案审核前必须填写申请号或注册号")
    await assess_conflict_review(record, identity, db, trigger="case_save")
    gate = await get_conflict_review_gate(record, db, action="提交知识产权立案")
    if gate["blocking"]:
        await db.commit()
        raise HTTPException(status_code=409, detail={
            "code": "CONFLICT_REVIEW_REQUIRED", "message": gate["message"],
            "record_id": gate["record_id"], "review_id": (gate.get("review") or {}).get("id"),
            "conflict_review": gate.get("review"),
        })
    data = record.data or {}
    previous = record.status; record.status = "待立案审核"; record.data = {**data, "submitted_at": datetime.now().isoformat(timespec="seconds"), "submitted_by": identity["username"]}
    db.add(WorkflowEvent(record_id=record.id, action="提交知识产权立案审核", from_status=previous, to_status=record.status, operator=identity["username"], comment=""))
    await db.commit(); await db.refresh(record)
    return _record_dict(record, await _allowed_field_keys(identity, db))


@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/review")
async def review_ipr_case(case_id: int, body: IprCaseReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    if identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="仅管理员或管理人员可以审核知识产权立案")
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    if record.status != "待立案审核": raise HTTPException(status_code=409, detail="该知识产权案件不在待立案审核状态")
    if not body.approved and not body.comment.strip(): raise HTTPException(status_code=422, detail="驳回必须填写原因")
    if body.approved:
        await require_conflict_clear(record, db, action="知识产权立案审核")
    previous = record.status; record.status = "在办" if body.approved else "已驳回"; record.data = {**(record.data or {}), "reviewed_at": datetime.now().isoformat(timespec="seconds"), "reviewed_by": identity["username"], "review_comment": body.comment.strip()}
    db.add(WorkflowEvent(record_id=record.id, action="知识产权立案审核通过" if body.approved else "知识产权立案审核驳回", from_status=previous, to_status=record.status, operator=identity["username"], comment=body.comment.strip()))
    await db.commit(); await db.refresh(record)
    return _record_dict(record, await _allowed_field_keys(identity, db))


@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/close")
async def close_ipr_case(case_id: int, body: IprCaseLifecycleInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    await _require_record_owner_or_manager(record, identity, db)
    if record.status != "在办": raise HTTPException(status_code=409, detail="仅在办知识产权案件可以结案")
    previous = record.status; record.status = "已结案"; record.data = {**(record.data or {}), "closed_at": datetime.now().isoformat(timespec="seconds"), "closed_by": identity["username"]}
    db.add(WorkflowEvent(record_id=record.id, action="知识产权案件结案", from_status=previous, to_status=record.status, operator=identity["username"], comment=body.comment.strip()))
    await db.commit(); await db.refresh(record)
    return _record_dict(record, await _allowed_field_keys(identity, db))


@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/reopen")
async def reopen_ipr_case(case_id: int, body: IprCaseLifecycleInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    if identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="仅管理员或管理人员可以重新开启知识产权案件")
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    if record.status != "已结案": raise HTTPException(status_code=409, detail="仅已结案知识产权案件可以重新开启")
    await require_conflict_clear(record, db, action="重新开启知识产权案件")
    previous = record.status; record.status = "在办"; record.data = {**(record.data or {}), "reopened_at": datetime.now().isoformat(timespec="seconds"), "reopened_by": identity["username"]}
    db.add(WorkflowEvent(record_id=record.id, action="重新开启知识产权案件", from_status=previous, to_status=record.status, operator=identity["username"], comment=body.comment.strip()))
    await db.commit(); await db.refresh(record)
    return _record_dict(record, await _allowed_field_keys(identity, db))


@router.post(f"{settings.api_prefix}/ipr/cases/{{case_id}}/documents/{{document_type}}", status_code=status.HTTP_201_CREATED)
async def generate_ipr_case_document(case_id: int, document_type: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.ipr import (
        _ipr_case_document_bytes,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    if document_type not in IPR_CASE_DOCUMENT_TYPES:
        raise HTTPException(status_code=404, detail="不支持的知识产权案件文书类型")
    record = await _ensure_record_module(case_id, "ipr_case", identity, db)
    await _require_record_owner_or_manager(record, identity, db)
    if record.status not in {"在办", "已结案"}:
        raise HTTPException(status_code=409, detail="仅在办或已结案知识产权案件可以生成正式案件文书")
    title, content = _ipr_case_document_bytes(record, document_type)
    stored_name = f"{uuid4().hex}.docx"
    target = UPLOAD_ROOT / stored_name
    target.write_bytes(content)
    original_name = f"{record.serial_no}-{title}-{datetime.now():%Y%m%d%H%M%S}.docx"
    attachment = FileAttachment(record_id=record.id, category="知识产权案件文书", original_name=original_name, stored_name=stored_name, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", size=len(content), path=str(target), uploader=identity["username"], remark=f"系统生成：{document_type}")
    db.add(attachment)
    db.add(WorkflowEvent(record_id=record.id, action="生成知识产权案件文书", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{title}：{original_name}"))
    await db.commit(); await db.refresh(attachment)
    return _attachment_dict(attachment, record)


@router.post(f"{settings.api_prefix}/ipr/official-files/import-batches", status_code=status.HTTP_201_CREATED)
async def create_ipr_official_import_batch(
    file: UploadFile = File(...), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """Parse a CSV source into reviewable candidates; this never creates formal official files."""
    from app.core.formatters import (
        _parse_ipr_official_candidate_date,
    )
    from app.core.permissions import (
        _require_record_module_menu,
    )
    await _require_record_module_menu("ipr_official_file", identity, db, action="导入")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix != ".csv":
        raise HTTPException(status_code=422, detail="候选解析当前仅接受 CSV 源文件；请先按模板整理后上传")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="候选导入源文件不能为空")
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="候选导入源文件不能超过 20MB")
    try:
        source_text = content.decode("utf-8-sig")
        source_rows = list(csv.DictReader(io.StringIO(source_text)))
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="CSV 必须使用 UTF-8 编码") from exc
    if not source_rows:
        raise HTTPException(status_code=422, detail="CSV 没有可解析的数据行")
    if len(source_rows) > 1000:
        raise HTTPException(status_code=422, detail="单个候选导入批次最多 1000 行")
    username = identity["username"]
    user = await db.scalar(select(User).where(User.username == username))
    source_name = Path(file.filename or "ipr-official-candidates.csv").name
    source_path = UPLOAD_ROOT / f"{uuid4().hex}{suffix}"
    try:
        source_path.write_bytes(content)
        batch = IprOfficialImportBatch(source_filename=source_name, source_path=str(source_path), source_size=len(content), created_by=username, department=user.department if user else "")
        db.add(batch); await db.flush()
        error_count = 0
        for row_no, raw in enumerate(source_rows, 2):
            normalized = {str(key or "").strip(): str(value or "").strip() for key, value in raw.items()}
            application_no = normalized.get("申请号") or normalized.get("application_no") or ""
            official_type = normalized.get("通知书名称") or normalized.get("官文类型") or normalized.get("official_type") or ""
            official_no = normalized.get("发文号") or normalized.get("官文号") or normalized.get("official_no") or ""
            errors: list[str] = []
            if not application_no: errors.append("缺少申请号")
            if not official_type: errors.append("缺少通知书名称/官文类型")
            received_date = _parse_ipr_official_candidate_date(normalized.get("收发文日") or normalized.get("received_date") or "", "收发文日", errors)
            due_date = _parse_ipr_official_candidate_date(normalized.get("办理期限") or normalized.get("due_date") or "", "办理期限", errors)
            case_record = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "ipr_case", BusinessRecord.data["application_no"].as_string() == application_no)) if application_no else None
            if application_no and not case_record: errors.append("未匹配到知识产权案件，请人工选择")
            if case_record and case_record.status != "在办": errors.append("匹配案件不是在办状态")
            if errors:
                error_count += 1
            db.add(IprOfficialImportCandidate(batch_id=batch.id, row_no=row_no, ipr_case_id=case_record.id if case_record and case_record.status == "在办" else None, application_no=application_no, official_type=official_type, official_no=official_no, received_date=received_date, due_date=due_date, raw_data=normalized, errors=errors, status="待确认" if not errors else "待修正"))
        batch.total_count = len(source_rows); batch.error_count = error_count
        await db.commit()
    except Exception:
        await db.rollback()
        source_path.unlink(missing_ok=True)
        raise
    await db.refresh(batch)
    return {"id": batch.id, "status": batch.status, "total_count": batch.total_count, "error_count": batch.error_count}


@router.get(f"{settings.api_prefix}/ipr/official-files/import-batches")
async def list_ipr_official_import_batches(
    batch_status: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """Return only import batches visible to the caller, newest first."""
    from app.core.permissions import (
        _require_record_module_menu,
    )
    await _require_record_module_menu("ipr_official_file", identity, db, action="查看")
    conditions = []
    if identity.get("role") != "admin":
        user = await db.scalar(select(User).where(User.username == identity["username"]))
        if identity.get("role") == "manager" and user:
            conditions.append(or_(IprOfficialImportBatch.created_by == identity["username"], IprOfficialImportBatch.department == user.department))
        else:
            conditions.append(IprOfficialImportBatch.created_by == identity["username"])
    if batch_status:
        conditions.append(IprOfficialImportBatch.status == batch_status)
    rows = (await db.scalars(select(IprOfficialImportBatch).where(*conditions).order_by(IprOfficialImportBatch.created_at.desc()).limit(100))).all()
    return {"items": [{
        "id": row.id, "source_filename": row.source_filename, "source_size": row.source_size, "status": row.status,
        "total_count": row.total_count, "error_count": row.error_count, "imported_count": row.imported_count,
        "created_by": row.created_by, "department": row.department, "created_at": row.created_at, "updated_at": row.updated_at,
    } for row in rows]}


@router.get(f"{settings.api_prefix}/ipr/official-files/import-batches/{{batch_id}}/candidates")
async def list_ipr_official_import_candidates(
    batch_id: int, candidate_status: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _ensure_ipr_import_batch_visible, _require_record_module_menu,
    )
    await _require_record_module_menu("ipr_official_file", identity, db, action="查看")
    await _ensure_ipr_import_batch_visible(batch_id, identity, db)
    conditions = [IprOfficialImportCandidate.batch_id == batch_id]
    if candidate_status:
        conditions.append(IprOfficialImportCandidate.status == candidate_status)
    rows = (await db.scalars(select(IprOfficialImportCandidate).where(*conditions).order_by(IprOfficialImportCandidate.row_no))).all()
    return {"items": [{
        "id": row.id, "row_no": row.row_no, "ipr_case_id": row.ipr_case_id, "application_no": row.application_no,
        "official_type": row.official_type, "official_no": row.official_no, "received_date": row.received_date,
        "due_date": row.due_date, "raw_data": row.raw_data, "errors": row.errors, "status": row.status,
        "official_record_id": row.official_record_id,
    } for row in rows], "total": len(rows)}


@router.get(f"{settings.api_prefix}/ipr/official-files/checklist")
async def list_ipr_official_file_checklist(
    keyword: str = "", candidate_status: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """Legacy-equivalent import check list, including rows not yet confirmed as official files."""
    from app.core.permissions import (
        _require_record_module_menu, _visible_ipr_import_batches,
    )
    await _require_record_module_menu("ipr_official_file", identity, db, action="查看")
    batches = await _visible_ipr_import_batches(identity, db)
    batch_by_id = {item.id: item for item in batches}
    if not batch_by_id:
        return {"items": [], "total": 0}
    conditions = [IprOfficialImportCandidate.batch_id.in_(list(batch_by_id))]
    if candidate_status:
        conditions.append(IprOfficialImportCandidate.status == candidate_status)
    if keyword:
        like = f"%{keyword.strip()}%"
        conditions.append(or_(
            IprOfficialImportCandidate.application_no.ilike(like), IprOfficialImportCandidate.official_type.ilike(like),
            IprOfficialImportCandidate.official_no.ilike(like),
        ))
    candidates = list((await db.scalars(select(IprOfficialImportCandidate).where(*conditions).order_by(IprOfficialImportCandidate.created_at.desc(), IprOfficialImportCandidate.row_no))).all())
    official_ids = [row.official_record_id for row in candidates if row.official_record_id]
    officials = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(official_ids), BusinessRecord.module == "ipr_official_file"))).all()) if official_ids else []
    officials_by_id = {item.id: item for item in officials}
    cases = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_([row.ipr_case_id for row in candidates if row.ipr_case_id]), BusinessRecord.module == "ipr_case"))).all()) if any(row.ipr_case_id for row in candidates) else []
    cases_by_id = {item.id: item for item in cases}
    items = []
    for row in candidates:
        batch = batch_by_id[row.batch_id]
        official = officials_by_id.get(row.official_record_id)
        case_record = cases_by_id.get(row.ipr_case_id)
        raw = row.raw_data or {}
        items.append({
            "id": row.id, "batch_id": row.batch_id, "source_filename": batch.source_filename,
            "application_no": row.application_no, "official_type": row.official_type,
            "invention_title": raw.get("发明创造名称") or raw.get("invention_title") or raw.get("案件名称") or "",
            "official_no": row.official_no, "electronic_date": row.received_date,
            "download_status": "已确认导入" if official else "待确认导入",
            "system_status": official.status if official else row.status,
            "case_id": row.ipr_case_id, "case_no": case_record.serial_no if case_record else "",
            "imported_at": (official.data or {}).get("imported_at") if official else batch.created_at,
            "errors": row.errors or [], "candidate_status": row.status, "official_record_id": row.official_record_id,
        })
    return {"items": items, "total": len(items)}


@router.get(f"{settings.api_prefix}/ipr/official-files/checklist/export/excel")
async def export_ipr_official_file_checklist(
    keyword: str = "", candidate_status: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.system import (
        _excel_response,
    )
    result = await list_ipr_official_file_checklist(keyword, candidate_status, identity, db)
    return _excel_response(
        f"知识产权官文检查清单-{date.today()}.xls",
        ["申请号/不受理编号", "通知书名称", "发明创造名称", "发文序列号", "电子发文日", "下载状态", "系统状态", "案号", "入库时间", "错误消息"],
        [[
            item["application_no"], item["official_type"], item["invention_title"], item["official_no"],
            item["electronic_date"] or "", item["download_status"], item["system_status"], item["case_no"],
            item["imported_at"] or "", "；".join(item["errors"]),
        ] for item in result["items"]],
    )


@router.post(f"{settings.api_prefix}/ipr/official-files/import-candidates/{{candidate_id}}/match")
async def match_ipr_official_import_candidate(candidate_id: int, body: IprOfficialCandidateMatchInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_ipr_import_batch_visible, _ensure_record_module, _require_record_module_menu,
    )
    await _require_record_module_menu("ipr_official_file", identity, db, action="导入")
    candidate = await db.get(IprOfficialImportCandidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="官文候选行不存在")
    await _ensure_ipr_import_batch_visible(candidate.batch_id, identity, db)
    if candidate.status == "已导入":
        raise HTTPException(status_code=409, detail="已导入候选行不能重新匹配案件")
    case_record = await _ensure_record_module(body.ipr_case_id, "ipr_case", identity, db)
    if case_record.status != "在办":
        raise HTTPException(status_code=409, detail="只能匹配在办知识产权案件")
    errors = [item for item in (candidate.errors or []) if item not in {"未匹配到知识产权案件，请人工选择", "匹配案件不是在办状态"}]
    candidate.ipr_case_id = case_record.id
    candidate.errors = errors
    candidate.status = "待确认" if not errors else "待修正"
    await db.commit(); await db.refresh(candidate)
    return {"id": candidate.id, "ipr_case_id": candidate.ipr_case_id, "status": candidate.status, "errors": candidate.errors}


@router.patch(f"{settings.api_prefix}/ipr/official-files/import-candidates/{{candidate_id}}")
async def correct_ipr_official_import_candidate(candidate_id: int, body: IprOfficialCandidateCorrectInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_ipr_import_batch_visible, _ensure_record_module, _ensure_record_visible, _require_record_module_menu,
    )
    await _require_record_module_menu("ipr_official_file", identity, db, action="导入")
    candidate = await db.get(IprOfficialImportCandidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="官文候选行不存在")
    await _ensure_ipr_import_batch_visible(candidate.batch_id, identity, db)
    if candidate.status == "已导入":
        raise HTTPException(status_code=409, detail="已导入候选行不能再修改")
    if "application_no" in body.model_fields_set: candidate.application_no = (body.application_no or "").strip()
    if "official_type" in body.model_fields_set: candidate.official_type = (body.official_type or "").strip()
    if "official_no" in body.model_fields_set: candidate.official_no = (body.official_no or "").strip()
    if "received_date" in body.model_fields_set: candidate.received_date = body.received_date
    if "due_date" in body.model_fields_set: candidate.due_date = body.due_date
    errors: list[str] = []
    if not candidate.application_no: errors.append("缺少申请号")
    if not candidate.official_type: errors.append("缺少通知书名称/官文类型")
    case_record = None
    if candidate.application_no:
        case_record = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "ipr_case", BusinessRecord.data["application_no"].as_string() == candidate.application_no))
        if case_record and case_record.status == "在办":
            await _ensure_record_visible(case_record.id, identity, db)
            candidate.ipr_case_id = case_record.id
        elif not candidate.ipr_case_id:
            errors.append("未匹配到知识产权案件，请人工选择")
    if candidate.ipr_case_id:
        linked_case = await _ensure_record_module(candidate.ipr_case_id, "ipr_case", identity, db)
        if linked_case.status != "在办": errors.append("匹配案件不是在办状态")
    else:
        errors.append("未匹配到知识产权案件，请人工选择")
    candidate.errors = list(dict.fromkeys(errors)); candidate.status = "待确认" if not candidate.errors else "待修正"
    await db.commit(); await db.refresh(candidate)
    return {"id": candidate.id, "status": candidate.status, "errors": candidate.errors, "ipr_case_id": candidate.ipr_case_id}


@router.post(f"{settings.api_prefix}/ipr/official-files/import-batches/{{batch_id}}/confirm")
async def confirm_ipr_official_import_candidates(batch_id: int, body: IprOfficialCandidateConfirmInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Atomically turn confirmed candidate rows into formal official-file records."""
    from app.core.ipr import (
        _next_ipr_official_file_serial,
    )
    from app.core.permissions import (
        _ensure_ipr_import_batch_visible, _ensure_record_visible, _require_record_module_menu,
    )
    await _require_record_module_menu("ipr_official_file", identity, db, action="导入")
    batch = await _ensure_ipr_import_batch_visible(batch_id, identity, db)
    candidate_ids = list(dict.fromkeys(body.candidate_ids))
    candidates = list((await db.scalars(select(IprOfficialImportCandidate).where(IprOfficialImportCandidate.batch_id == batch.id, IprOfficialImportCandidate.id.in_(candidate_ids)))).all())
    if len(candidates) != len(candidate_ids):
        raise HTTPException(status_code=404, detail="存在不属于当前批次的官文候选行")
    by_id = {candidate.id: candidate for candidate in candidates}
    ordered = [by_id[candidate_id] for candidate_id in candidate_ids]
    case_ids = {candidate.ipr_case_id for candidate in ordered if candidate.ipr_case_id}
    cases = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(case_ids), BusinessRecord.module == "ipr_case"))).all()) if case_ids else []
    cases_by_id = {case.id: case for case in cases}
    for candidate in ordered:
        if candidate.status != "待确认" or candidate.errors:
            raise HTTPException(status_code=409, detail=f"候选行 {candidate.row_no} 仍有待修正内容，不能确认导入")
        case_record = cases_by_id.get(candidate.ipr_case_id)
        if not case_record:
            raise HTTPException(status_code=404, detail=f"候选行 {candidate.row_no} 的关联案件不存在")
        await _ensure_record_visible(case_record.id, identity, db)
        if case_record.status != "在办":
            raise HTTPException(status_code=409, detail=f"候选行 {candidate.row_no} 的关联案件不在办，不能确认导入")
    created: list[BusinessRecord] = []
    now = datetime.now()
    for candidate in ordered:
        case_record = cases_by_id[candidate.ipr_case_id]
        serial_no = await _next_ipr_official_file_serial(db)
        case_data = case_record.data or {}
        record = BusinessRecord(
            module="ipr_official_file", serial_no=serial_no, title=candidate.official_type,
            customer=case_record.customer, status="待校验", owner=identity["username"], department=case_record.department,
            description=body.comment.strip(), data={
                "ipr_case_id": case_record.id, "ipr_case_no": case_record.serial_no, "case_kind": case_data.get("case_kind", ""),
                "official_type": candidate.official_type, "official_no": candidate.official_no,
                "received_date": str(candidate.received_date or ""), "due_date": str(candidate.due_date or ""),
                "application_no": candidate.application_no, "source_import_batch_id": batch.id, "source_candidate_id": candidate.id,
                "source_filename": batch.source_filename, "imported_at": now.isoformat(timespec="seconds"), "imported_by": identity["username"],
                "business_process_status": "未处理", "service_process_status": "未处理",
            },
        )
        db.add(record); await db.flush()
        candidate.status = "已导入"; candidate.official_record_id = record.id; candidate.confirmed_by = identity["username"]; candidate.confirmed_at = now
        db.add(WorkflowEvent(record_id=record.id, action="确认导入知识产权官文", to_status=record.status, operator=identity["username"], comment=f"来源批次 {batch.id} 第 {candidate.row_no} 行；{body.comment.strip()}".strip()))
        created.append(record)
    batch.imported_count += len(created)
    remaining = await db.scalar(select(func.count(IprOfficialImportCandidate.id)).where(IprOfficialImportCandidate.batch_id == batch.id, IprOfficialImportCandidate.status != "已导入"))
    batch.status = "已完成" if not remaining else "部分确认"
    await db.commit()
    return {"created": len(created), "record_ids": [record.id for record in created], "batch_status": batch.status}


@router.get(f"{settings.api_prefix}/ipr/official-files")
async def list_ipr_official_files(
    case_kind: str = "", record_status: str = "", keyword: str = "",
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _record_scope_conditions, _require_record_module_menu,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    await _require_record_module_menu("ipr_official_file", identity, db, action="查看")
    conditions = [BusinessRecord.module == "ipr_official_file", *(await _record_scope_conditions(identity, db))]
    if case_kind:
        if case_kind not in IPR_CASE_KINDS: raise HTTPException(status_code=422, detail="知识产权案件类型无效")
        conditions.append(BusinessRecord.data["case_kind"].as_string() == case_kind)
    if record_status: conditions.append(BusinessRecord.status == record_status)
    if keyword:
        like = f"%{keyword.strip()}%"
        conditions.append(or_(BusinessRecord.serial_no.ilike(like), BusinessRecord.title.ilike(like), BusinessRecord.data["official_no"].as_string().ilike(like), BusinessRecord.data["ipr_case_no"].as_string().ilike(like)))
    total = await db.scalar(select(func.count()).select_from(BusinessRecord).where(*conditions))
    rows = (await db.scalars(select(BusinessRecord).where(*conditions).order_by(BusinessRecord.updated_at.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    return {"items": [_record_dict(row, await _allowed_field_keys(identity, db)) for row in rows], "total": total or 0, "page": page, "page_size": page_size}


@router.get(f"{settings.api_prefix}/ipr/official-files/export/excel")
async def export_ipr_official_files_excel(
    case_kind: str = "", record_status: str = "", keyword: str = "",
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _record_scope_conditions, _require_record_module_menu,
    )
    await _require_record_module_menu("ipr_official_file", identity, db, action="查看")
    conditions = [BusinessRecord.module == "ipr_official_file", *(await _record_scope_conditions(identity, db))]
    if case_kind:
        if case_kind not in IPR_CASE_KINDS:
            raise HTTPException(status_code=422, detail="知识产权案件类型无效")
        conditions.append(BusinessRecord.data["case_kind"].as_string() == case_kind)
    if record_status:
        conditions.append(BusinessRecord.status == record_status)
    if keyword:
        like = f"%{keyword.strip()}%"
        conditions.append(or_(BusinessRecord.serial_no.ilike(like), BusinessRecord.title.ilike(like), BusinessRecord.data["official_no"].as_string().ilike(like), BusinessRecord.data["ipr_case_no"].as_string().ilike(like)))
    rows = (await db.scalars(select(BusinessRecord).where(*conditions).order_by(BusinessRecord.updated_at.desc()))).all()
    headers = ["官文编号", "官文类型", "官文号", "关联案件", "案件类型", "客户", "接收日期", "办理期限", "状态", "导入人", "导入时间"]
    def cell(value: object) -> str:
        return f'<Cell><Data ss:Type="String">{xml_escape(str(value or ""))}</Data></Cell>'
    sheet_rows = ["<Row>" + "".join(cell(header) for header in headers) + "</Row>"]
    for row in rows:
        data = row.data or {}
        values = [row.serial_no, row.title, data.get("official_no"), data.get("ipr_case_no"), data.get("case_kind"), row.customer, data.get("received_date"), data.get("due_date"), row.status, data.get("imported_by") or row.owner, data.get("imported_at")]
        sheet_rows.append("<Row>" + "".join(cell(value) for value in values) + "</Row>")
    sheet_name = "知识产权官文"
    workbook = '<?xml version="1.0" encoding="UTF-8"?><?mso-application progid="Excel.Sheet"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="知识产权官文"><Table>' + "".join(sheet_rows) + "</Table></Worksheet></Workbook>"
    filename = f"{sheet_name}清单-{date.today()}.xls"
    return Response(content=workbook.encode("utf-8"), media_type="application/vnd.ms-excel", headers={"Content-Disposition": f"attachment; filename=ipr-official-files.xls; filename*=UTF-8''{quote(filename)}"})


@router.get(f"{settings.api_prefix}/ipr/official-files/download-zip")
async def download_ipr_official_files_zip(
    ids: str = Query(min_length=1), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _ensure_record_visible, _require_record_module_menu,
    )
    from app.core.system import (
        _export_ids,
    )
    await _require_record_module_menu("ipr_official_file", identity, db, action="查看")
    selected_ids = list(dict.fromkeys(_export_ids(ids)))
    if not selected_ids:
        raise HTTPException(status_code=422, detail="请选择需要打包下载的知识产权官文")
    records = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(selected_ids), BusinessRecord.module == "ipr_official_file"))).all())
    if len(records) != len(selected_ids):
        raise HTTPException(status_code=404, detail="选中的知识产权官文不存在")
    by_id = {record.id: record for record in records}
    ordered = [by_id[record_id] for record_id in selected_ids]
    for record in ordered:
        await _ensure_record_visible(record.id, identity, db)
    attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id.in_(selected_ids), FileAttachment.category == "知识产权官文原件").order_by(FileAttachment.id.asc()))).all())
    if not attachments:
        raise HTTPException(status_code=409, detail="所选官文没有可下载的原件")
    archive_content = io.BytesIO()
    missing: list[str] = []
    with zipfile.ZipFile(archive_content, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for attachment in attachments:
            path = Path(attachment.path)
            if not path.exists() or not path.is_file():
                missing.append(attachment.original_name)
                continue
            serial_no = by_id.get(int(attachment.record_id or 0)).serial_no if by_id.get(int(attachment.record_id or 0)) else "官文"
            archive.writestr(f"{serial_no}-{Path(attachment.original_name).name}", path.read_bytes())
    if missing:
        raise HTTPException(status_code=409, detail=f"以下官文原件缺失，未生成不完整压缩包：{'、'.join(missing[:3])}")
    archive_content.seek(0)
    filename = f"知识产权官文原件-{date.today()}.zip"
    return StreamingResponse(archive_content, media_type="application/zip", headers={"Content-Disposition": f"attachment; filename=ipr-official-files.zip; filename*=UTF-8''{quote(filename)}"})


@router.post(f"{settings.api_prefix}/ipr/official-files", status_code=status.HTTP_201_CREATED)
async def upload_ipr_official_file(
    file: UploadFile = File(...), ipr_case_id: int = Form(...), official_type: str = Form(...), official_no: str = Form(""),
    received_date: date | None = Form(None), due_date: date | None = Form(None), remark: str = Form(""),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.ipr import (
        _next_ipr_official_file_serial,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_record_module_menu,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    await _require_record_module_menu("ipr_official_file", identity, db, action="导入")
    case_record = await _ensure_record_module(ipr_case_id, "ipr_case", identity, db)
    if case_record.status != "在办": raise HTTPException(status_code=409, detail="仅在办知识产权案件可以导入官文")
    if not official_type.strip(): raise HTTPException(status_code=422, detail="必须填写官文类型")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".txt", ".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=422, detail="不支持的官文文件格式")
    content = await file.read()
    if not content: raise HTTPException(status_code=422, detail="官文文件不能为空")
    if len(content) > 20 * 1024 * 1024: raise HTTPException(status_code=413, detail="单个官文不能超过 20MB")
    serial_no = await _next_ipr_official_file_serial(db)
    target = UPLOAD_ROOT / f"{uuid4().hex}{suffix}"; target.write_bytes(content)
    data = case_record.data or {}
    official = BusinessRecord(module="ipr_official_file", serial_no=serial_no, title=official_type.strip(), customer=case_record.customer, status="待校验", owner=identity["username"], department=case_record.department, description=remark.strip(), data={"ipr_case_id": case_record.id, "ipr_case_no": case_record.serial_no, "case_kind": data.get("case_kind", ""), "official_type": official_type.strip(), "official_no": official_no.strip(), "received_date": str(received_date) if received_date else "", "due_date": str(due_date) if due_date else "", "imported_at": datetime.now().isoformat(timespec="seconds"), "imported_by": identity["username"], "business_process_status": "未处理", "service_process_status": "未处理"})
    db.add(official); await db.flush()
    attachment = FileAttachment(record_id=official.id, category="知识产权官文原件", original_name=Path(file.filename or target.name).name, stored_name=target.name, content_type=file.content_type or "application/octet-stream", size=len(content), path=str(target), uploader=identity["username"], remark=f"关联知识产权案件 {case_record.serial_no}")
    db.add(attachment)
    db.add(WorkflowEvent(record_id=official.id, action="导入知识产权官文", to_status=official.status, operator=identity["username"], comment=attachment.original_name))
    await db.commit(); await db.refresh(official)
    return {"record": _record_dict(official, await _allowed_field_keys(identity, db)), "attachment": _attachment_dict(attachment, official)}


@router.delete(f"{settings.api_prefix}/ipr/official-files/{{official_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ipr_official_file(official_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Delete an unvalidated official file owned by the caller, including its stored originals."""
    from app.core.permissions import (
        _require_record_owner_or_manager,
    )
    official = await db.get(BusinessRecord, official_id)
    if not official or official.module != "ipr_official_file":
        raise HTTPException(status_code=404, detail="知识产权官文不存在")
    await _require_record_owner_or_manager(official, identity, db)
    if official.status != "待校验":
        raise HTTPException(status_code=409, detail="仅待校验官文可以删除")
    attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id == official.id))).all())
    attachment_paths = [Path(item.path) for item in attachments]
    for attachment in attachments:
        await db.delete(attachment)
    await db.execute(delete(FinanceTransaction).where(FinanceTransaction.finance_record_id == official.id))
    await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == official.id))
    await db.delete(official)
    await db.commit()
    for path in attachment_paths:
        if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
            path.unlink()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(f"{settings.api_prefix}/ipr/official-files/{{official_id}}/validate")
async def validate_ipr_official_file(official_id: int, body: IprOfficialFileActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    if identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="仅管理员或管理人员可以校验知识产权官文")
    official = await _ensure_record_module(official_id, "ipr_official_file", identity, db)
    if official.status != "待校验": raise HTTPException(status_code=409, detail="仅待校验官文可以执行校验")
    case_record = await _ensure_record_module(int((official.data or {}).get("ipr_case_id") or 0), "ipr_case", identity, db)
    if case_record.status != "在办": raise HTTPException(status_code=409, detail="关联知识产权案件不在办，不能校验官文")
    previous = official.status; official.status = "待转发"; official.data = {**(official.data or {}), "business_process_status": "处理中", "validated_at": datetime.now().isoformat(timespec="seconds"), "validated_by": identity["username"], "validate_comment": body.comment.strip()}
    db.add(WorkflowEvent(record_id=official.id, action="校验知识产权官文", from_status=previous, to_status=official.status, operator=identity["username"], comment=body.comment.strip()))
    await db.commit(); await db.refresh(official)
    return _record_dict(official, await _allowed_field_keys(identity, db))


@router.post(f"{settings.api_prefix}/ipr/official-files/{{official_id}}/transmit")
async def transmit_ipr_official_file(official_id: int, body: IprOfficialFileActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    official = await _ensure_record_module(official_id, "ipr_official_file", identity, db)
    await _require_record_owner_or_manager(official, identity, db)
    if official.status != "待转发": raise HTTPException(status_code=409, detail="仅已校验官文可以转发")
    previous = official.status; official.status = "已转发"; official.data = {**(official.data or {}), "service_process_status": "处理中", "transmitted_at": datetime.now().isoformat(timespec="seconds"), "transmitted_by": identity["username"], "transmit_comment": body.comment.strip()}
    db.add(WorkflowEvent(record_id=official.id, action="转发知识产权官文", from_status=previous, to_status=official.status, operator=identity["username"], comment=body.comment.strip()))
    await db.commit(); await db.refresh(official)
    return _record_dict(official, await _allowed_field_keys(identity, db))


@router.post(f"{settings.api_prefix}/ipr/official-files/{{official_id}}/complete")
async def complete_ipr_official_file(official_id: int, body: IprOfficialFileActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    official = await _ensure_record_module(official_id, "ipr_official_file", identity, db)
    await _require_record_owner_or_manager(official, identity, db)
    if official.status != "已转发": raise HTTPException(status_code=409, detail="仅已转发官文可以办结")
    previous = official.status; official.status = "已办结"; official.data = {**(official.data or {}), "business_process_status": "已处理", "service_process_status": "已处理", "completed_at": datetime.now().isoformat(timespec="seconds"), "completed_by": identity["username"], "complete_comment": body.comment.strip()}
    db.add(WorkflowEvent(record_id=official.id, action="办结知识产权官文", from_status=previous, to_status=official.status, operator=identity["username"], comment=body.comment.strip()))
    await db.commit(); await db.refresh(official)
    return _record_dict(official, await _allowed_field_keys(identity, db))


@router.post(f"{settings.api_prefix}/ipr/official-files/actions/batch/{{action}}")
async def batch_ipr_official_file_action(action: str, body: IprOfficialFileBatchActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Apply one legitimate official-document transition to selected rows atomically.

    The legacy system exposes grouped transfer actions.  This endpoint keeps that
    efficiency without allowing the generic record interface to bypass the
    validation / transfer / completion lifecycle.
    """
    from app.core.permissions import (
        _ensure_record_module, _ensure_record_visible, _require_record_owner_or_manager,
    )
    transitions = {
        "validate": ("待校验", "待转发", "校验知识产权官文"),
        "transmit": ("待转发", "已转发", "转发知识产权官文"),
        "complete": ("已转发", "已办结", "办结知识产权官文"),
    }
    if action not in transitions:
        raise HTTPException(status_code=404, detail="不支持的知识产权官文批量操作")
    ids = list(dict.fromkeys(body.official_ids))
    if action == "validate" and identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="仅管理员或管理人员可以校验知识产权官文")
    expected, target, event_action = transitions[action]
    records = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(ids), BusinessRecord.module == "ipr_official_file"))).all())
    if len(records) != len(ids):
        raise HTTPException(status_code=404, detail="选中的知识产权官文不存在")
    records_by_id = {record.id: record for record in records}
    ordered = [records_by_id[item_id] for item_id in ids]
    for official in ordered:
        await _ensure_record_visible(official.id, identity, db)
        if action != "validate":
            await _require_record_owner_or_manager(official, identity, db)
        if official.status != expected:
            raise HTTPException(status_code=409, detail=f"官文 {official.serial_no} 当前为“{official.status}”，不能执行{event_action}")
        if action == "validate":
            linked_case_id = int((official.data or {}).get("ipr_case_id") or 0)
            case_record = await _ensure_record_module(linked_case_id, "ipr_case", identity, db)
            if case_record.status != "在办":
                raise HTTPException(status_code=409, detail=f"关联知识产权案件 {case_record.serial_no} 不在办，不能校验官文")
    timestamp_key = {"validate": "validated", "transmit": "transmitted", "complete": "completed"}[action]
    for official in ordered:
        previous = official.status
        official.status = target
        dual_status = "处理中" if action in {"validate", "transmit"} else "已处理"
        dual_key = "business_process_status" if action == "validate" else "service_process_status"
        data = {**(official.data or {}), dual_key: dual_status, f"{timestamp_key}_at": datetime.now().isoformat(timespec="seconds"), f"{timestamp_key}_by": identity["username"], f"{action}_comment": body.comment.strip()}
        if action == "complete":
            data["business_process_status"] = "已处理"
        official.data = data
        db.add(WorkflowEvent(record_id=official.id, action=event_action, from_status=previous, to_status=target, operator=identity["username"], comment=body.comment.strip()))
    await db.commit()
    return {"processed": len(ordered), "ids": ids, "status": target}


@router.post(f"{settings.api_prefix}/ipr/official-files/history/actions/batch/{{action}}")
async def batch_ipr_official_history_action(action: str, body: IprOfficialFileBatchActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Mark one of the two historic official-file processing dimensions complete.

    The legacy history queue has independent \"business\" and \"service\" mark
    actions.  They must not reopen or otherwise change the completed document
    lifecycle, so this dedicated endpoint only updates the corresponding
    historical processing flag and records an auditable event.
    """
    from app.core.permissions import (
        _ensure_record_visible, _require_record_owner_or_manager,
    )
    action_map = {
        "business-process": ("business_process_status", "标记历史官文业务已处理"),
        "service-process": ("service_process_status", "标记历史官文流程已处理"),
    }
    if action not in action_map:
        raise HTTPException(status_code=404, detail="不支持的历史官文操作")
    ids = list(dict.fromkeys(body.official_ids))
    records = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(ids), BusinessRecord.module == "ipr_official_file"))).all())
    if len(records) != len(ids):
        raise HTTPException(status_code=404, detail="选中的知识产权官文不存在")
    key, event_action = action_map[action]
    for official in records:
        await _ensure_record_visible(official.id, identity, db)
        await _require_record_owner_or_manager(official, identity, db)
        if official.status != "已办结":
            raise HTTPException(status_code=409, detail=f"官文 {official.serial_no} 尚未办结，不能作为历史官文标记处理")
    now = datetime.now().isoformat(timespec="seconds")
    for official in records:
        official.data = {**(official.data or {}), key: "已处理", f"history_{key}_at": now, f"history_{key}_by": identity["username"]}
        db.add(WorkflowEvent(record_id=official.id, action=event_action, from_status=official.status, to_status=official.status, operator=identity["username"], comment=body.comment.strip()))
    await db.commit()
    return {"processed": len(records), "ids": ids, "field": key, "value": "已处理"}


class IprOfficialProcessingBatchInput(IprOfficialFileBatchActionInput):
    status: Literal["未处理", "处理中", "已处理"]


@router.post(f"{settings.api_prefix}/ipr/official-files/processing/{{dimension}}")
async def update_ipr_official_processing(
    dimension: Literal["business", "service"],
    body: IprOfficialProcessingBatchInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Set one independent legacy processing dimension without changing lifecycle."""
    from app.core.permissions import (
        _ensure_record_visible, _require_record_owner_or_manager, _require_record_module_menu,
    )
    await _require_record_module_menu("ipr_official_file", identity, db, action="编辑")
    ids = list(dict.fromkeys(body.official_ids))
    records = list((await db.scalars(
        select(BusinessRecord)
        .where(BusinessRecord.id.in_(ids), BusinessRecord.module == "ipr_official_file")
        .order_by(BusinessRecord.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )).all())
    if len(records) != len(ids):
        raise HTTPException(status_code=404, detail="选中的官文不存在，请刷新后重试")
    for official in records:
        await _ensure_record_visible(official.id, identity, db)
        await _require_record_owner_or_manager(official, identity, db)
    key = f"{dimension}_process_status"
    label = "业务" if dimension == "business" else "流程"
    now = datetime.now().isoformat(timespec="seconds")
    changed = 0
    for official in records:
        data = dict(official.data or {})
        previous = data.get(key) or "未处理"
        if previous == body.status:
            continue
        official.data = {
            **data, key: body.status,
            f"{key}_at": now, f"{key}_by": identity["username"],
        }
        db.add(WorkflowEvent(
            record_id=official.id, action=f"官文{label}处理状态变更",
            from_status=official.status, to_status=official.status,
            operator=identity["username"],
            comment=f"{label}处理：{previous} → {body.status}。{body.comment.strip()}",
        ))
        changed += 1
    await db.commit()
    return {"processed": len(records), "changed": changed, "ids": ids, "field": key, "value": body.status}
