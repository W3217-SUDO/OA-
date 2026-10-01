import { Form } from "antd";
import { useState } from "react";
import type { RefundAmountFormValues, RefundCompleteFormValues } from "../formTypes";
import type { FinanceFlow } from "../types";

/** 退款金额修改与到账登记各自维护表单生命周期。 */
export function useRefundMaintenanceState() {
  const [refundAmountTarget, setRefundAmountTarget] = useState<FinanceFlow | null>(null);
  const [refundCompleteTarget, setRefundCompleteTarget] = useState<FinanceFlow | null>(null);
  const [refundAmountForm] = Form.useForm<RefundAmountFormValues>();
  const [refundCompleteForm] = Form.useForm<RefundCompleteFormValues>();

  const closeRefundAmount = () => {
    setRefundAmountTarget(null);
    refundAmountForm.resetFields();
  };
  const closeRefundComplete = () => setRefundCompleteTarget(null);

  return {
    refundAmountTarget, setRefundAmountTarget, refundAmountForm, closeRefundAmount,
    refundCompleteTarget, setRefundCompleteTarget, refundCompleteForm, closeRefundComplete,
  };
}
