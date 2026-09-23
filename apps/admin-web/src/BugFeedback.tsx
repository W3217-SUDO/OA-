import { useState } from "react";
import { Button, Form, Input, message, Modal } from "antd";
import { api } from "./api";

export default function BugFeedback() {
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [screenshot, setScreenshot] = useState<File | null>(null);
  const [form] = Form.useForm<{ description: string }>();

  const submit = async () => {
    const { description } = await form.validateFields();
    const body = new FormData();
    body.append("description", description.trim());
    body.append("page", `${window.location.pathname}${window.location.search}`);
    if (screenshot) body.append("screenshot", screenshot);
    setSubmitting(true);
    try {
      const { data } = await api.post("/feedback", body);
      message.success(`反馈已提交：${data.serial_no}`);
      form.resetFields();
      setScreenshot(null);
      setOpen(false);
    } catch (error: any) {
      message.error(error?.response?.data?.detail || "反馈提交失败");
    } finally {
      setSubmitting(false);
    }
  };

  return <>
    <Button className="bug-feedback-trigger" onClick={() => setOpen(true)}>问题反馈</Button>
    <Modal open={open} title="问题反馈" okText="提交反馈" confirmLoading={submitting}
      onOk={() => void submit()} onCancel={() => setOpen(false)}>
      <Form form={form} layout="vertical">
        <Form.Item name="description" label="问题描述" rules={[{ required: true, min: 5, max: 2000, message: "请填写 5 到 2000 字的问题描述" }]}>
          <Input.TextArea rows={5} placeholder="请描述操作步骤和出现的问题" />
        </Form.Item>
        <Form.Item label="截图（可选）">
          <input type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => setScreenshot(event.target.files?.[0] || null)} />
        </Form.Item>
      </Form>
    </Modal>
  </>;
}
