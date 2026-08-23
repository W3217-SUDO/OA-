"""Audit and explicitly backfill unique contract/customer relations.

This utility deliberately stays outside the API.  It never guesses from a
duplicate customer name and only writes when --apply is supplied.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path
from typing import Any


CUSTOMER_MODULE = "customer"
RELATED_MODULES = {"contract", "case"}


def _normalise_name(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _parse_data(value: object) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return dict(value)
    if not isinstance(value, str):
        return {}
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _linked_customer_id(data: dict[str, Any]) -> int:
    for key in ("customer_id", "customer_record_id"):
        try:
            value = int(data.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        if value > 0:
            return value
    return 0


def _records(connection: sqlite3.Connection, module: str) -> list[sqlite3.Row]:
    connection.row_factory = sqlite3.Row
    return connection.execute(
        "SELECT id, module, serial_no, title, customer, data FROM business_records WHERE module = ?",
        (module,),
    ).fetchall()


def scan_connection(connection: sqlite3.Connection) -> dict[str, Any]:
    """Return an audit report without modifying the database."""
    customer_by_name: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for customer in _records(connection, CUSTOMER_MODULE):
        customer_by_name[_normalise_name(customer["title"])].append(customer)

    report: dict[str, Any] = {
        "proposed_updates": [],
        "already_linked": [],
        "ambiguous": [],
        "unmatched": [],
        "invalid_data": [],
    }
    for module in sorted(RELATED_MODULES):
        for record in _records(connection, module):
            data = _parse_data(record["data"])
            record_info = {"id": record["id"], "module": module, "serial_no": record["serial_no"]}
            if data is None:
                report["invalid_data"].append(record_info)
                continue
            if _linked_customer_id(data):
                report["already_linked"].append(record_info)
                continue
            name = _normalise_name(record["customer"])
            candidates = customer_by_name.get(name, []) if name else []
            if len(candidates) == 1:
                customer = candidates[0]
                report["proposed_updates"].append(
                    {
                        **record_info,
                        "customer_id": customer["id"],
                        "customer_no": customer["serial_no"] or "",
                        "customer_name": customer["title"],
                    }
                )
            elif len(candidates) > 1:
                report["ambiguous"].append({**record_info, "customer_name": record["customer"], "candidate_ids": [row["id"] for row in candidates]})
            else:
                report["unmatched"].append({**record_info, "customer_name": record["customer"]})
    return report


def apply_unique_backfill(connection: sqlite3.Connection, report: dict[str, Any]) -> int:
    """Apply only the proposals created by scan_connection, atomically."""
    updates = report["proposed_updates"]
    with connection:
        for proposal in updates:
            row = connection.execute("SELECT data FROM business_records WHERE id = ?", (proposal["id"],)).fetchone()
            if row is None:
                raise ValueError(f"record {proposal['id']} disappeared during the audit")
            data = _parse_data(row[0])
            if data is None or _linked_customer_id(data):
                raise ValueError(f"record {proposal['id']} is no longer eligible for a unique backfill")
            data["customer_id"] = proposal["customer_id"]
            if not data.get("customer_no"):
                data["customer_no"] = proposal["customer_no"]
            connection.execute(
                "UPDATE business_records SET data = ? WHERE id = ?",
                (json.dumps(data, ensure_ascii=False, separators=(",", ":")), proposal["id"]),
            )
    return len(updates)


def audit_database(database: Path, apply: bool = False) -> dict[str, Any]:
    with closing(sqlite3.connect(database)) as connection:
        report = scan_connection(connection)
        report["applied"] = apply_unique_backfill(connection, report) if apply else 0
        return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit unique customer links for contracts and cases.")
    parser.add_argument("--database", type=Path, required=True, help="SQLite database to inspect; no default is used.")
    parser.add_argument("--apply", action="store_true", help="Persist only unambiguous matches from this audit run.")
    args = parser.parse_args()
    print(json.dumps(audit_database(args.database, apply=args.apply), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
