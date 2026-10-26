"""问题反馈编号改为“BUG + 提交日期 + 当天流水”后，把旧的随机编号按提交时间重新编号（用户要求，2026-10-26）。

旧编号形如 BUG855D1A2F448043179850（BUG + 20 位十六进制）。按提交时间（北京时间）先后、同一天依次编号，
接在当天已有的新编号后面；已删除的问题一起改，回收站里看到的也是新编号。旧编号写进 data.legacy_serial_no，
按旧编号仍能搜到，需要还原时把 serial_no 改回该值即可。不改“最近更新”时间。
"""

import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.engine import Connection

MIGRATION_REVISION = "feedback_date_serial_v1"
FEEDBACK_TZ = ZoneInfo("Asia/Shanghai")
FEEDBACK_SERIAL_PREFIX = "BUG"
LEGACY_SERIAL = re.compile(r"BUG[0-9A-F]{20}")
DATE_SERIAL = re.compile(r"BUG(\d{8})(\d{3,4})")


def _beijing_day(value: datetime | str | None) -> str:
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value is None:
        value = datetime.now(timezone.utc)
    if value.tzinfo is None:  # SQLite 读出的时间不带时区，按 UTC 存储
        value = value.replace(tzinfo=timezone.utc)
    return f"{value.astimezone(FEEDBACK_TZ):%Y%m%d}"


def upgrade_feedback_date_serial(connection: Connection) -> int:
    """返回改号的条数；没有旧编号时不做任何改动，可重复执行。"""
    from app.models import BusinessRecord

    table = BusinessRecord.__table__
    # 用核心语句读写：已删除的问题也要改号，且不触发 ORM 的逻辑删除过滤和“最近更新”时间。
    rows = connection.execute(select(table.c.id, table.c.serial_no, table.c.created_at, table.c.data).where(
        table.c.module == "bug_feedback",
    ).order_by(table.c.created_at, table.c.id)).all()
    used: dict[str, int] = {}
    for row in rows:
        if match := DATE_SERIAL.fullmatch(row.serial_no or ""):
            used[match.group(1)] = max(used.get(match.group(1), 0), int(match.group(2)))
    changed = 0
    for row in rows:
        if not LEGACY_SERIAL.fullmatch(row.serial_no or ""):
            continue
        day = _beijing_day(row.created_at)
        used[day] = used.get(day, 0) + 1
        connection.execute(table.update().where(table.c.id == row.id).values(
            serial_no=f"{FEEDBACK_SERIAL_PREFIX}{day}{used[day]:03d}",
            data={**(row.data or {}), "legacy_serial_no": row.serial_no},
            updated_at=table.c.updated_at,
        ))
        changed += 1
    return changed
