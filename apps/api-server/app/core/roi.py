"""资金运营情况统计（品牌、律师）：同一套算法，按客户或开庭律师分组（tgn 11-01，BUG20261101001/003）。"""
from datetime import date
from decimal import Decimal, InvalidOperation


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


# 品牌资金运营情况统计（BUG20261101001，tgn 11-01 确认）。
BRAND_ARCHIVED_STATUSES = {"已归档", "亏损归档"}
BRAND_LOSS_STATUSES = {"亏损内审", "亏损审核", "亏损拒绝", "亏损归档"}
# 一审、二审、再审诉讼费，保全费，公证费（含旧系统早期编号）。
BRAND_ADVANCE_FEE_CODES = {"11010020", "11010030", "11010040", "1101010", "1101020", "11010090", "11010050", "1101040"}
BRAND_ADVANCE_FEE_NAMES = {"一审诉讼费", "二审诉讼费", "再审诉讼费", "保全费", "公证费"}
AGENCY_FEE_CODES = {"11020010", "11020020", "11020030", "11020040"}
AGENCY_FEE_NAMES = {"律师代理费", "代理费", "律师咨询费", "律师培训费", "律师见证费"}


def _fee_code(data: dict) -> str:
    legacy = data.get("legacy") if isinstance(data.get("legacy"), dict) else {}
    return str(data.get("case_fee_type_id") or data.get("fee_type_code") or legacy.get("CaseFeeTypeId") or "")


def _fee_case_id(fee, case_by_id, case_by_no):
    data = fee.data or {}
    try:
        case_id = int(data.get("case_id") or data.get("case_record_id") or 0)
    except (TypeError, ValueError):
        case_id = 0
    case = case_by_id.get(case_id) or case_by_no.get(str(data.get("case_no") or ""))
    return case.id if case else None


# 品牌图上显示客户简称（tgn 11-01，BUG20261101002）；没登记简称的按规则自动截短（tgn 16:18 选 B）。
_REGION_PREFIXES = (
    "北京市", "上海市", "天津市", "重庆市", "北京", "上海", "天津", "重庆", "黑龙江", "内蒙古",
    "河北", "山西", "辽宁", "吉林", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南",
    "广东", "广西", "海南", "四川", "贵州", "云南", "陕西", "甘肃", "青海", "宁夏", "新疆", "西藏",
    "杭州", "广州", "深圳", "青岛", "苏州", "南京", "宁波", "厦门", "武汉", "成都", "西安", "无锡", "佛山", "东莞",
)
_COMPANY_SUFFIXES = ("股份有限公司", "有限责任公司", "有限公司", "集团", "公司")


def auto_short_name(name: str, limit: int = 8) -> str:
    """去掉省市名、括号里的内容和公司字样，最多 limit 个字。"""
    import re
    text = re.sub(r"[（(][^）)]*[）)]", "", str(name or "")).strip()
    for prefix in _REGION_PREFIXES:
        if text.startswith(prefix) and len(text) > len(prefix) + 1:
            text = text[len(prefix):].lstrip("省市")
            break
    changed = True
    while changed:
        changed = False
        for suffix in _COMPANY_SUFFIXES:
            if text.endswith(suffix) and len(text) > len(suffix) + 1:
                text, changed = text[: -len(suffix)], True
    return (text or str(name or ""))[:limit]


async def _brand_short_names(names, db) -> dict:
    """客户资料里登记的“客户简称”优先；没有的自动截短。"""
    from sqlalchemy import select as sa_select
    from app.models import BusinessRecord

    found: dict[str, str] = {}
    if names:
        rows = (await db.execute(sa_select(BusinessRecord.title, BusinessRecord.data).where(
            BusinessRecord.module == "customer", BusinessRecord.title.in_(set(names)), BusinessRecord.deleted_at.is_(None),
        ))).all()
        for title, data in rows:
            short = str((data or {}).get("short_name") or (data or {}).get("customer_short_name") or "").strip()
            if short and not found.get(title):
                found[title] = short
    return {name: found.get(name) or auto_short_name(name) for name in names}


