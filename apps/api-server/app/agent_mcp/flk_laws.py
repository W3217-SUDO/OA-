"""智能体从国家法律法规数据库（flk.npc.gov.cn）查找并下载法律法规原文（陶国南 11-02）。

- 只按用户要求查一次、下一次：先按名称搜出候选（名称、制定机关、时效性、公布/施行日期），用户选定后下载 PDF 或 Word；
- 用网站页面自己调用的公开查询和下载接口，不登录、不带凭据、不碰验证码；全进程串行并且两次请求至少间隔 1 秒，
  每人每天限量，避免给网站添负担；
- 下载链接只接受网站返回的官方文件存储地址，文件存到本人个人空间（当前对话），可再另存到案件。
"""
import asyncio
import re
import time
from datetime import date
from urllib.parse import urlsplit

from fastapi import HTTPException
import httpx2

from app.agent_mcp.web_fetch import _FetchTransport
from app.areas.capability_market.connector_transport import PublicHttpsTransport

BASE = "https://flk.npc.gov.cn"
FILE_HOSTS = ("flkoss.obs-bj2.cucloud.cn",)
SEARCH_LIMIT = 10
MAX_FILE_BYTES = 20 * 1024 * 1024
TIMEOUT_SECONDS = 20
MIN_INTERVAL_SECONDS = 1.0
DAILY_SEARCHES = 60
DAILY_DOWNLOADS = 30
VALIDITY = {1: "已废止", 2: "已修改", 3: "现行有效", 4: "尚未生效"}
FORMATS = {"pdf": ("pdf", "application/pdf", b"%PDF"),
           "word": ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", b"PK")}
HEADERS = {"User-Agent": "Mozilla/5.0 OA-Reader", "Referer": BASE + "/search",
           "Content-Type": "application/json;charset=utf-8"}

_lock = asyncio.Lock()
_last_request = 0.0
_usage: dict[tuple[str, str, str], int] = {}


def _count(username: str, kind: str, limit: int) -> None:
    key = (str(date.today()), username, kind)
    for old in [item for item in _usage if item[0] != key[0]]:
        _usage.pop(old, None)
    if _usage.get(key, 0) >= limit:
        label = "查找" if kind == "search" else "下载"
        raise HTTPException(429, f"今天在国家法律法规数据库{label}的次数已到上限（{limit} 次），请明天再试或直接到 flk.npc.gov.cn 下载")
    _usage[key] = _usage.get(key, 0) + 1


class _FileTransport(PublicHttpsTransport):
    def response_limit(self, request):
        return MAX_FILE_BYTES

    async def handle_async_request(self, request):
        if (request.url.host or "").lower() not in FILE_HOSTS:
            raise HTTPException(422, "下载地址不是国家法律法规数据库的官方文件存储，已停止下载")
        return await super().handle_async_request(request)


async def _flk(method: str, path: str, *, params=None, json=None) -> dict:
    """串行调用 flk 接口，两次之间至少间隔 1 秒。"""
    global _last_request
    async with _lock:
        wait = MIN_INTERVAL_SECONDS - (time.monotonic() - _last_request)
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            async with asyncio.timeout(TIMEOUT_SECONDS):
                async with httpx2.AsyncClient(transport=_FetchTransport(), follow_redirects=False, trust_env=False,
                                              timeout=httpx2.Timeout(TIMEOUT_SECONDS), headers=HEADERS) as client:
                    response = await client.request(method, BASE + path, params=params, json=json)
        except TimeoutError:
            raise HTTPException(504, "国家法律法规数据库 20 秒内没有返回，请稍后再试") from None
        except httpx2.HTTPError:
            raise HTTPException(502, "国家法律法规数据库暂时打不开，请稍后再试") from None
        finally:
            _last_request = time.monotonic()
    if response.status_code != 200:
        raise HTTPException(502, f"国家法律法规数据库返回 HTTP {response.status_code}，请稍后再试")
    try:
        payload = response.json()
    except ValueError:
        raise HTTPException(502, "国家法律法规数据库返回的不是数据（网站可能改版或要求验证），请直接到 flk.npc.gov.cn 下载") from None
    if not isinstance(payload, dict) or payload.get("code") != 200:
        raise HTTPException(502, "国家法律法规数据库没有返回结果：" + str((payload or {}).get("msg") or "未知原因")[:100])
    return payload


def _plain(text) -> str:
    return re.sub(r"<[^>]*>", "", str(text or "")).strip()


def _law_id(value) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9A-Za-z]{16,64}", value):
        raise HTTPException(422, "法规编号无效，请先用 flk_search_laws 查找后再选")
    return value


