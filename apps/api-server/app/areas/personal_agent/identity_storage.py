"""身份文件的个人 OSS 归集；数据库声明跨会话和进程保持幂等。"""

import asyncio
import hashlib

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.agent_mcp.auth import get_auth_context
from app.config import settings
from app.core.generated_file_records import FILE_MODULE, SPACE_MODULE, generated_file_item, resolve_generated_scope
from app.core.generated_file_storage import save_generated_file
from app.core.oss_attachments import _load_credentials
from app.data_models.records import BusinessRecord


async def _claim(db, serial):
    record = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.serial_no == serial, BusinessRecord.module == SPACE_MODULE,
    ).execution_options(populate_existing=True))
    return record


async def _available_file(db, claim, scope, digest, size):
    data = claim.data or {}
    if (data.get("owner_user_id") != scope.owner_user_id or data.get("sha256") != digest
            or data.get("source_kind") != "personal_identity" or data.get("space_id") != scope.space_id):
        raise HTTPException(409, "个人身份文件版本声明与真实账号或内容不一致，请人工核对")
    if claim.status != "available":
        raise HTTPException(409, {
            "status": claim.status, "file_id": data.get("file_id"),
            "detail": "个人身份文件原保存尚未确认成功，请人工核对，禁止自动重试",
        })
    record = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == FILE_MODULE, BusinessRecord.id == data.get("file_record_id"),
        BusinessRecord.serial_no == "AIGF-" + str(data.get("file_id") or ""),
    ).execution_options(populate_existing=True))
    saved = record.data if record is not None else {}
    if (record is None or record.status != "available" or saved.get("owner_user_id") != scope.owner_user_id
            or saved.get("space_id") != scope.space_id or saved.get("source_kind") != "personal_identity"
            or saved.get("name") != "IDENTITY.md" or saved.get("sha256") != digest
            or saved.get("size") != size or saved.get("case_id") is not None):
        raise HTTPException(409, "个人身份文件版本与实际可用索引不一致，请人工核对")
    item = generated_file_item(record)
    await db.commit()
    return item


async def _record_failure(db, serial, error):
    await db.rollback()
    claim = await _claim(db, serial)
    if claim is None:
        raise HTTPException(503, "个人身份文件写入声明无法读取，请人工核对") from error
    if claim.status == "available":
        return
    plan = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == FILE_MODULE,
        BusinessRecord.data["space_id"].as_integer() == claim.data["space_id"],
        BusinessRecord.data["source_request_id"].as_string() == serial,
        BusinessRecord.data["source_kind"].as_string() == "personal_identity",
    ))
    status = plan.status if plan is not None and plan.status in {"failed", "uncertain"} else (
        "uncertain" if plan is not None or isinstance(error, asyncio.CancelledError) else "failed")
    claim.status = status
    claim.data = {
        **claim.data, "file_record_id": plan.id if plan is not None else None,
        "file_id": (plan.data or {}).get("file_id") if plan is not None else None,
        "error": "身份文件保存未完成，请核对原写入计划；禁止自动重试",
    }
    await db.commit()


async def persist_personal_identity(db, identity, *, content: str, conversation_id: str) -> dict:
    context = get_auth_context()
    if context.scope.get("method") != "POST" or context.scope.get("path") != settings.api_prefix + "/personal-agent/messages":
        raise HTTPException(403, "个人身份文件只能在本人实际提问时归集")
    _load_credentials(settings.ai_oss_credentials_file)
    scope = await resolve_generated_scope(db, identity)
    binary = content.encode("utf-8")
    digest = hashlib.sha256(binary).hexdigest()
    # 唯一键压缩真实账号 ID 与内容哈希；元数据再校验完整原值，不接受哈希碰撞冒名复用。
    serial = "PAID-" + hashlib.sha256(f"{scope.owner_user_id}:{digest}".encode()).hexdigest()[:59]
    existing = await _claim(db, serial)
    if existing is not None:
        return await _available_file(db, existing, scope, digest, len(binary))
    claim = BusinessRecord(module=SPACE_MODULE, serial_no=serial, title="IDENTITY.md", owner=scope.owner,
                           department=scope.department, status="uploading", data={
                               "owner_user_id": scope.owner_user_id, "owner_name": scope.owner_name,
                               "space_id": scope.space_id, "sha256": digest, "source_kind": "personal_identity",
                               "conversation_id": conversation_id, "file_record_id": None, "file_id": None, "error": None,
                           })
    try:
        async with db.begin_nested():
            db.add(claim)
            await db.flush()
    except IntegrityError:
        await db.rollback()
        existing = await _claim(db, serial)
        if existing is None:
            raise
        return await _available_file(db, existing, scope, digest, len(binary))
    # 上传前提交版本声明；后续进程只读真实状态，失败及未确认状态不会重新 PUT。
    await db.commit()

    async def on_available(session, attachment):
        record = await session.get(BusinessRecord, attachment.record_id)
        if (record is None or record.data.get("source_request_id") != serial
                or record.data.get("sha256") != digest):
            raise HTTPException(409, "个人身份文件最终版本与保存声明不一致")
        current = await session.scalar(select(BusinessRecord).where(
            BusinessRecord.module == SPACE_MODULE, BusinessRecord.serial_no == serial,
        ).with_for_update().execution_options(populate_existing=True))
        if current is None or current.status != "uploading" or current.data.get("sha256") != digest:
            raise HTTPException(409, "个人身份文件保存声明已变化，未确认成功")
        current.status = "available"
        current.data = {**current.data, "file_record_id": record.id, "file_id": record.data["file_id"]}

    try:
        result = await save_generated_file(
            db, identity, name="IDENTITY.md", content=binary, content_type="text/markdown; charset=utf-8",
            source_kind="personal_identity", conversation_id=conversation_id,
            source_request_id=serial, on_available=on_available,
        )
    except (Exception, asyncio.CancelledError) as exc:
        await _record_failure(db, serial, exc)
        raise
    return result["file"]
