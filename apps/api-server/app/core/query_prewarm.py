"""后台预热：记住最近用过的已缓存查询，数据修订或业务日期变化后由主进程提前重算。

只登记已经走共享缓存的纯查询入口；重放仍经过原缓存流程（快照校验、重算锁、大小与内存
准入），结果与用户请求时完全相同。重放使用请求当时已认证的身份，权限变化后身份不同、
缓存键不同，旧登记只会白算一次，不会把结果交给其它身份。
"""
import asyncio
import hashlib
import json
import logging
import time
from copy import deepcopy
from datetime import date

from fastapi import HTTPException
from redis.exceptions import RedisError

from app.config import settings
from app.core import dashboard_metrics_redis as shared
from app.core import query_cache_store as store


logger = logging.getLogger(__name__)
_REGISTRY_PREFIX = "sunhold:prewarm:v1"
# 稳定等待：连续写入（批量导入、多步保存）结束后再重算，避免每步都整轮预热。
_SETTLE_SECONDS = 5
_REPLAY_TIMEOUT_SECONDS = 120
_replayers = {}


def register(kind, replay):
    """replay(name, identity, parameters, db) 须经原缓存流程计算并发布结果。"""
    _replayers[kind] = replay


def _canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _registry_key(bind):
    # 与查询缓存键相同：数据库连接只以摘要参与，凭据不进入 Redis。
    database = hashlib.sha256(bind.url.render_as_string(hide_password=False).encode()).hexdigest()
    return f"{_REGISTRY_PREFIX}:{database}"


# 缓存账号只开放 get/set/expire/eval 等命令：索引为一个 JSON 字符串（登记摘要 -> 最近使用时间），
# 由脚本原子更新并同时剔除过期与超出名额的登记；登记内容各存一个键，随有效期自然清理。
_TOUCH_INDEX = """
local raw = redis.call('GET', KEYS[1])
local index = raw and cjson.decode(raw) or {}
index[ARGV[1]] = tonumber(ARGV[2])
local items = {}
for field, used_at in pairs(index) do
    if used_at >= tonumber(ARGV[3]) then table.insert(items, {field, used_at}) end
end
table.sort(items, function(left, right) return left[2] > right[2] end)
local kept = {}
for position = 1, math.min(#items, tonumber(ARGV[4])) do kept[items[position][1]] = items[position][2] end
redis.call('SET', KEYS[1], cjson.encode(kept), 'EX', tonumber(ARGV[5]))
return 1
"""


async def remember(db, kind, name, identity, parameters):
    """登记失败只记日志，不影响本次查询。"""
    if not (settings.query_prewarm_enabled and settings.cache_redis_url.strip()) or kind not in _replayers:
        return
    try:
        entry = {"kind": kind, "name": name, "identity": store.json_value(identity),
                 "parameters": store.json_value(parameters)}
        payload = _canonical(entry)
        field = hashlib.sha256(payload.encode()).hexdigest()
        key = _registry_key(db.get_bind())
        retention = settings.query_prewarm_idle_days * 86400
        now = int(time.time())
        client = shared.client()
        await client.set(f"{key}:entry:{field}", payload, ex=retention)
        await client.eval(_TOUCH_INDEX, 1, f"{key}:index", field, now, now - retention,
                          settings.query_prewarm_max_entries, retention)
    except (RedisError, HTTPException, TypeError, ValueError) as exc:
        logger.warning("查询预热登记失败：%s kind=%s name=%s", type(exc).__name__, kind, name)


async def _recent_entries(client, key):
    raw = await client.get(f"{key}:index")
    try:
        index = json.loads(raw) if raw else {}
    except (ValueError, TypeError):
        index = {}
    if not isinstance(index, dict):
        index = {}
    cutoff = time.time() - settings.query_prewarm_idle_days * 86400
    fields = sorted((field for field, used_at in index.items() if isinstance(used_at, (int, float)) and used_at >= cutoff),
                    key=lambda field: index[field], reverse=True)[:settings.query_prewarm_max_entries]
    entries = []
    for field in fields:
        payload = await client.get(f"{key}:entry:{field}")
        try:
            entry = json.loads(payload) if payload else None
        except (ValueError, TypeError):
            entry = None
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


async def prewarm_once(sessions, bind):
    """按最近使用顺序逐项重放；已是最新的项只读一次缓存，几乎不耗时。"""
    started = time.monotonic()
    entries = await _recent_entries(shared.client(), _registry_key(bind))
    warmed = failed = 0
    for entry in entries:
        replay = _replayers.get(entry.get("kind"))
        if replay is None:
            continue
        try:
            async with sessions() as db, asyncio.timeout(_REPLAY_TIMEOUT_SECONDS):
                await replay(entry["name"], deepcopy(entry["identity"]), deepcopy(entry["parameters"]), db)
            warmed += 1
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # 单项失败（参数已失效、权限变化、超时）不影响其它项
            failed += 1
            logger.warning("查询预热单项失败：%s kind=%s name=%s", type(exc).__name__, entry.get("kind"), entry.get("name"))
    logger.info("查询预热完成：%s 项，失败 %s 项，耗时 %.1f 秒", warmed, failed, time.monotonic() - started)


async def _data_state(sessions):
    from app.core.dashboard_revision import dashboard_snapshot
    from app.core.finance_query_revision import finance_revision_snapshot

    async with sessions() as db:
        finance = await finance_revision_snapshot(db, "query.prewarm.finance_revision")
        dashboard = await dashboard_snapshot(db, "query.prewarm.dashboard_revision")
    return None if finance is None and dashboard is None else (finance, dashboard, date.today())


async def query_prewarm_loop():
    """仅由后台主进程运行；同一数据状态只预热一轮。"""
    from app.database import SessionLocal, engine

    if not (settings.query_prewarm_enabled and settings.cache_redis_url.strip()) or engine.dialect.name != "postgresql":
        return
    last_state = None
    while True:
        await asyncio.sleep(settings.query_prewarm_interval_seconds)
        try:
            state = await _data_state(SessionLocal)
            if state is None or state == last_state:
                continue
            await asyncio.sleep(_SETTLE_SECONDS)
            if await _data_state(SessionLocal) != state:
                continue
            await prewarm_once(SessionLocal, engine)
            last_state = state
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # Redis 未就绪或数据库暂时不可用时下一轮再试
            logger.warning("查询预热本轮跳过：%s", type(exc).__name__)
