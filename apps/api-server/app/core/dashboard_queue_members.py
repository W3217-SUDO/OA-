"""工作台提醒的成员（哪些案件、哪些费用）：算数字时顺手记下，点进去的列表直接按这批记录取，
数字和列表一致，列表也不必再把整套范围和队列条件重算一遍（陶威 2026-11-01：点进去太慢）。

按账号和当天存在共享缓存里；工作台数字每次重算都会刷新。缓存不可用或没有记录时，调用方照原流程现算。
"""
import hashlib
import json
import logging
from datetime import date

from fastapi import HTTPException
from redis.exceptions import RedisError

from app.config import settings

logger = logging.getLogger(__name__)

TTL_SECONDS = 6 * 3600
CASE_GROUP = "cases"
FINANCE_GROUP = "finance"


def _available(db) -> bool:
    return bool(settings.cache_redis_url.strip()) and db.get_bind().dialect.name == "postgresql"


def _key(db, username: str, group: str) -> str:
    from app.core import dashboard_metrics_redis as shared
    database = hashlib.sha256(db.get_bind().url.render_as_string(hide_password=False).encode()).hexdigest()[:16]
    user = hashlib.sha256(username.encode()).hexdigest()[:24]
    return f"sunhold:dashboard:queue-members:v1:{shared.source_revision()}:{database}:{user}:{group}:{date.today().isoformat()}"


async def remember(db, username: str, group: str, queues: dict[str, list[dict]]) -> None:
    """queues 是 personal_*_queues 的结果；记下每个提醒的案件 id 和费用 id。"""
    if not _available(db):
        return
    members = {
        key: {"case_ids": sorted({int(row["id"]) for row in rows}),
              "fee_ids": sorted({int(row["fee_id"]) for row in rows if row.get("fee_id") is not None})}
        for key, rows in queues.items()
    }
    try:
        from app.core import dashboard_metrics_redis as shared
        await shared.client().set(_key(db, username, group), json.dumps(members, separators=(",", ":")), ex=TTL_SECONDS)
    except (RedisError, HTTPException) as exc:
        # 缓存连接未就绪或出错时不影响工作台，列表照常现算。
        logger.warning("工作台提醒成员缓存写入失败：%s", type(exc).__name__)


async def recall(db, username: str, group: str, queue: str) -> dict | None:
    if not _available(db):
        return None
    try:
        from app.core import dashboard_metrics_redis as shared
        payload = await shared.client().get(_key(db, username, group))
    except (RedisError, HTTPException) as exc:
        logger.warning("工作台提醒成员缓存读取失败：%s", type(exc).__name__)
        return None
    if payload is None:
        return None
    members = json.loads(payload)
    return members.get(queue)
