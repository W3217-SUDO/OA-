"""10.27：每个接口请求都记一行 api_timing 精确耗时；慢请求仍记 slow_api。

只记路由模板和白名单枚举参数（section），不记原始路径、其他查询参数或身份。
"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import unittest

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.request_metrics import RequestMetricsMiddleware, tag_request


def build_app(threshold_seconds):
    app = FastAPI()
    app.add_middleware(RequestMetricsMiddleware, api_prefix="/api/v1",
                       threshold_seconds=threshold_seconds, log_every_request=True)

    @app.get("/api/v1/dashboard")
    async def dashboard(section: str | None = None):
        tag_request("cache", "stale")
        return {"section": section}

    @app.get("/api/v1/customers/{customer_id}")
    async def customer(customer_id: str):
        return {}

    return app


class RequestTimingLogTest(unittest.IsolatedAsyncioTestCase):
    async def get(self, app, url):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated") as client:
            return await client.get(url)

    async def test_fast_request_logs_api_timing_with_section_and_cache_tag(self):
        app = build_app(threshold_seconds=60)
        with self.assertLogs("app.api_timing", level="INFO") as logs:
            response = await self.get(app, "/api/v1/dashboard?section=todos&keyword=CODEX-SECRET")
        self.assertEqual(response.status_code, 200)
        line = logs.records[-1].getMessage()
        self.assertTrue(line.startswith("api_timing method=GET route=/api/v1/dashboard status=200 total_ms="), line)
        self.assertTrue(line.endswith(" section=todos cache=stale"), line)
        self.assertNotIn("CODEX-SECRET", line)

    async def test_raw_path_and_unsafe_section_not_logged(self):
        app = build_app(threshold_seconds=60)
        with self.assertLogs("app.api_timing", level="INFO") as logs:
            await self.get(app, "/api/v1/customers/HZKH-CODEX-1027?section=<x>")
        line = logs.records[-1].getMessage()
        self.assertIn("route=/api/v1/customers/{customer_id}", line)
        self.assertNotIn("HZKH-CODEX-1027", line)
        self.assertNotIn("section=", line)

    async def test_slow_request_still_logs_slow_api_warning(self):
        app = build_app(threshold_seconds=0.000001)
        with self.assertLogs("app.core.request_metrics", level="WARNING") as logs:
            await self.get(app, "/api/v1/dashboard?section=cases")
        line = logs.records[-1].getMessage()
        self.assertTrue(line.startswith("slow_api method=GET route=/api/v1/dashboard"), line)
        self.assertIn("section=cases", line)


if __name__ == "__main__":
    unittest.main()
