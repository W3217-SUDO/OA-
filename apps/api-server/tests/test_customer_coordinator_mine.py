"""陶威 2026-10-31：协作人也算“我的客户”，行上标“协作”；协作人只能查看，不能修改。"""
import unittest

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.crm.router import list_customers
from app.core.permissions import (
    _case_coordinator_only, _case_view_only_capabilities, _deny_customer_coordinator_write, _ensure_record_visible, mark_coordinated_cases,
)
from app.database import Base
from app.models import BusinessRecord, SystemParameter, User


def identity(username, method="GET", role="staff"):
    return {"username": username, "display_name": "", "role": role, "role_ids": [role],
            "_actual_role": role, "_actual_role_ids": [role], "_page_menu_capability": True,
            "_request_method": method, "menu_keys": ["customer-mine"]}


class CustomerCoordinatorMineTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.sessions() as db:
            for username in ("codexmgr", "codexco", "codexother"):
                db.add(User(username=username, display_name=username, password_hash="isolated-only", department="CODEX", role="staff"))
            db.add(SystemParameter(category="customer_type", code="client", name="客户", is_active=True))
            db.add(BusinessRecord(id=1, module="customer", serial_no="KH1", title="管理的客户", status="T", owner="codexmgr",
                                  department="CODEX", data={"customer_managers": ["codexmgr"], "coordinators": ["codexco"]}))
            db.add(BusinessRecord(id=2, module="customer", serial_no="KH2", title="无关客户", status="T", owner="codexother",
                                  department="CODEX", data={"customer_managers": ["codexother"]}))
            db.add(BusinessRecord(id=11, module="case", serial_no="AJ1", title="协作客户的案件", status="文书准备", owner="codexmgr",
                                  department="CODEX", customer="管理的客户", data={"customer_record_id": 1}))
            db.add(BusinessRecord(id=12, module="case", serial_no="AJ2", title="本人承办的案件", status="文书准备", owner="codexco",
                                  department="CODEX", customer="管理的客户", data={"customer_record_id": 1, "case_team_usernames": ["codexco"]}))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def mine(self, username):
        async with self.sessions() as db:
            return await list_customers(scope="mine", customer_name="", customer_type="客户", manager="", page=1,
                                        page_size=15, identity=identity(username), db=db)

    async def test_coordinator_sees_customer_marked_as_coordination(self):
        result = await self.mine("codexco")
        self.assertEqual([item["id"] for item in result["items"]], [1])
        self.assertEqual(result["items"][0]["data"]["my_customer_relation"], "协作")
        manager = await self.mine("codexmgr")
        self.assertEqual([item["id"] for item in manager["items"]], [1])
        self.assertNotIn("my_customer_relation", manager["items"][0]["data"])
        self.assertEqual((await self.mine("codexother"))["items"][0]["id"], 2)

    async def test_coordinator_can_read_but_not_write(self):
        async with self.sessions() as db:
            customer = await db.get(BusinessRecord, 1)
            await _deny_customer_coordinator_write(customer, identity("codexco", "GET"), db)
            with self.assertRaises(HTTPException) as caught:
                await _deny_customer_coordinator_write(customer, identity("codexco", "POST"), db)
            self.assertEqual(caught.exception.status_code, 403)
            await _deny_customer_coordinator_write(customer, identity("codexmgr", "POST"), db)
            await _deny_customer_coordinator_write(customer, identity("codexco", "POST", role="admin"), db)

    async def test_coordinator_opens_detail_only_for_reads(self):
        reader = {**identity("codexco", "GET"), "_page_menu_capability": False}
        async with self.sessions() as db:
            self.assertEqual((await _ensure_record_visible(1, reader, db)).id, 1)
            with self.assertRaises(HTTPException) as caught:
                await _ensure_record_visible(1, {**reader, "_request_method": "POST"}, db)
            self.assertEqual(caught.exception.status_code, 404)
            with self.assertRaises(HTTPException):
                await _ensure_record_visible(2, reader, db)

    async def test_coordinator_cases_are_marked_and_view_only(self):
        async with self.sessions() as db:
            items = await mark_coordinated_cases([{"id": 11, "data": {}}, {"id": 12, "data": {}}], identity("codexco"), db)
            self.assertEqual(items[0]["data"].get("my_case_relation"), "协作")
            self.assertNotIn("my_case_relation", items[1]["data"])
            reader = {**identity("codexco", "GET"), "_page_menu_capability": False}
            self.assertEqual((await _ensure_record_visible(11, reader, db)).id, 11)
            self.assertTrue(await _case_coordinator_only(await db.get(BusinessRecord, 11), identity("codexco", "POST"), db))
            self.assertFalse(await _case_coordinator_only(await db.get(BusinessRecord, 12), identity("codexco", "POST"), db))
            with self.assertRaises(HTTPException) as caught:
                await _deny_customer_coordinator_write(await db.get(BusinessRecord, 11), identity("codexco", "POST"), db)
            self.assertEqual(caught.exception.status_code, 403)
        view_only = _case_view_only_capabilities({"can_write": True, "can_create_finance": True, "can_view_case_logs": True, "team_role": "x"})
        self.assertEqual((view_only["can_write"], view_only["can_create_finance"], view_only["can_view_case_logs"]), (False, False, True))


if __name__ == "__main__":
    unittest.main()
