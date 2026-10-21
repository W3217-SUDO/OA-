"""通过官方 DSH CLI 管理原生插件包，不执行用户拼接的 shell 命令。"""

import asyncio
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess

from fastapi import HTTPException

from app.config import settings
from .paths import native_path

CORE_BUNDLES = ("@deepseek-ai/dsh-base", "@deepseek-ai/dsh-sdk-app")
PACKAGE_NAME = re.compile(r"(?:@[a-z0-9._-]+/)?[a-z0-9][a-z0-9._-]*")


def package_environment(home: Path) -> dict:
    from .runtime import _environment

    environment = {**os.environ, **_environment(), "DSH_HOME": native_path(home),
                   "OA_MODEL_API_KEY": "", "CI": "true", "GIT_TERMINAL_PROMPT": "0"}
    configured = settings.deepseek_harness_plugin_path.strip()
    if configured:
        if not Path(configured).is_absolute() or not Path(configured).is_dir():
            raise HTTPException(503, "DSH 插件工具目录未就绪")
        environment["PATH"] = configured + os.pathsep + environment.get("PATH", "")
    return environment


def validate_spec(spec: str) -> str:
    spec = spec.strip()
    npm = r"(?:@[a-z0-9._-]+/)?[a-z0-9][a-z0-9._-]*(?:@[a-zA-Z0-9.*^~+<>=| -]+)?"
    github = r"(?:github:|https://github\.com/)[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+(?:#[a-zA-Z0-9_./-]+)?"
    if len(spec) > 500 or not re.fullmatch(f"(?:{npm}|{github})", spec):
        raise HTTPException(422, "请输入 npm 包名（可带版本）或 GitHub 仓库地址，不接受命令或服务器路径")
    return spec


def manifest(home: Path) -> dict:
    path = home / "profiles/sdk/package.json"
    try:
        value = json.loads(path.read_bytes())
        bundles = value["dsh"]["profile"]["bundles"]
        if not isinstance(bundles, list) or any(not isinstance(name, str) for name in bundles):
            raise ValueError
        if not all(name in bundles for name in CORE_BUNDLES):
            raise ValueError
        dependencies = value.get("dependencies", {})
        if not isinstance(dependencies, dict) or any(
            not isinstance(name, str) or not isinstance(source, str) for name, source in dependencies.items()
        ):
            raise ValueError
        return value
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(409, "DSH 插件配置损坏，未覆盖现有版本") from exc


def write_manifest(home: Path, value: dict):
    (home / "profiles/sdk/package.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cli(home: Path, arguments: list[str], *, timeout: int = 75) -> str:
    from deepseek_harness_runtime import bundled_runtime_path

    environment = package_environment(home)
    try:
        process = subprocess.Popen([str(bundled_runtime_path()), *arguments], env=environment,
                                   cwd=native_path(home), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=os.name != "nt",
                                   creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
    except OSError as exc:
        raise HTTPException(503, "DSH 插件执行环境不可用") from exc
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=10, check=True)
        else:
            os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise HTTPException(504, "DSH 插件操作超时，已结束安装进程，现用配置未切换") from exc
    if process.returncode:
        detail = (stderr or stdout).decode("utf-8", errors="replace")[-6000:]
        raise HTTPException(422, "DSH 原生插件操作失败：\n" + detail)
    return stdout.decode("utf-8", errors="replace")


def package_manager_ready() -> bool:
    try:
        return bool(shutil.which("pnpm", path=package_environment(Path.cwd()).get("PATH")))
    except HTTPException:
        return False


def installed_packages(home: Path) -> list[dict]:
    value = manifest(home)
    enabled = value["dsh"]["profile"]["bundles"]
    items = []
    for name, source in value.get("dependencies", {}).items():
        if name in CORE_BUNDLES:
            continue
        if not PACKAGE_NAME.fullmatch(name):
            raise HTTPException(409, "DSH 插件包名无效")
        try:
            package = json.loads((home / "profiles/sdk/node_modules" / name / "package.json").read_bytes())
            if not isinstance(package, dict) or not isinstance(package.get("dsh"), dict):
                raise ValueError
            bundle = package["dsh"].get("bundle")
            if not isinstance(bundle, dict) or not bundle.get("patch"):
                raise ValueError
            if any(not isinstance(package.get(key, ""), str) for key in ("version", "description")):
                raise ValueError
            items.append({"name": name, "version": package.get("version", ""),
                          "description": package.get("description", ""), "source": source,
                          "enabled": name in enabled, "error": ""})
        except (OSError, ValueError, TypeError):
            items.append({"name": name, "version": "", "description": "", "source": source,
                          "enabled": name in enabled, "error": "不是有效的 DSH bundle 或插件文件缺失"})
    return items


async def run_operation(function, *args):
    # 原生包管理和配置校验均在线程执行，不阻塞 OA API 事件循环。
    return await asyncio.to_thread(function, *args)
