"""501289（陶国南 11-03 21:23）：智能体别先回“正在查询案件空间”之类的话。"""
import unittest

from app.cloud_agent.runtime import final_answer
from app.harness_agent.runtime import oa_persona


class CloudAgentNarrationTest(unittest.TestCase):
    def test_short_narration_before_tools_is_dropped(self):
        messages = ["正在查询案件空间…", "已生成待确认操作：将案件HZMS2600441的案由补填为侵害商标权纠纷，请在下方确认。"]
        self.assertEqual(final_answer(messages, [1]), messages[1])

    def test_real_content_before_tools_is_kept(self):
        long_text = "根据案件材料，" + "这是正式的分析内容。" * 10
        self.assertEqual(final_answer([long_text, "已查询完毕。"], [1]), long_text + "\n\n已查询完毕。")

    def test_without_tools_everything_is_kept(self):
        self.assertEqual(final_answer(["你好", "有什么可以帮你"], []), "你好\n\n有什么可以帮你")
        self.assertEqual(final_answer(["正在查询…"], [1]), "正在查询…", "只剩过程说明时不吞掉回答")

    def test_rule_shared_by_dsh_and_cloud(self):
        self.assertIn("不要先写“正在查询……”", oa_persona())


if __name__ == "__main__":
    unittest.main()
