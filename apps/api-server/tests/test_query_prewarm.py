import json
import time
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import app.main  # noqa: F401  挂载全部路由，财务缓存入口完成登记
from app.areas.finance import query_cache_routes
from app.core import query_prewarm


class _FakeRedis:
    """只实现缓存账号允许的命令；eval 按索引脚本的语义执行。"""

    def __init__(self):
        self.values = {}

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, ex=None):
        self.values[key] = value

    async def delete(self, *keys):
        for key in keys:
            self.values.pop(key, None)

    async def eval(self, script, count, key, field, now, cutoff, limit, retention):
        assert script is query_prewarm._TOUCH_INDEX and count == 1
        index = json.loads(self.values.get(key) or "{}")
        index[field] = now
        items = sorted(((name, used_at) for name, used_at in index.items() if used_at >= cutoff),
                       key=lambda item: item[1], reverse=True)[:limit]
        self.values[key] = json.dumps(dict(items))
        return 1


class _Session:
    def __init__(self):
        self.bind = SimpleNamespace(url=SimpleNamespace(render_as_string=lambda hide_password: "postgresql://x/oa"))

    def get_bind(self):
        return self.bind

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


IDENTITY = {"username": "caiwu", "role": "finance", "role_ids": ["finance"], "menu_keys": ["finance"]}


class QueryPrewarmTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.redis = _FakeRedis()
        patches = [
            patch.object(query_prewarm.shared, "client", return_value=self.redis),
            patch.object(query_prewarm.settings, "cache_redis_url", "redis://cache/0"),
            patch.object(query_prewarm.settings, "query_prewarm_enabled", True),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    async def test_finance_parameters_round_trip_to_the_same_call(self):
        path = "/finance/case-fees/refunds"
        endpoint_signature, _ = query_cache_routes._PREWARM_ROUTES[path]
        parameters = {name: parameter.default for name, parameter in endpoint_signature.parameters.items()
                      if name not in {"db", "identity"}}
        parameters.update(paid_from=date(2026, 10, 1), refund_amount_from=12.5, page=2, page_size=15,
                          case_no="HD-1", court_case_no="", court_name="", customer="", paid_organization="",
                          refund_status="", hearing_lawyer="", assistant="", case_stages="", fee_types="",
                          dashboard_queue="", paid_to=None, refund_amount_to=None)
        db = _Session()
        await query_prewarm.remember(db, "finance", path, IDENTITY, parameters)
        replay = AsyncMock()
        with patch.dict(query_cache_routes._PREWARM_ROUTES, {path: (endpoint_signature, replay)}):
            await query_prewarm.prewarm_once(lambda: _Session(), db.get_bind())
        kwargs = replay.await_args.kwargs
        self.assertEqual(kwargs.pop("identity"), IDENTITY)
        self.assertIs(type(kwargs.pop("db")), _Session)
        self.assertEqual(kwargs, parameters)
        self.assertIsInstance(kwargs["paid_from"], date)

    async def test_registry_keeps_recent_entries_in_order_and_prunes_the_rest(self):
        replay = AsyncMock()
        db = _Session()
        with patch.dict(query_prewarm._replayers, {"probe": replay}), \
             patch.object(query_prewarm.settings, "query_prewarm_max_entries", 2):
            for index in range(3):
                with patch.object(query_prewarm.time, "time", return_value=time.time() - 100 + index):
                    await query_prewarm.remember(db, "probe", f"section-{index}", IDENTITY, {})
            index_key = query_prewarm._registry_key(db.get_bind()) + ":index"
            self.assertEqual(len(json.loads(self.redis.values[index_key])), 2)
            # 过期登记不再重放
            index = json.loads(self.redis.values[index_key])
            index["old"] = 1
            self.redis.values[index_key] = json.dumps(index)
            # 同一查询再次使用只刷新时间，不新增登记
            await query_prewarm.remember(db, "probe", "section-1", IDENTITY, {})
            await query_prewarm.prewarm_once(lambda: _Session(), db.get_bind())
        self.assertEqual([call.args[0] for call in replay.await_args_list], ["section-1", "section-2"])
        self.assertEqual(len(json.loads(self.redis.values[index_key])), 2)

    async def test_failed_or_unknown_entries_do_not_stop_the_round(self):
        db = _Session()
        failing = AsyncMock(side_effect=ValueError("参数失效"))
        working = AsyncMock()
        with patch.dict(query_prewarm._replayers, {"failing": failing, "working": working}):
            await query_prewarm.remember(db, "failing", "a", IDENTITY, {})
            await query_prewarm.remember(db, "working", "b", IDENTITY, {})
            await query_prewarm.remember(db, "unregistered", "c", IDENTITY, {})
            await query_prewarm.prewarm_once(lambda: _Session(), db.get_bind())
        failing.assert_awaited_once()
        working.assert_awaited_once()

    async def test_changed_entry_point_signature_is_rejected(self):
        path = "/finance/case-fees/refunds"
        endpoint_signature, _ = query_cache_routes._PREWARM_ROUTES[path]
        with self.assertRaises((KeyError, ValueError)):
            await query_cache_routes._replay_finance_query(path, IDENTITY, {"page": 1}, _Session())

    async def test_disabled_or_without_redis_does_not_register(self):
        db = _Session()
        with patch.object(query_prewarm.settings, "query_prewarm_enabled", False):
            await query_prewarm.remember(db, "dashboard", "todos", IDENTITY, {})
        with patch.object(query_prewarm.settings, "cache_redis_url", ""):
            await query_prewarm.remember(db, "dashboard", "todos", IDENTITY, {})
        self.assertEqual(self.redis.values, {})


if __name__ == "__main__":
    unittest.main()
