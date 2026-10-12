import { useEffect, useRef, useState } from "react";
import { message } from "antd";
import { api } from "../api";

export type MessageItem = { role: "user" | "assistant"; content: string; created_at?: string };
export type PendingAction = { id: string; type: string; summary: string; payload?: Record<string, unknown>; status: "pending" | "approved" | "rejected" };
export type AgentState = { messages: MessageItem[]; pending_actions: PendingAction[] };
export type AgentStatus = { ready: boolean; model: string; model_provider?: string; write_requires_confirmation: boolean; identity: { display_name?: string; department?: string; role?: string; position?: string } };

export const actionLabel = (item: PendingAction) => item.type === "create_task" ? "新建任务" : item.type === "approve_contract" ? "合同审批" : item.summary;

// 个人智能体的状态、对话和待确认操作；界面与工作台的各个提醒共用同一份对话。
export function usePersonalAgent() {
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [state, setState] = useState<AgentState>({ messages: [], pending_actions: [] });
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const requestRef = useRef<AbortController | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const [statusResponse, stateResponse] = await Promise.all([
        api.get("/personal-agent/status"),
        api.get("/personal-agent/state"),
      ]);
      setStatus(statusResponse.data);
      setState(stateResponse.data);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "个人智能体加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);
  useEffect(() => () => requestRef.current?.abort(), []);

  const decide = async (action: PendingAction, decision: "approved" | "rejected") => {
    try {
      const { data } = await api.post(`/personal-agent/actions/${action.id}/decision`, { decision });
      setState(data.state || state);
      message.success(decision === "approved" ? "操作已完成" : "已取消操作");
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "操作未完成，系统数据未改变");
      void load();
    }
  };

  const send = async (text: string) => {
    const content = text.trim();
    if (!content || sending) return;
    setSending(true);
    const controller = new AbortController();
    requestRef.current = controller;
    const assistantIndex = state.messages.length + 1;
    setState((current) => ({ ...current, messages: [...current.messages, { role: "user", content }, { role: "assistant", content: "" }] }));
    try {
      const response = await fetch("/api/v1/personal-agent/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("access_token") || ""}` },
        body: JSON.stringify({ content }),
        signal: controller.signal,
      });
      if (!response.ok || !response.body) {
        const detail = await response.text();
        throw new Error(detail || "个人智能体响应失败");
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      const consume = (chunk: string) => {
        buffer += chunk;
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() || "";
        for (const block of blocks) {
          const line = block.split("\n").find((item) => item.startsWith("data:"));
          if (!line) continue;
          const event = JSON.parse(line.slice(5).trim()) as { type: string; content?: string; detail?: string; state?: AgentState };
          if (event.type === "delta") {
            setState((current) => ({ ...current, messages: current.messages.map((item, index) => index === assistantIndex ? { ...item, content: `${item.content}${event.content || ""}` } : item) }));
          } else if (event.type === "state" && event.state) {
            setState(event.state);
          } else if (event.type === "error") {
            throw new Error(event.detail || "个人智能体处理失败");
          }
        }
      };
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        consume(decoder.decode(value, { stream: true }));
      }
    } catch (error: any) {
      if (error?.name !== "AbortError") {
        setState((current) => ({ ...current, messages: current.messages.map((item, index) => index === assistantIndex ? { ...item, content: error?.message || "个人智能体处理失败" } : item) }));
      }
    } finally {
      requestRef.current = null;
      setSending(false);
    }
  };

  const stop = () => requestRef.current?.abort();

  return { status, state, loading, sending, reload: load, send, stop, decide };
}

export type PersonalAgent = ReturnType<typeof usePersonalAgent>;
