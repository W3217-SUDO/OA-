import { Form } from "antd";
import { useState } from "react";
import type { PaymentWriteoffFormValues } from "../formTypes";
import type { Fee } from "../types";

/** 付款核销的目标与表单同属一个流程，关闭时同步清理。 */
export function usePaymentWriteoffState() {
  const [writeoffTarget, setWriteoffTarget] = useState<Fee | null>(null);
  const [writeoffForm] = Form.useForm<PaymentWriteoffFormValues>();

  const closePaymentWriteoff = () => {
    setWriteoffTarget(null);
    writeoffForm.resetFields();
  };

  return { writeoffTarget, setWriteoffTarget, writeoffForm, closePaymentWriteoff };
}
