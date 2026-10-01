import { Form, message } from "antd";
import { useEffect, useRef, useState } from "react";
import { financeErrorDetail } from "../financeErrors";
import type { PaymentPackageEditorFormValues, PaymentPackageWriteoffFormValues } from "../formTypes";
import { loadPaymentPackageCandidates } from "../services/paymentsActions";
import type { Fee, PaymentPackagePreview } from "../types";

/** 付款包预览、编辑和核销共享付款包上下文。 */
export function usePaymentPackageWorkspaceState() {
  const [paymentPackagePreview, setPaymentPackagePreview] = useState<PaymentPackagePreview | null>(null);
  const [paymentPackageLoading, setPaymentPackageLoading] = useState(false);
  const [paymentPackageDetail, setPaymentPackageDetail] = useState<Fee | null>(null);
  const [paymentPackageEditTarget, setPaymentPackageEditTarget] = useState<Fee | null>(null);
  const [paymentPackageEditorOpen, setPaymentPackageEditorOpen] = useState(false);
  const [paymentPackageSelectedFeeIds, setPaymentPackageSelectedFeeIds] = useState<number[]>([]);
  const [paymentPackageCandidates, setPaymentPackageCandidates] = useState<Fee[]>([]);
  const [paymentPackageWriteoffTarget, setPaymentPackageWriteoffTarget] = useState<Fee | null>(null);
  const [paymentPackageWriteoffForm] = Form.useForm<PaymentPackageWriteoffFormValues>();
  const [paymentPackageEditForm] = Form.useForm<PaymentPackageEditorFormValues>();
  const candidateRequestRef = useRef<AbortController | null>(null);

  const cancelCandidateRequest = () => {
    candidateRequestRef.current?.abort();
    candidateRequestRef.current = null;
  };
  useEffect(() => () => cancelCandidateRequest(), []);

  const openPaymentPackageEditor = (row?: Fee) => {
    cancelCandidateRequest();
    const target = row || null;
    const controller = new AbortController();
    candidateRequestRef.current = controller;
    setPaymentPackageEditTarget(target);
    setPaymentPackageEditorOpen(true);
    setPaymentPackageSelectedFeeIds((target?.data?.fee_ids || []).map((id: unknown) => Number(id)));
    paymentPackageEditForm.setFieldsValue({ comment: target?.data?.comment || target?.description || "" });
    void loadPaymentPackageCandidates(target, controller.signal)
      .then((rows) => { if (!controller.signal.aborted) setPaymentPackageCandidates(rows); })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) message.error(financeErrorDetail(error) || "付款包候选费用加载失败");
      });
  };
  const closePaymentPackageEditor = () => {
    cancelCandidateRequest();
    setPaymentPackageEditTarget(null);
    setPaymentPackageEditorOpen(false);
    setPaymentPackageSelectedFeeIds([]);
    setPaymentPackageCandidates([]);
    paymentPackageEditForm.resetFields();
  };
  const resetPaymentPackageRoute = () => {
    setPaymentPackagePreview(null);
    setPaymentPackageDetail(null);
    closePaymentPackageEditor();
    setPaymentPackageWriteoffTarget(null);
  };

  return {
    paymentPackagePreview, setPaymentPackagePreview, paymentPackageLoading, setPaymentPackageLoading,
    paymentPackageDetail, setPaymentPackageDetail,
    paymentPackageEditTarget, setPaymentPackageEditTarget,
    paymentPackageEditorOpen, setPaymentPackageEditorOpen,
    paymentPackageSelectedFeeIds, setPaymentPackageSelectedFeeIds,
    paymentPackageCandidates, paymentPackageWriteoffTarget, setPaymentPackageWriteoffTarget,
    paymentPackageWriteoffForm, paymentPackageEditForm,
    openPaymentPackageEditor, closePaymentPackageEditor, resetPaymentPackageRoute,
  };
}
