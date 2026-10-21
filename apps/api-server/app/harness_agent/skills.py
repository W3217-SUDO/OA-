"""把 OA 已授权技能发布到原生技能目录，保留中文名称和原始技能编号。"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from uuid import uuid4

from fastapi import HTTPException
import yaml


def native_name(identifier: str) -> str:
    return "oa-" + hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:24]


async def definitions(identity, db):
    from app.core.permissions import _agent_skill_catalog_for_identity, _agent_skill_for_identity

    result = []
    for item in await _agent_skill_catalog_for_identity(identity, db):
        if item.get("available"):
            result.append(await _agent_skill_for_identity(item["id"], identity, db))
    return result


def _publish_file(path: Path, data: bytes):
    if path.exists():
        if path.is_symlink() or path.read_bytes() != data:
            raise HTTPException(409, "原生技能版本内容与摘要不一致")
        return
    staging = path.with_name("." + uuid4().hex)
    try:
        with staging.open("xb") as handle:
            handle.write(data)
        os.replace(staging, path)
    finally:
        staging.unlink(missing_ok=True)


def publish(directory: Path, skills) -> dict[str, Path]:
    entries = {}
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    for skill in skills:
        name = native_name(skill.id)
        # 内容摘要构成只读版本目录，启停及正文变化不覆盖旧会话用过的版本。
        digest = hashlib.sha256(json.dumps([skill.id, skill.description, skill.instruction, skill.bundle], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        target = directory / digest / name
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        text = "---\n" + yaml.safe_dump({"name": name, "description": skill.name + "：" + skill.description}, allow_unicode=True) + "---\n\n" + skill.instruction + "\n"
        path = target / "SKILL.md"
        _publish_file(path, text.encode("utf-8"))
        if skill.bundle:
            from .bundles import read_resource
            for resource in skill.bundle["files"]:
                if resource == "SKILL.md":
                    continue
                data = read_resource(skill.bundle, resource)
                destination = target / resource
                destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                _publish_file(destination, data)
        entries[name] = target
    return entries


RESOURCE_TOOL = {"type": "function", "function": {
    "name": "harness_read_skill_resource", "description": "读取当前账号已安装技能中的参考资料、脚本源码或资源清单。name 使用原生 skill 名、技能编号或当前账号可用的唯一技能名称，path 为相对路径；不能读取服务器其他文件。",
    "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "path": {"type": "string", "maxLength": 500},
                    "offset": {"type": "integer", "minimum": 0}, "limit": {"type": "integer", "minimum": 1, "maximum": 16000}},
                    "required": ["name", "path"], "additionalProperties": False}}}

SCRIPT_TOOL = {"type": "function", "function": {
    "name": "harness_run_skill_script", "description": "在受控容器中执行当前账号已安装且启用技能包内的 Node/Python/Bash 脚本。先用 skill 加载指令；name 为原生技能名、技能编号或当前账号可用的唯一技能名称，path 为包内相对脚本路径，args 为独立参数数组，指令的baseDir在此环境对应/skill，临时输出目录为/work。仅准公网HTTP/HTTPS，不提供OA凭据和内网访问，不保留临时输出文件；失败和缺依赖必须如实说明。",
    "parameters": {"type": "object", "properties": {"name": {"type": "string"},
        "path": {"type": "string", "maxLength": 500}, "args": {"type": "array", "maxItems": 32,
        "items": {"type": "string", "maxLength": 2000}}}, "required": ["name", "path", "args"],
        "additionalProperties": False}}}


CODE_TOOL = {"type": "function", "function": {
    "name": "harness_run_code", "description": "在隔离沙箱里运行你写的 Python / Node / Bash 代码，用于计算、统计、数据整理、格式转换、调用公网接口等。沙箱没有 OA 数据库、凭据和内网，只准公网 HTTP/HTTPS，每次最多运行 45 秒、输出最多 64000 字节，文件不保留（/work 为临时目录）。需要的数据由你在代码里写入；用 print 输出结果。失败和缺依赖必须如实说明，不得声称已执行。",
    "parameters": {"type": "object", "properties": {
        "language": {"type": "string", "enum": ["python", "node", "bash"]},
        "code": {"type": "string", "minLength": 1, "maxLength": 200000},
        "args": {"type": "array", "maxItems": 32, "items": {"type": "string", "maxLength": 2000}}},
        "required": ["language", "code"], "additionalProperties": False}}}


def sandbox_allowed(identity) -> bool:
    """沙箱可运行任意代码，只开放给系统管理员。"""
    from app.agent_permissions import is_actual_system_admin
    return is_actual_system_admin(identity)


class WorkspaceTools:
    def __init__(self, delegate, identity, db, on_progress=None):
        self.delegate, self.identity, self.db = delegate, identity, db
        self.on_progress = on_progress

    async def execute(self, name, arguments):
        """所有工具调用统一在这里记录：先告诉前端正在调用什么，结束后把名称、参数摘要和结果状态记入本轮调用记录。"""
        import time
        from . import tool_trace
        label = tool_trace.describe(name, arguments)[0]
        if self.on_progress:
            await self.on_progress("正在调用：" + label)
        started, ok = time.perf_counter(), False
        try:
            result = await self._execute(name, arguments)
            ok = not (isinstance(result, dict) and result.get("isError"))
            return result
        finally:
            tool_trace.record(name, arguments, ok=ok, started=started)

    async def _execute(self, name, arguments):
        if name == "harness_run_code":
            if not sandbox_allowed(self.identity):
                raise HTTPException(403, "沙箱运行代码仅限系统管理员")
            from .script_runtime import run_code
            if not isinstance(arguments, dict) or set(arguments) - {"language", "code", "args"}:
                raise HTTPException(422, "沙箱参数错误")
            return await run_code(arguments.get("language"), arguments.get("code"), arguments.get("args", []))
        if name not in {"harness_read_skill_resource", "harness_run_skill_script"}:
            return await self.delegate.execute(name, arguments)
        allowed = {"name", "path", "args"} if name == "harness_run_skill_script" else {"name", "path", "offset", "limit"}
        if not isinstance(arguments, dict) or set(arguments) - allowed:
            raise HTTPException(422, "技能资源参数错误")
        available = await definitions(self.identity, self.db)
        # 原生插件自己的 skill 提供器可加载指令；资源执行同样只接受当前已启用插件的完整技能快照。
        from .native_plugin_skills import definitions as plugin_definitions
        available = [*available, *plugin_definitions()]
        requested = arguments.get("name")
        matched = [item for item in available if requested in (native_name(item.id), item.id, item.name)]
        if not matched:
            raise HTTPException(404, "技能不存在或当前账号无权使用")
        if len(matched) != 1:
            raise HTTPException(409, "技能名称存在重复，请使用加载该技能时显示的原生技能名或技能编号")
        skill = matched[0]
        if name == "harness_run_skill_script":
            from .script_runtime import run_script
            if self.on_progress:
                await self.on_progress("正在执行技能：" + skill.name)
            try:
                result = await run_script(skill, arguments.get("path"), arguments.get("args"))
            except asyncio.CancelledError:
                if self.on_progress:
                    await self.on_progress("技能执行已停止：" + skill.name)
                raise
            except Exception:
                if self.on_progress:
                    await self.on_progress("技能执行失败：" + skill.name)
                raise
            if self.on_progress:
                await self.on_progress(("技能执行失败：" if result["isError"] else "技能执行完成：") + skill.name)
            return result
        relative = PurePosixPath(str(arguments.get("path", "")))
        if relative.is_absolute() or ".." in relative.parts or "\\" in str(relative) or not relative.parts:
            raise HTTPException(422, "技能资源路径无效")
        if str(relative) == "SKILL.md":
            content = skill.instruction
        elif skill.bundle:
            from .bundles import read_resource
            data = read_resource(skill.bundle, str(relative))
            try:
                content = data.decode("utf-8-sig")
            except UnicodeDecodeError:
                return {"path": str(relative), "binary": True, "size": len(data),
                        "sha256": hashlib.sha256(data).hexdigest(), "source": skill.source}
        else:
            from app.areas.capability_market.catalog import catalog, entry
            matched = next((entry(item["id"]) for item in catalog()["items"]
                            if item.get("source") == skill.source), None)
            if matched is None or str(relative) not in matched.get("resources", {}):
                raise HTTPException(404, "此技能未安装该资源；请安装包含参考资料的完整技能包")
            content = matched["resources"][str(relative)]
        offset, limit = arguments.get("offset", 0), arguments.get("limit", 6000)
        if type(offset) is not int or type(limit) is not int or not 0 <= offset <= len(content) or not 1 <= limit <= 16000:
            raise HTTPException(422, "技能资源读取范围错误")
        end = min(offset + limit, len(content))
        return {"content": content[offset:end], "offset": offset, "next_offset": end if end < len(content) else None,
                "total_characters": len(content), "source": skill.source}
