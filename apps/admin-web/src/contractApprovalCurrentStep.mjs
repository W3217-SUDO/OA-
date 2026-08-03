const isApprovalStep = (value) => value && typeof value === "object";

export const selectContractCurrentApprovalStep = (payload = {}) => {
  const current = payload?.current_step;
  if (isApprovalStep(current)) return current;
  const items = Array.isArray(payload?.items) ? payload.items : [];
  return items.find((item) => isApprovalStep(item) && ["审批中", "待审批", "P", "Pending"].includes(String(item.status || ""))) || null;
};
