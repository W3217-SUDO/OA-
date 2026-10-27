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
            logger.error("控制台共享缓存请求失败：%s", type(exc).__name__)
            raise shared.unavailable() from exc

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
# 没有任何旧结果（新账号、发版后第一次）时仍等计算结果，但计算放在独立任务里：
# 用户离开页面（499）不会中断它，算完照常写缓存；同一进程里同一账号同一分区只算一份。
# 预热重放不传 compute_in，始终按原流程算最新值。
_refreshing: dict[str, asyncio.Task] = {}


def _swr_available(db):
    return (bool(settings.cache_redis_url.strip()) and db.get_bind().dialect.name == "postgresql"
            and not (db.new or db.dirty or db.deleted))


async def _stale_result(db, key):
    try:
        cached = await query_cache_store.read(key)
    except RedisError:
        return None
    if cached is None:
        return None
    snapshot = await dashboard_snapshot(db)
    if snapshot is None or snapshot == cached["snapshot"]:
        return None  # 最新结果由独立任务走共享流程，一次读缓存即返回
    return cached["result"]


def _shared_refresh(key, identity, section, compute_in):
    task = _refreshing.get(key)
    if task is not None:
        return task

    async def refresh():
        from app.database import SessionLocal

        try:
            async with SessionLocal() as session:
                return await cached_dashboard_query(session, identity, section, lambda: compute_in(session))
        finally:
            _refreshing.pop(key, None)

    def observe(done):
        if not done.cancelled() and done.exception() is not None:
            logger.warning("控制台后台计算失败：%s section=%s", type(done.exception()).__name__, section)

    task = _refreshing[key] = asyncio.create_task(refresh())
    task.add_done_callback(observe)
    return task


async def cached_dashboard_query(db, identity, section, compute, *, compute_in=None):
    """compute_in(session) 给出时：有旧结果先返回并后台重算，否则等独立任务算完（离开页面不中断）。"""
    if section not in {"metrics_finance", "metrics_cases", "todos", "cases"}:
        raise ValueError("无效的控制台缓存分区")
    if compute_in is not None and _swr_available(db):
        from app.core.query_cache import _query_key

        key = _query_key(db, identity, f"dashboard.{section}", {}, date.today())
        stale = await _stale_result(db, key)
        if db.in_transaction():
            await db.rollback()
        task = _shared_refresh(key, deepcopy(identity), section, compute_in)
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
    return await _cached_query(db, identity, f"dashboard.{section}", {}, compute,
                               snapshot_reader=dashboard_snapshot, query_store=store)
