import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { errorText, type WorkspaceMessage, type WorkspaceState } from "./types";

type Activity = { progress: string; stopping: boolean };
type Generation = { controller: AbortController; stopping: boolean; finished: boolean; done: Promise<WorkspaceState | null> };
type MessageBody = { content: string; skill_id: string; attachment_ids: number[]; case_id?: number; document_ids: number[]; response_mode: string };
const EMPTY: WorkspaceState = { messages: [], pending_actions: [] };

export function useConversationRuntime() {
  const [state, renderState] = useState<WorkspaceState>(EMPTY);
  const [activities, setActivities] = useState<Record<string, Activity>>({});
  const active = useRef<WorkspaceState>(EMPTY);
  const cache = useRef(new Map<string, WorkspaceState>());
  const requests = useRef(new Map<string, Generation>());

  const update = (id: string, change: (current: WorkspaceState) => WorkspaceState) => {
    const current = cache.current.get(id);
    if (!current) throw new Error("对话运行状态不存在");
    const next = change(current);
    cache.current.set(id, next);
    if (active.current.conversation_id === id) { active.current = next; renderState(next); }
  };
  const activate = (next: WorkspaceState) => {
    const id = next.conversation_id;
    const selected = id ? cache.current.get(id) || next : next;
    if (id) cache.current.set(id, selected);
    active.current = selected;
    renderState(selected);
  };
  const replace = (next: WorkspaceState) => {
    if (!next.conversation_id) throw new Error("响应缺少对话编号");
    update(next.conversation_id, () => next);
  };
  const activity = (id: string, change: Partial<Activity>) => setActivities((current) => ({ ...current, [id]: { ...current[id], ...change } }));
  const finish = (id: string, entry: Generation) => {
    if (requests.current.get(id) !== entry) return;
    requests.current.delete(id);
    setActivities((current) => { const next = { ...current }; delete next[id]; return next; });
  };

  const generate = async (conversation: WorkspaceState, body: MessageBody, user: WorkspaceMessage, metadata: Partial<WorkspaceMessage>) => {
    const id = conversation.conversation_id;
    if (!id) throw new Error("请先新建对话");
    if (requests.current.has(id)) throw new Error("该对话正在回答");
    const entry: Generation = { controller: new AbortController(), stopping: false, finished: false, done: Promise.resolve(null) };
    requests.current.set(id, entry);
    activity(id, { progress: "正在连接办公助手…", stopping: false });
    const assistantIndex = conversation.messages.length + 1;
    update(id, (current) => ({ ...current, messages: [...current.messages, user, { role: "assistant", content: "", ...metadata }] }));
    entry.done = (async () => {
      try {
        const response = await fetch("/api/v1/personal-agent/messages", {
          method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("access_token") || ""}` },
          body: JSON.stringify({ ...body, conversation_id: id }), signal: entry.controller.signal,
        });
        if (!response.ok || !response.body) throw new Error((await response.text()) || "智能体响应失败");
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let result: WorkspaceState | null = null;
        const consume = (chunk: string) => {
          buffer += chunk.replace(/\r\n/g, "\n");
          const blocks = buffer.split("\n\n");
          buffer = blocks.pop() || "";
          for (const block of blocks) {
            const line = block.split("\n").find((item) => item.startsWith("data:"));
            if (!line) continue;
            const event = JSON.parse(line.slice(5).trim()) as { type: string; content?: string; detail?: string; state?: WorkspaceState };
            if (entry.stopping) continue;
            if (event.type === "progress") activity(id, { progress: event.content || "" });
            else if (event.type === "delta") update(id, (current) => ({ ...current, messages: current.messages.map((item, index) => index === assistantIndex ? { ...item, content: item.content + (event.content || "") } : item) }));
            else if (event.type === "state" && event.state) {
              if (event.state.conversation_id !== id) throw new Error("响应对话编号不匹配");
              result = event.state; replace(result);
            } else if (event.type === "error") throw new Error(event.detail || "智能体处理失败");
          }
        };
        while (true) {
          const { done, value } = await reader.read();
          if (done) { consume(decoder.decode()); break; }
          consume(decoder.decode(value, { stream: true }));
        }
        if (!result && !entry.stopping) throw new Error("响应中断，未收到完整结果，请重新发送");
        return result;
      } catch (error) {
        if ((error as Error).name === "AbortError" || entry.stopping) return null;
        update(id, (current) => ({ ...current, messages: current.messages.map((item, index) => index === assistantIndex ? { ...item, failed: true, content: errorText(error, "智能体处理失败") } : item) }));
        throw error;
      } finally {
        entry.finished = true;
        if (!entry.stopping) finish(id, entry);
      }
    })();
    return entry.done;
  };

  const stop = async (id: string) => {
    const entry = requests.current.get(id);
    if (!entry || entry.stopping) return;
    entry.stopping = true;
    activity(id, { stopping: true, progress: "正在停止当前回答…" });
    try {
      const { data } = await api.post<{ state: WorkspaceState }>(`/personal-agent/conversations/${encodeURIComponent(id)}/stop`);
      if (data.state.conversation_id !== id) throw new Error("停止响应对话编号不匹配");
      replace(data.state);
      entry.controller.abort();
      await entry.done;
      finish(id, entry);
    } catch (error) {
      entry.stopping = false;
      if (entry.finished) finish(id, entry);
      else activity(id, { stopping: false, progress: "停止失败，回答可能仍在生成" });
      throw error;
    }
  };
  const forget = (id: string) => cache.current.delete(id);
  const reset = () => { if (requests.current.size) throw new Error("请先停止正在运行的对话再刷新"); cache.current.clear(); };
  useEffect(() => () => { for (const entry of requests.current.values()) entry.controller.abort(); }, []);

  const get = (id: string) => {
    const current = cache.current.get(id);
    if (!current) throw new Error("对话运行状态不存在");
    return current;
  };
  return { state, get, activate, replace, generate, stop, forget, reset, activities, running: (id?: string | null) => !!id && requests.current.has(id), anyRunning: () => !!requests.current.size };
}
