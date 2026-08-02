export type ContractListPagination = {
  current: number;
  pageSize: number;
};

type PaginationStorage = Pick<Storage, "getItem" | "setItem">;

const DEFAULT_PAGINATION: ContractListPagination = {
  current: 1,
  pageSize: 15,
};
const PAGE_SIZES = new Set([10, 15, 20, 50, 100, 200]);
const storageKey = (view: string) => `sunhold:contract-pagination:${view}`;

const normalize = (value: Partial<ContractListPagination> | null | undefined): ContractListPagination => {
  const current = Number(value?.current);
  const pageSize = Number(value?.pageSize);
  return {
    current: Number.isInteger(current) && current > 0 ? current : DEFAULT_PAGINATION.current,
    pageSize: PAGE_SIZES.has(pageSize) ? pageSize : DEFAULT_PAGINATION.pageSize,
  };
};

export const readContractListPagination = (
  storage: Pick<PaginationStorage, "getItem"> | null | undefined,
  view: string,
): ContractListPagination => {
  if (!storage) return { ...DEFAULT_PAGINATION };
  try {
    return normalize(JSON.parse(storage.getItem(storageKey(view)) || "null"));
  } catch {
    return { ...DEFAULT_PAGINATION };
  }
};

export const saveContractListPagination = (
  storage: Pick<PaginationStorage, "setItem"> | null | undefined,
  view: string,
  value: ContractListPagination,
): ContractListPagination => {
  const normalized = normalize(value);
  storage?.setItem(storageKey(view), JSON.stringify(normalized));
  return normalized;
};
