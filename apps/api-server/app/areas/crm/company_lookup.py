"""新建客户按关键词从企查查开放平台带出工商信息（501106，陶威 11-02 开通）。

- 凭据：管理员在“系统参数 › API 设置 › 企查查开放平台”粘贴 Key + SecretKey，加密存在 system_configs，不回显、不进日志；
  页面没配时才读服务器私有配置 QCC_APP_KEY / QCC_SECRET_KEY。
- 签名：Header 带 Token、Timespan；Token = MD5(Key + Timespan + SecretKey) 32 位大写，Timespan 为 Unix 时间戳（秒）。
- 接口：模糊搜索 886（FuzzySearch/GetList，每次最多 5 条）、企业工商信息 410（ECIV4/GetBasicDetailsByName，keyword 为
  企业全称或统一社会信用代码，不含电话）。735 工商详情（ECIInfoVerify/GetInfo）含电话但单价 2 元，暂不用。
- 控费：同一关键词结果缓存 7 天，同一企业详情缓存 30 天；每人每天 50 次、全所每天上限可调；每次调用（含命中缓存）都记日志。

官方文档（11-02 核对，以此为准）：
- 模糊搜索 886：https://openapi.qcc.com/dataApi/886
- 企业工商信息 410：https://openapi.qcc.com/dataApi/410
- 企业工商详情 735：https://openapi.qcc.com/dataApi/735
- 请求状态码：https://openapi.qcc.com/services/after/status
  （页面数据来自 https://openapi.qcc.com/API/DataApiDetail/getErrorCodeInfo，下面 QCC_STATUS 照抄）
"""
import base64
import hashlib
import json
import os
import time
from datetime import date, datetime, timedelta, timezone

import httpx
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import current_identity, get_db
from app.models import BusinessRecord, SystemConfig

router = APIRouter()

QCC_BASE = "https://api.qichacha.com"
SEARCH_PATH = "/FuzzySearch/GetList"            # ApiCode 886 企业模糊搜索，每次最多 5 条
DETAIL_PATH = "/ECIV4/GetBasicDetailsByName"    # ApiCode 410 企业工商信息
CREDENTIAL_KEY = "external_credential_qcc"
SETTINGS_KEY = "external_qcc_settings"
SEARCH_CACHE_DAYS, DETAIL_CACHE_DAYS = 7, 30
DEFAULT_USER_DAILY, DEFAULT_TOTAL_DAILY = 50, 500
ABNORMAL_STATUS = ("注销", "吊销", "撤销", "迁出", "停业", "清算")
# 官方请求状态码（https://openapi.qcc.com/services/after/status），200 查询成功、201 查询无结果，其余为错误。
QCC_STATUS = {
    "101": "当前的KEY无效或者还未生效中", "102": "当前KEY已欠费", "103": "当前KEY被暂停使用", "104": "请求KEY异常，请联系管理员", "105": "接口已下线停用",
    "106": "非法请求过多，请联系管理员", "107": "被禁止的IP或者签名错误", "108": "异常请求过多，请联系管理员", "109": "请求超过每日系统限制", "110": "当前相同查询连续出错，请等2小时后重试",
    "111": "接口权限未开通，请联系管理员", "112": "您的账号剩余使用量已不足或已过期", "113": "当前接口已被删除，请重新申请", "114": "当前接口已被禁用，请联系管理员",
    "115": "身份验证错误或者已过期", "116": "请求超过每日（服务期）调用总量限制", "117": "当前不支持的请求参数调用量过多", "118": "当前接口不支持此方式的调用", "119": "您的账号出现异常，请联系管理员",
    "120": "系统流量异常，请稍后再试", "121": "数据不能出境", "122": "请求超过系统并发限制", "123": "您的请求已达未认证权益上限，请及时认证", "124": "系统维护中，暂时无法下单",
    "125": "查询参数错误", "126": "查询参数类型或结构有误", "199": "系统未知错误，请联系技术客服", "200": "查询成功", "201": "查询无结果", "202": "查询参数错误，请检查",
    "203": "系统查询有异常，请联系技术人员", "205": "等待处理中", "207": "请求数据的条目数超过上限（5000）", "208": "此接口不支持此公司类型查询", "209": "企业数量超过上限",
    "213": "参数长度不能小于2", "214": "您还未购买过该接口，请先购买", "215": "不支持的查询关键字", "218": "该企业暂不支持空壳扫描", "219": "该企业暂不支持准入尽调",
    "223": "查询参数模糊，无法获取结果", "224": "查询参数无效",
}
# 管理员能处理的几种，补一句该做什么。
QCC_HINTS = {
    "101": "请在 API 设置里核对 Key", "107": "请在企查查后台把服务器出口 IP 加入白名单，并核对 SecretKey",
    "112": "请到企查查充值或续期", "115": "请核对 Key 和 SecretKey，并确认服务器时间准确",
    "111": "请在企查查开通该接口", "214": "请在企查查购买该接口",
}


