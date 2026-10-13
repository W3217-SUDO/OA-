"""生成文件的真实身份、命名目录及持久元数据，不创建新业务表。"""

from dataclasses import dataclass
import re
import unicodedata

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.data_models.identity import User
from app.data_models.records import BusinessRecord
from app.security import user_role_ids


SPACE_MODULE = "personal_ai_space"
FILE_MODULE = "ai_generated_file"
PRIVATE_MODULES = frozenset({SPACE_MODULE, FILE_MODULE})


def generated_storage_config() -> tuple[str, str]:
    bucket = settings.ai_oss_bucket.strip()
    prefix = settings.ai_oss_prefix.strip().rstrip("/")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", bucket):
        raise HTTPException(503, "AI 文件 OSS bucket 未配置或无效")
    if (not prefix or len(prefix) > 128 or prefix.startswith("/") or "\\" in prefix
            or any(part in {"", ".", ".."} for part in prefix.split("/"))
            or any(unicodedata.category(char).startswith("C") for char in prefix)):
        raise HTTPException(503, "AI 文件 OSS prefix 未配置或无效")
    return bucket, prefix


def generated_storage_endpoint() -> str:
    from app.core.oss_attachments import _endpoint_host

    endpoint = settings.ai_oss_endpoint.strip()
    if not endpoint:
        raise HTTPException(503, "AI 文件 OSS endpoint 未配置")
    _endpoint_host(endpoint)
    return endpoint


def named_segment(value: str) -> str:
    name = str(value or "").strip()
    if not name or any(unicodedata.category(char).startswith("C") for char in name):
        raise HTTPException(422, "真实姓名或案件名称缺失、无效，请先维护身份及业务资料")
    segment = re.sub(r'[\\/:*?"<>|]', "_", name).strip(". ")
    if not segment or segment in {".", ".."}:
        raise HTTPException(422, "真实姓名或案件名称不能用作 OSS 目录")
    return segment


async def actual_user(db, identity: dict) -> User:
    from app.agent_mcp.auth import authenticated_identity

    actual = await authenticated_identity(db)
    if actual["username"] != identity.get("username"):
        raise HTTPException(403, "生成文件身份与原登录账号不一致")
    user = await db.scalar(select(User).where(User.username == actual["username"]).execution_options(populate_existing=True))
    if user is None or not user.is_active:
        raise HTTPException(401, "账号不存在或已停用")
    return user


async def employee_name(db, user: User) -> tuple[str, int | None]:
    rows = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "hr",
        or_(BusinessRecord.data["system_user_id"].as_integer() == user.id,
            func.lower(func.trim(BusinessRecord.data["username"].as_string())) == user.username.casefold()),
    ))).all()
    matched = []
    for row in rows:
        data = row.data or {}
        username = data.get("username")
        linked_id = data.get("system_user_id")
        if ("username" in data and not str(username or "").strip()) or (
                username and str(username).strip().casefold() != user.username.casefold()) or (
                linked_id is not None and str(linked_id) != str(user.id)):
            raise HTTPException(409, "员工档案与账号绑定不一致，请先核对绑定")
        if str(data.get("account_type") or "员工账号") != "员工账号":
            raise HTTPException(403, "个人 AI 空间仅供员工账号使用")
        matched.append(row)
    if len(matched) > 1:
        raise HTTPException(409, "同一账号绑定多个员工档案，请先核对真实关联")
    if str((user.profile or {}).get("account_type") or "员工账号") != "员工账号":
        raise HTTPException(403, "个人 AI 空间仅供员工账号使用")
    employee = matched[0] if matched else None
    name = str(employee.title or "").strip() if employee else ""
    if not name:
        name = str(user.display_name or "").strip()
    named_segment(name)
    return name, employee.id if employee else None


