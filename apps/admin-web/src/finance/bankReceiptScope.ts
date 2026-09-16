const bankNames: Record<string, string[]> = {
  icbc: ["工行", "工商银行"],
  citic: ["中信"],
  boc: ["中行", "中国银行"],
  cmb: ["招商", "招行"],
};

export function receiptBankCode(route: string): string | undefined {
  const match = /^finance-receipts-(icbc|citic|boc|cmb)$/.exec(route);
  return match?.[1];
}

export function matchesReceiptBank(source: string | null | undefined, code: string): boolean {
  const value = (source || "").trim().toLowerCase();
  return value === code || (bankNames[code] || []).some((name) => value.includes(name));
}
