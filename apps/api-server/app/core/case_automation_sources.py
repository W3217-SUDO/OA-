"""案件自动化扫描所需的历史阶段、证据和财务来源。"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BusinessRecord, FileAttachment, HearingSchedule, IncomingPayment,
    LegacyCasePhaseHistory, LegacyInvestigationClue, LegacyInvestigationClueEvidence,
    SystemConfig, SystemParameter,
)


def _as_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value or "").strip()
    try:
        return date.fromisoformat(raw[:10]) if raw else None
    except ValueError:
        return None


def _reference_list(value: object) -> list[str]:
    values = value if isinstance(value, list) else str(value or "").replace("，", ",").split(",")
    return list(dict.fromkeys(str(item or "").strip() for item in values if str(item or "").strip()))


def _case_clues(case_record: BusinessRecord) -> list[str]:
    data = case_record.data or {}
    return _reference_list(data.get("investigation_clue_nos") or data.get("clue_nos") or data.get("clue_no"))


@dataclass
class HearingTrigger:
    source_id: str
    hearing_date: date


@dataclass
class RuleSources:
    phase_start: dict[int, date] = field(default_factory=dict)
    phase_count: dict[tuple[int, str], int] = field(default_factory=dict)
    clue_evidence: dict[str, list[tuple[LegacyInvestigationClue, LegacyInvestigationClueEvidence]]] = field(default_factory=lambda: defaultdict(list))
    current_clues: dict[str, BusinessRecord] = field(default_factory=dict)
    certificate_upload_clues: set[str] = field(default_factory=set)
    hearings: dict[int, list[HearingTrigger]] = field(default_factory=lambda: defaultdict(list))
    payments: dict[int, list[IncomingPayment]] = field(default_factory=lambda: defaultdict(list))
    invoices: dict[int, list[BusinessRecord]] = field(default_factory=lambda: defaultdict(list))
    invoice_fees: dict[int, BusinessRecord] = field(default_factory=dict)
    preservation_events: dict[int, list[tuple[str, date]]] = field(default_factory=lambda: defaultdict(list))
    settlement_cases: set[int] = field(default_factory=set)
    staff_companies: dict[str, dict] = field(default_factory=dict)


async def _load_sources(db: AsyncSession, cases: list[BusinessRecord], *, include_finance: bool = True) -> RuleSources:
    sources = RuleSources()
    staff_config = await db.scalar(select(SystemConfig).where(SystemConfig.key == "automatic_task_staff"))
    companies = (staff_config.value or {}).get("companies", {}) if staff_config else {}
    if isinstance(companies, dict):
        sources.staff_companies = companies
    case_ids = {case.id for case in cases}
    case_by_no = {case.serial_no: case for case in cases}
    phases = (await db.execute(select(
        LegacyCasePhaseHistory.case_record_id, SystemParameter.name,
        LegacyCasePhaseHistory.legacy_created_at,
    ).join(SystemParameter, SystemParameter.id == LegacyCasePhaseHistory.phase_parameter_id)
     .where(LegacyCasePhaseHistory.case_record_id.in_(case_ids))
     .order_by(LegacyCasePhaseHistory.legacy_created_at, LegacyCasePhaseHistory.id))).all()
    current_status = {case.id: case.status for case in cases}
    for case_id, name, entered_at in phases:
        if not case_id or not entered_at:
            continue
        key = (case_id, name)
        sources.phase_count[key] = sources.phase_count.get(key, 0) + 1
        if current_status.get(case_id) == name:
            sources.phase_start[case_id] = entered_at.date()
    for case in cases:
        changed = _as_date((case.data or {}).get("phase_changed_at"))
        if changed:
            sources.phase_start[case.id] = changed

    clue_numbers = {number for case in cases for number in _case_clues(case)}
    if clue_numbers:
        clues = (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "clue", BusinessRecord.serial_no.in_(clue_numbers),
        ))).all()
        sources.current_clues = {clue.serial_no: clue for clue in clues}
        evidence = (await db.execute(select(LegacyInvestigationClue, LegacyInvestigationClueEvidence)
            .join(LegacyInvestigationClueEvidence, LegacyInvestigationClueEvidence.ClueGuid == LegacyInvestigationClue.ClueGuid)
            .where(LegacyInvestigationClue.ClueNo.in_(clue_numbers)))).all()
        for clue, row in evidence:
            if str(row.IsActived or "").upper() not in {"N", "F", "0"}:
                sources.clue_evidence[str(clue.ClueNo)].append((clue, row))

        notaries = (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "notary",
            BusinessRecord.data["clue_no"].as_string().in_(clue_numbers),
        ))).all()
        notary_clues = {
            notary.id: str((notary.data or {}).get("clue_no") or "").strip()
            for notary in notaries
        }
        if notary_clues:
            scans = (await db.scalars(select(FileAttachment).where(
                FileAttachment.record_id.in_(notary_clues),
                FileAttachment.category == "公证书扫描件",
            ))).all()
            sources.certificate_upload_clues = {
                notary_clues[scan.record_id] for scan in scans
                if notary_clues[scan.record_id] in clue_numbers
            }

    hearings = (await db.scalars(select(HearingSchedule).where(
        HearingSchedule.case_record_id.in_(case_ids), HearingSchedule.status == "已排期",
    ))).all()
    for hearing in hearings:
        sources.hearings[hearing.case_record_id].append(HearingTrigger(f"schedule:{hearing.id}", hearing.hearing_date))
    for case in cases:
        scheduled_dates = {trigger.hearing_date for trigger in sources.hearings[case.id]}
        for field_name in (
            "next_hearing_date", "first_court_hearing_date", "second_court_hearing_date",
            "execution_court_hearing_date", "retrial_court_hearing_date",
        ):
            hearing_date = _as_date((case.data or {}).get(field_name))
            if hearing_date and hearing_date not in scheduled_dates:
                sources.hearings[case.id].append(HearingTrigger(f"case:{field_name}", hearing_date))
                scheduled_dates.add(hearing_date)
    orders = (await db.scalars(select(FileAttachment).where(
        FileAttachment.record_id.in_(case_ids),
        FileAttachment.original_name.ilike("%保全裁定%"),
    ))).all()
    for order in orders:
        if order.created_at:
            sources.preservation_events[order.record_id].append((f"order:{order.id}", order.created_at.date()))
    preservation_fees = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance",
        BusinessRecord.data["remark"].as_string().ilike("%保全费%"),
    ))).all()
    for fee in preservation_fees:
        fee_data = fee.data or {}
        try:
            paid_amount = float(fee_data.get("paid_amount") or 0)
        except (TypeError, ValueError):
            continue
        if paid_amount <= 0:
            continue
        try:
            linked_case_id = int(fee_data.get("case_id") or 0)
        except (TypeError, ValueError):
            continue
        paid = _as_date(fee_data.get("cashed_date") or fee_data.get("paid_at"))
        if linked_case_id in case_ids and paid:
            sources.preservation_events[linked_case_id].append((f"fee:{fee.id}", paid))
    if not include_finance:
        return sources
    payments = (await db.scalars(select(IncomingPayment).where(
        IncomingPayment.received_date.is_not(None),
    ))).all()
    for payment in payments:
        for allocation in payment.allocations or []:
            if not isinstance(allocation, dict):
                continue
            try:
                allocation_amount = float(allocation.get("amount") or 0)
            except (TypeError, ValueError):
                continue
            if allocation_amount <= 0:
                continue
            linked = case_by_no.get(str(allocation.get("case_no") or "").strip())
            try:
                case_id = int(allocation.get("case_id") or 0)
            except (TypeError, ValueError):
                case_id = 0
            if case_id in case_ids:
                sources.payments[case_id].append(payment)
            elif linked:
                sources.payments[linked.id].append(payment)
    settlements = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "finance_settlement",
        BusinessRecord.status.not_in({"已拒绝", "已撤回", "已取消"}),
    ))).all()
    for settlement in settlements:
        for allocation in (settlement.data or {}).get("allocation_details") or []:
            if not isinstance(allocation, dict):
                continue
            try:
                linked_case_id = int(allocation.get("case_id") or 0)
            except (TypeError, ValueError):
                continue
            if linked_case_id in case_ids:
                sources.settlement_cases.add(linked_case_id)
    invoices = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "invoice"))).all()
    fee_ids = set()
    for invoice in invoices:
        data = invoice.data or {}
        for raw_id in data.get("case_fee_ids") or []:
            try:
                fee_ids.add(int(raw_id))
            except (TypeError, ValueError):
                continue
        linked_ids = data.get("case_ids") if isinstance(data.get("case_ids"), list) else []
        for case_id in linked_ids:
            try:
                parsed = int(case_id)
            except (TypeError, ValueError):
                continue
            if parsed in case_ids:
                sources.invoices[parsed].append(invoice)
        linked = case_by_no.get(str(data.get("case_no") or "").strip())
        if linked:
            sources.invoices[linked.id].append(invoice)
    if fee_ids:
        fees = (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.id.in_(fee_ids), BusinessRecord.module.in_({"finance", "case_fee"}),
        ))).all()
        sources.invoice_fees = {fee.id: fee for fee in fees}
    return sources
