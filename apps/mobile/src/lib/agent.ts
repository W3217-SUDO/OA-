import { fetch as streamingFetch } from "expo/fetch";
import { API_BASE_URL, ApiError, api, authHeaders, errorDetail } from "./api";
import type { ConversationSnapshot, WorkspaceState } from "./types";

// 协议与网页端 personal-agent/useConversationRuntime.ts 一致：POST 后按 SSE 读取 progress / delta / state / done / error。
type StreamEvent = { type: string; content?: string; detail?: string; state?: WorkspaceState };

export type StreamHandlers = {
  onProgress: (text: string) => void;
  onDelta: (text: string) => void;
};

export async function sendAgentMessage(conversationId: string, content: string, handlers: StreamHandlers, signal: AbortSignal): Promise<WorkspaceState | null> {
  const response = await streamingFetch(`${API_BASE_URL}/personal-agent/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream", ...authHeaders() },
    body: JSON.stringify({ conversation_id: conversationId, content, skill_id: "", attachment_ids: [], document_ids: [], response_mode: "fast" }),
    signal,
  });
  if (!response.ok || !response.body) {
    const text = await response.text();
    let body: unknown = null;
    try {
      body = JSON.parse(text);
    } catch {
      body = null;
    }
    throw new ApiError(response.status, errorDetail(body, text || "智能体响应失败"));
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: WorkspaceState | null = null;
  let completed = false;
  const consume = (chunk: string) => {
    buffer += chunk.replace(/\r\n/g, "\n");
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() || "";
    for (const block of blocks) {
      const line = block.split("\n").find((item) => item.startsWith("data:"));
      if (!line) continue;
      const event = JSON.parse(line.slice(5).trim()) as StreamEvent;
      if (event.type === "progress") handlers.onProgress(event.content || "");
      else if (event.type === "delta") handlers.onDelta(event.content || "");
      else if (event.type === "state" && event.state) {
        if (event.state.conversation_id !== conversationId) throw new Error("响应对话编号不匹配");
        result = event.state;
        completed = true;
      } else if (event.type === "done") completed = true;
      else if (event.type === "error") throw new Error(event.detail || "智能体处理失败");
    }
  };
  try {
    while (!completed) {
      const { done, value } = await reader.read();
      if (done) {
        consume(decoder.decode());
        break;
      }
      consume(decoder.decode(value, { stream: true }));
    }
    if (completed) await reader.cancel();
  } finally {
    reader.releaseLock();
  }
  return result;
}

export const agentApi = {
  snapshot: () => api.get<ConversationSnapshot>("/personal-agent/conversations"),
  create: () => api.post<ConversationSnapshot>("/personal-agent/conversations"),
  select: (id: string) => api.post<ConversationSnapshot>(`/personal-agent/conversations/${encodeURIComponent(id)}/select`),
  stop: (id: string) => api.post<{ state: WorkspaceState }>(`/personal-agent/conversations/${encodeURIComponent(id)}/stop`),
  decide: (actionId: string, conversationId: string, decision: "approved" | "rejected") =>
    api.post<{ state: WorkspaceState }>(
      `/personal-agent/actions/${encodeURIComponent(actionId)}/decision`,
      { conversation_id: conversationId, decision },
      { "X-OA-Agent-Confirmation": "frontend" },
    ),
};
