"""调查任务详情及关联资料的只读查询。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import BusinessRecord, FileAttachment, User, current_identity, get_db, settings
from app.core.formatters import _task_display_dicts
from app.core.permissions import _ensure_record_visible, _record_scope_conditions
from app.core.storage import _attachment_dict
from app.core.investigation_access import _actual_identity, _manages_parent, _parent_id, ensure_investigation_material_access

router = APIRouter()


async def _detail_context(record_id: int, identity: dict, db: AsyncSession):
    source = await db.get(BusinessRecord, record_id)
    if not source or source.module not in {"investigation", "task"}:
        raise HTTPException(status_code=404, detail="调查任务不存在或无权访问")
    if source.module == "investigation":
        parent = source
    else:
        parent_id = _parent_id(source)
        parent = await db.get(BusinessRecord, parent_id) if parent_id else None
    if not parent or parent.module != "investigation":
        raise HTTPException(status_code=409, detail="调查任务缺少有效的父调查关联")
    if not _manages_parent(parent, identity):
        await _ensure_record_visible(source.id, identity, db)
    await ensure_investigation_material_access(parent.id, identity, db)
    return source, parent


@router.get(f"{settings.api_prefix}/investigations/{{record_id}}/task-detail")
async def investigation_task_detail(
    record_id: int, page: int = Query(1, ge=1), page_size: int = Query(15, ge=1, le=100),
    identity: dict = Depends(current_identity), db: AsyncSession = Depends(get_db),
):
    identity = await _actual_identity(identity, db)
    source, parent = await _detail_context(record_id, identity, db)
    if source.module == "investigation":
        conditions = [BusinessRecord.module == "task", BusinessRecord.data["investigation_record_id"].as_integer() == parent.id]
        if not _manages_parent(parent, identity):
            conditions.extend(await _record_scope_conditions(identity, db))
    else:
        conditions = [BusinessRecord.module == "clue", BusinessRecord.data["source_task_id"].as_integer() == source.id]
    total = await db.scalar(select(func.count()).select_from(BusinessRecord).where(*conditions))
    related = list((await db.scalars(select(BusinessRecord).where(*conditions)
        .order_by(BusinessRecord.created_at.desc(), BusinessRecord.id.desc()).offset((page - 1) * page_size).limit(page_size))).all())
    files = list((await db.scalars(select(FileAttachment).where(FileAttachment.record_id == parent.id)
        .order_by(FileAttachment.created_at.desc(), FileAttachment.id.desc()))).all())
    users = (await db.scalars(select(User).where(User.username.in_({item.uploader for item in files})))).all() if files else []
    names = {item.username.lower(): item.display_name for item in users}
    record_data, parent_data = await _task_display_dicts([source, parent], db)
    return {
        "record": record_data, "parent": parent_data,
        "materials": [_attachment_dict(item, parent, names) for item in files],
        "items": await _task_display_dicts(related, db), "total": total, "page": page, "page_size": page_size,
    }
