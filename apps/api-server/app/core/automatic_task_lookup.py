"""单轮自动任务巡检的查重定位，保留数据库实时校验。"""

from contextlib import asynccontextmanager
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BusinessRecord


_LOOKUP_KEY = "automatic_task_key_lookup"


@dataclass
class _TaskLookup:
    ids: dict[tuple[int, str, str], int]
    ambiguous: set[tuple[int, str, str]]
    by_case_id: dict[int, set[int]]
    by_case_no: dict[str, set[int]]


@asynccontextmanager
async def automatic_task_lookup_scope(db: AsyncSession):
    """只保存查重键和主键，不加载任务正文，不跨巡检保留。"""
    if _LOOKUP_KEY in db.info:
        raise RuntimeError("自动任务查重索引不能在同一会话重复进入")
    rows = await db.execute(select(
        BusinessRecord.id,
        BusinessRecord.data["case_id"].as_integer(),
        BusinessRecord.data["auto_task_type"].as_string(),
        BusinessRecord.data["trigger_source_id"].as_string(),
        BusinessRecord.data["case_record_id"].as_integer(),
        BusinessRecord.data["case_no"].as_string(),
    ).where(
        BusinessRecord.module == "task",
    ))
    lookup = _TaskLookup({}, set(), {}, {})
    for task_id, case_id, kind, source, case_record_id, case_no in rows:
        for linked_id in (case_id, case_record_id):
            if linked_id is not None:
                lookup.by_case_id.setdefault(linked_id, set()).add(task_id)
        if case_no is not None:
            lookup.by_case_no.setdefault(case_no, set()).add(task_id)
        if case_id is None or kind is None or source is None:
            continue
        key = (case_id, kind, source)
        if key in lookup.ids:
            lookup.ambiguous.add(key)
        else:
            lookup.ids[key] = task_id
    db.info[_LOOKUP_KEY] = lookup
    try:
        yield
    finally:
        del db.info[_LOOKUP_KEY]


async def find_automatic_task(db: AsyncSession, case_id: int, kind: str, source: str) -> BusinessRecord | None:
    query = select(BusinessRecord).where(
        BusinessRecord.module == "task",
        BusinessRecord.data["case_id"].as_integer() == case_id,
        BusinessRecord.data["auto_task_type"].as_string() == kind,
        BusinessRecord.data["trigger_source_id"].as_string() == source,
    )
    lookup = db.info.get(_LOOKUP_KEY)
    key = (case_id, kind, source)
    if lookup is not None and key not in lookup.ambiguous:
        task_id = lookup.ids.get(key)
        if task_id is not None:
            existing = await db.scalar(query.where(BusinessRecord.id == task_id))
            if existing is not None:
                return existing
            lookup.ids.pop(key)
    # 未命中或巡检期间关联发生变化时，仍从数据库确认，不能缓存“不存在”。
    existing = await db.scalar(query)
    if existing is not None:
        remember_automatic_task(db, case_id, kind, source, existing.id)
    return existing


def remember_automatic_task(db: AsyncSession, case_id: int, kind: str, source: str, task_id: int):
    lookup = db.info.get(_LOOKUP_KEY)
    if lookup is not None:
        lookup.ids[(case_id, kind, source)] = task_id


async def find_case_automatic_task(db, case_record, matches):
    query = select(BusinessRecord).where(
        BusinessRecord.module == "task",
        or_(BusinessRecord.data["case_id"].as_integer() == case_record.id,
            BusinessRecord.data["case_record_id"].as_integer() == case_record.id,
            BusinessRecord.data["case_no"].as_string() == case_record.serial_no),
    ).order_by(BusinessRecord.id)
    lookup = db.info.get(_LOOKUP_KEY)
    if lookup is not None:
        ids = lookup.by_case_id.get(case_record.id, set()) | lookup.by_case_no.get(case_record.serial_no, set())
        if ids:
            tasks = (await db.scalars(query.where(BusinessRecord.id.in_(ids)))).all()
            existing = next((task for task in tasks if matches(task)), None)
            if existing is not None:
                return existing
    # 索引不记录不存在；未命中时查询实时关联，避免巡检期间新增任务被重复创建。
    tasks = (await db.scalars(query)).all()
    if lookup is not None:
        for task in tasks:
            lookup.by_case_id.setdefault(case_record.id, set()).add(task.id)
    return next((task for task in tasks if matches(task)), None)
