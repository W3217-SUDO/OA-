"""50 人压测（陶威 11-06）查出的慢点：工作台重算限流、无规则不读知产案件、任务只解析一次、客户匹配走索引。"""
import asyncio
import inspect
import unittest
from unittest.mock import AsyncMock, patch

import app.main  # noqa: F401
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.core import dashboard_metrics_cache as cache
from app.core import ipr
from app.core import permissions
from app.core.startup_migrations import _apply_customer_coordinator_trgm_indexes
from app.core.task_query import stream_task_rows
from app.models import BusinessRecord


class ComputeGateTest(unittest.IsolatedAsyncioTestCase):
    async def test_one_at_a_time_and_waiting_users_go_first(self):
        gate = cache.ComputeGate(1)
        order = []
        release = asyncio.Event()

        async def job(name, urgent=False, ticket=None):
            async with gate.slot(urgent=urgent, ticket=ticket):
                order.append(name)
                await release.wait()

        ticket = {}
        tasks = [asyncio.create_task(job("first"))]
        await asyncio.sleep(0)
        tasks.append(asyncio.create_task(job("background")))
        tasks.append(asyncio.create_task(job("promoted", ticket=ticket)))
        await asyncio.sleep(0)
        tasks.append(asyncio.create_task(job("waiting", urgent=True)))
        await asyncio.sleep(0)
        gate.promote(ticket["waiter"])
        self.assertEqual(order, ["first"], "名额只有一个")
        self.assertEqual(gate.running, 1)
        release.set()
        await asyncio.gather(*tasks)
        self.assertEqual(order, ["first", "waiting", "promoted", "background"], "等结果的排在后台刷新前面")
        self.assertEqual(gate.running, 0)

    async def test_cancelled_waiter_releases_nothing_and_slot_returns(self):
        gate = cache.ComputeGate(1)
        hold = asyncio.Event()

        async def holder():
            async with gate.slot():
                await hold.wait()

        first = asyncio.create_task(holder())
        await asyncio.sleep(0)
        second = asyncio.create_task(holder())
        await asyncio.sleep(0)
        second.cancel()
        await asyncio.gather(second, return_exceptions=True)
        hold.set()
        await first
        self.assertEqual(gate.running, 0)


class _Redis:
    def __init__(self):
        self.values = {}

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.values:
            return None
        self.values[key] = value
        return True

    async def get(self, key):
        return self.values.get(key)


class RefreshCooldownTest(unittest.IsolatedAsyncioTestCase):
    async def test_started_then_recent_then_cooling(self):
        redis = _Redis()
        with patch.object(cache.shared, "client", return_value=redis), patch.object(cache, "time", return_value=1000.0):
            self.assertEqual(await cache._refresh_state("k"), "started")
            self.assertEqual(await cache._refresh_state("k"), "recent")
        with patch.object(cache.shared, "client", return_value=redis), patch.object(cache, "time", return_value=1031.0):
            self.assertEqual(await cache._refresh_state("k"), "cooling")

    async def test_redis_failure_falls_back_to_refresh(self):
        from redis.exceptions import RedisError

        broken = AsyncMock()
        broken.set.side_effect = RedisError("down")
        with patch.object(cache.shared, "client", return_value=broken):
            self.assertEqual(await cache._refresh_state("k"), "started")


class SqlShapeTest(unittest.TestCase):
    def _sql(self, statement):
        return str(statement.compile(dialect=postgresql.dialect()))

    def test_coordinated_condition_splits_into_indexable_union(self):
        sql = self._sql(select(BusinessRecord.id).where(permissions._coordinated_case_condition("u1", "postgresql")))
        self.assertEqual(sql.count("UNION"), 3, "管理人、负责人、协作人、客户账号各一条")
        manager = self._sql(select(BusinessRecord.id).where(permissions._coordinated_case_condition("u1", "postgresql", "manager")))
        self.assertEqual(manager.count("UNION"), 1)
        self.assertIn("coalesce", sql.lower())
        self.assertIn("''", sql, "空串是字面量，表达式才能匹配索引")

    def test_index_revision_expressions_exist(self):
        source = inspect.getsource(_apply_customer_coordinator_trgm_indexes)
        for field in ("customer_managers", "coordinators", "contact_accounts"):
            self.assertIn(field, source)
        self.assertIn("WHERE module = 'customer'", source)

    def test_task_stream_parses_each_row_once(self):
        self.assertIn("json_to_record", inspect.getsource(stream_task_rows))


class IprWarningsTest(unittest.IsolatedAsyncioTestCase):
    async def test_no_active_rules_means_no_case_load(self):
        db = AsyncMock()
        db.scalars.return_value = type("R", (), {"all": lambda self: []})()
        with patch("app.core.permissions._require_record_module_menu", new=AsyncMock()), \
                patch("app.core.permissions._visible_ipr_cases", new=AsyncMock()) as visible:
            self.assertEqual(await ipr._materialize_ipr_case_warnings({"username": "u1"}, db), 0)
        visible.assert_not_called()


class DashboardIdentityTest(unittest.TestCase):
    def test_page_does_not_split_cache_but_permissions_do(self):
        base = {"username": "u", "role": "user", "_page_menu_capability": False, "_page_scope_actual": True}
        same = [cache.dashboard_cache_identity({**base, "_request_page": page}) for page in ("feedback", "ai-chat", "")]
        self.assertEqual(same[0], same[1])
        self.assertEqual(same[1], same[2])
        other = cache.dashboard_cache_identity({**base, "_request_page": "feedback", "_page_menu_capability": True})
        self.assertNotEqual(same[0], other, "页面头决定的权限字段仍然分开缓存")
        self.assertNotEqual(same[0], cache.dashboard_cache_identity({**base, "username": "v"}))


class SeedActiveUsersTest(unittest.IsolatedAsyncioTestCase):
    async def test_seeds_unknown_users_only_and_one_failure_does_not_stop_others(self):
        from types import SimpleNamespace
        from app.core import query_prewarm

        class Session:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def scalars(self, statement):
                users = [SimpleNamespace(username="broken"), SimpleNamespace(username="new1")]
                return SimpleNamespace(all=lambda: users)

        async def identity_for(user, db):
            if user.username == "broken":
                raise ValueError("bad")
            return {"username": user.username}

        remembered = []

        async def remember(db, kind, name, identity, parameters):
            remembered.append((kind, name, identity["username"]))

        with patch.object(query_prewarm.shared, "client", return_value=object()), \
                patch.object(query_prewarm, "_registry_key", return_value="k"), \
                patch.object(query_prewarm, "_recent_entries", new=AsyncMock(return_value=[{"identity": {"username": "old"}}])), \
                patch.object(query_prewarm, "_dashboard_identity_for", new=identity_for), \
                patch.object(query_prewarm, "remember", new=remember):
            seeded = await query_prewarm.seed_dashboards_for_active_users(Session, object())
        self.assertEqual(seeded, 1)
        self.assertEqual(len(remembered), 6)
        self.assertEqual({item[2] for item in remembered}, {"new1"})


if __name__ == "__main__":
    unittest.main()
