// 知识产权案件单独开标签（BUG20261102003，高勤兰 11-02）：列表里点案号另开“专利 案号”/“商标 案号”标签，
// 原列表标签不动；同一案件只开一个标签。
export type IprCaseTabRecord = { id: number; serial_no: string; data?: { case_kind?: string } | null };

export const IPR_CASE_TAB_PREFIX = "ipr-case-detail-";

export function iprCaseDetailRoute(record: IprCaseTabRecord): string {
  const kind = record.data?.case_kind === "商标" ? "t" : "p";
  return `${IPR_CASE_TAB_PREFIX}${record.id}-${kind}-${encodeURIComponent(record.serial_no || String(record.id))}`;
}

export function parseIprCaseDetailRoute(route: string): { id: number; kind: "专利" | "商标"; serialNo: string } | null {
  const match = route.match(/^ipr-case-detail-(\d+)-([pt])-(.+)$/);
  if (!match) return null;
  let serialNo = match[3];
  try { serialNo = decodeURIComponent(serialNo); } catch { /* 保留原文 */ }
  return { id: Number(match[1]), kind: match[2] === "t" ? "商标" : "专利", serialNo };
}

export function iprCaseTabLabel(route: string): string | null {
  const parsed = parseIprCaseDetailRoute(route);
  return parsed ? `${parsed.kind} ${parsed.serialNo}` : null;
}

/** 501209：工作台“非诉期限预警”的入口，打开知识产权中心并弹出预警列表；有知识产权菜单就能进。 */
export const IPR_WARNINGS_ROUTE = "ipr-warnings";
