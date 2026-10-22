"""MCP 个人访问令牌：只存摘要、可撤销可过期、账号停用即失效、只读过滤、审计和限流。"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.agent_mcp import personal_tokens
from app.agent_mcp.auth import AuthContext
from app.data_models.mcp_tokens import McpAccessToken, McpCallLog
from app.database import Base
from app.models import User

ADMIN = {"username": "boss"}


class _Base(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username="boss", display_name="管理者", role="admin", role_ids=["admin"], password_hash="x"))
            await db.commit()
        patcher = patch.object(personal_tokens, "SessionLocal", self.sessions)
        patcher.start()
        self.addCleanup(patcher.stop)
        personal_tokens._calls.clear()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _create(self, name="笔记本", days=30):
        async with self.sessions() as db:
            return await personal_tokens.create_token(ADMIN, db, name, days)


class PersonalTokenTest(_Base):

    async def test_plain_token_is_returned_once_and_only_hash_is_stored(self):
        created = await self._create()
        self.assertTrue(personal_tokens.is_personal_token(created["token"]))
        async with self.sessions() as db:
            row = await db.scalar(select(McpAccessToken))
            listed = await personal_tokens.list_tokens(ADMIN, db)
        self.assertEqual(row.token_hash, personal_tokens.token_hash(created["token"]))
        self.assertNotIn(created["token"], repr(row.__dict__))
        self.assertNotIn("token", listed[0])
        self.assertEqual(listed[0]["status"], "active")

    async def test_validity_and_active_count_limits(self):
        for days in (0, personal_tokens.MAX_DAYS + 1):
            with self.assertRaises(HTTPException):
                await self._create(days=days)
        for _ in range(personal_tokens.MAX_ACTIVE_PER_USER):
            await self._create()
        with self.assertRaises(HTTPException) as caught:
            await self._create()
        self.assertEqual(caught.exception.status_code, 409)

    async def test_authenticate_accepts_active_and_rejects_revoked_expired_unknown_or_disabled(self):
        created = await self._create()
        token_id, username, session = await personal_tokens.authenticate(created["token"])
        self.assertEqual((token_id, username), (created["id"], "boss"))
        self.assertTrue(session)
        with self.assertRaises(HTTPException):
            await personal_tokens.authenticate("oamcp_" + "x" * 40)
        async with self.sessions() as db:
            await personal_tokens.revoke_token(ADMIN, db, created["id"])
        with self.assertRaises(HTTPException) as caught:
            await personal_tokens.authenticate(created["token"])
        self.assertEqual(caught.exception.status_code, 401)

        expired = await self._create(name="过期")
        async with self.sessions() as db:
            row = await db.get(McpAccessToken, expired["id"])
            row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            await db.commit()
        with self.assertRaises(HTTPException):
            await personal_tokens.authenticate(expired["token"])

        disabled = await self._create(name="停用")
        async with self.sessions() as db:
            user = await db.scalar(select(User))
            user.is_active = False
            await db.commit()
        with self.assertRaises(HTTPException):
            await personal_tokens.authenticate(disabled["token"])

    async def test_rate_limit(self):
        created = await self._create()
        with patch.object(personal_tokens, "RATE_LIMIT_PER_MINUTE", 3):
            for _ in range(3):
                await personal_tokens.authenticate(created["token"])
            with self.assertRaises(HTTPException) as caught:
                await personal_tokens.authenticate(created["token"])
        self.assertEqual(caught.exception.status_code, 429)

    async def test_record_call_writes_audit_and_counts(self):
        created = await self._create()
        await personal_tokens.record_call(created["id"], "boss", "list_cases", True, {"page": 1})
        async with self.sessions() as db:
            log = await db.scalar(select(McpCallLog))
            listed = await personal_tokens.list_tokens(ADMIN, db)
        self.assertEqual((log.tool_name, log.ok, log.token_id), ("list_cases", 1, created["id"]))
        self.assertEqual(listed[0]["call_count"], 1)
        self.assertIsNotNone(listed[0]["last_used_at"])


class WriteTokenTest(_Base):
    async def test_write_rate_limit_is_lower_than_read_limit(self):
        with patch.object(personal_tokens, "WRITE_RATE_LIMIT_PER_MINUTE", 2):
            personal_tokens.check_write_rate(9)
            personal_tokens.check_write_rate(9)
            with self.assertRaises(HTTPException) as caught:
                personal_tokens.check_write_rate(9)
        self.assertEqual(caught.exception.status_code, 429)

    async def test_write_audit_keeps_full_request(self):
        created = await self._create()
        await personal_tokens.record_call(created["id"], "boss", "delete_case", True, detail='{"method":"DELETE","path":"/cases/1"}', is_write=True)
        async with self.sessions() as db:
            log = (await personal_tokens.list_calls(ADMIN, db))[0]
        self.assertTrue(log["is_write"])
        self.assertIn("DELETE", log["detail"])


class PermissionTest(unittest.TestCase):
    def test_admin_or_granted_action_may_use_personal_token(self):
        from app.agent_permissions import MCP_PERSONAL_TOKEN_ACTION, USER_ACTION_KEYS, can_use_mcp_personal_token
        self.assertIn(MCP_PERSONAL_TOKEN_ACTION, USER_ACTION_KEYS)
        staff = {"username": "tgn", "role": "user", "_user_action_keys": []}
        with patch("app.agent_permissions.is_actual_system_admin", lambda identity: identity["role"] == "admin"):
            self.assertFalse(can_use_mcp_personal_token(staff))
            self.assertTrue(can_use_mcp_personal_token({**staff, "_user_action_keys": [MCP_PERSONAL_TOKEN_ACTION]}))
            self.assertFalse(can_use_mcp_personal_token({**staff, "_user_action_keys": ["agent.settings.global.manage"]}))
            self.assertTrue(can_use_mcp_personal_token({"username": "boss", "role": "admin"}))
        from app.agent_permissions import MCP_PERSONAL_TOKEN_WRITE_ACTION, can_write_with_mcp_token
        self.assertFalse(can_write_with_mcp_token({**staff, "_user_action_keys": [MCP_PERSONAL_TOKEN_ACTION]}))
        self.assertTrue(can_write_with_mcp_token({**staff, "_user_action_keys": [MCP_PERSONAL_TOKEN_WRITE_ACTION]}))


class BusinessOnlyTest(unittest.TestCase):
    def _spec(self, method, path):
        return SimpleNamespace(method=method, path="/api/v1" + path)

    def test_system_admin_interfaces_are_not_exposed_but_business_and_lookups_are(self):
        allowed = personal_tokens.token_tool_allowed
        for method, path in (("GET", "/cases"), ("POST", "/customers"), ("DELETE", "/contracts/{contract_id}"), ("GET", "/records"),
                             ("GET", "/agent/documents"), ("GET", "/templates"), ("GET", "/hr/departments"),
                             ("GET", "/system/parameters/options"), ("GET", "/system/parameters/cause/autocomplete")):
            self.assertTrue(allowed(self._spec(method, path)), (method, path))
        for method, path in (("GET", "/system/parameters"), ("POST", "/system/parameters"), ("DELETE", "/system/parameters/{parameter_id}"),
                             ("PATCH", "/system/configs/{config_key}"), ("POST", "/system/menus"), ("PATCH", "/system/role-permissions/{role}"),
                             ("PATCH", "/system/users/{user_id}/permissions"), ("POST", "/system/recycle-bin/restore"),
                             ("POST", "/agent/global-skills"), ("GET", "/agent/skills"), ("POST", "/agent-admin/dsh-plugins/install"),
                             ("GET", "/capability-market/resources/{item_id}"), ("GET", "/hr/job-roles/{role_id}/permissions"),
                             ("PATCH", "/hr/job-roles/{role_id}/permissions")):
            self.assertFalse(allowed(self._spec(method, path)), (method, path))


class BusinessScopeTest(unittest.IsolatedAsyncioTestCase):
    def _context(self, groups, write=True):
        return AuthContext(application=object(), bearer="jwt", scope={}, token_id=7, write_allowed=write, groups=groups)

    def test_connection_address_resolves_businesses_and_groups(self):
        from app.agent_mcp.tool_groups import BUSINESS_BUNDLES, resolve_business_scope
        self.assertIsNone(resolve_business_scope(None, None))
        self.assertEqual(resolve_business_scope("finance", None), frozenset(BUSINESS_BUNDLES["finance"][1]))
        self.assertEqual(resolve_business_scope("customer", "15"), frozenset((*BUSINESS_BUNDLES["customer"][1], "15")))
        for bad in (("nope", None), (None, "99")):
            with self.assertRaises(HTTPException) as caught:
                resolve_business_scope(*bad)
            self.assertEqual(caught.exception.status_code, 400)

    async def test_selected_business_lists_only_its_tools_directly_and_refuses_others(self):
        from app.agent_mcp import gateway, service
        case_tool = SimpleNamespace(name="list_cases", title="查询案件", is_write=False, method="GET", path="/api/v1/cases", group_id="06",
                                    to_mcp=lambda: {"name": "list_cases", "description": "查案", "inputSchema": {"type": "object"}, "annotations": {"readOnlyHint": True}})
        pay_tool = SimpleNamespace(name="list_payments", title="付款", is_write=False, method="GET", path="/api/v1/finance/payments", group_id="19",
                                   to_mcp=lambda: {"name": "list_payments", "description": "付款", "inputSchema": {"type": "object"}})
        catalog = SimpleNamespace(tools=[case_tool, pay_tool], get=lambda name: {"list_cases": case_tool, "list_payments": pay_tool}[name])
        scope = frozenset({"06", "07"})
        with patch.object(gateway, "get_auth_context", lambda: self._context(scope)), patch.object(gateway, "get_catalog", lambda _app: catalog):
            listed = await gateway._list_tools(None, None)
        # 所选业务的接口直接列出（带完整定义），外加两个范围内的发现工具；其他业务的接口不出现
        self.assertEqual({tool.name for tool in listed.tools}, {"list_cases", "oa_get_usage_guide", "oa_list_tool_groups", "oa_search_tools", "oa_describe_tool"})
        light = next(tool for tool in listed.tools if tool.name == "list_cases")
        self.assertIn("GET /cases", light.description)  # 精简形式：标题 + 方法路径，参数定义按需取
        self.assertIn("oa_describe_tool", light.description)
        self.assertNotIn("PARAMETER", str(light.input_schema))
        with patch.object(service, "get_auth_context", lambda: self._context(scope)), patch.object(service, "get_catalog", lambda _app: catalog), \
             patch.object(service, "authenticated_identity", lambda: _async({"username": "boss"})):
            with self.assertRaises(HTTPException) as caught:
                await service.call_tool("list_payments", {})
            self.assertEqual(caught.exception.status_code, 403)
            self.assertEqual([spec.name for spec in service.token_visible_tools(self._context(scope), catalog)], ["list_cases"])
        with patch.object(gateway, "get_auth_context", lambda: self._context(None)), patch.object(gateway, "get_catalog", lambda _app: catalog):
            listed = await gateway._list_tools(None, None)
        self.assertIn("oa_list_tool_groups", {tool.name for tool in listed.tools})  # 没选业务：只给入口工具
        self.assertNotIn("list_cases", {tool.name for tool in listed.tools})


class UsageSkillTest(unittest.IsolatedAsyncioTestCase):
    def _catalog(self):
        reader = SimpleNamespace(name="list_cases", is_write=False, method="GET", path="/api/v1/cases", group_id="06", title="查询案件")
        writer = SimpleNamespace(name="create_case", is_write=True, method="POST", path="/api/v1/cases", group_id="07", title="新建案件")
        return SimpleNamespace(tools=[reader, writer], get=lambda name: {"list_cases": reader, "create_case": writer}[name])

    def test_skill_states_current_scope_permission_and_rules(self):
        from app.agent_mcp import service, usage_skill
        catalog = self._catalog()
        ctx = AuthContext(application=object(), bearer="jwt", scope={}, token_id=7, write_allowed=False, groups=frozenset({"06", "07"}))
        with patch.object(service, "get_auth_context", lambda: ctx):
            read_only = usage_skill.build_skill(ctx, catalog)
        self.assertTrue(read_only.startswith("---\nname: oa-mcp-usage"))
        self.assertIn("只读", read_only)
        self.assertIn("当前可用接口：1 个", read_only)  # 只读令牌看不到写入类
        for rule in ("oa_describe_tool", "先问用户", "直接执行", "待确认", "逻辑删除", "429", "等用户明确说"):
            self.assertIn(rule, read_only)
        writable = AuthContext(application=object(), bearer="jwt", scope={}, token_id=7, write_allowed=True, groups=None)
        text = usage_skill.build_skill(writable, catalog)
        self.assertIn("可新增、修改、删除", text)
        self.assertIn("未选业务", text)
        self.assertIn("当前可用接口：2 个", text)

    async def test_guide_is_served_as_tool_resource_and_prompt(self):
        from app.agent_mcp import gateway, usage_skill
        catalog = self._catalog()
        ctx = AuthContext(application=object(), bearer="jwt", scope={}, token_id=7, write_allowed=True, groups=None)
        with patch.object(gateway, "get_auth_context", lambda: ctx), patch.object(gateway, "get_catalog", lambda _app: catalog):
            tool = await gateway._dispatch_tool(SimpleNamespace(name=usage_skill.GUIDE_TOOL, arguments={}))
            resource = await gateway._read_resource(None, SimpleNamespace(uri=usage_skill.SKILL_URI))
            prompt = await gateway._get_prompt(None, SimpleNamespace(name=usage_skill.PROMPT_NAME))
        self.assertFalse(tool.is_error)
        self.assertIn("oa-mcp-usage", tool.content[0].text)
        self.assertIn("oa-mcp-usage", resource.contents[0].text)
        self.assertIn("oa-mcp-usage", prompt.messages[0].content.text)
        self.assertIn("oa_get_usage_guide", usage_skill.INSTRUCTIONS)  # 握手说明指向使用指南


class LocalConfirmTest(unittest.TestCase):
    def test_local_agent_is_told_to_confirm_with_user_before_ordinary_writes(self):
        from app.agent_mcp.personal_tokens import LOCAL_CONFIRM_TEXT, direct_write_view
        from app.agent_mcp.semantic_metadata import DIRECT_WRITE_TEXT
        view = direct_write_view({"name": "update_case", "title": "修改案件", "description": "案件：修改。" + DIRECT_WRITE_TEXT}, "PATCH")
        self.assertIn(LOCAL_CONFIRM_TEXT, view["description"])  # 给本地智能体看的：先向用户确认
        self.assertNotIn(DIRECT_WRITE_TEXT, view["description"])  # 站内智能体那句“不需要再确认”不出现在 MCP 里
        self.assertIn("明确同意", LOCAL_CONFIRM_TEXT)


class IrreversibleTest(unittest.IsolatedAsyncioTestCase):
    def _spec(self, method, path):
        return SimpleNamespace(name="x", is_write=True, method=method, path="/api/v1" + path, validate_arguments=lambda a: {"path": {}, "query": {}, "body": None, "files": {}})

    def test_categories(self):
        from app.agent_mcp.irreversible import irreversible_category
        cases = {
            ("POST", "/contracts/{contract_id}/approve"): "审批", ("POST", "/finance/fees/{fee_id}/review"): "审批",
            ("POST", "/conflict-reviews/{review_id}/decision"): "审批", ("POST", "/finance/fees/batch-review"): "审批",
            ("POST", "/seals/applications/{record_id}/stamp"): "盖章与对外转交", ("POST", "/official-outgoing/mark-stamped"): "盖章与对外转交",
            ("POST", "/ipr/official-files/{official_id}/transmit"): "盖章与对外转交",
            ("POST", "/contract-payment-applications/{payment_id}/pay"): "付款与核销", ("POST", "/finance/fees/{fee_id}/writeoff"): "付款与核销",
            ("POST", "/finance/invoices/{invoice_id}/issue"): "开票与作废", ("POST", "/finance/invoices/{invoice_id}/void"): "开票与作废",
            ("POST", "/finance/refunds/{refund_id}/complete"): "退费登记到账",
        }
        for (method, path), expected in cases.items():
            self.assertEqual(irreversible_category(self._spec(method, path)), expected, path)
        for method, path in (("POST", "/customers"), ("PATCH", "/cases/{case_id}"), ("DELETE", "/hr/departments/{department_id}"),
                             ("POST", "/contracts/{contract_id}/submit"), ("POST", "/cases/{case_id}/assign"), ("POST", "/finance/invoices"),
                             ("POST", "/notifications/send"), ("POST", "/tasks/{task_id}/resend")):
            self.assertIsNone(irreversible_category(self._spec(method, path)), path)
        self.assertIsNone(irreversible_category(SimpleNamespace(is_write=False, path="/api/v1/notifications/send")))

    async def test_in_app_agent_write_executes_directly_and_is_labelled_agent(self):
        from app.agent_mcp import service
        from app.core import change_log
        spec = self._spec("PATCH", "/cases/{case_id}")
        seen = []

        async def fake_execute(spec, params, **kwargs):
            seen.append(change_log.source_var.get())
            return {"updated": True}

        class FakeSession:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): return False

        async def passthrough(spec, arguments, params, identity, db):
            return arguments

        async def nothing(*args, **kwargs):
            return None

        context = AuthContext(application=object(), bearer="jwt", scope={})  # 站内智能体：不是个人令牌
        catalog = SimpleNamespace(get=lambda name: spec)
        with patch.object(service, "get_auth_context", lambda: context), patch.object(service, "get_catalog", lambda _app: catalog), \
             patch.object(service, "authenticated_identity", lambda: _async({"username": "boss", "department": "d"})), \
             patch.object(service, "SessionLocal", FakeSession), patch.object(service, "require_business_record_target", nothing), \
             patch.object(service, "prepare_business_arguments", passthrough), patch.object(service, "execute_original", fake_execute), \
             patch.object(service, "trusted_case_origin", lambda: None), patch.object(service, "_record_agent_call", nothing) as _:
            result = await service.call_tool("x", {})
        self.assertEqual(result, {"updated": True})  # 不再生成待确认，直接执行
        self.assertEqual(seen, ["agent"])  # 变更留痕记为“智能体”来源
        self.assertEqual(change_log.source_var.get(), "system")  # 调用结束后来源复原


class ReadOnlyGatewayTest(unittest.IsolatedAsyncioTestCase):
    def _context(self, token_id, write=False):
        return AuthContext(application=object(), bearer="jwt", scope={}, token_id=token_id, write_allowed=write)

    async def test_write_tools_are_hidden_and_refused_for_personal_token(self):
        from app.agent_mcp import gateway, service
        reader = SimpleNamespace(name="list_cases", is_write=False, method="GET", path="/api/v1/cases", to_mcp=lambda: {
            "name": "list_cases", "description": "查案", "inputSchema": {"type": "object"}})
        writer = SimpleNamespace(name="create_case", is_write=True, method="POST", path="/api/v1/cases", to_mcp=lambda: {
            "name": "create_case", "description": "建案", "inputSchema": {"type": "object"}})
        catalog = SimpleNamespace(tools=[reader, writer], get=lambda name: {"list_cases": reader, "create_case": writer}[name])
        entry = {"oa_get_usage_guide", "oa_list_tool_groups", "oa_list_group_tools", "oa_search_tools", "oa_describe_tool", "oa_call_read_tool"}
        for token_id, expected in ((7, entry),  # 个人令牌：只给入口工具，按需加载，不一次列出全部接口
                                   (None, {"oa_get_usage_guide", "oa_list_tool_groups", "oa_search_tools", "list_cases", "create_case"})):
            with patch.object(gateway, "get_auth_context", lambda token_id=token_id: self._context(token_id)), \
                 patch.object(gateway, "get_catalog", lambda _app: catalog):
                listed = await gateway._list_tools(None, None)
            self.assertEqual({tool.name for tool in listed.tools}, expected)
        with patch.object(service, "get_auth_context", lambda: self._context(7)), \
             patch.object(service, "get_catalog", lambda _app: catalog), \
             patch.object(service, "authenticated_identity", lambda: _async({"username": "boss"})):
            with self.assertRaises(HTTPException) as caught:
                await service.call_tool("create_case", {})
        self.assertEqual(caught.exception.status_code, 403)

    async def test_write_token_lists_writes_and_executes_directly_without_pending_record(self):
        from app.agent_mcp import gateway, service
        remover = SimpleNamespace(name="delete_case", is_write=True, method="DELETE", path="/api/v1/cases/{case_id}",
                                  title="删除案件", validate_arguments=lambda arguments: {"path": {"case_id": 1}, "query": {}, "body": None, "files": {}},
                                  to_mcp=lambda: {"name": "delete_case", "title": "删除案件", "description": "删。须持久化人工确认后调用，继续执行原权限、数据范围、校验和业务审批。",
                                                  "inputSchema": {"type": "object"}})
        catalog = SimpleNamespace(tools=[remover], get=lambda name: remover)
        with patch.object(gateway, "get_auth_context", lambda: self._context(7, write=True)), patch.object(gateway, "get_catalog", lambda _app: catalog):
            listed = await gateway._list_tools(None, None)
        self.assertEqual({tool.name for tool in listed.tools},  # 有写入权限时多一个写入入口，且业务接口仍不逐个列出
                         {"oa_get_usage_guide", "oa_list_tool_groups", "oa_list_group_tools", "oa_search_tools", "oa_describe_tool", "oa_call_read_tool", "oa_call_write_tool"})
        write_entry = next(item for item in listed.tools if item.name == "oa_call_write_tool")
        self.assertFalse(write_entry.annotations.read_only_hint)
        self.assertTrue(write_entry.annotations.destructive_hint)
        with patch.object(service, "get_auth_context", lambda: self._context(7, write=True)), patch.object(service, "get_catalog", lambda _app: catalog), \
             patch.object(service, "public_tool", lambda spec: spec.to_mcp()):
            described = service.describe_tool("delete_case")
        self.assertTrue(described["description"].startswith("【删除操作】"))
        self.assertNotIn("须持久化人工确认", described["description"])  # 旧的“人工确认”说法已去掉

        executed = []

        async def fake_execute(spec, params, **kwargs):
            executed.append((spec.name, params))
            return {"deleted": True}

        class FakeSession:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): return False

        async def passthrough(spec, arguments, params, identity, db):
            return arguments

        async def nothing(*args, **kwargs):
            return None

        with patch.object(service, "get_auth_context", lambda: self._context(7, write=True)), patch.object(service, "get_catalog", lambda _app: catalog), \
             patch.object(service, "authenticated_identity", lambda: _async({"username": "boss", "department": "d"})), \
             patch.object(service, "SessionLocal", FakeSession), patch.object(service, "require_business_record_target", nothing), \
             patch.object(service, "prepare_business_arguments", passthrough), patch.object(service, "execute_original", fake_execute), \
             patch.object(service, "trusted_case_origin", lambda: None):
            result = await service.call_tool("delete_case", {})
        self.assertEqual(result, {"deleted": True})
        self.assertEqual(executed[0][0], "delete_case")
        # 只读令牌即使点名调用也被拒绝
        with patch.object(service, "get_auth_context", lambda: self._context(7, write=False)), patch.object(service, "get_catalog", lambda _app: catalog), \
             patch.object(service, "authenticated_identity", lambda: _async({"username": "boss"})):
            with self.assertRaises(HTTPException) as caught:
                await service.call_tool("delete_case", {})
        self.assertEqual(caught.exception.status_code, 403)

    async def test_entry_call_tools_route_by_read_write_and_audit_the_real_target(self):
        from app.agent_mcp import gateway
        reader = SimpleNamespace(name="list_cases", is_write=False, method="GET", path="/api/v1/cases")
        writer = SimpleNamespace(name="create_case", is_write=True, method="POST", path="/api/v1/cases")
        catalog = SimpleNamespace(tools=[reader, writer], get=lambda name: {"list_cases": reader, "create_case": writer}[name])
        calls = []

        async def fake_call_tool(name, arguments, **kwargs):
            calls.append((name, arguments))
            return {"ok": name}

        def params(entry, name, arguments=None):
            return SimpleNamespace(name=entry, arguments={"name": name, "arguments": arguments or {}})

        with patch.object(gateway, "get_auth_context", lambda: self._context(7, write=True)), patch.object(gateway, "get_catalog", lambda _app: catalog), \
             patch.object(gateway, "call_tool", fake_call_tool):
            ok = await gateway._dispatch_tool(params("oa_call_read_tool", "list_cases", {"query": {"page": 1}}))
            self.assertFalse(ok.is_error)
            wrong_read = await gateway._dispatch_tool(params("oa_call_read_tool", "create_case"))
            wrong_write = await gateway._dispatch_tool(params("oa_call_write_tool", "list_cases"))
            ok_write = await gateway._dispatch_tool(params("oa_call_write_tool", "create_case", {"body": {"a": 1}}))
        self.assertTrue(wrong_read.is_error and wrong_write.is_error)  # 读写入口不能混用，客户端才能分别设置确认策略
        self.assertFalse(ok_write.is_error)
        self.assertEqual([name for name, _ in calls], ["list_cases", "create_case"])
        # 非个人令牌不能用入口调用工具
        with patch.object(gateway, "get_auth_context", lambda: self._context(None)), patch.object(gateway, "get_catalog", lambda _app: catalog):
            self.assertTrue((await gateway._dispatch_tool(params("oa_call_read_tool", "list_cases"))).is_error)

    async def test_personal_token_never_valid_outside_mcp_entry(self):
        from app.agent_mcp.auth import RequestAuthContextMiddleware
        seen = {}

        async def app(scope, receive, send):
            from app.agent_mcp.auth import get_auth_context
            seen["bearer"] = get_auth_context().bearer

        middleware = RequestAuthContextMiddleware(app, application=object())
        await middleware({"type": "http", "path": "/api/v1/cases", "headers": [(b"authorization", b"Bearer oamcp_" + b"y" * 40)]}, None, None)
        self.assertTrue(seen["bearer"].startswith("oamcp_"))  # 原样透传给普通接口，由 JWT 校验拒绝


async def _async(value):
    return value


if __name__ == "__main__":
    unittest.main()
