"""Focused tests for the standalone historical case-person migration planner."""

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "scripts" / "audit_backfill_case_people.py"
SPEC = importlib.util.spec_from_file_location("audit_backfill_case_people", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CasePeopleBackfillPlannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.users = [
            {"username": "fanwenling", "display_name": "范文玲"},
            {"username": "wangmin", "display_name": "王敏"},
            {"username": "wangmin-two", "display_name": "王敏"},
        ]

    def test_unique_legacy_name_backfills_account_and_display_name(self) -> None:
        plan = MODULE.plan_case_person_backfill(
            {"data": {"assistant": "范文玲"}}, {}, self.users,
        )
        self.assertEqual(plan["updates"], {"assistant_username": "fanwenling"})
        self.assertEqual(plan["issues"], [])

    def test_ambiguous_or_missing_name_is_reported_without_update(self) -> None:
        plan = MODULE.plan_case_person_backfill(
            {"data": {}}, {"CaseLawyerName": "王敏", "CaseAssistantName": "不存在"}, self.users,
        )
        self.assertEqual(plan["updates"], {})
        self.assertEqual(
            plan["issues"],
            [
                {"field": "handling_lawyers", "value": "王敏", "status": "ambiguous"},
                {"field": "assistant", "value": "不存在", "status": "missing"},
            ],
        )

    def test_existing_username_mapping_is_idempotent(self) -> None:
        data = {"assistant_username": "fanwenling", "assistant": "范文玲"}
        plan = MODULE.plan_case_person_backfill({"data": data}, {}, self.users)
        self.assertEqual(plan["updates"], {})
        self.assertEqual(plan["issues"], [])

    def test_mixed_multi_person_field_reports_without_dropping_unresolved_name(self) -> None:
        plan = MODULE.plan_case_person_backfill(
            {"data": {"handling_lawyers": ["范文玲", "不存在"]}}, {}, self.users,
        )
        self.assertEqual(plan["updates"], {})
        self.assertEqual(
            plan["issues"],
            [{"field": "handling_lawyers", "value": "不存在", "status": "missing"}],
        )


if __name__ == "__main__":
    unittest.main()
