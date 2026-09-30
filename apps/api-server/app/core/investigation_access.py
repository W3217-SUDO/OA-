"""调查详情与父资料的真实身份及只读关系授权。"""
from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import BusinessRecord, User
from app.security import user_role_ids
from app.core.permissions import _ensure_record_visible, _require_record_owner_or_manager


def _parent_id(record: BusinessRecord) -> int | None:
    value = (record.data or {}).get("investigation_record_id")
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


def _manages_parent(parent: BusinessRecord, identity: dict) -> bool:
    username = str(identity["username"]).lower()
    return identity.get("role") == "admin" or username in {
        str(parent.owner).lower(), str((parent.data or {}).get("publisher") or "").lower(),
    }


async def _actual_identity(identity: dict, db: AsyncSession) -> dict:
    user = await db.scalar(select(User).where(User.username == identity["username"], User.is_active.is_(True)))
    if not user:
        raise HTTPException(status_code=401, detail="当前用户不存在或已停用")
    roles = user_role_ids(user)
    return {**identity, "role": roles[0], "role_ids": roles, "_actual_role_ids": roles, "_page_menu_capability": False}


async def ensure_investigation_material_access(record_id: int, identity: dict, db: AsyncSession, *, write: bool = False) -> bool:
    """子任务关系仅授予读取；菜单能力不扩大父调查资料范围。"""
    parent = await db.get(BusinessRecord, record_id)
    if not parent or (parent.module != "investigation" and not (parent.module == "task" and _parent_id(parent))):
        return False
    actual = await _actual_identity(identity, db)
    if parent.module == "task":
        from app.core.permissions import _ensure_attachment_record_visible
        await _ensure_attachment_record_visible(parent.id, actual, db)
        return True
    username = actual["username"]
    if write or _manages_parent(parent, actual):
        await _ensure_record_visible(parent.id, actual, db)
        if write and not _manages_parent(parent, actual):
            await _require_record_owner_or_manager(parent, actual, db)
        return True
    task_id = await db.scalar(select(BusinessRecord.id).where(
        BusinessRecord.module == "task",
        BusinessRecord.data["investigation_record_id"].as_integer() == parent.id,
        or_(BusinessRecord.owner == username, BusinessRecord.data["initiator"].as_string() == username),
    ).limit(1))
    if task_id is None:
        await _ensure_record_visible(parent.id, actual, db)
    return True