# ---------- 凭据 ----------

def _cipher() -> Fernet:
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"oa.external.qcc.v1").derive(settings.secret_key.encode())
    return Fernet(base64.urlsafe_b64encode(key))


def _require_admin(identity: dict) -> None:
    """API 设置只有系统管理员能看能改（陶威 11-02 23:27）。"""
    from app.core.permissions import _require_actual_system_admin
    try:
        _require_actual_system_admin(identity)
    except HTTPException as exc:
        raise HTTPException(403, "API 设置只有系统管理员可以查看和修改") from exc


async def _config(db: AsyncSession, key: str, *, lock: bool = False) -> SystemConfig | None:
    statement = select(SystemConfig).where(SystemConfig.key == key)
    return await db.scalar(statement.with_for_update() if lock else statement)


async def credentials(db: AsyncSession) -> tuple[str, str, str]:
    """返回 (key, secret, 来源)；页面配置优先，其次服务器私有配置。"""
    record = await _config(db, CREDENTIAL_KEY)
    if record and record.value.get("encrypted"):
        try:
            value = json.loads(_cipher().decrypt(record.value["encrypted"].encode()))
            return value["key"], value["secret"], "page"
        except (InvalidToken, ValueError, KeyError) as exc:
            raise HTTPException(409, "企查查凭据解密失败，请管理员重新填写") from exc
    key, secret = os.environ.get("QCC_APP_KEY", "").strip(), os.environ.get("QCC_SECRET_KEY", "").strip()
    if key and secret:
        return key, secret, "server"
    raise HTTPException(409, "企查查接口尚未配置，请管理员在“系统参数 › API 设置”填写")


def _signature(key: str, secret: str) -> dict:
    timespan = str(int(time.time()))
    token = hashlib.md5((key + timespan + secret).encode()).hexdigest().upper()
    return {"Token": token, "Timespan": timespan}


class QccError(HTTPException):
    """企查查返回的业务错误，带上官方状态码，调用方据此判断接口是否开通。"""

    def __init__(self, qcc_status: str):
        super().__init__(502, qcc_error_message(qcc_status))
        self.qcc_status = qcc_status


# 接口没买或没开通（官方状态码 111、113、114、214）：模糊搜索不可用时改用工商信息按全称直接查（陶威 11-03 只开通了 410）。
QCC_NOT_OPEN = {"111", "113", "114", "214"}
EXACT_HINT = "企查查模糊搜索接口未开通，只能按企业全称或统一社会信用代码查，请输入准确全称后再点“查企业”"


async def _qcc_get(path: str, params: dict, key: str, secret: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=15, trust_env=False, follow_redirects=False) as client:
            response = await client.get(QCC_BASE + path, params={"key": key, **params}, headers=_signature(key, secret))
    except httpx.HTTPError as exc:
        raise HTTPException(502, "连接企查查失败，请稍后再试") from exc
    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(502, f"企查查返回异常（HTTP {response.status_code}）") from exc
    status = str(payload.get("Status") or "")
    if status == "200":
        return payload
    if status == "201":
        return {"Status": "201", "Result": None}
    raise QccError(status)


def qcc_error_message(status: str) -> str:
    text = QCC_STATUS.get(status) or str(status or "未知错误")
    hint = QCC_HINTS.get(status)
    return f"企查查返回 {status}：{text}" + (f"（{hint}）" if hint else "")


# ---------- 缓存、限量、日志 ----------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _cache_key(kind: str, keyword: str) -> str:
    return "qcc_c_" + hashlib.sha256(f"{kind}:{keyword}".encode()).hexdigest()[:40]


async def _cached(db: AsyncSession, kind: str, keyword: str):
    record = await _config(db, _cache_key(kind, keyword))
    if record and record.value.get("expires_at", "") > _now().isoformat():
        return record.value.get("data")
    return None


