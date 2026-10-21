"""组合查询真实 ASGI 调用链与权限透传；数据和替身仅在独立测试目录。"""

from contextlib import asynccontextmanager
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import Depends, FastAPI, HTTPException
import httpx
from pydantic import ValidationError

from app.agent_mcp import service
from app.agent_mcp.auth import RequestAuthContextMiddleware, get_auth_context
from app.agent_mcp.catalog import get_catalog
from app.areas.data_query.models import DataQuery
from app.areas.data_query.router import router
from app.areas.data_query.transform import transform
from app.config import settings
from app.security import current_identity


class QueryTransformTest(unittest.TestCase):
    def query(self, **kwargs):
        return DataQuery(source_tool="sample", **kwargs)

    def test_combined_filters_grouping_decimal_amounts_and_numeric_sort(self):
        rows = [{"id": 1, "team": "A", "amount": "2.10", "status": "open"},
                {"id": 2, "team": "A", "amount": "0.20", "status": "open"},
                {"id": 3, "team": "B", "amount": "10.00", "status": "open"},
                {"id": 4, "team": "B", "amount": "90", "status": "closed"}]
        result = transform(rows, self.query(where=[{"field": "status", "op": "eq", "value": "open"}],
            group_by=["team"], metrics=[{"name": "sum", "op": "sum", "field": "amount"}, {"name": "count", "op": "count"}],
            order_by=[{"field": "sum", "direction": "desc"}]))
        self.assertEqual(result["filtered_source_rows"], 3)
        self.assertEqual(result["items"], [{"team": "B", "sum": "10.00", "count": 1}, {"team": "A", "sum": "2.30", "count": 2}])

    def test_or_nested_fields_projection_and_offset(self):
        rows = [{"id": 1, "data": {"kind": "A"}}, {"id": 2, "data": {"kind": "B"}}, {"id": 3, "data": {"kind": "A"}}]
        result = transform(rows, self.query(fields=["id", "data.kind"], match="any",
            where=[{"field": "data.kind", "op": "eq", "value": "A"}, {"field": "id", "op": "eq", "value": 2}],
            order_by=[{"field": "id", "direction": "desc"}], offset=1, limit=1))
        self.assertEqual(result["items"], [{"id": 2, "data.kind": "B"}])
        self.assertEqual(result["total"], 3)

    def test_redacted_fields_cannot_be_selected_filtered_or_aggregated(self):
        for params in ({"fields": ["secret"]}, {"where": [{"field": "secret", "op": "eq", "value": "x"}]},
                       {"metrics": [{"name": "sum", "op": "sum", "field": "secret"}]}):
            with self.subTest(params=params), self.assertRaises(HTTPException) as caught:
                transform([{"id": 1}], self.query(**params))
            self.assertEqual(caught.exception.status_code, 422)

    def test_invalid_numeric_value_is_not_silently_dropped(self):
        with self.assertRaises(HTTPException):
            transform([{"amount": "not-a-number"}], self.query(metrics=[{"name": "sum", "op": "sum", "field": "amount"}]))

    def test_no_raw_sql_identity_or_unbounded_queries(self):
        for params in ({"sql": "SELECT 1"}, {"username": "admin"}, {"limit": 10000}, {"all_pages": True},
                       {"metrics": [{"name": "sum", "op": "sum"}]}):
            with self.subTest(params=params), self.assertRaises(ValidationError):
                self.query(**params)


class QueryApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.app = FastAPI()
        self.calls = []
        self.source_mode = "normal"

        async def identity():
            token = get_auth_context().bearer.removeprefix("test-bearer-")
            if token not in {"alice", "bob"}:
                raise HTTPException(401, "测试账号未登录")
            return {"username": token, "role": "user"}

        @self.app.get(settings.api_prefix + "/reports/query-samples")
        async def list_query_samples(page: int = 1, page_size: int = 1, identity=Depends(current_identity)):
            self.calls.append((identity["username"], page))
            records = [{"id": i, "owner": identity["username"], "amount": str(i)} for i in (1, 2, 3)]
            batch = records[(page-1)*page_size:page*page_size]
            total = 6000 if self.source_mode == "oversize" else 3
            if self.source_mode == "changed" and page == 2:
                total = 4
            if self.source_mode == "duplicate" and page == 2:
                batch = [records[0]]
            return {"items": batch, "total": total}

        @self.app.post(settings.api_prefix + "/reports/query-samples")
        async def create_query_sample(_identity=Depends(current_identity)):
            self.fail("组合查询不应执行写路由")

        self.app.include_router(router)
        self.app.dependency_overrides[current_identity] = identity
        self.app.add_middleware(RequestAuthContextMiddleware, application=self.app)
        self.auth = patch.object(service, "authenticated_identity", identity)
        self.auth.start()

        @asynccontextmanager
        async def session():
            yield SimpleNamespace()
        self.db = patch.object(service, "SessionLocal", session)
        self.db.start()
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://test")
        catalog = get_catalog(self.app)
        self.read = next(x.name for x in catalog.tools if x.path.endswith("/reports/query-samples") and not x.is_write)
        self.write = next(x.name for x in catalog.tools if x.path.endswith("/reports/query-samples") and x.is_write)
        spec = next(x for x in catalog.tools if x.path == settings.api_prefix + "/data-query")
        self.assertFalse(spec.is_write)
        self.assertEqual((spec.group_id, spec.subgroup_id), ("25", "reporting"))

    async def asyncTearDown(self):
        await self.client.aclose()
        self.auth.stop()
        self.db.stop()

    async def query(self, actor="alice", **body):
        return await self.client.post(settings.api_prefix + "/data-query", headers={"Authorization": "Bearer test-bearer-" + actor},
                                      json={"source_tool": self.read, **body})

    async def test_all_pages_reuse_original_account_and_aggregate_complete_scope(self):
        for actor in ("alice", "bob"):
            result = await self.query(actor, all_pages=True, pagination={"location": "query", "page_size": 2},
                                     group_by=["owner"], metrics=[{"name": "sum", "op": "sum", "field": "amount"}])
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json()["items"], [{"owner": actor, "sum": "6"}])
            self.assertEqual(result.json()["source_rows"], 3)
            self.assertEqual(result.json()["aggregation_scope"], "all_matching_source_rows")
        self.assertEqual(self.calls, [("alice", 1), ("alice", 2), ("bob", 1), ("bob", 2)])

    async def test_single_page_scope_is_explicit(self):
        result = await self.query(metrics=[{"name": "count", "op": "count"}])
        self.assertEqual(result.json()["items"], [{"count": 1}])
        self.assertEqual(result.json()["source_total"], 3)
        self.assertEqual(result.json()["aggregation_scope"], "returned_source_rows")

    async def test_changed_duplicate_or_excessive_data_never_returns_partial_full_statistics(self):
        for mode, status in (("changed", 409), ("duplicate", 409), ("oversize", 413)):
            self.source_mode = mode
            result = await self.query(all_pages=True, pagination={"location": "query", "page_size": 2},
                                      metrics=[{"name": "count", "op": "count"}])
            self.assertEqual(result.status_code, status, result.text)
            self.assertNotIn("items", result.json())

    async def test_unauthenticated_write_and_recursive_sources_are_rejected(self):
        result = await self.query("invalid")
        self.assertEqual(result.status_code, 401)
        for name in (self.write, next(x.name for x in get_catalog(self.app).tools if x.path == settings.api_prefix + "/data-query")):
            result = await self.client.post(settings.api_prefix + "/data-query", headers={"Authorization": "Bearer test-bearer-alice"},
                                           json={"source_tool": name})
            self.assertEqual(result.status_code, 422, result.text)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
