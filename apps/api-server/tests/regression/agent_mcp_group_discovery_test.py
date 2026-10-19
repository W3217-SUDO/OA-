"""真实目录的分组与模型会话契约；不连接业务数据库或真实模型。"""

from collections import Counter
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.agent_mcp import gateway, model_tools, service
from app.agent_mcp.auth import AuthContext, _auth_context
from app.agent_mcp.catalog import ToolCatalog
from app.agent_mcp.model_context import TOOL_RESULT_BYTES, encoded_size
from app.agent_mcp.tool_groups import GROUPS, SUBGROUPS
from app.main import app


class GroupCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = ToolCatalog(app)

    def test_all_825_tools_have_one_primary_group_and_are_retrievable(self):
        self.assertEqual(len(self.catalog.tools), 825)
        names = [tool.name for tool in self.catalog.tools]
        self.assertEqual(len(set(names)), 825)
        resources = self.catalog.search('读取系统技能参考资料', group_id='25', subgroup_id='ai_documents_skills', limit=3)
        self.assertEqual(resources[0].name, 'oa_read_system_skill_resource_get')
        counts = Counter()
        for tool in self.catalog.tools:
            with self.subTest(tool=tool.name):
                self.assertIn(tool.group_id, GROUPS)
                counts[tool.group_id] += 1
                self.assertEqual(tool.group_name, GROUPS[tool.group_id][0])
                if tool.group_id == "25":
                    self.assertIn(tool.subgroup_id, SUBGROUPS)
                else:
                    self.assertIsNone(tool.subgroup_id)
                found = self.catalog.search(tool.name, limit=3, group_id=tool.group_id, subgroup_id=tool.subgroup_id)
                self.assertIn(tool.name, [item.name for item in found])
                self.assertTrue(all(item.group_id == tool.group_id for item in found))
                if tool.subgroup_id:
                    self.assertTrue(all(item.subgroup_id == tool.subgroup_id for item in found))
        print(f"Primary groups (deterministic directory coverage, not LLM accuracy): {dict(sorted(counts.items()))}")
        self.assertEqual(sum(counts.values()), 825)

    def test_25_group_summaries_have_counts_without_schemas(self):
        groups = self.catalog.list_groups()
        self.assertEqual({item["group_id"] for item in groups}, set(GROUPS))
        self.assertEqual(len(groups), 25)
        self.assertEqual(sum(item["tool_count"] for item in groups), 825)
        serialized = json.dumps(groups)
        for key in ("inputSchema", "properties", "$defs", "parameter_groups"):
            self.assertNotIn(key, serialized)
        auxiliary = next(item for item in groups if item["group_id"] == "25")
        self.assertEqual({item["subgroup_id"] for item in auxiliary["subgroups"]}, set(SUBGROUPS))
        self.assertEqual(sum(item["tool_count"] for item in auxiliary["subgroups"]), auxiliary["tool_count"])
        self.assertLess(encoded_size(groups), TOOL_RESULT_BYTES)

    def test_auxiliary_group_keywords_discover_only_relevant_subgroups(self):
        for query, expected in (("模板", "ai_documents_skills"), ("菜单", "system_parameters"),
                                ("notifications_feedback", "notifications_feedback")):
            with self.subTest(query=query):
                found = self.catalog.list_groups(query)
                group = next(item for item in found if item["group_id"] == "25")
                self.assertIn(expected, {item["subgroup_id"] for item in group["subgroups"]})
        with self.assertRaises(HTTPException) as raised:
            self.catalog.search("报表", group_id="25")
        self.assertEqual(raised.exception.status_code, 422)

    def test_finance_near_synonyms_recall_top_three_without_payment_confusion(self):
        cases = (
            ("登记费用", "15", "oa_create_finance_fee_post"),
            ("录一笔费用", "15", "oa_create_finance_fee_post"),
            ("新增费用", "15", "oa_create_finance_fee_post"),
            ("回款", "16", "oa_list_incoming_payments_get"),
            ("到账", "16", "oa_list_incoming_payments_get"),
            ("分配回款", "16", "oa_allocate_incoming_payment_post"),
            ("分派回款", "16", "oa_allocate_incoming_payment_post"),
            ("付款", "19", "oa_list_internal_payment_packages_get"),
            ("支出", "19", "oa_list_internal_payment_packages_get"),
        )
        for query, group, expected in cases:
            with self.subTest(query=query):
                found = self.catalog.search(query, limit=3, group_id=group)
                self.assertIn(expected, [tool.name for tool in found])
                self.assertTrue(all(tool.group_id == group for tool in found))
        fee = service.public_tool(self.catalog.get("oa_create_finance_fee_post"))
        incoming = service.public_tool(self.catalog.get("oa_allocate_incoming_payment_post"))
        self.assertIn("不是付款", json.dumps(fee["usage"], ensure_ascii=False))
        self.assertIn("不等于对外付款", json.dumps(incoming["usage"], ensure_ascii=False))

    def test_natural_short_phrases_recall_groups_and_tools_in_top_three(self):
        cases = (
            ("新增一笔律师费", "15", {"oa_create_finance_fee_post"}),
            ("登记代理费", "15", {"oa_create_finance_fee_post"}),
            ("官费", "15", {"oa_create_finance_fee_post"}),
            ("诉讼费", "15", {"oa_create_finance_fee_post"}),
            ("登记官费", "15", {"oa_create_finance_fee_post"}),
            ("登记诉讼费", "15", {"oa_create_finance_fee_post"}),
            ("客户打钱了", "16", {"oa_create_incoming_payment_post"}),
            ("收到一笔款", "16", {"oa_create_incoming_payment_post"}),
            ("收款入账", "16", {"oa_create_incoming_payment_post"}),
            ("给供应商打款", "19", {"oa_list_internal_payment_packages_get", "oa_create_payment_application_post"}),
            ("付出去一笔钱", "19", {"oa_list_internal_payment_packages_get", "oa_create_payment_application_post"}),
            ("某律师手上的案子有多少", "06", {"oa_case_statistics_post"}),
            ("查某律师手上的案子有多少", "06", {"oa_case_statistics_post"}),
        )
        for query, group, expected in cases:
            groups = self.catalog.list_groups(query)
            found = self.catalog.search(query, limit=3, group_id=group)
            group_ids = [item["group_id"] for item in groups[:3]]
            names = [tool.name for tool in found]
            print(f"Natural phrase matrix: {query!r}; groups={group_ids}; tools={names}")
            with self.subTest(query=query, stage="groups"):
                self.assertIn(group, group_ids)
            with self.subTest(query=query, stage="tools"):
                self.assertTrue(expected.intersection(names), names)
                self.assertTrue(all(tool.group_id == group for tool in found))


class GroupSessionTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = ToolCatalog(app)

    async def asyncSetUp(self):
        self.token = _auth_context.set(AuthContext(app, "CODEX-isolated-token", {
            "type": "http", "path": "/api/v1/mcp", "method": "POST", "headers": [],
        }))
        self.session = model_tools.ModelToolSession()
        self.catalog_patch = patch.object(model_tools, "get_catalog", return_value=self.catalog)
        self.service_patch = patch.object(service, "get_catalog", return_value=self.catalog)
        self.catalog_patch.start()
        self.service_patch.start()
        self.addCleanup(self.catalog_patch.stop)
        self.addCleanup(self.service_patch.stop)

    async def asyncTearDown(self):
        _auth_context.reset(self.token)

    async def test_no_group_or_unread_schema_can_call_tool(self):
        with patch.object(model_tools, "call_tool", new=AsyncMock()) as call:
            result = await self.session.execute("oa_search_tools", {"query": "客户", "group_id": "03"})
            self.assertEqual(result["status_code"], 422)
            listed = await self.session.execute("oa_list_tool_groups", {})
            self.assertEqual(len(listed["groups"]), 25)
            self.assertEqual(self.session.discovered, {})
            result = await self.session.execute("oa_call_tool", {"name": "oa_list_customers_get", "arguments": {}})
            self.assertEqual(result["status_code"], 422)
            call.assert_not_awaited()

    async def test_search_without_group_only_returns_summaries(self):
        result = await self.session.execute("oa_search_tools", {"query": "客户"})
        self.assertEqual(result["discovery_stage"], "groups")
        self.assertNotIn("tools", result)
        self.assertNotIn("inputSchema", json.dumps(result))
        self.assertIn("03", self.session.discovered_groups)
        self.assertEqual(self.session.discovered, {})

    async def test_scoped_discovery_and_call_keep_permissions_and_session_isolation(self):
        await self.session.execute("oa_list_tool_groups", {"query": "客户"})
        result = await self.session.execute("oa_search_tools", {"query": "查客户", "group_id": "03", "limit": 3})
        self.assertTrue(result["tools"])
        self.assertTrue(all(tool["group_id"] == "03" for tool in result["tools"]))
        self.assertIn("oa_list_customers_get", self.session.discovered)
        with patch.object(model_tools, "call_tool", new=AsyncMock(side_effect=HTTPException(403, "CODEX denied"))) as call:
            denied = await self.session.execute("oa_call_tool", {"name": "oa_list_customers_get", "arguments": {}})
            self.assertEqual(denied["status_code"], 403)
            call.assert_awaited_once()
            foreign = await self.session.execute("oa_call_tool", {"name": "oa_list_internal_payment_packages_get", "arguments": {}})
            self.assertEqual(foreign["status_code"], 422)
            fresh = await model_tools.ModelToolSession().execute("oa_call_tool", {"name": "oa_list_customers_get", "arguments": {}})
            self.assertEqual(fresh["status_code"], 422)
            self.assertEqual(call.await_count, 1)

    async def test_group_25_requires_explicit_subgroup_before_schemas(self):
        await self.session.execute("oa_list_tool_groups", {})
        result = await self.session.execute("oa_search_tools", {"query": "报表", "group_id": "25"})
        self.assertEqual(result["discovery_stage"], "groups")
        self.assertNotIn("tools", result)
        result = await self.session.execute("oa_search_tools", {
            "query": "报表", "group_id": "25", "subgroup_id": "reporting", "limit": 3,
        })
        self.assertTrue(result["tools"])
        self.assertTrue(all(item["subgroup_id"] == "reporting" for item in result["tools"]))
        self.session.discovered_subgroups.clear()
        denied = await self.session.execute("oa_search_tools", {
            "query": "报表", "group_id": "25", "subgroup_id": "reporting",
        })
        self.assertEqual(denied["status_code"], 422)

    async def test_external_search_remains_compatible_without_group(self):
        found = service.search_tools("客户", limit=3)
        self.assertEqual(len(found), 3)
        self.assertTrue(all("inputSchema" in item for item in found))

    async def test_gateway_tools_list_keeps_all_business_schemas_and_adds_group_entry(self):
        with patch.object(gateway, "get_catalog", return_value=self.catalog):
            result = await gateway._list_tools(None, None)
        tools = {item.name: item for item in result.tools}
        self.assertEqual(len(result.tools), 827)
        self.assertEqual(len(tools), 827)
        self.assertEqual(set(tools), {tool.name for tool in self.catalog.tools} | {"oa_search_tools", "oa_list_tool_groups"})
        for tool in self.catalog.tools:
            self.assertEqual(tools[tool.name].input_schema, tool.input_schema)
        self.assertEqual({item["function"]["name"] for item in model_tools.MODEL_TOOLS},
                         {"oa_list_tool_groups", "oa_search_tools", "oa_call_tool"})

    async def test_gateway_group_summaries_and_subgroup_errors_keep_external_compatibility(self):
        result = await gateway._call_tool(None, SimpleNamespace(name="oa_list_tool_groups", arguments={}))
        self.assertFalse(result.is_error)
        self.assertEqual(len(result.structured_content["groups"]), 25)
        self.assertNotIn("inputSchema", json.dumps(result.structured_content))
        result = await gateway._call_tool(None, SimpleNamespace(name="oa_search_tools", arguments={
            "query": "报表", "group_id": "25",
        }))
        self.assertTrue(result.is_error)
        self.assertEqual(result.structured_content["status_code"], 422)
        result = await gateway._call_tool(None, SimpleNamespace(name="oa_search_tools", arguments={
            "query": "报表", "group_id": "25", "subgroup_id": "reporting", "limit": 3,
        }))
        self.assertFalse(result.is_error)
        self.assertTrue(all(item["subgroup_id"] == "reporting" for item in result.structured_content["tools"]))
        with patch.object(gateway, "call_tool", new=AsyncMock(return_value={"items": []})) as call:
            result = await gateway._call_tool(None, SimpleNamespace(name="oa_list_customers_get", arguments={}))
            self.assertFalse(result.is_error)
            call.assert_awaited_once_with("oa_list_customers_get", {})


if __name__ == "__main__":
    unittest.main()
