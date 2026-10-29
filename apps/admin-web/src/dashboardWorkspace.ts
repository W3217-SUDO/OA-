// 控制台使用独立标签，保留固定业务筛选，避免与普通菜单查询互相覆盖。
export const dashboardWorkspaces: Record<string, { label: string; view: string; kind: "finance" | "case" | "receivable" }> = {
  "official-fee-unpaid": { label: "待缴官费", view: "finance-fee-query", kind: "finance" },
  // BUG20261028003（范明明 2026-10-29）：能打开请款单审批的人，“待缴官费”进请款单审批，只看待审批的官方费用。
  "official-fee-audit": { label: "待缴官费", view: "finance-payment-audit", kind: "finance" },
  "refund-pending": { label: "待退费", view: "finance-refund", kind: "finance" },
  // BUG20261028004/005：只看内部提成-待审核和内部提成(退费)-待审核。
  "internal-commission-audit": { label: "待审内部提成费用", view: "finance-internal-commission-audit", kind: "finance" },
  "evidence-supplement": { label: "补充证据", view: "case-company", kind: "case" },
  "opinion-supplement": { label: "补充意见", view: "case-company", kind: "case" },
  "appeal-pending": { label: "待上诉", view: "case-company", kind: "case" },
  "execution-pending": { label: "待执行", view: "case-company", kind: "case" },
  "urgent-cases": { label: "紧急案件", view: "case-company", kind: "case" },
  "official-fee-unreceived": { label: "未到官费", view: "contract-receivable-detail", kind: "receivable" },
};

// 进费用列表（费用查询/退费接口）的控制台入口；其他入口（如待缴官费-请款单审批）按各自页面加载数据。
export const FEE_LIST_DASHBOARD_QUEUES = ["official-fee-unpaid", "refund-pending"];

export function dashboardWorkspace(route: string) {
  const key = route.startsWith("dashboard-queue-") ? route.slice("dashboard-queue-".length) : "";
  return Object.hasOwn(dashboardWorkspaces, key) ? { ...dashboardWorkspaces[key], key } : null;
}
