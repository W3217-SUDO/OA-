import { Modal, Form, Radio, Select, Input } from "antd";
import { CheckCircleOutlined } from "@ant-design/icons";
import type { Row } from "./types";

interface NotaryReviewModalProps {
  open: boolean;
  reviewing: Row | null;
  reviewForm: any;
  onOk: () => void;
  onCancel: () => void;
}

export default function NotaryReviewModal({
  open,
  reviewing,
  reviewForm,
  onOk,
  onCancel,
}: NotaryReviewModalProps) {
  return (
    <Modal
      open={open}
      title={`公证审核：${reviewing?.serial_no || ""}`}
      okText="提交审核"
      cancelText="取消"
      onOk={onOk}
      onCancel={onCancel}
    >
      <Form form={reviewForm} layout="vertical">
        <Form.Item
          label="审核结果"
          name="approved"
          rules={[{ required: true }]}
        >
          <Radio.Group>
            <Radio value={true}>
              <CheckCircleOutlined /> 通过并自动转案件
            </Radio>
            <Radio value={false}>驳回</Radio>
          </Radio.Group>
        </Form.Item>
        <Form.Item label="案件类型" name="case_type">
          <Select
            options={["民事案件", "刑事案件", "行政案件", "仲裁案件"].map(
              (v) => ({ value: v, label: v }),
            )}
          />
        </Form.Item>
        <Form.Item label="拟管辖法院" name="court">
          <Input />
        </Form.Item>
        <Form.Item label="审核意见" name="comment">
          <Input.TextArea rows={4} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
