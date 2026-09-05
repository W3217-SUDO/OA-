import { Button, Descriptions, Drawer, Space, Tag } from "antd";
import { DownloadOutlined } from "@ant-design/icons";
import type { Attachment, Template } from "./types";
import { fileSize, personDisplayName } from "./constants";

// ===== 附件详情 Drawer =====
interface AttachmentDetailDrawerProps {
  open: boolean;
  attachmentDetail: Attachment | null;
  onClose: () => void;
  onDownload: (row: Attachment) => void;
  onOpenRecord: (attachment: Attachment) => void;
}

export function AttachmentDetailDrawer({
  open,
  attachmentDetail,
  onClose,
  onDownload,
  onOpenRecord,
}: AttachmentDetailDrawerProps) {
  return (
    <Drawer
      size={560}
      open={open}
      title={`附件详情：${attachmentDetail?.original_name || ""}`}
      onClose={onClose}
      extra={
        attachmentDetail && (
          <Button type="primary" icon={<DownloadOutlined />} onClick={() => onDownload(attachmentDetail)}>
            下载附件
          </Button>
        )
      }
    >
      {attachmentDetail && (
        <Descriptions bordered size="small" column={1}>
          <Descriptions.Item label="文件名称">{attachmentDetail.original_name}</Descriptions.Item>
          <Descriptions.Item label="分类">{attachmentDetail.category || "—"}</Descriptions.Item>
          <Descriptions.Item label="关联编号">
            {attachmentDetail.record_no || "公共文件"}
          </Descriptions.Item>
          <Descriptions.Item label="关联业务">
            {attachmentDetail.record_id ? (
              <Button type="link" onClick={() => onOpenRecord(attachmentDetail)}>
                {attachmentDetail.record_title || attachmentDetail.record_no || "查看关联业务"}
              </Button>
            ) : (
              "公共文件"
            )}
          </Descriptions.Item>
          <Descriptions.Item label="大小">{fileSize(attachmentDetail.size)}</Descriptions.Item>
          <Descriptions.Item label="上传人">
            {personDisplayName(attachmentDetail.uploader_display_name)}
          </Descriptions.Item>
          <Descriptions.Item label="上传时间">
            {attachmentDetail.created_at
              ? new Date(attachmentDetail.created_at).toLocaleString()
              : "—"}
          </Descriptions.Item>
          <Descriptions.Item label="备注">{attachmentDetail.remark || "—"}</Descriptions.Item>
        </Descriptions>
      )}
    </Drawer>
  );
}

// ===== 模板详情 Drawer =====
interface TemplateDetailDrawerProps {
  open: boolean;
  templateDetail: Template | null;
  onClose: () => void;
}

export function TemplateDetailDrawer({
  open,
  templateDetail,
  onClose,
}: TemplateDetailDrawerProps) {
  return (
    <Drawer
      size={560}
      open={open}
      title={`模板详情：${templateDetail?.name || ""}`}
      onClose={onClose}
    >
      {templateDetail && (
        <Descriptions bordered size="small" column={1}>
          <Descriptions.Item label="模板名称">{templateDetail.name}</Descriptions.Item>
          <Descriptions.Item label="分类">{templateDetail.category || "—"}</Descriptions.Item>
          <Descriptions.Item label="版本">{templateDetail.version || "—"}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={templateDetail.is_active ? "green" : "default"}>
              {templateDetail.is_active ? "启用" : "停用"}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="模板字段">
            <Space wrap>
              {(templateDetail.fields || []).map((field) => (
                <Tag key={field}>{field}</Tag>
              )) || "—"}
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="说明">{templateDetail.description || "—"}</Descriptions.Item>
        </Descriptions>
      )}
    </Drawer>
  );
}
