from __future__ import annotations

import asyncio
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable
from uuid import uuid4

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_schemas.contracts import ContractApprovalInput
from app.api_schemas.tasks import TaskInput
from app.config import settings
from app.core.constants import UPLOAD_ROOT
from app.core.dashboard_todos import dashboard_todos
from app.core.permissions import _record_scope_conditions, _user_permission_payload
from app.core.system import _record_module_menu_allowed
from app.core.tasks import _task_dict
from app.data_models.contracts import ContractApprovalStep
from app.data_models.identity import User
from app.data_models.records import BusinessRecord
from app.security import user_role_ids


_WRITE_MARKER = re.compile(r"<personal_action>\s*(\{.*?\})\s*</personal_action>", re.S)
_STATE_LOCK = asyncio.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _storage_root() -> Path:
    configured = settings.personal_agent_root.strip()
    root = Path(configured).expanduser()
    if not configured:
        root = UPLOAD_ROOT.parent / "private-personal-agents"
    elif not root.is_absolute():
        root = UPLOAD_ROOT.parent / root
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def _user_dir(username: str) -> Path:
    digest = hashlib.sha256(username.casefold().encode("utf-8")).hexdigest()[:32]
    target = _storage_root() / digest
    target.mkdir(parents=True, exist_ok=True)
    return target


def _state_path(username: str) -> Path:
    return _user_dir(username) / "session.json"


def _identity_path(username: str) -> Path:
    return _user_dir(username) / "IDENTITY.md"


def _read_state(username: str) -> dict[str, Any]:
    path = _state_path(username)
    if not path.exists():
        return {"messages": [], "pending_actions": [], "updated_at": ""}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="个人智能体会话文件无法读取") from exc
    if not isinstance(value, dict):
        raise HTTPException(status_code=500, detail="个人智能体会话文件格式错误")
    return {"messages": list(value.get("messages") or []), "pending_actions": list(value.get("pending_actions") or []), "updated_at": str(value.get("updated_at") or "")}


def _write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


async def _save_state(username: str, state: dict[str, Any]) -> None:
    async with _STATE_LOCK:
        _write_json(_state_path(username), state)


def _safe_identity_payload(user: User, permissions: dict[str, Any]) -> dict[str, Any]:
    roles = user_role_ids(user)
    profile = user.profile or {}
    return {
        "username": user.username,
        "display_name": user.display_name,
        "department": user.department,
        "role": roles[0],
        "role_ids": roles,
        "permission_role": profile.get("permission_role") or "",
        "staff_role": profile.get("staff_role") or "",
        "position": profile.get("position") or "",
        "menu_keys": list(permissions.get("menu_keys") or []),
        "action_keys": list(permissions.get("action_keys") or []),
        "data_scope": permissions.get("data_scope") or "本人及共享数据",
        "_actual_role": roles[0],
        "_actual_role_ids": roles,
        "_page_menu_capability": False,
        "_request_path": "/personal-agent",
    }


