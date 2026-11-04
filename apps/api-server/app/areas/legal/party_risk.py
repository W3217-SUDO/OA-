"""当事人风险信息（501226 尽职调查报告的风险部分，陶威 11-03 定先用火山企业风险库试，企查查 736 接入保留）。

两个数据源整理成同一个结构，报告只认这个结构：
    {"source": "volc"|"qcc736", "source_label": str, "queried_at": iso, "flags": {标记: bool},
     "sections": {key: {"count": int, "amount": float|None, "items": [{字段: 值}]}}}
每类只存最新的 ITEM_LIMIT 条明细，条数和金额按全量算。
"""
import csv
import io
import json
import re
from datetime import date

ITEM_LIMIT = 20

# 类目：(标题, [(字段, 表头)])；报告按这个顺序出表。
SECTIONS = {
    "executed": ("被执行人", [("date", "立案日期"), ("court", "执行法院"), ("case_no", "案号"), ("amount", "执行标的(元)")]),
    "dishonest": ("失信被执行人", [("date", "立案日期"), ("case_no", "案号"), ("court", "执行法院"), ("performance", "履行情况")]),
    "restricted": ("限制高消费", [("date", "立案日期"), ("court", "法院"), ("reason", "案由"), ("applicant", "申请人")]),
    "end_execution": ("终结本次执行", [("date", "立案日期"), ("end_date", "终本日期"), ("court", "法院"), ("target", "执行标的(元)"), ("unfulfilled", "未履行(元)")]),
    "bankruptcy": ("破产重整", [("date", "公开日期"), ("court", "法院"), ("type", "案件类型"), ("applicant", "申请人")]),
    "auction": ("司法拍卖", [("date", "拍卖时间"), ("item", "标的物"), ("unit", "处置单位")]),
    "filing": ("立案信息", [("date", "立案日期"), ("court", "法院"), ("reason", "案由"), ("role", "身份"), ("other", "对方")]),
    "court_notice": ("开庭公告", [("date", "开庭日期"), ("court", "法院"), ("reason", "案由"), ("role", "身份")]),
    "judgement": ("裁判文书", [("date", "裁判日期"), ("title", "标题"), ("court", "法院"), ("role", "身份")]),
    "abnormal": ("经营异常", [("date", "列入日期"), ("reason", "列入原因"), ("office", "决定机关"), ("removed", "移出")]),
    "penalty": ("行政处罚", [("date", "处罚日期"), ("doc_no", "文书号"), ("reason", "事由"), ("office", "处罚机关"), ("amount", "罚款(元)")]),
    "own_tax": ("欠税", [("date", "发布日期"), ("category", "税种"), ("amount", "欠税金额(元)"), ("balance", "欠税余额(元)")]),
    "serious_illegal": ("严重违法", [("date", "列入日期"), ("reason", "列入原因"), ("office", "决定机关")]),
    "pledge": ("股权出质", [("date", "登记日期"), ("pledgor", "出质人"), ("pledgee", "质权人"), ("amount", "出质股权"), ("status", "状态")]),
    "mortgage": ("动产抵押", [("date", "登记日期"), ("amount", "被担保债权(元)"), ("status", "状态"), ("office", "登记机关")]),
    "liquidation": ("清算", [("leader", "清算组负责人"), ("member", "清算组成员")]),
    "partners": ("股东", [("name", "股东"), ("percent", "持股比例"), ("capital", "认缴出资")]),
    "employees": ("主要人员", [("name", "姓名"), ("job", "职务")]),
}
LITIGATION = ("filing", "court_notice", "judgement")
ENFORCEMENT = ("executed", "dishonest", "restricted", "end_execution", "bankruptcy", "auction")
OPERATION = ("abnormal", "penalty", "own_tax", "serious_illegal", "pledge", "mortgage", "liquidation")
SOURCE_LABELS = {"volc": "火山方舟专业数据集·企业风险库", "qcc736": "企查查企业风险扫描"}


