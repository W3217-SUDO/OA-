import { Alert, Button, Modal } from "antd";
import type { SealPreviewMode } from "./types";

interface SealPreviewModalProps {
  open: boolean;
  name: string;
  mode: SealPreviewMode;
  url: string;
  text: string;
  detail: string;
  onClose: () => void;
}

export function SealPreviewModal({
  open,
  name,
  mode,
  url,
  text,
  detail,
  onClose,
}: SealPreviewModalProps) {
  return (
    <Modal
      open={open}
      title={`文件预览：${name}`}
      width={900}
      footer={<Button onClick={onClose}>关闭</Button>}
      onCancel={onClose}
    >
      {mode === "binary" && url && (
        <iframe
          title={name}
          src={url}
          style={{ width: "100%", height: 620, border: 0 }}
        />
      )}
      {mode === "text" && (
        <pre style={{ maxHeight: 620, overflow: "auto", whiteSpace: "pre-wrap" }}>
          {text}
        </pre>
      )}
      {mode === "unsupported" && <Alert type="info" message={detail || "当前文件格式暂不支持在线预览，请下载后查看"} />}
    </Modal>
  );
}
