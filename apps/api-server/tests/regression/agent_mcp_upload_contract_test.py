"""MCP 上传能力的搜索、分组及参数展示契约。"""

import unittest

from app.agent_mcp.auth import AuthContext, _auth_context
from app.agent_mcp.catalog import get_catalog
from app.agent_mcp.model_context import discovered_tools_view
from app.agent_mcp.router import tool_catalog
from app.agent_mcp.service import public_tool
from app.main import app


class AgentMcpUploadContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = get_catalog(app)

    def _names(self, query: str) -> set[str]:
        return {tool.name for tool in self.catalog.search(query, limit=50)}

    def test_upload_synonyms_find_generic_and_business_tools(self):
        generic = "oa_upload_attachment_post"
        business_queries = {
            "客户上传附件": "oa_upload_customer_contact_photo_post",
            "财务上传文件": "oa_upload_receipt_files_post",
            "回款导入": "oa_import_incoming_payments_post",
        }
        self.assertIn(generic, self._names("上传附件"))
        self.assertIn(generic, self._names("附件"))
        self.assertIn(generic, self._names("文件"))
        for query, expected in business_queries.items():
            with self.subTest(query=query):
                self.assertIn(expected, self._names(query))

    def test_business_action_synonyms_find_representative_tools(self):
        action_queries = {
            "检索客户": "oa_customer_conflicts_get",
            "新增客户": "oa_create_customer_post",
            "编辑客户": "oa_patch_customer_patch",
            "移除客户": "oa_delete_customer_contact_delete",
            "核准案件": "oa_review_case_creation_post",
            "下载附件": "oa_download_attachment_get",
            "导出案件": "oa_export_current_ordinary_cases_excel_post",
            "分派回款": "oa_allocate_incoming_payment_post",
        }
        for query, expected in action_queries.items():
            with self.subTest(query=query):
                self.assertIn(expected, self._names(query))

    def test_discovered_tools_are_grouped_by_business_domain(self):
        tools = [
            public_tool(self.catalog.get("oa_upload_attachment_post")),
            public_tool(self.catalog.get("oa_upload_receipt_files_post")),
        ]
        result = discovered_tools_view(tools)
        self.assertIn("groups", result)
        groups = {group["domain"]: group for group in result["groups"]}
        self.assertEqual(set(groups), {"案件", "财务"})
        self.assertEqual(
            set(groups["案件"]["tool_names"]),
            {"oa_upload_attachment_post"},
        )
        self.assertEqual(
            set(groups["财务"]["tool_names"]),
            {"oa_upload_receipt_files_post"},
        )

    def test_upload_tool_exposes_parameter_groups_and_required_fields(self):
        descriptor = public_tool(self.catalog.get("oa_upload_attachment_post"))
        self.assertIn("parameter_groups", descriptor)
        self.assertIn("required_parameters", descriptor)
        self.assertEqual(descriptor["request_media_type"], "multipart/form-data")
        self.assertIn("file", descriptor["required_parameters"]["files"])
        body_names = {field["name"] for field in descriptor["parameter_groups"]["body"]}
        file_names = {field["name"] for field in descriptor["parameter_groups"]["files"]}
        self.assertIn("category", body_names)
        self.assertIn("file", file_names)

    def test_catalog_endpoint_returns_full_business_groups(self):
        token = _auth_context.set(AuthContext(
            app, "CODEX-test-bearer",
            {"type": "http", "path": "/api/v1/agent-tools/catalog", "method": "GET", "headers": []},
        ))
        try:
            result = self._run(tool_catalog())
        finally:
            _auth_context.reset(token)

        self.assertIn("groups", result)
        groups = {group["domain"]: group for group in result["groups"]}
        self.assertEqual(sum(group["tool_count"] for group in groups.values()), result["inventory"]["tool_count"])
        self.assertEqual(
            {name for group in groups.values() for name in group["tool_names"]},
            {tool["name"] for tool in result["tools"]},
        )
        self.assertIn("oa_upload_attachment_post", groups["案件"]["tool_names"])
        self.assertIn("oa_upload_receipt_files_post", groups["财务"]["tool_names"])

    @staticmethod
    def _run(awaitable):
        import asyncio
        return asyncio.run(awaitable)


if __name__ == "__main__":
    unittest.main()