def _day(value) -> str:
    text = str(value or "").strip()
    return text[:10] if re.match(r"\d{4}-\d{2}-\d{2}", text) else ""


def _money(value) -> float | None:
    try:
        return float(str(value).replace(",", "")) if str(value or "").strip() not in ("", "None", "null") else None
    except ValueError:
        return None


def _json(value):
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value) if value else None
    except (TypeError, ValueError):
        return None


def _names(value, skip: str = "") -> str:
    """[{"name": ...}] 或 ["..."] 转成“甲、乙”，去掉本企业。"""
    items = _json(value)
    if not isinstance(items, list):
        return str(value or "").strip()
    names = [str(item.get("name") if isinstance(item, dict) else item).strip() for item in items]
    return "、".join(name for name in names if name and name != skip)


def _section(items: list[dict], *, amount_key: str = "", latest: bool = False) -> dict:
    """同一内容的多条（数据源对同一案件、同一笔欠税重复公示）只算一条；latest=True 时金额取最新一条（欠税余额），否则累加。"""
    unique = {}
    for item in items:
        unique.setdefault(json.dumps({k: v for k, v in item.items() if k != "date"} if latest else item, ensure_ascii=False, sort_keys=True), item)
    items = sorted(unique.values(), key=lambda item: str(item.get("date") or item.get("end_date") or ""), reverse=True)
    amount = None
    if amount_key:
        values = [value for item in items if (value := _money(item.get(amount_key))) is not None]
        amount = (values[0] if latest else round(sum(values), 2)) if values else None
    return {"count": len(items), "amount": amount, "items": items[:ITEM_LIMIT]}


# ---------- 火山企业风险库 ----------

def csv_rows(text: str) -> list[dict]:
    """火山 CSV 表头是“中文说明(english_key)”，按括号里的英文键取值。"""
    reader = csv.reader(io.StringIO(text.lstrip("﻿")))
    header = next(reader, [])
    keys = [(found[-1] if (found := re.findall(r"\(([A-Za-z_0-9]+)\)\s*$", column)) else column) for column in header]
    return [dict(zip(keys, row)) for row in reader]


# 火山“司法诉讼信息”里按案件统计的条数（比 CSV 逐条明细准：同一案件会有多条执行记录）
JUDICIAL_COUNTS = {"executed": "作为被执行人的案件数", "dishonest": "失信被执行人案件数", "restricted": "限制高消费案件数",
                   "end_execution": "终本案件总数", "bankruptcy": "破产重整总数", "auction": "司法拍卖案件数",
                   "filing": "立案总案件数", "court_notice": "开庭公告总数", "judgement": "裁判文书总数"}


