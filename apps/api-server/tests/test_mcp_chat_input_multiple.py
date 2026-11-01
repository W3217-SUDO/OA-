"""陶国南、陶威 11-01：一次粘贴多个 MCP 服务时自动拆开，逐个配置；超过上限才提示分开发。"""
import json
import unittest

from fastapi import HTTPException

from app.areas.personal_agent.mcp_chat_input import MAX_BATCH_SERVERS, ChatConnectionBatch, extract_chat_connection


def server(index, auth="Bearer fake-token-%d"):
    return {"url": f"https://s{index}.example.com/mcp", "headers": {"Authorization": auth % index}}


class McpChatInputMultipleTest(unittest.TestCase):
    def test_multiple_servers_split_with_per_server_errors(self):
        text = json.dumps({"mcpServers": {"amap": server(1), "bad": server(2, "Basic fake-%d"), "search": server(3)}})
        batch = extract_chat_connection(text)
        self.assertIsInstance(batch, ChatConnectionBatch)
        self.assertEqual([(name, item is not None) for name, item, _ in batch.items], [("amap", True), ("bad", False), ("search", True)])
        self.assertEqual(batch.items[1][2], "Authorization 仅支持 Bearer Token")
        self.assertEqual(batch.items[2][1].credential.get_secret_value(), "fake-token-3")
        self.assertNotIn("fake-token", repr(batch) + batch.message())

    def test_mcp_json_wrapper_with_many_servers(self):
        batch = extract_chat_connection(json.dumps({"mcp.json": {"mcpServers": {"a": server(1), "b": server(2)}}}))
        self.assertEqual(len(batch.items), 2)

    def test_over_limit_asks_to_split(self):
        servers = {f"s{index}": server(index) for index in range(MAX_BATCH_SERVERS + 1)}
        with self.assertRaises(HTTPException) as caught:
            extract_chat_connection(json.dumps({"mcpServers": servers}))
        self.assertIn("请分几条消息发送", caught.exception.detail)

    def test_single_server_still_works(self):
        submission = extract_chat_connection(json.dumps({"mcpServers": {"amap": server(1)}}))
        self.assertEqual((submission.plan.name, submission.credential.get_secret_value()), ("amap", "fake-token-1"))


if __name__ == "__main__":
    unittest.main()