async def _store_cache(db: AsyncSession, kind: str, keyword: str, data, days: int) -> None:
    key = _cache_key(kind, keyword)
    record = await _config(db, key) or SystemConfig(key=key, label="企查查查询缓存", group="外部接口缓存", value={}, description="")
    record.value = {"data": data, "expires_at": (_now() + timedelta(days=days)).isoformat(), "kind": kind}
    db.add(record)


async def limits(db: AsyncSession) -> dict:
    record = await _config(db, SETTINGS_KEY)
    value = record.value if record else {}
    return {"user_daily": int(value.get("user_daily") or DEFAULT_USER_DAILY), "total_daily": int(value.get("total_daily") or DEFAULT_TOTAL_DAILY)}


def _log_key(day: date) -> str:
    return f"qcc_log_{day:%Y%m%d}"


async def _log_record(db: AsyncSession, *, lock: bool = False) -> SystemConfig:
    key = _log_key(date.today())
    record = await _config(db, key, lock=lock)
    if record is None:
        record = SystemConfig(key=key, label="企查查调用日志", group="外部接口日志", value={"entries": []}, description="")
        db.add(record)
        await db.flush()
    return record


async def _check_quota(db: AsyncSession, username: str) -> dict:
    record = await _log_record(db, lock=True)
    paid = [entry for entry in record.value.get("entries", []) if not entry.get("cached") and entry.get("billed", True)]
    quota = await limits(db)
    used_by_user = sum(1 for entry in paid if entry.get("user") == username)
    if used_by_user >= quota["user_daily"]:
        raise HTTPException(429, f"今天的企查查查询次数已用完（每人每天 {quota['user_daily']} 次），请明天再查或手工填写")
    if len(paid) >= quota["total_daily"]:
        raise HTTPException(429, f"全所今天的企查查查询次数已用完（每天 {quota['total_daily']} 次），请手工填写")
    return {"user_remaining": quota["user_daily"] - used_by_user - 1}


async def _log(db: AsyncSession, username: str, kind: str, keyword: str, *, cached: bool, count: int, error: str = "") -> None:
    record = await _log_record(db, lock=True)
    entries = list(record.value.get("entries", []))
    entries.append({"user": username, "at": _now().isoformat(timespec="seconds"), "kind": kind, "keyword": keyword[:60],
                    "cached": cached, "count": count, "billed": not cached and not error, **({"error": error[:120]} if error else {})})
    record.value = {**record.value, "entries": entries}
    db.add(record)


# ---------- 字段整理 ----------

def _abnormal(status: str) -> bool:
    return any(word in (status or "") for word in ABNORMAL_STATUS)


def _organization_type(econ_kind: str) -> str:
    text = econ_kind or ""
    if "个体" in text:
        return "个体工商户"
    if "事业单位" in text:
        return "事业单位"
    if any(word in text for word in ("机关", "社会团体", "社团", "基金会", "民办非企业")):
        return "机关团体"
    if any(word in text for word in ("公司", "企业", "合伙", "独资", "分支机构", "集体", "股份")):
        return "公司企业"
    return ""


def _search_item(row: dict) -> dict:
    status = str(row.get("Status") or "")
    return {"name": row.get("Name") or "", "credit_code": row.get("CreditCode") or row.get("No") or "",
            "legal_person": row.get("OperName") or "", "start_date": str(row.get("StartDate") or "")[:10],
            "status": status, "address": row.get("Address") or "", "abnormal": _abnormal(status)}


ENT_TYPES = {"0": "大陆企业", "1": "社会组织", "4": "事业单位", "7": "医院", "9": "律师事务所", "10": "学校", "11": "机关单位", "-1": "其他"}


def _day(value) -> str:
    return str(value or "")[:10]


