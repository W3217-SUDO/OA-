"""陶威/陶国南 2026-10-31：旧系统的多位客户管理人（迁移在 coordinators）也算“我的客户”，显示为客户管理人，权限相同。"""
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
            db.add(BusinessRecord(id=13, module="case", serial_no="AJ3", title="管理客户的他人案件", status="文书准备", owner="codexother",
                                  department="CODEX", customer="管理的客户", data={"customer_record_id": 1, "case_team_usernames": ["codexother"]}))
            db.add(BusinessRecord(id=14, module="case", serial_no="AJ4", title="调查员案件", status="文书准备", owner="codexother",
                                  department="CODEX", customer="无关客户", data={"customer_record_id": 2, "investigator": "调查员姓名",
                                                                              "investigator_username": "codexco"}))
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
        self.assertNotIn("my_customer_relation", result["items"][0]["data"])
        self.assertEqual(len(result["items"][0]["data"]["customer_manager_display_names"]), 2)
        manager = await self.mine("codexmgr")
        self.assertEqual([item["id"] for item in manager["items"]], [1])
        self.assertNotIn("my_customer_relation", manager["items"][0]["data"])
        self.assertEqual((await self.mine("codexother"))["items"][0]["id"], 2)

    async def test_coordinator_can_write_customer_like_manager(self):
        # 陶国南 2026-10-31：协作人与客户管理人权限一样。
        async with self.sessions() as db:
            customer = await db.get(BusinessRecord, 1)
            await _deny_customer_coordinator_write(customer, identity("codexco", "POST"), db)
            reader = {**identity("codexco", "POST"), "_page_menu_capability": False}
            self.assertEqual((await _ensure_record_visible(1, reader, db)).id, 1)

    async def test_only_creator_without_linked_data_can_delete(self):
        from app.core.crm import customer_delete_denials
        async with self.sessions() as db:
            db.add(BusinessRecord(id=3, module="customer", serial_no="KH3", title="新建空客户", status="T", owner="codexmgr",
                                  department="CODEX", data={"customer_managers": ["codexmgr"], "created_by": "codexmgr"}))
            await db.commit()
            customers = [await db.get(BusinessRecord, record_id) for record_id in (1, 3)]
            mine = await customer_delete_denials(customers, identity("codexmgr"), db)
            self.assertIn("案件", mine[1])
            self.assertNotIn(3, mine)
            other = await customer_delete_denials(customers, identity("codexco"), db)
            self.assertEqual(other[3], "只有客户的创建人可以删除客户")
            admin = await customer_delete_denials(customers, identity("codexco", role="admin"), db)
            self.assertNotIn(3, admin)
            self.assertIn(1, admin)

    async def test_coordinator_opens_detail(self):
        reader = {**identity("codexco", "GET"), "_page_menu_capability": False}
        async with self.sessions() as db:
            self.assertEqual((await _ensure_record_visible(1, reader, db)).id, 1)
            with self.assertRaises(HTTPException):
                await _ensure_record_visible(2, reader, db)

    async def test_coordinator_cases_are_marked_and_view_only(self):
        async with self.sessions() as db:
            items = await mark_coordinated_cases([{"id": 11, "data": {}}, {"id": 12, "data": {}}], identity("codexco"), db)
            self.assertEqual(items[0]["data"].get("my_case_relation"), "客户管理")
            self.assertNotIn("my_case_relation", items[1]["data"])
            reader = {**identity("codexco", "GET"), "_page_menu_capability": False}
            self.assertEqual((await _ensure_record_visible(11, reader, db)).id, 11)
            self.assertTrue(await _case_coordinator_only(await db.get(BusinessRecord, 11), identity("codexco", "POST"), db))
            self.assertFalse(await _case_coordinator_only(await db.get(BusinessRecord, 12), identity("codexco", "POST"), db))
            with self.assertRaises(HTTPException) as caught:
                await _deny_customer_coordinator_write(await db.get(BusinessRecord, 11), identity("codexco", "POST"), db)
            self.assertEqual(caught.exception.status_code, 403)
        async with self.sessions() as db:
            managed = await mark_coordinated_cases([{"id": 11, "data": {}}, {"id": 13, "data": {}}], identity("codexmgr"), db)
            self.assertNotIn("my_case_relation", managed[0]["data"])
            self.assertEqual(managed[1]["data"].get("my_case_relation"), "客户管理")
            self.assertTrue(await _case_coordinator_only(await db.get(BusinessRecord, 13), identity("codexmgr", "POST"), db))
        view_only = _case_view_only_capabilities({"can_write": True, "can_create_finance": True, "can_view_case_logs": True, "team_role": "x"})
        self.assertEqual((view_only["can_write"], view_only["can_create_finance"], view_only["can_view_case_logs"]), (False, False, True))

    async def test_migrated_investigator_username_counts_as_my_case(self):
        from sqlalchemy import select
        from app.core.permissions import _case_mine_scope_condition
        async with self.sessions() as db:
            ids = set((await db.scalars(select(BusinessRecord.id).where(
                BusinessRecord.module == "case", await _case_mine_scope_condition({"username": "codexco"}, db),
            ))).all())
        self.assertIn(14, ids)

    async def test_assign_replaces_managers_and_clears_migrated_ones(self):
        from app.areas.crm.router import update_customer_managers
        from app.models_shared import CustomerManagersInput
        admin = {**identity("codexmgr", "PUT", role="admin"), "action_keys": ["*"]}
        async with self.sessions() as db:
            await update_customer_managers(1, CustomerManagersInput(managers=["codexother"]), admin, db)
        async with self.sessions() as db:
            customer = await db.get(BusinessRecord, 1)
            self.assertEqual(customer.data["customer_managers"], ["codexother"])
            self.assertEqual(customer.data["coordinators"], [])
            self.assertEqual(customer.data["assignment_history"][-1]["previous_coordinators"], ["codexco"])
            self.assertEqual(customer.owner, "codexmgr")  # 案源人/负责人不随分配变化

    async def test_change_source_person_updates_owner(self):
        from app.areas.crm.router import change_customer_source_person
        from app.models_shared import CustomerSourcePersonInput
        admin = {**identity("codexmgr", "POST", role="admin"), "action_keys": ["*"]}
        async with self.sessions() as db:
            await change_customer_source_person(2, CustomerSourcePersonInput(source_person="codexco"), admin, db)
        async with self.sessions() as db:
            customer = await db.get(BusinessRecord, 2)
            self.assertEqual((customer.owner, customer.data["customer_source"]), ("codexco", "codexco"))
            self.assertEqual(customer.data["customer_managers"], ["codexother"])


if __name__ == "__main__":
    unittest.main()
