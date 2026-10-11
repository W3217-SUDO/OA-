"""只读查询共享的快照校验、有限等待和重算锁生命周期。"""
import asyncio
import logging
import sys
from datetime import date
from time import monotonic

from redis.exceptions import RedisError
from sqlalchemy import Text, cast, func, select

from app.config import settings
from app.core.request_metrics import measure_phase


logger = logging.getLogger(__name__)


async def visible_snapshot(db, phase="query.cache.snapshot"):
    with measure_phase(phase):
        row = (await db.execute(select(
            cast(func.pg_current_snapshot(), Text).label("snapshot"),
            cast(func.pg_current_xact_id_if_assigned(), Text).label("own_xid"),
            func.current_setting("transaction_isolation").label("isolation"),
        ))).one()
    return row.snapshot if row.own_xid is None and row.isolation == "read committed" else None


async def release_lock(store, key, token, primary_error=None):
    # 取消也等待所有权校验解锁完成，不留下仍在运行的清理任务。
    cleanup = asyncio.create_task(store.release(key, token))
    try:
        await asyncio.shield(cleanup)
    except asyncio.CancelledError as cancelled:
        try:
            await cleanup
        except RedisError as exc:
            logger.error("共享缓存取消查询后的解锁失败：%s", type(exc).__name__)
        raise cancelled
    except RedisError as exc:
        if primary_error is None:
            raise
        logger.error("共享缓存失败查询后的解锁失败：%s", type(exc).__name__)


async def read_shared_query(db, *, key_for_date, compute, store, snapshot_reader,
                            release, label, today=date.today):
    deadline = monotonic() + settings.dashboard_metrics_cache_wait_seconds
    while True:
        if monotonic() >= deadline:
            raise store.unavailable(f"{label}仍在重算，请稍后重试")
        if db.new or db.dirty or db.deleted:
            return await compute()
        if db.in_transaction():
            snapshot = await snapshot_reader(db)
            if snapshot is None:
                return await compute()
            if db.new or db.dirty or db.deleted:
                return await compute()
            # 调用者须为纯身份字典且无 ORM 依赖；只结束已确认无写入的读事务。
            await db.rollback()
        business_date = today()
        key = key_for_date(business_date)
        cached = await store.read(key)
        if cached is not None:
            end_snapshot = await snapshot_reader(db)
            if end_snapshot == cached["snapshot"] and business_date == today():
                return cached["result"]
            snapshot = end_snapshot
            if snapshot is None:
                return await compute()
            if db.new or db.dirty or db.deleted:
                return await compute()
            await db.rollback()
        token = await store.acquire(key)
        if token is not None:
            try:
                snapshot = await snapshot_reader(db)
                if snapshot is None:
                    return await compute()
                cached = await store.read(key)
                if (cached is not None and cached["snapshot"] == snapshot
                        and business_date == today()):
                    end_snapshot = await snapshot_reader(db)
                    if end_snapshot == snapshot and business_date == today():
                        return cached["result"]
                    snapshot = end_snapshot
                    if snapshot is None:
                        return await compute()
                try:
                    async with asyncio.timeout(settings.dashboard_metrics_compute_timeout_seconds):
                        result = await compute()
                except TimeoutError as exc:
                    raise store.unavailable(f"{label}计算超时，请稍后重试") from exc
                end_snapshot = await snapshot_reader(db)
                if (snapshot == end_snapshot and business_date == today()
                        and not (db.new or db.dirty or db.deleted)):
                    await store.publish(key, token, snapshot, result)
                return result
            finally:
                await release(key, token, sys.exception())
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise store.unavailable(f"{label}仍在重算，请稍后重试")
        await asyncio.sleep(min(0.1, remaining))
