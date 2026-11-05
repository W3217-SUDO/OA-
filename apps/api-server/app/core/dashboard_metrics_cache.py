"""仅在账号、业务日期和数据库可见快照不变时复用控制台统计。"""
import asyncio
import hashlib
import json
import logging
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date
from time import monotonic
from types import SimpleNamespace

from app.core.dashboard_metrics import dashboard_metrics
from app.core.query_cache_flow import read_shared_query, release_lock
from app.core.dashboard_revision import dashboard_snapshot
from app.config import settings
from app.core import dashboard_metrics_redis as shared
from app.core import query_cache_store
from app.core.query_cache import _cached_query
from app.core.request_metrics import tag_request
from fastapi import HTTPException
from redis.exceptions import RedisError


_MAX_ENTRIES = 64
_SHARED_PREFIX = "sunhold:dashboard:metrics:v1"
logger = logging.getLogger(__name__)


@dataclass
class _MetricsEntry:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    snapshot: str | None = None
    business_date: date | None = None
    expires_at: float = 0
    result: dict | None = None


_entries: OrderedDict[tuple, _MetricsEntry] = OrderedDict()


async def _visible_snapshot(db):
    return await dashboard_snapshot(db, "dashboard.metrics.snapshot")


def _matches(entry, snapshot, business_date):
    return (snapshot is not None and entry.result is not None and entry.snapshot == snapshot
            and entry.business_date == business_date and monotonic() < entry.expires_at)


