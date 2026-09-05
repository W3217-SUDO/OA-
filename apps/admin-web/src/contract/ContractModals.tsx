import { CheckOutlined,CloseOutlined,PlusOutlined } from "@ant-design/icons";
import type { FormInstance } from "antd";
import {
Alert,
Button,
Checkbox,
DatePicker,
Empty,
Form,
Input,
InputNumber,
Modal,
Select,
Space,
Steps,
Table,
Timeline
} from "antd";
import dayjs from "dayjs";
import type { Key } from "react";
import { AttachmentPreviewContent } from "../components/common/AttachmentContent";
import {
CONTRACT_ATTACHMENT_ACCEPT,
filterContractCaseOptions
} from "../contractWorkflowPolicy.mjs";
import { INVESTIGATION_REGION_GROUPS } from "../investigationRegionOptions.mjs";
import {
CONTRACT_FEE_MODE_OPTIONS,
CONTRACT_TYPE_OPTIONS
} from "./constants";
import type {
AttachmentPreview,
Change,
Contract,
ContractObjectRow,
ContractPaymentCandidate,
PaymentTypeOption,
Step
} from "./types";

// ==================== 合同标的编辑 Modal ====================
interface ContractObjectEditModalProps {
  open: boolean;
  editing: { id?: number } | null;
  objectForm: FormInstance;
  objectCases: Array<{ id: number; serial_no: string; title: string; customer: string }>;
  viewingCustomer: string;
  onCancel: () => void;
  onOk: () => void;
}

