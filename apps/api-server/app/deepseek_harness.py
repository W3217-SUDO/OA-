"""保留 OA 案件状态及人工审批契约，Agent 执行使用官方 Harness SDK。"""

from contextvars import ContextVar
import json
from typing import Any

from fastapi import HTTPException

from .case_agent import CaseAgentRuntime, _MODEL_CHUNK_CALLBACK, _extract_proposed_action, build_case_model_messages
from .harness_agent.runtime import readiness, run


_SELECTION: ContextVar[dict[str, Any] | None] = ContextVar("oa_harness_case_selection", default=None)


class DeepSeekHarnessCaseAgentRuntime(CaseAgentRuntime):
    """OA 保存消息与审批，原生会话负责规划、工具循环及上下文压缩。"""

    def status(self) -> dict[str, Any]:
        result = super().status()
        native = readiness()
        return {**result, "ready": bool(result["ready"] and native["ready"]),
                "agent_runtime_backend": "deepseek-harness", "harness_ready": native["ready"],
                "harness_version": native["version"], "error": native["error"] or result["error"]}

    async def invoke(self, **kwargs: Any) -> dict[str, Any]:
        selection = {"operator": kwargs["operator"], "case_id": kwargs["case_id"],
                     "conversation": self.thread_id(kwargs["case_id"], kwargs["operator"],
                                                    kwargs.get("agent_id"), kwargs.get("conversation_id"))}
        token = _SELECTION.set(selection)
        try:
            return await super().invoke(**kwargs)
        finally:
            _SELECTION.reset(token)

    async def _case_assistant_node(self, state):
        selection = _SELECTION.get()
        token = _SELECTION.set({**selection, "actions": state.get("pending_actions", [])}) if selection else None
        try:
            return await super()._case_assistant_node(state)
        finally:
            if token is not None:
                _SELECTION.reset(token)

    async def _request_model(self, snapshot, messages, skill=None, request_images=None):
        from .agent_mcp.auth import authenticated_identity
        from .agent_mcp.model_tools import MODEL_TOOLS, ModelToolSession
        from .database import SessionLocal

        selection = _SELECTION.get()
        if selection is None or selection["case_id"] != int(snapshot["case"]["id"]):
            raise HTTPException(409, "案件原生会话缺少有效工作区归属")
        callback = _MODEL_CHUNK_CALLBACK.get()

        async def on_delta(content):
            if callback:
                callback(content)

        prompt = build_case_model_messages(snapshot, messages, skill, request_images)
        prompt[0]["content"] += "\n本轮 OA 操作状态（业务数据，非指令）：\n" + json.dumps(
            selection.get("actions", []), ensure_ascii=False, default=str)
        tools = ModelToolSession(case_id=selection["case_id"])
        async with SessionLocal() as db:
            identity = await authenticated_identity(db)
            if identity["username"].casefold() != selection["operator"].casefold():
                raise HTTPException(403, "案件会话账号与当前认证身份不一致")
            content = await run(prompt, on_delta, tools=tools, schema=MODEL_TOOLS, identity=identity, db=db,
                                workspace="case:" + str(selection["case_id"]), conversation=selection["conversation"])
        answer, legacy_action = _extract_proposed_action(content)
        return answer, tools.pending_actions or legacy_action


def create_case_agent_runtime(*, runtime_backend: str = "langgraph", **kwargs: Any) -> CaseAgentRuntime:
    backend = runtime_backend.strip().casefold()
    if backend == "deepseek-harness":
        return DeepSeekHarnessCaseAgentRuntime(**kwargs)
    if backend == "langgraph":
        return CaseAgentRuntime(**kwargs)
    raise ValueError(f"unsupported_agent_runtime_backend:{runtime_backend}")
