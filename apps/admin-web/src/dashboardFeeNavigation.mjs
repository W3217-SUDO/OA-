export const DASHBOARD_FEE_QUERY_STORAGE_KEY = "sunhold:dashboard-fee-query";

export function rememberDashboardFeeQuery(query, storage = globalThis.sessionStorage) {
  if (!query || !storage) return;
  storage.setItem(DASHBOARD_FEE_QUERY_STORAGE_KEY, JSON.stringify(query));
}

export function consumeDashboardFeeQuery(initialView, storage = globalThis.sessionStorage) {
  if (initialView !== "finance-fee-query" || !storage) return {};
  const raw = storage.getItem(DASHBOARD_FEE_QUERY_STORAGE_KEY);
  if (!raw) return {};
  try {
    const query = JSON.parse(raw);
    if (query?.scope !== "mine" || query?.unpaid_official !== true) return {};
    return {
      dashboardScope: "mine",
      dashboardUnpaidOfficial: true,
    };
  } catch {
    return {};
  }
}

export function clearDashboardFeeQuery(storage = globalThis.sessionStorage) {
  storage?.removeItem(DASHBOARD_FEE_QUERY_STORAGE_KEY);
}

export function preserveDashboardFeeQueryContext(query) {
  return query?.dashboardScope === "mine" && query?.dashboardUnpaidOfficial === true
    ? { dashboardScope: "mine", dashboardUnpaidOfficial: true }
    : {};
}
