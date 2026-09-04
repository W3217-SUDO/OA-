"""Exercise performance HTTP routes against an isolated in-memory database."""
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import main as api
from app.models import Base, BusinessRecord, HrSubrecord, User, WorkflowEvent


class HrPerformanceManagementTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as db:
            db.add_all([
                User(username="manager", display_name="测试经理", department="部门", role="manager", password_hash="isolated"),
                User(username="reader", display_name="测试员工", department="部门", role="employee", password_hash="isolated"),
            ])
            db.add_all([BusinessRecord(id=101, module="hr", serial_no="CODEX-PERFORMANCE-A", title="测试员工甲", department="部门", owner="reader", status="在职", data={}),
                       BusinessRecord(id=102, module="hr", serial_no="CODEX-PERFORMANCE-B", title="测试员工乙", department="部门二", owner="other", status="在职", data={})])
            await db.commit()
        self.identity = {"username": "admin", "role": "admin"}
        async def identity():
            return self.identity
        async def database():
            async with self.sessions() as db:
                yield db
        api.app.dependency_overrides[api.current_identity] = identity
        api.app.dependency_overrides[api.get_db] = database
        self.permission = patch.object(api, "_permission_payload_for_identity", AsyncMock(return_value={"menu_keys": ["hr-performance"], "action_keys": []}))
        self.scope = patch.object(api, "_user_permission_payload", AsyncMock(return_value={"data_scope": "本部门数据"}))
        self.permission.start(); self.scope.start()
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app), base_url="http://test/api/v1")

    async def asyncTearDown(self):
        await self.client.aclose()
        api.app.dependency_overrides.clear()
        self.permission.stop(); self.scope.stop()
        await self.engine.dispose()

    async def create(self, employee_id=101, **data):
        response = await self.client.post("/hr/performance", json={"employee_id": employee_id, "data": {"start_date": "2026-01-01", "scheme_name": "CODEX-PERFORMANCE", "source_rate": 10, **data}})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def test_crud_shared_data_export_audit_and_case_resolution(self):
        item = await self.create()
        item_id = item["id"]
        self.assertEqual(item["data"]["source_rate"], 10)
        self.assertEqual((await self.client.get(f"/hr/performance/{item_id}")).json()["employee_name"], "测试员工甲")
        legacy = (await self.client.get("/hr/101/subrecords?kind=commission")).json()["items"]
        self.assertEqual(legacy[0]["id"], item_id)
        async with self.sessions() as db:
            scheme = await api._commission_scheme_for_case(101, api.date(2026, 6, 1), db)
            self.assertEqual(scheme["source_rate"], 10)
        updated = await self.client.patch(f"/hr/performance/{item_id}", json={"data": {**item["data"], "base_salary": 8000, "remark": "已调整"}})
        self.assertEqual(updated.status_code, 200, updated.text)
        export = await self.client.get("/hr/performance/export?employee_id=101")
        self.assertEqual(export.status_code, 200, export.text)
        self.assertIn("text/csv", export.headers["content-type"])
        self.assertIn("已调整", export.text)
        self.assertEqual((await self.client.delete(f"/hr/performance/{item_id}")).status_code, 204)
        self.assertEqual((await self.client.get(f"/hr/performance/{item_id}")).status_code, 404)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(HrSubrecord)), 0)
            events = (await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == 101))).all()
            self.assertEqual([event.action for event in events], ["新增绩效方案", "修改绩效方案", "删除绩效方案"])
            self.assertTrue(all(str(item_id) in event.comment for event in events))

    async def test_effective_period_department_pagination_and_scope(self):
        own = await self.create(end_date="2026-03-31")
        other = await self.create(102)
        result = await self.client.get("/hr/performance?department=部门&start_date=2026-03-31&end_date=2026-04-01")
        self.assertEqual([row["id"] for row in result.json()["items"]], [own["id"]])
        result = await self.client.get("/hr/performance?start_date=2027-01-01")
        self.assertEqual([row["id"] for row in result.json()["items"]], [other["id"]])
        result = await self.client.get("/hr/performance?page_size=1&page=2")
        self.assertEqual(result.json()["total"], 2)
        self.assertEqual(len(result.json()["items"]), 1)
        self.identity = {"username": "manager", "role": "manager"}
        self.assertEqual((await self.client.get("/hr/performance")).json()["total"], 1)
        self.assertEqual((await self.client.get(f"/hr/performance/{other['id']}")).status_code, 404)
        self.assertEqual((await self.client.delete(f"/hr/performance/{other['id']}")).status_code, 404)
        self.assertNotIn("测试员工乙", (await self.client.get("/hr/performance/export")).text)
        self.assertEqual((await self.client.patch(f"/hr/performance/{own['id']}", json={"data": own["data"]})).status_code, 200)
        self.identity = {"username": "reader", "role": "employee"}
        self.assertEqual((await self.client.delete(f"/hr/performance/{own['id']}")).status_code, 403)
        self.assertEqual((await self.client.post("/hr/101/subrecords", json={"kind": "commission", "data": own["data"]})).status_code, 403)
        with patch.object(api, "_permission_payload_for_identity", AsyncMock(return_value={"menu_keys": [], "action_keys": []})):
            self.assertEqual((await self.client.get("/hr/performance")).status_code, 403)
            self.assertEqual((await self.client.get("/hr/101/subrecords?kind=commission")).status_code, 403)

    async def test_validation_legacy_entry_and_no_partial_writes(self):
        for value in ("NaN", "Infinity", "bad", -1):
            response = await self.client.post("/hr/performance", json={"employee_id": 101, "data": {"start_date": "2026-01-01", "base_salary": value}})
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual((await self.client.get("/hr/performance?start_date=2026-03-01&end_date=2026-01-01")).status_code, 422)
        response = await self.client.post("/hr/101/subrecords", json={"kind": "commission", "data": {"start_date": "2026-01-01", "source_rate": ".1"}})
        self.assertEqual(response.status_code, 201, response.text)
        item = response.json()
        self.assertEqual((await self.client.get(f"/hr/performance/{item['id']}")).json()["data"]["source_rate"], .1)
        self.assertEqual((await self.client.delete(f"/hr/101/subrecords/{item['id']}")).status_code, 204)
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(HrSubrecord)), 0)
            self.assertEqual(await db.scalar(select(func.count()).select_from(WorkflowEvent)), 2)


if __name__ == "__main__":
    unittest.main()
