"""费用查询、待退费列表的筛选事实缓存：与筛选条件、页码无关的部分每个数据修订只算一次。

两张列表原本对每次请求（换一个筛选条件、翻一页）都把全部费用的付款、开票、到账、退费聚合
重新计算一遍，再在内存中逐条筛选、分页。这些聚合只取决于身份可见范围与数据修订，与筛选条件
无关；这里把“每笔费用的筛选与合计事实”按身份 + 财务数据修订缓存（压缩后存入共享缓存，命中
时同样核对修订号），请求只在事实上套用与原逻辑同一个判定函数，再只为当前页取完整行。
"""
import asyncio
import logging
import zlib
from types import SimpleNamespace

import orjson

from app.config import settings
from app.core import dashboard_metrics_redis as shared
from app.core import query_cache_store as store


logger = logging.getLogger(__name__)
_FORMAT = 1


def _encode(snapshot, result):
    payload = zlib.compress(orjson.dumps({"format": _FORMAT, "snapshot": snapshot, "result": result}), 1)
    return payload if len(payload) <= settings.fee_facts_cache_max_payload_bytes else None


def _decode(payload):
    try:
        entry = orjson.loads(zlib.decompress(payload))
    except (zlib.error, orjson.JSONDecodeError, TypeError) as exc:
        raise store.unavailable("费用筛选事实缓存格式损坏，请核查服务日志") from exc
    if (not isinstance(entry, dict) or entry.get("format") != _FORMAT
            or not isinstance(entry.get("snapshot"), str) or "result" not in entry):
        raise store.unavailable("费用筛选事实缓存字段类型无效，请核查服务日志")
    return {"snapshot": entry["snapshot"], "result": entry["result"]}


async def _read(key):
    payload = await shared.client().get(key + ":data")
    return None if payload is None else await asyncio.to_thread(_decode, payload)


async def _publish(key, token, snapshot, result):
    # 与查询缓存相同的内存准入；超限只是不缓存，本次结果照常返回。
    if not await store._memory_allows_publish():
        return
    payload = await asyncio.to_thread(_encode, snapshot, result)
    if payload is None:
        logger.info("费用筛选事实未进入共享缓存：压缩后超过大小限制；key=%s", key)
        return
    if not await shared.client().eval(shared._PUBLISH, 2, key + ":lock", key + ":data",
                                      token, payload, settings.query_cache_ttl_seconds):
        raise store.unavailable("查询重算锁已失效，请重新查询")


_STORE = SimpleNamespace(read=_read, acquire=store.acquire, unavailable=store.unavailable, publish=_publish)


async def _cached(db, identity, namespace, parameters, compute):
    from app.core.finance_query_revision import finance_revision_snapshot
    from app.core.query_cache import _cached_query

    if not settings.cache_redis_url.strip():
        return await compute()
    return await _cached_query(db, identity, namespace, parameters, compute,
                               snapshot_reader=finance_revision_snapshot, query_store=_STORE)


def _columns(rows):
    # 按列存放：数万行重复的字段名不进入缓存，解码后再还原为与实时计算相同的字典。
    fields = list(rows[0]) if rows else []
    return {"fields": fields, "rows": [[row[field] for field in fields] for row in rows]}


def _rows(table):
    fields = table["fields"]
    return [dict(zip(fields, values)) for values in table["rows"]]


async def fee_query_facts(identity, db, *, scope):
    """费用查询的全部可见费用事实（顺序与实时计算相同）。不适用于控制台限定费用集合的身份。"""
    from app.core.finance import _invoice_case_fee_rows

    if "_dashboard_fee_ids" in identity:
        raise ValueError("控制台限定费用集合不使用费用事实缓存")

    async def compute():
        rows = await _invoice_case_fee_rows(
            identity, db, scope=scope, include_all_fee_types=True, summary_only=True, facts_only=True,
        )
        return _columns(rows)

    return _rows(await _cached(db, identity, "finance.facts.fee_query", {"scope": scope}, compute))


def fee_query_row_passes(facts, *, external_only, refund_amount_from, refund_amount_to, payment_status, unpaid_official):
    """与 _fee_query_rows 末段的筛选逐项一致（金额为已按权限遮蔽的值）。"""
    if external_only and facts["is_internal"]:
        return False
    refund_amount = facts["refund_requested_amount"]
    if refund_amount_from is not None and (refund_amount is None or float(refund_amount) < refund_amount_from):
        return False
    if refund_amount_to is not None and (refund_amount is None or float(refund_amount) > refund_amount_to):
        return False
    if payment_status and str(facts["payment_status"] or "") != payment_status:
        return False
    if unpaid_official and not facts["unpaid_official"]:
        return False
    return True


async def refund_pending_base(identity, db):
    """待退费的全部候选行（已按待退、非 R100 筛过并排序），每行附带筛选事实与未遮蔽的申请退费额。"""
    from app.core.finance import _refund_case_fee_base

    if "_dashboard_fee_ids" in identity:
        raise ValueError("控制台限定费用集合不使用费用事实缓存")

    async def compute():
        return store.json_value(await _refund_case_fee_base(identity, db))

    return await _cached(db, identity, "finance.facts.refund_pending", {}, compute)
