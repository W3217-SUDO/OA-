"""报表大屏“员工业绩排行”：按案源人、开庭律师两个角度统计新建案件数和代理费到账（BUG 500798，思法汇成 11-01）。

口径与客户ROI 的收入一致：到账单里分配到“代理费”的金额，按到账日期统计；
公司之间（沪知/恒达/国定）的转款不算（只有客户钱以“其他费用”进来、平台记的“平台代理费”算），
代收代付的到账不算，测试客户不算，退款不算；全部客户都算（不限框架合作合同客户）。
按到账分配到的案件（或合同）分别归到“案源人”和“开庭律师”，多人各算一次。
"""
import re
from datetime import date

from sqlalchemy import func, or_, select

from app.core.json_relation_query import scalar_in_values
from app.core.person_names import person_name, refresh_person_names
from app.models import BusinessRecord, IncomingPayment

RANKING_LIMIT = 10
NO_SOURCE_PERSON = "未填案源人"
NO_HEARING_LAWYER = "未填开庭律师"
_PEOPLE_SPLIT = re.compile(r"[、,，;；\s]+")


def _positive_int(value) -> int:
    try:
        number = int(str(value or "").strip())
    except ValueError:
        return 0
    return number if number > 0 else 0


def _people(value, fallback: str) -> list[str]:
    names = [person_name(item) for item in _PEOPLE_SPLIT.split(str(value or "")) if item]
    return list(dict.fromkeys(names)) or [fallback]


def source_people(record) -> list[str]:
    """案源人：案件上的“案源人”，与案件详情页显示一致（案源人 → 来源人 → 负责人）。"""
    data = record.data or {}
    return _people(data.get("business_owner") or data.get("source_person") or record.owner, NO_SOURCE_PERSON)


def hearing_people(record) -> list[str]:
    hearing = (record.data or {}).get("hearing_lawyer") if record.module == "case" else ""
    return _people(hearing, NO_HEARING_LAWYER)


def investigator_people(record) -> list[str]:
    data = (record.data or {}) if record.module == "case" else {}
    return _people(data.get("investigator") or data.get("investigator_username"), "未填调查员")


def assistant_people(record) -> list[str]:
    data = (record.data or {}) if record.module == "case" else {}
    return _people(data.get("assistant") or data.get("assistant_username"), "未填律师助理")


def case_counts(cases) -> dict:
    """新建案件数按案源人、开庭律师分别统计（18:14：不要按案件负责人），多人各算一次。"""
    by_source: dict[str, int] = {}
    by_hearing: dict[str, int] = {}
    for case in cases:
        for person in source_people(case):
            by_source[person] = by_source.get(person, 0) + 1
        for person in hearing_people(case):
            by_hearing[person] = by_hearing.get(person, 0) + 1
    return {"by_source_person": by_source, "by_hearing_lawyer": by_hearing}


def _is_test_customer(title: str) -> bool:
    return "测试" in title or "test" in title.lower()


