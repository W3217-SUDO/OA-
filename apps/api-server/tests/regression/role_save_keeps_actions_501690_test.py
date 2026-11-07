"""501690：角色不改东西保存，页面和功能都不能变，也不能变多；取消的开关要真的取消。内部账号和外部账号都走真实令牌。"""
import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.cases import _case_action_granted
from app.core.constants import CUSTOMER_ROLE_ACTIONS, IPR_ROLE_ACTIONS
from app.core.data_scope_gate import reset_gate_cache
from app.data_models.identity import JobRole, SystemMenu
from app.database import Base, get_db
from app.main import app
from app.core.constants import DEFAULT_SYSTEM_MENUS
from app.models import BusinessRecord, User
from app.security import create_token

API = settings.api_prefix
CUSTOMER_PAGES = ["customer-mine", "customer-company", "customer-dept"]
CRM_BASE = [f"action:{code}" for code in ("crm.customer.update", "crm.customer.release", "crm.customer.share", "crm.customer.assign", "crm.customer.recycle")]
IPR = [f"action:{code}" for code in ("ipr.case.create", "ipr.case.update", "ipr.case.file.manage")]


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node.get("children") or [])


class RoleSaveKeepsActions(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        reset_gate_cache()
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all(SystemMenu(key=key, parent_key=parent, label=label, icon=icon or "", sort_order=order, description="", is_visible=True, is_active=True)
                       for key, parent, label, icon, order in DEFAULT_SYSTEM_MENUS)
            db.add_all([
                JobRole(code="R-IN", name="内部甲", permissions=[*CUSTOMER_PAGES, *CRM_BASE, *IPR], field_keys=[], is_active=True),
                JobRole(code="R-PARENT", name="内部乙", permissions=["ipr", "customer", *CRM_BASE], field_keys=[], is_active=True),
                JobRole(code="LEGACY-EXT-SOURCE", name="外部案源人", permissions=["customer-mine", *CRM_BASE, *IPR], field_keys=[], is_active=True),
                User(username="root690", display_name="管理员", password_hash="x", department="D", role="admin", role_ids=["admin"], is_active=True, profile={}),
                User(username="in690", display_name="内部", password_hash="x", department="D", role="user", role_ids=["user"], is_active=True, profile={"permission_role": "内部甲"}),
                User(username="pa690", display_name="内部二", password_hash="x", department="D", role="user", role_ids=["user"], is_active=True, profile={"permission_role": "内部乙"}),
                User(username="ex690", display_name="外部", password_hash="x", department="D", role="user", role_ids=["user"], is_active=True, profile={"permission_role": "外部案源人"}),
            ])
            await db.commit()
            self.role_id = {role.code: role.id for role in (await db.scalars(select(JobRole))).all()}

        async def override_db():
            async with self.sessions() as db:
                yield db
        self.previous = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous)
        await self.engine.dispose()
        reset_gate_cache()

    def headers(self, username):
        return {"Authorization": "Bearer " + create_token(username, "admin" if username == "root690" else "user", 30)}

    async def me(self, username):
        response = await self.client.get(f"{API}/auth/me", headers=self.headers(username))
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        return set(data["menu_keys"]), set(data["configured_action_keys"])

    async def tree_payload(self, code):
        """和页面一样：只提交树上有、并且勾着的节点。"""
        response = await self.client.get(f"{API}/hr/job-roles/{self.role_id[code]}/permissions", headers=self.headers("root690"))
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        keys = {str(node["key"]) for node in walk(data["tree"])}
        return [value for value in data["checked_permissions"] if (value if value.startswith("action:") else f"menu:{value}") in keys], keys

    async def save(self, code, permissions):
        response = await self.client.patch(f"{API}/hr/job-roles/{self.role_id[code]}/permissions", json={"permissions": permissions, "case_actions_explicit": True},
                                           headers=self.headers("root690"))
        self.assertEqual(response.status_code, 200, response.text)

    async def backend_can(self, username, code):
        async with self.sessions() as db:
            identity = {"username": username, "role": "user", "role_ids": ["user"], "_actual_role_ids": ["user"], "permission_role": ""}
            return await _case_action_granted(identity, db, code)

    async def test_unchanged_save_changes_nothing(self):
        for code, username in (("R-IN", "in690"), ("R-PARENT", "pa690"), ("LEGACY-EXT-SOURCE", "ex690")):
            before = await self.me(username)
            backend = {action: await self.backend_can(username, action) for action in (*CUSTOMER_ROLE_ACTIONS, *IPR_ROLE_ACTIONS) if isinstance(action, str)}
            payload, _keys = await self.tree_payload(code)
            await self.save(code, payload)
            self.assertEqual(await self.me(username), before, code)
            for action, allowed in backend.items():
                self.assertEqual(await self.backend_can(username, action), allowed, f"{code} {action}")
            # 再存一次也不变
            payload, _keys = await self.tree_payload(code)
            await self.save(code, payload)
            self.assertEqual(await self.me(username), before, f"{code} 第二次")

    async def test_tree_shows_real_state_for_old_roles(self):
        payload, keys = await self.tree_payload("R-IN")
        self.assertIn("action:crm.customer.update@customer-mine", payload)
        self.assertIn("action:crm.customer.update@customer-mine", keys)

    async def test_unticking_really_closes(self):
        payload, _keys = await self.tree_payload("R-IN")
        target = "action:crm.customer.update@customer-mine"
        await self.save("R-IN", [value for value in payload if value != target])
        _menus, actions = await self.me("in690")
        self.assertNotIn("crm.customer.update@customer-mine", actions)
        self.assertIn("crm.customer.update@customer-company", actions)
        payload, _keys = await self.tree_payload("R-IN")
        self.assertNotIn(target, payload, "重新打开树仍是没勾")
        await self.save("R-IN", [value for value in payload if not value.startswith("action:crm.customer.update@")])
        _menus, actions = await self.me("in690")
        self.assertFalse([code for code in actions if code.startswith("crm.customer.update")], "全部取消后这个功能就没了")

    async def test_removing_last_center_page_revokes_its_actions(self):
        async with self.sessions() as db:
            customer = BusinessRecord(module="customer", serial_no="C690", title="我的客户", customer="我的客户", owner="in690", department="D", status="正常", data={})
            db.add(customer)
            await db.commit()
            customer_id = customer.id
        payload, _keys = await self.tree_payload("R-IN")
        # 取消全部客户页面，功能开关照页面原样留着（页面上取消页面不会自动取消功能）。
        kept = [value for value in payload if not value.startswith("customer")]
        await self.save("R-IN", kept)
        menus, actions = await self.me("in690")
        self.assertFalse([key for key in menus if key.startswith("customer")])
        self.assertFalse([code for code in actions if code.startswith("crm.")], "取消最后一个页面，这个中心的功能就没了")
        for method, path, body in (("PATCH", f"/customers/{customer_id}", {"title": "x"}), ("POST", f"/customers/{customer_id}/notes", {"content": "x"}), ("POST", f"/customers/{customer_id}/recycle", {})):
            response = await self.client.request(method, API + path, json=body, headers=self.headers("in690"))
            self.assertEqual(response.status_code, 403, f"{method} {path}: {response.text}")
        # 再加回一页，只有页面带出的功能，旧功能不回来。
        payload, _keys = await self.tree_payload("R-IN")
        await self.save("R-IN", [*payload, "customer-mine"])
        _menus, actions = await self.me("in690")
        self.assertFalse([code for code in actions if code.startswith("crm.customer.update")], "加回页面不带回旧功能")

    async def test_save_never_adds_power(self):
        for code, username in (("R-IN", "in690"), ("LEGACY-EXT-SOURCE", "ex690")):
            menus, actions = await self.me(username)
            payload, _keys = await self.tree_payload(code)
            await self.save(code, payload)
            after_menus, after_actions = await self.me(username)
            self.assertLessEqual(after_menus, menus)
            self.assertLessEqual(after_actions, actions)


if __name__ == "__main__":
    unittest.main()
