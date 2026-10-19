"""原生 SDK 边界与协议回归；验证数据、模拟模型及文件仅存在隔离测试目录。"""
import asyncio
from dataclasses import replace
from contextlib import asynccontextmanager, contextmanager
import json
import os
from pathlib import Path
import socket
import shutil
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from starlette.requests import Request

from app.case_agent import CaseAgentRuntime
from app.deepseek_harness import create_case_agent_runtime
from app.harness_agent.bridge import _Server
from app.harness_agent.lease import session_lease
from app.harness_agent.runtime import _content, _environment, readiness, run, workspace_paths
from app.config import settings
from app.agent_skills import GENERAL_SKILL
from app.harness_agent.skills import native_name
import uvicorn


@contextmanager
def isolated_home():
    with tempfile.TemporaryDirectory(prefix="oa-harness-test-") as temporary:
        try:
            yield temporary
        finally:
            # 官方日志把 cwd 编入目录名；Windows 清理时使用长路径语法。
            target = Path(temporary).resolve()
            if target.parent != Path(tempfile.gettempdir()).resolve() or not target.name.startswith("oa-harness-test-"):
                raise RuntimeError("隔离核验目录归属不符")
            if os.name == "nt":
                shutil.rmtree("\\\\?\\" + str(target))


@asynccontextmanager
async def model_server(requests, choose_function=None):
    application = FastAPI()

    @application.post("/v1/chat/completions")
    async def completion(request: Request):
        payload = await request.json()
        requests.append(payload)
        first = len(requests) <= 2
        function = {"name": "skill", "arguments": json.dumps({"name": native_name("isolated-skill")})} if len(requests) == 1 else {"name": "mcp__oa__metadata_probe", "arguments": "{}"}
        if choose_function is not None:
            function = choose_function(len(requests))
            first = function is not None
        delta = {"role": "assistant", "tool_calls": [{"index": 0, "id": "probe-call", "type": "function",
                 "function": function}]} if first else {"role": "assistant", "content": "核验完成"}
        async def stream():
            for data, reason in ((delta, None), ({}, "tool_calls" if first else "stop")):
                yield "data: " + json.dumps({"id": "probe", "object": "chat.completion.chunk", "created": 1,
                    "model": "oa-probe", "choices": [{"index": 0, "delta": data, "finish_reason": reason}]}) + "\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(stream(), media_type="text/event-stream")

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(8)
    server = _Server(uvicorn.Config(application, log_config=None, access_log=False, lifespan="off"))
    task = asyncio.create_task(server.serve(sockets=[listener]))
    try:
        async with asyncio.timeout(5):
            while not server.started:
                await asyncio.sleep(0.01)
        yield "http://127.0.0.1:" + str(listener.getsockname()[1]) + "/v1"
    finally:
        server.should_exit = True
        await asyncio.wait_for(task, 5)
        listener.close()


