from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable

import pypdfium2 as pdfium
from docx import Document
from app.pdf_runtime import serialized_pdfium


MAX_TEXT_CHARS = 36_000
MAX_PDF_PAGES = 40
MAX_VISUAL_PAGES = 4
IMAGE_SUFFIXES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".csv", ".json", ".xml", ".html", ".htm"}


@dataclass(frozen=True)
class AttachmentReading:
    status: str
    text: str
    page_count: int
    images: tuple[dict[str, str], ...] = ()
    cache_hit: bool = False
    cache_status: str = "disabled"
    content_sha256: str = ""
    content_size: int = 0


def _clip(value: str, limit: int = MAX_TEXT_CHARS) -> str:
    normalized = "\n".join(line.rstrip() for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n")).strip()
    return normalized if len(normalized) <= limit else normalized[:limit] + "\n[正文过长，已截取前部内容]"


def _image_data_url(content: bytes, mime_type: str) -> str:
    return f"data:{mime_type};base64,{base64.b64encode(content).decode('ascii')}"


def _read_docx(path: Path) -> AttachmentReading:
    document = Document(path)
    lines = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
            if any(cells):
                lines.append(" | ".join(cells))
    text = _clip("\n".join(lines))
    return AttachmentReading(status="parsed" if text else "empty", text=text, page_count=0)


def _read_text(path: Path) -> AttachmentReading:
    content = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            text = content.decode(encoding)
            return AttachmentReading(status="parsed", text=_clip(text), page_count=0)
        except UnicodeDecodeError:
            continue
    return AttachmentReading(status="unsupported_encoding", text="", page_count=0)


def _render_pdf_page(page: object, page_number: int) -> dict[str, str]:
    bitmap = page.render(scale=1.35)
    try:
        image = bitmap.to_pil().convert("RGB")
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=82, optimize=True)
        return {"page": str(page_number), "mime_type": "image/jpeg", "data_url": _image_data_url(buffer.getvalue(), "image/jpeg")}
    finally:
        bitmap.close()


@serialized_pdfium
def _read_pdf(path: Path) -> AttachmentReading:
    document = pdfium.PdfDocument(path)
    text_parts: list[str] = []
    images: list[dict[str, str]] = []
    try:
        page_count = len(document)
        for index in range(min(page_count, MAX_PDF_PAGES)):
            page = document[index]
            try:
                text_page = page.get_textpage()
                try:
                    page_text = (text_page.get_text_range() or "").strip()
                finally:
                    text_page.close()
                if page_text:
                    text_parts.append(f"[第 {index + 1} 页]\n{page_text}")
                if len(page_text) < 40 and len(images) < MAX_VISUAL_PAGES:
                    images.append(_render_pdf_page(page, index + 1))
            finally:
                page.close()
            if sum(len(item) for item in text_parts) >= MAX_TEXT_CHARS:
                break
    finally:
        document.close()
    text = _clip("\n\n".join(text_parts))
    status = "parsed" if text else ("visual" if images else "empty")
    return AttachmentReading(status=status, text=text, page_count=page_count, images=tuple(images))


def _read_uncached(path: Path, name: str) -> AttachmentReading:
    path = Path(path)
    suffix = Path(name or path.name).suffix.lower()
    if suffix == ".pdf":
        return _read_pdf(path)
    if suffix == ".docx":
        return _read_docx(path)
    if suffix in TEXT_SUFFIXES:
        return _read_text(path)
    if suffix in IMAGE_SUFFIXES:
        content = path.read_bytes()
        return AttachmentReading(
            status="visual",
            text="",
            page_count=1,
            images=({"page": "1", "mime_type": IMAGE_SUFFIXES[suffix], "data_url": _image_data_url(content, IMAGE_SUFFIXES[suffix])},),
        )
    return AttachmentReading(status="unsupported", text="", page_count=0)


@lru_cache(maxsize=256)
def _read_cached(path_text: str, name: str, size: int, modified_ns: int) -> AttachmentReading:
    del size, modified_ns
    return _read_uncached(Path(path_text), name)


