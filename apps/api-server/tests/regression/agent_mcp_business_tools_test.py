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

        with patch.object(business_tools, "get_auth_context", return_value=_context(readonly=False)):
            result = await business_tools.run_business_tool("biz_task_create", {
                "title": "CODEX-任务", "owner": "admin", "deadline": "2026-11-30", "confirm": True}, call=fake_call)
        self.assertTrue(result["isError"])
        self.assertEqual(result["failed_step"]["error"], "合同当前不在审批中")

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
