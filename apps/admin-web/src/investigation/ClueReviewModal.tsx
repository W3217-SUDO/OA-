import { Modal, Form, Input, Radio } from "antd";
import { CheckCircleOutlined } from "@ant-design/icons";
import type { Row } from "./types";

interface ClueReviewModalProps {
  open: boolean;
  clueReviewing: Row | null;
  clueReviewForm: any;
  projectedPersonDisplayName: (displayName: unknown, username: unknown) => string;
  onOk: () => void;
  onCancel: () => void;
}

export default function ClueReviewModal({
  open,
  clueReviewing,
  clueReviewForm,
  projectedPersonDisplayName,
  onOk,
  onCancel,
}: ClueReviewModalProps) {
  return (
    <Modal
      open={open}
      title={`${clueReviewing?.status === "待客户审核" ? "客户审核确认" : "线索内部审批"}：${clueReviewing?.serial_no || ""}`}
      okText="提交审核"
      cancelText="取消"
      onOk={onOk}
      onCancel={onCancel}
    >
      <Form form={clueReviewForm} layout="vertical">
        {clueReviewing?.status === "待客户审核" && (
          <div className="form-grid audit-reference">
            <Form.Item label="上一级审核员">
              <Input
                value={projectedPersonDisplayName(
                  clueReviewing.data.reviewer_display_name,
                  clueReviewing.data.reviewer,
                )}
                readOnly
              />
            </Form.Item>
            <Form.Item label="上一级审核意见">
              <Input.TextArea
                value={clueReviewing.data.review_comment || "—"}
                readOnly
                rows={2}
              />
            </Form.Item>
          </div>
        )}
        <Form.Item
          label="审核结果"
          name="approved"
          rules={[{ required: true }]}
        >
          <Radio.Group>
            <Radio value={true}>
              <CheckCircleOutlined />{" "}
              {clueReviewing?.status === "待客户审核"
                ? "客户确认通过，进入待取证"
                : "内部审批通过，进入客户审核或取证"}
            </Radio>
            <Radio value={false}>驳回修改</Radio>
          </Radio.Group>
        </Form.Item>
        <Form.Item
          label={
            clueReviewing?.status === "待客户审核"
              ? "客户反馈/驳回原因"
              : "审核意见/驳回原因"
          }
          name="comment"
          rules={[{ required: true, min: 2 }]}
        >
          <Input.TextArea rows={4} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
