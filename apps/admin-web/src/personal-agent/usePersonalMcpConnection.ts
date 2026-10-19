import { useCallback, useEffect, useRef, useState } from "react";
import { message } from "antd";
import { api, AUTH_EXPIRED_EVENT } from "../api";
import { emptyMcpDraft, hasConnectionCredential, parsePersonalMcpConfig, personalMcpConfiguration, validatePersonalMcpDraft, type PersonalMcpDraft } from "./personalMcpConfig";
import { personalMcpError, personalMcpVerificationError } from "./personalMcpErrors";
import type { ConnectorConfiguration, ConnectorSecretField } from "../capability-market/connectorAuth";

const BASE = "/capability-market/personal-mcp";
type Scope = "personal" | "global";
type ConnectionSummary = {
  id: string; name: string; revision: string; status: string; scope: Scope; can_manage: boolean;
};
type Connection = ConnectionSummary & {
  servers: { tool_count: number }[];
  capabilities: { discovery: boolean; tool_call: boolean };
};
type StoredConnection = Connection & { configuration: ConnectorConfiguration; secret_fields: ConnectorSecretField[]; error_code?: string };
type Edit = { connection: Connection; auth: PersonalMcpDraft["auth_type"]; header: string; keep: string[][] };

// 只保留安全摘要，不把服务端配置、密钥字段或原始错误带入对话状态。
function summary(data: Connection): Connection {
  const available = availableSummary(data);
  if (!available.can_manage) throw new Error("connection_management_not_authorized");
  return { ...available, servers: data.servers.map(server => ({ tool_count: server.tool_count })), capabilities: { discovery: data.capabilities.discovery, tool_call: data.capabilities.tool_call } };
}

function availableSummary(data: ConnectionSummary): ConnectionSummary {
  if (data.scope !== "personal" && data.scope !== "global") throw new Error("invalid_connection_scope");
  if (typeof data.can_manage !== "boolean") throw new Error("invalid_connection_permission");
  return { id: data.id, name: data.name, revision: data.revision, status: data.status, scope: data.scope, can_manage: data.can_manage };
}

const sameConnection = (left: ConnectionSummary, right: ConnectionSummary) => left.id === right.id && left.scope === right.scope;

