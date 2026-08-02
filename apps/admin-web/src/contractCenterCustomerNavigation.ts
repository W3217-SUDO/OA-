export type ContractCenterNavigate = (target: string) => void;

export const openContractCustomerCreation = (
  onNavigate?: ContractCenterNavigate,
): boolean => {
  if (!onNavigate) return false;
  onNavigate("customer-new");
  return true;
};
