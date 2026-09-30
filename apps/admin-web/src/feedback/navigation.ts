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
