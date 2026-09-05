import { Modal, Form, Input, Select } from "antd";
import type { Row } from "./types";

interface EvidenceCreateModalProps {
  open: boolean;
  evidenceSource: Row | null;
  evidenceForm: any;
  systemPersonOptions: { value: string; label: string }[];
  onOk: () => void;
  onCancel: () => void;
}

export default function EvidenceCreateModal({
  open,
  evidenceSource,
  evidenceForm,
  systemPersonOptions,
  onOk,
  onCancel,
}: EvidenceCreateModalProps) {
  return (
    <Modal
      open={open}
      title={`建立证据目录：${evidenceSource?.serial_no || ""}`}
      okText="创建证据"
      cancelText="取消"
      onOk={onOk}
      onCancel={onCancel}
    >
      <Form form={evidenceForm} layout="vertical">
        <Form.Item label="证据标题" name="title" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <div className="form-grid">
          <Form.Item label="负责人" name="owner" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="label" options={systemPersonOptions} />
          </Form.Item>
          <Form.Item label="材料来源" name="source">
            <Input />
          </Form.Item>
        </div>
        <Form.Item label="证据说明" name="description">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
