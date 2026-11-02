import type { CaseRow } from "./types";

export function caseCourtDisplay(data: CaseRow["data"], level: string): string {
  const display = data.court_displays?.[level];
  if (!display) return "法院名称未加载";
  if (display.status === "empty") return "—";
  if (display.status === "unresolved") return `法院无法解析（${display.raw}），请完善法院参数`;
  return display.name;
}

/** 列表、表格里显示法院：有解析好的全称用全称，否则显示原值；案件里多存“冀01”这类代号（501149 全站排查）。 */
export function caseCourtName(data: CaseRow["data"] | undefined, level = "court"): string {
  const display = data?.court_displays?.[level];
  if (display?.status === "resolved" && display.name) return display.name;
  if (display?.raw) return display.raw;
  const raw = level === "court" ? data?.court || data?.first_court_name
    : level === "first" ? data?.first_court_name || data?.first_instance_court || data?.court
    : level === "second" ? data?.second_court_name || data?.second_instance_court
    : level === "execution" ? data?.execution_court_name || data?.execution_instance_court
    : level === "retrial" ? data?.retrial_court_name || data?.last_instance_court : "";
  return String(raw || "");
}
