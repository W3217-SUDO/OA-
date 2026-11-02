import { useEffect, useState } from "react";
import { Alert, Button, Card, Descriptions, Form, Input, InputNumber, Space, Spin, Tag, message } from "antd";
import { ApiOutlined, SaveOutlined } from "@ant-design/icons";
import { api } from "../api";
import { errorText } from "../personal-agent/types";

type ProviderStatus = {
  configured: boolean; source: "page" | "server" | ""; updated_by: string; updated_at: string;
  verified_at: string; verify_message: string; limits?: { user_daily: number; total_daily: number };
  today_billed: number; today_calls: number;
};
type Provider = {
  id: string; name: string; doc_url: string; usage: string; test_note: string; has_limits: boolean;
  fields: { name: string; label: string }[]; status: ProviderStatus;
};

const time = (value: string) => value ? new Date(value).toLocaleString("zh-CN") : "—";

/** 系统参数 › API 设置（501106，陶威 11-02 23:27）：外部接口凭据，每个接口一张卡片，字段由后端给出；
 *  只有系统管理员能看，凭据加密保存、保存后不回显。以后接百度等接口只需后端 PROVIDERS 加一项。 */
export function SystemApiSettings() {
  const [providers, setProviders] = useState<Provider[] | null>(null);
  const [error, setError] = useState("");
  const load = async () => {
    setError("");
    try { const { data } = await api.get<{ items: Provider[] }>("/external-credentials"); setProviders(data.items); }
    catch (failure) { setError(errorText(failure, "API 设置读取失败")); setProviders([]); }
  };
  useEffect(() => { void load(); }, []);
  if (!providers) return <Spin />;
  return <div className="system-api-settings">
    {error && <Alert type="error" showIcon title={error} style={{ marginBottom: 12 }} />}
    <Space orientation="vertical" size={16} style={{ width: "100%" }}>
      {providers.map((provider) => <ProviderCard key={provider.id} provider={provider} onChanged={(status) =>
        setProviders((items) => (items || []).map((item) => item.id === provider.id ? { ...item, status } : item))} />)}
    </Space>
  </div>;
}

function ProviderCard({ provider, onChanged }: { provider: Provider; onChanged: (status: ProviderStatus) => void }) {
  const { status } = provider;
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [form] = Form.useForm<Record<string, string>>();
  const [limitForm] = Form.useForm<{ user_daily: number; total_daily: number }>();
  const base = `/external-credentials/${encodeURIComponent(provider.id)}`;
  useEffect(() => { if (status.limits) limitForm.setFieldsValue(status.limits); }, [status.limits?.user_daily, status.limits?.total_daily]);
  const reload = async () => { const { data } = await api.get<ProviderStatus>(base); onChanged(data); };
  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      const { data } = await api.put<ProviderStatus>(base, values);
      onChanged(data); form.resetFields(); message.success(`${provider.name}凭据已加密保存`);
    } catch (failure) { message.error(errorText(failure, "保存失败")); }
    finally { setSaving(false); }
  };
  const test = async () => {
    setTesting(true);
    try {
      const { data } = await api.post<{ ok: boolean; message: string }>(`${base}/test`);
      if (data.ok) message.success("连接正常"); else message.error(data.message);
      await reload();
    } catch (failure) { message.error(errorText(failure, "测试连接失败")); }
    finally { setTesting(false); }
  };
  const saveLimits = async () => {
    const values = await limitForm.validateFields();
    try { const { data } = await api.put<ProviderStatus>(`${base}/limits`, values); onChanged(data); message.success("查询上限已保存"); }
    catch (failure) { message.error(errorText(failure, "保存失败")); }
  };
  return <Card title={provider.name} extra={provider.doc_url && <a href={provider.doc_url} target="_blank" rel="noreferrer">接口文档</a>}>
    <Descriptions size="small" column={1} bordered>
      <Descriptions.Item label="用途">{provider.usage || "—"}</Descriptions.Item>
      <Descriptions.Item label="状态">{status.configured
        ? <Tag color="success">已配置（{status.source === "page" ? "本页面填写" : "服务器私有配置"}）</Tag>
        : <Tag>未配置</Tag>}</Descriptions.Item>
      <Descriptions.Item label="最近更新">{status.updated_by ? `${status.updated_by} · ${time(status.updated_at)}` : "—"}</Descriptions.Item>
      <Descriptions.Item label="测试结果">{status.verify_message ? `${status.verify_message}${status.verified_at ? `（${time(status.verified_at)} 连通）` : ""}` : "未测试"}</Descriptions.Item>
      <Descriptions.Item label="今日调用">{`${status.today_calls} 次（计费 ${status.today_billed} 次，命中缓存不计费）`}</Descriptions.Item>
    </Descriptions>
    <Alert type="info" showIcon style={{ margin: "12px 0" }}
      title={`凭据加密保存，保存后不再显示；重新填写会覆盖原凭据。${provider.test_note ? `${provider.test_note}。` : ""}`} />
    <Form form={form} layout="vertical" autoComplete="off">
      {provider.fields.map((field) => <Form.Item key={field.name} label={field.label} name={field.name}
        rules={[{ required: true, min: 8, message: `请粘贴${field.label}` }]}>
        <Input.Password autoComplete="new-password" placeholder={status.configured ? "已配置，如需更换请重新粘贴" : `粘贴${field.label}`} />
      </Form.Item>)}
      <Space wrap>
        <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={() => void save()}>保存</Button>
        <Button icon={<ApiOutlined />} loading={testing} disabled={!status.configured} onClick={() => void test()}>测试连接</Button>
      </Space>
    </Form>
    {provider.has_limits && <Form form={limitForm} layout="inline" style={{ marginTop: 16 }}>
      <Form.Item label="每人每天上限" name="user_daily" rules={[{ required: true }]}><InputNumber min={1} max={1000} /></Form.Item>
      <Form.Item label="全所每天上限" name="total_daily" rules={[{ required: true }]}><InputNumber min={1} max={100000} /></Form.Item>
      <Form.Item><Button onClick={() => void saveLimits()}>保存上限</Button></Form.Item>
    </Form>}
  </Card>;
}
