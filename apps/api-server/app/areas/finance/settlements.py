"""按业务职责组织的 API 路由，保留原有端点行为与注册顺序。"""

from app.core.dependencies import (
    AsyncSession, BusinessRecord, Depends, HTTPException, IncomingPayment, Query, Response,
    WorkflowEvent, current_identity, date, datetime, delete, get_db, quote, select, settings, status,
    xml_escape,
)
from app.models_shared import (
    ArchiveSettlementPaymentReviewInput, ArchiveSettlementRejectedActionInput,
    ArchiveSettlementRollbackInput, FinanceSettlementApplyInput, FinanceSettlementPaymentInput,
    FinanceSettlementReapplyInput, FinanceSettlementReviewInput,
)
from fastapi import APIRouter
from app.core.incoming_settlement import (_active_settlements_by_receipt, _settlement_financial_snapshot)

router = APIRouter()


@router.get(f"{settings.api_prefix}/finance/general-settlements/pending")
async def list_general_settlement_candidates(
    customer: str = "", case_no: str = "",
    received_from: date | None = None, received_to: date | None = None,
    payer: str = "", payment_method: str = "", case_customer: str = "",
    hearing_lawyer: str = "", assistant: str = "", customer_manager: str = "", source_person: str = "",
    page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _general_settlement_rows, _round_fee_amount,
    )
    if received_from and received_to and received_from > received_to:
        raise HTTPException(status_code=422, detail="回款开始日期不能晚于结束日期")
    rows = await _general_settlement_rows(
        identity, db, customer=customer, case_no=case_no,
        received_from=received_from, received_to=received_to, payer=payer,
        payment_method=payment_method, case_customer=case_customer,
        hearing_lawyer=hearing_lawyer, assistant=assistant,
        customer_manager=customer_manager, source_person=source_person,
    )
    amount_keys = ["receipt_amount", "allocated_amount", "remaining_amount", "assigned_official_fee", "assigned_agency_fee", "assigned_other_fee", "agency_settlement_amount", "archive_fee", "actual_settlement_amount"]
    totals = {key: _round_fee_amount(sum(float((row.get("data") or {}).get(key) or 0) for row in rows)) for key in amount_keys}
    start = (page - 1) * page_size
    return {"items": rows[start:start + page_size], "total": len(rows), "totals": totals, "page": page, "page_size": page_size}


@router.post(f"{settings.api_prefix}/finance/general-settlements/apply", status_code=status.HTTP_201_CREATED)
async def apply_general_settlements(body: FinanceSettlementApplyInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _general_settlement_rows,
    )
    receipt_ids = list(dict.fromkeys(body.receipt_ids))
    locked_receipts = list((await db.scalars(select(IncomingPayment).where(
        IncomingPayment.id.in_(receipt_ids),
    ).with_for_update())).all())
    if len(locked_receipts) != len(receipt_ids):
        raise HTTPException(status_code=404, detail="部分回款不存在")
    active_settlements = await _active_settlements_by_receipt(db, set(receipt_ids))
    if active_settlements:
        blocked = [active_settlements[receipt_id].serial_no for receipt_id in receipt_ids if receipt_id in active_settlements]
        raise HTTPException(status_code=409, detail="部分回款已有有效结算申请：" + "、".join(blocked))
    rows = await _general_settlement_rows(identity, db, receipt_ids=set(receipt_ids))
    rows_by_id = {int(row["id"]): row for row in rows}
    missing = [str(receipt_id) for receipt_id in receipt_ids if receipt_id not in rows_by_id]
    if missing:
        raise HTTPException(status_code=409, detail="部分回款尚未完整分配或无权办理：" + "、".join(missing))
    created: list[BusinessRecord] = []
    now_key = datetime.now().strftime("%Y%m%d%H%M%S%f")
    for index, receipt_id in enumerate(receipt_ids):
        row = rows_by_id[receipt_id]
        row_data = dict(row.get("data") or {})
        application = BusinessRecord(
            module="finance_settlement",
            serial_no=f"JS{now_key}{index:02d}",
            title=f"{row.get('customer') or row_data.get('payer_name')}结算申请",
            customer=str(row.get("customer") or ""),
            status="待审批",
            owner=identity["username"],
            department=str(identity.get("department") or "上海分所"),
            description=body.comment.strip(),
            data={**row_data, "applied_by": identity["username"], "applied_at": datetime.now().isoformat(timespec="seconds")},
        )
        db.add(application)
        await db.flush()
        db.add(WorkflowEvent(record_id=application.id, action="申请结算", to_status="待审批", operator=identity["username"], comment=body.comment.strip()))
        created.append(application)
    await db.commit()
    return {"created": len(created), "application_ids": [item.id for item in created], "application_nos": [item.serial_no for item in created]}


@router.get(f"{settings.api_prefix}/finance/archive-settlements/pending")
async def list_pending_archive_settlements(
    case_type: str = "", case_stage: str = "", payer: str = "",
    received_from: date | None = None, received_to: date | None = None,
    hearing_lawyer: str = "", assistant: str = "", submitted_by: str = "",
    settled_from: date | None = None, settled_to: date | None = None,
    case_no: str = "", customer: str = "", reviewer: str = "",
    page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _pending_archive_settlement_rows, _round_fee_amount,
    )
    for start_date, end_date, label in (
        (received_from, received_to, "回款"),
        (settled_from, settled_to, "结算支付"),
    ):
        if start_date and end_date and start_date > end_date:
            raise HTTPException(status_code=422, detail=f"{label}开始日期不能晚于结束日期")
    rows = await _pending_archive_settlement_rows(
        identity, db, case_type=case_type, case_stage=case_stage, payer=payer,
        received_from=received_from, received_to=received_to,
        hearing_lawyer=hearing_lawyer, assistant=assistant, submitted_by=submitted_by,
        settled_from=settled_from, settled_to=settled_to, case_no=case_no,
        customer=customer, reviewer=reviewer,
    )
    totals = {
        "receipt_amount": _round_fee_amount(sum(float((row.get("data") or {}).get("receipt_amount") or 0) for row in rows)),
        "archive_fee_amount": _round_fee_amount(sum(float((row.get("data") or {}).get("archive_fee_amount") or 0) for row in rows)),
    }
    start = (page - 1) * page_size
    return {"items": rows[start:start + page_size], "total": len(rows), "totals": totals, "page": page, "page_size": page_size}


