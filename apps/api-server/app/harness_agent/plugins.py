"""全所 DSH 插件使用独立配置版本，既有会话继续保留各自历史与工作区。"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
from uuid import uuid4

from fastapi import HTTPException
import yaml

from app.config import settings
from .lease import session_lease
from .paths import filesystem_path, native_path
from .plugin_packages import (CORE_BUNDLES, PACKAGE_NAME, cli, installed_packages, manifest,
                              package_manager_ready, validate_spec, write_manifest)


def root() -> Path:
    from app.areas.personal_agent.service import _storage_root
    from app.core.constants import UPLOAD_ROOT

    base = Path(settings.deepseek_harness_root.strip()).expanduser() if settings.deepseek_harness_root.strip() else _storage_root().parent / "private-harness"
    directory = filesystem_path(base / "global-plugins")
    public = filesystem_path(UPLOAD_ROOT)
    if not base.is_absolute() or directory == public or public in directory.parents:
        raise HTTPException(503, "DSH 插件必须存储在独立的私有目录")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    return directory


def current() -> tuple[str, Path] | None:
    directory = root()
    pointer = directory / "current.json"
    if not pointer.exists():
        return None
    try:
        revision = json.loads(pointer.read_bytes())["revision"]
        if not isinstance(revision, str) or not re.fullmatch(r"[a-f0-9]{32}", revision):
            raise ValueError
        home = directory / "versions" / revision
        if home.is_symlink() or not home.is_dir():
            raise ValueError
        manifest(home)
        return revision, home
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(409, "现用 DSH 插件版本损坏，未切换工作区") from exc


def overview() -> dict:
    active = current()
    ready = package_manager_ready()
    return {"items": installed_packages(active[1]) if active else [],
            "revision": active[0] if active else "", "package_manager_ready": ready,
            "error": "" if ready else "插件安装工具 pnpm 未就绪，当前不能安装或卸载插件",
            "effective": "对后续消息生效，正在执行的回复保持原插件版本"}


def change(action: str, data: dict) -> dict:
    directory = root()
    with session_lease(directory / "management.lock"):
        if not package_manager_ready() and action in {"install", "remove"}:
            raise HTTPException(503, "插件安装工具 pnpm 未就绪")
        before = current()
        revision = uuid4().hex
        home = directory / "versions" / revision
        home.parent.mkdir(exist_ok=True, mode=0o700)
        published = False
        try:
            if before:
                shutil.copytree(before[1], home, symlinks=True)
            else:
                home.mkdir(mode=0o700)
                cli(home, ["--profile", "sdk", "--dump-default-config"], timeout=20)
            value = manifest(home)
            if action == "install":
                spec = validate_spec(data["spec"])
                builds = data.get("allow_builds", [])
                if any(not PACKAGE_NAME.fullmatch(name) for name in builds):
                    raise HTTPException(422, "构建授权必须填写准确的 npm 包名")
                if builds:
                    path = home / "profiles/sdk/pnpm-workspace.yaml"
                    workspace = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
                    workspace = workspace or {}
                    workspace.setdefault("allowBuilds", {}).update({name: True for name in builds})
                    path.write_text(yaml.safe_dump(workspace, allow_unicode=True), encoding="utf-8")
                previous = dict(value.get("dependencies", {}))
                cli(home, ["plugin", "--profile", "sdk", "add", "--save-exact", spec])
                packages = installed_packages(home)
                changed = [item for item in packages if item["name"] not in previous or item["source"] != previous[item["name"]]]
                if not changed:
                    raise HTTPException(409, "该插件版本已安装；请刷新列表或选择明确的新版本")
                if any(item["error"] for item in changed):
                    raise HTTPException(422, "此软件包未声明有效的 DSH bundle，未启用到系统")
            else:
                name = data["name"]
                if name in CORE_BUNDLES or name not in value.get("dependencies", {}):
                    raise HTTPException(404, "未找到可管理的外部插件")
                if action == "remove":
                    cli(home, ["plugin", "--profile", "sdk", "remove", name])
                elif action == "toggle":
                    bundles = value["dsh"]["profile"]["bundles"]
                    value["dsh"]["profile"]["bundles"] = [item for item in bundles if item != name]
                    if data["enabled"]:
                        package = next(item for item in installed_packages(home) if item["name"] == name)
                        if package["error"]:
                            raise HTTPException(409, package["error"])
                        value["dsh"]["profile"]["bundles"].append(name)
                    write_manifest(home, value)
                else:
                    raise HTTPException(422, "不支持的插件操作")
            # 官方配置合成校验通过后才切换；失败不修改现用版本。
            cli(home, ["--profile", "sdk", "--dump-config"], timeout=20)
            marker = {"revision": revision, "changed_at": datetime.now(timezone.utc).isoformat()}
            staged = directory / (revision + ".json")
            staged.write_text(json.dumps(marker), encoding="utf-8")
            os.replace(staged, directory / "current.json")
            published = True
            return overview()
        except BaseException:
            if not published and home.exists() and home.resolve().parent == (directory / "versions").resolve() and not home.is_symlink():
                shutil.rmtree(home)
            raise


def attach(home: Path) -> str:
    active = current()
    if active is None:
        return "sdk"
    revision, shared = active
    if not any(item["enabled"] for item in installed_packages(shared)):
        return "sdk"
    profile = "oa-plugins-" + revision
    target = home / "profiles" / profile
    target.parent.mkdir(exist_ok=True, mode=0o700)
    if target.exists() or target.is_symlink():
        if not target.is_symlink() or target.resolve() != (shared / "profiles/sdk").resolve():
            raise HTTPException(409, "工作区插件配置映射不一致，未覆盖现有目录")
    else:
        target.symlink_to(native_path(shared / "profiles/sdk"), target_is_directory=True)
    return profile