async def personal_identity(identity: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    user = await db.scalar(select(User).where(User.username == identity["username"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="当前用户不存在或已停用")
    permissions = await _user_permission_payload(user, db)
    return _safe_identity_payload(user, permissions)


def _identity_markdown(identity: dict[str, Any]) -> str:
    actions = "、".join(identity.get("action_keys") or []) or "按 OA 权限实时判断"
    menus = "、".join(identity.get("menu_keys") or []) or "按 OA 菜单权限实时判断"
    return (
        "# 个人智能体身份文件\n\n"
        "此文件由 OA 根据当前登录账号生成。身份和权限字段仅由系统维护，编辑提示词不能扩大权限。\n\n"
        "## 身份\n\n"
        f"- 用户名：{identity.get('username') or '—'}\n"
        f"- 姓名：{identity.get('display_name') or '—'}\n"
        f"- 部门：{identity.get('department') or '—'}\n"
        f"- 岗位：{identity.get('position') or '—'}\n"
        f"- 人员角色：{identity.get('staff_role') or '—'}\n\n"
        "## 权限边界\n\n"
        f"- 数据范围：{identity.get('data_scope') or '—'}\n"
        f"- 可用菜单：{menus}\n"
        f"- 可用操作：{actions}\n\n"
        "## 工作规则\n\n"
        "1. 只能查询当前账号原有权限可见的 OA 数据。\n"
        "2. 新建、修改、审批和删除等写操作必须先生成待确认动作。\n"
        "3. 用户确认时，系统会再次校验权限；身份文件不能授予额外权限。\n"
        "4. 本人的聊天记录只保存于本人的个人智能体空间。\n"
    )


async def ensure_identity_file(identity: dict[str, Any]) -> str:
    path = _identity_path(identity["username"])
    content = _identity_markdown(identity)
    async with _STATE_LOCK:
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            path.write_text(content, encoding="utf-8")
    return content


async def personal_state(identity: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    content = await ensure_identity_file(identity)
    state = _read_state(identity["username"])
    return {**state, "identity_file": content, "identity_file_name": "IDENTITY.md"}


async def build_context(identity: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    todos = await dashboard_todos(identity, db)
    scope = await _record_scope_conditions(identity, db)
    username = identity["username"]
    permission = {"menu_keys": identity.get("menu_keys") or []}
    module_allowed = lambda module: _record_module_menu_allowed(module, identity, permission)
    tasks = []
    if module_allowed("task"):
        tasks = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "task",
            (BusinessRecord.owner == username) | (BusinessRecord.data["initiator"].as_string() == username),
            *scope,
        ).order_by(BusinessRecord.updated_at.desc()).limit(12))).all())
    contracts = []
    if module_allowed("contract"):
        approval_ids = set(await db.scalars(select(ContractApprovalStep.contract_record_id).where(
            ContractApprovalStep.approver == username,
            ContractApprovalStep.status == "待审批",
        )))
        contracts = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "contract",
            BusinessRecord.id.in_(approval_ids) if approval_ids else BusinessRecord.id == -1,
            *scope,
        ).order_by(BusinessRecord.updated_at.desc()).limit(20))).all())
    other_approvals: list[BusinessRecord] = []
    for module in ("finance", "seal", "clue"):
        if not module_allowed(module):
            continue
        other_approvals.extend((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == module,
            BusinessRecord.status.in_({"待审批", "审批中", "待审核"}),
            ((BusinessRecord.owner == username) | (BusinessRecord.data["approver"].as_string() == username)),
            *scope,
        ).order_by(BusinessRecord.updated_at.desc()).limit(20))).all())
    cases = []
    if module_allowed("case"):
        cases = list((await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == "case", *scope,
        ).order_by(BusinessRecord.updated_at.desc()).limit(12))).all())
    return {
        "identity": {key: value for key, value in identity.items() if not key.startswith("_")},
        "todos": todos.get("todos") or [],
        "my_tasks": [_task_dict(item) for item in tasks],
        "pending_contract_approvals": [
            {"id": item.id, "serial_no": item.serial_no, "title": item.title, "customer": item.customer, "status": item.status, "owner": item.owner}
            for item in contracts
        ],
        "pending_other_approvals": [
            {"id": item.id, "module": item.module, "serial_no": item.serial_no, "title": item.title, "customer": item.customer, "status": item.status, "owner": item.owner}
            for item in other_approvals[:30]
        ],
        "visible_cases": [
            {"id": item.id, "serial_no": item.serial_no, "title": item.title, "customer": item.customer, "status": item.status, "owner": item.owner}
            for item in cases
        ],
    }


