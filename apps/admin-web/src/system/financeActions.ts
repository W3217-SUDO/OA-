// 财务回款/付款/费用的编辑、删除（陶威 2026-10-28 定）：只有管理页面默认带出，员工管理里可按人勾选或取消。
// 页面和动作的对应与后端 constants.FINANCE_EDIT_DELETE_ACTIONS 一致。
export const FINANCE_ACTIONS = [
  { value: "finance.receipt.update", label: "编辑回款" },
  { value: "finance.receipt.delete", label: "删除回款" },
  { value: "finance.payment.update", label: "编辑付款包" },
  { value: "finance.payment.delete", label: "删除付款包" },
  { value: "finance.fee.update", label: "编辑费用" },
  { value: "finance.fee.delete", label: "删除费用" },
  // BUG20261028012：回款领取、待分配回款、已分配回款页面的删除各自单独设。
  { value: "finance.receipt.claim.delete", label: "删除回款（回款领取）" },
  { value: "finance.receipt.pending.delete", label: "删除回款（待分配回款）" },
  { value: "finance.receipt.allocated.delete", label: "删除回款（已分配回款）" },
];
export const FINANCE_ACTION_KEYS = FINANCE_ACTIONS.map((item) => item.value);
// 可以在员工管理里给别人配置上面 6 项。
export const FINANCE_CONFIGURE_ACTION = "finance.actions.configure";

// 每个动作对应的页面（与后端 FINANCE_EDIT_DELETE_ACTIONS 第二列一致）；到账查询、付款单查询、费用查询等不带。
const ACTION_PAGES: Record<string, string> = {
  "finance.receipt.update": "finance-receipts-manage", "finance.receipt.delete": "finance-receipts-manage",
  "finance.receipt.claim.delete": "finance-receipts-claim", "finance.receipt.pending.delete": "finance-receipts-pending",
  "finance.receipt.allocated.delete": "finance-receipts-allocated",
  "finance.payment.update": "finance-payment-package-manage", "finance.payment.delete": "finance-payment-package-manage",
  "finance.fee.update": "finance-payment-audit", "finance.fee.delete": "finance-payment-audit",
};
const PLATFORM_RECEIPT_PAGES: Record<string, string> = {
  "platform-finance-overview-manage": "finance-receipts-manage", "platform-finance-overview-claim": "finance-receipts-claim",
  "platform-finance-overview-pending": "finance-receipts-pending", "platform-finance-overview-allocated": "finance-receipts-allocated",
};

/** 勾选的管理页面默认带出的财务动作。 */
export function pageFinanceActions(menuKeys: string[]): string[] {
  // BUG20261028012：平台财务中心的回款页面和财务中心同名页面带同一组开关。
  const pages = [...menuKeys, ...menuKeys.map((key) => PLATFORM_RECEIPT_PAGES[key]).filter(Boolean)];
  return FINANCE_ACTION_KEYS.filter((code) => pages.includes(ACTION_PAGES[code]));
}
