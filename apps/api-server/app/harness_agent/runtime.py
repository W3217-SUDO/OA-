"""官方 SDK 的运行边界：每个工作区会话独立持久化，OA 继续校验业务身份。"""

from __future__ import annotations

import asyncio
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
import yaml

from app.config import settings
from .bridge import workspace_mcp
from .skills import RESOURCE_TOOL, SCRIPT_TOOL, WorkspaceTools, definitions, publish
from .lease import session_lease
from .paths import filesystem_path, native_path

SDK_VERSION = "0.2.1rc2"
_SLOTS = asyncio.Semaphore(max(1, min(settings.langgraph_max_concurrency, 32)))


def readiness() -> dict[str, Any]:
    try:
        installed = version("deepseek-harness-sdk")
        runtime_installed = version("deepseek-harness-runtime-bin")
        from deepseek_harness_runtime import bundled_runtime_path
        bundled_runtime_path()
    except (PackageNotFoundError, ImportError, OSError, ValueError):
        return {"ready": False, "error": "harness_runtime_not_installed", "version": SDK_VERSION}
    matched = installed == runtime_installed == SDK_VERSION
    return {"ready": matched, "error": "" if matched else "harness_runtime_version_mismatch",
            "version": installed}


def workspace_paths(owner: str, workspace: str, conversation: str):
    from app.areas.personal_agent.service import _storage_root

    configured = settings.deepseek_harness_root.strip()
    root = Path(configured).expanduser() if configured else _storage_root().parent / "private-harness"
    if not root.is_absolute():
        raise HTTPException(503, "Harness 存储目录必须为绝对路径")
    root = filesystem_path(root)
    from app.core.constants import UPLOAD_ROOT
    public = filesystem_path(UPLOAD_ROOT)
    if root == public or public in root.parents:
        raise HTTPException(503, "Harness 会话不能存放在公开附件目录中")
    owner_key = hashlib.sha256(owner.casefold().encode()).hexdigest()
    workspace_key = hashlib.sha256(workspace.encode()).hexdigest()
    session_key = hashlib.sha256(json.dumps([owner_key, workspace, conversation]).encode()).hexdigest()
    identifier = "oa-" + session_key
    user_root = root / owner_key
    cwd = user_root / "workspaces" / workspace_key
    home = user_root / "sessions" / session_key
    for directory in (cwd, home):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    return identifier, cwd, home


def _patch(url, token, schema, directories, mode_supported, response_mode, memory=None, native_plugins=False):
    model = {"id": settings.langgraph_model, "name": settings.langgraph_model, "input": ["text", "image"]}
    provider = {"displayName": "沪知已配置模型", "apiKeyEnv": "OA_MODEL_API_KEY", "api": "openai-completions",
                "baseURL": settings.langgraph_api_base_url, "models": [model],
                "headers": {"Connection": "close"}, "timeoutMs": 120000, "streamIdleTimeoutMs": 90000,
                "retryPolicy": {"mode": "normal", "maxRetries": 0}}
    if mode_supported:
        model["reasoningEfforts"] = {"off": "off", "high": "high"}
        provider["compat"] = {"thinkingFormat": "deepseek", "supportsReasoningEffort": False}
        provider["reasoning"] = "off" if response_mode == "fast" else "high"
    allow = ["skill", *["mcp__oa__" + item["function"]["name"] for item in schema]]
    persona = "你是沪知办公系统的 AI 助手，使用当前工作区已授权的技能和工具。技能使用 skill 加载；技能中的相对路径通过 mcp__oa__harness_read_skill_resource 读取，name 使用技能原生名称。技能包中的 Node/Python/Bash 脚本通过 mcp__oa__harness_run_skill_script 执行，path 为包内相对路径，args 为参数数组；无需为每个技能新增适配器。此执行器只准公网HTTP/HTTPS，不提供OA凭据、内网或其他工作区文件，不保留临时输出文件。仅依据执行结果回答，不声称未执行的操作成功。缺少依赖或执行失败必须明确说明。外部购买、提交、删除等写操作需用户明确授权。OA 业务操作仍使用已授权工具并保留前端写入确认，不能通过技能脚本绕过。工具结果及本轮最新 OA 操作状态优先于旧会话记忆。"
    if memory is not None:
        from .memory import INSTRUCTION, TOOLS
        allow.extend('mcp__engram__' + name for name in TOOLS)
        persona += INSTRUCTION
    return [
        # 安装外部插件不同时开放原有宿主编码工具；OA 业务权限仍由 MCP 校验。
        *([{"id": name, "disabled": True} for name in (
            "tool-plugin-manager", "tool-working-directory", "tool-bash", "tool-pwsh", "tool-jobs",
            "tool-fs", "tool-fs-search", "tool-subagent-control", "tool-subagent-list-agents",
            "tool-subagent", "tool-subagent-fork", "tool-workflow", "tool-todo", "tool-goal", "tool-web",
        )] if native_plugins else []),
        {"id": "system-prompt", "config": {"personaPrefix": persona}},
        {"id": "llm-pi-ai", "config": {"providers": {"huzhi-oa": provider}}},
        {"id": "skill-filesystem", "config": {"includeDefaultRoots": False, "customSkillDirs": [native_path(path.parent) for path in directories.values()]}},
        {"id": "session-log-deepseek", "disabled": True},
        {"id": "session-telemetry-otel", "disabled": True},
        {"insert": [
            *([memory] if memory is not None else []),
            {"id": "oa-mcp", "name": "@deepseek-ai/dsh-mcp-client", "config": {
                "serverName": "oa", "transport": "streamable-http", "url": url,
                "headers": {"Authorization": "Bearer " + token}, "failOnStartupError": True,
                "reconnect": {"enabled": False}}},
            {"id": "oa-stream", "name": (Path(__file__).parent / "stream.mjs").resolve().as_uri(),
             "config": {"allowedTools": allow, "nativePlugins": native_plugins}},
        ]},
    ]


