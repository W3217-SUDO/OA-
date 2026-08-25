export const GLOBAL_CASE_SEARCH_ROUTE: string;
export const GLOBAL_CASE_SEARCH_CONTEXT_KEY: string;
export function buildGlobalCaseSearchContext(value: unknown): {
  route: string;
  page: number;
  pageSize: number;
  query: { keyword: string };
} | null;
export function readStoredGlobalCaseSearchContext(storage: Pick<Storage, "getItem">): {
  route?: string;
  page?: number;
  pageSize?: number;
  query?: Record<string, unknown>;
} | null;
