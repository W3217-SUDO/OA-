import { Modal, Form, Select, Input } from "antd";
import type { Row, PersonOption } from "./types";

interface AssignInvestigatorModalProps {
  open: boolean;
  assignTarget: Row | null;
  assignForm: any;
  systemPersonOptions: PersonOption[];
  onOk: () => void;
  onCancel: () => void;
}

export default function AssignInvestigatorModal({
  open,
  assignTarget,
  assignForm,
  systemPersonOptions,
  onOk,
  onCancel,
}: AssignInvestigatorModalProps) {
  return (
    <Modal
      open={open}
      title={`分配调查员：${assignTarget?.serial_no || ""}`}
      okText="确认分配"
      cancelText="取消"
      onOk={onOk}
      onCancel={onCancel}
    >
      <Form form={assignForm} layout="vertical">
        <Form.Item
          label="调查员"
          name="investigator"
          rules={[{ required: true, min: 1 }]}
        >
          <Select
            showSearch
            optionFilterProp="label"
            options={systemPersonOptions}
          />
        </Form.Item>
        <Form.Item label="分配说明" name="comment">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
