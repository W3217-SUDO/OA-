import { Form } from "antd";
import { useEffect, useRef, useState } from "react";
import { resolveIncomingPaymentDetailTarget } from "../../incomingPaymentDetailNavigation";
import { financeErrorDetail } from "../financeErrors";
import type { IncomingClaimFormValues, IncomingPaymentFormValues } from "../formTypes";
import { loadIncomingPaymentDetail } from "../services/accountingActions";
import type { FinanceScope, IncomingPayment } from "../types";

/** 回款登记、认领和详情的局部状态。 */
export function useFinanceIncomingState(initialView: string, financeScope: FinanceScope) {
  const [incomingOpen, setIncomingOpen] = useState(false);
  const [editingIncoming, setEditingIncoming] = useState<IncomingPayment | null>(null);
  const [claimTarget, setClaimTarget] = useState<IncomingPayment | null>(null);
  const [claimCustomers, setClaimCustomers] = useState<Array<{ id: number; title: string; serial_no: string }>>([]);
  const [claimCustomersLoading, setClaimCustomersLoading] = useState(false);
  const claimCustomerSearchRequest = useRef(0);
  const [incomingAllocationTarget, setIncomingAllocationTarget] = useState<IncomingPayment | null>(null);
  const [incomingDetailTarget, setIncomingDetailTarget] = useState<IncomingPayment | null>(null);
  const [incomingDetailLoading, setIncomingDetailLoading] = useState(false);
  const [incomingDetailError, setIncomingDetailError] = useState<string | null>(null);
  const [incomingDetailAttempt, setIncomingDetailAttempt] = useState(0);
  const [incomingForm] = Form.useForm<IncomingPaymentFormValues>();
  const [claimForm] = Form.useForm<IncomingClaimFormValues>();

  useEffect(() => {
    const paymentId = resolveIncomingPaymentDetailTarget(initialView);
    setIncomingDetailTarget(null);
    setIncomingDetailError(null);
    setIncomingDetailLoading(Boolean(paymentId));
    if (!paymentId) return;
    const controller = new AbortController();
    void loadIncomingPaymentDetail(paymentId, financeScope, controller.signal)
      .then((payment) => { if (!controller.signal.aborted) setIncomingDetailTarget(payment); })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setIncomingDetailError(financeErrorDetail(error) || "回款详情加载失败");
      })
      .finally(() => { if (!controller.signal.aborted) setIncomingDetailLoading(false); });
    return () => controller.abort();
  }, [initialView, financeScope, incomingDetailAttempt]);

  return {
    incomingOpen, setIncomingOpen, editingIncoming, setEditingIncoming,
    claimTarget, setClaimTarget, claimCustomers, setClaimCustomers,
    claimCustomersLoading, setClaimCustomersLoading, claimCustomerSearchRequest,
    incomingAllocationTarget, setIncomingAllocationTarget, incomingDetailTarget, setIncomingDetailTarget,
    incomingDetailLoading, incomingDetailError,
    retryIncomingDetail: () => setIncomingDetailAttempt((value) => value + 1),
    incomingForm, claimForm,
  };
}
