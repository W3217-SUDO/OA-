import {
  Alert,
  Button,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Upload,
} from "antd";
import { UploadOutlined } from "@ant-design/icons";
import type { FormInstance } from "antd";
import type { AttachmentRow, RelationRow, SealAsset, SealRow } from "./types";
import { sealFilePagination, formatSealAttachmentSize } from "../sealWorkflowPolicy";

interface SealCreateModalProps {
  open: boolean;
  editingApplication: SealRow | null;
  form: FormInstance;
  submitting: boolean;
  isContractSeal: boolean;
  isCaseSeal: boolean;
  showSourceRelationFields: boolean;
  customers: RelationRow[];
  cases: RelationRow[];
  contracts: RelationRow[];
  availableAssets: SealAsset[];
  sourceAttachments: AttachmentRow[];
  sourceAttachmentLoading: boolean;
  sourceAttachmentTotal: number;
  pendingCreateFiles: File[];
  selectedSourceRecord: RelationRow | null;
  onCancel: () => void;
  onSave: () => void;
  onSubmit: () => void;
  onUseTypeChange: (value: string) => void;
  onQueueCreateFiles: (files: File[]) => void;
  onRemoveCreateFile: (file: { uid: string }) => void;
  onOpenDetailFromEdit: () => void;
  onLoadMoreSourceAttachments: () => void;
  onSelectAllSourceAttachments: () => void;
}

