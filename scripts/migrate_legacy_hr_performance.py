#!/usr/bin/env python3
"""Migrate active legacy HR commission settings into hr_subrecords."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "apps" / "api-server" / "legal_platform.db"
ACTOR = "legacy_hr_performance_migration"


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def json_number(value: Any) -> int | float | None:
    if value is None or clean(value) == "":
        return None
    number = Decimal(str(value))
    return int(number) if number == number.to_integral_value() else float(number)


def date_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    return clean(value)[:10]


def read_source(server: str, database: str, driver: str) -> list[dict[str, Any]]:
    try:
        import pyodbc
    except ImportError as exc:
        raise RuntimeError("pyodbc is required to read the legacy SQL Server") from exc
    connection_string = (
        f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};"
        "Trusted_Connection=yes;ApplicationIntent=ReadOnly;TrustServerCertificate=yes;"
    )
    query = """
        SELECT SettingId,StaffName,Salary,AyRate,PgRate,KtRate,TcRate,WsRate,
               AyFixed,PgFixed,KtFixed,TcFixed,WsFixed,AnnualFrom,AnnualEnd,IsActived
        FROM dbo.HR_Staff_Performance
        ORDER BY SettingId
    """
    with pyodbc.connect(connection_string, autocommit=True) as connection:
        cursor = connection.cursor()
        tables = {clean(row[0]) for row in cursor.execute(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'"
        )}
        if "HR_Staff_Performance" not in tables:
            raise RuntimeError("legacy source table missing: HR_Staff_Performance")
        columns = [column[0] for column in cursor.execute(query).description]
        return [dict(zip(columns, row)) for row in cursor]


def migrate(connection: sqlite3.Connection, source_rows: list[dict[str, Any]], dry_run: bool) -> dict[str, int]:
    connection.row_factory = sqlite3.Row
    employees = {
        clean(row["owner"]).casefold(): int(row["id"])
        for row in connection.execute("SELECT id,owner FROM business_records WHERE module='hr'")
        if clean(row["owner"])
    }
    existing = {
        int(row[0]) for row in connection.execute("SELECT DISTINCT employee_id FROM hr_subrecords WHERE kind='commission'")
    }
    stats = {"migrated": 0, "skipped": 0, "unmatched": 0}
    for row in source_rows:
        setting_id = row["SettingId"]
        username = clean(row["StaffName"])
        if clean(row["IsActived"]).upper() != "T":
            stats["skipped"] += 1
            continue
        employee_id = employees.get(username.casefold())
        if employee_id is None:
            stats["unmatched"] += 1
            print(f"UNMATCHED SettingId={setting_id} StaffName={username}")
            continue
        if employee_id in existing:
            stats["skipped"] += 1
            print(f"SKIP SettingId={setting_id} StaffName={username}: commission already exists")
            continue
        data = {
            "base_salary": json_number(row["Salary"]),
            "source_rate": json_number(row["AyRate"]), "source_fixed": json_number(row["AyFixed"]),
            "quality_rate": json_number(row["PgRate"]), "quality_fixed": json_number(row["PgFixed"]),
            "hearing_rate": json_number(row["KtRate"]), "hearing_fixed": json_number(row["KtFixed"]),
            "document_rate": json_number(row["WsRate"]), "document_fixed": json_number(row["WsFixed"]),
            "investigation_rate": json_number(row["TcRate"]), "investigation_fixed": json_number(row["TcFixed"]),
            "start_date": date_text(row["AnnualFrom"]), "end_date": date_text(row["AnnualEnd"]),
        }
        print(f"{'DRY-RUN' if dry_run else 'MIGRATE'} SettingId={setting_id} StaffName={username} employee_id={employee_id}")
        if not dry_run:
            connection.execute(
                "INSERT INTO hr_subrecords(employee_id,kind,data,created_by,updated_by) VALUES(?,?,?,?,?)",
                (employee_id, "commission", json.dumps(data, ensure_ascii=False, sort_keys=True), ACTOR, ACTOR),
            )
        existing.add(employee_id)
        stats["migrated"] += 1
    if dry_run:
        connection.rollback()
    else:
        connection.commit()
    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--server", default=".")
    parser.add_argument("--database", default="PRD_CRM_GD_20200211")
    parser.add_argument("--driver", default="SQL Server")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = read_source(args.server, args.database, args.driver)
    with sqlite3.connect(args.db) as connection:
        stats = migrate(connection, rows, args.dry_run)
    print(json.dumps(stats, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
