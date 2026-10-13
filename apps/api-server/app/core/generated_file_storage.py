"""个人与案件共用的私有 OSS 生成文件存储，失败保留持久写入计划。"""

import asyncio
import hashlib
from pathlib import PurePosixPath, PureWindowsPath
from types import SimpleNamespace
import unicodedata
from uuid import uuid4

from fastapi import HTTPException
import httpx
from sqlalchemy import select
from app.config import settings

from app.core.generated_file_records import FILE_MODULE, generated_file_item, generated_storage_endpoint, resolve_generated_scope
from app.core.oss_attachments import (
    _load_credentials, oss_attachment_location, oss_attachment_signed_url, oss_put_editor_revision,
)
from app.data_models.documents import FileAttachment
from app.data_models.records import BusinessRecord


MAX_GENERATED_BYTES = 20 * 1024 * 1024


def safe_original_name(name: str) -> str:
    value = str(name or "").strip()
    if (not value or len(value) > 255 or value in {".", ".."}
            or PurePosixPath(value).name != value or PureWindowsPath(value).name != value
            or any(char in value for char in '\\/:*?"<>|')
            or any(unicodedata.category(char).startswith("C") for char in value)):
        raise HTTPException(422, "生成文件名无效，不能包含路径或控制字符")
    return value


def _read_local_bytes(path, max_bytes: int) -> bytes:
    with path.open("rb") as handle:
        content = handle.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(413, "生成文件超过读取大小限制")
    return content


async def read_generated_bytes(attachment, *, max_bytes: int = MAX_GENERATED_BYTES) -> bytes:
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    if oss_attachment_location(attachment) is None:
        from app.core.storage import _attachment_storage_path

        path = _attachment_storage_path(attachment)
        if path is None:
            raise HTTPException(404, "生成文件实体不存在")
        return await asyncio.to_thread(_read_local_bytes, path, max_bytes)
    url = oss_attachment_signed_url(attachment, endpoint=getattr(attachment, "oss_endpoint", None))
    try:
        async with httpx.AsyncClient(timeout=60, trust_env=False, follow_redirects=False) as client:
            async with client.stream("GET", url) as response:
                if response.status_code != 200:
                    raise HTTPException(502, f"AI 文件 OSS 读取失败（HTTP {response.status_code}）")
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(content) + len(chunk) > max_bytes:
                        raise HTTPException(413, "生成文件超过读取大小限制")
                    content.extend(chunk)
                return bytes(content)
    except httpx.HTTPError as exc:
        raise HTTPException(502, "AI 文件 OSS 读取失败") from exc


async def _mark_failure(db, record_id: int, error: BaseException, *, attempted: bool) -> str:
    await db.rollback()
    record = await db.get(BusinessRecord, record_id)
    if record is None:
        raise HTTPException(503, "AI 文件保存失败且写入计划无法读取，请人工核对") from error
    if record.status == "available":
        return "available"
    status = "uncertain" if attempted else "failed"
    reason = str(error.detail) if isinstance(error, HTTPException) and isinstance(error.detail, str) else f"文件保存未完成（{type(error).__name__}），请人工核对"
    record.status = status
    record.data = {**record.data, "error": reason}
    await db.commit()
    return status


