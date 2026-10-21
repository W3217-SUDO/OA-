"""官方 SDK 的运行边界：每个工作区会话独立持久化，OA 继续校验业务身份。"""

from __future__ import annotations

import asyncio
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import os
import re
import logging
import tempfile
import time
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

logger = logging.getLogger(__name__)
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
    environment = {key: value if key.upper() in allowed else "" for key, value in os.environ.items()}
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


# ---- 常驻会话 ----
# 每个会话的运行时启动（进程、工具通道、技能发布）约占每轮的固定开销。同一会话的后续提问复用它，
# 空闲超过 agent_resident_idle_seconds 自动关停，数量超过上限时关停最久未用的。
# 多个 API 进程各有各的常驻表：会话文件里记录最近一次由谁跑完，不是自己跑的就丢弃重建，避免用到过期的内存历史。

class _Resident:
    def __init__(self, key, fingerprint):
        self.key, self.fingerprint = key, fingerprint
        self.harness = None
        self.session = None
        self.stack = None
        self.patch_path = None
        self.holder = {"tools": None, "context": None}
        self.turns = 0
        self.last_used = time.monotonic()
        self.closed = False


_RESIDENTS: dict[str, _Resident] = {}
_REAPER: asyncio.Task | None = None
_OWNER = uuid4().hex  # 本 API 进程的标识


def _resident_enabled() -> bool:
    return settings.agent_resident_idle_seconds > 0 and settings.agent_resident_max_sessions > 0


def _turn_marker(home: Path) -> Path:
    return home / "oa-resident-turn.json"


