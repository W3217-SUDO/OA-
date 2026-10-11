"""控制台统计的共享存储和带所有权校验的重算锁，不访问数据库会话。"""
import json
import logging
import re
import hashlib
from math import ceil
from pathlib import Path
from secrets import token_hex

from fastapi import HTTPException
from redis.asyncio import BlockingConnectionPool, Redis
from redis.asyncio.connection import parse_url
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff
from redis.exceptions import RedisError

from app.config import settings


logger = logging.getLogger(__name__)
_client: Redis | None = None
_revision: str | None = None
_RELEASE = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""
_PUBLISH = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then
    return 0
end
redis.call('SET', KEYS[2], ARGV[2], 'EX', ARGV[3])
return 1
"""


def unavailable(detail="控制台共享缓存暂不可用，请稍后重试"):
    return HTTPException(503, detail, headers={"Retry-After": "1"})


async def start_dashboard_metrics_cache():
    global _client, _revision
    if not settings.cache_redis_url.strip():
        return
    if _client is not None:
        raise unavailable("控制台共享缓存连接已初始化")
    try:
        cache_options = parse_url(settings.cache_redis_url)
        queue_options = parse_url(settings.redis_url)
    except ValueError as exc:
        raise unavailable("控制台共享缓存连接配置无效") from exc

    def database(options):
        return (options.get("host", "localhost"), options.get("port", 6379),
                options.get("path"), options.get("db", 0))

    if database(cache_options) == database(queue_options):
        raise unavailable("共享缓存必须使用与任务队列不同的 Redis 数据库")
    try:
        _revision = _source_digest(Path(__file__).resolve().parent.parent)
    except OSError as exc:
        logger.error("控制台共享缓存源码摘要失败：%s", type(exc).__name__)
        raise unavailable("控制台共享缓存无法确认源码版本") from exc
    pool = BlockingConnectionPool.from_url(settings.cache_redis_url)
    # URL 查询参数不能取消连接数量和网络超时边界，也不隐式重试故障请求。
    pool.max_connections = settings.cache_redis_max_connections
    pool.timeout = settings.cache_redis_timeout_seconds
    pool.connection_kwargs.update(
        socket_connect_timeout=settings.cache_redis_timeout_seconds,
        socket_timeout=settings.cache_redis_timeout_seconds,
        decode_responses=False, retry=Retry(NoBackoff(), 0), retry_on_timeout=False,
    )
    _client = Redis.from_pool(pool)
    try:
        await _client.ping()
    except RedisError as exc:
        await close_dashboard_metrics_cache()
        logger.error("控制台共享缓存初始化失败：%s", type(exc).__name__)
        raise unavailable() from exc


async def close_dashboard_metrics_cache():
    global _client, _revision
    client, _client = _client, None
    _revision = None
    if client is not None:
        await client.aclose()


def client():
    if _client is None:
        raise unavailable("控制台共享缓存连接尚未初始化")
    return _client


def _source_digest(root):
    # 只在启用时读取 app Python 源码；相对路径和内容都参与跨进程一致的版本摘要。
    digest = hashlib.sha256()
    paths = sorted(root.rglob("*.py"), key=lambda path: path.relative_to(root).as_posix())
    if not paths:
        raise unavailable("控制台共享缓存未找到应用源码")
    for path in paths:
        name = path.relative_to(root).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(name).to_bytes(4, "big"))
        digest.update(name)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def source_revision():
    if _revision is None:
        raise unavailable("控制台共享缓存源码版本尚未初始化")
    return _revision


def _valid_entry(entry):
    if (not isinstance(entry, dict) or set(entry) != {"snapshot", "result"}
            or not isinstance(entry["snapshot"], str)
            or re.fullmatch(r"[0-9]+:[0-9]+:(?:[0-9]+(?:,[0-9]+)*)?", entry["snapshot"]) is None):
        return False
    result = entry["result"]
    if not isinstance(result, dict) or set(result) != {"metrics"}:
        return False
    metrics = result["metrics"]
    if not isinstance(metrics, list) or len(metrics) != 8:
        return False
    fields = {"key", "label", "tone", "value", "route"}
    return all(isinstance(item, dict) and set(item) == fields
               and all(isinstance(value, str) for value in item.values()) for item in metrics)


async def read(key):
    payload = await client().get(key + ":data")
    if payload is None:
        return None
    try:
        entry = json.loads(payload)
    except (ValueError, UnicodeError, TypeError) as exc:
        raise unavailable("控制台共享缓存格式损坏，请核查服务日志") from exc
    if not _valid_entry(entry):
        raise unavailable("控制台共享缓存字段类型无效，请核查服务日志")
    return entry


async def acquire(key):
    token = token_hex(24)
    # 计算有单独超时；租约额外覆盖查询取消和网络往返，发布仍再次原子校验所有权。
    lease_ms = ceil((settings.dashboard_metrics_compute_timeout_seconds
                     + 2 * settings.cache_redis_timeout_seconds + 10) * 1000)
    acquired = await client().set(key + ":lock", token, nx=True, px=lease_ms)
    return token if acquired else None


async def publish(key, token, snapshot, result):
    entry = {"snapshot": snapshot, "result": result}
    if not _valid_entry(entry):
        raise unavailable("控制台统计结果不符合共享缓存格式")
    payload = json.dumps(entry,
                         ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    if not await client().eval(_PUBLISH, 2, key + ":lock", key + ":data",
                               token, payload, settings.dashboard_metrics_cache_ttl_seconds):
        raise unavailable("控制台统计重算锁已失效，请重新查询")


async def release(key, token):
    await client().eval(_RELEASE, 1, key + ":lock", token)
