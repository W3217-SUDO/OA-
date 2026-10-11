from __future__ import annotations

import asyncio
import json
import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator
from uuid import uuid4

from fastapi import HTTPException


STATE_LOCK = asyncio.Lock()
_ACTIVE_OPERATIONS: set[tuple[Path, str]] = set()
_CONVERSATION_ID = re.compile(r"^(default|[0-9a-f]{32})$")


def _validate_id(conversation_id: str) -> str:
    if not _CONVERSATION_ID.fullmatch(conversation_id):
        raise HTTPException(status_code=422, detail="对话编号无效")
    return conversation_id


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="个人智能体会话文件无法读取") from exc
    if not isinstance(value, dict):
        raise HTTPException(status_code=500, detail="个人智能体会话文件格式错误")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _index(directory: Path) -> dict[str, Any]:
    path = directory / "conversations.json"
    # 未建立索引的旧账号沿用原 session.json，不迁移或覆盖已有聊天。
    if not path.exists():
        return {"version": 1, "ids": ["default"], "active_id": "default"}
    value = _read_json(path)
    ids = value.get("ids")
    active_id = value.get("active_id")
    if (value.get("version") != 1 or not isinstance(ids, list)
            or any(not isinstance(item, str) or not _CONVERSATION_ID.fullmatch(item) for item in ids)
            or len(set(ids)) != len(ids) or (active_id is not None and active_id not in ids)
            or (ids and active_id is None)):
        raise HTTPException(status_code=500, detail="个人智能体对话索引格式错误")
    return value


def _path(directory: Path, conversation_id: str) -> Path:
    _validate_id(conversation_id)
    return directory / "session.json" if conversation_id == "default" else directory / "conversations" / f"{conversation_id}.json"


def _empty(conversation_id: str | None) -> dict[str, Any]:
    return {"conversation_id": conversation_id, "conversation_title": "办公对话" if conversation_id == "default" else "新对话",
            "messages": [], "pending_actions": [], "structured_results": [], "created_at": "", "updated_at": ""}


def read_state(directory: Path, conversation_id: str | None = None) -> dict[str, Any]:
    index = _index(directory)
    selected = conversation_id if conversation_id is not None else index["active_id"]
    if selected is None:
        return _empty(None)
    _validate_id(selected)
    if selected not in index["ids"]:
        raise HTTPException(status_code=404, detail="对话不存在或已删除")
    path = _path(directory, selected)
    if selected == "default" and not path.exists():
        return _empty(selected)
    value = _read_json(path)
    state = _empty(selected)
    for key in ("messages", "pending_actions", "structured_results"):
        items = value.get(key, [])
        if not isinstance(items, list):
            raise HTTPException(status_code=500, detail="个人智能体会话内容格式错误")
        state[key] = items
    state["created_at"] = str(value.get("created_at") or "")
    state["updated_at"] = str(value.get("updated_at") or "")
    first = next((item for item in state["messages"] if isinstance(item, dict) and item.get("role") == "user" and item.get("content")), None)
    state["conversation_title"] = str(value.get("conversation_title") or (" ".join(str(first["content"]).split())[:40] if first else state["conversation_title"]))
    return state


def _snapshot(directory: Path) -> dict[str, Any]:
    index = _index(directory)
    items = []
    for conversation_id in index["ids"]:
        state = read_state(directory, conversation_id)
        items.append({"id": conversation_id, "title": state["conversation_title"], "message_count": len(state["messages"]),
                      "updated_at": state["updated_at"] or state["created_at"]})
    items.sort(key=lambda item: item["updated_at"], reverse=True)
    return {"items": items, "active_id": index["active_id"], "state": read_state(directory)}


async def list_conversations(directory: Path) -> dict[str, Any]:
    async with STATE_LOCK:
        return _snapshot(directory)


async def create_conversation(directory: Path) -> dict[str, Any]:
    async with STATE_LOCK:
        index = _index(directory)
        conversation_id = uuid4().hex
        state = _empty(conversation_id)
        state["created_at"] = datetime.now(timezone.utc).isoformat()
        path = _path(directory, conversation_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(path, state)
        try:
            _write_json(directory / "conversations.json", {"version": 1, "ids": [*index["ids"], conversation_id], "active_id": conversation_id})
        except Exception:
            path.unlink()
            raise
        return _snapshot(directory)


async def select_conversation(directory: Path, conversation_id: str) -> dict[str, Any]:
    async with STATE_LOCK:
        read_state(directory, conversation_id)
        index = _index(directory)
        index["active_id"] = conversation_id
        _write_json(directory / "conversations.json", index)
        return _snapshot(directory)


async def delete_conversation(directory: Path, conversation_id: str) -> dict[str, Any]:
    async with STATE_LOCK:
        state = read_state(directory, conversation_id)
        if (directory, conversation_id) in _ACTIVE_OPERATIONS:
            raise HTTPException(status_code=409, detail="该对话正在处理，请完成或停止生成后再删除")
        if state["pending_actions"]:
            raise HTTPException(status_code=409, detail="请先处理或取消该对话的待确认操作，再删除对话")
        index = _index(directory)
        remaining = [item["id"] for item in _snapshot(directory)["items"] if item["id"] != conversation_id]
        index["ids"] = remaining
        if index["active_id"] == conversation_id:
            index["active_id"] = remaining[0] if remaining else None
        path = _path(directory, conversation_id)
        # 先移出索引，文件删除失败时恢复索引并明确报错。
        previous = _index(directory)
        _write_json(directory / "conversations.json", index)
        try:
            path.unlink(missing_ok=conversation_id == "default")
        except OSError:
            _write_json(directory / "conversations.json", previous)
            raise
        return _snapshot(directory)


async def save_state(directory: Path, state: dict[str, Any]) -> None:
    async with STATE_LOCK:
        conversation_id = state["conversation_id"]
        read_state(directory, conversation_id)
        if not conversation_id:
            raise HTTPException(status_code=409, detail="请先新建对话")
        if not state["created_at"]:
            state["created_at"] = datetime.now(timezone.utc).isoformat()
        if len(state["messages"]) == 1 and state["messages"][0].get("role") == "user":
            state["conversation_title"] = " ".join(str(state["messages"][0]["content"]).split())[:40]
        _write_json(_path(directory, conversation_id), state)


@asynccontextmanager
async def conversation_operation(directory: Path, conversation_id: str | None) -> AsyncIterator[dict[str, Any]]:
    async with STATE_LOCK:
        state = read_state(directory, conversation_id)
        if not state["conversation_id"]:
            raise HTTPException(status_code=409, detail="请先新建对话")
        key = (directory, state["conversation_id"])
        if key in _ACTIVE_OPERATIONS:
            raise HTTPException(status_code=409, detail="该对话正在处理，请稍后再试")
        _ACTIVE_OPERATIONS.add(key)
    try:
        yield state
    finally:
        async with STATE_LOCK:
            _ACTIVE_OPERATIONS.remove(key)
