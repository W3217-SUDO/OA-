"""财务查询缓存修订：仅 PostgreSQL 生效，覆盖缺失时不使用缓存，路由改用该修订。"""

import inspect
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase

from app.areas.finance import query_cache_routes
from app.core import finance_query_revision as revision


class _Session:
    def __init__(self, dialect):
        self._dialect = dialect
        self.new, self.dirty, self.deleted = [], [], []

    def get_bind(self):
        return SimpleNamespace(dialect=SimpleNamespace(name=self._dialect))


class FinanceQueryRevisionTest(IsolatedAsyncioTestCase):
    async def test_non_postgresql_never_uses_cache(self):
        self.assertIsNone(await revision.finance_revision_snapshot(_Session("sqlite")))

    async def test_pending_writes_never_use_cache(self):
        session = _Session("postgresql")
        session.dirty = [object()]
        self.assertIsNone(await revision.finance_revision_snapshot(session))


class FinanceQueryRevisionDefinitionTest(TestCase):
    def test_only_high_churn_non_finance_tables_are_excluded(self):
        self.assertEqual(revision.EXCLUDED_TABLES, frozenset({
            "dashboard_change_revisions", "schema_migrations",
            "notification_sync_schedules", "ipr_case_reminder_types",
            "notifications", "notification_deliveries",
            "checkpoints", "checkpoint_blobs", "checkpoint_writes", "checkpoint_migrations",
        }))
        for table in ("business_records", "incoming_payments", "legacy_finance_records",
                      "legacy_finance_allocations", "receivable_plans", "Legal_Case_Log"):
            self.assertNotIn(table, revision.EXCLUDED_TABLES)

    def test_coverage_check_requires_both_triggers(self):
        self.assertIn(revision.ROW_TRIGGER, revision._COVERAGE_SQL)
        self.assertIn(revision.TRUNCATE_TRIGGER, revision._COVERAGE_SQL)
        self.assertIn("tgenabled = 'A'", revision._COVERAGE_SQL)

    def test_finance_routes_use_finance_revision(self):
        source = inspect.getsource(query_cache_routes._wrap_query)
        self.assertIn("snapshot_reader=finance_revision_snapshot", source)
