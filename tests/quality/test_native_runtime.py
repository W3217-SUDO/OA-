"""隔离验证原生运行包激活、启动命令与 API/静态资源健康。"""

import hashlib
from contextlib import redirect_stderr
import io
import json
import os
import re
import sys
import subprocess
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import native_runtime
import quality_gate
import runtime_package


class NativeRuntimeTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="oa-test-native-runtime-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.package, self.manifest = self.make_package("old", "a" * 40)

    def make_package(self, name: str, commit: str) -> tuple[Path, dict]:
        package = self.root / name
        files = {
            "api/app/main.py": b"app = None\n",
            "api/requirements.txt": b"fastapi==0.136.3\n",
            "api/requirements.lock": b"fastapi==0.136.3\n",
            "web/index.html": b'<html><script src="/assets/app.js"></script></html>',
            "web/assets/app.js": b"window.app = true;\n",
            "web/build-info.json": json.dumps({"version": "1.2.3", "source_commit": commit}).encode(),
        }
        for resource in runtime_package.API_RESOURCE_FILES:
            files[f"api/app/{resource}"] = b"{}\n"
        for relative, content in files.items():
            path = package / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        manifest = {
            "format": 1,
            "version": "1.2.3",
            "source_commit": commit,
            "files": {relative: hashlib.sha256(content).hexdigest() for relative, content in files.items()},
        }
        (package / "runtime-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return package, manifest

    def service(self, responses: dict[str, bytes]) -> tuple[ThreadingHTTPServer, list[str]]:
        paths = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                paths.append(self.path)
                payload = responses.get(self.path)
                self.send_response(200 if payload is not None else 404)
                self.end_headers()
                if payload is not None:
                    self.wfile.write(payload)

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server, paths

    def test_verified_package_rejects_checkout_and_tampering(self):
        self.assertEqual(native_runtime.checked_package(self.package)[1], self.manifest)
        (self.package / "web/assets/app.js").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "哈希不一致"):
            native_runtime.checked_package(self.package)
        (self.package / "web/assets/app.js").write_bytes(b"window.app = true;\n")
        (self.root / ".git").mkdir()
        with self.assertRaisesRegex(RuntimeError, "Git checkout"):
            native_runtime.checked_package(self.package)

    def test_health_checks_api_proxy_and_exact_static_bytes(self):
        api, api_paths = self.service({"/health": b'{"status":"ok"}'})
        web_responses = {"/health": b'{"status":"ok"}'}
        for relative in ("index.html", "assets/app.js", "build-info.json"):
            web_responses[f"/{relative}"] = (self.package / "web" / relative).read_bytes()
        web, web_paths = self.service(web_responses)
        values = {"OA_NATIVE_API_HOST": "127.0.0.1", "OA_NATIVE_API_PORT": str(api.server_port),
                  "OA_NATIVE_WEB_HOST": "127.0.0.1", "OA_NATIVE_WEB_PORT": str(web.server_port)}
        with patch.dict(os.environ, values):
            self.assertEqual(native_runtime.health(self.package, self.manifest)["assets"], 1)
            self.assertEqual(api_paths, ["/health"])
            self.assertEqual(set(web_paths), set(web_responses))
            web_responses["/assets/app.js"] = b"wrong version"
            with self.assertRaisesRegex(RuntimeError, "运行包不一致"):
                native_runtime.health(self.package, self.manifest)

    def test_activation_restarts_verified_package_and_rolls_back_failure(self):
        candidate, candidate_manifest = self.make_package("candidate", "b" * 40)
        current = self.root / "current"
        current.symlink_to(self.package, target_is_directory=True)
        def switch_link(link: Path, package: Path) -> None:
            link.unlink()
            link.symlink_to(package, target_is_directory=True)

        with patch.dict(os.environ, {"OA_NATIVE_RUNTIME_CURRENT": str(current)}), patch.object(
            native_runtime, "atomic_link", side_effect=switch_link
        ), patch.object(
            native_runtime, "services"
        ) as services, patch.object(
            native_runtime, "await_health", return_value={"status": "passed"}
        ) as await_health:
            self.assertEqual(native_runtime.activate(candidate, current, candidate_manifest["source_commit"]),
                             {"status": "passed"})
            self.assertEqual(current.resolve(), candidate.resolve())
            services.assert_called_once_with("restart")
            await_health.assert_called_once_with(candidate.resolve(), candidate_manifest)
        with patch.dict(os.environ, {"OA_NATIVE_RUNTIME_CURRENT": str(current)}), patch.object(
            native_runtime, "atomic_link", side_effect=switch_link
        ), patch.object(
            native_runtime, "services"
        ) as services, patch.object(
            native_runtime, "await_health", side_effect=RuntimeError("健康检查失败")
        ):
            with self.assertRaisesRegex(RuntimeError, "已恢复旧版本"):
                native_runtime.activate(self.package, current, self.manifest["source_commit"])
            self.assertEqual(current.resolve(), candidate.resolve())
            self.assertEqual([call.args for call in services.call_args_list], [("restart",), ("restart",)])
        with patch.dict(os.environ, {"OA_NATIVE_RUNTIME_CURRENT": str(current)}), patch.object(
            native_runtime, "services"
        ) as services:
            with self.assertRaisesRegex(RuntimeError, "预期发布提交"):
                native_runtime.activate(self.package, current, "c" * 40)
            services.assert_not_called()

    def test_activation_rejects_configuration_mismatch(self):
        candidate, manifest = self.make_package("candidate", "b" * 40)
        current = self.root / "current"
        with (
            patch.dict(os.environ, {"OA_NATIVE_RUNTIME_CURRENT": str(self.root / "different")}),
            self.assertRaisesRegex(RuntimeError, "服务配置"),
        ):
            native_runtime.activate(candidate, current, manifest["source_commit"])
        self.assertFalse(current.exists())

    def test_environment_file_uses_strict_shared_values(self):
        config = self.root / "native-runtime.env"
        config.write_text("# 测试配置\nOA_NATIVE_RUNTIME_CURRENT=/srv/sunhold/current\nOA_NATIVE_API_PORT=8001\n", encoding="utf-8")
        config.chmod(0o600)
        with patch.dict(os.environ, {}):
            native_runtime.load_environment_file(config)
            self.assertEqual(os.environ["OA_NATIVE_API_PORT"], "8001")
        config.write_text("OA_NATIVE_API_PORT=\"8001\"\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "格式无效"):
            native_runtime.load_environment_file(config)

    @unittest.skipIf(os.name == "nt", "Windows 不支持覆盖现有目录符号链接；原子替换须在 Linux CI 验证")
    def test_atomic_link_replaces_existing_link(self):
        candidate, _ = self.make_package("candidate", "b" * 40)
        current = self.root / "current"
        current.symlink_to(self.package, target_is_directory=True)
        native_runtime.atomic_link(current, candidate)
        self.assertEqual(current.resolve(), candidate.resolve())
        self.assertEqual(list(self.root.glob("current.next-*")), [])

    def test_api_and_web_launch_use_package_without_reload(self):
        current = self.root / "current"
        current.symlink_to(self.package, target_is_directory=True)
        upload = self.root / "uploads"
        upload.mkdir()
        state = self.root / "web-state"
        state.mkdir()
        nginx = self.root / "nginx"
        nginx.write_bytes(b"test executable placeholder")
        mime = self.root / "mime.types"
        mime.write_text("types {}\n", encoding="utf-8")
        values = {
            "OA_NATIVE_RUNTIME_CURRENT": str(current), "APP_ENV": "production",
            "DATABASE_URL": "postgresql+asyncpg://test@localhost/test", "SECRET_KEY": "test-only",
            "INITIAL_ADMIN_PASSWORD": "test-only", "UPLOAD_ROOT": str(upload),
            "OA_NATIVE_PYTHON": sys.executable, "OA_NATIVE_API_HOST": "127.0.0.1",
            "OA_NATIVE_API_PORT": "19001", "OA_NATIVE_WEB_HOST": "127.0.0.1",
            "OA_NATIVE_WEB_PORT": "19002", "OA_NATIVE_WEB_STATE_DIR": str(state),
            "OA_NATIVE_NGINX": str(nginx), "OA_NATIVE_MIME_TYPES": str(mime),
        }
        with patch.dict(os.environ, values), patch.object(native_runtime.os, "chdir") as chdir, patch.object(
            native_runtime.os, "execve", side_effect=RuntimeError("命令已截获")
        ) as execute:
            with self.assertRaisesRegex(RuntimeError, "命令已截获"):
                native_runtime.start_api()
            command = execute.call_args.args[1]
            self.assertNotIn("--reload", command)
            self.assertEqual(command[2:4], ["uvicorn", "app.main:app"])
            self.assertEqual(execute.call_args.args[2]["PYTHONPATH"], str(self.package.resolve() / "api"))
            chdir.assert_called_once_with(self.package.resolve() / "api")
        with patch.dict(os.environ, values), patch.object(
            native_runtime.subprocess, "run"
        ) as nginx_check, patch.object(native_runtime.os, "execve", side_effect=RuntimeError("命令已截获")) as execute:
            with self.assertRaisesRegex(RuntimeError, "命令已截获"):
                native_runtime.start_web()
            nginx_check.assert_called_once()
            self.assertEqual(nginx_check.call_args.args[0][1], "-t")
            self.assertIn("daemon off;", execute.call_args.args[1])
            config = (state / "nginx.conf").read_text(encoding="utf-8")
            self.assertIn(str((self.package.resolve() / "web").as_posix()), config)
            self.assertIn("location /api/", config)
            self.assertIn("location = /health", config)
            import_location = re.search(
                r"location = /api/v1/finance/incoming-payments/import \{([^}]*)\}", config, re.DOTALL
            )
            self.assertIsNotNone(import_location)
            self.assertEqual(config.count("location = /api/v1/finance/incoming-payments/import"), 1)
            for directive in (
                "client_max_body_size 101m;", "client_body_timeout 600s;",
                "proxy_connect_timeout 5s;", "proxy_read_timeout 600s;", "proxy_send_timeout 600s;",
                "proxy_pass http://127.0.0.1:19001;",
            ):
                self.assertIn(directive, import_location.group(1))
            api_location = re.search(r"location /api/ \{([^}]*)\}", config, re.DOTALL)
            self.assertIsNotNone(api_location)
            self.assertIn("proxy_read_timeout 120s;", api_location.group(1))
            self.assertIn("proxy_send_timeout 120s;", api_location.group(1))
            self.assertIn("client_max_body_size 21m;", config)
            self.assertTrue((state / "client-body").is_dir())
            self.assertTrue((state / "proxy").is_dir())


class SourceQualityGateTest(unittest.TestCase):
    """发布前源码门禁不能被构建、旧报告或不同提交替代。"""

    def test_github_actions_rejects_default_and_explicit_full_before_checks(self):
        with tempfile.TemporaryDirectory(prefix="oa-test-github-full-rejection-") as directory:
            for profile_args in ([], ["--profile", "full"]):
                with self.subTest(profile_args=profile_args):
                    errors = io.StringIO()
                    with (
                        patch.object(sys, "argv", ["quality_gate.py", "--report-dir", directory, *profile_args]),
                        patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}),
                        patch.object(quality_gate.shutil, "which") as discover,
                        patch.object(quality_gate.subprocess, "check_output") as check,
                        patch.object(quality_gate.subprocess, "run") as execute,
                        redirect_stderr(errors),
                        self.assertRaises(SystemExit) as rejected,
                    ):
                        quality_gate.main()
                    self.assertEqual(rejected.exception.code, 2)
                    self.assertIn("GitHub Actions 禁止运行 full", errors.getvalue())
                    discover.assert_not_called()
                    check.assert_not_called()
                    execute.assert_not_called()

    def source_evidence(self, report_dir: Path) -> tuple[dict, dict]:
        report_dir.mkdir(parents=True, exist_ok=True)
        pending = [{"file": "test_postgres_startup_migrations.py", "status": "DEFERRED", "passed": False}]
        backend = {"execution_profile": "source", "total": 1, "passed": 1, "partial": 0,
                   "failed": 0, "skipped": 0, "excluded": [], "failures": [], "skips": [],
                   "deferred": pending, "pending_full": [], "results": [
                       {"file": "test_local.py", "status": "PASS", "exit_code": 0, "executed_methods": 1, "skipped_methods": 0},
                   ]}
        report = {"profile": "source", "passed": True, "source_commit": "a" * 40,
                  "backend_scope": quality_gate.SOURCE_BACKEND_SCOPE,
                  "pending_ci": ["完整 regression", "PostgreSQL 专用回归与集成"], "backend_pending_ci": pending, "steps": []}
        for name in quality_gate.SOURCE_STEPS:
            log = report_dir / f"{name}.log"
            log.write_text("successful isolated fixture\n", encoding="utf-8")
            report["steps"].append({"name": name, "exit_code": 0, "seconds": 0.1, "log": str(log)})
        (report_dir / "quality-gate.json").write_text(json.dumps(report), encoding="utf-8")
        (report_dir / "backend-regression.json").write_text(json.dumps(backend), encoding="utf-8")
        return report, backend

    def test_receipt_rejects_zero_execution_and_incomplete_file_results(self):
        with tempfile.TemporaryDirectory(prefix="oa-test-receipt-counts-") as temporary:
            report_dir = Path(temporary).resolve()
            _, backend = self.source_evidence(report_dir)
            quality_gate.validate_source_backend({**backend, "passed": 0, "partial": 1,
                                                  "results": [{**backend["results"][0], "status": "PARTIAL"}]})
            invalid = [
                [], None,
                {**backend, "passed": 0}, {**backend, "results": []},
                {**backend, "results": [{**backend["results"][0], "executed_methods": 0}]},
                {**backend, "results": [{"file": "test_local.py", "status": "PASS", "exit_code": 0}]},
                {**backend, "passed": 0, "results": [{**backend["results"][0], "status": "EXCLUDED", "executed_methods": 0}]},
            ]
            for report in invalid:
                with self.subTest(report=report):
                    (report_dir / "backend-regression.json").write_text(json.dumps(report), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "后端"):
                        quality_gate.receipt_evidence(report_dir, "a" * 40)

    def test_cached_report_retains_original_steps_and_pending_scope(self):
        with tempfile.TemporaryDirectory(prefix="oa-test-cache-scope-") as temporary:
            root = Path(temporary).resolve()
            original = root / "original"
            report, _ = self.source_evidence(original)
            fingerprint = {"commit": "a" * 40}
            receipt = root / "git/source-receipt.json"
            quality_gate.write_source_receipt(receipt, fingerprint, original)
            evidence = quality_gate.receipt_evidence(original, "a" * 40)
            self.assertIn("backend-runner-selfcheck.log", evidence)
            requested = root / "requested"
            with (
                patch.object(sys, "argv", ["quality_gate.py", "--profile", "source", "--push-commit", "a" * 40, "--report-dir", str(requested)]),
                patch.object(quality_gate.shutil, "which", return_value="node"),
                patch.object(quality_gate.subprocess, "check_output", side_effect=lambda command, **_kwargs: "v22.20.0" if command[-1] == "--version" else str(receipt)),
                patch.object(quality_gate, "source_fingerprint", return_value=fingerprint),
                patch.object(quality_gate, "assert_push_source"),
                patch.object(quality_gate, "inspect_production_sources") as inspect,
                patch.object(quality_gate.subprocess, "run") as execute,
            ):
                self.assertEqual(quality_gate.main(), 0)
            reused = json.loads((requested / "quality-gate.json").read_text(encoding="utf-8"))
            for key in ("profile", "steps", "backend_scope", "pending_ci", "backend_pending_ci", "source_commit"):
                self.assertEqual(reused[key], report[key])
            self.assertEqual(reused["reused_report"], str(original))
            self.assertEqual(quality_gate.receipt_evidence(original, "a" * 40), evidence)
            inspect.assert_not_called()
            execute.assert_not_called()

    def invoke_gate(self, profile: str, failed_output: str = "", failed_command: str = "tests/run-unit.mjs") -> tuple[int, dict, list[str], str]:
        with tempfile.TemporaryDirectory(prefix="oa-test-source-gate-") as temporary:
            report = Path(temporary)
            commands = []

            def execute(command, **_kwargs):
                commands.append(command)
                environment = _kwargs["env"]
                self.assertEqual(environment["APP_ENV"], "testing")
                self.assertEqual(environment["DATABASE_URL"], "sqlite+aiosqlite:///:memory:")
                self.assertTrue(Path(environment["UPLOAD_ROOT"]).is_dir())
                if profile == "source":
                    self.assertNotIn("OA_TEST_POSTGRES_URL", environment)
                    self.assertNotIn("OA_TEST_API_BASE", environment)
                    self.assertNotIn("GIT_DIR", environment)
                if "tests.test_regression_runner" in command:
                    self.assertEqual(_kwargs["cwd"], quality_gate.API)
                failed = failed_output and failed_command in command
                if "tests/run_regression.py" in command:
                    (report / "backend-regression.json").write_text(json.dumps({
                        "execution_profile": "source", "total": 1, "passed": 1, "partial": 0,
                        "scope": {"groups": ["unit", "structural"], "regression_files": [
                            "case_agent_mvp_contract_test.py", "deepseek_harness_runtime_test.py",
                            "case_word_editor_contract_test.py", "case_word_editor_independent_test.py",
                        ]},
                        "failed": 0, "skipped": 0, "excluded": [], "failures": [], "skips": [],
                        "results": [{"file": "test_local.py", "status": "PASS", "exit_code": 0, "executed_methods": 1, "skipped_methods": 0}],
                        "deferred": [{"file": "test_agent_commands_postgres.py", "status": "DEFERRED", "passed": False}],
                        "pending_full": [{"file": "test_domain_route_storage.py", "status": "NOT_PASSED", "skipped_methods": 9}],
                    }), encoding="utf-8")
                return subprocess.CompletedProcess(command, 1 if failed else 0, failed_output if failed else "", "")

            # 旧成功报告不能放行新的失败；回归数据只存在于独立临时目录。
            (report / "quality-gate.json").write_text('{"passed": true}', encoding="utf-8")
            errors = io.StringIO()
            with (
                patch.object(sys, "argv", ["quality_gate.py", "--profile", profile, "--report-dir", str(report)]),
                patch.object(quality_gate.shutil, "which", return_value=str(report / "node")),
                patch.object(quality_gate.subprocess, "check_output", side_effect=lambda command, **_kwargs: "v22.20.0\n" if command[-1] == "--version" else "GIT_DIR\nGIT_WORK_TREE\n"),
                patch.object(quality_gate.subprocess, "run", side_effect=execute),
                patch.object(quality_gate, "inspect_production_sources"),
                patch.dict(os.environ, {"OA_TEST_POSTGRES_URL": "must-not-use", "OA_TEST_API_BASE": "must-not-use", "GIT_DIR": "must-not-use", "GITHUB_ACTIONS": "false"}),
                redirect_stderr(errors),
            ):
                result = quality_gate.main()
            summary = json.loads((report / "quality-gate.json").read_text(encoding="utf-8"))
            return result, summary, commands, errors.getvalue()

    def test_source_runs_all_frontend_units_and_fixed_backend_scope_without_building(self):
        result, summary, commands, _ = self.invoke_gate("source")
        self.assertEqual(result, 0)
        self.assertTrue(summary["passed"])
        self.assertEqual([step["name"] for step in summary["steps"]], [
            "backend-static", "backend-runner-selfcheck", "quality-tools", "frontend-unit", "client-api-contract", "menu-route-coverage", "backend-regression",
        ])
        self.assertEqual(commands[1][1:], ["-m", "unittest", "tests.test_regression_runner"])
        self.assertEqual(commands[3][1:], ["tests/run-unit.mjs"])
        self.assertEqual(commands[-1][1:9], ["tests/run_regression.py", "--group", "unit", "--group", "regression", "--group", "structural", "--exclude-category"])
        self.assertEqual(commands[-1][-2:], ["--execution-profile", "source"])
        self.assertEqual(summary["backend_scope"]["groups"], ["unit", "structural"])
        self.assertEqual(len(summary["backend_scope"]["regression_files"]), 4)
        self.assertIn("完整 regression", summary["pending_ci"])
        self.assertEqual([item["status"] for item in summary["backend_pending_ci"]], ["DEFERRED", "NOT_PASSED"])
        self.assertIn("PostgreSQL 专用回归与集成", summary["pending_ci"])
        for profile in ("source", "full", "static"):
            with self.subTest(profile=profile):
                result, summary, _, errors = self.invoke_gate(
                    profile, "FAIL: nested fixture\nIndexError: 1\n", "tests.test_regression_runner",
                )
                self.assertEqual(result, 1)
                self.assertFalse(summary["passed"])
                self.assertEqual([step["name"] for step in summary["steps"]], [
                    "backend-static", "backend-runner-selfcheck",
                ])
                self.assertIn("IndexError: 1", errors)

    def test_static_keeps_build_and_runtime_checks(self):
        result, summary, _, _ = self.invoke_gate("static")
        self.assertEqual(result, 0)
        self.assertEqual([step["name"] for step in summary["steps"]][-4:], [
            "frontend-build", "runtime-package", "runtime-integrity", "runtime-health",
        ])

    def test_both_ci_failure_classes_reject_stale_success_and_print_diagnostics(self):
        for diagnostic in ("MODULE_NOT_FOUND '../../AgentOperationPreview'", "AgentOperationPreview still imports AntD Table directly"):
            with self.subTest(diagnostic=diagnostic):
                result, summary, _, errors = self.invoke_gate("source", f"not ok 2 - frontend regression\n{diagnostic}\n# fail 1\n")
                self.assertEqual(result, 1)
                self.assertFalse(summary["passed"])
                self.assertEqual(summary["steps"][-1]["name"], "frontend-unit")
                self.assertIn(diagnostic, errors)

    def test_failure_summary_is_bounded_and_keeps_ruff_and_node_diagnostics(self):
        for diagnostic in ("F401 unused import\n --> app/main.py:1:1", "not ok 2 - module import\nMODULE_NOT_FOUND"):
            errors = io.StringIO()
            with redirect_stderr(errors):
                quality_gate.print_failure_summary("checks", diagnostic + "\n" + "x" * 1000 + "\n" + "not ok many\ndetail\n" * 1000)
            self.assertIn(diagnostic, errors.getvalue())
            self.assertIn("摘要已截断", errors.getvalue())
            self.assertLess(len(errors.getvalue()), 13000)

    def test_receipt_requires_same_inputs_and_complete_success_evidence(self):
        with tempfile.TemporaryDirectory(prefix="oa-test-quality-receipt-") as temporary:
            root = Path(temporary).resolve()
            report_dir = root / "evidence"
            report_dir.mkdir()
            receipt = root / "git/source-receipt.json"
            fingerprint = {"commit": "a" * 40, "python": "3.12.14", "node": "v22.20.0", "locks": {"dependencies": "sha256"}}
            report = {"profile": "source", "passed": True, "source_commit": fingerprint["commit"], "steps": []}
            for name in quality_gate.SOURCE_STEPS:
                log = report_dir / f"{name}.log"
                log.write_text("successful isolated fixture\n", encoding="utf-8")
                report["steps"].append({"name": name, "exit_code": 0, "log": str(log)})
            report_file = report_dir / "quality-gate.json"
            report_file.write_text(json.dumps(report), encoding="utf-8")
            backend_report = report_dir / "backend-regression.json"
            backend = {"execution_profile": "source", "total": 1, "passed": 1, "partial": 0,
                       "failed": 0, "skipped": 0, "excluded": [], "failures": [], "skips": [],
                       "deferred": [], "pending_full": [], "results": [
                           {"file": "test_local.py", "status": "PASS", "exit_code": 0, "executed_methods": 1, "skipped_methods": 0},
                       ]}
            backend_report.write_text(json.dumps(backend), encoding="utf-8")
            self.assertIsNone(quality_gate.reusable_source_receipt(receipt, fingerprint))
            quality_gate.write_source_receipt(receipt, fingerprint, report_dir)
            self.assertEqual(quality_gate.reusable_source_receipt(receipt, fingerprint), report_dir)
            self.assertEqual(list(receipt.parent.glob(".source-receipt.json-*.tmp")), [])
            created = json.loads(receipt.read_text(encoding="utf-8"))["created_at"]
            with patch.object(quality_gate.time, "time", return_value=created + quality_gate.SOURCE_RECEIPT_MAX_AGE_SECONDS + 1):
                self.assertIsNone(quality_gate.reusable_source_receipt(receipt, fingerprint))
            for key, changed in (("commit", "b" * 40), ("python", "3.12.15"), ("node", "v22.21.0"), ("locks", {"dependencies": "new-sha256"})):
                with self.subTest(changed=key):
                    self.assertIsNone(quality_gate.reusable_source_receipt(receipt, {**fingerprint, key: changed}))
            (report_dir / "frontend-unit.log").write_text("tampered\n", encoding="utf-8")
            self.assertIsNone(quality_gate.reusable_source_receipt(receipt, fingerprint))
            (report_dir / "frontend-unit.log").write_text("successful isolated fixture\n", encoding="utf-8")
            backend_report.unlink()
            self.assertIsNone(quality_gate.reusable_source_receipt(receipt, fingerprint))
            backend_report.write_text(json.dumps({**backend, "failed": 1}), encoding="utf-8")
            self.assertIsNone(quality_gate.reusable_source_receipt(receipt, fingerprint))
            backend_report.write_text(json.dumps(backend), encoding="utf-8")
            report["passed"] = False
            report_file.write_text(json.dumps(report), encoding="utf-8")
            self.assertIsNone(quality_gate.reusable_source_receipt(receipt, fingerprint))
            with self.assertRaisesRegex(ValueError, "不是完整成功"):
                quality_gate.write_source_receipt(receipt, fingerprint, report_dir)
            for unknown in ('{"passed": true}', '[]', 'invalid-json'):
                receipt.write_text(unknown, encoding="utf-8")
                self.assertIsNone(quality_gate.reusable_source_receipt(receipt, fingerprint))

    def test_receipt_refuses_directory_and_file_links(self):
        with tempfile.TemporaryDirectory(prefix="oa-test-receipt-links-") as temporary:
            root = Path(temporary).resolve()
            actual = root / "actual"
            actual.mkdir()
            linked = root / "linked"
            linked.symlink_to(actual, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "符号链接"):
                quality_gate.reusable_source_receipt(linked / "receipt.json", {})
            receipt = root / "receipt.json"
            receipt.symlink_to(actual / "missing.json")
            with self.assertRaisesRegex(ValueError, "符号链接"):
                quality_gate.write_source_receipt(receipt, {}, root)
            self.assertFalse((actual / "missing.json").exists())

    def test_fingerprint_binds_parameters_environment_and_dependency_files(self):
        with tempfile.TemporaryDirectory(prefix="oa-test-gate-fingerprint-") as temporary:
            root = Path(temporary).resolve()
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            api, web = root / "api", root / "web"
            files = (api / "requirements.lock", root / "requirements-dev.lock", web / "package.json",
                     web / "package-lock.json", web / "node_modules/.package-lock.json")
            for path in files:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("isolated dependency fixture\n", encoding="utf-8")
            with patch.object(quality_gate, "ROOT", root), patch.object(quality_gate, "API", api), patch.object(
                quality_gate, "WEB", web
            ), patch.object(quality_gate, "distributions", return_value=[]):
                fingerprint = quality_gate.source_fingerprint("a" * 40, "node", "v22.20.0", 2)
                self.assertEqual(fingerprint, json.loads(json.dumps(fingerprint)))
                self.assertNotEqual(fingerprint, quality_gate.source_fingerprint("a" * 40, "node", "v22.20.0", 1))
                with patch.dict(os.environ, {"OA_GATE_PARAMETER": "changed"}):
                    self.assertNotEqual(fingerprint, quality_gate.source_fingerprint("a" * 40, "node", "v22.20.0", 2))
                config = root / "global.gitconfig"
                config.write_text("[core]\n    hooksPath = first-hooks\n", encoding="utf-8")
                with patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(config)}):
                    changed = quality_gate.source_fingerprint("a" * 40, "node", "v22.20.0", 2)
                    self.assertNotEqual(fingerprint, changed)
                    config.write_text("[core]\n    hooksPath = second-hooks\n", encoding="utf-8")
                    self.assertNotEqual(changed, quality_gate.source_fingerprint("a" * 40, "node", "v22.20.0", 2))
                    self.assertNotIn("first-hooks", json.dumps(changed))
                    self.assertNotIn(str(config), json.dumps(changed))
                with patch.dict(os.environ, {"GIT_UNKNOWN_QUALITY_SETTING": "changed"}):
                    self.assertNotEqual(fingerprint, quality_gate.source_fingerprint("a" * 40, "node", "v22.20.0", 2))
                files[-1].write_text("changed installed dependency lock\n", encoding="utf-8")
                self.assertNotEqual(fingerprint, quality_gate.source_fingerprint("a" * 40, "node", "v22.20.0", 2))

    def test_hook_installer_preserves_external_hooks_and_updates_managed_templates(self):
        with tempfile.TemporaryDirectory(prefix="oa-test-hook-installer-") as temporary:
            root = Path(temporary).resolve()
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            template = root / ".githooks/pre-push"
            template.parent.mkdir()
            content = (SCRIPTS.parent / ".githooks/pre-push").read_text(encoding="utf-8").replace("\r\n", "\n")
            template.write_text(content, encoding="utf-8", newline="\n")
            hook = root / ".git/hooks/pre-push"
            shell = "powershell" if os.name == "nt" else "pwsh"
            setup = str(SCRIPTS / "setup-local.ps1").replace("'", "''")
            target = str(root).replace("'", "''")
            command = [shell, "-NoProfile", "-Command", f"$ErrorActionPreference='Stop'; . '{setup}'; $root='{target}'; Install-QualityPrePushHook"]

            def install(code):
                completed = subprocess.run(command, capture_output=True, encoding="utf-8")
                self.assertEqual(completed.returncode, code, completed.stdout + completed.stderr)
                return completed

            install(0)
            self.assertEqual(hook.read_text(encoding="utf-8"), content)
            install(0)
            hook.write_text(content + "# 旧受管理模板\n", encoding="utf-8", newline="\n")
            install(0)
            self.assertEqual(hook.read_text(encoding="utf-8"), content)
            self.assertNotIn(b"\r", hook.read_bytes())
            self.assertFalse(hook.read_bytes().startswith(b"\xef\xbb\xbf"))
            if os.name != "nt":
                self.assertTrue(os.access(hook, os.X_OK))
            external = "#!/bin/sh\nexit 42\n"
            hook.write_text(external, encoding="utf-8", newline="\n")
            install(1)
            self.assertEqual(hook.read_text(encoding="utf-8"), external)
            subprocess.run(["git", "-C", str(root), "config", "core.hooksPath", ".custom-hooks"], check=True)
            self.assertIn("core.hooksPath", install(1).stderr)
            self.assertEqual(hook.read_text(encoding="utf-8"), external)
            subprocess.run(["git", "-C", str(root), "config", "core.hooksPath", ""], check=True)
            self.assertIn("core.hooksPath", install(1).stderr)

    def test_hook_selects_remote_targets_and_requires_explicit_runtimes(self):
        with tempfile.TemporaryDirectory(prefix="oa-test-push-hook-") as temporary:
            root = Path(temporary).resolve()
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            template = SCRIPTS.parent / ".githooks/pre-push"
            hook = root / ".git/hooks/pre-push"
            hook.write_bytes(template.read_bytes().replace(b"\r\n", b"\n"))
            hook.chmod(0o755)
            data = root / "push-input.txt"
            environment = os.environ.copy()
            environment.pop("OA_QUALITY_PYTHON", None)
            environment.pop("OA_QUALITY_NODE", None)
            cases = (
                (f"refs/heads/main {'a' * 40} refs/heads/feature {'0' * 40}\n", 0, ""),
                (f"refs/heads/feature {'a' * 40} refs/heads/dev {'0' * 40}\n", 1, "OA_QUALITY_PYTHON"),
                (f"refs/heads/dev {'a' * 40} refs/heads/main {'0' * 40}\n", 1, "OA_QUALITY_PYTHON"),
                (f"(delete) {'0' * 40} refs/heads/dev {'a' * 40}\n", 1, "deleting dev/main"),
                (f"x {'a' * 40} refs/heads/dev {'0' * 40}\ny {'b' * 40} refs/heads/main {'0' * 40}\n", 1, "same checked commit"),
            )
            for payload, code, diagnostic in cases:
                with self.subTest(payload=payload):
                    data.write_text(payload, encoding="utf-8")
                    completed = subprocess.run(["git", "hook", "run", f"--to-stdin={data}", "pre-push"], cwd=root, env=environment, capture_output=True, encoding="utf-8")
                    self.assertEqual(completed.returncode, code, completed.stderr)
                    self.assertIn(diagnostic, completed.stderr)

    def test_hook_forwards_explicit_jobs_and_rejects_invalid_values(self):
        with tempfile.TemporaryDirectory(prefix="oa-test-hook-jobs-") as temporary:
            root = Path(temporary).resolve()
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            hook = root / ".git/hooks/pre-push"
            hook.write_bytes((SCRIPTS.parent / ".githooks/pre-push").read_bytes().replace(b"\r\n", b"\n"))
            hook.chmod(0o755)
            script = root / "scripts/quality_gate.py"
            script.parent.mkdir()
            script.write_text("import json, sys\nprint('HOOK_ARGUMENTS=' + json.dumps(sys.argv[1:]))\n", encoding="utf-8")
            data = root / "push-input.txt"
            data.write_text(f"x {'a' * 40} refs/heads/dev {'0' * 40}\n", encoding="utf-8")
            reports = root / "reports"
            reports.mkdir()
            environment = {**os.environ, "OA_QUALITY_PYTHON": sys.executable, "OA_QUALITY_NODE": "explicit-node", "TMPDIR": str(reports)}
            for jobs in (None, "6", "0", "-1", "unknown"):
                with self.subTest(jobs=jobs):
                    environment.pop("OA_QUALITY_JOBS", None)
                    if jobs is not None:
                        environment["OA_QUALITY_JOBS"] = jobs
                    completed = subprocess.run(["git", "hook", "run", f"--to-stdin={data}", "pre-push"], cwd=root, env=environment, capture_output=True, encoding="utf-8")
                    if jobs in (None, "6"):
                        self.assertEqual(completed.returncode, 0, completed.stderr)
                        lines = [line.removeprefix("HOOK_ARGUMENTS=") for line in (completed.stdout + completed.stderr).splitlines() if line.startswith("HOOK_ARGUMENTS=")]
                        self.assertEqual(len(lines), 1)
                        arguments = json.loads(lines[0])
                        self.assertEqual(arguments[arguments.index("--jobs") + 1], jobs or "2")
                        Path(arguments[arguments.index("--report-dir") + 1]).rmdir()
                    else:
                        self.assertNotEqual(completed.returncode, 0)
                        self.assertIn("OA_QUALITY_JOBS", completed.stderr)

    def test_push_checks_real_git_head_and_clean_source(self):
        with tempfile.TemporaryDirectory(prefix="oa-test-push-source-") as temporary:
            root = Path(temporary).resolve()

            def git(*arguments):
                return subprocess.check_output(["git", *arguments], cwd=root, text=True, encoding="utf-8", stderr=subprocess.STDOUT).strip()

            git("init")
            source = root / "source.txt"
            source.write_text("original\n", encoding="utf-8")
            git("add", "--", "source.txt")
            git("-c", "user.name=Quality gate", "-c", "user.email=quality@example.invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=", "commit", "-m", "isolated gate fixture")
            first = git("rev-parse", "HEAD")
            with patch.object(quality_gate, "ROOT", root):
                quality_gate.assert_push_source(first)
                source.write_text("uncommitted fix\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "工作树必须干净"):
                    quality_gate.assert_push_source(first)
                git("add", "--", "source.txt")
                git("-c", "user.name=Quality gate", "-c", "user.email=quality@example.invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=", "commit", "-m", "second isolated fixture")
                with self.assertRaisesRegex(ValueError, "不是当前 HEAD"):
                    quality_gate.assert_push_source(first)
                quality_gate.assert_push_source(git("rev-parse", "HEAD"))
                (root / "untracked.txt").write_text("not checked in\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "工作树必须干净"):
                    quality_gate.assert_push_source(git("rev-parse", "HEAD"))
                with self.assertRaisesRegex(ValueError, "完整的小写"):
                    quality_gate.assert_push_source(first[:8])


if __name__ == "__main__":
    unittest.main()
