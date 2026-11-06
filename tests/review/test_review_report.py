"""代码审查报告的分档、基线比较，以及“只提示不拦截”。

放在 tests/review 而不是 tests/quality：门禁只发现 tests/quality，这些脚本坏了不能挡推送。
"""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil
import tempfile
import time
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
            ("scripts/review/baseline.json", "发布和质量门"),
            # 分支 2 审查指出判低的文件
            ("apps/api-server/scripts/promote_imported_case_fees.py", "数据写入"),
            ("apps/api-server/scripts/repair_case_relations.py", "数据写入"),
            ("apps/api-server/app/core/incoming_allocation_records.py", "财务"),
            ("apps/api-server/app/core/incoming_local_amounts.py", "财务"),
            ("apps/api-server/app/areas/ipr/fees.py", "财务"),
            ("apps/api-server/app/areas/contract/router.py", "财务"),
            ("apps/api-server/app/core/case_merge.py", "数据写入"),
            ("apps/api-server/app/core/system.py", "权限"),
            ("apps/api-server/app/core/contract_delete.py", "数据写入"),
            ("apps/api-server/app/core/startup_backfills.py", "数据写入"),
            ("apps/api-server/app/core/investigation_access.py", "权限"),
            ("apps/admin-web/src/FinanceCenterPage.tsx", "财务"),
            ("apps/admin-web/src/PlatformFinancePage.tsx", "财务"),
            ("apps/admin-web/src/roleActions.ts", "权限"),
            ("apps/admin-web/src/legal/CaseDetail/CaseFeesPanel.tsx", "财务"),
        ):
            self.assertEqual(risk.classify_file(path), ("high", reason), path)

    def test_other_files(self):
        self.assertEqual(risk.classify_file("apps/api-server/app/areas/ipr/router.py")[0], "medium")
        self.assertEqual(risk.classify_file("apps/admin-web/src/ipr/IprCaseList.tsx")[0], "medium")
        # “feedback”里有 fee，不能算财务。
        self.assertEqual(risk.classify_file("apps/api-server/app/areas/system/feedback_forward.py")[0], "medium")
        self.assertEqual(risk.classify_file("apps/admin-web/src/feedback/FeedbackForm.tsx")[0], "medium")
        for path in ("docs/a.md", "docs/代码审查流程.md", "apps/api-server/tests/regression/a_test.py", "apps/admin-web/src/a.css"):
            self.assertEqual(risk.classify_file(path)[0], "low", path)
        self.assertEqual(risk.classify([])["tier"], "low")

    def test_raw_write_in_business_code_is_high(self):
        path = "apps/api-server/app/areas/ipr/router.py"
        self.assertEqual(risk.classify([path], {path: ["x = 1"]})["tier"], "medium")
        self.assertEqual(risk.classify([path], {path: ['await db.execute(text("UPDATE users SET a=1"))']})["tier"], "high")
        self.assertEqual(risk.classify([path], {path: ["    db.add(record)"]})["tier"], "high")
        self.assertEqual(risk.classify([path], {path: ["    await db.execute(update(User).where(x))"]})["tier"], "high")
        self.assertEqual(risk.classify([path], {path: ["    record.status = 'x'"]})["tier"], "medium")  # 已知局限
        view = "apps/admin-web/src/ipr/IprCaseList.tsx"
        self.assertEqual(risk.classify([view], {view: ["  db.add(x)"]})["tier"], "medium")

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


class TemporaryRepo:
    """让 report 模块指向一个临时 Git 仓库。"""

    def __enter__(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.saved = report.ROOT, report.BASELINE
        report.ROOT, report.BASELINE = self.root, self.root / "scripts/review/baseline.json"
        self.git("init", "-q")
        self.git("config", "user.email", "t@t")
        self.git("config", "user.name", "t")
        return self

    def __exit__(self, *_):
        report.ROOT, report.BASELINE = self.saved
        self.temporary.cleanup()

    def git(self, *arguments):
        return subprocess.run(["git", *arguments], cwd=self.root, check=True, capture_output=True, text=True).stdout.strip()

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "c")
        return self.git("rev-parse", "HEAD")


