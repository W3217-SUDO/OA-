"""账号安全（陶威 2026-11-07）：有人事页面的账号可以新增普通账号、重置普通员工密码、在普通角色之间换别人的角色；
系统管理员、高权限角色和这些账号本身只有真实系统管理员能动。本人改密码和登录不受影响。

页面能力会把人临时提升成 admin，所以全部走真实 JWT，不能用替换 current_identity 的写法。
"""
import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.data_scope_gate import reset_gate_cache
from app.core.permissions import is_high_privilege_job_role
from app.data_models.change_logs import DataChangeLog
from app.data_models.identity import JobRole
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, Department, SecurityPolicy, User
from app.security import create_token, hash_password, verify_password

API = settings.api_prefix
PASSWORD = "FakeRev#12345678"
NEW_PASSWORD = "OtherRev#1234567"
HR_PAGES = ["hr", "hr-all", "hr-new", "hr-roles", "hr-departments"]

def person(username, display_name, role="user", permission_role="", **profile):
    return User(username=username, display_name=display_name, password_hash=hash_password(PASSWORD), department="D", role=role, role_ids=[role],
                is_active=True, profile={"permission_role": permission_role, "staff_role": permission_role, **profile} if permission_role else profile)


def employee(username, display_name, position):
    return BusinessRecord(module="hr", serial_no=f"E-{username}", title=display_name, customer="公司", status="在职", owner=username, department="D",
                          data={"username": username, "position": position, "staff_role": position, "permission_role": position, "account_type": "员工账号"})


class AccountSecurityTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        reset_gate_cache()
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                JobRole(code="R-HR", name="人事甲", permissions=HR_PAGES, field_keys=[], is_active=True),
                JobRole(code="R-PLAIN", name="普通甲", permissions=["dashboard"], field_keys=[], is_active=True),
                JobRole(code="R-OTHER", name="普通乙", permissions=["case-mine"], field_keys=[], is_active=True),
                JobRole(code="R-HEAD", name="某部部长", permissions=["dashboard"], field_keys=[], is_active=True),
                JobRole(code="R-SCOPE", name="范围甲", permissions=["dashboard"], field_keys=[], is_active=True, data_scope="全所数据"),
                JobRole(code="R-FIN", name="审核甲", permissions=["finance-internal-audit"], field_keys=[], is_active=True),
                JobRole(code="R-SYS", name="配置甲", permissions=["system-management-config"], field_keys=[], is_active=True),
                JobRole(code="SYSTEM-ADMIN", name="系统管理员", permissions=["dashboard"], field_keys=[], is_active=True),
                JobRole(code="LEGACY-EXT-SOURCE", name="外部案源人", permissions=["dashboard"], field_keys=[], is_active=True),
                Department(code="D", name="D", is_active=True, sort_order=1, created_by="t", updated_by="t"),
                person("realadmin", "真实管理员", "admin"),
                person("hrholder", "人事账号", permission_role="人事甲"),
                person("plain", "普通账号", permission_role="普通甲"),
                person("external", "外部账号", permission_role="外部案源人"),
                person("victim", "目标账号", permission_role="普通甲"),
                person("boss", "部长账号", permission_role="某部部长"),
                person("auditor", "审核账号", "auditor", permission_role="普通甲"),
                employee("victim", "目标账号", "普通甲"), employee("boss", "部长账号", "某部部长"),
                employee("hrholder", "人事账号", "人事甲"), employee("realadmin", "真实管理员", "普通甲"),
                SecurityPolicy(min_password_length=8, max_failed_attempts=5, lock_minutes=15, token_minutes=480),
            ])
            await db.commit()
            self.uid = {user.username: user.id for user in (await db.scalars(select(User))).all()}
            self.emp = {row.owner: row.id for row in (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "hr"))).all()}

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

    async def role_row(self, code):
        async with self.sessions() as db:
            return await db.scalar(select(JobRole.id).where(JobRole.code == code))

    def headers(self, username):
        return {"Authorization": "Bearer " + create_token(username, "admin" if username == "realadmin" else "user", 30)}

    async def state(self, username):
        async with self.sessions() as db:
            user = await db.scalar(select(User).where(User.username == username))
            return None if user is None else (user.username, tuple(user.role_ids or []), user.password_hash, dict(user.profile or {}))

    def body(self, username="victim", display_name="目标账号", position="普通甲", **extra):
        return {"username": username, "display_name": display_name, "department": "D", "role": "user", "position": position,
                "is_active": True, "joined_at": "2024-01-01", "data": {}, **extra}

    async def call(self, username, method, path, body=None):
        return await self.client.request(method, API + path, json=body, headers=self.headers(username))

    def new_system_user(self, username, **extra):
        return {"username": username, "display_name": username, "department": "D", "role": "user", "password": PASSWORD, **extra}

    def new_employee(self, username, position="普通甲", **extra):
        return {"username": username, "display_name": username, "employee_no": "N-" + username, "company": "公司", "department": "D", "password": PASSWORD,
                "role": "user", "position": position, "is_active": True, "account_type": "员工账号", "data": {"joined_at": "2024-01-01"}, **extra}

    def forbidden(self):
        victim, admin, boss, auditor, me = (self.uid[name] for name in ("victim", "realadmin", "boss", "auditor", "hrholder"))
        emp = self.emp
        return [
            # 设成系统管理员或系统角色
            ("hr 他人提成 admin", "victim", "PATCH", f"/hr/employees/{emp['victim']}", self.body(role="admin")),
            ("hr 他人提成 manager", "victim", "PATCH", f"/hr/employees/{emp['victim']}", self.body(role="manager")),
            ("hr 自己提成 admin", "hrholder", "PATCH", f"/hr/employees/{emp['hrholder']}", self.body("hrholder", "人事账号", "人事甲", role="admin")),
            ("sys 他人提成 admin", "victim", "PATCH", f"/system/users/{victim}", {"role_ids": ["admin"]}),
            ("sys 他人 role=admin", "victim", "PATCH", f"/system/users/{victim}", {"role": "admin"}),
            ("sys 他人 manager", "victim", "PATCH", f"/system/users/{victim}", {"role": "manager"}),
            ("sys 自己提成 admin", "hrholder", "PATCH", f"/system/users/{me}", {"role_ids": ["admin"]}),
            # 换成高权限角色
            ("hr 换部长", "victim", "PATCH", f"/hr/employees/{emp['victim']}", self.body(position="某部部长")),
            ("hr 换系统管理员岗位", "victim", "PATCH", f"/hr/employees/{emp['victim']}", self.body(position="系统管理员")),
            ("hr 换全所范围角色", "victim", "PATCH", f"/hr/employees/{emp['victim']}", self.body(position="范围甲")),
            ("hr 换财务审核角色", "victim", "PATCH", f"/hr/employees/{emp['victim']}", self.body(position="审核甲")),
            ("hr 换人事角色", "victim", "PATCH", f"/hr/employees/{emp['victim']}", self.body(position="人事甲")),
            ("hr 换系统页面角色", "victim", "PATCH", f"/hr/employees/{emp['victim']}", self.body(position="配置甲")),
            ("sys 资料换高权限", "victim", "PATCH", f"/system/users/{victim}", {"profile": {"permission_role": "某部部长"}}),
            ("sys 资料带个人覆盖", "victim", "PATCH", f"/system/users/{victim}", {"profile": {"permission_overrides": {"menu_keys": ["hr-all"]}}}),
            # 不给自己换角色
            ("hr 自己换普通角色", "hrholder", "PATCH", f"/hr/employees/{emp['hrholder']}", self.body("hrholder", "人事账号", "普通乙")),
            ("sys 自己换角色", "hrholder", "PATCH", f"/system/users/{me}", {"profile": {"permission_role": "普通乙"}}),
            ("sys 自己改密码绕过原密码", "hrholder", "PATCH", f"/system/users/{me}", {"password": NEW_PASSWORD}),
            # 真实管理员和高权限账号本身
            ("重置真实管理员", "realadmin", "POST", f"/system/users/{admin}/reset-password", {"new_password": NEW_PASSWORD}),
            ("sys 改真实管理员密码", "realadmin", "PATCH", f"/system/users/{admin}", {"password": NEW_PASSWORD}),
            ("sys 改真实管理员用户名", "realadmin", "PATCH", f"/system/users/{admin}", {"username": "x-admin"}),
            ("sys 改真实管理员资料", "realadmin", "PATCH", f"/system/users/{admin}", {"department": "E"}),
            ("hr 改真实管理员", "realadmin", "PATCH", f"/hr/employees/{emp['realadmin']}", self.body("x-admin", "真实管理员")),
            ("绑定真实管理员钉钉", "realadmin", "PATCH", f"/system/users/{admin}/dingtalk", {"user_id": "FAKE"}),
            ("解绑真实管理员钉钉", "realadmin", "DELETE", f"/system/users/{admin}/dingtalk-bindings/FAKE", None),
            ("解锁真实管理员", "realadmin", "POST", f"/system/users/{admin}/unlock", {}),
            ("重置部长", "boss", "POST", f"/system/users/{boss}/reset-password", {"new_password": NEW_PASSWORD}),
            ("sys 改部长用户名", "boss", "PATCH", f"/system/users/{boss}", {"username": "x-boss"}),
            ("hr 部长换普通角色", "boss", "PATCH", f"/hr/employees/{emp['boss']}", self.body("boss", "部长账号", "普通乙")),
            ("绑定部长钉钉", "boss", "PATCH", f"/system/users/{boss}/dingtalk", {"user_id": "FAKE"}),
            ("重置带系统角色的账号", "auditor", "POST", f"/system/users/{auditor}/reset-password", {"new_password": NEW_PASSWORD}),
        ]

    def forbidden_new(self):
        return [
            ("sys 新建 admin", "POST", "/system/users", self.new_system_user("n1", role="admin")),
            ("sys 新建 manager", "POST", "/system/users", self.new_system_user("n2", role="manager")),
            ("sys 新建高权限角色", "POST", "/system/users", self.new_system_user("n3", profile={"permission_role": "某部部长"})),
            ("hr 新建 admin", "POST", "/hr/employees", self.new_employee("n4", role="admin")),
            ("hr 新建部长", "POST", "/hr/employees", self.new_employee("n5", position="某部部长")),
            ("hr 新建系统管理员岗位", "POST", "/hr/employees", self.new_employee("n6", position="系统管理员")),
        ]

    def test_high_privilege_is_by_capability(self):
        role = lambda name, permissions, code="R", scope=None: JobRole(code=code, name=name, permissions=permissions, data_scope=scope, field_keys=[])
        for item in (role("系统", [], "SYSTEM-ADMIN"), role("某部部长", []), role("客户主管", []), role("合伙人律师", []), role("甲", ["hr-all"]),
                     role("乙", ["system-management-config"]), role("丙", ["finance-internal-audit"]), role("丁", [], scope="全所数据")):
            self.assertTrue(is_high_privilege_job_role(item), item.name)
        for item in (role("普通", []), role("助理", ["case-mine", "customer-mine", "contract-mine"])):
            self.assertFalse(is_high_privilege_job_role(item), item.name)

    async def test_hr_holder_cannot_escalate_or_touch_protected(self):
        for name, target, method, path, body in self.forbidden():
            before = await self.state(target)
            response = await self.call("hrholder", method, path, body)
            self.assertEqual(response.status_code, 403, f"{name}: {response.text}")
            self.assertEqual(await self.state(target), before, name)
        self.assertEqual((await self.client.get(f"{API}/auth/me", headers=self.headers("hrholder"))).json()["actual_role_ids"], ["user"])

    async def test_hr_holder_cannot_create_privileged_accounts(self):
        for name, method, path, body in self.forbidden_new():
            response = await self.call("hrholder", method, path, body)
            self.assertEqual(response.status_code, 403, f"{name}: {response.text}")
        for username in ("n1", "n2", "n3", "n4", "n5", "n6"):
            self.assertIsNone(await self.state(username))

    async def test_accounts_without_hr_pages_get_nothing(self):
        for actor in ("plain", "external"):
            for name, _target, method, path, body in self.forbidden():
                self.assertEqual((await self.call(actor, method, path, body)).status_code, 403, f"{actor} {name}")
            for name, method, path, body in [*self.forbidden_new(), ("重置普通", "POST", f"/system/users/{self.uid['victim']}/reset-password", {"new_password": NEW_PASSWORD}),
                                             ("新建普通", "POST", "/system/users", self.new_system_user("n9"))]:
                self.assertEqual((await self.call(actor, method, path, body)).status_code, 403, f"{actor} {name}")

    async def test_hr_holder_can_reset_ordinary_password_with_trail(self):
        response = await self.call("hrholder", "POST", f"/system/users/{self.uid['victim']}/reset-password", {"new_password": NEW_PASSWORD})
        self.assertEqual(response.status_code, 200, response.text)
        login = await self.client.post(f"{API}/auth/login", data={"username": "victim", "password": NEW_PASSWORD})
        self.assertEqual(login.status_code, 200, login.text)
        self.assertTrue(login.json()["must_change_password"])
        async with self.sessions() as db:
            logs = (await db.scalars(select(DataChangeLog).where(DataChangeLog.table_name == "users", DataChangeLog.row_id == str(self.uid["victim"])))).all()
        self.assertTrue(any(log.actor == "hrholder" and "password_hash" in (log.changes or {}) for log in logs), "重置留痕要记操作人")

    async def test_hr_holder_can_create_ordinary_accounts(self):
        response = await self.call("hrholder", "POST", "/system/users", self.new_system_user("okuser"))
        self.assertEqual(response.status_code, 201, response.text)
        response = await self.call("hrholder", "POST", "/hr/employees", self.new_employee("okemp"))
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual((await self.state("okemp"))[1], ("user",))

    async def test_hr_holder_can_swap_ordinary_roles_of_others(self):
        response = await self.call("hrholder", "PATCH", f"/hr/employees/{self.emp['victim']}", self.body(position="普通乙"))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.state("victim"))[3]["permission_role"], "普通乙")
        self.assertEqual((await self.state("victim"))[1], ("user",))

    async def test_hr_holder_keeps_ordinary_edits(self):
        response = await self.call("hrholder", "PATCH", f"/hr/employees/{self.emp['victim']}", self.body(data={"staff_role": "普通甲", "note": "x"}))
        self.assertEqual(response.status_code, 200, response.text)
        after = await self.state("victim")
        self.assertEqual((after[1], after[3]["permission_role"], after[3]["note"]), (("user",), "普通甲", "x"))
        response = await self.call("hrholder", "PATCH", f"/hr/employees/{self.emp['hrholder']}", self.body("hrholder", "人事账号", "人事甲"))
        self.assertEqual(response.status_code, 200, "人事改自己的普通资料: " + response.text)
        response = await self.call("hrholder", "PATCH", f"/hr/employees/{self.emp['boss']}", self.body("boss", "部长账号", "某部部长", data={"note": "y"}))
        self.assertEqual(response.status_code, 200, "高权限账号的普通资料: " + response.text)
        response = await self.call("hrholder", "PATCH", f"/system/users/{self.uid['victim']}", {"department": "E", "role": "user", "username": "victim"})
        self.assertEqual(response.status_code, 200, "前端原样带回账号和角色: " + response.text)
        self.assertEqual((await self.call("hrholder", "PATCH", f"/system/users/{self.uid['victim']}", {"username": "victim2"})).status_code, 200, "普通账号改用户名")
        self.assertEqual((await self.call("hrholder", "POST", f"/system/users/{self.uid['boss']}/unlock", {})).status_code, 200)

    async def test_roles_cannot_be_used_to_bypass(self):
        high = await self.role_row("R-HEAD")
        cases = [
            ("停用角色", "PATCH", f"/hr/job-roles/{high}", {"is_active": False}),
            ("改角色名", "PATCH", f"/hr/job-roles/{high}", {"name": "普通丙"}),
            ("改角色代码", "PATCH", f"/hr/job-roles/{high}", {"code": "R-X"}),
            ("改数据范围", "PATCH", f"/hr/job-roles/{await self.role_row('R-HR')}", {"data_scope": "全所数据"}),
            ("改字段", "PATCH", f"/hr/job-roles/{await self.role_row('R-PLAIN')}", {"field_keys": []}),
            ("删角色", "DELETE", f"/hr/job-roles/{high}", None),
            ("新建带范围角色", "POST", "/hr/job-roles", {"code": "R-N1", "name": "新一", "data_scope": "全所数据"}),
        ]
        for name, method, path, body in cases:
            response = await self.call("hrholder", method, path, body)
            self.assertEqual(response.status_code, 403, f"{name}: {response.text}")
        self.assertEqual((await self.call("hrholder", "PATCH", f"/hr/job-roles/{high}", {"description": "说明", "sort_order": 3})).status_code, 200, "说明和排序照常")
        self.assertEqual((await self.call("hrholder", "PATCH", f"/hr/job-roles/{high}", {"name": "某部部长", "is_active": True})).status_code, 200, "没变不算改")

    async def test_inactive_or_unknown_role_cannot_be_assigned(self):
        async with self.sessions() as db:
            (await db.scalar(select(JobRole).where(JobRole.code == "R-HEAD"))).is_active = False
            await db.commit()
        before = await self.state("victim")
        response = await self.call("hrholder", "PATCH", f"/system/users/{self.uid['victim']}", {"profile": {"permission_role": "某部部长"}})
        self.assertEqual(response.status_code, 403, response.text)
        response = await self.call("hrholder", "PATCH", f"/system/users/{self.uid['victim']}", {"profile": {"permission_role_code": "R-HEAD"}})
        self.assertEqual(response.status_code, 403, response.text)
        response = await self.call("hrholder", "POST", "/system/users", self.new_system_user("n7", profile={"permission_role": "不存在的角色"}))
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(await self.state("victim"), before)

    async def test_protected_accounts_cannot_be_disabled_deleted_or_offboarded(self):
        for target in ("boss", "realadmin"):
            emp = self.emp[target]
            before = await self.state(target)
            for name, method, path, body in [
                ("关登录", "PATCH", f"/hr/employees/{emp}/login-status", {"is_active": False}),
                ("合同审批", "PATCH", f"/hr/employees/{emp}/contract-approval-status", {"contract_approval_enabled": True}),
                ("用印审批", "PATCH", f"/hr/employees/{emp}/seal-approval-status", {"seal_approval_enabled": True}),
                ("办离职", "POST", f"/hr/{emp}/transition", {"to_status": "离职", "effective_date": "2026-11-07", "reason": "测试原因"}),
                ("删档案", "DELETE", f"/hr/employees/{emp}", None),
            ]:
                response = await self.call("hrholder", method, path, body)
                self.assertIn(response.status_code, {403, 409}, f"{target} {name}: {response.text}")
                self.assertEqual(await self.state(target), before, f"{target} {name}")
        for path, body in ((f"/hr/employees/{self.emp['boss']}/login-status", {"is_active": False}),):
            self.assertEqual((await self.call("hrholder", "PATCH", path, body)).status_code, 403)
        self.assertEqual((await self.call("hrholder", "DELETE", f"/system/users/{self.uid['boss']}")).status_code, 403)

    async def test_cannot_grant_self_approval_or_write_it_through_profile(self):
        me = self.emp["hrholder"]
        for path, body in ((f"/hr/employees/{me}/contract-approval-status", {"contract_approval_enabled": True}), (f"/hr/employees/{me}/seal-approval-status", {"seal_approval_enabled": True})):
            self.assertEqual((await self.call("hrholder", "PATCH", path, body)).status_code, 403, path)
        self.assertEqual((await self.call("hrholder", "PATCH", f"/system/users/{self.uid['hrholder']}", {"profile": {"contract_approval_enabled": True}})).status_code, 403)
        self.assertFalse((await self.state("hrholder"))[3].get("contract_approval_enabled"))

    async def test_ordinary_targets_still_managed(self):
        emp = self.emp["victim"]
        self.assertEqual((await self.call("hrholder", "PATCH", f"/hr/employees/{emp}/contract-approval-status", {"contract_approval_enabled": True})).status_code, 200)
        self.assertEqual((await self.call("hrholder", "PATCH", f"/hr/employees/{emp}/login-status", {"is_active": False})).status_code, 200)

    async def test_page_style_save_of_protected_account_ordinary_fields(self):
        """页面总带 permission_role_code=角色名：什么都不改保存不能被当成换角色。"""
        data = {"permission_role_code": "某部部长", "staff_role": "某部部长", "permission_role": "某部部长", "note": "z"}
        response = await self.call("hrholder", "PATCH", f"/hr/employees/{self.emp['boss']}", self.body("boss", "部长账号", "某部部长", data=data))
        self.assertEqual(response.status_code, 200, response.text)
        response = await self.call("hrholder", "PATCH", f"/system/users/{self.uid['boss']}", {"profile": data, "role": "user", "username": "boss"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.state("boss"))[3]["permission_role"], "某部部长")

    async def test_dingtalk_ids_and_reserved_names(self):
        async with self.sessions() as db:
            admin = await db.scalar(select(User).where(User.username == "realadmin"))
            admin.profile = {**(admin.profile or {}), "dingtalk_user_id": "ADMINDING", "dingtalk_login_ids": ["ADMINDING2"]}
            await db.commit()
        for ding in ("ADMINDING", "ADMINDING2"):
            response = await self.call("hrholder", "PATCH", f"/system/users/{self.uid['victim']}", {"profile": {"dingtalk_login_ids": [ding]}})
            self.assertEqual(response.status_code, 409, response.text)
            response = await self.call("hrholder", "POST", "/hr/employees", self.new_employee("n8" + ding.lower(), data={"joined_at": "2024-01-01", "dingtalk_user_id": ding}))
            self.assertEqual(response.status_code, 403, response.text)
            response = await self.call("hrholder", "POST", "/system/users", self.new_system_user("n9" + ding.lower(), profile={"dingtalk_login_ids": [ding]}))
            self.assertEqual(response.status_code, 403, response.text)
        for name in ("feedback-bot", "system", "hz-sync"):
            self.assertEqual((await self.call("hrholder", "POST", "/system/users", self.new_system_user(name))).status_code, 403, name)
            self.assertEqual((await self.call("hrholder", "PATCH", f"/system/users/{self.uid['victim']}", {"username": name})).status_code, 403, name)

    async def test_real_admin_keeps_every_power(self):
        for name, method, path, body in self.forbidden_new():
            response = await self.call("realadmin", method, path, body)
            self.assertLess(response.status_code, 400, f"{name}: {response.text}")
        for name, _target, method, path, body in self.forbidden():
            if "自己" in name or "真实管理员" in name:  # 改自己的密码后要先改密码才能继续
                continue
            response = await self.call("realadmin", method, path, body)
            self.assertLess(response.status_code, 500, f"{name}: {response.text}")
            self.assertNotEqual(response.status_code, 403, f"{name}: {response.text}")

    async def test_own_password_and_login_unaffected(self):
        for username in ("hrholder", "plain", "external", "boss"):
            login = await self.client.post(f"{API}/auth/login", data={"username": username, "password": PASSWORD})
            self.assertEqual(login.status_code, 200, login.text)
            response = await self.client.patch(f"{API}/auth/me", json={"current_password": PASSWORD, "new_password": "NewRev#123456789"},
                                               headers={"Authorization": "Bearer " + login.json()["access_token"]})
            self.assertEqual(response.status_code, 200, response.text)
            async with self.sessions() as db:
                self.assertTrue(verify_password("NewRev#123456789", (await db.scalar(select(User).where(User.username == username))).password_hash))


if __name__ == "__main__":
    unittest.main()
