import unittest

from app.agent_skills import AGENT_SKILLS, GENERAL_SKILL, parse_skill_message, public_skill_catalog


class AgentSkillRegistryContractTest(unittest.TestCase):
    def test_official_github_office_skills_are_registered(self):
        sources = {item["source"] for item in public_skill_catalog()}
        self.assertTrue({
            "openai/skills:pdf",
            "openai/skills:jupyter-notebook",
            "openai/skills:screenshot",
            "openai/skills:speech",
            "openai/skills:transcribe",
            "openai/skills:security-best-practices",
        }.issubset(sources))
        self.assertEqual(len(public_skill_catalog()), len(AGENT_SKILLS))

    def test_skill_marker_is_parsed_and_removed_from_visible_message(self):
        skill, message = parse_skill_message("[[skill:pdf-review]]\n审阅材料")
        self.assertEqual(skill.id, "pdf-review")
        self.assertEqual(message, "审阅材料")
        fallback, untouched = parse_skill_message("普通问题")
        self.assertEqual(fallback, GENERAL_SKILL)
        self.assertEqual(untouched, "普通问题")

    def test_screenshot_skill_is_available_while_audio_skills_explain_their_boundary(self):
        catalog = {item["id"]: item for item in public_skill_catalog()}
        self.assertTrue(catalog["screenshot-evidence"]["available"])
        self.assertFalse(catalog["screenshot-evidence"]["unavailable_reason"])
        for skill_id in ("speech-output", "meeting-transcription"):
            self.assertFalse(catalog[skill_id]["available"])
            self.assertTrue(catalog[skill_id]["unavailable_reason"])


if __name__ == "__main__":
    unittest.main()
