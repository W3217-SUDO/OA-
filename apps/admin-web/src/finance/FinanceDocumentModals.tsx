import { DeleteOutlined, DownloadOutlined, UploadOutlined } from "@ant-design/icons";
import { Alert, Button, DatePicker, Form, Input, Modal, Select, Space, Tag, TreeSelect } from "antd";
import type { FormInstance } from "antd";
import Table from "../components/ResizableTable";
import type { RecordFileFormValues, VoucherFormValues } from "./formTypes";
import type { Attachment, FinanceFlow, RecordFileTypeNode, Transaction } from "./types";

export interface RecordFilesModalProps {
  target: FinanceFlow | null;
  targets: FinanceFlow[];
  files: Attachment[];
  form: FormInstance<RecordFileFormValues>;
  typeTree: RecordFileTypeNode[];
  role: string;
  onClose: () => void;
  onDownload: (file: Attachment) => void;
  onDelete: (file: Attachment) => void;
  onUpload: () => Promise<unknown>;
  onUploadFilesChange: (files: File[]) => void;
  onFileChange: (file: File | null) => void;
}

export function RecordFilesModal({
  target: recordFileTarget,
  targets: recordFileTargets,
  files: recordFiles,
  form: recordFileForm,
  typeTree: recordFileTypeTree,
  role,
  onClose,
  onDownload: downloadVoucher,
  onDelete: deleteRecordFile,
  onUpload: uploadRecordFile,
  onUploadFilesChange: setRecordUploadFiles,
  onFileChange: setRecordFile,
}: RecordFilesModalProps) {
  return (
      <Modal
        width={760}
        open={Boolean(recordFileTarget)}
        title={recordFileTargets.length > 1 ? `批量上传案件文档（已选 ${recordFileTargets.length} 个案件）` : `业务凭证：${recordFileTarget?.serial_no || ""}`}
        footer={null}
        onCancel={onClose}
      >
        <Table
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={recordFiles}
          locale={{ emptyText: "尚未上传凭证" }}
          columns={[
            {
              title: "凭证类型",
              dataIndex: "category",
              width: 120,
              render: (v: string) => <Tag color="blue">{v}</Tag>,
            },
            { title: "文件名", dataIndex: "original_name" },
            {
              title: "大小",
              dataIndex: "size",
              width: 90,
              render: (v: number) => `${(v / 1024).toFixed(1)} KB`,
            },
            { title: "上传人", dataIndex: "uploader", width: 85 },
            {
              title: "操作",
              width: 130,
              render: (_: unknown, r: Attachment) => (
                <Space size={0}>
                  <Button type="link" onClick={() => downloadVoucher(r)}>
                    下载
                  </Button>
                  {role === "admin" && (
                    <Button
                      type="link"
                      danger
                      onClick={() => deleteRecordFile(r)}
                    >
                      删除
                    </Button>
                  )}
                </Space>
              ),
            },
          ]}
        />
        <Form form={recordFileForm} layout="vertical" style={{ marginTop: 16 }}>
          <div className="form-grid">
            <Form.Item
              label="凭证类型"
              name="category"
              rules={[{ required: true }]}
            >
              {recordFileTargets.length > 1 ? (
                <TreeSelect
                  treeData={recordFileTypeTree.length ? recordFileTypeTree : [
                    {
                      title: "案件文件",
                      value: "CASE_GROUP",
                      children: [
                        { title: "主体及委托资料", value: "主体及委托资料" },
                        { title: "起诉材料及证据", value: "起诉材料及证据" },
                        { title: "答辩材料及证据", value: "答辩材料及证据" },
                        { title: "法院诉讼文书", value: "法院诉讼文书" },
                        { title: "庭审及庭后文件", value: "庭审及庭后文件" },
                        { title: "普通附件", value: "普通附件" },
                      ],
                    },
                    {
                      title: "调查文档",
                      value: "INVESTIGATION_GROUP",
                      children: [
                        { title: "鉴别资料", value: "鉴别资料" },
                        { title: "调查文档", value: "调查文档" },
                        { title: "取证文档", value: "取证文档" },
                      ],
                    },
                  ]}
                  treeDefaultExpandAll
                  placeholder="请选择文档类型"
                  treeNodeFilterProp="title"
                  showSearch
                />
              ) : (
                <Select
                  options={[
                    "发票扫描件",
                    "退费凭证",
                    "法院退费通知",
                    "银行回单",
                    "其他财务材料",
                  ].map((v) => ({ value: v, label: v }))}
                />
              )}
            </Form.Item>
            {recordFileTargets.length > 0 && <Form.Item label="参考日期" name="document_date" rules={[{ required: true }]}><DatePicker style={{ width: "100%" }} /></Form.Item>}
            <Form.Item label="选择文件" required>
              <input
                type="file"
                multiple={recordFileTargets.length > 0}
                accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx"
                onChange={(e) => {
                  const files = Array.from(e.target.files || []);
                  setRecordUploadFiles(files);
                  setRecordFile(files[0] || null);
                }}
              />
            </Form.Item>
          </div>
          <Form.Item label="说明" name="remark">
            <Input />
          </Form.Item>
          <Button
            type="primary"
            icon={<UploadOutlined />}
            onClick={uploadRecordFile}
          >
            上传凭证
          </Button>
        </Form>
      </Modal>
  );
}

