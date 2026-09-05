import { Modal, Form, Select, Input } from "antd";
import type { Row, PersonOption } from "./types";

interface TurnOnAuditModalProps {
  open: boolean;
  turnOnAuditTarget: Row | null;
  turnOnAuditForm: any;
  reviewerCandidatesLoading: boolean;
  reviewerCandidates: PersonOption[];
  onOk: () => void;
  onCancel: () => void;
}

export default function TurnOnAuditModal({
  open,
  turnOnAuditTarget,
  turnOnAuditForm,
  reviewerCandidatesLoading,
  reviewerCandidates,
  onOk,
  onCancel,
}: TurnOnAuditModalProps) {
  return (
    <Modal
      open={open}
      title={`转交审核人：${turnOnAuditTarget?.serial_no || ""}`}
      okText="确认转交"
      cancelText="取消"
      confirmLoading={reviewerCandidatesLoading}
      onOk={onOk}
      onCancel={onCancel}
    >
      <Form form={turnOnAuditForm} layout="vertical">
        <Form.Item
          label="目标审核人"
          name="reviewer"
          rules={[{ required: true, message: "请选择具备线索审批岗位的审核人" }]}
        >
          <Select
            showSearch
            optionFilterProp="label"
            loading={reviewerCandidatesLoading}
            options={reviewerCandidates}
            notFoundContent={
              reviewerCandidatesLoading ? "正在加载审核人" : "没有可用审核人"
            }
          />
        </Form.Item>
        <Form.Item label="转交说明" name="comment">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