def _material_cache_root() -> Path:
    """返回不暴露给附件下载路由的持久化材料解析缓存目录。"""
    from app.config import settings
    from app.core.constants import UPLOAD_ROOT

    configured = settings.personal_agent_root.strip()
    root = Path(configured).expanduser()
    if not configured:
        root = UPLOAD_ROOT.parent / "private-agent-material-cache"
    elif not root.is_absolute():
        root = UPLOAD_ROOT.parent / root / "material-reading-cache"
    else:
        root = root / "material-reading-cache"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _file_sha256(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _cache_key(scope: str, attachment_id: int, name: str, digest: str, size: int) -> str:
    payload = f"{scope.strip().casefold()}\x00{int(attachment_id)}\x00{name}\x00{digest}\x00{size}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _reading_payload(reading: AttachmentReading) -> dict:
    return {
        "status": reading.status,
        "text": reading.text,
        "page_count": reading.page_count,
        "images": list(reading.images),
    }


def _from_cache_payload(payload: dict, digest: str, size: int) -> AttachmentReading:
    return AttachmentReading(
        status=str(payload.get("status") or "empty"),
        text=str(payload.get("text") or ""),
        page_count=int(payload.get("page_count") or 0),
        images=tuple(payload.get("images") or ()),
        cache_hit=True,
        cache_status="hit",
        content_sha256=digest,
        content_size=size,
    )


def read_cached_attachment(
    path: Path,
    name: str,
    *,
    cache_scope: str,
    attachment_id: int,
    parser: Callable[[Path], AttachmentReading] | None = None,
) -> AttachmentReading:
    """按用户、附件 ID、内容哈希和大小复用解析结果。

    缓存只保存成功解析的正文、页数和扫描页图片；权限校验仍由调用方完成。
    源文件内容变化会生成新的键，临时 OSS 下载路径不会影响命中。
    """
    digest, size = _file_sha256(path)
    key = _cache_key(cache_scope, attachment_id, name, digest, size)
    try:
        cache_path = _material_cache_root() / f"{key}.json"
    except OSError:
        reading = (parser or (lambda source: _read_uncached(source, name)))(path)
        return AttachmentReading(
            status=reading.status, text=reading.text, page_count=reading.page_count,
            images=reading.images, cache_hit=False, cache_status="failed",
            content_sha256=digest, content_size=size,
        )
    try:
        with cache_path.open("r", encoding="utf-8") as handle:
            cached = json.load(handle)
        if (cached.get("version") == 1 and cached.get("scope") == cache_scope.strip().casefold()
                and cached.get("attachment_id") == int(attachment_id)
                and cached.get("name") == name and cached.get("sha256") == digest
                and cached.get("size") == size):
            return _from_cache_payload(cached["reading"], digest, size)
    except (FileNotFoundError, OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError, KeyError):
        pass

    reading = (parser or (lambda source: _read_uncached(source, name)))(path)
    reading = AttachmentReading(
        status=reading.status, text=reading.text, page_count=reading.page_count,
        images=reading.images, cache_hit=False, cache_status="not_cached",
        content_sha256=digest, content_size=size,
    )
    if reading.status not in {"parsed", "visual"} or not (reading.text or reading.images):
        return reading
    document = {
        "version": 1, "scope": cache_scope.strip().casefold(), "attachment_id": int(attachment_id),
        "name": name, "sha256": digest, "size": size, "reading": _reading_payload(reading),
    }
    temporary = cache_path.with_name(f".{cache_path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(document, handle, ensure_ascii=False, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, cache_path)
        return AttachmentReading(
            status=reading.status, text=reading.text, page_count=reading.page_count,
            images=reading.images, cache_hit=False, cache_status="stored",
            content_sha256=digest, content_size=size,
        )
    except OSError:
        temporary.unlink(missing_ok=True)
        return AttachmentReading(
            status=reading.status, text=reading.text, page_count=reading.page_count,
            images=reading.images, cache_hit=False, cache_status="failed",
            content_sha256=digest, content_size=size,
        )


def read_attachment(
    path: Path,
    name: str,
    *,
    cache_scope: str = "",
    attachment_id: int | None = None,
    parser: Callable[[Path], AttachmentReading] | None = None,
) -> AttachmentReading:
    if cache_scope and attachment_id is not None:
        return read_cached_attachment(path, name, cache_scope=cache_scope, attachment_id=attachment_id, parser=parser)
    stat = path.stat()
    return _read_cached(str(path.resolve()), name, stat.st_size, stat.st_mtime_ns)
