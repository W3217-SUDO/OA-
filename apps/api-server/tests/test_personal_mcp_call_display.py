"""外部MCP调用：确认卡参数用中文提示；外部工具报错时把它自己的错误码和信息（去凭据）告诉人。"""
import unittest
from types import SimpleNamespace

from app.areas.capability_market.remote_tools import _remote_error_text
from app.areas.personal_agent.mcp_tools import _argument_labels
from app.areas.personal_agent.service import _remote_result_text

CONF = {"mcp.json": {"mcpServers": {"default": {"headers": {"Authorization": "Bearer SECRET-KEY-123"}}}}}


class PersonalMcpCallDisplayTests(unittest.TestCase):
    def test_remote_error_shows_code_and_message(self):
        result = SimpleNamespace(content=[SimpleNamespace(text='{"request_id":"x","code":"invalid_model","message":"The model does not exist or you do not have access to it."}')])
        self.assertEqual(_remote_error_text(result, CONF), "（外部返回：invalid_model：The model does not exist or you do not have access to it.）")

    def test_remote_error_hides_credential_echo_and_empty(self):
        echoed = SimpleNamespace(content=[SimpleNamespace(text="bad header Bearer SECRET-KEY-123")])
        self.assertNotIn("SECRET-KEY-123", _remote_error_text(echoed, CONF))
        self.assertEqual(_remote_error_text(SimpleNamespace(content=[]), CONF), "")

    def test_argument_labels_from_schema_descriptions(self):
        descriptor = {"inputSchema": {"properties": {"query": {"description": "搜索查询关键词或短语，用于指定需要搜索的内容。"}, "model": {}}}}
        self.assertEqual(_argument_labels(descriptor, {"query": "a", "model": "b"}), {"query": "搜索查询关键词或短语（query）", "model": "model"})


class RemoteResultTextTests(unittest.TestCase):
    def test_text_content_joined_not_raw_json(self):
        text = _remote_result_text({"_meta": None, "content": [{"type": "text", "text": "Title: 公司法\nURL: https://a"}, {"type": "text", "text": "第二条"}]})
        self.assertTrue(text.startswith("外部服务已返回结果"))
        self.assertIn("Title: 公司法\nURL: https://a\n\n第二条", text)
        self.assertNotIn('"_meta"', text)

    def test_non_text_falls_back_to_json(self):
        self.assertIn('"items"', _remote_result_text({"items": [1]}))


if __name__ == "__main__":
    unittest.main()
