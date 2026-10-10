"""统一执行本地与 CI 的质量检查，逐步保存失败证据。"""

from __future__ import annotations

import argparse
import ast
import hashlib
from importlib.metadata import distributions
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps/api-server"
WEB = ROOT / "apps/admin-web"
SOURCE_STEPS = ("backend-static", "backend-runner-selfcheck", "quality-tools", "frontend-unit", "client-api-contract", "menu-route-coverage", "backend-regression")
SOURCE_RECEIPT_MAX_AGE_SECONDS = 2 * 60 * 60
SOURCE_BACKEND_SCOPE = "unit + structural + four fixed regression files"


def source_git_environment() -> dict[str, str]:
    environment = os.environ.copy()
    local_variables = subprocess.check_output(
        ["git", "rev-parse", "--local-env-vars"], cwd=ROOT, text=True, encoding="utf-8",
    ).splitlines()
    for name in local_variables:
        environment.pop(name, None)
    return environment


def source_fingerprint(commit: str, node: str, node_version: str, jobs: int) -> dict:
    """回执绑定正式运行时、锁文件及本次实际安装的依赖。"""
    paths = (
        API / "requirements.lock", ROOT / "requirements-dev.lock",
        WEB / "package.json", WEB / "package-lock.json", WEB / "node_modules/.package-lock.json",
    )
    locks = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    installed = sorted((item.metadata["Name"], item.version) for item in distributions())
    overridden = {"APP_ENV", "DATABASE_URL", "UPLOAD_ROOT", "SEED_DEMO_DATA", "PYTHONIOENCODING", "PYTHONDONTWRITEBYTECODE", "PYTHONPATH"}
    volatile = {"PWD", "OLDPWD", "SHLVL", "_", "OA_ROUTE_EFFECTS_POSTGRES_URL", "OA_TEST_API_BASE"}
    inherited = source_git_environment()
    environment = sorted((name, value) for name, value in inherited.items()
                         if name not in overridden | volatile and "TEST_POSTGRES" not in name)
    configuration = subprocess.check_output(
        ["git", "config", "--null", "--list", "--show-origin", "--show-scope"], cwd=ROOT, env=inherited,
    )
    return {
        "commit": commit, "python": sys.version, "python_executable": str(Path(sys.executable).resolve()),
        "node": node_version, "node_executable": node, "locks": locks,
        "python_dependencies": hashlib.sha256(json.dumps(installed).encode("utf-8")).hexdigest(),
        "parameters": {"profile": "source", "execution_profile": "source", "backend_scope": SOURCE_BACKEND_SCOPE,
                       "jobs": jobs, "steps": list(SOURCE_STEPS), "exclude_category": "permissions"},
        "environment": hashlib.sha256(json.dumps(environment).encode("utf-8")).hexdigest(),
        "git_configuration": hashlib.sha256(configuration).hexdigest(),
    }


def validate_source_backend(backend: dict) -> None:
    """文件通过数和真实方法执行证据必须相互吻合，纯排除文件不算执行。"""
    if not isinstance(backend, dict):
        raise ValueError("回执后端报告必须是完整对象")
    counts = ("total", "passed", "partial", "failed", "skipped")
    if (backend.get("execution_profile") != "source"
            or any(type(backend.get(name)) is not int or backend[name] < 0 for name in counts)
            or backend["total"] < 1 or backend["passed"] + backend["partial"] != backend["total"]
            or backend["failed"] or backend["skipped"]):
        raise ValueError("回执后端报告没有覆盖全部实际执行文件")
    results = backend.get("results")
    if not isinstance(results, list) or len(results) != backend["total"]:
        raise ValueError("回执后端报告缺少完整逐文件执行结果")
    for item in results:
        if (not isinstance(item, dict) or not isinstance(item.get("file"), str) or not item["file"]
                or item.get("status") not in {"PASS", "PARTIAL"}
                or type(item.get("exit_code")) is not int or item["exit_code"] != 0
                or type(item.get("executed_methods")) is not int or item["executed_methods"] < 1
                or type(item.get("skipped_methods")) is not int or item["skipped_methods"] < 0):
            raise ValueError("回执后端结果没有真实的正数方法执行计数")
    if (len({item["file"] for item in results}) != backend["total"]
            or sum(item["status"] == "PASS" for item in results) != backend["passed"]
            or sum(item["status"] == "PARTIAL" for item in results) != backend["partial"]):
        raise ValueError("回执后端逐文件结果与汇总计数不一致")


