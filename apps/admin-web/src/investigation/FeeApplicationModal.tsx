import { Modal, Form, Select, InputNumber, Input } from "antd";
import type { Row } from "./types";

interface FeeApplicationModalProps {
  open: boolean;
  feeTarget: Row | null;
  feeForm: any;
  onOk: () => void;
  onCancel: () => void;
}

export default function FeeApplicationModal({
  open,
  feeTarget,
  feeForm,
  onOk,
  onCancel,
}: FeeApplicationModalProps) {
  return (
    <Modal
      open={open}
      title={`申请调查费用：${feeTarget?.serial_no || ""}`}
      okText="创建费用申请"
      cancelText="取消"
      onOk={onOk}
      onCancel={onCancel}
    >
      <Form form={feeForm} layout="vertical">
        <Form.Item
          label="费用类型"
          name="fee_type"
          rules={[{ required: true }]}
        >
          <Select
            options={[
              "调查取证费",
              "公证费已付",
              "公证费",
              "公证服务费",
              "差旅费",
              "购买样品费",
              "其他",
            ].map((value) => ({ value, label: value }))}
          />
        </Form.Item>
        <Form.Item
          label="申请金额"
          name="amount"
          rules={[{ required: true }]}
        >
          <InputNumber min={0.01} precision={2} style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item label="费用说明" name="description">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
