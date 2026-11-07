import { useCallback, useEffect, useState } from "react";
import { Alert, Button, Form, Input, Space, Tag, message } from "antd";
import { ReloadOutlined, RobotOutlined, ThunderboltOutlined } from "@ant-design/icons";
import { api } from "../api";
import { errorText } from "../personal-agent/types";
import "./dsh-plugin-center.css";

// 钉钉机器人中心：系统管理员在这里填收文助手的 AppKey、AppSecret。Secret 加密保存、不回显。
type BotState = {
  app_key: string; secret_set: boolean; updated_by: string; updated_at: string;
  verified_at: string; verify_ok: boolean | null; verify_message: string;
};
type BotForm = { app_key: string; app_secret?: string };

const BASE = "/agent-admin/dingtalk-bots";

export function DingtalkBotCenter({ onBusy }: { onBusy: (busy: boolean) => void }) {
  const [state, setState] = useState<BotState | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [form] = Form.useForm<BotForm>();

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const { data } = await api.get<BotState>(BASE);
      setState(data);
      form.setFieldsValue({ app_key: data.app_key, app_secret: "" });
    } catch (failure) { setError(errorText(failure, "钉钉机器人配置加载失败")); }
    finally { setLoading(false); }
  }, [form]);
  useEffect(() => { void load(); }, [load]);

  const save = async () => {
    if (busy) return;
    const values = await form.validateFields();
    setBusy("save"); setError(""); onBusy(true);
    try {
      const { data } = await api.put<BotState>(BASE, { app_key: values.app_key.trim(), app_secret: (values.app_secret || "").trim() });
      setState(data);
      form.setFieldsValue({ app_secret: "" });
      message.success("已保存");
    } catch (failure) { setError(errorText(failure, "保存未完成")); }
    finally { setBusy(""); onBusy(false); }
  };
  const test = async () => {
    if (busy) return;
    const unsaved = form.getFieldsValue();
    if ((unsaved.app_key || "").trim() !== state?.app_key || (unsaved.app_secret || "").trim()) {
      message.warning("测试的是已保存的凭证，请先保存改动");
      return;
    }
    setBusy("test"); setError("");
    try {
      const { data } = await api.post<{ ok: boolean; message: string }>(`${BASE}/test`, {}, { timeout: 30000 });
      if (data.ok) message.success(data.message); else message.error(data.message);
      await load();
    } catch (failure) { setError(errorText(failure, "测试连接未完成")); }
    finally { setBusy(""); }
  };

  return <section className="dsh-plugin-center" aria-label="钉钉机器人中心">
    <header className="dsh-plugin-heading">
      <div><span className="dsh-plugin-eyebrow">DINGTALK BOTS</span><h2><RobotOutlined />钉钉机器人中心</h2>
        <p>配置接入 OA 的钉钉机器人。这里只保存凭证，机器人的收发功能上线后才会用到。</p></div>
      <Space wrap>
        <Button icon={<ReloadOutlined />} loading={loading} disabled={!!busy} onClick={() => void load()}>刷新</Button>
      </Space>
    </header>
    {error && <Alert type="error" showIcon title={error} />}
    {state && <div className="dsh-provider-list"><article>
      <div className="dsh-plugin-info">
        <div className="dsh-plugin-title">
          <strong>收文助手</strong>
          {state.verify_ok === true && <Tag color="success">连接正常</Tag>}
          {state.verify_ok === false && <Tag color="error">连接失败</Tag>}
        </div>
        <small>AppSecret：{state.secret_set ? "已保存（不显示）" : "未填写"}
          {state.updated_at ? `　最近修改：${state.updated_by} ${state.updated_at.slice(0, 16).replace("T", " ")}` : ""}</small>
        {state.verify_message && <p className={state.verify_ok === false ? "dsh-plugin-failure" : undefined}>测试结果：{state.verify_message}</p>}
        <Form form={form} layout="vertical" autoComplete="off" disabled={!!busy}>
          <Form.Item name="app_key" label="AppKey（Client ID）" extra="钉钉开发者后台 › 收文助手 › 凭证与基础信息。"
            rules={[{ required: true, whitespace: true, message: "请填写 AppKey" },
              { pattern: /^\s*[A-Za-z0-9_-]+\s*$/, message: "AppKey 只能包含字母、数字、下划线和短横线" }]}>
            <Input maxLength={128} autoComplete="off" />
          </Form.Item>
          <Form.Item name="app_secret" label="AppSecret（Client Secret）" extra={state.secret_set ? "已保存的 Secret 不显示；留空表示不修改。" : "保存后加密存放，任何页面都不再显示。"}>
            <Input.Password maxLength={256} autoComplete="new-password" visibilityToggle={false} />
          </Form.Item>
        </Form>
      </div>
      <Space wrap>
        <Button icon={<ThunderboltOutlined />} loading={busy === "test"} disabled={!!busy || !state.secret_set} onClick={() => void test()}>测试连接</Button>
        <Button type="primary" loading={busy === "save"} disabled={!!busy} onClick={() => void save()}>保存</Button>
      </Space>
    </article></div>}
  </section>;
}
