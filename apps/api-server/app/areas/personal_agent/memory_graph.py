"""LangGraph-backed short/long memory pipeline for the personal assistant.

Memory is deliberately conservative: only explicit user requests such as
"记住/以后/我的偏好" create long-term memories. Recall is filtered by the
authenticated owner and optional case scope before anything reaches the model.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph


_MEMORY_FILE = "memories.json"
_EXPLICIT_MEMORY = re.compile(r"(?:记住|请记住|以后|今后|我的偏好|我习惯|保存这个偏好|记下来)[：:，,\s]*(.+)", re.I | re.S)
_TOKEN = re.compile(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]{2,}")


class MemoryState(TypedDict, total=False):
    directory: str
    owner_user_id: int
    conversation_id: str | None
    case_id: int | None
    user_text: str
    messages: list[dict[str, Any]]
    summary: str
    recalled: list[dict[str, Any]]
    candidate: str | None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty() -> dict[str, Any]:
    return {"version": 1, "settings": {"enabled": True, "retention_days": 365, "recall_limit": 5}, "items": []}


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _empty()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _empty()
    if not isinstance(value, dict) or value.get("version") != 1 or not isinstance(value.get("items"), list):
        return _empty()
    value.setdefault("settings", _empty()["settings"])
    return value


def _write(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _compact_node(state: MemoryState) -> dict[str, Any]:
    messages = [item for item in state.get("messages", []) if isinstance(item, dict)]
    keep = 12
    older = messages[:-keep] if len(messages) > keep else []
    if not older:
        return {"summary": state.get("summary", "")}
    lines = []
    for item in older[-40:]:
        role = "用户" if item.get("role") == "user" else "助手"
        content = " ".join(str(item.get("content") or "").split())
        if content:
            lines.append(f"{role}：{content[:280]}")
    previous = str(state.get("summary") or "").strip()
    summary = "\n".join(([previous] if previous else []) + lines)[-8_000:]
    return {"summary": summary}


def _extract_node(state: MemoryState) -> dict[str, Any]:
    match = _EXPLICIT_MEMORY.search(str(state.get("user_text") or ""))
    return {"candidate": " ".join(match.group(1).split())[:1_000] if match else None}


def _recall_node(state: MemoryState) -> dict[str, Any]:
    path = Path(state["directory"]) / _MEMORY_FILE
    data = _read(path)
    settings = data["settings"]
    if not settings.get("enabled", True):
        return {"recalled": []}
    query = set(_TOKEN.findall(str(state.get("user_text") or "").lower()))
    case_id = state.get("case_id")
    owner = int(state.get("owner_user_id") or 0)
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, min(int(settings.get("retention_days", 365)), 3650)))
    candidates = []
    for item in data["items"]:
        if not isinstance(item, dict) or item.get("owner_user_id") != owner or item.get("deleted_at"):
            continue
        try:
            if datetime.fromisoformat(str(item.get("updated_at"))).astimezone(timezone.utc) < cutoff:
                continue
        except (TypeError, ValueError):
            continue
        item_case = item.get("case_id")
        if item_case not in (None, case_id):
            continue
        tokens = set(_TOKEN.findall(str(item.get("content") or "").lower()))
        score = len(query & tokens)
        if score or not query:
            candidates.append({**item, "recall_score": score})
    candidates.sort(key=lambda item: (item["recall_score"], item.get("updated_at", "")), reverse=True)
    return {"recalled": candidates[: max(0, min(int(settings.get("recall_limit", 5)), 20))]}


def _graph():
    graph = StateGraph(MemoryState)
    graph.add_node("compact", _compact_node)
    graph.add_node("extract", _extract_node)
    graph.add_node("recall", _recall_node)
    graph.add_edge(START, "compact")
    graph.add_edge("compact", "extract")
    graph.add_edge("extract", "recall")
    graph.add_edge("recall", END)
    return graph.compile()


_MEMORY_GRAPH = _graph()


def _save_candidate(directory: Path, owner_user_id: int, conversation_id: str | None, case_id: int | None, candidate: str | None) -> dict[str, Any] | None:
    if not candidate:
        return None
    path = directory / _MEMORY_FILE
    data = _read(path)
    settings = data["settings"]
    if not settings.get("enabled", True):
        return None
    now = _now()
    item = {"id": uuid4().hex, "kind": "long", "content": candidate, "owner_user_id": owner_user_id,
            "conversation_id": conversation_id, "case_id": case_id, "permission_scope": "case" if case_id else "personal",
            "created_at": now, "updated_at": now, "deleted_at": None}
    data["items"] = [*data["items"], item][-500:]
    _write(path, data)
    return item


def run_memory_pipeline(directory: Path, owner_user_id: int, conversation_id: str | None, case_id: int | None,
                        messages: list[dict[str, Any]], user_text: str, summary: str = "") -> dict[str, Any]:
    result = _MEMORY_GRAPH.invoke({"directory": str(directory), "owner_user_id": owner_user_id,
                                   "conversation_id": conversation_id, "case_id": case_id,
                                   "messages": messages, "user_text": user_text, "summary": summary})
    item = _save_candidate(directory, owner_user_id, conversation_id, case_id, result.get("candidate"))
    return {"summary": result.get("summary", ""), "recalled": result.get("recalled", []), "created": item}


def list_memories(directory: Path, owner_user_id: int, limit: int = 50) -> dict[str, Any]:
    data = _read(directory / _MEMORY_FILE)
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, min(int(data["settings"].get("retention_days", 365)), 3650)))
    items = []
    for item in data["items"]:
        if not isinstance(item, dict) or item.get("owner_user_id") != owner_user_id or item.get("deleted_at"):
            continue
        try:
            if datetime.fromisoformat(str(item.get("updated_at"))).astimezone(timezone.utc) < cutoff:
                continue
        except (TypeError, ValueError):
            continue
        items.append(item)
    items.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    return {"settings": data["settings"], "items": items[: max(1, min(limit, 100))]}


def delete_memory(directory: Path, owner_user_id: int, memory_id: str) -> bool:
    path = directory / _MEMORY_FILE
    data = _read(path)
    for item in data["items"]:
        if item.get("id") == memory_id and item.get("owner_user_id") == owner_user_id and not item.get("deleted_at"):
            item["deleted_at"] = _now()
            _write(path, data)
            return True
    return False


def update_settings(directory: Path, owner_user_id: int, *, enabled: bool | None = None,
                    retention_days: int | None = None, recall_limit: int | None = None) -> dict[str, Any]:
    path = directory / _MEMORY_FILE
    data = _read(path)
    settings = data["settings"]
    if enabled is not None:
        settings["enabled"] = enabled
    if retention_days is not None:
        settings["retention_days"] = max(1, min(retention_days, 3650))
    if recall_limit is not None:
        settings["recall_limit"] = max(0, min(recall_limit, 20))
    _write(path, data)
    return settings
