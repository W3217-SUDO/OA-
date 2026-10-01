import { DatePicker, Form, Input, InputNumber, Modal, Select } from "antd";
import type { FormInstance } from "antd";
import type { RefundCreationFormValues } from "./formTypes";
import type { Fee } from "./types";

export interface RefundCreationModalProps {
  open: boolean;
  form: FormInstance<RefundCreationFormValues>;
  cases: Fee[];
  onSubmit: () => Promise<void>;
  onClose: () => void;
}

export function RefundCreationModal({ open, form, cases, onSubmit, onClose }: RefundCreationModalProps) {
  return (
    <Modal
      width={760}
      open={open}
      title="新增诉讼费退款申请"
      okText="保存草稿"
      cancelText="取消"
      onOk={onSubmit}
      onCancel={onClose}
    >
      <Form form={form} layout="vertical">
        <Form.Item name="fee_record_id" hidden>
          <Input />
        </Form.Item>
        <div className="form-grid">
          <Form.Item className="span-2" label="关联案件" name="case_no" rules={[{ required: true }]}>
            <Select
              showSearch
              optionFilterProp="label"
              options={cases.map((item) => ({
                value: item.serial_no,
                label: `${item.serial_no}｜${item.customer}｜${item.title}`,
              }))}
              onChange={(caseNo) => {
                const item = cases.find((candidate) => candidate.serial_no === caseNo);
                if (item) {
                  form.setFieldValue("customer", item.customer);
                  form.setFieldValue("court", item.data.court || "");
                }
              }}
            />
          </Form.Item>
          <Form.Item label="客户" name="customer" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="退款法院" name="court" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="原缴费票号" name="original_payment_no" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="退款金额" name="amount" rules={[{ required: true }]}>
            <InputNumber min={0.01} precision={2} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="申请人" name="applicant" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="预计到账日" name="expected_date">
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="退款账户名" name="refund_account_name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="退款银行" name="refund_bank" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item className="span-2" label="退款账号" name="refund_account" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="退款原因" name="reason">
            <Input />
          </Form.Item>
          <Form.Item label="备注" name="remark">
            <Input />
          </Form.Item>
        </div>
      </Form>
    </Modal>
  );
}
