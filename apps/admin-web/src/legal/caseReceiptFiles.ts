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