class BaselineFromBaseTest(unittest.TestCase):
    def test_refreshing_baseline_in_same_commit_cannot_hide_new_issue(self):
        with TemporaryRepo() as repo:
            repo.write("a.py", "old()\nbad()\n")
            repo.write("scripts/review/baseline.json", json.dumps(report.to_baseline([report.issue("ruff", "a.py", 1, "X1", "m")], "c")))
            base = repo.commit()
            # 同一提交：加问题，并把它刷进基线
            refreshed = report.to_baseline([report.issue("ruff", "a.py", 1, "X1", "m"), report.issue("ruff", "a.py", 2, "X1", "m")], "c")
            repo.write("scripts/review/baseline.json", json.dumps(refreshed))
            head = repo.commit()
            baseline, note = report.load_baseline(base, {})
            self.assertIsNone(note)
            result = report.split_new([report.issue("ruff", "a.py", 1, "X1", "m"), report.issue("ruff", "a.py", 2, "X1", "m")], baseline, {"a.py": {2}})
            self.assertEqual([item["line"] for item in result["new_on_changed_lines"]], [2])
            changed, _, _ = report.parse_diff(repo.git("diff", "--unified=0", base, head))
            self.assertIn("scripts/review/baseline.json", report.changed_paths(base, head, changed))

    def test_broken_baseline_is_reported_not_raised(self):
        with TemporaryRepo() as repo:
            repo.write("scripts/review/baseline.json", "<<<<<<< HEAD\n")
            base = repo.commit()
            timings = {}
            self.assertEqual(report.load_baseline(base, timings)[0], {})
            self.assertIn("基线", timings["_errors"])

    def test_base_without_baseline_falls_back_with_note(self):
        with TemporaryRepo() as repo:
            repo.write("a.py", "x\n")
            base = repo.commit()
            repo.write("scripts/review/baseline.json", json.dumps({"format": 1, "files": {}}))
            repo.commit()
            baseline, note = report.load_baseline(base, {})
            self.assertEqual(baseline["format"], 1)
            self.assertIn("还没有基线", note)


class RenameTest(unittest.TestCase):
    def test_pure_rename_judges_both_paths(self):
        with TemporaryRepo() as repo:
            repo.write("apps/api-server/app/core/permissions.py", "x = 1\n")
            base = repo.commit()
            repo.git("mv", "apps/api-server/app/core/permissions.py", "apps/api-server/app/core/helpers.py")
            head = repo.commit()
            changed, _, _ = report.parse_diff(repo.git("diff", "--unified=0", base, head))
            self.assertEqual(changed, {})  # 没有差异内容，只靠 changed_paths
            files = report.changed_paths(base, head, changed)
            self.assertIn("apps/api-server/app/core/permissions.py", files)
            self.assertEqual(risk.classify(files)["tier"], "high")


