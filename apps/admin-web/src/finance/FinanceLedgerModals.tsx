import { DatePicker, Form, Input, InputNumber, Modal, Select } from "antd";
import type { FormInstance } from "antd";
import type { ReconciliationFormValues, TransactionFormValues } from "./formTypes";
import type { Fee } from "./types";

export interface TransactionModalProps {
  open: boolean;
  form: FormInstance<TransactionFormValues>;
  fees: Fee[];
  onSubmit: () => Promise<void>;
  onClose: () => void;
}

export function TransactionModal({
  open: transactionOpen,
  form: transactionForm,
  fees,
  onSubmit: createTransaction,
  onClose,
}: TransactionModalProps) {
  return (
      <Modal
        open={transactionOpen}
        title="登记财务流水"
        okText="保存流水"
        cancelText="取消"
        onOk={createTransaction}
        onCancel={onClose}
      >
        <Form form={transactionForm} layout="vertical">
          <Form.Item label="关联费用" name="finance_record_id">
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              options={fees.map((x) => ({
                value: x.id,
                label: `${x.serial_no}｜${x.title}`,
              }))}
            />
          </Form.Item>
          <div className="form-grid">
            <Form.Item
              label="流水类型"
              name="transaction_type"
              rules={[{ required: true }]}
            >
              <Select
                options={["付款", "开票", "回款", "退费"].map((v) => ({
                  value: v,
                  label: v,
                }))}
              />
            </Form.Item>
            <Form.Item label="金额" name="amount" rules={[{ required: true }]}>
              <InputNumber min={0.01} precision={2} style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item
              label="日期"
              name="transaction_date"
              rules={[{ required: true }]}
            >
              <DatePicker style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item label="凭证/票号" name="voucher_no">
              <Input />
            </Form.Item>
          </div>
          <Form.Item label="对方单位" name="counterparty">
            <Input />
          </Form.Item>
          <Form.Item label="备注" name="remark">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
  );
}

export interface ReconciliationModalProps {
  open: boolean;
  form: FormInstance<ReconciliationFormValues>;
  onSubmit: () => Promise<void>;
  onClose: () => void;
}

export function ReconciliationModal({
  open: reconcileOpen,
  form: reconcileForm,
  onSubmit: createReconciliation,
  onClose,
}: ReconciliationModalProps) {
  return (
      <Modal
        open={reconcileOpen}
        title="生成对账单"
        okText="生成"
        cancelText="取消"
        onOk={createReconciliation}
        onCancel={onClose}
      >
        <Form form={reconcileForm} layout="vertical">
          <Form.Item
            label="对账周期"
            name="period_type"
            rules={[{ required: true }]}
          >
            <Select
              options={["周对账", "月对账"].map((v) => ({
                value: v,
                label: v,
              }))}
            />
          </Form.Item>
          <Form.Item
            label="起止日期"
            name="period"
            rules={[{ required: true }]}
          >
            <DatePicker.RangePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="差异金额" name="discrepancy_amount">
            <InputNumber precision={2} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="备注" name="remark">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
  );
}