@router.get(f"{settings.api_prefix}/finance/archive-settlements/export")
async def export_pending_archive_settlements(
    ids: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _pending_archive_settlement_rows,
    )
    selected_ids = {item.strip() for item in ids.split(",") if item.strip()}
    if not selected_ids:
        raise HTTPException(status_code=422, detail="请选择需要导出的归档费.")
    rows = await _pending_archive_settlement_rows(identity, db, selected_ids=selected_ids)
    if len(rows) != len(selected_ids):
        raise HTTPException(status_code=409, detail="部分归档费不存在、已进入下一环节或无权导出")
    headers = ["案号", "客户", "案件阶段", "律师助理", "开庭律师", "客户管理人", "费用类型", "回款方式", "回款时间", "回款金额", "归档费金额", "结算时间"]
    numeric = {9, 10}
    values = [[
        row["data"].get("case_no"), row.get("customer"), row["data"].get("case_stage"),
        row["data"].get("assistant"), row["data"].get("hearing_lawyer"), row["data"].get("customer_manager"),
        row["data"].get("fee_type"), row["data"].get("payment_method"), row["data"].get("received_date"),
        row["data"].get("receipt_amount"), row["data"].get("archive_fee_amount"), row["data"].get("settlement_paid_at"),
    ] for row in rows]
    def cell(value: object, *, number: bool = False) -> str:
        value_text = f"{float(value or 0):.2f}" if number else str(value or "")
        return f'<Cell><Data ss:Type="{"Number" if number else "String"}">{xml_escape(value_text)}</Data></Cell>'
    sheet_rows = ["<Row>" + "".join(cell(value) for value in headers) + "</Row>"]
    sheet_rows.extend("<Row>" + "".join(cell(value, number=index in numeric and value is not None) for index, value in enumerate(row)) + "</Row>" for row in values)
    workbook = '<?xml version="1.0" encoding="UTF-8"?><?mso-application progid="Excel.Sheet"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="待归档"><Table>' + "".join(sheet_rows) + "</Table></Worksheet></Workbook>"
    filename = f"待归档-{date.today()}.xls"
    disposition = f"attachment; filename=archive-settlement-pending.xls; filename*=UTF-8''{quote(filename)}"
    return Response(content=workbook.encode("utf-8"), media_type="application/vnd.ms-excel", headers={"Content-Disposition": disposition})


@router.get(f"{settings.api_prefix}/finance/archive-settlements/payment")
async def list_archive_settlement_payments(
    case_type: str = "", case_stage: str = "", payer: str = "",
    received_from: date | None = None, received_to: date | None = None,
    hearing_lawyer: str = "", assistant: str = "", submitted_by: str = "",
    settled_from: date | None = None, settled_to: date | None = None,
    case_no: str = "", customer: str = "", reviewer: str = "",
    archive_from: date | None = None, archive_to: date | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _pending_archive_settlement_rows, _round_fee_amount,
    )
    for start_date, end_date, label in (
        (received_from, received_to, "回款"),
        (settled_from, settled_to, "结算支付"),
        (archive_from, archive_to, "归档"),
    ):
        if start_date and end_date and start_date > end_date:
            raise HTTPException(status_code=422, detail=f"{label}开始日期不能晚于结束日期")
    rows = await _pending_archive_settlement_rows(
        identity, db, case_type=case_type, case_stage=case_stage, payer=payer,
        received_from=received_from, received_to=received_to,
        hearing_lawyer=hearing_lawyer, assistant=assistant, submitted_by=submitted_by,
        settled_from=settled_from, settled_to=settled_to, case_no=case_no,
        customer=customer, reviewer=reviewer, archive_from=archive_from,
        archive_to=archive_to, require_archived=True,
    )
    totals = {
        "receipt_amount": _round_fee_amount(sum(float((row.get("data") or {}).get("receipt_amount") or 0) for row in rows)),
        "archive_fee_amount": _round_fee_amount(sum(float((row.get("data") or {}).get("archive_fee_amount") or 0) for row in rows)),
    }
    start = (page - 1) * page_size
    return {"items": rows[start:start + page_size], "total": len(rows), "totals": totals, "page": page, "page_size": page_size}


