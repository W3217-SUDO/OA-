import { useState } from "react";
import { Alert, Button, Form, Input, Popconfirm, Select, Spin, Tag, Tooltip } from "antd";
import { ApiOutlined, CloseOutlined, DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined, SaveOutlined } from "@ant-design/icons";
import type { usePersonalMcpConnection } from "./usePersonalMcpConnection";
import "./personal-mcp-connection.css";

type Props = { connection: ReturnType<typeof usePersonalMcpConnection> };

const statusLabel: Record<string, string> = { configured: "已保存 · 未验证", verified: "握手与目录已验证", failed: "连接检测失败", unconfigured: "待配置" };

export function PersonalMcpConnectionCard({ connection: mcp }: Props) {
  const [configText, setConfigText] = useState("");
  const { draft, connection, busy } = mcp;
  const update = <K extends keyof typeof draft>(key: K, value: typeof draft[K]) => mcp.update({ ...draft, [key]: value });
  const importConfig = (text: string) => { mcp.importConfig(text); setConfigText(""); };
  const newConnection = () => { setConfigText(""); mcp.newConnection(); };

  return <section className="personal-mcp-card" aria-label="连接我的 MCP">
    <header className="personal-mcp-heading">
      <strong><ApiOutlined />连接我的 MCP</strong>
      <Tooltip title="关闭并清除未保存凭据"><Button type="text" icon={<CloseOutlined />} aria-label="关闭并清除未保存凭据" onClick={mcp.close} /></Tooltip>
    </header>
    <div className="personal-mcp-body">
      {mcp.error && <Alert type="error" showIcon title={mcp.error} />}
      {connection ? <div className="personal-mcp-result" role="status">
        <strong>{connection.name}</strong>
        <Tag color={connection.status === "verified" ? "success" : connection.status === "failed" ? "error" : "default"}>{statusLabel[connection.status] || "状态未知"}</Tag>
        {connection.status === "verified" && <span>发现 {connection.servers.reduce((sum, server) => sum + server.tool_count, 0)} 个工具。{connection.capabilities.tool_call ? "支持发起工具调用，执行前需确认；本次检测未执行工具。" : "当前仅验证握手与工具目录，工具执行尚不可用。"}</span>}
        <div className="personal-mcp-actions">
          <Button icon={<ReloadOutlined />} loading={busy} disabled={busy} onClick={() => void mcp.retryTest()}>重新检测</Button>
          <Button icon={<EditOutlined />} disabled={busy} onClick={() => void mcp.edit(connection)}>修改配置</Button>
          <Button icon={<PlusOutlined />} disabled={busy} onClick={newConnection}>添加另一个连接</Button>
        </div>
      </div> : <Form layout="vertical" onFinish={() => void mcp.saveAndConnect()} autoComplete="off">
        <Form.Item label="粘贴 MCP 配置" htmlFor="personal-mcp-config">
          <div className="personal-mcp-import">
            <Input.Password id="personal-mcp-config" value={configText} visibilityToggle={false} autoComplete="new-password" disabled={busy} placeholder="MCP URL 或 JSON 配置" onChange={event => setConfigText(event.target.value)} onPaste={event => { event.preventDefault(); importConfig(event.clipboardData.getData("text")); }} />
            <Button disabled={busy || !configText.trim()} onClick={() => importConfig(configText)}>载入配置</Button>
          </div>
        </Form.Item>
        <div className="personal-mcp-fields">
          <Form.Item label="连接名称" htmlFor="personal-mcp-name" required><Input id="personal-mcp-name" value={draft.name} maxLength={100} disabled={busy} onChange={event => update("name", event.target.value)} /></Form.Item>
          <Form.Item label="MCP 地址" htmlFor="personal-mcp-url" required><Input.Password id="personal-mcp-url" value={draft.server_url} visibilityToggle={false} autoComplete="new-password" disabled={busy} placeholder="https://…/mcp" onChange={event => update("server_url", event.target.value)} /></Form.Item>
          <Form.Item label="传输方式" htmlFor="personal-mcp-transport"><Select id="personal-mcp-transport" value={draft.transport} disabled={busy} onChange={value => update("transport", value)} options={[{ value: "streamable_http", label: "Streamable HTTP" }, { value: "sse", label: "SSE" }]} /></Form.Item>
          <Form.Item label="认证方式" htmlFor="personal-mcp-auth"><Select id="personal-mcp-auth" value={draft.auth_type} disabled={busy} onChange={value => mcp.update({ ...draft, auth_type: value, credential: "" })} options={[{ value: "none", label: "无需 Token" }, { value: "bearer", label: "Bearer Token" }, { value: "api_key", label: "API Key" }]} /></Form.Item>
          {draft.auth_type === "api_key" && <Form.Item label="API Key 请求头" htmlFor="personal-mcp-header" required><Input id="personal-mcp-header" value={draft.api_key_header} disabled={busy} onChange={event => update("api_key_header", event.target.value)} /></Form.Item>}
          {draft.auth_type !== "none" && <Form.Item label={draft.auth_type === "bearer" ? "Bearer Token" : "API Key"} htmlFor="personal-mcp-key" required={!mcp.credentialSaved}><Input.Password id="personal-mcp-key" value={draft.credential} visibilityToggle={false} autoComplete="new-password" disabled={busy} placeholder={mcp.credentialSaved ? "已保存，留空保留原凭据" : ""} onChange={event => update("credential", event.target.value)} /></Form.Item>}
        </div>
        <div className="personal-mcp-actions"><Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={busy} disabled={busy}>{mcp.editing ? "确认更新并连接" : "确认保存并连接"}</Button>{mcp.editing && <Button disabled={busy} onClick={newConnection}>取消修改</Button>}<span>仅本人可见 · 凭据加密保存 · 不进入模型或聊天记录</span></div>
      </Form>}
      <div className="personal-mcp-list-heading"><strong>我的 MCP</strong><Tooltip title="刷新个人连接"><Button type="text" icon={<ReloadOutlined />} aria-label="刷新个人连接" loading={mcp.listing} disabled={busy || mcp.listing} onClick={() => void mcp.refresh()} /></Tooltip></div>
      {mcp.listError && <Alert type="error" title={mcp.listError} showIcon />}
      {mcp.listing ? <Spin size="small" /> : <ul className="personal-mcp-list">
        {mcp.items.map(item => <li key={item.id}><div><strong>{item.name}</strong><span>{statusLabel[item.status] || "状态未知"}</span></div><div className="personal-mcp-row-actions">
          <Tooltip title="检测连接"><Button icon={<ApiOutlined />} aria-label={`检测连接：${item.name}`} disabled={busy} onClick={() => void mcp.retryTest(item)} /></Tooltip>
          <Tooltip title="修改配置"><Button icon={<EditOutlined />} aria-label={`修改配置：${item.name}`} disabled={busy} onClick={() => void mcp.edit(item)} /></Tooltip>
          <Popconfirm title="删除此个人 MCP 连接？" description="已保存的连接和凭据将被删除" okText="确认删除" cancelText="取消" onConfirm={() => mcp.remove(item)} disabled={busy}><Tooltip title="删除连接"><Button danger icon={<DeleteOutlined />} aria-label={`删除连接：${item.name}`} disabled={busy} /></Tooltip></Popconfirm>
        </div></li>)}
        {!mcp.items.length && !mcp.listError && <li>暂无已保存的个人连接</li>}
      </ul>}
    </div>
  </section>;
}
