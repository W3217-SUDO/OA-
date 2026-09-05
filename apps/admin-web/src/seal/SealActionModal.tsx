import {
  Button,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Upload,
} from "antd";
import { UploadOutlined } from "@ant-design/icons";
import type { FormInstance } from "antd";
import type { AttachmentRow, SealActionState } from "./types";
import { personDisplayName } from "./constants";

interface SealActionModalProps {
  action: SealActionState | null;
  form: FormInstance;
  submitting: boolean;
  stampAttachments: AttachmentRow[];
  stampAttachmentLoading: boolean;
  stampAttachmentUploading: boolean;
  stampAttachmentUploadFailed: boolean;
  stampAttachmentTotal: number;
  onOk: () => void;
  onCancel: () => void;
  onOpenDetail: () => void;
  onStampAttachmentChange: (values: number[]) => void;
  onLoadMoreStampAttachments: () => void;
  onUploadStampAttachments: (files: File[]) => void;
}

export function SealActionModal({
  action,
  form,
  submitting,
  stampAttachments,
  stampAttachmentLoading,
  stampAttachmentUploading,
  stampAttachmentUploadFailed,
  stampAttachmentTotal,
  onOk,
  onCancel,
  onOpenDetail,
  onStampAttachmentChange,
  onLoadMoreStampAttachments,
  onUploadStampAttachments,
}: SealActionModalProps) {
  const actionType = action?.type || "approve";
  const titleMap: Record<string, string> = {
    approve: "审批通过",
    reject: "审批拒绝",
    stamp: "登记实际用印",
    archive: "归档用印材料",
  };

  return (
    <Modal
      open={Boolean(action)}
      title={titleMap[actionType]}
      okText="确认"
      cancelText="取消"
      confirmLoading={submitting}
      onOk={onOk}
      onCancel={onCancel}
    >
      {(actionType === "approve" || actionType === "reject") && (
        <Descriptions
          size="small"
          bordered
          column={1}
          items={[
            {
              key: "serial_no",
              label: "用印编号",
              children: action?.row.serial_no,
            },
            {
              key: "title",
              label: "申请标题",
              children: action?.row.title,
            },
            {
              key: "customer",
              label: "客户",
              children: action?.row.customer || "—",
            },
            {
              key: "contract_no",
              label: "合同编号",
              children: action?.row.data.contract_no || "—",
            },
            {
              key: "customer_no",
              label: "客户编号",
              children: action?.row.data.customer_no || "—",
            },
            {
              key: "seal_type",
              label: "印章类型",
              children:
                action?.row.data.seal_type ||
                action?.row.seal_asset?.seal_type ||
                "—",
            },
            {
              key: "electronic",
              label: "是否电章",
              children: action?.row.data.is_electronic_seal ? "是" : "否",
            },
            {
              key: "offline_print",
              label: "是否打印盖章",
              children: action?.row.data.is_offline_print ? "需要" : "不需要",
            },
            {
              key: "print_quantity",
              label: "盖章份数",
              children:
                action?.row.data.print_quantity ??
                action?.row.data.copies ??
                "—",
            },
            {
              key: "remark",
              label: "用印备注",
              children: action?.row.data.remark || action?.row.description || "—",
            },
          ]}
          style={{ marginBottom: 12 }}
        />
      )}
      {(actionType === "approve" || actionType === "reject") && (
        <Button
          type="link"
          onClick={onOpenDetail}
        >
          查看用印文件
        </Button>
      )}
      <Form form={form} layout="vertical">
        {actionType === "stamp" && (
          <>
            <Form.Item
              label="实际用印份数"
              name="actual_copies"
              rules={[{ required: true }]}
            >
              <InputNumber
                min={1}
                max={action?.row.data.copies}
                style={{ width: "100%" }}
              />
            </Form.Item>
            <Form.Item
              label="用印操作人"
              name="operator"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="归档号"
              name="archive_no"
            >
              <Input placeholder="例如：YY-2026-0042" />
            </Form.Item>
            <Form.Item
              label="盖章文件"
              name="stamp_attachment_ids"
            >
              <Select
                mode="multiple"
                allowClear
                loading={stampAttachmentLoading || stampAttachmentUploading}
                placeholder="选择已上传盖章文件"
                options={stampAttachments.map((file) => ({
                  value: file.id,
                  label: file.original_name + "｜" + personDisplayName(file.uploader_display_name),
                }))}
                onChange={(values) => {
                  onStampAttachmentChange(values.map(Number).filter(Boolean));
                }}
                dropdownRender={(menu) => (
                  <>
                    {menu}
                    {stampAttachmentTotal > stampAttachments.length && (
                      <div style={{ padding: 8, textAlign: "center" }}>
                        <Button
                          type="link"
                          size="small"
                          loading={stampAttachmentLoading}
                          onMouseDown={(event) => event.preventDefault()}
                          onClick={() => onLoadMoreStampAttachments()}
                        >
                          加载更多盖章文件（{stampAttachments.length}/{stampAttachmentTotal}）
                        </Button>
                      </div>
                    )}
                  </>
                )}
              />
            </Form.Item>
            <Upload
              multiple
              showUploadList={false}
              beforeUpload={(file, fileList) => {
                const firstFile = fileList[0] as File & { uid?: string };
                const currentFile = file as File & { uid?: string };
                if (!firstFile || firstFile.uid === currentFile.uid || firstFile === currentFile) {
                  onUploadStampAttachments(fileList as File[]);
                }
                return Upload.LIST_IGNORE;
              }}
            >
              <Button icon={<UploadOutlined />} loading={stampAttachmentUploading}>
                上传盖章文件
              </Button>
            </Upload>
          </>
        )}
        <Form.Item
          label="审批/操作意见"
          name="comment"
          rules={
            actionType === "reject"
              ? [{ required: true, message: "拒绝时必须填写原因" }]
              : []
          }
        >
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
