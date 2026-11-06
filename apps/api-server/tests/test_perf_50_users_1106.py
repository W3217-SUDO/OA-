"""50 人压测（陶威 11-06）查出的慢点：工作台重算限流、无规则不读知产案件、任务只解析一次、客户匹配走索引。"""
import asyncio
import inspect
import unittest
from unittest.mock import AsyncMock, patch

import app.main  # noqa: F401
from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core import dashboard_metrics_cache as cache
from app.core import ipr
from app.core import permissions
from app.core.startup_migrations import _apply_record_scope_indexes
from app.core.task_query import stream_task_rows
from app.database import Base
from app.models import BusinessRecord, User


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
        source = inspect.getsource(_apply_record_scope_indexes)
        for field in ("customer_managers", "coordinators", "contact_accounts", "shared_with", "shared_to", "source_person",
                      "customer_source", "case_team_usernames", "legacy_participants", "customer_record_id"):
            self.assertIn(field, source)
        self.assertIn("WHERE module = '{module}'", source)

    def test_task_stream_parses_each_row_once(self):
        self.assertIn("json_to_record", inspect.getsource(stream_task_rows))


class ModuleScopeEquivalenceTest(unittest.IsolatedAsyncioTestCase):
    """_record_scope_conditions(module=...) 只换写法：每个账号看到的案件、客户和原写法一模一样。"""

    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        self.users = ("ann", "joann", "bob", "carol", "dave")
        async with self.sessions() as db:
            for username in self.users:
                db.add(User(username=username, display_name=username, password_hash="isolated-only", department="D1", role="staff"))
            rows = [
                ("customer", "owner-ann", "T", "ann", "D1", {}),
                ("customer", "managers", "T", "x", "D2", {"customer_managers": ["joann"]}),
                ("customer", "coord", "T", "x", "D2", {"coordinators": ["bob"]}),
                ("customer", "source", "T", "x", "D2", {"customer_source": "carol"}),
                ("customer", "person", "T", "x", "D2", {"source_person": "dave"}),
                ("customer", "shared-with", "T", "x", "D2", {"shared_with": ["ann"]}),
                ("customer", "shared-to", "T", "x", "D2", {"shared_to": ["bob"]}),
                ("customer", "public", "公海", "x", "D2", {}),
                ("customer", "other", "T", "x", "D2", {"customer_managers": ["nobody"]}),
                ("case", "c-owner", "S", "ann", "D1", {}),
                ("case", "c-team", "S", "x", "D2", {"case_team_usernames": ["joann"]}),
                ("case", "c-part", "S", "x", "D2", {"legacy_participants": '[{"staff_name":"bob"}]'}),
                ("case", "c-shared", "S", "x", "D2", {"shared_to": ["carol"]}),
                ("case", "c-customer", "S", "x", "D2", {"customer_record_id": 2}),
                ("case", "c-coord", "S", "x", "D2", {"customer_record_id": 3}),
                ("case", "c-other", "S", "x", "D2", {"customer_record_id": 9}),
                ("task", "t-owner", "S", "ann", "D1", {"case_team_usernames": ["bob"]}),
            ]
            for index, (module, serial, status, owner, department, data) in enumerate(rows, start=1):
                db.add(BusinessRecord(id=index, module=module, serial_no=serial, title=serial, status=status, owner=owner,
                                      department=department, data=data))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_same_rows_as_or_form_for_every_user_and_method(self):
        seen = {}
        async with self.sessions() as db:
            for username in self.users:
                for method in ("GET", "POST"):
                    identity = {"username": username, "role": "staff", "role_ids": ["staff"], "_actual_role": "staff",
                                "_actual_role_ids": ["staff"], "_request_method": method}
                    for module in ("case", "customer"):
                        base = BusinessRecord.module == module
                        old = set((await db.scalars(select(BusinessRecord.id).where(
                            base, *(await permissions._record_scope_conditions(identity, db))))).all())
                        new = set((await db.scalars(select(BusinessRecord.id).where(
                            base, *(await permissions._record_scope_conditions(identity, db, module=module))))).all())
                        self.assertEqual(old, new, (username, method, module))
                        seen[(username, method, module)] = old
        self.assertIn(2, seen[("joann", "GET", "customer")])
        self.assertNotIn(1, seen[("joann", "GET", "customer")], "ann 不能因为 joann 的名字串被匹配")
        self.assertIn(14, seen[("joann", "GET", "case")], "客户管理人读取时能看到客户的案件")
        self.assertNotIn(14, seen[("joann", "POST", "case")], "写操作不算协作范围")
        self.assertNotIn(16, seen[("ann", "GET", "case")])

    async def test_other_module_never_leaks_through_the_module_form(self):
        async with self.sessions() as db:
            identity = {"username": "ann", "role": "staff", "role_ids": ["staff"], "_actual_role": "staff",
                        "_actual_role_ids": ["staff"], "_request_method": "GET"}
            rows = set((await db.scalars(select(BusinessRecord.id).where(
                *(await permissions._record_scope_conditions(identity, db, module="case"))))).all())
        self.assertEqual({r for r in rows if r > 16 or r < 10}, set(), "传了 case 就只含案件，任务不会混进来")


