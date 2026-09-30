import { useRef, useState } from "react";
import { Button, Form, Input, message, Space } from "antd";
import { api } from "../api";

type Props = { sourcePage: string; onCancel: () => void; onSubmitted?: (id: number) => void };

export default function FeedbackForm({ sourcePage, onCancel, onSubmitted }: Props) {
  const [submitting, setSubmitting] = useState(false);
  const [screenshot, setScreenshot] = useState<File | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const [form] = Form.useForm<{ description: string }>();

  const submit = async ({ description }: { description: string }) => {
    const body = new FormData();
    body.append("description", description.trim());
    body.append("page", sourcePage);
    if (screenshot) body.append("screenshot", screenshot);
    setSubmitting(true);
    try {
      const { data } = await api.post("/feedback", body);
      message.success(`反馈已提交：${data.serial_no}`);
      form.resetFields();
      setScreenshot(null);
      if (fileInput.current) fileInput.current.value = "";
      onSubmitted?.(data.id);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "反馈提交失败");
    } finally {
      setSubmitting(false);
    }
  };

  return <Form form={form} layout="vertical" onFinish={(values) => void submit(values)} style={{ maxWidth: 850 }}>
    <Form.Item label="问题所在页面">
      <span style={{ overflowWrap: "anywhere" }}>{sourcePage || "未关联业务页面"}</span>
    </Form.Item>
    <Form.Item name="description" label="问题描述" rules={[{ required: true, min: 5, max: 2000, message: "请填写 5 到 2000 字的问题描述" }]}>
      <Input.TextArea rows={8} placeholder="请描述操作步骤和出现的问题" />
    </Form.Item>
    <Form.Item label="截图（可选）">
      <input ref={fileInput} type="file" accept="image/png,image/jpeg,image/webp"
        onChange={(event) => setScreenshot(event.target.files?.[0] || null)} />
    </Form.Item>
    <Space>
      <Button type="primary" htmlType="submit" loading={submitting}>提交反馈</Button>
      <Button onClick={onCancel} disabled={submitting}>取消</Button>
    </Space>
  </Form>;
}
