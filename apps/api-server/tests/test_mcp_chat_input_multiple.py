"""陶国南 11-01：一次粘贴多个 MCP 服务时，提示要说清楚贴了哪几个、怎么拆开发。"""
import json
import unittest

from fastapi import HTTPException

from app.areas.personal_agent.mcp_chat_input import extract_chat_connection


class McpChatInputMultipleTest(unittest.TestCase):
    def test_multiple_servers_message_names_them_and_says_how_to_split(self):
        text = json.dumps({"mcpServers": {
            "amap": {"url": "https://a.example.com/mcp", "headers": {"Authorization": "Bearer tokenA1"}},
            "search": {"url": "https://b.example.com/mcp", "headers": {"Authorization": "Bearer tokenB2"}},
        }})
        with self.assertRaises(HTTPException) as caught:
            extract_chat_connection(text)
        detail = caught.exception.detail
        self.assertIn("这次粘贴了 2 个（「amap」、「search」）", detail)
        self.assertIn("请分开发送", detail)
        self.assertNotIn("tokenA1", detail)

    def test_single_server_still_works(self):
        text = json.dumps({"mcpServers": {"amap": {"url": "https://a.example.com/mcp", "headers": {"Authorization": "Bearer tokenA1"}}}})
        self.assertEqual(extract_chat_connection(text).plan.name, "amap")


if __name__ == "__main__":
    unittest.main()
