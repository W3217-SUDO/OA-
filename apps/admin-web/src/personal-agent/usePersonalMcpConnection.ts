import { useCallback, useEffect, useRef, useState } from "react";
import { api, AUTH_EXPIRED_EVENT } from "../api";
import { emptyMcpDraft, hasConnectionCredential, isMcpConnectionInput, parsePersonalMcpConfig, personalMcpConfiguration, validatePersonalMcpDraft, type PersonalMcpDraft } from "./personalMcpConfig";
import { personalMcpError, personalMcpVerificationError } from "./personalMcpErrors";
import type { ConnectorConfiguration, ConnectorSecretField } from "../capability-market/connectorAuth";

const BASE = "/capability-market/personal-mcp";
type Connection = {
  id: string; name: string; revision: string; status: string;
  servers: { tool_count: number }[];
  capabilities: { discovery: boolean; tool_call: boolean };
};
type StoredConnection = Connection & { configuration: ConnectorConfiguration; secret_fields: ConnectorSecretField[]; error_code?: string };
type Edit = { connection: Connection; auth: PersonalMcpDraft["auth_type"]; header: string; keep: string[][] };

// 只保留安全摘要，不把服务端配置、密钥字段或原始错误带入对话状态。
function summary(data: Connection): Connection {
  return { id: data.id, name: data.name, revision: data.revision, status: data.status, servers: data.servers.map(server => ({ tool_count: server.tool_count })), capabilities: { discovery: data.capabilities.discovery, tool_call: data.capabilities.tool_call } };
}

