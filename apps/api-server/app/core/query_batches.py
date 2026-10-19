"""Bound expanding IN parameters without partitioning projection context."""


def _batch_size(db) -> int:
    # SQLite 历史上限为 999 个变量；PostgreSQL 的绑定参数上限为 32767。
    # 调用方每批最多带两个 IN 表达式（数值/字符串 JSON id），所以 PostgreSQL
    # 取 10000，避免十万级 id 被切成数百条语句。
    try:
        return 10000 if db.get_bind().dialect.name == "postgresql" else 400
    except Exception:  # noqa: BLE001 - 无法判断方言时退回保守批量
        return 400


async def _scalars_in_batches(db, values, statement_for_batch):
    # At most two IN expressions per caller batch (numeric/string JSON ids).
    # 800 values leaves room for JSON paths and fixed predicates even on
    # SQLite builds with the historical 999-variable limit.
    values = list(values)
    size = _batch_size(db)
    rows = []
    for offset in range(0, len(values), size):
        statement = statement_for_batch(values[offset:offset + size])
        rows.extend((await db.scalars(statement)).all())
    return rows