async def read_dashboard_metrics(identity, db):
    bind = db.get_bind()
    # 其它数据库继续执行原计算；仅只读的 PostgreSQL 请求采用快照校验。
    if bind.dialect.name != "postgresql" or db.new or db.dirty or db.deleted:
        return await dashboard_metrics(identity, db)
    snapshot = await _visible_snapshot(db)
    if snapshot is None:
        return await dashboard_metrics(identity, db)

    if settings.cache_redis_url.strip():
        try:
            return await _read_shared_metrics(identity, db, snapshot)
        except RedisError as exc:
            # 缓存不可用时直接现算，不让用户看到报错；同时现算的数量有上限（见 query_cache.FALLBACK_COMPUTE）。
            from app.core.query_cache import FALLBACK_COMPUTE
            if FALLBACK_COMPUTE.locked():
                logger.error("控制台共享缓存请求失败且现算已满：%s", type(exc).__name__)
                raise shared.unavailable() from exc
            logger.error("控制台共享缓存请求失败，改为现算：%s", type(exc).__name__)
            async with FALLBACK_COMPUTE:
                return await dashboard_metrics(identity, db)

    # 包含完整已认证身份和权限，不跨账号、权限集合或数据库连接复用。
    key = (bind, json.dumps(identity, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
    entry = _entries.get(key)
    if entry is None:
        if len(_entries) >= _MAX_ENTRIES:
            _entries.popitem(last=False)
        entry = _entries[key] = _MetricsEntry()
    _entries.move_to_end(key)
    business_date = date.today()
    if _matches(entry, snapshot, business_date):
        return deepcopy(entry.result)

    # 同账号并发刷新只计算一次，等待期间不共享数据库会话。
    async with entry.lock:
        snapshot = await _visible_snapshot(db)
        business_date = date.today()
        if _matches(entry, snapshot, business_date):
            return deepcopy(entry.result)
        result = await dashboard_metrics(identity, db)
        end_snapshot = await _visible_snapshot(db)
        # 计算期间若发生提交或跨日，结果照常返回但不进入复用集合。
        if snapshot is not None and snapshot == end_snapshot and business_date == date.today():
            entry.result = deepcopy(result)
            entry.snapshot = snapshot
            entry.business_date = business_date
            entry.expires_at = monotonic() + settings.dashboard_metrics_cache_ttl_seconds
        return result


def _shared_key(identity, db, business_date):
    # 凭据仅参与内存中的摘要计算，不进入 Redis key 或日志。
    database = hashlib.sha256(db.get_bind().url.render_as_string(hide_password=False).encode()).hexdigest()
    identity_key = hashlib.sha256(json.dumps(
        identity, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    return f"{_SHARED_PREFIX}:{shared.source_revision()}:{{{database}:{identity_key}:{business_date.isoformat()}}}"


async def _release_shared_lock(key, token, primary_error=None):
    await release_lock(shared, key, token, primary_error)


async def _read_shared_metrics(identity, db, snapshot):
    return await read_shared_query(
        db, key_for_date=lambda today: _shared_key(identity, db, today),
        compute=lambda: dashboard_metrics(identity, db), store=shared,
        snapshot_reader=_visible_snapshot, release=_release_shared_lock,
        label="控制台统计", today=date.today,
    )


async def _publish_dashboard_query(key, token, snapshot, result):
    ttl = settings.dashboard_metrics_cache_ttl_seconds
    if type(ttl) is not int or not 1 <= ttl <= 86400:
        raise ValueError("控制台缓存留存时间必须为 1 至 86400 秒")
    await query_cache_store._publish(key, token, snapshot, result, ttl)


# 10-27：控制台首屏要求约 1 秒内出数。数据修订变化后先返回同一账号、同一天、同一版本的上次结果
# （标记 stale），并在后台按原共享流程重算发布；前端收到 stale 后几秒内再取一次最新值。
# 11-05（陶国南同意的提速方案）：当天还没有结果（每天第一次进入、发版后第一次）时，先给这个账号这一块
# 最近一次算好的结果（跨天、跨版本也给，同样标 stale），后台照常重算；从来没算过的账号才等计算结果。
# 计算放在独立任务里：用户离开页面（499）不会中断它，算完照常写缓存；同一进程里同一账号同一分区只算一份。
# 预热重放不传 compute_in，始终按原流程算最新值。
SECTIONS = {"metrics_finance", "metrics_cases", "todos", "cases", "portals", "rejections"}
_LAST_PREFIX = "sunhold:dashboard:last:v1"
# 某个分区的返回结构做了不兼容的改动时加一，旧版本留下的“最近一次结果”就不再拿出来用。
LAST_RESULT_SHAPE = 1
_refreshing: dict[str, asyncio.Task] = {}


def _swr_available(db):
    return (bool(settings.cache_redis_url.strip()) and db.get_bind().dialect.name == "postgresql"
            and not (db.new or db.dirty or db.deleted))


def _last_key(db, identity, section):
    from app.core.query_cache import _digest

    database = hashlib.sha256(db.get_bind().url.render_as_string(hide_password=False).encode()).hexdigest()
    return f"{_LAST_PREFIX}:{LAST_RESULT_SHAPE}:{section}:{{{database}:{_digest(identity)}}}"


async def _remember_last(db, identity, section, result):
    """保存这一块最近一次算好的结果，留存与预热登记相同的天数；写不进去只记日志。"""
    if not settings.cache_redis_url.strip() or not isinstance(result, dict):
        return
    try:
        if not await query_cache_store._memory_allows_publish():
            return
        payload = await asyncio.to_thread(query_cache_store._encode, "0:0:", result)
        if payload is None:
            return
        await shared.client().set(_last_key(db, identity, section), payload,
                                  ex=settings.query_prewarm_idle_days * 86400)
    except (RedisError, TypeError, ValueError) as exc:
        logger.warning("控制台最近结果保存失败：%s section=%s", type(exc).__name__, section)


async def _last_result(db, identity, section):
    try:
        payload = await shared.client().get(_last_key(db, identity, section))
        if payload is None:
            return None
        result = (await asyncio.to_thread(query_cache_store._decode, payload))["result"]
    except (RedisError, HTTPException):
        return None
    return result if isinstance(result, dict) else None


async def _stale_result(db, key, identity=None, section=None):
    try:
        cached = await query_cache_store.read(key)
    except RedisError:
        return None
    if cached is None:
        # 当天（或这个版本）还没有结果：拿最近一次的结果先显示。
        return None if section is None else await _last_result(db, identity, section)
    snapshot = await dashboard_snapshot(db)
    if snapshot is None or snapshot == cached["snapshot"]:
        return None  # 最新结果由独立任务走共享流程，一次读缓存即返回
    return cached["result"]


def _shared_refresh(key, identity, section, compute_in, parameters=None):
    task = _refreshing.get(key)
    if task is not None:
        return task

    async def refresh():
        from app.database import SessionLocal

        try:
            async with SessionLocal() as session:
                return await cached_dashboard_query(session, identity, section, lambda: compute_in(session),
                                                    parameters=parameters, remember_last=True)
        finally:
            _refreshing.pop(key, None)

    def observe(done):
        if not done.cancelled() and done.exception() is not None:
            logger.warning("控制台后台计算失败：%s section=%s", type(done.exception()).__name__, section)

    task = _refreshing[key] = asyncio.create_task(refresh())
    task.add_done_callback(observe)
    return task


async def cached_dashboard_query(db, identity, section, compute, *, compute_in=None, parameters=None,
                                 remember_last=False):
    """compute_in(session) 给出时：有旧结果先返回并后台重算，否则等独立任务算完（离开页面不中断）。

    parameters 只放影响结果、但不在业务修订集合里的配置摘要（如分端待办配置），参与缓存键。
    """
    if section not in SECTIONS:
        raise ValueError("无效的控制台缓存分区")
    parameters = parameters or {}
    if compute_in is not None and _swr_available(db):
        from app.core.query_cache import _query_key

        key = _query_key(db, identity, f"dashboard.{section}", parameters, date.today())
        stale = await _stale_result(db, key, identity, section)
        if db.in_transaction():
            await db.rollback()
        task = _shared_refresh(key, deepcopy(identity), section, compute_in, parameters)
        if stale is not None:
            tag_request("cache", "stale")
            return {**stale, "stale": True}
        tag_request("cache", "shared")
        return deepcopy(await asyncio.shield(task))
    # 留存期只控制清理；每次命中仍由共享流程核对当前业务修订号。
    store = SimpleNamespace(
        read=query_cache_store.read, acquire=query_cache_store.acquire,
        unavailable=query_cache_store.unavailable, publish=_publish_dashboard_query,
    )
    result = await _cached_query(db, identity, f"dashboard.{section}", parameters, compute,
                                 snapshot_reader=dashboard_snapshot, query_store=store)
    if remember_last:
        await _remember_last(db, identity, section, result)
    return result
