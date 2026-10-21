"""常驻会话复用后的第二轮仍要能调用工具：工具通道不能引用已被置空的 resident 变量。"""
import json
import unittest
from unittest.mock import AsyncMock, patch

from app.agent_skills import GENERAL_SKILL
from app.config import settings
from app.harness_agent import runtime
from app.harness_agent.runtime import run
from tests.regression.deepseek_harness_runtime_test import isolated_home, model_server


class ResidentToolCallTest(unittest.IsolatedAsyncioTestCase):
    async def test_tool_call_works_on_reused_resident_turn(self):
        requests = []
        tools = AsyncMock()
        tools.execute.return_value = {"verified": True}
        schema = [{"type": "function", "function": {"name": "metadata_probe", "description": "x",
                  "parameters": {"type": "object", "properties": {}}}}]

        def choose(count):  # 每轮两次模型请求：先调用工具，再给出最终回答
            return {"name": "mcp__oa__metadata_probe", "arguments": "{}"} if count % 2 == 1 else None

        async with isolated_home() as home:
            async with model_server(requests, choose) as url:
                with patch.object(settings, "deepseek_harness_root", home), patch.object(settings, "langgraph_api_base_url", url), \
                     patch.object(settings, "langgraph_api_key", "isolated-key"), patch.object(settings, "langgraph_model", "oa-probe"), \
                     patch("app.harness_agent.runtime.definitions", AsyncMock(return_value=[GENERAL_SKILL])):
                    try:
                        for text in ("第一轮", "第二轮"):
                            result = await run([{"role": "user", "content": text}], AsyncMock(), tools=tools, schema=schema,
                                               identity={"username": "resident-probe"}, db=None, workspace="personal",
                                               conversation="reuse", mode_supported=True, response_mode="fast")
                            self.assertEqual(result, "核验完成")
                        self.assertEqual(tools.execute.await_count, 2)
                    finally:
                        await runtime.close_all_residents()


if __name__ == "__main__":
    unittest.main()
