export const FEEDBACK_ROUTE = "feedback";
export const FEEDBACK_SOURCE_PAGE_KEY = "sunhold:feedback-source-page";
export const FEEDBACK_SOURCE_ROUTE_KEY = "sunhold:feedback-source-route";
// 按页面记下的按钮清单 { route: 按钮名[] }，退出登录时随其他会话导航数据一起清掉。
export const FEEDBACK_SOURCE_CONTROLS_KEY = "sunhold:feedback-page-controls";
const FEEDBACK_TARGET_KEY = "sunhold:feedback-target";
const MAX_CONTROLS = 40;
const MAX_PAGES = 30;

// 页面打开期间读出页面上的按钮和标签页名称，反馈时勾选哪个页面就能点选那个页面的“哪个按钮有问题”。
// 分页按钮跳过；名称里的统计数字（“(2021)”“433件”“595”）会变，去掉。
function collectPageControls(): string[] {
  const root = document.querySelector("main.page-workbench");
  if (!root) return [];
  const names: string[] = [];
  root.querySelectorAll<HTMLElement>("button, [role=tab], .ant-tabs-tab-btn, .ant-segmented-item-label").forEach((element) => {
    // 表格行、列表项里的按钮是数据（案号、客户名），不是页面功能。
    if (element.closest("tbody, li, [role=row], [role=listitem], .ant-list-item, .ant-timeline-item, .ant-pagination, .ant-select-dropdown, .ant-picker-dropdown")) return;
    if (element.closest("[aria-hidden=true]") || !element.getClientRects().length) return;
    const text = (element.innerText || element.getAttribute("aria-label") || element.title || "")
      .replace(/\s+/g, "").replace(/[（(]\d+[)）]/g, "").replace(/\d+(?:\.\d+)?(?:件|元|条|个|项)?/g, "")
      // 去掉数字后留下的空括号（如“等待公证书【】”）。
      .replace(/[【\[（(]\s*[】\]）)]/g, "").trim();
    // 只有符号的按钮（如折叠箭头“‹”）不是页面功能。
    if (!/[\u4e00-\u9fa5A-Za-z]/.test(text)) return;
    // 带冒号的是“删除对话：某对话名”这类拼了数据的按钮，不是固定功能。
    if (/[:：]/.test(text)) return;
    if (text.length <= 20 && !names.includes(text)) names.push(text);
  });
  return names.slice(0, MAX_CONTROLS);
}

export function readFeedbackPageControls(): Record<string, string[]> {
  try {
    const value = JSON.parse(sessionStorage.getItem(FEEDBACK_SOURCE_CONTROLS_KEY) || "{}");
    if (!value || typeof value !== "object" || Array.isArray(value)) return {};
    return Object.fromEntries(Object.entries(value)
      .filter(([, names]) => Array.isArray(names))
      .map(([route, names]) => [route, (names as unknown[]).filter((item): item is string => typeof item === "string")]));
  } catch {
    return {};
  }
}

// 记下当前页面的按钮；页面还没渲染出按钮时不覆盖之前记到的清单。最近打开的页面排在最后，最多留 30 个页面。
export function rememberPageControls(route: string) {
  if (!route || route === FEEDBACK_ROUTE) return;
  const names = collectPageControls();
  if (!names.length) return;
  const map = readFeedbackPageControls();
  delete map[route];
  map[route] = names;
  const entries = Object.entries(map).slice(-MAX_PAGES);
  try { sessionStorage.setItem(FEEDBACK_SOURCE_CONTROLS_KEY, JSON.stringify(Object.fromEntries(entries))); } catch { /* 存储满时只是少记 */ }
}

export function rememberFeedbackSource(route: string) {
  if (route === FEEDBACK_ROUTE) return;
  sessionStorage.setItem(FEEDBACK_SOURCE_PAGE_KEY, `${window.location.pathname}${window.location.search}`);
  sessionStorage.setItem(FEEDBACK_SOURCE_ROUTE_KEY, route);
  rememberPageControls(route);
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