def _detail(row: dict) -> dict:
    status = str(row.get("Status") or "")
    contact = row.get("ContactInfo") if isinstance(row.get("ContactInfo"), dict) else {}
    area = row.get("Area") if isinstance(row.get("Area"), dict) else {}
    revoke = row.get("RevokeInfo") if isinstance(row.get("RevokeInfo"), dict) else {}
    names = [item for item in (row.get("OriginalName") or []) if isinstance(item, dict)]
    delegates = [item for item in (row.get("DesignatedRepresentativeList") or []) if isinstance(item, dict)]
    return {
        "name": row.get("Name") or "", "credit_code": row.get("CreditCode") or "",
        "legal_representative": row.get("OperName") or "", "registered_address": row.get("Address") or "",
        "organization_type": _organization_type(str(row.get("EconKind") or "")), "econ_kind": row.get("EconKind") or "",
        "phone": contact.get("PhoneNumber") or row.get("PhoneNumber") or "",
        "registered_capital": row.get("RegistCapi") or "", "established_date": _day(row.get("StartDate")),
        "status": status, "business_scope": row.get("Scope") or "", "registration_authority": row.get("BelongOrg") or "",
        "abnormal": _abnormal(status),
        # 501226：410 本来就返回、以前没存的字段，一并存下（不多调接口）。
        "registration_no": row.get("No") or "", "org_code": row.get("OrgNo") or "",
        "entity_type": ENT_TYPES.get(str(row.get("EntType") or ""), ""), "paid_in_capital": row.get("RecCap") or "",
        "term_start": _day(row.get("TermStart")), "term_end": _day(row.get("TermEnd")), "approved_date": _day(row.get("CheckDate")),
        "former_names": [{"name": item.get("Name") or "", "change_date": _day(item.get("ChangeDate"))} for item in names if item.get("Name")],
        "designated_representatives": [{"partner": item.get("PartnerName") or "", "delegate": item.get("DelegatedName") or ""} for item in delegates],
        "listed": str(row.get("IsOnStock") or "") == "1", "stock_number": row.get("StockNumber") or "", "stock_type": row.get("StockType") or "",
        "province": area.get("Province") or row.get("Province") or "", "city": area.get("City") or "", "county": area.get("County") or "",
        "area_code": row.get("AreaCode") or "",
        "cancel_date": _day(revoke.get("CancelDate")), "cancel_reason": revoke.get("CancelReason") or "",
        "revoke_date": _day(revoke.get("RevokeDate")), "revoke_reason": revoke.get("RevokeReason") or "",
        "qcc_updated_date": _day(row.get("UpdatedDate")),
    }


# 当事人信息窗口、被告基本信息文档按这个顺序显示（空的不显示）。
BUSINESS_FIELDS = [
    ("name", "企业名称"), ("credit_code", "统一社会信用代码"), ("registration_no", "注册号"), ("org_code", "组织机构代码"),
    ("legal_representative", "法定代表人"), ("designated_representatives", "委派代表"), ("econ_kind", "企业类型"),
    ("entity_type", "企业性质"), ("status", "登记状态"), ("established_date", "成立日期"), ("term", "营业期限"),
    ("approved_date", "核准日期"), ("registered_capital", "注册资本"), ("paid_in_capital", "实缴资本"),
    ("registration_authority", "登记机关"), ("region", "所在地区"), ("area_code", "行政区划代码"),
    ("registered_address", "注册地址"), ("phone", "电话"), ("listing", "上市情况"), ("former_names", "曾用名"),
    ("cancel", "注销信息"), ("revoke", "吊销信息"), ("business_scope", "经营范围"), ("qcc_updated_date", "企查查更新日期"),
]


def business_rows(detail: dict) -> list[dict]:
    """把工商信息整理成“栏目 + 内容”，窗口和 Word 文档共用。"""
    def value(key: str) -> str:
        if key == "term":
            start, end = detail.get("term_start") or "", detail.get("term_end") or ""
            return f"{start or '—'} 至 {end or '无固定期限'}" if start or end else ""
        if key == "region":
            return "".join(dict.fromkeys(part for part in (detail.get("province"), detail.get("city"), detail.get("county")) if part))
        if key == "listing":
            return f"已上市（{detail.get('stock_type') or ''} {detail.get('stock_number') or ''}）".replace("（ ", "（").replace(" ）", "）") if detail.get("listed") else ""
        if key == "former_names":
            return "；".join(f"{item['name']}{'（' + item['change_date'] + ' 变更）' if item.get('change_date') else ''}" for item in detail.get("former_names") or [])
        if key == "designated_representatives":
            return "；".join("：".join(part for part in (item.get("partner"), item.get("delegate")) if part) for item in detail.get("designated_representatives") or [])
        if key in ("cancel", "revoke"):
            day, reason = detail.get(f"{key}_date") or "", detail.get(f"{key}_reason") or ""
            return "，".join(part for part in (day, reason) if part)
        return str(detail.get(key) or "")
    return [{"key": key, "label": label, "value": text} for key, label in BUSINESS_FIELDS if (text := value(key))]


