import { useEffect, useState } from "react";
import { Alert, Modal, Spin } from "antd";
import { api } from "../api";
import { AttachmentPreviewContent, type PreviewAttachment } from "../components/common/AttachmentContent";
import { errorText, type Material } from "./types";

export function MaterialPreview({ item, onClose }: { item: Material | null; onClose: () => void }) {
  const [preview, setPreview] = useState<PreviewAttachment | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!item) return;
    let active = true;
    let objectUrl = "";
    setLoading(true); setError(""); setPreview(null);
    void (async () => {
      try {
        const options = { params: item.case_id ? { case_id: item.case_id } : undefined };
        const { data } = await api.get<{ kind: string; text?: string; detail?: string }>(`/attachments/${item.id}/preview`, options);
        if (data.kind === "unsupported") throw new Error(data.detail || "文件暂不支持预览");
        const value: PreviewAttachment = { name: item.name, kind: data.kind, text: data.text };
        if (["image", "pdf", "docx", "xlsx"].includes(data.kind)) {
          const response = await api.get<Blob>(`/attachments/${item.id}/download`, { ...options, responseType: "blob" });
          value.blob = response.data;
          if (data.kind === "image" || data.kind === "pdf") { objectUrl = URL.createObjectURL(response.data); value.url = objectUrl; }
        }
        if (active) setPreview(value);
        else if (objectUrl) URL.revokeObjectURL(objectUrl);
      } catch (failure) { if (active) setError(errorText(failure, "材料预览失败")); }
      finally { if (active) setLoading(false); }
    })();
    return () => { active = false; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [item]);
  return <Modal open={!!item} title={item?.name} width={900} footer={null} onCancel={onClose}>
    {error ? <Alert type="error" showIcon title={error} /> : <Spin spinning={loading}><div style={{ minHeight: 120 }}><AttachmentPreviewContent preview={preview} /></div></Spin>}
  </Modal>;
}