@router.post(f"{settings.api_prefix}/finance/archive-settlements/payment/review")
async def review_archive_settlement_payments(
    body: ArchiveSettlementPaymentReviewInput,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _pending_archive_settlement_rows,
    )
    from app.core.permissions import (
        _settlement_application_scope,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有归档费支付审核权限")
    settlement_ids = list(dict.fromkeys(item.strip() for item in body.settlement_ids if item.strip()))
    if len(settlement_ids) != len(body.settlement_ids):
        raise HTTPException(status_code=422, detail="归档费记录不能为空或重复")
    if not body.approved and not body.comment.strip():
        raise HTTPException(status_code=422, detail="拒绝支付时请输入备注.")
    rows = await _pending_archive_settlement_rows(
        identity, db, require_archived=True, selected_ids=set(settlement_ids),
    )
    if len(rows) != len(settlement_ids):
        raise HTTPException(status_code=409, detail="部分归档费不存在、已处理或无权审核")
    row_map = {row["id"]: row for row in rows}
    decided_at = datetime.now().isoformat(timespec="seconds")
    reusable = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance_archive_settlement",
        BusinessRecord.status == "已回滚",
        *_settlement_application_scope(identity),
    ))).all())
    reusable_by_source = {str((item.data or {}).get("source_row_id") or ""): item for item in reusable}
    created: list[BusinessRecord] = []
    for source_id in settlement_ids:
        row = row_map[source_id]
        data = row.get("data") or {}
        target_status = "已支付" if body.approved else "已拒绝"
        decision = reusable_by_source.get(source_id)
        if decision:
            previous_status = decision.status
            decision.status = target_status
            decision.title = row.get("title") or "归档费支付"
            decision.customer = row.get("customer") or ""
            decision.owner = row.get("owner") or identity["username"]
            decision.department = row.get("department") or str(identity.get("department") or "")
            decision.data = {
                **data,
                "source_row_id": source_id,
                "source_application_id": data.get("application_id"),
                "archive_payment_submitted_by": data.get("submitted_by") or row.get("owner") or identity["username"],
                "archive_payment_submitted_at": data.get("settlement_paid_at") or decided_at,
                "archive_payment_reviewer": identity["username"],
                "archive_payment_reviewed_at": decided_at,
                "archive_payment_comment": body.comment.strip(),
            }
        else:
            previous_status = "待支付"
            decision = BusinessRecord(
                module="finance_archive_settlement",
                serial_no=f"ARCP-{source_id.replace(':', '-')}",
                title=row.get("title") or "归档费支付",
                customer=row.get("customer") or "",
                status=target_status,
                owner=row.get("owner") or identity["username"],
                department=row.get("department") or str(identity.get("department") or ""),
                data={
                    **data,
                    "source_row_id": source_id,
                    "source_application_id": data.get("application_id"),
                    "archive_payment_submitted_by": data.get("submitted_by") or row.get("owner") or identity["username"],
                    "archive_payment_submitted_at": data.get("settlement_paid_at") or decided_at,
                    "archive_payment_reviewer": identity["username"],
                    "archive_payment_reviewed_at": decided_at,
                    "archive_payment_comment": body.comment.strip(),
                },
            )
        db.add(decision)
        await db.flush()
        db.add(WorkflowEvent(
            record_id=decision.id,
            action="归档费同意支付" if body.approved else "归档费拒绝支付",
            from_status=previous_status, to_status=target_status,
            operator=identity["username"], comment=body.comment.strip(),
        ))
        created.append(decision)
    await db.commit()
    return {"reviewed": len(created), "status": "已支付" if body.approved else "已拒绝", "record_ids": [item.id for item in created]}


@router.get(f"{settings.api_prefix}/finance/archive-settlements/payment/export")
async def export_archive_settlement_payments(
    ids: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _pending_archive_settlement_rows,
    )
    selected_ids = {item.strip() for item in ids.split(",") if item.strip()}
    if not selected_ids:
        raise HTTPException(status_code=422, detail="请选择需要导出的归档费.")
    rows = await _pending_archive_settlement_rows(identity, db, require_archived=True, selected_ids=selected_ids)
    if len(rows) != len(selected_ids):
        raise HTTPException(status_code=409, detail="部分归档费不存在、已处理或无权导出")
    headers = ["案号", "客户", "案件阶段", "律师助理", "开庭律师", "客户管理人", "费用类型", "回款方式", "回款时间", "回款金额", "归档费金额", "支付时间", "归档号", "归档日期"]
    numeric = {9, 10}
    values = [[
        row["data"].get("case_no"), row.get("customer"), row["data"].get("case_stage"),
        row["data"].get("assistant"), row["data"].get("hearing_lawyer"), row["data"].get("customer_manager"),
        row["data"].get("fee_type"), row["data"].get("payment_method"), row["data"].get("received_date"),
        row["data"].get("receipt_amount"), row["data"].get("archive_fee_amount"), row["data"].get("settlement_paid_at"),
        row["data"].get("archive_no"), row["data"].get("archive_date"),
    ] for row in rows]
    def cell(value: object, *, number: bool = False) -> str:
        value_text = f"{float(value or 0):.2f}" if number else str(value or "")
        return f'<Cell><Data ss:Type="{"Number" if number else "String"}">{xml_escape(value_text)}</Data></Cell>'
    sheet_rows = ["<Row>" + "".join(cell(value) for value in headers) + "</Row>"]
    sheet_rows.extend("<Row>" + "".join(cell(value, number=index in numeric) for index, value in enumerate(row)) + "</Row>" for row in values)
    workbook = '<?xml version="1.0" encoding="UTF-8"?><?mso-application progid="Excel.Sheet"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="待支付"><Table>' + "".join(sheet_rows) + "</Table></Worksheet></Workbook>"
    filename = f"待支付归档费-{date.today()}.xls"
    disposition = f"attachment; filename=archive-settlement-payment.xls; filename*=UTF-8''{quote(filename)}"
    return Response(content=workbook.encode("utf-8"), media_type="application/vnd.ms-excel", headers={"Content-Disposition": disposition})


@router.get(f"{settings.api_prefix}/finance/archive-settlements/paid")
async def list_paid_archive_settlements(
    case_type: str = "", case_stage: str = "", payer: str = "",
    received_from: date | None = None, received_to: date | None = None,
    hearing_lawyer: str = "", assistant: str = "", submitted_by: str = "",
    settled_from: date | None = None, settled_to: date | None = None,
    case_no: str = "", customer: str = "", reviewer: str = "",
    archive_from: date | None = None, archive_to: date | None = None,
    payment_from: date | None = None, payment_to: date | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _archive_settlement_decision_rows, _round_fee_amount,
    )
    for start_date, end_date, label in (
        (received_from, received_to, "回款"), (settled_from, settled_to, "结算支付"),
        (archive_from, archive_to, "归档"), (payment_from, payment_to, "归档费支付"),
    ):
        if start_date and end_date and start_date > end_date:
            raise HTTPException(status_code=422, detail=f"{label}开始日期不能晚于结束日期")
    rows = await _archive_settlement_decision_rows(
        identity, db, statuses={"已支付"}, case_type=case_type, case_stage=case_stage,
        payer=payer, received_from=received_from, received_to=received_to,
        hearing_lawyer=hearing_lawyer, assistant=assistant, submitted_by=submitted_by,
        settled_from=settled_from, settled_to=settled_to, case_no=case_no,
        customer=customer, reviewer=reviewer, archive_from=archive_from,
        archive_to=archive_to, payment_from=payment_from, payment_to=payment_to,
    )
    totals = {
        "receipt_amount": _round_fee_amount(sum(float((row.get("data") or {}).get("receipt_amount") or 0) for row in rows)),
        "archive_fee_amount": _round_fee_amount(sum(float((row.get("data") or {}).get("archive_fee_amount") or 0) for row in rows)),
    }
    start = (page - 1) * page_size
    return {"items": rows[start:start + page_size], "total": len(rows), "totals": totals, "page": page, "page_size": page_size}


