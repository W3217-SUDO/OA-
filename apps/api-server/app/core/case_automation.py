"""案件阶段计时和经确认的自动任务规则。"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.automatic_task_diagnostics import warn_automatic_task
from app.core.case_automation_sources import RuleSources, _as_date, _case_clues, _load_sources, _reference_list
from app.core.task_personnel import resolve_automatic_task_user
from app.models import (
    BusinessRecord, Department, User, WorkflowEvent,
)


RULE_PREFIX = "confirmed_case_rule_"
PHASE_COMPLETION_RULES = frozenset({1, 4, 5, 6})
TERMINAL_TASK_STATUSES = frozenset({"已完成", "待确认", "已验收", "已拒绝", "已撤回", "已停止", "已取消"})
MEDIATION_CLOSED = frozenset({"一审和解结案", "二审和解结案", "再审和解结案", "执行和解结案"})
MEDIATING = frozenset({"一审和解中", "二审和解中", "再审和解中", "执行和解中"})
PENDING_EXECUTION = frozenset({"一审待执行", "二审待执行", "再审待执行"})
ARCHIVE_STAGES = frozenset({"待归档审核", "归档审核", "亏损内审", "亏损审核", "已归档", "亏损归档"})
TIMESTAMP_ORGANIZATIONS = frozenset({"时间戳", "权利卫士", "时间戳取证"})


def _certificate_received(evidence: object, clue_data: dict, clue_no: str, sources: RuleSources) -> bool:
    return bool(
        (evidence.NotarialNo and evidence.NotarialObtainDate)
        or clue_data.get("certificate_no")
        or clue_no in sources.certificate_upload_clues
    )


def requires_phase_completion(task: BusinessRecord) -> bool:
    task_type = str((task.data or {}).get("auto_task_type") or "")
    return task_type in {f"{RULE_PREFIX}{number:02d}" for number in PHASE_COMPLETION_RULES}


def case_progress_rank(status: str) -> int:
    """统一法院信息自动推进的审级优先级。"""
    if status in ARCHIVE_STAGES:
        return 100
    if status in {"再审待执行"}:
        return 48
    if status in {"再审通知开庭", "再审准备开庭"}:
        return 43
    if status == "再审补充证据":
        return 42
    if status == "再审立案受理":
        return 41
    if status.startswith("再审"):
        return 40 if status == "再审" else 44
    if status == "执行受理":
        return 52
    if status == "准备材料":
        return 49
    if status == "提交法院":
        return 50
    if status.startswith("执行"):
        return 51 if status == "执行" else 53
    if status == "二审待执行":
        return 27
    if status in {"二审通知开庭", "二审准备开庭"}:
        return 23
    if status == "二审补充证据":
        return 22
    if status == "二审立案受理":
        return 21
    if status.startswith("二审"):
        return 20 if status == "二审" else 24
    if status == "一审待执行":
        return 17
    if status in {"待上诉", "一审等待上诉"}:
        return 16
    if status == "一审准备开庭":
        return 13
    if status == "一审立案受理":
        return 11
    if status == "一审补充证据":
        return 12
    if status.startswith("一审"):
        return 14
    return {"新案待分配": 0, "文书准备": 1, "提交立案": 2}.get(status, 0)


def _hearing_reached_or_case_closed(status: str) -> bool:
    return bool(
        "开庭" in status
        or "庭后" in status
        or "判决" in status
        or status.endswith("结案")
        or status in PENDING_EXECUTION | ARCHIVE_STAGES | {"待上诉", "一审等待上诉", "提交法院"}
        or status.startswith("执行")
    )


async def advance_case_for_uploaded_document(
    case_record: BusinessRecord, filename: str, db: AsyncSession, *, operator: str,
) -> bool:
    """受理通知书上传后按审级前进，不覆盖更高审级和归档阶段。"""
    from app.core.tasks import _automatic_case_conflict_blocked

    name = str(filename or "").strip()
    if "受理通知书" not in name or case_record.status in ARCHIVE_STAGES:
        return False
    if await _automatic_case_conflict_blocked(case_record, db):
        return False
    if "再审" in name:
        target = "再审立案受理"
    elif "执行" in name:
        target = "执行受理"
    elif "二审" in name:
        target = "二审立案受理"
    elif "一审" in name:
        target = "一审立案受理"
    else:
        return False
    status = case_record.status
    if case_progress_rank(target) <= case_progress_rank(status) or target == status:
        return False
    case_record.status = target
    case_record.data = {
        **(case_record.data or {}), "phase_changed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    db.add(WorkflowEvent(
        record_id=case_record.id, action="受理通知书自动推进案件阶段",
        from_status=status, to_status=target, operator=operator, comment=name,
    ))
    await apply_case_rules_on_change(case_record, db)
    return True


def _current_phase_token(case_record: BusinessRecord, phase_start: date) -> str:
    entered = str((case_record.data or {}).get("phase_changed_at") or "").strip()
    return f"{case_record.status}:{entered or phase_start.isoformat()}"


async def _configured_staff(
    db: AsyncSession, case_record: BusinessRecord, role: str, sources: RuleSources,
) -> User | None:
    company_id = str((case_record.data or {}).get("company_id") or "").strip()
    company = sources.staff_companies.get(company_id, {})
    username = company.get(role) if isinstance(company, dict) else None
    if not username:
        warn_automatic_task(
            "case automatic task skipped: case_id=%s role=%s company_id=%s reason=staff_not_configured",
            case_record.id, role, company_id,
        )
        return None
    return await resolve_automatic_task_user(username, db)


async def _people(case_record: BusinessRecord, db: AsyncSession) -> tuple[User | None, User | None, User | None]:
    data = case_record.data or {}
    lawyer = await resolve_automatic_task_user(
        data.get("handling_lawyer_usernames") or data.get("handling_lawyers"), db,
    )
    assistant = await resolve_automatic_task_user(
        data.get("assistant_usernames") or data.get("assistant_username") or data.get("assistant"), db,
    )
    hearing_lawyer = await resolve_automatic_task_user(
        data.get("hearing_lawyer_username") or data.get("hearing_lawyer"), db,
    )
    return lawyer, assistant, hearing_lawyer


async def _create(
    case_record: BusinessRecord, db: AsyncSession, *,
    number: int, title: str, owner: User | None, initiator: User | None,
    description: str, trigger_at: date, source: str, days: int,
    deadline: date | None = None,
) -> BusinessRecord | None:
    if owner is None or (number in {1, 4, 5, 6, 11, 12, 13, 14} and initiator is None):
        warn_automatic_task(
            "case automatic task skipped: case_id=%s rule=%s reason=required_person_missing",
            case_record.id, number,
        )
        return None
    from app.core.tasks import _materialize_legacy_case_task

    return await _materialize_legacy_case_task(
        case_record, db, auto_task_type=f"{RULE_PREFIX}{number:02d}",
        legacy_task_type_id=0, title=title, initiator=initiator, owner=owner,
        collaborators=[], description=description, started_on=date.today(),
        deadline=deadline or date.today() + timedelta(days=days),
        trigger_at=trigger_at, trigger_source_id=source,
    )


async def _apply_phase_rules(case_record: BusinessRecord, sources: RuleSources, db: AsyncSession, today: date) -> None:
    phase = case_record.status
    if phase not in {"文书准备", "提交立案", "一审立案受理", "二审立案受理", "再审立案受理", "执行终本"} | PENDING_EXECUTION | MEDIATION_CLOSED | MEDIATING:
        return
    phase_start = sources.phase_start.get(case_record.id)
    if phase_start is None:
        warn_automatic_task("case automatic task skipped: case_id=%s reason=phase_start_unknown", case_record.id)
        return
    age = (today - phase_start).days
    source = _current_phase_token(case_record, phase_start)
    lawyer, assistant, hearing_lawyer = await _people(case_record, db)
    if phase == "文书准备":
        if age > 100 and lawyer and assistant:
            await _create(case_record, db, number=1, title="文书过期提醒", owner=assistant,
                initiator=lawyer, description="尽快完成文书准备工作", trigger_at=phase_start + timedelta(days=101),
                source=source, days=10)
        if sources.phase_count.get((case_record.id, "文书准备"), 0) <= 1 and not any(
            visit.get("phase") == "文书准备" for visit in (case_record.data or {}).get("phase_visits") or []
        ) and assistant:
            clue_numbers = _case_clues(case_record)
            evidence_rows = [
                (clue, evidence) for number in clue_numbers
                for clue, evidence in sources.clue_evidence.get(number, [])
            ]
            current_methods = [
                str((sources.current_clues[number].data or {}).get("notary_institution") or "").strip()
                for number in clue_numbers if number in sources.current_clues
            ]
            if any(str(evidence.NotaryOrganization or "").strip() in TIMESTAMP_ORGANIZATIONS for _, evidence in evidence_rows) or any(
                method in TIMESTAMP_ORGANIZATIONS for method in current_methods
            ):
                investigator = await resolve_automatic_task_user(
                    (case_record.data or {}).get("investigator_username")
                    or next((
                        (sources.current_clues[number].data or {}).get("collected_by")
                        for number in clue_numbers if number in sources.current_clues
                        and (sources.current_clues[number].data or {}).get("collected_by")
                    ), "")
                    or _reference_list(next((clue.Investigators or clue.InvestigatorNames for clue, _ in evidence_rows if clue.Investigators or clue.InvestigatorNames), "")), db,
                )
                await _create(case_record, db, number=2, title="交接时间戳文件", owner=investigator,
                    initiator=assistant, description="完成时间戳文件交接", trigger_at=phase_start,
                    source=source, days=10)
            if any(
                str(evidence.NotaryOrganization or "").strip()
                and str(evidence.NotaryOrganization or "").strip() not in TIMESTAMP_ORGANIZATIONS
                for _, evidence in evidence_rows
            ) or any(method and method not in TIMESTAMP_ORGANIZATIONS for method in current_methods):
                owner = await _configured_staff(db, case_record, "notary_handover_username", sources)
                await _create(case_record, db, number=3, title="交接公证书", owner=owner,
                    initiator=assistant, description="完成公证书交接", trigger_at=phase_start,
                    source=source, days=10)
    elif phase == "提交立案" and age > 100:
        await _create(case_record, db, number=4, title="跟进立案", owner=assistant,
            initiator=hearing_lawyer, description="案件提交立案已经超过100天，尽快跟进法院立案",
            trigger_at=phase_start + timedelta(days=101), source=source, days=10)
    elif phase in {"一审立案受理", "二审立案受理", "再审立案受理"} and age > 100:
        await _create(case_record, db, number=5, title="跟进立案", owner=assistant,
            initiator=hearing_lawyer, description="案件立案受理已经超过100天，尽快跟进法院开庭",
            trigger_at=phase_start + timedelta(days=101), source=source, days=10)
    elif phase in PENDING_EXECUTION and age > 60:
        await _create(case_record, db, number=6, title="执行提醒", owner=assistant,
            initiator=hearing_lawyer, description="提交执行",
            trigger_at=phase_start + timedelta(days=61), source=source, days=10)
    elif phase == "执行终本":
        await _create(case_record, db, number=7, title="案件研究", owner=hearing_lawyer,
            initiator=None, description="本案现已终本，请研究可行的后续执行方案，或移交其他人员研究",
            trigger_at=phase_start, source=source, days=10)
    elif phase in MEDIATION_CLOSED and age > 60:
        await _create(case_record, db, number=8, title="跟进结案", owner=hearing_lawyer,
            initiator=None, description="本案和解结案，尽快完成结案归档工作或移交执行",
            trigger_at=phase_start + timedelta(days=61), source=source, days=10)
    elif phase in MEDIATING and age > 60:
        await _create(case_record, db, number=9, title="跟进和解", owner=hearing_lawyer,
            initiator=None, description="本案和解超期限，尽快完成和解或转庭审阶段",
            trigger_at=phase_start + timedelta(days=61), source=source, days=10)


def _advance_due_notary_review(case_record: BusinessRecord, sources: RuleSources, db: AsyncSession, today: date) -> None:
    """公证书审核阶段满三十日后，转入新案待分配。"""
    if case_record.status not in {"等待审核公证书", "审核公证书"}:
        return
    entered = sources.phase_start.get(case_record.id)
    if entered is None or today < entered + timedelta(days=30):
        return
    previous = case_record.status
    case_record.status = "新案待分配"
    case_record.data = {**(case_record.data or {}), "phase_changed_at": datetime.now().astimezone().isoformat(timespec="seconds")}
    sources.phase_start[case_record.id] = today
    db.add(WorkflowEvent(
        record_id=case_record.id, action="公证书审核期满自动推进阶段",
        from_status=previous, to_status="新案待分配", operator="system",
        comment=f"{entered.isoformat()}进入审核阶段，满30日后转入待分配",
    ))


async def _apply_evidence_rules(case_record: BusinessRecord, sources: RuleSources, db: AsyncSession, today: date) -> None:
    data = case_record.data or {}
    _, assistant, hearing_lawyer = await _people(case_record, db)
    clues = _case_clues(case_record)
    for clue_no in clues:
        current = sources.current_clues.get(clue_no)
        current_data = current.data or {} if current else {}
        for legacy_clue, evidence in sources.clue_evidence.get(clue_no, []):
            notary_organization = str(evidence.NotaryOrganization or "").strip()
            if not notary_organization or notary_organization in TIMESTAMP_ORGANIZATIONS:
                continue
            notary_date = _as_date(evidence.EvidenceDate) or _as_date(current_data.get("collected_at"))
            certificate_received = _certificate_received(evidence, current_data, clue_no, sources)
            in_stock = evidence.EvidenceStatus == 20 or str(current_data.get("evidence_status") or "").strip() in {"已入库", "已重新入库"}
            if notary_date and today > notary_date + timedelta(days=60) and not (certificate_received and in_stock):
                investigator = await resolve_automatic_task_user(
                    current_data.get("collected_by") or _reference_list(legacy_clue.Investigators or legacy_clue.InvestigatorNames), db,
                )
                await _create(case_record, db, number=10, title="跟进公证书", owner=investigator,
                    initiator=None, description="本案公证超过60日，抓紧催公证书和证物入库",
                    trigger_at=notary_date + timedelta(days=61),
                    source=f"evidence:{evidence.EvidenceId}", days=10)
        if sources.clue_evidence.get(clue_no):
            continue
        method = str(current_data.get("notary_institution") or "").strip()
        notary_date = _as_date(current_data.get("collected_at"))
        certificate_received = bool(current_data.get("certificate_no") or clue_no in sources.certificate_upload_clues)
        in_stock = str(current_data.get("evidence_status") or "").strip() in {"已入库", "已重新入库"}
        if method and method not in TIMESTAMP_ORGANIZATIONS and notary_date and today > notary_date + timedelta(days=60) and not (certificate_received and in_stock):
            investigator = await resolve_automatic_task_user(current_data.get("collected_by"), db)
            await _create(case_record, db, number=10, title="跟进公证书", owner=investigator,
                initiator=None, description="本案公证超过60日，抓紧催公证书和证物入库",
                trigger_at=notary_date + timedelta(days=61),
                source=f"clue:{clue_no}", days=10)

    for hearing in sources.hearings.get(case_record.id, []):
        hearing_date = hearing.hearing_date
        if hearing_date < today or hearing_date > today + timedelta(days=10) or not assistant:
            continue
        for clue_no in clues:
            current = sources.current_clues.get(clue_no)
            current_data = current.data or {} if current else {}
            has_physical = any(
                evidence.WarehouseNo and evidence.NotaryOrganization
                for _, evidence in sources.clue_evidence.get(clue_no, [])
            ) or bool(
                current_data.get("notary_institution")
                and current_data.get("storage_location")
                and current_data.get("evidence_status") in {"已入库", "已重新入库"}
            )
            if not has_physical:
                continue
            warehouse = await _configured_staff(db, case_record, "warehouse_username", sources)
            deadline = min(today + timedelta(days=7), hearing_date - timedelta(days=1))
            if deadline < today:
                warn_automatic_task("case automatic task skipped: case_id=%s rule=11 reason=hearing_too_soon", case_record.id)
                continue
            await _create(case_record, db, number=11, title="交接证物", owner=warehouse,
                initiator=assistant, description="案件快要开庭了，交接证物",
                trigger_at=today, source=f"hearing:{hearing.source_id}:clue:{clue_no}:{hearing_date}", days=7,
                deadline=deadline)

    changed_at = _as_date(data.get("hearing_lawyer_changed_at"))
    if changed_at and changed_at <= today and assistant and hearing_lawyer:
        handling = set(_reference_list(data.get("handling_lawyer_usernames") or data.get("handling_lawyers")))
        if hearing_lawyer.username not in handling and hearing_lawyer.display_name not in handling:
            department = await db.scalar(select(Department).where(
                Department.name == assistant.department, Department.is_active.is_(True),
            ))
            manager = await resolve_automatic_task_user(department.manager, db) if department else None
            await _create(case_record, db, number=12, title="更换经办律师", owner=manager,
                initiator=assistant, description="开庭律师与经办律师不一致，请更换代理律师",
                trigger_at=changed_at, source=f"hearing-lawyer:{data.get('hearing_lawyer_changed_at')}",
                days=3)

    preservation_events = sources.preservation_events.get(case_record.id, [])
    if preservation_events:
        preservation_date = min(event_date for _, event_date in preservation_events)
        await _create(case_record, db, number=13, title="保全期限提醒", owner=assistant,
            initiator=hearing_lawyer, description="本案存在保全措施，请根据保全措施期限，设定任务日期",
            trigger_at=preservation_date, source=f"preservation:case:{case_record.id}", days=3)


async def _apply_finance_rules(case_record: BusinessRecord, sources: RuleSources, db: AsyncSession, today: date) -> None:
    data = case_record.data or {}
    _, assistant, hearing_lawyer = await _people(case_record, db)
    payments = sources.payments.get(case_record.id, [])
    if payments and case_record.status not in ARCHIVE_STAGES and case_record.id not in sources.settlement_cases and not data.get("archive_submitted_at"):
        first = min((payment.received_date for payment in payments if payment.received_date), default=None)
        if first and today > first + timedelta(days=60):
            await _create(case_record, db, number=14, title="结算归档提醒", owner=assistant,
                initiator=hearing_lawyer, description="本案已经到款，可以归档结算",
                trigger_at=first + timedelta(days=61), source=f"payment:{first}", days=10)
    for invoice in sources.invoices.get(case_record.id, []):
        if invoice.status in {"已作废", "作废"}:
            continue
        invoice_data = invoice.data or {}
        issued = _as_date(invoice_data.get("invoice_date"))
        agency_fees = [sources.invoice_fees.get(int(fee_id)) for fee_id in invoice_data.get("case_fee_ids") or [] if str(fee_id).isdigit()]
        agency_fees = [fee for fee in agency_fees if fee and str((fee.data or {}).get("fee_type") or "") == "代理费"]
        if not agency_fees:
            continue
        unpaid = any(_fee_unpaid(fee) is True for fee in agency_fees)
        if not issued or not unpaid or today <= issued + timedelta(days=90):
            continue
        applicant = await resolve_automatic_task_user(
            invoice_data.get("invoice_applicant") or invoice_data.get("applicant"), db,
        )
        await _create(case_record, db, number=15, title="催收代理费", owner=applicant,
            initiator=None, description="本案已经开具代理费发票90日，尽快催收代理费",
            trigger_at=issued + timedelta(days=91), source=f"invoice:{invoice.id}", days=10)


def _fee_unpaid(fee: BusinessRecord) -> bool | None:
    data = fee.data or {}
    legacy = data.get("legacy_record") if isinstance(data.get("legacy_record"), dict) else {}
    try:
        amount = float(data.get("amount") if data.get("amount") is not None else legacy.get("Amount"))
        received = float(
            data.get("received_amount") if data.get("received_amount") is not None
            else data.get("cashed_amount") if data.get("cashed_amount") is not None
            else legacy.get("CashedAmount") if legacy.get("CashedAmount") is not None
            else 0
        )
    except (TypeError, ValueError):
        warn_automatic_task("agency fee balance unresolved: finance_record_id=%s", fee.id)
        return None
    return amount - received > 0.001


async def _complete_matching_tasks(db: AsyncSession, sources: RuleSources, cases: list[BusinessRecord]) -> None:
    from app.core.tasks import _add_task_message_notifications, _finish_legacy_auto_task

    by_id = {case.id: case for case in cases}
    tasks = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "task",
        BusinessRecord.data["auto_task_type"].as_string().like(f"{RULE_PREFIX}%"),
        BusinessRecord.data["case_id"].as_integer().in_(by_id),
    ))).all()
    for task in tasks:
        data = task.data or {}
        try:
            case_id = int(data.get("case_id") or 0)
            rule_number = int(str(data.get("auto_task_type") or "")[-2:])
        except (TypeError, ValueError):
            continue
        case = by_id.get(case_id)
        if not case or task.status in TERMINAL_TASK_STATUSES:
            continue
        status = case.status
        reason = ""
        if rule_number == 11:
            valid_sources = {
                f"hearing:{hearing.source_id}:clue:{clue_no}:{hearing.hearing_date}"
                for hearing in sources.hearings.get(case.id, []) for clue_no in _case_clues(case)
            }
            if str(data.get("trigger_source_id") or "") not in valid_sources:
                previous = task.status
                task.status = "已取消"
                original_source = str(data.get("trigger_source_id") or "")
                task.data = {
                    **data, "cancelled_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "original_trigger_source_id": original_source,
                    "trigger_source_id": f"cancelled:{task.id}:{original_source}",
                }
                await _add_task_message_notifications(
                    task,
                    WorkflowEvent(
                        record_id=task.id, action="开庭排期变化取消交接任务",
                        from_status=previous, to_status="已取消", operator="system",
                        comment="开庭日期或关联线索已变更，原证物交接任务不再适用",
                    ), db, content="开庭日期或关联线索已变更，原证物交接任务已取消",
                )
            continue
        if rule_number == 1 and case_progress_rank(status) >= case_progress_rank("提交立案"):
            reason = "案件已离开文书准备，系统自动完成"
        elif rule_number == 4 and case_progress_rank(status) >= case_progress_rank("一审立案受理"):
            reason = "案件已经立案受理，系统自动完成"
        elif rule_number == 5 and _hearing_reached_or_case_closed(status):
            reason = "案件已进入开庭阶段，系统自动完成"
        elif rule_number == 6 and (status == "提交法院" or status.startswith("执行")):
            reason = "案件已提交执行，系统自动完成"
        elif rule_number == 14 and (status in ARCHIVE_STAGES or case.id in sources.settlement_cases or (case.data or {}).get("archive_submitted_at")):
            reason = "案件已提交结算或归档，系统自动完成"
        elif rule_number == 10:
            trigger_source = str(data.get("trigger_source_id") or "")
            evidence_id = trigger_source.removeprefix("evidence:")
            for clue_no in _case_clues(case):
                current = sources.current_clues.get(clue_no)
                current_data = current.data or {} if current else {}
                if trigger_source == f"clue:{clue_no}":
                    certificate_received = bool(
                        current_data.get("certificate_no")
                        or clue_no in sources.certificate_upload_clues
                    )
                    in_stock = str(current_data.get("evidence_status") or "") in {"已入库", "已重新入库"}
                    if certificate_received and in_stock:
                        reason = "公证书已上传且证物已入库，系统自动完成"
                for _, evidence in sources.clue_evidence.get(clue_no, []):
                    if str(evidence.EvidenceId) != evidence_id:
                        continue
                    certificate_received = _certificate_received(evidence, current_data, clue_no, sources)
                    in_stock = evidence.EvidenceStatus == 20 or str(current_data.get("evidence_status") or "") in {"已入库", "已重新入库"}
                    if certificate_received and in_stock:
                        reason = "公证书已上传且证物已入库，系统自动完成"
        elif rule_number == 15:
            invoice_id = str(data.get("trigger_source_id") or "").removeprefix("invoice:")
            for invoice in sources.invoices.get(case.id, []):
                if str(invoice.id) != invoice_id:
                    continue
                if invoice.status in {"已作废", "作废"}:
                    reason = "代理费发票已作废，系统自动完成"
                    break
                fee_ids = (invoice.data or {}).get("case_fee_ids") or []
                agency_fees = [sources.invoice_fees.get(int(fee_id)) for fee_id in fee_ids if str(fee_id).isdigit()]
                agency_fees = [fee for fee in agency_fees if fee and str((fee.data or {}).get("fee_type") or "") == "代理费"]
                if agency_fees and all(_fee_unpaid(fee) is False for fee in agency_fees):
                    reason = "代理费已经到账，系统自动完成"
        if reason:
            await _finish_legacy_auto_task(task, db, reason=reason)


async def scan_confirmed_case_rules(db: AsyncSession, *, today: date | None = None) -> int:
    """逐案扫描确认规则；旧导出规则不参与生成。"""
    from app.core.automatic_task_lookup import automatic_task_lookup_scope
    from app.core.task_personnel import automatic_task_personnel_scope
    from app.core.tasks import _automatic_case_conflict_blocked

    effective_today = today or date.today()
    before = int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
        BusinessRecord.module == "task",
    )) or 0)
    cases = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case",
        BusinessRecord.status.not_in({"已归档", "亏损归档", "已合并"}),
    ))).all()
    sources = await _load_sources(db, cases)
    has_reviews = bool(await db.scalar(select(BusinessRecord.id).where(BusinessRecord.module == "conflict_review").limit(1)))
    async with automatic_task_personnel_scope(db), automatic_task_lookup_scope(db):
        for case_record in cases:
            if (case_record.data or {}).get("case_type") == "法律顾问":
                continue
            if has_reviews and await _automatic_case_conflict_blocked(case_record, db):
                continue
            _advance_due_notary_review(case_record, sources, db, effective_today)
            await _apply_phase_rules(case_record, sources, db, effective_today)
            await _apply_evidence_rules(case_record, sources, db, effective_today)
            await _apply_finance_rules(case_record, sources, db, effective_today)
        await _complete_matching_tasks(db, sources, cases)
    after = int(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
        BusinessRecord.module == "task",
    )) or 0)
    return max(after - before, 0)


async def apply_case_rules_on_change(case_record: BusinessRecord, db: AsyncSession) -> None:
    """案件保存后立即处理事件规则，事务由调用端统一提交。"""
    from app.core.automatic_task_lookup import automatic_task_lookup_scope
    from app.core.task_personnel import automatic_task_personnel_scope
    from app.core.tasks import _automatic_case_conflict_blocked

    if (case_record.data or {}).get("case_type") == "法律顾问":
        return
    if await _automatic_case_conflict_blocked(case_record, db):
        return
    sources = await _load_sources(db, [case_record], include_finance=False)
    async with automatic_task_personnel_scope(db), automatic_task_lookup_scope(db):
        await _apply_phase_rules(case_record, sources, db, date.today())
        await _apply_evidence_rules(case_record, sources, db, date.today())
        await _complete_matching_tasks(db, sources, [case_record])
