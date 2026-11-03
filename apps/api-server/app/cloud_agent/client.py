"""火山方舟 Managed Agents 接口：普通请求和会话事件流（SSE）。只用 Bearer 方舟 API Key，Key 不写日志。"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import httpx

from .config import BASE_URL


class ArkError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(f"{status} {code}: {message}")
        self.status, self.code, self.message = status, code, message


def _error(response: httpx.Response) -> ArkError:
    try:
        detail = response.json().get("error") or {}
    except (ValueError, AttributeError):
        detail = {}
    return ArkError(response.status_code, str(detail.get("code") or ""), str(detail.get("message") or "")[:500])


class ArkClient:
    def __init__(self, api_key: str, *, base_url: str = BASE_URL, transport: httpx.AsyncBaseTransport | None = None):
        self._client = httpx.AsyncClient(base_url=base_url, transport=transport, follow_redirects=False,
                                         headers={"Authorization": "Bearer " + api_key},
                                         timeout=httpx.Timeout(60, read=300))

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self._client.aclose()

    async def request(self, method: str, path: str, *, json_body: Any = None, params: dict | None = None) -> dict:
        response = await self._client.request(method, path, json=json_body, params=params)
        if response.status_code >= 300:
            raise _error(response)
        return response.json() if response.content else {}

    @asynccontextmanager
    async def events(self, session_id: str) -> AsyncIterator["EventStream"]:
        """打开会话事件流；调用方先 await ready() 再发消息（事件流不回放连接前的事件）。"""
        async with self._client.stream("GET", f"/sessions/{session_id}/events/stream",
                                       params={"event_deltas": "agent.message"},
                                       headers={"Accept": "text/event-stream"}) as response:
            if response.status_code >= 300:
                await response.aread()
                raise _error(response)
            yield EventStream(response.aiter_lines())


class EventStream:
    def __init__(self, lines):
        self._lines = lines
        self._ready = False

    async def ready(self) -> None:
        async for line in self._lines:
            if line.startswith(":") and line[1:].strip() == "ready":
                self._ready = True
                return
        raise ArkError(502, "StreamClosed", "事件流在就绪前断开")

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self):
        data: list[str] = []
        async for line in self._lines:
            if line.startswith("data:"):
                data.append(line[5:].lstrip(" "))
                if len(data) == 1:  # 多数事件一行就是完整 JSON，不等空行
                    try:
                        event = json.loads(data[0])
                    except ValueError:
                        continue
                    data = []
                    if isinstance(event, dict):
                        yield event
                continue
            if line.strip() or not data:
                continue  # 注释行（如心跳）、event/id 字段忽略
            payload, data = "\n".join(data), []
            if payload == "[DONE]":
                return
            try:
                event = json.loads(payload)
            except ValueError:
                continue
            if isinstance(event, dict):
                yield event
