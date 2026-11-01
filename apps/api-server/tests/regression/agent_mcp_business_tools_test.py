"""按操作手册组合的业务工具：只经目录里的原接口调用、写工具两段确认、令牌范围过滤。"""

import inspect
import re
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from jsonschema import Draft202012Validator

from app.agent_mcp import business_tools
from app.agent_mcp.catalog import get_catalog
from app.agent_mcp.model_tools import MODEL_TOOLS
from app.main import app


class BusinessToolCatalogTest(unittest.TestCase):
    def test_every_internal_step_is_a_declared_catalog_tool(self):
        catalog = get_catalog(app)
        for tool in business_tools.TOOLS.values():
            for name in tool.uses:
                catalog.get(name)  # 不存在会抛 422
            called = set(re.findall(r'"(oa_[a-z0-9_]+)"', inspect.getsource(tool.handler)))
            helpers = {"oa_get_record_get", "oa_list_records_get", "oa_list_customers_get", "oa_search_ordinary_cases_post"}
            self.assertLessEqual(called - helpers, set(tool.uses), tool.name)

    def test_schemas_are_valid_and_write_tools_take_confirm(self):
        for tool in business_tools.TOOLS.values():
            Draft202012Validator.check_schema(tool.input_schema)
            self.assertEqual(tool.write, "confirm" in tool.input_schema["properties"], tool.name)
            self.assertTrue(tool.name.startswith("biz_"))

    def test_in_app_agent_receives_business_tools(self):
        names = {item["function"]["name"] for item in MODEL_TOOLS}
        self.assertLessEqual(set(business_tools.TOOLS), names)


def _context(**overrides):
    values = dict(application=app, readonly=True, groups=None, write_allowed=False, username="u")
    values.update(overrides)
    return SimpleNamespace(**values)


class BusinessToolRunTest(unittest.IsolatedAsyncioTestCase):
    async def test_plan_mode_never_calls_write_endpoints(self):
        calls = []

        async def fake_call(name, arguments):
            calls.append(name)
            if name == "oa_list_customers_get":
                return {"items": []}
            return {"found": False}

        with patch.object(business_tools, "get_auth_context", return_value=_context(readonly=False)):
            result = await business_tools.run_business_tool(
                "biz_customer_create", {"title": "CODEX-甲公司", "customer_managers": ["admin"]}, call=fake_call)
        self.assertEqual(result["mode"], "计划")
        catalog = get_catalog(app)
        self.assertTrue(calls and not any(catalog.get(name).is_write for name in calls), calls)
        self.assertTrue(any(step["status"] == "待执行" for step in result["steps"]))

    async def test_legacy_failure_envelope_stops_execution(self):
        async def fake_call(name, arguments):
            return {"IsSuccess": False, "Message": "合同当前不在审批中"}

        from app.agent_mcp.service import APPROVED_EXECUTION
        token = APPROVED_EXECUTION.set(True)  # 用户已在确认卡片上同意后的执行
        try:
            with patch.object(business_tools, "get_auth_context", return_value=_context(readonly=False)):
                result = await business_tools.run_business_tool("biz_task_create", {
                    "title": "CODEX-任务", "owner": "admin", "deadline": "2026-11-30", "confirm": True}, call=fake_call)
        finally:
            APPROVED_EXECUTION.reset(token)
        self.assertTrue(result["isError"])
        self.assertEqual(result["failed_step"]["error"], "合同当前不在审批中")

    async def test_confirm_true_creates_one_confirmation_card_instead_of_executing(self):
        # 陶威 11-01 21:55：所有写操作先确认。业务工具带 confirm=true 时只出计划并整体生成一条待确认请求，不调用任何写接口。
        calls, prepared = [], {}

        async def fake_call(name, arguments):
            calls.append(name)
            return {"items": []} if name == "oa_list_customers_get" else {"found": False}

        async def fake_prepare(tool, values, plan, *, conversation_id=None):
            prepared.update(tool=tool.name, values=values, steps=len(plan["steps"]), conversation_id=conversation_id)
            return {"request_id": "r1", "status": "pending", "summary": "新建客户", "preview": {"operation_name": tool.title}}

        from app.agent_mcp import service
        with patch.object(business_tools, "get_auth_context", return_value=_context(readonly=False)), \
                patch.object(service, "prepare_business_request", fake_prepare):
            result = await business_tools.run_business_tool(
                "biz_customer_create", {"title": "CODEX-甲公司", "customer_managers": ["admin"], "confirm": True},
                call=fake_call, conversation_id="c1")
        self.assertEqual((result["status"], result["mode"], result["request_id"]), ("pending", "待确认", "r1"))
        self.assertEqual((prepared["tool"], prepared["conversation_id"]), ("biz_customer_create", "c1"))
        self.assertNotIn("confirm", prepared["values"])
        catalog = get_catalog(app)
        self.assertFalse(any(catalog.get(name).is_write for name in calls), calls)

    async def test_plan_skips_allocation_candidates_until_payment_is_claimed(self):
        calls = []

        async def fake_call(name, arguments):
            calls.append(name)
            return {"id": 1, "status": "待认领", "claimed_customer": ""}

        with patch.object(business_tools, "get_auth_context", return_value=_context(readonly=False)):
            result = await business_tools.run_business_tool(
                "biz_incoming_payment_claim_allocate", {"payment_id": 1, "customer": "CODEX-甲公司"}, call=fake_call)
        self.assertFalse(result.get("isError"), result)
        self.assertNotIn("oa_incoming_payment_allocation_candidates_get", calls)
        self.assertIn("认领后才能列出可分配费用", str(result))

    async def test_read_only_token_cannot_see_or_run_write_tools(self):
        with patch.object(business_tools, "get_auth_context", return_value=_context()):
            visible = {tool.name for tool in business_tools.visible_tools(get_catalog(app))}
            self.assertIn("biz_case_overview", visible)
            self.assertNotIn("biz_customer_create", visible)
            with self.assertRaises(HTTPException) as caught:
                await business_tools.run_business_tool("biz_customer_create", {"title": "x", "customer_managers": ["a"]})
        self.assertEqual(caught.exception.status_code, 403)

    async def test_business_scope_requires_every_internal_endpoint(self):
        with patch.object(business_tools, "get_auth_context", return_value=_context(groups=frozenset({"16"}), write_allowed=True)):
            visible = {tool.name for tool in business_tools.visible_tools(get_catalog(app))}
        self.assertEqual(visible, {"biz_incoming_payment_find", "biz_incoming_payment_claim_allocate", "biz_incoming_payment_register"})


