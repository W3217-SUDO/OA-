"""云端智能体运行：每个 OA 对话对应一个火山 Session，OA 业务工具作为自定义工具由 OA 按当前登录人执行。

- 智能体循环、对话历史、上下文压缩在火山；服务器上不再常驻 DSH 进程。
- 云沙箱（bash、读写文件、联网搜索、读网页）在火山执行，里面没有 OA 数据库、凭据和内网。
- OA 工具调用（查/改案件等）走 agent.custom_tool_use → WorkspaceTools.execute → user.custom_tool_result，
  权限校验和写操作确认与 DSH 时完全相同。
- 长期记忆用火山 Memory Store，每人一个库；个人设置里关掉记忆就不挂载。
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path

from fastapi import HTTPException

from app.harness_agent.lease import session_lease
from app.harness_agent.skills import CODE_TOOL, RESOURCE_TOOL, SCRIPT_TOOL, WEB_TOOL, WorkspaceTools, definitions, native_name, scoped_schemas

from .client import ArkClient, ArkError
from .config import CloudSettings
from .harness import HarnessTools, schemas as harness_schemas
from .usage import TurnUsage, append

logger = logging.getLogger(__name__)
TURN_SECONDS = 300
TOOLSET = "agent_toolset_20260916"
SANDBOX_TOOLS = ("bash", "read", "write", "edit", "glob", "grep", "web_fetch", "web_search")
ENVIRONMENT_NAME = "huzhi-oa-cloud"
CLOUD_RULES = (
    "\n云端运行补充：每条用户消息里 [SYSTEM] 段落是 OA 给出的本轮规则和业务数据，必须遵守；[USER] 段落是用户原话。"
    "OA 的工具都以自定义工具提供，按工具名直接调用。技能目录在 [SYSTEM] 段落里，加载技能就是用 harness_read_skill_resource 读取它的 SKILL.md。"
    "你另有一个云端沙箱（bash、读写文件、读网页），里面没有 OA 数据库、凭据和内网，不要在里面登录或访问 OA；临时计算、整理资料可以用它或 harness_run_code。"
    "沙箱里的文件用户看不到也下载不了：不要在沙箱里生成要交给用户的 Word、PDF、Excel 等文件，也不要回答“文件已生成在 /mnt/... 目录”。"
    "用户要 Word 或要存进案件时，按 OA 规则把完整正文直接写在本次回答里（标题、条款、段落都写全），页面会在回答下方给出保存到个人空间或案件的按钮，"
    "用户点击确认后由 OA 生成 Word 并保存。文书正文第一行写文书标题（如“# 委托代理合同”），说明、提示放在正文之后，页面会用第一行标题作文件名。"
    "专业资料：查法条、判例、企业工商和风险时用 volc_professional_data（权威库），引用法条和案号前可用它做法律幻觉校验；"
    "查最新公开信息用 doubao_search（没有这个工具时用 web_search 或 harness_web_fetch）。这两个工具按次计费，不要重复查同一问题。"
    "长期记忆：挂载了记忆库时，用户明确要求记住的事写入记忆库；历史信息相关时先检索记忆库。记忆不是最新业务事实，"
    "权限、金额、状态仍须查询 OA。不得保存密钥、密码或整段原始聊天；用户要求遗忘时删除对应记忆。"
)


def system_prompt() -> str:
    """和 DSH 共用同一套 OA 业务规则（harness_agent.runtime.oa_persona），只把 DSH 专有的说法换成云端的。"""
    from app.harness_agent.runtime import oa_persona

    persona = oa_persona().replace("mcp__oa__", "").replace(
        "技能使用 skill 加载；", "技能用 harness_read_skill_resource 读取其 SKILL.md 加载；").replace(
        "DSH 插件提供的原生工具直接按工具名调用；", "")
    return persona + CLOUD_RULES


def _state_root() -> Path:
    from app.harness_agent.runtime import storage_root

    root = storage_root() / "cloud"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def _read(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _write(path: Path, value: dict) -> None:
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def custom_tool(item: dict) -> dict:
    """OpenAI function 定义 → Managed Agents 自定义工具。"""
    function = item["function"]
    return {"type": "custom", "name": function["name"], "description": function.get("description", "")[:4000],
            "input_schema": function.get("parameters") or {"type": "object", "properties": {}}}


def agent_body(model: str, schemas: list[dict], *, web_search: bool = True) -> dict:
    # 接了豆包搜索（套餐抵扣）就关掉云端自带的 web_search（按次另计费），避免两个搜索都开。
    enabled = [name for name in SANDBOX_TOOLS if web_search or name != "web_search"]
    sandbox = {"type": TOOLSET, "default_config": {"enabled": False, "permission_policy": {"type": "always_allow"}},
               "configs": [{"name": name, "enabled": True} for name in enabled]}
    return {"model": {"id": model}, "system": system_prompt(), "tools": [sandbox, *[custom_tool(item) for item in schemas]]}


async def _agent(client: ArkClient, cloud: CloudSettings, schemas: list[dict]) -> str:
    """同一套模型和工具只建一个 Agent，按指纹复用；工具变了（权限变化、上线新工具）就建新的。"""
    body = agent_body(cloud.model, schemas, web_search=not cloud.doubao_search)
    fingerprint = hashlib.sha256(json.dumps([cloud.fingerprint(), body], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    path = _state_root() / "agents.json"
    known = _read(path)
    if fingerprint in known:
        return known[fingerprint]
    created = await client.request("POST", "/agents", json_body={"name": "huzhi-oa-" + fingerprint[:16], **body})
    known = _read(path)
    known[fingerprint] = created["id"]
    _write(path, known)
    return created["id"]


async def _environment(client: ArkClient, cloud: CloudSettings) -> str:
    path = _state_root() / "environment.json"
    known = _read(path)
    if known.get(cloud.fingerprint()):
        return known[cloud.fingerprint()]
    try:
        created = await client.request("POST", "/environments", json_body={
            "name": ENVIRONMENT_NAME, "config": {"type": "cloud", "networking": {"type": "unrestricted"}}})
        identifier = created["id"]
    except ArkError as exc:
        if exc.status not in (400, 409):
            raise
        listed = await client.request("GET", "/environments", params={"limit": 100})
        identifier = next((item["id"] for item in listed.get("data", []) if item.get("name") == ENVIRONMENT_NAME), "")
        if not identifier:
            raise
    known = _read(path)
    known[cloud.fingerprint()] = identifier
    _write(path, known)
    return identifier


def _memory_enabled(owner: str) -> bool:
    from app.areas.personal_agent.memory_store import list_memories
    from app.areas.personal_agent.service import _user_dir

    return bool(list_memories(_user_dir(owner), 0)["settings"].get("enabled", True))


async def _memory_store(client: ArkClient, cloud: CloudSettings, owner: str) -> str:
    owner_key = hashlib.sha256(owner.casefold().encode()).hexdigest()[:32]
    path = _state_root() / "memory.json"
    key = cloud.fingerprint() + ":" + owner_key
    known = _read(path)
    if known.get(key):
        return known[key]
    created = await client.request("POST", "/memory_stores", json_body={
        "name": "oa-" + owner_key, "description": "沪知 OA 当前登录人的长期记忆：偏好、约定和需要记住的背景，不存密钥和原始聊天。"})
    known = _read(path)
    known[key] = created["id"]
    _write(path, known)
    return created["id"]


async def _session(client, home: Path, agent_id: str, environment_id: str, memory_id: str, title: str) -> tuple[str, bool]:
    """返回 (session_id, 是否新建)。Agent 或记忆挂载变了就新建会话，并把完整历史作为首条消息带过去。"""
    path = home / "cloud-session.json"
    known = _read(path)
    if known.get("session") and known.get("agent") == agent_id and known.get("memory", "") == memory_id:
        return known["session"], False
    body = {"agent": agent_id, "environment_id": environment_id, "title": title[:100]}
    if memory_id:
        body["resources"] = [{"type": "memory_store", "memory_store_id": memory_id, "access": "read_write"}]
    created = await client.request("POST", "/sessions", json_body=body)
    _write(path, {"session": created["id"], "agent": agent_id, "memory": memory_id})
    return created["id"], True


def _bill(home: Path, usage, identity, workspace, conversation, model, ok) -> None:
    """记一轮用量；记账失败只写日志，不影响回答。"""
    try:
        if usage.active_total is not None:
            path = home / "cloud-session.json"
            known = _read(path)
            if known:
                _write(path, {**known, "active_total": usage.active_total})
        if usage.requests or usage.oa_tools or usage.datapro or usage.searches:
            append(usage.record(username=identity["username"], display_name=str(identity.get("display_name") or ""),
                                workspace=workspace, conversation=conversation, model=model, ok=ok))
    except Exception:
        logger.exception("cloud_agent_usage_record_failed")


def _forget_session(home: Path) -> None:
    (home / "cloud-session.json").unlink(missing_ok=True)


def skill_catalog(skills) -> str:
    if not skills:
        return ""
    lines = ["当前账号可用技能（编号｜名称｜用途）："]
    for skill in skills:
        lines.append(f"- {native_name(skill.id)}｜{skill.name}｜{(skill.description or '').strip()[:200]}")
    return "\n".join(lines)


def content_blocks(messages, *, resumed: bool, catalog: str) -> list[dict]:
    """和 DSH 一致：新会话带完整历史；续聊只带系统段和最后一条用户消息。"""
    selected = [item for item in messages if item.get("role") == "system"] + [messages[-1]] if resumed else list(messages)
    blocks: list[dict] = []
    if catalog:
        blocks.append({"type": "text", "text": "[SYSTEM]\n" + catalog})
    for item in selected:
        content = item.get("content", "")
        if isinstance(content, str):
            blocks.append({"type": "text", "text": f"[{str(item.get('role', 'user')).upper()}]\n{content}"})
            continue
        for block in content if isinstance(content, list) else []:
            if block.get("type") == "text":
                blocks.append({"type": "text", "text": block["text"]})
            elif block.get("type") == "image_url":
                url = block.get("image_url", {}).get("url", "")
                if not isinstance(url, str) or not url.startswith("data:image/") or ";base64," not in url:
                    raise HTTPException(422, "云端智能体仅接收已授权读取的内联图片")
                header, data = url.split(";base64,", 1)
                blocks.append({"type": "image", "source": {"type": "base64", "media_type": header[5:], "data": data}})
    return blocks


def _delta_text(event: dict) -> str:
    # 实测格式（11-03）：{"type": "event_delta", "event_id": ..., "delta": {"type": "content_delta", "content": {"type": "text", "text": ...}}}
    delta = event.get("delta")
    content = delta.get("content") if isinstance(delta, dict) else None
    if isinstance(content, dict) and content.get("type") == "text" and isinstance(content.get("text"), str):
        return content["text"]
    return ""


def _message_text(event: dict) -> str:
    return "".join(block.get("text", "") for block in event.get("content") or [] if block.get("type") == "text")


async def _tool_result(guarded: WorkspaceTools, event: dict, usage=None) -> dict:
    name, arguments = event.get("name", ""), event.get("input") or {}
    result = None
    try:
        result = await guarded.execute(name, arguments)
        text, failed = json.dumps(result, ensure_ascii=False, default=str), bool(isinstance(result, dict) and result.get("isError"))
    except HTTPException as exc:
        text, failed = json.dumps({"isError": True, "message": str(exc.detail)}, ensure_ascii=False), True
    finally:
        if usage is not None:
            usage.tool(name, result)
    return {"type": "user.custom_tool_result", "custom_tool_use_id": event["id"], "is_error": failed,
            "content": [{"type": "text", "text": text}]}


NARRATION_LIMIT = 80


def final_answer(messages: list[str], tool_marks: list[int]) -> str:
    """最终回答：去掉调用工具之前那些很短的过程说明（如“正在查询案件空间…”），保留工具之后的回答（501289）。
    工具前写的是正式内容（较长）的照样保留；没有调用工具时原样拼接。"""
    last_tool = tool_marks[-1] if tool_marks else 0
    kept = [text for index, text in enumerate(messages)
            if text.strip() and (index >= last_tool or len(text.strip()) > NARRATION_LIMIT)]
    return "\n\n".join(kept).strip() or "\n\n".join(text for text in messages if text.strip()).strip()


async def run_turn(client: ArkClient, session_id: str, blocks: list[dict], guarded: WorkspaceTools, on_delta, on_progress,
                   usage=None, active_before: float = 0.0) -> str:
    """用户点“停止”或本轮超时时，同时让火山那边停下（user.interrupt），不再继续计时，下一条消息也不会排在后面。"""
    try:
        return await _run_turn(client, session_id, blocks, guarded, on_delta, on_progress, usage, active_before)
    except (asyncio.CancelledError, TimeoutError):
        await _interrupt(client, session_id)
        raise


async def _interrupt(client: ArkClient, session_id: str) -> None:
    try:
        await asyncio.wait_for(asyncio.shield(client.request(
            "POST", f"/sessions/{session_id}/events", json_body={"events": [{"type": "user.interrupt"}]})), 5)
    except BaseException as exc:  # 中断只是尽力而为，失败只记日志
        logger.warning("cloud_agent_interrupt_failed session=%s error=%s", session_id, type(exc).__name__)


async def _run_turn(client: ArkClient, session_id: str, blocks: list[dict], guarded: WorkspaceTools, on_delta, on_progress,
                    usage=None, active_before: float = 0.0) -> str:
    pending: dict[str, dict] = {}
    streamed: dict[str, str] = {}
    messages: list[str] = []
    tool_marks: list[int] = []  # 每次调用工具时已经有几条消息，用来去掉工具前的过程说明
    state = {"emitted": False, "current": ""}

    async def emit(event_id: str, text: str) -> None:
        if not text:
            return
        if state["current"] != event_id:
            if state["emitted"]:
                await on_delta("\n\n")
            state["current"] = event_id
        state["emitted"] = True
        streamed[event_id] = streamed.get(event_id, "") + text
        await on_delta(text)

    async with client.events(session_id) as stream:
        await stream.ready()
        await client.request("POST", f"/sessions/{session_id}/events",
                             json_body={"events": [{"type": "user.message", "content": blocks}]})
        async for event in stream:
            kind = event.get("type", "")
            if kind == "event_delta":
                await emit(str(event.get("event_id") or ""), _delta_text(event))
            elif kind == "agent.message":
                full, already = _message_text(event), streamed.get(event.get("id", ""), "")
                await emit(event.get("id", ""), full[len(already):] if full.startswith(already) else ("" if already else full))
                messages.append(full)
            elif kind == "agent.custom_tool_use":
                pending[event["id"]] = event
                tool_marks.append(len(messages))
            elif kind in ("agent.tool_use", "agent.mcp_tool_use"):
                tool_marks.append(len(messages))
                if on_progress:
                    await on_progress("正在调用：" + {"web_fetch": "上网读取网页", "web_search": "联网搜索"}.get(
                        str(event.get("name") or ""), "云端临时空间"))
            elif kind == "span.model_request_end" and usage is not None:
                usage.model_request(event)
            elif kind == "session.usage" and usage is not None:
                usage.active_total = usage.session_usage(event, active_before)
            elif kind == "session.error":
                logger.warning("cloud_agent_session_error session=%s error=%s", session_id,
                               json.dumps(event.get("error") or {}, ensure_ascii=False)[:500])
            elif kind in ("session.status_terminated", "session.deleted"):
                raise ArkError(410, kind, "云端会话已结束")
            elif kind == "session.status_idle":
                reason = event.get("stop_reason") or {}
                if reason.get("type") == "end_turn":
                    break
                if reason.get("type") == "retries_exhausted":
                    raise HTTPException(502, "云端智能体本轮重试已用尽，未确认任何未执行操作成功")
                if reason.get("type") == "requires_action":
                    replies = []
                    for event_id in reason.get("event_ids") or []:
                        if event_id in pending:
                            replies.append(await _tool_result(guarded, pending.pop(event_id), usage))
                        else:  # 云沙箱工具都是 always_allow，一般不会走到这里；沙箱里没有 OA 数据，放行
                            replies.append({"type": "user.tool_confirmation", "tool_use_id": event_id, "result": "allow"})
                    if replies:
                        await client.request("POST", f"/sessions/{session_id}/events", json_body={"events": replies})
        else:
            raise HTTPException(502, "云端事件流提前断开，未确认任何未执行操作成功")
    answer = final_answer(messages, tool_marks)
    if not answer:
        raise HTTPException(502, "云端智能体本轮没有回复，未确认任何未执行操作成功")
    return answer


def _http_error(exc: ArkError) -> HTTPException:
    logger.warning("cloud_agent_error status=%s code=%s message=%s", exc.status, exc.code, exc.message)
    if exc.status == 401:
        return HTTPException(503, "云端智能体的方舟 API Key 无效，请系统管理员在“智能体设置”里检查")
    if exc.status in (400, 403, 404) and ("not open" in exc.message or "NotOpen" in exc.code):
        return HTTPException(503, "云端智能体的模型或服务还没在火山方舟开通，请系统管理员检查（" + exc.code + "）")
    if exc.status == 429:
        return HTTPException(503, "云端智能体请求太频繁或额度用完，请稍后再试")
    return HTTPException(502, "云端智能体调用失败（" + (exc.code or str(exc.status)) + "），未确认任何未执行操作成功")


async def run(messages, on_delta, *, tools, schema, identity, db, workspace, conversation, cloud: CloudSettings,
              on_progress=None, **_ignored) -> str:
    from app.harness_agent.runtime import workspace_paths

    _, _, home = workspace_paths(identity["username"], workspace, conversation)
    delegate = HarnessTools(tools, cloud.plan_key) if cloud.plan_key else tools
    guarded = WorkspaceTools(delegate, identity, db, on_progress)
    # 工具和 DSH 时一个不少：OA 业务工具、技能资料/脚本、运行代码、读网页，再加 Agent Plan 的 Harness。
    schemas = scoped_schemas(tools, schema, [RESOURCE_TOOL, SCRIPT_TOOL, CODE_TOOL, WEB_TOOL,
                                             *harness_schemas(datapro=cloud.datapro, search=cloud.doubao_search)])
    from app.harness_agent.native_plugin_skills import definitions as plugin_definitions
    catalog = skill_catalog([*await definitions(identity, db), *plugin_definitions()])
    try:
        async with asyncio.timeout(TURN_SECONDS):
            with session_lease(home / "cloud.lock"):
                async with ArkClient(cloud.api_key) as client:
                    if on_progress:
                        await on_progress("正在连接云端智能体…")
                    agent_id = await _agent(client, cloud, schemas)
                    environment_id = await _environment(client, cloud)
                    memory_id = await _memory_store(client, cloud, identity["username"]) if cloud.memory and _memory_enabled(identity["username"]) else ""
                    session_id, fresh = await _session(client, home, agent_id, environment_id, memory_id, workspace + " " + conversation)
                    blocks = content_blocks(messages, resumed=not fresh, catalog=catalog)
                    usage = TurnUsage()
                    before = float(_read(home / "cloud-session.json").get("active_total") or 0)
                    ok = False
                    try:
                        answer = await run_turn(client, session_id, blocks, guarded, on_delta, on_progress, usage, before)
                        ok = True
                        return answer
                    except ArkError as exc:
                        if exc.status in (404, 410):
                            _forget_session(home)  # 会话被删或已终止：下一轮新建会话并带上完整历史
                        raise
                    finally:
                        _bill(home, usage, identity, workspace, conversation, cloud.model, ok)
    except TimeoutError as exc:
        raise HTTPException(504, "云端智能体本轮执行超时，未取得完成结果") from exc
    except ArkError as exc:
        raise _http_error(exc) from None
