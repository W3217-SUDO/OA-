"""后台刷新算完后歇一会：名额还是自己的才延长，已被别人拿走时不能延长别人的名额（分支 2 审查 11-08）。"""
import unittest
from unittest.mock import patch

from app.core import dashboard_metrics_cache as cache


class FakeRedis:
    """只实现名额用到的两个脚本：比 token 再删 / 再延长。"""

    def __init__(self):
        self.values, self.ttl = {}, {}

    async def eval(self, script, numkeys, key, token, *args):
        if self.values.get(key) != token:
            return 0
        if script == cache._RELEASE_SLOT:
            self.values.pop(key, None)
            return 1
        if script == cache._REST_SLOT:
            self.ttl[key] = int(args[0])
            return 1
        raise AssertionError("未知脚本")

    async def expire(self, *args):  # 不应再直接调用
        raise AssertionError("不能不比 token 直接 expire")


class SlotRestTest(unittest.IsolatedAsyncioTestCase):
    async def test_rest_only_extends_own_slot(self):
        redis = FakeRedis()
        with patch.object(cache.shared, "client", lambda: redis), \
                patch.object(cache.settings, "dashboard_background_rest_ratio", 1.0):
            redis.values["slot:0"] = "mine"
            await cache._release_global_slot(("slot:0", "mine"), seconds=30)
            self.assertEqual(redis.ttl.get("slot:0"), 30)
            # 算得太久，名额已过期并被别人拿走：不能延长别人的
            redis.values["slot:0"], redis.ttl = "someone-else", {}
            await cache._release_global_slot(("slot:0", "mine"), seconds=30)
            self.assertEqual(redis.ttl, {})
            self.assertEqual(redis.values["slot:0"], "someone-else")
            # 等结果的请求算完直接释放，同样只删自己的
            await cache._release_global_slot(("slot:0", "mine"), urgent=True)
            self.assertEqual(redis.values["slot:0"], "someone-else")


if __name__ == "__main__":
    unittest.main()
