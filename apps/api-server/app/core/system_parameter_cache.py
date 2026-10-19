"""系统参数进程内缓存的跨进程有效性校验。

``SYSTEM_PARAMETER_CACHE`` 存在每个工作进程内，修改参数时只能清除处理该请求的进程。
多进程运行时，其他进程需要知道自己的缓存已过期。这里为每个缓存条目记录生成时
对应分类全部参数行的数据库指纹；读取缓存前重新计算，指纹不一致即作废该条目。

指纹在读取参数行之前计算：若两步之间有修改，记录的指纹早于数据，下次读取时必然
不一致而重新加载，不会把旧数据当作新数据长期保留。非 PostgreSQL（测试环境，单进程）
不做校验，保持原有缓存行为。
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import SYSTEM_PARAMETER_CACHE


# cache_key -> (生成缓存时使用的分类集合, 数据库指纹)
SYSTEM_PARAMETER_CACHE_SOURCES: dict[str, tuple[tuple[str, ...], str]] = {}


def _validates(db: AsyncSession) -> bool:
    return db.get_bind().dialect.name == "postgresql"


async def system_parameter_fingerprint(db: AsyncSession, categories) -> str | None:
    if not _validates(db):
        return None
    return await db.scalar(text(
        "SELECT md5(coalesce(string_agg(sp::text, '|' ORDER BY sp.id), '')) "
        "FROM system_parameters sp WHERE sp.category = ANY(:categories)"
    ), {"categories": sorted(categories)})


async def read_system_parameter_cache(db: AsyncSession, cache_key: str) -> list[dict] | None:
    """返回仍然有效的缓存条目；已被其他进程修改的条目在此作废。"""
    if cache_key not in SYSTEM_PARAMETER_CACHE:
        return None
    if not _validates(db):
        return SYSTEM_PARAMETER_CACHE[cache_key]
    source = SYSTEM_PARAMETER_CACHE_SOURCES.get(cache_key)
    if source is None or await system_parameter_fingerprint(db, source[0]) != source[1]:
        SYSTEM_PARAMETER_CACHE.pop(cache_key, None)
        SYSTEM_PARAMETER_CACHE_SOURCES.pop(cache_key, None)
        return None
    return SYSTEM_PARAMETER_CACHE.get(cache_key)


def store_system_parameter_cache(cache_key: str, categories, fingerprint: str | None, result: list[dict]) -> None:
    SYSTEM_PARAMETER_CACHE[cache_key] = result
    if fingerprint is None:
        SYSTEM_PARAMETER_CACHE_SOURCES.pop(cache_key, None)
    else:
        SYSTEM_PARAMETER_CACHE_SOURCES[cache_key] = (tuple(sorted(categories)), fingerprint)