@router.post(f"{settings.api_prefix}/finance/archive-settlements/paid/rollback")
async def rollback_paid_archive_settlements(
    body: ArchiveSettlementRollbackInput,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import (
        _settlement_application_scope,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有归档费支付回滚权限")
    if not body.comment.strip():
        raise HTTPException(status_code=422, detail="请输入备注.")
    record_ids = list(dict.fromkeys(body.record_ids))
    if len(record_ids) != len(body.record_ids):
        raise HTTPException(status_code=422, detail="归档费记录不能重复")
    records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(record_ids),
        BusinessRecord.module == "finance_archive_settlement",
        BusinessRecord.status == "已支付",
        *_settlement_application_scope(identity),
    ))).all())
    if len(records) != len(record_ids):
        raise HTTPException(status_code=409, detail="部分归档费不存在、不是已支付状态或无权回滚")
    rolled_back_at = datetime.now().isoformat(timespec="seconds")
    for record in records:
        record.status = "已回滚"
        record.data = {
            **(record.data or {}),
            "archive_payment_rollback_by": identity["username"],
            "archive_payment_rollback_at": rolled_back_at,
            "archive_payment_rollback_comment": body.comment.strip(),
        }
        db.add(WorkflowEvent(
            record_id=record.id, action="回滚归档费支付",
            from_status="已支付", to_status="已回滚",
            operator=identity["username"], comment=body.comment.strip(),
        ))
    await db.commit()
    return {"rolled_back": len(records), "status": "已回滚"}


@router.get(f"{settings.api_prefix}/finance/archive-settlements/paid/export")
async def export_paid_archive_settlements(
    ids: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _archive_settlement_decision_rows,
    )
    try:
        selected_ids = {int(item.strip()) for item in ids.split(",") if item.strip()}
    except ValueError:
        raise HTTPException(status_code=422, detail="归档费记录编号无效")
    if not selected_ids:
        raise HTTPException(status_code=422, detail="请选择需要导出的归档费.")
    rows = await _archive_settlement_decision_rows(identity, db, statuses={"已支付"}, selected_ids=selected_ids)
    if len(rows) != len(selected_ids):
        raise HTTPException(status_code=409, detail="部分归档费不存在、已回滚或无权导出")
    headers = ["案号", "客户", "案件阶段", "律师助理", "开庭律师", "客户管理人", "费用类型", "回款方式", "回款时间", "回款金额", "归档费金额", "结算时间", "归档费支付日期"]
    numeric = {9, 10}
    values = [[
        row["data"].get("case_no"), row.get("customer"), row["data"].get("case_stage"),
        row["data"].get("assistant"), row["data"].get("hearing_lawyer"), row["data"].get("customer_manager"),
        row["data"].get("fee_type"), row["data"].get("payment_method"), row["data"].get("received_date"),
        row["data"].get("receipt_amount"), row["data"].get("archive_fee_amount"), row["data"].get("settlement_paid_at"),
        row["data"].get("archive_payment_reviewed_at"),
    ] for row in rows]
    def cell(value: object, *, number: bool = False) -> str:
        value_text = f"{float(value or 0):.2f}" if number else str(value or "")
        return f'<Cell><Data ss:Type="{"Number" if number else "String"}">{xml_escape(value_text)}</Data></Cell>'
    sheet_rows = ["<Row>" + "".join(cell(value) for value in headers) + "</Row>"]
    sheet_rows.extend("<Row>" + "".join(cell(value, number=index in numeric and value is not None) for index, value in enumerate(row)) + "</Row>" for row in values)
    workbook = '<?xml version="1.0" encoding="UTF-8"?><?mso-application progid="Excel.Sheet"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="已支付"><Table>' + "".join(sheet_rows) + "</Table></Worksheet></Workbook>"
    filename = f"已支付归档费-{date.today()}.xls"
    disposition = f"attachment; filename=archive-settlement-paid.xls; filename*=UTF-8''{quote(filename)}"
    return Response(content=workbook.encode("utf-8"), media_type="application/vnd.ms-excel", headers={"Content-Disposition": disposition})


@router.get(f"{settings.api_prefix}/finance/archive-settlements/rejected")
async def list_rejected_archive_settlements(
    case_type: str = "", case_stage: str = "", payer: str = "",
    received_from: date | None = None, received_to: date | None = None,
    hearing_lawyer: str = "", assistant: str = "", submitted_by: str = "",
    submitted_from: date | None = None, submitted_to: date | None = None,
    case_no: str = "", customer: str = "", reviewer: str = "",
    reviewed_from: date | None = None, reviewed_to: date | None = None,
    page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _archive_settlement_decision_rows, _round_fee_amount,
    )
    for start_date, end_date, label in (
        (received_from, received_to, "回款"),
        (submitted_from, submitted_to, "提交"),
        (reviewed_from, reviewed_to, "审核"),
    ):
        if start_date and end_date and start_date > end_date:
            raise HTTPException(status_code=422, detail=f"{label}开始日期不能晚于结束日期")
    rows = await _archive_settlement_decision_rows(
        identity, db, statuses={"已拒绝"}, case_type=case_type, case_stage=case_stage,
        payer=payer, received_from=received_from, received_to=received_to,
        hearing_lawyer=hearing_lawyer, assistant=assistant, submitted_by=submitted_by,
        submitted_from=submitted_from, submitted_to=submitted_to,
        case_no=case_no, customer=customer, reviewer=reviewer,
        reviewed_from=reviewed_from, reviewed_to=reviewed_to,
    )
    totals = {
        "receipt_amount": _round_fee_amount(sum(float((row.get("data") or {}).get("receipt_amount") or 0) for row in rows)),
        "archive_fee_amount": _round_fee_amount(sum(float((row.get("data") or {}).get("archive_fee_amount") or 0) for row in rows)),
    }
    start = (page - 1) * page_size
    return {"items": rows[start:start + page_size], "total": len(rows), "totals": totals, "page": page, "page_size": page_size}