# ---------- 查询接口 ----------

async def _require_customer_create(identity: dict, db: AsyncSession) -> None:
    from app.core.permissions import _require_record_module_menu
    await _require_record_module_menu("customer", identity, db, action="新建")


@router.get(f"{settings.api_prefix}/company-lookup/search")
async def search_companies(keyword: str = Query(min_length=2, max_length=60),
                           identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """企查查企业模糊搜索（至少 2 个字），每次最多 5 条；同一关键词 7 天内用缓存，不重复计费。"""
    await _require_customer_create(identity, db)
    keyword = " ".join(keyword.split())
    username = identity["username"]
    cached = await _cached(db, "search", keyword)
    if cached is not None:
        await _log(db, username, "search", keyword, cached=True, count=len(cached))
        await db.commit()
        return {"items": cached, "cached": True}
    key, secret, _ = await credentials(db)
    quota = await _check_quota(db, username)
    try:
        payload = await _qcc_get(SEARCH_PATH, {"searchKey": keyword}, key, secret)
    except HTTPException as exc:
        await _log(db, username, "search", keyword, cached=False, count=0, error=str(exc.detail))
        await db.commit()
        if isinstance(exc, QccError) and exc.qcc_status in QCC_NOT_OPEN:
            return await _exact_candidates(keyword, identity, db)
        raise
    items = [_search_item(row) for row in (payload.get("Result") or []) if isinstance(row, dict)]
    await _store_cache(db, "search", keyword, items, SEARCH_CACHE_DAYS)
    await _log(db, username, "search", keyword, cached=False, count=len(items))
    await db.commit()
    return {"items": items, "cached": False, **quota}


async def _exact_candidates(keyword: str, identity: dict, db: AsyncSession) -> dict:
    """模糊搜索没开通时按全称或信用代码直接查工商信息，查到就作为唯一候选；选中时读缓存，不再计费。"""
    try:
        detail = await company_detail(keyword, identity, db)
    except HTTPException as exc:
        if exc.status_code == 404:
            return {"items": [], "cached": False, "mode": "exact", "hint": EXACT_HINT}
        raise
    item = {"name": detail["name"], "credit_code": detail["credit_code"], "legal_person": detail["legal_representative"],
            "start_date": detail["established_date"], "status": detail["status"], "address": detail["registered_address"],
            "abnormal": detail["abnormal"]}
    return {"items": [item], "cached": detail.get("cached", False), "mode": "exact", "hint": EXACT_HINT}


@router.get(f"{settings.api_prefix}/company-lookup/detail")
async def company_detail(keyword: str = Query(min_length=2, max_length=60, description="企业全称或统一社会信用代码"),
                         identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """企查查企业工商信息；同一企业 30 天内用缓存，不重复计费。"""
    await _require_customer_create(identity, db)
    return await lookup_company(keyword, identity["username"], db)


async def lookup_company(keyword: str, username: str, db: AsyncSession, *, refresh: bool = False, aliases: tuple[str, ...] = ()) -> dict:
    """查企业工商信息（410）：先读缓存，refresh=True 才跳过缓存重新计费查询；
    查到的同时按关键词、企业名称、信用代码和 aliases（如案件里写的当事人名称）存进企业档案（不过期）。"""
    keyword = keyword.strip()
    cached = None if refresh else await _cached(db, "detail", keyword)
    if cached is not None:
        for name in set(aliases) - {""}:
            await _store_profile(db, name, cached)
        await _log(db, username, "detail", keyword, cached=True, count=1)
        await db.commit()
        return {**cached, "cached": True}
    key, secret, _ = await credentials(db)
    await _check_quota(db, username)
    try:
        payload = await _qcc_get(DETAIL_PATH, {"keyword": keyword}, key, secret)
    except HTTPException as exc:
        await _log(db, username, "detail", keyword, cached=False, count=0, error=str(exc.detail))
        await db.commit()
        raise
    result = payload.get("Result")
    if not isinstance(result, dict):
        await _log(db, username, "detail", keyword, cached=False, count=0)
        await db.commit()
        raise HTTPException(404, "企查查没有查到这家企业的工商信息，请手工填写")
    detail = {**_detail(result), "source": "企查查", "queried_at": _now().isoformat(timespec="seconds"), "queried_by": username}
    await _store_cache(db, "detail", keyword, detail, DETAIL_CACHE_DAYS)
    if detail["credit_code"] and detail["credit_code"] != keyword:
        await _store_cache(db, "detail", detail["credit_code"], detail, DETAIL_CACHE_DAYS)
    for name in {keyword, detail["name"], detail["credit_code"], *aliases} - {""}:
        await _store_profile(db, name, detail)
    await _log(db, username, "detail", keyword, cached=False, count=1)
    await db.commit()
    return {**detail, "cached": False}


# ---------- 企业档案（501226） ----------
# 查到的工商信息按名称、信用代码另存一份，不过期：当事人信息窗口直接显示，谁再看都不再扣费，只有“重新查询”才计费。

def _profile_key(keyword: str) -> str:
    return "qcc_p_" + hashlib.sha256(keyword.strip().encode()).hexdigest()[:40]


async def _store_profile(db: AsyncSession, keyword: str, detail: dict) -> None:
    key = _profile_key(keyword)
    record = await _config(db, key) or SystemConfig(key=key, label="企查查企业档案", group="外部接口缓存", value={}, description="")
    record.value = {"data": detail, "keyword": keyword.strip()[:60]}
    db.add(record)


async def company_profile(db: AsyncSession, *keywords: str) -> dict | None:
    """按名称或信用代码取已查过的工商信息：先找企业档案，没有再找 30 天缓存（501226 之前查过的只在缓存里）。"""
    for keyword in [item.strip() for item in keywords if item and item.strip()]:
        record = await _config(db, _profile_key(keyword))
        if record and isinstance(record.value.get("data"), dict):
            return record.value["data"]
    for keyword in [item.strip() for item in keywords if item and item.strip()]:
        cached = await _cached(db, "detail", keyword)
        if isinstance(cached, dict):
            return cached
    return None


async def find_duplicate_customers(db: AsyncSession, credit_code: str, name: str) -> list[dict]:
    """先按统一社会信用代码、再按名称查已有客户；回收站（已删除）里的也算。"""
    conditions = []
    if credit_code.strip():
        conditions.append(BusinessRecord.data["credit_code"].as_string() == credit_code.strip())
    if name.strip():
        conditions.append(or_(BusinessRecord.title == name.strip(), BusinessRecord.customer == name.strip()))
    if not conditions:
        return []
    rows = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "customer", or_(*conditions))
                             .order_by(BusinessRecord.id).execution_options(include_deleted=True))).all()
    code = credit_code.strip()
    rows = sorted(rows, key=lambda row: (0 if code and (row.data or {}).get("credit_code") == code else 1, row.id))
    return [{"id": row.id, "serial_no": row.serial_no, "title": row.title, "deleted": row.deleted_at is not None,
             "matched_by": "统一社会信用代码" if code and (row.data or {}).get("credit_code") == code else "名称"} for row in rows]


