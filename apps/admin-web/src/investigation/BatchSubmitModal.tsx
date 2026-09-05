import { Modal, Alert, Form, Input } from "antd";

interface BatchSubmitModalProps {
  open: boolean;
  selectedCount: number;
  batchSubmitForm: any;
  onOk: () => void;
  onCancel: () => void;
}

export default function BatchSubmitModal({
  open,
  selectedCount,
  batchSubmitForm,
  onOk,
  onCancel,
}: BatchSubmitModalProps) {
  return (
    <Modal
      open={open}
      title={`批量提交线索审批（${selectedCount} 条）`}
      okText="确认提交"
      cancelText="取消"
      onOk={onOk}
      onCancel={onCancel}
    >
      <Alert
        type="info"
        showIcon
        message="已选线索将作为一个批次提交"
        description="服务端会统一校验全部线索；任一线索不满足提交条件时，本次不会提交任何线索。"
        style={{ marginBottom: 16 }}
      />
      <Form form={batchSubmitForm} layout="vertical">
        <Form.Item label="审批说明" name="comment">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
