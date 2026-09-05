"""Financial operating charts based on the legacy CaseSearchDao and fee view."""
from datetime import date
from decimal import Decimal, InvalidOperation
import re

from sqlalchemy import select

from app.models import FinanceTransaction, IncomingPayment
from app.core.query_batches import _scalars_in_batches


def _money(value):
    try:
        number = Decimal(str(value or 0))
        return number if number.is_finite() else Decimal(0)
    except (InvalidOperation, ValueError):
        return Decimal(0)


def _day(value):
    try:
        return date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None


async def operating_charts(cases, fees, view, group_mode, db):
    from app.core.finance import _case_fee_link_maps, _resolve_case_fee_link_id
    from app.core.formatters import _user_display_map

    case_by_id = {case.id: case for case in cases}
    case_by_no = {case.serial_no: case for case in cases}
    fee_cases = {}
    for fee in fees:
        data = fee.data or {}
        if fee.status in {"已撤销", "已删除", "已作废", "已拒绝"}:
            continue
        try:
            case_id = int(data.get("case_id") or data.get("case_record_id") or 0)
        except (TypeError, ValueError):
            case_id = 0
        case = case_by_id.get(case_id) or case_by_no.get(str(data.get("case_no") or ""))
        if case:
            fee_cases[fee.id] = case
    fees = [fee for fee in fees if fee.id in fee_cases]
    fee_by_id = {fee.id: fee for fee in fees}
    fee_ids, legacy_ids = _case_fee_link_maps(fees)
    paid = {}
    for tx in await _scalars_in_batches(db, fee_ids, lambda batch: select(FinanceTransaction).where(
        FinanceTransaction.finance_record_id.in_(batch), FinanceTransaction.transaction_type == "付款",
    )):
        paid[tx.finance_record_id] = paid.get(tx.finance_record_id, Decimal(0)) + _money(tx.amount)
    received, allocation_dates = {}, {}
    # Only explicit fee links are attributable. Never spread an unallocated bank receipt.
    incoming = (await db.scalars(select(IncomingPayment).where(
        IncomingPayment.status.not_in({"已撤销", "已删除", "已作废", "已拒绝"}),
        IncomingPayment.allocated_amount > 0,
    ))).all() if fees else []
    for payment in incoming:
        for allocation in payment.allocations or []:
            if not isinstance(allocation, dict):
                continue
            parts = allocation.get("settlement_items") or [allocation]
            for part in parts:
                if not isinstance(part, dict):
                    continue
                fee_id = _resolve_case_fee_link_id(part, fee_ids, legacy_ids)
                if not fee_id:
                    try:
                        fee_id = int(part.get("finance_record_id") or 0)
                    except (TypeError, ValueError):
                        continue
                if fee_id not in fee_by_id:
                    continue
                case_no = str(allocation.get("case_no") or "").strip()
                if case_no and case_no != fee_cases[fee_id].serial_no:
                    continue
                amount = part.get("amount")
                if amount is None:
                    amount = part.get("settlement_amount")
                received[fee_id] = received.get(fee_id, Decimal(0)) + _money(amount)
                allocated = _day(part.get("allocated_at") or allocation.get("allocated_at"))
                if allocated:
                    allocation_dates[fee_id] = min(allocation_dates.get(fee_id, allocated), allocated)

    rows = {}
    for fee in fees:
        data = fee.data or {}
        case = fee_cases[fee.id]
        row = rows.setdefault(case.id, {"paid": Decimal(0), "official_received": Decimal(0),
                                      "agency_received": Decimal(0), "notice": None, "cashed": None})
        legacy = data.get("legacy") if isinstance(data.get("legacy"), dict) else {}
        code = str(data.get("fee_type_code") or legacy.get("CaseFeeTypeId") or "")
        category = str(data.get("fee_type") or "")
        name = str(data.get("fee_type_name") or data.get("expense_subtype") or category)
        official_codes = {"11010010", "11010020", "11010030", "11010040", "11010050", "11010060", "11010070", "11010090", "11010180", "11010190", "11020065"}
        official = code in official_codes or category in {"官方费用", "官费"} or str(data.get("fee_type_group") or "") in {"1", "官方费用", "官费"}
        agency = code in {"11020010", "11020020", "11020030", "11020040"} or (
            not code and name in {"律师代理费", "代理费", "律师咨询费", "律师培训费", "律师见证费"}
        )
        # Persisted actual totals are a compatibility source, not extra transactions.
        fee_paid = paid.get(fee.id, _money(data.get("paid_amount")))
        fee_received = received.get(fee.id, _money(data.get("cashed_amount") if data.get("cashed_amount") is not None else data.get("received_amount")))
        if official:
            row["paid"] += fee_paid
            row["official_received"] += fee_received
        if agency:
            row["agency_received"] += fee_received
        notice = _day(data.get("inform_date") or legacy.get("InformDate"))
        allocated = allocation_dates.get(fee.id) or _day(data.get("allocated_at"))
        if notice:
            row["notice"] = min(row["notice"] or notice, notice)
        if allocated:
            row["cashed"] = min(row["cashed"] or allocated, allocated)

    grouped = {}
    usernames = set()
    for case in cases:
        if case.id not in rows:
            continue
        data = case.data or {}
        if view == "brand":
            names = [case.customer or "未关联客户"]
        else:
            raw = data.get("assistant") if group_mode == "按文书分组统计" else data.get("hearing_lawyers") or data.get("hearing_lawyer")
            names = raw if isinstance(raw, list) else re.split(r"[,，;；、]", str(raw or ""))
            names = list(dict.fromkeys(str(name).strip() for name in names if str(name).strip())) or ["未分配"]
            usernames.update(names)
        row = rows[case.id]
        legacy = data.get("legacy") if isinstance(data.get("legacy"), dict) else {}
        loss_case = str(data.get("case_phase_id") or legacy.get("CasePhaseId") or "") == "106018" or any(
            "亏损归档" in str(value or "") or str(value or "") == "106018"
            for value in (case.status, data.get("case_stage"), data.get("business_stage"), data.get("phase"))
        )
        loss = row["paid"] - row["official_received"] if loss_case else Decimal(0)
        for name in names:
            group = grouped.setdefault(name, {"all": set(), "cycle": set(), "missing": False})
            group["all"].add((loss, row["paid"], row["agency_received"]))
            if view == "brand" and loss_case:
                continue
            if row["cashed"] is None:
                if row["agency_received"] or row["official_received"]:
                    group["missing"] = True
                continue
            if row["notice"] is None:
                group["missing"] = True
                continue
            gap = (row["cashed"] - row["notice"]).days
            group["cycle"].add((loss, row["paid"], row["agency_received"], row["notice"], row["cashed"], gap))
    displays = await _user_display_map(usernames, db) if usernames else {}
    charts = [{"title": title, "unit": unit, "items": []} for title, unit in (
        ("资金回款周期统计", "天/案"), ("资金亏损金额统计", "元"),
        ("资金回报率统计", "百分比"), ("资金亏损率统计", "百分比"),
    )]
    warnings = []
    for name, group in sorted(grouped.items())[:30]:
        user = displays.get(name.lower())
        label = user.display_name if user else name
        total_loss = sum((item[0] for item in group["all"]), Decimal(0))
        total_paid = sum((item[1] for item in group["all"]), Decimal(0))
        charts[1]["items"].append({"name": label, "value": float(total_loss)})
        charts[3]["items"].append({"name": label, "value": float(total_loss / total_paid * 100) if total_paid else 0})
        cycle = group["cycle"]
        if group["missing"]:
            warnings.append(f"{label}：缺少费用通知日期或回款分配日期，周期和回报率无法完整计算")
        if not cycle or group["missing"]:
            for index in (0, 2):
                charts[index]["items"].append({"name": label, "value": None})
            continue
        avg_days = int(sum(item[5] for item in cycle) / len(cycle))
        loss = sum((item[0] for item in cycle), Decimal(0))
        expense = sum((item[1] for item in cycle), Decimal(0))
        income = sum((item[2] for item in cycle), Decimal(0))
        roi = Decimal(100) if not expense else (income * Decimal("0.15") - loss) / expense / avg_days * 365 * 100 if avg_days else None
        if roi is None:
            warnings.append(f"{label}：平均回款周期为0，资金回报率不可计算")
        charts[0]["items"].append({"name": label, "value": avg_days})
        charts[2]["items"].append({"name": label, "value": round(float(roi), 2) if roi is not None else None})
    return charts, warnings
