"""普通案件与法律业务路由编排。"""
from app.core.case_archive import ArchiveSearchInput, ArchiveBatchReviewInput, ArchiveExportInput, search_archive_cases
from app.core.constants import (
    ADMINISTRATIVE_CLIENT_POSITIONS, CASE_CLIENT_POSITIONS_BY_TYPE, CASE_CREATABLE_TYPES,
    CASE_CREATE_PERMISSION_BY_TYPE, CASE_CREATE_STATUS_ALIASES, CASE_DOCUMENT_CATEGORY, CASE_DOCUMENT_TYPES,
    CIVIL_CASE_TYPES, CRIMINAL_JUDICIAL_PREFIXES, CUSTOMER_SYSTEM_DATA_FIELDS, EXPENSE_SUBTYPE_FEE_TYPE,
    GENERIC_RECORD_DELETABLE_MODULES, GENERIC_RECORD_EDITABLE_MODULES, GENERIC_RECORD_TRANSITION_MODULES, INVESTIGATION_RECORD_MODULES, INVOICE_RELEASED_STATUSES,
    JAR_FEE_MODULE, NORMAL_CASE_BASIC_TYPES, UPLOAD_ROOT, WORKFLOW_TRANSITIONS, _BUILTIN_DOCUMENT_TEMPLATES, logger,
)
from app.core.dependencies import (
    Annotated, AsyncSession, BusinessRecord, CaseAssistedFee, CaseTypeCasePhaseRelation, CaseTypeFileTypeRelation, ContractApprovalStep, Department, Depends, Document, FileAttachment, FinanceTransaction, HTTPException, HearingSchedule,
    Inches, IncomingPayment, IntegrityError, Path,
    Pt, Query, Response, SQLAlchemyError,
    SealAsset, SystemParameter,
    User, WD_ALIGN_PARAGRAPH, Warehouse, WarehouseStorageLocation,
    WorkflowEvent, csv, current_identity, date, datetime, delete,
    func, get_db, io, json,
    or_, qn, qrcode, quote, re,
    select, settings, status,
    timedelta, timezone, uuid4,
)
from app.models_shared import (
    ArchiveCheckInput, ArchiveReviewInput, CaseArbitrationBasicInput, CaseAssignmentInput,
    CaseAssistedFeeConfirmInput, CaseAssistedFeeCreateInput, CaseAssistedFeeUpdateInput, CaseBatchDeleteInput, CaseBatchFeeInput, CaseBatchUpdateInput, CaseCommissionBatchInput, CaseCommissionPreviewInput, CaseCounselBasicInput, CaseCourtInfoInput,
    CaseCreateInput, CaseCreationCompleteInput, CaseCreationReviewInput, CaseExecutionStatusInput, CaseHearingLawyerInput,
    CaseJudicialInput, CaseLitigantsInput, CaseLogInput, CaseMergeInput, CaseNormalBasicInput,
    CaseNotaryInfoInput, CasePhaseChangeInput, CaseProgressInput, CaseSettlementAmountInput,
    CaseTaskFinishedInput, CaseUnarchiveRequestInput, CaseUnarchiveReviewInput, CounselCaseSearchInput, CriminalCourtMaintenanceInput, CriminalProcuratorateMaintenanceInput,
    CriminalPublicSecurityMaintenanceInput, HearingInput, RecordInput, RecordUpdate, TaskActionInput, TransitionInput,
)
from fastapi import APIRouter
from app.core.conflict_review import assess_conflict_review, get_conflict_review_gate, require_conflict_clear
from fastapi.responses import FileResponse

router = APIRouter()


from app.areas.legal.communications import (
    router as communications_router,
    list_communications as list_communications,
    list_communication_attachments as list_communication_attachments,
    upload_communication_attachment as upload_communication_attachment,
    delete_communication_attachment as delete_communication_attachment,
    create_communication as create_communication,
    update_communication as update_communication,
    delete_communication as delete_communication,
)
router.include_router(communications_router)


from app.areas.legal.record_exports import (
    router as record_exports_router,
    export_records as export_records,
    export_records_excel as export_records_excel,
)
router.include_router(record_exports_router)


@router.get(f"{settings.api_prefix}/cases/export/excel")
async def export_selected_ordinary_cases_excel(ids: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _ordinary_case_export_rows, _selected_ordinary_case_export_records,
    )
    from app.core.system import (
        _excel_response,
    )
    records = await _selected_ordinary_case_export_records(ids, identity, db)
    return _excel_response(
        f"普通案件导出-{date.today()}.xls",
        ["案号", "案件名称", "案件类型", "案件阶段", "客户", "合同编号", "案由/罪名", "经办律师", "律师助理", "开庭律师", "法院/机构", "立案日期", "创建日期"],
        _ordinary_case_export_rows(records),
    )


@router.get(f"{settings.api_prefix}/cases/export/archive-manifest")
async def export_selected_case_archive_manifest(ids: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _selected_ordinary_case_export_records,
    )
    from app.core.system import (
        _excel_response,
    )
    records = await _selected_ordinary_case_export_records(ids, identity, db)
    attachment_counts = dict((await db.execute(
        select(FileAttachment.record_id, func.count(FileAttachment.id)).where(FileAttachment.record_id.in_([record.id for record in records])).group_by(FileAttachment.record_id)
    )).all())
    rows = []
    for record in records:
        data = record.data or {}
        rows.append([
            record.serial_no, record.title, record.customer, data.get("case_type", ""), record.status,
            data.get("contract_no", ""), record.owner, attachment_counts.get(record.id, 0),
            data.get("archive_no", ""), data.get("paper_archive_location", ""), data.get("paper_volume_count", ""),
        ])
    return _excel_response(
        f"案件归档清单-{date.today()}.xls",
        ["案号", "案件名称", "客户", "案件类型", "归档状态", "合同编号", "负责人", "附件数量", "归档号", "纸质卷宗位置", "纸质卷宗数量"],
        rows,
    )