@router.post(f"{settings.api_prefix}/finance/archive-settlements/rejected/rollback")
async def rollback_rejected_archive_settlements(
    body: ArchiveSettlementRejectedActionInput,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _rejected_archive_settlement_records,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有归档费拒绝回滚权限")
    if not body.comment.strip():
        raise HTTPException(status_code=422, detail="请输入审核备注.")
    records = await _rejected_archive_settlement_records(body.record_ids, identity, db)
    changed_at = datetime.now().isoformat(timespec="seconds")
    for record in records:
        record.status = "已支付"
        record.data = {
            **(record.data or {}),
            "archive_rejection_rollback_by": identity["username"],
            "archive_rejection_rollback_at": changed_at,
            "archive_rejection_rollback_comment": body.comment.strip(),
        }
        db.add(WorkflowEvent(
            record_id=record.id, action="回滚归档费拒绝",
            from_status="已拒绝", to_status="已支付",
            operator=identity["username"], comment=body.comment.strip(),
        ))
    await db.commit()
    return {"rolled_back": len(records), "status": "已支付"}


@router.post(f"{settings.api_prefix}/finance/archive-settlements/rejected/reapply")
async def reapply_rejected_archive_settlements(
    body: ArchiveSettlementRejectedActionInput,
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _rejected_archive_settlement_records,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有归档费重新申请权限")
    records = await _rejected_archive_settlement_records(body.record_ids, identity, db)
    changed_at = datetime.now().isoformat(timespec="seconds")
    for record in records:
        record.status = "已回滚"
        record.data = {
            **(record.data or {}),
            "archive_payment_reapplied_by": identity["username"],
            "archive_payment_reapplied_at": changed_at,
            "archive_payment_reapply_comment": body.comment.strip(),
        }
        db.add(WorkflowEvent(
            record_id=record.id, action="重新申请归档费",
            from_status="已拒绝", to_status="已回滚",
            operator=identity["username"], comment=body.comment.strip(),
        ))
    await db.commit()
    return {"reapplied": len(records), "status": "待支付"}


@router.get(f"{settings.api_prefix}/finance/archive-settlements/rejected/export")
async def export_rejected_archive_settlements(
    ids: str = "", identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _archive_settlement_decision_rows,
    )
    try:
        selected_ids = {int(item.strip()) for item in ids.split(",") if item.strip()}
    except ValueError:
        raise HTTPException(status_code=422, detail="归档费记录编号无效")
    if not selected_ids:
        raise HTTPException(status_code=422, detail="请选择案件.")
    rows = await _archive_settlement_decision_rows(identity, db, statuses={"已拒绝"}, selected_ids=selected_ids)
    if len(rows) != len(selected_ids):
        raise HTTPException(status_code=409, detail="部分归档费不存在、已重新申请或无权导出")
    headers = ["案号", "客户", "案件阶段", "律师助理", "开庭律师", "客户管理人", "费用类型", "回款方式", "回款时间", "回款金额", "归档费金额", "结算时间", "支付状态"]
    numeric = {9, 10}
    values = [[
        row["data"].get("case_no"), row.get("customer"), row["data"].get("case_stage"),
        row["data"].get("assistant"), row["data"].get("hearing_lawyer"), row["data"].get("customer_manager"),
        row["data"].get("fee_type"), row["data"].get("payment_method"), row["data"].get("received_date"),
        row["data"].get("receipt_amount"), row["data"].get("archive_fee_amount"), row["data"].get("settlement_paid_at"),
        row.get("status"),
    ] for row in rows]
    def cell(value: object, *, number: bool = False) -> str:
        value_text = f"{float(value or 0):.2f}" if number else str(value or "")
        return f'<Cell><Data ss:Type="{"Number" if number else "String"}">{xml_escape(value_text)}</Data></Cell>'
    sheet_rows = ["<Row>" + "".join(cell(value) for value in headers) + "</Row>"]
    sheet_rows.extend("<Row>" + "".join(cell(value, number=index in numeric and value is not None) for index, value in enumerate(row)) + "</Row>" for row in values)
    workbook = '<?xml version="1.0" encoding="UTF-8"?><?mso-application progid="Excel.Sheet"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="已拒绝"><Table>' + "".join(sheet_rows) + "</Table></Worksheet></Workbook>"
    filename = f"已拒绝归档费-{date.today()}.xls"
    disposition = f"attachment; filename=archive-settlement-rejected.xls; filename*=UTF-8''{quote(filename)}"
    return Response(content=workbook.encode("utf-8"), media_type="application/vnd.ms-excel", headers={"Content-Disposition": disposition})


@router.get(f"{settings.api_prefix}/finance/general-settlements/applications")
async def list_general_settlement_applications(
    customer: str = "", case_no: str = "", customer_manager: str = "",
    received_from: date | None = None, received_to: date | None = None,
    payer: str = "", payment_method: str = "", applied_by: str = "",
    applied_from: date | None = None, applied_to: date | None = None,
    hearing_lawyer: str = "", assistant: str = "", reviewer: str = "",
    reviewed_from: date | None = None, reviewed_to: date | None = None,
    paid_from: date | None = None, paid_to: date | None = None,
    source_person: str = "", application_status: str = Query("待审批", alias="status"),
    page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=200),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _round_fee_amount,
    )
    from app.core.permissions import (
        _record_dict_for_identity, _settlement_application_scope,
    )
    for start_date, end_date, label in (
        (received_from, received_to, "回款"),
        (applied_from, applied_to, "提交"),
        (reviewed_from, reviewed_to, "审核"),
        (paid_from, paid_to, "付款"),
    ):
        if start_date and end_date and start_date > end_date:
            raise HTTPException(status_code=422, detail=f"{label}开始日期不能晚于结束日期")
    allowed_statuses = {"待审批", "待付款", "部分付款", "已付款", "已拒绝", "已驳回", "已退回"}
    application_statuses = {item.strip() for item in application_status.split(",") if item.strip()}
    if not application_statuses or not application_statuses.issubset(allowed_statuses):
        raise HTTPException(status_code=422, detail="结算申请状态无效")
    records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance_settlement",
        BusinessRecord.status.in_(application_statuses),
        *_settlement_application_scope(identity),
    ).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()))).all())

    def contains(value: object, needle: str) -> bool:
        return not needle.strip() or needle.strip().casefold() in str(value or "").casefold()

    def date_in_range(value: object, start_date: date | None, end_date: date | None) -> bool:
        if not start_date and not end_date:
            return True
        try:
            current = date.fromisoformat(str(value or "")[:10])
        except ValueError:
            return False
        return (not start_date or current >= start_date) and (not end_date or current <= end_date)

    from app.core.finance import _settlement_customer_manager_resolver
    resolve_manager = await _settlement_customer_manager_resolver(db)
    current_managers = {record.id: resolve_manager(record.data or {}, record.customer) for record in records}
    filtered: list[BusinessRecord] = []
    for record in records:
        data = record.data or {}
        # CaseCenter writes handling_lawyers as an array, while older rows
        # may contain a singular string.  Normalize before any legacy join so
        # a string is never iterated character-by-character.
        handling_values = data.get("handling_lawyers")
        if isinstance(handling_values, str):
            data = {**data, "handling_lawyers": [handling_values]}
        elif not handling_values and isinstance(data.get("handling_lawyer"), str):
            data = {**data, "handling_lawyers": [data["handling_lawyer"]]}
        if not contains(record.customer, customer) or not contains(data.get("case_nos"), case_no):
            continue
        if not contains(current_managers[record.id], customer_manager):
            continue
        if not date_in_range(data.get("received_date"), received_from, received_to):
            continue
        if not contains(data.get("payer_name"), payer) or not contains(data.get("payment_method"), payment_method):
            continue
        if not contains(data.get("applied_by") or record.owner, applied_by):
            continue
        if not date_in_range(data.get("applied_at") or record.created_at, applied_from, applied_to):
            continue
        if not contains(data.get("hearing_lawyer"), hearing_lawyer) or not contains(data.get("assistant"), assistant):
            continue
        if not contains(data.get("reviewer"), reviewer):
            continue
        if not date_in_range(data.get("reviewed_at"), reviewed_from, reviewed_to):
            continue
        if not date_in_range(data.get("paid_at"), paid_from, paid_to):
            continue
        if not contains(data.get("source_person"), source_person):
            continue
        filtered.append(record)

    items = [await _record_dict_for_identity(record, identity, db) for record in filtered]
    for item in items:
        item["data"] = {**item.get("data", {}), "customer_manager": current_managers[item["id"]]}
    amount_keys = ["receipt_amount", "allocated_amount", "remaining_amount", "assigned_official_fee", "assigned_agency_fee", "assigned_other_fee", "agency_settlement_amount", "archive_fee", "actual_settlement_amount"]
    totals = {key: _round_fee_amount(sum(float((item.get("data") or {}).get(key) or 0) for item in items)) for key in amount_keys}
    start = (page - 1) * page_size
    return {"items": items[start:start + page_size], "total": len(items), "totals": totals, "page": page, "page_size": page_size}


