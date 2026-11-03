import { useCallback, useEffect, useState } from "react";
import { Alert, AutoComplete, Button, Form, Input, Space, Switch, Tag, message } from "antd";
import { CloudOutlined, ReloadOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { api } from "../api";
import { errorText } from "../personal-agent/types";
import "./dsh-plugin-center.css";

// 陶威 11-03：智能体中心改用火山方舟 Managed Agents（云端智能体），不再在服务器上跑 DSH。Key 加密保存、不回显。
export type CloudState = {
  enabled: boolean; model: string; memory: boolean; key_set: boolean; models: string[]; revision: number;
  updated_by: string; updated_at: string; verified_at: string; verify_ok: boolean | null; verify_message: string;
};
type CloudForm = { enabled: boolean; model: string; memory: boolean; api_key?: string };

const BASE = "/agent-admin/cloud-runtime";

export function CloudRuntimeSettings({ active, canManage, onBusy }: { active: boolean; canManage: boolean; onBusy: (busy: boolean) => void }) {
  const [state, setState] = useState<CloudState | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [form] = Form.useForm<CloudForm>();

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const { data } = await api.get<CloudState>(BASE);
      setState(data);
      form.setFieldsValue({ enabled: data.enabled, model: data.model, memory: data.memory, api_key: "" });
    } catch (failure) { setError(errorText(failure, "云端智能体配置加载失败")); }
    finally { setLoading(false); }
  }, [form]);
  useEffect(() => { if (active && canManage) void load(); }, [active, canManage, load]);

  const save = async () => {
    if (busy) return;
    const values = await form.validateFields();
    setBusy("save"); setError(""); onBusy(true);
    try {
      const { data } = await api.put<CloudState>(BASE, { ...values, model: values.model.trim(), api_key: (values.api_key || "").trim() });
      setState(data);
      form.setFieldsValue({ api_key: "" });
      message.success(data.enabled ? "已保存：智能体改用云端运行" : "已保存：智能体仍在服务器上运行");
    } catch (failure) { setError(errorText(failure, "保存未完成")); }
    finally { setBusy(""); onBusy(false); }
  };
  const test = async () => {
    if (busy) return;
    setBusy("test"); setError("");
    try {
      const { data } = await api.post<{ ok: boolean; message: string }>(`${BASE}/test`, {}, { timeout: 40000 });
      if (data.ok) message.success(data.message); else message.error(data.message);
      await load();
    } catch (failure) { setError(errorText(failure, "测试连接未完成")); }
    finally { setBusy(""); }
  };

  return <section className="dsh-plugin-center" aria-label="云端智能体">
    <header className="dsh-plugin-heading">
      <div><span className="dsh-plugin-eyebrow">VOLCENGINE MANAGED AGENTS</span><h2><CloudOutlined />云端智能体</h2>
        <p>启用后，个人助手和案件智能体都在火山方舟云端运行，服务器不再承担智能体运行；查改 OA 数据仍由 OA 按登录人权限执行。关闭后恢复使用下方的 DSH 配置。</p></div>
      <Space wrap>
        <Button icon={<ReloadOutlined />} loading={loading} disabled={!!busy || !canManage} onClick={() => void load()}>刷新</Button>
      </Space>
    </header>
    {!canManage && <Alert type="info" showIcon title="云端智能体配置只有系统管理员可以查看和修改。" />}
    {error && <Alert type="error" showIcon title={error} />}
    {state && <div className="dsh-provider-list"><article className={state.enabled ? "is-active" : undefined}>
      <div className="dsh-plugin-info">
        <div className="dsh-plugin-title">
          <strong>火山方舟 Managed Agents</strong>
          {state.enabled ? <Tag color="success">已启用</Tag> : <Tag>未启用</Tag>}
          {state.verify_ok === true && <Tag color="success">连接正常</Tag>}
          {state.verify_ok === false && <Tag color="error">连接失败</Tag>}
        </div>
        <small>方舟 API Key：{state.key_set ? "已保存（不显示）" : "未填写"}
          {state.updated_at ? `　最近修改：${state.updated_by} ${state.updated_at.slice(0, 16).replace("T", " ")}` : ""}</small>
        {state.verify_message && <p className={state.verify_ok === false ? "dsh-plugin-failure" : undefined}>测试结果：{state.verify_message}</p>}
        <Form form={form} layout="vertical" autoComplete="off" disabled={!canManage || !!busy}>
          <Form.Item name="api_key" label="方舟 API Key" extra={state.key_set ? "已保存的 Key 不显示；留空表示不修改。" : "在火山方舟控制台“API Key 管理”里创建，加密保存，保存后不再显示。"}>
            <Input.Password maxLength={500} autoComplete="new-password" visibilityToggle={false} />
          </Form.Item>
          <Form.Item name="model" label="模型" extra="模型 ID 带版本号，需要先在方舟“开通管理”里开通；可以从下拉里选，也可以直接填写。"
            rules={[{ required: true, whitespace: true, message: "请填写模型" }]}>
            <AutoComplete maxLength={120} options={state.models.map(value => ({ value }))} />
          </Form.Item>
          <Form.Item name="memory" label="长期记忆" valuePropName="checked" extra="开启后每人一个云端记忆库；个人在“记忆”里关掉的不挂载。">
            <Switch />
          </Form.Item>
          <Form.Item name="enabled" label="启用云端智能体" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </div>
      {canManage && <Space wrap>
        <Button icon={<ThunderboltOutlined />} loading={busy === "test"} disabled={!!busy || !state.key_set} onClick={() => void test()}>测试连接</Button>
        <Button type="primary" loading={busy === "save"} disabled={!!busy} onClick={() => void save()}>保存</Button>
      </Space>}
    </article></div>}
  </section>;
}
