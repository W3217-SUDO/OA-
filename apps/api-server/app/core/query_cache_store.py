"""有大小准入限制的 JSON 查询结果存储，复用现有 Redis 连接和锁。"""
import asyncio
import json
import logging
import re
from math import isfinite

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import DeclarativeBase
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.core import dashboard_metrics_redis as shared


logger = logging.getLogger(__name__)


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


async def publish(key, token, snapshot, result):
    # 文件、流和自定义响应的状态、头部不可被 JSON 缓存替换。
    if isinstance(result, Response):
        logger.info("查询结果未进入共享缓存：响应对象；key=%s", key)
        return
    payload = await asyncio.to_thread(_encode, snapshot, result)
    if payload is None:
        logger.info("查询结果未进入共享缓存：超过大小准入限制；limit=%s key=%s",
                    settings.query_cache_max_payload_bytes, key)
        return
    if not await shared.client().eval(shared._PUBLISH, 2, key + ":lock", key + ":data",
                                      token, payload, settings.query_cache_ttl_seconds):
        raise unavailable("查询重算锁已失效，请重新查询")
