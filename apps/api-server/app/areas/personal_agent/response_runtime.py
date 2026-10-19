"""个人助手的模型请求、响应模式和受控工具循环。"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Literal
from urllib.parse import urlsplit

from fastapi import HTTPException

from app.agent_mcp.model_tools import MODEL_TOOLS, ModelToolSession
from app.config import settings


ResponseMode = Literal["fast", "deep"]
ProgressCallback = Callable[[str], Awaitable[None]]


def supports_response_modes() -> bool:
    # 仅向已经确认支持 thinking 的方舟模型传参，不影响其他 OpenAI 兼容服务。
    host = urlsplit(settings.langgraph_api_base_url).hostname or ""
    return host.startswith("ark.") and host.endswith(".volces.com") and settings.langgraph_model == "ark-code-latest"


async def request_model(
    messages: list[dict[str, Any]],
    on_delta: Callable[[str], Awaitable[None]],
    *,
    tools: ModelToolSession,
    response_mode: ResponseMode = "fast",
    on_progress: ProgressCallback | None = None,
    model_tools: list[dict[str, Any]] | None = None,
    identity: dict[str, Any] | None = None,
    db: Any = None,
    workspace: str = "",
    conversation: str = "",
) -> str:
    if not (settings.langgraph_api_base_url and settings.langgraph_api_key and settings.langgraph_model):
        raise HTTPException(status_code=503, detail="个人智能体模型未配置")
    mode_supported = supports_response_modes()
    if response_mode == "deep" and not mode_supported:
        raise HTTPException(status_code=422, detail="当前模型未启用回答模式切换")
    if settings.agent_runtime_backend != "deepseek-harness":
        raise HTTPException(503, "旧智能体引擎已停用，请配置 deepseek-harness")
    from app.harness_agent.runtime import run

    if identity is None or db is None or not workspace or not conversation:
        raise HTTPException(409, "Harness 缺少已认证的工作区会话，未创建共享会话")
    return await run(messages, on_delta, tools=tools,
                     schema=MODEL_TOOLS if model_tools is None else model_tools,
                     identity=identity, db=db, workspace=workspace, conversation=conversation,
                     response_mode=response_mode, mode_supported=mode_supported, on_progress=on_progress)