@router.post(f"{settings.api_prefix}/finance/general-settlements/applications/reapply")
async def reapply_general_settlement_applications(body: FinanceSettlementReapplyInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _general_settlement_rows,
    )
    from app.core.permissions import (
        _settlement_application_scope,
    )
    comment = body.comment.strip()
    if not comment:
        raise HTTPException(status_code=422, detail="请输入备注.")
    application_ids = list(dict.fromkeys(body.application_ids))
    records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(application_ids),
        BusinessRecord.module == "finance_settlement",
        *_settlement_application_scope(identity),
    ))).all())
    if len(records) != len(application_ids):
        raise HTTPException(status_code=404, detail="部分结算申请不存在或无权访问")
    allowed_from = {"已拒绝", "已驳回", "已退回"}
    invalid = [record.serial_no for record in records if record.status not in allowed_from]
    if invalid:
        raise HTTPException(status_code=409, detail="仅已拒绝或已退回结算可以重新申请：" + "、".join(invalid))
    receipt_ids = [int((record.data or {}).get("receipt_id") or 0) for record in records]
    if any(not receipt_id for receipt_id in receipt_ids):
        raise HTTPException(status_code=409, detail="结算申请缺少来源回款，不能重新申请")
    if len(set(receipt_ids)) != len(receipt_ids):
        raise HTTPException(status_code=409, detail="同一批次不能重复重提同一笔回款")
    locked_receipts = list((await db.scalars(select(IncomingPayment).where(
        IncomingPayment.id.in_(receipt_ids),
    ).with_for_update())).all())
    if len(locked_receipts) != len(receipt_ids):
        raise HTTPException(status_code=409, detail="部分来源回款不存在，不能重新申请")
    active_settlements = await _active_settlements_by_receipt(
        db, set(receipt_ids), exclude_application_ids=set(application_ids),
    )
    if active_settlements:
        blocked = [active_settlements[receipt_id].serial_no for receipt_id in receipt_ids if receipt_id in active_settlements]
        raise HTTPException(status_code=409, detail="来源回款已有其他有效结算申请：" + "、".join(blocked))
    current_rows = await _general_settlement_rows(
        identity, db, receipt_ids=set(receipt_ids), include_active_receipts=True,
    )
    current_by_receipt = {int(row["id"]): row for row in current_rows}
    missing_receipts = [str(receipt_id) for receipt_id in receipt_ids if receipt_id not in current_by_receipt]
    if missing_receipts:
        raise HTTPException(status_code=409, detail="部分来源回款未完整分配或当前不可结算：" + "、".join(missing_receipts))
    reapplied_at = datetime.now().isoformat(timespec="seconds")
    for record in records:
        previous_status = record.status
        receipt_id = int((record.data or {}).get("receipt_id") or 0)
        current_data = dict(current_by_receipt[receipt_id].get("data") or {})
        record.status = "待审批"
        record.description = comment
        record.data = {
            **current_data,
            "applied_by": identity["username"],
            "applied_at": reapplied_at,
            "reapplied_by": identity["username"],
            "reapplied_at": reapplied_at,
            "reapply_comment": comment,
        }
        db.add(WorkflowEvent(
            record_id=record.id,
            action="重新申请结算",
            from_status=previous_status,
            to_status="待审批",
            operator=identity["username"],
            comment=comment,
        ))
    await db.commit()
    return {"reapplied": len(records), "application_ids": application_ids, "status": "待审批"}


