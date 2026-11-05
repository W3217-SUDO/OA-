"""工作台提速（陶国南 11-05 同意）：分端待办、驳回提醒走缓存；当天没结果先给最近一次结果；工作台预热单独名额、早间统一预热。"""
import asyncio
import json
import time
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import app.main  # noqa: F401  挂载全部路由，工作台预热完成登记
from app.core import dashboard_metrics_cache as dashboard_cache
from app.core import query_cache_store
from app.core import query_prewarm


IDENTITY = {"username": "lawyer1", "role": "lawyer", "role_ids": ["lawyer"], "menu_keys": ["dashboard"]}


class _FakeRedis:
    def __init__(self):
        self.values = {}

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, ex=None):
        self.values[key] = value

    async def info(self, _section):
        return {"used_memory": 1, "maxmemory": 0}

    async def eval(self, script, count, key, field, now, cutoff, limit, retention):
        assert script is query_prewarm._TOUCH_INDEX and count == 1
        index = json.loads(self.values.get(key) or "{}")
        index[field] = now
        items = sorted(((name, used_at) for name, used_at in index.items() if used_at >= cutoff),
                       key=lambda item: item[1], reverse=True)[:limit]
        self.values[key] = json.dumps(dict(items))
        return 1


class _Session:
    new = dirty = deleted = ()

    def __init__(self):
        self.bind = SimpleNamespace(url=SimpleNamespace(render_as_string=lambda hide_password: "postgresql://x/oa"),
                                    dialect=SimpleNamespace(name="postgresql"))

    def get_bind(self):
        return self.bind

    def in_transaction(self):
        return False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _Base(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.redis = _FakeRedis()
        query_cache_store._memory_state.update(checked_at=None, allowed=True)
        patches = [
            patch.object(dashboard_cache.shared, "client", return_value=self.redis),
            patch.object(query_prewarm.shared, "client", return_value=self.redis),
            patch.object(dashboard_cache.settings, "cache_redis_url", "redis://cache/0"),
            patch.object(dashboard_cache.settings, "query_prewarm_enabled", True),
            patch("app.core.query_cache.shared.source_revision", return_value="src-a"),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)


class DashboardLastResultTest(_Base):
    async def _query(self, section="todos", refresh_result=None):
        db = _Session()
        task = asyncio.get_running_loop().create_future()
        task.set_result(refresh_result or {"todos": ["new"]})
        with patch.object(dashboard_cache, "_shared_refresh", return_value=task) as refresh, \
             patch.object(dashboard_cache, "dashboard_snapshot", AsyncMock(return_value="1:1:")):
            result = await dashboard_cache.cached_dashboard_query(
                db, IDENTITY, section, AsyncMock(), compute_in=lambda session: None)
        return result, refresh

    async def test_new_day_without_cache_gives_last_result_as_stale_and_refreshes(self):
        await dashboard_cache._remember_last(_Session(), IDENTITY, "todos", {"todos": ["yesterday"]})
        result, refresh = await self._query()
        self.assertEqual(result, {"todos": ["yesterday"], "stale": True})
        refresh.assert_called_once()

    async def test_never_computed_waits_for_the_calculation(self):
        result, refresh = await self._query()
        self.assertEqual(result, {"todos": ["new"]})
        refresh.assert_called_once()

    async def test_last_result_is_per_identity_and_section(self):
        await dashboard_cache._remember_last(_Session(), {**IDENTITY, "username": "other"}, "todos", {"todos": ["x"]})
        await dashboard_cache._remember_last(_Session(), IDENTITY, "cases", {"cases": ["x"]})
        result, _ = await self._query()
        self.assertEqual(result, {"todos": ["new"]})

    async def test_portals_and_rejections_are_cache_sections(self):
        self.assertTrue({"portals", "rejections"} <= dashboard_cache.SECTIONS)
        await dashboard_cache._remember_last(_Session(), IDENTITY, "portals", {"portals": [1]})
        result, _ = await self._query("portals", {"portals": [2]})
        self.assertEqual(result, {"portals": [1], "stale": True})

    async def test_remember_last_without_redis_or_on_error_is_silent(self):
        with patch.object(dashboard_cache.settings, "cache_redis_url", ""):
            await dashboard_cache._remember_last(_Session(), IDENTITY, "todos", {"todos": []})
        self.assertEqual(self.redis.values, {})
        with patch.object(self.redis, "set", AsyncMock(side_effect=dashboard_cache.RedisError("down"))):
            await dashboard_cache._remember_last(_Session(), IDENTITY, "todos", {"todos": []})


class PortalCacheParametersTest(unittest.IsolatedAsyncioTestCase):
    async def test_portal_config_digest_changes_with_config(self):
        from app.areas.system import router

        with patch("app.core.dashboard_portals.load_config", AsyncMock(return_value={"portals": [], "role_portals": {}})):
            first = await router._dashboard_cache_parameters("portals", None)
        with patch("app.core.dashboard_portals.load_config",
                   AsyncMock(return_value={"portals": [], "role_portals": {"律师": ["lawyer"]}})):
            second = await router._dashboard_cache_parameters("portals", None)
        self.assertNotEqual(first, second)
        self.assertEqual(await router._dashboard_cache_parameters("rejections", None), {})


class DashboardPrewarmTest(_Base):
    async def test_dashboard_entries_have_their_own_quota(self):
        db = _Session()
        replay = AsyncMock()
        with patch.dict(query_prewarm._replayers, {"probe": replay}), \
             patch.object(query_prewarm.settings, "query_prewarm_max_entries", 2):
            for index in range(3):
                await query_prewarm.remember(db, "probe", f"finance-{index}", IDENTITY, {})
            for section in ("todos", "cases", "portals"):
                await query_prewarm.remember(db, "dashboard", section, IDENTITY, {})
        key = query_prewarm._registry_key(db.get_bind())
        self.assertEqual(len(json.loads(self.redis.values[f"{key}:index"])), 2)
        self.assertEqual(len(json.loads(self.redis.values[f"{key}:index:dashboard"])), 3)

    async def test_on_change_round_only_replays_recent_dashboard_users_and_morning_replays_all(self):
        db = _Session()
        replay = AsyncMock()
        with patch.dict(query_prewarm._replayers, {"dashboard": replay}):
            with patch.object(query_prewarm.time, "time", return_value=time.time() - 3 * 3600):
                await query_prewarm.remember(db, "dashboard", "todos", {**IDENTITY, "username": "old"}, {})
            await query_prewarm.remember(db, "dashboard", "todos", IDENTITY, {})
            await query_prewarm.prewarm_once(lambda: _Session(), db.get_bind())
            self.assertEqual([call.args[1]["username"] for call in replay.await_args_list], ["lawyer1"])
            replay.reset_mock()
            with patch.object(query_prewarm, "_MORNING_PAUSE_SECONDS", 0):
                await query_prewarm.prewarm_dashboards_morning(lambda: _Session(), db.get_bind())
            self.assertEqual(sorted(call.args[1]["username"] for call in replay.await_args_list), ["lawyer1", "old"])

    async def test_busy_entries_are_not_failures_and_failures_name_the_reason(self):
        db = _Session()
        busy = AsyncMock(side_effect=query_cache_store.unavailable("查询结果仍在重算，请稍后重试"))
        denied = AsyncMock(side_effect=query_prewarm.HTTPException(403, "无权限"))
        with patch.dict(query_prewarm._replayers, {"busy": busy, "denied": denied}):
            await query_prewarm.remember(db, "busy", "a", IDENTITY, {})
            await query_prewarm.remember(db, "denied", "b", IDENTITY, {})
            with self.assertLogs(query_prewarm.logger, "WARNING") as logs:
                result = await query_prewarm._replay_entries(
                    lambda: _Session(), await query_prewarm._recent_entries(self.redis, query_prewarm._registry_key(db.get_bind())))
        self.assertEqual(result, (0, 1, 1))
        self.assertIn("403 无权限", "\n".join(logs.output))
        self.assertIn("user=lawyer1", "\n".join(logs.output))

    def test_morning_window(self):
        today = datetime(2026, 11, 5, 6, 10)
        self.assertTrue(query_prewarm._morning_due(today, None))
        self.assertFalse(query_prewarm._morning_due(today, today.date()))
        self.assertFalse(query_prewarm._morning_due(datetime(2026, 11, 5, 5, 59), None))
        self.assertFalse(query_prewarm._morning_due(datetime(2026, 11, 5, 7, 30), None))


if __name__ == "__main__":
    unittest.main()
