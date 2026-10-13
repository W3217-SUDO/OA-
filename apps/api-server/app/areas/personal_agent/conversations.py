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
from app.agent_mcp.action_summary import summary_from_preview


STATE_LOCK = asyncio.Lock()
_ACTIVE_OPERATIONS: dict[tuple[Path, str], tuple[asyncio.Task, bool]] = {}
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
            "messages": [], "pending_actions": [], "structured_results": [], "dismissed_action_ids": [],
            "created_at": "", "updated_at": ""}


def _pending_action_view(action):
    """只转换返回副本，旧待确认卡按已存参数展示，不修改会话文件或操作参数。"""
    if not isinstance(action, dict):
        return action
    payload = action.get("payload") or {}
    if action.get("type") == "mcp.call" and isinstance(action.get("preview"), dict):
        return {**action, "summary": summary_from_preview(action["preview"])}
    if action.get("type") == "create_task" and isinstance(payload, dict) and payload.get("title"):
        summary = f"新建任务“{payload['title']}”，负责人 {payload.get('owner') or action.get('requested_by') or '未指定'}，截止 {payload.get('deadline') or '未指定'}"
        return {**action, "summary": summary}
    if (action.get("type") == "approve_contract" and isinstance(payload, dict)
            and action.get("summary") in (None, "", "审批合同", "批量任务")
            and payload.get("contract_id") and isinstance(payload.get("approved"), bool)):
        summary = f"{'批准' if payload['approved'] else '拒绝'}合同 {payload['contract_id']} 的当前审批节点"
        return {**action, "summary": summary}
    return action


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
    state["pending_actions"] = [_pending_action_view(action) for action in state["pending_actions"]]
    dismissed = value.get("dismissed_action_ids", [])
    if (not isinstance(dismissed, list) or any(not isinstance(item, str) or not item for item in dismissed)
            or len(set(dismissed)) != len(dismissed)):
        raise HTTPException(status_code=500, detail="个人智能体操作卡展示记录格式错误")
    state["dismissed_action_ids"] = dismissed
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


async def read_conversation_states(directory: Path) -> list[dict[str, Any]]:
    """仅从本人索引读取结构化操作来源，不扫描其他账号或猜测会话编号。"""
    async with STATE_LOCK:
        return [read_state(directory, item) for item in _index(directory)["ids"]]


async def save_action_dismissals(directory: Path, conversation_id: str, action_ids: list[str]) -> dict[str, Any]:
    """在既有会话操作锁内调用，只修改展示元数据，保留原请求与聊天。"""
    async with STATE_LOCK:
        state = read_state(directory, conversation_id)
        existing = {item.get("id") for item in state["pending_actions"] if isinstance(item, dict)}
        if not set(action_ids).issubset(existing):
            raise HTTPException(status_code=404, detail="操作卡不存在或已从原会话处理")
        raw = _read_json(_path(directory, conversation_id))
        retained = [item for item in state["dismissed_action_ids"] if item in existing]
        dismissed = [*retained, *(item for item in action_ids if item not in retained)]
        if dismissed != state["dismissed_action_ids"]:
            raw["dismissed_action_ids"] = dismissed
            _write_json(_path(directory, conversation_id), raw)
        return read_state(directory, conversation_id)


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
async def conversation_operation(directory: Path, conversation_id: str | None, *, cancellable: bool = False) -> AsyncIterator[dict[str, Any]]:
    async with STATE_LOCK:
        state = read_state(directory, conversation_id)
        if not state["conversation_id"]:
            raise HTTPException(status_code=409, detail="请先新建对话")
        key = (directory, state["conversation_id"])
        if key in _ACTIVE_OPERATIONS:
            raise HTTPException(status_code=409, detail="该对话正在处理，请稍后再试")
        task = asyncio.current_task()
        if task is None:
            raise RuntimeError("对话操作缺少运行任务")
        _ACTIVE_OPERATIONS[key] = (task, cancellable)
    try:
        yield state
    finally:
        async with STATE_LOCK:
            del _ACTIVE_OPERATIONS[key]


async def stop_generation(directory: Path, conversation_id: str) -> dict[str, Any]:
    async with STATE_LOCK:
        read_state(directory, conversation_id)
        operation = _ACTIVE_OPERATIONS.get((directory, conversation_id))
        if operation and not operation[1]:
            raise HTTPException(status_code=409, detail="该对话正在执行已确认的 OA 操作，不能中断")
        if operation:
            task = operation[0]
            if not task.cancelling():
                task.cancel()
    # 不持有文件锁等待取消，让生成任务保存部分回答并释放对话占用。
    if operation:
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            if asyncio.current_task().cancelling():
                raise
    async with STATE_LOCK:
        return read_state(directory, conversation_id)
