"""智能体运行时常驻：同一会话复用，配置变了/别的进程跑过/出错就重建，空闲或超量时关停。"""
import json
import sys
import tempfile
import types
import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.harness_agent import runtime


class FakeSession:
    def __init__(self, owner):
        self.owner, self.runs = owner, []

    def get_working_directory(self):
        return "."

    def run(self, content, on_notification=None):
        self.runs.append(content)
        if self.owner.fail:
            return SimpleNamespace(finish_reason="error", final_response="", events=[])
        return SimpleNamespace(finish_reason="completed", final_response=f"回答{len(self.runs)}", events=[])


class FakeHarness:
    instances = []
    fail = False

    def __init__(self, **kwargs):
        self.kwargs, self.sessions, self.closed = kwargs, [], False
        FakeHarness.instances.append(self)

    def start_session(self, identifier):
        self.sessions.append(("start", identifier))
        return FakeSession(self)

    def resume_session(self, identifier):
        self.sessions.append(("resume", identifier))
        return FakeSession(self)

    def close(self):
        self.closed = True


@asynccontextmanager
async def fake_mcp(tools, schemas, context_provider=None):
    yield "http://127.0.0.1:1/mcp", "secret"


class ResidentRuntimeTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        FakeHarness.instances, FakeHarness.fail = [], False
        runtime._RESIDENTS.clear()
        self.root = Path(tempfile.mkdtemp())
        self.home, self.cwd = self.root / "u" / "sessions" / "s", self.root / "cwd"
        self.home.mkdir(parents=True)
        self.cwd.mkdir()
        module = types.ModuleType("deepseek_harness")
        module.DeepSeekHarness = FakeHarness
        errors = types.ModuleType("deepseek_harness.errors")
        errors.HarnessError = type("HarnessError", (Exception,), {})
        self.modules = patch.dict(sys.modules, {"deepseek_harness": module, "deepseek_harness.errors": errors})
        self.modules.start()

        async def definitions(identity, db):
            return []

        self.patches = [
            patch.object(runtime, "definitions", definitions), patch.object(runtime, "publish", lambda *a, **k: {}),
            patch.object(runtime, "WorkspaceTools", lambda tools, identity, db, progress: SimpleNamespace(tools=tools)),
            patch.object(runtime, "workspace_mcp", fake_mcp), patch.object(runtime, "_environment", lambda: {}),
            patch("app.harness_agent.memory.configuration", lambda cwd, owner: None),
            patch("app.harness_agent.plugins.attach", lambda home: "sdk"),
            patch.object(runtime.settings, "agent_resident_idle_seconds", 600),
            patch.object(runtime.settings, "agent_resident_max_sessions", 2),
        ]
        for item in self.patches:
            item.start()

    async def asyncTearDown(self):
        if runtime._REAPER is not None:
            runtime._REAPER.cancel()
            runtime._REAPER = None
        await runtime.close_all_residents()
        for item in self.patches:
            item.stop()
        self.modules.stop()

    async def turn(self, text, *, schema=None, identifier="oa-s", home=None):
        schema = schema or [{"function": {"name": "oa_call_tool", "parameters": {"type": "object"}}}]
        messages = [{"role": "system", "content": "系统"}, {"role": "user", "content": "旧问题"}, {"role": "user", "content": text}]
        return await runtime._run_session(
            messages, self._delta, tools=object(), schema=schema, identity={"username": "u1"}, db=None, identifier=identifier,
            cwd=self.cwd, home=home or self.home, response_mode="fast", mode_supported=False, on_progress=None)

    async def _delta(self, text):
        pass

    async def test_second_turn_reuses_the_running_runtime_and_sends_only_the_new_message(self):
        self.assertEqual(await self.turn("第一问"), "回答1")
        self.assertEqual(await self.turn("第二问"), "回答2")
        self.assertEqual(len(FakeHarness.instances), 1)  # 只启动一次
        harness = FakeHarness.instances[0]
        self.assertEqual(harness.sessions, [("start", "oa-s")])
        first, second = [json.dumps(run, ensure_ascii=False) for run in harness.sessions and
                         runtime._RESIDENTS["oa-s"].session.runs]
        self.assertIn("旧问题", first)  # 首轮发送完整消息
        self.assertNotIn("旧问题", second)  # 之后只发系统提示和最新一条
        self.assertIn("第二问", second)
        self.assertFalse(harness.closed)
        self.assertIsNone(runtime._RESIDENTS["oa-s"].holder["tools"])  # 轮间不持有请求上下文

    async def test_changed_tool_configuration_restarts_the_runtime(self):
        await self.turn("一")
        other = [{"function": {"name": "oa_call_tool", "parameters": {"type": "object", "x": 1}}}]
        await self.turn("二", schema=other)
        self.assertEqual(len(FakeHarness.instances), 2)
        self.assertTrue(FakeHarness.instances[0].closed)

    async def test_a_turn_run_by_another_process_invalidates_the_resident_copy(self):
        await self.turn("一")
        (self.home / "oa-resident-turn.json").write_text(json.dumps({"owner": "别的进程", "turns": 3}))
        await self.turn("二")
        self.assertEqual(len(FakeHarness.instances), 2)
        self.assertTrue(FakeHarness.instances[0].closed)
        self.assertEqual(FakeHarness.instances[1].sessions, [("resume", "oa-s")])  # 从磁盘历史恢复

    async def test_failed_turn_discards_the_resident_and_next_turn_starts_fresh(self):
        await self.turn("一")
        FakeHarness.fail = True
        with self.assertRaises(HTTPException):
            await self.turn("二")
        self.assertNotIn("oa-s", runtime._RESIDENTS)
        self.assertTrue(FakeHarness.instances[0].closed)
        FakeHarness.fail = False
        await self.turn("三")
        self.assertEqual(len(FakeHarness.instances), 2)

    async def test_disabled_or_over_capacity_does_not_keep_runtimes(self):
        with patch.object(runtime.settings, "agent_resident_idle_seconds", 0):
            await self.turn("一")
        self.assertFalse(runtime._RESIDENTS)
        self.assertTrue(FakeHarness.instances[0].closed)
        homes = []
        for index in range(3):
            home = self.root / f"h{index}"
            home.mkdir()
            homes.append(home)
            await self.turn("问", identifier=f"oa-{index}", home=home)
            runtime._RESIDENTS[f"oa-{index}"].last_used = index  # 按先后确定最久未用
        self.assertEqual(sorted(runtime._RESIDENTS), ["oa-1", "oa-2"])  # 上限 2，最久未用的 oa-0 被关停
        self.assertTrue(FakeHarness.instances[1].closed)

    async def test_idle_resident_is_closed_by_the_reaper_and_busy_ones_are_not(self):
        await self.turn("一")
        resident = runtime._RESIDENTS["oa-s"]
        resident.last_used -= 10_000
        with patch.object(runtime.settings, "agent_resident_idle_seconds", 60):
            sleeps = []

            async def quick(seconds):
                sleeps.append(seconds)

            with patch.object(runtime.asyncio, "sleep", quick):
                await runtime._reap_idle()
        self.assertNotIn("oa-s", runtime._RESIDENTS)
        self.assertTrue(FakeHarness.instances[0].closed)
        self.assertEqual(sleeps[0], 30)  # 每 30 秒检查一次


if __name__ == "__main__":
    unittest.main()