export function ContractObjectEditModal({
  open,
  editing,
  objectForm,
  objectCases,
  viewingCustomer,
  onCancel,
  onOk,
}: ContractObjectEditModalProps) {
  return (
    <Modal
      open={open}
      title={editing?.id ? "修改合同标的" : "新增合同标的"}
      okText="保存"
      cancelText="取消"
      onCancel={onCancel}
      onOk={onOk}
    >
      <Form form={objectForm} layout="vertical">
        <Form.Item name="case_record_id" label="关联案件" rules={[{ required: true, message: "请选择合同客户下的案件" }]}>
          <Select
            showSearch
            optionFilterProp="label"
            options={filterContractCaseOptions(objectCases, viewingCustomer).map((item) => ({
              value: item.id,
              label: `${item.serial_no}｜${item.title}`,
            }))}
          />
        </Form.Item>
        <Form.Item name="fee_type" label="费用类型" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item name="amount" label="费用金额" rules={[{ required: true }]}>
          <InputNumber min={0} precision={2} style={{ width: "100%" }} />
        </Form.Item>
        <Form.Item name="remark" label="备注">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ==================== 合同标的日志 Modal ====================
interface ContractObjectLogModalProps {
  open: boolean;
  logTarget: ContractObjectRow | null;
  personName: (value: unknown) => string;
  onCancel: () => void;
}

export function ContractObjectLogModal({ open, logTarget, personName, onCancel }: ContractObjectLogModalProps) {
  return (
    <Modal
      open={open}
      title={logTarget ? `合同标的日志：${logTarget.case_no}｜${logTarget.fee_type}` : "合同标的日志"}
      footer={null}
      onCancel={onCancel}
    >
      {logTarget?.logs?.length ? (
        <Timeline
          items={logTarget.logs.map((log) => ({
            children: (
              <div className="contract-history-item">
                <b>{log.action}</b>
                <small>
                  {personName(log.operator)} · {dayjs(log.created_at).format("YYYY-MM-DD HH:mm")}
                </small>
                <small>变更前：{Object.keys(log.before || {}).length ? JSON.stringify(log.before) : "-"}</small>
                <small>变更后：{Object.keys(log.after || {}).length ? JSON.stringify(log.after) : "-"}</small>
              </div>
            ),
          }))}
        />
      ) : (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无合同标的日志" />
      )}
    </Modal>
  );
}

// ==================== 附件在线预览 Modal ====================
interface AttachmentPreviewModalProps {
  open: boolean;
  preview: AttachmentPreview | null;
  onClose: () => void;
}

export function AttachmentPreviewModal({ open, preview, onClose }: AttachmentPreviewModalProps) {
  return (
    <Modal
      open={open}
      title={`在线查看：${preview?.name || ""}`}
      footer={<Button onClick={onClose}>关闭</Button>}
      onCancel={onClose}
      width={preview?.kind === "pdf" ? 1000 : 760}
      destroyOnHidden
    >
      <AttachmentPreviewContent preview={preview} />

    </Modal>
  );
}

// ==================== 新增合同事项 Modal ====================
interface ContractEventModalProps {
  open: boolean;
  target: Contract | null;
  eventForm: FormInstance;
  saving: boolean;
  onCancel: () => void;
  onOk: () => void;
}

export function ContractEventModal({ open, target, eventForm, saving, onCancel, onOk }: ContractEventModalProps) {
  return (
    <Modal
      open={open}
      title={`新增合同事项：${target?.serial_no || ""}`}
      okText="保存"
      cancelText="取消"
      confirmLoading={saving}
      cancelButtonProps={{ disabled: saving }}
      closable={!saving}
      onOk={onOk}
      onCancel={onCancel}
      destroyOnHidden
    >
      <Form form={eventForm} layout="vertical">
        <Form.Item
          label="事项内容"
          name="content"
          rules={[{ required: true, whitespace: true, max: 1000, message: "请填写不超过 1000 字的事项内容" }]}
        >
          <Input.TextArea rows={5} maxLength={1000} showCount placeholder="记录合同履行、沟通或需要跟进的事项" />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ==================== 配置审批流程 Modal ====================
interface ContractSubmitModalProps {
  open: boolean;
  submitting: Contract | null;
  submitForm: FormInstance;
  approvalOptions: { value: string; label: string }[];
  contractApproverLabel: React.ReactNode;
  saving: boolean;
  onCancel: () => void;
  onOk: () => void;
}

export function ContractSubmitModal({
  open,
  submitting,
  submitForm,
  approvalOptions,
  contractApproverLabel,
  saving,
  onCancel,
  onOk,
}: ContractSubmitModalProps) {
  return (
    <Modal
      open={open}
      title={`配置审批流程：${submitting?.title || ""}`}
      okText="提交审批"
      confirmLoading={saving}
      closable={!saving}
      onOk={onOk}
      cancelButtonProps={{ disabled: saving }}
      onCancel={onCancel}
    >
      <Form form={submitForm} layout="vertical">
        <Form.Item label={contractApproverLabel} name="approvers" rules={[{ required: true }]}>
          <Select
            showSearch
            optionFilterProp="label"
            options={approvalOptions}
            placeholder="请选择后台已配置的合同审批人"
            notFoundContent="没有可用审批人，请由管理员设置在职员工的合同审批资格"
          />
        </Form.Item>
        <Form.Item label="提交说明" name="comment">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ==================== 设置合同审批人 Modal ====================
interface ApproverSettingsModalProps {
  open: boolean;
  approverSettings: Array<{ username: string; display_name: string; display_name_valid?: boolean; department: string; position: string; selected: boolean }>;
  selectedApproverUsernames: string[];
  approverSettingsTargetUsername: string;
  loading: boolean;
  saving: boolean;
  personName: (value: unknown) => string;
  onNavigate: (key: string) => void;
  onCancel: () => void;
  onOk: () => void;
  onSelectionChange: (keys: Key[]) => void;
}

export function ApproverSettingsModal({
  open,
  approverSettings,
  selectedApproverUsernames,
  approverSettingsTargetUsername,
  loading,
  saving,
  personName,
  onNavigate,
  onCancel,
  onOk,
  onSelectionChange,
}: ApproverSettingsModalProps) {
  return (
    <Modal
      width={760}
      open={open}
      title="设置合同审批人"
      okText="保存设置"
      cancelText="取消"
      confirmLoading={saving}
      onOk={onOk}
      onCancel={onCancel}
    >
      <Alert
        type="info"
        showIcon
        title="仅管理员可以配置"
        description={
          <Space direction="vertical" size={4}>
            这些人员来自人事中心的在职员工。取消勾选只移除合同审批资格，不会删除员工档案；姓名待维护的员工不会进入合同提交下拉。
            <Button
              type="link"
              style={{ padding: 0, height: "auto", alignSelf: "flex-start" }}
              onClick={() => {
                onCancel();
                onNavigate("hr-all");
              }}
            >
              前往人事中心维护姓名
            </Button>
          </Space>
        }
        style={{ marginBottom: 16 }}
      />
      <Table
        rowKey="username"
        size="small"
        loading={loading}
        pagination={false}
        dataSource={approverSettings}
        rowClassName={(row) => (row.username === approverSettingsTargetUsername ? "contract-approver-target-row" : "")}
        rowSelection={{
          selectedRowKeys: selectedApproverUsernames,
          onChange: (keys) => onSelectionChange(keys),
          getCheckboxProps: (row: { username: string; display_name_valid?: boolean }) => ({
            disabled: row.display_name_valid === false && !selectedApproverUsernames.includes(row.username),
          }),
        }}
        columns={[
          { title: "姓名", dataIndex: "display_name", render: (value: string) => personName(value) },
          { title: "登录账号", dataIndex: "username" },
          { title: "部门", dataIndex: "department", render: (value: string) => value || "—" },
          { title: "职务", dataIndex: "position", render: (value: string) => value || "—" },
        ]}
        locale={{ emptyText: "暂无可配置的启用、在职员工" }}
      />
    </Modal>
  );
}

// ==================== 合同审批 Modal ====================
interface ContractReviewModalProps {
  open: boolean;
  reviewing: Contract | null;
  reviewForm: FormInstance;
  stepItems: Array<{ title: string; description?: React.ReactNode; status: "finish" | "process" | "error" | "wait" }>;
  currentApproval: Step | undefined;
  canActOnCurrentApproval: boolean;
  personName: (value: unknown) => string;
  onCancel: () => void;
  onApprove: (approved: boolean) => void;
}

export function ContractReviewModal({
  open,
  reviewing,
  reviewForm,
  stepItems,
  currentApproval,
  canActOnCurrentApproval,
  personName,
  onCancel,
  onApprove,
}: ContractReviewModalProps) {
  return (
    <Modal
      width={680}
      open={open}
      title={`合同审批：${reviewing?.title || ""}`}
      footer={
        reviewing?.status === "审批中" && canActOnCurrentApproval ? (
          <Space>
            <Button danger icon={<CloseOutlined />} onClick={() => onApprove(false)}>
              拒绝
            </Button>
            <Button type="primary" icon={<CheckOutlined />} onClick={() => onApprove(true)}>
              通过当前节点
            </Button>
          </Space>
        ) : (
          <Button onClick={onCancel}>关闭</Button>
        )
      }
      onCancel={onCancel}
    >
      <Steps direction="vertical" items={stepItems} />
      {reviewing?.status === "审批中" && canActOnCurrentApproval && (
        <Form form={reviewForm} layout="vertical">
          <Form.Item label="审批意见" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      )}
      {reviewing?.status === "审批中" && !canActOnCurrentApproval && currentApproval && (
        <Alert
          type="info"
          showIcon
          title={`当前节点应由 ${personName(currentApproval.approver_display_name || currentApproval.approver)} 审批`}
          description="当前账号没有该审批节点的办理权限。"
        />
      )}
    </Modal>
  );
}

// ==================== 合同变更 Modal ====================
interface ContractChangeModalProps {
  open: boolean;
  changing: Contract | null;
  changeForm: FormInstance;
  changeFile: File | null;
  CONTRACT_CREATE_STEP_TITLES: string[];
  onCancel: () => void;
  onOk: () => void;
  onChangeFile: (file: File | null) => void;
}

export function ContractChangeModal({
  open,
  changing,
  changeForm,
  changeFile,
  CONTRACT_CREATE_STEP_TITLES,
  onCancel,
  onOk,
  onChangeFile,
}: ContractChangeModalProps) {
  return (
    <Modal
      width={820}
      open={open}
      title={`合同变更：${changing?.serial_no || ""}`}
      okText="下一步"
      cancelText="取消"
      onOk={onOk}
      onCancel={onCancel}
    >
      <Steps className="contract-create-steps" current={0} items={CONTRACT_CREATE_STEP_TITLES.map((title) => ({ title }))} />
      <Form form={changeForm} layout="vertical">
        <Form.Item label="客户" name="customer">
          <Input disabled />
        </Form.Item>
        <Form.Item label="变更类型" name="change_type" rules={[{ required: true }]}>
          <Select
            options={["合同补充/修订", "金额调整", "期限变更", "主体信息变更", "其他"].map((v) => ({
              value: v,
              label: v,
            }))}
          />
        </Form.Item>
        <Form.Item label="变更原因" name="reason" rules={[{ required: true, min: 2 }]}>
          <Input.TextArea rows={3} />
        </Form.Item>
        <div className="form-grid">
          <Form.Item label="合同主体" name="contract_body">
            <Select options={["律所", "平台"].map((value) => ({ value, label: value }))} />
          </Form.Item>
          <Form.Item label="合同类别" name="contract_type">
            <Select options={CONTRACT_TYPE_OPTIONS} />
          </Form.Item>
          <Form.Item label="收费模式" name="fee_type">
            <Select options={CONTRACT_FEE_MODE_OPTIONS} />
          </Form.Item>
          <Form.Item className="span-2" label="合同名称" name="title">
            <Input />
          </Form.Item>
          <Form.Item label="合同金额" name="amount">
            <InputNumber min={0} precision={2} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="外部合同号（可多个）" name="external_contract_numbers">
            <Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入后回车，可关联多个" />
          </Form.Item>
          <Form.Item className="span-2" label="合同截止日期" name="end_date">
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item className="span-2" label="备注" name="description">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item className="span-2" label="合同附件" extra="可选；未选择时保留原有附件">
            <input
              type="file"
              accept={CONTRACT_ATTACHMENT_ACCEPT}
              onChange={(event) => onChangeFile(event.target.files?.[0] || null)}
            />
            {changeFile && <span className="contract-upload-name">{changeFile.name}</span>}
          </Form.Item>
        </div>
      </Form>
    </Modal>
  );
}

// ==================== 合同变更记录 Modal ====================
interface ContractChangeHistoryModalProps {
  open: boolean;
  changeHistory: Contract | null;
  changes: Change[];
  personName: (value: unknown) => string;
  onCancel: () => void;
}

export function ContractChangeHistoryModal({
  open,
  changeHistory,
  changes,
  personName,
  onCancel,
}: ContractChangeHistoryModalProps) {
  return (
    <Modal
      width={820}
      open={open}
      title={`合同变更记录：${changeHistory?.serial_no || ""}`}
      footer={<Button onClick={onCancel}>关闭</Button>}
      onCancel={onCancel}
    >
      <Table
        rowKey="id"
        size="small"
        pagination={false}
        dataSource={changes}
        columns={[
          {
            title: "时间",
            dataIndex: "created_at",
            width: 170,
            render: (v: string) => new Date(v).toLocaleString("zh-CN"),
          },
          { title: "类型", dataIndex: "change_type", width: 130 },
          {
            title: "变更内容",
            key: "detail",
            render: (_: unknown, r: Change) => (
              <>
                {r.changes.map((x) => (
                  <div key={x.field}>
                    {x.label}：{String(x.before ?? "—")} → <b>{String(x.after ?? "—")}</b>
                  </div>
                ))}
              </>
            ),
          },
          { title: "原因", dataIndex: "reason", width: 170 },
          { title: "操作人", dataIndex: "operator", width: 90, render: (value: string) => personName(value) },
        ]}
      />
    </Modal>
  );
}

// ==================== 合同付款 Modal ====================
interface ContractPaymentModalProps {
  open: boolean;
  paymentTarget: Contract | null;
  paymentForm: FormInstance;
  paymentTypes: PaymentTypeOption[];
  paymentTypeSearch: string;
  selectedPaymentObjectKeys: Key[];
  paymentAmounts: Record<number, number>;
  paymentCandidates: ContractPaymentCandidate[];
  selectedContractPaymentType: PaymentTypeOption | undefined;
  paymentSaving: boolean;
  onCancel: () => void;
  onOk: () => void;
  onPaymentTypeSearch: (value: string) => void;
  onOpenPaymentTypeCreator: () => void;
  onPaymentObjectSelectionChange: (keys: Key[]) => void;
  onPaymentAmountChange: (objectId: number, value: number) => void;
}

export function ContractPaymentModal({
  open,
  paymentTarget,
  paymentForm,
  paymentTypes,
  paymentTypeSearch,
  selectedPaymentObjectKeys,
  paymentAmounts,
  paymentCandidates,
  selectedContractPaymentType,
  paymentSaving,
  onCancel,
  onOk,
  onPaymentTypeSearch,
  onOpenPaymentTypeCreator,
  onPaymentObjectSelectionChange,
  onPaymentAmountChange,
}: ContractPaymentModalProps) {
  return (
    <Modal
      open={open}
      title={`合同付款：${paymentTarget?.serial_no || ""}`}
      width={980}
      okText="提交合同付款申请"
      cancelText="取消"
      confirmLoading={paymentSaving}
      closable={!paymentSaving}
      onOk={onOk}
      cancelButtonProps={{ disabled: paymentSaving }}
      onCancel={onCancel}
    >
      <Form form={paymentForm} layout="vertical">
        <div className="form-grid">
          <Form.Item label="收款单位" name="payment_type_id" rules={[{ required: true, message: "请选择系统付款单位" }]}>
            <Select
              showSearch
              optionFilterProp="label"
              placeholder="输入关键字选择收款单位"
              options={paymentTypes}
              onSearch={onPaymentTypeSearch}
              notFoundContent={
                <Button type="link" icon={<PlusOutlined />} onClick={onOpenPaymentTypeCreator}>
                  新增“{paymentTypeSearch || "付款单位"}”
                </Button>
              }
            />
          </Form.Item>
          <Form.Item label="新增单位">
            <Button icon={<PlusOutlined />} onClick={onOpenPaymentTypeCreator}>
              新增付款单位
            </Button>
          </Form.Item>
          <Form.Item label="申请日期" name="application_date" rules={[{ required: true }]}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
        </div>
        {selectedContractPaymentType && (
          <Alert
            type="info"
            showIcon
            message={selectedContractPaymentType.payee}
            description={`性质：${selectedContractPaymentType.nature || "—"}　开户行：${selectedContractPaymentType.account_bank || "—"}　账号信息：${selectedContractPaymentType.account || "—"}`}
            style={{ marginBottom: 12 }}
          />
        )}
        <Form.Item label="申请说明" name="remark">
          <Input.TextArea rows={2} />
        </Form.Item>
      </Form>
      <Alert
        showIcon
        type="info"
        message="按合同标的逐项申请"
        description="勾选需要付款的合同标的并填写本次支付金额；系统将保留已提交、待付款和已付款金额，阻止重复超额申请。"
        style={{ marginBottom: 12 }}
      />
      <Table<ContractPaymentCandidate>
        rowKey="contract_object_id"
        size="small"
        pagination={false}
        locale={{ emptyText: "当前合同没有可付款的合同标的" }}
        dataSource={paymentCandidates}
        rowSelection={{
          selectedRowKeys: selectedPaymentObjectKeys,
          onChange: (keys) => onPaymentObjectSelectionChange(keys),
        }}
        columns={[
          { title: "案号", dataIndex: "case_no", width: 140 },
          { title: "案件名称", dataIndex: "case_title", ellipsis: true },
          { title: "费用类型", dataIndex: "fee_type", width: 120 },
          { title: "合同金额", dataIndex: "contract_amount", width: 105, render: (value) => Number(value).toFixed(2) },
          { title: "已占用", dataIndex: "reserved_amount", width: 100, render: (value) => Number(value).toFixed(2) },
          { title: "待付余额", dataIndex: "remaining_amount", width: 105, render: (value) => Number(value).toFixed(2) },
          {
            title: "本次支付",
            width: 130,
            render: (_, row) => (
              <InputNumber
                disabled={!selectedPaymentObjectKeys.includes(row.contract_object_id)}
                min={0.01}
                max={row.remaining_amount}
                precision={2}
                value={paymentAmounts[row.contract_object_id]}
                style={{ width: "100%" }}
                onChange={(value) => onPaymentAmountChange(row.contract_object_id, Number(value || 0))}
              />
            ),
          },
        ]}
      />
    </Modal>
  );
}

// ==================== 新增付款单位 Modal ====================
interface PaymentTypeCreateModalProps {
  open: boolean;
  paymentTypeCreateForm: FormInstance;
  creating: boolean;
  onCancel: () => void;
  onOk: () => void;
}

export function PaymentTypeCreateModal({
  open,
  paymentTypeCreateForm,
  creating,
  onCancel,
  onOk,
}: PaymentTypeCreateModalProps) {
  return (
    <Modal
      open={open}
      title="新增付款单位"
      okText="确定"
      cancelText="取消"
      confirmLoading={creating}
      onOk={onOk}
      onCancel={onCancel}
      forceRender
    >
      <Form form={paymentTypeCreateForm} layout="vertical">
        <Form.Item label="性质" name="nature" rules={[{ required: true, message: "请选择性质" }]}>
          <Select options={["官费", "其他费用", "代理费", "对公", "个人"].map((value) => ({ value, label: value }))} />
        </Form.Item>
        <Form.Item label="收款单位" name="payee" rules={[{ required: true, message: "请输入收款单位" }]}>
          <Input />
        </Form.Item>
        <Form.Item label="开户行" name="account_bank" rules={[{ required: true, message: "请输入开户行" }]}>
          <Input />
        </Form.Item>
        <Form.Item label="账号信息" name="account" rules={[{ required: true, message: "请输入账号信息" }]}>
          <Input.TextArea rows={4} maxLength={1000} showCount />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ==================== 合同开票 Modal ====================
interface ContractInvoiceModalProps {
  open: boolean;
  invoiceTarget: Contract | null;
  invoiceForm: FormInstance;
  invoiceSaving: boolean;
  onCancel: () => void;
  onOk: () => void;
}

export function ContractInvoiceModal({
  open,
  invoiceTarget,
  invoiceForm,
  invoiceSaving,
  onCancel,
  onOk,
}: ContractInvoiceModalProps) {
  return (
    <Modal
      open={open}
      title={`合同开票：${invoiceTarget?.serial_no || ""}`}
      okText="创建开票申请"
      cancelText="取消"
      confirmLoading={invoiceSaving}
      closable={!invoiceSaving}
      onOk={onOk}
      cancelButtonProps={{ disabled: invoiceSaving }}
      onCancel={onCancel}
    >
      <Form form={invoiceForm} layout="vertical">
        <div className="form-grid">
          <Form.Item label="开票金额" name="amount" rules={[{ required: true }]}>
            <InputNumber min={0.01} precision={2} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="发票抬头" name="invoice_title" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="纳税人识别号" name="taxpayer_id" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="发票类型" name="invoice_type" rules={[{ required: true }]}>
            <Select
              options={["增值税普通发票", "增值税专用发票", "电子普通发票", "电子专用发票"].map((value) => ({
                value,
                label: value,
              }))}
            />
          </Form.Item>
          <Form.Item label="开票内容" name="invoice_content" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="交付方式" name="delivery_method">
            <Select
              options={["电子发票", "邮寄纸质发票", "现场领取"].map((value) => ({ value, label: value }))}
            />
          </Form.Item>
          <Form.Item label="接收邮箱" name="email">
            <Input />
          </Form.Item>
          <Form.Item label="联系电话" name="recipient_phone">
            <Input />
          </Form.Item>
        </div>
        <Form.Item label="邮寄地址" name="delivery_address">
          <Input />
        </Form.Item>
        <Form.Item label="备注" name="remark">
          <Input.TextArea rows={2} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ==================== 选择城市（调查区域）Modal ====================
interface InvestigationRegionPickerModalProps {
  open: boolean;
  selectedRegions: string[];
  expandedProvinces: string[];
  investigationForm: FormInstance;
  onCancel: () => void;
  onOk: () => void;
  onSelectAll: () => void;
  onClearAll: () => void;
  onProvinceToggle: (province: string, checked: boolean) => void;
  onProvinceExpand: (province: string) => void;
  onCitiesChange: (province: string, values: string[]) => void;
}

export function InvestigationRegionPickerModal({
  open,
  selectedRegions,
  expandedProvinces,
  investigationForm,
  onCancel,
  onOk,
  onSelectAll,
  onClearAll,
  onProvinceToggle,
  onProvinceExpand,
  onCitiesChange,
}: InvestigationRegionPickerModalProps) {
  return (
    <Modal
      open={open}
      title="选择城市"
      footer={
        <Space>
          <Button onClick={onCancel}>取消</Button>
          <Button type="primary" onClick={onOk}>
            确定
          </Button>
        </Space>
      }
      onCancel={onCancel}
    >
      <Space style={{ marginBottom: 12 }}>
        <Button type="link" onClick={onSelectAll}>
          全选
        </Button>
        <Button type="link" onClick={onClearAll}>
          清空
        </Button>
      </Space>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 10 }}>
        {INVESTIGATION_REGION_GROUPS.map(({ province, cities }) => {
          const expanded = expandedProvinces.includes(province);
          const isSelected = selectedRegions.includes(province);
          return (
            <div key={province} style={{ gridColumn: expanded && cities.length ? "span 4" : undefined }}>
              <Space size={4}>
                <Checkbox
                  aria-label={`选择${province}`}
                  checked={isSelected}
                  onChange={(event) => onProvinceToggle(province, event.target.checked)}
                />
                {cities.length ? (
                  <Button type="link" size="small" onClick={() => onProvinceExpand(province)}>
                    {province}
                  </Button>
                ) : (
                  <span>{province}</span>
                )}
              </Space>
              {expanded && cities.length > 0 && (
                <div
                  style={{
                    margin: "8px 0 4px 24px",
                    padding: 8,
                    background: "#fafafa",
                    border: "1px solid #f0f0f0",
                  }}
                >
                  <Checkbox.Group
                    value={selectedRegions.filter((value) => cities.includes(value))}
                    onChange={(values) => onCitiesChange(province, values as string[])}
                    options={cities.map((city) => ({ label: city, value: city }))}
                    style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 8 }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Modal>
  );
}
