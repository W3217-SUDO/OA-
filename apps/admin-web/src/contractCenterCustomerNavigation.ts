export type ContractCenterNavigate = (target: string) => void;

export type ContractCustomerRelationTarget = {
  serial_no?: string;
  title?: string;
  target?: string;
};

export const buildContractCustomerQueryFromRelation = (
  target?: ContractCustomerRelationTarget | null,
): { customer: string; customer_no?: string; exclude_archived: boolean } | null => {
  if (!target || target.target !== "contracts") return null;
  const customerNo = String(target.serial_no || "").trim();
  const customer = String(target.title || customerNo).trim();
  return customer ? { customer, ...(customerNo ? { customer_no: customerNo } : {}), exclude_archived: true } : null;
};

export const openContractCustomerCreation = (
  onNavigate?: ContractCenterNavigate,
): boolean => {
  if (!onNavigate) return false;
  onNavigate("customer-new");
  return true;
};
