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

from app.core.dashboard_metrics import dashboard_metrics
from app.core.query_cache_flow import read_shared_query, release_lock, visible_snapshot
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
    return await visible_snapshot(db, "dashboard.metrics.snapshot")


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
    await release_lock(shared, key, token, primary_error)


async def _read_shared_metrics(identity, db, snapshot):
    return await read_shared_query(
        db, key_for_date=lambda today: _shared_key(identity, db, today),
        compute=lambda: dashboard_metrics(identity, db), store=shared,
        snapshot_reader=_visible_snapshot, release=_release_shared_lock,
        label="控制台统计", today=date.today,
    )