export function usePersonalMcpConnection(sessionKey: string) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(emptyMcpDraft);
  const [error, setError] = useState("");
  const [connection, setConnection] = useState<Connection | null>(null);
  const [items, setItems] = useState<ConnectionSummary[]>([]);
  const [defaultScope, setDefaultScope] = useState<Scope | null>(null);
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
    setOpen(false); setDraft(emptyMcpDraft()); setError(""); setConnection(null); setItems([]); setDefaultScope(null); setListing(false); setListError(""); setBusy(false); setEditing(null);
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
      const { data } = await api.get<{ available_connections: ConnectionSummary[]; default_scope: Scope }>(BASE, { signal: lifecycle.current.signal });
      if (version === listVersion.current) {
        if (data.default_scope !== "personal" && data.default_scope !== "global") throw new Error("invalid_default_scope");
        const available = data.available_connections.map(availableSummary);
        setItems(available); setDefaultScope(data.default_scope);
      }
    } catch (failure) {
      if (version === listVersion.current) { setDefaultScope(null); setItems([]); setListError(personalMcpError(failure, "读取 MCP 连接")); }
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
    if (!hasConnectionCredential(text)) return false;
    message.error("密钥不能发送到普通聊天。请先告诉我 MCP 地址和认证方式，在连接确认时使用安全输入填写密钥。");
    return true;
  };
  const update = (next: PersonalMcpDraft) => {
    if (lock.current) return;
    setDraft(next); setConnection(null); setError("");
  };
  const verify = async (saved: ConnectionSummary, signal: AbortSignal) => {
    const { data } = await api.post<{ ok: boolean; configuration: StoredConnection }>(`${BASE}/${encodeURIComponent(saved.id)}/verify`, { revision: saved.revision }, { params: { scope: saved.scope }, timeout: 35000, signal });
    if (signal.aborted) return;
    const checked = summary(data.configuration);
    if (!sameConnection(checked, saved)) throw new Error("connection_response_mismatch");
    setConnection(checked);
    setItems(current => current.map(item => sameConnection(item, checked) ? availableSummary(checked) : item));
    if (!data.ok || checked.status !== "verified") setError(`${personalMcpVerificationError(data.configuration.error_code)}。配置已保存，尚未证明工具可执行。`);
  };
  const saveAndConnect = async () => {
    if (lock.current || connection) return;
    if (!editing && !defaultScope) { setError("请先刷新连接列表，确认新建连接的可见范围后再保存"); return; }
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
        ? await api.put<Connection>(`${BASE}/${encodeURIComponent(editing.connection.id)}`, { ...payload, revision: editing.connection.revision, keep_credentials: preserveCredential ? editing.keep : [] }, { params: { scope: editing.connection.scope }, signal })
        : await api.post<Connection>(BASE, payload, { signal });
      if (signal.aborted) return;
      saved = summary(data);
      if (editing && !sameConnection(saved, editing.connection)) throw new Error("connection_response_mismatch");
      setConnection(saved);
      setEditing(null);
      setDraft(current => ({ ...current, credential: "" }));
      const created = saved;
      setItems(current => [...current.filter(item => !sameConnection(item, created)), availableSummary(created)]);
      await verify(saved, signal);
    } catch (failure) {
      if (signal.aborted) return;
      // 不展示可能包含请求凭据的原始网络异常或服务端响应。
      setError(`${personalMcpError(failure, saved ? "检测连接" : "保存连接")}。${saved ? "配置已保存，尚未证明工具可执行。" : "请核对列表中的实际状态，避免重复创建。"}`);
    } finally { if (!signal.aborted) { lock.current = false; setBusy(false); } }
  };
  const retryTest = async (target: ConnectionSummary | null = connection) => {
    if (!target || lock.current) return;
    if (!target.can_manage) { setError("此全局连接可在聊天中使用，但你没有检测或管理配置的权限"); return; }
    lock.current = true; setBusy(true); setError(""); setConnection(null);
    ++listVersion.current; setListing(false); setDraft(emptyMcpDraft()); setEditing(null);
    const signal = lifecycle.current.signal;
    try { await verify(target, signal); }
    catch (failure) { if (!signal.aborted) setError(`${personalMcpError(failure, "检测连接")}。尚未证明工具可执行。`); }
    finally { if (!signal.aborted) { lock.current = false; setBusy(false); } }
  };
  const edit = async (target: ConnectionSummary) => {
    if (lock.current) return;
    if (!target.can_manage) { setError("没有读取或修改此连接配置的权限"); return; }
    lock.current = true; setBusy(true); setError("");
    ++listVersion.current; setListing(false); setDraft(emptyMcpDraft()); setConnection(null); setEditing(null);
    const signal = lifecycle.current.signal;
    try {
      const { data } = await api.get<StoredConnection>(`${BASE}/${encodeURIComponent(target.id)}`, { params: { scope: target.scope }, signal });
      if (signal.aborted) return;
      if (!sameConnection(data, target)) throw new Error("connection_response_mismatch");
      const managed = summary(data);
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
      setEditing({ connection: managed, auth: next.auth_type, header: next.api_key_header, keep: data.secret_fields.filter(field => field.configured).map(field => field.path) });
    } catch (failure) { if (!signal.aborted) setError(personalMcpError(failure, "载入连接配置")); }
    finally { if (!signal.aborted) { lock.current = false; setBusy(false); } }
  };
  const remove = async (target: ConnectionSummary) => {
    if (lock.current) return;
    if (!target.can_manage) { setError("没有删除此连接的权限"); return; }
    lock.current = true; setBusy(true); setError("");
    ++listVersion.current; setListing(false);
    const signal = lifecycle.current.signal;
    try {
      const { data } = await api.delete<{ id: string; scope: Scope; deleted: boolean }>(`${BASE}/${encodeURIComponent(target.id)}`, { params: { revision: target.revision, scope: target.scope }, signal });
      if (signal.aborted) return;
      if (!data.deleted || data.id !== target.id || data.scope !== target.scope) throw new Error("delete_not_confirmed");
      setItems(current => current.filter(item => !sameConnection(item, target)));
      if ((connection && sameConnection(connection, target)) || (editing && sameConnection(editing.connection, target))) { setConnection(null); setEditing(null); setDraft(emptyMcpDraft()); }
    } catch (failure) { if (!signal.aborted) setError(personalMcpError(failure, "删除连接")); }
    finally { if (!signal.aborted) { lock.current = false; setBusy(false); } }
  };
  const newConnection = () => { if (!lock.current) { setEditing(null); update(emptyMcpDraft()); } };
  const credentialSaved = !!editing && editing.auth === draft.auth_type && editing.header === draft.api_key_header && editing.keep.length > 0;
  const scope = editing?.connection.scope || connection?.scope || defaultScope;
  return { open, draft, error, connection, items, listError, listing, busy, scope, defaultScope, editing: !!editing, credentialSaved, intercept, importConfig, update, close: reset, saveAndConnect, retryTest, show, refresh, edit, remove, newConnection };
}
