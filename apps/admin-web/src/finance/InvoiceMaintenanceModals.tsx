import { DatePicker, Form, Input, Modal } from "antd";
import type { FormInstance } from "antd";
import type { InvoiceDateFormValues, InvoiceNumberFormValues } from "./formTypes";
import type { FinanceFlow } from "./types";

export interface InvoiceMaintenanceModalsProps {
  loading: boolean;
  number: {
    target: FinanceFlow | null;
    form: FormInstance<InvoiceNumberFormValues>;
    onSubmit: () => Promise<void>;
    onClose: () => void;
  };
  date: {
    target: FinanceFlow | null;
    form: FormInstance<InvoiceDateFormValues>;
    onSubmit: () => Promise<void>;
    onClose: () => void;
  };
}

export function InvoiceMaintenanceModals({ loading, number, date }: InvoiceMaintenanceModalsProps) {
  return (
    <>
      <Modal
        open={Boolean(number.target)}
        title="修改发票编号"
        okText="确定"
        cancelText="取消"
        confirmLoading={loading}
        onOk={() => void number.onSubmit()}
        onCancel={number.onClose}
      >
        <Form form={number.form} layout="horizontal" labelCol={{ span: 6 }}>
          <Form.Item label="请票单号" name="application_no">
            <Input readOnly />
          </Form.Item>
          <Form.Item label="合同编号" name="contract_no">
            <Input readOnly />
          </Form.Item>
          <Form.Item label="原发票号码" name="old_invoice_no">
            <Input readOnly />
          </Form.Item>
          <Form.Item label="新发票号码" name="new_invoice_no" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(date.target)}
        title="修改发票日期"
        okText="确定"
        cancelText="取消"
        confirmLoading={loading}
        onOk={() => void date.onSubmit()}
        onCancel={date.onClose}
      >
        <Form form={date.form} layout="horizontal" labelCol={{ span: 6 }}>
          <Form.Item label="请票单号" name="application_no">
            <Input readOnly />
          </Form.Item>
          <Form.Item label="发票申请日期" name="application_date" rules={[{ required: true }]}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="发票开票日期" name="invoice_date" rules={[{ required: true }]}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
