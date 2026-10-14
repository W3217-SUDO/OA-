"""个人 AI 空间查询与人工确认保存，不把生成文件当成正式案卷。"""

import hashlib
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import select
from app.config import settings

from app.core.generated_file_records import (
    FILE_MODULE, SPACE_MODULE, actual_user, employee_name, generated_file_item,
    generated_storage_config, generated_storage_endpoint, named_segment, require_generated_record_access,
)
from app.core.generated_file_storage import read_generated_bytes, save_generated_file
from app.data_models.documents import FileAttachment
from app.data_models.identity import User
from app.data_models.records import BusinessRecord
from app.security import user_role_ids
from app.areas.personal_agent import conversations


async def personal_save_capability(identity, db):
    from app.core.oss_attachments import _load_credentials

    try:
        generated_storage_config()
        _load_credentials(settings.ai_oss_credentials_file)
        generated_storage_endpoint()
        user = await actual_user(db, identity)
        await employee_name(db, user)
    except HTTPException as exc:
        if exc.status_code not in {403, 409, 422, 503}:
            raise
        return {"can_save": False, "error": exc.detail}
    return {"can_save": True, "error": None}


async def space_owner(identity, db, owner_user_id=None):
    user = await actual_user(db, identity)
    if owner_user_id is None or owner_user_id == user.id:
        return user
    if "admin" not in user_role_ids(user):
        raise HTTPException(403, "只有真实系统管理员可以读取其他员工的 AI 空间")
    target = await db.get(User, owner_user_id)
    if target is None:
        raise HTTPException(404, "员工账号不存在")
    return target


async def space_info(identity, db, owner_user_id=None):
    from app.core.oss_attachments import _load_credentials

    user = await space_owner(identity, db, owner_user_id)
    name, employee_id = await employee_name(db, user)
    bucket, prefix = generated_storage_config()
    endpoint = generated_storage_endpoint()
    _load_credentials(settings.ai_oss_credentials_file)
    record = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == SPACE_MODULE, BusinessRecord.serial_no == f"PAIS-U{user.id}",
    ))
    folder = f"{prefix}/personal/{named_segment(name)}--u{user.id}"
    if record is not None:
        data = record.data or {}
        if (data.get("owner_user_id") != user.id or data.get("bucket") != bucket or not data.get("folder")
                or not str(data["folder"]).startswith(prefix + "/personal/")
                or not str(data["folder"]).endswith(f"--u{user.id}") or data.get("endpoint") != endpoint):
            raise HTTPException(409, "个人 AI 空间目录映射与账号或配置不一致")
        folder = data["folder"]
    return {"owner_user_id": user.id, "owner_name": name, "employee_record_id": employee_id,
            "folder": folder, "storage_backend": "oss", "configured": True,
            "verification_scope": "configuration_only", "put_verified": False}


async def list_space_files(identity, db, *, page, page_size, owner_user_id=None):
    user = await space_owner(identity, db, owner_user_id)
    records = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == FILE_MODULE, BusinessRecord.data["owner_user_id"].as_integer() == user.id,
    ).order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()))).all()
    visible = []
    for record in records:
        try:
            await require_generated_record_access(record, identity, db)
        except HTTPException as exc:
            if exc.status_code not in {403, 404}:
                raise
            continue
        visible.append(generated_file_item(record))
    return {"items": visible[(page - 1) * page_size:page * page_size], "total": len(visible),
            "page": page, "page_size": page_size}


async def space_file_record(file_id, identity, db):
    record = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == FILE_MODULE, BusinessRecord.serial_no == "AIGF-" + file_id,
    ))
    if record is None:
        raise HTTPException(404, "生成文件不存在")
    await require_generated_record_access(record, identity, db)
    return record


async def space_file_bytes(file_id, identity, db):
    record = await space_file_record(file_id, identity, db)
    item = generated_file_item(record)
    if record.status != "available":
        raise HTTPException(409, {"file_id": file_id, "status": record.status, "detail": "文件尚未完成持久保存"})
    attachment = await db.get(FileAttachment, item["attachment_id"])
    if attachment is None:
        raise HTTPException(404, "生成文件附件已不存在")
    # 版本读取使用该次保存的不可变路径，不把历史索引静默指向附件的最新版本。
    source = SimpleNamespace(path=record.data["path"], original_name=item["name"], stored_name=record.data["stored_name"],
                             oss_endpoint=record.data["endpoint"])
    content = await read_generated_bytes(source)
    if len(content) != item["size"] or hashlib.sha256(content).hexdigest() != item["sha256"]:
        raise HTTPException(409, "生成文件大小或 SHA256 与持久记录不一致")
    return item, content


async def space_file_text(file_id, identity, db):
    from app.core.formatters import _case_ai_draft_text

    await space_file_record(file_id, identity, db)
    item, content = await space_file_bytes(file_id, identity, db)
    suffix = str(item["name"]).lower().rsplit(".", 1)[-1] if "." in str(item["name"]) else ""
    if suffix not in {"docx", "md", "txt"}:
        raise HTTPException(422, "当前文件格式不支持在线编辑")
    attachment = await db.get(FileAttachment, item["attachment_id"])
    if attachment is None:
        raise HTTPException(404, "生成文件附件已不存在")
    # Reuse the same DOCX extraction contract as the case AI editor.
    text = _case_ai_draft_text(attachment, content)
    return {"id": file_id, "name": item["name"], "content": text, "content_editable": True}


async def edit_space_file(file_id, name, content, identity, db):
    from app.core.cases import _case_ai_draft_bytes, _case_ai_draft_name
    from app.core.generated_file_storage import save_generated_file
    from app.core.generated_file_records import actual_user

    record = await space_file_record(file_id, identity, db)
    actual = await actual_user(db, identity)
    if (record.data or {}).get("owner_user_id") != actual.id:
        raise HTTPException(403, "只有文件所属员工可以在线编辑个人 AI 文件")
    await space_file_text(file_id, identity, db)
    safe_name = _case_ai_draft_name(name)
    binary, content_type = _case_ai_draft_bytes(safe_name, content)
    result = await save_generated_file(
        db, identity, name=safe_name, content=binary, content_type=content_type,
        source_kind="personal_edit", conversation_id=(record.data or {}).get("conversation_id"),
    )
    return {"file": result["file"], "supersedes": file_id}


async def save_space_message(body, identity, db):
    from app.core.cases import _case_ai_draft_bytes, _case_ai_draft_name
    from app.areas.personal_agent.service import _user_dir

    user = await actual_user(db, identity)
    async with conversations.conversation_operation(_user_dir(user.username), body.conversation_id) as state:
        if body.message_index >= len(state["messages"]):
            raise HTTPException(404, "原回答已不在当前会话中")
        message = state["messages"][body.message_index]
        content = message.get("content")
        if message.get("role") != "assistant" or message.get("failed") or message.get("stopped") or not isinstance(content, str) or not content.strip():
            raise HTTPException(422, "只能保存本人已完整生成的真实回答")
        if hashlib.sha256(content.encode("utf-8")).hexdigest() != body.expected_content_sha256:
            raise HTTPException(409, "原回答内容已变化，请重新核对后确认保存")
        name = _case_ai_draft_name(body.name)
        binary, content_type = _case_ai_draft_bytes(name, content)
        result = await save_generated_file(db, identity, name=name, content=binary, content_type=content_type,
                                           source_kind="assistant_message", conversation_id=body.conversation_id)
        return result["file"]