if __name__ == "__main__":
    unittest.main()


class ConfirmedBusinessExecutionTest(unittest.IsolatedAsyncioTestCase):
    """用户在确认卡片上同意后：整串业务工具按确认时记录的案件来源执行，内部普通写入不再逐步弹卡片；失败按执行失败处理。"""

    async def test_confirmed_business_runs_with_approval_and_case_origin(self):
        from app.agent_mcp import service, auth
        seen = {}

        async def fake_run(name, arguments, **kwargs):
            seen.update(name=name, arguments=arguments, approved=service.APPROVED_EXECUTION.get(), origin=auth._case_origin.get())
            return {"tool": name, "mode": "执行", "steps": []}

        with patch.object(business_tools, "run_business_tool", fake_run), patch.object(auth, "get_auth_context", return_value=_context(readonly=False)):
            result = await service._execute_confirmed_business({"tool_name": "biz_task_create", "arguments": {"title": "T"}, "case_origin": 12})
        self.assertEqual(result["mode"], "执行")
        self.assertEqual(seen, {"name": "biz_task_create", "arguments": {"title": "T", "confirm": True}, "approved": True, "origin": 12})
        self.assertFalse(service.APPROVED_EXECUTION.get())  # 执行完复原

        async def failing(name, arguments, **kwargs):
            return {"isError": True, "message": "第 1 步失败", "failed_step": {"step": 1}}

        with patch.object(business_tools, "run_business_tool", failing), patch.object(auth, "get_auth_context", return_value=_context(readonly=False)):
            with self.assertRaises(HTTPException) as caught:
                await service._execute_confirmed_business({"tool_name": "biz_task_create", "arguments": {}, "case_origin": None})
        self.assertEqual(caught.exception.status_code, 422)

    def test_fingerprint_changes_when_tool_definition_changes(self):
        tool = business_tools.TOOLS["biz_customer_create"]
        self.assertEqual(business_tools.business_fingerprint(tool), business_tools.business_fingerprint(tool))
        from dataclasses import replace
        self.assertNotEqual(business_tools.business_fingerprint(tool), business_tools.business_fingerprint(replace(tool, uses=tool.uses[:-1])))
