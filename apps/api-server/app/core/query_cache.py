"""供已审计的纯 JSON 查询入口复用，鉴权仍由每次请求执行。"""
import hashlib
import json
import logging
import re
from functools import partial
from types import SimpleNamespace

from redis.exceptions import RedisError

from app.config import settings
from app.core import dashboard_metrics_redis as shared
from app.core import query_cache_store as store
from app.core.query_cache_flow import read_shared_query, release_lock, visible_snapshot


logger = logging.getLogger(__name__)


def _digest(value):
    return hashlib.sha256(json.dumps(store.json_value(value), ensure_ascii=True,
                                    sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _query_key(db, identity, namespace, parameters, business_date):
    database = hashlib.sha256(db.get_bind().url.render_as_string(hide_password=False).encode()).hexdigest()
    return (f"sunhold:query:v1:{shared.source_revision()}:{namespace}:"
            f"{{{database}:{_digest(identity)}:{_digest(parameters)}:{business_date.isoformat()}}}")


async def cached_query(db, identity, namespace, parameters, compute, *, snapshot_reader=None, ttl_seconds=None):
    """只包装最终响应；调用者不得捕获 ORM 依赖或包含写入、下载及动态签名操作。"""
    if not settings.cache_redis_url.strip():
        return await compute()
    if not isinstance(identity, dict):
        raise TypeError("共享查询缓存需要已认证的身份字典")
    if not isinstance(namespace, str) or re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", namespace) is None:
        raise ValueError("共享查询缓存需要稳定的查询命名空间")
    if ttl_seconds is not None and (type(ttl_seconds) is not int or not 1 <= ttl_seconds <= 300):
        raise ValueError("共享查询缓存有效期必须为 1 至 300 秒")
    if db.get_bind().dialect.name != "postgresql" or db.new or db.dirty or db.deleted:
        return await compute()
    reader = visible_snapshot if snapshot_reader is None else snapshot_reader
    if await reader(db) is None:
        return await compute()
    query_store = store if ttl_seconds is None else SimpleNamespace(
        read=store.read, acquire=store.acquire, unavailable=store.unavailable,
        publish=partial(store.publish, ttl_seconds=ttl_seconds),
    )

    async def release(key, token, primary_error):
        await release_lock(store, key, token, primary_error)

    try:
        return await read_shared_query(
            db, key_for_date=lambda today: _query_key(db, identity, namespace, parameters, today),
            compute=compute, store=query_store, snapshot_reader=reader,
            release=release, label="查询结果",
        )
    except RedisError as exc:
        logger.error("查询共享缓存请求失败：%s namespace=%s", type(exc).__name__, namespace)
        raise store.unavailable() from exc
