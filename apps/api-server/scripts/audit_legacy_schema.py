"""Read-only SQL Server to SQLAlchemy legacy projection schema audit.

Uses Windows integrated authentication by default and never writes to the
legacy database.  It intentionally compares the compatibility projections,
not the application's unrelated extension tables.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from pathlib import Path

import pyodbc

# Allow `python scripts/audit_legacy_schema.py` from the API project root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import Base


DEFAULT_TABLES = (
    "CRM_Customer",
    "CRM_Customer_Contacts",
    "FCM_Contract",
    "FCM_Contract_Audit",
    "FCM_Contract_File",
    "Legal_Case",
    "Legal_Investigation",
    "Legal_Investigation_Task",
    "Legal_Investigation_Clue",
    "Legal_Investigation_Clue_Evidence",
    "Legal_Investigation_Clue_Evidence_File",
    "Legal_Investigation_Clue_File",
)


def legacy_columns(connection: pyodbc.Connection, table: str) -> dict[str, dict[str, object]]:
    cursor = connection.cursor()
    rows = cursor.execute(
        """
        SELECT c.name, ty.name, c.max_length, c.precision, c.scale, c.is_nullable
        FROM sys.columns AS c
        JOIN sys.tables AS t ON t.object_id = c.object_id
        JOIN sys.schemas AS s ON s.schema_id = t.schema_id
        JOIN sys.types AS ty ON ty.user_type_id = c.user_type_id
        WHERE s.name = 'dbo' AND t.name = ?
        ORDER BY c.column_id
        """,
        table,
    ).fetchall()
    return {
        row[0]: {
            "type": row[1],
            "max_length": row[2],
            "precision": row[3],
            "scale": row[4],
            "nullable": bool(row[5]),
        }
        for row in rows
    }


def projection_columns(table: str) -> dict[str, dict[str, object]]:
    metadata_table = Base.metadata.tables.get(table)
    if metadata_table is None:
        return {}
    return {
        column.name: {
            "type": str(column.type),
            "nullable": bool(column.nullable),
            "primary_key": bool(column.primary_key),
        }
        for column in metadata_table.columns
    }


def run(tables: Iterable[str], server: str, database: str) -> dict[str, object]:
    connection_string = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={server};DATABASE={database};Trusted_Connection=yes;"
        "TrustServerCertificate=yes"
    )
    report: dict[str, object] = {"server": server, "database": database, "tables": {}}
    with pyodbc.connect(connection_string, readonly=True) as connection:
        for table in tables:
            legacy = legacy_columns(connection, table)
            projected = projection_columns(table)
            report["tables"][table] = {
                "legacy_column_count": len(legacy),
                "projection_column_count": len(projected),
                "missing_table": not bool(projected),
                "missing_columns": sorted(set(legacy) - set(projected)),
                "extra_projection_columns": sorted(set(projected) - set(legacy)),
                "legacy": legacy,
                "projection": projected,
            }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="localhost")
    parser.add_argument("--database", default="PRD_CRM_GD_20200211")
    parser.add_argument("--table", action="append", dest="tables")
    parser.add_argument("--output")
    args = parser.parse_args()
    report = run(args.tables or DEFAULT_TABLES, args.server, args.database)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(payload + "\n")
    else:
        print(payload)


if __name__ == "__main__":
    main()
