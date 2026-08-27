"""Static contract tests for the dedicated case execution-status API.

These tests do not log in, create records, or touch the local database. They
guard the Case-only API hunk and its atomic/permission/error-message contract.
"""
import ast
import pathlib
import re
import unittest


SOURCE_PATH = pathlib.Path(__file__).with_name("app") / "main.py"
SOURCE = SOURCE_PATH.read_text(encoding="utf-8")


class CaseExecutionStatusContractTest(unittest.TestCase):
    def test_case_execution_status_input_and_whitelist_exist(self):
        self.assertIn("class CaseExecutionStatusInput(BaseModel):", SOURCE)
        self.assertIn("CASE_EXECUTION_STATUSES", SOURCE)
        self.assertIn('"一审待执行"', SOURCE)
        self.assertIn('"执行结案"', SOURCE)
        for status in ("一审待执行", "二审待执行", "准备材料", "提交法院", "执行亏损", "执行异议", "执行和解中"):
            self.assertIn(f'"{status}"', SOURCE)
        self.assertIn('"执行立案": "提交法院"', SOURCE)
        self.assertIn('"终结执行": "执行终结"', SOURCE)
        self.assertIn("case_nos: str | list[str]", SOURCE)
        self.assertIn("execution_status: str", SOURCE)

    def test_dedicated_endpoint_normalizes_case_numbers_before_writing(self):
        self.assertRegex(SOURCE, r'@app\.post\(f"\{settings\.api_prefix\}/cases/execution-status"\)')
        self.assertIn("_normalize_case_numbers(body.case_nos)", SOURCE)
        self.assertIn("values.split(\",\")", SOURCE)
        self.assertIn("if not case_nos:", SOURCE)
        self.assertIn("case_nos.in_(case_nos)", SOURCE)
        self.assertIn("all_cases", SOURCE)
        self.assertIn("await db.commit()", SOURCE)

    def test_execution_status_uses_case_permission_and_failure_messages(self):
        self.assertIn("_require_case_progress_write_access(case_record, identity, db)", SOURCE)
        self.assertIn("已合并", SOURCE)
        self.assertIn("执行状态不能为空", SOURCE)
        self.assertIn("执行状态无效", SOURCE)
        self.assertIn("修改成功！", SOURCE)
        self.assertIn("未找到案件或当前账号无权查看", SOURCE)

    def test_phase_and_progress_routes_keep_case_only_guards(self):
        self.assertIn("@app.post(f\"{settings.api_prefix}/cases/{{case_id}}/progress\")", SOURCE)
        self.assertIn("只有案件负责人、部门负责人、受派经办律师或系统管理员可以维护案件进展和开庭排期", SOURCE)
        self.assertIn("当前案件阶段不能登记诉讼进展", SOURCE)
        ast.parse(SOURCE)


if __name__ == "__main__":
    unittest.main()
