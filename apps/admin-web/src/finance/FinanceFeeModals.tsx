import { Button, Descriptions, Form, Input, InputNumber, Modal } from "antd";
import type { FormInstance } from "antd";
import { FeeTypePicker } from "./FeeTypePicker";
import { money } from "./constants";
import type { FeeEditorFormValues } from "./formTypes";
import type { Fee, Transaction } from "./types";

export interface FeeDetailModalProps {
  fee: Fee | null;
  isInternalHistoryList: boolean;
  initialView: string;
  onClose: () => void;
  paymentStatus: (fee: Fee) => string;
  latestTransaction: (fee: Fee) => Transaction | undefined;
  linkedCaseForFee: (fee: Fee) => Fee | undefined;
  onOpenCase: (caseNo: unknown) => void;
  onOpenContract: (contractNo: string) => void;
  onOpenCustomer: (customer: string, customerNo?: string) => void;
  financePersonDisplayName: (identity?: unknown, displayName?: unknown) => string;
}

export function FeeDetailModal({
  fee: feeDetail,
  isInternalHistoryList,
  initialView,
  onClose,
  paymentStatus,
  latestTransaction,
  linkedCaseForFee,
  onOpenCase: openCaseDetail,
  onOpenContract: openContractDetail,
  onOpenCustomer: openCustomerDetail,
  financePersonDisplayName,
}: FeeDetailModalProps) {
  return (
      <Modal
        width={760}
        open={Boolean(feeDetail) && !isInternalHistoryList}
        title="请款单详情"
        footer={null}
        onCancel={onClose}
      >
        {feeDetail && (
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="请款单号">
              {feeDetail.serial_no || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              {initialView === "finance-internal-refused"
                ? "已拒绝"
                : paymentStatus(feeDetail)}
            </Descriptions.Item>
            <Descriptions.Item label="付款包号">
              {feeDetail.data.payment_package_no ||
                feeDetail.data.package_no ||
                feeDetail.data.payment_package_context?.serial_no ||
                "—"}
            </Descriptions.Item>
            <Descriptions.Item label="付款包状态">
              {feeDetail.data.payment_package_context?.status || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="申请日期">
              {(
                feeDetail.data.application_date ||
                feeDetail.created_at ||
                "—"
              ).slice(0, 10)}
            </Descriptions.Item>
            <Descriptions.Item label="审核日期">
              {(feeDetail.data.audit_date || feeDetail.updated_at || "—").slice(
                0,
                10,
              )}
            </Descriptions.Item>
            <Descriptions.Item label="申请金额">
              {feeDetail.data.amount == null
                ? "—"
                : money(feeDetail.data.payment_request_amount ?? feeDetail.data.amount)}
            </Descriptions.Item>
            <Descriptions.Item label="费用类型">
              {feeDetail.data.fee_type || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="案件编号">
              {feeDetail.data.case_no ? <Button type="link" onClick={() => openCaseDetail(feeDetail.data.case_no)}>{feeDetail.data.case_no}</Button> : "—"}
            </Descriptions.Item>
            <Descriptions.Item label="合同编号">
              {feeDetail.data.contract_no ? (
                <Button
                  type="link"
                  onClick={() => openContractDetail(feeDetail.data.contract_no)}
                >
                  {feeDetail.data.contract_no}
                </Button>
              ) : (
                "—"
              )}
            </Descriptions.Item>
            <Descriptions.Item label="案件阶段">
              {feeDetail.data.case_stage ||
                linkedCaseForFee(feeDetail)?.data.case_stage ||
                linkedCaseForFee(feeDetail)?.status ||
                "—"}
            </Descriptions.Item>
            <Descriptions.Item label="案件名称" span={2}>
              {linkedCaseForFee(feeDetail)?.title || feeDetail.title || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="客户名称">
              {feeDetail.customer ? <Button type="link" onClick={() => openCustomerDetail(feeDetail.customer, feeDetail.data.customer_no)}>{feeDetail.customer}</Button> : "—"}
            </Descriptions.Item>
            <Descriptions.Item label="收款单位">
              {feeDetail.data.payee || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="付款日期">
              {latestTransaction(feeDetail)?.transaction_date || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="申请人">
              {financePersonDisplayName(
                feeDetail.data.applicant || feeDetail.owner,
                feeDetail.data.applicant_display_name || feeDetail.data.owner_display_name,
              )}
            </Descriptions.Item>
            <Descriptions.Item label="缴费法院/机构">
              {feeDetail.data.court || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="缴费通知文号">
              {feeDetail.data.document_no || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="说明" span={2}>
              {feeDetail.data.description || "—"}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
  );
}

export interface FeeEditorModalProps {
  open: boolean;
  target: Fee | null;
  form: FormInstance<FeeEditorFormValues>;
  selectedFeeType: string;
  onFeeTypeChange: (type: string) => void;
  onSubmit: () => Promise<void>;
  onClose: () => void;
}

export function FeeEditorModal({
  open: feeOpen,
  target: feeEditTarget,
  form: feeForm,
  selectedFeeType,
  onFeeTypeChange: setFeeTypeOverride,
  onSubmit: createFee,
  onClose: closeFeeModal,
}: FeeEditorModalProps) {
  return (
      <Modal
        open={feeOpen}
        title={feeEditTarget ? "编辑费用" : "新增费用"}
        okText={feeEditTarget ? "保存修改" : "保存草稿"}
        cancelText="取消"
        onOk={createFee}
        onCancel={closeFeeModal}
      >
        <Form form={feeForm} layout="vertical">
          <Form.Item name="case_record_id" hidden>
            <Input />
          </Form.Item>
          <Form.Item name="contract_record_id" hidden>
            <Input />
          </Form.Item>
          <Form.Item label="费用名称" name="title" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="fee_type" hidden><Input /></Form.Item>
          <Form.Item name="expense_subtype" hidden><Input /></Form.Item>
          <Form.Item name="expense_scope" hidden><Input /></Form.Item>
          <div className="form-grid">
            <Form.Item
              label="费用类型"
              name="fee_type_id"
              rules={[{ required: true, message: "请选择费用子类型" }]}
            >
              <FeeTypePicker editing scope={feeForm.getFieldValue("expense_scope")}
                onSelectOption={(item) => {
                  feeForm.setFieldsValue({ fee_type: item.base_fee_type, expense_subtype: item.name });
                  setFeeTypeOverride(item.base_fee_type);
                }}
              />
            </Form.Item>
            <Form.Item
              label="金额"
              name="amount"
              rules={[
                { required: true },
                {
                  validator: (_, value) =>
                    value === 0
                      ? Promise.reject(new Error("金额不能为 0"))
                      : Promise.resolve(),
                },
              ]}
            >
              <InputNumber
                min={selectedFeeType === "内部费用" ? undefined : 0.01}
                precision={3}
                style={{ width: "100%" }}
                placeholder={
                  selectedFeeType === "内部费用" ? "允许负数冲销" : "请输入正数"
                }
              />
            </Form.Item>
            <Form.Item
              label="经办人员"
              name="handler"
              rules={[{ required: true }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="关联案号"
              name="case_no"
              rules={[{ required: true, message: "请选择或填写关联案号" }]}
            >
              <Input />
            </Form.Item>
            <Form.Item label="客户" name="customer">
              <Input />
            </Form.Item>
            <Form.Item label="收款单位" name="payee">
              <Input />
            </Form.Item>
          </div>
          <Form.Item label="缴费法院/机构" name="court">
            <Input />
          </Form.Item>
          <Form.Item label="缴费通知文号" name="document_no">
            <Input />
          </Form.Item>
          <Form.Item label="说明" name="description">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
  );
}
