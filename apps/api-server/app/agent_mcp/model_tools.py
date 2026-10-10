from __future__ import annotations

import asyncio
import json
import re
from contextvars import ContextVar
from typing import Any, Awaitable, Callable

import httpx
from fastapi import HTTPException

from app.config import settings

from .auth import get_auth_context, tool_origin
from .catalog import ToolDefinition, get_catalog
from .service import call_tool, search_tools


MAX_TOOL_ROUNDS = 8
MAX_TOOL_CALLS = 24
TOOL_RESULT_SINK: ContextVar[list[dict[str, Any]] | None] = ContextVar("oa_model_tool_results", default=None)
MODEL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "oa_search_tools",
            "description": "搜索 OA 当前已注册的真实业务接口，返回匹配工具的完整参数 schema。调用前必须先搜索，不要猜名称或字段。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 1, "description": "用户要办理的具体业务，例如案件新增律师费用"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 12, "default": 8},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "oa_call_tool",
            "description": "调用本轮搜索发现的 OA 工具。arguments 严格对应其 inputSchema；查询立即执行，写操作仅生成待人工确认请求。此工具不能批准写入。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "arguments": {"type": "object", "description": "发现的业务工具 inputSchema 中规定的 path、query、body、files 参数"},
                },
                "required": ["name", "arguments"],
                "additionalProperties": False,
            },
        },
    },
]


class ModelToolSession:
    """仅在本轮模型请求内保留发现结果，不保存登录凭据。"""

    def __init__(self, case_id: int | None = None) -> None:
        self.case_id = case_id
        self.discovered: dict[str, ToolDefinition] = {}
        self.pending_actions: list[dict[str, Any]] = []
        self.structured_results: list[dict[str, Any]] = []
        self._prepared: dict[str, dict[str, Any]] = {}
        self._call_count = 0

    async def execute(self, name: str, arguments: object) -> dict[str, Any]:
        self._call_count += 1
        if self._call_count > MAX_TOOL_CALLS:
            raise RuntimeError("oa_tool_call_limit_exceeded")
        if not isinstance(arguments, dict):
            return {"isError": True, "detail": "工具参数必须为 JSON 对象"}
        try:
            async with asyncio.timeout(45):
                return await self._execute(name, arguments)
        except HTTPException as exc:
            return {"isError": True, "status_code": exc.status_code, "detail": exc.detail}
        except TimeoutError:
            return {"isError": True, "detail": "业务工具调用超时，未取得成功结果，请查询实际状态，不要重复提交写操作"}

    async def _execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "oa_search_tools":
            query = arguments.get("query")
            limit = arguments.get("limit", 8)
            if set(arguments) - {"query", "limit"} or not isinstance(query, str) or not query.strip():
                raise HTTPException(status_code=422, detail="搜索需要非空 query，且不能包含未知字段")
            if type(limit) is not int or not 1 <= limit <= 12:
                raise HTTPException(status_code=422, detail="limit 必须是 1 至 12 的整数")
            catalog = get_catalog(get_auth_context().application)
            tools = search_tools(query.strip(), limit=limit)
            self.discovered.update({tool["name"]: catalog.get(tool["name"]) for tool in tools})
            return {"tools": tools}
        if name != "oa_call_tool":
            raise HTTPException(status_code=422, detail="模型只能使用 OA 工具发现与受控调用")
        if set(arguments) != {"name", "arguments"} or not isinstance(arguments.get("name"), str):
            raise HTTPException(status_code=422, detail="调用参数只能包含 name 和 arguments")
        tool = self.discovered.get(arguments["name"])
        if tool is None:
            raise HTTPException(status_code=422, detail="必须先搜索并读取该工具的完整 schema，再调用")
        tool.validate_arguments(arguments["arguments"])
        call_key = json.dumps([tool.name, arguments["arguments"]], ensure_ascii=False, sort_keys=True)
        if call_key in self._prepared:
            return {"result": self._prepared[call_key]}
        if self.case_id is None:
            result = await call_tool(tool.name, arguments["arguments"])
        else:
            with tool_origin(self.case_id):
                result = await call_tool(tool.name, arguments["arguments"])
        if isinstance(result, dict) and result.get("status") == "pending":
            request_id = result.get("request_id")
            preview = result.get("preview")
            if not isinstance(request_id, str) or not request_id or not isinstance(preview, dict):
                raise RuntimeError("oa_pending_request_invalid")
            self.pending_actions.append({
                "type": "mcp.call",
                "summary": str(result["summary"]),
                "payload": {"request_id": request_id},
                "preview": preview,
            })
            self._prepared[call_key] = result
        self._collect_resources(result)
        return {"result": result}

    def _collect_resources(self, value: object) -> None:
        if isinstance(value, list):
            for item in value:
                self._collect_resources(item)
        elif isinstance(value, dict):
            uri = value.get("uri")
            match = re.fullmatch(r"oa-mcp-(artifact|source)://([0-9a-f]{32})", uri) if isinstance(uri, str) else None
            controlled = False
            if value.get("type") == "resource_link" and match:
                kind, identifier = match.groups()
                id_field = "artifact_id" if kind == "artifact" else "resource_id"
                collection = "artifacts" if kind == "artifact" else "resources"
                controlled = (
                    value.get(id_field) == identifier
                    and value.get("download_url") == settings.api_prefix + f"/agent-tools/{collection}/{identifier}"
                )
            if controlled:
                self.structured_results.append(value)
                sink = TOOL_RESULT_SINK.get()
                if sink is not None:
                    sink.append(value)
            else:
                for item in value.values():
                    self._collect_resources(item)

    async def execute_calls(self, calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(calls) > MAX_TOOL_CALLS - self._call_count:
            raise RuntimeError("oa_tool_call_limit_exceeded")
        call_ids = [call.get("id") for call in calls]
        if any(not isinstance(value, str) or not value for value in call_ids) or len(set(call_ids)) != len(call_ids):
            raise RuntimeError("model_tool_call_invalid")
        results = []
        for call in calls:
            function = call.get("function") or {}
            try:
                arguments = json.loads(function.get("arguments") or "{}")
            except (ValueError, TypeError):
                result = {"isError": True, "detail": "工具 arguments 不是合法 JSON，请按照已发现的 schema 修正"}
            else:
                result = await self.execute(str(function.get("name") or ""), arguments)
            results.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(result, ensure_ascii=False, default=str),
            })
        return results


