"""代码审查报告：分档、新增问题、改动行覆盖率。第一阶段只提示，任何情况下都不让推送或 CI 失败。

老问题记在 baseline.json，只比新增。流程和各项含义见 docs/代码审查流程.md。
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import signal
import sys
import tempfile
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import risk  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
API = ROOT / "apps/api-server"
WEB = ROOT / "apps/admin-web"
BASELINE = HERE / "baseline.json"
KNOWN_ISSUES = HERE / "known_issues.json"
DEFAULT_TOOLS_PYTHON = Path.home() / ".local/share/oa/review-tools/bin/python"
SCAN_PY = ("apps/api-server/app", "scripts")
SECTION_LIMIT = 40
SECRET_ENV = re.compile(r"TOKEN|SECRET|PASSWORD|API_?KEY|ACCESS_?KEY|DINGTALK|DEEPSEEK|VOLC|^OSS_|^ALIBABA", re.I)
RUN: dict = {"deadline": None, "process": None}
DUPLICATE_WINDOW = 12
VULTURE_IGNORE = ("@router.*,@app.*,@*.get,@*.post,@*.put,@*.patch,@*.delete,@*_validator,@validator,"
                  "@*.on_event,@*.middleware,@*.exception_handler,@*.tool,@*.task")
TRIVIAL_LINE = re.compile(r"^(?:[\s()\[\]{},;:]*|(?:from|import)\s.*|#.*|//.*|\"\"\".*|</?>|\}\)?;?)$")


def git(*arguments: str) -> str:
    return subprocess.run(["git", *arguments], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True).stdout


# ---------- 这次改了什么 ----------

def parse_diff(diff: str) -> tuple[dict[str, set[int]], dict[str, list[str]], list[str]]:
    """返回 改动行号、新增行文本、删改的文件。只改版本号的 package 文件不算改动。"""
    changed: dict[str, set[int]] = {}
    added: dict[str, list[str]] = {}
    removed: dict[str, int] = {}
    current = None
    previous = None
    line_number = 0
    for line in diff.splitlines():
        if line.startswith("--- "):
            previous = line[6:] if line.startswith("--- a/") else None
        elif line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else previous
            if current:
                changed.setdefault(current, set())
                added.setdefault(current, [])
        elif line.startswith("@@"):
            match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", line)
            line_number = int(match.group(1)) if match else 0
        elif current and line.startswith("+"):
            changed[current].add(line_number)
            added[current].append(line[1:])
            line_number += 1
        elif current and line.startswith("-"):
            removed[current] = removed.get(current, 0) + 1
    version_line = re.compile(r'^\s*"version":\s*"\d+\.\d+\.\d+",?\s*$')
    for name in ("apps/admin-web/package.json", "apps/admin-web/package-lock.json"):
        if name in added and all(version_line.match(line) for line in added[name]):
            changed.pop(name)
            added.pop(name)
    return changed, added, sorted(changed)


def changed_paths(base: str, head: str, changed: dict[str, set[int]]) -> list[str]:
    """判档用的全部路径。--no-renames 让改名的新旧路径都出现，纯改名、二进制没有差异内容也不会漏。"""
    names = git("-c", "core.quotepath=off", "diff", "--name-only", "--no-renames", base, head).splitlines()
    version_only = {"apps/admin-web/package.json", "apps/admin-web/package-lock.json"} - set(changed)
    return sorted(name for name in names if name not in version_only)


def resolve_base(head: str, base: str | None) -> str:
    """远端还没有这个分支，或给的基准本地没有时，退回和 origin/dev 的分叉点。"""
    if base and set(base) != {"0"}:
        try:
            git("cat-file", "-e", f"{base}^{{commit}}")
            return base
        except subprocess.CalledProcessError:
            pass
    return git("merge-base", head, "origin/dev").strip()


# ---------- 各工具 ----------

def kill_active() -> None:
    process = RUN["process"]
    if process and process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            pass


def fail_tool(timings: dict, name: str, reason: str) -> None:
    timings.setdefault("_errors", {})[name] = reason


def run_tool(name: str, command: list[str], cwd: Path, timeout: int, timings: dict, env: dict | None = None, ok_codes: tuple[int, ...] | None = None) -> subprocess.CompletedProcess | None:
    """崩溃、超时、退出码不对都记入“没跑成”并返回 None，不能当成没问题。超时连子进程一起杀。"""
    started = time.monotonic()
    limit = timeout
    if RUN["deadline"] is not None:
        limit = min(timeout, RUN["deadline"] - started)
        if limit <= 0:
            fail_tool(timings, name, "总时限到了，没跑")
            return None
    try:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8", errors="replace", start_new_session=True)
        RUN["process"] = process
        try:
            stdout, stderr = process.communicate(timeout=limit)
        except subprocess.TimeoutExpired:
            kill_active()
            process.communicate()
            fail_tool(timings, name, f"超时（{int(limit)} 秒）")
            return None
        if ok_codes is not None and process.returncode not in ok_codes:
            fail_tool(timings, name, f"退出码 {process.returncode}：{(stderr or stdout)[-200:].strip()}")
            return None
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    except OSError as exc:
        fail_tool(timings, name, str(exc))
        return None
    finally:
        timings[name] = round(time.monotonic() - started, 1)


def load_json_output(name: str, text: str, timings: dict):
    try:
        return json.loads(text)
    except ValueError:
        fail_tool(timings, name, f"输出不是 JSON：{text[:120].strip()}")
        return None


def issue(tool: str, file: str, line: int, rule: str, message: str, key: str | None = None) -> dict:
    return {"tool": tool, "file": file, "line": line, "rule": rule, "message": message, **({"key": key} if key else {})}


def relative_to_root(path: str, cwd: Path = ROOT) -> str:
    target = Path(path) if Path(path).is_absolute() else cwd / path
    return target.resolve().relative_to(ROOT.resolve()).as_posix()


def run_ruff(python: str, timings: dict) -> list[dict]:
    command = [python, "-m", "ruff", "check", "--no-cache", "--exit-zero", "--config", str(HERE / "ruff.toml"), "--output-format", "json", *SCAN_PY]
    done = run_tool("ruff", command, ROOT, 60, timings, ok_codes=(0,))
    items = load_json_output("ruff", done.stdout, timings) if done else None
    return [issue("ruff", relative_to_root(item["filename"]), item["location"]["row"], item["code"] or "E999", item["message"])
            for item in items or []]


def run_mypy(tools_python: str, python: str, cache: Path, timings: dict) -> list[dict]:
    command = [tools_python, "-m", "mypy", "--python-executable", python, "--ignore-missing-imports", "--follow-imports=silent", "--check-untyped-defs",
               "--no-error-summary", "--show-error-codes", "--no-pretty", "--cache-dir", str(cache), "app"]
    done = run_tool("mypy", command, API, 180, timings, ok_codes=(0, 1))
    found = []
    for line in (done.stdout if done else "").splitlines():
        match = re.match(r"^(.+?):(\d+): error: (.+?)(?:\s+\[([\w-]+)\])?$", line)
        if match:
            found.append(issue("mypy", relative_to_root(match[1], API), int(match[2]), f"mypy:{match[4] or 'error'}", match[3]))
    if done and done.returncode and not found:
        fail_tool(timings, "mypy", f"报错但没有结果：{(done.stderr or done.stdout)[-200:].strip()}")
    return found


def run_vulture(tools_python: str, timings: dict) -> list[dict]:
    command = [tools_python, "-m", "vulture", "apps/api-server/app", "--min-confidence", "60", "--ignore-decorators", VULTURE_IGNORE,
               "--exclude", "*/data_models/*,*/api_schemas/*,*/models.py"]
    # vulture 退出码：0 没有，3 有无用代码，其他是出错。
    done = run_tool("vulture", command, ROOT, 60, timings, ok_codes=(0, 3))
    found = []
    for line in (done.stdout if done else "").splitlines():
        match = re.match(r"^(.+?):(\d+): (.+?) \(\d+% confidence", line)
        # ORM 和 Pydantic 字段几乎全被判成“未使用的属性”，误报太多，不看。
        if match and not match[3].startswith("unused attribute"):
            found.append(issue("vulture", match[1], int(match[2]), "dead-code", match[3]))
    return found


def run_tsc(node: str, timings: dict) -> list[dict]:
    done = run_tool("tsc", [node, "node_modules/typescript/bin/tsc", "--noEmit", "-p", ".", "--pretty", "false"], WEB, 120, timings, ok_codes=(0, 1, 2))
    found = []
    for line in (done.stdout if done else "").splitlines():
        match = re.match(r"^(.+?)\((\d+),\d+\): error (TS\d+): (.+)$", line)
        if match:
            found.append(issue("tsc", f"apps/admin-web/{match[1]}", int(match[2]), match[3], match[4]))
    if done and done.returncode and not found:
        fail_tool(timings, "tsc", f"报错但没有结果：{(done.stdout or done.stderr)[-200:].strip()}")
    return found


def run_ts_metrics(node: str, timings: dict) -> list[dict]:
    done = run_tool("ts-metrics", [node, str(HERE / "ts_metrics.mjs"), str(WEB)], ROOT, 60, timings, ok_codes=(0,))
    items = load_json_output("ts-metrics", done.stdout, timings) if done else None
    return [issue("ts-metrics", f"apps/admin-web/{item['file']}", item["line"], item["rule"], item["message"])
            for item in items or []]


def source_files() -> list[Path]:
    paths = [path for path in (API / "app").rglob("*.py") if "export_templates" not in path.parts]
    paths += [path for path in (WEB / "src").rglob("*") if path.suffix in {".ts", ".tsx"}]
    return sorted(paths)


def find_duplicates(timings: dict, window: int = DUPLICATE_WINDOW) -> list[dict]:
    """连续 window 行（去掉空行、注释、import）一模一样算重复。不加依赖，复制粘贴能抓到，改了变量名的抓不到。"""
    started = time.monotonic()
    seen: dict[str, list[tuple[str, int]]] = {}
    for path in source_files():
        if RUN["deadline"] is not None and time.monotonic() > RUN["deadline"]:
            fail_tool(timings, "duplicate", "总时限到了，没查完，不算结果")
            return []
        relative = path.relative_to(ROOT).as_posix()
        lines = [(number, line.strip()) for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1)]
        lines = [item for item in lines if not TRIVIAL_LINE.match(item[1])]
        for index in range(len(lines) - window + 1):
            chunk = lines[index:index + window]
            digest = hashlib.sha256("\n".join(text for _, text in chunk).encode()).hexdigest()[:12]
            seen.setdefault(digest, []).append((relative, chunk[0][0]))
    found, reported = [], set()
    for digest, places in seen.items():
        if len(places) < 2:
            continue
        for file, line in places:
            # 同一段重复只在每个文件报开头一处：相邻窗口合并。
            if (file, line - 1) not in reported and not any((file, line - offset) in reported for offset in range(1, window)):
                other = next(((f, n) for f, n in places if (f, n) != (file, line)), None)
                found.append(issue("duplicate", file, line, "duplicate-block", f"和 {other[0]}:{other[1]} 有连续 {window} 行以上相同", key=digest))
            reported.add((file, line))
    timings["duplicate"] = round(time.monotonic() - started, 1)
    return found


def run_dependency_audit(python: str, timings: dict) -> list[dict]:
    """需要联网，只在依赖文件有改动或 CI 时跑。"""
    found = []
    # 这两个工具有漏洞时退出码是 1，所以用输出判断是否真的跑成。
    done = run_tool("pip-audit", [python, "-m", "pip_audit", "-r", str(API / "requirements.lock"), "--format", "json", "--no-deps", "--disable-pip", "--progress-spinner", "off"], ROOT, 180, timings, ok_codes=(0, 1))
    data = load_json_output("pip-audit", done.stdout, timings) if done else None
    for package in (data or {}).get("dependencies", []):
        for vulnerability in package.get("vulns", []):
            found.append(issue("pip-audit", "apps/api-server/requirements.lock", 0, vulnerability["id"], f"{package['name']} {package.get('version', '')}", key=f"{package['name']}|{vulnerability['id']}"))
    npm = shutil.which("npm") or "npm"
    done = run_tool("npm-audit", [npm, "audit", "--json"], WEB, 120, timings, ok_codes=(0, 1))
    data = load_json_output("npm-audit", done.stdout, timings) if done else None
    if data and "error" in data:
        fail_tool(timings, "npm-audit", str(data["error"])[:200])
    for name, item in (data or {}).get("vulnerabilities", {}).items():
        found.append(issue("npm-audit", "apps/admin-web/package-lock.json", 0, item.get("severity", "unknown"), f"{name} {item.get('range', '')}", key=name))
    return found


# ---------- 改动行覆盖率 ----------

def related_tests(targets: list[str], changed_tests: list[str], limit: int = 8) -> list[str]:
    """这次改到的测试优先；其余按“提到改动模块名”挑，越少测试提到的模块越优先，免得 ipr 这种通用名占满名额。"""
    stems = {Path(path).stem for path in targets} - {"__init__", "router", "main", "constants"}
    tests = API / "tests"
    candidates = [*tests.glob("test_*.py"), *(tests / "regression").glob("*.py"), *(tests / "structural").glob("*.py")]
    # probe 是手工探测外部服务的脚本，不能在推送时自动跑。
    candidates = [path for path in candidates if path.name not in {"__init__.py", "environment.py"} and "probe" not in path.name]
    chosen = sorted({Path(path).name for path in changed_tests} & {path.name for path in candidates})
    texts = {path.name: path.read_text(encoding="utf-8", errors="replace") for path in sorted(candidates)}
    hits = {stem: [name for name, text in texts.items() if re.search(rf"\b{re.escape(stem)}\b", text)] for stem in stems}
    for stem in sorted(hits, key=lambda value: len(hits[value])):
        for name in hits[stem][:3]:
            if name not in chosen:
                chosen.append(name)
    return chosen[:limit]


def measure_coverage(changed: dict[str, set[int]], python: str, tools_python: str, jobs: int, timeout: int, whole_suite: bool, timings: dict, report_dir: Path) -> dict:
    targets = {path: lines for path, lines in changed.items() if path.startswith("apps/api-server/app/") and path.endswith(".py") and lines}
    frontend = sorted(path for path in changed if path.startswith("apps/admin-web/src/") and path.endswith((".ts", ".tsx")))
    result: dict = {"frontend_note": "前端不统计行覆盖：前端测试大多读源码文本断言，不真正执行页面代码，算出来的数字没有意义。"}
    if frontend:
        tests_text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in (WEB / "tests").rglob("*") if path.suffix in {".mjs", ".ts", ".tsx"})
        result["frontend_without_test"] = [path for path in frontend if Path(path).stem not in tests_text]
    if not targets:
        return {**result, "status": "没有改动后端代码"}
    changed_tests = [path for path in changed if path.startswith("apps/api-server/tests/") and path.endswith(".py")]
    tests = [] if whole_suite else related_tests(list(targets), changed_tests)
    if not whole_suite and not tests:
        return {**result, "status": "没找到提到这些模块的测试", "total": sum(map(len, targets.values())), "covered": 0, "percent": 0.0, "scope": "相关测试"}
    site = subprocess.run([tools_python, "-c", "import coverage, pathlib; print(pathlib.Path(coverage.__file__).parent)"], capture_output=True, encoding="utf-8", check=True).stdout.strip()
    with tempfile.TemporaryDirectory(prefix="oa-review-coverage-") as temporary:
        shim = Path(temporary) / "shim"
        shim.mkdir()
        # 只露出 coverage 一个包，避免工具环境的依赖盖掉门禁环境的版本。
        (shim / "coverage").symlink_to(site)
        (shim / "sitecustomize.py").write_text("import coverage\ncoverage.process_startup()\n", encoding="utf-8")
        data_file = Path(temporary) / ".coverage"
        rc = Path(temporary) / "coveragerc"
        rc.write_text(f"[run]\nparallel = True\ndata_file = {data_file}\nsource = {API / 'app'}\ncore = sysmon\n", encoding="utf-8")
        # 去掉密钥类变量，测试不可能连到真实外部服务；去掉 GIT_*，pre-push 里 Git 会设置 GIT_DIR，测试里的 git 命令不能碰到真仓库。
        inherited = {name: value for name, value in os.environ.items() if not SECRET_ENV.search(name) and not name.startswith("GIT_")}
        env = {**inherited, "APP_ENV": "testing", "DATABASE_URL": "sqlite+aiosqlite:///:memory:", "UPLOAD_ROOT": temporary, "SEED_DEMO_DATA": "false",
               "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": os.pathsep.join((str(shim), str(API))), "COVERAGE_PROCESS_START": str(rc)}
        for name in tuple(env):
            if "TEST_POSTGRES" in name or name in {"OA_ROUTE_EFFECTS_POSTGRES_URL", "OA_TEST_API_BASE"}:
                env.pop(name)
        run_report = report_dir / "coverage-tests.json"
        report_dir.mkdir(parents=True, exist_ok=True)
        dirty_before = git("status", "--porcelain=v1", "--untracked-files=all")
        command = ["nice", "-n", "10", python, "tests/run_regression.py", "--group", "unit", "--group", "regression", "--group", "structural", "--jobs", str(jobs),
                   "--timeout", "120" if not whole_suite else "300", "--report", str(run_report)]
        for name in tests:
            command += ["--file", name]
        done = run_tool("coverage-tests", command, API, timeout, timings, env)
        if git("status", "--porcelain=v1", "--untracked-files=all") != dirty_before:
            fail_tool(timings, "coverage-tests", "跑完后工作区多了文件，下次推送门禁会拒绝，请先清理")
        if not done:
            return {**result, "status": "测试没在限定时间内跑完，本次没有覆盖率"}
        if not list(Path(temporary).glob(".coverage.*")):
            return {**result, "status": f"没产生覆盖数据：{done.stderr[-200:]}"}
        subprocess.run([tools_python, "-m", "coverage", "combine", f"--rcfile={rc}", "-q"], cwd=temporary, capture_output=True, check=True)
        output = Path(temporary) / "coverage.json"
        subprocess.run([tools_python, "-m", "coverage", "json", f"--rcfile={rc}", f"--data-file={data_file}", "-o", str(output), "-q", "--ignore-errors"], cwd=API, capture_output=True, check=True)
        files = json.loads(output.read_text(encoding="utf-8")).get("files", {})
    by_path = {relative_to_root(name, API): value for name, value in files.items()}
    total = covered = 0
    uncovered: dict[str, list[int]] = {}
    for path, lines in targets.items():
        record = by_path.get(path)
        if not record:
            # 没被任何测试导入：全部可执行行都算没覆盖。用改动行数近似。
            total += len(lines)
            uncovered[path] = sorted(lines)
            continue
        executable = lines & (set(record["executed_lines"]) | set(record["missing_lines"]))
        hit = lines & set(record["executed_lines"])
        total += len(executable)
        covered += len(hit)
        if executable - hit:
            uncovered[path] = sorted(executable - hit)
    results = []
    if run_report.exists():
        results = json.loads(run_report.read_text(encoding="utf-8")).get("failures", [])
    return {**result, "status": "已统计", "scope": "全部后端测试（不含 PostgreSQL）" if whole_suite else f"相关测试 {len(tests)} 个文件",
            "tests": tests, "total": total, "covered": covered, "percent": round(covered * 100 / total, 1) if total else 100.0,
            "uncovered": uncovered, "failed_tests": [item["file"] for item in results]}


# ---------- 基线 ----------

def fingerprint(item: dict, cache: dict[str, list[str]]) -> str:
    """不用行号：代码上下挪动不算新问题；这一行内容改了才算。"""
    if item.get("key"):
        return f"{item['rule']}|{item['key']}"
    lines = cache.get(item["file"])
    if lines is None:
        path = ROOT / item["file"]
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.is_file() else []
        cache[item["file"]] = lines
    text = lines[item["line"] - 1].strip() if 0 < item["line"] <= len(lines) else item["message"]
    return f"{item['rule']}|{hashlib.sha256(text.encode()).hexdigest()[:10]}"


def to_baseline(issues: list[dict], commit: str) -> dict:
    cache: dict[str, list[str]] = {}
    files: dict[str, Counter] = {}
    for item in issues:
        files.setdefault(item["file"], Counter())[fingerprint(item, cache)] += 1
    return {"format": 1, "commit": commit, "total": len(issues), "by_tool": dict(sorted(Counter(item["tool"] for item in issues).items())),
            "files": {name: dict(sorted(counter.items())) for name, counter in sorted(files.items())}}


def load_baseline(base: str, timings: dict) -> tuple[dict, str | None]:
    """从比较基准读基线：同一次提交既加问题又刷基线时，新增问题照样报出来。"""
    relative = BASELINE.relative_to(ROOT).as_posix()
    note = None
    try:
        text = git("show", f"{base}:{relative}")
    except subprocess.CalledProcessError:
        text = BASELINE.read_text(encoding="utf-8") if BASELINE.exists() else ""
        note = "比较基准还没有基线，用的是这次提交自带的基线（只有基线首次加入时才该出现）"
    try:
        return (json.loads(text) if text else {}), note
    except ValueError:
        fail_tool(timings, "基线", "基线文件坏了（可能是合并冲突），下面所有问题都算成新增，数字不可信")
        return {}, note


def split_new(issues: list[dict], baseline: dict, changed: dict[str, set[int]]) -> dict[str, list[dict]]:
    """基线之外的问题分三类：这次改动行上的、这次改到的文件其他位置的、别处的。"""
    remaining = {name: Counter(counts) for name, counts in baseline.get("files", {}).items()}
    cache: dict[str, list[str]] = {}
    outside: list[dict] = []
    # 不在改动行的先抵扣基线，改动行上的问题才更可能被判成新增。
    ordered = sorted(issues, key=lambda item: item["line"] in changed.get(item["file"], ()))
    for item in ordered:
        counter = remaining.get(item["file"])
        key = fingerprint(item, cache)
        if counter and counter[key] > 0:
            counter[key] -= 1
        else:
            outside.append(item)
    new_lines, same_file, elsewhere = [], [], []
    for item in sorted(outside, key=lambda value: (value["file"], value["line"], value["rule"])):
        if item["line"] in changed.get(item["file"], ()):
            new_lines.append(item)
        elif item["file"] in changed:
            same_file.append(item)
        else:
            elsewhere.append(item)
    return {"new_on_changed_lines": new_lines, "same_file": same_file, "elsewhere": elsewhere}


# ---------- 报告 ----------

def known_issues() -> list[dict]:
    return json.loads(KNOWN_ISSUES.read_text(encoding="utf-8")) if KNOWN_ISSUES.exists() else []


def issue_lines(items: list[dict]) -> list[str]:
    lines = [f"- `{item['file']}:{item['line']}` {item['rule']}（{item['tool']}）：{item['message']}" for item in items[:SECTION_LIMIT]]
    if len(items) > SECTION_LIMIT:
        lines.append(f"- 还有 {len(items) - SECTION_LIMIT} 条，见 report.json")
    return lines


def render(report: dict) -> str:
    tier, buckets, coverage, timings = report["tier"], report["issues"], report["coverage"], report["timings"]
    out = ["# 代码审查报告（只提示，不拦截）", "",
           f"- 范围：`{report['base'][:10]}..{report['head'][:10]}`，改动 {len(tier['files'])} 个文件",
           f"- 风险档位：**{tier['name']}**（{'、'.join(tier['reasons']) or '无代码改动'}）" + ("，人工提档" if tier["raised_manually"] else ""),
           f"- 这一档要做：{tier['requirement']}",
           f"- 新增问题：改动行上 **{len(buckets['new_on_changed_lines'])}** 个；改动文件其他位置 {len(buckets['same_file'])} 个；基线后别处累计 {len(buckets['elsewhere'])} 个",
           f"- 多花时间：{report['seconds']} 秒", ""]
    if report["failed"]:
        out += [f"**本次不完整，“没有”不代表真的没有。没跑成：{'；'.join(f'{name}（{reason}）' for name, reason in report['failed'].items())}**", ""]
    if report["baseline_changed"]:
        out += ["**这次改了基线 baseline.json，需要人工确认。新增问题按比较基准提交的基线计算，不受这次改动影响。**", ""]
    if report["baseline_note"]:
        out += [f"注意：{report['baseline_note']}。", ""]
    nothing = ["这几项工具里没发现，但有工具没跑成，见上。"] if report["failed"] else ["没有。"]
    out += ["## 改动行上的新增问题", "", *(issue_lines(buckets["new_on_changed_lines"]) or nothing), ""]
    if buckets["same_file"]:
        out += ["## 改动文件其他位置（基线之后出现，可能是函数变复杂，也可能是早先带入）", "", *issue_lines(buckets["same_file"]), ""]
    out += ["## 改动行测试覆盖", ""]
    if "percent" in coverage:
        out.append(f"- {coverage['covered']}/{coverage['total']} 行，{coverage['percent']}%（{coverage.get('scope', '')}）")
        for path, lines in list(coverage.get("uncovered", {}).items())[:15]:
            out.append(f"- 没覆盖 `{path}`：{', '.join(map(str, lines[:20]))}" + (" 等" if len(lines) > 20 else ""))
        if coverage.get("failed_tests"):
            out.append(f"- 统计时失败的测试（不代表门禁失败，这里的环境和门禁不同）：{', '.join(coverage['failed_tests'][:10])}")
    if coverage.get("status") != "已统计":
        out.append(f"- {coverage.get('status', '没有统计')}")
    if coverage.get("frontend_without_test"):
        out.append(f"- 没被任何前端测试提到的改动文件：{', '.join(coverage['frontend_without_test'][:15])}")
    if coverage.get("frontend_note"):
        out.append(f"- {coverage['frontend_note']}")
    out += ["", "## 风险判定依据", ""]
    for item in tier["files"][:SECTION_LIMIT]:
        out.append(f"- {risk.TIER_NAMES[item['tier']]} `{item['file']}`（{item['reason']}）")
    if len(tier["files"]) > SECTION_LIMIT:
        out.append(f"- 还有 {len(tier['files']) - SECTION_LIMIT} 个文件，见 report.json")
    known = report["known_issues"]
    if known:
        out += ["", "## 已知现存问题（这阶段不修）", ""]
        out += [f"- {item['title']}：{item['detail']}（核实于 {item['verified']}）" for item in known]
    out += ["", "## 各工具耗时和没跑的项", ""]
    out += [f"- {name}：{value} 秒" for name, value in timings.items() if name != "_errors"]
    out += [f"- {name} 没跑成：{reason}" for name, reason in report["failed"].items()]
    out += [f"- {name} 没跑：{reason}" for name, reason in report["skipped"].items()]
    return "\n".join(out) + "\n"


def collect_issues(args: argparse.Namespace, timings: dict, skipped: dict, audit: bool) -> list[dict]:
    python, tools = args.python, args.tools_python
    issues = run_ruff(python, timings)
    if Path(tools).exists():
        cache = Path(args.cache_dir)
        issues += run_mypy(tools, python, cache / "mypy", timings)
        issues += run_vulture(tools, timings)
    else:
        skipped["mypy、vulture、覆盖率"] = f"没装工具环境 {tools}，运行 sh scripts/install-review-tools.sh"
    if (WEB / "node_modules/typescript").is_dir() and shutil.which(args.node):
        issues += run_tsc(args.node, timings)
        issues += run_ts_metrics(args.node, timings)
    else:
        skipped["tsc、前端复杂度"] = "前端依赖没装（apps/admin-web 下 npm ci）"
    issues += find_duplicates(timings)
    if audit:
        issues += run_dependency_audit(python, timings)
    else:
        skipped["依赖漏洞"] = "要联网，依赖文件没改时只在 CI 跑"
    return issues


def state_dir() -> Path:
    """放在所有 worktree 共用的 Git 目录，试运行统计才能合在一起。"""
    path = Path(git("rev-parse", "--git-common-dir").strip())
    return (path if path.is_absolute() else ROOT / path) / "oa-review"


def trial_summary() -> int:
    log = state_dir() / "trial.jsonl"
    rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
    if not rows:
        print("还没有记录。")
        return 0
    seconds = [row["seconds"] for row in rows]
    print(f"推送 {len(rows)} 次；档位 {dict(Counter(row['tier'] for row in rows))}；改动行新增问题合计 {sum(row['new'] for row in rows)}；"
          f"平均多花 {sum(seconds) / len(seconds):.0f} 秒，最长 {max(seconds)} 秒")
    return 0


def build(args: argparse.Namespace) -> dict:
    started = time.monotonic()
    head = git("rev-parse", args.head).strip()
    base = resolve_base(head, args.base)
    # quotepath 关掉，否则中文文件名被转义，解析不到。
    diff = git("-c", "core.quotepath=off", "diff", "--unified=0", "--no-color", "--no-ext-diff", base, head)
    changed, added, _ = parse_diff(diff)
    files = changed_paths(base, head, changed)
    messages = git("log", "--format=%B", f"{base}..{head}")
    raise_to = max((args.raise_to or "low", risk.manual_tier(messages) or "low"), key=risk.TIERS.index)
    tier = risk.classify(files, added, raise_to=raise_to)
    timings: dict = {}
    skipped: dict = {}
    dependencies_changed = any(re.search(r"requirements|package(-lock)?\.json$", path) for path in files)
    issues = collect_issues(args, timings, skipped, args.audit or dependencies_changed)
    baseline, baseline_note = load_baseline(base, timings)
    if not baseline and "基线" not in timings.get("_errors", {}):
        skipped["基线"] = "没有基线，所有问题都会算新增"
    buckets = split_new(issues, baseline, changed)
    if not Path(args.tools_python).exists():
        coverage = {"status": "没装工具环境，本次没有覆盖率", "frontend_note": ""}
    elif args.coverage == "none" or tier["computed"] == "low":
        coverage = {"status": "这次没有需要统计覆盖率的后端代码" if tier["computed"] == "low" else "本次关闭", "frontend_note": ""}
    else:
        try:
            coverage = measure_coverage(changed, args.python, args.tools_python, args.jobs, args.coverage_timeout, args.coverage == "all", timings, args.report_dir)
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
            fail_tool(timings, "覆盖率", f"{type(exc).__name__}: {exc}")
            coverage = {"status": "覆盖率没统计成", "frontend_note": ""}
    failed = timings.pop("_errors", {})
    return {"format": 1, "base": base, "head": head, "tier": tier, "issues": buckets, "coverage": coverage, "timings": timings, "skipped": skipped, "failed": failed,
            "baseline_changed": BASELINE.relative_to(ROOT).as_posix() in files, "baseline_note": baseline_note,
            "total_scanned": len(issues), "baseline_commit": baseline.get("commit"), "known_issues": known_issues(), "seconds": round(time.monotonic() - started, 1)}


def save(report: dict, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    markdown = report_dir / "report.md"
    markdown.write_text(render(report), encoding="utf-8")
    keep = state_dir() / report["head"][:12]
    keep.mkdir(parents=True, exist_ok=True)
    shutil.copy2(markdown, keep / "report.md")
    shutil.copy2(report_dir / "report.json", keep / "report.json")
    with (state_dir() / "trial.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"head": report["head"][:12], "time": int(time.time()), "tier": report["tier"]["tier"], "new": len(report["issues"]["new_on_changed_lines"]),
                                 "coverage": report["coverage"].get("percent"), "seconds": report["seconds"]}) + "\n")
    return keep / "report.md"


def abort_on_deadline(seconds: int) -> None:
    kill_active()
    print(f"OA 代码审查报告超过总时限 {seconds} 秒，已放弃，不影响推送。", file=sys.stderr, flush=True)
    os._exit(0)


def reusable_report(head: str) -> bool:
    path = state_dir() / git("rev-parse", head).strip()[:12] / "report.json"
    if not path.exists():
        return False
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("failed"):
        return False
    print(f"OA 代码审查（只提示）：同一提交的报告已有，不重跑：{path.with_name('report.md')}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, help="报告目录，默认放进 Git 目录的 oa-review/")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--base", help="比较基准提交，默认和 origin/dev 的分叉点")
    parser.add_argument("--raise-to", choices=risk.TIERS, help="人工提档，只能提不能降")
    parser.add_argument("--python", default=sys.executable, help="门禁用的 Python（带业务依赖）")
    parser.add_argument("--tools-python", default=str(DEFAULT_TOOLS_PYTHON))
    parser.add_argument("--node", default=os.environ.get("OA_QUALITY_NODE", "node"))
    parser.add_argument("--audit", action="store_true", help="跑依赖漏洞扫描（要联网）")
    parser.add_argument("--coverage", choices=("related", "all", "none"), default="related")
    parser.add_argument("--coverage-timeout", type=int, default=150)
    parser.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 2))
    parser.add_argument("--cache-dir", help="mypy 缓存位置，默认放进 Git 目录")
    parser.add_argument("--deadline", type=int, default=180, help="总时限（秒），到点放弃并以 0 退出")
    parser.add_argument("--reuse", action="store_true", help="同一提交已有完整报告就不再跑（发布时 dev、main 各推一次）")
    parser.add_argument("--update-baseline", action="store_true", help="把当前全部问题写成基线")
    parser.add_argument("--allow-partial-baseline", action="store_true", help="允许不跑依赖审计等可选项就写基线")
    parser.add_argument("--trial-summary", action="store_true", help="打印试运行的自动统计")
    args = parser.parse_args()
    # 主动时限先到，能写出“不完整”的报告；万一卡在别处，再由看门狗强制退出。两者都不影响推送。
    RUN["deadline"] = time.monotonic() + max(1, args.deadline - 10)
    watchdog = threading.Timer(args.deadline, abort_on_deadline, args=(args.deadline,))
    watchdog.daemon = True
    watchdog.start()
    try:
        if args.trial_summary:
            return trial_summary()
        if args.reuse and reusable_report(args.head):
            return 0
        # mypy 缓存和路径绑定，每个 worktree 一份。
        args.cache_dir = args.cache_dir or str(state_dir() / "cache" / hashlib.sha256(str(ROOT).encode()).hexdigest()[:10])
        args.report_dir = args.report_dir or Path(tempfile.mkdtemp(prefix="oa-review-"))
        if args.update_baseline:
            timings: dict = {}
            skipped: dict = {}
            issues = collect_issues(args, timings, skipped, args.audit)
            if timings.get("_errors") or (skipped and not args.allow_partial_baseline):
                print(f"基线没写入，有工具没跑成或没跑：{timings.get('_errors')} {skipped}")
                return 0
            if skipped:
                print(f"注意，这些项没进基线：{skipped}")
            BASELINE.write_text(json.dumps(to_baseline(issues, git("rev-parse", "HEAD").strip()), ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
            print(f"基线已写入 {BASELINE}：{len(issues)} 条，耗时 {timings}")
            return 0
        report = build(args)
        path = save(report, args.report_dir)
        buckets = report["issues"]
        coverage = report["coverage"]
        print(f"OA 代码审查（只提示）：{report['tier']['name']}；改动行新增问题 {len(buckets['new_on_changed_lines'])} 个；"
              + (f"改动行覆盖 {coverage['percent']}%；" if "percent" in coverage else "")
              + f"多花 {report['seconds']} 秒；报告：{path}")
    except Exception as exc:  # noqa: BLE001 第一阶段报告出任何错都不能影响推送
        print(f"OA 代码审查报告没产出，不影响推送：{type(exc).__name__}: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