def receipt_evidence(report_dir: Path, commit: str) -> dict[str, str]:
    """只承认具有完整成功步骤、后端报告和日志的本门禁证据。"""
    report = json.loads((report_dir / "quality-gate.json").read_text(encoding="utf-8"))
    steps = report["steps"]
    if (
        report.get("passed") is not True or report.get("profile") != "source"
        or report.get("source_commit") != commit
        or tuple(step["name"] for step in steps) != SOURCE_STEPS
        or any(type(step.get("exit_code")) is not int or step["exit_code"] != 0 for step in steps)
    ):
        raise ValueError("回执引用的 source 报告不是完整成功检查")
    for step in steps:
        if Path(step["log"]).resolve() != (report_dir / f"{step['name']}.log").resolve():
            raise ValueError("回执日志不属于该检查报告")
    backend = json.loads((report_dir / "backend-regression.json").read_text(encoding="utf-8"))
    validate_source_backend(backend)
    names = ("quality-gate.json", "backend-regression.json", *(f"{name}.log" for name in SOURCE_STEPS))
    evidence = {}
    for name in names:
        path = report_dir / name
        if path.is_symlink():
            raise ValueError("回执证据不能是符号链接")
        evidence[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return evidence


def assert_receipt_location(path: Path) -> None:
    for candidate in (path, *path.parents):
        if candidate.is_symlink() or candidate.is_junction():
            raise ValueError("回执文件或目录不能是符号链接或目录联接")


def reusable_source_receipt(path: Path, fingerprint: dict) -> Path | None:
    assert_receipt_location(path)
    if not path.exists():
        return None
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(receipt, dict) or type(receipt.get("format")) is not int or receipt["format"] != 1 or receipt["fingerprint"] != fingerprint:
            raise ValueError("提交、运行时或依赖已变化")
        created = receipt["created_at"]
        if type(created) not in (int, float) or not 0 <= time.time() - created <= SOURCE_RECEIPT_MAX_AGE_SECONDS:
            raise ValueError("检查回执时间无效或已超过两小时有效期")
        report_dir = Path(receipt["report_dir"]).resolve()
        if report_dir.is_relative_to(ROOT) or receipt["evidence"] != receipt_evidence(report_dir, fingerprint["commit"]):
            raise ValueError("回执证据位置或哈希无效")
        return report_dir
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"检查回执不可复用，必须重新验证：{exc}", flush=True)
        return None


