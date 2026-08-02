export type ContractListPagination = {
  current: number;
  pageSize: number;
};

export function isContractAuditListView(view: string): boolean;
export function defaultContractListPageSize(view: string): number;
export function readContractListPagination(
  storage: Pick<Storage, "getItem"> | null | undefined,
  view: string,
): ContractListPagination;
export function saveContractListPagination(
  storage: Pick<Storage, "setItem"> | null | undefined,
  view: string,
  value: ContractListPagination,
): ContractListPagination;
