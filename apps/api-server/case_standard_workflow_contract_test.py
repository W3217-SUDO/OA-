"""Contract tests for the manual-driven case workflow guide."""

import unittest
from datetime import date

from app.case_workflow_rules import build_case_workflow_guide


class CaseStandardWorkflowContractTest(unittest.TestCase):
    def test_builds_phase_deadlines_materials_and_role_tasks(self):
        guide = build_case_workflow_guide(
            {
                "case": {
                    "status": "执行中",
                    "data": {
                        "judgment_effective_date": "2026-08-01",
                        "preservation_expiry": "2026-12-31",
                        "closed_at": "2026-08-05",
                    },
                },
                "documents": [
                    {"name": "授权委托书.pdf", "category": "起诉材料"},
                    {"name": "起诉状.docx", "category": "起诉材料"},
                ],
                "deadlines": [{"id": 1, "type": "案件提醒", "title": "举证期限", "deadline": "2026-08-12"}],
                "people": [{"role": "经办律师", "name": "范文玲"}, {"role": "文书", "name": "张三"}],
                "tasks": [],
            },
            reference_date=date(2026, 8, 11),
        )
        self.assertEqual(guide["current_phase"]["code"], "enforcement")
        self.assertEqual(guide["deadlines"][0]["title"], "举证期限")
        self.assertEqual(guide["deadlines"][0]["risk"], "critical")
        self.assertTrue(any(item["code"] == "enforcement-filing" for item in guide["deadlines"]))
        self.assertEqual(guide["material_progress"]["completed"], 2)
        self.assertEqual(next(item for item in guide["materials"] if item["code"] == "authorization")["status"], "uploaded")
        self.assertEqual(next(item for item in guide["role_tasks"] if item["role"] == "经办律师")["owner_name"], "范文玲")
        self.assertTrue(guide["agent_rules"])

    def test_missing_dates_are_reported_instead_of_invented(self):
        guide = build_case_workflow_guide({"case": {"status": "办理中", "data": {}}, "documents": []}, reference_date=date(2026, 8, 11))
        self.assertIn("保全到期日（存在保全时必填）", guide["deadline_missing_inputs"])
        self.assertIn("裁判生效日期（进入执行阶段时必填）", guide["deadline_missing_inputs"])
        self.assertFalse(any(item["code"] == "enforcement-legal-limit" for item in guide["deadlines"]))
        self.assertGreater(guide["risk_summary"]["missing_required_materials"], 0)


if __name__ == "__main__":
    unittest.main()
