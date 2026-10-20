import { useEffect } from "react";
import { Alert, Button, Drawer, Empty, Modal, Tag, Tooltip } from "antd";
import { ApiOutlined, DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import { PersonalMcpConnectionCard } from "../personal-agent/PersonalMcpConnectionCard";
import { usePersonalMcpConnection } from "../personal-agent/usePersonalMcpConnection";
import { connectionLabel } from "./ConnectorConfigPanel";
import "./global-mcp-workspace.css";

type Props = { active: boolean; canManage: boolean };

export function GlobalMcpWorkspace({ active, canManage }: Props) {
  const mcp = usePersonalMcpConnection("agent-admin-global-mcp");
  useEffect(() => { if (active) void mcp.refresh(); }, [active]);
  const globals = mcp.items.filter(item => item.scope === "global");
  const canCreate = canManage && mcp.defaultScope === "global";
  const close = () => { mcp.close(); void mcp.refresh(); };

  const openNew = () => {
    mcp.newConnection();
    mcp.show();
  };
  const openEdit = (item: typeof globals[number]) => {
    mcp.show();
    void mcp.edit(item);
  };
  const remove = (item: typeof globals[number]) => Modal.confirm({
    title: `删除全局 MCP“${item.name}”？`,
    content: "删除后全所账号将无法再使用此连接；请确认没有业务流程依赖它。",
    okText: "确认删除", cancelText: "取消", okButtonProps: { danger: true },
    onOk: () => mcp.remove(item),
  });

  return <section className="global-mcp-workspace" aria-label="全局 MCP 连接">
    <header className="global-mcp-workspace-header">
      <div><h2>全局 MCP</h2><p>管理已共享的远程连接；验证仅检查握手和工具目录，调用外部工具仍需前端确认。</p></div>
      <div className="global-mcp-workspace-actions">
        <Tooltip title="刷新连接"><Button icon={<ReloadOutlined />} aria-label="刷新连接" loading={mcp.listing} onClick={() => void mcp.refresh()} /></Tooltip>
        {canCreate && <Button type="primary" icon={<PlusOutlined />} onClick={openNew}>新增全局 MCP</Button>}
      </div>
    </header>
    {mcp.error && <Alert type="error" showIcon title={mcp.error} />}
    {mcp.listError && <Alert type="error" showIcon title={mcp.listError} action={<Button onClick={() => void mcp.refresh()}>重试</Button>} />}
    {canManage && mcp.defaultScope === "personal" && <Alert type="info" showIcon title="当前账号可以管理已有全局连接；新建连接的服务端默认范围为个人，暂不提供全局新建。" />}
    {!canManage && !mcp.listing && <Alert type="info" showIcon title="当前账号只能查看和使用全局连接，配置由管理员维护。" />}
    {!mcp.listing && !mcp.listError && !globals.length && <Empty description="尚无全局 MCP 连接" />}
    <div className="global-mcp-workspace-list">
      {globals.map(item => <article key={item.id}>
        <div className="global-mcp-workspace-summary">
          <strong>{item.name}</strong>
          <Tag color={item.status === "verified" ? "success" : item.status === "failed" ? "error" : "default"}>{connectionLabel(item.status)}</Tag>
          <span>全局共享</span>
        </div>
        {canManage && item.can_manage && <div className="global-mcp-workspace-row-actions">
          <Tooltip title="验证连接"><Button icon={<ApiOutlined />} aria-label={`验证连接：${item.name}`} disabled={mcp.busy} onClick={() => { mcp.show(); void mcp.retryTest(item); }} /></Tooltip>
          <Tooltip title="修改配置"><Button icon={<EditOutlined />} aria-label={`修改配置：${item.name}`} disabled={mcp.busy} onClick={() => openEdit(item)} /></Tooltip>
          <Tooltip title="删除连接"><Button danger icon={<DeleteOutlined />} aria-label={`删除连接：${item.name}`} disabled={mcp.busy} onClick={() => remove(item)} /></Tooltip>
        </div>}
      </article>)}
    </div>
    <Drawer title="全局 MCP 配置" open={mcp.open && canManage} onClose={close} width={680} destroyOnHidden maskClosable={!mcp.busy} closable={!mcp.busy} rootClassName="global-mcp-workspace-drawer">
      {mcp.open && <PersonalMcpConnectionCard connection={{ ...mcp, close, items: globals }} allowNewConnection={false} allowConfigImport={false} />}
    </Drawer>
  </section>;
}