def normalize_volc(summary: dict, judicial: list[dict], risks: list[dict], *, queried_at: str, judicial_summary: dict | None = None) -> dict:
    name = str(summary.get("企业名称") or "").strip()
    buckets: dict[str, dict[str, dict]] = {key: {} for key in SECTIONS}

    def put(key: str, ident: str, item: dict) -> None:
        if ident and ident not in buckets[key]:
            buckets[key][ident] = item

    for row in judicial:
        if row.get("company_executed_id"):
            detail = _json(row.get("company_executed_content_details")) or {}
            put("executed", row["company_executed_id"], {"date": _day(detail.get("executed_start_date")), "court": detail.get("executed_court") or "",
                                                         "case_no": detail.get("executed_case_no") or row.get("case_no") or "",
                                                         "amount": _money(detail.get("executed_amount"))})
        if row.get("dishonest_id"):
            detail = _json(row.get("dishonest_content_details")) or {}
            put("dishonest", row["dishonest_id"], {"date": _day(detail.get("start_date") or detail.get("dishonest_start_date")),
                                                   "case_no": detail.get("doc_no") or detail.get("dishonest_doc_no") or "",
                                                   "court": detail.get("court") or detail.get("dishonest_court") or "",
                                                   "performance": detail.get("performance") or detail.get("dishonest_performance") or ""})
        if row.get("sumptuary_restricted_consumption_id"):
            detail = _json(row.get("sumptuary_restricted_consumption_details")) or {}
            put("restricted", row["sumptuary_restricted_consumption_id"], {
                "date": _day(detail.get("limit_consume_start_date")), "court": detail.get("limit_consume_court") or "",
                "reason": detail.get("limit_consume_case_reason") or "", "applicant": _names(detail.get("limit_consume_applicant_name"))})
        if row.get("end_execution_case_id"):
            detail = _json(row.get("end_execution_case_content_detail")) or {}
            put("end_execution", row["end_execution_case_id"], {
                "date": _day(detail.get("end_execution_case_filing_date")), "end_date": _day(detail.get("end_execution_end_date")),
                "court": detail.get("end_execution_court") or "", "target": _money(detail.get("end_execution_enforcement_target")),
                "unfulfilled": _money(detail.get("end_execution_unfulfilled_amount"))})
        if row.get("bankruptcy_case_id"):
            put("bankruptcy", row["bankruptcy_case_id"], {"date": _day(row.get("bankruptcy_publish_date")), "court": row.get("bankruptcy_court") or "",
                                                         "type": row.get("bankruptcy_case_type") or "", "applicant": _names(row.get("bankruptcy_applicant"), name)})
        if row.get("judicial_auction_id"):
            put("auction", row["judicial_auction_id"], {"date": _day(row.get("judicial_auction_time")), "item": (row.get("judicial_auction_item_desc") or "")[:80],
                                                       "unit": row.get("judicial_auction_disposal_unit") or ""})
        if row.get("filing_id"):
            role = row.get("filing_party_role_name") or ""
            other = row.get("filing_plaintiff") if "被" in role else row.get("filing_defendant")
            put("filing", row["filing_id"], {"date": _day(row.get("filing_filing_time")), "court": row.get("filing_court") or "",
                                            "reason": row.get("filing_case_reason") or "", "role": role, "other": _names(other, name)})
        if row.get("court_notice_id"):
            put("court_notice", row["court_notice_id"], {"date": _day(row.get("court_notice_hearing_date")), "court": row.get("court_notice_court") or "",
                                                        "reason": row.get("court_notice_case_reason") or "", "role": row.get("court_notice_party_role_name") or ""})
        if row.get("judgement_doc_id"):
            put("judgement", row["judgement_doc_id"], {"date": _day(row.get("judgement_date")), "title": row.get("judgement_doc_title") or "",
                                                      "court": row.get("judgement_court_name") or "", "role": row.get("judgement_party_role_name") or ""})
    for row in risks:
        kind, ident = row.get("risk_type") or "", row.get("id") or row.get("source_id") or ""
        if row.get("is_delete") == "1":
            continue
        if kind == "abnormal":
            put("abnormal", ident, {"date": _day(row.get("abnormal_put_date")), "reason": row.get("abnormal_put_reason") or "",
                                    "office": row.get("abnormal_put_department") or "",
                                    "removed": f"{_day(row.get('abnormal_remove_date'))} {row.get('abnormal_remove_reason') or ''}".strip()})
        elif kind == "punish":
            put("penalty", ident, {"date": _day(row.get("punish_decision_date")), "doc_no": row.get("punish_punish_number") or "",
                                   "reason": row.get("punish_reason") or row.get("punish_illegal_type") or "",
                                   "office": row.get("punish_department_name") or "", "amount": _money(row.get("punish_penalty_amount"))})
        elif kind == "own_tax":
            put("own_tax", ident, {"date": _day(row.get("own_tax_publish_date")), "category": row.get("own_tax_tax_category") or "",
                                   "amount": _money(row.get("own_tax_amount")), "balance": _money(row.get("own_tax_balance"))})
        elif kind == "illegal":
            put("serious_illegal", ident, {"date": _day(row.get("illegal_put_date")), "reason": row.get("illegal_put_reason") or "",
                                           "office": row.get("illegal_put_department") or ""})
        elif kind == "pledge":
            put("pledge", ident, {"date": _day(row.get("pledge_reg_date")), "pledgor": row.get("pledge_pledgor") or "",
                                  "pledgee": row.get("pledge_pledgee") or "", "amount": row.get("pledge_equity") or "", "status": row.get("pledge_status") or ""})
        elif kind == "mortgage":
            put("mortgage", ident, {"date": _day(row.get("mortgage_reg_date")), "amount": _money(row.get("mortgage_amount")),
                                    "status": row.get("mortgage_status") or "", "office": row.get("mortgage_reg_department") or ""})
        elif kind == "liquidation":
            put("liquidation", ident, {"leader": row.get("liquidation_manager") or "", "member": row.get("liquidation_member") or ""})
        elif kind == "bankruptcy":
            put("bankruptcy", ident, {"date": _day(row.get("bankruptcy_risk_date")), "court": row.get("bankruptcy_court_name") or "",
                                      "type": row.get("bankruptcy_case_type") or "", "applicant": row.get("bankruptcy_applicant") or ""})
    # 被执行金额不汇总：同一案件恢复执行等会有多条记录，加总会重复。
    amounts = {"end_execution": "unfulfilled", "penalty": "amount", "own_tax": "balance", "mortgage": "amount"}
    flags = {label: str(summary.get(key)) == "1" for label, key in (
        ("失信", "是否有失信记录，1有，0无"), ("欠税", "是否有欠税记录，1有，0无"),
        ("经营异常", "是否有经营异常记录，1有，0无"), ("税收违法", "是否有税收违法记录，1有，0无"))}
    sections = {key: _section(list(items.values()), amount_key=amounts.get(key, ""), latest=key == "own_tax")
                for key, items in buckets.items() if items}
    for key, field in JUDICIAL_COUNTS.items():
        try:
            official = int((judicial_summary or {}).get(field) or 0)
        except (TypeError, ValueError):
            continue
        if official and key in sections:
            sections[key]["count"] = official
    return {"source": "volc", "source_label": SOURCE_LABELS["volc"], "queried_at": queried_at, "name": name,
            "credit_code": summary.get("统一社会信用代码") or "", "flags": flags,
            "industry": "／".join(part for part in (summary.get("一级行业名称"), summary.get("二级行业名称")) if part),
            "sections": sections}


