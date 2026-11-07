"""财务旁表与原 JSON 的一致性检查（11-07 慢查询 A3）。

两张旁表由触发器维护，只是派生数据：
- legacy_ar_payment_fields：legacy_finance_records 里 FAM_AR_Payment 行的 source_payload 拆出的字段；
- incoming_allocation_items：incoming_payments.allocations 展开的（费用、金额）明细。

check 只读，逐行比对旁表和按原 JSON 现算的结果，返回两边多出的行数；repair 只重建旁表，
不碰原表和业务数据。同步写入或回滚后可以跑：

    python -m app.core.finance_side_tables          # 只检查，有差异时退出码 1
    python -m app.core.finance_side_tables --repair  # 有差异时重建旁表
"""
import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.data_models.finance_side_ddl import ALLOCATION_EXPECTED, LEGACY_COLUMNS, LEGACY_EXPECTED, POSTGRES_BACKFILL

LEGACY_ACTUAL = f"SELECT {LEGACY_COLUMNS} FROM legacy_ar_payment_fields"
ALLOCATION_ACTUAL = "SELECT incoming_payment_id, fee_id, amt FROM incoming_allocation_items"


async def check(connection: AsyncConnection) -> dict[str, dict[str, int]]:
    """两张旁表各自“原数据有、旁表没有”和“旁表有、原数据没有”的行数（按多重集比较）。"""
    result = {}
    for name, expected, actual in (("legacy_ar_payment_fields", LEGACY_EXPECTED, LEGACY_ACTUAL),
                                   ("incoming_allocation_items", ALLOCATION_EXPECTED, ALLOCATION_ACTUAL)):
        missing = await connection.scalar(text(f"SELECT count(*) FROM (({expected}) EXCEPT ALL ({actual})) d"))
        extra = await connection.scalar(text(f"SELECT count(*) FROM (({actual}) EXCEPT ALL ({expected})) d"))
        result[name] = {"missing": int(missing or 0), "extra": int(extra or 0)}
    return result


async def repair(connection: AsyncConnection) -> None:
    """按原 JSON 重建两张旁表；在一个事务里做，期间来源表的写入会等锁（几百毫秒）。"""
    await connection.execute(text("LOCK TABLE legacy_finance_records, incoming_payments IN SHARE MODE"))
    for statement in POSTGRES_BACKFILL:
        await connection.execute(text(statement))


async def _main(argv: list[str]) -> int:
    from app.database import engine
    if engine.dialect.name != "postgresql":
        print("只在 PostgreSQL 上有旁表")
        return 0
    async with engine.connect() as connection:
        drift = await check(connection)
    print(drift)
    if not any(value["missing"] or value["extra"] for value in drift.values()):
        return 0
    if "--repair" not in argv:
        return 1
    async with engine.begin() as connection:
        await repair(connection)
    async with engine.connect() as connection:
        drift = await check(connection)
    print("重建后", drift)
    return 0 if not any(value["missing"] or value["extra"] for value in drift.values()) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_main(sys.argv[1:])))
