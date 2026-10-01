"""逐文件、逐进程运行后端回归，并为每个文件提供独立数据库与附件目录。"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy.engine import make_url

API_ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(__file__).resolve().parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


GROUPS = ("unit", "regression", "structural", "integration")
SUITE_REQUIREMENTS = json.loads((TEST_ROOT / "suite_manifest.json").read_text(encoding="utf-8"))
INTEGRATION_REQUIREMENTS = SUITE_REQUIREMENTS["integration_requirements"]
UNIT_REQUIREMENTS = SUITE_REQUIREMENTS["unit_requirements"]
EXCLUDED_CATEGORIES = SUITE_REQUIREMENTS["excluded_categories"]


def selected_files(groups: list[str], patterns: list[str]) -> list[Path]:
    files = [
        path
        for group in groups
        for path in sorted(TEST_ROOT.glob("test_*.py") if group == "unit" else (TEST_ROOT / group).glob("*.py"))
        if path.name not in {"__init__.py", "environment.py"}
    ]
    if patterns:
        files = [path for path in files if any(fnmatch.fnmatch(path.name, pattern) for pattern in patterns)]
    return files


def decode_output(value: bytes | None, stream: str) -> str:
    try:
        return (value or b"").decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(f"测试进程的{stream}不是 UTF-8：字节偏移 {exc.start}") from exc


def test_environment(path: Path, temporary: Path, args: argparse.Namespace) -> dict[str, str]:
    environment = os.environ.copy()
    search_paths = [str(API_ROOT), str(API_ROOT.parents[1]), str(TEST_ROOT / "regression"), str(TEST_ROOT / "structural"), str(TEST_ROOT / "integration")]
    if environment.get("PYTHONPATH"):
        search_paths.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(search_paths)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8:strict"
    environment.pop("OA_TEST_EXCLUDED_METHODS", None)
    if path.parent.name == "integration" and "api_base" in INTEGRATION_REQUIREMENTS[path.name]:
        if args.api_base:
            environment["OA_TEST_API_BASE"] = args.api_base
        return environment
    if path.parent == TEST_ROOT and "postgres_dsn" in UNIT_REQUIREMENTS.get(path.name, []):
        from tests.environment import validate_database_url

        postgres_url = os.environ.get("OA_TEST_POSTGRES_URL") or os.environ.get("OA_TEST_POSTGRES_DSN", "")
        validate_database_url(postgres_url)
        if make_url(postgres_url).drivername not in {"postgresql+asyncpg", "postgresql+psycopg"}:
            raise RuntimeError("PostgreSQL 启动迁移测试必须指定隔离 PostgreSQL 数据库")
        environment["OA_TEST_POSTGRES_URL"] = postgres_url
    upload_root = temporary / "uploads"
    upload_root.mkdir()
    database = temporary / "test.db"
    if path.name in {"finance929Regression_test.py", "invoice929ReworkApi_test.py"}:
        environment["OA_FINANCE_TEST_DB"] = str(temporary / "finance-test.db")
    if path.name == "finance929Rework10_test.py":
        runtime = temporary / "runtime"
        runtime.mkdir()
        upload_root = runtime / "uploads"
        upload_root.mkdir()
        database = runtime / "row10-test.db"
        environment["OA_RW10_TEST_DB"] = str(database)
    environment.update(
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{database.as_posix()}",
        UPLOAD_ROOT=str(upload_root),
        SEED_DEMO_DATA="false",
        OA_BATCH_EVIDENCE=str(temporary),
        OA_929_CLUES_EVIDENCE_DIR=str(temporary),
        OA_TEST_RUNTIME_DIR=str(temporary),
    )
    if args.api_base:
        environment["OA_TEST_API_BASE"] = args.api_base
    if args.legacy_source_root:
        environment["OA_TEST_LEGACY_SOURCE_ROOT"] = str(args.legacy_source_root)
    if args.legacy_bundle:
        environment["OA_TEST_LEGACY_BUNDLE"] = str(args.legacy_bundle)
    return environment


def run_file(path: Path, args: argparse.Namespace) -> dict[str, object]:
    relative = path.relative_to(TEST_ROOT).as_posix()
    excluded = {
        method: {"file": relative, "method": method, "category": category, "reason": reason}
        for category in getattr(args, "exclude_category", [])
        for method, reason in EXCLUDED_CATEGORIES[category].get(relative, {}).items()
    }
    if any(not item["reason"].strip() for item in excluded.values()):
        raise RuntimeError(f"测试排除必须有具体依据：{relative}")
    if path.parent == TEST_ROOT:
        missing = [
            requirement for requirement in UNIT_REQUIREMENTS.get(path.name, [])
            if requirement == "postgres_dsn" and not (os.environ.get("OA_TEST_POSTGRES_URL") or os.environ.get("OA_TEST_POSTGRES_DSN"))
        ]
        if missing:
            return {"file": relative, "status": "SKIP", "reason": f"缺少显式测试前置配置：{', '.join(missing)}"}
    if path.parent.name == "integration":
        requirements = INTEGRATION_REQUIREMENTS[path.name]
        present = {
            "api_base": bool(args.api_base or os.environ.get("OA_TEST_API_BASE")) and all(os.environ.get(name) for name in ("APP_ENV", "DATABASE_URL", "UPLOAD_ROOT")),
            "legacy_source_root": bool(args.legacy_source_root or os.environ.get("OA_TEST_LEGACY_SOURCE_ROOT")),
            "legacy_bundle": bool(args.legacy_bundle or os.environ.get("OA_TEST_LEGACY_BUNDLE")),
            "postgres_dsn": bool(os.environ.get("OA_TEST_POSTGRES_DSN")),
        }
        missing = [requirement for requirement in requirements if not present[requirement]]
        if missing:
            return {"file": relative, "status": "SKIP", "reason": f"缺少显式测试前置配置：{', '.join(missing)}"}
    with TemporaryDirectory(prefix="oa-test-regression-") as directory:
        try:
            environment = test_environment(path, Path(directory), args)
        except RuntimeError as exc:
            return {"file": relative, "status": "FAIL", "exit_code": 1, "output": str(exc)}
        if excluded:
            environment["OA_TEST_EXCLUDED_METHODS"] = json.dumps(sorted(excluded))
        direct_entry = not excluded and "if __name__" in path.read_text(encoding="utf-8")
        if direct_entry:
            command = [sys.executable, str(path)]
        else:
            command = [sys.executable, str(TEST_ROOT / "_run_one.py"), str(path)]
        try:
            completed = subprocess.run(command, cwd=API_ROOT, env=environment, capture_output=True, timeout=args.timeout, check=False)
            try:
                stdout = decode_output(completed.stdout, "stdout")
                output = stdout + decode_output(completed.stderr, "stderr")
                return_code = completed.returncode
            except ValueError as exc:
                output = f"{exc}\n"
                return_code = 1
            selection = None
            if not direct_entry and return_code == 0:
                selection_lines = [line.removeprefix("TEST_SELECTION_JSON=") for line in stdout.splitlines() if line.startswith("TEST_SELECTION_JSON=")]
                if len(selection_lines) != 1:
                    output += "\n测试排除没有返回唯一的方法选择报告"
                    return_code = 1
                else:
                    try:
                        selection = json.loads(selection_lines[0])
                        if set(selection["excluded"]) != set(excluded):
                            raise ValueError("方法清单不一致")
                        if not isinstance(selection["executed"], int) or selection["executed"] < 0:
                            raise ValueError("执行数量无效")
                        if not isinstance(selection["skipped"], int) or selection["skipped"] < 0:
                            raise ValueError("跳过数量无效")
                    except (ValueError, KeyError, TypeError) as exc:
                        output += f"\n测试排除报告无效：{exc}"
                        selection = None
                        return_code = 1
            direct_skipped = False
            if direct_entry and return_code == 0:
                lines = [line.strip() for line in output.splitlines()]
                ran = next((match for line in lines if (match := re.fullmatch(r"Ran (\d+) tests? in .+", line))), None)
                skipped_count = next((match for line in lines if (match := re.fullmatch(r"OK \(skipped=(\d+)\)", line))), None)
                direct_skipped = bool(ran and (
                    int(ran.group(1)) == 0
                    or skipped_count and int(ran.group(1)) == int(skipped_count.group(1))
                ))
            unrun = bool(selection and selection["executed"] == 0 and selection["skipped"] > 0) or direct_skipped
            status = "FAIL" if return_code else "SKIP" if unrun else "EXCLUDED" if selection and selection["executed"] == 0 else "PARTIAL" if excluded else "PASS"
            result = {"file": relative, "status": status, "exit_code": return_code, "output": output[-2000:]}
            if selection:
                result["excluded"] = [excluded[method] for method in selection["excluded"]]
                result["executed_methods"] = selection["executed"]
                result["skipped_methods"] = selection["skipped"]
            if status == "SKIP":
                result["reason"] = "测试文件没有实际执行任何方法"
        except subprocess.TimeoutExpired as exc:
            try:
                partial = decode_output(exc.stdout, "stdout") + decode_output(exc.stderr, "stderr")
            except ValueError as decode_error:
                partial = f"{decode_error}\n"
            output = f"超时 {args.timeout} 秒：{exc}\n{partial}"
            result = {"file": path.relative_to(TEST_ROOT).as_posix(), "status": "FAIL", "exit_code": 124, "output": output}
        if args.report and result["exit_code"] != 0:
            log_dir = args.report.expanduser().resolve().parent / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / f"{path.parent.name}-{path.name}.log"
            log_path.write_text(output, encoding="utf-8")
            result["log"] = str(log_path)
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", choices=GROUPS, action="append")
    parser.add_argument("--exclude-category", choices=sorted(EXCLUDED_CATEGORIES), action="append", default=[])
    parser.add_argument("--file", action="append", default=[], help="文件名 glob，可重复")
    parser.add_argument("--api-base", help="显式隔离服务地址，完整 /api/v1 URL")
    parser.add_argument("--legacy-source-root", type=Path, help="显式旧系统 SH.CRM.WEB 源码目录")
    parser.add_argument("--legacy-bundle", type=Path, help="显式旧系统导入数据目录")
    parser.add_argument("--report", type=Path, help="外部证据 JSON 路径")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--jobs", type=int, default=1, help="独立临时目录中的并发文件数")
    args = parser.parse_args()
    groups = args.group or ["unit", "regression", "structural"]
    files = selected_files(groups, args.file)
    if args.list:
        for path in files:
            print(path.relative_to(TEST_ROOT).as_posix())
        print(f"total={len(files)}")
        return 0
    if not files:
        parser.error("没有匹配的测试文件")
    if args.jobs < 1:
        parser.error("--jobs 必须大于零")
    results = []
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = {executor.submit(run_file, path, args): path for path in files}
        for index, future in enumerate(as_completed(futures), 1):
            result = future.result()
            results.append(result)
            print(f"[{index}/{len(files)}] {result['status']} {result['file']}", flush=True)
    order = {path.relative_to(TEST_ROOT).as_posix(): index for index, path in enumerate(files)}
    results.sort(key=lambda item: order[item["file"]])
    failures = [item for item in results if item["status"] == "FAIL"]
    skipped = [item for item in results if item["status"] == "SKIP"]
    excluded = [method for item in results for method in item.get("excluded", [])]
    summary = {"total": len(results), "passed": sum(item["status"] == "PASS" for item in results), "partial": sum(item["status"] == "PARTIAL" for item in results), "failed": len(failures), "skipped": len(skipped), "excluded": excluded, "failures": failures, "skips": skipped}
    if args.report:
        target = args.report.expanduser().resolve()
        if target.is_relative_to(API_ROOT):
            parser.error("测试报告必须保存在后端源码目录之外")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value if key != "excluded" else len(value) for key, value in summary.items() if key not in {"failures", "skips"}}, ensure_ascii=False))
    for item in failures:
        print(f"FAIL {item['file']}: {item.get('log', '')}")
    return 1 if failures or skipped else 0


if __name__ == "__main__":
    raise SystemExit(main())
