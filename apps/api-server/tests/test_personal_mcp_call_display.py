"""外部MCP调用：确认卡参数用中文提示；外部工具报错时把它自己的错误码和信息（去凭据）告诉人。"""
import unittest
from types import SimpleNamespace

from app.areas.capability_market.remote_tools import _remote_error_text
from app.areas.personal_agent.mcp_tools import _argument_labels

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


if __name__ == "__main__":
    unittest.main()
