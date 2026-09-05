import {
  Alert,
  Button,
  Checkbox,
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
import dayjs from "dayjs";
import type { ReceiptRow, RecordRow, SealAsset, Template, Attachment } from "./types";
import { allCategories, fileSize, templateCategoryOptions } from "./constants";

// ===== 收发文登记 Modal =====
interface DocumentCreateModalProps {
  open: boolean;
  documentForm: FormInstance;
  cases: RecordRow[];
  onCreate: () => void;
  onCancel: () => void;
}

export function DocumentCreateModal({
  open,
  documentForm,
  cases,
  onCreate,
  onCancel,
}: DocumentCreateModalProps) {
  return (
    <Modal
      open={open}
      title="登记收发文"
      okText="保存草稿"
      cancelText="取消"
      onOk={onCreate}
      onCancel={onCancel}
    >
      <Form form={documentForm} layout="vertical">
        <Alert
          type="info"
          showIcon
          title="保存后先进入待登记；核对资料并上传附件后点击“完成登记”。"
          style={{ marginBottom: 16 }}
        />
        <Form.Item label="文件名称" name="title" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <div className="form-grid">
          <Form.Item label="收发类型" name="direction" rules={[{ required: true }]}>
            <Select options={["收文", "发文"].map((v) => ({ value: v, label: v }))} />
          </Form.Item>
          <Form.Item label="文件日期" name="document_date" rules={[{ required: true }]}>
            <DatePicker style={{ width: "100%" }} format="YYYY-MM-DD" />
          </Form.Item>
          <Form.Item label="负责人" name="owner">
            <Input />
          </Form.Item>
          <Form.Item label="客户" name="customer">
            <Input />
          </Form.Item>
          <Form.Item label="关联案号" name="case_no">
            <Select
              allowClear
              showSearch
              options={cases.map((c) => ({
                value: c.serial_no,
                label: `${c.serial_no}｜${c.title}`,
              }))}
            />
          </Form.Item>
          <Form.Item label="来文/送达单位" name="sender">
            <Input />
          </Form.Item>
        </div>
        <Form.Item label="备注" name="description">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ===== 上传文件 Modal =====
interface UploadModalProps {
  open: boolean;
  uploadForm: FormInstance;
  uploadTarget: RecordRow | null;
  tab: string;
  cases: RecordRow[];
  documents: RecordRow[];
  file: File | null;
  onFileChange: (file: File | null) => void;
  onOk: () => void;
  onCancel: () => void;
}

export function UploadModal({
  open,
  uploadForm,
  uploadTarget,
  tab,
  cases,
  documents,
  file,
  onFileChange,
  onOk,
  onCancel,
}: UploadModalProps) {
  const isOfficial = tab === "official";
  const options = isOfficial ? cases : [...cases, ...documents];

  return (
    <Modal
      open={open}
      title={`上传文件${uploadTarget ? `：${uploadTarget.serial_no}` : ""}`}
      okText="开始上传"
      cancelText="取消"
      onOk={onOk}
      onCancel={onCancel}
    >
      <Form form={uploadForm} layout="vertical">
        <Form.Item label={isOfficial ? "关联案件" : "关联业务"} name="record_id">
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            options={options.map((r) => ({
              value: r.id,
              label: `${r.serial_no}｜${r.title}`,
            }))}
          />
        </Form.Item>
        {isOfficial && (
          <Form.Item
            label="文件日期"
            name="document_date"
            rules={[{ required: true, message: "请选择文件日期" }]}
          >
            <DatePicker style={{ width: "100%" }} format="YYYY-MM-DD" />
          </Form.Item>
        )}
        <Form.Item label="材料分类" name="category" rules={[{ required: true }]}>
          <Select options={allCategories.map((v) => ({ value: v, label: v }))} />
        </Form.Item>
        <Form.Item label="选择文件" required>
          <Upload
            beforeUpload={(f) => {
              onFileChange(f);
              return false;
            }}
            maxCount={1}
            onRemove={() => onFileChange(null)}
          >
            <Button icon={<UploadOutlined />}>选择文件（最大 20MB）</Button>
          </Upload>
          {file && <div style={{ marginTop: 8, color: "#666" }}>{file.name}</div>}
        </Form.Item>
        <Form.Item label="备注" name="remark">
          <Input.TextArea rows={2} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ===== 模板编辑 Modal =====
interface TemplateModalProps {
  open: boolean;
  templateForm: FormInstance;
  editingTemplate: Template | null;
  onSave: () => void;
  onCancel: () => void;
}

export function TemplateModal({
  open,
  templateForm,
  editingTemplate,
  onSave,
  onCancel,
}: TemplateModalProps) {
  return (
    <Modal
      open={open}
      title={editingTemplate ? "编辑文书模板" : "新增文书模板"}
      okText="保存模板"
      cancelText="取消"
      onOk={onSave}
      onCancel={onCancel}
    >
      <Form form={templateForm} layout="vertical">
        <Form.Item label="模板名称" name="name" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <div className="form-grid">
          <Form.Item label="模板分类" name="category" rules={[{ required: true }]}>
            <Select options={templateCategoryOptions.map((v) => ({ value: v, label: v }))} />
          </Form.Item>
          <Form.Item label="版本" name="version">
            <Input />
          </Form.Item>
        </div>
        <Form.Item label="模板字段" name="fields">
          <Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入字段名后回车" />
        </Form.Item>
        <Form.Item label="模板说明" name="description">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ===== 流程动作 Modal =====
interface ActionModalProps {
  open: boolean;
  actionForm: FormInstance;
  actionStatus: string;
  direction?: string;
  onSubmit: () => void;
  onCancel: () => void;
}

export function ActionModal({
  open,
  actionForm,
  actionStatus,
  direction,
  onSubmit,
  onCancel,
}: ActionModalProps) {
  const getTitle = () => {
    if (actionStatus === "待签收") return "完成收发文登记";
    if (actionStatus === "已签收") {
      return direction === "发文" ? "确认文件送达" : "确认文件签收";
    }
    return "文档归档";
  };

  const getAlertTitle = () => {
    if (actionStatus === "待签收") return "登记完成后进入待签收，后续不能直接修改流程状态。";
    if (actionStatus === "已签收") return "请登记实际签收/送达人和日期，完成后可进入归档。";
    return "归档编号用于纸质及电子档案定位，归档后流程办结。";
  };

  return (
    <Modal
      open={open}
      title={getTitle()}
      okText="确认提交"
      cancelText="取消"
      onOk={onSubmit}
      onCancel={onCancel}
      destroyOnHidden
    >
      <Form form={actionForm} layout="vertical">
        <Alert
          type="info"
          showIcon
          title={getAlertTitle()}
          style={{ marginBottom: 16 }}
        />
        <Form.Item label="办理日期" name="action_date" rules={[{ required: true }]}>
          <DatePicker style={{ width: "100%" }} format="YYYY-MM-DD" />
        </Form.Item>
        {actionStatus === "已签收" && (
          <Form.Item
            label={direction === "发文" ? "送达确认人" : "签收人"}
            name="handler"
            rules={[{ required: true, message: "请填写人员" }]}
          >
            <Input />
          </Form.Item>
        )}
        {actionStatus === "已归档" && (
          <>
            <Form.Item
              label="归档编号"
              name="archive_no"
              rules={[{ required: true, message: "请填写归档编号" }]}
            >
              <Input />
            </Form.Item>
            <Form.Item label="存放位置" name="archive_location">
              <Input placeholder="例如：上海档案室 A-03-12" />
            </Form.Item>
          </>
        )}
        <Form.Item label="办理说明" name="comment">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ===== 收文日期 Modal =====
interface ReceiptDateModalProps {
  open: boolean;
  receiptDate: ReturnType<typeof dayjs> | null;
  selectedCount: number;
  onDateChange: (date: ReturnType<typeof dayjs> | null) => void;
  onOk: () => void;
  onCancel: () => void;
}

export function ReceiptDateModal({
  open,
  receiptDate,
  selectedCount,
  onDateChange,
  onOk,
  onCancel,
}: ReceiptDateModalProps) {
  return (
    <Modal
      open={open}
      title={`修改收文日期（已选 ${selectedCount} 条）`}
      okText="保存"
      cancelText="取消"
      onOk={onOk}
      onCancel={onCancel}
      destroyOnHidden
    >
      <Alert
        type="info"
        showIcon
        title="修改后会同步更新正式收文记录，并写入操作日志。"
        style={{ marginBottom: 16 }}
      />
      <DatePicker
        value={receiptDate}
        onChange={onDateChange}
        format="YYYY-MM-DD"
        style={{ width: "100%" }}
      />
    </Modal>
  );
}

// ===== 批量关联案件 Modal =====
interface CaseLinkModalProps {
  open: boolean;
  caseLinkForm: FormInstance<{ case_ids: number[] }>;
  cases: RecordRow[];
  linkingCases: boolean;
  selectedCount: number;
  onOk: () => void;
  onCancel: () => void;
}

export function CaseLinkModal({
  open,
  caseLinkForm,
  cases,
  linkingCases,
  selectedCount,
  onOk,
  onCancel,
}: CaseLinkModalProps) {
  return (
    <Modal
      open={open}
      title={`批量关联案件（已选 ${selectedCount} 条官文收文）`}
      okText="确认关联"
      cancelText="取消"
      confirmLoading={linkingCases}
      onOk={onOk}
      onCancel={onCancel}
      destroyOnHidden
    >
      <Form form={caseLinkForm} layout="vertical">
        <Form.Item
          label="关联普通案件"
          name="case_ids"
          rules={[{ required: true, type: "array", min: 1, message: "请选择至少一个案件" }]}
        >
          <Select
            mode="multiple"
            showSearch
            optionFilterProp="label"
            placeholder="选择案件"
            options={cases.map((item) => ({
              value: item.id,
              label: `${item.serial_no}｜${item.title}`,
            }))}
            notFoundContent="暂无可关联的普通案件"
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ===== 正式发文编辑 Modal =====
interface OutgoingModalProps {
  open: boolean;
  outgoingForm: FormInstance;
  editingOutgoing: any;
  cases: RecordRow[];
  contracts: RecordRow[];
  sealAssets: SealAsset[];
  attachments: Attachment[];
  onCreate: () => void;
  onUpdate: () => void;
  onCancel: () => void;
}

export function OutgoingModal({
  open,
  outgoingForm,
  editingOutgoing,
  cases,
  contracts,
  sealAssets,
  attachments,
  onCreate,
  onUpdate,
  onCancel,
}: OutgoingModalProps) {
  return (
    <Modal
      open={open}
      title={editingOutgoing ? "编辑正式发文" : "新建正式发文"}
      okText={editingOutgoing ? "保存修改" : "创建草稿"}
      cancelText="取消"
      onOk={editingOutgoing ? onUpdate : onCreate}
      onCancel={onCancel}
      destroyOnHidden
    >
      <Form form={outgoingForm} layout="vertical">
        <Form.Item label="文书名称" name="title" rules={[{ required: true, message: "请输入文书名称" }]}>
          <Input />
        </Form.Item>
        <Form.Item label="来源类型" name="source_type" rules={[{ required: true }]}>
          <Select
            disabled={!!editingOutgoing}
            options={[
              { value: "contract", label: "合同" },
              { value: "case", label: "案件" },
            ]}
            onChange={() =>
              outgoingForm.setFieldsValue({ source_record_id: undefined, source_file_ids: [] })
            }
          />
        </Form.Item>
        <Form.Item
          noStyle
          shouldUpdate={(previous, current) => previous.source_type !== current.source_type}
        >
          {() => (
            <Form.Item
              label="来源业务"
              name="source_record_id"
              rules={[{ required: true, message: "请选择来源合同或案件" }]}
            >
              <Select
                disabled={!!editingOutgoing}
                showSearch
                optionFilterProp="label"
                options={(outgoingForm.getFieldValue("source_type") === "case" ? cases : contracts).map(
                  (item) => ({
                    value: item.id,
                    label: `${item.serial_no}｜${item.title}`,
                  }),
                )}
                onChange={() => outgoingForm.setFieldsValue({ source_file_ids: [] })}
              />
            </Form.Item>
          )}
        </Form.Item>
        <Form.Item
          noStyle
          shouldUpdate={
            (previous, current) =>
              previous.source_record_id !== current.source_record_id ||
              previous.source_type !== current.source_type
          }
        >
          {() => {
            const sourceId = Number(outgoingForm.getFieldValue("source_record_id") || 0);
            const sourceFiles = attachments.filter((item) => item.record_id === sourceId);
            return (
              <Form.Item
                label="随文附件"
                name="source_file_ids"
                extra={
                  editingOutgoing
                    ? "编辑不改变既有来源和已复制附件；请在详情中维护正式发文附件。"
                    : outgoingForm.getFieldValue("source_type") === "contract"
                      ? "未选择时将按旧系统规则带入该合同全部附件。"
                      : "案件发文仅带入本处选中的附件。"
                }
              >
                <Select
                  mode="multiple"
                  allowClear
                  placeholder={sourceId ? "选择需要带入正式发文的附件" : "请先选择来源业务"}
                  disabled={!!editingOutgoing || !sourceId}
                  options={sourceFiles.map((item) => ({
                    value: item.id,
                    label: `${item.original_name}（${fileSize(item.size)}）`,
                  }))}
                  notFoundContent={sourceId ? "该来源暂无可带入附件" : undefined}
                />
              </Form.Item>
            );
          }}
        </Form.Item>
        <Form.Item
          label="印章类型"
          name="seal_asset_id"
          rules={[{ required: true, message: "请选择可用印章类型" }]}
        >
          <Select
            placeholder="请选择可用印章"
            options={sealAssets
              .filter((item) => item.status === "可用")
              .map((item) => ({ value: item.id, label: `${item.seal_type}｜${item.name}` }))}
            onChange={(value) => outgoingForm.setFieldsValue({ seal_asset_id: value })}
            onSelect={(value) => outgoingForm.setFieldsValue({ seal_asset_id: value })}
          />
        </Form.Item>
        <Form.Item label="盖章份数" name="print_quantity" rules={[{ required: true }]}>
          <InputNumber min={1} max={9999} precision={0} style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item name="is_electronic_seal" valuePropName="checked">
          <Checkbox>使用电子印章</Checkbox>
        </Form.Item>
        <Form.Item name="is_offline_print" valuePropName="checked">
          <Checkbox>需要打印盖章</Checkbox>
        </Form.Item>
        <Form.Item name="need_audit" valuePropName="checked">
          <Checkbox>提交后进入正式发文审批</Checkbox>
        </Form.Item>
        <Form.Item label="文书内容" name="content">
          <Input.TextArea rows={4} />
        </Form.Item>
        <Form.Item label="备注" name="remark">
          <Input.TextArea rows={2} />
        </Form.Item>
      </Form>
      <Alert
        type="info"
        showIcon
        message="先创建草稿；可上传/删除正式发文附件后再提交审批。来源合同或案件、附件和印章均由服务端校验。"
      />
    </Modal>
  );
}

// ===== 正式发文审核 Modal =====
interface OutgoingReviewModalProps {
  open: boolean;
  outgoingReviewForm: FormInstance;
  reviewData: { row: RecordRow; approved: boolean } | null;
  onOk: () => void;
  onCancel: () => void;
}

export function OutgoingReviewModal({
  open,
  outgoingReviewForm,
  reviewData,
  onOk,
  onCancel,
}: OutgoingReviewModalProps) {
  return (
    <Modal
      open={open}
      title={reviewData?.approved ? "通过正式发文" : "拒绝正式发文"}
      okText={reviewData?.approved ? "确认通过" : "确认拒绝"}
      okButtonProps={{ danger: !reviewData?.approved }}
      cancelText="取消"
      onOk={onOk}
      onCancel={onCancel}
      destroyOnHidden
    >
      {reviewData && (
        <>
          <Alert
            type={reviewData.approved ? "info" : "warning"}
            showIcon
            message={`${(reviewData.row as any).official_no || reviewData.row.serial_no}｜${reviewData.row.title}`}
            description={
              reviewData.approved
                ? "请填写本次审核意见；该意见将同步写入正式发文审批记录。"
                : "请填写具体驳回原因；申请人可在修改后再次提交。"
            }
            style={{ marginBottom: 16 }}
          />
          <Form form={outgoingReviewForm} layout="vertical">
            <Form.Item
              label="审核意见"
              name="comment"
              rules={
                reviewData.approved
                  ? [{ max: 1000 }]
                  : [
                      { required: true, whitespace: true, message: "请填写驳回原因" },
                      { max: 1000 },
                    ]
              }
            >
              <Input.TextArea
                rows={4}
                maxLength={1000}
                showCount
                placeholder={
                  reviewData.approved
                    ? "例如：材料齐全，同意正式发文"
                    : "请说明需补正或修改的具体事项"
                }
              />
            </Form.Item>
          </Form>
        </>
      )}
    </Modal>
  );
}

// ===== 文件预览 Modal =====
interface PreviewModalProps {
  open: boolean;
  previewName: string;
  previewKind: "image" | "pdf" | "text";
  previewUrl: string;
  previewText: string;
  onCancel: () => void;
}

export function PreviewModal({
  open,
  previewName,
  previewKind,
  previewUrl,
  previewText,
  onCancel,
}: PreviewModalProps) {
  return (
    <Modal
      open={open}
      title={`文件预览：${previewName}`}
      footer={null}
      width={760}
      onCancel={onCancel}
      destroyOnHidden
    >
      {previewKind === "image" ? (
        <img src={previewUrl} alt={previewName} style={{ maxWidth: "100%" }} />
      ) : previewKind === "pdf" ? (
        <iframe src={previewUrl} title={previewName} style={{ width: "100%", height: 520 }} />
      ) : (
        <pre style={{ whiteSpace: "pre-wrap", maxHeight: 520, overflow: "auto" }}>
          {previewText}
        </pre>
      )}
    </Modal>
  );
}