@router.get(f"{settings.api_prefix}/cases/export/qr-word")
async def export_selected_case_qr_word(ids: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _selected_ordinary_case_export_records,
    )
    records = await _selected_ordinary_case_export_records(ids, identity, db)
    document = Document()
    document.add_heading("案件二维码清单", level=0)
    document.add_paragraph(f"生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}")
    document.add_paragraph("二维码包含案件记录编号与案号，用于内部扫描核对；扫描后仍须按当前账号权限在系统内查看案件详情。")
    for index, record in enumerate(records, 1):
        if index > 1:
            document.add_page_break()
        data = record.data or {}
        document.add_heading(f"{index}. {record.serial_no}", level=1)
        qr_payload = json.dumps({"case_record_id": record.id, "case_no": record.serial_no}, ensure_ascii=False, separators=(",", ":"))
        image = qrcode.make(qr_payload)
        image_buffer = io.BytesIO()
        image.save(image_buffer, format="PNG")
        image_buffer.seek(0)
        document.add_picture(image_buffer, width=Inches(1.5))
        document.add_paragraph(f"案件名称：{record.title}")
        document.add_paragraph(f"客户：{record.customer or '【待补充】'}")
        document.add_paragraph(f"案件类型：{data.get('case_type') or '【待补充】'}")
        document.add_paragraph(f"案件阶段：{record.status}")
    content = io.BytesIO()
    document.save(content)
    filename = f"案件二维码清单-{date.today()}.docx"
    disposition = f"attachment; filename=case-qr.docx; filename*=UTF-8''{quote(filename)}"
    return Response(content=content.getvalue(), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": disposition})


from app.areas.legal.record_import import (
    router as record_import_router,
    records_import_template as records_import_template,
    import_business_records as import_business_records,
)
router.include_router(record_import_router)


from app.areas.legal.record_queries import (
    router as record_queries_router,
    list_records as list_records,
)
router.include_router(record_queries_router)


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/commission-preview")
async def preview_case_commissions(
    case_id: int,
    source_fee_id: int = Query(gt=0),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.cases import (
        _case_commission_preview,
    )
    return await _case_commission_preview(case_id, source_fee_id, identity, db)


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/commission-preview")
async def preview_case_commissions_for_amount(
    case_id: int,
    body: CaseCommissionPreviewInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.cases import (
        _case_commission_preview_for_amount,
    )
    from app.core.permissions import (
        _case_detail_action_capabilities, _ensure_record_module,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    if not (await _case_detail_action_capabilities(case_record, identity, db))["can_create_finance"]:
        raise HTTPException(status_code=403, detail="当前账号没有新增案件提成权限")
    preview = await _case_commission_preview_for_amount(case_record, body.amount, db)
    return {**preview, "source_fee": {"id": None, "serial_no": "", "amount": body.amount, "fee_type": "代理费"}}


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/commissions", status_code=status.HTTP_201_CREATED)
async def create_case_commissions(
    case_id: int,
    body: CaseCommissionBatchInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.cases import (
        _case_commission_preview,
    )
    from app.core.finance import (
        _new_internal_payment_package_no, _round_fee_amount, _sync_case_commission_lifecycle,
    )
    from app.core.permissions import (
        _record_dicts_for_identity,
    )
    preview = await _case_commission_preview(case_id, body.source_fee_id, identity, db)
    templates = {item["preview_key"]: item for item in preview["items"]}
    normalized: list[tuple[dict, float, str]] = []
    for index, item in enumerate(body.items, start=1):
        template = templates.get(item.preview_key)
        if not template:
            raise HTTPException(status_code=422, detail=f"第{index}行提成项目已失效，请重新打开新增提成窗口")
        base_amount = _round_fee_amount(item.base_amount if item.base_amount is not None else template["base_amount"])
        reference_commission = (
            _round_fee_amount(template["fixed_amount"])
            if template["calculation_kind"] == "fixed"
            else _round_fee_amount(base_amount * template["rate"])
        )
        normalized.append(({
            **template,
            "base_amount": base_amount,
            "reference_commission": reference_commission,
        }, _round_fee_amount(item.actual_amount), item.remark.strip()))
    actor = await db.scalar(select(User).where(User.username == identity["username"]));
    if not actor:
        raise HTTPException(status_code=401, detail="当前用户不存在")
    case_record = await db.get(BusinessRecord, case_id)
    source_fee = await db.get(BusinessRecord, body.source_fee_id)
    source_data = source_fee.data or {}
    refund_commission = source_data.get("refund_fee") is True and source_data.get("fee_type") == "代理费"
    initial_status = "待审批" if refund_commission else "待结算"
    application_no = _new_internal_payment_package_no()
    applied_at = datetime.now().isoformat(timespec="seconds")
    created: list[BusinessRecord] = []
    for template, amount, remark in normalized:
        serial = f"FY{datetime.now():%Y%m%d%H%M%S%f}{len(created):02d}"
        record = BusinessRecord(
            module="finance", serial_no=serial,
            title=f"{case_record.serial_no} {template['commission_type']}",
            customer=case_record.customer, status=initial_status,
            owner=template["employee_username"] or identity["username"],
            department=actor.department, description=remark,
            data={
                "amount": amount, "fee_type": "内部费用", "expense_scope": "内部",
                "expense_subtype": template["expense_subtype"],
                "case_no": case_record.serial_no, "case_id": case_record.id,
                "contract_id": (case_record.data or {}).get("contract_id"),
                "contract_no": (case_record.data or {}).get("contract_no", ""),
                "handler": identity["username"], "payee": template["employee_username"],
                "payee_display_name": template["employee_display_name"],
                "base_amount": template["base_amount"],
                "reference_commission": template["reference_commission"],
                "commission_type": template["commission_type"],
                "commission_role": template["commission_role"],
                "source_fee_id": source_fee.id, "source_fee_no": source_fee.serial_no,
                "source_fee_amount": preview["source_fee"]["amount"],
                "payment_application_no": application_no,
                "payment_requested_amount": amount,
                "payment_status": initial_status,
                "commission_lifecycle": "case_agency_refund" if refund_commission else "case_agency_fee",
                "is_refund": refund_commission,
                "commission_created_at": applied_at,
                "commission_created_by": identity["username"],
                "applicant": identity["username"],
                "application_date": applied_at[:10],
            },
        )
        db.add(record); await db.flush()
        db.add(WorkflowEvent(
            record_id=record.id, action="创建案件提成", to_status=initial_status,
            operator=identity["username"],
            comment=f"{application_no}｜{template['employee_display_name']}｜{template['commission_type']}｜{amount:.2f} 元｜来源 {source_fee.serial_no}",
        ))
        created.append(record)
    await _sync_case_commission_lifecycle(
        created, db, operator=identity["username"], comment="根据来源代理费结算及案件归档事实初始化提成状态",
    )
    await db.commit()
    for record in created:
        await db.refresh(record)
    return {
        "application_no": application_no,
        "application_date": applied_at[:10],
        "items": await _record_dicts_for_identity(created, identity, db),
        "payment_items": [
            {
                "record_id": record.id,
                "application_no": application_no,
                "payee": str((record.data or {}).get("payee_display_name") or record.owner),
                "commission_type": str((record.data or {}).get("commission_type") or record.title),
                "amount": _round_fee_amount(float((record.data or {}).get("amount") or 0)),
                "case_no": case_record.serial_no,
                "application_date": applied_at[:10],
            }
            for record in created
        ],
        "total": len(created),
    }


@router.post(f"{settings.api_prefix}/cases/batch-update")
async def batch_update_cases(body: CaseBatchUpdateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_commission_personnel_changed, _case_team_payload, _recalculate_case_draft_commissions, _resolve_active_case_people,
    )
    from app.core.permissions import (
        _record_dicts_for_identity, _record_scope_conditions, _require_case_creation_completed,
    )
    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以批量修改案件")
    changes_requested = any(value is not None for value in (body.hearing_lawyer, body.handling_lawyers, body.assistant, body.case_stage, body.source_lawyer, body.litigation_amount))
    if not changes_requested:
        raise HTTPException(status_code=422, detail="请至少提供一个需要修改的案件字段")
    case_ids = list(dict.fromkeys(body.case_ids))
    case_nos = list(dict.fromkeys(value.strip() for value in body.case_nos if value.strip()))
    if not case_ids and not case_nos:
        raise HTTPException(status_code=422, detail="请至少选择一个案件 ID 或案号")
    if len(case_ids) + len(case_nos) > 100:
        raise HTTPException(status_code=422, detail="单次最多批量修改 100 个案件")
    handling_lawyers: list[str] | None = None
    handling_usernames: list[str] | None = None
    assistant_value: str | None = None
    assistant_username: str | None = None
    hearing_value: str | None = None
    hearing_username: str | None = None
    if body.hearing_lawyer is not None:
        hearing_values, hearing_usernames = await _resolve_active_case_people(
            [body.hearing_lawyer] if body.hearing_lawyer.strip() else [], db, field_name="开庭律师",
        )
        hearing_value = hearing_values[0] if hearing_values else ""
        hearing_username = hearing_usernames[0] if hearing_usernames else ""
    if body.handling_lawyers is not None:
        handling_lawyers, handling_usernames = await _resolve_active_case_people(body.handling_lawyers, db, field_name="经办律师")
        if not handling_lawyers:
            raise HTTPException(status_code=422, detail="请至少保留一名有效经办律师")
    if body.assistant is not None:
        assistant_values, assistant_usernames = await _resolve_active_case_people([body.assistant] if body.assistant.strip() else [], db, field_name="律师助理")
        assistant_value = assistant_values[0] if assistant_values else ""
        assistant_username = assistant_usernames[0] if assistant_usernames else ""
    requested = []
    if case_ids: requested.append(BusinessRecord.id.in_(case_ids))
    if case_nos: requested.append(BusinessRecord.serial_no.in_(case_nos))
    visible_cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case", or_(*requested), *(await _record_scope_conditions(identity, db)),
    ))).all())
    by_id = {case.id: case for case in visible_cases}; by_no = {case.serial_no: case for case in visible_cases}
    missing_ids = [case_id for case_id in case_ids if case_id not in by_id]
    missing_nos = [case_no for case_no in case_nos if case_no not in by_no]
    if missing_ids or missing_nos:
        parts = []
        if missing_ids: parts.append("ID：" + "、".join(str(value) for value in missing_ids))
        if missing_nos: parts.append("案号：" + "、".join(missing_nos))
        raise HTTPException(status_code=404, detail="案件不存在或无权访问（" + "；".join(parts) + "）")
    cases = []
    for case in [*(by_id[value] for value in case_ids), *(by_no[value] for value in case_nos)]:
        if all(existing.id != case.id for existing in cases): cases.append(case)
    if body.case_stage is not None:
        for case in cases:
            await require_conflict_clear(case, db, action="批量修改案件阶段")
    for case in cases:
        _require_case_creation_completed(case)
        if case.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
            raise HTTPException(status_code=409, detail=f"案件 {case.serial_no} 已进入归档流程，不能批量修改")
        before_data = dict(case.data or {})
        data = dict(before_data)
        changes = []
        if body.hearing_lawyer is not None:
            changes.append(f"开庭律师：{data.get('hearing_lawyer', '')} → {hearing_value or ''}")
            data["hearing_lawyer"] = hearing_value or ""
            data["hearing_lawyer_username"] = hearing_username or ""
        if body.handling_lawyers is not None:
            changes.append(f"经办律师：{','.join(data.get('handling_lawyers') or [])} → {','.join(handling_lawyers or [])}")
            data = _case_team_payload(data, handling_lawyers or [], handling_usernames or [], data.get("assistant", ""), str(data.get("assistant_username") or ""))
        if body.assistant is not None:
            changes.append(f"律师助理：{data.get('assistant', '')} → {assistant_value or ''}")
            data = _case_team_payload(data, list(data.get("handling_lawyers") or []), list(data.get("handling_lawyer_usernames") or []), assistant_value or "", assistant_username or "")
        if body.case_stage is not None:
            changes.append(f"案件阶段：{data.get('case_stage') or case.status} → {body.case_stage.strip()}")
            data["case_stage"] = body.case_stage.strip()
        if body.source_lawyer is not None:
            changes.append(f"案源人：{data.get('source_lawyer', '')} → {body.source_lawyer.strip()}")
            data["source_lawyer"] = body.source_lawyer.strip()
        if body.litigation_amount is not None:
            changes.append(f"诉讼标的：{data.get('litigation_amount', 0)} → {body.litigation_amount}")
            data["litigation_amount"] = body.litigation_amount
        case.data = data
        await assess_conflict_review(case, identity, db, trigger="case_save")
        gate = await get_conflict_review_gate(case, db, action="批量修改案件阶段")
        if gate["blocking"] and body.case_stage is not None:
            restored_data = dict(case.data or {})
            if "case_stage" in before_data:
                restored_data["case_stage"] = before_data["case_stage"]
            else:
                restored_data.pop("case_stage", None)
            case.data = restored_data
            changes = [item for item in changes if not item.startswith("案件阶段：")]
            changes.append("案件阶段未变更：待利益冲突核查")
        if _case_commission_personnel_changed(before_data, data):
            await _recalculate_case_draft_commissions(case, db, identity["username"])
        db.add(WorkflowEvent(record_id=case.id, action="批量修改案件", from_status=case.status, to_status=case.status, operator=identity["username"], comment="；".join(changes + ([body.comment.strip()] if body.comment.strip() else []))))
    await db.commit()
    for case in cases:
        await db.refresh(case)
    return {"updated": len(cases), "items": await _record_dicts_for_identity(cases, identity, db)}


from app.areas.legal.case_events import (
    router as case_events_router,
    list_case_reminders as list_case_reminders,
    list_case_events as list_case_events,
    create_case_event as create_case_event,
    update_case_event as update_case_event,
    delete_case_event as delete_case_event,
    batch_delete_case_events as batch_delete_case_events,
    create_case_reminder as create_case_reminder,
    delete_case_reminder as delete_case_reminder,
    list_case_logs as list_case_logs,
)
router.include_router(case_events_router)


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/relations")
async def list_case_relations(
    case_id: int,
    clue_page: Annotated[int | None, Query(ge=1)] = None,
    clue_page_size: Annotated[int | None, Query(ge=1, le=200)] = None,
    clue_keyword: str = "",
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Return one case's related records, with opt-in clue search and pagination.

    Existing consumers receive the original complete ``clues`` array when no
    clue query option is supplied.  The case-detail clue tab can opt into a
    page without changing the fee relation payload or the old response shape.
    """
    from app.core.finance import (
        _case_fee_link_maps, _incoming_payment_legacy_summary, _invoice_linked_fee_ids, _resolve_case_fee_link_id, _round_fee_amount,
    )
    from app.core.formatters import (
        _person_reference_display, _user_display_map,
    )
    from app.core.legacy_sync import (
        _legacy_case_fee_projection,
    )
    from app.core.permissions import (
        _ensure_case_read_module,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_case_read_module(case_id, identity, db)
    case_data = case_record.data or {}
    raw_clue_nos = case_data.get("investigation_clue_nos") or case_data.get("clue_nos") or []
    if isinstance(raw_clue_nos, str):
        clue_nos = [value.strip() for value in re.split(r"[,，;；、|]+", raw_clue_nos) if value.strip()]
    else:
        clue_nos = [str(value or "").strip() for value in raw_clue_nos if str(value or "").strip()]
    for value in (case_data.get("clue_no"), case_data.get("investigation_clue"), case_data.get("source_clue_no")):
        normalized = str(value or "").strip()
        if normalized and normalized not in clue_nos:
            clue_nos.append(normalized)
    raw_clue_ids = case_data.get("investigation_clue_ids") if isinstance(case_data.get("investigation_clue_ids"), list) else []
    clue_ids = {
        int(value)
        for value in (
            case_data.get("clue_id"), case_data.get("clue_record_id"),
            case_data.get("investigation_clue_id"), *raw_clue_ids,
        )
        if str(value or "").isdigit() and int(value) > 0
    }
    link_condition = or_(
        BusinessRecord.data["case_id"].as_integer() == case_record.id,
        BusinessRecord.data["case_record_id"].as_integer() == case_record.id,
        BusinessRecord.data["converted_case_id"].as_integer() == case_record.id,
        BusinessRecord.data["case_no"].as_string() == case_record.serial_no,
        BusinessRecord.data["converted_case_no"].as_string() == case_record.serial_no,
    )
    fees = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance", BusinessRecord.status != "已删除", link_condition,
    ).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()))).all())
    # A converted case owns an explicit source-clue relation.  Do not union that
    # relation with stale reverse links left on other clues during migration or
    # an earlier conversion; doing so makes one selected clue look like many.
    if clue_ids:
        clue_condition = BusinessRecord.id.in_(clue_ids)
    elif clue_nos:
        clue_condition = BusinessRecord.serial_no.in_(list(dict.fromkeys(clue_nos)))
    else:
        clue_condition = link_condition
    clues = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "clue", clue_condition,
    ).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()))).all())
    clue_query_requested = clue_page is not None or clue_page_size is not None or bool(clue_keyword.strip())
    if clue_keyword.strip():
        keyword = clue_keyword.strip().casefold()
        clue_search_fields = (
            "shop_name", "store_name", "shop_address", "address", "location_address",
            "platform", "product", "certificate_no", "notary_no", "notarization_no",
        )
        clues = [
            item for item in clues
            if keyword in " ".join(
                str(value or "") for value in (
                    item.serial_no, item.title, item.customer, item.description,
                    *((item.data or {}).get(field) for field in clue_search_fields),
                )
            ).casefold()
        ]
    clue_total = len(clues)
    effective_clue_page = clue_page or 1
    effective_clue_page_size = clue_page_size or 15
    clue_pages = (clue_total + effective_clue_page_size - 1) // effective_clue_page_size if clue_total else 0
    if clue_query_requested:
        clue_start = (effective_clue_page - 1) * effective_clue_page_size
        paged_clues = clues[clue_start:clue_start + effective_clue_page_size]
    else:
        paged_clues = clues
    refunds = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "refund"))).all())
    refunds_by_fee: dict[int, list[BusinessRecord]] = {}
    for refund in refunds:
        try:
            fee_id = int((refund.data or {}).get("fee_record_id") or 0)
        except (TypeError, ValueError):
            fee_id = 0
        if fee_id:
            refunds_by_fee.setdefault(fee_id, []).append(refund)
    fee_ids, legacy_fee_ids = _case_fee_link_maps(fees)
    fees_by_id = {item.id: item for item in fees}
    active_invoices_by_fee: dict[int, BusinessRecord] = {}
    if fee_ids:
        invoices = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "invoice",
            BusinessRecord.status.not_in(INVOICE_RELEASED_STATUSES),
        ).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()))).all())
        for invoice in invoices:
            for fee_id in _invoice_linked_fee_ids(invoice.data or {}):
                if fee_id in fee_ids:
                    active_invoices_by_fee.setdefault(fee_id, invoice)
    incoming_by_fee: dict[int, dict] = {}
    if fee_ids:
        # Allocations are durable links to fees.  Customer names are snapshots and
        # may diverge after a customer rename, so they must not gate case-fee
        # receipt projection.
        incoming_payments = list((await db.scalars(select(IncomingPayment).order_by(
            IncomingPayment.received_date.desc(), IncomingPayment.id.desc(),
        ))).all())
        for payment in incoming_payments:
            for allocation in payment.allocations or []:
                allocation_case_no = str(allocation.get("case_no") or "").strip()
                direct_fee_id = _resolve_case_fee_link_id(allocation, fee_ids, legacy_fee_ids)
                settlement_rows = allocation.get("settlement_items") if isinstance(allocation.get("settlement_items"), list) else []
                matched_amounts: dict[int, float] = {}
                direct_fee = fees_by_id.get(direct_fee_id)
                direct_case_no = str(((direct_fee.data or {}) if direct_fee else {}).get("case_no") or "").strip()
                if direct_fee_id in fee_ids and (not allocation_case_no or allocation_case_no == direct_case_no):
                    matched_amounts[direct_fee_id] = float(allocation.get("amount") or 0)
                for settlement in settlement_rows:
                    if not isinstance(settlement, dict):
                        continue
                    settlement_fee_id = _resolve_case_fee_link_id(settlement, fee_ids, legacy_fee_ids)
                    settlement_fee = fees_by_id.get(settlement_fee_id)
                    settlement_case_no = str(((settlement_fee.data or {}) if settlement_fee else {}).get("case_no") or "").strip()
                    if (
                        settlement_fee_id in fee_ids
                        and settlement_fee_id not in matched_amounts
                        and (not allocation_case_no or allocation_case_no == settlement_case_no)
                    ):
                        matched_amounts[settlement_fee_id] = float(
                            settlement.get("amount") or settlement.get("settlement_amount") or 0
                        )
                for fee_id, matched_amount in matched_amounts.items():
                    summary = incoming_by_fee.setdefault(fee_id, {
                        "incoming_payment_id": payment.id,
                        "receipt_no": payment.receipt_no,
                        "received_at": payment.received_date.isoformat(),
                        "received_amount": 0.0,
                        "incoming_payments": [],
                    })
                    summary["received_amount"] = _round_fee_amount(summary["received_amount"] + matched_amount)
                    payment_summary = _incoming_payment_legacy_summary(payment)
                    summary["incoming_payments"].append({
                        "id": payment.id,
                        "receipt_no": payment.receipt_no,
                        "received_date": payment.received_date.isoformat(),
                        "allocated_amount": _round_fee_amount(matched_amount),
                        "amount": _round_fee_amount(float(payment.amount)),
                        "payer_name": payment.payer_name,
                        "bank_reference": payment.bank_reference,
                        "status": payment.status,
                        **payment_summary,
                    })
    users_by_username = await _user_display_map({item.owner for item in [*fees, *clues]}, db)

    def related_dict(item: BusinessRecord) -> dict:
        result = _record_dict(item)
        result["owner_display_name"] = _person_reference_display(item.owner, users_by_username)[0]
        result_data = _legacy_case_fee_projection(result.get("data") or {}) if item.module == "finance" else dict(result.get("data") or {})
        linked_invoice = active_invoices_by_fee.get(item.id)
        if linked_invoice:
            invoice_data = linked_invoice.data or {}
            result_data["invoice_status"] = "已开票" if linked_invoice.status == "已开票" else "已申请"
            result_data["invoice_application_no"] = linked_invoice.serial_no
            result_data["invoice_record_id"] = linked_invoice.id
            result_data["invoice_no"] = invoice_data.get("invoice_no") or result_data.get("invoice_no") or ""
            result_data["invoice_date"] = invoice_data.get("invoice_date") or result_data.get("invoice_date") or ""
        linked_incoming = incoming_by_fee.get(item.id)
        if linked_incoming:
            result_data.update(linked_incoming)
            result_data["cashed_date"] = linked_incoming["received_at"]
        if str((item.data or {}).get("fee_type") or "") in {"官方费用", "代理费"}:
            linked = refunds_by_fee.get(item.id, [])
            if linked:
                valid_refunds = [refund for refund in linked if refund.status not in {"已驳回", "已作废"}]
                total_refund = round(sum(float((refund.data or {}).get("amount") or 0) for refund in valid_refunds), 2)
                refunded_amount = round(sum(float((refund.data or {}).get("amount") or 0) for refund in valid_refunds if refund.status == "已退款"), 2)
                result_data["refund_amount"] = total_refund
                result_data["refund_requested_amount"] = total_refund
                result_data["refunded_amount"] = refunded_amount
            from app.core.finance_batch_parity import official_refund_progress
            result_data["refunded_amount"] = official_refund_progress(
                result_data,
                float(result_data.get("refund_amount") or result_data.get("refund_requested_amount") or 0),
                max(float(result_data.get("refunded_amount") or 0), float((item.data or {}).get("refunded_amount") or 0)),
            )
        result["data"] = result_data
        return result

    from app.core.case_relations import case_source_projection
    return {
        "case_data": await case_source_projection(case_record, identity, db),
        "case_id": case_record.id,
        "case_no": case_record.serial_no,
        "fees": [related_dict(item) for item in fees],
        "clues": [related_dict(item) for item in paged_clues],
        "fee_total": len(fees),
        "clue_total": clue_total,
        "clue_page": effective_clue_page,
        "clue_page_size": effective_clue_page_size,
        "clue_pages": clue_pages,
    }


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/logs", status_code=status.HTTP_201_CREATED)
async def create_case_log(case_id: int, body: CaseLogInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _require_case_note_write_access,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_note_write_access(case_record, identity, db, "case.log.create")
    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="请输入日志内容")
    if body.kind == "refund" and body.case_fee_id is not None:
        from app.core.refund_logs import refund_fee_case
        case_fee = await db.scalar(select(BusinessRecord).where(
            BusinessRecord.id == body.case_fee_id,
            BusinessRecord.module == "finance",
        ))
        linked_case = await refund_fee_case(case_fee, db) if case_fee else None
        if not linked_case or linked_case.id != case_record.id:
            raise HTTPException(status_code=422, detail="所选案件费用不属于当前案件")
    log_record = BusinessRecord(
        module="case_log", serial_no=f"CASELOG-{uuid4().hex.upper()}",
        title="退费日志" if body.kind == "refund" else "案件日志",
        customer=case_record.customer, status="有效", owner=identity["username"], department=case_record.department,
        description=content, data={
            "kind": body.kind, "case_id": case_record.id, "case_no": case_record.serial_no,
            "case_fee_id": body.case_fee_id,
        },
    )
    db.add(log_record)
    event = WorkflowEvent(
        record_id=case_record.id, action="新增案件日志", from_status=case_record.status,
        to_status=case_record.status, operator=identity["username"], comment=content,
    )
    db.add(event)
    await db.commit()
    await db.refresh(log_record)
    return {"id": f"business-{log_record.id}", "content": log_record.description, "operator": log_record.owner, "created_at": log_record.created_at, "kind": body.kind, "case_fee_id": body.case_fee_id}


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/documents/generate", name="generate_case_document")
async def download_case_document_template(
    case_id: int,
    doc_type: str = Query(..., description="文档类型：authorization(授权委托书)/law-firm-letter(律所函)/identity(身份证明)/settlement(结算提成表)"),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.documents import (
        _build_case_template_data, _fill_template,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    template = _BUILTIN_DOCUMENT_TEMPLATES.get(doc_type)
    if not template:
        raise HTTPException(status_code=400, detail="不支持的文档类型")
    case_data = _build_case_template_data(case_record)
    filled_content = _fill_template(template["content"], case_data)
    doc = Document()
    for paragraph_text in filled_content.split("\n"):
        paragraph = doc.add_paragraph()
        run = paragraph.add_run(paragraph_text)
        run.font.name = "宋体"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
        if paragraph_text.startswith("　　") or paragraph_text == paragraph_text.lstrip():
            pass
        if any(keyword in paragraph_text for keyword in ["授 权", "律师事务所函", "身 份", "案 件 结 算"]):
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run.font.size = Pt(18)
            run.bold = True
    import io
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    filename = f"{template['name']}-{case_data['case_no']}.docx"
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename.encode('utf-8').decode('latin-1')}"},
    )


@router.post(f"{settings.api_prefix}/cases/batch-fees", status_code=status.HTTP_201_CREATED)
async def create_case_batch_fees(body: CaseBatchFeeInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _case_fee_type_snapshot, _resolve_case_fee_contract, _resolve_case_fee_type_master, _round_fee_amount,
    )
    from app.core.permissions import (
        _record_dicts_for_identity, _record_scope_conditions, _require_case_action,
    )
    if len(set(body.case_ids)) != len(body.case_ids):
        raise HTTPException(status_code=422, detail="批量费用案件不能重复")
    case_ids = list(body.case_ids)
    cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case", BusinessRecord.id.in_(case_ids),
        *(await _record_scope_conditions(identity, db)),
    ))).all())
    if len(cases) != len(case_ids):
        raise HTTPException(status_code=404, detail="存在无权访问或不存在的案件")
    expected_fee_type = EXPENSE_SUBTYPE_FEE_TYPE.get(body.expense_subtype, "")
    fee_parameter, fee_option = await _resolve_case_fee_type_master(
        body.fee_type_id, body.expense_scope, db,
        legacy_name=body.expense_subtype, legacy_base=expected_fee_type,
    )
    fee_snapshot = _case_fee_type_snapshot(fee_parameter, fee_option)
    if body.expense_subtype != fee_parameter.name:
        raise HTTPException(status_code=422, detail="费用子类型与系统费用分类不一致")
    handler = body.handler.strip() or identity["username"]
    if identity.get("role") == "user":
        handler = identity["username"]
    handler_user = await db.scalar(select(User).where(User.username == handler, User.is_active.is_(True)))
    if not handler_user:
        raise HTTPException(status_code=422, detail="费用经办人不存在或已停用")
    ordered_cases = sorted(cases, key=lambda item: case_ids.index(item.id))
    contract_ids_by_case: dict[int, int] = {}
    for mapping in body.case_contracts:
        if mapping.case_id not in case_ids:
            raise HTTPException(status_code=422, detail=f"案件 {mapping.case_id} 不在本次批量费用范围内")
        if mapping.case_id in contract_ids_by_case:
            raise HTTPException(status_code=422, detail=f"案件 {mapping.case_id} 存在重复合同映射")
        contract_ids_by_case[mapping.case_id] = mapping.contract_record_id
    if body.expense_scope != "内部":
        missing_contract_cases = [item.serial_no for item in ordered_cases if item.id not in contract_ids_by_case]
        if missing_contract_cases:
            raise HTTPException(status_code=422, detail="非内部案件费用必须逐案明确合同：" + "、".join(missing_contract_cases))
    contracts_by_case: dict[int, BusinessRecord | None] = {}
    for case_record in ordered_cases:
        await _require_case_action(identity, db, "case.fee.create")
        if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
            raise HTTPException(status_code=409, detail=f"案件 {case_record.serial_no} 已进入归档流程，不能新增费用")
        contract_record = None
        contract_id = contract_ids_by_case.get(case_record.id)
        if contract_id:
            contract_record = await db.get(BusinessRecord, contract_id)
            if not contract_record or contract_record.module != "contract":
                raise HTTPException(status_code=422, detail=f"案件 {case_record.serial_no} 选择的关联记录不是合同")
        contracts_by_case[case_record.id] = await _resolve_case_fee_contract(
            case_record, contract_record, body.expense_scope, identity, db,
        )
    created: list[BusinessRecord] = []
    amount = _round_fee_amount(body.amount)
    for case_record in ordered_cases:
        contract_record = contracts_by_case[case_record.id]
        serial = f"FY{datetime.now():%Y%m%d%H%M%S%f}{uuid4().hex[:6]}"
        item = BusinessRecord(
            module="finance", serial_no=serial, title=f"{case_record.title}{fee_parameter.name}",
            customer=case_record.customer, status="草稿", owner=handler,
            department=case_record.department, description=body.description,
            data={"amount": amount, **fee_snapshot,
                  "expense_scope": body.expense_scope,
                  "is_refund": False, "case_no": case_record.serial_no, "case_id": case_record.id,
                  "contract_id": contract_record.id if contract_record else None,
                  "contract_no": contract_record.serial_no if contract_record else "",
                  "handler": handler, "court": (case_record.data or {}).get("court", ""),
                  "document_no": "", "payee": (case_record.data or {}).get("court", "")},
        )
        db.add(item)
        await db.flush()
        created.append(item)
        db.add(WorkflowEvent(record_id=item.id, action="批量创建案件费用", to_status="草稿", operator=identity["username"], comment=f"{case_record.serial_no}｜{fee_option['path']}：{amount:.2f} 元"))
        db.add(WorkflowEvent(record_id=case_record.id, action="批量新增案件费用", from_status=case_record.status, to_status=case_record.status, operator=identity["username"], comment=f"{item.serial_no}｜{fee_option['path']}：{amount:.2f} 元"))
    await db.commit()
    for item in created:
        await db.refresh(item)
    return {"created": len(created), "items": await _record_dicts_for_identity(created, identity, db)}


@router.get(f"{settings.api_prefix}/cases/summary")
async def case_summary(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _record_scope_conditions,
    )
    counts = dict((await db.execute(select(BusinessRecord.status, func.count()).where(
        BusinessRecord.module == "case", *(await _record_scope_conditions(identity, db)),
    ).group_by(BusinessRecord.status))).all())
    return {
        "total": sum(counts.values()),
        "pending_assignment": counts.get("新案待分配", 0),
        "in_progress": sum(count for status, count in counts.items() if status not in {"新案待分配", "已归档"}),
        "execution": counts.get("执行", 0),
        "archived": counts.get("已归档", 0),
    }


@router.get(f"{settings.api_prefix}/cases/pending-execution")
async def list_pending_execution_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.cases import (
        _is_pending_execution_case,
    )
    from app.core.contracts import (
        _contract_customer_record_dicts,
    )
    from app.core.permissions import (
        _record_scope_conditions, _require_record_module_menu,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    await _require_record_module_menu("case", identity, db, action="查看")
    records = list((await db.scalars(
        select(BusinessRecord).where(
            BusinessRecord.module == "case",
            *(await _record_scope_conditions(identity, db)),
        ).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc())
    )).all())
    pending = [record for record in records if _is_pending_execution_case(record)]
    total = len(pending)
    start = (page - 1) * page_size
    allowed_fields = await _allowed_field_keys(identity, db)
    return {
        "items": await _contract_customer_record_dicts(
            pending[start:start + page_size], allowed_fields, db, identity=identity,
        ),
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
    }


@router.get(f"{settings.api_prefix}/cases/invoice-files")
async def list_case_invoice_files(
    page: int = Query(1, ge=1), page_size: int = Query(200, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.case_invoice_files import invoice_file_rows
    return await invoice_file_rows(identity, db, page, page_size)


@router.post(f"{settings.api_prefix}/cases/invoice-files/import")
async def import_case_invoice_files(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.case_invoice_files import import_invoice_files
    return await import_invoice_files(identity, db)


@router.post(f"{settings.api_prefix}/cases/counsel/search")
async def search_counsel_cases(body: CounselCaseSearchInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _query_counsel_cases,
    )
    from app.core.contracts import (
        _contract_customer_record_dicts,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    records = await _query_counsel_cases(body, identity, db)
    total = len(records)
    start = (body.page - 1) * body.page_size
    allowed_fields = await _allowed_field_keys(identity, db)
    return {
        "items": await _contract_customer_record_dicts(
            records[start:start + body.page_size], allowed_fields, db, identity=identity
        ),
        "total": total,
        "page": body.page,
        "page_size": body.page_size,
        "pages": (total + body.page_size - 1) // body.page_size if total else 0,
    }


@router.post(f"{settings.api_prefix}/cases/search")
async def search_ordinary_cases(body: CounselCaseSearchInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Server-side ordinary-case search; unlike the legacy UI it never truncates to the first 100 rows."""
    from app.core.cases import (
        _query_counsel_cases,
    )
    from app.core.contracts import (
        _contract_customer_record_dicts,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    from app.core.case_search_projection import matches_case_search_status, read_case_search_page
    from app.core.request_metrics import measure_phase
    # 阶段树和列表共用非阶段筛选结果，不重复读取所有案件。
    with measure_phase("cases.search"):
        count_records = await _query_counsel_cases(
            body, identity, db, counsel_only=False, include_status_filter=False, search_projection=True,
        )
    phase_counts: dict[str, int] = {}
    for record in count_records:
        phase = str(record.status or "")
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
    records = [record for record in count_records if matches_case_search_status(record, body)]
    total = len(records)
    allowed_fields = await _allowed_field_keys(identity, db)
    from app.core.case_list_tasks import attach_case_list_tasks
    with measure_phase("cases.page"):
        page_records = await read_case_search_page(records, body.page, body.page_size, db)
        items = await _contract_customer_record_dicts(page_records, allowed_fields, db, identity=identity)
    with measure_phase("cases.tasks"):
        await attach_case_list_tasks(items, identity, db)
    return {
        "items": items,
        "total": total,
        "page": body.page,
        "page_size": body.page_size,
        "pages": (total + body.page_size - 1) // body.page_size if total else 0,
        "phase_counts": phase_counts,
    }


@router.post(f"{settings.api_prefix}/cases/counsel/export")
async def export_counsel_cases(body: CounselCaseSearchInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _query_counsel_cases,
    )
    records = await _query_counsel_cases(body, identity, db)
    if body.selected_only:
        selected_ids = list(dict.fromkeys(body.selected_ids))
        if not selected_ids:
            raise HTTPException(status_code=422, detail="请选择需要导出的法律顾问案件")
        selected_set = set(selected_ids)
        records = [record for record in records if record.id in selected_set]
        if len(records) != len(selected_set):
            raise HTTPException(status_code=403, detail="选中的案件不存在、不可见或不符合当前查询条件")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["案件编号", "案件名称", "顾问类型", "客户", "顾问开始日期", "顾问结束日期", "经办律师", "律师助理", "案源人", "案件阶段", "所属部门"])
    for record in records:
        data = record.data or {}
        writer.writerow([
            record.serial_no, record.title, data.get("counsel_type", ""), record.customer,
            data.get("counsel_start", ""), data.get("counsel_end", ""),
            "、".join(data.get("handling_lawyers") or []), data.get("assistant", ""),
            data.get("source_person") or record.owner, record.status, record.department,
        ])
    scope_label = "selected" if body.selected_only else "all"
    content = ("\ufeff" + output.getvalue()).encode("utf-8")
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="counsel-cases-{scope_label}-{date.today()}.csv"'},
    )


@router.get(f"{settings.api_prefix}/cases/eligible-contracts")
async def list_case_eligible_contracts(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Return every visible contract that can actually start the staged case flow."""
    from app.core.contracts import (
        _contract_customer_record_dicts,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _allowed_field_keys,
    )
    conditions = [
        BusinessRecord.module == "contract",
        BusinessRecord.status != "草稿",
        *(await _record_scope_conditions(identity, db)),
    ]
    contracts = (await db.scalars(
        select(BusinessRecord).where(*conditions).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc())
    )).all()
    items = await _contract_customer_record_dicts(
        list(contracts), await _allowed_field_keys(identity, db), db, identity=identity,
    )
    return {"items": items, "total": len(contracts)}


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/fee-contracts")
async def list_case_fee_contracts(
    case_id: int,
    expense_scope: str = Query(pattern="^(律所|平台)$"),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Return every customer contract for a visible case and fee scope."""
    from app.core.finance import (
        _case_fee_contract_body,
    )
    from app.core.permissions import (
        _case_detail_action_capabilities, _ensure_record_module, _record_dicts_for_identity,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    capabilities = await _case_detail_action_capabilities(case_record, identity, db)
    if not capabilities["can_create_finance"]:
        raise HTTPException(status_code=403, detail="当前账号没有新增案件费用权限")
    contracts = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "contract",
        BusinessRecord.customer == case_record.customer,
    ).order_by(BusinessRecord.updated_at.desc(), BusinessRecord.id.desc()))).all())
    contracts = [item for item in contracts if _case_fee_contract_body(item) == expense_scope]
    return {"items": await _record_dicts_for_identity(contracts, identity, db), "total": len(contracts)}


