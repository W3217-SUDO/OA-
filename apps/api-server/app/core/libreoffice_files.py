"""完整 DOCX 二进制传输与不可变版本存储，不重写 Word 文档结构。"""

import asyncio
import hashlib
import io
import os
import tempfile
import zipfile
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException, Request

from app.config import settings
from app.core.constants import UPLOAD_ROOT
from app.core.oss_attachments import (
    oss_attachment_location,
    oss_attachment_signed_url,
    oss_editor_revision_key,
    oss_put_editor_revision,
)
from app.core.storage import _attachment_storage_path

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def validate_docx(content: bytes) -> str:
    if not content or len(content) > settings.office_editor_max_file_bytes:
        raise HTTPException(status_code=413, detail="DOCX 为空或超过在线编辑大小限制")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            entries = archive.infolist()
            names = {entry.filename for entry in entries}
            if not {"[Content_Types].xml", "word/document.xml"}.issubset(names) or "word/vbaProject.bin" in names:
                raise ValueError("不是无宏 DOCX 文件")
            if any(entry.flag_bits & 1 for entry in entries) or sum(entry.file_size for entry in entries) > 200 * 1024 * 1024:
                raise ValueError("DOCX 加密或解压体积过大")
            if archive.getinfo("[Content_Types].xml").file_size > 1024 * 1024:
                raise ValueError("DOCX 内容类型声明过大")
            if b"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml" not in archive.read("[Content_Types].xml"):
                raise ValueError("DOCX 内容类型不匹配")
    except (zipfile.BadZipFile, KeyError, OSError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail="文件不是有效的 DOCX，原附件未修改") from exc
    return hashlib.sha256(content).hexdigest()


async def read_put_body(request: Request) -> bytes:
    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > settings.office_editor_max_file_bytes:
            raise HTTPException(status_code=413, detail="WOPI 文件超过大小限制")
        content.extend(chunk)
    return bytes(content)


def _read_local(path: Path) -> bytes:
    with path.open("rb") as handle:
        content = handle.read(settings.office_editor_max_file_bytes + 1)
    if len(content) > settings.office_editor_max_file_bytes:
        raise HTTPException(status_code=413, detail="附件超过在线编辑大小限制")
    return content


async def read_document(item) -> bytes:
    location = oss_attachment_location(item)
    if location is None:
        path = _attachment_storage_path(item)
        if path is None:
            raise HTTPException(status_code=404, detail="附件文件不存在")
        return await asyncio.to_thread(_read_local, path)
    signed_url = oss_attachment_signed_url(item)
    parsed = urlsplit(signed_url)
    if parsed.scheme != "https" or parsed.username or parsed.password:
        raise HTTPException(status_code=503, detail="OSS 签名下载地址无效")
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=False, trust_env=False) as client:
            async with client.stream("GET", signed_url) as response:
                if response.status_code != 200:
                    raise HTTPException(status_code=502, detail=f"OSS 文档读取失败（HTTP {response.status_code}）")
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(content) + len(chunk) > settings.office_editor_max_file_bytes:
                        raise HTTPException(status_code=413, detail="OSS 文档超过在线编辑大小限制")
                    content.extend(chunk)
                return bytes(content)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="OSS 文档下载失败") from exc


def revision_path(item, session: dict, version: str) -> str:
    location = oss_attachment_location(item)
    if location is not None:
        if session.get("scope") == "personal":
            folder = session["revision_folder"]
            return f"oss://{location[0]}/{folder}/office-versions/{session['file_id']}/{session['id']}/{version}.docx"
        return f"oss://{location[0]}/{oss_editor_revision_key(item.id, session['id'], version)}"
    return str(UPLOAD_ROOT / "libreoffice" / str(item.id) / session["id"] / f"{version}.docx")


def _write_local_revision(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".pending-", delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        except Exception:
            handle.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        try:
            os.link(temporary, path)
        except FileExistsError:
            if _read_local(path) != content:
                raise HTTPException(status_code=409, detail="不可变文件键已存在且内容不一致")
    finally:
        temporary.unlink(missing_ok=True)


async def write_revision(path: str, content: bytes) -> None:
    target = SimpleNamespace(path=path, original_name="revision.docx", stored_name=Path(path).name)
    location = oss_attachment_location(target)
    if location is None:
        await asyncio.to_thread(_write_local_revision, Path(path), content)
        return
    created = await oss_put_editor_revision(*location, content, DOCX_CONTENT_TYPE)
    if not created and await read_document(target) != content:
        raise HTTPException(status_code=409, detail="OSS 不可变文件键已存在且实际内容不一致")
