import { CheckOutlined } from "@ant-design/icons";
import type { FormInstance } from "antd";
import {
Alert,
Button,
DatePicker,
Descriptions,
Divider,
Form,
Input,
Modal,
Select,
Space,
Steps,
} from "antd";
import { CONTRACT_ATTACHMENT_ACCEPT } from "../contractWorkflowPolicy.mjs";
import type { Contract } from "./types";

interface ContractInvestigationWizardProps {
  open: boolean;
  isContractInvestigationView: boolean;
  investigating: Contract | null;
  wizardStep: number;
  investigationForm: FormInstance;
  investigationError: string;
  investigationDraftValues: Record<string, any> | null;
  investigationSupervisor: { username: string; display_name: string } | null;
  createdInvestigation: { id: number; serial_no: string; title: string } | null;
  investigationSubmitting: boolean;
  investigationRegion: string;
  contractFile: File | null;
  personName: (value: unknown) => string;
  onCancel: () => void;
  onNext: () => void;
  onPrev: () => void;
  onSubmit: () => void;
  onRegionPickerOpen: () => void;
  onContractFileChange: (file: File | null) => void;
  onNavigate: (key: string) => void;
}

export function ContractInvestigationWizard({
  open,
  isContractInvestigationView,
  investigating,
  wizardStep,
  investigationForm,
  investigationError,
  investigationDraftValues,
  investigationSupervisor,
  createdInvestigation,
  investigationSubmitting,
  investigationRegion,
  contractFile,
  personName,
  onCancel,
  onNext,
  onPrev,
  onSubmit,
  onRegionPickerOpen,
  onContractFileChange,
  onNavigate,
}: ContractInvestigationWizardProps) {
  return (
    <Modal
      width={isContractInvestigationView ? "100%" : 1100}
      open={open}
      title="新建调查任务"
      footer={null}
      maskClosable={false}
      onCancel={onCancel}
      getContainer={isContractInvestigationView ? false : undefined}
      mask={!isContractInvestigationView}
      rootClassName={isContractInvestigationView ? "contract-detail-static-root" : undefined}
    >
      <div className={isContractInvestigationView ? "contract-investigation-workbench" : undefined}>
        <Steps
          current={wizardStep}
          items={["新建调查任务", "选择分配人", "完成分配"].map((title) => ({ title }))}
          style={{ marginBottom: 24 }}
        />
        {investigationError && (
          <Alert type="error" showIcon message={investigationError} style={{ marginBottom: 12 }} />
        )}
        <Form form={investigationForm} layout="horizontal" labelCol={{ span: 5 }} wrapperCol={{ span: 17 }}>
          {wizardStep === 0 && (
            <>
              <Form.Item name="title" hidden>
                <Input />
              </Form.Item>
              <Form.Item name="owner" hidden>
                <Input />
              </Form.Item>
              <Form.Item label="权利人">
                <Input readOnly value={investigating?.data.customer_name || investigating?.customer || ""} />
              </Form.Item>
              <Form.Item label="合同编号">
                <Input readOnly value={investigating?.serial_no || ""} />
              </Form.Item>
              <Form.Item label="合同名称">
                <Input readOnly value={investigating?.title || ""} />
              </Form.Item>
              <Form.Item label="权利类型" name="right_type" rules={[{ required: true }]}>
                <Select
                  options={["商标", "专利", "著作权", "不正当竞争"].map((value) => ({
                    value,
                    label: value,
                  }))}
                />
              </Form.Item>
              <Form.Item label="线索是否客户审核" name="customer_review" rules={[{ required: true }]}>
                <Select options={[{ value: true, label: "是" }, { value: false, label: "否" }]} />
              </Form.Item>
              <Form.Item label="授权期限" required>
                <Space.Compact style={{ width: "100%" }}>
                  <Form.Item name="authorized_from" noStyle rules={[{ required: true, message: "请选择授权开始日期" }]}>
                    <DatePicker placeholder="开始日期" style={{ width: "50%" }} />
                  </Form.Item>
                  <Form.Item name="authorized_to" noStyle rules={[{ required: true, message: "请选择授权结束日期" }]}>
                    <DatePicker placeholder="结束日期" style={{ width: "50%" }} />
                  </Form.Item>
                </Space.Compact>
              </Form.Item>
              <Form.Item label="授权范围" name="region" rules={[{ required: true, message: "请选择授权范围" }]}>
                <Select
                  options={["全国", "区域"].map((value) => ({ value, label: value }))}
                  onChange={(value) => {
                    investigationForm.setFieldValue(
                      "authorization_scope",
                      value === "全国" ? "全国" : "",
                    );
                  }}
                />
              </Form.Item>
              {investigationRegion === "区域" && (
                <Form.Item
                  label="授权区域"
                  name="authorization_scope"
                  rules={[{ required: true, message: "请选择授权区域" }]}
                >
                  <Input
                    readOnly
                    placeholder="请选择省、市或具体授权区域"
                    onClick={onRegionPickerOpen}
                    suffix={
                      <Button type="link" size="small" onClick={onRegionPickerOpen}>
                        选择城市
                      </Button>
                    }
                  />
                </Form.Item>
              )}
              <Form.Item label="备注" name="description">
                <Input.TextArea rows={3} />
              </Form.Item>
              <Form.Item label="资料">
                <input
                  type="file"
                  accept={CONTRACT_ATTACHMENT_ACCEPT}
                  onChange={(event) => onContractFileChange(event.target.files?.[0] || null)}
                />
                {contractFile && <span className="contract-upload-name">{contractFile.name}</span>}
              </Form.Item>
              <Form.Item wrapperCol={{ offset: 5, span: 17 }}>
                <Space>
                  <Button onClick={onCancel}>取消</Button>
                  <Button type="primary" onClick={onNext}>
                    下一步
                  </Button>
                </Space>
              </Form.Item>
            </>
          )}
          {wizardStep === 1 && (
            <>
              <Form.Item label="分配人" name="owner" rules={[{ required: true, message: "请选择分配人" }]}>
                <Select
                  disabled
                  options={
                    investigationSupervisor
                      ? [
                          {
                            value: investigationSupervisor.username,
                            label: investigationSupervisor.display_name || investigationSupervisor.username,
                          },
                        ]
                      : []
                  }
                />
              </Form.Item>
              <Divider titlePlacement="start">调查信息</Divider>
              <Descriptions bordered size="small" column={2} style={{ marginBottom: 20 }}>
                <Descriptions.Item label="调查编号">提交后自动生成</Descriptions.Item>
                <Descriptions.Item label="案源人">
                  {personName(investigating?.data.source_person || investigating?.owner)}
                </Descriptions.Item>
                <Descriptions.Item label="权利人">
                  {investigating?.data.customer_name || investigating?.customer || "—"}
                </Descriptions.Item>
                <Descriptions.Item label="权利类型">
                  {investigationDraftValues?.right_type || "—"}
                </Descriptions.Item>
                <Descriptions.Item label="合同编号">{investigating?.serial_no || "—"}</Descriptions.Item>
                <Descriptions.Item label="合同名称">{investigating?.title || "—"}</Descriptions.Item>
                <Descriptions.Item label="授权开始时间">
                  {investigationDraftValues?.authorized_from?.format?.("YYYY-MM-DD") || "—"}
                </Descriptions.Item>
                <Descriptions.Item label="授权结束时间">
                  {investigationDraftValues?.authorized_to?.format?.("YYYY-MM-DD") || "—"}
                </Descriptions.Item>
                <Descriptions.Item label="授权区域" span={2}>
                  {investigationDraftValues?.authorization_scope || "—"}
                </Descriptions.Item>
              </Descriptions>
              <Form.Item wrapperCol={{ offset: 5, span: 17 }}>
                <Space>
                  <Button onClick={onPrev}>上一步</Button>
                  <Button type="primary" loading={investigationSubmitting} onClick={onSubmit}>
                    提交
                  </Button>
                </Space>
              </Form.Item>
            </>
          )}
          {wizardStep === 2 && (
            <div style={{ textAlign: "center", padding: "32px 0" }}>
              <CheckOutlined style={{ color: "#00a870", fontSize: 48 }} />
              <h3>调查任务分配完成</h3>
              <p>
                {createdInvestigation?.serial_no}｜{createdInvestigation?.title}
              </p>
              <Space>
                <Button onClick={onCancel}>返回合同列表</Button>
                <Button
                  type="primary"
                  onClick={() => {
                    onCancel();
                    onNavigate("investigation-task-published");
                  }}
                >
                  查看我发布的调查任务
                </Button>
              </Space>
            </div>
          )}
        </Form>
      </div>
    </Modal>
  );
}
