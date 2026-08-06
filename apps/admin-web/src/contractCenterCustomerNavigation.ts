export type ContractCenterNavigate = (target: string) => void;

export type ContractCustomerRelationTarget = {
  id?: number;
  serial_no?: string;
  title?: string;
  target?: string;
};

export const buildContractCustomerQueryFromRelation = (
  target?: ContractCustomerRelationTarget | null,
): { customer_id?: number; customer_no?: string; customer?: string; exclude_archived: boolean } | null => {
  if (!target || target.target !== "contracts") return null;
  const customerId = Number(target.id || 0) || undefined;
  const customerNo = String(target.serial_no || "").trim() || undefined;
  const customer = String(target.title || "").trim() || undefined;
  return customerId || customerNo || customer
    ? { customer_id: customerId, customer_no: customerNo, customer, exclude_archived: true }
    : null;
};

export const openContractCustomerCreation = (
  onNavigate?: ContractCenterNavigate,
): boolean => {
  if (!onNavigate) return false;
  onNavigate("customer-new");
  return true;
};
