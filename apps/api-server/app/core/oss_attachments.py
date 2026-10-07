"""识别 OSS 附件路径，并为已授权的远程对象生成短时签名地址。"""

import base64
import csv
import hashlib
import hmac
import re
import time
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit

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