async def agency_fee_totals(db, scope: list, date_from: date, date_to: date, *, extra_roles: dict | None = None) -> dict:
    """extra_roles：员工业绩统计中心（BUG 500799）另按调查员、律师助理等角色归，{结果键: 取人函数}。"""
    from app.core.crm import _roi_receipts
    from app.core.internal_payers import is_internal_payer
    await refresh_person_names(db)
    receipts = await _roi_receipts(
        db, IncomingPayment.amount > 0,
        ~func.coalesce(IncomingPayment.claimed_customer, "").contains("代收代付"),
        IncomingPayment.received_date >= date_from, IncomingPayment.received_date <= date_to,
    )

    def case_key(allocation) -> str:
        return str(allocation.get("case_no") or allocation.get("case_id") or "").strip()

    # 与客户ROI 相同：同一案件客户已直接付代理费时，公司之间转款里的代理费是同一笔钱，不算。
    customer_agency: dict[str, float] = {}
    customer_other: dict[str, float] = {}
    internal_fee_ids: set[int] = set()
    for receipt in receipts:
        internal = is_internal_payer(receipt.payer_name)
        for allocation in receipt.allocations or []:
            if not isinstance(allocation, dict) or allocation.get("is_refund"):
                continue
            if internal:
                if allocation.get("fee_type") == "代理费":
                    internal_fee_ids.add(_positive_int(allocation.get("fee_id")))
                continue
            target = customer_agency if allocation.get("fee_type") == "代理费" else customer_other if allocation.get("fee_type") == "其他费用" else None
            if target is not None:
                target[case_key(allocation)] = target.get(case_key(allocation), 0.0) + abs(float(allocation.get("amount") or 0))
    internal_fee_ids.discard(0)
    fee_titles = dict((await db.execute(select(BusinessRecord.id, BusinessRecord.title).where(
        scalar_in_values(BusinessRecord.id, internal_fee_ids)))).all()) if internal_fee_ids else {}

    def counts_as_agency_income(receipt, allocation) -> bool:
        if allocation.get("is_refund") or allocation.get("fee_type") != "代理费":
            return False
        if not is_internal_payer(receipt.payer_name):
            return True
        key = case_key(allocation)
        return (str(fee_titles.get(_positive_int(allocation.get("fee_id")), "")).startswith("平台代理费")
                and customer_agency.get(key, 0.0) <= 0 and customer_other.get(key, 0.0) > 0)

    incomes = [(receipt, allocation) for receipt in receipts for allocation in receipt.allocations or []
               if isinstance(allocation, dict) and counts_as_agency_income(receipt, allocation)]
    ids = {_positive_int(allocation.get("case_id")) for _, allocation in incomes} - {0}
    serials = {str(allocation.get(key) or "").strip() for _, allocation in incomes for key in ("case_no", "contract_no")} - {""}
    links = [scalar_in_values(BusinessRecord.id, ids)] if ids else []
    if serials:
        links.append(scalar_in_values(BusinessRecord.serial_no, serials))
    records = (await db.execute(select(
        BusinessRecord.id, BusinessRecord.module, BusinessRecord.serial_no, BusinessRecord.customer, BusinessRecord.owner, BusinessRecord.data,
    ).where(BusinessRecord.module.in_({"case", "contract"}), *scope, or_(*links)))).all() if links else []
    by_id = {record.id: record for record in records}
    by_serial = {record.serial_no: record for record in records}

    by_source: dict[str, float] = {}
    by_hearing: dict[str, float] = {}
    by_extra: dict[str, dict[str, float]] = {key: {} for key in (extra_roles or {})}
    total = 0.0
    for receipt, allocation in incomes:
        record = (by_id.get(_positive_int(allocation.get("case_id")))
                  or by_serial.get(str(allocation.get("case_no") or "").strip())
                  or by_serial.get(str(allocation.get("contract_no") or "").strip()))
        if record is None:  # 没关联到案件/合同，或当前账号看不到
            continue
        if _is_test_customer(str(receipt.claimed_customer or record.customer or "")):
            continue
        amount = abs(float(allocation.get("amount") or 0))
        total += amount
        for person in source_people(record):
            by_source[person] = by_source.get(person, 0.0) + amount
        for person in hearing_people(record):
            by_hearing[person] = by_hearing.get(person, 0.0) + amount
        for key, people_of in (extra_roles or {}).items():
            for person in people_of(record):
                by_extra[key][person] = by_extra[key].get(person, 0.0) + amount

    return {"by_source_person": by_source, "by_hearing_lawyer": by_hearing, **by_extra, "total": round(total, 2)}


def performance_rankings(counts: dict, fees: dict | None) -> dict:
    """每组一张图：每人案件数和代理费到账两根柱子，按代理费从高到低前 10 名（18:17 选 B）。

    没有金额权限（fees 为 None）时只给案件数，按案件数排。
    """
    result = {}
    for key in ("by_source_person", "by_hearing_lawyer"):
        case_values = counts.get(key, {})
        fee_values = (fees or {}).get(key, {})
        names = set(case_values) | set(fee_values)
        rows = [{"name": name, "cases": case_values.get(name, 0),
                 "fee": round(fee_values.get(name, 0.0), 2) if fees is not None else None} for name in names]
        rows.sort(key=lambda row: (-(row["fee"] or 0), -row["cases"], row["name"]))
        result[key] = rows[:RANKING_LIMIT]
    return result
