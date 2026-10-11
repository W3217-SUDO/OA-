"""工具预算用尽后，仅依据已有真实结果生成最终答复。"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

import httpx

from app.core.constants import logger

from .model_tools import MAX_TOOL_CALLS, ModelToolSession, request_completion


FINAL_ANSWER_RULES = (
    "本轮工具调用预算已用尽，不能再调用工具。请读取已经返回的真实工具结果并直接回答。"
    "统计值必须来自满足用户筛选条件和权限范围的完整统计，不得把摘要、最近记录或分页样本当成全量结果。"
    "如果已有结果不足以回答，应明确说明查询尚未完成，并指出缺少的证据，不能编造数值或宣称查询成功。"
    "写操作只能说明已返回的待人工确认请求，不得宣称尚未确认的操作已经执行。"
)


async def request_final_answer(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    *,
    tools: ModelToolSession,
    entry: str,
    tool_rounds: int,
    stream: bool,
    on_delta: Callable[[str], Awaitable[None]] | None = None,
    on_stream_support: Callable[[bool], None] | None = None,
) -> dict[str, Any]:
    # 只记录固定入口与预算数字，不记录用户问题、工具参数或业务结果。
    logger.warning(
        "agent_tool_budget_reached entry=%s rounds=%s calls=%s",
        entry, tool_rounds, MAX_TOOL_CALLS - tools.remaining_calls,
    )
    result = await request_completion(
        client, url, headers,
        {
            **payload,
            "messages": [*payload["messages"], {"role": "system", "content": FINAL_ANSWER_RULES}],
            "tool_choice": "none",
        },
        stream=stream,
        on_delta=on_delta,
        on_stream_support=on_stream_support,
    )
    if result.get("tool_calls"):
        logger.warning("agent_final_answer_tool_violation entry=%s rounds=%s", entry, tool_rounds)
        raise RuntimeError("oa_tool_final_answer_violation")
    if not str(result.get("content") or "").strip():
        raise RuntimeError("model_empty_response")
    return result