# ---------- 企查查 736 企业风险扫描 ----------

def normalize_qcc736(result: dict, *, queried_at: str) -> dict:
    def rows(key: str) -> list[dict]:
        value = result.get(key)
        return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []

    sections = {
        "executed": [{"date": _day(item.get("Liandate")), "court": item.get("ExecuteGov") or "", "case_no": item.get("Anno") or "",
                      "amount": _money(item.get("Biaodi"))} for item in rows("ZhiXingItems")],
        "dishonest": [{"date": _day(item.get("Liandate")), "case_no": item.get("Anno") or "", "court": item.get("Executegov") or "",
                       "performance": item.get("Executestatus") or ""} for item in rows("ShiXinItems")],
        "abnormal": [{"date": _day(item.get("AddDate")), "reason": item.get("AddReason") or "", "office": item.get("DecisionOffice") or "",
                      "removed": f"{_day(item.get('RemoveDate'))} {item.get('RomoveReason') or ''}".strip()} for item in rows("Exceptions")],
        "penalty": [{"date": _day(item.get("PenaltyDate")), "doc_no": item.get("DocNo") or "", "reason": item.get("PenaltyType") or "",
                     "office": item.get("OfficeName") or "", "amount": None} for item in rows("Penalty")],
        "pledge": [{"date": _day(item.get("RegDate")), "pledgor": item.get("Pledgor") or "", "pledgee": item.get("Pledgee") or "",
                    "amount": item.get("PledgedAmount") or "", "status": item.get("Status") or ""} for item in rows("Pledge")],
        "mortgage": [{"date": _day(item.get("RegisterDate")), "amount": _money(item.get("DebtSecuredAmount")), "status": item.get("Status") or "",
                      "office": item.get("RegisterOffice") or ""} for item in rows("MPledge")],
        "partners": [{"name": item.get("StockName") or "", "percent": item.get("StockPercent") or "", "capital": item.get("ShouldCapi") or ""}
                     for item in rows("Partners")],
        "employees": [{"name": item.get("Name") or "", "job": item.get("Job") or ""} for item in rows("Employees")],
    }
    liquidation = result.get("Liquidation")
    if isinstance(liquidation, dict) and (liquidation.get("Leader") or liquidation.get("Member")):
        sections["liquidation"] = [{"leader": liquidation.get("Leader") or "", "member": liquidation.get("Member") or ""}]
    amounts = {"executed": "amount", "mortgage": "amount"}
    return {"source": "qcc736", "source_label": SOURCE_LABELS["qcc736"], "queried_at": queried_at, "name": result.get("Name") or "",
            "credit_code": result.get("CreditCode") or "", "flags": {"失信": bool(sections["dishonest"])}, "industry": "",
            "sections": {key: _section(items, amount_key=amounts.get(key, "")) for key, items in sections.items() if items}}


