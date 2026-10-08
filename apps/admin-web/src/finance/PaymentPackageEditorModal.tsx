import { Alert, DatePicker, Form, Input, InputNumber, Modal, Select } from "antd";
import type { FormInstance } from "antd";
import Table from "../components/ResizableTable";
import { money, paymentMethodOptions } from "./constants";
import type { PaymentPackageEditorFormValues, PaymentPackageWriteoffFormValues } from "./formTypes";
import type { Fee } from "./types";

export interface PaymentPackageEditorModalProps {
  open: boolean;
  target: Fee | null;
  loading: boolean;
  selectedFeeIds: number[];
  onSelectedFeeIdsChange: (ids: number[]) => void;
  form: FormInstance<PaymentPackageEditorFormValues>;
  candidates: Fee[];
  onSubmit: () => Promise<void>;
  onClose: () => void;
}

export function PaymentPackageEditorModal({
  open: paymentPackageEditorOpen,
  target: paymentPackageEditTarget,
  loading: paymentPackageLoading,
  selectedFeeIds: paymentPackageSelectedFeeIds,
  onSelectedFeeIdsChange: setPaymentPackageSelectedFeeIds,
  form: paymentPackageEditForm,
  candidates: paymentPackageCandidates,
  onSubmit: submitPaymentPackageEditor,
  onClose,
}: PaymentPackageEditorModalProps) {
  return (
      <Modal
        width={860}
        open={paymentPackageEditorOpen}
        title={paymentPackageEditTarget ? `编辑付款包：${paymentPackageEditTarget.serial_no}` : "新增付款包"}
        okText="保存"
        cancelText="取消"
        confirmLoading={paymentPackageLoading}
        onOk={() => void submitPaymentPackageEditor()}
        onCancel={onClose}
      >
        <Alert
          type="info"
          showIcon
          message="请选择同一收款人的已审批内部费用"
          description="编辑后会重新计算金额，并同步更新所选费用。已核销付款包不可编辑。"
          style={{ marginBottom: 12 }}
        />
        <Table
          rowKey="id"
          size="small"
          pagination={{ pageSize: 6, size: "small" }}
          dataSource={paymentPackageCandidates}
          rowSelection={{
            selectedRowKeys: paymentPackageSelectedFeeIds,
            onChange: (keys) => setPaymentPackageSelectedFeeIds(keys.map(Number)),
          }}
          columns={[
            { title: "请款单号", dataIndex: "serial_no", width: 180 },
            { title: "收款人", render: (_: unknown, fee: Fee) => fee.data?.payee || fee.data?.applicant || fee.owner || "—" },
            { title: "金额", render: (_: unknown, fee: Fee) => money(Number(fee.data?.actual_commission ?? fee.data?.amount ?? 0)) },
            { title: "状态", dataIndex: "status", width: 100 },
          ]}
        />
        <Form form={paymentPackageEditForm} layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item label="备注" name="comment" rules={[{ max: 500, message: "备注不能超过500个字符" }]}>
            <Input.TextArea rows={3} placeholder="可选，记录本次付款打包说明" />
          </Form.Item>
        </Form>
      </Modal>
  );
}

export interface PaymentPackageWriteoffModalProps {
  target: Fee | null;
  form: FormInstance<PaymentPackageWriteoffFormValues>;
  loading: boolean;
  onSubmit: () => Promise<void>;
  onClose: () => void;
}

export function PaymentPackageWriteoffModal({
  target: paymentPackageWriteoffTarget,
  form: paymentPackageWriteoffForm,
  loading: paymentPackageLoading,
  onSubmit: writeoffPaymentPackage,
  onClose,
}: PaymentPackageWriteoffModalProps) {
  return (
      <Modal
        className="finance-payment-package-writeoff-modal"
        width={600}
        style={{ top: 30 }}
        open={Boolean(paymentPackageWriteoffTarget)}
        title="付款核销"
        okText="确定"
        cancelText="取消"
        confirmLoading={paymentPackageLoading}
        onOk={() => void writeoffPaymentPackage()}
        onCancel={onClose}
      >
        <Form form={paymentPackageWriteoffForm} layout="vertical">
          <Form.Item
            label="付款打包号"
            name="package_no"
            required
          >
            <Input readOnly />
          </Form.Item>
          <Form.Item
            label="请确认付款金额"
            name="amount"
            rules={[{ required: true, message: "请确认付款金额." }]}
          >
            <InputNumber
              precision={2}
              readOnly
              controls={false}
              style={{ width: "100%" }}
            />
          </Form.Item>
          <Form.Item
            label="请输入付款日期"
            name="paid_date"
            rules={[{ required: true, message: "请输入付款日期." }]}
          >
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item
            label="请选择付款方式"
            name="payment_method"
            rules={[{ required: true, message: "请选择付款方式." }]}
          >
            <Select
              options={paymentMethodOptions.map((value) => ({
                label: value,
                value,
              }))}
            />
          </Form.Item>
          <Form.Item
            label="请输入付款单据号"
            name="invoice_no"
            rules={[{ required: true, message: "请输入付款单据号." }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="请输入付款备注" name="remark">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
  );
}
