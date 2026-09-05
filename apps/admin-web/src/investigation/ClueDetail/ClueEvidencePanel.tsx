import { Table, Typography, Button, Space } from "antd";
import type { Attachment, ClueEvidenceRow, ClueWorkspace } from "../types";

interface ClueEvidencePanelProps {
  clueWorkspace: ClueWorkspace | null;
  clueWorkspaceLoading: boolean;
  selectedEvidenceId: number | null;
  onSelectEvidence: (id: number | null) => void;
  onEditEvidence: () => void;
  onDeleteEvidence: () => void;
  onDownloadFile: (row: Attachment) => void;
}

export default function ClueEvidencePanel({
  clueWorkspace,
  clueWorkspaceLoading,
  selectedEvidenceId,
  onSelectEvidence,
  onEditEvidence,
  onDeleteEvidence,
  onDownloadFile,
}: ClueEvidencePanelProps) {
  const selectedEvidence = clueWorkspace?.evidence.find((item) => item.id === selectedEvidenceId) || null;


  return (
    <div className="clue-workspace">
      <Typography.Title level={5}>线索文件</Typography.Title>
      <Table<Attachment>
        rowKey="id"
        size="small"
        loading={clueWorkspaceLoading}
        pagination={false}
        dataSource={clueWorkspace?.clue_files || []}
        columns={[
          { title: "上传人", width: 120, render: (_, row) => row.uploader_display_name || row.uploader || "—" },
          { title: "文件名称", dataIndex: "original_name" },
          { title: "文档日期", width: 150, render: (_, row) => String(row.created_at || "").replace("T", " ").slice(0, 19) || "—" },
          { title: "操作", width: 80, render: (_, row) => <Button type="link" onClick={() => onDownloadFile(row)}>下载</Button> },
        ]}
      />
      <Typography.Title level={5}>取证信息</Typography.Title>
      <Table<ClueEvidenceRow>
        rowKey="id"
        size="small"
        loading={clueWorkspaceLoading}
        pagination={false}
        rowSelection={{
          type: "radio",
          selectedRowKeys: selectedEvidenceId ? [selectedEvidenceId] : [],
          onChange: (keys) => onSelectEvidence(Number(keys[0]) || null),
        }}
        dataSource={clueWorkspace?.evidence || []}
        scroll={{ x: 1180 }}
        columns={[
          { title: "取证编号", dataIndex: "serial_no", width: 170 },
          { title: "取证日期", width: 120, render: (_, row) => row.data.collected_at || "—" },
          { title: "取证机构", width: 180, render: (_, row) => row.data.notary_institution || "—" },
          { title: "公证书号", width: 180, render: (_, row) => row.data.notarization_no || row.data.certificate_no || "—" },
          { title: "发票号", width: 140, render: (_, row) => row.data.invoice_no || "—" },
          { title: "证物存放处", width: 180, render: (_, row) => row.data.storage_location || "—" },
          { title: "证物状态", width: 110, render: (_, row) => row.data.storage_state || row.data.evidence_status || row.status || "—" },
          { title: "文件", width: 80, render: (_, row) => row.files?.length || 0 },
        ]}
      />
      <Space style={{ marginTop: 12 }}>
        <Button danger disabled={!selectedEvidence?.can_delete} onClick={onDeleteEvidence}>
          删除
        </Button>
        <Button disabled={!selectedEvidence?.can_edit} onClick={onEditEvidence}>
          修改
        </Button>
      </Space>
    </div>
  );
}