export function usePersonalMcpConnection(sessionKey: string) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(emptyMcpDraft);
  const [error, setError] = useState("");
  const [connection, setConnection] = useState<Connection | null>(null);
  const [items, setItems] = useState<Connection[]>([]);
  const [listError, setListError] = useState("");
  const [listing, setListing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<Edit | null>(null);
  const lock = useRef(false);
  const listVersion = useRef(0);
  const lifecycle = useRef(new AbortController());
  const reset = useCallback(() => {
    lifecycle.current.abort(); lifecycle.current = new AbortController();
    ++listVersion.current; lock.current = false;
    setOpen(false); setDraft(emptyMcpDraft()); setError(""); setConnection(null); setItems([]); setListing(false); setListError(""); setBusy(false); setEditing(null);
  }, []);
  useEffect(() => { reset(); return () => { lifecycle.current.abort(); }; }, [sessionKey, reset]);
  useEffect(() => {
    if (typeof window === "undefined") return;
    const storage = (event: StorageEvent) => { if (event.key === "access_token") reset(); };
    window.addEventListener(AUTH_EXPIRED_EVENT, reset);
    window.addEventListener("storage", storage);
    return () => { window.removeEventListener(AUTH_EXPIRED_EVENT, reset); window.removeEventListener("storage", storage); };
  }, [reset]);

  const refresh = async () => {
    const version = ++listVersion.current;
    setListing(true); setListError("");
    try {
      const { data } = await api.get<{ items: Connection[] }>(BASE, { signal: lifecycle.current.signal });
      if (version === listVersion.current) setItems(data.items.map(summary));
    } catch (failure) {
      if (version === listVersion.current) setListError(personalMcpError(failure, "读取个人连接"));
    } finally { if (version === listVersion.current) setListing(false); }
  };
  const show = () => { setOpen(true); void refresh(); };
  const importConfig = (text: string) => {
    if (lock.current) return;
    setConnection(null); setEditing(null); setError("");
    try { setDraft(parsePersonalMcpConfig(text)); }
    catch (failure) {
      setDraft(emptyMcpDraft());
      setError(failure instanceof Error ? failure.message : "配置解析失败，请重新填写");
    }
  };
  const intercept = (text: string) => {
    const intent = isMcpConnectionInput(text, open);
    if (!intent && !hasConnectionCredential(text)) return false;
    if (lock.current) return true;
    show();
    if (!intent) {
      setError("检测到疑似凭据，已阻止进入模型和聊天记录。连接 MCP 请在此填写地址和 Key；普通聊天请移除凭据后重发。");
      return true;
    }
    if (/https?:\/\/|\{/.test(text)) {
      const url = text.trim().match(/^(?:[^{}]*?(?:连接|接入|添加)\s*(?:MCP)?\s*[:：]?\s*)?(https?:\/\/\S+)$/i)?.[1];
      importConfig(url || text);
    }
    return true;
  };
  const update = (next: PersonalMcpDraft) => {
    if (lock.current) return;
    setDraft(next); setConnection(null); setError("");
  };
  const verify = async (saved: Connection, signal: AbortSignal) => {
    const { data } = await api.post<{ ok: boolean; configuration: StoredConnection }>(`${BASE}/${encodeURIComponent(saved.id)}/verify`, { revision: saved.revision }, { timeout: 35000, signal });
    if (signal.aborted) return;
    const checked = summary(data.configuration);
    setConnection(checked);
    setItems(current => current.map(item => item.id === checked.id ? checked : item));
    if (!data.ok || checked.status !== "verified") setError(`${personalMcpVerificationError(data.configuration.error_code)}。配置已保存，尚未证明工具可执行。`);
  };
  const saveAndConnect = async () => {
    if (lock.current || connection) return;
    const preserveCredential = !!editing && editing.auth === draft.auth_type && editing.header === draft.api_key_header && !draft.credential && editing.keep.length > 0;
    const validation = validatePersonalMcpDraft(draft, preserveCredential);
    if (validation) { setError(validation); return; }
    lock.current = true; setBusy(true); setError("");
    ++listVersion.current; setListing(false);
    const signal = lifecycle.current.signal;
    let saved: Connection | null = null;
    try {
      const payload = { name: draft.name.trim(), configuration: personalMcpConfiguration(draft) };
      const { data } = editing
        ? await api.put<Connection>(`${BASE}/${encodeURIComponent(editing.connection.id)}`, { ...payload, revision: editing.connection.revision, keep_credentials: preserveCredential ? editing.keep : [] }, { signal })
        : await api.post<Connection>(BASE, payload, { signal });
      if (signal.aborted) return;
      saved = summary(data);
      setConnection(saved);
      setEditing(null);
      setDraft(current => ({ ...current, credential: "" }));
      const created = saved;
      setItems(current => [...current.filter(item => item.id !== created.id), created]);
      await verify(saved, signal);
    } catch (failure) {
      if (signal.aborted) return;
      // 不展示可能包含请求凭据的原始网络异常或服务端响应。
      setError(`${personalMcpError(failure, saved ? "检测连接" : "保存连接")}。${saved ? "配置已保存，尚未证明工具可执行。" : "请核对列表中的实际状态，避免重复创建。"}`);
    } finally { if (!signal.aborted) { lock.current = false; setBusy(false); } }
  };
  const retryTest = async (target = connection) => {
    if (!target || lock.current) return;
    lock.current = true; setBusy(true); setError(""); setConnection(target);
    ++listVersion.current; setListing(false); setDraft(emptyMcpDraft()); setEditing(null);
    const signal = lifecycle.current.signal;
    try { await verify(target, signal); }
    catch (failure) { if (!signal.aborted) setError(`${personalMcpError(failure, "检测连接")}。尚未证明工具可执行。`); }
    finally { if (!signal.aborted) { lock.current = false; setBusy(false); } }
  };
  const edit = async (target: Connection) => {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError("");
    ++listVersion.current; setListing(false); setDraft(emptyMcpDraft()); setConnection(null); setEditing(null);
    const signal = lifecycle.current.signal;
    try {
      const { data } = await api.get<StoredConnection>(`${BASE}/${encodeURIComponent(target.id)}`, { signal });
      if (signal.aborted) return;
      const config = structuredClone(data.configuration);
      // 已保存凭据按路径显式保留，表单只读脱敏后的空值。
      for (const field of data.secret_fields.filter(field => field.configured)) {
        let parent = config;
        for (const part of field.path.slice(0, -1)) parent = parent[part];
        parent[field.path.at(-1)!] = "";
      }
      const next = parsePersonalMcpConfig(JSON.stringify(config));
      next.name = data.name; next.credential = "";
      setDraft(next); setConnection(null);
      setEditing({ connection: summary(data), auth: next.auth_type, header: next.api_key_header, keep: data.secret_fields.filter(field => field.configured).map(field => field.path) });
    } catch (failure) { if (!signal.aborted) setError(personalMcpError(failure, "载入连接配置")); }
    finally { if (!signal.aborted) { lock.current = false; setBusy(false); } }
  };
  const remove = async (target: Connection) => {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError("");
    ++listVersion.current; setListing(false);
    const signal = lifecycle.current.signal;
    try {
      const { data } = await api.delete<{ id: string; deleted: boolean }>(`${BASE}/${encodeURIComponent(target.id)}`, { params: { revision: target.revision }, signal });
      if (signal.aborted) return;
      if (!data.deleted || data.id !== target.id) throw new Error("delete_not_confirmed");
      setItems(current => current.filter(item => item.id !== target.id));
      if (connection?.id === target.id || editing?.connection.id === target.id) { setConnection(null); setEditing(null); setDraft(emptyMcpDraft()); }
    } catch (failure) { if (!signal.aborted) setError(personalMcpError(failure, "删除连接")); }
    finally { if (!signal.aborted) { lock.current = false; setBusy(false); } }
  };
  const newConnection = () => { if (!lock.current) { setEditing(null); update(emptyMcpDraft()); } };
  const credentialSaved = !!editing && editing.auth === draft.auth_type && editing.header === draft.api_key_header && editing.keep.length > 0;
  return { open, draft, error, connection, items, listError, listing, busy, editing: !!editing, credentialSaved, intercept, importConfig, update, close: reset, saveAndConnect, retryTest, show, refresh, edit, remove, newConnection };
}
