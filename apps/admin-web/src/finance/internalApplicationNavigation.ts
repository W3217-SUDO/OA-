import type { FinanceOriginalQuery } from "./originalQuery";

const storageKey = "sunhold:internal-application-query";

export function rememberInternalApplicationQuery(applicationNo: string, caseNo: string): void {
  if (!applicationNo.trim() || !caseNo.trim()) throw new Error("请款单号或案件编号缺失，无法定位");
  sessionStorage.setItem(storageKey, JSON.stringify({ applicationNo: applicationNo.trim(), caseNo: caseNo.trim() }));
}

export function readInternalApplicationQuery(route: string): FinanceOriginalQuery {
  if (route !== "finance-internal-mine") return {};
  const raw = sessionStorage.getItem(storageKey);
  if (!raw) return {};
  const query = JSON.parse(raw);
  if (typeof query.applicationNo !== "string" || !query.applicationNo.trim()
      || typeof query.caseNo !== "string" || !query.caseNo.trim()) {
    throw new Error("请款单定位参数无效");
  }
  return { routeField4: query.caseNo, routeField5: query.applicationNo };
}

export function clearInternalApplicationQuery(): void {
  sessionStorage.removeItem(storageKey);
}
