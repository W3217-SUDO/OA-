export const GLOBAL_CASE_SEARCH_ROUTE = "case-mine";
export const GLOBAL_CASE_SEARCH_CONTEXT_KEY = "sunhold:case-list-return";

export const buildGlobalCaseSearchContext = (value) => {
  const keyword = String(value ?? "").trim();
  if (!keyword) return null;
  return {
    route: GLOBAL_CASE_SEARCH_ROUTE,
    page: 1,
    pageSize: 15,
    query: { keyword },
  };
};

export const readStoredGlobalCaseSearchContext = (storage) => {
  try {
    const raw = storage?.getItem?.(GLOBAL_CASE_SEARCH_CONTEXT_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};
