import { Form, message } from "antd";
import { useEffect, useState } from "react";
import { buildInvoiceSourceFields, invoiceFeeAvailableAmount } from "../constants";
import type { Fee, FinanceFlow } from "../types";

/** 开票申请的表单、费用选择与编辑状态。 */
export function useInvoiceApplicationState(initialView: string, invoiceDetailRequestGuard: { begin: () => number; isLatest: (token: number) => boolean }) {
  const [invoiceCandidateFees, setInvoiceCandidateFees] = useState<Fee[]>([]);
  const [invoiceOpen, setInvoiceOpen] = useState(false);
  const [invoiceEditTarget, setInvoiceEditTarget] = useState<FinanceFlow | null>(null);
  const [invoiceSelectedFeeIds, setInvoiceSelectedFeeIds] = useState<number[]>([]);
  const [invoiceForm] = Form.useForm();
  useEffect(() => () => { invoiceDetailRequestGuard.begin(); }, [initialView, invoiceDetailRequestGuard]);

  const closeInvoiceApplication = () => {
    invoiceDetailRequestGuard.begin();
    setInvoiceOpen(false);
    setInvoiceEditTarget(null);
    setInvoiceSelectedFeeIds([]);
    invoiceForm.resetFields();
  };
  const openInvoiceFromFee = (fee: Fee, customerRows: Fee[], customerDefaults: Record<string, unknown>) => {
    invoiceDetailRequestGuard.begin();
    invoiceForm.resetFields();
    invoiceForm.setFieldsValue({
      ...buildInvoiceSourceFields([fee], [], customerRows),
      ...customerDefaults,
      customer_record_id: customerRows[0]?.id,
      case_fee_ids: [fee.id],
      case_fee_allocations: [{ fee_id: fee.id, amount: invoiceFeeAvailableAmount(fee) }],
      extra_amount: 0,
      invoice_type: "增值税普通发票",
      invoice_content: "法律服务费",
      delivery_method: "电子发票",
    });
    setInvoiceSelectedFeeIds([fee.id]);
    setInvoiceOpen(true);
  };
  const applyInvoiceFeeSelection = (nextIds: number[], candidateRows: Fee[], contracts: Fee[], customers: Fee[]) => {
    const selectedFees = candidateRows.filter((fee) => nextIds.includes(fee.id));
    if (!selectedFees.length) {
      setInvoiceSelectedFeeIds([]);
      invoiceForm.setFieldsValue({
        case_no: undefined, case_record_id: undefined,
        contract_record_id: undefined, contract_no: undefined,
        external_contract_no: undefined, customer: undefined,
        customer_no: undefined, amount: undefined,
        case_fee_ids: [], case_fee_allocations: [],
      });
      return;
    }
    const first = buildInvoiceSourceFields([selectedFees[0]], contracts, customers);
    if (selectedFees.some((fee) => buildInvoiceSourceFields([fee], contracts, customers).customer !== first.customer)) {
      message.warning("一次申请开票只能选择同一客户下的费用。");
      return;
    }
    const previous: Array<{ fee_id: number; amount: number }> = invoiceForm.getFieldValue("case_fee_allocations") || [];
    const allocations = selectedFees.map((fee) => ({
      fee_id: fee.id,
      amount: previous.find((row) => Number(row.fee_id) === fee.id)?.amount ?? invoiceFeeAvailableAmount(fee),
    }));
    setInvoiceSelectedFeeIds(nextIds);
    invoiceForm.setFieldsValue({
      ...buildInvoiceSourceFields(selectedFees, contracts, customers),
      case_fee_ids: nextIds,
      case_fee_allocations: allocations,
      amount: Number(allocations.reduce((sum, row) => sum + Number(row.amount || 0), 0).toFixed(2)),
    });
  };

  return {
    invoiceCandidateFees, setInvoiceCandidateFees,
    invoiceOpen, setInvoiceOpen, invoiceEditTarget, setInvoiceEditTarget,
    invoiceSelectedFeeIds, setInvoiceSelectedFeeIds, invoiceForm,
    closeInvoiceApplication, openInvoiceFromFee, applyInvoiceFeeSelection,
  };
}
