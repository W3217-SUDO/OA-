import { useRef, useState } from "react";
import { api } from "../api";
import type { ConversationSnapshot, WorkspaceConversation, WorkspaceState } from "./types";
import type { ConversationWorkspace, WorkspaceProject } from "./types";
import { conversationWorkspaceKey, conversationWorkspaceParams, requireConversationWorkspace } from "./conversationWorkspace";
import { useConversationSpaces, type ConversationView } from "./useConversationSpaces";
import { errorText } from "./types";

export function usePersonalConversations(onState: (state: WorkspaceState) => void, onBackgroundState?: (state: WorkspaceState) => void) {
  const [items, setItems] = useState<WorkspaceConversation[]>([]);
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [projects, setProjects] = useState<WorkspaceProject[]>([]);
  const spaces = useConversationSpaces();
  const validate = (snapshot: ConversationSnapshot, workspace?: ConversationWorkspace) => {
    if (workspace && (conversationWorkspaceKey(requireConversationWorkspace(snapshot.workspace)) !== conversationWorkspaceKey(workspace)
      || conversationWorkspaceKey(requireConversationWorkspace(snapshot.state.workspace)) !== conversationWorkspaceKey(workspace))) throw new Error("会话响应的空间归属不匹配，请刷新核对");
    if (workspace && !Array.isArray(snapshot.workspaces)) throw new Error("会话响应缺少空间目录，请刷新核对");
    if (workspace && snapshot.items.some((item) => conversationWorkspaceKey(requireConversationWorkspace(item.workspace)) !== conversationWorkspaceKey(workspace))) throw new Error("空间会话列表归属不匹配，请刷新核对");
  };
  const apply = (snapshot: ConversationSnapshot, ticket: ConversationView) => {
    validate(snapshot, ticket.workspace);
    if (spaces.isCurrent(ticket)) { setItems(snapshot.items); if (snapshot.workspaces) setProjects(snapshot.workspaces); setError(snapshot.active_unavailable_reason || ""); onState(snapshot.state); }
    else onBackgroundState?.(snapshot.state);
    return snapshot.state;
  };
  const read = async (ticket = spaces.capture(), timeout?: number) => (await api.get<ConversationSnapshot>("/personal-agent/conversations", { params: conversationWorkspaceParams(ticket.workspace), ...(timeout ? { timeout } : {}) })).data;
  const load = async () => {
    const ticket = spaces.capture();
    try { return apply(await read(ticket), ticket); }
    catch (failure) { if (spaces.isCurrent(ticket)) setError(errorText(failure, "空间会话加载失败")); throw failure; }
  };
  const refresh = async (ticket = spaces.capture()) => {
    const data = await read(ticket);
    validate(data, ticket.workspace);
    // 生成结束的旧空间请求只更新其原视图，不能覆盖之后切入的空间列表。
    if (spaces.isCurrent(ticket)) { setItems(data.items); if (data.workspaces) setProjects(data.workspaces); setError(data.active_unavailable_reason || ""); }
  };
  const openWorkspace = async (workspace?: ConversationWorkspace, register = false) => {
    if (workspace) workspace = requireConversationWorkspace(workspace);
    const ticket = spaces.change(workspace);
    setItems([]); setLoading(true); setError("");
    onState({ conversation_id: null, messages: [], pending_actions: [], dismissed_action_ids: [], ...(workspace ? { workspace } : {}) });
    try { return apply(register && workspace ? (await api.post<ConversationSnapshot>("/personal-agent/workspaces", { workspace })).data : await read(ticket), ticket); }
    catch (failure) { if (spaces.isCurrent(ticket)) setError(errorText(failure, "空间会话加载失败")); throw failure; }
    finally { if (spaces.isCurrent(ticket)) setLoading(false); }
  };
  const change = async (action: "create" | "select" | "delete", id?: string, captured?: ConversationView) => {
    if (lock.current) throw new Error("正在切换对话，请稍后再试");
    lock.current = true;
    setBusy(true);
    try {
      const ticket = captured || spaces.capture();
      let requestedWorkspace = ticket.workspace;
      if (action === "select" && ticket.workspace) {
        const summary = items.find((item) => item.id === id) || (await read({ revision: ticket.revision })).items.find((item) => item.id === id);
        if (!summary) throw new Error("来源对话不存在或已删除");
        requestedWorkspace = requireConversationWorkspace(summary.workspace);
      }
      const url = `/personal-agent/conversations${id ? `/${encodeURIComponent(id)}` : ""}`;
      const config = { params: conversationWorkspaceParams(requestedWorkspace) };
      const response = action === "delete" ? await api.delete<ConversationSnapshot>(url, config) : await api.post<ConversationSnapshot>(action === "select" ? `${url}/select` : url, action === "create" && ticket.workspace ? { workspace: ticket.workspace } : undefined, config);
      validate(response.data, requestedWorkspace);
      if (action === "create" && !response.data.state.conversation_id) throw new Error("新建对话响应缺少会话编号，未清空当前草稿");
      const appliedTicket = action === "select" && ticket.workspace && spaces.isCurrent(ticket) ? spaces.change(requestedWorkspace) : { ...ticket, workspace: requestedWorkspace };
      return apply(response.data, appliedTicket);
    } finally { lock.current = false; setBusy(false); }
  };
  return { items, projects, busy, loading, error, workspace: spaces.workspace, capture: spaces.capture, read, openWorkspace, locked: () => lock.current, load, refresh, create: (view?: ConversationView) => change("create", undefined, view), select: (id: string) => change("select", id), remove: (id: string) => change("delete", id) };
}