def write_source_receipt(path: Path, fingerprint: dict, report_dir: Path) -> None:
    assert_receipt_location(path)
    receipt = {"format": 1, "created_at": time.time(), "fingerprint": fingerprint, "report_dir": str(report_dir),
               "evidence": receipt_evidence(report_dir, fingerprint["commit"])}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.name}-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        assert_receipt_location(path)
        temporary.replace(path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def assert_push_source(commit: str) -> None:
    """推送目标必须是正在检查的完整提交，且不能夹带未提交的修复。"""
    def git(*arguments: str) -> str:
        return subprocess.check_output(
            ["git", *arguments], cwd=ROOT, text=True, encoding="utf-8", stderr=subprocess.STDOUT,
        ).strip()

    if len(commit) not in (40, 64) or any(char not in "0123456789abcdef" for char in commit):
        raise ValueError("推送目标必须是完整的小写 Git 提交号")
    if Path(git("rev-parse", "--show-toplevel")).resolve() != ROOT:
        raise ValueError("质量门禁必须运行在所属仓库根目录")
    if git("rev-parse", "--verify", f"{commit}^{{commit}}") != commit or git("rev-parse", "HEAD") != commit:
        raise ValueError("实际推送提交不是当前 HEAD；请在该提交对应的工作树运行门禁")
    status = git("status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise ValueError("推送前工作树必须干净，禁止用未提交代码替推送提交通过检查：\n" + status)


def print_failure_summary(name: str, output: str) -> None:
    """控制台保留失败项与诊断上下文，完整输出仍保存为独立日志。"""
    lines = output.splitlines()
    selected: set[int] = set()
    for index, line in enumerate(lines):
        if line.startswith("not ok ") or "FAIL:" in line or "ERROR:" in line or re.search(r"\b[A-Z]{1,4}\d{3}\b", line):
            selected.update(range(max(0, index - 1), min(len(lines), index + 12)))
    selected.update(range(max(0, len(lines) - 40), len(lines)))
    print(f"--- {name} 失败摘要 ---", file=sys.stderr, flush=True)
    indices = sorted(selected)
    truncated = len(indices) > 120
    if truncated:
        indices = indices[:80] + indices[-40:]
    remaining = 12000
    for index in indices:
        line = lines[index]
        if len(line) > 400:
            line = line[:400] + "..."
            truncated = True
        remaining -= len(line) + 1
        if remaining < 0:
            truncated = True
            break
        print(line, file=sys.stderr)
    if truncated:
        print("摘要已截断，完整诊断见该检查的日志文件。", file=sys.stderr)


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
    parser.add_argument("--profile", choices=("full", "static", "source"), default="full")
    parser.add_argument("--push-commit", help="pre-push 传入的实际完整提交号，仅用于 source 检查")
    parser.add_argument("--refresh-receipt", action="store_true", help="强制重新执行推送提交的 source 检查")
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    report_dir = args.report_dir.expanduser().resolve()
    if report_dir.is_relative_to(ROOT):
        parser.error("证据目录必须位于项目源码目录之外")
    if args.jobs < 1:
        parser.error("jobs 必须大于零")
    if args.push_commit and args.profile != "source":
        parser.error("push-commit 只能与 source 检查一起使用")
    if args.refresh_receipt and not args.push_commit:
        parser.error("refresh-receipt 必须同时提供 push-commit")
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
            print_failure_summary(name, completed.stdout + completed.stderr)
            raise RuntimeError(f"{name} 失败（退出码 {completed.returncode}），详情：{log}")
        print(f"通过 {name}", flush=True)

    save()
    try:
        fingerprint = None
        receipt_path = None
        if args.push_commit:
            assert_push_source(args.push_commit)
            summary["source_commit"] = args.push_commit
            fingerprint = source_fingerprint(args.push_commit, args.node, version, args.jobs)
            receipt_path = Path(subprocess.check_output(
                ["git", "rev-parse", "--git-path", "oa-quality/source-receipt.json"], cwd=ROOT, text=True, encoding="utf-8",
            ).strip())
            if not receipt_path.is_absolute():
                receipt_path = ROOT / receipt_path
            assert_receipt_location(receipt_path)
            cached_report = None if args.refresh_receipt else reusable_source_receipt(receipt_path, fingerprint)
            if cached_report:
                assert_push_source(args.push_commit)
                summary.update(json.loads((cached_report / "quality-gate.json").read_text(encoding="utf-8")))
                summary["reused_report"] = str(cached_report)
                save()
                print(f"复用完整 source 检查回执：{args.push_commit}；原始报告：{cached_report}", flush=True)
                return 0
            receipt_path.unlink(missing_ok=True)
        inspect_production_sources()
        with tempfile.TemporaryDirectory(prefix="oa-test-quality-gate-") as temporary:
            environment = source_git_environment() if args.profile == "source" else os.environ.copy()
            environment.update(
                APP_ENV="testing", DATABASE_URL="sqlite+aiosqlite:///:memory:",
                UPLOAD_ROOT=temporary, SEED_DEMO_DATA="false", PYTHONIOENCODING="utf-8",
                PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(API),
            )
            if args.profile == "source":
                # 本地源码门禁不继承任何 PostgreSQL 或远端测试服务配置。
                for name in tuple(environment):
                    if "TEST_POSTGRES" in name or name in {"OA_ROUTE_EFFECTS_POSTGRES_URL", "OA_TEST_API_BASE"}:
                        environment.pop(name)
                summary["backend_scope"] = SOURCE_BACKEND_SCOPE
                summary["pending_ci"] = ["完整 regression", "PostgreSQL 专用回归与集成", "依赖安全审计", "生产构建与运行包检查", "Linux 依赖镜像"]
                print("source 仅执行 unit、structural 与固定四项回归；完整 regression、PG 及依赖镜像待隔离测试环境完整验证。", flush=True)
            environment["PATH"] = str(Path(args.node).resolve().parent) + os.pathsep + environment.get("PATH", "")
            run("backend-static", [sys.executable, "-m", "ruff", "check", str(API / "app")], ROOT, environment)
            run("backend-runner-selfcheck", [sys.executable, "-m", "unittest", "tests.test_regression_runner"], API, environment)
            run("quality-tools", [sys.executable, "-m", "unittest", "discover", "-s", "tests/quality", "-p", "test_*.py"], ROOT, environment)
            run("frontend-unit", [args.node, "tests/run-unit.mjs"], WEB, environment)
            run("client-api-contract", [sys.executable, "scripts/audit-client-api-coverage.py"], ROOT, environment)
            run("menu-route-coverage", [sys.executable, "scripts/audit-menu-coverage.py"], ROOT, environment)
            regression_command = [sys.executable, "tests/run_regression.py", "--group", "unit", "--group", "regression", "--group", "structural", "--exclude-category", "permissions", "--jobs", str(args.jobs), "--report", str(report_dir / "backend-regression.json")]
            if args.profile == "source":
                run("backend-regression", [*regression_command, "--execution-profile", "source"], API, environment)
                backend_report = json.loads((report_dir / "backend-regression.json").read_text(encoding="utf-8"))
                validate_source_backend(backend_report)
                summary["backend_scope"] = backend_report["scope"]
                summary["backend_pending_ci"] = backend_report["deferred"] + backend_report["pending_full"]
                print(f"后端待隔离测试环境完整验证：{len(summary['backend_pending_ci'])} 项未通过；具体名单见 backend-regression.json。", flush=True)
            if args.profile != "source":
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
                run("backend-dependencies", [sys.executable, "-m", "pip_audit", "-r", str(API / "requirements.lock"), "--format", "json", "--output", str(report_dir / "backend-dependencies.json")], ROOT, environment)
                npm = "npm.cmd" if os.name == "nt" else "npm"
                run("frontend-dependencies", [npm, "audit", "--audit-level=low"], WEB, environment)
                run("harness-dependencies", [npm, "exec", "--yes", "--package=pnpm@11.24.0", "--", "pnpm", "audit", "--audit-level=low"], ROOT / "apps/deepseek-harness-host", environment)
                run("backend-regression", regression_command, API, environment)
                run("postgres-domain-boundaries", [sys.executable, "tests/run_regression.py", "--group", "integration", "--file", "postgres_domain_boundaries_test.py", "--report", str(report_dir / "postgres-domain.json")], API, environment)
                run("harness-health", [sys.executable, "scripts/verify_harness.py", "--node", args.node, "--report-dir", str(report_dir)], ROOT, environment)
            if args.profile != "source":
                runtime = report_dir / "runtime"
                run("runtime-package", [sys.executable, "scripts/runtime_package.py", "build", "--output", str(runtime)], ROOT, environment)
                run("runtime-integrity", [sys.executable, "scripts/runtime_package.py", "verify", "--output", str(runtime)], ROOT, environment)
                run("runtime-health", [sys.executable, "scripts/verify_runtime.py", "--package", str(runtime), "--report-dir", str(report_dir)], ROOT, environment)
            if args.push_commit:
                assert_push_source(args.push_commit)
                if fingerprint != source_fingerprint(args.push_commit, args.node, version, args.jobs):
                    raise ValueError("检查期间运行时或依赖变化，拒绝生成成功回执")
            summary["passed"] = True
            save()
            if receipt_path:
                write_source_receipt(receipt_path, fingerprint, report_dir)
    except Exception as exc:
        summary["passed"] = False
        summary["error"] = str(exc)
        save()
        print(str(exc), file=sys.stderr)
        return 1
    print(f"质量检查完成，范围：{args.profile}，报告：{report_dir / 'quality-gate.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