class ToolFailureTest(unittest.TestCase):
    def fake(self, directory, code, stdout=""):
        path = Path(directory) / "fake.py"
        path.write_text(f"import sys\nprint({stdout!r})\nprint('boom', file=sys.stderr)\nraise SystemExit({code})\n", encoding="utf-8")
        return path

    def test_crashed_tools_are_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            script = self.fake(directory, 4)
            wrapper = Path(directory) / "python"
            wrapper.write_text(f"#!/bin/sh\nexec {sys.executable} {script}\n", encoding="utf-8")
            wrapper.chmod(0o755)
            for name, run in (
                ("ruff", lambda t: report.run_ruff(str(wrapper), t)),
                ("mypy", lambda t: report.run_mypy(str(wrapper), str(wrapper), Path(directory), t)),
                ("vulture", lambda t: report.run_vulture(str(wrapper), t)),
                ("tsc", lambda t: report.run_tsc(str(wrapper), t)),
                ("ts-metrics", lambda t: report.run_ts_metrics(str(wrapper), t)),
            ):
                timings = {}
                self.assertEqual(run(timings), [], name)
                self.assertIn(name, timings["_errors"], name)

    def test_tool_errors_without_results_are_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            wrapper = Path(directory) / "python"
            wrapper.write_text("#!/bin/sh\necho 'fatal: cannot start'\nexit 1\n", encoding="utf-8")
            wrapper.chmod(0o755)
            timings = {}
            report.run_mypy(str(wrapper), str(wrapper), Path(directory), timings)
            self.assertIn("mypy", timings["_errors"])
            timings = {}
            report.run_dependency_audit(str(wrapper), timings)
            self.assertIn("pip-audit", timings["_errors"])

    def test_incomplete_report_does_not_say_clean(self):
        tier = risk.classify(["docs/a.md"])
        empty = {"new_on_changed_lines": [], "same_file": [], "elsewhere": []}
        text = report.render({"base": "a" * 40, "head": "b" * 40, "tier": tier, "issues": empty, "coverage": {"status": "x", "frontend_note": ""}, "timings": {}, "skipped": {},
                              "failed": {"mypy": "退出码 2"}, "baseline_changed": True, "baseline_note": None, "known_issues": [], "seconds": 1})
        self.assertIn("本次不完整", text)
        self.assertIn("这次改了基线", text)
        self.assertNotIn("\n没有。\n", text)


