import { DatePicker, Form, Input, InputNumber, Modal } from "antd";
import type { FormInstance } from "antd";
import type { RefundAmountFormValues, RefundCompleteFormValues } from "./formTypes";
import type { FinanceFlow } from "./types";

export interface RefundMaintenanceModalsProps {
  amount: {
    target: FinanceFlow | null;
    form: FormInstance<RefundAmountFormValues>;
    loading: boolean;
    onSubmit: () => Promise<void>;
    onClose: () => void;
  };
  complete: {
    target: FinanceFlow | null;
    form: FormInstance<RefundCompleteFormValues>;
    onSubmit: () => Promise<void>;
    onClose: () => void;
  };
}

export function RefundAmountModal({ target, form, loading, onSubmit, onClose }: RefundMaintenanceModalsProps["amount"]) {
  return (
    <Modal
      open={Boolean(target)}
      title={`修改退款金额：${target?.serial_no || ""}`}
      okText="保存"
      cancelText="取消"
      confirmLoading={loading}
      onOk={onSubmit}
      onCancel={onClose}
    >
      <Form form={form} layout="vertical">
        <Form.Item label="退款金额" name="amount" rules={[{ required: true, type: "number", min: 0.01 }]}>
          <InputNumber min={0.01} precision={2} style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item label="修改说明" name="comment">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

export function RefundCompleteModal({ target, form, onSubmit, onClose }: RefundMaintenanceModalsProps["complete"]) {
  return (
    <Modal
      open={Boolean(target)}
      title={`登记退款到账：${target?.serial_no || ""}`}
      okText="确认到账"
      cancelText="取消"
      onOk={onSubmit}
      onCancel={onClose}
    >
      <Form form={form} layout="vertical">
        <Form.Item label="实际到账日期" name="actual_date" rules={[{ required: true }]}>
          <DatePicker style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item label="退款凭证号" name="voucher_no" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item label="到账说明" name="comment">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
