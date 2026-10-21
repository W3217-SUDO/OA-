"""读取已启用 DSH 原生插件随包发布的技能，交给同一个隔离脚本执行器。"""

from functools import lru_cache
import hashlib

from fastapi import HTTPException
import yaml

from app.agent_skills import AgentSkill
from . import plugins
from .plugin_packages import installed_packages


def definitions():
    active = plugins.current()
    if active is None:
        return []
    revision, home = active
    enabled = tuple(item["name"] for item in installed_packages(home) if item["enabled"] and not item["error"])
    return list(_load(revision, home, enabled))


@lru_cache(maxsize=4)
def _load(revision, home, enabled):
    result = []
    for package_name in enabled:
        package = (home / "profiles/sdk/node_modules" / package_name).resolve()
        if not package.is_relative_to(home.resolve()):
            raise HTTPException(409, "原生插件技能不能指向配置版本之外")
        directory = package / "skills"
        if not directory.exists():
            continue
        if directory.is_symlink():
            raise HTTPException(409, "原生插件技能目录不能是链接")
        for document in sorted(directory.glob("*/SKILL.md")):
            root = document.parent
            if root.is_symlink() or document.is_symlink():
                raise HTTPException(409, "原生插件技能不能引用包外文件")
            content = document.read_text(encoding="utf-8-sig")
            sections = content.replace("\r\n", "\n").split("---", 2)
            try:
                metadata = yaml.safe_load(sections[1]) if len(sections) == 3 and not sections[0].strip() else None
            except yaml.YAMLError as exc:
                raise HTTPException(409, "原生插件技能元信息格式无效") from exc
            if not isinstance(metadata, dict) or not isinstance(metadata.get("name"), str) or not metadata["name"].strip():
                raise HTTPException(409, "原生插件技能缺少有效名称")
            files = {}
            total = 0
            for path in root.rglob("*"):
                if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                    raise HTTPException(409, "原生插件技能包含链接或包外文件")
                if path.is_file():
                    size = path.stat().st_size
                    total += size
                    if size > 8 * 1024 * 1024 or total > 32 * 1024 * 1024 or len(files) >= 512:
                        raise HTTPException(413, "原生插件技能目录超过大小或数量上限")
                    files[path.relative_to(root).as_posix()] = path.read_bytes()
            from .bundles import store_files
            bundle = store_files(files)
            identifier = "native-" + hashlib.sha256((package_name + "/" + root.name).encode()).hexdigest()[:32]
            result.append(AgentSkill(id=identifier, name=metadata["name"].strip(), category="DSH 原生插件",
                description=str(metadata.get("description") or metadata["name"]), source=package_name,
                available=True, unavailable_reason="", instruction=content, quick_prompts=(), bundle=bundle))
    return tuple(result)
