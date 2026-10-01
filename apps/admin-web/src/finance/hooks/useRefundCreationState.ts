import { Form } from "antd";
import { useState } from "react";
import type { RefundCreationFormValues } from "../formTypes";

/** 退款草稿表单与打开状态保持同一生命周期。 */
export function useRefundCreationState() {
  const [refundOpen, setRefundOpen] = useState(false);
  const [refundForm] = Form.useForm<RefundCreationFormValues>();

  const openRefundCreation = (displayName: string) => {
    refundForm.setFieldsValue({
      applicant: displayName || "姓名待维护",
      reason: "诉讼费退费",
    });
    setRefundOpen(true);
  };
  const closeRefundCreation = () => setRefundOpen(false);

  return { refundOpen, setRefundOpen, refundForm, openRefundCreation, closeRefundCreation };
}
