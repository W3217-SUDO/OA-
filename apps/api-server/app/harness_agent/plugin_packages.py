"""通过官方 DSH CLI 管理原生插件包，不执行用户拼接的 shell 命令。"""

import asyncio
import json
import os
from pathlib import Path
import re
import shlex
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
    return environment


def validate_spec(spec: str) -> str:
    spec = spec.strip()
    if len(spec) > 500:
        raise HTTPException(422, "插件来源过长，请填写一个 npm 包名或 GitHub 仓库地址")
    if re.match(r"^dsh\s", spec):
        # 只读取安装命令中的来源，不执行命令，也不使用外部配置名称。
        try:
            tokens = shlex.split(spec)
        except ValueError as exc:
            raise HTTPException(422, "安装命令的引号不完整，请检查后重试") from exc
        tokens = tokens[1:]
        profile_seen = False
        for position in (0, 1):
            if len(tokens) > position and tokens[position].startswith("--profile"):
                option = tokens[position]
                if profile_seen:
                    raise HTTPException(422, "安装命令不能重复指定 profile")
                if option == "--profile" and len(tokens) > position + 1:
                    profile = tokens[position + 1]
                    del tokens[position:position + 2]
                elif option.startswith("--profile="):
                    profile = option.removeprefix("--profile=")
                    del tokens[position]
                else:
                    raise HTTPException(422, "安装命令的 profile 参数无效")
                if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", profile):
                    raise HTTPException(422, "安装命令的 profile 参数无效")
                profile_seen = True
        if tokens[:2] != ["plugin", "add"]:
            raise HTTPException(422, "这里只接受 dsh plugin add 安装命令、npm 包名或 GitHub 仓库地址")
        sources = tokens[2:]
        if sources[:1] == ["--save-exact"]:
            sources = sources[1:]
        if len(sources) != 1:
            raise HTTPException(422, "每次只安装一个插件，请移除额外参数或其他命令")
        spec = sources[0]
    npm = r"(?:@[a-z0-9._-]+/)?[a-z0-9][a-z0-9._-]*(?:@[a-zA-Z0-9.*^~+<>=| -]+)?"
    github = r"(?:github:|https://github\.com/)[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+(?:#[a-zA-Z0-9_./-]+)?"
    if len(spec) > 500 or not re.fullmatch(f"(?:{npm}|{github})", spec):
        raise HTTPException(422, "未识别到有效插件来源，请填写 npm 包名、GitHub 仓库地址或单条 dsh plugin add 安装命令")
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
