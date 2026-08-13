"""Synchronize and audit the PostgreSQL legacy compatibility schema."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import MetaData, inspect, text

from app.database import engine
from app.legacy_schema import (
    LEGACY_METADATA,
    align_legacy_column_types,
    align_legacy_constraints,
    align_legacy_indexes,
    audit_legacy_schema,
    create_full_legacy_schema,
    ensure_legacy_indexes,
    load_legacy_schema_manifest,
)


def rebuild_column_order(connection, table_name: str) -> None:
    if connection.dialect.name != "postgresql":
        raise RuntimeError("Column-order rebuilding is supported only on PostgreSQL")
    dependencies = connection.execute(text("""
        SELECT conname
        FROM pg_constraint
        WHERE contype = 'f'
          AND (conrelid = to_regclass(:table_name) OR confrelid = to_regclass(:table_name))
    """), {"table_name": f'"{table_name}"'}).scalars().all()
    if dependencies:
        raise RuntimeError(f"Cannot reorder {table_name}; foreign keys exist: {dependencies}")

    source = LEGACY_METADATA.tables[table_name]
    temporary_name = f"__legacy_order_{table_name}"
    if temporary_name in inspect(connection).get_table_names():
        raise RuntimeError(f"Temporary table already exists: {temporary_name}")
    temporary_metadata = MetaData()
    temporary = source.to_metadata(temporary_metadata, name=temporary_name)
    for index in list(temporary.indexes):
        temporary.indexes.remove(index)
    temporary.create(connection)

    quote = connection.dialect.identifier_preparer.quote
    columns = ", ".join(quote(column.name) for column in source.c)
    source_count = connection.execute(text(f"SELECT count(*) FROM {quote(table_name)}")).scalar_one()
    connection.execute(text(
        f"INSERT INTO {quote(temporary_name)} ({columns}) "
        f"OVERRIDING SYSTEM VALUE SELECT {columns} FROM {quote(table_name)}"
    ))
    copied_count = connection.execute(text(f"SELECT count(*) FROM {quote(temporary_name)}")).scalar_one()
    if copied_count != source_count:
        raise RuntimeError(f"Row-count mismatch rebuilding {table_name}: {source_count} != {copied_count}")

    connection.execute(text(f"DROP TABLE {quote(table_name)}"))
    connection.execute(text(f"ALTER TABLE {quote(temporary_name)} RENAME TO {quote(table_name)}"))
    for column in source.c:
        if column.identity is None:
            continue
        connection.execute(text(f"""
            SELECT setval(
                pg_get_serial_sequence(:table_name, :column_name),
                COALESCE((SELECT max({quote(column.name)}) FROM {quote(table_name)}), 1),
                EXISTS (SELECT 1 FROM {quote(table_name)})
            )
        """), {"table_name": f'"{table_name}"', "column_name": column.name})


async def run(apply: bool, align_column_order: bool) -> None:
    manifest = load_legacy_schema_manifest()
    async with engine.connect() as connection:
        transaction = await connection.begin()
        await connection.run_sync(create_full_legacy_schema)
        await connection.run_sync(align_legacy_column_types)
        await connection.run_sync(align_legacy_constraints)
        await connection.run_sync(ensure_legacy_indexes)
        await connection.run_sync(align_legacy_indexes)
        report = await connection.run_sync(audit_legacy_schema)
        if align_column_order:
            for table_name in report["column_order_warnings"]:
                await connection.run_sync(rebuild_column_order, table_name)
            await connection.run_sync(ensure_legacy_indexes)
            report = await connection.run_sync(audit_legacy_schema)
        if report["errors"]:
            await transaction.rollback()
            raise RuntimeError(json.dumps(report, ensure_ascii=False, default=str))
        if apply:
            await transaction.commit()
        else:
            await transaction.rollback()
        print(json.dumps({
            "applied": apply,
            "expected_tables": manifest["table_count"],
            "expected_columns": sum(len(table["columns"]) for table in manifest["tables"]),
            "audit": report,
        }, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Commit the synchronized schema")
    parser.add_argument(
        "--align-column-order",
        action="store_true",
        help="Rebuild tables whose physical column order differs from the legacy manifest",
    )
    args = parser.parse_args()
    asyncio.run(run(args.apply, args.align_column_order))
