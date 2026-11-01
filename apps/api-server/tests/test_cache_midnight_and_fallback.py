"""陶威 11-01：按天缓存零点过期；缓存不可用（Redis 重启那一两秒）时直接现算，不报错。"""
import unittest
from datetime import datetime, timedelta
from unittest import mock

from redis.exceptions import ConnectionError as RedisConnectionError

from app.core import dashboard_metrics_redis as shared


class CacheMidnightTest(unittest.TestCase):
    def test_ttl_never_passes_next_midnight(self):
        now = datetime.now().astimezone()
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        left = (midnight - now).total_seconds()
        ttl = shared.ttl_until_midnight(86400)
        self.assertLessEqual(ttl, left + 301)
        self.assertGreater(ttl, 0)
        self.assertEqual(shared.ttl_until_midnight(5), 5)


class CacheFallbackTest(unittest.IsolatedAsyncioTestCase):
    async def test_query_cache_computes_when_redis_fails(self):
        from app.core import query_cache

        db = mock.MagicMock()
        db.get_bind.return_value.dialect.name = "postgresql"
        db.new = db.dirty = db.deleted = []

        async def snapshot(_db):
            return "s1"

        async def compute():
            return {"ok": True}

        async def broken(*args, **kwargs):
            raise RedisConnectionError("restarting")

        with mock.patch.object(query_cache.settings, "cache_redis_url", "redis://cache"), \
                mock.patch.object(query_cache, "read_shared_query", broken):
            result = await query_cache._cached_query(
                db, {"username": "u"}, "test.ns", {}, compute, snapshot_reader=snapshot, query_store=mock.MagicMock())
        self.assertEqual(result, {"ok": True})


if __name__ == "__main__":
    unittest.main()
