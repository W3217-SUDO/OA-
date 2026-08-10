from pathlib import Path
import unittest


SOURCE = (Path(__file__).parent / "app" / "main.py").read_text(encoding="utf-8")


class AgentCenterMenuContractTest(unittest.TestCase):
    def test_global_agent_center_is_a_system_menu(self):
        self.assertIn('(\"agent-center\", \"\", \"智能体中心\", \"robot\", 5)', SOURCE)

    def test_existing_case_roles_receive_the_agent_center(self):
        self.assertIn("'agent_center_menu_v1'", SOURCE)
        self.assertIn('if "case" in keys and "agent-center" not in keys:', SOURCE)
        for role in ("manager", "auditor", "user"):
            role_line = next(line for line in SOURCE.splitlines() if line.strip().startswith(f'"{role}":'))
            self.assertIn('"agent-center"', role_line)


if __name__ == "__main__":
    unittest.main()