async def search_laws(keyword: str, identity: dict) -> dict:
    keyword = keyword.strip().strip("《》") if isinstance(keyword, str) else ""
    if not keyword or len(keyword) > 100:
        raise HTTPException(422, "请给出法律法规或司法解释的名称（不超过100字）")
    _count(identity["username"], "search", DAILY_SEARCHES)
    # 先按标题精确匹配（网站默认），查不到再模糊匹配。
    for search_type in (1, 2):
        payload = await _flk("POST", "/law-search/search/list", json={
            "searchContent": keyword, "searchType": search_type, "searchRange": 1,
            "pageNum": 1, "pageSize": SEARCH_LIMIT, "flfgCodeId": [], "zdjgCodeId": [], "gbrqYear": [], "orderByParam": {},
        })
        rows = payload.get("rows") or []
        if rows or len(keyword) == 1:
            break
    items = [{
        "law_id": row.get("bbbs"), "title": _plain(row.get("title")), "issuer": row.get("zdjgName") or "",
        "category": row.get("flxz") or "", "validity": VALIDITY.get(row.get("sxx"), "未知"),
        "published_on": row.get("gbrq") or "", "effective_on": row.get("sxrq") or "",
    } for row in rows if isinstance(row, dict) and row.get("bbbs")]
    return {"source": "国家法律法规数据库 flk.npc.gov.cn", "keyword": keyword, "total": payload.get("total") or len(items),
            "items": items,
            "hint": "把候选按 名称｜制定机关｜时效性｜公布日期 列给用户，请用户选定一项和格式（PDF 或 Word）后再调用 flk_download_law；"
                    "同名有多个版本时提醒用户注意时效性。"}


async def download_law(law_id: str, file_format: str, identity: dict, db, *, conversation_id: str) -> dict:
    from app.agent_mcp.artifacts import _generated_metadata, resource_metadata
    from app.core.generated_file_storage import safe_original_name, save_generated_file

    law_id = _law_id(law_id)
    if file_format not in FORMATS:
        raise HTTPException(422, "格式只能是 pdf 或 word")
    extension, content_type, magic = FORMATS[file_format]
    _count(identity["username"], "download", DAILY_DOWNLOADS)
    detail = (await _flk("GET", "/law-search/search/flfgDetails", params={"bbbs": law_id})).get("data") or {}
    files = detail.get("ossFile") or {}
    if not files.get("ossPdfPath" if file_format == "pdf" else "ossWordPath"):
        other = "Word" if file_format == "pdf" else "PDF"
        raise HTTPException(404, f"这部法规在国家法律法规数据库没有{'PDF' if file_format == 'pdf' else 'Word'}版本，可以改下{other}")
    link = (await _flk("GET", "/law-search/download/pc", params={"format": extension, "bbbs": law_id, "fileId": ""})).get("data") or {}
    url = link.get("url")
    if not isinstance(url, str) or urlsplit(url).scheme != "https" or (urlsplit(url).hostname or "").lower() not in FILE_HOSTS:
        raise HTTPException(502, "国家法律法规数据库没有给出可用的下载地址，请稍后再试")
    try:
        async with asyncio.timeout(60):
            async with httpx2.AsyncClient(transport=_FileTransport(), follow_redirects=False, trust_env=False,
                                          timeout=httpx2.Timeout(60), headers={"User-Agent": HEADERS["User-Agent"]}) as client:
                response = await client.get(url)
    except TimeoutError:
        raise HTTPException(504, "文件 60 秒内没有下载完，请稍后再试") from None
    except httpx2.HTTPError:
        raise HTTPException(502, "文件没有下载成功（可能超过 20MB），请直接到 flk.npc.gov.cn 下载") from None
    content = response.content
    if response.status_code != 200 or not content.startswith(magic):
        raise HTTPException(502, "下载到的不是有效的法规文件，请稍后再试")
    title = _plain(detail.get("title")) or "法律法规"
    stamp = str(detail.get("gbrq") or "").replace("-", "")
    name = safe_original_name(f"{title}{'_' + stamp if stamp else ''}.{extension}")
    saved = await save_generated_file(db, identity, name=name, content=content, content_type=content_type,
                                      source_kind="flk_download", conversation_id=conversation_id)
    return {"law": {"title": title, "issuer": detail.get("zdjgName") or "", "validity": VALIDITY.get(detail.get("sxx"), "未知"),
                    "published_on": detail.get("gbrq") or "", "effective_on": detail.get("sxrq") or ""},
            "file": resource_metadata(_generated_metadata(saved["file"])),
            "source": "国家法律法规数据库 flk.npc.gov.cn（电子文本与标准文本不一致时，以标准文本为准）",
            "saved_to": "本人个人空间（当前对话），可在个人空间另存到案件"}
