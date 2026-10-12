import { LEGACY_THIRD_PARTY_FEE_SUBTYPES } from "../caseRelationConsumption.mjs";

export type CaseReceiptFile = {
  attachmentId: number;
  billNo: string;
  billDate: string;
  originalName: string;
};

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
