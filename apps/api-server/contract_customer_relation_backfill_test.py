from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from contract_customer_relation_backfill import audit_database


class ContractCustomerRelationBackfillTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Path(self.temp_dir.name) / "legal_platform.db"
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute(
                "CREATE TABLE business_records (id INTEGER PRIMARY KEY, module TEXT, serial_no TEXT, title TEXT, customer TEXT, data TEXT)"
            )
            connection.executemany(
                "INSERT INTO business_records (id, module, serial_no, title, customer, data) VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (1, "customer", "KH-001", "Northwind", "", "{}"),
                    (2, "customer", "KH-002", "Duplicate", "", "{}"),
                    (3, "customer", "KH-003", "Duplicate", "", "{}"),
                    (11, "contract", "HT-001", "Unique contract", " Northwind ", "{}"),
                    (12, "contract", "HT-002", "Ambiguous contract", "Duplicate", "{}"),
                    (13, "case", "SHMS-001", "Unmatched case", "Missing", "{}"),
                    (14, "contract", "HT-003", "Already linked", "Northwind", '{"customer_id": 1}'),
                    (15, "contract", "HT-004", "Invalid data", "Northwind", "not-json"),
                ],
            )
            connection.commit()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_only_unique_name_is_proposed_and_applied_idempotently(self) -> None:
        dry_run = audit_database(self.database)
        self.assertEqual([row["id"] for row in dry_run["proposed_updates"]], [11])
        self.assertEqual([row["id"] for row in dry_run["ambiguous"]], [12])
        self.assertEqual([row["id"] for row in dry_run["unmatched"]], [13])
        self.assertEqual([row["id"] for row in dry_run["already_linked"]], [14])
        self.assertEqual([row["id"] for row in dry_run["invalid_data"]], [15])

        applied = audit_database(self.database, apply=True)
        self.assertEqual(applied["applied"], 1)
        with closing(sqlite3.connect(self.database)) as connection:
            data = json.loads(connection.execute("SELECT data FROM business_records WHERE id = 11").fetchone()[0])
        self.assertEqual(data, {"customer_id": 1, "customer_no": "KH-001"})

        rerun = audit_database(self.database)
        self.assertEqual(rerun["proposed_updates"], [])
        self.assertEqual({row["id"] for row in rerun["already_linked"]}, {11, 14})


if __name__ == "__main__":
    unittest.main()
