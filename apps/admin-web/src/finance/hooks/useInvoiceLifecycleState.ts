import { Form } from "antd";
import { useState } from "react";
import type { InvoiceIssueFormValues, InvoiceVoidFormValues } from "../formTypes";
import type { FinanceFlow } from "../types";

/** 开票登记与作废分别管理目标和表单，保持原有关闭行为。 */
export function useInvoiceLifecycleState() {
  const [issueTarget, setIssueTarget] = useState<FinanceFlow | null>(null);
  const [voidTarget, setVoidTarget] = useState<FinanceFlow | null>(null);
  const [issueForm] = Form.useForm<InvoiceIssueFormValues>();
  const [voidForm] = Form.useForm<InvoiceVoidFormValues>();

  const closeIssue = () => setIssueTarget(null);
  const closeVoid = () => setVoidTarget(null);

  return { issueTarget, setIssueTarget, issueForm, closeIssue, voidTarget, setVoidTarget, voidForm, closeVoid };
}
