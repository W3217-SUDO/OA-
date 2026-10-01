import { useState } from "react";
import type { Fee } from "../types";

/** 请款撤销和回滚弹窗只管理输入状态；提交和刷新仍由付款业务服务负责。 */
export function usePaymentReversalState() {
  const [paymentCancelTarget, setPaymentCancelTarget] = useState<Fee | null>(null);
  const [paymentCancelReason, setPaymentCancelReason] = useState("");
  const [paymentRollbackTarget, setPaymentRollbackTarget] = useState<Fee | null>(null);
  const [paymentRollbackComment, setPaymentRollbackComment] = useState("");

  const openPaymentCancel = (row: Fee) => {
    setPaymentCancelReason("");
    setPaymentCancelTarget(row);
  };
  const closePaymentCancel = () => {
    setPaymentCancelTarget(null);
    setPaymentCancelReason("");
  };
  const openPaymentRollback = (row: Fee) => {
    setPaymentRollbackComment("");
    setPaymentRollbackTarget(row);
  };
  const closePaymentRollback = () => {
    setPaymentRollbackTarget(null);
    setPaymentRollbackComment("");
  };

  return {
    paymentCancelTarget,
    setPaymentCancelTarget,
    paymentCancelReason,
    setPaymentCancelReason,
    paymentRollbackTarget,
    setPaymentRollbackTarget,
    paymentRollbackComment,
    setPaymentRollbackComment,
    openPaymentCancel,
    closePaymentCancel,
    openPaymentRollback,
    closePaymentRollback,
  };
}
