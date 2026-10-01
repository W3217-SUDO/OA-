import { Form, message } from "antd";
import dayjs from "dayjs";
import { useEffect, useRef, useState } from "react";
import { financeErrorDetail } from "../financeErrors";
import type { RefundBatchFeeFormValues } from "../formTypes";
import { loadRefundBatchFeeSubTypes, loadRefundBatchPaymentTypes } from "../services/refundsActions";
import type { Fee, RefundBatchFeeSubtype, RefundBatchPaymentType } from "../types";

/** 批量新增费用的两步表单、参考选项与请求生命周期。 */
export function useRefundBatchFeeState() {
  const [refundBatchFeeOpen, setRefundBatchFeeOpen] = useState(false);
  const [refundBatchFeeStep, setRefundBatchFeeStep] = useState(0);
  const [refundBatchFeeLoading, setRefundBatchFeeLoading] = useState(false);
  const [refundBatchFeeKind, setRefundBatchFeeKind] = useState<"ordinary" | "internal">("ordinary");
  const [refundBatchFeeBaseType, setRefundBatchFeeBaseType] = useState("官方费用");
  const [refundBatchFeeSubTypes, setRefundBatchFeeSubTypes] = useState<RefundBatchFeeSubtype[]>([]);
  const [refundBatchPaymentTypes, setRefundBatchPaymentTypes] = useState<RefundBatchPaymentType[]>([]);
  const [refundBatchFeeForm] = Form.useForm<RefundBatchFeeFormValues>();
  const optionsRequestRef = useRef<AbortController | null>(null);

  const cancelOptionsRequest = () => {
    optionsRequestRef.current?.abort();
    optionsRequestRef.current = null;
  };
  useEffect(() => () => cancelOptionsRequest(), []);

  const openRefundBatchFee = (feeType: string, linked: Fee[], username: string) => {
    cancelOptionsRequest();
    const controller = new AbortController();
    optionsRequestRef.current = controller;
    const internal = feeType === "内部费用";
    setRefundBatchFeeKind(internal ? "internal" : "ordinary");
    setRefundBatchFeeBaseType(feeType);
    if (!internal) {
      void loadRefundBatchPaymentTypes(controller.signal)
        .then((rows) => { if (!controller.signal.aborted) setRefundBatchPaymentTypes(rows); })
        .catch((error: unknown) => {
          if (!controller.signal.aborted) message.error(financeErrorDetail(error) || "收款单位加载失败");
        });
    }
    void loadRefundBatchFeeSubTypes(feeType, controller.signal)
      .then((rows) => { if (!controller.signal.aborted) setRefundBatchFeeSubTypes(rows); })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setRefundBatchFeeSubTypes([]);
        message.error(financeErrorDetail(error) || "费用类型加载失败");
      });
    const deadline = dayjs().add(5, "day");
    refundBatchFeeForm.setFieldsValue({
      handler: username,
      items: linked.map((item) => ({
        case_id: item.id, case_no: item.serial_no, customer: item.customer,
        contract_record_id: Number(item.data?.contract_record_id || item.data?.contract_id || 0) || undefined,
        fee_type: feeType, fee_type_id: undefined, fee_type_name: "",
        amount: undefined, payment_amount: undefined, payment_type_id: undefined,
        payment_remark: "", payee_username: undefined, base_amount: undefined,
        reference_commission: undefined, remark: "", deadline,
      })),
    });
    setRefundBatchFeeStep(0);
    setRefundBatchFeeOpen(true);
  };
  const closeRefundBatchFee = () => {
    cancelOptionsRequest();
    setRefundBatchFeeOpen(false);
    setRefundBatchFeeStep(0);
    refundBatchFeeForm.resetFields();
  };
  const syncFirstRefundFeeField = (field: string) => {
    const items = refundBatchFeeForm.getFieldValue("items") || [];
    if (items.length < 2) return;
    const first = items[0] || {};
    const value = first[field];
    if (value === undefined || value === null || value === "") return;
    refundBatchFeeForm.setFieldValue("items", items.map((item: Record<string, unknown>, index: number) =>
      index === 0 ? item : { ...item, [field]: value }));
  };

  return {
    refundBatchFeeOpen, setRefundBatchFeeOpen, refundBatchFeeStep, setRefundBatchFeeStep,
    refundBatchFeeLoading, setRefundBatchFeeLoading, refundBatchFeeKind,
    refundBatchFeeBaseType, refundBatchFeeSubTypes, refundBatchPaymentTypes,
    refundBatchFeeForm, openRefundBatchFee, closeRefundBatchFee, syncFirstRefundFeeField,
  };
}
