"""Static contract tests for the CasePhaseTypeChange parity endpoint.

These tests only inspect the Case API source; they do not log in, create data,
or touch the local database.
"""
import ast
import pathlib
import unittest


SOURCE = (pathlib.Path(__file__).with_name("app") / "main.py").read_text(encoding="utf-8")


class CasePhaseChangeContractTest(unittest.TestCase):
    @staticmethod
    def phase_defaults():
        module = ast.parse(SOURCE)
        assignment = next(
            node for node in module.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "DEFAULT_SYSTEM_PARAMETERS" for target in node.targets)
        )
        return {
            code: (name, extra)
            for category, code, name, extra in ast.literal_eval(assignment.value)
            if category == "case_phase"
        }

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
        self.assertIn("await _require_case_phase_change_access(case_record, identity, db)", SOURCE)
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

    def test_picker_catalog_matches_legacy_first_second_and_execution_groups(self):
        phases = self.phase_defaults()
        self.assertEqual(phases["FIRST_PENDING_EXECUTION"], (
            "一审待执行", {"case_type": "民事争议", "parent_code": "EXECUTION", "sort_order": 501},
        ))
        self.assertEqual(phases["SECOND_PENDING_EXECUTION"], (
            "二审待执行", {"case_type": "民事争议", "parent_code": "EXECUTION", "sort_order": 502},
        ))
        execution = [
            (name, extra["sort_order"])
            for name, extra in phases.values()
            if extra.get("parent_code") == "EXECUTION"
        ]
        self.assertEqual(sorted(execution, key=lambda item: item[1]), [
            ("一审待执行", 501), ("二审待执行", 502), ("准备材料", 503),
            ("提交法院", 504), ("执行受理", 505), ("执行中止", 506),
            ("执行结案", 507), ("执行终本", 508), ("执行终结", 509),
            ("执行亏损", 510), ("执行异议", 511), ("执行和解中", 512),
        ])
        self.assertEqual(phases["EXECUTION_SUBMIT_COURT"][0], "提交法院")
        for restored_code in ("EXECUTION_PREP_MATERIALS", "EXECUTION_DEFICIT", "EXECUTION_OBJECTION"):
            self.assertIn(restored_code, phases)

    def test_startup_reconciles_existing_civil_phase_rows_idempotently(self):
        self.assertIn("civil_phase_defaults", SOURCE)
        self.assertIn("phase.name = name", SOURCE)
        self.assertIn("phase.extra = dict(extra)", SOURCE)
        self.assertIn("phase.sort_order = int(extra.get(\"sort_order\") or 0)", SOURCE)
        self.assertIn("phase.is_active = True", SOURCE)


if __name__ == "__main__":
    unittest.main()
