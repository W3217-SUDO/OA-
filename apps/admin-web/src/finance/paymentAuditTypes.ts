import type { FeeTypeOption } from "./FeeTypePicker";

// 请款单审批的“类型”只留官方费用里这几种和其他费用，其余（代理费、核定成本等）默认不显示，
// 管理员可打开“显示全部类型”审批（范明明 BUG20261030003，2026-10-30）。与后端 contract_payment_lifecycle 同一口径。
export const PAYMENT_AUDIT_OFFICIAL_SUBTYPES = ["诉讼费", "一审诉讼费", "二审诉讼费", "再审诉讼费", "公证费", "保全费", "执行费"];
export const PAYMENT_AUDIT_OTHER_FEE_TYPE = "其他费用";

type AuditItem = { module?: string; data?: Record<string, any> };

const typePairs = (item: AuditItem): [string, string][] => {
  const data = item.data || {};
  if (item.module === "contract_payment")
    return (Array.isArray(data.lines) ? data.lines : []).map((line: any) => [String(line?.fee_type || ""), String(line?.expense_subtype || "")]);
  return [[String(data.fee_type || ""), String(data.expense_subtype || data.fee_type_name || "")]];
};

export const isPaymentAuditOfficialType = (item: AuditItem) =>
  typePairs(item).some(([base, sub]) => base === "官方费用" && PAYMENT_AUDIT_OFFICIAL_SUBTYPES.includes(sub));

export const isPaymentAuditTypeVisible = (item: AuditItem) =>
  isPaymentAuditOfficialType(item) || typePairs(item).some(([base]) => base === PAYMENT_AUDIT_OTHER_FEE_TYPE);

/** “费用类型”筛选只列官方费用里这几种和其他费用（含下级）。 */
export function paymentAuditFeeTypeItems(items: FeeTypeOption[]) {
  const byCode = new Map(items.map(item => [item.code, item]));
  const rootOf = (item: FeeTypeOption) => {
    let current = item;
    const seen = new Set<string>();
    while (current.parent_code && byCode.has(current.parent_code) && !seen.has(current.code)) {
      seen.add(current.code);
      current = byCode.get(current.parent_code)!;
    }
    return current;
  };
  return items.filter(item => {
    const root = rootOf(item);
    if (root.name === PAYMENT_AUDIT_OTHER_FEE_TYPE) return true;
    if (root.name !== "官方费用") return false;
    return item === root || PAYMENT_AUDIT_OFFICIAL_SUBTYPES.includes(item.name);
  });
}