class TimeLimitTest(unittest.TestCase):
    def tearDown(self):
        report.RUN["deadline"] = None

    def test_tool_timeout_kills_child_processes(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "marker"
            child = f"import time,pathlib;time.sleep(2);pathlib.Path({str(marker)!r}).write_text('x')"
            parent = f"import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',{child!r}]);time.sleep(30)"
            report.RUN["deadline"] = time.monotonic() + 0.5
            timings = {}
            started = time.monotonic()
            self.assertIsNone(report.run_tool("slow", [sys.executable, "-c", parent], Path(directory), 60, timings))
            self.assertLess(time.monotonic() - started, 5)
            self.assertIn("超时", timings["_errors"]["slow"])
            time.sleep(2.2)
            self.assertFalse(marker.exists(), "子进程没被杀掉")

    def test_tool_not_started_after_deadline(self):
        report.RUN["deadline"] = time.monotonic() - 1
        timings = {}
        self.assertIsNone(report.run_tool("late", [sys.executable, "-c", "pass"], Path("."), 60, timings))
        self.assertIn("总时限", timings["_errors"]["late"])

    def test_whole_run_stops_at_deadline_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            started = time.monotonic()
            done = subprocess.run([sys.executable, str(REPO / "scripts/review/report.py"), "--deadline", "1", "--coverage", "none", "--report-dir", directory,
                                   "--cache-dir", directory, "--base", "HEAD"], capture_output=True, encoding="utf-8", cwd=REPO)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertLess(time.monotonic() - started, 15)


class TsMetricsTest(unittest.TestCase):
    @unittest.skipUnless((REPO / "apps/admin-web/node_modules/typescript").is_dir() and shutil.which(os.environ.get("OA_QUALITY_NODE", "node")), "前端依赖没装")
    def test_complexity_length_and_unused_export(self):
        with tempfile.TemporaryDirectory() as directory:
            web = Path(directory)
            (web / "package.json").write_text("{}", encoding="utf-8")
            (web / "node_modules").symlink_to(REPO / "apps/admin-web/node_modules")
            (web / "src").mkdir()
            (web / "tests").mkdir()
            branches = "\n".join(f"  if (a === {index}) return {index};" for index in range(20))
            filler = "\n".join(f"  const v{index} = {index}; void v{index};" for index in range(210))
            (web / "src/a.ts").write_text(
                f"export function complex(a: number) {{\n{branches}\n  return 0;\n}}\n"
                f"export function long() {{\n{filler}\n}}\n"
                "export const used = 1;\nexport const usedInTest = 2;\nexport type Lonely = string;\n", encoding="utf-8")
            (web / "src/b.tsx").write_text("import {used} from './a';\nexport default function B() { return <div>{used}</div>; }\n", encoding="utf-8")
            (web / "tests/a.test.mjs").write_text("// usedInTest complex long\n", encoding="utf-8")
            done = subprocess.run([os.environ.get("OA_QUALITY_NODE", "node"), str(REPO / "scripts/review/ts_metrics.mjs"), str(web)], capture_output=True, encoding="utf-8")
            self.assertEqual(done.returncode, 0, done.stderr)
            found = {(item["rule"], item["message"].split()[0]) for item in json.loads(done.stdout)}
            self.assertIn(("TS-COMPLEXITY", "complex"), found)
            self.assertIn(("TS-LENGTH", "long"), found)
            self.assertIn(("TS-UNUSED-EXPORT", "导出的"), found)
            lonely = [item["message"] for item in json.loads(done.stdout) if item["rule"] == "TS-UNUSED-EXPORT"]
            self.assertEqual(lonely, ["导出的 Lonely 没有其他文件使用"])


class CoverageSafetyTest(unittest.TestCase):
    def test_probe_scripts_are_never_selected(self):
        selected = report.related_tests(["apps/api-server/app/core/workbuddy_model.py"], ["apps/api-server/tests/regression/workbuddy_model_probe.py"])
        self.assertFalse([name for name in selected if "probe" in name])

    def test_secret_env_names(self):
        for name in ("DINGTALK_APP_SECRET", "DEEPSEEK_API_KEY", "OSS_ACCESS_KEY_ID", "GITHUB_TOKEN"):
            self.assertTrue(report.SECRET_ENV.search(name), name)
        for name in ("PATH", "HOME", "APP_ENV"):
            self.assertFalse(report.SECRET_ENV.search(name), name)


class NeverBlocksTest(unittest.TestCase):
    def hook_run(self, gate_code: int, report_source: str | None, budget: int | None = None):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            hook = root / ".git/hooks/pre-push"
            content = (REPO / ".githooks/pre-push").read_bytes().replace(b"\r\n", b"\n")
            if budget is not None:
                self.assertIn(b"push_budget=300", content)
                content = content.replace(b"push_budget=300", f"push_budget={budget}".encode())
            hook.write_bytes(content)
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

    def test_report_limit_includes_gate_time(self):
        arguments = "import sys\nprint('ARGS', sys.argv[1:])\n"
        done = self.hook_run(0, arguments)
        self.assertRegex(done.stderr, r"'--deadline', '180'")
        # 门禁已用去大半：只给剩下的时间
        done = self.hook_run(0, arguments, budget=60)
        self.assertRegex(done.stderr, r"'--deadline', '(59|60)'")
        # 剩下的不够：跳过报告，照样放行
        done = self.hook_run(0, "print('REPORT_RAN')\n", budget=10)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertNotIn("REPORT_RAN", done.stdout + done.stderr)
        self.assertIn("跳过代码审查报告", done.stderr)

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

    def test_gate_does_not_discover_these_tests(self):
        gate = (REPO / "scripts/quality_gate.py").read_text(encoding="utf-8")
        self.assertIn('"-s", "tests/quality"', gate)
        self.assertFalse(list((REPO / "tests/quality").glob("*review*")))

    def test_gate_rules_stay_separate_from_review_rules(self):
        self.assertIn('select = ["F"]', (REPO / "pyproject.toml").read_text(encoding="utf-8"))
        gate = (REPO / ".github/workflows/quality.yml").read_text(encoding="utf-8")
        self.assertNotIn("review", gate)
        workflow = (REPO / ".github/workflows/review-report.yml").read_text(encoding="utf-8")
        self.assertIn("continue-on-error: true", workflow)
        self.assertEqual(json.loads((REPO / "scripts/review/baseline.json").read_text(encoding="utf-8"))["format"], 1)


if __name__ == "__main__":
    unittest.main()