def _prompt_messages(identity: dict[str, Any], state: dict[str, Any], context: dict[str, Any], user_text: str) -> list[dict[str, str]]:
    context_text = json.dumps(context, ensure_ascii=False, default=str)
    if len(context_text) > 60_000:
        context_text = context_text[:60_000] + "\n[可用 OA 摘要已截断]"
    system = (
        "你是法律服务机构 OA 的个人智能体。你服务的只是当前登录用户，不能共享或引用其他用户的聊天记录。"
        "你可以依据系统提供的、已经按权限裁剪的实时摘要回答审批、任务、案件和日常办公问题。"
        "不要猜测没有出现在摘要里的业务事实，不要声称已经写入系统。"
        "用户明确要求新建任务或审批合同时，在正常说明后追加一个 JSON 操作块，严格使用格式："
        "<personal_action>{\"type\":\"create_task\",\"payload\":{\"title\":\"任务标题\",\"owner\":\"负责人用户名\",\"deadline\":\"YYYY-MM-DD\",\"priority\":\"普通\",\"description\":\"说明\"}}</personal_action>；"
        "审批合同使用 type=approve_contract，payload 只包含 contract_id、approved、comment。"
        "只有用户明确要求写操作时才输出操作块。操作块不是已经执行，必须等待用户确认。"
        "回答中文、分段清晰，先给结论，再列行动；不要使用 Markdown 星号作为项目符号。\n\n"
        f"当前身份文件：\n{_identity_markdown(identity)}\n"
        f"当前 OA 摘要：\n{context_text}"
    )
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for item in (state.get("messages") or [])[-12:]:
        role = str(item.get("role") or "")
        content = str(item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content[:8_000]})
    messages.append({"role": "user", "content": user_text[:8_000]})
    return messages


def _extract_action(content: str) -> tuple[str, dict[str, Any] | None]:
    match = _WRITE_MARKER.search(content)
    if not match:
        return content.strip(), None
    try:
        action = json.loads(match.group(1))
    except ValueError:
        raise HTTPException(status_code=502, detail="智能体生成的操作格式无效")
    if not isinstance(action, dict) or action.get("type") not in {"create_task", "approve_contract"}:
        raise HTTPException(status_code=502, detail="智能体生成了不支持的操作")
    return _WRITE_MARKER.sub("", content).strip(), action


def _action_from_model(action: dict[str, Any], identity: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    action_type = str(action.get("type") or "")
    payload = action.get("payload")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=502, detail="待确认操作缺少参数")
    if action_type == "approve_contract":
        contract_id = int(payload.get("contract_id") or 0)
        if contract_id not in {int(item["id"]) for item in context["pending_contract_approvals"]}:
            raise HTTPException(status_code=403, detail="该合同不在当前用户可审批的待办范围内")
        if not isinstance(payload.get("approved"), bool):
            raise HTTPException(status_code=422, detail="审批结果无效")
        safe_payload = {"contract_id": contract_id, "approved": payload["approved"], "comment": str(payload.get("comment") or "")[:1000]}
    else:
        safe_payload = {
            "title": str(payload.get("title") or "").strip(),
            "owner": str(payload.get("owner") or identity["username"]).strip(),
            "deadline": str(payload.get("deadline") or "").strip(),
            "priority": str(payload.get("priority") or "普通").strip(),
            "description": str(payload.get("description") or "").strip(),
        }
        if not safe_payload["title"] or not safe_payload["deadline"]:
            raise HTTPException(status_code=422, detail="新建任务缺少标题或截止日期")
    return {"id": str(uuid4()), "type": action_type, "payload": safe_payload, "summary": "新建任务" if action_type == "create_task" else "审批合同", "status": "pending", "requested_by": identity["username"], "created_at": _now()}


