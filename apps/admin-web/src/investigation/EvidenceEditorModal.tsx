import { Modal, Form, Input, AutoComplete, DatePicker, Select } from "antd";
import type { ClueEvidenceRow } from "./types";

interface EvidenceEditorModalProps {
  open: boolean;
  editingEvidence: ClueEvidenceRow | null;
  notaryOfficeOptions: { value: string }[];
  evidenceEditForm: any;
  onOk: () => void;
  onCancel: () => void;
}

export default function EvidenceEditorModal({
  open,
  editingEvidence,
  notaryOfficeOptions,
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
        <Form.Item label="取证机构" name="notary_institution" rules={[{ required: true, message: "请输入取证机构" }]}>
          <AutoComplete options={notaryOfficeOptions} placeholder="选择或填写取证机构" />
        </Form.Item>
        <div className="form-grid">
          <Form.Item label="公证书号" name="certificate_no"><Input /></Form.Item>
          <Form.Item label="取证时间" name="collected_at" rules={[{ required: true, message: "请选择取证时间" }]}><DatePicker style={{ width: "100%" }} /></Form.Item>
          <Form.Item label="发票号码" name="invoice_no"><Input /></Form.Item>
          <Form.Item label="证物状态" name="evidence_status"><Select options={["未入库", "已入库", "已出库", "已重新入库", "已销毁"].map(value => ({ value, label: value }))} /></Form.Item>
        </div>
        <Form.Item label="证物存放处" name="storage_location"><Input /></Form.Item>
        <Form.Item label="证据文件"><Input disabled value={editingEvidence?.files?.map(file => file.original_name).join("、") || "无"} /></Form.Item>
      </Form>
    </Modal>
  );
}