@router.get(f"{settings.api_prefix}/cases/reference-options")
async def list_case_reference_options(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Return active case dictionaries needed by the staged create form."""
    from app.core.system import (
        _is_smoke_test_username,
    )
    case_types = (await db.scalars(select(SystemParameter).where(
        SystemParameter.category == "case_type", SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.sort_order, SystemParameter.id))).all()
    causes = (await db.scalars(select(SystemParameter).where(
        SystemParameter.category == "cause", SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.sort_order, SystemParameter.id))).all()
    case_file_types = (await db.scalars(select(SystemParameter).where(
        SystemParameter.category == "case_file_type", SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.sort_order, SystemParameter.id))).all()
    courts = (await db.scalars(select(SystemParameter).where(
        SystemParameter.category == "court", SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.sort_order, SystemParameter.id))).all()
    court_officers = (await db.scalars(select(SystemParameter).where(
        SystemParameter.category == "court_officer", SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.sort_order, SystemParameter.id))).all()
    file_type_relations = list((await db.scalars(select(CaseTypeFileTypeRelation))).all())
    case_type_ids_by_file_type: dict[int, list[int]] = {}
    for relation in file_type_relations:
        case_type_ids_by_file_type.setdefault(relation.file_type_id, []).append(relation.case_type_id)
    serialized_case_file_types = [{
        "id": item.id, "value": item.name, "label": item.name, "code": item.code,
        "parent_code": (item.extra or {}).get("parent_code", ""),
        "case_type_ids": sorted(case_type_ids_by_file_type.get(item.id, [])),
    } for item in case_file_types]
    # 普通案件的通用上传接口接受“普通附件”作为合法兜底；向客户端公开它，
    # 防止旧租户尚未配置案件文件类型时页面提交无效的静态分类。
    if not any(item["value"] == "普通附件" for item in serialized_case_file_types):
        serialized_case_file_types.append({"id": 0, "value": "普通附件", "label": "普通附件", "code": "COMMON", "parent_code": "", "case_type_ids": []})
    # users 是人员主数据；HR 业务记录仅保存员工扩展资料，不能限制已创建账号出现在人员选择器中。
    # 旧系统的人员选择器展示所有在职账号，因此兼容没有 HR 记录但已在系统创建的真实账号。
    active_users = (await db.scalars(select(User).where(
        User.is_active.is_(True),
    ).order_by(User.display_name, User.username))).all()
    people_options = []
    seen_usernames: set[str] = set()
    for item in active_users:
        username = item.username.strip().lower()
        if _is_smoke_test_username(item.username):
            continue
        if username in seen_usernames:
            continue
        seen_usernames.add(username)
        # A task is assigned to a login username, so its label must come from
        # that same identity.  HR archives are extension records and legacy
        # imports can contain conflicting rows for one username; allowing the
        # last HR row to overwrite the account name hides the real employee
        # from both owner and collaborator searches.
        display_name = str(item.display_name or "").strip() or item.username
        people_options.append({
            "value": item.username,
            "label": f"{display_name}（{item.department}）",
            "position": str((item.profile or {}).get("position") or (item.profile or {}).get("staff_role") or "").strip(),
        })
    # The legacy AvailableUsers endpoint searches every active staff account by
    # Chinese display name.  Although the old control is named
    # AssociateAvailableUser_Laywer, it does not filter by the HR position text;
    # filtering here made valid active employees impossible to select.
    lawyer_options = people_options
    return {
        "case_types": [{
            "id": item.id,
            "value": "民事案件" if item.name == "民事争议" else item.name,
            "label": item.name,
            "code": item.code,
        } for item in case_types],
        "causes": [{"value": item.name, "label": item.name, "code": item.code} for item in causes],
        "case_file_types": serialized_case_file_types,
        "courts": [{"value": item.name, "label": item.name, "code": item.code} for item in courts],
        "court_officers": [{"value": item.name, "label": item.name, "code": item.code, "court_code": (item.extra or {}).get("court_code", ""), "role": (item.extra or {}).get("role", ""), "phone": (item.extra or {}).get("phone", "")} for item in court_officers],
        "case_lawyers": lawyer_options,
        "case_assistants": people_options,
        "right_types": ["商标权", "专利权", "著作权", "不正当竞争", "商业秘密", "其他"],
    }


@router.post(f"{settings.api_prefix}/cases", status_code=status.HTTP_201_CREATED)
async def create_case(body: CaseCreateInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """从有效合同建立案件；客户、部门和合同编号均以合同资料为准。"""
    from app.core.cases import (
        _case_team_payload, _next_case_serial, _resolve_active_case_people,
    )
    from app.core.contracts import (
        _contract_allows_downstream_creation,
    )
    from app.core.crm import (
        _customer_reference_from_maps, _persist_case_litigant_customers,
    )
    from app.core.formatters import (
        _normalized_customer_name, _person_display_name,
    )
    from app.core.legacy_sync import (
        _sync_legacy_projection,
    )
    from app.core.permissions import (
        _ensure_record_visible, _permission_payload_for_identity,
    )
    from app.core.projections import (
        _contract_customer_projection_context,
    )
    from app.core.system import (
        _record_dict,
    )
    title = body.title.strip()
    case_type = body.case_type.strip()
    cause_or_charge = body.cause_or_charge.strip()
    if not title:
        raise HTTPException(status_code=422, detail="案件名称不能为空")
    if case_type not in CASE_CREATABLE_TYPES:
        raise HTTPException(status_code=422, detail="案件类型不是原系统允许的新建类型")
    serial_no = body.serial_no.strip() or await _next_case_serial(case_type, db)
    canonical_status = CASE_CREATE_STATUS_ALIASES.get(body.status.strip())
    if canonical_status is None:
        raise HTTPException(status_code=422, detail="新建案件阶段必须为待分配")
    counsel_type = body.counsel_type.strip()
    if case_type != "法律顾问" and not cause_or_charge:
        raise HTTPException(status_code=422, detail="罪名或案由不能为空")
    if case_type == "法律顾问":
        if not counsel_type:
            raise HTTPException(status_code=422, detail="顾问类型不能为空")
        if len(counsel_type) > 128:
            raise HTTPException(status_code=422, detail="顾问类型过长")
        if not body.counsel_start or not body.counsel_end:
            raise HTTPException(status_code=422, detail="顾问期限不能为空")
        if body.counsel_start > body.counsel_end:
            raise HTTPException(status_code=422, detail="顾问结束日期不能早于开始日期")
        cause_or_charge = ""
    elif counsel_type or body.counsel_start or body.counsel_end:
        raise HTTPException(status_code=422, detail="仅法律顾问案件可以填写顾问类型和顾问期限")
    handling_lawyers = list(dict.fromkeys(str(item or "").strip() for item in body.handling_lawyers if str(item or "").strip()))
    if not handling_lawyers or any(len(item) > 128 for item in handling_lawyers):
        raise HTTPException(status_code=422, detail="请按顺序录入有效的经办律师")
    client_position = body.client_position.strip()
    if case_type == "法律顾问":
        client_position = ""
    allowed_client_positions = CASE_CLIENT_POSITIONS_BY_TYPE.get(case_type)
    if allowed_client_positions and client_position not in allowed_client_positions:
        raise HTTPException(status_code=422, detail=f"{case_type}客户诉讼地位无效")
    if case_type == "行政案件及国家赔偿" and client_position not in ADMINISTRATIVE_CLIENT_POSITIONS:
        raise HTTPException(status_code=422, detail="行政案件客户诉讼地位无效")
    right_type = body.right_type.strip()
    if case_type == "法律顾问":
        right_type = ""
    if len(right_type) > 128:
        raise HTTPException(status_code=422, detail="权利类型过长")
    assistant = body.assistant.strip()
    if len(assistant) > 128:
        raise HTTPException(status_code=422, detail="律师助理姓名过长")
    creator_user = await db.scalar(select(User).where(User.username == identity["username"], User.is_active.is_(True)))
    creator_label = str(creator_user.display_name if creator_user else identity["username"]).strip()
    creator_selection = len(handling_lawyers) == 1 and handling_lawyers[0] in {identity["username"], creator_label}
    if creator_selection and creator_user:
        handling_lawyers, handling_usernames = [creator_label], [creator_user.username]
    else:
        handling_lawyers, handling_usernames = await _resolve_active_case_people(handling_lawyers, db, field_name="经办律师")
    assistant_values, assistant_usernames = await _resolve_active_case_people([assistant] if assistant else [], db, field_name="律师助理")
    assistant = assistant_values[0] if assistant_values else ""
    assistant_username = assistant_usernames[0] if assistant_usernames else ""
    permission_key = CASE_CREATE_PERMISSION_BY_TYPE[case_type]
    if identity.get("role") != "admin":
        permission = await _permission_payload_for_identity(identity, db)
        if permission_key not in set(permission.get("menu_keys", [])):
            raise HTTPException(status_code=403, detail="当前角色没有该案件类型的新建权限")
    contract = await _ensure_record_visible(body.contract_record_id, identity, db)
    if contract.module != "contract":
        raise HTTPException(status_code=422, detail="关联记录不是合同")
    if not _contract_allows_downstream_creation(contract):
        raise HTTPException(status_code=409, detail="草稿合同不能新建案件")
    contract_context = await _contract_customer_projection_context([contract], db)
    contract_customer, relation_status = _customer_reference_from_maps(
        contract.customer,
        contract.data or {},
        contract_context["customers_by_id"],
        contract_context["customers_by_no"],
        contract_context["customers_by_name"],
    )
    if not contract_customer:
        detail = "关联合同未绑定唯一有效客户，不能新建案件"
        if relation_status.startswith("ambiguous"):
            detail = "关联合同客户名称存在重名，必须先绑定明确客户后再新建案件"
        raise HTTPException(status_code=409, detail=detail)
    requested_customer_id = body.customer_record_id or body.customer_id
    if requested_customer_id and requested_customer_id != contract_customer.id:
        raise HTTPException(status_code=422, detail="所选客户与关联合同绑定客户不一致")
    if body.customer_no.strip() and body.customer_no.strip() != contract_customer.serial_no:
        raise HTTPException(status_code=422, detail="客户编号与关联合同绑定客户不一致")
    if body.customer.strip() and _normalized_customer_name(body.customer) != _normalized_customer_name(contract_customer.title):
        raise HTTPException(status_code=422, detail="客户名称与关联合同绑定客户不一致")
    customer_data = contract_customer.data or {}
    customer_organization_type = str(customer_data.get("organization_type") or "").strip()
    customer_identity = str(customer_data.get("identity_no") if customer_organization_type == "个人" else customer_data.get("credit_code") or "").strip()
    if not customer_organization_type or not customer_identity:
        raise HTTPException(status_code=409, detail="客户缺少组织类型或唯一证件号，请先补齐客户资料后再新建案件")
    contract.data = {
        **(contract.data or {}),
        "customer_id": contract_customer.id,
        "customer_record_id": contract_customer.id,
        "customer_no": contract_customer.serial_no,
    }
    contract.customer = contract_customer.title
    department = contract.department.strip()
    if not department or not await db.scalar(select(Department.id).where(Department.name == department, Department.is_active.is_(True))):
        raise HTTPException(status_code=409, detail="关联合同没有有效的所属部门")
    if await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == serial_no)):
        raise HTTPException(status_code=409, detail="业务编号已存在")
    contract_data = contract.data or {}
    opponent = body.opponent.strip()
    source_token = body.source_person.strip() or str(contract_data.get("source_person") or contract.owner or "").strip()
    source_user = await db.scalar(select(User).where(User.username == source_token)) if source_token else None
    source_person, _ = _person_display_name(source_user.display_name, source_user.username) if source_user else (source_token, False)
    owner = body.owner.strip() or identity["username"]
    if identity.get("role") != "admin":
        user = await db.scalar(select(User).where(User.username == identity["username"]))
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="当前用户不存在")
        owner = user.username
    owner_user = await db.scalar(select(User).where(User.username == owner, User.is_active.is_(True)))
    if not owner_user:
        raise HTTPException(status_code=422, detail="案件负责人必须是有效用户")
    record = BusinessRecord(
        module="case", serial_no=serial_no, title=title,
        customer=contract_customer.title, status=canonical_status, owner=owner,
        department=department, description="",
        data={
            "contract_id": contract.id,
            "contract_no": contract.serial_no,
            "external_contract_no": contract_data.get("external_contract_no", ""),
            "external_contract_numbers": contract_data.get("external_contract_numbers", []),
            "contract_title": contract.title,
            "customer_id": contract_customer.id,
            "customer_record_id": contract_customer.id,
            "customer_no": contract_customer.serial_no,
            "case_type": case_type,
            "client_position": client_position,
            "opponent": opponent,
            "defendants": [opponent] if opponent else [],
            "cause_or_charge": cause_or_charge,
            "right_type": right_type,
            "source_person": source_person,
            "source_person_username": source_user.username if source_user else "",
            "investigator": body.investigator.strip(),
            "investigation_clue": body.investigation_clue.strip(),
            "counsel_type": counsel_type,
            "counsel_start": str(body.counsel_start) if body.counsel_start else "",
            "counsel_end": str(body.counsel_end) if body.counsel_end else "",
            **_case_team_payload({}, handling_lawyers, handling_usernames, assistant, assistant_username),
            "case_creation_step": "basic",
            "case_creation_approval_status": "未提交",
            "business_stage": "立案",
        },
    )
    db.add(record)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="业务编号已存在") from exc
    await _persist_case_litigant_customers(
        record,
        {"对方当事人": [opponent] if opponent else []},
        identity,
        db,
    )
    db.add(WorkflowEvent(
        record_id=record.id, action="从合同新建案件", to_status=record.status,
        operator=identity["username"], comment=f"关联合同：{contract.serial_no}｜{contract.title}",
    ))
    await assess_conflict_review(record, identity, db, trigger="case_save")
    await _sync_legacy_projection(record, identity, db)
    await db.commit()
    await db.refresh(record)
    return _record_dict(record)


@router.delete(f"{settings.api_prefix}/cases/{{case_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Delete a company case and its case-owned operational records."""
    await _delete_company_cases([case_id], identity, db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _delete_case_owned_records(record: BusinessRecord, db: AsyncSession) -> list[Path]:
    from app.core.tasks import (
        _delete_task_notifications,
    )
    case_id = record.id
    related_tasks = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "task",
        BusinessRecord.data["case_id"].as_integer() == case_id,
    ))).all())
    owned_ids = [case_id, *(task.id for task in related_tasks)]
    attachments = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id.in_(owned_ids)))).all())
    attachment_paths = [Path(item.path) for item in attachments]
    for attachment in attachments:
        await db.delete(attachment)
    for task in related_tasks:
        await _delete_task_notifications(task.id, db)
        await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == task.id))
        await db.delete(task)
    await db.execute(delete(CaseAssistedFee).where(CaseAssistedFee.case_record_id == case_id))
    await db.execute(delete(HearingSchedule).where(HearingSchedule.case_record_id == case_id))
    await db.execute(delete(FinanceTransaction).where(FinanceTransaction.finance_record_id == case_id))
    await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == case_id))
    await db.delete(record)
    return attachment_paths