# ---------- 能不能执行到 ----------

def _yuan(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value / 10000:,.2f} 万元" if value >= 10000 else f"{value:,.2f} 元"


def enforceability(risk: dict) -> tuple[str, list[str]]:
    """按公开的执行、失信、经营风险数据判断胜诉后能不能执行到：结论一句 + 依据几条。"""
    sections = risk.get("sections") or {}
    count = lambda key: (sections.get(key) or {}).get("count", 0)  # noqa: E731
    amount = lambda key: (sections.get(key) or {}).get("amount")  # noqa: E731
    reasons = []
    if count("bankruptcy"):
        reasons.append(f"有破产重整记录 {count('bankruptcy')} 条：进入破产程序后个别执行中止，应向管理人申报债权。")
    if count("dishonest") or risk.get("flags", {}).get("失信"):
        reasons.append(f"被列为失信被执行人 {count('dishonest')} 条。" if count("dishonest") else "被列为失信被执行人。")
    if count("end_execution"):
        unfulfilled = _yuan(amount("end_execution"))
        reasons.append(f"终结本次执行 {count('end_execution')} 件{f'，未履行合计 {unfulfilled}' if unfulfilled else ''}：法院已查无可供执行财产。")
    if count("restricted"):
        reasons.append(f"被限制高消费 {count('restricted')} 次。")
    if count("executed"):
        reasons.append(f"作为被执行人的案件 {count('executed')} 件。")
    if count("auction"):
        reasons.append(f"有司法拍卖 {count('auction')} 次，名下财产已被处置。")
    if count("own_tax"):
        balance = _yuan(amount("own_tax"))
        reasons.append(f"有欠税公告 {count('own_tax')} 条{f'，最新欠税余额 {balance}' if balance else ''}，税款优先于普通债权。")
    active_pledge = [item for item in (sections.get("pledge") or {}).get("items", []) if "无效" not in str(item.get("status"))]
    if active_pledge:
        reasons.append(f"有有效的股权出质 {len(active_pledge)} 条，股权已设质押。")
    if count("mortgage"):
        reasons.append(f"有动产抵押 {count('mortgage')} 条，抵押物上有优先受偿的债权。")
    if count("abnormal"):
        reasons.append(f"被列入经营异常名录 {count('abnormal')} 次。")
    if risk.get("flags", {}).get("税收违法") and not count("serious_illegal"):
        reasons.append("风险库标记有税收违法记录。")
    severe = [label for label, hit in (("破产", count("bankruptcy")), ("失信", count("dishonest") or risk.get("flags", {}).get("失信")),
                                       ("终本", count("end_execution"))) if hit]
    if severe:
        conclusion = (f"执行风险高：已有{'、'.join(severe)}记录，胜诉后很可能执行不到。起诉前应先查清财产线索，"
                      "考虑诉前或诉讼财产保全，或追加股东等责任主体。")
    elif count("restricted") or count("executed") >= 3:
        conclusion = "执行风险较高：已有多起被执行或限制高消费记录，偿债能力不足，建议同时申请财产保全。"
    elif count("executed") or count("own_tax") or active_pledge or count("mortgage"):
        conclusion = "有一定执行风险：存在被执行、欠税或财产设押记录，建议起诉时关注财产保全。"
    else:
        conclusion = "公开数据中未发现被执行、失信、限高、终本、破产记录，执行风险较低。"
    return conclusion, reasons


