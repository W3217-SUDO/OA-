"""统一执行本地与 CI 的质量检查，逐步保存失败证据。"""

from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps/api-server"
WEB = ROOT / "apps/admin-web"


def inspect_production_sources() -> None:
    """语法检查不生成缓存；禁止测试入口进入正式源码。"""
    for directory in (API / "app", WEB / "src"):
        for path in directory.rglob("*"):
            if path.is_symlink():
                raise ValueError(f"正式源码包含符号链接：{path.relative_to(ROOT)}")
            if not path.is_file():
                continue
            name = path.name.lower()
            if (
                name.startswith("test_") or ".test." in name or "_test." in name
                or any(part.lower() in {"tests", "fixtures", "mocks", "stubs"} for part in path.relative_to(directory).parts)
            ):
                raise ValueError(f"测试文件进入正式源码：{path.relative_to(ROOT)}")
            if path.suffix == ".py":
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                if path.is_relative_to(API / "app/core"):
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app.areas.") and node.module.endswith(".router"):
                            raise ValueError(f"领域服务反向依赖 HTTP 路由：{path.relative_to(ROOT)}:{node.lineno}")
            elif path.suffix in {".ts", ".tsx", ".mjs", ".js", ".json", ".css"}:
                path.read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, required=True, help="源码目录以外的检查日志目录")
    parser.add_argument("--node", default="node", help="Node.js 22 可执行文件")
    parser.add_argument("--profile", choices=("full", "static"), default="full")
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    report_dir = args.report_dir.expanduser().resolve()
    if report_dir.is_relative_to(ROOT):
        parser.error("证据目录必须位于项目源码目录之外")
    if args.jobs < 1:
        parser.error("jobs 必须大于零")
    if sys.version_info[:2] != (3, 12):
        parser.error("正式目标环境要求 Python 3.12")
    resolved_node = shutil.which(args.node)
    if not resolved_node:
        parser.error(f"找不到 Node.js 可执行文件：{args.node}")
    args.node = str(Path(resolved_node).resolve())
    version = subprocess.check_output([args.node, "--version"], text=True, encoding="utf-8").strip()
    if not version.startswith("v22."):
        parser.error(f"正式目标环境要求 Node.js 22，当前 {version}")
    report_dir.mkdir(parents=True, exist_ok=True)
    summary = {"profile": args.profile, "python": sys.version.split()[0], "node": version, "steps": [], "passed": False}

    def save() -> None:
        (report_dir / "quality-gate.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def run(name: str, command: list[str], cwd: Path, environment: dict[str, str]) -> None:
        started = time.monotonic()
        print(f"执行 {name}", flush=True)
        completed = subprocess.run(command, cwd=cwd, env=environment, capture_output=True, encoding="utf-8")
        log = report_dir / f"{name}.log"
        log.write_text(completed.stdout + completed.stderr, encoding="utf-8")
        summary["steps"].append({"name": name, "exit_code": completed.returncode, "seconds": round(time.monotonic() - started, 3), "log": str(log)})
        save()
        if completed.returncode:
            raise RuntimeError(f"{name} 失败（退出码 {completed.returncode}），详情：{log}")
        print(f"通过 {name}", flush=True)

    save()
    try:
        inspect_production_sources()
        with tempfile.TemporaryDirectory(prefix="oa-test-quality-gate-") as temporary:
            environment = os.environ.copy()
            environment.update(
                APP_ENV="testing", DATABASE_URL="sqlite+aiosqlite:///:memory:",
                UPLOAD_ROOT=temporary, SEED_DEMO_DATA="false", PYTHONIOENCODING="utf-8",
                PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(API),
            )
            environment["PATH"] = str(Path(args.node).resolve().parent) + os.pathsep + environment.get("PATH", "")
            run("backend-static", [sys.executable, "-m", "ruff", "check", str(API / "app")], ROOT, environment)
            run("quality-tools", [sys.executable, "-m", "unittest", "discover", "-s", "tests/quality", "-p", "test_*.py"], ROOT, environment)
            run("frontend-unit", [args.node, "tests/run-unit.mjs"], WEB, environment)
            run("client-api-contract", [sys.executable, "scripts/audit-client-api-coverage.py"], ROOT, environment)
            run("menu-route-coverage", [sys.executable, "scripts/audit-menu-coverage.py"], ROOT, environment)
            run("frontend-build", [args.node, "scripts/build-production.mjs"], WEB, environment)
            if args.profile == "full":
                required_databases = (
                    "OA_TEST_POSTGRES_URL", "OUTBOX_TEST_POSTGRES_URL",
                    "AGENT_COMMANDS_TEST_POSTGRES_URL", "INCOMING_QUERY_TEST_POSTGRES_URL",
                    "ARCHIVE_EVIDENCE_TEST_POSTGRES_URL", "FILE_IO_TEST_POSTGRES_URL",
                    "CUSTOMER_TASK_TEST_POSTGRES_URL", "BUSINESS_RULE_TEST_POSTGRES_URL",
                    "FINANCE_SELECTED_TEST_POSTGRES_URL", "TASK_PROJECTION_TEST_POSTGRES_URL",
                    "TASK_QUERY_TEST_POSTGRES_URL", "DASHBOARD_DATES_TEST_POSTGRES_URL",
                    "OA_TEST_POSTGRES_DSN", "OA_ROUTE_EFFECTS_POSTGRES_URL",
                )
                missing_databases = [name for name in required_databases if not environment.get(name)]
                if missing_databases:
                    raise ValueError("完整门禁要求隔离 PostgreSQL 测试配置：" + ", ".join(missing_databases))
                run("backend-regression", [sys.executable, "tests/run_regression.py", "--group", "unit", "--group", "regression", "--group", "structural", "--exclude-category", "permissions", "--jobs", str(args.jobs), "--report", str(report_dir / "backend-regression.json")], API, environment)
                run("postgres-domain-boundaries", [sys.executable, "tests/run_regression.py", "--group", "integration", "--file", "postgres_domain_boundaries_test.py", "--report", str(report_dir / "postgres-domain.json")], API, environment)
                run("backend-dependencies", [sys.executable, "-m", "pip_audit", "-r", str(API / "requirements.lock"), "--format", "json", "--output", str(report_dir / "backend-dependencies.json")], ROOT, environment)
                npm = "npm.cmd" if os.name == "nt" else "npm"
                run("frontend-dependencies", [npm, "audit", "--audit-level=low"], WEB, environment)
                run("harness-dependencies", [npm, "exec", "--yes", "--package=pnpm@11.24.0", "--", "pnpm", "audit", "--audit-level=low"], ROOT / "apps/deepseek-harness-host", environment)
                run("harness-health", [sys.executable, "scripts/verify_harness.py", "--node", args.node, "--report-dir", str(report_dir)], ROOT, environment)
            runtime = report_dir / "runtime"
            run("runtime-package", [sys.executable, "scripts/runtime_package.py", "build", "--output", str(runtime)], ROOT, environment)
            run("runtime-integrity", [sys.executable, "scripts/runtime_package.py", "verify", "--output", str(runtime)], ROOT, environment)
            run("runtime-health", [sys.executable, "scripts/verify_runtime.py", "--package", str(runtime), "--report-dir", str(report_dir)], ROOT, environment)
            summary["passed"] = True
            save()
    except Exception as exc:
        summary["error"] = str(exc)
        save()
        print(str(exc), file=sys.stderr)
        return 1
    print(f"质量检查完成，范围：{args.profile}，报告：{report_dir / 'quality-gate.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
