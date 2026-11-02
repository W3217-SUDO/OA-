"""新建客户按关键词从企查查开放平台带出工商信息（501106，陶威 11-02 开通）。

- 凭据：管理员在“智能体设置 › 外部接口凭据”粘贴 Key + SecretKey，加密存在 system_configs，不回显、不进日志；
  页面没配时才读服务器私有配置 QCC_APP_KEY / QCC_SECRET_KEY。
- 签名：Token = MD5(Key + Timespan + SecretKey) 大写，Header 带 Token、Timespan。
- 接口：模糊搜索 886（FuzzySearch/GetList）、企业工商信息 410（ECIV4/GetBasicDetailsByName）。
- 控费：同一关键词结果缓存 7 天，同一企业详情缓存 30 天；每人每天 50 次、全所每天上限可调；每次调用（含命中缓存）都记日志。
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
QCC_MESSAGES = {
    "101": "企查查 Key 无效，请管理员核对凭据", "102": "企查查 Key 已过期", "103": "企查查账户余额不足",
    "104": "企查查接口未开通或无权限", "107": "服务器 IP 不在企查查白名单", "109": "企查查签名校验失败，请核对 SecretKey",
    "112": "企查查调用频率超限，请稍后再试", "201": "企查查没有查到匹配的企业",
}


# ---------- 凭据 ----------

def _cipher() -> Fernet:
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"oa.external.qcc.v1").derive(settings.secret_key.encode())
    return Fernet(base64.urlsafe_b64encode(key))


def _require_admin(identity: dict) -> None:
    from app.agent_permissions import require_agent_settings_management
    require_agent_settings_management(identity)


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
    raise HTTPException(409, "企查查接口尚未配置，请管理员在“智能体设置 › 外部接口凭据”填写")


def _signature(key: str, secret: str) -> dict:
    timespan = str(int(time.time()))
    token = hashlib.md5((key + timespan + secret).encode()).hexdigest().upper()
    return {"Token": token, "Timespan": timespan}


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
    raise HTTPException(502, QCC_MESSAGES.get(status, f"企查查返回错误（{status}）"))


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


def _detail(row: dict) -> dict:
    status = str(row.get("Status") or "")
    contact = row.get("ContactInfo") if isinstance(row.get("ContactInfo"), dict) else {}
    return {
        "name": row.get("Name") or "", "credit_code": row.get("CreditCode") or "",
        "legal_representative": row.get("OperName") or "", "registered_address": row.get("Address") or "",
        "organization_type": _organization_type(str(row.get("EconKind") or "")), "econ_kind": row.get("EconKind") or "",
        "phone": contact.get("PhoneNumber") or row.get("PhoneNumber") or "",
        "registered_capital": row.get("RegistCapi") or "", "established_date": str(row.get("StartDate") or "")[:10],
        "status": status, "business_scope": row.get("Scope") or "", "registration_authority": row.get("BelongOrg") or "",
        "abnormal": _abnormal(status),
    }


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
        raise
    items = [_search_item(row) for row in (payload.get("Result") or []) if isinstance(row, dict)]
    await _store_cache(db, "search", keyword, items, SEARCH_CACHE_DAYS)
    await _log(db, username, "search", keyword, cached=False, count=len(items))
    await db.commit()
    return {"items": items, "cached": False, **quota}


@router.get(f"{settings.api_prefix}/company-lookup/detail")
async def company_detail(keyword: str = Query(min_length=2, max_length=60, description="企业全称或统一社会信用代码"),
                         identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """企查查企业工商信息；同一企业 30 天内用缓存，不重复计费。"""
    await _require_customer_create(identity, db)
    keyword = keyword.strip()
    username = identity["username"]
    cached = await _cached(db, "detail", keyword)
    if cached is not None:
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
    detail = {**_detail(result), "source": "企查查", "queried_at": _now().isoformat(timespec="seconds")}
    await _store_cache(db, "detail", keyword, detail, DETAIL_CACHE_DAYS)
    if detail["credit_code"] and detail["credit_code"] != keyword:
        await _store_cache(db, "detail", detail["credit_code"], detail, DETAIL_CACHE_DAYS)
    await _log(db, username, "detail", keyword, cached=False, count=1)
    await db.commit()
    return {**detail, "cached": False}


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
        key=CREDENTIAL_KEY, label="企查查开放平台凭据", group="外部接口凭据", value={}, description="加密保存，不回显")
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
        key=SETTINGS_KEY, label="企查查查询上限", group="外部接口凭据", value={}, description="")
    record.value = {"user_daily": body.user_daily, "total_daily": body.total_daily}
    db.add(record)
    await db.commit()
    return await _status(db)


@router.post(f"{settings.api_prefix}/external-credentials/qcc/test")
async def test_qcc_connection(identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db)):
    """测试连接：用当前凭据做一次模糊搜索（计 1 次费用），只返回是否连通，不返回企业数据。"""
    _require_admin(identity)
    key, secret, source = await credentials(db)
    ok, message = True, "连接正常"
    try:
        await _qcc_get(SEARCH_PATH, {"searchKey": "企查查科技"}, key, secret)
    except HTTPException as exc:
        ok, message = False, str(exc.detail)
    await _log(db, identity["username"], "test", "测试连接", cached=False, count=0, error="" if ok else message)
    record = await _config(db, CREDENTIAL_KEY, lock=True)
    if record is not None:
        record.value = {**record.value, "verified_at": _now().isoformat(timespec="seconds") if ok else record.value.get("verified_at", ""),
                        "verify_message": message}
        db.add(record)
    await db.commit()
    return {"ok": ok, "message": message, "source": source}
