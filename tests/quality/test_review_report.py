"""代码审查报告的分档、基线比较，以及“只提示不拦截”。"""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts/review"))
SPEC = importlib.util.spec_from_file_location("oa_review_report", REPO / "scripts/review/report.py")
report = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(report)
risk = report.risk


class RiskTierTest(unittest.TestCase):
    def test_sensitive_files_are_high(self):
        for path, reason in (
            ("apps/api-server/app/security.py", "权限"),
            ("apps/api-server/app/core/permissions.py", "权限"),
            ("apps/api-server/app/core/data_scope_gate.py", "权限"),
            ("apps/admin-web/src/workspacePermissions.ts", "权限"),
            ("apps/api-server/app/areas/finance/settlements.py", "财务"),
            ("apps/api-server/app/core/invoice_permissions.py", "权限"),
            ("apps/api-server/app/core/case_fee_payments.py", "财务"),
            ("apps/admin-web/src/finance/InvoicePage.tsx", "财务"),
            ("apps/api-server/app/core/soft_delete.py", "数据写入"),
            ("apps/api-server/app/models.py", "数据写入"),
            ("scripts/import_hz_snapshot.py", "数据写入"),
            ("apps/api-server/app/core/startup_migrations.py", "数据库结构"),
            ("apps/api-server/app/core/feedback_serial_migration.py", "数据库结构"),
            ("scripts/hd_live_sync.py", "同步"),
            ("apps/api-server/app/core/legacy_sync.py", "同步"),
            (".github/workflows/quality.yml", "发布和质量门"),
            ("scripts/quality_gate.py", "发布和质量门"),
            ("scripts/review/report.py", "发布和质量门"),
        ):
            self.assertEqual(risk.classify_file(path), ("high", reason), path)

    def test_other_files(self):
        self.assertEqual(risk.classify_file("apps/api-server/app/areas/ipr/router.py")[0], "medium")
        self.assertEqual(risk.classify_file("apps/admin-web/src/ipr/IprCaseList.tsx")[0], "medium")
        for path in ("docs/a.md", "docs/代码审查流程.md", "apps/api-server/tests/regression/a_test.py", "apps/admin-web/src/a.css", "scripts/review/baseline.json"):
            self.assertEqual(risk.classify_file(path)[0], "low", path)
        self.assertEqual(risk.classify([])["tier"], "low")

    def test_raw_write_in_business_code_is_high(self):
        path = "apps/api-server/app/areas/ipr/router.py"
        self.assertEqual(risk.classify([path], {path: ["x = 1"]})["tier"], "medium")
        self.assertEqual(risk.classify([path], {path: ['await db.execute(text("UPDATE users SET a=1"))']})["tier"], "high")

    def test_manual_can_only_raise(self):
        doc = ["docs/a.md"]
        self.assertEqual(risk.classify(doc, raise_to="high")["tier"], "high")
        self.assertTrue(risk.classify(doc, raise_to="high")["raised_manually"])
        self.assertEqual(risk.classify(["scripts/quality_gate.py"], raise_to="low")["tier"], "high")
        self.assertEqual(risk.manual_tier("修复\n\nReview-Tier: high\n"), "high")
        self.assertIsNone(risk.manual_tier("修复 Review-Tier 说明"))


