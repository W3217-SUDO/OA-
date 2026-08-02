const DEFAULT_PAGINATION = { current: 1, pageSize: 15 };
const AUDIT_DEFAULT_PAGE_SIZE = 20;
const PAGE_SIZES = new Set([10, 15, 20, 50, 100, 200]);

const storageKey = (view) => `sunhold:contract-pagination:${view}`;

export const isContractAuditListView = (view) =>
  view === "contract-audit" || view.startsWith("contract-audit-");

export const defaultContractListPageSize = (view) =>
  isContractAuditListView(view) ? AUDIT_DEFAULT_PAGE_SIZE : DEFAULT_PAGINATION.pageSize;

const normalize = (value, view) => {
  const current = Number(value?.current);
  const pageSize = Number(value?.pageSize);
  return {
    current: Number.isInteger(current) && current > 0 ? current : DEFAULT_PAGINATION.current,
    pageSize: PAGE_SIZES.has(pageSize) ? pageSize : defaultContractListPageSize(view),
  };
};

export const readContractListPagination = (storage, view) => {
  if (!storage) return { current: 1, pageSize: defaultContractListPageSize(view) };
  try {
    return normalize(JSON.parse(storage.getItem(storageKey(view)) || "null"), view);
  } catch {
    return { current: 1, pageSize: defaultContractListPageSize(view) };
  }
};

export const saveContractListPagination = (storage, view, value) => {
  const normalized = normalize(value, view);
  storage?.setItem(storageKey(view), JSON.stringify(normalized));
  return normalized;
};
