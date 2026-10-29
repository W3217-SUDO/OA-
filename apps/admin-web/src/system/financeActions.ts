// 财务回款/付款/费用的编辑、删除（陶威 2026-10-28 定）：只有管理页面默认带出，员工管理里可按人勾选或取消。
// 页面和动作的对应与后端 constants.FINANCE_EDIT_DELETE_ACTIONS 一致。
export const FINANCE_ACTIONS = [
  { value: "finance.receipt.update", label: "编辑回款" },
  { value: "finance.receipt.delete", label: "删除回款" },
  { value: "finance.payment.update", label: "编辑付款包" },
  { value: "finance.payment.delete", label: "删除付款包" },
  { value: "finance.fee.update", label: "编辑费用" },
  { value: "finance.fee.delete", label: "删除费用" },
];
export const FINANCE_ACTION_KEYS = FINANCE_ACTIONS.map((item) => item.value);
// 可以在员工管理里给别人配置上面 6 项。
export const FINANCE_CONFIGURE_ACTION = "finance.actions.configure";

// 回款管理、付款打包-管理、请款单审批；律师能看的回款领取、到账查询、付款单查询、费用查询等不带。
const ACTION_PAGES: Record<string, string> = {
  "finance.receipt.": "finance-receipts-manage",
  "finance.payment.": "finance-payment-package-manage",
  "finance.fee.": "finance-payment-audit",
};

/** 勾选的管理页面默认带出的财务动作。 */
export function pageFinanceActions(menuKeys: string[]): string[] {
  // BUG20261028012：平台财务中心“回款管理”和财务中心“回款管理”带同一组回款编辑、删除开关。
  const pages = menuKeys.includes("platform-finance-overview-manage") ? [...menuKeys, "finance-receipts-manage"] : menuKeys;
  return FINANCE_ACTION_KEYS.filter((code) =>
    Object.entries(ACTION_PAGES).some(([action, page]) => code.startsWith(action) && pages.includes(page)));
}
