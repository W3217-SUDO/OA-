import { Modal, Alert, Space, Button } from "antd";
import { DownloadOutlined } from "@ant-design/icons";
import type { ModuleKey } from "./types";

interface ImportResultError {
  row: number;
  error: string;
}

interface ImportResult {
  created: number;
  failed: number;
  errors: ImportResultError[];
}

interface ImportModalProps {
  open: boolean;
  tab: ModuleKey;
  importFile: File | null;
  importResult: ImportResult | null;
  onOk: () => void;
  onCancel: () => void;
  onFileChange: (file: File | null) => void;
  onDownloadTemplate: () => void;
}

export default function ImportModal({
  open,
  tab,
  importFile,
  importResult,
  onOk,
  onCancel,
  onFileChange,
  onDownloadTemplate,
}: ImportModalProps) {
  return (
    <Modal
      open={open}
      title={`${tab === "notary" ? "公证记录" : "调查线索"}批量导入`}
      okText="开始导入"
      cancelText="关闭"
      onOk={onOk}
      onCancel={onCancel}
    >
      <Alert
        type="info"
        showIcon
        title={
          tab === "notary"
            ? "仅支持 UTF-8 CSV；来源线索必须存在且尚未生成公证记录。"
            : "仅支持 UTF-8 CSV；每一行只能填写一种侵权产品，重复线索不会导入。"
        }
      />
      <Space orientation="vertical" className="import-box">
        <Button icon={<DownloadOutlined />} onClick={onDownloadTemplate}>
          下载 CSV 模板
        </Button>
        <input
          type="file"
          accept=".csv,text/csv"
          onChange={(e) => onFileChange(e.target.files?.[0] || null)}
        />
        {importResult && (
          <Alert
            type={importResult.failed ? "warning" : "success"}
            showIcon
            title={`成功 ${importResult.created} 条，失败 ${importResult.failed} 条`}
            description={importResult.errors.slice(0, 8).map((x) => (
              <div key={`${x.row}-${x.error}`}>
                第 {x.row} 行：{x.error}
              </div>
            ))}
          />
        )}
      </Space>
    </Modal>
  );
}