class DiffAndBaselineTest(unittest.TestCase):
    def test_parse_diff_lines_and_version_only_package(self):
        diff = "\n".join((
            "--- a/a.py", "+++ b/a.py", "@@ -1,0 +2,2 @@", "+x", "+y", "@@ -8 +10 @@", "-old", "+new",
            "--- a/apps/admin-web/package.json", "+++ b/apps/admin-web/package.json", "@@ -4 +4 @@", '-  "version": "1.2.1",', '+  "version": "1.2.2",',
            "--- a/b.py", "+++ /dev/null", "@@ -1 +0,0 @@", "-gone",
        ))
        changed, added, files = report.parse_diff(diff)
        self.assertEqual(changed["a.py"], {2, 3, 10})
        self.assertEqual(added["a.py"], ["x", "y", "new"])
        self.assertEqual(files, ["a.py", "b.py"])

    def test_only_issues_beyond_baseline_are_new(self):
        with tempfile.TemporaryDirectory() as temporary:
            original = report.ROOT
            report.ROOT = Path(temporary)
            try:
                (report.ROOT / "a.py").write_text("old_problem()\nfine()\nold_problem()\n", encoding="utf-8")
                old = report.issue("ruff", "a.py", 1, "X1", "m")
                baseline = report.to_baseline([old], "c")
                # 上下挪动不算新问题；同样内容多出来一处，算在改动行上的那一处。
                moved = report.issue("ruff", "a.py", 1, "X1", "m")
                extra = report.issue("ruff", "a.py", 3, "X1", "m")
                result = report.split_new([extra, moved], baseline, {"a.py": {3}})
                self.assertEqual([item["line"] for item in result["new_on_changed_lines"]], [3])
                self.assertEqual(result["same_file"], [])
                other_rule = report.issue("ruff", "a.py", 2, "X2", "m")
                far = report.issue("ruff", "b.py", 1, "X2", "m")
                result = report.split_new([moved, other_rule, far], baseline, {"a.py": {3}})
                self.assertEqual(result["new_on_changed_lines"], [])
                self.assertEqual([item["rule"] for item in result["same_file"]], ["X2"])
                self.assertEqual([item["file"] for item in result["elsewhere"]], ["b.py"])
            finally:
                report.ROOT = original

    def test_duplicates_report_one_block_per_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            body = "".join(f"value_{index} = compute({index})\n" for index in range(30))
            (root / "a.py").write_text(body, encoding="utf-8")
            (root / "b.py").write_text("unique = 1\n" + body, encoding="utf-8")
            original_root, original_files = report.ROOT, report.source_files
            report.ROOT, report.source_files = root, lambda: [root / "a.py", root / "b.py"]
            try:
                found = report.find_duplicates({}, window=12)
            finally:
                report.ROOT, report.source_files = original_root, original_files
            self.assertEqual(sorted((item["file"], item["line"]) for item in found), [("a.py", 1), ("b.py", 2)])


class ChineseFileNameTest(unittest.TestCase):
    def test_chinese_paths_are_parsed(self):
        changed, _, files = report.parse_diff("--- /dev/null\n+++ b/docs/代码审查流程.md\n@@ -0,0 +1 @@\n+x\n")
        self.assertEqual(files, ["docs/代码审查流程.md"])
        self.assertEqual(changed["docs/代码审查流程.md"], {1})


class NeverBlocksTest(unittest.TestCase):
    def hook_run(self, gate_code: int, report_source: str | None):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            hook = root / ".git/hooks/pre-push"
            hook.write_bytes((REPO / ".githooks/pre-push").read_bytes().replace(b"\r\n", b"\n"))
            hook.chmod(0o755)
            (root / "scripts/review").mkdir(parents=True)
            (root / "scripts/quality_gate.py").write_text(f"raise SystemExit({gate_code})\n", encoding="utf-8")
            if report_source:
                (root / "scripts/review/report.py").write_text(report_source, encoding="utf-8")
            data = root / "push-input.txt"
            data.write_text(f"x {'a' * 40} refs/heads/dev {'b' * 40}\n", encoding="utf-8")
            environment = {**os.environ, "OA_QUALITY_PYTHON": sys.executable, "OA_QUALITY_NODE": "node", "TMPDIR": temporary}
            return subprocess.run(["git", "hook", "run", f"--to-stdin={data}", "pre-push"], cwd=root, env=environment, capture_output=True, encoding="utf-8")

    def test_report_failure_does_not_block_push(self):
        done = self.hook_run(0, "raise SystemExit(3)\n")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("不影响推送", done.stderr)

    def test_report_receives_push_range(self):
        done = self.hook_run(0, "import sys\nprint('ARGS', sys.argv[1:])\n")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("a" * 40, done.stderr)
        self.assertIn("b" * 40, done.stderr)

    def test_gate_failure_still_blocks_and_skips_report(self):
        done = self.hook_run(1, "print('REPORT_RAN')\n")
        self.assertNotEqual(done.returncode, 0)
        self.assertNotIn("REPORT_RAN", done.stdout + done.stderr)

    def test_internal_error_exits_zero(self):
        with tempfile.TemporaryDirectory() as temporary:
            done = subprocess.run([sys.executable, str(REPO / "scripts/review/report.py"), "--head", "no-such-commit", "--report-dir", temporary],
                                  capture_output=True, encoding="utf-8", cwd=REPO)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("不影响推送", done.stderr)

    def test_gate_rules_stay_separate_from_review_rules(self):
        self.assertIn('select = ["F"]', (REPO / "pyproject.toml").read_text(encoding="utf-8"))
        gate = (REPO / ".github/workflows/quality.yml").read_text(encoding="utf-8")
        self.assertNotIn("review", gate)
        workflow = (REPO / ".github/workflows/review-report.yml").read_text(encoding="utf-8")
        self.assertIn("continue-on-error: true", workflow)
        self.assertEqual(json.loads((REPO / "scripts/review/baseline.json").read_text(encoding="utf-8"))["format"], 1)


if __name__ == "__main__":
    unittest.main()
