/**
 * 501099（陶国南 11-02 定方案二）：财务数据分诉讼/非诉（知识产权），同一套页面。
 * - 知识产权中心下“非诉财务中心”（菜单 ipr-finance-*）固定只看非诉；
 * - 财务中心各页默认看诉讼，可切到“非诉”“全部”（全所合计）；
 * - 其他入口（平台财务中心、工作台等）不传，后端不筛。
 * 按当前页面（地址栏 page）区分：财务请求都由当前打开的页面发出。
 */
export type FinanceBusinessType = "诉讼" | "非诉" | "全部";

export const FINANCE_BUSINESS_TYPES: FinanceBusinessType[] = ["诉讼", "非诉", "全部"];

const choices = new Map<string, FinanceBusinessType>();

function currentPage(): string {
  return typeof window === "undefined" ? "" : new URLSearchParams(window.location.search).get("page") || "";
}

export function isNonlitigationFinancePage(page = currentPage()): boolean {
  return page === "ipr-finance" || page.startsWith("ipr-finance-");
}

function isFirmFinancePage(page: string): boolean {
  return page === "finance" || page.startsWith("finance-");
}

export function financeBusinessType(page = currentPage()): FinanceBusinessType | undefined {
  if (isNonlitigationFinancePage(page)) return "非诉";
  if (isFirmFinancePage(page)) return choices.get(page) ?? "诉讼";
  return undefined;
}

/** 与后端 finance_center_identity 同一规则：诉讼律师不看非诉，切换只给能看非诉的人。 */
export function canSeeNonlitigationFinance(): boolean {
  try {
    const user = JSON.parse(localStorage.getItem("user") || "{}");
    const roles: string[] = user.actual_role_ids || [user.actual_role || user.role];
    const menus: string[] = user.menu_keys || [];
    return roles.includes("admin") || roles.includes("auditor")
      || menus.some((key) => key === "ipr-finance" || key.startsWith("ipr-finance-"))
      || menus.includes("finance-receipts-manage") || menus.includes("platform-finance-overview-manage");
  } catch {
    return false;
  }
}

export function canChooseFinanceBusinessType(page = currentPage()): boolean {
  return isFirmFinancePage(page) && canSeeNonlitigationFinance();
}

export function setFinanceBusinessType(value: FinanceBusinessType, page = currentPage()): void {
  choices.set(page, value);
}

/** 非诉财务中心“我的回款”“部门回款”只看本人/本部门登记或认领的回款。 */
export function financeOwnerScope(page = currentPage()): "mine" | "dept" | undefined {
  if (page === "ipr-finance-receipts-mine") return "mine";
  if (page === "ipr-finance-receipts-dept") return "dept";
  return undefined;
}

export function financeBusinessParams(url: string, method: string): Record<string, string> {
  const params: Record<string, string> = {};
  const business = financeBusinessType();
  if (business) params.business_type = business;
  const owner = financeOwnerScope();
  if (owner && method === "get" && url === "/finance/incoming-payments") params.owner_scope = owner;
  return params;
}
