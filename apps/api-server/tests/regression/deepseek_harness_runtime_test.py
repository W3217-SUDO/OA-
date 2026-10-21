"""原生 SDK 边界与协议回归；验证数据、模拟模型及文件仅存在隔离测试目录。"""
import asyncio
from dataclasses import replace
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import socket
import shutil
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from starlette.requests import Request

from app.case_agent import CaseAgentRuntime
from app.deepseek_harness import create_case_agent_runtime
from app.harness_agent.bridge import _Server, workspace_mcp
from app.harness_agent.lease import session_lease
from app.harness_agent.runtime import _content, _environment, close_all_residents, readiness, run, workspace_paths
from app.config import settings
from app.agent_skills import GENERAL_SKILL
from app.harness_agent.skills import SCRIPT_TOOL, WorkspaceTools, native_name
from app.harness_agent.script_runtime import run_script, runtime_status
from app.harness_agent.script_container import _container_command, execute as execute_script, relative_path as _relative
from app.harness_agent.script_broker import Broker, unpack
from app.harness_agent.script_network import LABEL, check_firewall, network_rules
import uvicorn


@asynccontextmanager
async def isolated_home():
    with tempfile.TemporaryDirectory(prefix="oa-harness-test-") as temporary:
        try:
            yield temporary
        finally:
            # 常驻实例持有文件锁；先完成运行时关闭，再清理本次隔离目录。
            await close_all_residents()
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
    def test_response_modes_only_enable_verified_official_models(self):
        from app.areas.personal_agent.response_runtime import supports_response_modes

        cases = (
            ("https://api.deepseek.com", "deepseek-flash", True),
            ("https://api.deepseek.com/v1", "deepseek-flash", True),
            ("https://api.deepseek.com", "unknown-model", False),
            ("https://api.deepseek.com.example.org", "deepseek-flash", False),
            ("https://ark.cn-beijing.volces.com/api/v3", "ark-code-latest", True),
            ("https://compatible.example.org/v1", "deepseek-flash", False),
        )
        for base_url, model, expected in cases:
            with self.subTest(base_url=base_url, model=model), patch.object(settings, "langgraph_api_base_url", base_url), patch.object(settings, "langgraph_model", model):
                self.assertEqual(supports_response_modes(), expected)

    def test_script_status_keeps_network_and_missing_runtime_explicit(self):
        self.assertTrue(runtime_status(None, "整理摘要")["ready"])
        with patch("app.harness_agent.script_runtime.sys.platform", "win32"):
            state = runtime_status({"files": {"scripts/query.mjs": "digest"}}, "查询 12306")
        self.assertFalse(state["ready"])
        self.assertIn("linux-skill-runner-service", state["missing_dependencies"])
        self.assertFalse(runtime_status(None, "```bash\nnpx tool\n```")["ready"])

    def test_script_paths_and_sandbox_do_not_expose_host_workspace(self):
        for path in ("../secret.py", "/etc/passwd", "C:\\secret.py", "a/../../b.py", "x\0.py"):
            with self.subTest(path=path), self.assertRaises(HTTPException):
                _relative(path)
        command = _container_command("runner@sha256:" + "a" * 64, "oa-test-network", Path("/isolated/verified-bundle"),
                                     Path("scripts/query.mjs"), ["a;whoami", "$(env)"], "oa-skill-isolated")
        self.assertIn("--read-only", command)
        self.assertIn("--cap-drop=ALL", command)
        self.assertIn("--security-opt=no-new-privileges", command)
        self.assertIn("--pids-limit=64", command)
        self.assertNotIn("--privileged", command)
        self.assertNotIn("/etc", " ".join(command))
        self.assertNotIn("/var/run/docker.sock", " ".join(command))
        self.assertEqual(command[-2:], ["a;whoami", "$(env)"])

    async def test_script_tool_rechecks_current_authorization_and_reports_result(self):
        skill = replace(GENERAL_SKILL, id="script-skill", name="隔离脚本",
                        bundle={"id": "a" * 64, "files": {"scripts/query.mjs": "b" * 64}})
        progress = AsyncMock()
        tools = WorkspaceTools(AsyncMock(), {"username": "owner-one"}, None, progress)
        arguments = {"name": native_name(skill.id), "path": "scripts/query.mjs", "args": []}
        with patch("app.harness_agent.skills.definitions", AsyncMock(return_value=[skill])) as available, \
             patch("app.harness_agent.script_runtime.run_script", AsyncMock(return_value={"isError": True, "exit_code": 7})) as execute:
            result = await tools.execute("harness_run_skill_script", arguments)
            self.assertTrue(result["isError"])
            available.assert_awaited_once_with({"username": "owner-one"}, None)
            execute.assert_awaited_once_with(skill, "scripts/query.mjs", [])
        with patch("app.harness_agent.skills.definitions", AsyncMock(return_value=[])), \
             patch("app.harness_agent.script_runtime.run_script", AsyncMock()) as execute:
            with self.assertRaises(HTTPException) as failure:
                await tools.execute("harness_run_skill_script", arguments)
            self.assertEqual(failure.exception.status_code, 404)
            execute.assert_not_awaited()
        with patch("app.harness_agent.skills.definitions", AsyncMock(return_value=[skill])), \
             patch("app.harness_agent.script_runtime.run_script", AsyncMock(side_effect=HTTPException(503, "隔离服务未就绪"))):
            with self.assertRaises(HTTPException) as failure:
                await tools.execute("harness_run_skill_script", arguments)
            self.assertEqual(failure.exception.status_code, 503)
            progress.assert_awaited_with("技能执行失败：隔离脚本")

    async def test_script_execution_fails_before_start_for_unavailable_sandbox(self):
        skill = replace(GENERAL_SKILL, bundle={"files": {"scripts/query.py": "digest"}})
        with patch("app.harness_agent.script_runtime.sys.platform", "win32"), \
             patch("asyncio.create_subprocess_exec", AsyncMock()) as start:
            with self.assertRaises(HTTPException) as failure:
                await run_script(skill, "scripts/query.py", [])
            self.assertEqual(failure.exception.status_code, 503)
            start.assert_not_awaited()

    def test_broker_validates_bytes_and_rejects_host_configuration(self):
        import base64
        import hashlib
        self.assertEqual(Broker('sha256:' + 'a' * 64, 'oa-test-network', 1000).image, 'sha256:' + 'a' * 64)
        with self.assertRaises(ValueError):
            Broker('runner:latest', 'oa-test-network', 1000)
        data = b"print('isolated')"
        payload = {"method": "run", "path": "scripts/check.py", "args": [],
                   "files": {"scripts/check.py": base64.b64encode(data).decode()},
                   "manifest": {"scripts/check.py": hashlib.sha256(data).hexdigest()}}
        self.assertEqual(unpack(payload), {"scripts/check.py": data})
        with self.assertRaises(HTTPException):
            unpack({**payload, "image": "untrusted", "mount": "/"})
        payload["manifest"]["scripts/check.py"] = "a" * 64
        with self.assertRaises(HTTPException) as failure:
            unpack(payload)
        self.assertEqual(failure.exception.status_code, 409)

    async def test_broker_rejects_other_uid_and_busy_before_reading_large_body(self):
        import struct
        broker = Broker("runner@sha256:" + "a" * 64, "oa-test-network", 1234)
        peer = Mock()
        writer = Mock()
        writer.get_extra_info.return_value = peer
        reader = AsyncMock()
        with patch("app.harness_agent.script_broker.socket.SO_PEERCRED", 17, create=True):
            peer.getsockopt.return_value = struct.pack("3i", 1, 999, 999)
            result = await broker.invoke(reader, writer)
            self.assertEqual(result["status"], 403)
            reader.readexactly.assert_not_awaited()
            peer.getsockopt.return_value = struct.pack("3i", 1, 1234, 1234)
            broker.active = 2
            result = await broker.invoke(reader, writer)
            self.assertEqual(result["status"], 429)
            reader.readexactly.assert_not_awaited()
            self.assertEqual(broker.active, 2)

    async def test_script_container_timeout_and_cancel_remove_owned_container(self):
        for mode in ("timeout", "cancel"):
            with self.subTest(mode=mode):
                removed, calls = False, []
                started = asyncio.Event()
                stdout, stderr = asyncio.StreamReader(), asyncio.StreamReader()
                process = Mock(stdout=stdout, stderr=stderr, pid=123456789, returncode=None)
                process.wait = AsyncMock(return_value=0)

                async def start(*args, **kwargs):
                    started.set()
                    return process

                def read(command):
                    nonlocal removed
                    calls.append(command)
                    if command[1] == "create":
                        return "c" * 64
                    if command[1] == "ps":
                        return "" if removed else "c" * 12
                    if command[1] == "rm":
                        removed = True
                        return "removed"
                    raise AssertionError(command)

                with patch("app.harness_agent.script_container.verify_runtime"), \
                     patch("app.harness_agent.script_container._read", side_effect=read), \
                     patch("app.harness_agent.script_container._TIMEOUT", 0.03 if mode == "timeout" else 10), \
                     patch("asyncio.create_subprocess_exec", side_effect=start), \
                     patch("app.harness_agent.script_container.signal.SIGKILL", 9, create=True), \
                     patch("app.harness_agent.script_container.os.killpg", create=True):
                    task = asyncio.create_task(execute_script({"check.py": b"print('ok')"}, "check.py", [], "image", "network"))
                    await started.wait()
                    if mode == "cancel":
                        task.cancel()
                        with self.assertRaises(asyncio.CancelledError):
                            await task
                    else:
                        with self.assertRaises(HTTPException) as failure:
                            await task
                        self.assertEqual(failure.exception.status_code, 504)
                self.assertTrue(removed)
                removal = next(command for command in calls if command[1] == "rm")
                self.assertTrue(removal[-1].startswith("oa-skill-"))
                self.assertNotIn("--all", removal)

    async def test_script_cancel_notification_reaches_running_tool(self):
        import httpx
        started, cancelled = asyncio.Event(), asyncio.Event()

        async def execute(name, arguments):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        tools = Mock(execute=execute)
        async with workspace_mcp(tools, [SCRIPT_TOOL]) as (url, secret), httpx.AsyncClient(trust_env=False) as client:
            headers = {"Authorization": "Bearer " + secret}
            call = asyncio.create_task(client.post(url, headers=headers, json={"jsonrpc": "2.0", "id": "owned",
                "method": "tools/call", "params": {"name": "harness_run_skill_script", "arguments": {}}}))
            await asyncio.wait_for(started.wait(), 3)
            notice = await client.post(url, headers=headers, json={"jsonrpc": "2.0", "method": "notifications/cancelled",
                                                                  "params": {"requestId": "owned"}})
            self.assertEqual(notice.status_code, 202)
            response = await asyncio.wait_for(call, 3)
            self.assertEqual(response.json()["error"]["code"], -32800)
            self.assertTrue(cancelled.is_set())

    def test_network_policy_rejects_private_destination_and_bypass_rules(self):
        name, subnet = "oa-test-network", "172.29.248.0/28"
        bridge, chain, rules = network_rules(name, subnet)
        network = {"Name": name, "Driver": "bridge", "EnableIPv6": False,
                   "Labels": {LABEL: "public-http-v1"}, "IPAM": {"Config": [{"Subnet": subnet}]},
                   "Options": {"com.docker.network.bridge.name": bridge}}
        values = {chain: "\n".join(" ".join(["-A", chain, *rule]) for rule in rules),
                  "DOCKER-USER": f"-A DOCKER-USER -s {subnet} -j {chain}",
                  "INPUT": f"-A INPUT -i {bridge} -j REJECT"}
        # Ubuntu iptables 的真实输出先列目标地址，再列协议和自动补充的协议模块。
        values[chain] = "\n".join(
            f"-A {chain} -d 1.1.1.1/32 -p udp -m udp --dport 53 -j ACCEPT"
            if "1.1.1.1/32" in line else line for line in values[chain].splitlines())
        check_firewall(name, network, lambda command: values[command[-1]])
        self.assertTrue(any("169.254.0.0/16" in rule for rule in rules))
        values[chain] = f"-A {chain} -j ACCEPT\n" + values[chain]
        with self.assertRaisesRegex(ValueError, "出口规则"):
            check_firewall(name, network, lambda command: values[command[-1]])
        values[chain] = "\n".join(" ".join(["-A", chain, *rule]) for rule in rules)
        values["INPUT"] = "-A INPUT -j ACCEPT\n" + values["INPUT"]
        with self.assertRaisesRegex(ValueError, "首条规则"):
            check_firewall(name, network, lambda command: values[command[-1]])

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

        async with isolated_home() as temporary:
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
        async with isolated_home() as temporary:
            async with model_server(requests) as url:
                with patch.object(settings, "deepseek_harness_root", temporary), patch.object(settings, "langgraph_api_base_url", url), patch.object(settings, "langgraph_api_key", "private-model-key-isolated"), patch.object(settings, "langgraph_model", "oa-probe"), patch("app.harness_agent.runtime.definitions", AsyncMock(return_value=[skill])):
                    async def on_delta(value):
                        chunks.append(value)
                    for text, mode in (("调用已注册的核验工具", "fast"), ("继续", "deep")):
                        result = await run([{"role": "user", "content": text}], on_delta, tools=tools, schema=schema,
                                           identity={"username": "isolated-probe"}, db=None, workspace="personal", conversation="probe",
                                           mode_supported=True, response_mode=mode)
                        self.assertEqual(result, "核验完成")
                    # 先完成持久化并释放文件锁，再审计全部落盘内容。
                    await close_all_residents()
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
        self.assertEqual(names, {"skill", "mcp__oa__metadata_probe", "mcp__oa__harness_read_skill_resource", "mcp__oa__harness_run_skill_script"})
        self.assertIn("原生技能中文正文核验标记", json.dumps(requests[1]["messages"], ensure_ascii=False))
        self.assertEqual(len(requests), 4)
        self.assertEqual(requests[0].get("thinking"), {"type": "disabled"})
        self.assertEqual(requests[3].get("thinking"), {"type": "enabled"})
        self.assertGreater(len(requests[3]["messages"]), len(requests[2]["messages"]))


if __name__ == "__main__":
    unittest.main()
