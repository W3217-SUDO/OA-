"""回归入口的独立导入与 UTF-8 输出失败路径。"""

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tests import run_regression


class RegressionRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.path = Path(__file__)
        self.args = argparse.Namespace(timeout=1, report=None, api_base=None, legacy_source_root=None, legacy_bundle=None)

    def test_utf8_output_is_decoded_explicitly(self) -> None:
        with patch.object(run_regression.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "成功".encode(), b"")):
            result = run_regression.run_file(self.path, self.args)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["output"], "成功")

    def test_non_utf8_output_fails_with_diagnostic(self) -> None:
        with patch.object(run_regression.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, b"", b"\xff")):
            result = run_regression.run_file(self.path, self.args)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("stderr不是 UTF-8", result["output"])

    def test_timeout_decodes_partial_utf8_output(self) -> None:
        error = subprocess.TimeoutExpired([], 1, output="部分输出".encode(), stderr=b"")
        with patch.object(run_regression.subprocess, "run", side_effect=error):
            result = run_regression.run_file(self.path, self.args)
        self.assertEqual(result["exit_code"], 124)
        self.assertIn("部分输出", result["output"])

    def test_finance_fixture_importers_receive_an_isolated_database(self) -> None:
        for name in ("finance929Regression_test.py", "invoice929ReworkApi_test.py"):
            with self.subTest(name=name), tempfile.TemporaryDirectory(prefix="oa-test-runner-") as directory:
                temporary = Path(directory)
                path = run_regression.TEST_ROOT / "regression" / name
                environment = run_regression.test_environment(path, temporary, self.args)
                self.assertEqual(Path(environment["OA_FINANCE_TEST_DB"]), temporary / "finance-test.db")
                self.assertEqual(Path(environment["UPLOAD_ROOT"]), temporary / "uploads")
                self.assertEqual(environment["APP_ENV"], "test")
                self.assertTrue(Path(environment["UPLOAD_ROOT"]).is_dir())

    def test_direct_entry_adds_application_and_repository_roots(self) -> None:
        with tempfile.TemporaryDirectory(prefix="oa-test-runner-") as directory:
            testcase = Path(directory) / "test_imports.py"
            testcase.write_text(
                "import unittest\nfrom app.config import Settings\nfrom scripts.verify_area_split import capture\n"
                "class EntryTest(unittest.TestCase):\n    def test_imports(self):\n        self.assertTrue(Settings and capture)\n",
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment.pop("PYTHONPATH", None)
            result = subprocess.run(
                [sys.executable, str(run_regression.TEST_ROOT / "_run_one.py"), str(testcase)],
                cwd=directory, env=environment, capture_output=True, timeout=30, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="strict"))

    def test_method_exclusion_does_not_hide_other_failures(self) -> None:
        with tempfile.TemporaryDirectory(prefix="oa-test-runner-") as directory:
            testcase = Path(directory) / "test_mixed.py"
            testcase.write_text(
                "import unittest\n"
                "class MixedTest(unittest.TestCase):\n"
                "    def test_permission(self):\n        self.fail('excluded permission')\n"
                "    def test_business(self):\n        self.fail('business regression')\n",
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment["OA_TEST_EXCLUDED_METHODS"] = json.dumps(["MixedTest.test_permission"])
            environment["PYTHONIOENCODING"] = "utf-8:strict"
            result = subprocess.run(
                [sys.executable, str(run_regression.TEST_ROOT / "_run_one.py"), str(testcase)],
                cwd=directory, env=environment, capture_output=True, timeout=30, check=False,
            )
        output = (result.stdout + result.stderr).decode("utf-8", errors="strict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("business regression", output)
        self.assertNotIn("excluded permission", output)
        self.assertIn('"excluded": ["MixedTest.test_permission"]', output)

    def test_all_skipped_test_file_is_not_reported_as_passed(self) -> None:
        for direct_entry in (False, True):
            with self.subTest(direct_entry=direct_entry), tempfile.TemporaryDirectory(prefix="oa-test-runner-") as directory:
                test_root = Path(directory)
                shutil.copyfile(run_regression.TEST_ROOT / "_run_one.py", test_root / "_run_one.py")
                testcase = test_root / "test_all_skipped.py"
                testcase.write_text(
                    "import unittest\n"
                    "@unittest.skip('dependency unavailable')\n"
                    "class SkippedTest(unittest.TestCase):\n"
                    "    def test_work(self):\n        self.fail('must not execute')\n"
                    + ("if __name__ == '__main__':\n    unittest.main()\n" if direct_entry else ""),
                    encoding="utf-8",
                )
                args = argparse.Namespace(
                    timeout=30, report=None, api_base=None,
                    legacy_source_root=None, legacy_bundle=None,
                )
                with patch.object(run_regression, "TEST_ROOT", test_root):
                    result = run_regression.run_file(testcase, args)
                self.assertEqual(result["status"], "SKIP")
                self.assertEqual(result["exit_code"], 0)
                if not direct_entry:
                    self.assertEqual(result["executed_methods"], 0)
                    self.assertEqual(result["skipped_methods"], 1)

    def test_permission_exclusion_keeps_business_methods_running(self) -> None:
        with tempfile.TemporaryDirectory(prefix="oa-test-runner-") as directory:
            test_root = Path(directory)
            shutil.copyfile(run_regression.TEST_ROOT / "_run_one.py", test_root / "_run_one.py")
            testcase = test_root / "test_mixed.py"
            testcase.write_text(
                "import unittest\n"
                "class MixedTest(unittest.TestCase):\n"
                "    def test_permission(self):\n        self.fail('permission excluded')\n"
                "    def test_business(self):\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            args = argparse.Namespace(
                timeout=30, report=None, api_base=None,
                legacy_source_root=None, legacy_bundle=None,
                exclude_category=["permissions"],
            )
            category = {"permissions": {"test_mixed.py": {
                "MixedTest.test_permission": "权限专项暂排",
            }}}
            with patch.object(run_regression, "TEST_ROOT", test_root), patch.object(run_regression, "EXCLUDED_CATEGORIES", category):
                partial = run_regression.run_file(testcase, args)
            self.assertEqual(partial["status"], "PARTIAL")
            self.assertEqual(partial["executed_methods"], 1)
            self.assertEqual(partial["skipped_methods"], 0)
            testcase.write_text(
                "import unittest\n"
                "class MixedTest(unittest.TestCase):\n"
                "    def test_permission(self):\n        self.fail('permission excluded')\n",
                encoding="utf-8",
            )
            with patch.object(run_regression, "TEST_ROOT", test_root), patch.object(run_regression, "EXCLUDED_CATEGORIES", category):
                excluded = run_regression.run_file(testcase, args)
            self.assertEqual(excluded["status"], "EXCLUDED")
            self.assertEqual(excluded["executed_methods"], 0)
            self.assertEqual(excluded["skipped_methods"], 0)

    def test_missing_required_environment_returns_nonzero(self) -> None:
        environment = os.environ.copy()
        for name in ("OA_TEST_POSTGRES_URL", "OA_TEST_POSTGRES_DSN", "OA_TEST_API_BASE"):
            environment.pop(name, None)
        for group, filename in (
            ("unit", "test_postgres_startup_migrations.py"),
            ("integration", "case_create_contract_test.py"),
        ):
            with self.subTest(group=group):
                completed = subprocess.run(
                    [sys.executable, str(run_regression.TEST_ROOT / "run_regression.py"),
                     "--group", group, "--file", filename],
                    cwd=run_regression.API_ROOT, env=environment,
                    capture_output=True, timeout=30, check=False,
                )
                self.assertEqual(completed.returncode, 1, completed.stdout.decode("utf-8", errors="strict"))
                self.assertIn('"skipped": 1', completed.stdout.decode("utf-8", errors="strict"))

    def test_source_defers_only_declared_pg_files_and_retains_mixed_files(self) -> None:
        full = run_regression.selected_files(["unit", "regression", "structural"], [])
        local, deferred = run_regression.source_selection(full)
        self.assertEqual({item["file"] for item in deferred}, {
            "test_agent_commands_postgres.py", "test_postgres_startup_migrations.py",
        })
        self.assertEqual(len(local), len(full) - 2)
        self.assertTrue(all(item["status"] == "DEFERRED" and item["passed"] is False and item["requires_env"] for item in deferred))
        self.assertTrue({
            "test_archive_readonly_and_evidence_import.py", "test_business_rule_scheduler.py",
            "test_customer_task_query_bounds.py", "test_dashboard_business_dates.py",
            "test_domain_route_storage.py", "test_file_io_offloading.py",
            "test_finance_incoming_query.py", "test_finance_selected_query.py",
            "test_task_company_projection.py", "test_task_query_pushdown.py",
            "test_notification_outbox.py", "ipr_custom_import_batch_contract_test.py",
        }.issubset({path.name for path in local}))

    def test_source_with_only_deferred_files_is_not_successful(self) -> None:
        environment = os.environ.copy()
        for name in ("AGENT_COMMANDS_TEST_POSTGRES_URL", "OA_TEST_POSTGRES_URL", "OA_TEST_POSTGRES_DSN"):
            environment.pop(name, None)
        for profile, expected_code in (("source", 2), ("full", 1)):
            with self.subTest(profile=profile):
                completed = subprocess.run(
                    [sys.executable, str(run_regression.TEST_ROOT / "run_regression.py"),
                     "--execution-profile", profile, "--group", "unit",
                     "--file", "test_agent_commands_postgres.py", "--file", "test_postgres_startup_migrations.py"],
                    cwd=run_regression.API_ROOT, env=environment,
                    capture_output=True, timeout=30, check=False,
                )
                output = (completed.stdout + completed.stderr).decode("utf-8", errors="strict")
                self.assertEqual(completed.returncode, expected_code, output)
                if profile == "source":
                    self.assertEqual(output.count("DEFERRED (not passed"), 2)
                    self.assertIn("没有匹配的测试文件", output)
                else:
                    self.assertIn('"total": 2', output)
                    self.assertIn('"skipped": 2', output)
                    self.assertNotIn("DEFERRED", output)

    def test_source_reports_deferred_and_partial_methods_without_hiding_failures(self) -> None:
        files = [run_regression.TEST_ROOT / "test_agent_commands_postgres.py", self.path]
        for status in ("PASS", "FAIL", "SKIP"):
            with self.subTest(status=status), tempfile.TemporaryDirectory(prefix="oa-test-source-selection-") as directory:
                report = Path(directory) / "backend.json"
                output = io.StringIO()
                result = {"file": self.path.name, "status": status, "skipped_methods": 1, "exit_code": 1 if status == "FAIL" else 0}
                with (
                    patch.object(sys, "argv", ["run_regression.py", "--execution-profile", "source", "--report", str(report)]),
                    patch.object(run_regression, "selected_files", return_value=files),
                    patch.object(run_regression, "run_file", return_value=result) as execute,
                    redirect_stdout(output),
                ):
                    code = run_regression.main()
                self.assertEqual(code, 0 if status == "PASS" else 1)
                self.assertEqual(execute.call_args.args[0], self.path)
                self.assertEqual(execute.call_count, 1)
                summary = json.loads(report.read_text(encoding="utf-8"))
                self.assertEqual(summary["total"], 1)
                self.assertEqual(summary["deferred"][0]["file"], "test_agent_commands_postgres.py")
                self.assertEqual(summary["pending_full"][0]["status"], "NOT_PASSED")
                self.assertEqual(summary["pending_full"][0]["skipped_methods"], 1)
                self.assertIn("not passed; pending CI full", output.getvalue())

    def test_direct_mixed_file_reports_actual_skipped_method_count(self) -> None:
        output = b"Ran 3 tests in 0.001s\n\nOK (skipped=1)\n"
        with patch.object(run_regression.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, output, b"")), patch.object(Path, "read_text", return_value="if __name__"):
            result = run_regression.run_file(self.path, self.args)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["executed_methods"], 2)
        self.assertEqual(result["skipped_methods"], 1)
