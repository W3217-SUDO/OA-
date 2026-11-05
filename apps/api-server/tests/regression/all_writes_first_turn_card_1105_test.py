"""陶国南 11-05 08:48：安全前提下效率优先，所有写入第一轮直接出确认卡片，不先文字确认（云端和 DSH 共用规则）。"""

import unittest

from app.agent_mcp import business_tools
from app.agent_mcp.model_tools import MODEL_TOOLS
from app.agent_skills import _WRITE_RULE
from app.harness_agent.runtime import oa_persona


class AllWritesFirstTurnCardTest(unittest.TestCase):
    def test_rules_no_longer_wait_for_text_confirmation(self):
        for text in (_WRITE_RULE, oa_persona(), business_tools._CONFIRM["description"]):
            self.assertNotIn("用户同意后用相同参数", text)
            self.assertNotIn("用户看过计划并明确同意后", text)
        self.assertIn("第一次就带 confirm=true", _WRITE_RULE)
        self.assertIn("第一次就生成确认卡片", oa_persona())

    def test_call_tool_description_says_card_not_direct_execution(self):
        call = next(item for item in MODEL_TOOLS if item.get("function", {}).get("name") == "oa_call_tool")
        description = call["function"]["description"]
        self.assertIn("系统生成确认卡片", description)
        self.assertNotIn("参数齐全即直接执行", description)


    def test_confirm_wording_does_not_change_fingerprint(self):
        from unittest.mock import patch
        tool = business_tools.TOOLS["biz_case_update_info"]
        before = business_tools.business_fingerprint(tool)
        with patch.dict(business_tools._CONFIRM, {"description": "任意新说明"}):
            self.assertEqual(business_tools.business_fingerprint(tool), before, "改 confirm 说明不能让已生成的卡片失效")


if __name__ == "__main__":
    unittest.main()
