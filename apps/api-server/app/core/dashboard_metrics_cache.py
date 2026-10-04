"""仅在账号、业务日期和数据库可见快照不变时复用控制台统计。"""
import asyncio
import json
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date
from time import monotonic

from sqlalchemy import Text, cast, func, select

from app.core.dashboard_metrics import dashboard_metrics
from app.core.request_metrics import measure_phase


_MAX_ENTRIES = 64
_MAX_AGE_SECONDS = 300


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
