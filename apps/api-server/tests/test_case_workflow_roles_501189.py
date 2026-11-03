"""501189：案件智能体分工检查按案件信息里的经办律师/开庭律师/律师助理对应手册岗位，部门岗位不报未分配。"""
import unittest

from app.case_workflow_rules import build_case_workflow_guide


class CaseWorkflowRoleTests(unittest.TestCase):
    def test_roles_come_from_case_information(self):
        snapshot = {"case": {"status": "文书准备"}, "tasks": [], "documents": [], "people": [
            {"role": "开庭律师", "name": "沈建锋"}, {"role": "律师助理", "name": "邱梦宇"}, {"role": "经办律师", "name": "沈建锋"}]}
        guide = build_case_workflow_guide(snapshot)
        roles = {item["role"]: item for item in guide["role_tasks"]}
        self.assertEqual(roles["文书"]["owner_name"], "邱梦宇")
        self.assertEqual(roles["主办律师"]["owner_name"], "沈建锋")
        self.assertEqual(roles["分案人员"]["assignment_status"], "department")
        self.assertEqual(guide["risk_summary"]["unassigned_roles"], 0)
        self.assertTrue(any("团队负责制" in rule for rule in guide["agent_rules"]))

    def test_missing_case_member_still_unassigned(self):
        guide = build_case_workflow_guide({"case": {"status": "文书准备"}, "tasks": [], "documents": [], "people": [{"role": "开庭律师", "name": "甲"}]})
        roles = {item["role"]: item for item in guide["role_tasks"]}
        self.assertEqual(roles["文书"]["assignment_status"], "unassigned")
        self.assertEqual(guide["risk_summary"]["unassigned_roles"], 1)


if __name__ == "__main__":
    unittest.main()