def item_text(key: str, item: dict) -> list[str]:
    """一条明细按类目的列顺序转成表格单元格文字。"""
    cells = []
    for field, _header in SECTIONS[key][1]:
        value = item.get(field)
        cells.append(f"{value:,.2f}" if isinstance(value, float) else str(value or ""))
    return cells


def stale(risk: dict, days: int = 30) -> bool:
    queried = _day(risk.get("queried_at"))
    return not queried or (date.today() - date.fromisoformat(queried)).days > days


# ---------- 查询与存档 ----------
# 数据源开关：系统配置 party_risk_provider = {"provider": "volc" | "qcc736" | "off"}，默认火山（陶威 11-04 定先用火山试，
# 企查查企业风险扫描 736 接入保留，买了以后把开关改成 qcc736 即可）。查到的结果整理后按名称、信用代码存档，30 天内再生成报告直接用。
PROVIDER_KEY = "party_risk_provider"
RISK_DAYS = 30
VOLC_QUERY = "{name} 企业风险：司法诉讼、失信被执行、被执行、限制高消费、终本、经营异常、行政处罚、欠税"
QCC736_PATH = "/ECIInfoOverview/GetInfo"
MAX_CSV_BYTES = 40 * 1024 * 1024


def _risk_key(keyword: str) -> str:
    import hashlib
    return "risk_p_" + hashlib.sha256(keyword.strip().encode()).hexdigest()[:40]


async def provider(db) -> str:
    from sqlalchemy import select
    from app.models import SystemConfig
    record = await db.scalar(select(SystemConfig).where(SystemConfig.key == PROVIDER_KEY))
    value = record.value if record is not None and isinstance(record.value, dict) else {}
    return value.get("provider") if value.get("provider") in ("volc", "qcc736", "off") else "volc"


async def stored_risk(db, *keywords: str) -> dict | None:
    from sqlalchemy import select
    from app.models import SystemConfig
    for keyword in [item.strip() for item in keywords if item and item.strip()]:
        record = await db.scalar(select(SystemConfig).where(SystemConfig.key == _risk_key(keyword)))
        if record is not None and isinstance((record.value or {}).get("data"), dict):
            return record.value["data"]
    return None


async def _store_risk(db, keywords: list[str], risk: dict) -> None:
    from sqlalchemy import select
    from app.models import SystemConfig
    for keyword in dict.fromkeys(item.strip() for item in keywords if item and item.strip()):
        key = _risk_key(keyword)
        record = await db.scalar(select(SystemConfig).where(SystemConfig.key == key)) or SystemConfig(
            key=key, label="当事人风险档案", group="外部接口缓存", value={}, description="")
        record.value = {"data": risk, "keyword": keyword[:60]}
        db.add(record)


async def _download_csv(url: str) -> list[dict]:
    import httpx
    from fastapi import HTTPException
    if not str(url or "").startswith("https://datapro.hqd.cn-beijing.volces.com/"):
        return []
    chunks, size = [], 0
    async with httpx.AsyncClient(timeout=httpx.Timeout(20, read=90), follow_redirects=True, trust_env=False) as client:
        async with client.stream("GET", url) as response:
            if response.status_code != 200:
                raise HTTPException(502, f"火山风险库明细下载失败（{response.status_code}）")
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > MAX_CSV_BYTES:
                    raise HTTPException(502, "火山风险库明细太大，下载中止")
                chunks.append(chunk)
    return csv_rows(b"".join(chunks).decode("utf-8", errors="replace"))


