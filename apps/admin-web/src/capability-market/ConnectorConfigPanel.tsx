import { useEffect, useRef, useState } from "react";
import { Alert, Button, Checkbox, Form, Input, Popconfirm, Select, Skeleton, Tag, message } from "antd";
import { ApiOutlined, DeleteOutlined, DownloadOutlined, LinkOutlined, ReloadOutlined, SaveOutlined } from "@ant-design/icons";
import { api } from "../api";
import { errorText } from "../personal-agent/types";
import type { SkillScope } from "../personal-agent/skillScope";

type Configuration = Record<string, any>;
type SecretField = { path: string[]; label: string; configured: boolean; template: string };
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
  const operation = useRef(false);
  useEffect(() => { onBusy(busy); }, [busy, onBusy]);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(""); setState(null); setDirty(false); setCleared({});
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
      if (!target || typeof target !== "object" || !Object.hasOwn(target, part)) { setError("此字段已被JSON编辑修改，请保存后重新载入表单"); return; }
      target = target[part];
    }
    target[path.at(-1)!] = value;
    setText(JSON.stringify(next, null, 2)); setDirty(true);
  };
  const accepted = (data: ConnectorState) => {
    setState(data); setText(JSON.stringify(data.configuration, null, 2)); setCleared({}); setDirty(false); setError(""); onChanged(data);
  };
  const perform = async (action: () => Promise<void>) => {
    if (operation.current) return;
    operation.current = true; setBusy(true); setError("");
    try { await action(); } catch (failure) { setError(errorText(failure, "连接器操作失败")); }
    finally { operation.current = false; setBusy(false); }
  };
  const save = () => perform(async () => {
    let value: Configuration;
    try { value = JSON.parse(text); } catch { throw new Error("JSON格式不正确，请检查配置编辑内容"); }
    const keep = state?.secret_fields.filter(field => {
      let current: any = value;
      for (const part of field.path) current = current?.[part];
      return field.configured && current === "" && !cleared[JSON.stringify(field.path)];
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
    accepted(data); message.success("连接配置已删除");
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
      <div className="connector-config-links">{state.links.map(link => <Button key={link.url} icon={<LinkOutlined />} href={link.url} target="_blank" rel="noopener noreferrer">{link.label}</Button>)}</div>
      <Form layout="vertical" className="connector-config-form">
        {servers.map(([serverName, server]) => <fieldset key={serverName}><legend>{serverName}</legend>
          {server.url !== undefined ? <>
            <Form.Item label="接入方式"><Select disabled={busy} value={server.type} onChange={value => editPath(["mcp.json", "mcpServers", serverName, "type"], value)} options={[{ value: "streamableHttp", label: "Streamable HTTP" }, { value: "http", label: "HTTP" }, { value: "streamable-http", label: "Streamable HTTP（原包命名）" }, { value: "sse", label: "SSE" }]} /></Form.Item>
            <Form.Item label="MCP服务地址"><Input disabled={busy} value={server.url} onChange={event => editPath(["mcp.json", "mcpServers", serverName, "url"], event.target.value)} /></Form.Item>
          </> : <Tag>stdio · 本地运行器</Tag>}
        </fieldset>)}
        {state.secret_fields.map(field => {
          let value: any = configuration;
          for (const part of field.path) value = value?.[part];
          const key = JSON.stringify(field.path);
          return <Form.Item key={key} label={field.label}><Input.Password autoComplete="new-password" disabled={busy} value={typeof value === "string" ? value : ""} placeholder={field.configured ? "已保存，留空保留原值" : field.template || "填写凭据"} onChange={event => { editPath(field.path, event.target.value); setCleared(previous => ({ ...previous, [key]: false })); }} />
            {field.configured && <Checkbox disabled={busy || !!value} checked={!!cleared[key]} onChange={event => { setCleared(previous => ({ ...previous, [key]: event.target.checked })); setDirty(true); }}>删除已保存值</Checkbox>}
          </Form.Item>;
        })}
      </Form>
      {!canVerify && <Alert type="warning" showIcon title="CLI或stdio运行器未接入，配置可保存并下载，不能进行远程连接验证" />}
      <details><summary>编辑完整JSON配置</summary><Input.TextArea disabled={busy} value={text} onChange={event => { setText(event.target.value); setDirty(true); }} autoSize={{ minRows: 8, maxRows: 20 }} spellCheck={false} />{parseError && <Alert type="error" title={parseError} />}</details>
      <div className="connector-config-actions">
        <Button type="primary" icon={<SaveOutlined />} loading={busy} disabled={!configuration} onClick={() => void save()}>保存配置</Button>
        <Button icon={<ApiOutlined />} loading={busy} disabled={!state.saved || dirty || !canVerify} onClick={() => void verify()}>测试连接</Button>
        <Button icon={<DownloadOutlined />} disabled={busy || dirty} onClick={download}>下载配置模板</Button>
        {state.saved && <Popconfirm title="删除此连接器配置和已保存的凭据？" onConfirm={remove}><Button danger icon={<DeleteOutlined />} disabled={busy}>删除配置</Button></Popconfirm>}
      </div>
      {state.last_checked && <p className="connector-config-checked">最近验证：{new Date(state.last_checked).toLocaleString()}</p>}
      {!!state.servers.length && <details><summary>服务工具目录（{state.servers.reduce((total, server) => total + server.tool_count, 0)}）</summary>{state.servers.map(server => <section key={server.name}><h4>{server.server_name} · {server.server_version}</h4>{server.tools.map(tool => <p key={tool.name}><strong>{tool.name}</strong><br />{tool.description}</p>)}</section>)}</details>}
    </>}
  </section>;
}
