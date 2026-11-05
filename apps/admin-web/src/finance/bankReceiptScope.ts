const bankNames: Record<string, string[]> = {
  icbc: ["工行", "工商银行"],
  citic: ["中信"],
  boc: ["中行", "中国银行"],
  cmb: ["招商", "招行"],
  gdicbc: ["国定工行"],
};

export function receiptBankCode(route: string): string | undefined {
  const match = /^finance-receipts-(icbc|citic|boc|cmb|gdicbc)$/.exec(route);
  return match?.[1];
}

export function matchesReceiptBank(source: string | null | undefined, code: string): boolean {
  const value = (source || "").trim().toLowerCase();
  // 501588：“国定工行”也含“工行”，工行页不算国定工行。
  if (code === "icbc" && value.includes("国定")) return false;
  return value === code || (bankNames[code] || []).some((name) => value.includes(name));
}

/** 回款四个银行页上传确认后通知本页“未导入”列表刷新（279951）。 */
export const BANK_FLOW_UPLOADED_EVENT = "bank-flow-lines-uploaded";
