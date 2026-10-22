import type { CaseRow } from "./types";

export function caseCourtDisplay(data: CaseRow["data"], level: string): string {
  const display = data.court_displays?.[level];
  if (!display) return "法院名称未加载";
  if (display.status === "empty") return "—";
  if (display.status === "unresolved") return `法院无法解析（${display.raw}），请完善法院参数`;
  return display.name;
}
