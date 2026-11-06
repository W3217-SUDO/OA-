"""仅在账号、业务日期和数据库可见快照不变时复用控制台统计。"""
import asyncio
import hashlib
import json
import logging
from collections import OrderedDict, deque
from contextlib import asynccontextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date
from time import monotonic, time
from types import SimpleNamespace
from uuid import uuid4
from weakref import WeakKeyDictionary

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


def dashboard_cache_identity(identity):
    """工作台数字和用户当时停在哪个页面无关；页面头已决定的权限字段（角色、页面能力、数据范围）都留在键里。

    11-06 查到：缓存键带 _request_page，同一账号从不同页面取工作台各算一份（生产 8 个账号登记了 499 份）。
    """
    return {**identity, "_request_page": ""}
_LAST_PREFIX = "sunhold:dashboard:last:v1"
# 某个分区的返回结构做了不兼容的改动时加一，旧版本留下的“最近一次结果”就不再拿出来用。
LAST_RESULT_SHAPE = 1
_refreshing: dict[str, asyncio.Task] = {}
# 11-06 压测：一个人打开工作台要算 6 块，任何一笔写入都让所有人的结果过期，几十人同时用时重算把 CPU 和连接池占满，
# 别的页面也跟着超时。所以每个进程同时只算一份，有人等着的排在后台刷新前面；已有旧结果的，同一块冷却期内不重复算。
_REFRESH_COOLDOWN_PREFIX = "sunhold:dashboard:refresh:v1"
# 冷却期开始后这么久内仍告诉前端“新结果快好了”，前端继续短轮询；之后不再轮询，等下一次刷新。
_REFRESH_RETRY_WINDOW_SECONDS = 30


_GLOBAL_SLOT_PREFIX = "sunhold:dashboard:compute:v1"
_GLOBAL_SLOT_SECONDS = 90
_GLOBAL_POLL_SECONDS = 0.2
_RELEASE_SLOT = "if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) end return 0"


async def _global_slot(urgent):
    """跨进程名额（4 个进程共用）：后台只用 0 号，等结果的可用全部。Redis 不可用时不限制，只靠进程内名额。"""
    if not settings.cache_redis_url.strip():
        return None
    token = uuid4().hex
    slots = range(settings.dashboard_global_compute_slots if urgent else 1)
    try:
        client = shared.client()
        while True:
            for index in slots:
                key = f"{_GLOBAL_SLOT_PREFIX}:{index}"
                if await client.set(key, token, nx=True, ex=_GLOBAL_SLOT_SECONDS):
                    return key, token
            await asyncio.sleep(_GLOBAL_POLL_SECONDS)
    except (RedisError, HTTPException):
        return None


async def _release_global_slot(lease, *, urgent=False, seconds=0.0):
    if lease is None:
        return
    try:
        # 后台刷新算完后名额再占一段时间（算的时长 × 倍数），把它占用的 CPU 限制在一定比例内，用户请求不被挤掉。
        rest = 0 if urgent else min(_GLOBAL_SLOT_SECONDS, int(seconds * settings.dashboard_background_rest_ratio))
        if rest >= 1:
            await asyncio.shield(shared.client().expire(lease[0], rest))
            return
        await asyncio.shield(shared.client().eval(_RELEASE_SLOT, 1, lease[0], lease[1]))
    except (RedisError, HTTPException) as exc:
        logger.warning("控制台计算名额释放失败：%s", type(exc).__name__)  # 到期自动释放


class ComputeGate:
    """按进程限制同时运行的重算数；等结果的请求优先于后台刷新。只在单个事件循环内使用。"""

    def __init__(self, slots=1):
        self.slots = slots
        self.running = 0
        self.waiting = {True: deque(), False: deque()}

    def _wake(self):
        for lane in (self.waiting[True], self.waiting[False]):
            while lane and self.running < self.slots:
                waiter = lane.popleft()
                if not waiter.done():
                    self.running += 1
                    waiter.set_result(None)

    def promote(self, waiter):
        """后台排队的刷新来了等结果的人：提到优先队列。"""
        if waiter in self.waiting[False]:
            self.waiting[False].remove(waiter)
            self.waiting[True].append(waiter)

    @asynccontextmanager
    async def slot(self, *, urgent=False, ticket=None):
        waiter = asyncio.get_running_loop().create_future()
        if ticket is not None:
            ticket["waiter"] = waiter
        self.waiting[bool(urgent)].append(waiter)
        self._wake()
        try:
            await waiter
        except asyncio.CancelledError:
            if waiter.done() and not waiter.cancelled():
                self.running -= 1
                self._wake()
            raise
        lease = None
        started = monotonic()
        try:
            lease = await _global_slot(urgent)
            started = monotonic()
            yield
        finally:
            await _release_global_slot(lease, urgent=urgent, seconds=monotonic() - started)
            self.running -= 1
            self._wake()


_gates = WeakKeyDictionary()


def compute_gate():
    loop = asyncio.get_running_loop()
    gate = _gates.get(loop)
    if gate is None:
        gate = _gates[loop] = ComputeGate(settings.dashboard_compute_concurrency)
    return gate


async def _refresh_state(key):
    """started：本次由我发起；recent：刚有人发起，新结果快好了；cooling：冷却中，先用旧结果。"""
    cooldown = settings.dashboard_stale_refresh_cooldown_seconds
    cooldown_key = f"{_REFRESH_COOLDOWN_PREFIX}:{hashlib.sha256(key.encode()).hexdigest()}"
    now = time()
    try:
        client = shared.client()
        if await client.set(cooldown_key, str(now), nx=True, ex=cooldown):
            return "started"
        started_at = await client.get(cooldown_key)
        started_at = float(started_at.decode() if isinstance(started_at, bytes) else started_at)
    except (RedisError, HTTPException, TypeError, ValueError, AttributeError):
        return "started"  # 冷却记录读写失败时按原流程刷新
    return "recent" if now - started_at < _REFRESH_RETRY_WINDOW_SECONDS else "cooling"


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


def _shared_refresh(key, identity, section, compute_in, parameters=None, *, urgent=True):
    task = _refreshing.get(key)
    if task is not None:
        if urgent and task.ticket.get("waiter") is not None:
            compute_gate().promote(task.ticket["waiter"])
        return task
    ticket = {}

    async def refresh():
        from app.database import SessionLocal

        try:
            async with compute_gate().slot(urgent=urgent, ticket=ticket):
                async with SessionLocal() as session:
                    return await cached_dashboard_query(session, identity, section, lambda: compute_in(session),
                                                        parameters=parameters, remember_last=True)
        finally:
            _refreshing.pop(key, None)

    def observe(done):
        if not done.cancelled() and done.exception() is not None:
            logger.warning("控制台后台计算失败：%s section=%s", type(done.exception()).__name__, section)

    task = _refreshing[key] = asyncio.create_task(refresh())
    task.ticket = ticket
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
        if stale is not None:
            state = "started" if key in _refreshing else await _refresh_state(key)
            if state == "started":
                _shared_refresh(key, deepcopy(identity), section, compute_in, parameters, urgent=False)
            tag_request("cache", "stale" if state != "cooling" else "cooldown")
            # 冷却中不带 stale 标记：前端不用再短轮询，等下一次定时刷新。
            return {**stale, "stale": True} if state != "cooling" else stale
        task = _shared_refresh(key, deepcopy(identity), section, compute_in, parameters)
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
