import { isWorkspaceRouteGranted, normalizeWorkspaceRoute } from "./workspacePermissions";

type NoticeTarget = {
  source_type: string;
  source_id: number | null;
  source_serial_no?: string;
  target_route?: string;
};

const fallbackRoutes: Record<string, string> = {
  task: "task-my-accepted",
  finance: "finance-audit",
  finance_package: "finance-fee-query",
  finance_settlement: "finance-fee-query",
  finance_archive_settlement: "finance-fee-query",
  contract: "contract-audit",
  case: "case-schedule",
  feedback: "feedback",
};

export function resolveNotificationNavigation(
  item: NoticeTarget,
  grantedMenuKeys: Set<string>,
  iprWarningRoute = "",
) {
  const caseDetailRoute = item.source_type === "case" && item.source_id && item.source_serial_no
    ? `case-detail-${item.source_id}-${encodeURIComponent(item.source_serial_no)}` : "";
  const route = normalizeWorkspaceRoute(caseDetailRoute || iprWarningRoute || item.target_route || fallbackRoutes[item.source_type]
    || (["clue", "notary", "evidence"].includes(item.source_type) ? item.source_type : ""));
  const allowed = !route || isWorkspaceRouteGranted(route, grantedMenuKeys);
  return { route, allowed, caseDetailRoute };
}