class IprWarningsTest(unittest.IsolatedAsyncioTestCase):
    async def test_no_active_rules_means_no_case_load(self):
        db = AsyncMock()
        db.scalars.return_value = type("R", (), {"all": lambda self: []})()
        with patch("app.core.permissions._require_record_module_menu", new=AsyncMock()), \
                patch("app.core.permissions._visible_ipr_cases", new=AsyncMock()) as visible:
            self.assertEqual(await ipr._materialize_ipr_case_warnings({"username": "u1"}, db), 0)
        visible.assert_not_called()


class FreshCacheSkipsGateTest(unittest.IsolatedAsyncioTestCase):
    async def test_fresh_cache_returns_without_waiting_for_slot(self):
        from types import SimpleNamespace

        db = SimpleNamespace(new=(), dirty=(), deleted=(), in_transaction=lambda: False,
                             get_bind=lambda: SimpleNamespace(
                                 url=SimpleNamespace(render_as_string=lambda hide_password: "postgresql://x/oa"),
                                 dialect=SimpleNamespace(name="postgresql")))
        with patch.object(cache.settings, "cache_redis_url", "redis://cache/0"), \
                patch("app.core.query_cache.shared.source_revision", return_value="src"), \
                patch.object(cache.query_cache_store, "read", new=AsyncMock(return_value={"snapshot": "1:1:", "result": {"x": 1}})), \
                patch.object(cache, "dashboard_snapshot", new=AsyncMock(return_value="1:1:")), \
                patch.object(cache, "_shared_refresh") as refresh:
            result = await cache.cached_dashboard_query(db, {"username": "u"}, "todos", AsyncMock(), compute_in=lambda session: None)
        self.assertEqual(result, {"x": 1})
        refresh.assert_not_called()


class PriorityAndPendingTest(unittest.IsolatedAsyncioTestCase):
    def _db(self):
        from types import SimpleNamespace
        return SimpleNamespace(new=(), dirty=(), deleted=(), in_transaction=lambda: False,
                               get_bind=lambda: SimpleNamespace(
                                   url=SimpleNamespace(render_as_string=lambda hide_password: "postgresql://x/oa"),
                                   dialect=SimpleNamespace(name="postgresql")))

    def _common(self):
        return (patch.object(cache.settings, "cache_redis_url", "redis://cache/0"),
                patch("app.core.query_cache.shared.source_revision", return_value="src"))

    async def test_priority_skips_cooldown_and_is_urgent(self):
        a, b = self._common()
        with a, b, patch.object(cache, "_cached_state", new=AsyncMock(return_value=("stale", {"x": 1}))), \
                patch.object(cache, "_priority_refresh_allowed", new=AsyncMock(return_value=True)), \
                patch.object(cache, "_refresh_state", new=AsyncMock(return_value="cooling")) as cooldown, \
                patch.object(cache, "_shared_refresh") as refresh:
            result = await cache.cached_dashboard_query(self._db(), {"username": "u"}, "todos", AsyncMock(),
                                                        compute_in=lambda s: None, priority=True)
        self.assertEqual(result, {"x": 1, "stale": True})
        cooldown.assert_not_called()
        self.assertTrue(refresh.call_args.kwargs["urgent"])

    async def test_never_computed_returns_pending_without_blocking(self):
        a, b = self._common()
        slow = asyncio.get_running_loop().create_future()
        with a, b, patch.object(cache, "_cached_state", new=AsyncMock(return_value=(None, None))), \
                patch.object(cache, "_shared_refresh", return_value=slow), \
                patch.object(cache.settings, "dashboard_foreground_wait_seconds", 0.01):
            result = await cache.cached_dashboard_query(self._db(), {"username": "u"}, "todos", AsyncMock(),
                                                        compute_in=lambda s: None, allow_pending=True)
        self.assertEqual(result, {"pending": True, "stale": True})
        self.assertFalse(slow.cancelled(), "后台计算不被取消")
        slow.cancel()

    def test_computed_at_only_adds_one_key(self):
        result = cache.with_computed_at({"todos": [1]})
        self.assertEqual(set(result), {"todos", "computed_at"})


class OptionsCacheTest(unittest.IsolatedAsyncioTestCase):
    async def test_reuses_within_ttl_and_returns_copies(self):
        from app.core.shared_options_cache import cached_options, clear_options_cache
        clear_options_cache()
        calls = []

        async def compute():
            calls.append(1)
            return {"items": [1]}

        first = await cached_options("t", 60, compute)
        first["items"].append(2)
        self.assertEqual(await cached_options("t", 60, compute), {"items": [1]})
        self.assertEqual(len(calls), 1)
        clear_options_cache()


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
                users = [SimpleNamespace(username="broken", role="user", profile={}),
                         SimpleNamespace(username="new1", role="user", profile={}),
                         SimpleNamespace(username="external", role="user", profile={"permission_role": "外部案源人"})]
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
