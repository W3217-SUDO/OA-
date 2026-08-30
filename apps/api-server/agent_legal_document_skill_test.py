from pathlib import Path
import unittest


SOURCE = (Path(__file__).parent / "app" / "agent_skills.py").read_text(encoding="utf-8")


class AgentLegalDocumentSkillTest(unittest.TestCase):
    def test_legal_document_drafting_skill_is_installed(self):
        self.assertIn('id="legal-document-drafting"', SOURCE)
        self.assertIn('name="法律文书起草"', SOURCE)
        self.assertIn("不得虚构当事人、案号、法院、日期、金额、证据或法律程序", SOURCE)
        self.assertIn("【待补充：具体字段】", SOURCE)
        self.assertIn("输出应直接作为 Word 文档正文", SOURCE)


if __name__ == "__main__":
    unittest.main()