@router.post(f"{settings.api_prefix}/finance/general-settlements/applications/review")
async def review_general_settlement_applications(body: FinanceSettlementReviewInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _general_settlement_rows,
    )
    from app.core.permissions import (
        _settlement_application_scope,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有结算审批权限")
    application_ids = list(dict.fromkeys(body.application_ids))
    records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(application_ids),
        BusinessRecord.module == "finance_settlement",
        *_settlement_application_scope(identity),
    ))).all())
    if len(records) != len(application_ids):
        raise HTTPException(status_code=404, detail="部分结算申请不存在或无权访问")
    invalid = [record.serial_no for record in records if record.status != "待审批"]
    if invalid:
        raise HTTPException(status_code=409, detail="仅待审批结算申请可以审核：" + "、".join(invalid))
    if body.approved:
        receipt_ids = {int((record.data or {}).get("receipt_id") or 0) for record in records}
        if 0 in receipt_ids:
            raise HTTPException(status_code=409, detail="结算申请缺少来源回款，不能审批")
        current_rows = await _general_settlement_rows(
            identity, db, receipt_ids=receipt_ids, include_active_receipts=True,
        )
        current_by_receipt = {int(row["id"]): row for row in current_rows}
        stale = []
        for record in records:
            receipt_id = int((record.data or {}).get("receipt_id") or 0)
            current = current_by_receipt.get(receipt_id)
            if not current or _settlement_financial_snapshot(record.data or {}) != _settlement_financial_snapshot(current.get("data") or {}):
                stale.append(record.serial_no)
        if stale:
            raise HTTPException(status_code=409, detail="结算来源金额或分配已变化，请退回后重新申请：" + "、".join(stale))
    target_status = "待付款" if body.approved else "已拒绝"
    action = "同意结算" if body.approved else "拒绝结算"
    reviewed_at = datetime.now().isoformat(timespec="seconds")
    comment = body.comment.strip()
    for record in records:
        record.status = target_status
        record.data = {
            **(record.data or {}),
            "reviewer": identity["username"],
            "reviewed_at": reviewed_at,
            "review_comment": comment,
        }
        db.add(WorkflowEvent(
            record_id=record.id, action=action, from_status="待审批",
            to_status=target_status, operator=identity["username"], comment=comment,
        ))
    await db.commit()
    return {"reviewed": len(records), "application_ids": application_ids, "status": target_status}


@router.post(f"{settings.api_prefix}/finance/general-settlements/applications/payment")
async def pay_or_rollback_general_settlement_applications(body: FinanceSettlementPaymentInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    from app.core.finance import (
        _sync_case_commissions_for_links,
    )
    from app.core.permissions import (
        _settlement_application_scope,
    )
    if identity.get("role") not in {"admin", "manager", "auditor"}:
        raise HTTPException(status_code=403, detail="当前角色没有结算付款权限")
    application_ids = list(dict.fromkeys(body.application_ids))
    records = list((await db.scalars(select(BusinessRecord).where(
        BusinessRecord.id.in_(application_ids),
        BusinessRecord.module == "finance_settlement",
        *_settlement_application_scope(identity),
    ))).all())
    if len(records) != len(application_ids):
        raise HTTPException(status_code=404, detail="部分结算申请不存在或无权访问")
    invalid = [record.serial_no for record in records if record.status not in {"待付款", "已付款"}]
    if invalid:
        raise HTTPException(status_code=409, detail="仅待付款或已付款结算申请可以处理付款：" + "、".join(invalid))
    paid_again = [record.serial_no for record in records if record.status == "已付款" and body.action == "paid"]
    if paid_again:
        raise HTTPException(status_code=409, detail="已付款结算申请只能回退：" + "、".join(paid_again))
    comment = body.comment.strip()
    if body.action == "rollback" and not comment:
        raise HTTPException(status_code=422, detail="请输入回退备注。")
    if body.action == "rollback":
        archive_decisions = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "finance_archive_settlement",
            BusinessRecord.status.in_({"已支付", "已拒绝"}),
            *_settlement_application_scope(identity),
        ))).all())
        blocked_application_ids = {
            int((decision.data or {}).get("source_application_id") or 0)
            for decision in archive_decisions
        } & set(application_ids)
        if blocked_application_ids:
            raise HTTPException(
                status_code=409,
                detail="请先回滚或重新申请关联归档费，再回退结算",
            )
    processed_at = datetime.now().isoformat(timespec="seconds")
    if body.action == "paid":
        target_status = "已付款"
        action = "标记已支付"
        data_updates = {
            "paid_by": identity["username"],
            "paid_at": processed_at,
            "paid_comment": comment,
        }
    else:
        target_status = "已退回"
        action = "回退结算"
        data_updates = {
            "rollback_by": identity["username"],
            "rollback_at": processed_at,
            "rollback_comment": comment,
            "rejection_comment": comment,
        }
    for record in records:
        previous_status = record.status
        record.status = target_status
        record.data = {**(record.data or {}), **data_updates}
        db.add(WorkflowEvent(
            record_id=record.id,
            action=action,
            from_status=previous_status,
            to_status=target_status,
            operator=identity["username"],
            comment=comment,
        ))
    source_fee_ids = {
        int(detail.get("fee_id") or 0)
        for record in records
        for detail in list((record.data or {}).get("allocation_details") or [])
        if isinstance(detail, dict) and str(detail.get("fee_id") or "").isdigit()
    } - {0}
    await _sync_case_commissions_for_links(
        db,
        operator=identity["username"],
        source_fee_ids=source_fee_ids,
        comment="一般结算已付款" if body.action == "paid" else "一般结算付款回退",
    )
    await db.commit()
    return {
        "processed": len(records),
        "application_ids": application_ids,
        "status": target_status,
        "action": action,
    }


