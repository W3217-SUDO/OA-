"""隔离的 CODE 地址配置与受控 WOPI discovery。"""

import asyncio
import re
import time
from urllib.parse import urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree

import httpx
from fastapi import HTTPException

from app.config import settings

_discovery_cache: tuple[tuple, float, dict] | None = None
_discovery_lock = asyncio.Lock()


def validated_url(value: str, *, origin_only: bool = False) -> str:
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Office 地址端口无效") from exc
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or "\\" in value or any(part in {".", ".."} for part in parsed.path.split("/"))
            or any(char.isspace() for char in value) or (port is not None and port <= 0)):
        raise ValueError("Office 地址必须是无凭据、无查询参数的 HTTP(S) 地址")
    if origin_only and parsed.path not in {"", "/"}:
        raise ValueError("Office origin 不能包含路径")
    return value.rstrip("/")


def origin(value: str) -> str:
    parsed = urlsplit(value)
    return f"{parsed.scheme}://{parsed.netloc}"


def editor_configuration() -> dict:
    if not settings.office_editor_enabled:
        raise HTTPException(status_code=503, detail="LibreOffice 在线编辑尚未启用")
    try:
        server = validated_url(settings.code_server_url)
        browser = validated_url(settings.code_browser_url)
        wopi = validated_url(settings.office_wopi_base_url, origin_only=True)
        frontend = validated_url(settings.office_frontend_origin, origin_only=True)
        trusted = {validated_url(value, origin_only=True) for value in settings.office_trusted_origins}
        if not {origin(server), origin(browser), wopi, frontend}.issubset(trusted):
            raise ValueError("Office 地址必须逐一列入 OFFICE_TRUSTED_ORIGINS")
        if len(settings.office_wopi_token_secret) < 32:
            raise ValueError("Office WOPI 签名密钥至少需要 32 字符")
        if settings.app_env == "production" and any(urlsplit(value).scheme != "https" for value in (browser, frontend)):
            raise ValueError("正式环境的 Office 浏览器与前端地址必须使用 HTTPS")
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"server": server, "browser": browser, "wopi": wopi, "frontend": frontend, "trusted": trusted}


def office_validation_case_allowed(record) -> bool:
    codes = settings.office_editor_validation_case_codes
    return not codes or (record is not None and record.module == "case" and record.serial_no in codes)


def office_attachment_editable(item, record=None) -> bool:
    from app.core.constants import AI_SPACE_CATEGORY
    if not office_validation_case_allowed(record):
        return False
    if settings.office_editor_validation_case_codes and record.id != item.record_id:
        return False
    if item.category == AI_SPACE_CATEGORY or item.is_locked:
        return False
    if not settings.office_editor_enabled or not str(item.original_name).lower().endswith(".docx"):
        return False
    try:
        editor_configuration()
    except HTTPException:
        return False
    from app.core.oss_attachments import oss_attachment_location
    if oss_attachment_location(item) is not None:
        prefix = settings.office_oss_write_prefix.strip().rstrip("/")
        return bool(settings.oss_credentials_file and prefix and not prefix.startswith("/")
                    and all(part not in {"", ".", ".."} for part in prefix.split("/")))
    return True


async def discovery(*, refresh: bool = False) -> dict:
    global _discovery_cache
    config = editor_configuration()
    cache_key = (config["server"], config["browser"], tuple(sorted(config["trusted"])))
    async with _discovery_lock:
        if not refresh and _discovery_cache and _discovery_cache[0] == cache_key and time.monotonic() < _discovery_cache[1]:
            return _discovery_cache[2]
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=False, trust_env=False) as client:
                async with client.stream("GET", config["server"] + "/hosting/discovery") as response:
                    if response.status_code != 200:
                        raise HTTPException(status_code=502, detail="CODE discovery 未返回成功响应")
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        if len(body) + len(chunk) > 1024 * 1024:
                            raise HTTPException(status_code=502, detail="CODE discovery 超过大小限制")
                        body.extend(chunk)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="CODE discovery 无法连接") from exc
        try:
            if b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
                raise ValueError("discovery 不允许外部实体")
            root = ElementTree.fromstring(body)
            action = next(node for node in root.iter("action") if node.get("name") == "edit" and node.get("ext") == "docx")
            urlsrc = re.sub(r"<[^<>]*>", "", action.attrib["urlsrc"])
            parsed = urlsplit(urlsrc)
            if origin(urlsrc) not in config["trusted"] or parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
                raise ValueError("discovery 编辑地址不在可信 origin 中")
            if not parsed.path.startswith(("/browser/", "/loleaflet/")) or "\\" in parsed.path or ".." in parsed.path.split("/"):
                raise ValueError("discovery 编辑路径无效")
            proof = root.find("proof-key")
            if proof is None or not proof.get("modulus") or not proof.get("exponent"):
                raise ValueError("CODE discovery 未提供 WOPI proof 公钥")
            result = {"path": parsed.path, "query": parsed.query, "proof": dict(proof.attrib)}
        except (ElementTree.ParseError, KeyError, StopIteration, ValueError) as exc:
            raise HTTPException(status_code=502, detail=f"CODE discovery 无效：{exc}") from exc
        _discovery_cache = (cache_key, time.monotonic() + 300, result)
        return result


def editor_url(info: dict, session_id: str) -> str:
    config = editor_configuration()
    browser = urlsplit(config["browser"])
    wopi_src = f"{config['wopi']}{settings.api_prefix}/office/wopi/files/{session_id}"
    query = info["query"].rstrip("&")
    query = (query + "&" if query else "") + urlencode({"WOPISrc": wopi_src, "lang": "zh-CN"})
    return urlunsplit((browser.scheme, browser.netloc, browser.path.rstrip("/") + info["path"], query, ""))
