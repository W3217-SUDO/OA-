// 财务回款/付款/费用的编辑、删除（用户 2026-10-28 定）：能打开对应页面默认就有，员工管理里可按人勾选或取消。
// 页面和动作的对应与后端 finance_action_permissions.FINANCE_ACTION_PAGE_PREFIXES 一致。
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

const PAGE_PREFIXES: Record<string, string[]> = {
  "finance.receipt.": ["finance-receipts"],
  "finance.payment.": ["finance-payment"],
  "finance.fee.": ["finance-fee-query"],
};

/** 勾选的页面默认带出的财务动作；“我的…”个人页面不算。 */
export function pageFinanceActions(menuKeys: string[]): string[] {
  const menus = menuKeys.filter((key) => !key.endsWith("-mine"));
  return FINANCE_ACTION_KEYS.filter((code) => {
    const prefixes = Object.entries(PAGE_PREFIXES).find(([action]) => code.startsWith(action))?.[1] || [];
    return menus.some((menu) => prefixes.some((prefix) => menu.startsWith(prefix)));
  });
}
