"""仅在账号、业务日期和数据库可见快照不变时复用控制台统计。"""
import asyncio
import hashlib
import json
import logging
import sys
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date
from time import monotonic

from sqlalchemy import Text, cast, func, select

from app.core.dashboard_metrics import dashboard_metrics
from app.core.request_metrics import measure_phase
from app.config import settings
from app.core import dashboard_metrics_redis as shared
from redis.exceptions import RedisError


_MAX_ENTRIES = 64
_MAX_AGE_SECONDS = 300
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
    with measure_phase("dashboard.metrics.snapshot"):
        row = (await db.execute(select(
            cast(func.pg_current_snapshot(), Text).label("snapshot"),
            cast(func.pg_current_xact_id_if_assigned(), Text).label("own_xid"),
            func.current_setting("transaction_isolation").label("isolation"),
        ))).one()
    # 写事务和固定快照事务不复用，避免遗漏本事务的改动或读到过期版本。
    return row.snapshot if row.own_xid is None and row.isolation == "read committed" else None


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
            entry.expires_at = monotonic() + _MAX_AGE_SECONDS
        return result


def _shared_key(identity, db, business_date):
    # 凭据仅参与内存中的摘要计算，不进入 Redis key 或日志。
    database = hashlib.sha256(db.get_bind().url.render_as_string(hide_password=False).encode()).hexdigest()
    identity_key = hashlib.sha256(json.dumps(
        identity, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    return f"{_SHARED_PREFIX}:{shared.source_revision()}:{{{database}:{identity_key}:{business_date.isoformat()}}}"


async def _release_shared_lock(key, token, primary_error=None):
    # 客户端断开也等待精确解锁结束；不能把仍在执行的清理任务留给会话回收。
    cleanup = asyncio.create_task(shared.release(key, token))
    try:
        await asyncio.shield(cleanup)
    except asyncio.CancelledError as cancelled:
        try:
            await cleanup
        except RedisError as exc:
            logger.error("控制台取消查询后的解锁失败：%s", type(exc).__name__)
        raise cancelled
    except RedisError as exc:
        if primary_error is None:
            raise
        # 清理故障保留日志，但不能把客户端取消或计算失败替换成另一种异常。
        logger.error("控制台失败查询后的解锁失败：%s", type(exc).__name__)


async def _read_shared_metrics(identity, db, snapshot):
    deadline = monotonic() + settings.dashboard_metrics_cache_wait_seconds
    while True:
        if monotonic() >= deadline:
            raise shared.unavailable("控制台统计仍在重算，请稍后重试")
        if db.new or db.dirty or db.deleted:
            return await dashboard_metrics(identity, db)
        if db.in_transaction():
            # 仅此专用只读入口结束已验证的只读事务，等待 Redis 时不占数据库连接。
            snapshot = await _visible_snapshot(db)
            if snapshot is None:
                return await dashboard_metrics(identity, db)
            if db.new or db.dirty or db.deleted:
                return await dashboard_metrics(identity, db)
            await db.rollback()
        business_date = date.today()
        key = _shared_key(identity, db, business_date)
        # Redis 有结果时才取新快照；空缓存等待不增加数据库轮询。
        cached = await shared.read(key)
        if cached is not None:
            end_snapshot = await _visible_snapshot(db)
            if end_snapshot == cached["snapshot"] and business_date == date.today():
                return cached["result"]
            snapshot = end_snapshot
            if snapshot is None:
                return await dashboard_metrics(identity, db)
            if db.new or db.dirty or db.deleted:
                return await dashboard_metrics(identity, db)
            await db.rollback()
        token = await shared.acquire(key)
        if token is not None:
            try:
                snapshot = await _visible_snapshot(db)
                if snapshot is None:
                    return await dashboard_metrics(identity, db)
                cached = await shared.read(key)
                if (cached is not None and cached["snapshot"] == snapshot
                        and business_date == date.today()):
                    end_snapshot = await _visible_snapshot(db)
                    if end_snapshot == snapshot and business_date == date.today():
                        return cached["result"]
                    snapshot = end_snapshot
                    if snapshot is None:
                        return await dashboard_metrics(identity, db)
                try:
                    async with asyncio.timeout(settings.dashboard_metrics_compute_timeout_seconds):
                        result = await dashboard_metrics(identity, db)
                except TimeoutError as exc:
                    raise shared.unavailable("控制台统计计算超时，请稍后重试") from exc
                end_snapshot = await _visible_snapshot(db)
                if (snapshot == end_snapshot and business_date == date.today()
                        and not (db.new or db.dirty or db.deleted)):
                    await shared.publish(key, token, snapshot, result)
                return result
            finally:
                await _release_shared_lock(key, token, sys.exception())
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise shared.unavailable("控制台统计仍在重算，请稍后重试")
        await asyncio.sleep(min(0.1, remaining))
