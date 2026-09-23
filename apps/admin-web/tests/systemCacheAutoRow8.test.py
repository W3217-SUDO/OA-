"""9.22 第8行：缓存调度必须实际调用清理并留下执行时间。"""

import asyncio
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app.core import system
from app.core.constants import SYSTEM_CACHE_META


class SystemCacheAutoRow8Test(unittest.IsolatedAsyncioTestCase):
    async def test_cleanup_loop_records_automatic_execution(self):
        previous = {key: dict(value) for key, value in SYSTEM_CACHE_META.items()}
        sleep_calls = []

        async def advance(interval):
            sleep_calls.append(interval)
            if len(sleep_calls) > 1:
                raise asyncio.CancelledError()

        try:
            with patch.object(system.settings, "system_cache_ttl_seconds", 60), patch.object(system.asyncio, "sleep", advance):
                with self.assertRaises(asyncio.CancelledError):
                    await system._automatic_cache_cleanup_loop()
            self.assertEqual(sleep_calls, [60, 60])
            self.assertEqual(SYSTEM_CACHE_META["system-parameters"]["last_cleared_by"], "system:auto")
            cleared_at = datetime.fromisoformat(SYSTEM_CACHE_META["system-parameters"]["last_cleared_at"])
            if cleared_at.tzinfo is None:
                self.assertLess(abs((datetime.now() - cleared_at).total_seconds()), 5)
            else:
                self.assertLess(abs((datetime.now(timezone.utc) - cleared_at).total_seconds()), 5)
            self.assertIsNotNone(system._NEXT_AUTO_CACHE_CLEANUP_AT)
        finally:
            SYSTEM_CACHE_META.update(previous)


if __name__ == "__main__":
    unittest.main()
