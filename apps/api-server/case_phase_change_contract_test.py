"""Static contract tests for the CasePhaseTypeChange parity endpoint.

These tests only inspect the Case API source; they do not log in, create data,
or touch the local database.
"""
import ast
import pathlib
import unittest


SOURCE = (pathlib.Path(__file__).with_name("app") / "main.py").read_text(encoding="utf-8")


class CasePhaseChangeContractTest(unittest.TestCase):
    def test_phase_input_and_option_mapping_are_explicit(self):
        self.assertIn("class CasePhaseChangeInput(BaseModel):", SOURCE)
        self.assertIn("case_phase_id", SOURCE)
        self.assertIn("case_phase_name", SOURCE)
        self.assertIn("CASE_PHASE_STATUS_BY_CODE", SOURCE)
        self.assertIn('SystemParameter.category == "case_phase"', SOURCE)
        self.assertIn('@app.get(f"{settings.api_prefix}/cases/phases")', SOURCE)

    def test_phase_change_preflights_all_case_targets_before_writing(self):
        self.assertIn('@app.post(f"{settings.api_prefix}/cases/phase-change")', SOURCE)
        self.assertIn("_normalize_case_numbers(body.case_nos)", SOURCE)
        self.assertIn("all_cases", SOURCE)
        self.assertIn("missing", SOURCE)
        self.assertIn("await _require_case_progress_write_access(case_record, identity, db)", SOURCE)
        self.assertIn("if case_record.status == \"已合并\"", SOURCE)
        self.assertIn("当前案件已处于所选阶段", SOURCE)
        self.assertIn("await db.commit()", SOURCE)

    def test_phase_change_keeps_audit_and_legacy_response_copy(self):
        self.assertIn('action="修改案件阶段"', SOURCE)
        self.assertIn("修改成功！", SOURCE)
        self.assertIn("修改失败！", SOURCE)
        self.assertIn("阶段名称不能为空", SOURCE)
        self.assertIn("案件阶段不存在或已停用", SOURCE)
        ast.parse(SOURCE)


if __name__ == "__main__":
    unittest.main()
