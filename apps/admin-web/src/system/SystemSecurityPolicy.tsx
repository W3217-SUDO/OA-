import {
  Button,
  Card,
  Form,
  InputNumber,
} from "antd";
import type { SecurityPolicy } from "./types";
import { formatTime } from "./constants";

interface SystemSecurityPolicyProps {
  securityPolicy: SecurityPolicy | null;
  loading: boolean;
  securityForm: ReturnType<typeof Form.useForm>[0];
  onSaveSecurity: () => void;
}

export function SystemSecurityPolicy({
  securityPolicy,
  loading,
  securityForm,
  onSaveSecurity,
}: SystemSecurityPolicyProps) {
  return (
    <Card
      className="panel system-focused"
      title="账号安全策略"
      loading={loading}
    >
      <Form
        form={securityForm}
        className="system-config-form"
        labelCol={{ flex: "180px" }}
        wrapperCol={{ flex: "260px" }}
      >
        <Form.Item
          name="min_password_length"
          label="密码最小长度"
          rules={[{ required: true }]}
        >
          <InputNumber min={8} max={128} style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item
          name="max_failed_attempts"
          label="最大连续失败次数"
          rules={[{ required: true }]}
        >
          <InputNumber min={1} max={20} style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item
          name="lock_minutes"
          label="账号锁定时间"
          rules={[{ required: true }]}
        >
          <InputNumber
            min={1}
            max={1440}
            addonAfter="分钟"
            style={{ width: "100%" }}
          />
        </Form.Item>
        <Form.Item
          name="token_minutes"
          label="登录有效期"
          rules={[{ required: true }]}
        >
          <InputNumber
            min={5}
            max={10080}
            addonAfter="分钟"
            style={{ width: "100%" }}
          />
        </Form.Item>
        <Form.Item label="最近修改">
          {securityPolicy
            ? `${securityPolicy.updated_by || "—"}｜${formatTime(securityPolicy.updated_at)}`
            : "—"}
        </Form.Item>
        <Form.Item label=" ">
          <Button type="primary" onClick={onSaveSecurity}>
            保存安全策略
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );
}
