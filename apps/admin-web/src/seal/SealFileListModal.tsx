import { Button, Modal, Space, Table } from "antd";
import dayjs from "dayjs";
import type { AttachmentRow, SealRow } from "./types";
import { personDisplayName } from "./constants";
import { sealFilePagination, getSealAttachmentExtension, formatSealAttachmentSize } from "../sealWorkflowPolicy";

interface SealFileListModalProps {
  open: boolean;
  row: SealRow | null;
  attachments: AttachmentRow[];
  page: number;
  pageSize: number;
  total: number;
  onClose: () => void;
  onPageChange: (page: number, pageSize: number) => void;
  onPreview: (item: AttachmentRow) => void;
  onDownload: (item: AttachmentRow) => void;
}

export function SealFileListModal({
  open,
  row,
  attachments,
  page,
  pageSize,
  total,
  onClose,
  onPageChange,
  onPreview,
  onDownload,
}: SealFileListModalProps) {
  return (
    <Modal
      open={open}
      title="文件列表"
      onCancel={onClose}
      footer={<Button onClick={onClose}>关闭</Button>}
    >
      <Table
        size="small"
        rowKey="id"
        pagination={{
          current: page,
          pageSize: pageSize,
          total: total,
          showSizeChanger: sealFilePagination.showSizeChanger,
          pageSizeOptions: sealFilePagination.pageSizeOptions.map(String),
          showQuickJumper: sealFilePagination.showQuickJumper,
          showTotal: sealFilePagination.showTotal,
          onChange: onPageChange,
        }}
        locale={{ emptyText: "" }}
        dataSource={attachments}
        columns={[
          { title: "上传人", dataIndex: "uploader_display_name", render: personDisplayName },
          { title: "文件名称", dataIndex: "original_name" },
          {
            title: "类型",
            width: 70,
            render: (_: unknown, item: AttachmentRow) =>
              getSealAttachmentExtension(item.original_name) || "—",
          },
          {
            title: "大小",
            width: 90,
            dataIndex: "size",
            render: (value: number) => formatSealAttachmentSize(value),
          },
          {
            title: "文件日期",
            dataIndex: "created_at",
            render: (value: string) => dayjs(value).format("YYYY-MM-DD"),
          },
          {
            title: "操作",
            render: (_: unknown, item: AttachmentRow) => (
              <Space size={0}>
                <Button type="link" onClick={() => onPreview(item)}>查看</Button>
                <Button type="link" onClick={() => onDownload(item)}>下载</Button>
              </Space>
            ),
          },
        ]}
      />
      {!row && <span>暂无文件</span>}
    </Modal>
  );
}
