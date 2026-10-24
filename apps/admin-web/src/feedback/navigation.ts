export const FEEDBACK_ROUTE = "feedback";
export const FEEDBACK_SOURCE_PAGE_KEY = "sunhold:feedback-source-page";
export const FEEDBACK_SOURCE_ROUTE_KEY = "sunhold:feedback-source-route";
const FEEDBACK_TARGET_KEY = "sunhold:feedback-target";

export function rememberFeedbackSource(route: string) {
  if (route === FEEDBACK_ROUTE) return;
  sessionStorage.setItem(FEEDBACK_SOURCE_PAGE_KEY, `${window.location.pathname}${window.location.search}`);
  sessionStorage.setItem(FEEDBACK_SOURCE_ROUTE_KEY, route);
}

export function rememberFeedbackTarget(id: number) {
  sessionStorage.setItem(FEEDBACK_TARGET_KEY, String(id));
  window.dispatchEvent(new Event("sunhold:feedback-target"));
}

export function consumeFeedbackTarget(): number | null {
  const value = sessionStorage.getItem(FEEDBACK_TARGET_KEY);
  sessionStorage.removeItem(FEEDBACK_TARGET_KEY);
  const id = Number(value);
  return Number.isInteger(id) && id > 0 ? id : null;
}

export type FeedbackPageOption = { key: string; label: string };

const DETAIL_PAGE_PREFIXES: [string, string][] = [
  ["case-detail-", "案件详情"], ["contract-detail-", "合同详情"], ["customer-detail-", "客户详情"],
];

// 详情页的页签名只有编号，反馈里补上页面类型，处理人一眼能看出是哪类页面。
export function feedbackPageLabel(key: string, label: string) {
  const prefix = DETAIL_PAGE_PREFIXES.find(([route]) => key.startsWith(route))?.[1];
  return prefix && !label.startsWith(prefix) ? `${prefix} · ${label}` : label;
}
