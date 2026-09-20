// 控制台使用独立标签，保留固定业务筛选，避免与普通菜单查询互相覆盖。
export const dashboardWorkspaces: Record<string, { label: string; view: string; kind: "finance" | "case" | "receivable" }> = {
  "official-fee-unpaid": { label: "待缴官费", view: "finance-fee-query", kind: "finance" },
  "refund-pending": { label: "待退费", view: "finance-refund", kind: "finance" },
  "evidence-supplement": { label: "补充证据", view: "case-company", kind: "case" },
  "opinion-supplement": { label: "补充意见", view: "case-company", kind: "case" },
  "appeal-pending": { label: "待上诉", view: "case-company", kind: "case" },
  "execution-pending": { label: "待执行", view: "case-company", kind: "case" },
  "urgent-cases": { label: "紧急案件", view: "case-company", kind: "case" },
  "official-fee-unreceived": { label: "未到官费", view: "contract-receivable-detail", kind: "receivable" },
};

export function dashboardWorkspace(route: string) {
  const key = route.startsWith("dashboard-queue-") ? route.slice("dashboard-queue-".length) : "";
  return Object.hasOwn(dashboardWorkspaces, key) ? { ...dashboardWorkspaces[key], key } : null;
}
