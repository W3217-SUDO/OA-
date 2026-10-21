"""智能体工具调用记录（前端可见）与管理员沙箱运行代码。"""
import base64
import hashlib
import json
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.harness_agent import script_runtime, tool_trace
from app.harness_agent.skills import CODE_TOOL, WorkspaceTools, sandbox_allowed

ADMIN = {"username": "admin", "_actual_role_ids": ["admin"]}
STAFF = {"username": "u1", "_actual_role_ids": ["user"]}


class FakeDelegate:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, []

    async def execute(self, name, arguments):
        self.calls.append((name, arguments))
        if self.error:
            raise self.error
        return self.result


class ToolTraceTest(unittest.IsolatedAsyncioTestCase):
    async def test_every_tool_call_is_announced_and_recorded_with_name_arguments_and_status(self):
        trace, progress = tool_trace.begin(), []

        async def on_progress(text):
            progress.append(text)

        tools = WorkspaceTools(FakeDelegate({"items": []}), STAFF, None, on_progress)
        await tools.execute("oa_call_tool", {"name": "list_customers", "arguments": {"customer_name": "张三", "api_token": "abc"}})
        self.assertEqual(len(trace), 1)
        entry = trace[0]
        self.assertIn("list_customers", entry["label"])  # 显示实际调用的业务工具，而不是外层 oa_call_tool
        self.assertIn("张三", entry["detail"])
        self.assertNotIn("abc", entry["detail"])  # 密钥类参数不显示
        self.assertTrue(entry["ok"])
        self.assertTrue(progress[0].startswith("正在调用："))

    async def test_failed_calls_are_recorded_as_failed_and_still_raise(self):
        trace = tool_trace.begin()
        tools = WorkspaceTools(FakeDelegate(error=HTTPException(422, "缺少必填参数")), STAFF, None)
        with self.assertRaises(HTTPException):
            await tools.execute("oa_search_tools", {"query": "客户"})
        self.assertEqual([(item["label"], item["ok"]) for item in trace], [("搜索业务工具", False)])
        tools = WorkspaceTools(FakeDelegate({"isError": True}), STAFF, None)
        await tools.execute("oa_list_tool_groups", {})
        self.assertFalse(trace[-1]["ok"])  # 工具自己返回 isError 也算失败

    async def test_no_active_trace_is_harmless_and_long_details_are_truncated(self):
        tool_trace._TRACE.set(None)
        await WorkspaceTools(FakeDelegate({}), STAFF, None).execute("oa_search_tools", {})
        label, detail = tool_trace.describe("oa_call_tool", {"name": "x", "arguments": {"text": "字" * 500, "items": list(range(20))}})
        self.assertLessEqual(len(detail), 241)

    def test_native_tool_names_are_found_in_event_shapes_and_oa_tools_are_not_duplicated(self):
        self.assertEqual(tool_trace.native_call_name({"data": {"name": "archify"}}), "archify")
        self.assertEqual(tool_trace.native_call_name({"toolName": "skill"}), "skill")
        self.assertEqual(tool_trace.native_call_name({"type": "tool/call"}), "")
        trace = tool_trace.begin()
        tool_trace.record_native("mcp__oa__oa_call_tool")
        tool_trace.record_native("archify")
        self.assertEqual([item["name"] for item in trace], ["archify"])


class SandboxTest(unittest.IsolatedAsyncioTestCase):
    def test_only_system_admins_get_the_sandbox_tool(self):
        self.assertTrue(sandbox_allowed(ADMIN))
        self.assertFalse(sandbox_allowed(STAFF))
        self.assertEqual(CODE_TOOL["function"]["name"], "harness_run_code")

    async def test_non_admin_cannot_run_code(self):
        with self.assertRaises(HTTPException) as caught:
            await WorkspaceTools(FakeDelegate(), STAFF, None).execute("harness_run_code", {"language": "python", "code": "print(1)"})
        self.assertEqual(caught.exception.status_code, 403)

    async def test_admin_code_is_sent_to_the_isolated_runner_as_a_single_file_package(self):
        sent = {}

        async def submit(endpoint, payload):
            sent["endpoint"], sent["payload"] = endpoint, json.loads(payload)
            return {"exit_code": 0, "stdout": "42\n", "stderr": "", "isError": False}

        trace = tool_trace.begin()
        with patch.object(script_runtime, "_submit", submit), patch.object(script_runtime, "_socket_path", lambda: "/run/x.sock"):
            result = await WorkspaceTools(FakeDelegate(), ADMIN, None).execute(
                "harness_run_code", {"language": "python", "code": "print(6*7)", "args": ["a"]})
        payload = sent["payload"]
        data = b"print(6*7)"
        self.assertEqual((payload["method"], payload["path"], payload["args"]), ("run", "main.py", ["a"]))
        self.assertEqual(base64.b64decode(payload["files"]["main.py"]), data)
        self.assertEqual(payload["manifest"], {"main.py": hashlib.sha256(data).hexdigest()})  # 摘要与内容一致，broker 才会放行
        self.assertEqual((result["sandbox"], result["stdout"]), ("python", "42\n"))
        self.assertTrue(trace[0]["label"].startswith("沙箱运行代码（python）"))

    async def test_invalid_requests_are_rejected_before_reaching_the_runner(self):
        for arguments in ({"language": "ruby", "code": "x"}, {"language": "python", "code": "  "},
                          {"language": "python", "code": "x" * 200_001}, {"language": "python", "code": "x", "args": ["a"] * 33},
                          {"language": "python", "code": "x", "extra": 1}):
            with self.subTest(arguments=str(arguments)[:40]):
                with self.assertRaises(HTTPException) as caught:
                    await WorkspaceTools(FakeDelegate(), ADMIN, None).execute("harness_run_code", arguments)
                self.assertEqual(caught.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