async def _delete_company_cases(case_ids: list[int], identity: dict, db: AsyncSession) -> dict:
    from app.core.permissions import _record_scope_conditions

    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="仅管理员或管理人员可以删除案件")
    attachment_paths: list[Path] = []
    try:
        # Lock and validate the complete selection before any deletion can flush.
        records = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.id.in_(case_ids), BusinessRecord.module == "case",
            *(await _record_scope_conditions(identity, db)),
        ).order_by(BusinessRecord.id).with_for_update())).all())
        if len(records) != len(case_ids):
            raise HTTPException(status_code=404, detail="选中的案件不存在或无权访问，整批未删除")
        if any(record.status in {"已归档", "已合并"} for record in records):
            raise HTTPException(status_code=409, detail="包含已归档或已合并案件，整批未删除")
        for record in records:
            attachment_paths.extend(await _delete_case_owned_records(record, db))
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="案件存在不能删除的关联记录，整批未删除") from exc
    except Exception:
        await db.rollback()
        raise

    logger.info("Company case deletion committed: operator=%s case_ids=%s", identity["username"], case_ids)
    cleanup_pending = 0
    for path in set(attachment_paths):
        try:
            if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
                # Imported attachments may share a physical file with another record.
                if not await db.scalar(select(FileAttachment.id).where(FileAttachment.path == str(path)).limit(1)):
                    path.unlink()
        except (OSError, SQLAlchemyError):
            cleanup_pending += 1
            logger.exception("Case deletion committed; attachment cleanup pending for case_ids=%s", case_ids)
    return {"deleted": len(records), "case_ids": case_ids, "cleanup_pending": cleanup_pending}


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/assisted-fees")
async def list_case_assisted_fees(
    case_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """List the visible ordinary case's standalone assistance applications."""
    from app.core.finance import (
        _case_assisted_fee_dict,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    total = int(await db.scalar(select(func.count()).select_from(CaseAssistedFee).where(
        CaseAssistedFee.case_record_id == case_record.id,
    )) or 0)
    rows = list((await db.scalars(
        select(CaseAssistedFee).where(CaseAssistedFee.case_record_id == case_record.id)
        .order_by(CaseAssistedFee.created_at.desc(), CaseAssistedFee.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).all())
    return {
        "items": [_case_assisted_fee_dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
    }


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/assisted-fees", status_code=status.HTTP_201_CREATED)
async def create_case_assisted_fee(
    case_id: int,
    body: CaseAssistedFeeCreateInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _case_assisted_fee_dict,
    )
    from app.core.permissions import (
        _ensure_case_assisted_fee_write,
    )
    case_record = await _ensure_case_assisted_fee_write(case_id, identity, db)
    assisted_type = body.assisted_type.strip()
    if not assisted_type:
        raise HTTPException(status_code=422, detail="资助类别不能为空")
    row = CaseAssistedFee(
        case_record_id=case_record.id,
        assisted_type=assisted_type,
        amount=body.amount,
        request_user=identity["username"],
        remark=body.remark.strip(),
    )
    db.add(row)
    await db.flush()
    db.add(WorkflowEvent(
        record_id=case_record.id,
        action="新建案件资助费用",
        from_status=case_record.status,
        to_status=case_record.status,
        operator=identity["username"],
        comment=f"资助费用 #{row.id}；类别：{row.assisted_type}" + (f"；金额：{row.amount:.2f}" if row.amount is not None else "") + (f"；{row.remark}" if row.remark else ""),
    ))
    await db.commit()
    await db.refresh(row)
    return _case_assisted_fee_dict(row)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/assisted-fees/{{assisted_fee_id}}")
async def update_case_assisted_fee(
    case_id: int,
    assisted_fee_id: int,
    body: CaseAssistedFeeUpdateInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _case_assisted_fee_dict, _case_assisted_fee_for_case,
    )
    from app.core.permissions import (
        _ensure_case_assisted_fee_write,
    )
    if not body.model_fields_set:
        raise HTTPException(status_code=422, detail="请至少填写一项要修改的资助费用信息")
    case_record = await _ensure_case_assisted_fee_write(case_id, identity, db)
    row = await _case_assisted_fee_for_case(case_record, assisted_fee_id, db)
    if row.status != "待办理":
        raise HTTPException(status_code=409, detail="已办理的资助费用必须保留确认记录，不能修改")
    before = (row.assisted_type, row.amount, row.remark)
    if "assisted_type" in body.model_fields_set:
        assisted_type = (body.assisted_type or "").strip()
        if not assisted_type:
            raise HTTPException(status_code=422, detail="资助类别不能为空")
        row.assisted_type = assisted_type
    if "amount" in body.model_fields_set:
        row.amount = body.amount
    if "remark" in body.model_fields_set:
        row.remark = (body.remark or "").strip()
    db.add(WorkflowEvent(
        record_id=case_record.id,
        action="修改案件资助费用",
        from_status=case_record.status,
        to_status=case_record.status,
        operator=identity["username"],
        comment=(
            f"资助费用 #{row.id}：类别 {before[0]} → {row.assisted_type}；"
            f"金额 {before[1] if before[1] is not None else '未填'} → {row.amount if row.amount is not None else '未填'}；"
            f"备注 {before[2] or '未填'} → {row.remark or '未填'}"
        ),
    ))
    await db.commit()
    await db.refresh(row)
    return _case_assisted_fee_dict(row)


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/assisted-fees/{{assisted_fee_id}}/confirm")
async def confirm_case_assisted_fee(
    case_id: int,
    assisted_fee_id: int,
    body: CaseAssistedFeeConfirmInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _case_assisted_fee_dict, _case_assisted_fee_for_case,
    )
    from app.core.permissions import (
        _ensure_case_assisted_fee_write,
    )
    case_record = await _ensure_case_assisted_fee_write(case_id, identity, db)
    row = await _case_assisted_fee_for_case(case_record, assisted_fee_id, db)
    if row.status != "待办理":
        raise HTTPException(status_code=409, detail="该资助费用已办理，不能重复确认")
    row.status = "已办理"
    row.confirmed_date = body.confirmed_date or date.today()
    row.confirmed_user = identity["username"]
    if body.remark.strip():
        row.remark = (row.remark + "\n" + body.remark.strip()).strip()
    db.add(WorkflowEvent(
        record_id=case_record.id,
        action="办理案件资助费用",
        from_status=case_record.status,
        to_status=case_record.status,
        operator=identity["username"],
        comment=f"资助费用 #{row.id}；类别：{row.assisted_type}；办理日期：{row.confirmed_date}",
    ))
    await db.commit()
    await db.refresh(row)
    return _case_assisted_fee_dict(row)


@router.delete(f"{settings.api_prefix}/cases/{{case_id}}/assisted-fees/{{assisted_fee_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case_assisted_fee(
    case_id: int,
    assisted_fee_id: int,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _case_assisted_fee_for_case,
    )
    from app.core.permissions import (
        _ensure_case_assisted_fee_write,
    )
    case_record = await _ensure_case_assisted_fee_write(case_id, identity, db)
    row = await _case_assisted_fee_for_case(case_record, assisted_fee_id, db)
    if row.status != "待办理":
        raise HTTPException(status_code=409, detail="已办理的资助费用必须保留确认记录，不能删除")
    db.add(WorkflowEvent(
        record_id=case_record.id,
        action="删除案件资助费用",
        from_status=case_record.status,
        to_status=case_record.status,
        operator=identity["username"],
        comment=f"资助费用 #{row.id}；类别：{row.assisted_type}",
    ))
    await db.delete(row)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/duplicate", status_code=status.HTTP_201_CREATED)
async def duplicate_case(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Copy only the case's basic business data into a new, unstarted case.

    The legacy action preserves the source case number as the original case.
    Never clone downstream facts (tasks, files, fees, reminders, schedules or
    workflow history): those records describe work already performed and must
    not be silently recreated under the new case.
    """
    from app.core.cases import (
        _case_copy_root, _case_team_payload, _next_case_copy_serial, _resolve_active_case_people,
    )
    from app.core.permissions import (
        _ensure_record_module, _ensure_record_visible,
    )
    from app.core.system import (
        _allowed_field_keys, _record_dict,
    )
    source = await _ensure_record_module(case_id, "case", identity, db)
    source_data = dict(source.data or {})
    case_type = str(source_data.get("case_type") or "").strip()
    if case_type not in CASE_CREATABLE_TYPES and case_type not in CIVIL_CASE_TYPES:
        raise HTTPException(status_code=409, detail="原案件类型不支持复制新建")
    contract_id = int(source_data.get("contract_id") or source_data.get("contract_record_id") or 0)
    contract: BusinessRecord | None = None
    if contract_id:
        contract = await _ensure_record_visible(contract_id, identity, db)
        if contract.module != "contract":
            raise HTTPException(status_code=409, detail="原案件关联记录不是合同，不能复制")
    root = await _case_copy_root(source, db)
    root_serial_no = root.serial_no
    owner = source.owner if identity.get("role") == "admin" else identity["username"]
    owner_user = await db.scalar(select(User).where(User.username == owner, User.is_active.is_(True)))
    if not owner_user:
        owner = identity["username"]
    source_id = source.id
    source_serial_no = source.serial_no
    source_title = source.title
    source_status = source.status
    source_description = source.description
    contract_customer = contract.customer if contract else source.customer
    contract_department = contract.department if contract else source.department
    contract_data = dict(contract.data or {}) if contract else {}
    root_record_id = root.id or source_id
    copied_data = dict(source_data)
    for key in {
        "fixed_tasks_generated", "fixed_task_ids", "case_reminder_ids", "task_ids", "schedule_ids",
        "archived_at", "archived_by", "archive_comment", "submitted_at", "submitted_by",
        "approval_comment", "approval_by", "approval_at", "progress_logs", "conflict_review",
        "conflict_review_requires_creation_approval", "conflict_review_target_phase",
    }:
        copied_data.pop(key, None)
    contract_snapshot = {
        "contract_id": contract.id, "contract_record_id": contract.id, "contract_no": contract.serial_no,
        "contract_title": contract.title, "external_contract_no": contract_data.get("external_contract_no", ""),
        "external_contract_numbers": contract_data.get("external_contract_numbers", []),
    } if contract else {}
    copied_data.update({
        **contract_snapshot,
        "original_case_no": source_serial_no, "original_case_record_id": source_id,
        "copied_from_case_id": source_id, "copy_root_case_no": root_serial_no,
        "copy_root_case_record_id": root_record_id,
        "copied_at": datetime.now().isoformat(timespec="seconds"),
        "copied_by": identity["username"], "case_creation_step": "basic",
        "case_creation_approval_status": "未提交", "business_stage": "立案",
    })
    try:
        handling_lawyers, handling_usernames = await _resolve_active_case_people(
            copied_data.get("handling_lawyers") or [], db, field_name="经办律师",
        )
    except HTTPException as exc:
        if exc.status_code != 422:
            raise
        raise HTTPException(
            status_code=422,
            detail=f"源案件（{source_serial_no}）的经办律师无效，需要先修正源案件：{exc.detail}",
        ) from exc
    source_assistants = copied_data.get("assistants") or []
    source_assistants = list(source_assistants) if isinstance(source_assistants, list) else [source_assistants]
    source_assistants.append(copied_data.get("assistant") or "")
    assistant_values: list[str] = []
    assistant_usernames: list[str] = []
    for source_assistant in dict.fromkeys(str(value or "").strip() for value in source_assistants if str(value or "").strip()):
        try:
            resolved_values, resolved_usernames = await _resolve_active_case_people(
                [source_assistant], db, field_name="律师助理",
            )
        except HTTPException as exc:
            if exc.status_code == 422:
                continue
            raise
        assistant_values.extend(resolved_values)
        assistant_usernames.extend(resolved_usernames)
    copied_data = _case_team_payload(
        copied_data,
        handling_lawyers,
        handling_usernames,
        assistant_values,
        assistant_usernames,
    )
    copied: BusinessRecord | None = None
    for _ in range(128):
        serial_no = await _next_case_copy_serial(root_serial_no, db)
        copied = BusinessRecord(
            module="case", serial_no=serial_no, title=f"{source_title}（副本）", customer=contract_customer,
            status="新案待分配", owner=owner, department=contract_department, description=source_description,
            data=copied_data,
        )
        db.add(copied)
        try:
            await db.flush()
            break
        except IntegrityError:
            await db.rollback()
            copied = None
    if not copied:
        raise HTTPException(status_code=409, detail="复制案件编号生成冲突，请稍后重试")
    db.add(WorkflowEvent(
        record_id=copied.id, action="复制案件", to_status=copied.status, operator=identity["username"],
        comment=f"来源案件：{source_serial_no}；未复制任务、附件、费用、提醒、排期和历史记录。",
    ))
    db.add(WorkflowEvent(
        record_id=source_id, action="案件被复制", from_status=source_status, to_status=source_status,
        operator=identity["username"], comment=f"新案件：{copied.serial_no}",
    ))
    await assess_conflict_review(copied, identity, db, trigger="case_save")
    await db.commit(); await db.refresh(copied)
    return _record_dict(copied, await _allowed_field_keys(identity, db))


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/merge")
async def merge_case(case_id: int, body: CaseMergeInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """合并同客户案件关系，保留主案字段及来源审计记录。"""
    from app.core.case_merge import ensure_case_merge_contract_scope, merge_case_relations, move_case_finance_files
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _record_scope_conditions,
    )
    target = await _ensure_record_module(case_id, "case", identity, db)
    source_no = body.source_case_no.strip()
    if source_no == target.serial_no:
        raise HTTPException(status_code=422, detail="待合并案件不能与当前案件相同")
    source = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == "case", BusinessRecord.serial_no == source_no,
        *(await _record_scope_conditions(identity, db)),
    ))
    if not source:
        raise HTTPException(status_code=404, detail="未找到待合并案件，或当前账号无权查看")
    for record in sorted((target, source), key=lambda item: item.id):
        await db.refresh(record, with_for_update=True)
    blocked_statuses = {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档", "已合并"}
    if target.status in blocked_statuses or source.status in blocked_statuses:
        raise HTTPException(status_code=409, detail="归档中、已归档或已合并案件不能参与合并")
    if source.customer != target.customer:
        raise HTTPException(status_code=422, detail="待合并案件的客户与当前案件不一致，不允许操作")
    source_type = str((source.data or {}).get("case_type") or "").strip()
    target_type = str((target.data or {}).get("case_type") or "").strip()
    if source_type != target_type:
        raise HTTPException(status_code=422, detail="仅允许合并同一案件类型的案件")
    try:
        source_contract_id = int((source.data or {}).get("contract_record_id") or (source.data or {}).get("contract_id") or 0)
        target_contract_id = int((target.data or {}).get("contract_record_id") or (target.data or {}).get("contract_id") or 0)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="案件关联合同无效，不能合并")
    if not source_contract_id or not target_contract_id:
        raise HTTPException(status_code=422, detail="两个案件都必须关联同一份合同后才能合并")
    if source_contract_id != target_contract_id:
        raise HTTPException(status_code=422, detail="仅允许合并同一合同下的案件")
    await ensure_case_merge_contract_scope(source, source_contract_id, db)
    await ensure_case_merge_contract_scope(target, target_contract_id, db)

    await require_conflict_clear(source, db, action="合并案件")
    await require_conflict_clear(target, db, action="合并案件")
    await merge_case_relations(source, target, db)
    moved_fees, moved_assisted_fees, moved_attachments = await move_case_finance_files(source, target, identity, db)

    source_previous = source.status
    source.status = "已合并"
    source.data = {
        **(source.data or {}), "merged_into_case_id": target.id,
        "merged_into_case_no": target.serial_no, "merged_at": datetime.now().isoformat(timespec="seconds"),
        "merged_by": identity["username"], "merge_comment": body.comment.strip(),
    }
    db.add_all([
        WorkflowEvent(
            record_id=target.id, action="合并案件", from_status=target.status, to_status=target.status,
            operator=identity["username"],
            comment=f"合并来源案件 {source.serial_no}；迁移费用 {moved_fees} 条、资助费用 {moved_assisted_fees} 条、案件文件 {moved_attachments} 个。{body.comment.strip()}",
        ),
        WorkflowEvent(
            record_id=source.id, action="案件已合并", from_status=source_previous, to_status=source.status,
            operator=identity["username"],
            comment=f"已合并至 {target.serial_no}；迁移费用 {moved_fees} 条、资助费用 {moved_assisted_fees} 条、案件文件 {moved_attachments} 个。{body.comment.strip()}",
        ),
    ])
    await assess_conflict_review(target, identity, db, trigger="case_save")
    await db.commit(); await db.refresh(target); await db.refresh(source)
    return {
        "target": await _record_dict_for_identity(target, identity, db),
        "source": await _record_dict_for_identity(source, identity, db),
        "moved_fees": moved_fees, "moved_assisted_fees": moved_assisted_fees, "moved_attachments": moved_attachments,
    }


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/notary-info")
async def update_case_notary_info(case_id: int, body: CaseNotaryInfoInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.investigation import (
        _sync_case_notary_warehouse_evidence,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _require_case_action,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_action(identity, db, "case.notary.update")
    data = dict(case_record.data or {})
    if str(data.get("case_type") or "") not in CIVIL_CASE_TYPES:
        raise HTTPException(status_code=409, detail="仅民事案件可以维护公证信息")
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档", "已合并"}:
        raise HTTPException(status_code=409, detail="当前案件状态不能维护公证信息")
    previous_notary = str(data.get("notary_nos") or data.get("notary_no") or "")
    previous_address = str(data.get("deposit_address") or "")
    location_ids = list(dict.fromkeys(body.warehouse_location_ids))
    locations = list((await db.scalars(
        select(WarehouseStorageLocation).where(WarehouseStorageLocation.id.in_(location_ids))
    )).all())
    locations_by_id = {location.id: location for location in locations}
    if len(locations_by_id) != len(location_ids):
        raise HTTPException(status_code=422, detail="仓库库位不存在")
    warehouse_ids = {location.warehouse_id for location in locations}
    warehouses = list((await db.scalars(select(Warehouse).where(Warehouse.id.in_(warehouse_ids)))).all())
    warehouses_by_id = {warehouse.id: warehouse for warehouse in warehouses}
    resolved_locations = []
    for location_id in location_ids:
        location = locations_by_id[location_id]
        warehouse = warehouses_by_id.get(location.warehouse_id)
        if not warehouse or not warehouse.is_active or not location.is_active:
            raise HTTPException(status_code=422, detail="仓库库位已停用")
        resolved_locations.append({
            "warehouse_id": warehouse.id,
            "warehouse_no": warehouse.warehouse_no,
            "warehouse_name": warehouse.name,
            "storage_location_id": location.id,
            "storage_location_no": location.storage_location_no,
            "storage_location_name": location.name,
            "display_name": f"{warehouse.name}（{location.name}）",
        })
    deposit_address = "，".join(item["display_name"] for item in resolved_locations)
    case_record.data = {
        **data, "notary_nos": body.notary_nos.strip(), "notary_no": body.notary_nos.strip(),
        "deposit_address": deposit_address,
        "warehouse_location_ids": location_ids,
        "warehouse_locations": resolved_locations,
    }
    await _sync_case_notary_warehouse_evidence(
        case_record,
        [(warehouses_by_id[locations_by_id[location_id].warehouse_id], locations_by_id[location_id]) for location_id in location_ids],
        body.notary_nos.strip(),
        identity["username"],
        db,
    )
    db.add(WorkflowEvent(
        record_id=case_record.id, action="修改案件公证信息", from_status=case_record.status, to_status=case_record.status,
        operator=identity["username"],
        comment=f"公证书号：{previous_notary or '空'} → {body.notary_nos.strip()}；存放位置：{previous_address or '空'} → {deposit_address}。{body.comment.strip()}",
    ))
    await assess_conflict_review(case_record, identity, db, trigger="case_save")
    await db.commit(); await db.refresh(case_record)
    return await _record_dict_for_identity(case_record, identity, db)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/settlement-amount")
async def update_case_settlement_amount(case_id: int, body: CaseSettlementAmountInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _round_fee_amount,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity, _require_case_action,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_action(identity, db, "case.settlement.update")
    data = dict(case_record.data or {})
    if str(data.get("case_type") or "") not in NORMAL_CASE_BASIC_TYPES | {"仲裁"}:
        raise HTTPException(status_code=409, detail="当前案件类型不能维护诉讼或判决金额")
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档", "已合并"}:
        raise HTTPException(status_code=409, detail="当前案件状态不能维护诉讼或判决金额")
    previous_litigation = data.get("litigation_amount", 0)
    previous_settlement = data.get("settlement_amount", 0)
    case_record.data = {
        **data, "litigation_amount": _round_fee_amount(body.litigation_amount),
        "settlement_amount": _round_fee_amount(body.settlement_amount),
    }
    db.add(WorkflowEvent(
        record_id=case_record.id, action="修改案件诉讼或判决金额", from_status=case_record.status, to_status=case_record.status,
        operator=identity["username"],
        comment=f"诉讼标的：{previous_litigation} → {_round_fee_amount(body.litigation_amount)}；判决金额：{previous_settlement} → {_round_fee_amount(body.settlement_amount)}。{body.comment.strip()}",
    ))
    await db.commit(); await db.refresh(case_record)
    return await _record_dict_for_identity(case_record, identity, db)


@router.get(f"{settings.api_prefix}/case-litigant-candidates")
async def list_case_litigant_candidates(
    keyword: str = Query(default="", max_length=100),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """案件当事人选择器只返回公司客户的最小身份字段。"""
    from app.core.permissions import (
        _record_scope_conditions, _require_case_action,
    )
    await _require_case_action(identity, db, "case.litigants.update")
    scope_identity = {**identity, "role": identity.get("_actual_role") or identity.get("role")}
    scope_identity.pop("_page_menu_capability", None)
    conditions = [
        BusinessRecord.module == "customer",
        BusinessRecord.status != "已回收",
        *(await _record_scope_conditions(scope_identity, db)),
    ]
    normalized_keyword = keyword.strip()
    if normalized_keyword:
        like = f"%{normalized_keyword}%"
        conditions.append(or_(BusinessRecord.title.ilike(like), BusinessRecord.serial_no.ilike(like)))
    candidates = list((await db.scalars(
        select(BusinessRecord)
        .where(*conditions)
        .order_by(BusinessRecord.title, BusinessRecord.id)
        .limit(50)
    )).all())
    return {
        "items": [
            {
                "id": item.id,
                "serial_no": item.serial_no,
                "title": item.title,
                "customer_type": str((item.data or {}).get("customer_type") or "客户"),
            }
            for item in candidates
        ]
    }


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/litigants")
async def update_case_litigants(case_id: int, body: CaseLitigantsInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Creation-wizard endpoint; it may advance the wizard to the litigants step."""
    from app.core.cases import (
        _persist_case_litigants,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_case_action, _require_record_owner_or_manager,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    creation_step = str((case_record.data or {}).get("case_creation_step") or "")
    if creation_step:
        await _require_record_owner_or_manager(case_record, identity, db)
    else:
        await _require_case_action(identity, db, "case.litigants.update")
    return await _persist_case_litigants(
        case_record, body, identity, db,
        advance_creation=True,
        enforce_create_permission=True,
        action="维护当事人信息",
    )


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/litigants-detail")
async def update_case_litigants_from_detail(case_id: int, body: CaseLitigantsInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Legacy detail editor: update only parties, regardless of stale wizard markers."""
    from app.core.cases import (
        _persist_case_litigants,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_case_action,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_action(identity, db, "case.litigants.update")
    return await _persist_case_litigants(
        case_record, body, identity, db,
        advance_creation=False,
        enforce_create_permission=False,
        action="修改案件当事人",
    )


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/complete-creation")
async def complete_case_creation(case_id: int, body: CaseCreationCompleteInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _permission_payload_for_identity, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_record_owner_or_manager(case_record, identity, db)
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
        raise HTTPException(status_code=409, detail="归档中的案件不能完成新建")
    case_data = case_record.data or {}
    if str(case_data.get("case_type") or "") != "法律顾问":
        raise HTTPException(status_code=409, detail="当前案件类型必须通过司法机关步骤完成新建")
    if str(case_data.get("case_creation_step") or "") != "litigants":
        raise HTTPException(status_code=409, detail="请先完成当事人信息")
    permission_key = CASE_CREATE_PERMISSION_BY_TYPE["法律顾问"]
    if identity.get("role") != "admin":
        permission = await _permission_payload_for_identity(identity, db)
        if permission_key not in set(permission.get("menu_keys", [])):
            raise HTTPException(status_code=403, detail="当前角色没有法律顾问案件新建权限")
    await assess_conflict_review(case_record, identity, db, trigger="case_save")
    gate = await get_conflict_review_gate(case_record, db, action="完成案件新建")
    if gate["blocking"]:
        await db.commit()
        raise HTTPException(status_code=409, detail={
            "code": "CONFLICT_REVIEW_REQUIRED", "message": gate["message"],
            "record_id": gate["record_id"], "review_id": (gate.get("review") or {}).get("id"),
            "conflict_review": gate.get("review"),
        })
    case_data = case_record.data or {}
    previous_status = case_record.status
    case_record.status = "待立案审批"
    case_record.data = {
        **case_data,
        "case_creation_step": "completed",
        "case_creation_completed_at": datetime.now().isoformat(timespec="seconds"),
        "case_creation_completed_by": identity["username"],
        "case_creation_approval_status": "待审批",
        "case_creation_submitted_at": datetime.now().isoformat(timespec="seconds"),
        "case_creation_submitted_by": identity["username"],
    }
    db.add(WorkflowEvent(
        record_id=case_record.id,
        action="完成法律顾问案件新建",
        from_status=previous_status,
        to_status=case_record.status,
        operator=identity["username"],
        comment=body.comment or "案件资料填写完成，提交案件主管审批",
    ))
    await db.commit()
    await db.refresh(case_record)
    return _record_dict(case_record)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/counsel-basic")
async def update_counsel_case_basic(case_id: int, body: CaseCounselBasicInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_commission_personnel_changed, _case_team_payload, _recalculate_case_draft_commissions, _resolve_active_case_people,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_case_action,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_action(identity, db, "case.detail.update")
    case_data = case_record.data or {}
    if str(case_data.get("case_type") or "") != "法律顾问":
        raise HTTPException(status_code=409, detail="该接口仅用于法律顾问案件")
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
        raise HTTPException(status_code=409, detail="归档中的法律顾问案件不能修改基本信息")
    if str(case_data.get("case_creation_step") or "") != "completed":
        raise HTTPException(status_code=409, detail="请先完成法律顾问案件新建流程")
    title = body.title.strip()
    counsel_type = body.counsel_type.strip()
    if not title or not counsel_type:
        raise HTTPException(status_code=422, detail="案件名称和顾问类型不能为空")
    if body.counsel_start > body.counsel_end:
        raise HTTPException(status_code=422, detail="顾问结束日期不能早于开始日期")
    handling_lawyers = list(dict.fromkeys(str(item or "").strip() for item in body.handling_lawyers if str(item or "").strip()))
    assistant = body.assistant.strip()
    handling_lawyers, handling_usernames = await _resolve_active_case_people(handling_lawyers, db, field_name="经办律师")
    assistant_values, assistant_usernames = await _resolve_active_case_people([assistant] if assistant else [], db, field_name="律师助理")
    assistant = assistant_values[0] if assistant_values else ""
    assistant_username = assistant_usernames[0] if assistant_usernames else ""
    if not handling_lawyers:
        raise HTTPException(status_code=422, detail="请至少保留一名有效经办律师")
    old_summary = f"{case_record.title}｜{case_data.get('counsel_type', '')}｜{case_data.get('counsel_start', '')}至{case_data.get('counsel_end', '')}"
    case_record.title = title
    updated_case_data = _case_team_payload({
        **case_data,
        "counsel_type": counsel_type,
        "counsel_start": str(body.counsel_start),
        "counsel_end": str(body.counsel_end),
    }, handling_lawyers, handling_usernames, assistant, assistant_username)
    case_record.data = updated_case_data
    if _case_commission_personnel_changed(case_data, updated_case_data):
        await _recalculate_case_draft_commissions(case_record, db, identity["username"])
    db.add(WorkflowEvent(
        record_id=case_record.id,
        action="修改法律顾问案件基本信息",
        from_status=case_record.status,
        to_status=case_record.status,
        operator=identity["username"],
        comment=f"修改前：{old_summary}" + (f"｜说明：{body.comment.strip()}" if body.comment.strip() else ""),
    ))
    await assess_conflict_review(case_record, identity, db, trigger="case_save")
    await db.commit()
    await db.refresh(case_record)
    return _record_dict(case_record)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/normal-basic")
async def update_normal_case_basic(case_id: int, body: CaseNormalBasicInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Update the evidenced civil/criminal/administrative basic-information branch.

    The endpoint is intentionally separate from counsel-basic and from generic
    record PATCH so archived cases and the case lifecycle cannot be bypassed.
    """
    from app.core.cases import (
        _active_case_phase_values, _case_commission_personnel_changed, _case_team_payload, _prioritize_new_case_assistants,
        _recalculate_case_draft_commissions, _resolve_active_case_people,
    )
    from app.core.crm import (
        _customer_or_404,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_case_action,
    )
    from app.core.system import (
        _record_dict,
    )
    from app.core.tasks import (
        _ensure_document_preparation_task, _ensure_execution_application_reminder_task,
        _ensure_phase_automatic_tasks, _ensure_timestamp_evidence_handoff_task,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_action(identity, db, "case.detail.update")
    case_data = case_record.data or {}
    case_type = str(case_data.get("case_type") or "")
    if case_type not in NORMAL_CASE_BASIC_TYPES:
        raise HTTPException(status_code=409, detail="该接口仅用于民事、刑事、行政及国家赔偿案件")
    # This is the detail-page maintenance endpoint, not a creation-wizard step.
    # Historical and duplicated cases may retain ``basic``/``litigants`` in the
    # JSON marker even though they are already active.  Keep authorization and
    # archive locks below, but do not let that stale wizard marker block edits.
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
        raise HTTPException(status_code=409, detail="归档中的案件不能修改基本信息")
    title = body.title.strip()
    phase = body.case_phase.strip()
    cause_or_charge = body.cause_or_charge.strip()
    if phase != case_record.status:
        active_phase_values = await _active_case_phase_values(db)
        if phase not in active_phase_values:
            raise HTTPException(status_code=422, detail="案件阶段不是允许的办理阶段")
    if not title or not cause_or_charge:
        raise HTTPException(status_code=422, detail="案件名称、案由或罪名不能为空")
    customer = await _customer_or_404(body.customer_record_id, identity, db)
    if customer.status in {"公海", "已回收"}:
        raise HTTPException(status_code=409, detail="不能关联公海或回收站客户")
    handling_lawyers = list(dict.fromkeys(str(item or "").strip() for item in body.handling_lawyers if str(item or "").strip()))
    handling_lawyers, handling_usernames = await _resolve_active_case_people(handling_lawyers, db, field_name="经办律师")
    if not handling_lawyers:
        raise HTTPException(status_code=422, detail="请至少保留一名有效经办律师")
    requested_assistants = body.assistants if body.assistants is not None else ([body.assistant.strip()] if body.assistant.strip() else [])
    assistant_values, assistant_usernames = await _resolve_active_case_people(requested_assistants, db, field_name="律师助理")
    assistant_values, assistant_usernames = _prioritize_new_case_assistants(
        case_data, assistant_values, assistant_usernames,
    )
    investigator_values, _ = await _resolve_active_case_people([body.investigator.strip()] if body.investigator.strip() else [], db, field_name="调查员")
    business_owner_values, _ = await _resolve_active_case_people([body.business_owner.strip()] if body.business_owner.strip() else [], db, field_name="案源人")
    clue_ids = list(dict.fromkeys(body.investigation_clue_ids))
    clues = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(clue_ids), BusinessRecord.module == "clue", BusinessRecord.customer == customer.title,
    ))).all()) if clue_ids else []
    clues_by_id = {item.id: item for item in clues}
    if len(clues_by_id) != len(clue_ids):
        raise HTTPException(status_code=404, detail="关联调查线索不存在或无权访问")
    ordered_clues = [clues_by_id[item_id] for item_id in clue_ids]
    from app.core.case_relations import case_clue_ids, sync_case_clues, validate_case_clues
    await validate_case_clues(case_record, ordered_clues, customer.title, db)
    previous_clue_ids = case_clue_ids(case_record)
    right_type = body.right_type.strip()
    if case_type != "行政案件及国家赔偿" and right_type:
        raise HTTPException(status_code=422, detail="仅行政及国家赔偿案件可以修改权利类型")
    old_summary = f"{case_record.customer}｜{case_record.title}｜{case_record.status}｜{case_data.get('cause_or_charge', '')}"
    previous_status = case_record.status
    investigator = investigator_values[0] if investigator_values else ""
    business_owner = business_owner_values[0] if business_owner_values else ""
    clue_nos = [item.serial_no for item in ordered_clues]
    case_record.title = title
    case_record.customer = customer.title
    case_record.status = phase
    updated_case_data = _case_team_payload({
        **case_data,
        "customer_record_id": customer.id,
        "customer_id": customer.id,
        "customer_no": customer.serial_no,
        "cause_or_charge": cause_or_charge,
        "right_type": right_type if case_type == "行政案件及国家赔偿" else str(case_data.get("right_type") or ""),
        "source_person": business_owner or str(case_data.get("source_person") or ""),
        "business_owner": business_owner or str(case_data.get("business_owner") or ""),
        "investigator": investigator,
        "investigation_clue_ids": clue_ids,
        "investigation_clue_nos": clue_nos,
        "investigation_clue_id": clue_ids[0] if clue_ids else None,
        "investigation_clue": "、".join(clue_nos),
        "clue_record_id": clue_ids[0] if clue_ids else None,
        "clue_id": clue_ids[0] if clue_ids else None,
        "clue_no": clue_nos[0] if clue_nos else "",
        "source_clue_no": clue_nos[0] if clue_nos else "",
        "clue_nos": clue_nos,
    }, handling_lawyers, handling_usernames, assistant_values, assistant_usernames)
    case_record.data = updated_case_data
    await assess_conflict_review(case_record, identity, db, trigger="case_save")
    gate = await get_conflict_review_gate(case_record, db, action="修改案件阶段")
    if gate["blocking"]:
        phase = previous_status
        case_record.status = previous_status
    await sync_case_clues(case_record, ordered_clues, db, previous_clue_ids)
    if _case_commission_personnel_changed(case_data, updated_case_data):
        await _recalculate_case_draft_commissions(case_record, db, identity["username"])
    if phase != previous_status:
        case_record.data = {**case_record.data, "phase_changed_at": datetime.now().isoformat(timespec="seconds")}
        await _ensure_execution_application_reminder_task(
            case_record, db, previous_status=previous_status, operator=identity["username"],
        )
        await _ensure_phase_automatic_tasks(case_record, db, previous_status=previous_status)
    # These rules depend on both the current phase and assigned people. Run
    # after every basic-information save so assigning the assistant after the
    # phase transition cannot silently lose the automatic tasks.
    if not gate["blocking"]:
        await _ensure_document_preparation_task(case_record, db, system_operator=identity["username"])
        await _ensure_timestamp_evidence_handoff_task(case_record, db, system_operator=identity["username"])
    db.add(WorkflowEvent(
        record_id=case_record.id, action="修改普通案件基本信息",
        from_status=previous_status, to_status=case_record.status, operator=identity["username"],
        comment=f"修改前：{old_summary}" + (f"｜说明：{body.comment.strip()}" if body.comment.strip() else ""),
    ))
    await db.commit()
    await db.refresh(case_record)
    return _record_dict(case_record)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/arbitration-basic")
async def update_arbitration_case_basic(case_id: int, body: CaseArbitrationBasicInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Keep the old arbitration edit branch isolated from normal/counsel cases."""
    from app.core.cases import (
        _active_case_phase_values, _case_commission_personnel_changed, _case_team_payload, _recalculate_case_draft_commissions,
        _resolve_active_case_people,
    )
    from app.core.crm import (
        _customer_or_404,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_case_action, _require_case_creation_completed,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_action(identity, db, "case.detail.update")
    case_data = case_record.data or {}
    if str(case_data.get("case_type") or "") != "仲裁":
        raise HTTPException(status_code=409, detail="该接口仅用于仲裁案件")
    _require_case_creation_completed(case_record, require_approval=False)
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
        raise HTTPException(status_code=409, detail="归档中的仲裁案件不能修改基本信息")
    title, phase, cause_or_charge = body.title.strip(), body.case_phase.strip(), body.cause_or_charge.strip()
    active_phase_values = await _active_case_phase_values(db)
    if phase not in active_phase_values:
        raise HTTPException(status_code=422, detail="案件阶段不是允许的办理阶段")
    if not title or not cause_or_charge:
        raise HTTPException(status_code=422, detail="案件名称和案由不能为空")
    customer = await _customer_or_404(body.customer_record_id, identity, db)
    if customer.status in {"公海", "已回收"}:
        raise HTTPException(status_code=409, detail="不能关联公海或回收站客户")
    lawyers = list(dict.fromkeys(str(item or "").strip() for item in body.handling_lawyers if str(item or "").strip()))
    lawyers, lawyer_usernames = await _resolve_active_case_people(lawyers, db, field_name="经办律师")
    if not lawyers:
        raise HTTPException(status_code=422, detail="请至少保留一名有效经办律师")
    assistant_values, assistant_usernames = await _resolve_active_case_people([body.assistant.strip()] if body.assistant.strip() else [], db, field_name="律师助理")
    investigator_values, _ = await _resolve_active_case_people([body.investigator.strip()] if body.investigator.strip() else [], db, field_name="调查员")
    clue_ids = list(dict.fromkeys(body.investigation_clue_ids))
    clues = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(clue_ids), BusinessRecord.module == "clue", BusinessRecord.customer == customer.title,
    ))).all()) if clue_ids else []
    if len({item.id for item in clues}) != len(clue_ids):
        raise HTTPException(status_code=404, detail="关联调查线索不存在或无权访问")
    by_id = {item.id: item for item in clues}; clue_nos = [by_id[item_id].serial_no for item_id in clue_ids]
    from app.core.case_relations import case_clue_ids, sync_case_clues, validate_case_clues
    await validate_case_clues(case_record, clues, customer.title, db)
    previous_clue_ids = case_clue_ids(case_record)
    previous_status = case_record.status
    old_summary = f"{case_record.customer}｜{case_record.title}｜{case_record.status}｜{case_data.get('cause_or_charge', '')}"
    case_record.title, case_record.customer, case_record.status = title, customer.title, phase
    updated_case_data = _case_team_payload({
        **case_data, "customer_record_id": customer.id, "customer_id": customer.id, "customer_no": customer.serial_no,
        "cause_or_charge": cause_or_charge, "investigator": investigator_values[0] if investigator_values else "",
        "investigation_clue_ids": clue_ids, "investigation_clue_nos": clue_nos,
        "investigation_clue_id": clue_ids[0] if clue_ids else None, "investigation_clue": "、".join(clue_nos),
        "clue_record_id": clue_ids[0] if clue_ids else None, "clue_no": clue_nos[0] if clue_nos else "",
        "clue_id": clue_ids[0] if clue_ids else None, "source_clue_no": clue_nos[0] if clue_nos else "", "clue_nos": clue_nos,
    }, lawyers, lawyer_usernames, assistant_values[0] if assistant_values else "", assistant_usernames[0] if assistant_usernames else "")
    case_record.data = updated_case_data
    await assess_conflict_review(case_record, identity, db, trigger="case_save")
    gate = await get_conflict_review_gate(case_record, db, action="修改案件阶段")
    if gate["blocking"]:
        phase = previous_status
        case_record.status = previous_status
    await sync_case_clues(case_record, clues, db, previous_clue_ids)
    if _case_commission_personnel_changed(case_data, updated_case_data):
        await _recalculate_case_draft_commissions(case_record, db, identity["username"])
    if phase != previous_status:
        case_record.data = {**case_record.data, "phase_changed_at": datetime.now().isoformat(timespec="seconds")}
    db.add(WorkflowEvent(record_id=case_record.id, action="修改仲裁案件基本信息", from_status=previous_status, to_status=case_record.status, operator=identity["username"], comment=f"修改前：{old_summary}" + (f"｜说明：{body.comment.strip()}" if body.comment.strip() else "")))
    await db.commit(); await db.refresh(case_record)
    return _record_dict(case_record)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/criminal/litigants")
async def maintain_criminal_litigants(case_id: int, body: CaseLitigantsInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _clean_case_litigant_values, _criminal_detail_maintenance_case,
    )
    from app.core.crm import (
        _persist_case_litigant_customers,
    )
    from app.core.documents import (
        _clean_case_litigant_agents,
    )
    from app.core.system import (
        _save_criminal_detail,
    )
    record = await _criminal_detail_maintenance_case(case_id, identity, db, "case.litigants.update")
    payload = {
        "plaintiffs": _clean_case_litigant_values(body.plaintiffs),
        "plaintiff_agents": _clean_case_litigant_agents(body.plaintiff_agents),
        "defendants": _clean_case_litigant_values(body.defendants),
        "defendant_agents": _clean_case_litigant_agents(body.defendant_agents),
        "third_parties": _clean_case_litigant_values(body.third_parties),
        "third_party_agents": _clean_case_litigant_agents(body.third_party_agents),
    }
    await _persist_case_litigant_customers(
        record,
        {"原告": payload["plaintiffs"], "被告": payload["defendants"], "第三人": payload["third_parties"]},
        identity,
        db,
    )
    return await _save_criminal_detail(record, payload, "修改刑事案件当事人", body.comment, identity, db)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/criminal/public-security")
async def maintain_criminal_public_security(case_id: int, body: CriminalPublicSecurityMaintenanceInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _criminal_detail_maintenance_case,
    )
    from app.core.system import (
        _criminal_maintenance_payload, _save_criminal_detail,
    )
    record = await _criminal_detail_maintenance_case(case_id, identity, db, "case.criminal.public_security.update")
    return await _save_criminal_detail(record, _criminal_maintenance_payload(body), "修改刑事案件公安机关信息", body.comment, identity, db)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/criminal/procuratorates")
async def maintain_criminal_procuratorates(case_id: int, body: CriminalProcuratorateMaintenanceInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _criminal_detail_maintenance_case,
    )
    from app.core.system import (
        _criminal_maintenance_payload, _save_criminal_detail,
    )
    record = await _criminal_detail_maintenance_case(case_id, identity, db, "case.criminal.procuratorate.update")
    return await _save_criminal_detail(record, _criminal_maintenance_payload(body), "修改刑事案件检察院信息", body.comment, identity, db)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/criminal/courts")
async def maintain_criminal_courts(case_id: int, body: CriminalCourtMaintenanceInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _criminal_detail_maintenance_case,
    )
    from app.core.system import (
        _criminal_maintenance_payload, _save_criminal_detail,
    )
    record = await _criminal_detail_maintenance_case(case_id, identity, db, "case.criminal.court.update")
    return await _save_criminal_detail(record, _criminal_maintenance_payload(body), "修改刑事案件审级法院信息", body.comment, identity, db)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/judicial")
async def update_case_judicial(case_id: int, body: CaseJudicialInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _permission_payload_for_identity, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_record_owner_or_manager(case_record, identity, db)
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
        raise HTTPException(status_code=409, detail="归档中的案件不能修改司法机关信息")
    if str((case_record.data or {}).get("case_creation_step") or "") != "litigants":
        raise HTTPException(status_code=409, detail="请先完成当事人信息")
    case_type = str((case_record.data or {}).get("case_type") or "")
    if case_type == "法律顾问":
        raise HTTPException(status_code=409, detail="法律顾问案件不使用司法机关步骤")
    permission_key = CASE_CREATE_PERMISSION_BY_TYPE.get(case_type)
    if permission_key and identity.get("role") != "admin":
        permission = await _permission_payload_for_identity(identity, db)
        if permission_key not in set(permission.get("menu_keys", [])):
            raise HTTPException(status_code=403, detail="当前角色没有该案件类型的新建权限")
    hearing_time = body.hearing_time.strip()
    if hearing_time and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?", hearing_time):
        raise HTTPException(status_code=422, detail="开庭时间格式必须为 HH:MM 或 HH:MM:SS")
    judicial_data: dict[str, object] = {}
    for key, value in body.model_dump().items():
        if isinstance(value, str):
            judicial_data[key] = value.strip()
        elif isinstance(value, date):
            judicial_data[key] = str(value)
        else:
            judicial_data[key] = value
    enabled_court_specs = (
        ("first_court_enabled", "first_court_name", "first_court_judge", "first_court_clerk"),
        ("second_court_enabled", "second_court_name", "second_court_judge", "second_court_clerk"),
        ("retrial_court_enabled", "retrial_court_name", "retrial_court_judge", "retrial_court_clerk"),
    )
    enabled_court_names = [str(judicial_data.get(name_key) or "").strip() for enabled_key, name_key, _, _ in enabled_court_specs if judicial_data.get(enabled_key)]
    if enabled_court_names:
        courts = (await db.scalars(select(SystemParameter).where(SystemParameter.category == "court", SystemParameter.is_active.is_(True)))).all()
        court_codes = {court.name: court.code for court in courts}
        for enabled_key, name_key, judge_key, clerk_key in enabled_court_specs:
            if not judicial_data.get(enabled_key):
                continue
            court_name = str(judicial_data.get(name_key) or "").strip()
            if not court_name or court_name not in court_codes:
                raise HTTPException(status_code=422, detail="启用的法院信息必须选择有效法院")
            for officer_key, officer_role in ((judge_key, "法官"), (clerk_key, "书记员")):
                officer_name = str(judicial_data.get(officer_key) or "").strip()
                if not officer_name:
                    continue
                officer = await db.scalar(select(SystemParameter).where(
                    SystemParameter.category == "court_officer", SystemParameter.name == officer_name,
                    SystemParameter.is_active.is_(True)
                ))
                if not officer or str((officer.extra or {}).get("court_code") or "") != court_codes[court_name] or str((officer.extra or {}).get("role") or "") != officer_role:
                    raise HTTPException(status_code=422, detail=f"{officer_role}必须属于所选法院且处于启用状态")
    case_record.description = str(judicial_data.pop("description", ""))
    if case_type == "行政案件及国家赔偿":
        enabled_court_names = [
            str(judicial_data.get("first_court_name") or "").strip() if judicial_data.get("first_court_enabled") else "",
            str(judicial_data.get("second_court_name") or "").strip() if judicial_data.get("second_court_enabled") else "",
            str(judicial_data.get("retrial_court_name") or "").strip() if judicial_data.get("retrial_court_enabled") else "",
            str(judicial_data.get("court") or "").strip(),
        ]
        if not any(enabled_court_names):
            raise HTTPException(status_code=422, detail="行政案件请至少录入一个法院信息")
        for forbidden_key in (key for key in judicial_data if key.startswith(CRIMINAL_JUDICIAL_PREFIXES)):
            if str(judicial_data.get(forbidden_key) or "").strip():
                raise HTTPException(status_code=422, detail="行政案件不能填写公安或检察院信息")
    case_record.data = {**(case_record.data or {}), **judicial_data}
    await assess_conflict_review(case_record, identity, db, trigger="case_save")
    gate = await get_conflict_review_gate(case_record, db, action="完成案件新建")
    if gate["blocking"]:
        db.add(WorkflowEvent(
            record_id=case_record.id, action="保存司法机关信息待利益冲突核查",
            from_status=case_record.status, to_status=case_record.status,
            operator=identity["username"], comment=gate["message"],
        ))
        await db.commit()
        raise HTTPException(status_code=409, detail={
            "code": "CONFLICT_REVIEW_REQUIRED", "message": gate["message"],
            "record_id": gate["record_id"], "review_id": (gate.get("review") or {}).get("id"),
            "conflict_review": gate.get("review"),
        })
    previous_status = case_record.status
    case_record.status = "待立案审批"
    case_record.data = {
        **(case_record.data or {}),
        "case_creation_step": "completed",
        "case_creation_completed_at": datetime.now().isoformat(timespec="seconds"),
        "case_creation_completed_by": identity["username"],
        "case_creation_approval_status": "待审批",
        "case_creation_submitted_at": datetime.now().isoformat(timespec="seconds"),
        "case_creation_submitted_by": identity["username"],
    }
    nonempty_fields = [
        key for key, value in judicial_data.items()
        if value not in {"", None, False}
    ]
    db.add(WorkflowEvent(
        record_id=case_record.id,
        action="完成司法机关信息",
        from_status=previous_status,
        to_status=case_record.status,
        operator=identity["username"],
        comment=f"保存司法机关字段 {len(nonempty_fields)} 项并提交案件主管审批",
    ))
    await db.commit()
    await db.refresh(case_record)
    return _record_dict(case_record)


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/creation/review")
async def review_case_creation(case_id: int, body: CaseCreationReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_case_fixed_tasks, _ensure_record_module,
    )
    from app.core.system import (
        _record_dict,
    )
    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="只有管理员或案件主管可以审批新建案件")
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    data = case_record.data or {}
    if data.get("batch_converted") and not data.get("conflict_review_requires_creation_approval"):
        raise HTTPException(status_code=409, detail="线索自动生成案件无需人工立案审批")
    if data.get("case_creation_step") != "completed" or data.get("case_creation_approval_status") != "待审批" or case_record.status != "待立案审批":
        raise HTTPException(status_code=409, detail="该案件不在待立案审批状态")
    if not body.approved and not body.comment.strip():
        raise HTTPException(status_code=422, detail="驳回时必须填写原因")
    if body.approved:
        await require_conflict_clear(case_record, db, action="立案审批")
    previous = case_record.status
    if body.approved:
        case_record.status = str(data.get("conflict_review_target_phase") or "新案待分配") if data.get("conflict_review_requires_creation_approval") else "新案待分配"
        approval_status = "已通过"
    else:
        case_record.status = "新案待分配"
        approval_status = "已驳回"
    case_record.data = {
        **data, "case_creation_approval_status": approval_status, "business_stage": "立案",
        "case_creation_reviewer": identity["username"], "case_creation_reviewed_at": datetime.now().isoformat(timespec="seconds"),
        "case_creation_review_comment": body.comment.strip(),
        **({"case_register_date": str(date.today()), "filing_date": str(date.today())} if body.approved and data.get("conflict_review_requires_creation_approval") else {}),
        **({"case_creation_step": "litigants"} if not body.approved else {}),
    }
    action = "案件创建审批通过" if body.approved else "案件创建审批驳回"
    db.add(WorkflowEvent(record_id=case_record.id, action=action, from_status=previous, to_status=case_record.status, operator=identity["username"], comment=body.comment))
    if body.approved:
        await _ensure_case_fixed_tasks(case_record, db, operator="system")
    await db.commit(); await db.refresh(case_record)
    return _record_dict(case_record)


@router.get(f"{settings.api_prefix}/cases/action-capabilities")
async def case_list_action_capabilities(
    record_ids: str = Query(default="", max_length=1200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    """Return case capabilities for one visible list page in a single request."""
    from app.core.permissions import (
        _case_detail_action_capabilities, _record_scope_conditions,
    )
    try:
        requested_ids = list(dict.fromkeys(int(value) for value in record_ids.split(",") if value.strip()))
    except ValueError:
        raise HTTPException(status_code=422, detail="案件编号格式无效")
    if not requested_ids:
        return {"items": {}}
    if len(requested_ids) > 100:
        raise HTTPException(status_code=422, detail="一次最多查询 100 条案件的操作权限")
    records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(requested_ids),
        BusinessRecord.module == "case",
        *(await _record_scope_conditions(identity, db)),
    ))).all())
    return {
        "items": {
            str(record.id): await _case_detail_action_capabilities(record, identity, db)
            for record in records
        },
    }


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/action-capabilities")
async def case_detail_action_capabilities(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _case_detail_action_capabilities, _ensure_case_read_module, _ensure_record_module,
    )
    case_record = await _ensure_case_read_module(case_id, identity, db)
    capabilities = await _case_detail_action_capabilities(case_record, identity, db)
    try:
        await _ensure_record_module(case_id, "case", identity, db)
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        capabilities = {key: False if key.startswith("can_") else value for key, value in capabilities.items()}
    return {"case_id": case_record.id, **capabilities}


from app.areas.legal.case_space import (
    router as case_space_router,
    get_case_space_context as get_case_space_context,
    get_case_workflow_guide as get_case_workflow_guide,
    case_agent_status as case_agent_status,
    case_agent_state as case_agent_state,
    send_case_agent_message as send_case_agent_message,
    decide_case_agent_action as decide_case_agent_action,
    restore_case_agent_delete as restore_case_agent_delete,
)
router.include_router(case_space_router)


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/assign")
async def assign_case(case_id: int, body: CaseAssignmentInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_commission_personnel_changed, _case_team_payload, _recalculate_case_draft_commissions, _resolve_active_case_people,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _record_dict,
    )
    from app.core.tasks import (
        _add_task_message_notifications, _ensure_document_preparation_task,
        _ensure_timestamp_evidence_handoff_task, _next_manual_task_serial,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    previous = case_record.status
    handling_lawyers, handling_usernames = await _resolve_active_case_people(body.handling_lawyers, db, field_name="经办律师")
    if not handling_lawyers and not body.hearing_lawyer.strip():
        raise HTTPException(status_code=422, detail="请至少分配一名有效经办律师")
    assistant_values, assistant_usernames = await _resolve_active_case_people([body.assistant] if body.assistant.strip() else [], db, field_name="律师助理")
    hearing_values, _ = await _resolve_active_case_people([body.hearing_lawyer], db, field_name="开庭律师")
    manager_values, _ = await _resolve_active_case_people([body.customer_manager] if body.customer_manager.strip() else [], db, field_name="客户管理人")
    assistant = assistant_values[0] if assistant_values else ""
    assistant_username = assistant_usernames[0] if assistant_usernames else ""
    previous_case_data = dict(case_record.data or {})
    case_data = _case_team_payload({
        **(case_record.data or {}), "customer_manager": manager_values[0] if manager_values else "",
        "hearing_lawyer": hearing_values[0],
    }, handling_lawyers, handling_usernames, assistant, assistant_username)
    case_record.data = case_data
    await assess_conflict_review(case_record, identity, db, trigger="case_save")
    gate = await get_conflict_review_gate(case_record, db, action="案件分配")
    if gate["blocking"]:
        db.add(WorkflowEvent(
            record_id=case_record.id, action="保存案件人员分配待利益冲突核查",
            from_status=previous, to_status=previous, operator=identity["username"], comment=gate["message"],
        ))
        await db.commit()
        await db.refresh(case_record)
        return _record_dict(case_record)
    if _case_commission_personnel_changed(previous_case_data, case_data):
        await _recalculate_case_draft_commissions(case_record, db, identity["username"])
    if case_record.status == "新案待分配":
        case_record.status = "文书准备"
    db.add(WorkflowEvent(record_id=case_record.id, action="案件人员分配", from_status=previous, to_status=case_record.status, operator=identity["username"], comment=f"开庭律师：{case_data['hearing_lawyer']}；经办律师：{','.join(handling_lawyers)}；助理：{assistant}。{body.comment}"))
    await _ensure_document_preparation_task(case_record, db, system_operator=identity["username"])
    await _ensure_timestamp_evidence_handoff_task(case_record, db, system_operator=identity["username"])
    notary_id = int(case_data.get("notary_id") or 0)
    if notary_id and not case_data.get("notary_handoff_task_id"):
        notary = await db.get(BusinessRecord, notary_id)
        if notary:
            notary_data = notary.data or {}; scanner = str(notary_data.get("scan_uploaded_by") or notary.owner or identity["username"]).strip(); recipient = (assistant_username or next(iter(handling_usernames), "") or case_data["hearing_lawyer"])
            task = BusinessRecord(module="task", serial_no=await _next_manual_task_serial(db), title=f"公证书及公证费发票原件交接—{case_record.serial_no}", customer=case_record.customer, status="待接收", owner=scanner, department=case_record.department, description=f"扫描文员向案件文书人员 {recipient} 交接公证书及公证费发票原件", data={"deadline": str(date.today() + timedelta(days=5)), "priority": "紧急", "source": "案件任务", "creation_mode": "自动", "task_type": "自动任务", "initiator": recipient, "collaborators": [recipient] if recipient != scanner else [], "case_no": case_record.serial_no, "case_id": case_record.id, "notary_id": notary.id, "notary_no": notary.serial_no, "auto_task_type": "notary_original_handoff", "handoff_recipient": recipient, "system_created_by": identity["username"]})
            db.add(task); await db.flush(); case_record.data = {**case_record.data, "notary_handoff_task_id": task.id}; notary.data = {**notary_data, "handoff_task_id": task.id, "handoff_recipient": recipient}
            await _add_task_message_notifications(task, WorkflowEvent(record_id=task.id, action="系统生成原件交接任务", to_status="待接收", operator="system", comment=f"扫描文员 {scanner} 向 {recipient} 交接；来源案件 {case_record.serial_no}"), db, content="任务已分派.")
            db.add(WorkflowEvent(record_id=case_record.id, action="生成公证原件交接任务", from_status=case_record.status, to_status=case_record.status, operator="system", comment=f"任务 {task.serial_no}；负责人 {scanner}；接收人 {recipient}"))
    await db.commit()
    await db.refresh(case_record)
    return _record_dict(case_record)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/hearing-lawyer")
async def update_case_hearing_lawyer(
    case_id: int,
    body: CaseHearingLawyerInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Update the hearing lawyer independently from the creation wizard.

    The legacy action writes only the hearing-lawyer fields. Historical cases
    may retain an incomplete creation-step marker, which must not block this
    detail-page maintenance operation.
    """
    from app.core.cases import (
        _case_commission_personnel_changed, _recalculate_case_draft_commissions, _resolve_active_case_people,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}:
        raise HTTPException(status_code=409, detail="归档中的案件不能修改开庭律师")

    hearing_values, hearing_usernames = await _resolve_active_case_people(
        [body.hearing_lawyer], db, field_name="开庭律师",
    )
    before_case_data = dict(case_record.data or {})
    case_data = dict(before_case_data)
    previous_hearing_lawyer = str(case_data.get("hearing_lawyer") or "")
    case_data["hearing_lawyer"] = hearing_values[0]
    case_data["hearing_lawyer_username"] = hearing_usernames[0]
    case_record.data = case_data
    if _case_commission_personnel_changed(before_case_data, case_data):
        await _recalculate_case_draft_commissions(case_record, db, identity["username"])
    db.add(WorkflowEvent(
        record_id=case_record.id,
        action="修改开庭律师",
        from_status=case_record.status,
        to_status=case_record.status,
        operator=identity["username"],
        comment=(
            f"开庭律师：{previous_hearing_lawyer or '未设置'} → {hearing_values[0]}"
            + (f"；说明：{body.comment.strip()}" if body.comment.strip() else "")
        ),
    ))
    await assess_conflict_review(case_record, identity, db, trigger="case_save")
    await db.commit()
    await db.refresh(case_record)
    return _record_dict(case_record)


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/tasks")
async def list_case_tasks(
    case_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=200),
    scope: str = Query("", pattern="^(|case|customer)$"),
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
    is_vip: bool | None = None,
):
    from app.core.formatters import (
        _task_display_dict,
    )
    from app.core.permissions import (
        _ensure_case_read_module,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_case_read_module(case_id, identity, db)
    from app.core.case_task_view import case_task_relation
    link_condition = case_task_relation(case_record)
    base_task_condition = [BusinessRecord.module == "task", link_condition]
    task_condition = list(base_task_condition)
    if scope == "customer":
        task_condition.append(BusinessRecord.data["source"].as_string() == "客户任务")
    elif scope == "case":
        task_condition.append(func.coalesce(BusinessRecord.data["source"].as_string(), "") != "客户任务")
    if is_vip is True:
        task_condition.append(BusinessRecord.data["is_vip"].as_boolean().is_(True))
    elif is_vip is False:
        task_condition.append(or_(
            BusinessRecord.data["is_vip"].as_boolean().is_(False),
            BusinessRecord.data["is_vip"].as_boolean().is_(None),
        ))
    total = int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(*task_condition)) or 0)
    deadline_expr = func.coalesce(
        BusinessRecord.data["deadline"].as_string(),
        BusinessRecord.data["task_end_time"].as_string(),
        BusinessRecord.data["TaskEndTime"].as_string(),
    )
    rows = list((await db.scalars(
        select(BusinessRecord).where(*task_condition)
        .order_by(deadline_expr.desc(), BusinessRecord.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).all())
    pages = (total + page_size - 1) // page_size if total else 0
    items = [await _task_display_dict(item, db) for item in rows]
    for item in items:
        item["case_context_id"] = case_id
        if item.get("workflow_status") in {"待接收", "待处理"} and item.get("source") == "案件任务":
            item["status"] = "进行中"
    return {
        "case": _record_dict(case_record),
        "items": items,
        "total": total, "page": page, "page_size": page_size, "pages": pages,
    }


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/tasks/{{task_id}}")
async def read_case_task(case_id: int, task_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.case_task_view import case_task_detail
    return await case_task_detail(case_id, task_id, identity, db)


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/tasks/{{task_id}}/attachments/{{attachment_id}}/download")
async def download_case_task_file(case_id: int, task_id: int, attachment_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.case_task_view import visible_case_task
    from app.core.storage import _attachment_storage_path
    await visible_case_task(case_id, task_id, identity, db)
    item = await db.get(FileAttachment, attachment_id)
    if not item or item.record_id != task_id or item.category not in {"任务资料附件", "任务反馈附件"}:
        raise HTTPException(404, "该任务附件不存在")
    path = _attachment_storage_path(item)
    if path is None:
        raise HTTPException(404, "附件文件不存在")
    return FileResponse(path, media_type=item.content_type, filename=item.original_name)


@router.post(f"{settings.api_prefix}/cases/tasks/finished")
async def finish_case_tasks(
    body: CaseTaskFinishedInput,
    identity: dict = Depends(current_identity),
    db: AsyncSession = Depends(get_db),
):
    """Atomically implement legacy CaseTaskController.Finished(caseIds).

    The endpoint intentionally accepts case_ids only.  It resolves every linked
    task, checks case and task participation/status for the complete selection,
    then writes all status/events/notifications in one transaction.
    """
    from app.core.permissions import (
        _record_scope_conditions, _require_case_progress_write_access,
    )
    from app.core.tasks import (
        _add_task_message_notifications, _is_task_participant, _task_dict,
    )
    case_ids = list(dict.fromkeys(int(value) for value in body.case_ids))
    scope = await _record_scope_conditions(identity, db)
    cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case", BusinessRecord.id.in_(case_ids), *scope,
    ))).all())
    by_id = {case_record.id: case_record for case_record in cases}
    missing = [case_id for case_id in case_ids if case_id not in by_id]
    if missing:
        raise HTTPException(status_code=404, detail=f"未找到案件或当前账号无权查看: {','.join(str(value) for value in missing)}")
    for case_record in cases:
        await _require_case_progress_write_access(case_record, identity, db)

    links = [
        or_(BusinessRecord.data["case_id"].as_integer() == case_record.id, BusinessRecord.data["case_no"].as_string() == case_record.serial_no)
        for case_record in cases
    ]
    all_tasks = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "task", or_(*links),
    ))).all()) if links else []
    grouped: dict[int, list[BusinessRecord]] = {case_record.id: [] for case_record in cases}
    for task in all_tasks:
        data = task.data or {}
        for case_record in cases:
            if str(data.get("case_id") or "") == str(case_record.id) or str(data.get("case_no") or "") == case_record.serial_no:
                grouped[case_record.id].append(task)
                break
    for case_record in cases:
        linked = grouped[case_record.id]
        if not linked:
            raise HTTPException(status_code=409, detail="案件没有可完成的任务")
        for task in linked:
            if not _is_task_participant(task, identity):
                raise HTTPException(status_code=403, detail="只有任务参与人可以结束案件任务")
            if task.status != "处理中":
                raise HTTPException(status_code=409, detail="存在当前状态不能结束的任务")

    try:
        updated: list[BusinessRecord] = []
        comment = body.comment.strip()
        for case_record in cases:
            for task in grouped[case_record.id]:
                previous = task.status
                task.status = "已完成"
                task.data = {
                    **(task.data or {}),
                    "completion_submitted_at": datetime.now().isoformat(timespec="seconds"),
                    "completion_comment": comment,
                    "completion_case_id": case_record.id,
                }
                await _add_task_message_notifications(
                    task,
                    WorkflowEvent(
                        record_id=task.id, action="案件任务批量完成", from_status=previous,
                        to_status=task.status, operator=identity["username"], comment=comment,
                    ),
                    db,
                    content="任务结束成功！",
                )
                updated.append(task)
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="标记失败！")
    for task in updated:
        await db.refresh(task)
    return {
        "message": "标记成功！", "case_ids": case_ids, "updated": len(updated),
        "items": [_task_dict(task) for task in updated],
    }