@router.get(f"{settings.api_prefix}/finance/general-settlements/export")
async def export_general_settlements(
    kind: str = Query("settlement", pattern="^(settlement|receipt|case)$"), ids: str = "", application_ids: str = "",
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    from app.core.finance import (
        _general_settlement_rows,
    )
    from app.core.permissions import (
        _settlement_application_scope,
    )
    from app.core.system import (
        _export_ids,
    )
    if application_ids.strip():
        selected_application_ids = set(_export_ids(application_ids))
        if not selected_application_ids:
            raise HTTPException(status_code=422, detail="请选择需要导出的结算申请.")
        records = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.id.in_(selected_application_ids),
            BusinessRecord.module == "finance_settlement",
            *_settlement_application_scope(identity),
        ))).all())
        if len(records) != len(selected_application_ids):
            raise HTTPException(status_code=409, detail="部分结算申请不存在或无权导出")
        rows = [{
            "id": record.id,
            "serial_no": str((record.data or {}).get("receipt_no") or record.serial_no),
            "customer": record.customer,
            "data": record.data or {},
        } for record in records]
    else:
        selected_ids = set(_export_ids(ids)) if ids.strip() else None
        if selected_ids is not None and not selected_ids:
            raise HTTPException(status_code=422, detail="请选择需要导出的回款.")
        rows = await _general_settlement_rows(identity, db, receipt_ids=selected_ids)
        if selected_ids is not None and len({int(row["id"]) for row in rows}) != len(selected_ids):
            raise HTTPException(status_code=409, detail="部分回款已申请结算、尚未分配或无权导出")
    if not rows:
        raise HTTPException(status_code=422, detail="没有可导出的待结算记录")
    def cell(value: object, *, number: bool = False) -> str:
        value_text = f"{float(value or 0):.2f}" if number else str(value or "")
        return f'<Cell><Data ss:Type="{"Number" if number else "String"}">{xml_escape(value_text)}</Data></Cell>'
    if kind == "receipt":
        headers = ["回款编号", "客户名称", "回款单位", "回款日期", "回款金额", "已分金额", "未分金额", "回款方式", "银行备注"]
        values = [[row["serial_no"], row["customer"], row["data"].get("payer_name"), row["data"].get("received_date"), row["data"].get("receipt_amount"), row["data"].get("allocated_amount"), row["data"].get("remaining_amount"), row["data"].get("payment_method"), row["data"].get("bank_remark")] for row in rows]
        numeric = {4, 5, 6}
        sheet_name = "到账清单"
    elif kind == "case":
        headers = ["回款编号", "案号", "阶段", "费用类型", "本笔分配金额", "本笔结算金额", "本笔归档费", "客户", "经办律师", "律师助理", "合同号"]
        values = [[row["serial_no"], detail.get("case_no"), detail.get("case_stage"), detail.get("fee_type"), detail.get("current_amount"), detail.get("settlement_amount"), detail.get("archive_fee"), detail.get("customer"), detail.get("handling_lawyer"), detail.get("assistant"), detail.get("contract_no")] for row in rows for detail in row["data"].get("allocation_details", [])]
        numeric = {4, 5, 6}
        sheet_name = "案件清单"
    else:
        headers = ["回款编号", "客户名称", "客户管理人", "回款单位", "回款日期", "回款金额", "已分金额", "未分金额", "已分官费", "已分代理费", "已分其他费用", "代理费结算金额", "扣归档费", "实际结算金额"]
        values = [[row["serial_no"], row["customer"], row["data"].get("customer_manager"), row["data"].get("payer_name"), row["data"].get("received_date"), row["data"].get("receipt_amount"), row["data"].get("allocated_amount"), row["data"].get("remaining_amount"), row["data"].get("assigned_official_fee"), row["data"].get("assigned_agency_fee"), row["data"].get("assigned_other_fee"), row["data"].get("agency_settlement_amount"), row["data"].get("archive_fee"), row["data"].get("actual_settlement_amount")] for row in rows]
        numeric = set(range(5, 14))
        sheet_name = "结算清单"
    sheet_rows = ["<Row>" + "".join(cell(value) for value in headers) + "</Row>"]
    sheet_rows.extend("<Row>" + "".join(cell(value, number=index in numeric) for index, value in enumerate(row)) + "</Row>" for row in values)
    workbook = '<?xml version="1.0" encoding="UTF-8"?><?mso-application progid="Excel.Sheet"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet ss:Name="' + sheet_name + '"><Table>' + "".join(sheet_rows) + "</Table></Worksheet></Workbook>"
    filename = f"{sheet_name}-{date.today()}.xls"
    disposition = f"attachment; filename=settlement-export.xls; filename*=UTF-8''{quote(filename)}"
    return Response(content=workbook.encode("utf-8"), media_type="application/vnd.ms-excel", headers={"Content-Disposition": disposition})


@router.delete(f"{settings.api_prefix}/finance/general-settlements/applications/{{application_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_general_settlement_application(application_id: int, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    if identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可以删除结算申请")
    item = await db.get(BusinessRecord, application_id)
    if not item or item.module != "finance_settlement":
        raise HTTPException(status_code=404, detail="结算申请不存在")
    archive_decisions = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance_archive_settlement",
    ))).all()
    for decision in archive_decisions:
        if int((decision.data or {}).get("source_application_id") or 0) == item.id:
            await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == decision.id))
            await db.delete(decision)
    await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == item.id))
    await db.delete(item)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
