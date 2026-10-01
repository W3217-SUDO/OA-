import { CloseOutlined } from "@ant-design/icons";
import { Button, Space } from "antd";
import Table from "../components/ResizableTable";
import { CaseClueDetails } from "./CaseDetail/CaseClueDetails";
import type { AttachmentRow, CaseClueEvidenceRow, CaseClueWorkspace } from "./types";

type CaseClueContextPanelProps = {
  workspace: CaseClueWorkspace | null;
  loading: boolean;
  selectedEvidenceId: number | null;
  onClose: () => void;
  onSelectEvidence: (id: number | null) => void;
  onDownloadFile: (file: AttachmentRow) => void;
  onDeleteEvidence: () => void;
  onEditEvidence: () => void;
};

export function CaseClueContextPanel({
  workspace,
  loading,
  selectedEvidenceId,
  onClose,
  onSelectEvidence,
  onDownloadFile,
  onDeleteEvidence,
  onEditEvidence,
}: CaseClueContextPanelProps) {
  if (!workspace) return null;
  const selectedEvidence = workspace.evidence.find((item) => item.id === selectedEvidenceId) || null;
  return (
    <aside className="case-clue-context-panel" aria-label="案件内线索信息" data-testid="case-clue-context-panel">
      <div className="case-clue-context-header">
        <strong>线索信息</strong>
        <Button type="text" size="small" icon={<CloseOutlined />} aria-label="关闭线索信息" onClick={onClose}>关闭</Button>
      </div>
      <div className="case-clue-context-body">
        <CaseClueDetails clue={workspace.clue} />
        <section className="case-clue-context-section">
          <h3>线索文件</h3>
          <Table<AttachmentRow>
            rowKey="id"
            size="small"
            loading={loading}
            pagination={false}
            dataSource={workspace.clue_files || []}
            locale={{ emptyText: "没有查询到线索文件。" }}
            columns={[
              { title: "上传人", width: 110, render: (_, row) => row.uploader_display_name || row.uploader || "—" },
              { title: "文件名称", dataIndex: "original_name" },
              { title: "文档日期", width: 150, render: (_, row) => String(row.created_at || "").replace("T", " ").slice(0, 19) || "—" },
              { title: "操作", width: 70, render: (_, row) => <Button type="link" onClick={() => void onDownloadFile(row)}>下载</Button> },
            ]}
          />
        </section>
        <section className="case-clue-context-section">
          <h3>取证信息</h3>
          <Table<CaseClueEvidenceRow>
            rowKey="id"
            size="small"
            loading={loading}
            pagination={false}
            rowSelection={{
              type: "radio",
              selectedRowKeys: selectedEvidenceId ? [selectedEvidenceId] : [],
              onChange: (keys) => onSelectEvidence(Number(keys[0]) || null),
            }}
            dataSource={workspace.evidence || []}
            locale={{ emptyText: "没有查询到取证信息。" }}
            scroll={{ x: 1040 }}
            columns={[
              { title: "公证书号", width: 170, render: (_, row) => row.data.notarization_no || row.data.certificate_no || "—" },
              { title: "取证时间", width: 120, render: (_, row) => row.data.collected_at || "—" },
              { title: "取证机构", width: 180, render: (_, row) => row.data.notary_institution || "—" },
              { title: "发票号", width: 130, render: (_, row) => row.data.invoice_no || "—" },
              { title: "仓库", width: 130, render: (_, row) => row.data.warehouse_name || row.data.warehouse || row.data.storage_location || "—" },
              { title: "库位", width: 120, render: (_, row) => row.data.storage_location_name || row.data.location_name || row.data.storage_location || "—" },
              { title: "状态", width: 105, render: (_, row) => row.data.storage_state || row.data.evidence_status || row.status || "—" },
              { title: "文件", width: 70, render: (_, row) => row.files?.length || 0 },
            ]}
          />
          <Space className="case-clue-context-actions">
            <Button danger disabled={!selectedEvidence?.can_delete} onClick={onDeleteEvidence}>删除</Button>
            <Button disabled={!selectedEvidence?.can_edit} onClick={onEditEvidence}>修改</Button>
          </Space>
        </section>
      </div>
    </aside>
  );
}
