import { useEffect, useRef, useState } from "react";
import { Alert, Button, Checkbox, Form, Input, Popconfirm, Select, Skeleton, Tag, message } from "antd";
import { ApiOutlined, DeleteOutlined, DownloadOutlined, LinkOutlined, ReloadOutlined, SaveOutlined } from "@ant-design/icons";
import { api } from "../api";
import { errorText } from "../personal-agent/types";
import type { SkillScope } from "../personal-agent/skillScope";
import { changeServerAuth, editableSecretFields, inferServerAuth, safePublicUrl, validApiKeyHeader, type ConnectorConfiguration, type ConnectorSecretField, type ServerAuth } from "./connectorAuth";

type Configuration = ConnectorConfiguration;
type SecretField = ConnectorSecretField;
export type ConnectorState = {
  configuration: Configuration; secret_fields: SecretField[]; links: { label: string; url: string }[];
  revision: string; status: "unconfigured" | "configured" | "verified" | "failed"; error: string; saved: boolean;
  last_checked: string | null;
  servers: { name: string; server_name: string; server_version: string; tool_count: number; tools: { name: string; description: string }[] }[];
};
const CONNECTION_LABELS: Record<string, string> = { unconfigured: "待配置", configured: "配置已保存", verified: "连接验证通过", failed: "连接验证失败" };
export const connectionLabel = (status?: string) => CONNECTION_LABELS[status || "unconfigured"] || "状态异常";

type Props = { itemId: string; name: string; scope: SkillScope; onBusy: (busy: boolean) => void; onChanged: (state: ConnectorState) => void };