export interface VoucherModalProps {
  open: boolean;
  target: Transaction | null;
  form: FormInstance<VoucherFormValues>;
  onClose: () => void;
  onUpload: () => Promise<void>;
  onFileChange: (file: File | null) => void;
  onDownload: (file: Attachment) => void;
  onDelete: (file: Attachment) => void;
}

export function VoucherModal({
  open: voucherOpen,
  target: voucherTarget,
  form: voucherForm,
  onClose,
  onUpload: uploadVoucher,
  onFileChange: setVoucherFile,
  onDownload: downloadVoucher,
  onDelete: deleteVoucher,
}: VoucherModalProps) {
  return (
      <Modal
        width={760}
        open={voucherOpen}
        title={`财务凭证：${voucherTarget?.transaction_type || ""} #${voucherTarget?.id || ""}`}
        footer={null}
        onCancel={onClose}
      >
        <Alert
          type="info"
          showIcon
          title="凭证与本笔流水单独关联，可在文件中心统一检索和下载。"
        />
        <Table
          className="voucher-table"
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={voucherTarget?.vouchers || []}
          locale={{ emptyText: "尚未上传凭证" }}
          columns={[
            {
              title: "凭证类型",
              dataIndex: "category",
              width: 110,
              render: (v: string) => <Tag color="blue">{v}</Tag>,
            },
            { title: "文件名", dataIndex: "original_name", ellipsis: true },
            {
              title: "大小",
              dataIndex: "size",
              width: 90,
              render: (v: number) => `${(v / 1024).toFixed(1)} KB`,
            },
            { title: "上传人", dataIndex: "uploader", width: 80 },
            {
              title: "操作",
              key: "action",
              width: 125,
              render: (_: unknown, r: Attachment) => (
                <Space size={0}>
                  <Button
                    type="link"
                    icon={<DownloadOutlined />}
                    onClick={() => downloadVoucher(r)}
                  >
                    下载
                  </Button>
                  <Button
                    danger
                    type="link"
                    icon={<DeleteOutlined />}
                    onClick={() => deleteVoucher(r)}
                  >
                    删除
                  </Button>
                </Space>
              ),
            },
          ]}
        />
        <Form
          form={voucherForm}
          layout="vertical"
          className="voucher-upload-form"
        >
          <div className="form-grid">
            <Form.Item
              label="凭证类型"
              name="category"
              rules={[{ required: true }]}
            >
              <Select
                options={["付款凭证", "发票扫描件", "回款凭证", "退费凭证"].map(
                  (v) => ({ value: v, label: v }),
                )}
              />
            </Form.Item>
            <Form.Item label="选择文件" required>
              <input
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx"
                onChange={(e) => setVoucherFile(e.target.files?.[0] || null)}
              />
            </Form.Item>
          </div>
          <Form.Item label="附件说明" name="remark">
            <Input />
          </Form.Item>
          <Button
            type="primary"
            icon={<UploadOutlined />}
            onClick={uploadVoucher}
          >
            上传凭证
          </Button>
        </Form>
      </Modal>
  );
}
