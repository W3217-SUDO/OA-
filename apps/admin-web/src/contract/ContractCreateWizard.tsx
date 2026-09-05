import { CheckOutlined,CloseOutlined } from "@ant-design/icons";
import type { FormInstance } from "antd";
import {
Alert,
Button,
Checkbox,
DatePicker,
Descriptions,
Divider,
Empty,
Form,
Input,
InputNumber,
Radio,
Select,
Space,
Steps,
Tag,
Timeline,
} from "antd";
import { AttachmentFileInput } from "../components/common/AttachmentContent";
import { displayContractStatus } from "../contractStatusPresentation.mjs";
import { CONTRACT_ATTACHMENT_ACCEPT } from "../contractWorkflowPolicy.mjs";
import {
CONTRACT_CREATE_STEP_TITLES,
CONTRACT_FEE_MODE_OPTIONS,
CONTRACT_TYPE_OPTIONS,
colors,
} from "./constants";
import { ContractPageWizardContent } from "./ContractPageWizardContent";
import type { Attachment,Contract,SealAsset,Step } from "./types";

// ==================== 向导步骤内容（页面版和Modal版共用） ====================
export interface ContractWizardContentProps {
  onDownloadAttachment: (attachment: Attachment) => void;
  onClearLinkedCustomerContext: () => void;
  wizardStep: number;
  editing: Contract | null;
  wizardDraft: Contract | null;
  form: FormInstance;
  submitForm: FormInstance;
  reviewForm: FormInstance;
  sealForm: FormInstance;
  steps: Step[];
  attachments: Attachment[];
  historyItems: Array<{ children?: React.ReactNode }>;
  stepItems: Array<{ title: string; description?: React.ReactNode; status: "finish" | "process" | "error" | "wait" }>;
  customerOptions: Array<{ value: number; label: string }>;
  approvalOptions: Array<{ value: string; label: string }>;
  sealAssets: SealAsset[];
  currentApproval: Step | undefined;
  canActOnCurrentApproval: boolean;
  contractApproverLabel: React.ReactNode;
  contractCapabilities: (contract?: Contract | null, options?: Record<string, unknown>) => { canEdit?: boolean; canSubmit?: boolean };
  savingContract: boolean;
  submittingWizard: boolean;
  contractFile: File | null;
  personName: (value: unknown) => string;
  mode: "page" | "modal";
  onSave: () => void;
  onSubmitWizard: () => void;
  onRevokeDraft: () => void;
  onApproveWizard: (approved: boolean) => void;
  onRefreshWizard: () => void;
  onCreateSealApplication: (submit: boolean) => void;
  onContractFileChange: (file: File | null) => void;
  onUploadDraftAttachment: () => void;
  onStartCreate: () => void;
  onNavigate?: (key: string) => void;
  onOpenContractCustomerCreation: () => void;
}

