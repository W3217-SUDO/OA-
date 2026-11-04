"""陶国南 11-05：改、填案件信息一次出确认卡片；改案件信息时不带整个案件空间；等待时显示实际步骤。只用假接口。"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.agent_mcp import business_tools
from app.case_agent import CASE_INFO_EDIT_RULES, is_case_info_edit_request, slim_case_snapshot
from app.harness_agent.tool_trace import describe
from app.main import app


def _context():
    return SimpleNamespace(application=app, readonly=False, groups=None, write_allowed=True, username="u")


class CaseUpdateInfoToolTest(unittest.IsolatedAsyncioTestCase):
    async def _plan(self, arguments):
        calls = []

        async def fake_call(name, args):
            calls.append((name, args))
            if name == "oa_get_record_get":
                return {"id": 108416, "serial_no": "HZMS2500902", "title": "甲__乙", "data": {"litigation_amount": 80000, "settlement_amount": None}}
            return {"ok": True}

        with patch.object(business_tools, "get_auth_context", return_value=_context()):
            result = await business_tools.run_business_tool("biz_case_update_info", arguments, call=fake_call)
        return result, calls

    async def test_judgment_amount_keeps_litigation_amount_and_plans_one_write(self):
        result, calls = await self._plan({"case_id": 108416, "judgment_amount": 50000})
        self.assertEqual(result["mode"], "计划")
        writes = [step for step in result["steps"] if step["kind"] == "写"]
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0]["tool"], "oa_update_case_settlement_amount_put")
        self.assertEqual(writes[0]["arguments"]["body"]["litigation_amount"], 80000.0, "没改的诉讼标的保持原值")
        self.assertEqual(writes[0]["arguments"]["body"]["settlement_amount"], 50000)
        self.assertEqual([name for name, _ in calls], ["oa_get_record_get"], "计划阶段只读案件，不调写接口")

    async def test_court_lawyer_phase_in_one_call(self):
        result, _ = await self._plan({"case_id": 108416, "court": {"court": "上海知识产权法院", "court_case_no": "(2026)沪73民初1号", "judgment_date": "2026-11-01"},
                                      "hearing_lawyers": ["曹志刚"], "case_phase_name": "一审已判决"})
        tools = [step["tool"] for step in result["steps"] if step["kind"] == "写"]
        self.assertEqual(tools, ["oa_update_case_court_info_put", "oa_update_case_hearing_lawyer_put", "oa_update_case_phase_post"])
        court = next(step for step in result["steps"] if step["tool"] == "oa_update_case_court_info_put")["arguments"]["body"]
        self.assertEqual((court["first_court_name"], court["first_court_case_no"], court["first_court_judgment_date"]),
                         ("上海知识产权法院", "(2026)沪73民初1号", "2026-11-01"))

    async def test_nothing_to_change_is_rejected(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as caught:
            await self._plan({"case_id": 108416})
        self.assertEqual(caught.exception.status_code, 422)


class EditRequestSlimContextTest(unittest.TestCase):
    def test_edit_requests_detected(self):
        for text in ("判决金额改成5万元", "把诉讼标的填写为 8 万", "开庭律师改为曹志刚", "案件阶段变更为一审已判决", "录入一审案号（2026）沪73民初1号"):
            self.assertTrue(is_case_info_edit_request(text), text)
        for text in ("归纳案件情况", "根据判决书填写判决金额", "起草答辩状", "分析这个案件的风险", "法院在哪里"):
            self.assertFalse(is_case_info_edit_request(text), text)

    def test_slim_snapshot_keeps_only_basic_info(self):
        full = {"schema_version": "1.1", "space": {"case_id": 1}, "case": {"id": 1}, "people": [], "capabilities": {"can_write": True},
                "finances": {"fees": [1] * 50}, "documents": [1] * 200, "tasks": [1] * 20, "relationships": {}, "case_check": {}, "agent": {}}
        slim = slim_case_snapshot(full)
        self.assertEqual(set(slim) - {"scope_note"}, {"schema_version", "space", "case", "people", "capabilities"})

    def test_rule_points_to_the_direct_tool(self):
        self.assertIn("biz_case_update_info", CASE_INFO_EDIT_RULES)

    def test_progress_label_is_chinese(self):
        self.assertEqual(describe("biz_case_update_info", {})[0], "修改案件信息")


if __name__ == "__main__":
    unittest.main()