@router.post(f"{settings.api_prefix}/cases/execution-status")
async def update_case_execution_status(body: CaseExecutionStatusInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _validate_case_execution_status,
    )
    from app.core.formatters import (
        _normalize_case_numbers,
    )
    from app.core.permissions import (
        _record_scope_conditions, _require_case_progress_write_access,
    )
    from app.core.system import (
        _record_dict,
    )
    case_nos = _normalize_case_numbers(body.case_nos)
    if not case_nos:
        raise HTTPException(status_code=422, detail="至少选择一件案件")
    execution_status = _validate_case_execution_status(body.execution_status)
    scope = await _record_scope_conditions(identity, db)
    # The legacy case_nos.in_(case_nos) filter is represented by the serial_no column below.
    all_cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case", BusinessRecord.serial_no.in_(case_nos), *scope,
    ))).all())
    by_no = {case_record.serial_no: case_record for case_record in all_cases}
    missing = [case_no for case_no in case_nos if case_no not in by_no]
    if missing:
        raise HTTPException(status_code=404, detail=f"未找到案件或当前账号无权查看：{','.join(missing)}")
    for case_record in all_cases:
        await _require_case_progress_write_access(case_record, identity, db)
    for case_record in all_cases:
        previous_status = str((case_record.data or {}).get("execution_status") or "")
        case_record.data = {**(case_record.data or {}), "execution_status": execution_status}
        db.add(WorkflowEvent(
            record_id=case_record.id, action="修改案件执行状态", from_status=case_record.status,
            to_status=case_record.status, operator=identity["username"],
            comment=body.comment.strip() or f"{previous_status or '未设置'} → {execution_status}",
        ))
    await db.commit()
    for case_record in all_cases:
        await db.refresh(case_record)
    return {
        "message": "修改成功！", "updated": len(all_cases), "case_nos": case_nos,
        "execution_status": execution_status, "items": [_record_dict(case_record) for case_record in all_cases],
    }


