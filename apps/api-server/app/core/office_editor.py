"""自部署 ONLYOFFICE 的配置、签名和受控文件传输。"""

import hashlib
import io
import zipfile
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote, urlsplit

import httpx
import jwt
from fastapi import HTTPException

from app.config import settings

MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def office_configuration_enabled() -> bool:
    public = settings.onlyoffice_public_url.rstrip("/")
    internal = settings.onlyoffice_internal_url.rstrip("/")
    callback = settings.onlyoffice_callback_base_url.rstrip("/")
    for value, schemes in ((public, {"https"}), (internal, {"http", "https"}), (callback, {"https"})):
        parsed = urlsplit(value)
        if parsed.scheme not in schemes or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            return False
    return len(settings.onlyoffice_jwt_secret) >= 32


def office_settings() -> tuple[str, str, str]:
    if not office_configuration_enabled():
        raise HTTPException(status_code=503, detail="ONLYOFFICE 服务地址或签名密钥未正确配置")
    return (settings.onlyoffice_public_url.rstrip("/"), settings.onlyoffice_internal_url.rstrip("/"),
            settings.onlyoffice_callback_base_url.rstrip("/"))


def office_token(payload: dict) -> str:
    return jwt.encode(payload, settings.onlyoffice_jwt_secret, algorithm="HS256")


async def office_command(payload: dict) -> int:
    """命令成功仅表示请求已受理，保存结果必须由签名回调确认。"""
    _public, internal, _callback = office_settings()
    signed = {**payload, "exp": datetime.now(timezone.utc) + timedelta(seconds=60)}
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False, trust_env=False) as client:
            response = await client.post(f"{internal}/command", json={"token": office_token(signed)})
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Office 关闭保存命令结果未知，编辑锁保留，请勿销毁编辑器") from exc
    if response.status_code != 200 or len(response.content) > 65536:
        raise HTTPException(status_code=502, detail="Office 关闭保存命令返回异常，编辑锁保留")
    try:
        result = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Office 关闭保存命令响应不是有效 JSON") from exc
    if not isinstance(result, dict) or type(result.get("error")) is not int or result.get("key") != payload["key"]:
        raise HTTPException(status_code=502, detail="Office 关闭保存命令未绑定当前文档")
    return result["error"]


def verify_callback(body: dict, authorization: str) -> dict:
    office_settings()
    # 正文签名绑定顶层字段，请求头签名绑定 payload；正文存在签名时不能降级验证。
    body_signed = "token" in body
    token = body["token"] if body_signed else (
        authorization.removeprefix("Bearer ") if authorization.startswith("Bearer ") else ""
    )
    if not isinstance(token, str) or not token:
        raise HTTPException(status_code=401, detail="Office 回调缺少签名")
    try:
        signed = jwt.decode(token, settings.onlyoffice_jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Office 回调签名无效或已过期") from exc
    payload = signed if body_signed else signed.get("payload")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=401, detail="Office 回调签名正文无效")
    unsigned = {key: value for key, value in body.items() if key != "token"}
    if any(key not in payload or payload[key] != value for key, value in unsigned.items()):
        raise HTTPException(status_code=401, detail="Office 回调正文与签名不一致")
    if "key" not in payload or "status" not in payload:
        raise HTTPException(status_code=401, detail="Office 回调签名未绑定文档及状态")
    return payload


def validate_document(content: bytes) -> str:
    if not content or len(content) > MAX_DOCUMENT_BYTES:
        raise HTTPException(status_code=413, detail="Word 文件为空或超过 20MB")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            entries = archive.infolist()
            names = {entry.filename for entry in entries}
            if not {"[Content_Types].xml", "word/document.xml"}.issubset(names):
                raise ValueError("not a DOCX package")
            if any(entry.flag_bits & 1 for entry in entries) or sum(entry.file_size for entry in entries) > 200 * 1024 * 1024:
                raise ValueError("unsupported DOCX package")
            types = archive.read("[Content_Types].xml")
            if b"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml" not in types:
                raise ValueError("not a DOCX document")
    except (zipfile.BadZipFile, KeyError, OSError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail="文件不是有效的 DOCX 文档，原附件未修改") from exc
    return hashlib.sha256(content).hexdigest()


def check_editor_download_url(url: str) -> None:
    public, internal, _callback = office_settings()
    parsed = urlsplit(url)
    if parsed.username or parsed.password or parsed.fragment:
        raise HTTPException(status_code=422, detail="Office 输出地址无效")
    decoded_path = unquote(parsed.path)
    if "\\" in decoded_path or any(part in {".", ".."} for part in decoded_path.split("/")):
        raise HTTPException(status_code=422, detail="Office 输出地址包含非法路径")
    for base in (public, internal):
        allowed = urlsplit(base)
        if (parsed.scheme, parsed.netloc) == (allowed.scheme, allowed.netloc) and parsed.path.startswith(allowed.path.rstrip("/") + "/cache/files/"):
            return
    raise HTTPException(status_code=422, detail="Office 输出地址不属于已配置的自部署服务")


async def download_document(url: str) -> bytes:
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=False, trust_env=False) as client:
            async with client.stream("GET", url) as response:
                if response.status_code != 200:
                    raise HTTPException(status_code=502, detail=f"文档服务读取失败（HTTP {response.status_code}）")
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > MAX_DOCUMENT_BYTES:
                        raise HTTPException(status_code=413, detail="文档服务返回文件超过 20MB")
                return bytes(content)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="文档服务读取失败，原附件未修改") from exc


def document_ticket(case_id: int, item_id: int, session: dict) -> str:
    return jwt.encode({
        "purpose": "onlyoffice-document", "case_id": case_id, "attachment_id": item_id,
        "session_id": session["id"], "user": session["user"], "version": session["source_version"],
        "exp": datetime.now(timezone.utc) + timedelta(seconds=settings.onlyoffice_document_token_seconds),
    }, settings.secret_key, algorithm="HS256")
