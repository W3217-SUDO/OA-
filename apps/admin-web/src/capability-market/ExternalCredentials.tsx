import { useEffect, useState } from "react";
import { Alert, Button, Card, Descriptions, Form, Input, InputNumber, Space, Tag, message } from "antd";
import { ApiOutlined, SaveOutlined } from "@ant-design/icons";
import { api } from "../api";
import { errorText } from "../personal-agent/types";

type QccStatus = {
  configured: boolean; source: "page" | "server" | ""; updated_by: string; updated_at: string;
  verified_at: string; verify_message: string; limits: { user_daily: number; total_daily: number };
  today_billed: number; today_calls: number;
};

const time = (value: string) => value ? new Date(value).toLocaleString("zh-CN") : "—";

/** 智能体设置 › 外部接口凭据 › 企查查开放平台（501106）：Key 和 SecretKey 加密保存、不回显，测试连接只回报是否连通。 */
export function ExternalCredentials({ active, canManage }: { active: boolean; canManage: boolean }) {
  const [status, setStatus] = useState<QccStatus | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [form] = Form.useForm<{ key: string; secret: string }>();
  const [limitForm] = Form.useForm<{ user_daily: number; total_daily: number }>();
  const load = async () => {
    setError("");
    try {
      const { data } = await api.get<QccStatus>("/external-credentials/qcc");
      setStatus(data); limitForm.setFieldsValue(data.limits);
    } catch (failure) { setError(errorText(failure, "凭据状态读取失败")); }
  };
  useEffect(() => { if (active && canManage) void load(); }, [active, canManage]);
  if (!canManage) return <Alert type="info" showIcon title="外部接口凭据只能由系统管理员维护。" />;
  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      const { data } = await api.put<QccStatus>("/external-credentials/qcc", values);
      setStatus(data); form.resetFields(); message.success("企查查凭据已加密保存");
    } catch (failure) { message.error(errorText(failure, "保存失败")); }
    finally { setSaving(false); }
  };
  const test = async () => {
    setTesting(true);
    try {
      const { data } = await api.post<{ ok: boolean; message: string }>("/external-credentials/qcc/test");
      if (data.ok) message.success("连接正常"); else message.error(data.message);
      await load();
    } catch (failure) { message.error(errorText(failure, "测试连接失败")); }
    finally { setTesting(false); }
  };
  const saveLimits = async () => {
    const values = await limitForm.validateFields();
    try { const { data } = await api.put<QccStatus>("/external-credentials/qcc/limits", values); setStatus(data); message.success("查询上限已保存"); }
    catch (failure) { message.error(errorText(failure, "保存失败")); }
  };
  return <Card title="企查查开放平台" className="external-credentials-card">
    {error && <Alert type="error" showIcon title={error} style={{ marginBottom: 12 }} />}
    <Descriptions size="small" column={1} bordered>
      <Descriptions.Item label="状态">{status?.configured
        ? <Tag color="success">已配置（{status.source === "page" ? "本页面填写" : "服务器私有配置"}）</Tag>
        : <Tag>未配置</Tag>}</Descriptions.Item>
      <Descriptions.Item label="最近更新">{status?.updated_by ? `${status.updated_by} · ${time(status.updated_at)}` : "—"}</Descriptions.Item>
      <Descriptions.Item label="测试结果">{status?.verify_message ? `${status.verify_message}${status.verified_at ? `（${time(status.verified_at)} 连通）` : ""}` : "未测试"}</Descriptions.Item>
      <Descriptions.Item label="今日调用">{status ? `${status.today_calls} 次（计费 ${status.today_billed} 次，命中缓存不计费）` : "—"}</Descriptions.Item>
    </Descriptions>
    <Alert type="info" showIcon style={{ margin: "12px 0" }} title="Key 和 SecretKey 加密保存，保存后不再显示；重新填写会覆盖原凭据。测试连接会做一次模糊搜索，计 1 次费用。" />
    <Form form={form} layout="vertical" autoComplete="off">
      <Form.Item label="Key（应用 AppKey）" name="key" rules={[{ required: true, min: 8, message: "请粘贴企查查 Key" }]}>
        <Input.Password autoComplete="new-password" placeholder={status?.configured ? "已配置，如需更换请重新粘贴" : "粘贴企查查 Key"} />
      </Form.Item>
      <Form.Item label="SecretKey（密钥）" name="secret" rules={[{ required: true, min: 8, message: "请粘贴企查查 SecretKey" }]}>
        <Input.Password autoComplete="new-password" placeholder={status?.configured ? "已配置，如需更换请重新粘贴" : "粘贴企查查 SecretKey"} />
      </Form.Item>
      <Space wrap>
        <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={() => void save()}>保存</Button>
        <Button icon={<ApiOutlined />} loading={testing} disabled={!status?.configured} onClick={() => void test()}>测试连接</Button>
      </Space>
    </Form>
    <Form form={limitForm} layout="inline" style={{ marginTop: 16 }}>
      <Form.Item label="每人每天上限" name="user_daily" rules={[{ required: true }]}><InputNumber min={1} max={1000} /></Form.Item>
      <Form.Item label="全所每天上限" name="total_daily" rules={[{ required: true }]}><InputNumber min={1} max={100000} /></Form.Item>
      <Form.Item><Button onClick={() => void saveLimits()}>保存上限</Button></Form.Item>
    </Form>
  </Card>;
}
