import { LEGACY_THIRD_PARTY_FEE_SUBTYPES } from "../caseRelationConsumption.mjs";
import { displayFinancialValue } from "../financialValueDisplay";

export type CaseReceiptFile = {
  attachmentId: number;
  billNo: string;
  billDate: string;
  originalName: string;
};

export type CaseFeeFile = {
  attachment_id: number;
  kind: "invoice" | "payment" | "receipt";
  source: string;
  bill_no: string;
  bill_date: string;
  original_name: string;
  remark: string;
  invoice_record_id: number | null;
};

export function caseFeeBillDisplay(data: Record<string, unknown>) {
  const entries: { key: string; label: string; kind: "invoice" | "files" }[] = [];
  if (data.invoice_no) entries.push({ key: "invoice", label: String(data.invoice_no), kind: "invoice" });
  const files = Array.isArray(data.case_fee_files) ? data.case_fee_files as CaseFeeFile[] : null;
  const dates = [displayFinancialValue(String(data.invoice_date || "")).slice(0, 10), displayFinancialValue(String(data.paid_date || data.payment_date || "")).slice(0, 10)];
  if (files) {
    for (const file of files) {
      entries.push({ key: `attachment-${file.attachment_id}`, label: (file.kind === "invoice" && file.bill_no) || file.original_name || file.bill_no || "查看凭证", kind: "files" });
      dates.push(file.bill_date);
    }
  } else {
    // 非案件关系入口仍使用原始票据元数据，不把核销单据号写回发票字段。
    for (const receipt of caseReceiptFiles(data)) {
      entries.push({ key: `receipt-${receipt.attachmentId}`, label: receipt.originalName || receipt.billNo || "查看凭证", kind: "files" });
      dates.push(receipt.billDate);
    }
    if (Number(data.writeoff_voucher_record_id) > 0) {
      entries.push({ key: "writeoff", label: String(data.writeoff_voucher_no || "查看凭证"), kind: "files" });
    }
  }
  return {
    entries: entries.map(entry => ({ ...entry, label: displayFinancialValue(entry.label) })),
    dates: [...new Set(dates.filter(Boolean).map(date => displayFinancialValue(date)))],
  };
}

export function caseReceiptFiles(data: Record<string, unknown>): CaseReceiptFile[] {
  if (!Array.isArray(data?.receipt_files)) return [];
  return data.receipt_files
    .filter((item): item is Record<string, unknown> => Boolean(item && typeof item === "object"))
    .map((item) => ({
      attachmentId: Number(item.attachment_id) || 0,
      billNo: String(item.bill_no || "").trim(),
      billDate: String(item.bill_date || "").slice(0, 10),
      originalName: String(item.original_name || "").trim(),
    }));
}

export function caseFeeReceiptApplicable(data: Record<string, unknown>, title = ""): boolean {
  if (typeof data.receipt_allocation_applicable === "boolean") return data.receipt_allocation_applicable;
  return ![data.expense_subtype, data.fee_type_name, data.case_fee_type_name, data.fee_type, data.title, title]
    .some(value => LEGACY_THIRD_PARTY_FEE_SUBTYPES.includes(String(value || "").trim()));
}
