import { Modal, Table, Form, Select, Input, Button, Space, Tag } from "antd";
import { DownloadOutlined, DeleteOutlined, UploadOutlined } from "@ant-design/icons";
import type { Attachment } from "./types";

interface MaterialModalProps {
  open: boolean;
  materialTarget: { serial_no: string } | null;
  materials: Attachment[];
  materialForm: any;
  materialFiles: File[];
  allowedCategories: string[];
  projectedPersonDisplayName: (displayName: unknown, username: unknown) => string;
  onCancel: () => void;
  onDownload: (row: Attachment) => void;
  onDelete: (row: Attachment) => void;
  onUpload: () => void;
  onFilesChange: (files: File[]) => void;
}

export default function MaterialModal({
  open,
  materialTarget,
  materials,
  materialForm,
  materialFiles,
  allowedCategories,
  projectedPersonDisplayName,
  onCancel,
  onDownload,
  onDelete,
  onUpload,
  onFilesChange,
}: MaterialModalProps) {
  return (
    <Modal
      width={780}
      open={open}
      title={`${materialTarget?.serial_no || ""}｜材料目录`}
      footer={null}
      onCancel={onCancel}
    >
      <Table
        rowKey="id"
        size="small"
        pagination={false}
        scroll={{ x: 720 }}
        dataSource={materials}
        locale={{ emptyText: "尚未上传材料" }}
        columns={[
          {
            title: "目录",
            dataIndex: "category",
            width: 120,
            render: (v: string) => <Tag color="blue">{v}</Tag>,
          },
          {
            title: "文件名",
            dataIndex: "original_name",
            width: 280,
            ellipsis: { showTitle: true },
          },
          {
            title: "大小",
            dataIndex: "size",
            width: 90,
            render: (v: number) => `${(v / 1024).toFixed(1)} KB`,
          },
          {
            title: "上传人",
            dataIndex: "uploader",
            width: 85,
            render: (_: unknown, row: Attachment) =>
              projectedPersonDisplayName(
                row.uploader_display_name,
                row.uploader,
              ),
          },
          {
            title: "操作",
            key: "action",
            width: 140,
            render: (_: unknown, r: Attachment) => (
              <Space size={0}>
                <Button
                  type="link"
                  icon={<DownloadOutlined />}
                  onClick={() => onDownload(r)}
                >
                  下载
                </Button>
                <Button
                  danger
                  type="link"
                  icon={<DeleteOutlined />}
                  onClick={() => onDelete(r)}
                >
                  删除
                </Button>
              </Space>
            ),
          },
        ]}
      />
      <Form
        form={materialForm}
        layout="vertical"
        className="material-upload-form"
      >
        <div className="form-grid">
          <Form.Item
            label="材料目录"
            name="category"
            rules={[{ required: true }]}
          >
            <Select
              options={allowedCategories.map((v) => ({ value: v, label: v }))}
            />
          </Form.Item>
          <Form.Item label="批量选择文件" required>
            <input
              multiple
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx,.zip,.rar"
              onChange={(e) =>
                onFilesChange(Array.from(e.target.files || []))
              }
            />
          </Form.Item>
        </div>
        <Form.Item label="材料说明" name="remark">
          <Input />
        </Form.Item>
        <Button
          type="primary"
          icon={<UploadOutlined />}
          onClick={onUpload}
        >
          批量上传{materialFiles.length ? `（${materialFiles.length}）` : ""}
        </Button>
      </Form>
    </Modal>
  );
}
