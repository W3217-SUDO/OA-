import { Input, Modal } from "antd";
import type { Fee } from "./types";

interface ReversalModalProps {
  target: Fee | null;
  text: string;
  onTextChange: (value: string) => void;
  onSubmit: () => Promise<void>;
  onClose: () => void;
}

export interface PaymentReversalModalsProps {
  cancel: ReversalModalProps;
  rollback: ReversalModalProps;
}

export function PaymentReversalModals({ cancel, rollback }: PaymentReversalModalsProps) {
  return (
    <>
      <Modal
        open={Boolean(cancel.target)}
        title={`撤销请款单：${cancel.target?.serial_no || ""}`}
        okText="撤销"
        okButtonProps={{ danger: true }}
        cancelText="取消"
        onOk={() => void cancel.onSubmit()}
        onCancel={cancel.onClose}
      >
        <Input.TextArea
          rows={4}
          value={cancel.text}
          onChange={(event) => cancel.onTextChange(event.target.value)}
          placeholder="请输入撤回原因"
          aria-label="撤回原因"
        />
      </Modal>
      <Modal
        open={Boolean(rollback.target)}
        title={`回滚请款单：${rollback.target?.serial_no || ""}`}
        okText="回滚"
        cancelText="取消"
        onOk={() => void rollback.onSubmit()}
        onCancel={rollback.onClose}
      >
        <Input.TextArea
          rows={4}
          value={rollback.text}
          onChange={(event) => rollback.onTextChange(event.target.value)}
          placeholder="请输入回滚备注（可选）"
          aria-label="回滚备注"
        />
      </Modal>
    </>
  );
}
