from __future__ import annotations

import asyncio
import base64
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import websockets

from .agent_skills import GENERAL_SKILL, AgentSkill
from .case_agent import (
    CaseAgentRuntime,
    _MODEL_CHUNK_CALLBACK,
    _extract_proposed_action,
    build_case_model_messages,
)


class HarnessRpcError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class DeepSeekHarnessCaseAgentRuntime(CaseAgentRuntime):
    """DeepSeek Harness execution adapter with OA-owned state and approvals."""

    def __init__(
        self,
        *,
        harness_base_url: str,
        harness_provider: str = "sunhold-oa",
        harness_agent_preset: str = "standard",
        harness_workspace: str = "",
        harness_timeout_seconds: float = 120,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.harness_base_url = harness_base_url.strip().rstrip("/")
        self.harness_provider = harness_provider.strip() or "sunhold-oa"
        self.harness_agent_preset = harness_agent_preset.strip() or "standard"
        self.harness_workspace = harness_workspace.strip()
        self.harness_timeout_seconds = max(10.0, min(float(harness_timeout_seconds), 600.0))
        self.harness_ready = False
        self.harness_error = ""

    async def start(self) -> None:
        await super().start()
        if not self.enabled or self.graph is None:
            return
        try:
            await self._rpc("host.describe", {})
            if self._model_is_configured():
                await self._configure_model_route()
            self.harness_ready = True
            self.harness_error = ""
        except (httpx.HTTPError, HarnessRpcError, ValueError) as exc:
            self.harness_ready = False
            self.harness_error = f"harness_unavailable:{type(exc).__name__}"

    async def stop(self) -> None:
        self.harness_ready = False
        await super().stop()

    def _model_is_configured(self) -> bool:
        return bool(self.api_base_url and self.api_key and self.model)

    def status(self) -> dict[str, Any]:
        result = super().status()
        result.update({
            "ready": bool(result["ready"] and self.harness_ready),
            "agent_runtime_backend": "deepseek-harness",
            "harness_ready": self.harness_ready,
            "harness_base_url": self.harness_base_url,
            "harness_provider": self.harness_provider,
            "harness_agent_preset": self.harness_agent_preset,
            "model_configured": self._model_is_configured(),
            "error": self.harness_error or result["error"],
        })
        return result

    async def _rpc(
        self,
        method: str,
        payload: dict[str, Any],
        *,
        client: httpx.AsyncClient | None = None,
    ) -> Any:
        request = {
            "type": "client-request",
            "rpcId": str(uuid4()),
            "method": method,
            "payload": payload,
        }
        owns_client = client is None
        active_client = client or httpx.AsyncClient(timeout=self.harness_timeout_seconds, trust_env=False)
        try:
            response = await active_client.post(
                f"{self.harness_base_url}/api/{method}",
                headers={"Content-Type": "application/json"},
                json=request,
            )
            response.raise_for_status()
            envelope = response.json()
            result = envelope.get("result") or {}
            if not result.get("ok"):
                error = result.get("error") or {}
                raise HarnessRpcError(
                    str(error.get("code") or "harness-error"),
                    str(error.get("message") or "DeepSeek Harness request failed"),
                )
            return result.get("value")
        finally:
            if owns_client:
                await active_client.aclose()

    async def _configure_model_route(self) -> None:
        description = await self._rpc("settings.describe", {})
        namespace = next(
            (item for item in description.get("namespaces", []) if item.get("ns") == "llm-pi-ai"),
            None,
        )
        if not namespace:
            raise HarnessRpcError("settings-rejected", "llm-pi-ai settings are unavailable")
        profile = {
            "displayName": "Sunhold OA configured model",
            "apiKeyEnv": "SUNHOLD_OA_MODEL_API_KEY",
            "api": "openai-completions",
            "baseURL": self.api_base_url,
            "models": [{"id": self.model, "name": self.model}],
            "headers": {"Connection": "close"},
            "timeoutMs": int(self.harness_timeout_seconds * 1000),
            "streamIdleTimeoutMs": int(self.harness_timeout_seconds * 1000),
            "retryPolicy": {
                "mode": "normal",
                "maxRetries": 0,
            },
        }
        current = ((namespace.get("value") or {}).get("providers") or {}).get(self.harness_provider)
        if current != profile:
            await self._rpc(
                "settings.mutate",
                {
                    "ns": "llm-pi-ai",
                    "ops": [{
                        "op": "set",
                        "path": ["providers", self.harness_provider],
                        "value": profile,
                    }],
                    "expectedRevision": namespace.get("revision", 0),
                },
            )
        await self._rpc(
            "credentials.set",
            {"ref": "SUNHOLD_OA_MODEL_API_KEY", "value": self.api_key},
        )

    def _harness_session_id(self, snapshot: dict[str, Any], messages: list[dict[str, Any]]) -> str:
        case = snapshot.get("case") or {}
        case_id = int(case.get("id") or 0)
        latest = messages[-1] if messages else {}
        private_thread = self.thread_id(case_id, str(latest.get("operator") or "unknown"))
        digest = hashlib.sha256(private_thread.encode("utf-8")).hexdigest()[:32]
        return f"sunhold-{case_id}-{digest}"

    async def _ensure_session(self, session_id: str) -> None:
        try:
            await self._rpc("session.history", {"sessionId": session_id, "maxMessages": 1})
        except HarnessRpcError as exc:
            if exc.code != "session-not-found":
                raise
            payload: dict[str, Any] = {
                "sessionId": session_id,
                "agentPreset": self.harness_agent_preset,
            }
            if self.harness_workspace:
                workspace = Path(self.harness_workspace).expanduser().resolve()
                workspace.mkdir(parents=True, exist_ok=True)
                payload["cwd"] = str(workspace)
            await self._rpc("session.create", payload)
        await self._rpc(
            "session.selectModel",
            {"sessionId": session_id, "provider": self.harness_provider, "model": self.model},
        )

    @staticmethod
    def _prompt_content(
        prompt_messages: list[dict[str, Any]],
        request_images: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        sections = [
            "请直接回答以下 OA 案件请求。案件数据已经由 OA 权限层裁剪。",
            "不要调用 Bash、文件系统、网页、MCP 或其他 Harness 工具；不要自行访问或修改系统。",
            "任何写操作只能输出 OA 约定的 proposed_action，实际写入仍由 OA 人工审批执行。",
            "生成 Word 或法律文书到案件 AI空间属于草稿输出：请直接生成完整正文，不要声称不能创建 Word；由 OA 前端保存为 DOCX。",
        ]
        for message in prompt_messages:
            role = str(message.get("role") or "user").upper()
            content = message.get("content")
            if isinstance(content, str):
                sections.append(f"[{role}]\n{content}")
            elif isinstance(content, list):
                texts = [str(item.get("text") or "") for item in content if item.get("type") == "text"]
                if texts:
                    sections.append(f"[{role}]\n" + "\n".join(texts))
        parts: list[dict[str, Any]] = [{"type": "text", "text": "\n\n".join(sections)}]
        for image in request_images:
            data_url = str(image.get("data_url") or "")
            if not data_url.startswith("data:") or "," not in data_url:
                continue
            header, encoded = data_url.split(",", 1)
            media_type = header[5:].split(";", 1)[0]
            if media_type not in {"image/png", "image/jpeg", "image/webp", "image/gif"}:
                continue
            base64.b64decode(encoded, validate=True)
            parts.append({
                "type": "image",
                "mediaType": media_type,
                "data": encoded,
                "name": str(image.get("name") or "image"),
            })
        return parts

    @staticmethod
    def _event_envelope(raw: str) -> dict[str, Any] | None:
        value = json.loads(raw)
        return value if isinstance(value, dict) else None

    async def _run_prompt(
        self,
        session_id: str,
        content: list[dict[str, Any]],
    ) -> str:
        callback = _MODEL_CHUNK_CALLBACK.get()
        chunks: list[str] = []
        final_text = ""
        turn_error = ""
        websocket_url = self.harness_base_url.replace("http://", "ws://", 1).replace("https://", "wss://", 1)
        websocket_url += "/api/events.mux"
        async with httpx.AsyncClient(timeout=self.harness_timeout_seconds, trust_env=False) as client:
            async with websockets.connect(
                websocket_url,
                proxy=None,
                open_timeout=10,
                close_timeout=5,
                max_size=4 * 1024 * 1024,
            ) as socket:
                await self._rpc(
                    "session.prompt",
                    {
                        "sessionId": session_id,
                        "mode": "queue",
                        "content": content,
                        "clientTimeZone": "Asia/Shanghai",
                    },
                    client=client,
                )
                while True:
                    raw = await asyncio.wait_for(socket.recv(), timeout=self.harness_timeout_seconds)
                    envelope = self._event_envelope(raw) or {}
                    payload = envelope.get("payload") or {}
                    payload_type = payload.get("type")
                    if payload_type == "stream/error":
                        error = payload.get("error") or {}
                        raise RuntimeError(str(error.get("message") or "harness_stream_failed"))
                    if payload.get("sessionId") != session_id:
                        continue
                    if payload_type in {"approval/requested", "question/requested"}:
                        await self._rpc("session.cancel", {"sessionId": session_id}, client=client)
                        raise RuntimeError("harness_interaction_blocked_by_oa_approval_boundary")
                    if payload_type != "session/event":
                        continue
                    event = payload.get("event") or {}
                    data = event.get("data") or {}
                    if event.get("type") == "assistant/chunk":
                        chunk = data.get("chunk") or {}
                        if chunk.get("type") == "text-delta":
                            delta = str(chunk.get("text") or "")
                            if delta:
                                chunks.append(delta)
                                if callback:
                                    callback(delta)
                    elif event.get("type") == "assistant/message":
                        blocks = ((data.get("message") or {}).get("content") or [])
                        final_text = "".join(
                            str(block.get("text") or "")
                            for block in blocks
                            if block.get("type") == "text"
                        ).strip()
                    elif event.get("type") == "turn/end":
                        reason = data.get("reason") or {}
                        if reason.get("kind") == "error":
                            failure = reason.get("failure") or {}
                            turn_error = str(
                                failure.get("message")
                                or reason.get("message")
                                or reason.get("error")
                                or "harness_turn_failed"
                            )
                        break
        if turn_error:
            raise RuntimeError(turn_error)
        result = final_text or "".join(chunks).strip()
        if not result:
            raise RuntimeError("harness_empty_response")
        return result

    async def _request_model(
        self,
        snapshot: dict[str, Any],
        messages: list[dict[str, Any]],
        skill: AgentSkill = GENERAL_SKILL,
        request_images: list[dict[str, Any]] | None = None,
    ) -> tuple[str, dict[str, Any] | None]:
        session_id = self._harness_session_id(snapshot, messages)
        await self._ensure_session(session_id)
        prompt_messages = build_case_model_messages(snapshot, messages, skill, request_images)
        content = self._prompt_content(prompt_messages, list(request_images or []))
        response = await self._run_prompt(session_id, content)
        return _extract_proposed_action(response)

    async def cancel(self, case_id: int, operator: str) -> None:
        snapshot = {"case": {"id": case_id}}
        messages = [{"operator": operator}]
        await self._rpc("session.cancel", {"sessionId": self._harness_session_id(snapshot, messages)})


def create_case_agent_runtime(*, runtime_backend: str = "langgraph", **kwargs: Any) -> CaseAgentRuntime:
    backend = runtime_backend.strip().casefold()
    if backend == "deepseek-harness":
        return DeepSeekHarnessCaseAgentRuntime(**kwargs)
    if backend != "langgraph":
        raise ValueError(f"unsupported_agent_runtime_backend:{runtime_backend}")
    compatible = {
        key: value
        for key, value in kwargs.items()
        if not key.startswith("harness_")
    }
    return CaseAgentRuntime(**compatible)
