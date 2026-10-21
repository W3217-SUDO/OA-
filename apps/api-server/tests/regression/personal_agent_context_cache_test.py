"""智能体每轮的待办摘要：同一身份 60 秒内复用，换身份或过期重新查询，返回的是副本。"""
import unittest
from unittest.mock import AsyncMock, patch

from app.areas.personal_agent import service


class ContextCacheTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        service._context_cache.clear()

    async def test_same_identity_reuses_and_returns_independent_copies(self):
        builder = AsyncMock(side_effect=lambda identity, db: {"todos": [1], "who": identity["username"]})
        with patch.object(service, "build_context", builder):
            first = await service.cached_build_context({"username": "u1", "menu_keys": ["a"]}, None)
            first["project_workspace"] = "mutated"
            second = await service.cached_build_context({"username": "u1", "menu_keys": ["a"]}, None)
            other = await service.cached_build_context({"username": "u2", "menu_keys": ["a"]}, None)
            changed_menu = await service.cached_build_context({"username": "u1", "menu_keys": ["a", "b"]}, None)
        self.assertEqual(builder.await_count, 3)  # u1 复用一次；u2 和权限变化后的 u1 各查一次
        self.assertNotIn("project_workspace", second)  # 调用方改动不会污染缓存
        self.assertEqual((other["who"], changed_menu["who"]), ("u2", "u1"))

    async def test_expired_entries_are_rebuilt(self):
        builder = AsyncMock(return_value={"todos": []})
        with patch.object(service, "build_context", builder), patch.object(service, "_CONTEXT_TTL_SECONDS", 0):
            await service.cached_build_context({"username": "u1"}, None)
            await service.cached_build_context({"username": "u1"}, None)
        self.assertEqual(builder.await_count, 2)


if __name__ == "__main__":
    unittest.main()