BRAND_CONTRACT_TYPE = "框架合作合同"


async def _framework_contract_cases(cases, db):
    """品牌统计只算框架协议客户：只要合同类型为“框架合作合同”的合同下的案件；个案（争议解决）、顾问、其他、非诉项目合同下的不算（tgn 11-01 确认）。"""
    from sqlalchemy import select as sa_select
    from app.models import BusinessRecord

    def contract_id(case):
        data = case.data or {}
        try:
            return int(data.get("contract_record_id") or data.get("contract_id") or 0)
        except (TypeError, ValueError):
            return 0

    ids = {contract_id(case) for case in cases} - {0}
    if not ids:
        return []
    framework = set((await db.scalars(sa_select(BusinessRecord.id).where(
        BusinessRecord.module == "contract", BusinessRecord.id.in_(ids),
        BusinessRecord.data["contract_type"].as_string() == BRAND_CONTRACT_TYPE,
    ))).all())
    return [case for case in cases if contract_id(case) in framework]


async def brand_charts(cases, fees, db, *, group_by="brand"):
    """按品牌（案件客户）算四项：
    1. 平均回款时间 = 已归档、亏损归档案件从垫付款日期到归档日期的平均天数；垫付款日期取官费最早的请款单付款日期，没有请款单取费用通知日期。
    2. 亏损金额 = 亏损阶段案件里诉讼费、保全费、公证费已垫付未到账部分（逐笔，最少 0）的合计。
    3. 回款率（年化）= 回款案件（代理费有到账）的到账代理费 × 15% ÷ 这些案件已垫付官费 ÷ 平均回款时间 × 365。
    4. 亏损率 = 亏损金额 ÷ 全部已付官费。
    """
    from app.core.customer_fee_balance import _cashed_by_fee, _paid_and_first_dates

    cases = await _framework_contract_cases(cases, db)
    case_by_id = {case.id: case for case in cases}
    case_by_no = {case.serial_no: case for case in cases}
    fee_case = {}
    for fee in fees:
        if fee.status in {"已撤销", "已删除", "已作废", "已拒绝"}:
            continue
        if (case_id := _fee_case_id(fee, case_by_id, case_by_no)) is not None:
            fee_case[fee.id] = case_id
    fees = [fee for fee in fees if fee.id in fee_case]
    fee_ids = set(fee_case)
    from app.core.dashboard_list_counts import gather_counts
    # 已付和到账两次查询互不依赖，用独立只读会话并行（报表性能）。
    results = await gather_counts(db, {
        "paid": lambda session: _paid_and_first_dates(fee_ids, session),
        "cashed": lambda session: _cashed_by_fee(fee_ids, session),
    }) if fee_ids else {"paid": ({}, {}), "cashed": {}}
    paid, paid_dates = results["paid"]
    cashed = results["cashed"]
    rows = {case.id: {"official_paid": Decimal(0), "advance_unreceived": Decimal(0), "agency_received": Decimal(0), "first_paid": None}
            for case in cases}
    for fee in fees:
        data = fee.data or {}
        row = rows[fee_case[fee.id]]
        code = _fee_code(data)
        name = str(data.get("fee_type_name") or data.get("expense_subtype") or "")
        fee_paid = paid.get(fee.id, Decimal(0))
        fee_cashed = cashed.get(fee.id, Decimal(0))
        if data.get("fee_type") in {"官方费用", "官费"}:
            row["official_paid"] += fee_paid
            if fee_paid > 0:
                day = _day(paid_dates.get(fee.id)) or _day(data.get("inform_date") or (data.get("legacy") or {}).get("InformDate"))
                if day:
                    row["first_paid"] = min(row["first_paid"] or day, day)
        if code in BRAND_ADVANCE_FEE_CODES or (not code and name in BRAND_ADVANCE_FEE_NAMES):
            row["advance_unreceived"] += max(Decimal(0), fee_paid - fee_cashed)
        if code in AGENCY_FEE_CODES or (not code and (name in AGENCY_FEE_NAMES or data.get("fee_type") == "代理费")):
            row["agency_received"] += fee_cashed

    groups: dict[str, list] = {}
    for case in cases:
        for key in _group_keys(case, group_by):
            groups.setdefault(key, []).append(case)
    charts = [{"title": title, "unit": unit, "items": []} for title, unit in (
        ("资金回款周期统计", "天/案"), ("资金亏损金额统计", "元"),
        ("资金回报率统计", "百分比"), ("资金亏损率统计", "百分比"),
    )]
    warnings = []
    # 只显示有数据的客户，按已垫付官费从多到少排，不限个数，页面上左右拖动查看（tgn 11-01，BUG20261101001）。
    computed = []
    for name, members in groups.items():
        spans = []
        for case in members:
            archived = _day((case.data or {}).get("archived_at"))
            first_paid = rows[case.id]["first_paid"]
            # 归档日期早于垫付日期的（数据先后不对）不算进回款周期（tgn 11-01，BUG20261101003）。
            if case.status in BRAND_ARCHIVED_STATUSES and archived and first_paid and archived >= first_paid:
                spans.append((archived - first_paid).days)
        avg_days = round(sum(spans) / len(spans), 1) if spans else None
        loss = sum((rows[c.id]["advance_unreceived"] for c in members if c.status in BRAND_LOSS_STATUSES), Decimal(0))
        total_paid = sum((rows[c.id]["official_paid"] for c in members), Decimal(0))
        collected = [c for c in members if rows[c.id]["agency_received"] > 0]
        agency = sum((rows[c.id]["agency_received"] for c in collected), Decimal(0))
        collected_paid = sum((rows[c.id]["official_paid"] for c in collected), Decimal(0))
        rate = None
        warning = ""
        if collected_paid and avg_days:
            rate = round(float(agency * Decimal("0.15") / collected_paid / Decimal(str(avg_days)) * 365 * 100), 2)
        elif collected:
            warning = f"{name}：{'没有已垫付官费的回款案件' if not collected_paid else '没有可算回款时间的归档案件'}，资金回报率无法计算"
        values = (avg_days, float(loss), rate, round(float(loss / total_paid * 100), 2) if total_paid else 0)
        if any(value not in (None, 0, 0.0) for value in values):
            computed.append((total_paid, name, values, warning))
    ordered = sorted(computed, key=lambda row: (-row[0], row[1]))
    display = {}
    labels = await _brand_short_names([row[1] for row in ordered], db) if group_by == "brand" else {}
    if group_by != "brand":
        from app.core.formatters import _user_display_map
        users = await _user_display_map({row[1] for row in ordered}, db)
        display = {name: getattr(users.get(name.lower()) or users.get(name), "display_name", None) or name for _t, name, _v, _w in ordered}
    for _total, name, values, warning in ordered:
        label = display.get(name, name)
        item_label = labels.get(name) or label
        for chart, value in zip(charts, values):
            chart["items"].append({"name": label, "label": item_label, "value": value})
        if warning:
            warnings.append(warning.replace(name, label, 1))
    return charts, warnings


def _group_keys(case, group_by: str) -> list[str]:
    """品牌按客户；律师按开庭律师，按文书按律师助理。一个案件有几位就各算一份全额（tgn 11-01 选 A1），没登记的不算。"""
    import re
    if group_by == "brand":
        return [case.customer or "未关联客户"]
    data = case.data or {}
    if group_by == "assistant":
        raw = data.get("assistant_username") or data.get("assistant")
    else:
        raw = data.get("hearing_lawyer_username") or data.get("hearing_lawyers") or data.get("hearing_lawyer")
    values = raw if isinstance(raw, list) else re.split(r"[,，;；、|\s]+", str(raw or ""))
    return list(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


async def operating_charts(cases, fees, view, group_mode, db):
    if view == "brand":
        return await brand_charts(cases, fees, db)
    # 律师资金统计和品牌用同一套算法，按开庭律师（或按文书分组时按律师助理）统计（tgn 11-01，BUG20261101003）。
    return await brand_charts(cases, fees, db, group_by="assistant" if group_mode == "按文书分组统计" else "lawyer")
