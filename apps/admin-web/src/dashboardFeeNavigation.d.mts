export type DashboardFeeQuery = {
  scope?: "mine" | "company";
  unpaid_official?: boolean;
};

export function rememberDashboardFeeQuery(query?: DashboardFeeQuery): void;
export function consumeDashboardFeeQuery(initialView: string): Record<string, unknown>;
export function clearDashboardFeeQuery(): void;
export function preserveDashboardFeeQueryContext(query: Record<string, unknown>): Record<string, unknown>;