async def save_generated_file(
    db, identity: dict, *, name: str, content: bytes, content_type: str, source_kind: str,
    conversation_id: str | None = None, source_request_id: str | None = None,
    case_record=None, attachment=None, on_available=None,
) -> dict:
    name = safe_original_name(name)
    if not isinstance(content, bytes) or not content or len(content) > MAX_GENERATED_BYTES:
        raise HTTPException(413, "生成文件为空或超过20MB")
    if (not content_type or len(content_type) > 128 or "\r" in content_type or "\n" in content_type
            or not source_kind or len(source_kind) > 64):
        raise HTTPException(422, "生成文件类型或来源标识无效")
    _load_credentials(settings.ai_oss_credentials_file)
    generated_storage_endpoint()
    scope = await resolve_generated_scope(db, identity, case_record=case_record)
    original = None
    if scope.case_id is not None:
        from app.core.constants import AI_SPACE_CATEGORY
        from app.core.permissions import (
            _require_case_action, _require_case_attachment_upload_access, _require_case_detail_write_access,
        )

        if attachment is not None:
            await _require_case_detail_write_access(case_record, identity, db)
            await _require_case_action(identity, db, "case.document.manage")
            if attachment.record_id != scope.case_id or attachment.category != AI_SPACE_CATEGORY:
                raise HTTPException(403, "生成文件版本不属于当前案件 AI 草稿")
            original = (attachment.id, attachment.path, attachment.size, attachment.original_name)
        else:
            await _require_case_attachment_upload_access(case_record, identity, db)
    elif attachment is not None:
        raise HTTPException(422, "个人空间保存不能覆盖既有附件")
    file_id = uuid4().hex
    digest = hashlib.sha256(content).hexdigest()
    key = f"{scope.folder}/{file_id}/{digest}/{name}"
    path = f"oss://{scope.bucket}/{key}"
    if len(path) > 512:
        raise HTTPException(422, "真实目录及文件名过长，超出附件路径长度限制")
    record = BusinessRecord(
        module=FILE_MODULE, serial_no="AIGF-" + file_id, title=name, owner=scope.owner,
        department=scope.department, status="uploading", data={
            "file_id": file_id, "owner_user_id": scope.owner_user_id, "owner_name": scope.owner_name,
            "employee_record_id": scope.employee_record_id, "space_id": scope.space_id,
            "case_id": scope.case_id, "name": name, "content_type": content_type, "size": len(content),
            "sha256": digest, "path": path, "stored_name": file_id, "endpoint": scope.endpoint,
            "source_kind": source_kind, "conversation_id": conversation_id,
            "source_request_id": source_request_id, "attachment_id": None, "error": None,
        },
    )
    db.add(record)
    await db.flush()
    record_id = record.id
    # 上传前提交对象计划；OSS 与数据库不能原子回滚，失败对象仍有准确归属。
    await db.commit()
    attempted = False
    try:
        attempted = True
        await oss_put_editor_revision(scope.bucket, key, content, content_type, endpoint=scope.endpoint)
        stored = SimpleNamespace(path=path, original_name=name, stored_name=file_id, oss_endpoint=scope.endpoint)
        checked = await read_generated_bytes(stored, max_bytes=MAX_GENERATED_BYTES)
        if len(checked) != len(content) or hashlib.sha256(checked).hexdigest() != digest:
            raise HTTPException(409, "AI 文件 OSS 回读校验失败，未更新附件引用")
        record = await db.scalar(select(BusinessRecord).where(BusinessRecord.id == record_id).with_for_update())
        if record is None or record.status != "uploading":
            raise HTTPException(409, "生成文件写入计划状态变化，禁止覆盖")
        if original is not None:
            attachment = await db.scalar(select(FileAttachment).where(
                FileAttachment.id == original[0],
            ).with_for_update().execution_options(populate_existing=True))
            if (attachment is None or attachment.record_id != scope.case_id
                    or (attachment.id, attachment.path, attachment.size, attachment.original_name) != original
                    or attachment.category != AI_SPACE_CATEGORY):
                raise HTTPException(409, "原草稿已变化，未切换生成文件版本")
            attachment.path = path
            attachment.original_name = name
            attachment.stored_name = file_id
            attachment.size = len(content)
            attachment.content_type = content_type
        else:
            attachment = FileAttachment(
                record_id=scope.case_id if scope.case_id is not None else record.id,
                category=AI_SPACE_CATEGORY if scope.case_id is not None else "个人AI空间",
                original_name=name, stored_name=file_id, content_type=content_type, size=len(content),
                path=path, uploader=scope.owner, remark="AI生成文件；正式归档须经原业务确认流程",
            )
            db.add(attachment)
            await db.flush()
        record.status = "available"
        record.data = {**record.data, "attachment_id": attachment.id}
        if on_available is not None:
            await on_available(db, attachment)
        await db.commit()
    except asyncio.CancelledError as exc:
        await _mark_failure(db, record_id, exc, attempted=attempted)
        raise
    except Exception as exc:
        status = await _mark_failure(db, record_id, exc, attempted=attempted)
        raise HTTPException(exc.status_code if isinstance(exc, HTTPException) else 503, {
            "file_id": file_id, "status": status,
            "detail": ("文件已持久提交为 available，但本次响应确认失败；请查询文件状态，不要重复生成"
                       if status == "available" else "生成文件未完成可用状态提交，对象计划已保留；禁止自动重放业务操作"),
        }) from exc
    await db.refresh(record)
    await db.refresh(attachment)
    return {"file": generated_file_item(record), "attachment": attachment}
