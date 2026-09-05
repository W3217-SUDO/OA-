import { Form, Input, InputNumber, Modal } from "antd";
import type { FormInstance } from "antd";

interface SealBatchStampModalProps {
  open: boolean;
  form: FormInstance;
  submitting: boolean;
  onOk: () => void;
  onCancel: () => void;
}

export function SealBatchStampModal({
  open,
  form,
  submitting,
  onOk,
  onCancel,
}: SealBatchStampModalProps) {
  return (
    <Modal
      open={open}
      title="批量登记实际用印"
      okText="确认"
      cancelText="取消"
      confirmLoading={submitting}
      onOk={onOk}
      onCancel={onCancel}
    >
      <Form form={form} layout="vertical">
        <Form.Item
          label="实际用印份数"
          name="actual_copies"
          rules={[{ required: true }]}
        >
          <InputNumber min={1} style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item
          label="用印操作人"
          name="operator"
          rules={[{ required: true }]}
        >
          <Input />
        </Form.Item>
        <Form.Item
          label="归档号"
          name="archive_no"
        >
          <Input placeholder="例如：YY-2026-0042" />
        </Form.Item>
        <Form.Item label="审批/操作意见" name="comment">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
