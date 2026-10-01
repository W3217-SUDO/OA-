import { DatePicker, Form, Input, Modal } from "antd";
import type { FormInstance } from "antd";
import dayjs from "dayjs";
import type { PaymentWriteoffFormValues } from "./formTypes";
import type { Fee } from "./types";

export interface PaymentWriteoffModalProps {
  target: Fee | null;
  form: FormInstance<PaymentWriteoffFormValues>;
  onSubmit: () => Promise<void>;
  onClose: () => void;
}

export function PaymentWriteoffModal({ target, form, onSubmit, onClose }: PaymentWriteoffModalProps) {
  return (
    <Modal
      open={Boolean(target)}
      title={`付款核销：${target?.serial_no || ""}`}
      okText="确认核销"
      cancelText="取消"
      onOk={onSubmit}
      onCancel={onClose}
    >
      <Form form={form} layout="vertical">
        <Form.Item
          label="核销日期"
          name="writeoff_date"
          initialValue={dayjs()}
          rules={[{ required: true, message: "请选择核销日期" }]}
        >
          <DatePicker style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item
          label="核销凭证号"
          name="voucher_no"
          rules={[{ required: true, min: 2, message: "请输入核销凭证号" }]}
        >
          <Input placeholder="例如：HX-20260715-001" />
        </Form.Item>
        <Form.Item label="核销说明" name="comment">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
