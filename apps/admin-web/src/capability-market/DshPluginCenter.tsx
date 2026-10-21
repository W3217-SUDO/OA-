import { useCallback, useEffect, useRef, useState } from "react";
import { Alert, Button, Empty, Form, Input, Modal, Space, Switch, Tag, message } from "antd";
import { ApiOutlined, DeleteOutlined, DownloadOutlined, LinkOutlined, ReloadOutlined } from "@ant-design/icons";
import { api } from "../api";
import { errorText } from "../personal-agent/types";
import "./dsh-plugin-center.css";

type Plugin = { name: string; version: string; description: string; source: string; enabled: boolean; error: string };
type Overview = { items: Plugin[]; revision: string; package_manager_ready: boolean; error: string; effective: string };
type InstallForm = { spec: string; builds?: string };

export function DshPluginCenter({ active, canManage, onBusy }: {
  active: boolean; canManage: boolean; onBusy: (busy: boolean) => void;
}) {
  const [state, setState] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const operation = useRef(false);
  const [form] = Form.useForm<InstallForm>();
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setState((await api.get<Overview>("/agent-admin/dsh-plugins")).data); }
    catch (failure) { setError(errorText(failure, "DSH 插件列表加载失败")); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { if (active && canManage) void load(); }, [active, canManage, load]);

  const mutate = async (action: "install" | "toggle" | "remove", data: object, key: string) => {
    if (operation.current) return;
    operation.current = true;
    setBusy(key); setError(""); onBusy(true);
    try {
      const result = await api.post<Overview>(`/agent-admin/dsh-plugins/${action}`, data, { timeout: 200000 });
      setState(result.data);
      message.success(action === "install" ? "原生插件已安装，后续消息加载新配置" : action === "remove" ? "插件已卸载，后续消息不再加载" : "插件启用状态已更新");
      if (action === "install") form.resetFields();
    } catch (failure) { setError(errorText(failure, "DSH 插件操作失败，未确认新配置生效")); }
    finally { operation.current = false; setBusy(""); onBusy(false); }
  };
  const remove = (item: Plugin) => Modal.confirm({
    title: `卸载 ${item.name}？`, content: "后续个人空间和案件空间消息将不再加载此插件；已有对话、文件与记忆保留。",
    okText: "卸载插件", cancelText: "取消", okButtonProps: { danger: true },
    onOk: () => mutate("remove", { name: item.name }, item.name),
  });

  return <section className="dsh-plugin-center" aria-label="DSH 插件中心">
    <header className="dsh-plugin-heading">
      <div><span className="dsh-plugin-eyebrow">DEEPSEEK HARNESS</span><h2><ApiOutlined />DSH 插件中心</h2>
        <p>为智能体安装原生插件，扩展工具、记忆与工作流能力。个人空间和案件空间保持独立。</p></div>
      <Button icon={<ReloadOutlined />} loading={loading} disabled={!!busy || !canManage} onClick={() => void load()}>刷新列表</Button>
    </header>
    {!canManage && <Alert type="info" showIcon title="仅系统管理员可以管理 DSH 原生插件。" />}
    {error && <Alert type="error" showIcon title="插件操作未完成" description={<pre className="dsh-plugin-error">{error}</pre>} />}
    {state?.error && <Alert type="warning" showIcon title={state.error} />}
    {!!busy && <p role="status">正在安装或更新插件并校验配置，请勿重复操作。</p>}
    {canManage && <div className="dsh-plugin-install">
      <h3>安装原生插件</h3><p>粘贴 npm 包名、GitHub 仓库地址，或作者提供的 dsh plugin add 安装命令。Skill 仍在“全局 Skill”中管理。</p>
      <Form form={form} layout="vertical" onFinish={values => void mutate("install", {
        spec: values.spec.trim(), allow_builds: (values.builds || "").split(/[,，\s]+/).filter(Boolean),
      }, "install")} disabled={!!busy || !state?.package_manager_ready}>
        <div className="dsh-plugin-install-row"><Form.Item name="spec" label="插件来源" extra="安装命令只用于提取包名；其中的 profile 不会切换 OA 配置。" rules={[{ required: true, whitespace: true, message: "请输入插件包名、GitHub 地址或 dsh 安装命令" }]}>
          <Input placeholder="例如 dsh plugin --profile web add @作者/插件名" autoComplete="off" maxLength={500} />
        </Form.Item><Button type="primary" htmlType="submit" icon={<DownloadOutlined />} loading={busy === "install"}>安装到系统</Button></div>
        <details><summary>需要运行构建脚本的插件</summary>
          <Form.Item name="builds" label="允许构建的准确包名" extra="仅在插件要求 prepare / 构建步骤时填写，多个包名用逗号分隔。">
            <Input placeholder="填写插件作者声明的准确 npm 包名" autoComplete="off" />
          </Form.Item>
        </details>
      </Form>
    </div>}
    <section className="dsh-plugin-community" aria-label="开源插件社区">
      <h3>去开源社区找插件</h3>
      <p>在社区中浏览插件，将作者提供的 npm 包名、GitHub 仓库地址或 dsh plugin add 安装命令复制到上方安装。</p>
      <div className="dsh-plugin-community-links">
        <Button href="https://dshmarketplace.dev/" target="_blank" rel="noopener noreferrer" icon={<LinkOutlined />}>DSH Marketplace · 社区插件目录</Button>
        <Button href="https://github.com/deepseek-ai/deepseek-harness/discussions/categories/show-your-plugins" target="_blank" rel="noopener noreferrer" icon={<LinkOutlined />}>官方插件交流区</Button>
        <Button href="https://github.com/topics/dsh-plugin" target="_blank" rel="noopener noreferrer" icon={<LinkOutlined />}>GitHub 插件仓库</Button>
      </div>
      <small>社区页面将在新标签页打开，安装仍在本系统完成。</small>
    </section>
    <div className="dsh-plugin-list-heading"><h3>已安装的原生插件 <span>{state?.items.length ?? 0}</span></h3>
      <p>{state?.effective || "安装后在后续消息中加载；插件自身的界面扩展需兼容 OA。"}</p></div>
    {loading && !state && <p role="status">正在读取插件配置…</p>}
    {!loading && state && !state.items.length && <Empty description="尚未安装 DSH 原生插件" />}
    <div className="dsh-plugin-list">{state?.items.map(item => <article key={item.name}>
      <div className="dsh-plugin-info"><div className="dsh-plugin-title"><strong>{item.name}</strong><span>{item.version}</span>
        <Tag color={item.error ? "error" : item.enabled ? "success" : "default"}>{item.error ? "配置异常" : item.enabled ? "已启用" : "已停用"}</Tag></div>
        <p>{item.description || "插件作者未提供说明"}</p><small>安装来源：{item.source}</small>
        {item.error && <p className="dsh-plugin-failure">{item.error}</p>}</div>
      <Space wrap><Switch aria-label={`${item.name}启用状态`} checked={item.enabled} loading={busy === item.name}
        disabled={!!busy || !canManage || (!!item.error && !item.enabled)} onChange={enabled => void mutate("toggle", { name: item.name, enabled }, item.name)} />
        <Button danger icon={<DeleteOutlined />} disabled={!!busy || !canManage || !state.package_manager_ready} onClick={() => remove(item)}>卸载</Button></Space>
    </article>)}</div>
  </section>;
}