@router.get(f"{settings.api_prefix}/company-lookup/duplicates")
async def customer_duplicates(credit_code: str = "", name: str = "",
                              identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """新建客户查重：信用代码优先，其次名称，含回收站。"""
    await _require_customer_create(identity, db)
    return {"items": await find_duplicate_customers(db, credit_code, name)}


# ---------- 管理员：凭据与限额 ----------

class CredentialInput(BaseModel):
    key: str = Field(min_length=8, max_length=128)
    secret: str = Field(min_length=8, max_length=128)


class LimitInput(BaseModel):
    user_daily: int = Field(ge=1, le=1000)
    total_daily: int = Field(ge=1, le=100000)


async def _status(db: AsyncSession) -> dict:
    record = await _config(db, CREDENTIAL_KEY)
    page = bool(record and record.value.get("encrypted"))
    server = bool(os.environ.get("QCC_APP_KEY", "").strip() and os.environ.get("QCC_SECRET_KEY", "").strip())
    value = record.value if record else {}
    log = await _config(db, _log_key(date.today()))
    entries = (log.value.get("entries", []) if log else [])
    return {"configured": page or server, "source": "page" if page else ("server" if server else ""),
            "updated_by": value.get("updated_by", ""), "updated_at": value.get("updated_at", ""),
            "verified_at": value.get("verified_at", ""), "verify_message": value.get("verify_message", ""),
            "limits": await limits(db), "today_billed": sum(1 for entry in entries if entry.get("billed")),
            "today_calls": len(entries)}


# 系统参数 › API 设置：每个外部接口一项，页面按这里的字段画表单；以后接百度等接口在这里加一项并实现同样的 4 个路由。
PROVIDERS = [{
    "id": "qcc", "name": "企查查开放平台", "doc_url": "https://openapi.qcc.com/dataApi/886",
    "usage": "新建客户时“查企业”：输入名称查询，选中后带出工商基本信息",
    "fields": [{"name": "key", "label": "Key（应用 AppKey）"}, {"name": "secret", "label": "SecretKey（密钥）"}],
    "test_note": "测试连接会分别调一次企业模糊搜索（0.10 元）和企业工商信息（0.20 元）", "has_limits": True,
}]


@router.get(f"{settings.api_prefix}/external-credentials")
async def external_credential_providers(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """API 设置：所有外部接口及其配置状态（不回显任何凭据）。"""
    _require_admin(identity)
    return {"items": [{**provider, "status": await _status(db)} for provider in PROVIDERS]}


@router.get(f"{settings.api_prefix}/external-credentials/qcc")
async def qcc_credential_status(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """企查查凭据状态（不回显 Key 和 SecretKey）。"""
    _require_admin(identity)
    return await _status(db)


@router.put(f"{settings.api_prefix}/external-credentials/qcc")
async def save_qcc_credentials(body: CredentialInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """保存企查查 Key + SecretKey（加密存储，不回显、不进日志）。"""
    _require_admin(identity)
    record = await _config(db, CREDENTIAL_KEY, lock=True) or SystemConfig(
        key=CREDENTIAL_KEY, label="企查查开放平台凭据", group="API 设置", value={}, description="加密保存，不回显")
    encrypted = _cipher().encrypt(json.dumps({"key": body.key.strip(), "secret": body.secret.strip()}).encode()).decode()
    record.value = {"encrypted": encrypted, "updated_by": identity["username"], "updated_at": _now().isoformat(timespec="seconds")}
    db.add(record)
    await db.commit()
    return await _status(db)


@router.put(f"{settings.api_prefix}/external-credentials/qcc/limits")
async def save_qcc_limits(body: LimitInput, identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """每人每天、全所每天的企查查查询上限。"""
    _require_admin(identity)
    record = await _config(db, SETTINGS_KEY, lock=True) or SystemConfig(
        key=SETTINGS_KEY, label="企查查查询上限", group="API 设置", value={}, description="")
    record.value = {"user_daily": body.user_daily, "total_daily": body.total_daily}
    db.add(record)
    await db.commit()
    return await _status(db)


@router.post(f"{settings.api_prefix}/external-credentials/qcc/test")
async def test_qcc_connection(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """测试连接：用当前凭据分别调一次模糊搜索和工商信息（各计 1 次费用），只返回各接口是否可用，不返回企业数据。"""
    _require_admin(identity)
    key, secret, source = await credentials(db)
    # 两个接口分别测：模糊搜索（886）、工商信息（410）；工商信息能用就算连通，模糊搜索没开通时“查企业”按全称直接查。
    results = []
    for label, path, params in (("模糊搜索", SEARCH_PATH, {"searchKey": "企查查科技"}),
                                ("工商信息", DETAIL_PATH, {"keyword": "企查查科技股份有限公司"})):
        try:
            await _qcc_get(path, params, key, secret)
            results.append((label, True, "正常"))
        except HTTPException as exc:
            results.append((label, False, str(exc.detail)))
    ok = results[1][1]
    message = "；".join(f"{label}：{text}" for label, _, text in results)
    if ok and not results[0][1]:
        message += "。模糊搜索不可用，“查企业”只能按企业全称或统一社会信用代码查"
    await _log(db, identity["username"], "test", "测试连接", cached=False, count=0, error="" if ok else message)
    record = await _config(db, CREDENTIAL_KEY, lock=True)
    if record is not None:
        record.value = {**record.value, "verified_at": _now().isoformat(timespec="seconds") if ok else record.value.get("verified_at", ""),
                        "verify_message": message}
        db.add(record)
    await db.commit()
    return {"ok": ok, "message": message, "source": source}