def _read_turn(home: Path):
    try:
        return json.loads(_turn_marker(home).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return None


def _write_turn(home: Path, resident: _Resident) -> None:
    _turn_marker(home).write_text(json.dumps({"owner": _OWNER, "turns": resident.turns}), encoding="utf-8")


async def _close_resident(resident: _Resident) -> None:
    if resident.closed:
        return
    resident.closed = True
    if _RESIDENTS.get(resident.key) is resident:
        _RESIDENTS.pop(resident.key, None)
    try:
        if resident.harness is not None:
            await asyncio.to_thread(resident.harness.close)
    except Exception:
        logger.exception("关闭常驻智能体运行时失败")
    try:
        if resident.stack is not None:
            await resident.stack.aclose()
    except Exception:
        logger.exception("关闭常驻智能体工具通道失败")
    if resident.patch_path is not None:
        resident.patch_path.unlink(missing_ok=True)


async def _reap_idle() -> None:
    while True:
        await asyncio.sleep(30)
        now = time.monotonic()
        for resident in list(_RESIDENTS.values()):
            if now - resident.last_used >= settings.agent_resident_idle_seconds and not resident.holder["tools"]:
                await _close_resident(resident)
        if not _RESIDENTS:
            return


def _start_reaper() -> None:
    global _REAPER
    if _REAPER is None or _REAPER.done():
        _REAPER = asyncio.create_task(_reap_idle())


async def close_all_residents() -> None:
    """服务停止时关停全部常驻运行时。"""
    for resident in list(_RESIDENTS.values()):
        await _close_resident(resident)


def _fingerprint(schemas, directories, mode_supported, response_mode, memory, profile) -> str:
    material = json.dumps({
        "tools": [(item["function"]["name"], item["function"].get("parameters")) for item in schemas],
        "skills": sorted(str(path) for path in directories.values()),
        "mode": [mode_supported, response_mode], "memory": memory, "profile": profile,
    }, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(material.encode()).hexdigest()


async def _evict_for_capacity() -> None:
    while len(_RESIDENTS) >= settings.agent_resident_max_sessions:
        oldest = min(_RESIDENTS.values(), key=lambda item: item.last_used)
        if oldest.holder["tools"] is not None:
            return  # 最久未用的正在运行，不强关；本轮不再新增常驻
        await _close_resident(oldest)


async def _run_session(messages, on_delta, *, tools, schema, identity, db, identifier, cwd, home,
                       response_mode, mode_supported, on_progress):
    from deepseek_harness import DeepSeekHarness
    from deepseek_harness.errors import HarnessError
    from contextvars import copy_context

    marker = home / "oa-session.json"
    resident = None
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
        from app.core.request_metrics import add_phase, current_metrics, measure_phase
        metrics = current_metrics()  # 线程里测得的耗时也记到本次请求，慢请求日志里可看到各段耗时
        with measure_phase("agent.prepare"):
            available = await definitions(identity, db)
            directories = publish(home.parent.parent / "skill-versions", available)
            guarded = WorkspaceTools(tools, identity, db, on_progress)
            schemas = [*schema, RESOURCE_TOOL, SCRIPT_TOOL]
            from .memory import configuration as memory_configuration
            memory = memory_configuration(cwd, identity['username'])
            from .plugins import attach
            profile = attach(home)
        fingerprint = _fingerprint(schemas, directories, mode_supported, response_mode, memory, profile)

        # 复用常驻会话：配置未变、仍是本进程跑完的最近一轮、没被关停。
        key = identifier
        resident = _RESIDENTS.get(key) if _resident_enabled() else None
        if resident is not None:
            turn = _read_turn(home)
            stale = (resident.closed or resident.fingerprint != fingerprint or resident.holder["tools"] is not None
                     or turn != {"owner": _OWNER, "turns": resident.turns})
            if stale:
                await _close_resident(resident)
                resident = None
        reused = resident is not None
        started = time.perf_counter()
        if resident is None:
            # 冷启动：先作废其他进程里可能还留着的同一会话的常驻副本，它们不知道这一轮的对话。
            _turn_marker(home).write_text(json.dumps({"owner": uuid4().hex, "turns": 0}), encoding="utf-8")
            resident = _Resident(key, fingerprint)
            resident.holder["context"] = copy_context()
            resident.holder["tools"] = guarded
            from contextlib import AsyncExitStack
            from .bridge import _SwitchTools

            resident.stack = AsyncExitStack()
            try:
                url, secret = await resident.stack.enter_async_context(
                    workspace_mcp(_SwitchTools(resident.holder), schemas, lambda: resident.holder["context"]))
                resident.patch_path = home / ("oa-run-" + uuid4().hex + ".yml")
                resident.patch_path.write_text(yaml.safe_dump(
                    _patch(url, secret, schemas, directories, mode_supported, response_mode, memory, native_plugins=profile != "sdk"),
                    allow_unicode=True, sort_keys=False), encoding="utf-8")
                resident.patch_path.chmod(0o600)
                resident.harness = DeepSeekHarness(
                    dsh_home=native_path(home), cwd=native_path(cwd), profile=profile, patches=(native_path(resident.patch_path),),
                    provider="huzhi-oa", model=settings.langgraph_model, env=_environment(),
                    reasoning_effort=("off" if response_mode == "fast" else "high") if mode_supported else None,
                    initialize_timeout_seconds=40, request_timeout_seconds=180)
            except BaseException:
                await _close_resident(resident)
                raise
            add_phase("agent.harness_init", time.perf_counter() - started, metrics)
        else:
            resident.holder["context"] = copy_context()
            resident.holder["tools"] = guarded
            add_phase("agent.resident_reuse_x1000", 0.001, metrics)  # 次数：毫秒值即复用次数

        loop = asyncio.get_running_loop()
        queue = asyncio.Queue()

        def notification(item):
            if item.method == "oa.assistant.delta" and item.payload.get("sessionId") == identifier:
                text = item.payload.get("text")
                if isinstance(text, str) and text:
                    loop.call_soon_threadsafe(queue.put_nowait, ("delta", text))
            elif item.method == "session.event" and (item.payload.get("event") or {}).get("type") == "tool/call":
                add_phase("agent.tool_calls_x1000", 0.001, metrics)  # 次数：毫秒值即调用次数
                loop.call_soon_threadsafe(queue.put_nowait, ("progress", "正在调用工作区工具…"))

        use_resume = resumed and not reused
        run_resumed = resumed or reused

        def execute():
            try:
                if resident.session is None:
                    opened = time.perf_counter()
                    resident.session = resident.harness.resume_session(identifier) if use_resume else resident.harness.start_session(identifier)
                    resident.session.get_working_directory()
                    if not resumed:
                        marker.write_text(json.dumps({"format": 1, "session": identifier}), encoding="utf-8")
                    add_phase("agent.session_open", time.perf_counter() - opened, metrics)
                running = time.perf_counter()
                try:
                    return resident.session.run(_content(messages, resumed=run_resumed), on_notification=notification)
                finally:
                    add_phase("agent.session_run", time.perf_counter() - running, metrics)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, ("finished", ""))

        if on_progress:
            await on_progress("正在启动工作区智能体…" if not reused else "正在处理…")
        runner = asyncio.create_task(asyncio.to_thread(execute))
        first_delta = None
        async with asyncio.timeout(180):
            while True:
                kind, value = await queue.get()
                if kind == "finished":
                    break
                if kind == "delta":
                    if first_delta is None:
                        first_delta = time.perf_counter()
                        add_phase("agent.first_delta", first_delta - started, metrics)
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
        resident.turns += 1
        resident.last_used = time.monotonic()
        keep = _resident_enabled()
        if keep and not reused:
            await _evict_for_capacity()
            keep = len(_RESIDENTS) < settings.agent_resident_max_sessions
        if keep:
            _RESIDENTS[key] = resident
            _write_turn(home, resident)
            _start_reaper()
            resident.holder["tools"] = None  # 本轮结束：不再持有本次请求的事务和身份
            resident.holder["context"] = None
            resident = None  # 交给常驻表，不在 finally 里关闭
        return result.final_response.strip()
    except TimeoutError as exc:
        raise HTTPException(504, "Harness 本轮执行超时，未取得完成结果") from exc
    except HarnessError as exc:
        # 上游异常可能携带 stderr 或模型端点内容，只公开明确的故障类别。
        raise HTTPException(502, "Harness 协议或运行时失败：" + type(exc).__name__) from None
    except OSError as exc:
        raise HTTPException(503, "Harness 本地运行资源不可用，系统错误码：" + str(exc.errno)) from None
    finally:
        if runner is not None:
            await asyncio.gather(runner, return_exceptions=True)
        if resident is not None:
            # 出错、超时、被停止或未被保留的会话一律关闭，下一轮冷启动并从磁盘恢复历史。
            closing = time.perf_counter()
            await _close_resident(resident)
            from app.core.request_metrics import add_phase as _add
            _add("agent.harness_close", time.perf_counter() - closing)
