"""生成并校验仅含正式运行文件的可移植交付包。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

REPOSITORY = Path(__file__).resolve().parents[1]
API_RESOURCE_FILES = {
    "legacy_schema_manifest.json",
    "core/investigation_regions.json",
    "areas/crm/conflict_rules_20260928.json",
}
WEB_EXTENSIONS = {
    ".html", ".js", ".css", ".json", ".svg", ".png", ".jpg", ".jpeg",
    ".gif", ".webp", ".ico", ".woff", ".woff2", ".ttf", ".txt", ".webmanifest",
}
BLOCKED_DIRECTORIES = {
    "tests", "test", "fixtures", "fixture", "mocks", "mock", "stubs", "stub",
    "__pycache__", "node_modules", ".git", ".venv", "uploads", "backup", "backups",
}
BLOCKED_EXTENSIONS = {".db", ".sqlite", ".sqlite3", ".pyc", ".pyo", ".pem", ".key", ".p12", ".pfx", ".log", ".tmp"}


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def allowed_path(relative: str) -> None:
    path = Path(relative)
    parts = [part.lower() for part in path.parts]
    if path.is_absolute() or ".." in parts or not parts:
        raise ValueError(f"非法运行包路径：{relative}")
    if any(part in BLOCKED_DIRECTORIES for part in parts):
        raise ValueError(f"运行包包含禁止目录：{relative}")
    name = parts[-1]
    if name.startswith(".env") or name.startswith("id_rsa") or name.startswith("id_ed25519"):
        raise ValueError(f"运行包包含凭据路径：{relative}")
    if name.startswith("test_") or "_test." in name or ".test." in name or path.suffix.lower() in BLOCKED_EXTENSIONS:
        raise ValueError(f"运行包包含测试或临时文件：{relative}")
    if relative in {"api/requirements.txt", "api/requirements.lock"}:
        return
    if relative.startswith("api/app/"):
        resource = relative.removeprefix("api/app/")
        if path.suffix == ".py" or resource in API_RESOURCE_FILES:
            return
    if relative.startswith("web/") and path.suffix.lower() in WEB_EXTENSIONS:
        return
    raise ValueError(f"运行包包含白名单之外的文件：{relative}")


def frontend_inputs(frontend: Path) -> dict[str, str]:
    files = []
    files.append(frontend / "scripts/build-production.mjs")
    for directory in ("src", "public"):
        base = frontend / directory
        if base.exists():
            files.extend(path for path in base.rglob("*") if path.is_file())
    files.extend(path for path in frontend.iterdir() if path.is_file() and (
        path.name in {"package.json", "package-lock.json", "index.html", "vite.config.ts"}
        or path.name.startswith("tsconfig") and path.suffix == ".json"
    ))
    result = {}
    for path in sorted(files):
        if path.is_symlink():
            raise ValueError(f"构建输入不能是符号链接：{path}")
        result[path.relative_to(frontend).as_posix()] = digest(path)
    return dict(sorted(result.items()))


def verify(package: Path) -> dict:
    if package.is_symlink():
        raise ValueError("运行包目录不能是符号链接")
    manifest_path = package / "runtime-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != 1 or not isinstance(manifest.get("files"), dict) or not manifest["files"]:
        raise ValueError("运行包清单无效")
    actual = set()
    for path in package.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"运行包包含符号链接：{path}")
        if path.is_dir():
            if path.name.lower() in BLOCKED_DIRECTORIES:
                raise ValueError(f"运行包包含禁止目录：{path}")
            continue
        relative = path.relative_to(package).as_posix()
        if relative == "runtime-manifest.json":
            continue
        allowed_path(relative)
        actual.add(relative)
    if actual != set(manifest["files"]):
        raise ValueError("运行包文件集合与清单不一致")
    for relative, expected in manifest["files"].items():
        allowed_path(relative)
        path = package / relative
        if not isinstance(expected, str) or digest(path) != expected:
            raise ValueError(f"运行包哈希不一致：{relative}")
    required = {"api/app/main.py", "api/requirements.txt", "api/requirements.lock", "web/index.html", "web/build-info.json"}
    required.update(f"api/app/{relative}" for relative in API_RESOURCE_FILES)
    if not required.issubset(actual):
        raise ValueError("运行包缺少必需入口或构建标记")
    info = json.loads((package / "web/build-info.json").read_text(encoding="utf-8"))
    if info.get("version") != manifest.get("version") or info.get("source_commit") != manifest.get("source_commit"):
        raise ValueError("前端构建与运行包版本/提交不一致")
    return manifest


def build(repository: Path, destination: Path) -> dict:
    repository = repository.resolve()
    destination = destination.resolve()
    if destination.is_relative_to(repository):
        raise ValueError("运行包输出目录必须位于源码目录之外")
    if destination.exists():
        raise FileExistsError(f"运行包输出目录已存在：{destination}")
    frontend = repository / "apps/admin-web"
    info = json.loads((frontend / "dist/build-info.json").read_text(encoding="utf-8"))
    if info.get("format") != 1 or info.get("source_files") != frontend_inputs(frontend):
        raise ValueError("前端产物与当前源码不一致，请先运行生产构建")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repository, text=True).strip()
    version = json.loads((frontend / "package.json").read_text(encoding="utf-8"))["version"]
    if info.get("source_commit") != commit or info.get("version") != version:
        raise ValueError("前端产物的提交/版本已过期，请重新构建")
    sources = []
    api = repository / "apps/api-server"
    for source in (api / "app").rglob("*"):
        if source.is_symlink():
            raise ValueError(f"API源码不能是符号链接：{source}")
        if not source.is_file() or "__pycache__" in source.parts:
            continue
        relative = source.relative_to(api / "app").as_posix()
        if source.suffix == ".py" or relative in API_RESOURCE_FILES:
            sources.append((source, f"api/app/{relative}"))
        elif source.suffix != ".md":
            raise ValueError(f"API存在未声明运行资源：{relative}")
    sources.append((api / "requirements.txt", "api/requirements.txt"))
    sources.append((api / "requirements.lock", "api/requirements.lock"))
    for source in (frontend / "dist").rglob("*"):
        if source.is_symlink():
            raise ValueError(f"前端产物不能是符号链接：{source}")
        if source.is_file():
            sources.append((source, f"web/{source.relative_to(frontend / 'dist').as_posix()}"))
    for source, relative in sources:
        allowed_path(relative)
        if not source.is_file():
            raise FileNotFoundError(source)
    destination.mkdir(parents=True)
    hashes = {}
    for source, relative in sources:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        hashes[relative] = digest(target)
        if digest(source) != hashes[relative]:
            raise ValueError(f"复制期间源文件改变：{relative}")
    manifest = {"format":1, "version":version, "source_commit":commit, "files":dict(sorted(hashes.items()))}
    (destination / "runtime-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return verify(destination)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "verify"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repository", type=Path, default=REPOSITORY)
    args = parser.parse_args()
    result = build(args.repository, args.output) if args.action == "build" else verify(args.output)
    print(json.dumps({"status":"passed", "version":result["version"], "commit":result["source_commit"], "file_count":len(result["files"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
