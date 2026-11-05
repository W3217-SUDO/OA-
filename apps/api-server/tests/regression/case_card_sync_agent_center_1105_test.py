"""调度 11-05：在智能体中心处理掉的确认请求，案件窗口里同一张卡片同步显示结果、不再可点。只用假存储。"""

import unittest
from contextlib import asynccontextmanager

from app.case_agent import CaseAgentRuntime


class FakeStore:
    def __init__(self):
        self.written = []

    @asynccontextmanager
    async def operation(self, thread):
        yield

    async def write(self, thread, values):
        self.written.append(values)


def _runtime(actions):
    runtime = CaseAgentRuntime.__new__(CaseAgentRuntime)
    runtime.store = FakeStore()

    async def ensure(*args, **kwargs):
        return {"messages": [], "pending_actions": actions}

    runtime._ensure_private_state = ensure
    return runtime


def _card(action_id, request_id, status="pending"):
    return {"id": action_id, "type": "mcp.call", "status": status, "summary": "修改案件信息", "payload": {"request_id": request_id}}


class SyncTest(unittest.IsolatedAsyncioTestCase):
    async def test_decided_requests_update_case_cards(self):
        runtime = _runtime([_card("a1", "r1"), _card("a2", "r2"), _card("a3", "r3"), _card("a4", "r4", "rejected")])
        state = await runtime.sync_tool_requests(1, "admin", {
            "r1": {"status": "rejected", "decided_at": "2026-11-05T00:00:00+00:00", "comment": "不改"},
            "r2": {"status": "succeeded", "finished_at": "2026-11-05T00:01:00+00:00", "result": {"ok": True}},
            "r3": {"status": "executing"},
            "r4": {"status": "succeeded"},
        })
        by_id = {item["id"]: item for item in state["pending_actions"]}
        self.assertEqual(by_id["a1"]["status"], "rejected")
        self.assertEqual(by_id["a1"]["decided_via"], "agent_center")
        self.assertEqual(by_id["a2"]["status"], "approved")
        self.assertEqual(by_id["a3"]["status"], "executing")
        self.assertEqual(by_id["a4"]["status"], "rejected", "已决定的卡片不被改写")
        self.assertEqual(len(runtime.store.written), 1)

    async def test_no_change_writes_nothing(self):
        runtime = _runtime([_card("a1", "r1")])
        self.assertIsNone(await runtime.sync_tool_requests(1, "admin", {"r1": {"status": "pending"}}))
        self.assertIsNone(await runtime.sync_tool_requests(1, "admin", {}))
        self.assertEqual(runtime.store.written, [])


if __name__ == "__main__":
    unittest.main()
