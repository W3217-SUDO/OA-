import { Form } from "antd";
import { useState } from "react";
import type { InvoiceDateFormValues, InvoiceNumberFormValues } from "../formTypes";
import type { FinanceFlow } from "../types";

/** 发票编号与日期修改分别保留原表单实例和关闭清理行为。 */
export function useInvoiceMaintenanceState() {
  const [invoiceNumberTarget, setInvoiceNumberTarget] = useState<FinanceFlow | null>(null);
  const [invoiceDateTarget, setInvoiceDateTarget] = useState<FinanceFlow | null>(null);
  const [invoiceNumberForm] = Form.useForm<InvoiceNumberFormValues>();
  const [invoiceDateForm] = Form.useForm<InvoiceDateFormValues>();

  const closeInvoiceNumber = () => {
    setInvoiceNumberTarget(null);
    invoiceNumberForm.resetFields();
  };
  const closeInvoiceDate = () => {
    setInvoiceDateTarget(null);
    invoiceDateForm.resetFields();
  };

  return {
    invoiceNumberTarget, setInvoiceNumberTarget, invoiceNumberForm, closeInvoiceNumber,
    invoiceDateTarget, setInvoiceDateTarget, invoiceDateForm, closeInvoiceDate,
  };
}
