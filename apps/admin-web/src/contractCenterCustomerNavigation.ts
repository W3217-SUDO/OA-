export type ContractCenterNavigate = (target: string) => void;

export type ContractCustomerRelationTarget = {
  serial_no?: string;
  title?: string;
  target?: string;
};

export const buildContractCustomerQueryFromRelation = (
  target?: ContractCustomerRelationTarget | null,
): { customer: string } | null => {
  if (!target || target.target !== "contracts") return null;
  const customer = String(target.title || target.serial_no || "").trim();
  return customer ? { customer } : null;
};

export const openContractCustomerCreation = (
  onNavigate?: ContractCenterNavigate,
): boolean => {
  if (!onNavigate) return false;
  onNavigate("customer-new");
  return true;
};
