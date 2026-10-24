"""有大小准入限制的 JSON 查询结果存储，复用现有 Redis 连接和锁。"""
import asyncio
import json
import logging
import re
from math import isfinite
from time import monotonic

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from redis.exceptions import ResponseError
from sqlalchemy.orm import DeclarativeBase
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.core import dashboard_metrics_redis as shared


logger = logging.getLogger(__name__)
MAX_TTL_SECONDS = 86400
_MEMORY_CHECK_SECONDS = 30
_memory_state = {"checked_at": None, "allowed": True}


def unavailable(detail="查询共享缓存暂不可用，请稍后重试"):
    return HTTPException(503, detail, headers={"Retry-After": "1"})


def _reject_constant(value):
    raise ValueError("无效 JSON 数值")


def _reject_dependency(value):
    raise TypeError("查询缓存不得编码 Request 或 ORM 依赖")


def json_value(value):
    return jsonable_encoder(value, custom_encoder={Request: _reject_dependency, DeclarativeBase: _reject_dependency})


def _finite_float(value):
    number = float(value)
    if not isfinite(number):
        raise ValueError("无效 JSON 数值")
    return number


def _decode(payload):
    try:
        if len(payload) > settings.query_cache_max_payload_bytes:
            raise ValueError("缓存结果超过大小限制")
        entry = json.loads(payload, parse_constant=_reject_constant, parse_float=_finite_float)
    except (ValueError, UnicodeError, TypeError, RecursionError) as exc:
        raise unavailable("查询共享缓存格式损坏，请核查服务日志") from exc
    if (not isinstance(entry, dict) or set(entry) != {"snapshot", "result"}
            or not isinstance(entry["snapshot"], str)
            or re.fullmatch(r"[0-9]+:[0-9]+:(?:[0-9]+(?:,[0-9]+)*)?", entry["snapshot"]) is None):
        raise unavailable("查询共享缓存字段类型无效，请核查服务日志")
    return entry


def _encode(snapshot, result):
    entry = {"snapshot": snapshot, "result": json_value(result)}
    # 分块编码，超限立即停止；大列表的编码不阻塞事件循环。
    chunks, size = [], 0
    for chunk in json.JSONEncoder(ensure_ascii=True, separators=(",", ":"), allow_nan=False).iterencode(entry):
        size += len(chunk)
        if size > settings.query_cache_max_payload_bytes:
            return None
        chunks.append(chunk)
    return "".join(chunks)


async def read(key):
    payload = await shared.client().get(key + ":data")
    return None if payload is None else await asyncio.to_thread(_decode, payload)


async def acquire(key):
    return await shared.acquire(key)


async def release(key, token):
    await shared.release(key, token)


async def publish(key, token, snapshot, result, *, ttl_seconds=None):
    ttl = settings.query_cache_ttl_seconds if ttl_seconds is None else ttl_seconds
    if type(ttl) is not int or not 1 <= ttl <= MAX_TTL_SECONDS:
        raise ValueError("共享查询缓存有效期必须为 1 至 86400 秒")
    await _publish(key, token, snapshot, result, ttl)


async def _memory_allows_publish():
    # Redis 不淘汰旧键，写满后连重算锁都无法获取；接近上限时只停写新结果，查询照常实时计算。
    checked_at = _memory_state["checked_at"]
    if checked_at is not None and monotonic() - checked_at < _MEMORY_CHECK_SECONDS:
        return _memory_state["allowed"]
    try:
        info = await shared.client().info("memory")
    except ResponseError:
        allowed = True  # 账号无 INFO 权限时不阻断写入
    else:
        limit = int(info.get("maxmemory") or 0)
        allowed = not limit or int(info.get("used_memory") or 0) < limit * settings.query_cache_memory_ratio
    if not allowed and _memory_state["allowed"]:
        logger.warning("Redis 已用内存超过 %.0f%%，暂停写入新的查询缓存结果", settings.query_cache_memory_ratio * 100)
    _memory_state.update(checked_at=monotonic(), allowed=allowed)
    return allowed


async def _publish(key, token, snapshot, result, ttl):
    # 文件、流和自定义响应的状态、头部不可被 JSON 缓存替换。
    if isinstance(result, Response):
        logger.info("查询结果未进入共享缓存：响应对象；key=%s", key)
        return
    # 同一数据修订下，上次已判定超限的查询结果不会变小：直接跳过整份结果的 JSON 编码（几十兆的结果会白白
    # 编码数秒才发现超限）。标记带上限值与数据修订号，数据变化或上限调整后会重新判定。
    marker = key + ":oversize"
    marker_value = f"{settings.query_cache_max_payload_bytes}|{snapshot}"
    stored = await shared.client().get(marker)
    if (stored.decode() if isinstance(stored, bytes) else stored) == marker_value:
        logger.info("查询结果未进入共享缓存：同一数据修订下已判定超限；key=%s", key)
        return
    if not await _memory_allows_publish():
        return
    payload = await asyncio.to_thread(_encode, snapshot, result)
    if payload is None:
        await shared.client().set(marker, marker_value, ex=ttl)
        logger.info("查询结果未进入共享缓存：超过大小准入限制；limit=%s key=%s",
                    settings.query_cache_max_payload_bytes, key)
        return
    if not await shared.client().eval(shared._PUBLISH, 2, key + ":lock", key + ":data",
                                      token, payload, ttl):
        raise unavailable("查询重算锁已失效，请重新查询")
