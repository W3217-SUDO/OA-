"""Regression contract for ordinary case phase-tree statistics."""
import ast
import pathlib
import unittest


SOURCE = (pathlib.Path(__file__).with_name("app") / "main.py").read_text(encoding="utf-8")


class CasePhaseTreeCountsContractTest(unittest.TestCase):
    def test_phase_filter_does_not_limit_phase_tree_counts(self):
        self.assertIn("include_status_filter: bool = True", SOURCE)
        self.assertIn("if include_status_filter and not contains(record.status", SOURCE)
        self.assertIn("if include_status_filter and body.case_statuses:", SOURCE)
        self.assertIn("has_phase_filter = bool(body.case_statuses or (body.case_status or body.status).strip())", SOURCE)
        self.assertIn("include_status_filter=False", SOURCE)
        self.assertIn("for record in count_records:", SOURCE)
        ast.parse(SOURCE)


if __name__ == "__main__":
    unittest.main()
