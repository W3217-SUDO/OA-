"""Restore a row-18 GET export into a standalone evidence database.

This intentionally does not use the OA ORM or its database URL.  The output
must not exist and is created with evidence-only tables, so it cannot mutate a
development or production OA database.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("export_json", type=Path)
    parser.add_argument("isolated_db", type=Path)
    args = parser.parse_args()
    if args.isolated_db.exists():
        raise SystemExit("Refusing to overwrite an existing database.")
    if args.isolated_db.name.lower() == "legal_platform.db":
        raise SystemExit("Refusing to use the OA runtime database filename.")

    raw = args.export_json.read_bytes()
    payload = json.loads(raw.decode("utf-8-sig"))
    if payload.get("schema") != "oa-row18-readonly-export-v1":
        raise SystemExit("Unsupported snapshot schema.")
    if payload.get("serial_no") != "RW2413300774776":
        raise SystemExit("Snapshot is not the assigned row-18 record.")

    args.isolated_db.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(args.isolated_db)
    try:
        connection.executescript(
            """
            CREATE TABLE snapshot_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE snapshot_entities (
                kind TEXT NOT NULL, source_id TEXT NOT NULL, serial_no TEXT,
                payload_json TEXT NOT NULL, PRIMARY KEY (kind, source_id)
            );
            """
        )
        metadata = {
            "schema": payload["schema"],
            "serial_no": payload["serial_no"],
            "exported_at": str(payload.get("exported_at") or ""),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "source_mode": "GET-only",
        }
        connection.executemany("INSERT INTO snapshot_metadata VALUES (?, ?)", metadata.items())

        entities = [("investigation", payload["investigation"])]
        entities += [("task", item) for item in payload.get("tasks", {}).get("items", [])]
        entities += [("contract", item) for item in payload.get("contracts", {}).get("items", [])]
        for kind, item in entities:
            source_id = str(item.get("id") or item.get("record", {}).get("id") or "")
            serial_no = item.get("serial_no") or item.get("record", {}).get("serial_no")
            if not source_id:
                raise SystemExit(f"{kind} entity has no stable id")
            connection.execute(
                "INSERT INTO snapshot_entities VALUES (?, ?, ?, ?)",
                (kind, source_id, serial_no, json.dumps(item, ensure_ascii=False, sort_keys=True)),
            )
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
