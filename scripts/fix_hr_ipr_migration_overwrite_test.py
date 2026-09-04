import importlib.util
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("fix_hr_ipr_migration_overwrite.py")
SPEC = importlib.util.spec_from_file_location("row3_fix", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RepairTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.connection = sqlite3.connect(Path(self.temp.name) / "row3.db")
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            CREATE TABLE departments (code TEXT, name TEXT);
            CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, department TEXT, is_active INTEGER);
            CREATE TABLE business_records (
                id INTEGER PRIMARY KEY, module TEXT, owner TEXT, department TEXT, status TEXT, data TEXT
            );
            INSERT INTO departments VALUES ('D1', '诉讼一部');
            """
        )

    def tearDown(self):
        self.connection.close()
        self.temp.cleanup()

    def add_employee(self, *, record_id=1, username="former", users=1, department_code="D1"):
        data = (
            '{"username":"%s","is_active":true,'
            '"legacy_hr_identity":{"legacy_department_code":"%s","legacy_is_actived":false},'
            '"legacy_ipr_identity":{}}' % (username, department_code)
        )
        self.connection.execute(
            "INSERT INTO business_records VALUES (?, 'hr', ?, '错误部门', '在职', ?)",
            (record_id, username, data),
        )
        for index in range(users):
            self.connection.execute(
                "INSERT INTO users VALUES (?, ?, '错误部门', 1)",
                (record_id * 10 + index, username),
            )
        self.connection.commit()

    def snapshot(self):
        return (
            [tuple(row) for row in self.connection.execute("SELECT * FROM business_records ORDER BY id")],
            [tuple(row) for row in self.connection.execute("SELECT * FROM users ORDER BY id")],
        )

    def test_dry_run_reports_without_writes(self):
        self.add_employee()
        before = self.snapshot()
        stats = MODULE.repair(self.connection, dry_run=True)
        self.assertEqual(stats["eligible"], 1)
        self.assertEqual(stats["status_corrected"], 1)
        self.assertEqual(stats["updated"], 0)
        self.assertEqual(self.snapshot(), before)

    def test_apply_synchronizes_hr_and_user(self):
        self.add_employee()
        stats = MODULE.repair(self.connection, dry_run=False)
        record = self.connection.execute(
            "SELECT department,status,json_extract(data, '$.is_active') active FROM business_records"
        ).fetchone()
        user = self.connection.execute("SELECT department,is_active FROM users").fetchone()
        self.assertEqual(tuple(record), ("诉讼一部", "停用", 0))
        self.assertEqual(tuple(user), ("诉讼一部", 0))
        self.assertEqual(stats["updated"], 1)

    def test_apply_can_restore_active_employee(self):
        self.add_employee()
        self.connection.execute(
            "UPDATE business_records SET status='停用', data=json_set(data, '$.legacy_hr_identity.legacy_is_actived', true)"
        )
        self.connection.execute("UPDATE users SET is_active=0")
        self.connection.commit()
        MODULE.repair(self.connection, dry_run=False)
        record = self.connection.execute(
            "SELECT status,json_extract(data, '$.is_active') FROM business_records"
        ).fetchone()
        user = self.connection.execute("SELECT is_active FROM users").fetchone()
        self.assertEqual(tuple(record), ("在职", 1))
        self.assertEqual(tuple(user), (1,))

    def test_missing_user_blocks_all_changes(self):
        self.add_employee(record_id=1)
        self.add_employee(record_id=2, username="missing", users=0)
        before = self.snapshot()
        with self.assertRaisesRegex(MODULE.RepairBlocked, "user not found"):
            MODULE.repair(self.connection, dry_run=False)
        self.assertEqual(self.snapshot(), before)

    def test_duplicate_user_blocks_all_changes(self):
        self.add_employee(users=2)
        before = self.snapshot()
        with self.assertRaisesRegex(MODULE.RepairBlocked, "matched 2 users"):
            MODULE.repair(self.connection, dry_run=False)
        self.assertEqual(self.snapshot(), before)

    def test_missing_department_blocks_all_changes(self):
        self.add_employee(department_code="UNKNOWN")
        before = self.snapshot()
        with self.assertRaisesRegex(MODULE.RepairBlocked, "department code"):
            MODULE.repair(self.connection, dry_run=False)
        self.assertEqual(self.snapshot(), before)

    def test_postgresql_uses_native_placeholders(self):
        self.assertEqual(MODULE.placeholder("postgresql"), "%s")
        self.assertEqual(MODULE.placeholder("sqlite"), "?")


class Result:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class FakePostgresConnection:
    def __init__(self, fail_user_update=False):
        self.fail_user_update = fail_user_update
        self.statements = []
        self.commits = 0
        self.rollbacks = 0

    def execute(self, sql, params=()):
        self.statements.append((sql, params))
        if sql == "SELECT code,name FROM departments":
            return Result([{"code": "D1", "name": "诉讼一部"}])
        if sql.startswith("SELECT id,owner"):
            return Result([{
                "id": 1,
                "owner": "former",
                "department": "错误部门",
                "status": "在职",
                "data": {
                    "is_active": True,
                    "legacy_hr_identity": {"legacy_department_code": "D1", "legacy_is_actived": False},
                    "legacy_ipr_identity": {},
                },
            }])
        if sql.startswith("SELECT id,department,is_active"):
            self.last_user_lookup_sql = sql
            return Result([{"id": 10, "department": "错误部门", "is_active": True}])
        if sql.startswith("UPDATE users") and self.fail_user_update:
            raise RuntimeError("injected PostgreSQL write failure")
        return Result([])

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class PostgreSqlTransactionTest(unittest.TestCase):
    def test_postgresql_apply_commits_once_and_uses_percent_placeholders(self):
        connection = FakePostgresConnection()
        stats = MODULE.repair(connection, dry_run=False, dialect="postgresql")
        self.assertEqual(stats["updated"], 1)
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)
        self.assertIn("username=%s", connection.last_user_lookup_sql)
        updates = [sql for sql, _ in connection.statements if sql.startswith("UPDATE")]
        self.assertTrue(updates)
        self.assertTrue(all("%s" in sql and "?" not in sql for sql in updates))

    def test_postgresql_write_failure_rolls_back_without_commit(self):
        connection = FakePostgresConnection(fail_user_update=True)
        with self.assertRaisesRegex(RuntimeError, "injected PostgreSQL"):
            MODULE.repair(connection, dry_run=False, dialect="postgresql")
        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)


if __name__ == "__main__":
    unittest.main()
