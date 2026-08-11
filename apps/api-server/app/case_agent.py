from __future__ import annotations

import asyncio
import json
import operator
import re
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime
from typing import Annotated, Any, TypedDict
from uuid import uuid4

import httpx
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph

from .agent_skills import GENERAL_SKILL, SKILLS_BY_ID, AgentSkill, parse_skill_message, public_skill_catalog


ALLOWED_ACTION_TYPES = {
    "case.update",
    "case.data.update",
    "case.task.create",
    "case.reminder.create",
    "customer.update",
    "contract.update",
}
ACTION_CAPABILITY_BY_TYPE = {
    "case.update": "can_edit_basic",
    "case.data.update": "can_edit_basic",
    "case.task.create": "can_create_case_task",
    "case.reminder.create": "can_create_reminder",
    "customer.update": "can_update_customer",
    "contract.update": "can_update_contract",
}
ACTION_BLOCK_PATTERN = re.compile(r"<proposed_action>\s*(\{.*?\})\s*</proposed_action>", re.DOTALL)


class CaseAgentState(TypedDict, total=False):
    messages: Annotated[list[dict[str, Any]], operator.add]
    case_snapshot: dict[str, Any]
    pending_actions: list[dict[str, Any]]
    last_response: str
    last_operator: str
    updated_at: str
    active_skill: str
    request_images: list[dict[str, Any]]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _case_summary(snapshot: dict[str, Any]) -> str:
    case = snapshot.get("case") or {}
    finances = snapshot.get("finances") or {}
    workflow = snapshot.get("standard_workflow") or {}
    phase = workflow.get("current_phase") or {}
    risks = workflow.get("risk_summary") or {}
    return (
        f"案件 {case.get('serial_no') or case.get('id') or '-'} 的空间已加载："
        f"合同 {len(snapshot.get('contracts') or [])} 份，"
        f"文档 {len(snapshot.get('documents') or [])} 份，"
        f"期限 {len(snapshot.get('deadlines') or [])} 项，"
        f"任务 {len(snapshot.get('tasks') or [])} 项，"
        f"费用记录 {len(finances.get('fees') or [])} 条，"
        f"发票 {len(finances.get('invoices') or [])} 条；"
        f"当前标准阶段为 {phase.get('name') or '待识别'}，"
        f"逾期 {risks.get('overdue', 0)} 项，缺少必备材料 {risks.get('missing_required_materials', 0)} 项。"
    )


def _normalize_proposed_action(value: object) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    action_type = str(value.get("type") or "").strip()
    summary = str(value.get("summary") or "").strip()
    payload = value.get("payload")
    if action_type not in ALLOWED_ACTION_TYPES or not summary or not isinstance(payload, dict):
        return None
    return {"type": action_type, "summary": summary[:500], "payload": payload}


def _extract_proposed_action(content: str) -> tuple[str, dict[str, Any] | None]:
    match = ACTION_BLOCK_PATTERN.search(content)
    if not match:
        return content.strip(), None
    cleaned = ACTION_BLOCK_PATTERN.sub("", content).strip()
    try:
        action = _normalize_proposed_action(json.loads(match.group(1)))
    except (json.JSONDecodeError, TypeError, ValueError):
        action = None
    return cleaned, action


