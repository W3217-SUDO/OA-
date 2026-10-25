import { POPUP_WIDTH } from "../components/common/popupSize";
import { useEffect, useState } from "react";
import { Alert, Empty, List, Modal, Spin, Tag } from "antd";
import { api } from "../api";

type CaseAgentFile = {
  id: number;
  original_name?: string;
  name?: string;
  content_type?: string;
  size?: number;
  status?: string;
  created_at?: string;
  source_kind?: string;
};

type Props = {
  open: boolean;
  caseId: number | null;
  serialNo?: string;
  onClose: () => void;
};

const statusLabel: Record<string, string> = {
  available: "可用",
  uploading: "保存中",
  failed: "保存失败",
  uncertain: "待核对",
};

function formatSize(size?: number) {
  if (!Number.isFinite(size) || !size) return "大小未知";
  if (size < 1024) return `${size} 字节`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

export function CaseAgentFileFolderModal({ open, caseId, serialNo, onClose }: Props) {
  const [files, setFiles] = useState<CaseAgentFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open || !caseId) return;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setFiles([]);
    void api.get<{ items?: CaseAgentFile[] }>(`/cases/${caseId}/ai-space`, { signal: controller.signal })
      .then(({ data }) => {
        if (!controller.signal.aborted) setFiles(Array.isArray(data?.items) ? data.items : []);
      })
      .catch((failure) => {
        if (!controller.signal.aborted) setError(failure?.response?.data?.detail || "案件智能体文件夹加载失败");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [open, caseId]);

  return <Modal open={open} title={`案件智能体文件夹${serialNo ? ` · ${serialNo}` : ""}`} footer={null} width={POPUP_WIDTH.md} onCancel={onClose} destroyOnHidden>
    {error && <Alert type="error" showIcon title="文件夹加载失败" description={error} />}
    {loading ? <Spin tip="正在读取案件智能体生成文件" /> : files.length ? <>
      <div className="case-agent-folder-summary">当前案件智能体已生成 <strong>{files.length}</strong> 个文件</div>
      <List
        dataSource={files}
        renderItem={(file) => <List.Item>
          <List.Item.Meta
            title={<span>{file.original_name || file.name || "未命名文件"} {file.status && <Tag color={file.status === "available" ? "success" : file.status === "failed" ? "error" : "processing"}>{statusLabel[file.status] || file.status}</Tag>}</span>}
            description={<span>{file.content_type || "文件"} · {formatSize(file.size)}{file.created_at ? ` · ${new Date(file.created_at).toLocaleString("zh-CN", { hour12: false })}` : ""}</span>}
          />
        </List.Item>}
      />
    </> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前案件智能体尚未生成文件" />}
  </Modal>;
}