class DeepSeekHarnessRuntimeTest(unittest.IsolatedAsyncioTestCase):
    async def test_native_memory_survives_new_conversation_and_isolates_workspace(self):
        binary = os.environ.get('OA_TEST_ENGRAM_BINARY', '')
        if not binary:
            self.skipTest('未提供隔离 Engram 测试程序')
        requests = []
        marker = 'CODEX-PERSISTENT-RECALL-20261020'

        def choose(index):
            if index == 1:
                return {'name': 'mcp__engram__mem_save', 'arguments': json.dumps({
                    'title': marker, 'type': 'manual', 'content': marker})}
            if index in (3, 5):
                return {'name': 'mcp__engram__mem_search', 'arguments': json.dumps({'query': marker})}
            return None

        with isolated_home() as temporary:
            async with model_server(requests, choose) as url:
                with patch.object(settings, 'deepseek_harness_root', str(Path(temporary) / 'harness')), \
                     patch.object(settings, 'personal_agent_root', str(Path(temporary) / 'personal')), \
                     patch.object(settings, 'deepseek_harness_memory_command', binary), \
                     patch.object(settings, 'langgraph_api_base_url', url), \
                     patch.object(settings, 'langgraph_api_key', 'CODEX-isolated-model-key'), \
                     patch.object(settings, 'langgraph_model', 'oa-probe'), \
                     patch('app.harness_agent.runtime.definitions', AsyncMock(return_value=[])):
                    for workspace, conversation in [('personal', 'first'), ('personal', 'fresh'), ('case:7', 'separate')]:
                        await run([{'role': 'user', 'content': '核验原生长期记忆'}], AsyncMock(),
                                  tools=AsyncMock(), schema=[], identity={'username': 'CODEX-memory-owner'},
                                  db=AsyncMock(), workspace=workspace, conversation=conversation,
                                  response_mode='fast', mode_supported=False, on_progress=None)
                    first_search = [item for item in requests[3]['messages'] if item['role'] == 'tool']
                    other_search = [item for item in requests[5]['messages'] if item['role'] == 'tool']
                    self.assertIn(marker, json.dumps(first_search))
                    self.assertNotIn('No memories found', json.dumps(first_search))
                    self.assertIn('No memories found', json.dumps(other_search))
                    for request in requests:
                        self.assertIn('mcp__engram__mem_save', [item['function']['name'] for item in request['tools']])

    def test_factory_selects_native_runtime(self):
        runtime = create_case_agent_runtime(runtime_backend="deepseek-harness", enabled=False,
                                             database_url="sqlite+aiosqlite:///:memory:")
        self.assertIsInstance(runtime, CaseAgentRuntime)
        self.assertEqual(runtime.status()["agent_runtime_backend"], "deepseek-harness")
        with self.assertRaises(ValueError):
            create_case_agent_runtime(runtime_backend="unknown", enabled=False, database_url="")
        with self.assertRaises(ValueError):
            create_case_agent_runtime(runtime_backend="langgraph", enabled=False, database_url="")

    def test_latest_sdk_and_runtime_match(self):
        self.assertEqual(readiness(), {"ready": True, "error": "", "version": "0.2.1rc2"})

    def test_workspace_and_conversation_isolation(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(settings, "deepseek_harness_root", temporary):
            values = [workspace_paths(*args) for args in [("one", "personal", "same"),
                ("two", "personal", "same"), ("one", "case:1", "same"), ("one", "case:1", "other")]]
            self.assertEqual(len({item[0] for item in values}), 4)
            self.assertNotEqual(values[0][1], values[1][1])
            self.assertEqual(values[2][1], values[3][1])
            self.assertNotEqual(values[2][2], values[3][2])
            self.assertNotEqual(CaseAgentRuntime.thread_id(1, "one", 1, 2),
                                CaseAgentRuntime.thread_id(1, "one", 1, 3))

    def test_lease_released_on_exception(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "active.lock"
            with self.assertRaisesRegex(ValueError, "probe"):
                with session_lease(target):
                    with self.assertRaises(HTTPException):
                        with session_lease(target):
                            self.fail("重复占用会话锁")
                    raise ValueError("probe")
            with session_lease(target):
                self.assertTrue(target.exists())

    def test_business_credentials_not_inherited(self):
        with patch.dict(os.environ, {"DATABASE_URL": "private-db", "OSS_SECRET_ACCESS_KEY": "private-oss"}):
            environment = _environment()
        self.assertEqual(environment["DATABASE_URL"], "")
        self.assertEqual(environment["OSS_SECRET_ACCESS_KEY"], "")

    def test_resume_uses_fresh_context_and_last_message(self):
        parts = _content([{"role": "system", "content": "最新权限"}, {"role": "user", "content": "旧问题"},
                          {"role": "assistant", "content": "旧回答"}, {"role": "user", "content": "本轮问题"}], resumed=True)
        self.assertEqual(len(parts), 2)
        self.assertIn("最新权限", parts[0]["text"])
        self.assertIn("本轮问题", parts[1]["text"])

    async def test_native_tools_stream_and_durable_resume(self):
        requests, chunks = [], []
        tools = AsyncMock()
        tools.execute.return_value = {"verified": True}
        schema = [{"type": "function", "function": {"name": "metadata_probe", "description": "隔离协议核验",
                  "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}}]
        skill = replace(GENERAL_SKILL, id="isolated-skill", name="隔离技能", instruction="原生技能中文正文核验标记")
        with isolated_home() as temporary:
            async with model_server(requests) as url:
                with patch.object(settings, "deepseek_harness_root", temporary), patch.object(settings, "langgraph_api_base_url", url), patch.object(settings, "langgraph_api_key", "private-model-key-isolated"), patch.object(settings, "langgraph_model", "oa-probe"), patch("app.harness_agent.runtime.definitions", AsyncMock(return_value=[skill])):
                    async def on_delta(value):
                        chunks.append(value)
                    for text, mode in (("调用已注册的核验工具", "fast"), ("继续", "deep")):
                        result = await run([{"role": "user", "content": text}], on_delta, tools=tools, schema=schema,
                                           identity={"username": "isolated-probe"}, db=None, workspace="personal", conversation="probe",
                                           mode_supported=True, response_mode=mode)
                        self.assertEqual(result, "核验完成")
                    import zstandard
                    for file in Path("\\\\?\\" + temporary if os.name == "nt" else temporary).rglob("*"):
                        if file.is_file():
                            data = file.read_bytes()
                            if file.suffix == ".zstd":
                                with zstandard.ZstdDecompressor().stream_reader(data) as stream:
                                    data = stream.read()
                            self.assertNotIn(b"private-model-key-isolated", data)
        tools.execute.assert_awaited_once_with("metadata_probe", {})
        self.assertEqual("".join(chunks), "核验完成核验完成")
        names = {item["function"]["name"] for item in requests[0]["tools"]}
        self.assertEqual(names, {"skill", "mcp__oa__metadata_probe", "mcp__oa__harness_read_skill_resource"})
        self.assertIn("原生技能中文正文核验标记", json.dumps(requests[1]["messages"], ensure_ascii=False))
        self.assertEqual(len(requests), 4)
        self.assertEqual(requests[0].get("thinking"), {"type": "disabled"})
        self.assertEqual(requests[3].get("thinking"), {"type": "enabled"})
        self.assertGreater(len(requests[3]["messages"]), len(requests[2]["messages"]))


if __name__ == "__main__":
    unittest.main()
