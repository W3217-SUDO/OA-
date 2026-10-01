import unittest
from unittest.mock import AsyncMock

from app.deepseek_harness import (
    DeepSeekHarnessCaseAgentRuntime,
    create_case_agent_runtime,
)


class DeepSeekHarnessRuntimeTest(unittest.IsolatedAsyncioTestCase):
    def make_runtime(self) -> DeepSeekHarnessCaseAgentRuntime:
        return DeepSeekHarnessCaseAgentRuntime(
            enabled=True,
            database_url="sqlite+aiosqlite:///:memory:",
            api_base_url="https://model.example/v1",
            api_key="test-only",
            model_provider="openai-compatible",
            model="gpt-test",
            harness_base_url="http://127.0.0.1:3081",
            harness_workspace="C:/tmp/sunhold-agent",
        )

    def test_factory_keeps_langgraph_as_explicit_rollback(self):
        runtime = create_case_agent_runtime(
            runtime_backend="langgraph",
            enabled=False,
            database_url="sqlite+aiosqlite:///:memory:",
            harness_base_url="http://127.0.0.1:3081",
        )
        self.assertEqual(runtime.status()["agent_runtime_backend"], "langgraph")

    def test_factory_selects_deepseek_harness(self):
        runtime = create_case_agent_runtime(
            runtime_backend="deepseek-harness",
            enabled=False,
            database_url="sqlite+aiosqlite:///:memory:",
            harness_base_url="http://127.0.0.1:3081",
        )
        self.assertIsInstance(runtime, DeepSeekHarnessCaseAgentRuntime)
        self.assertEqual(runtime.status()["agent_runtime_backend"], "deepseek-harness")

    def test_private_harness_sessions_are_partitioned_by_user(self):
        runtime = self.make_runtime()
        snapshot = {"case": {"id": 4059}}
        lawyer = runtime._harness_session_id(snapshot, [{"operator": "lawyer"}])
        assistant = runtime._harness_session_id(snapshot, [{"operator": "assistant"}])
        self.assertNotEqual(lawyer, assistant)
        self.assertTrue(lawyer.startswith("sunhold-4059-"))

    def test_prompt_contains_oa_boundary_and_converts_images(self):
        runtime = self.make_runtime()
        parts = runtime._prompt_content(
            [{"role": "system", "content": "仅依据授权案件"}, {"role": "user", "content": "审阅截图"}],
            [{
                "name": "evidence.png",
                "data_url": "data:image/png;base64,dGVzdA==",
            }],
        )
        self.assertIn("不要调用 Bash", parts[0]["text"])
        self.assertIn("仅依据授权案件", parts[0]["text"])
        self.assertIn("由 OA 前端保存为 DOCX", parts[0]["text"])
        self.assertEqual(parts[1]["type"], "image")
        self.assertEqual(parts[1]["data"], "dGVzdA==")

    def test_websocket_envelope_parser_handles_server_request(self):
        raw = '{"type":"server-request","rpcId":"1","payload":{"type":"session/subscribed","sessionId":"s","lastSeq":-1}}'
        parsed = DeepSeekHarnessCaseAgentRuntime._event_envelope(raw)
        self.assertEqual(parsed["payload"]["sessionId"], "s")

    async def test_model_route_uses_existing_api_with_gateway_compatibility(self):
        runtime = self.make_runtime()
        runtime._rpc = AsyncMock(side_effect=[
            {"namespaces": [{"ns": "llm-pi-ai", "revision": 3, "value": {"providers": {}}}]},
            {},
            {},
        ])
        await runtime._configure_model_route()
        mutate = runtime._rpc.await_args_list[1].args[1]
        profile = mutate["ops"][0]["value"]
        self.assertEqual(profile["baseURL"], "https://model.example/v1")
        self.assertEqual(profile["headers"], {"Connection": "close"})
        self.assertEqual(profile["retryPolicy"]["maxRetries"], 0)
        self.assertGreaterEqual(profile["timeoutMs"], 120_000)

    async def test_model_response_keeps_oa_approval_contract(self):
        runtime = self.make_runtime()
        runtime._ensure_session = AsyncMock()
        runtime._run_prompt = AsyncMock(return_value=(
            "可以更新案件说明。"
            '<proposed_action>{"type":"case.update","summary":"更新说明",'
            '"payload":{"changes":{"description":"已核验"}}}</proposed_action>'
        ))
        content, action = await runtime._request_model(
            {"case": {"id": 4059, "serial_no": "SHMS2500726"}, "capabilities": {"can_edit_basic": True}},
            [{"role": "user", "operator": "lawyer", "content": "修改案件说明"}],
        )
        self.assertEqual(content, "可以更新案件说明。")
        self.assertEqual(action["type"], "case.update")
        prompt_parts = runtime._run_prompt.await_args.args[1]
        self.assertIn("SHMS2500726", prompt_parts[0]["text"])


if __name__ == "__main__":
    unittest.main()
