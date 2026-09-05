import { Modal, Form, Input } from "antd";
import type { Row, SubtaskLifecycleAction } from "./types";

interface SubtaskActionTarget {
  row: Row;
  action: SubtaskLifecycleAction;
}

interface SubtaskActionModalProps {
  open: boolean;
  subtaskActionTarget: SubtaskActionTarget | null;
  subtaskActionForm: any;
  onOk: () => void;
  onCancel: () => void;
}

export default function SubtaskActionModal({
  open,
  subtaskActionTarget,
  subtaskActionForm,
  onOk,
  onCancel,
}: SubtaskActionModalProps) {
  const isAccept = subtaskActionTarget?.action === "accept";

  return (
    <Modal
      open={open}
      title={`${isAccept ? "接收调查子任务" : "提交调查子任务完成"}：${subtaskActionTarget?.row.serial_no || ""}`}
      okText={isAccept ? "确认接收" : "提交完成"}
      cancelText="取消"
      onOk={onOk}
      onCancel={onCancel}
    >
      <Form form={subtaskActionForm} layout="vertical">
        <Form.Item
          label={isAccept ? "接收说明" : "办理结果说明"}
          name="comment"
          rules={
            subtaskActionTarget?.action === "complete"
              ? [{ required: true, min: 2, message: "请填写办理结果说明" }]
              : []
          }
        >
          <Input.TextArea
            rows={4}
            placeholder={
              isAccept ? "可填写接收说明" : "请说明本次调查办理结果"
            }
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}