export function ContractWizardContent({
  onDownloadAttachment,
  onClearLinkedCustomerContext,
  wizardStep,
  editing,
  wizardDraft,
  form,
  submitForm,
  reviewForm,
  sealForm,
  attachments,
  historyItems,
  stepItems,
  customerOptions,
  approvalOptions,
  sealAssets,
  currentApproval,
  canActOnCurrentApproval,
  contractApproverLabel,
  contractCapabilities,
  savingContract,
  submittingWizard,
  contractFile,
  personName,
  mode,
  onSave,
  onSubmitWizard,
  onRevokeDraft,
  onApproveWizard,
  onRefreshWizard,
  onCreateSealApplication,
  onContractFileChange,
  onUploadDraftAttachment,
  onStartCreate,
  onNavigate,
  onOpenContractCustomerCreation,
}: ContractWizardContentProps) {
  const showSteps = !editing && wizardStep < CONTRACT_CREATE_STEP_TITLES.length;
  const stepClass = mode === "page" ? "contract-page-steps" : "contract-create-steps";

  if (mode === "page") return <ContractPageWizardContent {...{ wizardStep, wizardDraft, form, submitForm, reviewForm, sealForm, attachments, historyItems, stepItems, customerOptions, approvalOptions, sealAssets, currentApproval, canActOnCurrentApproval, contractApproverLabel, personName, onContractFileChange, onApproveWizard, onOpenContractCustomerCreation, onClearLinkedCustomerContext, onDownloadAttachment }} />;

  return (
    <>
      {showSteps && (
        <Steps
          className={stepClass}
          current={Math.min(wizardStep, CONTRACT_CREATE_STEP_TITLES.length - 1)}
          items={CONTRACT_CREATE_STEP_TITLES.map((title) => ({ title }))}
        />
      )}
      {(editing || wizardStep === 0) && (
        <Form form={form} layout="vertical">
          <div className="form-grid">
            <Form.Item hidden={!editing} label="合同编号" name="serial_no" rules={[{ required: true }]}>
              <Input disabled={Boolean(editing)} />
            </Form.Item>
            <Form.Item label="客户" name="customer_id" rules={[{ required: true, message: "请选择客户" }]}>
              <Select
                showSearch
                optionFilterProp="label"
                placeholder="输入客户名称关键字后选择"
                options={customerOptions}
                notFoundContent="没有匹配客户，请先在客户管理中新建客户"
              />
            </Form.Item>
            <Form.Item label="合同主体" name="contract_body" rules={[{ required: true }]}>
              <Select options={["律所", "平台"].map((v) => ({ value: v, label: v }))} />
            </Form.Item>
            <Form.Item label="合同类别" name="type" rules={[{ required: true }]}>
              <Select
                allowClear
                showSearch
                optionFilterProp="label"
                placeholder="请选择合同类别"
                options={CONTRACT_TYPE_OPTIONS}
              />
            </Form.Item>
            <Form.Item label="收费模式" name="fee_type" rules={[{ required: true }]}>
              <Select options={CONTRACT_FEE_MODE_OPTIONS} />
            </Form.Item>
            <Form.Item label="外部合同号（可多个）" name="external_contract_numbers">
              <Select mode="tags" tokenSeparators={[",", "，"]} placeholder="输入客户方合同编号后回车" />
            </Form.Item>
            <Form.Item className="span-2" label="合同名称" name="title" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item label="合同金额" name="amount" hidden={!editing}>
              <InputNumber min={0} precision={2} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item label="签订日期" name="signed_at" hidden={!editing}>
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item label="负责人" name="owner" hidden={!editing}>
              <Input />
            </Form.Item>
            <Form.Item label="所属部门" name="department" hidden={!editing}>
              <Input />
            </Form.Item>
            <Form.Item className="span-2" label="备注" name="description" rules={[{ required: !editing }]}>
              <Input.TextArea rows={2} placeholder="备注" />
            </Form.Item>
            <Form.Item className="span-2" label="合同附件">
              <AttachmentFileInput onFileChange={onContractFileChange} />
            </Form.Item>
          </div>
        </Form>
      )}
      {!editing && wizardStep === 1 && (
        <div className="contract-wizard-panel">
          <Descriptions
            bordered
            size="small"
            column={2}
            items={
              wizardDraft
                ? [
                    { key: "no", label: "合同编号", children: wizardDraft.serial_no },
                    {
                      key: "status",
                      label: "当前状态",
                      children: <Tag>{displayContractStatus(wizardDraft.status)}</Tag>,
                    },
                    { key: "name", label: "合同名称", children: wizardDraft.title, span: 2 },
                    { key: "customer", label: "客户", children: wizardDraft.customer },
                    { key: "type", label: "合同类别", children: wizardDraft.data.type },
                  ]
                : []
            }
          />
          <Form.Item label="合同附件" extra="可在草稿阶段补传；未上传时提交审批会被阻断">
            <Space wrap>
              <AttachmentFileInput
                accept={CONTRACT_ATTACHMENT_ACCEPT}
                onFileChange={onContractFileChange} />
              <Button onClick={onUploadDraftAttachment} disabled={!contractFile}>
                上传附件
              </Button>
            </Space>
          </Form.Item>
          <Form form={submitForm} layout="vertical" className="contract-submit-form">
            <Form.Item label="是否同步用印" name="sync_seal" initialValue={false}>
              <Radio.Group
                disabled={!(["草稿", "已拒绝"].includes(wizardDraft?.status || ""))}
                options={[
                  { value: true, label: "是" },
                  { value: false, label: "否" },
                ]}
              />
            </Form.Item>
            <Form.Item label={contractApproverLabel} name="approvers" rules={[{ required: true, message: "请选择一名合同审批人" }]}>
              <Select
                disabled={!(["草稿", "已拒绝"].includes(wizardDraft?.status || ""))}
                showSearch
                optionFilterProp="label"
                options={approvalOptions}
                placeholder="请选择后台已配置的合同审批人"
                notFoundContent="没有可用审批人，请由管理员设置在职员工的合同审批资格"
              />
            </Form.Item>
            <Form.Item label="提交说明" name="comment">
              <Input.TextArea disabled={!(["草稿", "已拒绝"].includes(wizardDraft?.status || ""))} rows={3} />
            </Form.Item>
          </Form>
          <p className="contract-draft-tip">
            合同草稿已经持久化保存。关闭向导后，可在“我的合同”中继续编辑或提交。
          </p>
        </div>
      )}
      {!editing && wizardStep === 2 && (
        <div className="contract-wizard-panel">
          <Descriptions
            bordered
            size="small"
            column={2}
            items={
              wizardDraft
                ? [
                    { key: "no", label: "合同编号", children: wizardDraft.serial_no },
                    {
                      key: "status",
                      label: "合同状态",
                      children: (
                        <Tag color={colors[wizardDraft.status]}>{displayContractStatus(wizardDraft.status)}</Tag>
                      ),
                    },
                    { key: "name", label: "合同名称", children: wizardDraft.title, span: 2 },
                  ]
                : []
            }
          />
          <Steps direction="vertical" size="small" className="contract-approval-flow" items={stepItems} />
          {wizardDraft?.status === "审批中" && currentApproval && (
            canActOnCurrentApproval ? (
              <Form form={reviewForm} layout="vertical" className="contract-review-form">
                <div className="contract-current-approval">
                  当前节点：第 {currentApproval.step_order} 级 ·{" "}
                  {personName(currentApproval.approver_display_name || currentApproval.approver)}
                </div>
                <Form.Item label="审批意见" name="comment">
                  <Input.TextArea rows={3} placeholder="填写通过意见；拒绝时必须填写原因" />
                </Form.Item>
                <Space>
                  <Button danger icon={<CloseOutlined />} onClick={() => onApproveWizard(false)}>
                    拒绝
                  </Button>
                  <Button type="primary" icon={<CheckOutlined />} onClick={() => onApproveWizard(true)}>
                    通过当前节点
                  </Button>
                </Space>
              </Form>
            ) : (
              <Alert
                type="info"
                showIcon
                title={`合同已进入 ${personName(currentApproval.approver_display_name || currentApproval.approver)} 的待审批列表`}
                description="请等待指定审批人处理。"
              />
            )
          )}
          <Divider titlePlacement="start">合同附件</Divider>
          <div className="contract-attachment-list">
            {attachments.length ? (
              attachments.map((item) => (
                <Button key={item.id} type="link" onClick={() => onDownloadAttachment(item)}>
                  {item.original_name}
                </Button>
              ))
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无合同附件" />
            )}
          </div>
          <Divider titlePlacement="start">状态时间线</Divider>
          {historyItems.length ? <Timeline items={historyItems} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无流程记录" />}
        </div>
      )}
      {!editing && wizardStep === 3 && (
        <div className="contract-wizard-panel contract-seal-step">
          {wizardDraft?.status === "审批中" ? (
            <Alert
              type="info"
              showIcon
              title={wizardDraft.data.sync_seal ? "已选择同步用印" : "合同正在审批中"}
              description={
                wizardDraft.data.sync_seal
                  ? "可保存用印草稿，或立即提交同步用印；合同审批与用印审批将分别流转。"
                  : "可先提交用印申请；合同审批与用印审批将分别流转。"
              }
            />
          ) : (
            <div className="contract-wizard-finished">
              <CheckOutlined />
              <h3>合同审批已通过</h3>
              <p>合同草稿、审批意见、附件和时间线均已保存，可以继续办理合同用印。</p>
            </div>
          )}
          {wizardDraft?.data.seal_application_id ? (
            <Descriptions
              bordered
              size="small"
              column={2}
              items={[
                { key: "contract", label: "合同编号", children: wizardDraft.serial_no },
                {
                  key: "seal",
                  label: "用印申请编号",
                  children: wizardDraft.data.seal_application_no || `#${wizardDraft.data.seal_application_id}`,
                },
                {
                  key: "status",
                  label: "衔接状态",
                  children:
                    wizardDraft.data.sync_seal && !wizardDraft.data.sync_seal_submitted_at ? (
                      <Tag color="blue">用印草稿待提交</Tag>
                    ) : wizardDraft.data.sync_seal_file_required ? (
                      <Tag color="orange">待补用印文件</Tag>
                    ) : (
                      <Tag color="green">已提交用印审批</Tag>
                    ),
                  span: 2,
                },
              ]}
            />
          ) : (
            <Form form={sealForm} layout="vertical" className="contract-seal-form">
              <div className="form-grid">
                <Form.Item label="用印审批人" name="approver" rules={[{ required: true, message: "请选择用印审批人" }]}>
                  <Select
                    showSearch
                    optionFilterProp="label"
                    options={approvalOptions}
                    placeholder="请选择用印审批人"
                    notFoundContent="没有可用审批人，请先在人事中心配置合同审批资格"
                  />
                </Form.Item>
                <Form.Item label="选择印章" name="seal_asset_id" rules={[{ required: true, message: "请选择印章" }]}>
                  <Select
                    placeholder="请选择印章类型"
                    notFoundContent="暂无可用印章，请管理员到用印中心维护"
                    options={sealAssets.map((asset) => ({
                      value: asset.id,
                      label: `${asset.seal_type}｜${asset.name}（${asset.code}）`,
                    }))}
                  />
                </Form.Item>
                <Form.Item label="用印份数" name="copies" rules={[{ required: true }]}>
                  <InputNumber min={1} max={999} style={{ width: "100%" }} />
                </Form.Item>
                <Form.Item label="计划用印日期" name="use_date" rules={[{ required: true }]}>
                  <DatePicker style={{ width: "100%" }} />
                </Form.Item>
                <Form.Item label="办理方式" name="delivery_method">
                  <Select options={["现场用印", "邮寄用印", "外带用印"].map((value) => ({ value, label: value }))} />
                </Form.Item>
                <Form.Item className="span-2" label="文件名称" name="document_names">
                  <Input placeholder="多份文件可用顿号分隔" />
                </Form.Item>
                <Form.Item className="span-2" label="用印用途" name="purpose" rules={[{ required: true }]}>
                  <Input />
                </Form.Item>
                <Form.Item className="span-2" label="申请说明" name="description">
                  <Input.TextArea rows={2} />
                </Form.Item>
              </div>
              <Form.Item name="submit" valuePropName="checked" hidden>
                <Checkbox />
              </Form.Item>
            </Form>
          )}
          <Divider titlePlacement="start">合同附件</Divider>
          <div className="contract-attachment-list">
            {attachments.length ? (
              attachments.map((item) => (
                <Button key={item.id} type="link" onClick={() => onDownloadAttachment(item)}>
                  {item.original_name}
                </Button>
              ))
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无合同附件" />
            )}
          </div>
          <Divider titlePlacement="start">合同状态时间线</Divider>
          {historyItems.length ? <Timeline items={historyItems} /> : null}
        </div>
      )}
    </>
  );
}
