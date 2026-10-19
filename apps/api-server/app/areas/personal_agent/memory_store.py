"""OA 长期记忆的权限过滤与审计；上下文压缩统一交给 DPH。"""
from __future__ import annotations

import functools
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, TypedDict
from uuid import uuid4

from app.core.process_coordination import coordination_path, file_lock_sync


_MEMORY_FILE = "memories.json"
_AUDIT_FILE = "memory_audit.jsonl"
_LOCK_DEPTH: dict[str, int] = {}


def _memory_locked(function):
    """记忆文件的读-改-写在多个 API 进程间互斥。

    这些函数都在事件循环中同步执行、相互嵌套调用（例如流水线先过期再保存），
    同一进程按目录记录嵌套深度，只在最外层获取文件锁，避免同进程重入阻塞。
    """
    @functools.wraps(function)
    def wrapper(directory: Path, *args, **kwargs):
        key = str(directory)
        if _LOCK_DEPTH.get(key):
            _LOCK_DEPTH[key] += 1
            try:
                return function(directory, *args, **kwargs)
            finally:
                _LOCK_DEPTH[key] -= 1
        with file_lock_sync(coordination_path(f"personal-agent-memory:{key}")):
            _LOCK_DEPTH[key] = 1
            try:
                return function(directory, *args, **kwargs)
            finally:
                _LOCK_DEPTH.pop(key, None)
    return wrapper
_EXPLICIT_MEMORY = re.compile(r"(?:记住|请记住|以后|今后|我的偏好|我习惯|保存这个偏好|记下来)[：:，,\s]*(.+)", re.I | re.S)
_TOKEN = re.compile(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]{2,}")
_CATEGORY_FACT = re.compile(r"(?:我叫|我是|我的(?:姓名|名字|公司|职位|职业|所在|生日)|来自|住在)")
_CATEGORY_PREFERENCE = re.compile(r"(?:偏好|喜欢|习惯|倾向|希望|请用|不要用|优先)")
_LONG_TERM_COMMAND = re.compile(r"(?:(?:这个|上述|刚才|前面).{0,8}(?:长期记忆|永久记忆)|(?:保存|写入|加入|形成).{0,8}(?:长期记忆|永久记忆))")


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
    category: str | None
    allowed_case_ids: list[int] | None
    summary_metadata: dict[str, Any]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty() -> dict[str, Any]:
    return {"version": 1, "settings": {"enabled": True, "retention_days": 365, "recall_limit": 5}, "items": []}


def _task_scope(conversation_id: str | None, case_id: int | None, category: str) -> str:
    if case_id:
        return f"case:{case_id}"
    # Facts, preferences, and reusable experiences are global personal memory;
    # the conversation id remains provenance, not an authorization shortcut.
    return "global"


def _classify(content: str) -> str:
    if _CATEGORY_PREFERENCE.search(content):
        return "preference"
    if _CATEGORY_FACT.search(content):
        return "fact"
    return "experience"


def _terms(text: str) -> set[str]:
    """Build stable lexical/semantic-lite terms for Chinese and Latin text."""
    terms: set[str] = set(_TOKEN.findall(text.lower()))
    for span in re.findall(r"[\u4e00-\u9fff]+", text.lower()):
        terms.update(span)
        terms.update(span[index:index + 2] for index in range(len(span) - 1))
    return terms


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


