"""陶威 11-07 权限收口一版：页面授权不提升成管理员的几处。

1. 安全策略、菜单、维护模式和系统名称、清缓存只给真实管理员；系统配置列表不带云端智能体配置；
   智能体工具不读加密 Key、不填 plan_key，不碰变更留痕。
2. 不挂记录的附件按上传人或真实管理员判断；收文助手待处理里的送达文书，收文台的人能看。
3. 审批人不能自己设成自己；保留登录名加 ops、legacy-import；客户账号不能接管员工或高权限账号。

全部走真实 JWT（页面能力会把人临时提升成 admin，替换 current_identity 测不出来）。
"""
import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.aws.receipt_bot import MODULE as RECEIPT_MODULE, PENDING, DONE
from app.config import settings
from app.core.data_scope_gate import reset_gate_cache
from app.data_models.documents import FileAttachment
from app.data_models.identity import JobRole
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, Department, SecurityPolicy, SystemConfig, User
from app.security import create_token, hash_password

API = settings.api_prefix
PASSWORD = "FakeRev#12345678"
HR_PAGES = ["hr", "hr-all", "hr-new", "hr-roles", "hr-departments"]


def person(username, role="user", permission_role="", **profile):
    return User(username=username, display_name=username, password_hash=hash_password(PASSWORD), department="D", role=role, role_ids=[role],
                is_active=True, profile={"permission_role": permission_role, "staff_role": permission_role, **profile})


def employee(username, position):
    return BusinessRecord(module="hr", serial_no=f"E-{username}", title=username, customer="公司", status="在职", owner=username, department="D",
                          data={"username": username, "position": position, "staff_role": position, "permission_role": position, "account_type": "员工账号"})


def attachment(name, uploader):
    return FileAttachment(record_id=None, category="普通附件", original_name=f"{name}.pdf", stored_name=f"{name}-stored.pdf",
                          content_type="application/pdf", size=1, path=f"/nonexistent/{name}.pdf", uploader=uploader, remark="")


class AdminOnlySettingsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        reset_gate_cache()
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                JobRole(code="R-SYS", name="系统页甲", permissions=["system"], field_keys=[], is_active=True),
                JobRole(code="R-HR", name="人事甲", permissions=HR_PAGES, field_keys=[], is_active=True),
                JobRole(code="R-CASE", name="案件甲", permissions=["case-company"], field_keys=[], is_active=True),
                JobRole(code="R-DESK", name="收文甲", permissions=["documents", "documents-official"], field_keys=[], is_active=True),
                JobRole(code="R-CON", name="合同甲", permissions=["contract", "contract-company"], field_keys=[], is_active=True),
                JobRole(code="R-PLAIN", name="普通甲", permissions=["dashboard"], field_keys=[], is_active=True),
                JobRole(code="R-HEAD", name="某部部长", permissions=["dashboard"], field_keys=[], is_active=True),
                JobRole(code="LEGACY-EXT-SOURCE", name="外部案源人", permissions=["documents", "documents-official"], field_keys=[], is_active=True),
                Department(code="D", name="D", is_active=True, sort_order=1, created_by="t", updated_by="t"),
                person("realadmin", "admin"), person("syspage", permission_role="系统页甲"), person("hrholder", permission_role="人事甲"),
                person("caseworker", permission_role="案件甲"), person("desk", permission_role="收文甲"), person("conholder", permission_role="合同甲"),
                person("plain", permission_role="普通甲"), person("external", permission_role="外部案源人"),
                person("oldcustomer", account_type="客户账号", staff_role="客户联系人"), person("boss", permission_role="某部部长"),
                employee("hrholder", "人事甲"), employee("conholder", "合同甲"), employee("plain", "普通甲"), employee("realadmin", "普通甲"),
                SecurityPolicy(min_password_length=8, max_failed_attempts=5, lock_minutes=15, token_minutes=480),
                SystemConfig(key="application_settings", label="系统配置", group="运行配置", description="",
                             value={"system_name": "平台", "default_department": "D", "page_size": 20, "attachment_limit_mb": 20, "maintenance_mode": False}),
                SystemConfig(key="customer_share_policy", label="客户共享", group="业务配置", description="",
                             value={"all_days": 100, "filed_days": 360, "premium_days": 30, "standard_days": 40, "basic_days": 60, "shared_days": 1000}),
                SystemConfig(key="agent_cloud_runtime", label="云端智能体", group="智能体", description="",
                             value={"enabled": False, "encrypted_key": "sealed-fake", "encrypted_plan_key": "sealed-fake-plan"}),
                SystemConfig(key="external_credential_qcc", label="企查查", group="外部凭据", description="",
                             value={"encrypted": "sealed-fake-qcc"}),
                attachment("mine", "plain"), attachment("receipt", "lawyer"), attachment("done", "lawyer"),
            ])
            await db.commit()
            self.att = {row.original_name.split(".")[0]: row.id for row in (await db.scalars(select(FileAttachment))).all()}
            db.add_all([
                BusinessRecord(module=RECEIPT_MODULE, serial_no="R1", title="收文", status=PENDING, owner="lawyer", department="D",
                               data={"documents": [{"attachment_id": self.att["receipt"], "name": "传票"}]}),
                BusinessRecord(module=RECEIPT_MODULE, serial_no="R2", title="收文", status=DONE, owner="lawyer", department="D",
                               data={"documents": [{"attachment_id": self.att["done"], "name": "判决书"}]}),
            ])
            await db.commit()
            self.dept = await db.scalar(select(Department.id))

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

    async def call(self, username, method, path, body=None):
        token = create_token(username, "admin" if username == "realadmin" else "user", 30)
        return await self.client.request(method, API + path, json=body, headers={"Authorization": "Bearer " + token})

    # ---- 1. 系统设置 ----
    async def test_system_settings_need_real_admin(self):
        policy = (await self.call("realadmin", "GET", "/system/security-policy")).json()
        policy_body = {key: policy[key] for key in ("min_password_length", "max_failed_attempts", "lock_minutes", "token_minutes") if key in policy}
        app_settings = {"system_name": "新名字", "default_department": "D", "page_size": 20, "attachment_limit_mb": 20, "maintenance_mode": True}
        cases = [
            ("PATCH", "/system/security-policy", policy_body),
            ("POST", "/system/menus", {"key": "x-menu", "label": "X", "parent_key": "", "sort_order": 1}),
            ("PUT", "/system/menus/visibility", {"items": []}),
            ("PATCH", "/system/menus/999999", {"label": "X"}),
            ("DELETE", "/system/menus/999999", None),
            ("POST", "/system/menus/reset", None),
            ("POST", "/system/cache/clear-all", None),
            ("POST", "/system/caches/clear", {"cache_keys": []}),
            ("POST", "/system/cache/any/clear", None),
            ("PATCH", "/system/configs/application_settings", {"value": app_settings}),
        ]
        for method, path, body in cases:
            response = await self.call("syspage", method, path, body)
            self.assertEqual(response.status_code, 403, (method, path, response.text))
            if "/cache/" not in path:  # 单个和全部清缓存这个账号连菜单都没有，先被菜单挡住
                self.assertIn("系统管理员", response.text, path)
        self.assertEqual((await self.call("realadmin", "PATCH", "/system/security-policy", policy_body)).status_code, 200)
        self.assertEqual((await self.call("realadmin", "POST", "/system/cache/clear-all")).status_code, 200)
        self.assertEqual((await self.call("realadmin", "PATCH", "/system/configs/application_settings", {"value": app_settings})).status_code, 200)

    async def test_other_configs_unchanged_for_page_admin(self):
        value = {"all_days": 100, "filed_days": 360, "premium_days": 30, "standard_days": 40, "basic_days": 60, "shared_days": 999}
        self.assertEqual((await self.call("syspage", "PATCH", "/system/configs/customer_share_policy", {"value": value})).status_code, 200,
                         "其他系统配置这次不收")
        self.assertEqual((await self.call("syspage", "GET", "/system/security-policy")).status_code, 200, "查看安全策略不变")

    async def test_config_list_hides_cloud_agent(self):
        for username in ("syspage", "realadmin"):
            response = await self.call(username, "GET", "/system/configs")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn("agent_cloud_runtime", response.text)
            self.assertNotIn("external_credential_qcc", response.text)
            self.assertNotIn("sealed-fake", response.text)

    # ---- 1. 智能体工具 ----
    def test_agent_tool_filters(self):
        from app.agent_mcp.safety import reject_credentials, safe_result
        cleaned = safe_result({"encrypted_key": "x", "encrypted_plan_key": "y", "encrypted_secret": "z", "encrypted": "q", "encryptedKey": "k",
                               "plan_key_set": True, "model": "m"})
        self.assertEqual(cleaned, {"plan_key_set": True, "model": "m"})
        with self.assertRaises(Exception):
            reject_credentials({"plan_key": "fake-plan"})
        from app.agent_mcp.semantic_metadata import exclusion_reasons
        routes = [route for route in app.routes if "/system/change-logs" in getattr(route, "path", "")]
        self.assertGreaterEqual(len(routes), 4)
        for route in routes:
            self.assertTrue(exclusion_reasons(route), route.path)

    def test_agent_tool_schemas_drop_keys(self):
        from app.agent_mcp.catalog import get_catalog
        catalog = get_catalog(app)
        self.assertFalse([tool for tool in catalog.tools if "/system/change-logs" in tool.path])
        checked = 0
        for tool in catalog.tools:
            if tool.path.endswith("/agent-admin/cloud-runtime") or tool.path.endswith("/agent-admin/model-providers") or "/agent-admin/model-providers/{" in tool.path:
                text = str(tool.input_schema)
                self.assertNotIn("plan_key", text, tool.name)
                self.assertNotIn("api_key", text, tool.name)
                checked += 1
        self.assertGreater(checked, 0)

    # ---- 2. 不挂记录的附件 ----
    async def test_unlinked_attachment_by_uploader_or_real_admin(self):
        mine = f"/attachments/{self.att['mine']}"
        self.assertEqual((await self.call("plain", "GET", mine)).status_code, 200, "上传人自己")
        self.assertEqual((await self.call("realadmin", "GET", mine)).status_code, 200, "真实管理员")
        for username in ("caseworker", "syspage", "desk"):
            for suffix in ("", "/download", "/preview", "/pdf-preview"):
                response = await self.call(username, "GET", mine + suffix)
                self.assertEqual(response.status_code, 404, (username, suffix, response.text))
                self.assertIn("无权访问", response.text, (username, suffix))

    async def test_unlinked_attachment_list_and_delete(self):
        async def names(username):
            response = await self.call(username, "GET", "/attachments?page_size=200")
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            return {item["original_name"] for item in (body["items"] if isinstance(body, dict) else body)}
        self.assertIn("mine.pdf", await names("plain"), "上传人自己能在列表里看到")
        self.assertIn("mine.pdf", await names("realadmin"))
        for username in ("caseworker", "syspage"):
            self.assertNotIn("mine.pdf", await names(username), username)
        self.assertEqual((await self.call("syspage", "DELETE", f"/attachments/{self.att['mine']}")).status_code, 404, "页面管理员不能删别人不挂记录的附件")
        async with self.sessions() as db:
            self.assertIsNotNone(await db.get(FileAttachment, self.att["mine"]))

    async def test_pending_receipt_document_for_desk(self):
        receipt, done = f"/attachments/{self.att['receipt']}", f"/attachments/{self.att['done']}"
        self.assertEqual((await self.call("desk", "GET", receipt)).status_code, 200, "待处理里的送达文书，收文台能看")
        self.assertEqual((await self.call("desk", "GET", done)).status_code, 404, "已处理的不再按收文台放行")
        self.assertEqual((await self.call("external", "GET", receipt)).status_code, 404, "外部账号不行")
        self.assertEqual((await self.call("caseworker", "GET", receipt)).status_code, 404, "没有收文台菜单不行")

    # ---- 3. 审批人、保留名、客户账号 ----
    async def test_cannot_make_self_approver(self):
        dept = f"/hr/departments/{self.dept}"
        self.assertEqual((await self.call("hrholder", "PATCH", dept, {"manager": "hrholder"})).status_code, 403)
        self.assertEqual((await self.call("hrholder", "PATCH", dept, {"seal_reviewer": "hrholder"})).status_code, 403)
        self.assertEqual((await self.call("hrholder", "PATCH", dept, {"manager": "plain"})).status_code, 200, "设别人照常")
        seal = {"firm_approver": "hrholder", "stamp_users": [], "department_paths": {}}
        self.assertEqual((await self.call("hrholder", "PUT", "/hr/seal-approval-settings", seal)).status_code, 403)
        self.assertEqual((await self.call("hrholder", "PUT", "/hr/seal-approval-settings", {**seal, "firm_approver": "plain"})).status_code, 200)
        self.assertEqual((await self.call("conholder", "PUT", "/contracts/approver-settings", {"usernames": ["conholder"]})).status_code, 403)
        self.assertEqual((await self.call("conholder", "PUT", "/contracts/approver-settings", {"usernames": ["plain"]})).status_code, 200)
        self.assertEqual((await self.call("realadmin", "PATCH", dept, {"manager": "realadmin"})).status_code, 200, "真实管理员不限")
        new_dept = {"code": "N1", "name": "新部门", "manager": "hrholder", "seal_reviewer": "", "sort_order": 2}
        self.assertEqual((await self.call("hrholder", "POST", "/hr/departments", new_dept)).status_code, 403, "新建部门也不能设自己")
        self.assertEqual((await self.call("hrholder", "POST", "/hr/departments", {**new_dept, "manager": "plain", "seal_reviewer": "hrholder"})).status_code, 403)
        self.assertEqual((await self.call("hrholder", "POST", "/hr/departments", {**new_dept, "manager": "plain"})).status_code, 201)

    async def test_seal_roles_compared_separately(self):
        base = {"firm_approver": "plain", "stamp_users": ["hrholder"], "department_paths": {}}
        self.assertEqual((await self.call("realadmin", "PUT", "/hr/seal-approval-settings", base)).status_code, 200)
        self.assertEqual((await self.call("hrholder", "PUT", "/hr/seal-approval-settings", base)).status_code, 200, "原来就是盖章人，原样保存不挡")
        moved = {"firm_approver": "hrholder", "stamp_users": [], "department_paths": {}}
        self.assertEqual((await self.call("hrholder", "PUT", "/hr/seal-approval-settings", moved)).status_code, 403, "盖章人不能改成自己做全所审批人")
        path = {**base, "department_paths": {str(self.dept): ["hrholder", ""]}}
        self.assertEqual((await self.call("hrholder", "PUT", "/hr/seal-approval-settings", path)).status_code, 403, "不能把自己放进部门路径")

    async def test_reserved_names(self):
        for name in ("ops", "legacy-import"):
            body = {"username": name, "display_name": name, "department": "D", "role": "user", "password": PASSWORD}
            response = await self.call("hrholder", "POST", "/system/users", body)
            self.assertIn(response.status_code, {403, 409, 422}, (name, response.text))
            async with self.sessions() as db:
                self.assertIsNone(await db.scalar(select(User.id).where(User.username == name)))

    async def test_customer_account_cannot_take_over_staff(self):
        def body(username):
            return {"username": username, "display_name": "客户" + username, "employee_no": "N-" + username, "company": "公司", "department": "D",
                    "password": PASSWORD, "role": "user", "position": "普通甲", "is_active": True, "account_type": "客户账号", "data": {"joined_at": "2024-01-01"}}
        for username in ("boss",):
            response = await self.call("realadmin", "POST", "/hr/employees", body(username))
            self.assertEqual(response.status_code, 409, response.text)
            async with self.sessions() as db:
                user = await db.scalar(select(User).where(User.username == username))
                self.assertEqual(user.profile.get("permission_role"), "某部部长", "原账号没被改")
        self.assertEqual((await self.call("realadmin", "POST", "/hr/employees", body("oldcustomer"))).status_code, 201, "旧客户登录名照常接管")


if __name__ == "__main__":
    unittest.main()
