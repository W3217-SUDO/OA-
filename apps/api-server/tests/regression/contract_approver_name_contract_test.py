"""Contract approver names stay human-readable while usernames remain ACL keys."""

import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, ContractApprovalStep, JobRole, RolePermission, User
from app.security import current_identity


ADMIN = {"username": "admin", "role": "admin", "display_name": "系统管理员", "department": "上海分所"}
API = settings.api_prefix


class ContractApproverNameContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        tables = [User.__table__, BusinessRecord.__table__, ContractApprovalStep.__table__, JobRole.__table__, RolePermission.__table__]
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda sync_connection: Base.metadata.create_all(sync_connection, tables=tables))
        async with self.sessions() as db:
            db.add_all([
                User(username="zhangsan", display_name="张三", department="上海分所", role="user", password_hash="test", is_active=True, profile={"contract_approval_enabled": True}),
                User(username="ceshi", display_name="测试2", department="上海分所", role="user", password_hash="test", is_active=True, profile={"contract_approval_enabled": True}),
                User(username="job-title", display_name="范围经理", department="上海分所", role="user", password_hash="test", is_active=True, profile={"contract_approval_enabled": True}),
                User(username="missing-name", display_name="", department="上海分所", role="user", password_hash="test", is_active=True, profile={"contract_approval_enabled": True}),
                User(username="alice-account", display_name="Alice Smith", department="Shanghai", role="user", password_hash="test", is_active=True, profile={"contract_approval_enabled": False}),
            ])
            db.add_all([
                BusinessRecord(module="hr", serial_no="HR-NAME-01", title="张三", status="在职", owner="zhangsan", department="上海分所", data={"username": "zhangsan"}),
                BusinessRecord(module="hr", serial_no="HR-NAME-01B", title="测试2", status="在职", owner="ceshi", department="上海分所", data={"username": "ceshi"}),
                BusinessRecord(module="hr", serial_no="HR-NAME-01-DUP", title="张三", status="在职", owner="zhangsan", department="上海分所", data={"username": "zhangsan"}),
                BusinessRecord(module="hr", serial_no="HR-NAME-02", title="范围经理", status="在职", owner="job-title", department="上海分所", data={"username": "job-title"}),
                BusinessRecord(module="hr", serial_no="HR-NAME-03", title="待维护", status="在职", owner="missing-name", department="上海分所", data={"username": "missing-name"}),
                BusinessRecord(module="hr", serial_no="HR-NAME-04", title="Alice Smith", status="在职", owner="alice-account", department="Shanghai", data={"username": "alice-account"}),
            ])
            contract = BusinessRecord(
                module="contract",
                serial_no="HT-NAME-01",
                title="中文姓名合同",
                customer="中文客户",
                status="审批中",
                owner="zhangsan",
                department="上海分所",
                data={
                    "source_person": "zhangsan",
                    "customer_managers": ["zhangsan", "missing-name"],
                    "submitted_by": "job-title",
                    "current_approver": "zhangsan",
                },
            )
            db.add(contract)
            await db.flush()
            db.add(ContractApprovalStep(contract_record_id=contract.id, step_order=1, approver="zhangsan", status="待审批"))
            await db.commit()
            self.contract_id = contract.id

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://contract-name.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_approver_settings_filter_duplicate_and_missing_names_without_losing_cleanup_access(self):
        settings_response = await self.client.get(f"{API}/contracts/approver-settings")
        self.assertEqual(settings_response.status_code, 200)
        items = {item["username"]: item for item in settings_response.json()["items"]}
        self.assertEqual(set(items), {"zhangsan", "ceshi", "job-title", "missing-name", "alice-account"})
        self.assertEqual(items["zhangsan"]["display_name"], "张三")
        self.assertTrue(items["zhangsan"]["display_name_valid"])
        self.assertEqual(items["ceshi"]["display_name"], "测试2")
        self.assertTrue(items["ceshi"]["display_name_valid"])
        self.assertEqual(items["alice-account"]["display_name"], "Alice Smith")
        self.assertTrue(items["alice-account"]["display_name_valid"])
        self.assertEqual(items["job-title"]["display_name"], "范围经理")
        self.assertTrue(items["job-title"]["display_name_valid"])
        self.assertTrue(items["job-title"]["selected"])
        self.assertTrue(items["missing-name"]["selected"])

        directory = await self.client.get(f"{API}/users/directory")
        self.assertEqual(directory.status_code, 200)
        approvers = {item["username"]: item["can_approve_contract"] for item in directory.json()["items"]}
        self.assertTrue(approvers["zhangsan"])
        self.assertTrue(approvers["ceshi"])
        self.assertTrue(approvers["job-title"])
        self.assertFalse(approvers["missing-name"])

        invalid = await self.client.put(f"{API}/contracts/approver-settings", json={"usernames": ["missing-name"]})
        self.assertEqual(invalid.status_code, 422)
        self.assertIn("有效姓名", invalid.json()["detail"])

        saved = await self.client.put(f"{API}/contracts/approver-settings", json={"usernames": ["zhangsan", "alice-account"]})
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["usernames"], ["alice-account", "zhangsan"])

    async def test_contract_records_and_approval_steps_return_display_fields_without_replacing_acl_usernames(self):
        records = await self.client.get(f"{API}/records", params={"module": "contract"})
        self.assertEqual(records.status_code, 200)
        record = records.json()["items"][0]
        self.assertEqual(record["owner"], "zhangsan")
        self.assertEqual(record["owner_display_name"], "张三")
        self.assertEqual(record["data"]["source_person"], "zhangsan")
        self.assertEqual(record["data"]["source_person_display_name"], "张三")
        self.assertEqual(record["data"]["customer_manager_display_names"], ["张三", "姓名待维护"])

        approvals = await self.client.get(f"{API}/contracts/{self.contract_id}/approvals")
        self.assertEqual(approvals.status_code, 200)
        self.assertEqual(approvals.json()["items"][0]["approver"], "zhangsan")
        self.assertEqual(approvals.json()["items"][0]["approver_display_name"], "张三")


if __name__ == "__main__":
    unittest.main()
