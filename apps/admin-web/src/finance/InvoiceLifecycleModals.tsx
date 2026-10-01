import { Alert, DatePicker, Form, Input, Modal } from "antd";
import type { FormInstance } from "antd";
import type { InvoiceIssueFormValues, InvoiceVoidFormValues } from "./formTypes";
import type { FinanceFlow } from "./types";

export interface InvoiceLifecycleModalsProps {
  issue: {
    target: FinanceFlow | null;
    form: FormInstance<InvoiceIssueFormValues>;
    onSubmit: () => Promise<void>;
    onClose: () => void;
  };
  void: {
    target: FinanceFlow | null;
    form: FormInstance<InvoiceVoidFormValues>;
    onSubmit: () => Promise<void>;
    onClose: () => void;
  };
}

export function InvoiceLifecycleModals({ issue, void: voidInvoice }: InvoiceLifecycleModalsProps) {
  return (
    <>
      <Modal
        open={Boolean(issue.target)}
        title={`登记开票：${issue.target?.serial_no || ""}`}
        okText="确认开票"
        cancelText="取消"
        onOk={issue.onSubmit}
        onCancel={issue.onClose}
      >
        <Form form={issue.form} layout="vertical">
          <Form.Item label="发票号码" name="invoice_no" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="开票日期" name="invoice_date" rules={[{ required: true }]}>
            <DatePicker style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item label="开票备注" name="comment">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        open={Boolean(voidInvoice.target)}
        title={`作废发票：${voidInvoice.target?.data.invoice_no || voidInvoice.target?.serial_no || ""}`}
        okText="确认作废"
        okButtonProps={{ danger: true }}
        cancelText="取消"
        onOk={voidInvoice.onSubmit}
        onCancel={voidInvoice.onClose}
      >
        <Alert
          type="warning"
          showIcon
          title="作废后系统会生成等额负数开票流水进行冲销。"
          style={{ marginBottom: 16 }}
        />
        <Form form={voidInvoice.form} layout="vertical">
          <Form.Item label="作废原因" name="reason" rules={[{ required: true, min: 2 }]}>
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
