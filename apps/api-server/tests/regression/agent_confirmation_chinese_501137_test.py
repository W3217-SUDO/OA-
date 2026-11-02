"""501137：智能体确认页不显示英文代码，参数名和代码值都有中文。"""

import unittest

from app.agent_mcp import business_tools
from app.agent_mcp.action_summary import summary_from_preview
from app.agent_mcp.display_labels import OTHER_FIELD, display_maps, field_label, has_chinese


class AgentConfirmationChineseTest(unittest.TestCase):
    def test_task_act_card_from_ticket_is_chinese(self):
        tool = business_tools.TOOLS["biz_task_act"]
        values = {"task_id": 498463, "action": "complete", "comment": "这个案子可以启动，商标整体近似。"}
        preview = {"operation_name": tool.title, "path_template": "/business-tools/biz_task_act", "method": "POST",
                   "params": {"path": {}, "query": {}, "body": values}, **display_maps({"body": values}, tool.properties)}
        self.assertEqual(preview["field_labels"]["task_id"], "任务ID")
        self.assertEqual(preview["field_labels"]["action"], "动作")
        self.assertEqual(preview["value_labels"]["action"]["complete"], "完成任务")
        summary = summary_from_preview(preview)
        self.assertIn("动作：完成任务", summary)
        self.assertNotIn("complete", summary)

    def test_every_business_tool_parameter_has_chinese_name(self):
        for tool in business_tools.TOOLS.values():
            maps = display_maps({"body": {name: None for name in tool.properties}}, tool.properties)
            for name in tool.properties:
                label = maps["field_labels"][name]
                self.assertTrue(has_chinese(label), (tool.name, name, label))
                self.assertNotEqual(label, OTHER_FIELD, (tool.name, name))

    def test_unknown_code_name_is_never_shown(self):
        self.assertEqual(field_label("some_internal_code"), OTHER_FIELD)
        preview = {"operation_name": "测试", "path_template": "/x", "method": "POST",
                   "params": {"path": {}, "query": {}, "body": {"some_internal_code": "1"}}}
        self.assertNotIn("some_internal_code", summary_from_preview(preview))


if __name__ == "__main__":
    unittest.main()
