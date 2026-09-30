export const FEEDBACK_ROUTE = "feedback";
export const FEEDBACK_SOURCE_PAGE_KEY = "sunhold:feedback-source-page";
export const FEEDBACK_SOURCE_ROUTE_KEY = "sunhold:feedback-source-route";

export function rememberFeedbackSource(route: string) {
  if (route === FEEDBACK_ROUTE) return;
  sessionStorage.setItem(FEEDBACK_SOURCE_PAGE_KEY, `${window.location.pathname}${window.location.search}`);
  sessionStorage.setItem(FEEDBACK_SOURCE_ROUTE_KEY, route);
}