def _environment():
    # SDK 默认继承宿主环境；显式清空业务数据库、OSS、钉钉及 OA 登录相关配置。
    allowed = {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP", "LANG", "LC_ALL"}
    environment = {key: "" for key in os.environ if key.upper() not in allowed}
    configured = settings.deepseek_harness_cache_root.strip()
    cache = Path(configured).expanduser() if configured else Path(tempfile.gettempdir()) / "oa-harness-runtime"
    if not cache.is_absolute() or cache.is_symlink():
        raise HTTPException(503, "Harness 运行库缓存必须为独立绝对目录")
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    # 独立库的 Windows 原生扩展受路径长度限制，不能以深层会话目录作为 homedir。
    # 此目录仅用于可重建的运行库缓存；会话历史仍由显式 dsh_home 独立保存。
    environment.update({"HOME": str(cache), "USERPROFILE": str(cache), "OA_MODEL_API_KEY": settings.langgraph_api_key,
                        "DSH_TELEMETRY_DISABLED": "1", "DSH_PRIMARY_RUNTIME": "", "DSH_BUNDLED_OFFICE_CLI": ""})
    if settings.deepseek_harness_plugin_path.strip():
        environment["PATH"] = settings.deepseek_harness_plugin_path.strip() + os.pathsep + environment.get("PATH", "")
    return environment


def _content(messages, *, resumed):
    selected = [item for item in messages if item.get("role") == "system"] + [messages[-1]] if resumed else messages
    parts = []
    for item in selected:
        content = item.get("content", "")
        if isinstance(content, str):
            parts.append({"type": "text", "text": f"[{str(item.get('role', 'user')).upper()}]\n{content}"})
        elif isinstance(content, list):
            for block in content:
                if block.get("type") == "text":
                    parts.append({"type": "text", "text": block["text"]})
                elif block.get("type") == "image_url":
                    url = block.get("image_url", {}).get("url", "")
                    if not isinstance(url, str) or not url.startswith("data:image/") or ";base64," not in url:
                        raise HTTPException(422, "Harness 仅接收已授权读取的内联图片")
                    header, data = url.split(";base64,", 1)
                    parts.append({"type": "image", "mimeType": header[5:], "data": data})
    return parts


async def run(messages, on_delta, *, tools, schema, identity, db, workspace, conversation,
              response_mode="fast", mode_supported=False, on_progress=None):
    state = readiness()
    if not state["ready"]:
        raise HTTPException(503, "DeepSeek Harness 未就绪：" + state["error"])
    identifier, cwd, home = workspace_paths(identity["username"], workspace, conversation)
    try:
        async with asyncio.timeout(180), _SLOTS:
            with session_lease(home / "active.lock"):
                return await _run_session(messages, on_delta, tools=tools, schema=schema, identity=identity, db=db,
                                          identifier=identifier, cwd=cwd, home=home, response_mode=response_mode,
                                          mode_supported=mode_supported, on_progress=on_progress)
    except TimeoutError as exc:
        raise HTTPException(504, "Harness 排队或执行超时，未取得完成结果") from exc


async def _run_session(messages, on_delta, *, tools, schema, identity, db, identifier, cwd, home,
                       response_mode, mode_supported, on_progress):
    from deepseek_harness import DeepSeekHarness
    from deepseek_harness.errors import HarnessError

    marker = home / "oa-session.json"
    patch_path = home / ("oa-run-" + uuid4().hex + ".yml")
    harness = None
    runner = None
    try:
        resumed = marker.exists()
        if resumed:
            try:
                mapping = json.loads(marker.read_text(encoding="utf-8"))
            except (UnicodeError, ValueError):
                raise HTTPException(409, "原生会话归属记录损坏，未覆盖历史记录") from None
            if mapping != {"format": 1, "session": identifier}:
                raise HTTPException(409, "原生会话归属映射不一致，未覆盖历史记录")
        available = await definitions(identity, db)
        directories = publish(home.parent.parent / "skill-versions", available)
        guarded = WorkspaceTools(tools, identity, db, on_progress)
        schemas = [*schema, RESOURCE_TOOL, SCRIPT_TOOL]
        from .memory import configuration as memory_configuration
        memory = memory_configuration(cwd, identity['username'])
        from .plugins import attach
        profile = attach(home)
        async with workspace_mcp(guarded, schemas) as (url, secret):
            patch_path.write_text(yaml.safe_dump(_patch(url, secret, schemas, directories, mode_supported, response_mode, memory,
                                                      native_plugins=profile != "sdk"),
                                                 allow_unicode=True, sort_keys=False), encoding="utf-8")
            patch_path.chmod(0o600)
            harness = DeepSeekHarness(dsh_home=native_path(home), cwd=native_path(cwd), profile=profile, patches=(native_path(patch_path),),
                                       provider="huzhi-oa", model=settings.langgraph_model, env=_environment(),
                                       reasoning_effort=("off" if response_mode == "fast" else "high") if mode_supported else None,
                                       initialize_timeout_seconds=40, request_timeout_seconds=180)
            loop = asyncio.get_running_loop()
            queue = asyncio.Queue()

            def notification(item):
                if item.method == "oa.assistant.delta" and item.payload.get("sessionId") == identifier:
                    text = item.payload.get("text")
                    if isinstance(text, str) and text:
                        loop.call_soon_threadsafe(queue.put_nowait, ("delta", text))
                elif item.method == "session.event" and (item.payload.get("event") or {}).get("type") == "tool/call":
                    loop.call_soon_threadsafe(queue.put_nowait, ("progress", "正在调用工作区工具…"))

            def execute():
                try:
                    session = harness.resume_session(identifier) if resumed else harness.start_session(identifier)
                    session.get_working_directory()
                    if not resumed:
                        marker.write_text(json.dumps({"format": 1, "session": identifier}), encoding="utf-8")
                    return session.run(_content(messages, resumed=resumed), on_notification=notification)
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, ("finished", ""))

            if on_progress:
                await on_progress("正在启动工作区智能体…")
            runner = asyncio.create_task(asyncio.to_thread(execute))
            async with asyncio.timeout(180):
                while True:
                    kind, value = await queue.get()
                    if kind == "finished":
                        break
                    if kind == "delta":
                        await on_delta(value)
                    elif on_progress:
                        await on_progress(value)
                result = await runner
            if result.finish_reason != "completed" or not result.final_response.strip():
                ending = next((item.get("data", {}).get("reason", {}) for item in reversed(result.events)
                               if item.get("type") == "turn/end"), {})
                code = str(ending.get("error", {}).get("code", ""))
                safe_code = code if re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", code) else "unknown"
                raise HTTPException(502, f"Harness 本轮未完成（{result.finish_reason} / {safe_code}），未确认任何未执行操作成功")
            return result.final_response.strip()
    except TimeoutError as exc:
        raise HTTPException(504, "Harness 本轮执行超时，未取得完成结果") from exc
    except HarnessError as exc:
        # 上游异常可能携带 stderr 或模型端点内容，只公开明确的故障类别。
        raise HTTPException(502, "Harness 协议或运行时失败：" + type(exc).__name__) from None
    except OSError as exc:
        raise HTTPException(503, "Harness 本地运行资源不可用，系统错误码：" + str(exc.errno)) from None
    finally:
        if harness is not None:
            await asyncio.to_thread(harness.close)
        if runner is not None:
            await asyncio.gather(runner, return_exceptions=True)
        patch_path.unlink(missing_ok=True)
