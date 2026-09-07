import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("sync_legacy_hr_statuses.py")
SPEC = importlib.util.spec_from_file_location("hr_status_sync", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class StatusSyncTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.connection = sqlite3.connect(Path(self.temp.name) / "test.db")
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, is_active INTEGER, profile TEXT);
            CREATE TABLE business_records (
                id INTEGER PRIMARY KEY, module TEXT, serial_no TEXT, owner TEXT, status TEXT, data TEXT
            );
            """
        )

    def tearDown(self):
        self.connection.close()
        self.temp.cleanup()

    def add_target(self, username="former", guid="abc", active=1, status="在职"):
        identity = {"legacy_staff_guid": guid, "legacy_is_actived": True}
        data = {"username": username, "is_active": bool(active), "legacy_hr_identity": identity}
        self.connection.execute(
            "INSERT INTO users VALUES (10,?,?,?)",
            (username, active, json.dumps({"legacy_hr_identity": identity})),
        )
        self.connection.execute(
            "INSERT INTO business_records VALUES (1,'hr','411',?,?,?)",
            (username, status, json.dumps(data)),
        )
        self.connection.commit()

    def manifest(self, *, is_actived="F", job_status="T", resignation_date=""):
        return {
            "source_database": "PRD_CRM_HZ_20250207",
            "exported_at": "2026-09-07T12:00:00+08:00",
            "staff": [{
                "staff_guid": "abc",
                "staff_id": 258,
                "staff_no": "411",
                "username": "former",
                "is_actived": is_actived,
                "job_status": job_status,
                "resignation_date": resignation_date,
                "changed_at": "2025-11-18T17:53:37",
            }],
        }

    def snapshot(self):
        return (
            [tuple(row) for row in self.connection.execute("SELECT * FROM users")],
            [tuple(row) for row in self.connection.execute("SELECT * FROM business_records")],
        )

    def test_dry_run_does_not_write(self):
        self.add_target()
        before = self.snapshot()
        stats = MODULE.synchronize(self.connection, self.manifest(), True, "sqlite")
        self.assertEqual(stats["changed"], 1)
        self.assertEqual(stats["updated"], 0)
        self.assertEqual(self.snapshot(), before)

    def test_inactive_employee_becomes_disabled_not_departed(self):
        self.add_target()
        stats = MODULE.synchronize(self.connection, self.manifest(), False, "sqlite")
        user = self.connection.execute("SELECT is_active,profile FROM users").fetchone()
        record = self.connection.execute("SELECT status,data FROM business_records").fetchone()
        self.assertEqual(user["is_active"], 0)
        self.assertEqual(record["status"], "停用")
        self.assertFalse(json.loads(record["data"])["is_active"])
        self.assertEqual(json.loads(user["profile"])["legacy_job_status"], "T")
        self.assertEqual(stats["updated"], 1)

    def test_job_status_or_resignation_date_marks_departed(self):
        for job_status, resignation_date in (("F", ""), ("T", "2025-01-02")):
            with self.subTest(job_status=job_status, resignation_date=resignation_date):
                self.connection.execute("DELETE FROM users")
                self.connection.execute("DELETE FROM business_records")
                self.add_target()
                MODULE.synchronize(
                    self.connection,
                    self.manifest(job_status=job_status, resignation_date=resignation_date),
                    False,
                    "sqlite",
                )
                record = self.connection.execute("SELECT status,data FROM business_records").fetchone()
                self.assertEqual(record["status"], "离职")
                self.assertEqual(json.loads(record["data"])["left_at"], resignation_date)

    def test_unmatched_source_is_reported_without_creating_user(self):
        stats = MODULE.synchronize(self.connection, self.manifest(), False, "sqlite")
        self.assertEqual(stats["unmatched"], 1)
        self.assertEqual(stats["updated"], 0)

    def test_guid_mismatch_is_skipped_as_identity_conflict(self):
        self.add_target(guid="different")
        before = self.snapshot()
        stats = MODULE.synchronize(self.connection, self.manifest(), False, "sqlite")
        self.assertEqual(stats["identity_conflict"], 1)
        self.assertEqual(stats["updated"], 0)
        self.assertEqual(self.snapshot(), before)

    def test_missing_guid_is_backfilled_only_when_employee_number_matches(self):
        self.add_target(guid="")
        MODULE.synchronize(self.connection, self.manifest(), False, "sqlite")
        data = json.loads(self.connection.execute("SELECT data FROM business_records").fetchone()[0])
        self.assertEqual(data["legacy_hr_identity"]["legacy_staff_guid"], "abc")

    def test_missing_guid_and_employee_number_mismatch_is_skipped(self):
        self.add_target(guid="")
        self.connection.execute("UPDATE business_records SET serial_no='other'")
        self.connection.commit()
        stats = MODULE.synchronize(self.connection, self.manifest(), False, "sqlite")
        self.assertEqual(stats["identity_conflict"], 1)
        self.assertEqual(stats["updated"], 0)

    def test_active_employee_is_rejected_from_inactive_manifest(self):
        self.add_target()
        with self.assertRaisesRegex(MODULE.SyncBlocked, "includes active employee"):
            MODULE.synchronize(
                self.connection,
                self.manifest(is_actived="T", job_status="T"),
                True,
                "sqlite",
            )


if __name__ == "__main__":
    unittest.main()