@router.get(f"{settings.api_prefix}/cases/phases")
async def list_case_phases(case_type: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_phase_option, _case_type_parameter_for_value, _phase_is_builtin_for_case_type,
    )
    from app.core.permissions import (
        _require_record_module_menu,
    )
    await _require_record_module_menu("case", identity, db, action="查看")
    phases = list((await db.scalars(select(SystemParameter).where(
        SystemParameter.category == "case_phase", SystemParameter.is_active.is_(True),
    ).order_by(SystemParameter.sort_order, SystemParameter.id))).all())
    case_type_parameter = await _case_type_parameter_for_value(case_type, db)
    if case_type_parameter:
        related_ids = set((await db.scalars(select(CaseTypeCasePhaseRelation.case_phase_id).where(
            CaseTypeCasePhaseRelation.case_type_id == case_type_parameter.id,
        ))).all())
        builtin_ids = {phase.id for phase in phases if _phase_is_builtin_for_case_type(phase, case_type_parameter)}
        if related_ids or builtin_ids:
            phases = [phase for phase in phases if phase.id in related_ids or phase.id in builtin_ids]
    return {"items": [_case_phase_option(item) for item in phases]}


@router.post(f"{settings.api_prefix}/cases/phase-change")
async def update_case_phase(body: CasePhaseChangeInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_phase_is_allowed, _resolve_case_phase,
    )
    from app.core.formatters import (
        _normalize_case_numbers,
    )
    from app.core.permissions import (
        _record_scope_conditions, _require_case_phase_change_access,
    )
    from app.core.system import (
        _record_dict,
    )
    from app.core.tasks import (
        _ensure_execution_application_reminder_task,
        _ensure_document_preparation_task,
        _ensure_phase_automatic_tasks,
        _ensure_timestamp_evidence_handoff_task,
    )
    case_nos = _normalize_case_numbers(body.case_nos)
    if not case_nos:
        raise HTTPException(status_code=422, detail="至少选择一件案件")
    phase = await _resolve_case_phase(body, db)
    scope = await _record_scope_conditions(identity, db)
    # Preflight every selected case before changing any record, matching the legacy batch contract.
    all_cases = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case", BusinessRecord.serial_no.in_(case_nos), *scope,
    ))).all())
    by_no = {case_record.serial_no: case_record for case_record in all_cases}
    missing = [case_no for case_no in case_nos if case_no not in by_no]
    if missing:
        raise HTTPException(status_code=404, detail=f"未找到案件或当前账号无权查看：{','.join(missing)}")
    for case_record in all_cases:
        if case_record.status == "已合并":
            raise HTTPException(status_code=409, detail="已合并案件不能修改案件阶段")
        await _require_case_phase_change_access(case_record, identity, db)
        await require_conflict_clear(case_record, db, action="修改案件阶段")
        case_data = case_record.data or {}
        if not await _case_phase_is_allowed(str(case_data.get("case_type") or ""), phase["id"], db):
            raise HTTPException(status_code=422, detail=f"案件 {case_record.serial_no} 的类型不允许使用阶段“{phase['name']}”")
        if int(case_data.get("case_phase_id") or 0) == phase["id"] or case_record.status == phase["canonical_name"]:
            raise HTTPException(status_code=409, detail="当前案件已处于所选阶段")
    try:
        changed_at = datetime.now().isoformat(timespec="seconds")
        for case_record in all_cases:
            previous_status = case_record.status
            case_record.status = phase["canonical_name"]
            case_record.data = {
                **(case_record.data or {}),
                "case_phase_id": phase["id"], "case_phase_code": phase["code"],
                "case_phase_name": phase["name"], "phase_changed_at": changed_at,
            }
            db.add(WorkflowEvent(
                record_id=case_record.id, action="修改案件阶段", from_status=previous_status,
                to_status=case_record.status, operator=identity["username"],
                comment=f"{phase['name']}（{phase['id']}）" + (f"｜{body.comment.strip()}" if body.comment.strip() else ""),
            ))
            await _ensure_execution_application_reminder_task(
                case_record, db, previous_status=previous_status, operator=identity["username"],
            )
            await _ensure_document_preparation_task(case_record, db, system_operator=identity["username"])
            await _ensure_timestamp_evidence_handoff_task(case_record, db, system_operator=identity["username"])
            await _ensure_phase_automatic_tasks(case_record, db, previous_status=previous_status)
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="修改失败！")
    for case_record in all_cases:
        await db.refresh(case_record)
    return {
        "message": "修改成功！", "updated": len(all_cases), "case_nos": case_nos,
        "phase": phase, "items": [_record_dict(case_record) for case_record in all_cases],
    }


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/progress")
async def update_case_progress(case_id: int, body: CaseProgressInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module, _require_case_progress_write_access,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db); await _require_case_progress_write_access(case_record, identity, db)
    if case_record.status in {"等待公证书", "等待审核公证书", "待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}: raise HTTPException(status_code=409, detail="当前案件阶段不能登记诉讼进展")
    values = body.model_dump()
    for key, value in list(values.items()):
        if isinstance(value, date):
            values[key] = str(value)
    progress_keys = [
        "first_instance_court", "first_instance_case_no", "courtroom", "judge", "clerk", "judgment_date", "judgment_document_no",
        "second_instance_court", "second_instance_case_no", "first_court_name", "first_court_case_no", "second_court_name", "second_court_case_no",
        "execution_court_name", "execution_court_case_no", "retrial_court_name", "retrial_court_case_no",
        "first_court_courtroom", "first_court_judge", "first_court_clerk", "first_court_filing_date", "first_court_hearing_date", "first_court_judgment_date",
        "second_court_courtroom", "second_court_judge", "second_court_clerk", "second_court_filing_date", "second_court_hearing_date", "second_court_judgment_date",
        "execution_court_courtroom", "execution_court_judge", "execution_court_clerk", "execution_court_filing_date", "execution_court_hearing_date", "execution_court_judgment_date",
        "retrial_court_courtroom", "retrial_court_judge", "retrial_court_clerk", "retrial_court_filing_date", "retrial_court_hearing_date", "retrial_court_judgment_date",
    ]
    if not any(values.get(key) for key in progress_keys): raise HTTPException(status_code=422, detail="请至少填写一项案件进展信息")
    previous = case_record.status; target = previous
    if body.retrial_court_name.strip() or body.retrial_court_case_no.strip(): target = "再审"
    elif body.execution_court_name.strip() or body.execution_court_case_no.strip(): target = "执行"
    elif body.second_instance_case_no.strip() or body.second_court_name.strip() or body.second_court_case_no.strip(): target = "二审"
    elif body.judgment_date or body.judgment_document_no.strip(): target = "待上诉"
    elif body.first_instance_case_no.strip(): target = "一审立案受理"
    stage_rank = {"新案待分配": 0, "文书准备": 1, "一审立案受理": 2, "一审准备开庭": 3, "待上诉": 4, "二审": 5, "再审": 6, "执行": 7}
    if stage_rank.get(target, -1) < stage_rank.get(previous, -1): target = previous
    canonical_stage = "再审" if (body.retrial_court_name.strip() or body.retrial_court_case_no.strip()) else "执行" if (body.execution_court_name.strip() or body.execution_court_case_no.strip()) else "判决" if (body.judgment_date or body.judgment_document_no.strip()) else "审理" if (body.second_instance_case_no.strip() or body.second_court_name.strip() or body.second_court_case_no.strip()) else "立案"
    submitted_fields = body.model_fields_set
    merged_progress = {
        **(case_record.data or {}),
        **{
            key: value.strip() if isinstance(value, str) else value
            for key, value in values.items()
            if key != "comment" and key in submitted_fields
        },
        "business_stage": canonical_stage,
    }
    # Keep the legacy progress aliases and the detail-page canonical fields in sync.
    # Older cases use first_instance_court/second_instance_court while the detail
    # view reads first_court_name/second_court_name.
    if body.first_instance_court.strip():
        merged_progress["first_court_name"] = body.first_instance_court.strip()
        merged_progress["court"] = body.first_instance_court.strip()
    if body.first_instance_case_no.strip():
        merged_progress["first_court_case_no"] = body.first_instance_case_no.strip()
    if body.first_court_name.strip():
        merged_progress["first_instance_court"] = body.first_court_name.strip()
        merged_progress["court"] = body.first_court_name.strip()
    if body.second_instance_court.strip():
        merged_progress["second_court_name"] = body.second_instance_court.strip()
    if body.second_instance_case_no.strip():
        merged_progress["second_court_case_no"] = body.second_instance_case_no.strip()
    if body.second_court_name.strip():
        merged_progress["second_instance_court"] = body.second_court_name.strip()
    previous_business_stage = (case_record.data or {}).get("business_stage")
    case_record.data = merged_progress
    await assess_conflict_review(case_record, identity, db, trigger="case_save")
    gate = await get_conflict_review_gate(case_record, db, action="登记案件诉讼进展")
    if gate["blocking"]:
        target = previous
        case_record.data = {**case_record.data, "business_stage": previous_business_stage}
    if target != previous:
        case_record.data = {**case_record.data, "phase_changed_at": datetime.now().isoformat(timespec="seconds")}
    case_record.status = target
    progress_comment = "诉讼进展资料已保存，案件阶段待利益冲突核查" if gate["blocking"] else "根据法院案号、裁判日期等案件要素自动推进阶段"
    db.add(WorkflowEvent(record_id=case_record.id, action="登记案件诉讼进展", from_status=previous, to_status=target, operator=identity["username"], comment=body.comment or progress_comment))
    await db.commit(); await db.refresh(case_record); return _record_dict(case_record)


@router.put(f"{settings.api_prefix}/cases/{{case_id}}/court-info")
async def update_case_court_info(case_id: int, body: CaseCourtInfoInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """Persist one or more court-dialog fields without changing case workflow state."""
    from app.core.permissions import (
        _ensure_record_module, _require_case_court_info_write_access,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_court_info_write_access(case_record, identity, db)
    submitted_fields = set(body.model_fields_set) - {"comment"}
    if not submitted_fields:
        raise HTTPException(status_code=422, detail="请至少提交一项法院信息")
    values = body.model_dump()
    payload = {
        key: (str(value) if isinstance(value, date) else value.strip() if isinstance(value, str) else value)
        for key, value in values.items()
        if key in submitted_fields
    }
    merged = {**(case_record.data or {}), **payload}
    # Keep old and current field names synchronized, including deliberate clears.
    if "first_instance_court" in payload:
        merged["first_court_name"] = payload["first_instance_court"]
        merged["court"] = payload["first_instance_court"]
    if "first_instance_case_no" in payload:
        merged["first_court_case_no"] = payload["first_instance_case_no"]
    if "first_court_name" in payload:
        merged["first_instance_court"] = payload["first_court_name"]
        merged["court"] = payload["first_court_name"]
    if "first_court_case_no" in payload:
        merged["first_instance_case_no"] = payload["first_court_case_no"]
    if "second_instance_court" in payload:
        merged["second_court_name"] = payload["second_instance_court"]
    if "second_instance_case_no" in payload:
        merged["second_court_case_no"] = payload["second_instance_case_no"]
    if "second_court_name" in payload:
        merged["second_instance_court"] = payload["second_court_name"]
    if "second_court_case_no" in payload:
        merged["second_instance_case_no"] = payload["second_court_case_no"]
    court_levels = {
        "first_court": "一审法院", "second_court": "二审法院",
        "execution_court": "执行法院", "retrial_court": "再审法院",
    }
    for prefix, label in court_levels.items():
        alias = "first_instance_" if prefix == "first_court" else "second_instance_" if prefix == "second_court" else None
        if any(key.startswith(prefix + "_") or (alias and key.startswith(alias)) for key in payload):
            if not str(merged.get(prefix + "_name") or "").strip():
                raise HTTPException(status_code=422, detail=f"请填写{label}，不能只提交日期或案号")
    case_record.data = merged
    db.add(WorkflowEvent(
        record_id=case_record.id,
        action="修改法院信息",
        from_status=case_record.status,
        to_status=case_record.status,
        operator=identity["username"],
        comment=body.comment.strip() or "直接维护法院信息",
    ))
    await assess_conflict_review(case_record, identity, db, trigger="case_save")
    await db.commit()
    await db.refresh(case_record)
    return _record_dict(case_record)


@router.get(f"{settings.api_prefix}/hearings")
async def list_hearings(
    date_from: date | None = None, date_to: date | None = None,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.cases import (
        _hearing_dict,
    )
    from app.core.permissions import (
        _record_scope_conditions,
    )
    conditions = []
    if date_from:
        conditions.append(HearingSchedule.hearing_date >= date_from)
    if date_to:
        conditions.append(HearingSchedule.hearing_date <= date_to)
    schedules = (await db.scalars(select(HearingSchedule).where(*conditions).order_by(HearingSchedule.hearing_date, HearingSchedule.hearing_time))).all()
    case_ids = {item.case_record_id for item in schedules}
    cases = {item.id: item for item in (await db.scalars(select(BusinessRecord).where(BusinessRecord.id.in_(case_ids), *(await _record_scope_conditions(identity, db))))).all()} if case_ids else {}
    items = [_hearing_dict(item, cases[item.case_record_id]) for item in schedules if item.case_record_id in cases]
    return {"items": items, "total": len(items)}


@router.post(f"{settings.api_prefix}/hearings", status_code=status.HTTP_201_CREATED)
async def create_hearing(body: HearingInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _hearing_dict,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_case_progress_write_access,
    )
    case_record = await _ensure_record_module(body.case_record_id, "case", identity, db)
    await _require_case_progress_write_access(case_record, identity, db)
    item = HearingSchedule(**body.model_dump(), status="已排期")
    db.add(item)
    await db.flush()
    previous_status = case_record.status
    case_record.data = {**(case_record.data or {}), "court": body.court, "next_hearing_date": str(body.hearing_date), "next_hearing_time": body.hearing_time, "hearing_lawyer": body.hearing_lawyer, "business_stage": "审理"}
    if body.hearing_type.startswith("二审"):
        case_record.status = "二审"
    elif case_record.status in {"新案待分配", "文书准备", "一审立案受理"}:
        case_record.status = "一审准备开庭"
    db.add(WorkflowEvent(record_id=case_record.id, action="新增开庭排期并推进阶段", from_status=previous_status, to_status=case_record.status, operator=identity["username"], comment=f"{body.hearing_date} {body.hearing_time} {body.court} {body.courtroom}"))
    await db.commit()
    await db.refresh(item)
    return _hearing_dict(item, case_record)


@router.delete(f"{settings.api_prefix}/hearings/{{hearing_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hearing(hearing_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    if identity["role"] != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可删除排期")
    item = await db.get(HearingSchedule, hearing_id)
    if not item:
        raise HTTPException(status_code=404, detail="排期不存在")
    await db.delete(item)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(f"{settings.api_prefix}/hearing-sms/outbox")
async def hearing_sms_outbox(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _record_scope_conditions,
    )
    from app.core.system import (
        _record_dict,
    )
    if identity.get("role") not in {"admin", "manager"}: raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以查看短信发送记录")
    items = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "sms", *(await _record_scope_conditions(identity, db))).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()).limit(200))).all())
    return {"items": [_record_dict(item) for item in items], "total": len(items), "provider_configured": bool(settings.sms_webhook_url)}


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/archive-readiness")
async def archive_readiness(case_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_archive_readiness,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    data = case_record.data or {}
    checks, check_details, _ = await _case_archive_readiness(case_record, db)
    return {"case_id": case_id, "case_no": case_record.serial_no, "status": case_record.status, "checks": checks, "check_details": check_details, "archive_no": data.get("archive_no", ""), "paper_archive_location": data.get("paper_archive_location", ""), "paper_volume_count": data.get("paper_volume_count", 1), "archive_type": data.get("archive_type", "normal"), "archive_reject_reason": data.get("archive_reject_reason", ""), "ready": all(checks.values())}


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/close")
async def close_case_for_archive(case_id: int, body: TaskActionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _record_links_to_case,
    )
    from app.core.permissions import (
        _ensure_record_module, _record_dict_for_identity,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"}: raise HTTPException(status_code=409, detail="归档审核中或已归档案件不能重复办结")
    if (case_record.data or {}).get("case_closed_at"): raise HTTPException(status_code=409, detail="案件已经办理办结确认")
    tasks = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "task"))).all()
    active_tasks = [
        item for item in tasks
        if _record_links_to_case(item, case_record)
        and item.status not in {"已完成", "已验收", "已停止", "已撤回", "已拒绝", "已取消"}
    ]
    if active_tasks: raise HTTPException(status_code=409, detail=f"仍有 {len(active_tasks)} 项案件任务未办结，不能确认案件办结")
    now = datetime.now(timezone.utc)
    case_record.data = {**(case_record.data or {}), "case_closed": True, "case_closed_at": now.isoformat(), "case_closed_by": identity["username"], "case_close_comment": body.comment.strip(), "business_stage": "结案"}
    db.add(WorkflowEvent(record_id=case_record.id, action="确认案件办结", from_status=case_record.status, to_status=case_record.status, operator=identity["username"], comment=body.comment.strip()))
    await db.commit(); await db.refresh(case_record)
    return await _record_dict_for_identity(case_record, identity, db)


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/archive")
async def archive_case(case_id: int, body: ArchiveCheckInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _case_archive_checks,
    )
    from app.core.legacy_sync import (
        _sync_legacy_case,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    if case_record.status == "已归档": raise HTTPException(status_code=409, detail="案件已经归档")
    if case_record.status in {"待归档审核", "亏损内审", "亏损审核"} and body.submit: raise HTTPException(status_code=409, detail="案件已提交归档审核，请等待审核")
    checks = await _case_archive_checks(case_record, db)
    archive_type = body.archive_type if body.archive_type in {"normal", "deficit"} else "normal"
    if body.submit and archive_type == "deficit" and not body.comment.strip():
        raise HTTPException(status_code=422, detail="亏损归档必须填写亏损原因")
    details = {"archive_no": body.archive_no.strip(), "paper_archive_location": body.paper_archive_location.strip(), "paper_volume_count": body.paper_volume_count, "archive_type": archive_type}
    case_record.data = {**(case_record.data or {}), **checks, **details}
    if body.submit and archive_type == "normal" and not checks["fees_settled"]:
        details = ((case_record.data or {}).get("archive_check_details") or {}).get("unsettled_fees") or []
        fee_messages = [f"{item.get('fee_no')} {item.get('fee_type')} 尚差 {float(item.get('outstanding') or 0):.2f} 元" for item in details]
        raise HTTPException(status_code=409, detail="正常归档申请前请先结清案件费用" + ("：" + "；".join(fee_messages) if fee_messages else ""))
    previous = case_record.status
    action = "保存归档检查"
    if body.submit:
        case_record.data = {
            **(case_record.data or {}),
            "status_before_archive": previous,
            "archive_submitted_at": datetime.now().isoformat(timespec="seconds"),
            "archive_submitter": identity["username"],
            "archive_submit_comment": body.comment.strip(),
            "archive_reject_reason": "",
        }
        if archive_type == "deficit":
            case_record.status = "亏损内审"
            case_record.data = {
                **(case_record.data or {}),
                "case_phase": "亏损内审",
                "case_phase_id": 106016,
                "archive_status": "待内部审核",
                "archive_status_code": 7,
                "archive_internal_reviewer": "",
                "archive_internal_review_comment": "",
                "archive_internal_reviewed_at": None,
            }
            action = "提交亏损归档内部审核"
        else:
            case_record.status = "待归档审核"
            case_record.data = {
                **(case_record.data or {}),
                "archive_status": "待审核",
                "archive_status_code": 10,
            }
            action = "提交归档审核"
    type_label = "亏损归档" if archive_type == "deficit" else "正常归档"
    db.add(WorkflowEvent(record_id=case_record.id, action=action, from_status=previous, to_status=case_record.status, operator=identity["username"], comment=body.comment or (f"{type_label}；归档号：{details['archive_no']}；纸质卷宗：{details['paper_archive_location']}，{details['paper_volume_count']} 卷" if body.submit else f"更新{type_label}检查项")))
    await _sync_legacy_case(case_record, identity, db)
    await db.commit()
    await db.refresh(case_record)
    return {"record": _record_dict(case_record), "checks": checks, "ready": all(checks.values())}


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/archive/review")
async def review_case_archive(case_id: int, body: ArchiveReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.system import _record_dict
    try:
        await db.scalar(select(BusinessRecord).where(BusinessRecord.id == case_id).with_for_update())
        record = await _apply_case_archive_review(case_id, body, identity, db)
        await db.commit()
        await db.refresh(record)
        return _record_dict(record)
    except Exception:
        await db.rollback()
        raise


async def _apply_case_archive_review(case_id: int, body: ArchiveReviewInput, identity: dict, db: AsyncSession):
    """Apply one review inside the caller's transaction; never commit here."""
    from app.core.cases import (
        _case_archive_checks,
    )
    from app.core.legacy_sync import (
        _sync_legacy_case,
    )
    from app.core.finance import (
        _sync_case_commissions_for_links,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_case_action,
    )
    await _require_case_action(identity, db, "case.archive.review")
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    if case_record.status not in {"归档审核", "待归档审核", "亏损内审", "亏损审核"}: raise HTTPException(status_code=409, detail="只有待归档审核案件可以审核")
    if len(body.comment.strip()) < 2:
        raise HTTPException(status_code=422, detail="审核备注至少填写两个字")
    data = dict(case_record.data or {})
    if str(data.get("archive_submitter") or "").strip() == identity["username"]:
        raise HTTPException(status_code=403, detail="归档申请人不能审核本人提交的归档申请")
    if (
        case_record.status == "亏损审核"
        and str(data.get("archive_internal_reviewer") or "").strip() == identity["username"]
    ):
        raise HTTPException(status_code=403, detail="亏损归档内审人与最终审核人必须相互独立")
    archive_type = str(data.get("archive_type") or "normal")
    if archive_type == "deficit" and case_record.status == "待归档审核" and not data.get("archive_internal_reviewed_at"):
        case_record.status = "亏损内审"
    if body.approved and case_record.status != "亏损内审" and archive_type != "deficit":
        checks = await _case_archive_checks(case_record, db)
        # The legacy workflow treats material completeness and refund status as
        # reviewer guidance. Only unsettled case fees are a hard blocker.
        if not checks["fees_settled"]:
            raise HTTPException(status_code=409, detail="案件费用未到账，不允许通过归档审核")
    previous = case_record.status
    reviewed_at = datetime.now()
    if previous == "亏损内审":
        case_record.data = {
            **data,
            "archive_internal_reviewer": identity["username"],
            "archive_internal_reviewed_at": reviewed_at.isoformat(timespec="seconds"),
            "archive_internal_review_comment": body.comment.strip(),
        }
        if body.approved:
            case_record.status = "亏损审核"
            case_record.data = {
                **(case_record.data or {}),
                "case_phase": "亏损审核",
                "case_phase_id": 106017,
                "archive_status": "待审核",
                "archive_status_code": 10,
                "archive_reject_reason": "",
            }
            action = "亏损归档内部审核通过"
        else:
            case_record.status = "亏损归档拒绝"
            case_record.data = {
                **(case_record.data or {}),
                "case_phase": "亏损归档拒绝",
                "case_phase_id": 106019,
                "archive_status": "已拒绝",
                "archive_reject_reason": body.comment.strip(),
            }
            action = "亏损归档内部审核驳回"
    elif body.approved:
        case_record.status = "亏损归档" if archive_type == "deficit" else "已归档"
        archived_at = datetime.now()
        archive_no = body.archive_no.strip() or str(data.get("archive_no") or "").strip()
        if archive_type != "deficit" and not archive_no:
            raise HTTPException(status_code=422, detail="请填写归档号")
        case_record.data = {
            **data,
            "case_phase": "亏损归档" if archive_type == "deficit" else data.get("case_phase", "已归档"),
            "case_phase_id": 106018 if archive_type == "deficit" else data.get("case_phase_id"),
            "archive_status": "审核通过",
            "archive_status_code": 20,
            "archived_at": archived_at.isoformat(timespec="seconds"),
            "archive_reviewed_at": archived_at.isoformat(timespec="seconds"),
            "archive_no": archive_no,
            "archive_reviewer": identity["username"],
            "archive_review_comment": body.comment.strip(),
            "archive_reject_reason": "",
        }
        action = "亏损归档审核通过" if archive_type == "deficit" else "归档审核通过"
    else:
        restored_status = str(data.get("status_before_archive") or "执行")
        if archive_type == "deficit":
            case_record.status = "亏损归档拒绝"
            case_record.data = {
                **data,
                "case_phase": "亏损归档拒绝",
                "case_phase_id": 106019,
                "archive_status": "已拒绝",
                "archive_reviewer": identity["username"],
                "archive_reviewed_at": reviewed_at.isoformat(timespec="seconds"),
                "archive_reject_reason": body.comment.strip(),
            }
            action = "亏损归档审核驳回"
        else:
            if restored_status in {"归档审核", "待归档审核", "已归档"}: restored_status = "执行"
            case_record.status = restored_status
            case_record.data = {**data, "archive_reviewer": identity["username"], "archive_reviewed_at": reviewed_at.isoformat(timespec="seconds"), "archive_reject_reason": body.comment.strip()}
            action = "归档审核驳回"
    db.add(WorkflowEvent(record_id=case_record.id, action=action, from_status=previous, to_status=case_record.status, operator=identity["username"], comment=body.comment))
    await _sync_case_commissions_for_links(
        db,
        operator=identity["username"],
        case_ids={case_record.id},
        comment=action,
    )
    await _sync_legacy_case(case_record, identity, db)
    return case_record


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/unarchive/request")
async def request_case_unarchive(case_id: int, body: CaseUnarchiveRequestInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _record_dict,
    )
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    if case_record.status != "已归档":
        raise HTTPException(status_code=409, detail="只有已归档案件可以申请解档")
    data = case_record.data or {}; pending = data.get("unarchive_request") or {}
    if pending.get("status") == "待审批":
        raise HTTPException(status_code=409, detail="该案件已有解档申请正在审批")
    request_data = {
        "status": "待审批", "reason": body.reason.strip(), "requested_by": identity["username"],
        "requested_at": datetime.now().isoformat(timespec="seconds"),
    }
    case_record.data = {**data, "unarchive_request": request_data}
    db.add(WorkflowEvent(record_id=case_record.id, action="提交解档申请", from_status="已归档", to_status="已归档", operator=identity["username"], comment=body.reason.strip()))
    await db.commit(); await db.refresh(case_record)
    return _record_dict(case_record)


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/unarchive/review")
async def review_case_unarchive(case_id: int, body: CaseUnarchiveReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _sync_case_commissions_for_links,
    )
    from app.core.permissions import (
        _ensure_record_module,
    )
    from app.core.system import (
        _record_dict,
    )
    if identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="只有管理员或部门负责人可以审批解档")
    case_record = await _ensure_record_module(case_id, "case", identity, db)
    data = case_record.data or {}; pending = data.get("unarchive_request") or {}
    if case_record.status != "已归档" or pending.get("status") != "待审批":
        raise HTTPException(status_code=409, detail="该案件没有待审批的解档申请")
    if pending.get("requested_by") == identity["username"] and identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="解档申请人不能审批自己的申请")
    if not body.approved and not body.comment.strip():
        raise HTTPException(status_code=422, detail="驳回时必须填写原因")
    previous = case_record.status
    reviewed = {
        **pending, "status": "已通过" if body.approved else "已驳回", "reviewed_by": identity["username"],
        "reviewed_at": datetime.now().isoformat(timespec="seconds"), "review_comment": body.comment.strip(),
    }
    if body.approved:
        restored_status = str(data.get("status_before_archive") or "执行")
        if restored_status in {"已归档", "待归档审核", "待立案审批"}: restored_status = "执行"
        case_record.status = restored_status
        case_record.data = {**data, "unarchive_request": reviewed, "unarchived_at": datetime.now().isoformat(timespec="seconds"), "unarchived_by": identity["username"], "archive_locked": False}
        action = "解档审批通过"
    else:
        case_record.data = {**data, "unarchive_request": reviewed}
        action = "解档审批驳回"
    db.add(WorkflowEvent(record_id=case_record.id, action=action, from_status=previous, to_status=case_record.status, operator=identity["username"], comment=body.comment))
    if body.approved:
        await _sync_case_commissions_for_links(
            db,
            operator=identity["username"],
            case_ids={case_record.id},
            comment=action,
        )
    await db.commit(); await db.refresh(case_record)
    return _record_dict(case_record)