async def _request_non_stream_completion(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    on_delta: Callable[[str], Awaitable[None]] | None,
) -> dict[str, Any]:
    response = await client.post(url, headers=headers, json={**payload, "stream": False})
    if response.is_error:
        raise RuntimeError(f"model_http_{response.status_code}")
    result = response.json()["choices"][0]
    if result.get("finish_reason") in {"length", "content_filter"}:
        raise RuntimeError("model_response_incomplete")
    message = result["message"]
    if on_delta:
        visible = _visible_content(str(message.get("content") or ""))
        for offset in range(0, len(visible), 24):
            await on_delta(visible[offset:offset + 24])
            await asyncio.sleep(0)
    return message


async def request_completion(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    *,
    stream: bool,
    on_delta: Callable[[str], Awaitable[None]] | None = None,
    on_stream_support: Callable[[bool], None] | None = None,
) -> dict[str, Any]:
    if not stream:
        return await _request_non_stream_completion(client, url, headers, payload, on_delta)
    parts: list[str] = []
    reasoning_parts: list[str] = []
    calls: dict[int, dict[str, Any]] = {}
    finished = False
    emitted = 0
    async with client.stream("POST", url, headers=headers, json={**payload, "stream": True}) as response:
        if response.is_error:
            if response.status_code not in {400, 404, 405, 415, 422, 501}:
                raise RuntimeError(f"model_http_{response.status_code}")
            if on_stream_support:
                on_stream_support(False)
        else:
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if raw == "[DONE]":
                    finished = True
                    break
                if not raw:
                    continue
                event = json.loads(raw)
                if event.get("error"):
                    raise RuntimeError("model_stream_error")
                choices = event.get("choices") or []
                if not choices:
                    continue
                choice = choices[0]
                delta = choice.get("delta") or {}
                if delta.get("reasoning_content"):
                    reasoning_parts.append(str(delta["reasoning_content"]))
                if delta.get("content"):
                    parts.append(str(delta["content"]))
                    if on_delta:
                        visible = _visible_content("".join(parts))
                        if len(visible) > emitted:
                            await on_delta(visible[emitted:])
                            emitted = len(visible)
                for fragment in delta.get("tool_calls") or []:
                    index = fragment["index"]
                    call = calls.setdefault(index, {"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                    if fragment.get("id"):
                        call["id"] += fragment["id"]
                    function = fragment.get("function") or {}
                    call["function"]["name"] += str(function.get("name") or "")
                    call["function"]["arguments"] += str(function.get("arguments") or "")
                reason = choice.get("finish_reason")
                if reason in {"length", "content_filter"}:
                    raise RuntimeError("model_response_incomplete")
                if reason is not None:
                    finished = True
                    break
    if response.is_error:
        # 保留已有 provider 的非流式协议兼容；真实请求错误仍由第二次响应明确抛出。
        return await _request_non_stream_completion(client, url, headers, payload, on_delta)
    if not finished:
        raise RuntimeError("model_stream_incomplete")
    if on_stream_support:
        on_stream_support(True)
    result: dict[str, Any] = {"role": "assistant", "content": "".join(parts)}
    if reasoning_parts:
        result["reasoning_content"] = "".join(reasoning_parts)
    if calls:
        result["tool_calls"] = [calls[index] for index in sorted(calls)]
    return result


def _visible_content(content: str) -> str:
    # 暂存尚未收齐的动作标签，避免流分片把内部参数暴露为普通答复。
    end = len(content)
    for marker in ("<proposed_action>", "<personal_action>"):
        position = content.find(marker)
        if position >= 0:
            end = min(end, position)
        for size in range(1, min(len(marker), len(content)) + 1):
            if content.endswith(marker[:size]):
                end = min(end, len(content) - size)
    return content[:end]
