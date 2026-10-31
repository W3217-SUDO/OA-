"""陶威 2026-10-31：协作人也算“我的客户”，行上标“协作”；协作人只能查看，不能修改。"""
import unittest

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.crm.router import list_customers
from app.core.permissions import _deny_customer_coordinator_write, _ensure_record_visible
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


if __name__ == "__main__":
    unittest.main()
