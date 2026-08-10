from __future__ import annotations

import asyncio
import operator
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime
from typing import Annotated, Any, TypedDict
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph


class CaseAgentState(TypedDict, total=False):
    messages: Annotated[list[dict[str, Any]], operator.add]
    case_snapshot: dict[str, Any]
    pending_actions: list[dict[str, Any]]
    last_response: str
    last_operator: str
    updated_at: str


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _case_summary(snapshot: dict[str, Any]) -> str:
    case = snapshot.get("case") or {}
    finances = snapshot.get("finances") or {}
    return (
        f"案件 {case.get('serial_no') or case.get('id') or '-'} 的空间已加载："
        f"合同 {len(snapshot.get('contracts') or [])} 份，"
        f"文档 {len(snapshot.get('documents') or [])} 份，"
        f"期限 {len(snapshot.get('deadlines') or [])} 项，"
        f"任务 {len(snapshot.get('tasks') or [])} 项，"
        f"费用记录 {len(finances.get('fees') or [])} 条，"
        f"发票 {len(finances.get('invoices') or [])} 条。"
    )


def _case_assistant_node(state: CaseAgentState) -> dict[str, Any]:
    messages = state.get("messages") or []
    latest = messages[-1] if messages else {}
    snapshot = state.get("case_snapshot") or {}
    pending_actions = list(state.get("pending_actions") or [])
    proposed_action = latest.get("proposed_action") or None
    if proposed_action:
        action = {
            "id": uuid4().hex,
            "type": proposed_action.get("type", "case.update"),
            "summary": proposed_action.get("summary") or "案件写操作",
            "payload": proposed_action.get("payload") or {},
            "status": "pending",
            "requested_by": latest.get("operator", ""),
            "requested_at": _now(),
            "decided_by": "",
            "decided_at": "",
            "decision_comment": "",
        }
        pending_actions.append(action)
        response = f"已生成待审批操作：{action['summary']}。审批前不会写入业务数据。"
    else:
        response = _case_summary(snapshot)
    return {
        "messages": [{"role": "assistant", "content": response, "created_at": _now()}],
        "pending_actions": pending_actions,
        "last_response": response,
        "last_operator": latest.get("operator", ""),
        "updated_at": _now(),
    }


def build_case_agent_graph(checkpointer: Any):
    builder = StateGraph(CaseAgentState)
    builder.add_node("case_assistant", _case_assistant_node)
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
        model_provider: str = "",
        model: str = "",
        max_concurrency: int = 4,
    ) -> None:
        self.enabled = enabled
        self.database_url = database_url
        self.checkpoint_url = checkpoint_url
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
            self.graph = build_case_agent_graph(checkpointer)
            self.error = ""
        except Exception as exc:
            self.error = str(exc)
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
            "model_configured": bool(self.model_provider and self.model),
            "max_concurrency": self.max_concurrency,
            "write_requires_approval": True,
            "error": self.error,
        }

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
    ) -> dict[str, Any]:
        if self.graph is None:
            raise RuntimeError(self.error or "LangGraph case agent is not ready")
        user_message = {
            "id": uuid4().hex,
            "role": "user",
            "content": message,
            "operator": operator,
            "created_at": _now(),
        }
        if proposed_action:
            user_message["proposed_action"] = proposed_action
        async with self._semaphore:
            result = await self.graph.ainvoke(
                {"messages": [user_message], "case_snapshot": case_snapshot},
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
        })
        response = "待审批操作已批准。" if decision == "approved" else "待审批操作已驳回。"
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
        }
