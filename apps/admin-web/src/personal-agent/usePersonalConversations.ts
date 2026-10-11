import { useRef, useState } from "react";
import { api } from "../api";
import type { ConversationSnapshot, WorkspaceConversation, WorkspaceState } from "./types";

export function usePersonalConversations(onState: (state: WorkspaceState) => void) {
  const [items, setItems] = useState<WorkspaceConversation[]>([]);
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const apply = (snapshot: ConversationSnapshot) => {
    setItems(snapshot.items);
    onState(snapshot.state);
    return snapshot.state;
  };
  const load = async () => apply((await api.get<ConversationSnapshot>("/personal-agent/conversations")).data);
  const refresh = async () => {
    const { data } = await api.get<ConversationSnapshot>("/personal-agent/conversations");
    setItems(data.items);
  };
  const change = async (action: "create" | "select" | "delete", id?: string) => {
    if (lock.current) throw new Error("正在切换对话，请稍后再试");
    lock.current = true;
    setBusy(true);
    try {
      const url = `/personal-agent/conversations${id ? `/${encodeURIComponent(id)}` : ""}`;
      const response = action === "delete" ? await api.delete<ConversationSnapshot>(url) : await api.post<ConversationSnapshot>(action === "select" ? `${url}/select` : url);
      return apply(response.data);
    } finally { lock.current = false; setBusy(false); }
  };
  return { items, busy, locked: () => lock.current, load, refresh, create: () => change("create"), select: (id: string) => change("select", id), remove: (id: string) => change("delete", id) };
}