export function ConnectorConfigPanel({ itemId, name, scope, onBusy, onChanged }: Props) {
  const [state, setState] = useState<ConnectorState | null>(null);
  const [text, setText] = useState("");
  const [dirty, setDirty] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  const [cleared, setCleared] = useState<Record<string, boolean>>({});
  const [invalidated, setInvalidated] = useState<Record<string, boolean>>({});
  const [authChoices, setAuthChoices] = useState<Record<string, ServerAuth>>({});
  const [headerNames, setHeaderNames] = useState<Record<string, string>>({});
  const operation = useRef(false);
  useEffect(() => { onBusy(busy); }, [busy, onBusy]);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(""); setState(null); setDirty(false); setCleared({}); setInvalidated({}); setAuthChoices({}); setHeaderNames({});
    void api.get<ConnectorState>(`/capability-market/connectors/${itemId}/config`, { params: { scope }, signal: controller.signal })
      .then(({ data }) => { if (!controller.signal.aborted) { setState(data); setText(JSON.stringify(data.configuration, null, 2)); } })
      .catch(failure => { if (!controller.signal.aborted) setError(errorText(failure, "连接配置加载失败")); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [itemId, scope, reload]);

  let configuration: Configuration | null = null;
  let parseError = "";
  try {
    const parsed = JSON.parse(text);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("连接配置必须是JSON对象");
    if (parsed["mcp.json"]) {
      const declared = parsed["mcp.json"].mcpServers;
      if (!declared || typeof declared !== "object" || Array.isArray(declared) || Object.values(declared).some(server => !server || typeof server !== "object" || Array.isArray(server))) throw new Error("mcpServers及每个服务配置必须是JSON对象");
    }
    configuration = parsed;
  } catch (failure) { parseError = failure instanceof Error ? failure.message : "JSON配置无效"; }
  const servers: [string, Configuration][] = configuration?.["mcp.json"]?.mcpServers && typeof configuration["mcp.json"].mcpServers === "object"
    ? Object.entries(configuration["mcp.json"].mcpServers) : [];
  const canVerify = !!servers.length && servers.every(([, server]) => server.url && ["streamableHttp", "streamable-http", "http", "sse"].includes(server.type));

  const editPath = (path: string[], value: string) => {
    if (!configuration) return;
    const next = structuredClone(configuration);
    let target = next;
    for (const part of path.slice(0, -1)) {
      if (!target || typeof target !== "object" || Array.isArray(target) || !Object.hasOwn(target, part)) { setError("此字段已被JSON编辑修改，请保存后重新载入表单"); return; }
      target = target[part];
    }
    if (!target || typeof target !== "object" || Array.isArray(target)) { setError("此字段已被JSON编辑修改，请保存后重新载入表单"); return; }
    Object.defineProperty(target, path.at(-1)!, { value, enumerable: true, writable: true, configurable: true });
    setText(JSON.stringify(next, null, 2)); setDirty(true);
  };
  const accepted = (data: ConnectorState) => {
    setState(data); setText(JSON.stringify(data.configuration, null, 2)); setCleared({}); setInvalidated({}); setHeaderNames({}); setDirty(false); setError(""); onChanged(data);
  };
  const serverAuth = (serverName: string, server: Configuration): ServerAuth => {
    const selected = authChoices[serverName];
    return selected && (selected.mode === "none" || Object.hasOwn(server.headers || {}, selected.headerName)) ? selected : inferServerAuth(server, state?.secret_fields || [], serverName);
  };
  const replaceServer = (serverName: string, server: Configuration) => {
    if (!configuration) return;
    const next = structuredClone(configuration);
    next["mcp.json"].mcpServers[serverName] = server;
    setText(JSON.stringify(next, null, 2)); setDirty(true); setError("");
  };
  const selectAuth = (serverName: string, server: Configuration, mode: ServerAuth["mode"]) => {
    const previous = serverAuth(serverName, server);
    if (previous.mode === mode || mode === "existing") return;
    try {
      const next = changeServerAuth(server, previous, mode);
      replaceServer(serverName, next.server);
      setAuthChoices(choices => ({ ...choices, [serverName]: next.auth }));
      setHeaderNames(names => { const nextNames = { ...names }; delete nextNames[serverName]; return nextNames; });
      setInvalidated(values => {
        const nextValues = { ...values };
        for (const key of [...next.removed, next.auth.headerName].filter(Boolean)) nextValues[JSON.stringify(["mcp.json", "mcpServers", serverName, "headers", key])] = true;
        return nextValues;
      });
    } catch (failure) { setError(errorText(failure, "鉴权配置修改失败")); }
  };
  const renameHeader = (serverName: string, server: Configuration, auth: ServerAuth, headerName: string) => {
    setHeaderNames(names => ({ ...names, [serverName]: headerName })); setDirty(true);
    if (!validApiKeyHeader(headerName)) return;
    if (Object.keys(server.headers || {}).some(key => key !== auth.headerName && key.toLowerCase() === headerName.toLowerCase())) { setError("鉴权请求头与已有请求头冲突"); return; }
    if (headerName === auth.headerName) { setError(""); return; }
    const next = structuredClone(server);
    // 已保存的脱敏值不能迁移到新字段，改名后需要重新填写密钥。
    const value = next.headers[auth.headerName];
    delete next.headers[auth.headerName]; next.headers = { ...next.headers, [headerName]: value };
    replaceServer(serverName, next);
    setAuthChoices(choices => ({ ...choices, [serverName]: { ...auth, headerName } }));
    setInvalidated(values => ({ ...values, [JSON.stringify(["mcp.json", "mcpServers", serverName, "headers", auth.headerName])]: true, [JSON.stringify(["mcp.json", "mcpServers", serverName, "headers", headerName])]: true }));
  };
  const headerError = servers.some(([serverName, server]) => {
    const auth = serverAuth(serverName, server);
    const name = headerNames[serverName] ?? auth.headerName;
    return auth.mode === "apiKey" && (!validApiKeyHeader(name) || name !== auth.headerName);
  });
  const websiteError = servers.some(([, server]) => server.authUrl !== undefined && server.authUrl !== "" && (typeof server.authUrl !== "string" || !safePublicUrl(server.authUrl)));
  const perform = async (action: () => Promise<void>) => {
    if (operation.current) return;
    operation.current = true; setBusy(true); setError("");
    try { await action(); } catch (failure) { setError(errorText(failure, "连接器操作失败")); }
    finally { operation.current = false; setBusy(false); }
  };
  const save = () => perform(async () => {
    if (!configuration || headerError || websiteError) throw new Error("请先修正JSON配置、API Key请求头名称或网站链接");
    let value: Configuration;
    try { value = JSON.parse(text); } catch { throw new Error("JSON格式不正确，请检查配置编辑内容"); }
    const keep = state?.secret_fields.filter(field => {
      let current: any = value;
      for (const part of field.path) current = current?.[part];
      const key = JSON.stringify(field.path);
      return field.configured && current === "" && !cleared[key] && !invalidated[key];
    }).map(field => field.path) || [];
    const { data } = await api.put<ConnectorState>(`/capability-market/connectors/${itemId}/config`, { scope, configuration: value, keep_credentials: keep, revision: state?.revision || "" });
    accepted(data); message.success("连接配置已保存");
  });
  const verify = () => perform(async () => {
    const { data } = await api.post<{ ok: boolean; configuration: ConnectorState }>(`/capability-market/connectors/${itemId}/verify`, { scope, revision: state!.revision }, { timeout: 35000 });
    accepted(data.configuration);
    if (data.ok) message.success("MCP握手与工具目录验证通过");
    else message.error(data.configuration.error);
  });
  const remove = () => perform(async () => {
    const { data } = await api.delete<ConnectorState>(`/capability-market/connectors/${itemId}/config`, { params: { scope, revision: state!.revision } });
    setAuthChoices({}); accepted(data); message.success("连接配置已删除");
  });
  const download = () => {
    if (!state) return;
    const template = structuredClone(state.configuration);
    for (const field of state.secret_fields) {
      let current = template;
      for (const part of field.path.slice(0, -1)) current = current[part];
      current[field.path.at(-1)!] = field.template || "${" + field.path.slice(2).join("_").replace(/[^A-Za-z0-9_]/g, "_").toUpperCase() + "}";
    }
    const url = URL.createObjectURL(new Blob([JSON.stringify(template, null, 2)], { type: "application/json;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = name.replace(/[\\/:*?"<>|]/g, "_") + "-connector.json";
    document.body.appendChild(link); link.click(); link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  if (loading) return <Skeleton active />;
  return <section className="connector-config-panel" aria-label="连接器配置">
    {error && <Alert type="error" showIcon title={error} action={!state ? <Button icon={<ReloadOutlined />} onClick={() => setReload(value => value + 1)}>重新载入</Button> : undefined} />}
    {state && <>
      <div className="connector-config-state"><Tag>{scope === "global" ? "全局配置" : "个人配置"}</Tag><Tag color={state.status === "verified" ? "success" : state.status === "failed" ? "error" : "default"}>{connectionLabel(state.status)}</Tag></div>
      {state.error && <Alert type="error" showIcon title={state.error} />}
      <div className="connector-config-link-section"><h4>官网与账号 / 密钥入口</h4><div className="connector-config-links">{state.links.map(link => <Button key={link.url} icon={<LinkOutlined />} href={link.url} target="_blank" rel="noopener noreferrer">{link.label}</Button>)}</div>{!state.links.length && <Tag>未提供网站链接</Tag>}</div>
      <Form layout="vertical" className="connector-config-form">
        {servers.map(([serverName, server]) => {
          const auth = serverAuth(serverName, server);
          const path = ["mcp.json", "mcpServers", serverName, "headers", auth.headerName];
          const key = JSON.stringify(path);
          const saved = invalidated[key] ? undefined : state.secret_fields.find(field => JSON.stringify(field.path) === key);
          const value = server.headers?.[auth.headerName];
          const token = typeof value === "string" ? auth.mode === "bearer" ? value.replace(/^Bearer\s+/i, "") : value : "";
          const headerName = headerNames[serverName] ?? auth.headerName;
          const authUrl = typeof server.authUrl === "string" ? server.authUrl : "";
          const website = safePublicUrl(authUrl);
          return <fieldset key={serverName}><legend>{serverName}</legend>
          {server.url !== undefined ? <>
            <Form.Item label="接入方式"><Select disabled={busy} value={server.type} onChange={value => editPath(["mcp.json", "mcpServers", serverName, "type"], value)} options={[{ value: "streamableHttp", label: "Streamable HTTP" }, { value: "http", label: "HTTP" }, { value: "streamable-http", label: "Streamable HTTP（原包命名）" }, { value: "sse", label: "SSE" }]} /></Form.Item>
            <Form.Item label="API地址 / MCP服务地址"><Input disabled={busy} value={server.url} onChange={event => editPath(["mcp.json", "mcpServers", serverName, "url"], event.target.value)} /></Form.Item>
            <Form.Item label="鉴权方式"><Select disabled={busy} value={auth.mode} onChange={mode => selectAuth(serverName, server, mode)} options={[{ value: "none", label: "无需 Token" }, { value: "bearer", label: "Bearer Token" }, { value: "apiKey", label: "API Key" }, ...(auth.mode === "existing" ? [{ value: "existing", label: "保留原有请求头" }] : [])]} /></Form.Item>
            {auth.mode === "existing" && <Tag>原有鉴权协议未判定</Tag>}
            {auth.mode === "apiKey" && <Form.Item label="API Key请求头名称" validateStatus={!validApiKeyHeader(headerName) || headerName !== auth.headerName ? "error" : undefined} help={!validApiKeyHeader(headerName) ? "请输入合法请求头名称，不可使用Authorization或传输控制请求头" : headerName !== auth.headerName ? "请求头名称与已有字段冲突" : undefined}><Input disabled={busy} value={headerName} onChange={event => renameHeader(serverName, server, auth, event.target.value)} /></Form.Item>}
            {(auth.mode === "bearer" || auth.mode === "apiKey") && <Form.Item label={auth.mode === "bearer" ? "Token" : "API Key"}><Input.Password autoComplete="new-password" disabled={busy} value={token} placeholder={saved?.configured && !cleared[key] ? "已保存，留空保留原值" : "填写密钥"} onChange={event => { const input = event.target.value; editPath(path, input && auth.mode === "bearer" ? "Bearer " + input : input); }} />
              {saved?.configured && <Checkbox disabled={busy || !!token} checked={!!cleared[key]} onChange={event => { setCleared(values => ({ ...values, [key]: event.target.checked })); setDirty(true); }}>删除已保存值</Checkbox>}
            </Form.Item>}
            <Form.Item label="官网 / 获取密钥页面" validateStatus={authUrl && !website ? "error" : undefined} help={authUrl && !website ? "请输入有效HTTP/HTTPS公开链接，不可包含账号密码或密钥参数" : undefined}><div className="connector-config-website-field"><Input disabled={busy} value={authUrl} onChange={event => editPath(["mcp.json", "mcpServers", serverName, "authUrl"], event.target.value)} /><Button icon={<LinkOutlined />} aria-label="打开官网 / 获取密钥页面" title="打开官网 / 获取密钥页面" disabled={!website} href={website || undefined} target="_blank" rel="noopener noreferrer" /></div></Form.Item>
          </> : <Tag>stdio · 本地运行器</Tag>}
        </fieldset>;
        })}
        {editableSecretFields(configuration, state.secret_fields).filter(field => {
          const server = configuration?.["mcp.json"]?.mcpServers?.[field.path[2]];
          if (!server || server.url === undefined || field.path[3] !== "headers") return true;
          const auth = serverAuth(field.path[2], server);
          return auth.mode === "existing" || field.path[4] !== auth.headerName;
        }).map(field => {
          let value: any = configuration;
          for (const part of field.path) value = value?.[part];
          const key = JSON.stringify(field.path);
          const configured = field.configured && !invalidated[key];
          return <Form.Item key={key} label={field.label}><Input.Password autoComplete="new-password" disabled={busy} value={typeof value === "string" ? value : ""} placeholder={configured ? "已保存，留空保留原值" : field.template || "填写凭据"} onChange={event => { editPath(field.path, event.target.value); setCleared(previous => ({ ...previous, [key]: false })); }} />
            {configured && <Checkbox disabled={busy || !!value} checked={!!cleared[key]} onChange={event => { setCleared(previous => ({ ...previous, [key]: event.target.checked })); setDirty(true); }}>删除已保存值</Checkbox>}
          </Form.Item>;
        })}
      </Form>
      {!canVerify && <Alert type="warning" showIcon title="CLI或stdio运行器未接入，配置可保存并下载，不能进行远程连接验证" />}
      <details><summary>编辑完整JSON配置</summary><Input.TextArea disabled={busy} value={text} onChange={event => { setText(event.target.value); setAuthChoices({}); setHeaderNames({}); setDirty(true); }} autoSize={{ minRows: 8, maxRows: 20 }} spellCheck={false} />{parseError && <Alert type="error" title={parseError} />}</details>
      <div className="connector-config-actions">
        <Button type="primary" icon={<SaveOutlined />} loading={busy} disabled={busy || !configuration || headerError || websiteError} onClick={() => void save()}>保存配置</Button>
        <Button icon={<ApiOutlined />} loading={busy} disabled={!state.saved || dirty || !canVerify} onClick={() => void verify()}>测试连接</Button>
        <Button icon={<DownloadOutlined />} disabled={busy || dirty} onClick={download}>下载配置模板</Button>
        {state.saved && <Popconfirm title="删除此连接器配置和已保存的凭据？" onConfirm={remove}><Button danger icon={<DeleteOutlined />} disabled={busy}>删除配置</Button></Popconfirm>}
      </div>
      {state.last_checked && <p className="connector-config-checked">最近验证：{new Date(state.last_checked).toLocaleString()}</p>}
      {!!state.servers.length && <details><summary>服务工具目录（{state.servers.reduce((total, server) => total + server.tool_count, 0)}）</summary>{state.servers.map(server => <section key={server.name}><h4>{server.server_name} · {server.server_version}</h4>{server.tools.map(tool => <p key={tool.name}><strong>{tool.name}</strong><br />{tool.description}</p>)}</section>)}</details>}
    </>}
  </section>;
}
