import { useCallback, useEffect, useState } from "react";
import { Alert, Button, Empty, Form, Input, Modal, Radio, Select, Space, Tag, message } from "antd";
import { ApiOutlined, DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { api } from "../api";
import { errorText } from "../personal-agent/types";
import "./dsh-plugin-center.css";

// 陶威 11-03：智能体设置里配置 DSH 调用的模型服务商，可以切换；Key 加密保存、不回显，只有系统管理员可见。
export type ProviderType = { value: string; label: string; api: string; base_url: string; model: string };
export type Provider = {
  id: string; name: string; type: string; base_url: string; model: string; key_set: boolean; key_source: "server" | "page";
  updated_by: string; updated_at: string; verified_at: string; verify_message: string; verify_ok: boolean | null;
};
export type ProvidersState = { active_id: string; providers: Provider[]; revision: number; types: ProviderType[] };
type ProviderForm = { name: string; type: string; base_url: string; model: string; api_key?: string };

const BASE = "/agent-admin/model-providers";

export function DshModelProviders({ active, canManage, onBusy }: { active: boolean; canManage: boolean; onBusy: (busy: boolean) => void }) {
  const [state, setState] = useState<ProvidersState | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [editing, setEditing] = useState<Provider | "new" | null>(null);
  const [initial, setInitial] = useState<ProviderForm | undefined>();
  const [form] = Form.useForm<ProviderForm>();

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { setState((await api.get<ProvidersState>(BASE)).data); }
    catch (failure) { setError(errorText(failure, "模型服务商加载失败")); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { if (active && canManage) void load(); }, [active, canManage, load]);

  const run = async (key: string, action: () => Promise<ProvidersState | void>, done: string) => {
    if (busy) return false;
    setBusy(key); setError(""); onBusy(true);
    try {
      const next = await action();
      if (next) setState(next);
      message.success(done);
      return true;
    } catch (failure) { setError(errorText(failure, "操作未完成")); return false; }
    finally { setBusy(""); onBusy(false); }
  };

  const typeOf = (code: string) => state?.types.find(item => item.value === code);
  const openEditor = (item: Provider | "new") => {
    const first = state?.types[0];
    // 弹窗关闭时表单会卸载，打开时用 initialValues 带出默认值。
    setInitial(item === "new"
      ? { name: first?.label || "", type: first?.value || "", base_url: first?.base_url || "", model: first?.model || "", api_key: "" }
      : { name: item.name, type: item.type, base_url: item.base_url, model: item.model, api_key: "" });
    setEditing(item);
  };
  const changeType = (code: string) => {
    const type = typeOf(code);
    if (editing === "new" && type) form.setFieldsValue({ name: type.label, base_url: type.base_url, model: type.model });
  };
  const save = async () => {
    const values = await form.validateFields();
    const body = { ...values, api_key: (values.api_key || "").trim() };
    const ok = await run("save", async () => (editing === "new"
      ? await api.post<ProvidersState>(BASE, body)
      : await api.put<ProvidersState>(`${BASE}/${(editing as Provider).id}`, body)).data, "服务商已保存");
    if (ok) { setEditing(null); form.resetFields(); }
  };
  const activate = (item: Provider) => Modal.confirm({
    title: `切换到“${item.name}”？`, content: "切换后智能体新的请求马上使用这个服务商，正在进行的回答不受影响。",
    okText: "切换", cancelText: "取消",
    onOk: () => run("activate", async () => (await api.post<ProvidersState>(`${BASE}/activate`, { id: item.id })).data, "已切换服务商"),
  });
  const remove = (item: Provider) => Modal.confirm({
    title: `删除“${item.name}”？`, content: "删除后不再出现在列表里；记录保留在系统中。", okText: "删除", cancelText: "取消",
    okButtonProps: { danger: true },
    onOk: () => run(item.id, async () => (await api.delete<ProvidersState>(`${BASE}/${item.id}`)).data, "服务商已删除"),
  });
  const test = async (item: Provider) => {
    if (busy) return;
    setBusy("test:" + item.id); setError("");
    try {
      const { data } = await api.post<{ ok: boolean; message: string }>(`${BASE}/${item.id}/test`, {}, { timeout: 40000 });
      if (data.ok) message.success(data.message); else message.error(data.message);
      await load();
    } catch (failure) { setError(errorText(failure, "测试连接未完成")); }
    finally { setBusy(""); }
  };

  const editingProvider = editing && editing !== "new" ? editing : null;
  return <section className="dsh-plugin-center" aria-label="DSH API 配置">
    <header className="dsh-plugin-heading">
      <div><span className="dsh-plugin-eyebrow">DEEPSEEK HARNESS</span><h2><ApiOutlined />DSH API 配置</h2>
        <p>配置智能体调用的模型服务商。“当前使用”切换后，新的请求马上走新的服务商，不用重启。</p></div>
      <Space wrap>
        <Button icon={<ReloadOutlined />} loading={loading} disabled={!!busy || !canManage} onClick={() => void load()}>刷新</Button>
        {canManage && <Button type="primary" icon={<PlusOutlined />} disabled={!!busy || !state} onClick={() => openEditor("new")}>新增服务商</Button>}
      </Space>
    </header>
    {!canManage && <Alert type="info" showIcon title="DSH API 配置只有系统管理员可以查看和修改。" />}
    {error && <Alert type="error" showIcon title={error} />}
    {loading && !state && <p role="status">正在读取服务商…</p>}
    {!loading && state && !state.providers.length && <Empty description="还没有服务商" />}
    {state && <div className="dsh-provider-list" role="radiogroup" aria-label="当前使用的服务商">
      {state.providers.map(item => <article key={item.id} className={item.id === state.active_id ? "is-active" : undefined}>
        <div className="dsh-plugin-info">
          <div className="dsh-plugin-title">
            <Radio checked={item.id === state.active_id} disabled={!canManage || !!busy} aria-label={`使用${item.name}`}
              onChange={() => item.id !== state.active_id && activate(item)} />
            <strong>{item.name}</strong><span>{typeOf(item.type)?.label || item.type}</span>
            {item.id === state.active_id && <Tag color="success">当前使用</Tag>}
            {item.verify_ok === true && <Tag color="success">连接正常</Tag>}
            {item.verify_ok === false && <Tag color="error">连接失败</Tag>}
          </div>
          <p>接口地址：{item.base_url || "未填写"}　模型：{item.model || "未填写"}</p>
          <small>API Key：{item.key_set ? (item.key_source === "server" ? "使用服务器配置" : "已保存（不显示）") : "未填写"}
            {item.updated_at ? `　最近修改：${item.updated_by} ${item.updated_at.slice(0, 16).replace("T", " ")}` : ""}</small>
          {item.verify_message && <p className={item.verify_ok === false ? "dsh-plugin-failure" : undefined}>测试结果：{item.verify_message}</p>}
        </div>
        {canManage && <Space wrap>
          <Button icon={<ThunderboltOutlined />} loading={busy === "test:" + item.id} disabled={!!busy || !item.key_set} onClick={() => void test(item)}>测试连接</Button>
          <Button icon={<EditOutlined />} disabled={!!busy} onClick={() => openEditor(item)}>编辑</Button>
          <Button danger icon={<DeleteOutlined />} disabled={!!busy || item.id === state.active_id} onClick={() => remove(item)}>删除</Button>
        </Space>}
      </article>)}
    </div>}
    <Modal title={editing === "new" ? "新增服务商" : "编辑服务商"} open={!!editing} okText="保存" cancelText="取消"
      confirmLoading={busy === "save"} onOk={() => void save()} onCancel={() => { setEditing(null); form.resetFields(); }} destroyOnHidden>
      <Form form={form} layout="vertical" autoComplete="off" initialValues={initial}>
        <Form.Item name="type" label="类型" rules={[{ required: true, message: "请选择类型" }]}>
          <Select options={(state?.types || []).map(item => ({ value: item.value, label: item.label }))} onChange={changeType} />
        </Form.Item>
        <Form.Item name="name" label="名称" rules={[{ required: true, whitespace: true, message: "请填写名称" }]}><Input maxLength={60} /></Form.Item>
        <Form.Item name="base_url" label="接口地址" rules={[{ required: true, whitespace: true, message: "请填写接口地址" },
          { pattern: /^https:\/\/\S+$/, message: "接口地址必须以 https:// 开头" }]}><Input maxLength={300} placeholder="https://" /></Form.Item>
        <Form.Item name="model" label="默认模型" rules={[{ required: true, whitespace: true, message: "请填写模型名" }]}><Input maxLength={120} /></Form.Item>
        <Form.Item name="api_key" label="API Key"
          extra={editingProvider ? (editingProvider.key_source === "server" ? "现在使用服务器配置的 Key；填写后改用这里保存的 Key。" : "已保存的 Key 不显示；留空表示不修改。") : "加密保存，保存后不再显示。"}
          rules={editing === "new" ? [{ required: true, whitespace: true, message: "请填写 API Key" }] : []}>
          <Input.Password maxLength={500} autoComplete="new-password" visibilityToggle={false} />
        </Form.Item>
      </Form>
    </Modal>
  </section>;
}
