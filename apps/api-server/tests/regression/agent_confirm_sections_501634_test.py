"""501634（tgn 11-05 07:22）：确认窗口标题只写动了哪一块；业务工具改案件信息按“原值 → 新值”只列动了的。"""
import pathlib
import unittest

from app.agent_mcp.confirm_sections import confirm_sections

ROOT = pathlib.Path(__file__).resolve().parents[2]


class ConfirmSectionsTest(unittest.TestCase):
    def test_basic_info_and_lawyers(self):
        same = {"field": "title", "before": "a", "before_read": True, "after": "a"}
        cause = {"field": "cause_or_charge", "before": "a", "before_read": True, "after": "b"}
        lawyer = {"field": "handling_lawyers", "before": ["x"], "before_read": True, "after": ["y"]}
        tool = "oa_update_normal_case_basic_put"
        self.assertEqual(confirm_sections(tool, [same, cause]), ["案件基本信息"])
        self.assertEqual(confirm_sections(tool, [same, lawyer]), ["经办律师信息"])
        self.assertEqual(confirm_sections(tool, [cause, lawyer]), ["案件基本信息", "经办律师信息"])

    def test_amount_court_litigants(self):
        amounts = [{"field": "litigation_amount", "before": 1, "before_read": True, "after": 2},
                   {"field": "settlement_amount", "before": 0, "before_read": True, "after": 0}]
        self.assertEqual(confirm_sections("oa_update_case_settlement_amount_put", amounts), ["诉讼标的"])
        self.assertEqual(confirm_sections("oa_update_case_court_info_put", []), ["法院信息"])
        self.assertEqual(confirm_sections("oa_update_case_litigants_put", []), ["当事人"])
        self.assertEqual(confirm_sections("oa_unknown_put", []), [])

    def test_business_tool_passes_rows_and_sections(self):
        tools = (ROOT / "app/agent_mcp/business_tools.py").read_text(encoding="utf-8")
        self.assertIn('"change_rows": change_rows, "sections": sections', tools)
        self.assertIn('args["litigation_amount"], "诉讼标的")', tools)
        service = (ROOT / "app/agent_mcp/service.py").read_text(encoding="utf-8")
        self.assertIn('{"changes": plan["change_rows"]}', service)
        self.assertIn("confirm_sections(spec.name, changes)", service)


    def test_people_shown_as_names(self):
        import asyncio
        from unittest import mock
        from app.agent_mcp import display_labels

        async def names(accounts, db):
            return {"caozg": "曹志刚", "shenjf": "沈建锋", "haoyun": "郝蕴", "baoyulin": "鲍宇琳"}
        with mock.patch.object(display_labels, "_person_names", names):
            rows = asyncio.run(display_labels.humanize_change_rows([
                {"field": "开庭律师", "before": "caozg", "before_read": True, "after": "caozg、shenjf"},
                {"field": "诉讼标的（元）", "before": "30000.0", "before_read": True, "after": "20000"}], None))
            self.assertEqual(rows[0]["after"], "曹志刚、沈建锋")
            self.assertEqual(rows[0]["before"], "曹志刚")
            self.assertEqual(rows[1]["after"], "20000")
            maps = asyncio.run(display_labels.record_display_maps({"body": {"assistant": "haoyun,baoyulin"}}, None))
            self.assertEqual(maps["value_labels"]["assistant"]["haoyun,baoyulin"], "郝蕴、鲍宇琳")
        service = (ROOT / "app/agent_mcp/service.py").read_text(encoding="utf-8")
        self.assertIn("humanize_change_rows(preview[\"changes\"], db)", service)


if __name__ == "__main__":
    unittest.main()