from app.areas.legal.case_documents import (
    router as case_documents_router,
    list_case_document_folders as list_case_document_folders,
    create_case_document_folder as create_case_document_folder,
    rename_case_document_folder as rename_case_document_folder,
    delete_case_document_folder as delete_case_document_folder,
    get_case_ai_space as get_case_ai_space,
    create_case_ai_draft as create_case_ai_draft,
    get_case_ai_draft_content as get_case_ai_draft_content,
    update_case_ai_draft_content as update_case_ai_draft_content,
    promote_case_ai_draft as promote_case_ai_draft,
    get_case_word_editor_content as get_case_word_editor_content,
    acquire_case_word_editor_lock as acquire_case_word_editor_lock,
    renew_case_word_editor_lock as renew_case_word_editor_lock,
    update_case_word_editor_content as update_case_word_editor_content,
    release_case_word_editor_lock as release_case_word_editor_lock,
    download_case_attachments as download_case_attachments,
    delete_case_attachments as delete_case_attachments,
    unlock_case_attachment as unlock_case_attachment,
    move_case_attachments as move_case_attachments,
    rename_case_attachment as rename_case_attachment,
)
router.include_router(case_documents_router)


from app.areas.legal.seals import (
    router as seals_router,
    batch_delete_seal_attachments as batch_delete_seal_attachments,
    list_seal_applications as list_seal_applications,
    batch_download_seal_files as batch_download_seal_files,
    package_download_seal_files as package_download_seal_files,
    create_seal_application as create_seal_application,
    update_seal_application as update_seal_application,
    delete_seal_application as delete_seal_application,
    list_seal_application_files as list_seal_application_files,
    upload_seal_application_files as upload_seal_application_files,
    submit_seal_application as submit_seal_application,
    withdraw_seal_application as withdraw_seal_application,
    batch_withdraw_seal_applications as batch_withdraw_seal_applications,
    approve_seal_application as approve_seal_application,
    stamp_seal_application as stamp_seal_application,
    batch_stamp_seal_applications as batch_stamp_seal_applications,
    archive_seal_application as archive_seal_application,
    list_seal_assets as list_seal_assets,
    list_seal_asset_audit as list_seal_asset_audit,
    create_seal_asset as create_seal_asset,
    update_seal_asset as update_seal_asset,
    delete_seal_asset as delete_seal_asset,
)
router.include_router(seals_router)


