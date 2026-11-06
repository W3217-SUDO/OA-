"""页面能力不等于全所数据：页面头只放行所属中心，个人页面账号的导出和写按真实范围（陶威 2026-11-06）。"""
import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.data_scope_gate import (
    GATE_CONFIG_KEY, center_has_work_page, external_action_keys, header_read_kind, is_export_path, is_personal_page, reset_gate_cache,
)
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, JobRole, RolePermission, SystemConfig, User
from app.security import create_token
from tests.personnel_role_fixture import bind_system_role_pages

API = settings.api_prefix
PERSONAL_MENUS = ["customer-mine", "case-mine-civil", "task-my-created"]


class GateRulesTest(unittest.TestCase):
    def test_page_classes(self):
        for key in ("customer-mine", "case-new-civil", "seal-my-pending", "contract-recycle", "case-archive-refused"):
            self.assertTrue(is_personal_page(key), key)
        for key in ("customer-company", "case-dept-civil", "finance-receipts-new", "hr-new", "seal-audit-pending", "contract-company"):
            self.assertFalse(is_personal_page(key), key)
        self.assertFalse(center_has_work_page({"customer-mine"}, ("@root:customer",)))
        self.assertTrue(center_has_work_page({"customer-mine", "customer-company"}, ("@root:customer",)))

    def test_export_paths(self):
        for path in ("/records/export", "/records/export-excel", "/cases/export/excel", "/tasks/print-export",
                     "/finance/refunds/export-selected", "/finance/payment-packages/A1/print-word", "/ipr/official-files/download-zip"):
            self.assertTrue(is_export_path(path), path)
        for path in ("/records", "/customers", "/cases/summary", "/exporter-names"):
            self.assertFalse(is_export_path(path), path)

    def test_header_kinds(self):
        self.assertEqual(header_read_kind("/finance/transactions", ("case-mine-civil",), ("@root:finance", "@root:platform-finance")), "deny")
        self.assertEqual(header_read_kind("/finance/transactions", ("platform-finance-x",), ("@root:finance", "@root:platform-finance")), "allow")
        self.assertEqual(header_read_kind("/system/parameters/options", ("case-mine-civil",), ("@root:system",)), "allow")
        self.assertEqual(header_read_kind("/records", ("case-mine-civil",), ("@root:investigation",)), "scoped")
        self.assertEqual(header_read_kind("/agent-admin/overview", ("case-mine-civil",), ()), "deny")
        self.assertEqual(header_read_kind("/dashboard", ("case-mine-civil",), ()), "allow")


class DataScopeGateApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        reset_gate_cache()
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.sessions() as db:
            db.add_all([
                User(username="GATEPERSONAL", display_name="个人页面", password_hash="x", department="D", role="user"),
                User(username="GATEWORK", display_name="全所页面", password_hash="x", department="D", role="manager"),
                RolePermission(role="user", display_name="普通员工", data_scope="本人及共享数据", menu_keys=PERSONAL_MENUS, field_keys=[]),
                RolePermission(role="manager", display_name="工作页面", data_scope="本人及共享数据",
                               menu_keys=["customer-company", "customer-mine"], field_keys=[]),
                BusinessRecord(module="customer", serial_no="GATE-C1", title="别人的客户", owner="SOMEONE", status="正常", customer="别人的客户", data={}),
                BusinessRecord(module="customer", serial_no="GATE-C2", title="自己的客户", owner="GATEPERSONAL", status="正常", customer="自己的客户", data={}),
                BusinessRecord(module="finance", serial_no="GATE-F1", title="别人的费用", owner="SOMEONE", status="正常", customer="", data={}),
                BusinessRecord(module="clue", serial_no="GATE-L1", title="别人的线索", owner="SOMEONE", status="正常", customer="", data={}),
            ])
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        await bind_system_role_pages(self.sessions)
        self.personal = self._client("GATEPERSONAL", "user")
        self.work = self._client("GATEWORK", "manager")

    def _client(self, username, role):
        token = create_token(username, role, 30)
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test",
                                 headers={"Authorization": f"Bearer {token}"})

    async def asyncTearDown(self):
        await self.personal.aclose()
        await self.work.aclose()
        app.dependency_overrides.pop(get_db, None)
        await self.engine.dispose()
        reset_gate_cache()

    async def _records(self, client, module, page=None):
        headers = {"X-OA-Page": page} if page else {}
        return await client.get(f"{API}/records", params={"module": module, "page_size": 50}, headers=headers)

    async def test_header_no_longer_opens_other_center_data(self):
        self.assertEqual((await self._records(self.personal, "finance")).status_code, 403)
        response = await self._records(self.personal, "finance", "case-mine-civil")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 0)  # 下拉保留，但只有本人范围
        admin_tool = await self.personal.get(f"{API}/agent-admin/overview", headers={"X-OA-Page": "case-mine-civil"})
        self.assertEqual(admin_tool.status_code, 403)

    async def test_personal_page_writes_use_actual_scope(self):
        rows = (await self._records(self.personal, "customer")).json()["items"]
        ids = {row["serial_no"]: row["id"] for row in rows}
        self.assertEqual(set(ids), {"GATE-C1", "GATE-C2"})  # 本中心读取第 1 步不变
        denied = await self.personal.patch(f"{API}/records/{ids['GATE-C1']}", json={"title": "改别人的"})
        self.assertEqual(denied.status_code, 404)
        allowed = await self.personal.patch(f"{API}/records/{ids['GATE-C2']}", json={"title": "改自己的"})
        self.assertEqual(allowed.status_code, 200, allowed.text)

    async def test_personal_page_writes_do_not_become_admin(self):
        async with self.sessions() as db:
            task = BusinessRecord(module="task", serial_no="GATE-T1", title="别人的任务", owner="SOMEONE", status="待接收", customer="", data={})
            db.add(task)
            await db.commit()
        denied = await self.personal.post(f"{API}/tasks/{task.id}/accept", json={"comment": ""})
        self.assertEqual(denied.status_code, 403, denied.text)

    async def test_require_admin_not_granted_by_personal_page(self):
        from app.core.permissions import _require_admin
        from fastapi import HTTPException
        with self.assertRaises(HTTPException):
            _require_admin({"role": "user", "role_ids": ["user"], "_actual_role_ids": ["user"],
                            "_page_menu_capability": True, "_page_scope_actual": True})
        _require_admin({"role": "admin", "role_ids": ["admin", "user"], "_actual_role_ids": ["user"], "_page_menu_capability": True})

    async def test_personal_page_keeps_functions_on_own_records(self):
        rows = (await self._records(self.personal, "customer")).json()["items"]
        own = next(row for row in rows if row["serial_no"] == "GATE-C2")
        identity_check = await self.personal.delete(f"{API}/records/{own['id']}")
        self.assertNotEqual(identity_check.status_code, 403, identity_check.text)

    async def test_personal_page_export_uses_actual_scope(self):
        response = await self.personal.get(f"{API}/records/export", params={"module": "customer"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("GATE-C2", response.text)
        self.assertNotIn("GATE-C1", response.text)

    async def test_work_page_account_unchanged(self):
        rows = (await self._records(self.work, "customer")).json()["items"]
        target = next(row for row in rows if row["serial_no"] == "GATE-C1")
        changed = await self.work.patch(f"{API}/records/{target['id']}", json={"title": "部门改"})
        self.assertEqual(changed.status_code, 200, changed.text)
        exported = await self.work.get(f"{API}/records/export", params={"module": "customer"})
        self.assertIn("GATE-C1", exported.text)

    async def test_switch_off_restores_old_behaviour(self):
        async with self.sessions() as db:
            db.add(SystemConfig(key=GATE_CONFIG_KEY, label="数据范围闸门", group="权限", value="off"))
            await db.commit()
        reset_gate_cache()
        response = await self._records(self.personal, "finance", "case-mine-civil")
        self.assertEqual(response.json()["total"], 1)

    async def test_shadow_log_records_without_blocking(self):
        with self.assertLogs("app.core.data_scope_gate", level="INFO") as logs:
            response = await self._records(self.work, "customer", "customer-company")
        self.assertEqual(response.status_code, 200)
        self.assertIn("page-scope-shadow user=GATEWORK", logs.output[0])

    async def test_login_identity_never_blocked(self):
        me = await self.personal.get(f"{API}/auth/me", headers={"X-OA-Page": "not-a-real-page"})
        self.assertEqual(me.status_code, 200)


class ExternalAccountTest(unittest.IsolatedAsyncioTestCase):
    """外部账号按老系统：本中心也只看本人，客户不能导出，动作只给老系统有的。"""

    async def asyncSetUp(self):
        reset_gate_cache()
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.sessions() as db:
            db.add_all([
                User(username="EXTSOURCE", display_name="外部案源", password_hash="x", department="D", role="user",
                     profile={"permission_role": "外部案源人"}),
                User(username="EXTLAWYER", display_name="合作律师", password_hash="x", department="D", role="user",
                     profile={"permission_role": "合作律师"}),
                JobRole(code="LEGACY-EXT-SOURCE", name="外部案源人", permissions=["customer-mine", "case-mine-civil", "finance-receipts-claim"], field_keys=[]),
                JobRole(code="LEGACY-COOP-LAWYER", name="合作律师", permissions=["customer-mine", "case-mine-civil"], field_keys=[]),
                RolePermission(role="user", display_name="普通员工", data_scope="本人及共享数据", menu_keys=[], field_keys=[]),
                BusinessRecord(module="customer", serial_no="EXT-C1", title="别人的客户", owner="SOMEONE", status="正常", customer="别人的客户", data={}),
                BusinessRecord(module="customer", serial_no="EXT-C2", title="自己的客户", owner="EXTSOURCE", status="正常", customer="自己的客户", data={}),
            ])
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        await bind_system_role_pages(self.sessions)
        token = create_token("EXTSOURCE", "user", 30)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test",
                                        headers={"Authorization": f"Bearer {token}"})
        token = create_token("EXTLAWYER", "user", 30)
        self.lawyer = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test",
                                        headers={"Authorization": f"Bearer {token}"})

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.lawyer.aclose()
        app.dependency_overrides.pop(get_db, None)
        await self.engine.dispose()
        reset_gate_cache()

    async def test_same_center_read_is_own_scope(self):
        for headers in ({}, {"X-OA-Page": "customer-mine"}):
            rows = (await self.client.get(f"{API}/records", params={"module": "customer", "page_size": 50}, headers=headers)).json()["items"]
            self.assertEqual([row["serial_no"] for row in rows], ["EXT-C2"])

    async def test_customer_export_refused(self):
        response = await self.client.get(f"{API}/records/export", params={"module": "customer"})
        self.assertEqual(response.status_code, 403)

    async def test_login_and_me_not_blocked(self):
        me = await self.client.get(f"{API}/auth/me")
        self.assertEqual(me.status_code, 200)

    async def test_actions_follow_legacy_role(self):
        codes = ["case.fee.update", "case.team.assign", "case.internal_fee.create", "case.merge", "task.confirm",
                 "contract.payment.writeoff", "conflict.review.approve", "case.log.create"]
        source = external_action_keys("外部案源人", codes)
        self.assertEqual(source, ["case.log.create"])
        lawyer = external_action_keys("合作律师", codes)
        self.assertEqual(set(lawyer), {"case.fee.update", "case.team.assign", "case.internal_fee.create", "case.log.create"})
        self.assertIn("task.confirm", external_action_keys("外部合作调查员", codes))
        self.assertIn("case.merge", external_action_keys("外部案源人", codes, ["case.merge"]))  # 员工管理按人给的优先
        me = (await self.client.get(f"{API}/auth/me")).json()["configured_action_keys"]
        self.assertNotIn("case.merge", me)

    async def test_customer_list_scope_needs_that_page(self):
        response = await self.client.get(f"{API}/customers", params={"scope": "company"})
        self.assertEqual(response.status_code, 403)

    async def test_switch_off_restores(self):
        async with self.sessions() as db:
            db.add(SystemConfig(key=GATE_CONFIG_KEY, label="数据范围闸门", group="权限", value="off"))
            await db.commit()
        reset_gate_cache()
        rows = (await self.client.get(f"{API}/records", params={"module": "customer", "page_size": 50})).json()["items"]
        self.assertEqual(len(rows), 2)


if __name__ == "__main__":
    unittest.main()
