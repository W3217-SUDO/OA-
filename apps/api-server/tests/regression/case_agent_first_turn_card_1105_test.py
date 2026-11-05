"""陶国南 11-05 07:44/07:48：默认不带整个案件空间；改案件信息第一轮直接出卡片（写明从多少改成多少）；卡片一生成就推给页面；进度不显示英文名。只用假接口。"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.agent_mcp import business_tools, model_tools
from app.case_agent import CASE_INFO_EDIT_RULES, is_full_space_request, slim_case_snapshot
from app.harness_agent.runtime import oa_persona
from app.harness_agent.tool_trace import describe
from app.main import app


def _context():
    return SimpleNamespace(application=app, readonly=False, groups=None, write_allowed=True, username="u")


class FirstTurnCardTest(unittest.IsolatedAsyncioTestCase):
    async def test_plan_lists_before_and_after(self):
        async def fake_call(name, args):
            return {"id": 1, "serial_no": "HZMS1", "data": {"settlement_amount": 50000, "litigation_amount": 80000, "first_court_name": "",
                                                           "hearing_lawyer": "张三", "execution_status": "未开始"}}

        with patch.object(business_tools, "get_auth_context", return_value=_context()):
            result = await business_tools.run_business_tool("biz_case_update_info", {
                "case_id": 1, "judgment_amount": 60000, "court": {"court": "上海知识产权法院"}, "hearing_lawyers": ["李四"],
                "execution_status": "执行中"}, call=fake_call)
        self.assertEqual(result["changes"], ["判决/调解金额（元）：50000 → 60000", "一审法院：未填写 → 上海知识产权法院",
                                             "开庭律师：张三 → 李四", "执行状态：未开始 → 执行中"])

    async def test_card_shows_changes_as_current_info(self):
        from app.agent_mcp import service
        captured = {}

        async def fake_create(identity, db, **kwargs):
            captured.update(kwargs)
            return {"status": "pending", "request_id": "r1", "summary": "s", "preview": kwargs["preview"]}

        class FakeDb:
            async def __aenter__(self):
                return None

            async def __aexit__(self, *exc):
                return False

        tool = business_tools.TOOLS["biz_case_update_info"]
        plan = {"steps": [{"step": 1, "purpose": "修改诉讼标的/判决金额", "kind": "写"}], "changes": ["判决/调解金额（元）：50000 → 60000"]}

        async def fake_identity():
            return {"username": "u"}

        with patch.object(service, "authenticated_identity", fake_identity), patch.object(service, "SessionLocal", FakeDb), \
                patch.object(service, "_create_pending_request", fake_create), patch.object(service, "trusted_case_origin", lambda: None):
            await service.prepare_business_request(tool, {"case_id": 1, "judgment_amount": 60000}, plan)
        self.assertEqual(captured["preview"]["original_values"], "判决/调解金额（元）：50000 → 60000")

    def test_rules_say_confirm_true_on_first_call(self):
        self.assertIn("第一次就带 confirm=true", CASE_INFO_EDIT_RULES)
        self.assertNotIn("先不带 confirm 拿执行计划，用户同意后", CASE_INFO_EDIT_RULES)
        self.assertIn("第一次就带 confirm=true", oa_persona())
        self.assertIn("第一次直接带 confirm=true", business_tools.TOOLS["biz_case_update_info"].description)


class PendingCardPushTest(unittest.IsolatedAsyncioTestCase):
    async def test_business_card_is_announced_when_created(self):
        seen = []

        async def fake_run(name, arguments, **kwargs):
            return {"status": "pending", "request_id": "req-1", "summary": "修改案件信息", "preview": {"operation_name": "修改案件信息"}}

        token = model_tools.PENDING_ACTION_SINK.set(seen.append)
        try:
            with patch.object(model_tools, "run_business_tool", fake_run):
                await model_tools.ModelToolSession()._execute("biz_case_update_info", {"case_id": 1, "judgment_amount": 1, "confirm": True})
        finally:
            model_tools.PENDING_ACTION_SINK.reset(token)
        self.assertEqual([item["payload"]["request_id"] for item in seen], ["req-1"])

    async def test_sink_failure_does_not_break_turn(self):
        def broken(_):
            raise RuntimeError("x")

        async def fake_run(name, arguments, **kwargs):
            return {"status": "pending", "request_id": "req-2", "summary": "s", "preview": {}}

        token = model_tools.PENDING_ACTION_SINK.set(broken)
        try:
            with patch.object(model_tools, "run_business_tool", fake_run):
                session = model_tools.ModelToolSession()
                await session._execute("biz_case_update_info", {"case_id": 1, "judgment_amount": 1, "confirm": True})
        finally:
            model_tools.PENDING_ACTION_SINK.reset(token)
        self.assertEqual(len(session.pending_actions), 1)


class DefaultSlimContextTest(unittest.TestCase):
    def test_full_space_only_on_explicit_request(self):
        for text in ("查全部案件空间", "看整个案件再分析", "请全面分析这个案子"):
            self.assertTrue(is_full_space_request(text), text)
        for text in ("这个案件有哪些费用", "判决金额改成8万", "归纳案件情况", "下次开庭是什么时候"):
            self.assertFalse(is_full_space_request(text), text)

    def test_query_keeps_case_check(self):
        full = {"case": {"id": 1}, "case_check": {"items": []}, "documents": [1] * 10}
        self.assertIn("case_check", slim_case_snapshot(full, keep_check=True))
        self.assertNotIn("documents", slim_case_snapshot(full, keep_check=True))
        self.assertIn("全部案件空间", CASE_INFO_EDIT_RULES)


class PromptOnlySlimTest(unittest.TestCase):
    def test_model_prompt_is_slim_but_snapshot_keeps_targets(self):
        from app.case_agent import build_case_model_messages
        snapshot = {"case": {"id": 1, "serial_no": "SHMS1"}, "customer": {"serial_no": "SHKH-SECRET-1"}, "contracts": [{"id": 9, "serial_no": "HT-SECRET-9"}],
                    "document_readings": [{"name": "判决书-已选"}], "case_check": {"items": ["检查项甲"]}, "_model_scope": "basic"}
        text = build_case_model_messages(snapshot, [{"role": "user", "content": "这个案件有哪些费用"}])[0]["content"]
        self.assertNotIn("SHKH-SECRET-1", text)
        self.assertNotIn("HT-SECRET-9", text)
        self.assertIn("判决书-已选", text, "本轮勾选的材料照常给模型")
        self.assertIn("检查项甲", text)
        self.assertNotIn("_model_scope", text)
        edit = build_case_model_messages({**snapshot, "_model_scope": "basic_edit"}, [{"role": "user", "content": "判决金额改成8万"}])[0]["content"]
        self.assertNotIn("检查项甲", edit)
        full = build_case_model_messages({k: v for k, v in snapshot.items() if k != "_model_scope"}, [{"role": "user", "content": "查全部案件空间"}])[0]["content"]
        self.assertIn("HT-SECRET-9", full)


class ChineseOnlyLabelTest(unittest.TestCase):
    def test_call_tool_label_has_no_english_name(self):
        label, _ = describe("oa_call_tool", {"name": "oa_update_case_settlement_amount_put", "arguments": {}})
        self.assertNotIn("oa_", label)
        self.assertEqual(describe("oa_call_tool", {"name": "oa_not_a_real_tool_xyz", "arguments": {}})[0], "调用业务功能")


if __name__ == "__main__":
    unittest.main()
