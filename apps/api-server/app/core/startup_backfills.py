"""登记并执行一次性历史业务数据修正。"""

from collections.abc import Awaitable, Callable

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.startup_migrations import lock_startup_transaction
from app.models import BusinessRecord, WorkflowEvent


HISTORICAL_BACKFILL_REVISION = "startup_historical_backfills_v1"


async def run_historical_backfills(
    db: AsyncSession,
    backfill_clue_case_dates: Callable[[AsyncSession], Awaitable[int]],
    *,
    force: bool = False,
) -> bool:
    """在调用方事务内修正历史数据；显式 force 可安全重跑。"""
    from app.core.legacy_sync import _sync_legacy_case

    await db.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (key VARCHAR(128) PRIMARY KEY)"))
    if not force and (await db.execute(
        text("SELECT key FROM schema_migrations WHERE key = :key"),
        {"key": HISTORICAL_BACKFILL_REVISION},
    )).first():
        return False

    # SQLite 旧库可能没有启用外键，清除仅存于历史数据的孤立流程事件。
    await db.execute(delete(WorkflowEvent).where(
        WorkflowEvent.record_id.not_in(select(BusinessRecord.id))
    ))
    deficit_archives = (await db.scalars(select(BusinessRecord).where(
        BusinessRecord.module == "case",
        BusinessRecord.status == "待归档审核",
    ))).all()
    for record in deficit_archives:
        data = dict(record.data or {})
        if data.get("archive_type") != "deficit" or data.get("archive_internal_reviewed_at"):
            continue
        record.status = "亏损内审"
        record.data = {
            **data,
            "case_phase": "亏损内审",
            "case_phase_id": 106016,
            "archive_status": "待内部审核",
            "archive_status_code": 7,
        }
        await _sync_legacy_case(record, {"username": "system"}, db)
    await backfill_clue_case_dates(db)
    if not force:
        await db.execute(
            text("INSERT INTO schema_migrations (key) VALUES (:key)"),
            {"key": HISTORICAL_BACKFILL_REVISION},
        )
    return True


async def rerun_historical_backfills(
    session_factory: async_sessionmaker[AsyncSession],
    backfill_clue_case_dates: Callable[[AsyncSession], Awaitable[int]],
) -> None:
    """显式重跑历史修正，并自行管理跨进程锁及提交事务。"""
    async with session_factory() as db:
        await lock_startup_transaction(await db.connection())
        await run_historical_backfills(db, backfill_clue_case_dates, force=True)
        await db.commit()
