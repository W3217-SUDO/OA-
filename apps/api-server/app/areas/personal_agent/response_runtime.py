"""个人助手的模型请求、响应模式和受控工具循环。"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Literal

from fastapi import HTTPException

from app.agent_mcp.model_tools import MODEL_TOOLS, ModelToolSession
from app.config import settings


ResponseMode = Literal["fast", "deep"]
ProgressCallback = Callable[[str], Awaitable[None]]


def supports_response_modes(active=None) -> bool:
    """当前模型是否支持快速/深度切换；active 为 DSH API 配置里当前使用的服务商，没传时按服务器配置。"""
    from app.harness_agent.model_providers import active_from_settings, supports_response_modes as supports
    return supports(active or active_from_settings())


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
    if identity is None or db is None or not workspace or not conversation:
        raise HTTPException(409, "Harness 缺少已认证的工作区会话，未创建共享会话")
    from app.cloud_agent.config import active as cloud_active
    if await cloud_active(db) is not None:
        if response_mode == "deep":
            raise HTTPException(status_code=422, detail="当前模型未启用回答模式切换")
        from app.harness_agent.runtime import run
        return await run(messages, on_delta, tools=tools, schema=MODEL_TOOLS if model_tools is None else model_tools,
                         identity=identity, db=db, workspace=workspace, conversation=conversation, on_progress=on_progress)
    from app.harness_agent.model_providers import active_model
    active = await active_model(db)
    if not active.configured:
        raise HTTPException(status_code=503, detail="个人智能体模型未配置")
    mode_supported = supports_response_modes(active)
    if response_mode == "deep" and not mode_supported:
        raise HTTPException(status_code=422, detail="当前模型未启用回答模式切换")
    if settings.agent_runtime_backend != "deepseek-harness":
        raise HTTPException(503, "旧智能体引擎已停用，请配置 deepseek-harness")
    from app.harness_agent.runtime import run

    return await run(messages, on_delta, tools=tools,
                     schema=MODEL_TOOLS if model_tools is None else model_tools,
                     identity=identity, db=db, workspace=workspace, conversation=conversation,
                     response_mode=response_mode, mode_supported=mode_supported, on_progress=on_progress)