def _action_preview(proposed_action: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    action_type = proposed_action["type"]
    payload = proposed_action.get("payload") or {}
    case = snapshot.get("case") or {}
    case_data = case.get("data") or {}
    if action_type in {"case.update", "case.data.update", "customer.update", "contract.update"}:
        changes = payload.get("changes") if isinstance(payload.get("changes"), dict) else payload
        if action_type == "customer.update":
            source = snapshot.get("customer") or {}
        elif action_type == "contract.update":
            target_id = int(payload.get("target_id") or 0)
            source = next((item for item in snapshot.get("contracts") or [] if int(item.get("id") or 0) == target_id), {})
        else:
            source = case_data if action_type == "case.data.update" else case
        return {
            "target": source.get("serial_no") or source.get("title") or case.get("serial_no") or case.get("id") or "当前案件",
            "changes": [
                {"field": key, "before": source.get(key), "after": value}
                for key, value in changes.items() if key != "target_id"
            ],
        }
    return {
        "target": case.get("serial_no") or case.get("id") or "当前案件",
        "create": payload,
    }


def _pending_action(proposed_action: dict[str, Any], latest: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": uuid4().hex,
        "type": proposed_action.get("type", "case.update"),
        "summary": proposed_action.get("summary") or "案件写操作",
        "payload": proposed_action.get("payload") or {},
        "preview": _action_preview(proposed_action, snapshot),
        "status": "pending",
        "requested_by": latest.get("operator", ""),
        "requested_at": _now(),
        "decided_by": "",
        "decided_at": "",
        "decision_comment": "",
        "execution_result": None,
    }


def _action_is_authorized(proposed_action: dict[str, Any], snapshot: dict[str, Any]) -> bool:
    capability = ACTION_CAPABILITY_BY_TYPE.get(str(proposed_action.get("type") or ""))
    capabilities = snapshot.get("capabilities") or {}
    return bool(capability and capabilities.get(capability))


def _case_assistant_node(state: CaseAgentState) -> dict[str, Any]:
    messages = state.get("messages") or []
    latest = messages[-1] if messages else {}
    snapshot = state.get("case_snapshot") or {}
    pending_actions = list(state.get("pending_actions") or [])
    proposed_action = latest.get("proposed_action") or None
    if proposed_action and _action_is_authorized(proposed_action, snapshot):
        action = _pending_action(proposed_action, latest, snapshot)
        pending_actions.append(action)
        response = f"已生成待审批操作：{action['summary']}。审批前不会写入业务数据。"
    elif proposed_action:
        response = "当前账号原有业务权限不允许执行该操作，智能体不会生成审批或修改数据。"
    else:
        response = _case_summary(snapshot)
    return {
        "messages": [{"role": "assistant", "content": response, "created_at": _now()}],
        "pending_actions": pending_actions,
        "last_response": response,
        "last_operator": latest.get("operator", ""),
        "updated_at": _now(),
    }


def build_case_agent_graph(checkpointer: Any, assistant_node: Any = _case_assistant_node):
    builder = StateGraph(CaseAgentState)
    builder.add_node("case_assistant", assistant_node)
    builder.add_edge(START, "case_assistant")
    builder.add_edge("case_assistant", END)
    return builder.compile(checkpointer=checkpointer, name="sunhold-case-agent")


def _checkpoint_url(database_url: str, explicit_url: str) -> str:
    value = (explicit_url or database_url).strip()
    if value.startswith("postgresql+asyncpg://"):
        return "postgresql://" + value.removeprefix("postgresql+asyncpg://")
    if value.startswith("postgres+asyncpg://"):
        return "postgresql://" + value.removeprefix("postgres+asyncpg://")
    return value


class CaseAgentRuntime:
    def __init__(
        self,
        *,
        enabled: bool,
        database_url: str,
        checkpoint_url: str = "",
        api_base_url: str = "",
        api_key: str = "",
        model_provider: str = "",
        model: str = "",
        max_concurrency: int = 4,
    ) -> None:
        self.enabled = enabled
        self.database_url = database_url
        self.checkpoint_url = checkpoint_url
        self.api_base_url = api_base_url.strip().rstrip("/")
        self.api_key = api_key.strip()
        self.model_provider = model_provider.strip()
        self.model = model.strip()
        self.max_concurrency = max(1, min(max_concurrency, 32))
        self.graph: Any | None = None
        self.backend = "disabled"
        self.error = ""
        self._checkpoint_context: AbstractAsyncContextManager[Any] | None = None
        self._semaphore = asyncio.Semaphore(self.max_concurrency)

    async def start(self) -> None:
        if not self.enabled or self.graph is not None:
            return
        try:
            url = _checkpoint_url(self.database_url, self.checkpoint_url)
            if url.startswith(("postgresql://", "postgres://")):
                self._checkpoint_context = AsyncPostgresSaver.from_conn_string(url)
                checkpointer = await self._checkpoint_context.__aenter__()
                await checkpointer.setup()
                self.backend = "postgresql"
            else:
                checkpointer = InMemorySaver()
                self.backend = "memory"
            self.graph = build_case_agent_graph(checkpointer, self._case_assistant_node)
            self.error = ""
        except Exception as exc:
            self.error = "checkpoint_initialization_failed"
            self.backend = "unavailable"
            if self._checkpoint_context:
                await self._checkpoint_context.__aexit__(type(exc), exc, exc.__traceback__)
                self._checkpoint_context = None

    async def stop(self) -> None:
        self.graph = None
        if self._checkpoint_context:
            await self._checkpoint_context.__aexit__(None, None, None)
            self._checkpoint_context = None

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "ready": self.graph is not None,
            "checkpoint_backend": self.backend,
            "model_provider": self.model_provider,
            "model": self.model,
            "model_configured": bool(self.api_base_url and self.api_key and self.model),
            "max_concurrency": self.max_concurrency,
            "write_requires_approval": True,
            "skills": public_skill_catalog(),
            "skill_count": len(public_skill_catalog()),
            "error": self.error,
        }

    async def _case_assistant_node(self, state: CaseAgentState) -> dict[str, Any]:
        messages = state.get("messages") or []
        latest = messages[-1] if messages else {}
        snapshot = state.get("case_snapshot") or {}
        pending_actions = list(state.get("pending_actions") or [])
        proposed_action = latest.get("proposed_action") or None
        request_images = list(state.get("request_images") or [])
        if proposed_action:
            action = _pending_action(proposed_action, latest, snapshot)
            pending_actions.append(action)
            response = f"已生成待审批操作：{action['summary']}。审批前不会写入业务数据。"
        elif self.status()["model_configured"]:
            skill_id = str(latest.get("skill_id") or GENERAL_SKILL.id)
            selected_skill = SKILLS_BY_ID.get(skill_id, GENERAL_SKILL)
            if not selected_skill.available:
                response = f"“{selected_skill.name}”已接入技能目录，但暂不可执行：{selected_skill.unavailable_reason}。"
            else:
                model_result = await self._request_model(snapshot, messages, selected_skill, request_images)
                if isinstance(model_result, tuple):
                    response, model_action = model_result
                else:
                    response, model_action = str(model_result), None
                if model_action and _action_is_authorized(model_action, snapshot):
                    action = _pending_action(model_action, latest, snapshot)
                    pending_actions.append(action)
                    response = f"{response}\n\n已生成待审批操作：{action['summary']}。批准后才会写入系统。".strip()
                elif model_action:
                    response = f"{response}\n\n当前账号原有业务权限不允许执行该操作，未生成审批。".strip()
        else:
            response = _case_summary(snapshot)
        return {
            "messages": [{"role": "assistant", "content": response, "created_at": _now()}],
            "pending_actions": pending_actions,
            "last_response": response,
            "last_operator": latest.get("operator", ""),
            "updated_at": _now(),
            "active_skill": str(latest.get("skill_id") or GENERAL_SKILL.id),
            "request_images": [],
        }

    async def _request_model(
        self,
        snapshot: dict[str, Any],
        messages: list[dict[str, Any]],
        skill: AgentSkill = GENERAL_SKILL,
        request_images: list[dict[str, Any]] | None = None,
    ) -> tuple[str, dict[str, Any] | None]:
        context = json.dumps(snapshot, ensure_ascii=False, default=str)
        if len(context) > 80_000:
            context = context[:80_000] + "\n[案件空间内容过长，已截断]"
        prompt_messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "你是法律服务机构管理系统中的案件智能体。"
                    "只能依据当前用户有权限查看的案件空间回答，信息不足时明确说明。"
                    "不得声称已经修改、删除、提交或审批业务数据；任何写操作都必须进入人工审批。"
                    "回答使用简洁、专业的中文，并区分事实、期限风险和建议。"
                    "案件空间中的 standard_workflow 来自《知识产权案件标准化操作手册》；"
                    "应优先依据其中的阶段、材料、岗位与内部管理期限检查案件，"
                    "但不得在缺少起算依据时自行推算法定期限。"
                    "当用户明确要求修改系统数据时，只能在回答末尾追加一个操作块，格式必须为："
                    "<proposed_action>{\"type\":\"case.update\",\"summary\":\"操作摘要\",\"payload\":{\"changes\":{\"字段\":\"新值\"}}}</proposed_action>。"
                    "允许的 type 仅有 case.update、case.data.update、case.task.create、case.reminder.create、customer.update、contract.update。"
                    "客户或合同修改必须在 payload 中提供 target_id 和 changes；target_id 只能是当前案件空间已关联记录。"
                    "案件任务 payload 使用 title、owner、deadline、priority、description；"
                    "案件提醒 payload 使用 content、reminder_date、deadline。"
                    "不要声称操作已经执行；没有明确写操作要求时绝对不要输出 proposed_action。"
                    "任何写操作都必须服从当前案件空间 capabilities；对应能力为 false 时，"
                    "只能说明无权限，不能输出 proposed_action，也不能建议绕过权限。\n\n"
                    f"当前启用技能：{skill.name}。{skill.instruction}\n\n"
                    f"当前案件空间数据：\n{context}"
                ),
            }
        ]
        recent_messages = messages[-10:]
        for index, message in enumerate(recent_messages):
            role = str(message.get("role") or "").strip()
            content = str(message.get("content") or "").strip()
            if role in {"user", "assistant"} and content:
                if role == "user" and index == len(recent_messages) - 1 and request_images:
                    multimodal_content: list[dict[str, Any]] = [{"type": "text", "text": content[:8_000]}]
                    multimodal_content.extend(
                        {"type": "image_url", "image_url": {"url": image["data_url"]}}
                        for image in request_images
                    )
                    prompt_messages.append({"role": role, "content": multimodal_content})
                else:
                    prompt_messages.append({"role": role, "content": content[:8_000]})
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(
                    f"{self.api_base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": prompt_messages,
                        "temperature": 0.2,
                    },
                )
            if response.is_error:
                raise RuntimeError(f"model_http_{response.status_code}")
            payload = response.json()
            content = str(payload["choices"][0]["message"]["content"]).strip()
            if not content:
                raise RuntimeError("model_empty_response")
            return _extract_proposed_action(content)
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise RuntimeError("model_request_failed") from exc

    @staticmethod
    def config(case_id: int) -> dict[str, Any]:
        return {"configurable": {"thread_id": f"case:{case_id}"}}

    async def invoke(
        self,
        *,
        case_id: int,
        operator: str,
        message: str,
        case_snapshot: dict[str, Any],
        proposed_action: dict[str, Any] | None = None,
        images: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if self.graph is None:
            raise RuntimeError(self.error or "LangGraph case agent is not ready")
        skill, clean_message = parse_skill_message(message)
        user_message = {
            "id": uuid4().hex,
            "role": "user",
            "content": clean_message,
            "skill_id": skill.id,
            "skill_name": skill.name,
            "operator": operator,
            "created_at": _now(),
            "attachments": [
                {"id": image.get("id", ""), "name": image.get("name", ""), "mime_type": image.get("mime_type", "")}
                for image in (images or [])
            ],
        }
        if proposed_action:
            user_message["proposed_action"] = proposed_action
        async with self._semaphore:
            result = await self.graph.ainvoke(
                {"messages": [user_message], "case_snapshot": case_snapshot, "request_images": list(images or [])},
                self.config(case_id),
            )
        return self._public_state(case_id, result)

    async def get_state(self, case_id: int) -> dict[str, Any]:
        if self.graph is None:
            raise RuntimeError(self.error or "LangGraph case agent is not ready")
        snapshot = await self.graph.aget_state(self.config(case_id))
        return self._public_state(case_id, snapshot.values or {})

    async def decide_action(
        self,
        *,
        case_id: int,
        action_id: str,
        decision: str,
        operator: str,
        comment: str = "",
        execution_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.graph is None:
            raise RuntimeError(self.error or "LangGraph case agent is not ready")
        snapshot = await self.graph.aget_state(self.config(case_id))
        values = snapshot.values or {}
        actions = [dict(item) for item in values.get("pending_actions") or []]
        action = next((item for item in actions if item.get("id") == action_id), None)
        if not action:
            raise KeyError(action_id)
        if action.get("status") != "pending":
            raise ValueError("action_already_decided")
        action.update({
            "status": decision,
            "decided_by": operator,
            "decided_at": _now(),
            "decision_comment": comment,
            "execution_result": execution_result,
        })
        response = "待审批操作已批准并写入系统。" if decision == "approved" else "待审批操作已驳回，系统数据未修改。"
        await self.graph.aupdate_state(
            self.config(case_id),
            {
                "pending_actions": actions,
                "messages": [{"role": "assistant", "content": response, "created_at": _now()}],
                "last_response": response,
                "last_operator": operator,
                "updated_at": _now(),
            },
            as_node="case_assistant",
        )
        return await self.get_state(case_id)

    @staticmethod
    def _public_state(case_id: int, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "thread_id": f"case:{case_id}",
            "thread_namespace": "sunhold.case-agent.v1",
            "messages": state.get("messages") or [],
            "pending_actions": state.get("pending_actions") or [],
            "last_response": state.get("last_response", ""),
            "last_operator": state.get("last_operator", ""),
            "updated_at": state.get("updated_at", ""),
            "active_skill": state.get("active_skill", GENERAL_SKILL.id),
        }