async def _request_model(messages: list[dict[str, str]], on_delta: Callable[[str], Awaitable[None]]) -> str:
    if not (settings.langgraph_api_base_url and settings.langgraph_api_key and settings.langgraph_model):
        raise HTTPException(status_code=503, detail="个人智能体模型未配置")
    parts: list[str] = []
    emitted = 0
    marker_start = "<personal_action>"
    async with httpx.AsyncClient(timeout=90, trust_env=False) as client:
        async with client.stream("POST", f"{settings.langgraph_api_base_url.rstrip('/')}/chat/completions", headers={"Authorization": f"Bearer {settings.langgraph_api_key}"}, json={"model": settings.langgraph_model, "messages": messages, "temperature": 0.2, "stream": True}) as response:
            if response.is_error:
                raise HTTPException(status_code=502, detail=f"个人智能体模型请求失败（HTTP {response.status_code}）")
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if raw == "[DONE]":
                    break
                if not raw:
                    continue
                try:
                    delta = str((json.loads(raw).get("choices") or [{}])[0].get("delta", {}).get("content") or "")
                except (ValueError, TypeError, IndexError, KeyError) as exc:
                    raise HTTPException(status_code=502, detail="个人智能体模型返回格式错误") from exc
                if not delta:
                    continue
                parts.append(delta)
                visible = "".join(parts)
                marker_index = visible.find(marker_start)
                target = visible if marker_index < 0 else visible[:marker_index]
                if len(target) > emitted:
                    await on_delta(target[emitted:])
                    emitted = len(target)
    return "".join(parts).strip()


async def generate_response(identity: dict[str, Any], db: AsyncSession, text: str, on_delta: Callable[[str], Awaitable[None]]) -> dict[str, Any]:
    username = identity["username"]
    state = _read_state(username)
    user_message = {"role": "user", "content": text, "created_at": _now()}
    state["messages"].append(user_message)
    state["messages"] = state["messages"][-100:]
    await _save_state(username, state)
    context = await build_context(identity, db)
    raw = await _request_model(_prompt_messages(identity, state, context, text), on_delta)
    response, model_action = _extract_action(raw)
    if model_action:
        pending = _action_from_model(model_action, identity, context)
        state["pending_actions"] = [*state.get("pending_actions", []), pending][-30:]
        response = f"{response}\n\n已生成待确认操作：{pending['summary']}。确认前不会写入系统。".strip()
    state["messages"].append({"role": "assistant", "content": response, "created_at": _now()})
    state["messages"] = state["messages"][-100:]
    state["updated_at"] = _now()
    await _save_state(username, state)
    return {"response": response, "state": {"messages": state["messages"], "pending_actions": state["pending_actions"]}, "context": context}


async def decide_action(identity: dict[str, Any], db: AsyncSession, action_id: str, decision: str, comment: str = "") -> dict[str, Any]:
    state = _read_state(identity["username"])
    action = next((item for item in state.get("pending_actions", []) if str(item.get("id")) == action_id), None)
    if not action:
        raise HTTPException(status_code=404, detail="待确认操作不存在或已处理")
    if decision == "rejected":
        action["status"] = "rejected"
        action["decision_comment"] = comment[:1000]
        state["pending_actions"] = [item for item in state["pending_actions"] if item.get("id") != action_id]
        await _save_state(identity["username"], state)
        return {"status": "rejected", "state": state}
    current_context = await build_context(identity, db)
    action_type = action.get("type")
    payload = action.get("payload") or {}
    if action_type == "create_task":
        from app.core.task_commands import create_task_record
        body = TaskInput(**payload)
        record = await create_task_record(body, identity, db)
        await db.commit()
        await db.refresh(record)
        result = _task_dict(record)
    elif action_type == "approve_contract":
        if int(payload.get("contract_id") or 0) not in {int(item["id"]) for item in current_context["pending_contract_approvals"]}:
            raise HTTPException(status_code=403, detail="合同审批权限或待办状态已变化")
        from app.areas.contract.router import approve_contract
        result = await approve_contract(int(payload["contract_id"]), ContractApprovalInput(approved=bool(payload.get("approved")), comment=str(payload.get("comment") or comment)[:1000]), identity, db)
        if not isinstance(result, dict):
            raise HTTPException(status_code=409, detail="合同审批未完成，请在合同审批页面查看具体原因")
    else:
        raise HTTPException(status_code=422, detail="不支持的待确认操作")
    state["pending_actions"] = [item for item in state["pending_actions"] if item.get("id") != action_id]
    state["messages"].append({"role": "assistant", "content": "操作已完成，系统数据已更新。", "created_at": _now()})
    state["messages"] = state["messages"][-100:]
    state["updated_at"] = _now()
    await _save_state(identity["username"], state)
    return {"status": "approved", "result": result, "state": state}
