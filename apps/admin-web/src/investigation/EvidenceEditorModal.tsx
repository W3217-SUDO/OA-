import { Modal, Form, Input } from "antd";
import { EvidenceInfoFields } from "./EvidenceInfoFields";
import type { ClueEvidenceRow } from "./types";

interface EvidenceEditorModalProps {
  open: boolean;
  editingEvidence: ClueEvidenceRow | null;
  /** 公证处列表由 EvidenceInfoFields 自己读取（501336），保留参数兼容调用方。 */
  notaryOfficeOptions?: { value: string }[];
  evidenceEditForm: any;
  onOk: () => void;
  onCancel: () => void;
}

export default function EvidenceEditorModal({
  open,
  editingEvidence,
  evidenceEditForm,
  onOk,
  onCancel,
}: EvidenceEditorModalProps) {
  return (
    <Modal
      open={open}
      title={`修改取证信息：${editingEvidence?.serial_no || ""}`}
      okText="保存"
      cancelText="取消"
      onOk={onOk}
      onCancel={onCancel}
    >
      <Form form={evidenceEditForm} layout="vertical">
        <EvidenceInfoFields form={evidenceEditForm} open={open} />
        <Form.Item label="证据文件"><Input disabled value={editingEvidence?.files?.map(file => file.original_name).join("、") || "无"} /></Form.Item>
      </Form>
    </Modal>
  );
}