@router.post(f"{settings.api_prefix}/cases/{{case_id}}/documents/{{document_type}}", status_code=status.HTTP_201_CREATED)
async def generate_case_document(case_id: int, document_type: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.documents import (
        _case_document_bytes, _case_document_context, _case_document_required_fields,
    )
    from app.core.permissions import (
        _ensure_record_module, _require_case_document_write_access,
    )
    from app.core.storage import (
        _attachment_dict,
    )
    if document_type not in CASE_DOCUMENT_TYPES:
        raise HTTPException(status_code=404, detail="不支持的案件文书类型")
    record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_document_write_access(record, identity, db)
    if record.status in {"已合并", "已归档"}:
        raise HTTPException(status_code=409, detail="已合并或已归档案件不能再生成办理文书")
    context = await _case_document_context(record, db)
    missing_fields = _case_document_required_fields(record, document_type, context)
    if missing_fields:
        raise HTTPException(status_code=422, detail=f"{record.serial_no} 缺少{'、'.join(missing_fields)}，不能生成{CASE_DOCUMENT_TYPES[document_type]}")
    title, content = _case_document_bytes(record, document_type, context)
    stored_name = f"{uuid4().hex}.docx"
    path = UPLOAD_ROOT / stored_name
    path.write_bytes(content)
    attachment = FileAttachment(record_id=record.id, category=CASE_DOCUMENT_CATEGORY.get(document_type, "案件生成文书"), original_name=f"{record.serial_no}-{title}-{datetime.now():%Y%m%d%H%M%S}.docx", stored_name=stored_name, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", size=len(content), path=str(path), uploader=identity["username"], remark=f"系统生成案件文书：{document_type}")
    try:
        db.add(attachment); await db.flush()
        db.add(WorkflowEvent(record_id=record.id, action="生成案件文书", from_status=record.status, to_status=record.status, operator=identity["username"], comment=f"{title}｜附件 {attachment.original_name}"))
        await db.commit(); await db.refresh(attachment)
    except Exception:
        await db.rollback()
        path.unlink(missing_ok=True)
        raise
    return _attachment_dict(attachment, record)


@router.post(f"{settings.api_prefix}/records", status_code=status.HTTP_201_CREATED)
async def create_record(body: RecordInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.crm import (
        _resolve_active_customer_managers,
    )
    from app.core.legacy_sync import (
        _sync_legacy_projection,
    )
    from app.core.permissions import (
        _ensure_record_visible, _require_record_module_menu,
    )
    from app.core.system import (
        _record_dict,
    )
    if body.module == "conflict_review":
        raise HTTPException(status_code=409, detail="利益冲突审查必须使用专用入口办理")
    if body.module == "finance_fee_inform":
        raise HTTPException(status_code=422, detail="费用通知必须使用案件费用的专用通知入口创建")
    await _require_record_module_menu(body.module, identity, db, action="新建")
    if body.module in INVESTIGATION_RECORD_MODULES:
        raise HTTPException(status_code=422, detail="调查、公证和证据记录必须使用调查中心专用入口创建")
    if body.module == "customer":
        raise HTTPException(status_code=422, detail="新建客户必须使用客户专用入口")
    if body.module == "contract":
        raise HTTPException(status_code=422, detail="新建合同必须使用合同专用入口")
    if body.module == "case":
        raise HTTPException(status_code=422, detail="新建案件必须选择已审批合同，请使用案件创建入口")
    if body.module == "seal":
        raise HTTPException(status_code=422, detail="新建用印申请必须使用用印专用入口")
    if body.module == "ipr_case":
        raise HTTPException(status_code=422, detail="新建知识产权案件必须使用知识产权案件专用入口")
    if body.module == "task":
        raise HTTPException(status_code=422, detail="任务必须使用任务专用入口创建")
    if body.module == "finance_package":
        raise HTTPException(status_code=422, detail="付款包必须使用打包付款专用入口创建")
    if body.module == "finance_settlement":
        raise HTTPException(status_code=422, detail="结算申请必须使用结算管理专用入口创建")
    if body.module == "case_reminder":
        raise HTTPException(status_code=422, detail="案件提醒必须使用案件提醒专用入口创建")
    if body.module == "finance_archive_settlement":
        raise HTTPException(status_code=422, detail="归档费支付必须使用归档费结算专用入口创建")
    if body.module == "finance":
        raise HTTPException(status_code=422, detail="费用必须使用费用管理专用入口创建")
    if body.module == JAR_FEE_MODULE:
        raise HTTPException(status_code=422, detail="JAR fees must use the dedicated finance endpoint")
    if body.module in {"hr", "warehouse"} and identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="当前角色不能新建人事或仓库记录")
    if await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == body.serial_no)):
        raise HTTPException(status_code=409, detail="业务编号已存在")
    payload = body.model_dump()
    if body.module == "clue":
        payload["status"] = "草稿"
    if body.module == "document":
        direction = str((body.data or {}).get("direction") or "").strip()
        if direction not in {"收文", "发文"}: raise HTTPException(status_code=422, detail="收发类型必须为收文或发文")
        case_no = str((body.data or {}).get("case_no") or "").strip()
        if case_no:
            case_record = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "case", BusinessRecord.serial_no == case_no))
            if not case_record: raise HTTPException(status_code=422, detail="关联案件不存在")
            await _ensure_record_visible(case_record.id, identity, db)
        payload["status"] = "待登记"
    if body.module == "hr":
        joined_at = str((body.data or {}).get("joined_at") or "").strip()
        if not body.title.strip() or not (body.data or {}).get("position") or not joined_at: raise HTTPException(status_code=422, detail="员工姓名、岗位和入职日期不能为空")
        payload["status"] = "在职" if body.status == "在职" else "试用"
    if body.module == "warehouse":
        data = dict(body.data or {}); quantity = int(data.get("quantity") or 0)
        if data.get("evidence_status"): raise HTTPException(status_code=422, detail="证物必须使用证物登记入口创建")
        if quantity < 1 or not str(data.get("category") or "").strip() or not str(data.get("location") or "").strip(): raise HTTPException(status_code=422, detail="物品类别、数量和存放位置不能为空")
        data.update({"quantity": quantity, "borrower": "", "due_date": "", "borrow_purpose": ""}); payload["data"] = data; payload["status"] = "在库"
    if identity.get("role") != "admin":
        user = await db.scalar(select(User).where(User.username == identity["username"]))
        if not user: raise HTTPException(status_code=401, detail="当前用户不存在")
        payload["department"] = user.department
        if identity.get("role") == "user": payload["owner"] = user.username
    if body.module == "customer":
        managers = await _resolve_active_customer_managers(list((payload.get("data") or {}).get("customer_managers") or [payload.get("owner")]), db)
        owner = (await _resolve_active_customer_managers([payload.get("owner")], db))[0]
        managers = [owner, *[manager for manager in managers if manager != owner]]
        payload["owner"] = owner
        payload["data"] = {**(payload.get("data") or {}), "customer_managers": managers}
    record = BusinessRecord(**payload)
    db.add(record)
    await db.flush()
    db.add(WorkflowEvent(record_id=record.id, action="创建", to_status=record.status, operator=identity["username"], comment="创建业务记录"))
    await _sync_legacy_projection(record, identity, db)
    await db.commit()
    await db.refresh(record)
    return _record_dict(record)


@router.get(f"{settings.api_prefix}/records/{{record_id}}")
async def get_record(record_id: int, scope: str = Query("", pattern="^(|audit)$"), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import (
        _can_search_all_cases_from_global_search, _ensure_case_read_visible,
        _record_dict_for_identity, _require_record_module_menu,
    )
    if scope == "audit":
        from app.core.clue_audit_scope import ensure_clue_audit_record
        record = await ensure_clue_audit_record(record_id, identity, db)
    else:
        record = await _ensure_case_read_visible(record_id, identity, db)
    if record.module != "case" or not await _can_search_all_cases_from_global_search(identity, db):
        await _require_record_module_menu(record.module, identity, db, action="查看")
    return await _record_dict_for_identity(record, identity, db)


@router.get(f"{settings.api_prefix}/records/{{record_id}}/history")
async def record_history(record_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.formatters import (
        _person_reference_display, _user_display_map,
    )
    from app.core.permissions import (
        _can_search_all_cases_from_global_search, _ensure_case_read_visible, _require_record_module_menu,
    )
    record = await _ensure_case_read_visible(record_id, identity, db)
    if record.module != "case" or not await _can_search_all_cases_from_global_search(identity, db):
        await _require_record_module_menu(record.module, identity, db, action="查看")
    events = list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == record_id).order_by(WorkflowEvent.created_at.desc(), WorkflowEvent.id.desc()))).all())
    users_by_username = await _user_display_map({event.operator for event in events}, db)
    return {
        "transitions": WORKFLOW_TRANSITIONS.get(record.module, {}).get(record.status, []),
        "items": [{
            "id": event.id, "action": event.action, "from_status": event.from_status,
            "to_status": event.to_status, "operator": event.operator,
            "operator_display_name": _person_reference_display(event.operator, users_by_username)[0],
            "comment": event.comment, "created_at": event.created_at,
        } for event in events],
    }


@router.patch(f"{settings.api_prefix}/records/{{record_id}}")
async def update_record(record_id: int, body: RecordUpdate, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.customer_identity import validate_customer_identity
    from app.core.crm import (
        _mark_customer_modified, _resolve_active_customer_managers,
    )
    from app.core.legacy_sync import (
        _legacy_failure_response, _sync_legacy_projection,
    )
    from app.core.permissions import (
        _ensure_record_visible, _ensure_unique_customer_name, _record_dict_for_identity, _require_record_module_menu, _require_record_owner_or_manager,
    )
    record = await _ensure_record_visible(record_id, identity, db)
    if record.module == "investigation":
        from app.core.investigation_access import _actual_identity
        identity = await _actual_identity(identity, db)
        record = await _ensure_record_visible(record_id, identity, db)
    if record.module == "conflict_review":
        raise HTTPException(status_code=409, detail="利益冲突审查必须使用专用入口办理")
    await _require_record_module_menu(record.module, identity, db, action="编辑")
    await _require_record_owner_or_manager(record, identity, db)
    changes = body.model_dump(exclude_unset=True)
    if record.module not in GENERIC_RECORD_EDITABLE_MODULES:
        return _legacy_failure_response("该业务必须使用专用入口办理")
    if record.module in {"hr", "warehouse"} and identity.get("role") not in {"admin", "manager"}:
        raise HTTPException(status_code=403, detail="当前角色不能修改人事或仓库资料")
    if "status" in changes and record.module in {"clue", "evidence", "invoice", "refund", "document", "hr", "warehouse"}:
        return _legacy_failure_response("该业务必须使用专用审批或办理入口变更状态")
    if record.module == "customer" and "status" in changes and changes["status"] != record.status:
        return _legacy_failure_response("客户生命周期状态必须通过领取、释放、回收或恢复专用入口变更")
    if record.module == "warehouse" and "data" in changes:
        if record.status != "在库": return _legacy_failure_response("借出或归还中的物品不能直接修改资料")
        protected = {"borrower", "due_date", "borrow_purpose", "borrowed_at", "borrowed_by", "return_requested_at", "returned_at", "return_condition", "scrapped_at", "scrap_reason", "evidence_status", "checked_in_at", "checked_in_by", "checked_out_at", "checked_out_by", "recipient", "checkout_purpose", "rechecked_in_at", "rechecked_in_by", "destroyed_at", "destroyed_by", "destroy_reason"}
        incoming_data = dict(changes.get("data") or {})
        for key in protected:
            if incoming_data.get(key) != (record.data or {}).get(key): return _legacy_failure_response("借还及报废信息必须通过专用办理入口修改")
    if identity.get("role") != "admin":
        user = await db.scalar(select(User).where(User.username == identity["username"]))
        if not user: raise HTTPException(status_code=401, detail="当前用户不存在")
        if "department" in changes: changes["department"] = user.department
        if identity.get("role") == "user" and "owner" in changes: changes["owner"] = user.username
    if record.module == "customer":
        requested_title = str(changes.get("title", record.title) or "").strip()
        await _ensure_unique_customer_name(requested_title, db, exclude_id=record.id)
        changes["title"] = requested_title
        if "title" in body.model_fields_set:
            changes["customer"] = requested_title
        if "owner" in changes:
            requested_owner = (await _resolve_active_customer_managers([changes["owner"]], db))[0]
            if requested_owner != record.owner:
                return _legacy_failure_response("客户负责人必须通过客户管理人专用入口修改")
            changes["owner"] = record.owner
        if "data" in changes:
            customer_data = dict(changes.get("data") or {})
            existing_customer_data = dict(record.data or {})
            for protected_contact_field in CUSTOMER_SYSTEM_DATA_FIELDS:
                if (
                    protected_contact_field in customer_data
                    and customer_data.get(protected_contact_field) != existing_customer_data.get(protected_contact_field)
                ):
                    return _legacy_failure_response("客户系统维护字段必须通过对应专用入口修改")
                if protected_contact_field in existing_customer_data:
                    customer_data[protected_contact_field] = existing_customer_data[protected_contact_field]
                else:
                    customer_data.pop(protected_contact_field, None)
            existing_managers = [
                str(manager).strip()
                for manager in existing_customer_data.get("customer_managers", [])
                if str(manager).strip()
            ] or [record.owner]
            if "customer_managers" in customer_data:
                incoming_managers = [
                    str(manager).strip()
                    for manager in (customer_data.get("customer_managers") or [])
                    if str(manager).strip()
                ]
                if incoming_managers != existing_managers:
                    return _legacy_failure_response("客户管理人必须通过客户管理人专用入口修改")
            customer_data["customer_managers"] = existing_managers
            identity_fields = {"organization_type", "identity_no", "credit_code"}
            if any(customer_data.get(key) != existing_customer_data.get(key) for key in identity_fields):
                await validate_customer_identity(customer_data, db, exclude_id=record.id)
            changes["data"] = customer_data
    old_status = record.status
    for field, value in changes.items():
        setattr(record, field, value)
    if record.module == "customer":
        _mark_customer_modified(record, identity)
    if "status" in changes and changes["status"] != old_status:
        db.add(WorkflowEvent(record_id=record.id, action="编辑变更", from_status=old_status, to_status=record.status, operator=identity["username"], comment="通过编辑表单变更状态"))
    else:
        db.add(WorkflowEvent(record_id=record.id, action="编辑", from_status=record.status, to_status=record.status, operator=identity["username"], comment="修改业务资料"))
    await _sync_legacy_projection(record, identity, db)
    await db.commit()
    await db.refresh(record)
    return await _record_dict_for_identity(record, identity, db)


@router.post(f"{settings.api_prefix}/records/{{record_id}}/transition")
async def transition_record(record_id: int, body: TransitionInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.legacy_sync import (
        _legacy_failure_response, _sync_legacy_projection,
    )
    from app.core.permissions import (
        _ensure_record_visible, _require_record_module_menu, _require_record_owner_or_manager,
    )
    from app.core.system import (
        _record_dict,
    )
    record = await _ensure_record_visible(record_id, identity, db)
    if record.module == "conflict_review":
        raise HTTPException(status_code=409, detail="利益冲突审查必须使用专用入口办理")
    await _require_record_module_menu(record.module, identity, db, action="流转")
    if record.module not in GENERIC_RECORD_TRANSITION_MODULES:
        return _legacy_failure_response("该业务必须使用专用审批或办理入口变更状态")
    approval_access = identity.get("role") == "auditor" and record.module in {"contract", "finance", "invoice", "refund", "seal", "clue", "notary"} and record.status in {"待审批", "审批中", "待审核"}
    if not approval_access:
        await _require_record_owner_or_manager(record, identity, db)
    allowed = WORKFLOW_TRANSITIONS.get(record.module, {}).get(record.status, [])
    if body.to_status not in allowed:
        return _legacy_failure_response(f"不能从“{record.status}”流转到“{body.to_status}”")
    previous = record.status
    record.status = body.to_status
    action = "审批通过"
    if body.to_status in {"已拒绝", "已驳回", "已退回", "已撤回"}:
        action = "驳回/撤回"
    elif body.to_status in {"已完成", "已归档", "已用印", "已付款", "已对账", "已发布"}:
        action = "办结"
    db.add(WorkflowEvent(record_id=record.id, action=action, from_status=previous, to_status=body.to_status, operator=identity["username"], comment=body.comment))
    await _sync_legacy_projection(record, identity, db)
    await db.commit()
    await db.refresh(record)
    return _record_dict(record)


@router.delete(f"{settings.api_prefix}/records/{{record_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(record_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.cases import (
        _delete_case_events_for_case_cleanup,
    )
    from app.core.tasks import (
        _delete_task_notifications,
    )
    if identity["role"] != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可删除")
    record = await db.get(BusinessRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    if record.module == "conflict_review":
        raise HTTPException(status_code=409, detail="利益冲突审查必须保留审查历史，不能通过通用入口删除")
    if record.module not in GENERIC_RECORD_DELETABLE_MODULES:
        raise HTTPException(status_code=409, detail="该业务记录不能通过通用入口物理删除，请使用专用撤销、作废或冲正流程")
    if record.module == "hr":
        linked_username = str((record.data or {}).get("username") or "").strip().lower()
        if linked_username and await db.scalar(select(User.id).where(User.username == linked_username)):
            # A generic record delete must never leave an active login account
            # behind.  Employee exits are handled by the HR edit/disable flow.
            raise HTTPException(status_code=409, detail="该员工档案关联可登录账号，不能直接删除；请在员工资料中停用账号以保持同步")
    if record.module == "seal" and (record.data or {}).get("actual_copies"):
        asset = await db.get(SealAsset, int((record.data or {}).get("seal_asset_id") or 0))
        if asset:
            asset.usage_count = max(0, asset.usage_count - int((record.data or {}).get("actual_copies") or 0))
    attachments = (await db.scalars(select(FileAttachment).where(FileAttachment.record_id == record_id))).all()
    attachment_paths = [Path(item.path) for item in attachments]
    for attachment in attachments:
        await db.delete(attachment)
    await db.execute(delete(FinanceTransaction).where(FinanceTransaction.finance_record_id == record_id))
    await db.execute(delete(ContractApprovalStep).where(ContractApprovalStep.contract_record_id == record_id))
    await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == record_id))
    if record.module == "case":
        await _delete_case_events_for_case_cleanup(record_id, db)
    if record.module == "task":
        await _delete_task_notifications(record_id, db)
    await db.delete(record)
    await db.commit()
    for path in attachment_paths:
        if path.is_file() and UPLOAD_ROOT.resolve() in path.resolve().parents:
            path.unlink()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(f"{settings.api_prefix}/cases/archive/search")
async def search_case_archive(body: ArchiveSearchInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    return await search_archive_cases(body, identity, db)


@router.post(f"{settings.api_prefix}/cases/archive/batch-review")
async def batch_review_case_archive(body: ArchiveBatchReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import _record_scope_conditions, _require_case_action
    from app.core.system import _record_dict
    ids = [item.case_id for item in body.items]
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=422, detail="批量审核不能包含重复案件")
    await _require_case_action(identity, db, "case.archive.review")
    try:
        records = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.id.in_(ids), BusinessRecord.module == "case", *(await _record_scope_conditions(identity, db)),
        ).order_by(BusinessRecord.id).with_for_update())).all())
        if len(records) != len(ids):
            raise HTTPException(status_code=404, detail="选中的案件不存在或无权访问，整批未审核")
        by_id = {record.id: record for record in records}
        for item in body.items:
            try:
                await _apply_case_archive_review(item.case_id, item, identity, db)
            except HTTPException as exc:
                raise HTTPException(status_code=exc.status_code, detail=f"案件 {by_id[item.case_id].serial_no}：{exc.detail}；整批未审核") from exc
        await db.commit()
        for record in records:
            await db.refresh(record)
        return {"processed": len(records), "items": [_record_dict(by_id[item_id]) for item_id in ids]}
    except Exception:
        await db.rollback()
        raise


@router.post(f"{settings.api_prefix}/cases/archive/export")
async def export_case_archive(body: ArchiveExportInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.system import _csv_response, _excel_response
    records = await search_archive_cases(body, identity, db, export=True)
    if not records:
        raise HTTPException(status_code=422, detail="当前筛选没有可导出的归档案件")
    # Count each page of IDs separately to stay below database bind limits.
    counts = {}
    ids = [record.id for record in records]
    for start in range(0, len(ids), 400):
        counts.update(dict((await db.execute(select(FileAttachment.record_id, func.count(FileAttachment.id)).where(
            FileAttachment.record_id.in_(ids[start:start + 400]),
        ).group_by(FileAttachment.record_id))).all()))
    headers = ["案号", "案件名称", "客户", "案件类型", "归档状态", "合同编号", "负责人", "附件数量", "归档号", "纸质卷宗位置", "纸质卷宗数量"]
    rows = [[record.serial_no, record.title, record.customer, (record.data or {}).get("case_type", ""), record.status,
             (record.data or {}).get("contract_no", ""), record.owner, counts.get(record.id, 0),
             (record.data or {}).get("archive_no", ""), (record.data or {}).get("paper_archive_location", ""),
             (record.data or {}).get("paper_volume_count", "")] for record in records]
    if body.format == "csv":
        return _csv_response(f"案件归档清单-{date.today()}.csv", headers, rows)
    return _excel_response(f"案件归档清单-{date.today()}.xls", headers, rows)


@router.post(f"{settings.api_prefix}/cases/batch-delete")
async def delete_cases_batch(body: CaseBatchDeleteInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    return await _delete_company_cases(body.case_ids, identity, db)


@router.get(f"{settings.api_prefix}/cases/export/receipts")
async def export_selected_case_receipts(ids: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.case_receipt_export import RECEIPT_HEADERS, case_receipt_export_rows
    from app.core.system import _excel_response

    rows = await case_receipt_export_rows(ids, identity, db)
    return _excel_response(f"案件到账清单-{date.today()}.xls", RECEIPT_HEADERS, rows)


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/documents")
async def list_case_documents(case_id: int, page: int = Query(1, ge=1), page_size: int = Query(200, ge=1, le=200), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.case_documents import case_document_page
    return await case_document_page(case_id, identity, db, page, page_size)


@router.get(f"{settings.api_prefix}/cases/{{case_id}}/clue-candidates")
async def list_case_clue_candidates(case_id: int, keyword: str = Query("", max_length=100), identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.permissions import _ensure_record_module, _require_case_action
    from app.core.case_relations import case_clue_ids
    from app.core.system import _record_dict
    case = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_action(identity, db, "case.detail.update")
    if not case.customer.strip():
        raise HTTPException(status_code=409, detail="案件未关联客户，不能选择调查线索")
    existing = case_clue_ids(case)
    cases = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case", BusinessRecord.id != case.id, BusinessRecord.status != "已合并",
    ))).all()
    used = set().union(*(case_clue_ids(item) for item in cases))
    conditions = [BusinessRecord.module == "clue", BusinessRecord.customer == case.customer,
                  or_(BusinessRecord.id.in_(existing),
                      BusinessRecord.status == "已取证")]
    if keyword.strip():
        conditions.append(or_(BusinessRecord.title.contains(keyword.strip(), autoescape=True),
                              BusinessRecord.serial_no.contains(keyword.strip(), autoescape=True)))
    rows = (await db.scalars(select(BusinessRecord).where(*conditions).order_by(BusinessRecord.id.desc()))).all()
    candidates = [item for item in rows if item.id in existing or (item.id not in used and not any(
        (item.data or {}).get(key) for key in ("case_id", "case_record_id", "case_no", "converted_case_id", "converted_case_no")))]
    return {"items": [_record_dict(item) for item in candidates], "total": len(candidates)}


@router.get(f"{settings.api_prefix}/dashboard/personal-queues/{{queue_key}}")
async def list_dashboard_personal_queue(queue_key: str, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.dashboard_personal_queues import personal_queues
    queues = await personal_queues(identity, db)
    if queue_key not in queues:
        raise HTTPException(404, "提醒队列不存在")
    return {"items": queues[queue_key], "total": len(queues[queue_key])}