def _audit(directory: Path, owner_user_id: int, action: str, item: dict[str, Any] | None = None,
           *, detail: dict[str, Any] | None = None, conversation_id: str | None = None,
           case_id: int | None = None) -> None:
    """Append an evidence-preserving memory lifecycle event.

    Memory is file-backed today, so the audit log is append-only JSONL next to
    the memory store.  It intentionally contains no prompt/tool payload beyond
    the memory id and a bounded content snapshot.
    """
    directory.mkdir(parents=True, exist_ok=True)
    record = {
        "id": uuid4().hex,
        "occurred_at": _now(),
        "owner_user_id": owner_user_id,
        "action": action,
        "memory_id": item.get("id") if item else None,
        "memory_category": item.get("memory_category") if item else None,
        "task_scope": item.get("task_scope") if item else (f"case:{case_id}" if case_id else "global"),
        "permission_scope": item.get("permission_scope") if item else ("case" if case_id else "personal"),
        "conversation_id": conversation_id or (item.get("conversation_id") if item else None),
        "case_id": case_id if case_id is not None else (item.get("case_id") if item else None),
        "content_snapshot": str(item.get("content") or "")[:1000] if item else None,
        "detail": detail or {},
    }
    with (directory / _AUDIT_FILE).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def _parse_time(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _normalise_content(value: str) -> str:
    return " ".join(value.lower().split()).strip(" ，。；;,.、")


def _conflict_subject(value: str) -> str | None:
    """Return a stable subject for common fact/preference replacements."""
    text = _normalise_content(value)
    for pattern in (r"^(我叫|我是|我的(?:姓名|名字|公司|职位|职业|所在|生日))", r"^(偏好|喜欢|习惯|倾向|希望|请用|不要用|优先)"):
        match = re.match(pattern, text)
        if match:
            return match.group(1)
    return None


def _extract_node(state: MemoryState) -> dict[str, Any]:
    user_text = str(state.get("user_text") or "")
    match = _EXPLICIT_MEMORY.search(user_text)
    candidate = " ".join(match.group(1).split())[:1_000] if match else None
    # "这个要形成长期记忆" refers to the immediately preceding user fact or
    # preference; never store the command itself as a memory item.
    if _LONG_TERM_COMMAND.search(user_text) and (not candidate or len(candidate) < 8):
        for message in reversed(state.get("messages", [])):
            if message.get("role") != "user":
                continue
            previous = " ".join(str(message.get("content") or "").split())
            if previous and not _LONG_TERM_COMMAND.search(previous):
                candidate = previous[:1_000]
                break
    return {"candidate": candidate, "category": _classify(candidate) if candidate else None}


def _recall_node(state: MemoryState) -> dict[str, Any]:
    path = Path(state["directory"]) / _MEMORY_FILE
    data = _read(path)
    settings = data["settings"]
    if not settings.get("enabled", True):
        return {"recalled": []}
    query = _terms(str(state.get("user_text") or ""))
    case_id = state.get("case_id")
    allowed_case_ids = {int(value) for value in (state.get("allowed_case_ids") or []) if value}
    owner = int(state.get("owner_user_id") or 0)
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, min(int(settings.get("retention_days", 365)), 3650)))
    candidates = []
    for item in data["items"]:
        if not isinstance(item, dict) or item.get("owner_user_id") != owner or item.get("deleted_at") or item.get("lifecycle_state", "active") != "active":
            continue
        try:
            if datetime.fromisoformat(str(item.get("updated_at"))).astimezone(timezone.utc) < cutoff:
                continue
        except (TypeError, ValueError):
            continue
        item_case = item.get("case_id")
        if item_case not in (None, case_id):
            continue
        if item_case is not None and int(item_case) not in allowed_case_ids:
            continue
        task_scope = str(item.get("task_scope") or (f"case:{item_case}" if item_case else "global"))
        if task_scope.startswith("case:") and task_scope != f"case:{case_id}":
            continue
        if task_scope.startswith("conversation:") and task_scope != f"conversation:{state.get('conversation_id')}":
            continue
        permission_scope = str(item.get("permission_scope") or "personal")
        if permission_scope not in {"personal", "case", "current_user"}:
            continue
        tokens = _terms(str(item.get("content") or ""))
        score = len(query & tokens)
        if score or not query:
            candidates.append({**item, "recall_score": score})
    candidates.sort(key=lambda item: (item["recall_score"], item.get("updated_at", "")), reverse=True)
    return {"recalled": candidates[: max(0, min(int(settings.get("recall_limit", 5)), 20))]}


@_memory_locked
def _save_candidate(directory: Path, owner_user_id: int, conversation_id: str | None, case_id: int | None,
                    candidate: str | None, category: str | None) -> dict[str, Any] | None:
    if not candidate:
        return None
    path = directory / _MEMORY_FILE
    data = _read(path)
    settings = data["settings"]
    if not settings.get("enabled", True):
        return None
    now = _now()
    category = category if category in {"fact", "preference", "experience"} else "experience"
    normalized = _normalise_content(candidate)
    subject = _conflict_subject(candidate)
    new_id = uuid4().hex
    # Same-owner, same-scope memories are updated in place when they are exact
    # duplicates.  A changed fact/preference supersedes the old record so the
    # audit trail preserves the conflict resolution instead of accumulating
    # contradictory context.
    for existing in reversed(data["items"]):
        if not isinstance(existing, dict) or existing.get("owner_user_id") != owner_user_id:
            continue
        if existing.get("case_id") != case_id or existing.get("memory_category") != category or existing.get("lifecycle_state", "active") != "active":
            continue
        existing_text = _normalise_content(str(existing.get("content") or ""))
        if existing_text == normalized:
            existing["updated_at"] = now
            _audit(directory, owner_user_id, "deduplicated", existing, detail={"reason": "exact_content"}, conversation_id=conversation_id, case_id=case_id)
            _write(path, data)
            return existing
        existing_subject = existing.get("conflict_subject") or _conflict_subject(existing_text)
        if subject and existing_subject == subject:
            existing["lifecycle_state"] = "superseded"
            existing["superseded_at"] = now
            existing["superseded_by"] = new_id
            _audit(directory, owner_user_id, "conflict_resolved", existing, detail={"replacement_id": new_id}, conversation_id=conversation_id, case_id=case_id)
            break
    item = {"id": new_id, "kind": "long", "content": candidate, "memory_category": category,
            "owner_user_id": owner_user_id, "conversation_id": conversation_id, "case_id": case_id,
            "task_scope": _task_scope(conversation_id, case_id, category),
            "permission_scope": "case" if case_id else "personal", "source_type": "explicit_user",
            "source_label": "用户明确要求保存", "source_conversation_id": conversation_id,
            "confidence": 0.95, "conflict_subject": subject, "lifecycle_state": "active",
            "created_at": now, "updated_at": now, "deleted_at": None, "expires_at": None,
            "revoked_at": None, "superseded_at": None, "superseded_by": None}
    data["items"] = [*data["items"], item][-500:]
    _write(path, data)
    _audit(directory, owner_user_id, "created", item, conversation_id=conversation_id, case_id=case_id)
    return item


