"""BUG20261031002：已有库启动时补 departments.owner_username 列（1.2.71 因缺这条修订回滚）。"""
import unittest

from sqlalchemy import create_engine, inspect, text

from app.core.startup_migrations import _apply_department_owner


class DepartmentOwnerMigrationTest(unittest.TestCase):
    def test_adds_missing_column_once(self):
        engine = create_engine("sqlite://")
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE departments (id INTEGER PRIMARY KEY, name VARCHAR(128))"))
            connection.execute(text("INSERT INTO departments (id, name) VALUES (1, '诉讼一部')"))
            _apply_department_owner(connection, lambda _c: None)
            _apply_department_owner(connection, lambda _c: None)
            self.assertIn("owner_username", {c["name"] for c in inspect(connection).get_columns("departments")})
            self.assertEqual(connection.execute(text("SELECT owner_username FROM departments")).scalar(), "")


if __name__ == "__main__":
    unittest.main()