def _volc_item(payload, name: str, credit_code: str) -> dict | None:
    """在返回里找本企业那一条（名称或信用代码对得上）。"""
    found = []

    def walk(value):
        if isinstance(value, dict):
            if isinstance(value.get("企业风险信息"), dict):
                found.append(value)
                return
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    walk(payload)
    for item in found:
        info = item["企业风险信息"]
        if (credit_code and info.get("统一社会信用代码") == credit_code) or info.get("企业名称") == name:
            return item
    return found[0] if len(found) == 1 and not credit_code else None


async def _fetch_volc(db, name: str, credit_code: str) -> dict:
    from fastapi import HTTPException
    from app.cloud_agent import config as cloud_config, harness
    _record, value = await cloud_config.load(db)
    settings = cloud_config.resolve(value)
    if not settings.plan_key:
        raise HTTPException(409, "火山专业数据集未配置（智能体设置 › 云端智能体 › Agent Plan Key）")
    result = await harness.datapro(settings.plan_key, {"query": VOLC_QUERY.format(name=name)}, max_chars=2_000_000)
    if result.get("isError") or result.get("truncated"):
        raise HTTPException(502, "火山风险库查询失败")
    try:
        payload = json.loads(result.get("result") or "")
    except ValueError as exc:
        raise HTTPException(502, "火山风险库返回格式无法识别") from exc
    item = _volc_item(payload, name, credit_code)
    if item is None:
        raise HTTPException(404, "火山风险库没有查到这家企业")
    judicial = await _download_csv(item.get("司法诉讼全量数据下载地址"))
    risks = await _download_csv(item.get("企业风险信息全量数据下载地址"))
    from datetime import datetime
    return normalize_volc(item["企业风险信息"], judicial, risks, queried_at=datetime.now().astimezone().isoformat(timespec="seconds"),
                          judicial_summary=item.get("司法诉讼信息") if isinstance(item.get("司法诉讼信息"), dict) else None)


async def _fetch_qcc736(db, name: str, credit_code: str, username: str) -> dict:
    from fastapi import HTTPException
    from datetime import datetime
    from app.areas.crm import company_lookup as qcc
    key, secret, _ = await qcc.credentials(db)
    await qcc._check_quota(db, username)
    keyword = credit_code or name
    try:
        payload = await qcc._qcc_get(QCC736_PATH, {"searchKey": keyword}, key, secret)
    except HTTPException as exc:
        await qcc._log(db, username, "risk736", keyword, cached=False, count=0, error=str(exc.detail))
        raise
    result = payload.get("Result")
    if not isinstance(result, dict):
        raise HTTPException(404, "企查查企业风险扫描没有查到这家企业")
    await qcc._log(db, username, "risk736", keyword, cached=False, count=1)
    return normalize_qcc736(result, queried_at=datetime.now().astimezone().isoformat(timespec="seconds"))


async def risk_for(db, *, name: str, credit_code: str, username: str, keywords: list[str]) -> tuple[dict | None, str]:
    """生成尽调报告用的风险数据：30 天内查过的直接用；否则按开关查一次（火山 12 AFP/次，企查查 736 6 元/家）并存档。
    查不到或失败时报告照样生成，风险部分写明原因。返回 (风险数据或 None, 没有数据时的说明)。"""
    from fastapi import HTTPException
    source = await provider(db)
    if source == "off":
        return None, "风险扫描接口未开通"
    stored = await stored_risk(db, credit_code, name, *keywords)
    if stored and stored.get("source") == source and not stale(stored, RISK_DAYS):
        return stored, ""
    try:
        risk = await (_fetch_volc(db, name, credit_code) if source == "volc" else _fetch_qcc736(db, name, credit_code, username))
    except HTTPException as exc:
        if stored:
            return stored, ""
        return None, f"风险数据查询失败（{exc.detail}）"
    await _store_risk(db, [credit_code, name, *keywords], risk)
    await db.commit()
    return risk, ""