@dataclass(frozen=True)
class GeneratedFileScope:
    owner_user_id: int
    owner: str
    owner_name: str
    department: str
    employee_record_id: int | None
    folder: str
    bucket: str
    endpoint: str
    case_id: int | None = None
    space_id: int | None = None


async def resolve_generated_scope(db, identity: dict, *, case_record=None) -> GeneratedFileScope:
    bucket, prefix = generated_storage_config()
    endpoint = generated_storage_endpoint()
    user = await actual_user(db, identity)
    name, employee_id = await employee_name(db, user)
    if case_record is not None:
        from app.core.permissions import _ensure_record_module

        case = await _ensure_record_module(case_record.id, "case", identity, db)
        if not case.serial_no or not case.title:
            raise HTTPException(422, "案件真实编号或名称缺失")
        folder = f"{prefix}/cases/{named_segment(case.serial_no + '-' + case.title)}--c{case.id}"
        return GeneratedFileScope(user.id, user.username, name, user.department, employee_id, folder, bucket, endpoint, case.id)
    serial = f"PAIS-U{user.id}"
    space = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == SPACE_MODULE, BusinessRecord.serial_no == serial,
    ).with_for_update())
    if space is None:
        folder = f"{prefix}/personal/{named_segment(name)}--u{user.id}"
        space = BusinessRecord(module=SPACE_MODULE, serial_no=serial, title=name, owner=user.username,
                               department=user.department, status="已建立", data={
                                   "owner_user_id": user.id, "owner_name": name, "employee_record_id": employee_id,
                                   "folder": folder, "bucket": bucket, "endpoint": endpoint,
                               })
        try:
            async with db.begin_nested():
                db.add(space)
                await db.flush()
        except IntegrityError:
            space = await db.scalar(select(BusinessRecord).where(
                BusinessRecord.module == SPACE_MODULE, BusinessRecord.serial_no == serial,
            ).with_for_update())
            if space is None:
                raise
    data = space.data or {}
    if (data.get("owner_user_id") != user.id or not data.get("folder") or data.get("bucket") != bucket
            or data.get("endpoint") != endpoint):
        raise HTTPException(409, "个人 AI 空间归属或存储配置与既有映射不一致")
    folder = str(data["folder"])
    if (not folder.startswith(prefix + "/personal/") or not folder.endswith(f"--u{user.id}")
            or "\\" in folder or any(part in {"", ".", ".."} for part in folder.split("/"))):
        raise HTTPException(409, "个人 AI 空间目录映射无效")
    return GeneratedFileScope(user.id, user.username, name, user.department, employee_id, folder, bucket, endpoint, space_id=space.id)


async def require_generated_record_access(record, identity, db) -> None:
    user = await actual_user(db, identity)
    if record.module not in PRIVATE_MODULES:
        raise HTTPException(404, "个人 AI 文件元记录不存在")
    if (record.data or {}).get("owner_user_id") != user.id and "admin" not in user_role_ids(user):
        raise HTTPException(403, "无权访问其他员工的 AI 文件")
    case_id = (record.data or {}).get("case_id")
    if case_id is not None:
        from app.core.permissions import _ensure_record_module

        await _ensure_record_module(case_id, "case", identity, db)


def generated_file_item(record) -> dict:
    data = record.data or {}
    identifier = data["file_id"]
    available = record.status == "available"
    return {
        "id": identifier, "attachment_id": data.get("attachment_id"), "name": data["name"],
        "content_type": data["content_type"], "size": data["size"], "sha256": data["sha256"],
        "status": record.status, "storage_backend": "oss", "owner_user_id": data["owner_user_id"],
        "owner_name": data["owner_name"], "source_kind": data["source_kind"],
        "conversation_id": data.get("conversation_id"), "source_request_id": data.get("source_request_id"),
        "case_id": data.get("case_id"), "created_at": record.created_at,
        "download_url": f"{settings.api_prefix}/personal-agent/ai-space/files/{identifier}/download" if available else None,
        "error": data.get("error"),
    }
