"""个人助手的模型请求、响应模式和受控工具循环。"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Literal
from time import perf_counter
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException

from app.agent_mcp.model_tools import MAX_TOOL_ROUNDS, MODEL_TOOLS, ModelToolSession, request_completion
from app.config import settings
from app.core.constants import logger
from app.core.request_metrics import measure_phase


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
) -> str:
    if not (settings.langgraph_api_base_url and settings.langgraph_api_key and settings.langgraph_model):
        raise HTTPException(status_code=503, detail="个人智能体模型未配置")
    mode_supported = supports_response_modes()
    if response_mode == "deep" and not mode_supported:
        raise HTTPException(status_code=422, detail="当前模型未启用回答模式切换")
    payload = {"model": settings.langgraph_model, "messages": messages, "temperature": 0.2, "tools": MODEL_TOOLS}
    if mode_supported:
        payload["thinking"] = {"type": "disabled" if response_mode == "fast" else "enabled"}
    try:
        async with asyncio.timeout(180), httpx.AsyncClient(timeout=90, trust_env=False) as client:
            for round_index in range(MAX_TOOL_ROUNDS):
                if on_progress:
                    await on_progress("正在深入分析…" if mode_supported and response_mode == "deep" else "正在生成回答…")
                started = perf_counter()
                first_output_ms: float | None = None

                async def emit_delta(content: str) -> None:
                    nonlocal first_output_ms
                    if content and first_output_ms is None:
                        first_output_ms = round((perf_counter() - started) * 1000, 1)
                    await on_delta(content)

                with measure_phase("personal_agent.model"):
                    result = await request_completion(
                        client, f"{settings.langgraph_api_base_url.rstrip('/')}/chat/completions",
                        {"Authorization": f"Bearer {settings.langgraph_api_key}"},
                        payload, stream=True, on_delta=emit_delta,
                    )
                calls = result.get("tool_calls") or []
                # 只记录耗时和数量，不记录提示词、业务数据、推理内容或凭据。
                logger.info(
                    "personal_agent_model round=%s mode=%s total_ms=%.1f first_output_ms=%s tool_calls=%s",
                    round_index + 1, response_mode if mode_supported else "provider_default",
                    (perf_counter() - started) * 1000, first_output_ms, len(calls),
                )
                if calls:
                    messages.append({**result, "role": "assistant"})
                    if on_progress:
                        await on_progress("正在调用办公工具…")
                    with measure_phase("personal_agent.tools"):
                        messages.extend(await tools.execute_calls(calls))
                    continue
                content = str(result.get("content") or "").strip()
                if not content:
                    raise RuntimeError("model_empty_response")
                return content
            raise RuntimeError("oa_tool_round_limit_exceeded")
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail="个人智能体本轮处理超时，未取得完成结果") from exc
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail=f"个人智能体本轮处理失败：{exc}") from exc