export function SealCreateModal({
  open,
  editingApplication,
  form,
  submitting,
  isContractSeal,
  isCaseSeal,
  showSourceRelationFields,
  customers,
  cases,
  contracts,
  availableAssets,
  sourceAttachments,
  sourceAttachmentLoading,
  sourceAttachmentTotal,
  pendingCreateFiles,
  selectedSourceRecord,
  onCancel,
  onSave,
  onSubmit,
  onUseTypeChange,
  onQueueCreateFiles,
  onRemoveCreateFile,
  onOpenDetailFromEdit,
  onLoadMoreSourceAttachments,
  onSelectAllSourceAttachments,
}: SealCreateModalProps) {
  return (
    <Modal
      open={open}
      title={editingApplication ? "修改用印申请" : "申请用印"}
      width={760}
      okText="保存草稿"
      cancelText="取消"
      confirmLoading={submitting}
      onOk={onSave}
      footer={[
        <Button
          key="cancel"
          onClick={onCancel}
        >
          取消
        </Button>,
        <Button
          key="save"
          loading={submitting}
          onClick={onSave}
        >
          保存草稿
        </Button>,
        <Button
          key="submit"
          type="primary"
          loading={submitting}
          onClick={onSubmit}
        >
          保存并提交审批
        </Button>,
      ]}
      onCancel={onCancel}
    >
      <Form form={form} layout="vertical">
        <div className="seal-form-grid">
          <Form.Item
            label="申请标题"
            name="title"
            rules={[{ required: true }]}
          >
            <Input placeholder="例如：民事起诉状用印" />
          </Form.Item>
          <Form.Item
            label="用印类型"
            name="use_type"
            rules={[{ required: true }]}
          >
            <Select
              onChange={onUseTypeChange}
              options={["合同用印", "案件用印", "行政用印"].map((x) => ({
                value: x,
                label: x,
              }))}
            />
          </Form.Item>
          {showSourceRelationFields && (
            <Form.Item label="客户/单位" name="customer" preserve={false}>
              <Select
                showSearch
                allowClear
                optionFilterProp="label"
                options={customers.map((x) => ({
                  value: x.title || x.customer,
                  label: `${x.title || x.customer}｜${x.serial_no}`,
                }))}
              />
            </Form.Item>
          )}
          {isCaseSeal && (
            <Form.Item
              label="关联案号"
              name="case_no"
              preserve={false}
              rules={[{ required: true, message: "案件用印必须选择关联案件" }]}
            >
              <Select
                showSearch
                allowClear
                optionFilterProp="label"
                options={cases.map((x) => ({
                  value: x.serial_no,
                  label: `${x.serial_no}｜${x.title}`,
                }))}
              />
            </Form.Item>
          )}
          {isContractSeal && (
            <Form.Item
              label="关联合同号"
              name="contract_no"
              preserve={false}
              rules={[{ required: true, message: "合同用印必须选择关联合同" }]}
            >
              <Select
                showSearch
                allowClear
                optionFilterProp="label"
                options={contracts.map((x) => ({
                  value: x.serial_no,
                  label: `${x.serial_no}｜${x.customer}｜${x.title}`,
                }))}
              />
            </Form.Item>
          )}
          {showSourceRelationFields && (
            <Form.Item
              label="来源附件"
              name="source_attachment_ids"
              preserve={false}
            >
              <Select
                mode="multiple"
                allowClear
                loading={sourceAttachmentLoading}
                placeholder={
                  selectedSourceRecord
                    ? "选择合同/案件来源附件"
                    : "请先选择关联合同或案件"
                }
                options={sourceAttachments.map((file) => ({
                  value: file.id,
                  label: `${file.original_name}｜${formatSealAttachmentSize(file.size)}`,
                }))}
                dropdownRender={(menu) => (
                  <>
                    {menu}
                    {selectedSourceRecord && (
                      <div style={{ padding: 8, textAlign: "center" }}>
                        <Button
                          type="link"
                          size="small"
                          loading={sourceAttachmentLoading}
                          onMouseDown={(event) => event.preventDefault()}
                          onClick={onSelectAllSourceAttachments}
                        >
                          选择全部来源附件
                        </Button>
                      </div>
                    )}
                    {selectedSourceRecord &&
                      sourceAttachmentTotal > sourceAttachments.length && (
                        <div style={{ padding: 8, textAlign: "center" }}>
                          <Button
                            type="link"
                            size="small"
                            loading={sourceAttachmentLoading}
                            onMouseDown={(event) => event.preventDefault()}
                            onClick={onLoadMoreSourceAttachments}
                          >
                            加载更多来源附件（{sourceAttachments.length}/{sourceAttachmentTotal}）
                          </Button>
                        </div>
                      )}
                  </>
                )}
              />
            </Form.Item>
          )}
          <Form.Item
            label="选择印章"
            name="seal_asset_id"
            rules={[{ required: true }]}
          >
            <Select
              options={availableAssets.map((x) => ({
                value: x.id,
                label: `${x.name}（${x.code}）`,
              }))}
            />
          </Form.Item>
          <Form.Item
            label="计划用印日期"
            name="use_date"
            rules={[{ required: true }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item
            label="用印份数"
            name="copies"
            rules={[{ required: true }]}
          >
            <InputNumber min={1} max={999} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="办理方式" name="delivery_method">
            <Select
              options={["现场用印", "邮寄用印", "外带用印"].map((x) => ({
                value: x,
                label: x,
              }))}
            />
          </Form.Item>
          <Form.Item label="是否电子印章" name="is_electronic_seal">
            <Select
              options={[
                { value: true, label: "是" },
                { value: false, label: "否" },
              ]}
            />
          </Form.Item>
          <Form.Item label="是否打印盖章" name="is_offline_print">
            <Select
              options={[
                { value: true, label: "需要" },
                { value: false, label: "不需要" },
              ]}
            />
          </Form.Item>
        </div>
        <Alert
          type="info"
          showIcon
          title="可在保存草稿前选择真实用印文件，保存后将自动上传；未上传文件不能提交审批。"
          style={{ marginBottom: 12 }}
        />
        <Form.Item label="待上传附件">
          <Upload
            multiple
            fileList={pendingCreateFiles.map((file, index) => ({
              uid: `${file.name}-${file.lastModified}-${index}`,
              name: file.name,
              status: "done" as const,
            }))}
            beforeUpload={(file, fileList) => {
              const firstFile = fileList[0] as File & { uid?: string };
              const currentFile = file as File & { uid?: string };
              if (!firstFile || firstFile.uid === currentFile.uid || firstFile === currentFile) {
                onQueueCreateFiles(fileList as File[]);
              }
              return Upload.LIST_IGNORE;
            }}
            onRemove={(file) => {
              onRemoveCreateFile(file);
            }}
          >
            <Button icon={<UploadOutlined />}>选择待上传附件</Button>
          </Upload>
        </Form.Item>
        {editingApplication && (
          <Button
            type="link"
            onClick={onOpenDetailFromEdit}
          >
            管理已有用印文件
          </Button>
        )}
        <Form.Item
          label="用印用途"
          name="purpose"
          rules={[{ required: true }]}
        >
          <Input />
        </Form.Item>
        <Form.Item label="申请说明" name="description">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// Re-export sealFilePagination for consistency with other components
export { sealFilePagination };
