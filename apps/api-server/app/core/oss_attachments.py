"""识别 OSS 附件路径，并为已授权的远程对象生成短时签名地址。"""

import base64
import csv
import hashlib
import hmac
import re
import time
from email.utils import formatdate
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit

import httpx
from fastapi import HTTPException

from app.config import settings


def oss_attachment_location(item) -> tuple[str, str] | None:
    path = str(item.path or "")
    if not path.startswith("oss://"):
        return None
    bucket, separator, key = path.removeprefix("oss://").partition("/")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", bucket) or not separator or not key:
        raise HTTPException(status_code=409, detail="附件 OSS 路径无效，请核对迁移记录")
    return bucket, key


def _load_credentials() -> tuple[str, str]:
    credentials_file = settings.oss_credentials_file.strip()
    if not credentials_file:
        raise HTTPException(status_code=503, detail="附件已关联 OSS 路径；尚未配置签名读取凭据")
    path = Path(credentials_file).expanduser()
    if not path.is_file():
        raise HTTPException(status_code=503, detail="附件已关联 OSS 路径；签名读取凭据文件不存在")
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            row = next(csv.DictReader(handle), None)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise HTTPException(status_code=503, detail="附件 OSS 签名读取凭据无法读取") from exc
    access_key_id = str((row or {}).get("AccessKeyId") or "").strip()
    access_key_secret = str((row or {}).get("AccessKeySecret") or "").strip()
    if not access_key_id or not access_key_secret:
        raise HTTPException(status_code=503, detail="附件 OSS 签名读取凭据格式无效")
    return access_key_id, access_key_secret


def _endpoint_host() -> tuple[str, str]:
    endpoint = settings.oss_endpoint.strip()
    if not endpoint:
        raise HTTPException(status_code=503, detail="附件 OSS 端点未配置")
    parsed = urlsplit(endpoint if "://" in endpoint else f"https://{endpoint}")
    if parsed.scheme != "https" or not parsed.netloc:
        raise HTTPException(status_code=503, detail="附件 OSS 端点必须使用 HTTPS")
    return parsed.scheme, parsed.netloc.rstrip("/")


def oss_attachment_signed_url(item) -> str | None:
    location = oss_attachment_location(item)
    if location is None:
        return None
    bucket, key = location
    access_key_id, access_key_secret = _load_credentials()
    scheme, endpoint_host = _endpoint_host()
    expires = int(time.time()) + settings.oss_signed_url_expire_seconds
    encoded_key = quote(key, safe="/~")
    resource = f"/{bucket}/{key}"
    string_to_sign = f"GET\n\n\n{expires}\n{resource}"
    signature = base64.b64encode(
        hmac.new(access_key_secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha1).digest()
    ).decode("ascii")
    query = urlencode({"OSSAccessKeyId": access_key_id, "Expires": expires, "Signature": signature})
    return f"{scheme}://{bucket}.{endpoint_host}/{encoded_key}?{query}"


def oss_attachment_preview_kind(item) -> str | None:
    if oss_attachment_location(item) is None:
        return None
    suffix = Path(str(item.original_name or "")).suffix.lower()
    content_type = str(item.content_type or "").lower()
    if content_type.startswith("image/") or suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}:
        return "image"
    if content_type == "application/pdf" or suffix == ".pdf":
        return "pdf"
    if suffix == ".docx":
        return "docx"
    if suffix in {".xls", ".xlsx"}:
        return "xlsx"
    return "unsupported"


def office_revision_key(attachment_id: int, session_id: str, version: str) -> str:
    """只在显式授权的独立前缀生成不可变版本键。"""
    prefix = settings.oss_office_version_prefix.strip().rstrip("/")
    if not prefix or prefix.startswith("/") or any(part in {"", ".", ".."} for part in prefix.split("/")):
        raise HTTPException(status_code=503, detail="Office OSS 新版本写入前缀未配置或格式无效")
    if not re.fullmatch(r"[a-f0-9]{32}", session_id) or not re.fullmatch(r"[a-f0-9]{64}", version):
        raise HTTPException(status_code=422, detail="Office 文件版本标识无效")
    return f"{prefix}/{attachment_id}/{session_id}/{version}.docx"


async def put_office_revision(bucket: str, key: str, content: bytes, content_type: str) -> None:
    """用原 OSS 凭据写入私有新对象，服务端禁止覆盖已有键。"""
    access_key_id, access_key_secret = _load_credentials()
    scheme, host = _endpoint_host()
    date_header = formatdate(usegmt=True)
    checksum = base64.b64encode(hashlib.md5(content, usedforsecurity=False).digest()).decode("ascii")
    canonical_headers = "x-oss-forbid-overwrite:true\nx-oss-object-acl:private\n"
    signing = f"PUT\n{checksum}\n{content_type}\n{date_header}\n{canonical_headers}/{bucket}/{key}"
    signature = base64.b64encode(hmac.new(access_key_secret.encode(), signing.encode(), hashlib.sha1).digest()).decode("ascii")
    headers = {
        "Authorization": f"OSS {access_key_id}:{signature}", "Date": date_header,
        "Content-MD5": checksum, "Content-Type": content_type,
        "x-oss-forbid-overwrite": "true", "x-oss-object-acl": "private",
    }
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=False, trust_env=False) as client:
            response = await client.put(f"{scheme}://{bucket}.{host}/{quote(key, safe='/~')}", headers=headers, content=content)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Office OSS 新版本上传失败，原附件未修改") from exc
    # 同一内容重试只允许命中已有不可变键，调用方必须回读并核对实际 SHA-256。
    if response.status_code not in {200, 201, 409}:
        raise HTTPException(status_code=502, detail=f"Office OSS 新版本写入被拒绝（HTTP {response.status_code}），原附件未修改")