@_memory_locked
def prepare_memory_context(directory: Path, owner_user_id: int, conversation_id: str | None, case_id: int | None,
                        messages: list[dict[str, Any]], user_text: str, summary: str = "",
                        allowed_case_ids: list[int] | None = None,
                        summary_metadata: dict[str, Any] | None = None,
                        save_explicit: bool = True) -> dict[str, Any]:
    expire_memories(directory, owner_user_id)
    state = {"directory": str(directory), "owner_user_id": owner_user_id,
             "conversation_id": conversation_id, "case_id": case_id,
             "allowed_case_ids": ([case_id] if allowed_case_ids is None and case_id else (allowed_case_ids or [])),
             "messages": messages, "user_text": user_text}
    result = {**(_extract_node(state) if save_explicit else {}), **_recall_node(state)}
    item = _save_candidate(directory, owner_user_id, conversation_id, case_id, result.get("candidate"), result.get("category"))
    if result.get("recalled"):
        _audit(directory, owner_user_id, "recalled", detail={"memory_ids": [item.get("id") for item in result["recalled"] if item.get("id")]}, conversation_id=conversation_id, case_id=case_id)
    # 已有历史摘要仅保留供查看，不再生成或覆盖；原生会话独立管理上下文。
    return {"summary": summary, "summary_metadata": summary_metadata or {},
            "recalled": result.get("recalled", []), "created": item}


@_memory_locked
def list_memories(directory: Path, owner_user_id: int, limit: int = 50) -> dict[str, Any]:
    expire_memories(directory, owner_user_id)
    data = _read(directory / _MEMORY_FILE)
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, min(int(data["settings"].get("retention_days", 365)), 3650)))
    items = []
    for item in data["items"]:
        if not isinstance(item, dict) or item.get("owner_user_id") != owner_user_id or item.get("deleted_at") or item.get("lifecycle_state", "active") != "active":
            continue
        try:
            if datetime.fromisoformat(str(item.get("updated_at"))).astimezone(timezone.utc) < cutoff:
                continue
        except (TypeError, ValueError):
            continue
        items.append(item)
    items.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    return {"settings": data["settings"], "items": items[: max(1, min(limit, 100))]}


@_memory_locked
def delete_memory(directory: Path, owner_user_id: int, memory_id: str) -> bool:
    path = directory / _MEMORY_FILE
    data = _read(path)
    for item in data["items"]:
        if item.get("id") == memory_id and item.get("owner_user_id") == owner_user_id and not item.get("deleted_at"):
            item["deleted_at"] = _now()
            item["revoked_at"] = item["deleted_at"]
            item["lifecycle_state"] = "revoked"
            _write(path, data)
            _audit(directory, owner_user_id, "revoked", item, detail={"reason": "user_request"})
            return True
    return False


@_memory_locked
def expire_memories(directory: Path, owner_user_id: int | None = None, *, now: datetime | None = None) -> int:
    """Mark retained memories expired without physically deleting evidence."""
    path = directory / _MEMORY_FILE
    data = _read(path)
    current = now or datetime.now(timezone.utc)
    retention = max(1, min(int(data["settings"].get("retention_days", 365)), 3650))
    cutoff = current - timedelta(days=retention)
    changed = 0
    for item in data["items"]:
        if not isinstance(item, dict) or (owner_user_id is not None and item.get("owner_user_id") != owner_user_id):
            continue
        if item.get("lifecycle_state", "active") != "active":
            continue
        updated = _parse_time(item.get("updated_at"))
        if updated and updated < cutoff:
            item["lifecycle_state"] = "expired"
            item["expired_at"] = current.isoformat()
            changed += 1
            _audit(directory, int(item.get("owner_user_id") or 0), "expired", item, detail={"retention_days": retention})
    if changed:
        _write(path, data)
    return changed


def list_memory_audit(directory: Path, owner_user_id: int, limit: int = 100) -> list[dict[str, Any]]:
    path = directory / _AUDIT_FILE
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines()[-max(1, min(limit, 200)):]:
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if isinstance(value, dict) and value.get("owner_user_id") == owner_user_id:
                rows.append(value)
    except OSError:
        return []
    return list(reversed(rows))


@_memory_locked
def update_settings(directory: Path, owner_user_id: int, *, enabled: bool | None = None,
                    retention_days: int | None = None, recall_limit: int | None = None) -> dict[str, Any]:
    path = directory / _MEMORY_FILE
    data = _read(path)
    settings = data["settings"]
    before = dict(settings)
    if enabled is not None:
        settings["enabled"] = enabled
    if retention_days is not None:
        settings["retention_days"] = max(1, min(retention_days, 3650))
    if recall_limit is not None:
        settings["recall_limit"] = max(0, min(recall_limit, 20))
    _write(path, data)
    if before != settings:
        _audit(directory, owner_user_id, "settings_changed", detail={"before": before, "after": dict(settings)})
    return settings
