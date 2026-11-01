"""陶国南、陶威 11-01：一次粘贴多个 MCP 服务时自动拆开，逐个配置；超过上限才提示分开发。"""
import json
import unittest

from fastapi import HTTPException

from app.areas.personal_agent.mcp_chat_input import (MAX_BATCH_SERVERS, ChatConnectionBatch, chat_connection_timeout,
                                                     extract_chat_connection)


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

    def test_fourteen_servers_fit_and_turn_time_grows_with_count(self):
        """北大法宝整份 mcp.json 有 14 个服务（陶国南 11-01），上限 20。"""
        self.assertEqual(MAX_BATCH_SERVERS, 20)
        batch = extract_chat_connection(json.dumps({"mcpServers": {f"pkulaw-{index}": server(index) for index in range(14)}}))
        self.assertEqual(len(batch.items), 14)
        # 每个服务验证最多 25 秒，14 个也要在本轮时限内配完。
        self.assertGreaterEqual(chat_connection_timeout(batch), 14 * 25)
        self.assertEqual(chat_connection_timeout(None), 180)
        self.assertEqual(chat_connection_timeout(extract_chat_connection(json.dumps({"mcpServers": {"a": server(1)}}))), 180)

    def test_provider_page_copy_with_several_addresses_and_one_key(self):
        """华语元典网页上的地址表整段复制，加上自己的 Key：5 个服务逐个配置，示例占位符不算密钥（陶国南 11-01）。"""
        text = ("元典法律智能 MCP 接入\n请求 Header 使用\nAuthorization: Bearer YOUR_API_KEY\n"
                "yuandian-law\n法律法规\nhttps://open.chineselaw.com/mcp/law/stream\n"
                "yuandian-case\n案例文书\nhttps://open.chineselaw.com/mcp/case/stream\n"
                "yuandian-company\n企业信息\nhttps://open.chineselaw.com/mcp/company/stream\n"
                "我的 Key：Bearer fake-yd-token-123")
        batch = extract_chat_connection(text)
        self.assertIsInstance(batch, ChatConnectionBatch)
        self.assertEqual([name for name, _, _ in batch.items], ["yuandian-law", "yuandian-case", "yuandian-company"])
        self.assertEqual({item.credential.get_secret_value() for _, item, _ in batch.items}, {"fake-yd-token-123"})
        self.assertEqual(batch.items[1][1].plan.server_url, "https://open.chineselaw.com/mcp/case/stream")
        self.assertNotIn("fake-yd-token", batch.message())

    def test_harmless_extra_fields_are_ignored_and_local_commands_explained(self):
        submission = extract_chat_connection(json.dumps({"mcpServers": {"yuandian-law": {
            "type": "streamable-http", "url": "https://open.chineselaw.com/mcp/law/stream", "timeout": 60,
            "description": "法律法规", "disabled": False, "headers": {"Authorization": "Bearer fake-yd-1"}}}}))
        self.assertEqual((submission.plan.name, submission.plan.transport), ("yuandian-law", "streamable_http"))
        with self.assertRaises(HTTPException) as caught:
            extract_chat_connection(json.dumps({"mcpServers": {"local": {"command": "npx", "args": ["x"], "env": {"K": "v"}}}}))
        self.assertIn("本机启动方式", caught.exception.detail)

    def test_single_server_still_works(self):
        submission = extract_chat_connection(json.dumps({"mcpServers": {"amap": server(1)}}))
        self.assertEqual((submission.plan.name, submission.credential.get_secret_value()), ("amap", "fake-token-1"))


if __name__ == "__main__":
    unittest.main()
