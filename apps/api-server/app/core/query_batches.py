"""Bound expanding IN parameters without partitioning projection context."""


async def _scalars_in_batches(db, values, statement_for_batch):
    # At most two IN expressions per caller batch (numeric/string JSON ids).
    # 800 values leaves room for JSON paths and fixed predicates even on
    # SQLite builds with the historical 999-variable limit.
    values = list(values)
    rows = []
    for offset in range(0, len(values), 400):
        statement = statement_for_batch(values[offset:offset + 400])
        rows.extend((await db.scalars(statement)).all())
    return rows
