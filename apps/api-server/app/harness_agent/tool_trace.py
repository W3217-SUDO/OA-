"""每轮对话里智能体调用了哪些工具：随回答保存，前端展开可见。只记名称、关键参数摘要和结果状态。"""
from __future__ import annotations

from contextvars import ContextVar
import json
import re
import time

_TRACE: ContextVar[list | None] = ContextVar("oa_agent_tool_trace", default=None)
_SECRET = re.compile(r"token|password|passwd|secret|credential|authorization|api[_-]?key|cookie|session", re.I)
_DETAIL_LIMIT = 240
_MAX_ENTRIES = 80


def begin() -> list:
    """开始记录本轮调用；返回的列表之后可直接存进消息。"""
    trace: list = []
    _TRACE.set(trace)
    return trace


def _redact(value, depth=0):
    if depth > 4:
        return "…"
    if isinstance(value, dict):
        return {key: ("***" if _SECRET.search(str(key)) else _redact(item, depth + 1)) for key, item in list(value.items())[:12]}
    if isinstance(value, list):
        return [_redact(item, depth + 1) for item in value[:6]]
    if isinstance(value, str):
        return value if len(value) <= 120 else value[:120] + "…"
    return value


def _title(tool_name: str) -> str:
    """业务工具的中文名；取不到就用原名。"""
    try:
        from app.agent_mcp.catalog import get_catalog
        from app.main import app
        tool = get_catalog(app)._by_name.get(tool_name)
        return tool.title if tool is not None and tool.title else tool_name
    except Exception:
        return tool_name


def describe(name: str, arguments) -> tuple[str, str]:
    """返回（显示名称，参数摘要）。oa_call_tool 显示它实际调用的业务工具。"""
    arguments = arguments if isinstance(arguments, dict) else {}
    label, shown = name, arguments
    if name == "oa_call_tool" and isinstance(arguments.get("name"), str):
        label = _title(arguments["name"]) + "（" + arguments["name"] + "）"
        shown = arguments.get("arguments") or {}
    elif name == "oa_search_tools":
        label = "搜索业务工具"
    elif name == "oa_list_tool_groups":
        label = "查看业务工具分组"
    elif name == "harness_run_code":
        label = "沙箱运行代码（" + str(arguments.get("language") or "") + "）"
        shown = {"code": str(arguments.get("code") or "")[:_DETAIL_LIMIT], "args": arguments.get("args") or []}
    elif name == "harness_web_fetch":
        label = "上网读取网页"
    elif name == "harness_run_skill_script":
        label = "运行技能脚本"
    elif name == "harness_read_skill_resource":
        label = "读取技能资料"
    detail = json.dumps(_redact(shown), ensure_ascii=False, default=str)
    return label, detail if len(detail) <= _DETAIL_LIMIT else detail[:_DETAIL_LIMIT] + "…"


def record(name: str, arguments, *, ok: bool, started: float) -> None:
    trace = _TRACE.get()
    if trace is None or len(trace) >= _MAX_ENTRIES:
        return
    label, detail = describe(name, arguments)
    trace.append({"name": name, "label": label, "detail": detail, "ok": ok, "ms": round((time.perf_counter() - started) * 1000)})


def native_call_name(event: dict) -> str:
    """DSH 原生工具调用事件里的工具名（形态因版本而异，取不到返回空）。"""
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    for source in (data, event):
        for key in ("name", "toolName", "tool"):
            if isinstance(source.get(key), str) and source[key]:
                return source[key][:80]
    return ""


def record_native(name: str) -> None:
    """记录 DSH 原生工具（技能加载、插件工具等）的调用；OA 工具由 WorkspaceTools 记录，这里不重复。"""
    trace = _TRACE.get()
    if trace is None or len(trace) >= _MAX_ENTRIES or name.startswith("mcp__oa__"):
        return
    trace.append({"name": name, "label": "插件/技能工具：" + name, "detail": "", "ok": True, "ms": 0})
